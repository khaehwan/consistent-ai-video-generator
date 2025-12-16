#!/usr/bin/env python3
"""
Raspberry Pi Wearable Sensor System
Main application entry point for virtual production behavior detection
"""

import sys
import os
import signal
import time
import argparse
import yaml
import json
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from utils.logger import setup_logging, EventLogger, get_logger
from utils.display import AnimationController, DisplayPatterns
from api.client import APIClient
from api.websocket_client import VPWebSocketClient  # VP WebSocket 클라이언트
from behaviors.detector import BehaviorDetector


class WearableSensorApp:
    """
    Main application class for the wearable sensor system
    """

    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize the application

        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_file)

        # Setup logging
        self.logger = setup_logging(self.config)
        self.event_logger = EventLogger()

        # Initialize components
        self.api_client = None
        self.vp_ws_client = None  # VP WebSocket 클라이언트
        self.behavior_detector = None
        self.animation_controller = None

        # Running state
        self.running = False

        self.logger.info("Wearable Sensor Application initialized")

    def _load_config(self, config_file: str) -> dict:
        """
        Load configuration from YAML file

        Args:
            config_file: Path to config file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"Configuration loaded from {config_file}")
            return config
        except Exception as e:
            print(f"Failed to load configuration: {e}")
            print("Using default configuration")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """
        Get default configuration

        Returns:
            Default configuration dictionary
        """
        return {
            'api': {
                'base_url': 'http://localhost:8000',
                'endpoints': {
                    'behavior': '/api/behavior',
                    'status': '/api/status',
                    'heartbeat': '/api/heartbeat'
                },
                'timeout': 5,
                'retry_attempts': 3
            },
            'sensors': {
                'sense_hat': {'enabled': True},
                'camera': {'enabled': True},
                'microphone': {'enabled': True}
            },
            'behaviors': {
                'movement': {'enabled': True},
                'fall': {'enabled': True},
                'turn': {'enabled': True},
                'shout': {'enabled': True},
                'brightness': {'enabled': True}
            },
            'system': {
                'device_id': 'rpi_wearable_001',
                'offline_storage': True
            },
            'logging': {
                'level': 'INFO',
                'console_output': True
            }
        }

    def initialize_components(self):
        """Initialize all system components"""
        self.logger.info("Initializing system components...")

        # Initialize API client (HTTP - 백업용)
        try:
            self.api_client = APIClient(self.config)
            self.logger.info("API client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize API client: {e}")
            self.api_client = None

        # Initialize VP WebSocket client (실시간 통신용)
        try:
            self.vp_ws_client = VPWebSocketClient(self.config)
            self.logger.info("VP WebSocket client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize VP WebSocket client: {e}")
            self.vp_ws_client = None

        # Initialize behavior detector
        # WebSocket 클라이언트를 우선 사용, 없으면 HTTP 클라이언트 사용
        try:
            primary_client = self.vp_ws_client if self.vp_ws_client else self.api_client
            self.behavior_detector = BehaviorDetector(
                self.config,
                primary_client
            )
            self.logger.info("Behavior detector initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize behavior detector: {e}")
            raise

        # Initialize animation controller
        try:
            if self.behavior_detector.sense_hat:
                self.animation_controller = AnimationController(self.behavior_detector.sense_hat)
                self.logger.info("Animation controller initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize animation controller: {e}")

        # Register behavior callbacks for logging
        self._register_event_callbacks()

    def _register_event_callbacks(self):
        """Register callbacks for behavior events"""
        # Movement events
        self.behavior_detector.movement_detector.register_state_callback(
            lambda new, old: self.event_logger.log_event(new.value, {'previous': old.value})
        )

        # Fall events
        self.behavior_detector.fall_detector.register_fall_callback(
            lambda acc, orient: self.event_logger.log_event('fall', {
                'acceleration': acc,
                'orientation_change': orient
            })
        )

        # Turn events
        self.behavior_detector.turn_detector.register_turn_callback(
            lambda rot, dur: self.event_logger.log_event('turn', {
                'rotation': rot,
                'duration': dur
            })
        )

        # Shout events
        self.behavior_detector.shout_detector.register_shout_callback(
            lambda vol, dur: self.event_logger.log_event('shout', {
                'volume': vol,
                'duration': dur
            })
        )

        # Brightness events
        self.behavior_detector.brightness_detector.register_state_callback(
            lambda new, old: self.event_logger.log_event(new.value, {'previous': old.value})
        )

    def start(self):
        """Start the application"""
        self.logger.info("Starting Wearable Sensor System...")

        # Connect to VP WebSocket server
        if self.vp_ws_client:
            try:
                self.vp_ws_client.connect()
                self.logger.info("VP WebSocket connection started")
            except Exception as e:
                self.logger.error(f"Failed to start VP WebSocket connection: {e}")

        # Test API connection (백업용)
        if self.api_client:
            if self.api_client.test_connection():
                self.logger.info("API connection successful")
            else:
                self.logger.warning("API connection failed - running in offline mode")

        # Start behavior detection (includes startup animation and READY message)
        self.behavior_detector.start()

        self.running = True
        self.logger.info("System started successfully")

    def stop(self):
        """Stop the application"""
        self.logger.info("Stopping Wearable Sensor System...")

        self.running = False

        # Stop behavior detection
        if self.behavior_detector:
            self.behavior_detector.stop()

        # Close VP WebSocket client
        if self.vp_ws_client:
            self.vp_ws_client.close()
            self.logger.info("VP WebSocket connection closed")

        # Close API client
        if self.api_client:
            self.api_client.close()

        # Show shutdown animation
        if self.behavior_detector and self.behavior_detector.sense_hat:
            self.behavior_detector.sense_hat.show_text("BYE", color=[255, 0, 0])
            time.sleep(1)
            self.behavior_detector.sense_hat.clear_display()

        self.logger.info("System stopped")

    def run(self):
        """Run the main application loop"""
        self.logger.info("Entering main loop...")

        try:
            while self.running:
                # Get system status
                status = self.behavior_detector.get_status()

                # Log statistics periodically
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    self.logger.info(f"System status: {json.dumps(status['statistics'])}")

                # Check for user input (if running interactively)
                # This could be extended with a command interface

                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")

        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

        finally:
            self.stop()

    def handle_command(self, command: str):
        """
        Handle user commands

        Args:
            command: Command string
        """
        commands = {
            'status': self._cmd_status,
            'calibrate': self._cmd_calibrate,
            'test': self._cmd_test,
            'reset': self._cmd_reset,
            'help': self._cmd_help
        }

        cmd_parts = command.strip().lower().split()
        if not cmd_parts:
            return

        cmd = cmd_parts[0]
        if cmd in commands:
            commands[cmd]()
        else:
            self.logger.warning(f"Unknown command: {cmd}")

    def _cmd_status(self):
        """Show system status"""
        status = self.behavior_detector.get_status()
        self.logger.info("System Status:")
        self.logger.info(f"  Running: {status['running']}")
        self.logger.info(f"  Uptime: {status['uptime_seconds']:.1f} seconds")
        self.logger.info(f"  Events: {status['statistics']['events_detected']}")
        self.logger.info(f"  API: {'Connected' if self.api_client.is_connected() else 'Disconnected'}")

    def _cmd_calibrate(self):
        """Calibrate all sensors"""
        self.logger.info("Starting calibration...")
        self.behavior_detector.calibrate_all()
        self.logger.info("Calibration complete")

    def _cmd_test(self):
        """Test all displays"""
        self.logger.info("Testing display...")
        self.behavior_detector.test_display()
        self.logger.info("Display test complete")

    def _cmd_reset(self):
        """Reset all detectors"""
        self.logger.info("Resetting system...")
        self.behavior_detector.reset_all()
        self.logger.info("Reset complete")

    def _cmd_help(self):
        """Show help"""
        self.logger.info("Available commands:")
        self.logger.info("  status    - Show system status")
        self.logger.info("  calibrate - Calibrate sensors")
        self.logger.info("  test      - Test displays")
        self.logger.info("  reset     - Reset detectors")
        self.logger.info("  help      - Show this help")


def signal_handler(signum, frame):
    """Handle system signals"""
    print(f"\nSignal {signum} received, shutting down...")
    sys.exit(0)


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Raspberry Pi Wearable Sensor System')
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode'
    )
    parser.add_argument(
        '--calibrate',
        action='store_true',
        help='Calibrate sensors on startup'
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help='Run in offline mode (no API connection)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Create application instance
    app = WearableSensorApp(args.config)

    # Override configuration based on arguments
    if args.debug:
        app.config['logging']['level'] = 'DEBUG'
        app.logger = setup_logging(app.config)

    if args.offline:
        app.config['api']['base_url'] = ''
        app.logger.info("Running in offline mode")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize components
        app.initialize_components()

        # Calibrate if requested
        if args.calibrate:
            app.behavior_detector.calibrate_all()

        # Run test mode or normal mode
        if args.test:
            app.logger.info("Running in test mode...")
            app.behavior_detector.test_display()

            # Test each behavior detection
            app.logger.info("Testing behavior detections...")

            # You can add specific test sequences here
            time.sleep(5)

            app.logger.info("Test complete")
        else:
            # Start normal operation
            app.start()
            app.run()

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()