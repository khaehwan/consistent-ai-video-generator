"""
WebSocket Client Module for Kinect Virtual Production
Handles real-time communication with VP server
"""

import logging
import json
import time
import threading
from typing import Dict, Optional
from datetime import datetime
import websocket


class KinectWebSocketClient:
    """
    WebSocket client for real-time communication with Virtual Production server
    """

    def __init__(self, config: Dict):
        """
        Initialize WebSocket client

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # WebSocket configuration
        api_config = config.get('api_server', {})
        host = api_config.get('host', 'localhost')
        ws_port = api_config.get('ws_port', 8001)
        self.ws_url = f"ws://{host}:{ws_port}/vp/sensor-events"

        # Device identification
        kinect_config = config.get('kinect', {})
        self.sensor_id = kinect_config.get('sensor_id', 'kinect_001')

        # WebSocket settings
        ws_settings = config.get('websocket', {})
        self.reconnect_delay = ws_settings.get('reconnect_delay', 5.0)
        self.ping_interval = ws_settings.get('ping_interval', 30.0)

        # Connection state
        self.ws = None
        self.connected = False

        # Statistics
        self.stats = {
            'events_sent': 0,
            'events_failed': 0,
            'last_success': None,
            'last_error': None,
            'reconnects': 0
        }

        # Threads
        self.ws_thread = None
        self.should_run = True

        self.logger.info(f"WebSocket client initialized for {self.ws_url}")

    def connect(self):
        """Connect to WebSocket server"""
        if self.ws_thread and self.ws_thread.is_alive():
            self.logger.warning("WebSocket thread already running")
            return

        self.should_run = True
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        self.logger.info("WebSocket thread started")

    def _run_websocket(self):
        """Main WebSocket run loop with auto-reconnect"""
        while self.should_run:
            try:
                self.logger.info(f"Connecting to {self.ws_url}...")

                # Create WebSocket connection
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )

                # Run WebSocket (blocking)
                self.ws.run_forever(ping_interval=self.ping_interval)

            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                self.stats['last_error'] = str(e)

            # Reconnect delay
            if self.should_run:
                self.logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                self.stats['reconnects'] += 1
                time.sleep(self.reconnect_delay)

    def _on_open(self, ws):
        """WebSocket connection opened"""
        self.connected = True
        self.logger.info("✅ WebSocket connected")

    def _on_message(self, ws, message):
        """
        WebSocket message received

        Args:
            ws: WebSocket instance
            message: Received message
        """
        try:
            data = json.loads(message)
            self.logger.debug(f"Received: {data}")

            # Handle different message types if needed
            msg_type = data.get('type')
            if msg_type == 'action_change':
                self.logger.info(f"Background changed to {data.get('new_background')}")
            elif msg_type == 'scene_change':
                self.logger.info(f"Scene changed to {data.get('scene_id')}")

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def _on_error(self, ws, error):
        """
        WebSocket error occurred

        Args:
            ws: WebSocket instance
            error: Error object
        """
        self.logger.error(f"WebSocket error: {error}")
        self.stats['last_error'] = str(error)
        self.connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket connection closed

        Args:
            ws: WebSocket instance
            close_status_code: Close status code
            close_msg: Close message
        """
        self.logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.connected = False

    def send_posture_event(self, posture: str, metadata: Optional[Dict] = None) -> bool:
        """
        Send posture event to server

        Args:
            posture: Posture type (standing, sitting, lying, left_arm_up, right_arm_up)
            metadata: Optional metadata dictionary

        Returns:
            True if successful
        """
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sensor_id': self.sensor_id,
            'behavior': posture,  # API expects 'behavior' field
            'metadata': metadata or {}
        }

        return self._send_event(event)

    def _send_event(self, event: Dict) -> bool:
        """
        Internal method to send event via WebSocket

        Args:
            event: Event dictionary

        Returns:
            True if successful
        """
        if not self.connected or not self.ws:
            self.logger.warning(f"WebSocket not connected, cannot send event")
            self.stats['events_failed'] += 1
            return False

        try:
            # Send via WebSocket
            message = json.dumps(event)
            self.logger.info(f"📤 Sending posture event: {event['behavior']}")
            self.ws.send(message)

            self.stats['events_sent'] += 1
            self.stats['last_success'] = datetime.utcnow().isoformat()
            self.logger.info(f"✅ Event sent successfully: {event['behavior']} (total: {self.stats['events_sent']})")

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to send event: {e}")
            self.stats['events_failed'] += 1
            self.stats['last_error'] = str(e)
            return False

    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected

        Returns:
            True if connected
        """
        return self.connected

    def get_statistics(self) -> Dict:
        """
        Get WebSocket client statistics

        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()
        stats['connected'] = self.connected
        return stats

    def close(self):
        """Close WebSocket connection"""
        self.should_run = False

        if self.ws:
            self.ws.close()

        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)

        self.logger.info("WebSocket client closed")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    config = {
        'api_server': {
            'host': 'localhost',
            'ws_port': 8001
        },
        'kinect': {
            'sensor_id': 'kinect_test_001'
        },
        'websocket': {
            'reconnect_delay': 5.0,
            'ping_interval': 30.0
        }
    }

    client = KinectWebSocketClient(config)
    client.connect()

    # Wait for connection
    time.sleep(2)

    # Send test events
    postures = ['standing', 'sitting', 'lying', 'left_arm_up', 'right_arm_up']
    for posture in postures:
        client.send_posture_event(posture, metadata={'test': True})
        time.sleep(2)

    # Check stats
    print(f"Statistics: {client.get_statistics()}")

    # Close
    client.close()
