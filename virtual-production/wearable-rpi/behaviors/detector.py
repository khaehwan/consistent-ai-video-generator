"""
Main Behavior Detector Orchestrator
Coordinates all behavior detection modules and manages API communication
"""

import logging
import threading
import time
import json
from typing import Dict, Optional, List, Callable
from datetime import datetime
from queue import Queue, Empty

# Import sensor handlers
from sensors.sense_hat_handler import SenseHatHandler
from sensors.camera_handler import CameraHandler
from sensors.microphone_handler import MicrophoneHandler

# Import behavior detectors
from behaviors.movement_detector import MovementDetector, MovementState
from behaviors.fall_detector import FallDetector, FallState
from behaviors.turn_detector import TurnDetector
from behaviors.shout_detector import ShoutDetector
from behaviors.brightness_detector import BrightnessDetector, BrightnessState
from behaviors.compass_detector import CompassDetector

# Import LED display
from utils.led_display import LEDDisplay


class BehaviorDetector:
    """
    Main orchestrator for all behavior detection
    """

    def __init__(self, config: Dict, api_client=None):
        """
        Initialize the behavior detector

        Args:
            config: Configuration dictionary
            api_client: Optional API client for sending events
        """
        self.config = config
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)

        # Initialize sensor handlers
        self.logger.info("Initializing sensor handlers...")
        self.sense_hat = SenseHatHandler(config)
        self.camera = CameraHandler(config)
        self.microphone = MicrophoneHandler(config)

        # Initialize behavior detectors
        self.logger.info("Initializing behavior detectors...")
        self.movement_detector = MovementDetector(config, self.sense_hat)
        self.fall_detector = FallDetector(config, self.sense_hat)
        self.turn_detector = TurnDetector(config, self.sense_hat)
        self.shout_detector = ShoutDetector(config, self.microphone)
        self.brightness_detector = BrightnessDetector(config, self.camera)
        self.compass_detector = CompassDetector(config, self.sense_hat)

        # Initialize LED display
        self.led_display = LEDDisplay(self.sense_hat)
        self.logger.info("LED display initialized")

        # Event queue for API communication
        self.event_queue = Queue()
        self.event_thread = None

        # Statistics
        self.stats = {
            'events_detected': 0,
            'events_sent': 0,
            'events_failed': 0,
            'start_time': time.time()
        }

        # Running state
        self.running = False

        # Register callbacks for all detectors
        self._register_callbacks()

        # Register joystick callback for recalibration
        if self.sense_hat and hasattr(self.sense_hat, 'register_joystick_callback'):
            self.sense_hat.register_joystick_callback('middle', self._on_joystick_recalibrate)
            self.logger.info("Joystick recalibration callback registered")

        self.logger.info("Behavior detector initialized")

    def _register_callbacks(self):
        """Register callbacks for all behavior detectors"""
        # Movement detector callbacks
        self.movement_detector.register_state_callback(self._on_movement_state_change)

        # Fall detector callbacks
        self.fall_detector.register_fall_callback(self._on_fall_detected)

        # Turn detector callbacks
        self.turn_detector.register_turn_callback(self._on_turn_detected)

        # Shout detector callbacks
        self.shout_detector.register_shout_callback(self._on_shout_detected)

        # Brightness detector callbacks
        self.brightness_detector.register_state_callback(self._on_brightness_state_change)
        self.brightness_detector.register_change_callback(self._on_brightness_change)

        # Compass detector callbacks
        self.compass_detector.register_heading_callback(self._on_compass_heading_update)

    def start(self):
        """Start all detection systems"""
        self.logger.info("Starting behavior detection system...")

        # Start sensor handlers
        self.sense_hat.start()
        self.camera.start()
        self.microphone.start()

        # Wait for sensors to initialize
        time.sleep(1)

        # Show startup animation on LED display
        self.led_display.show_startup_animation()

        # Start LED display
        self.led_display.start()

        # Show READY message
        self.led_display.show_ready()

        # Start behavior detectors
        self.movement_detector.start()
        self.fall_detector.start()
        self.turn_detector.start()
        self.compass_detector.start()
        # Shout detector uses microphone callbacks, no separate thread needed
        # Brightness detector uses camera callbacks, no separate thread needed

        # Start event processing thread
        self.running = True
        self.event_thread = threading.Thread(target=self._event_processor, daemon=True)
        self.event_thread.start()

        self.logger.info("Behavior detection system started")

    def stop(self):
        """Stop all detection systems"""
        self.logger.info("Stopping behavior detection system...")

        self.running = False

        # Stop LED display
        self.led_display.stop()

        # Stop behavior detectors
        self.movement_detector.stop()
        self.fall_detector.stop()
        self.turn_detector.stop()
        self.compass_detector.stop()

        # Stop sensor handlers
        self.sense_hat.stop()
        self.camera.stop()
        self.microphone.stop()

        # Stop event thread
        if self.event_thread:
            self.event_thread.join(timeout=2)

        self.logger.info("Behavior detection system stopped")

    def _event_processor(self):
        """Process events and send to API"""
        while self.running:
            try:
                # Get event from queue with timeout
                event = self.event_queue.get(timeout=0.5)
                if event is None:
                    continue

                # Display on Sense HAT
                self._display_behavior(event)

                # Send to API if available
                if self.api_client:
                    self._send_to_api(event)

                # Log event
                self.logger.info(f"Event processed: {event['behavior']} at {event['timestamp']}")

            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Event processor error: {e}")

    def _create_event(self, behavior: str, metadata: Dict = None) -> Dict:
        """
        Create a behavior event

        Args:
            behavior: Behavior type
            metadata: Additional metadata

        Returns:
            Event dictionary
        """
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sensor_id': self.config.get('system', {}).get('device_id', 'rpi_wearable_001'),
            'behavior': behavior,
            'metadata': metadata or {}
        }

        self.stats['events_detected'] += 1
        return event

    def _display_behavior(self, event: Dict):
        """
        Display behavior on Sense HAT LED matrix (handled by LED display callbacks)

        Args:
            event: Event dictionary
        """
        # LED display updates automatically through callbacks
        # This method is kept for logging purposes
        pass

    def _send_to_api(self, event: Dict):
        """
        Send event to API server

        Args:
            event: Event to send
        """
        try:
            if self.api_client:
                success = self.api_client.send_behavior_event(event)
                if success:
                    self.stats['events_sent'] += 1
                else:
                    self.stats['events_failed'] += 1
        except Exception as e:
            self.logger.error(f"API send error: {e}")
            self.stats['events_failed'] += 1

    # Behavior callbacks

    def _on_movement_state_change(self, new_state: MovementState, old_state: MovementState):
        """Handle movement state change"""
        # Update LED display
        self.led_display.update_movement(new_state.value)

        event = self._create_event(
            behavior=new_state.value,
            metadata={
                'previous_state': old_state.value,
                'activity_level': self.movement_detector.get_activity_level(),
                'step_count': self.movement_detector.get_step_count()
            }
        )
        self.event_queue.put(event)
        self.logger.info(f"Movement: {old_state.value} -> {new_state.value}")

    def _on_fall_detected(self, max_acceleration: float, orientation_change: float):
        """Handle fall detection"""
        self.logger.warning(f"🚨 FALL DETECTED! Acceleration: {max_acceleration:.2f}g, Orientation: {orientation_change:.1f}°")

        # Flash fall indicator on LED display
        self.logger.info(f"Flashing fall event on LED (duration: 3.0s)")
        self.led_display.flash_event('fall', duration=3.0)

        event = self._create_event(
            behavior='fall',
            metadata={
                'max_acceleration': max_acceleration,
                'orientation_change': orientation_change,
                'severity': 'high' if max_acceleration > 3.0 else 'moderate'
            }
        )
        self.event_queue.put(event)
        self.logger.warning(f"Fall event queued for API transmission")

    def _on_turn_detected(self, rotation: float, duration: float):
        """Handle turn detection"""
        # Determine direction
        direction = 'left' if rotation < 0 else 'right'

        # Flash turn indicator on LED display with direction
        self.led_display.flash_event('turn', duration=2.0, direction=direction)

        event = self._create_event(
            behavior='turn',
            metadata={
                'rotation_degrees': rotation,
                'duration_seconds': duration,
                'direction': direction
            }
        )
        self.event_queue.put(event)
        self.logger.info(f"Turn around detected: {rotation:.1f}° ({direction}) in {duration:.2f}s")

    def _on_shout_detected(self, volume: float, duration: float):
        """Handle shout detection"""
        # Flash shout indicator on LED display
        self.led_display.flash_event('shout', duration=1.0)

        event = self._create_event(
            behavior='shout',
            metadata={
                'volume_db': volume,
                'duration_seconds': duration,
                'intensity': 'loud' if volume > 80 else 'moderate'
            }
        )
        self.event_queue.put(event)
        self.logger.info(f"Shout detected: {volume:.1f} dB for {duration:.2f}s")

    def _on_brightness_state_change(self, new_state: BrightnessState, old_state: BrightnessState):
        """Handle brightness state change"""
        # Convert brightness state to 0.0-1.0 level for LED display
        brightness_level_map = {
            BrightnessState.DARK: 0.2,    # Dark: 0.0-0.33 range
            BrightnessState.NORMAL: 0.5,  # Normal: 0.33-0.67 range
            BrightnessState.BRIGHT: 0.9   # Bright: 0.67-1.0 range
        }
        level = brightness_level_map.get(new_state, 0.5)

        # Update LED display
        self.led_display.update_brightness(level)

        # Only create events for transitions to dark or bright
        if new_state != BrightnessState.NORMAL:
            event = self._create_event(
                behavior=new_state.value,
                metadata={
                    'previous_state': old_state.value,
                    'brightness_level': self.brightness_detector.get_brightness()
                }
            )
            self.event_queue.put(event)
            self.logger.info(f"Brightness: {old_state.value} -> {new_state.value}")

    def _on_brightness_change(self, brightness: float, change: float):
        """Handle significant brightness change"""
        # Log significant changes but don't create events for every change
        self.logger.debug(f"Brightness change: {brightness:.1f} (change: {change:+.1f})")

    def _on_compass_heading_update(self, heading: float):
        """Handle compass heading update"""
        # Update LED display with current heading
        self.led_display.update_compass(heading)

        # Log heading updates at debug level (continuous updates)
        self.logger.debug(f"Compass heading: {heading:.1f}°")

    # Public methods

    def get_status(self) -> Dict:
        """
        Get overall system status

        Returns:
            Status dictionary
        """
        uptime = time.time() - self.stats['start_time']

        status = {
            'running': self.running,
            'uptime_seconds': uptime,
            'statistics': self.stats,
            'sensors': {
                'sense_hat': self.sense_hat.enabled,
                'camera': self.camera.enabled,
                'microphone': self.microphone.enabled
            },
            'detectors': {
                'movement': self.movement_detector.get_movement_info(),
                'fall': self.fall_detector.get_fall_info(),
                'turn': self.turn_detector.get_turn_info(),
                'shout': self.shout_detector.get_shout_info(),
                'brightness': self.brightness_detector.get_brightness_info()
            },
            'event_queue_size': self.event_queue.qsize()
        }

        return status

    def calibrate_all(self):
        """Calibrate all detectors"""
        self.logger.info("Calibrating all detectors...")

        # Calibrate movement detector
        self.movement_detector.reset_calibration()

        # Calibrate fall detector
        self.fall_detector.recalibrate()

        # Calibrate shout detector
        self.shout_detector.calibrate()

        # Calibrate brightness detector
        self.brightness_detector.calibrate()

        self.logger.info("Calibration complete")

    def _on_joystick_recalibrate(self):
        """
        Handle joystick middle button press
        Recalibrate all gravity-dependent detectors and reset states
        """
        self.logger.info("🔘 Joystick MIDDLE button pressed - Recalibrating all sensors...")

        # Reset and recalibrate movement detector (uses gravity vector)
        self.movement_detector.recalibrate()
        self.logger.info("  ✓ Movement detector recalibrated")

        # Reset and recalibrate turn detector (uses gravity vector)
        self.turn_detector.reset()
        self.turn_detector.recalibrate()
        self.logger.info("  ✓ Turn detector recalibrated and reset")

        # Recalibrate compass detector (magnetometer calibration)
        self.compass_detector.recalibrate()
        self.logger.info("  ✓ Compass detector recalibrated")

        # Fall detector doesn't need recalibration (only uses acceleration magnitude)
        # Shout detector doesn't need recalibration (audio-based)
        # Brightness detector doesn't need recalibration (camera-based)

        # Show calibration complete animation
        # (animation handles pausing/resuming LED display internally)
        self.led_display.show_calibration_complete()

        self.logger.info("✓ Sensor recalibration complete!")

    def reset_all(self):
        """Reset all detectors"""
        self.logger.info("Resetting all detectors...")

        self.movement_detector.reset_calibration()
        self.fall_detector.reset()
        self.turn_detector.reset()
        self.compass_detector.reset()
        self.shout_detector.reset_count()
        self.brightness_detector.reset()

        # Clear event queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except:
                pass

        # Reset statistics
        self.stats['events_detected'] = 0
        self.stats['events_sent'] = 0
        self.stats['events_failed'] = 0

        self.logger.info("Reset complete")

    def test_display(self):
        """Test LED display with all behavior states"""
        if not self.sense_hat.enabled:
            self.logger.warning("Sense HAT not available for display test")
            return

        self.logger.info("Testing LED display...")
        self.led_display.test_display()
        self.logger.info("Display test complete")

    def set_api_client(self, api_client):
        """
        Set or update the API client

        Args:
            api_client: API client instance
        """
        self.api_client = api_client
        self.logger.info("API client updated")