"""
WebSocket Client Module for Virtual Production
Handles real-time communication with VP server
"""

import logging
import json
import time
import threading
from typing import Dict, Optional, Callable
from datetime import datetime
import websocket


class VPWebSocketClient:
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
        ws_config = config.get('api', {}).get('websocket', {})
        ws_url = ws_config.get('url', 'ws://localhost:8001/vp/sensor-events')
        self.ws_url = ws_url

        # Device identification
        self.device_id = config.get('system', {}).get('device_id', 'rpi_wearable_001')
        self.location = config.get('system', {}).get('location', 'unspecified')

        # Connection state
        self.ws = None
        self.connected = False
        self.reconnect_delay = ws_config.get('reconnect_delay', 5)
        self.ping_interval = ws_config.get('ping_interval', 30)

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
        self.logger.info("WebSocket connected")

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

    def send_behavior_event(self, event: Dict) -> bool:
        """
        Send behavior event to server

        Args:
            event: Event dictionary with keys:
                - behavior: str (stop, walk, run, fall, etc.)
                - timestamp: str (ISO format)
                - metadata: dict (optional)

        Returns:
            True if successful
        """
        if not self.connected or not self.ws:
            self.logger.warning(f"WebSocket not connected, cannot send event (connected={self.connected}, ws={self.ws is not None})")
            self.stats['events_failed'] += 1
            return False

        try:
            # Add device info
            event['sensor_id'] = self.device_id
            event['location'] = self.location

            # Ensure timestamp
            if 'timestamp' not in event:
                event['timestamp'] = datetime.utcnow().isoformat() + 'Z'

            # Send via WebSocket
            message = json.dumps(event)
            self.logger.info(f"Sending event to VP server: {event['behavior']}")
            self.ws.send(message)

            self.stats['events_sent'] += 1
            self.stats['last_success'] = datetime.utcnow().isoformat()
            self.logger.info(f"Event sent successfully: {event['behavior']} (total sent: {self.stats['events_sent']})")

            return True

        except Exception as e:
            self.logger.error(f"Failed to send event: {e}")
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
        'api': {
            'websocket': {
                'url': 'ws://localhost:8001/vp/sensor-events',
                'reconnect_delay': 5,
                'ping_interval': 30
            }
        },
        'system': {
            'device_id': 'rpi_wearable_test',
            'location': 'test_location'
        }
    }

    client = VPWebSocketClient(config)
    client.connect()

    # Wait for connection
    time.sleep(2)

    # Send test events
    for i in range(5):
        event = {
            'behavior': 'walk' if i % 2 == 0 else 'stop',
            'metadata': {'test': i}
        }
        client.send_behavior_event(event)
        time.sleep(2)

    # Check stats
    print(f"Statistics: {client.get_statistics()}")

    # Close
    client.close()
