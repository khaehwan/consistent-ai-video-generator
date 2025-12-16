"""
API Client Module
Handles communication with the virtual production server
"""

import logging
import requests
import json
import time
import threading
from typing import Dict, Optional, List, Tuple
from queue import Queue, Empty
from datetime import datetime
import os


class APIClient:
    """
    Client for communicating with virtual production API server
    """

    def __init__(self, config: Dict):
        """
        Initialize the API client

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # API configuration
        self.base_url = config.get('api', {}).get('base_url', 'http://localhost:8000')
        self.endpoints = config.get('api', {}).get('endpoints', {})
        self.timeout = config.get('api', {}).get('timeout', 5)
        self.retry_attempts = config.get('api', {}).get('retry_attempts', 3)
        self.retry_delay = config.get('api', {}).get('retry_delay', 1)

        # Authentication
        auth_config = config.get('api', {}).get('auth', {})
        self.auth_enabled = auth_config.get('enabled', False)
        self.auth_token = auth_config.get('token', '')

        # Device identification
        self.device_id = config.get('system', {}).get('device_id', 'rpi_wearable_001')
        self.location = config.get('system', {}).get('location', 'unspecified')

        # Offline storage
        self.offline_storage = config.get('system', {}).get('offline_storage', True)
        self.offline_path = config.get('system', {}).get('offline_storage_path', 'data/offline_events.json')
        self.offline_queue = Queue()

        # Connection state
        self.connected = False
        self.last_heartbeat = 0
        self.heartbeat_interval = config.get('system', {}).get('heartbeat_interval', 30)

        # Statistics
        self.stats = {
            'events_sent': 0,
            'events_failed': 0,
            'events_offline': 0,
            'last_success': None,
            'last_error': None
        }

        # Session
        self.session = requests.Session()
        if self.auth_enabled and self.auth_token:
            self.session.headers.update({'Authorization': f'Bearer {self.auth_token}'})

        # Start heartbeat thread if configured
        self.heartbeat_thread = None
        if self.heartbeat_interval > 0:
            self._start_heartbeat()

        # Load offline events if any
        self._load_offline_events()

        self.logger.info(f"API client initialized for {self.base_url}")

    def _start_heartbeat(self):
        """Start heartbeat thread"""
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("Heartbeat thread started")

    def _heartbeat_worker(self):
        """Send periodic heartbeat to server"""
        while True:
            try:
                time.sleep(self.heartbeat_interval)
                self.send_heartbeat()
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL for endpoint

        Args:
            endpoint: Endpoint path

        Returns:
            Full URL
        """
        if endpoint.startswith('http'):
            return endpoint

        # Get endpoint from config or use as-is
        path = self.endpoints.get(endpoint, endpoint)

        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path

        return self.base_url + path

    def _make_request(self, method: str, endpoint: str, data: Dict = None,
                     params: Dict = None) -> Tuple[bool, Optional[Dict]]:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters

        Returns:
            Tuple of (success, response_data)
        """
        url = self._build_url(endpoint)
        attempts = 0

        while attempts < self.retry_attempts:
            attempts += 1

            try:
                # Make request
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )

                # Check status
                if response.status_code == 200:
                    self.connected = True
                    self.stats['last_success'] = datetime.utcnow().isoformat()

                    try:
                        return True, response.json()
                    except:
                        return True, {'status': 'success'}

                else:
                    self.logger.warning(f"API request failed: {response.status_code} - {response.text}")
                    self.stats['last_error'] = f"HTTP {response.status_code}"

            except requests.exceptions.Timeout:
                self.logger.warning(f"API request timeout (attempt {attempts}/{self.retry_attempts})")
                self.stats['last_error'] = "Timeout"

            except requests.exceptions.ConnectionError:
                self.logger.warning(f"API connection error (attempt {attempts}/{self.retry_attempts})")
                self.connected = False
                self.stats['last_error'] = "Connection error"

            except Exception as e:
                self.logger.error(f"API request error: {e}")
                self.stats['last_error'] = str(e)

            # Retry delay
            if attempts < self.retry_attempts:
                time.sleep(self.retry_delay)

        # All attempts failed
        self.connected = False
        return False, None

    def send_behavior_event(self, event: Dict) -> bool:
        """
        Send behavior event to server

        Args:
            event: Event dictionary

        Returns:
            True if successful
        """
        # Add device info to event
        event['sensor_id'] = self.device_id
        event['location'] = self.location

        # Try to send
        success, response = self._make_request('POST', 'behavior', data=event)

        if success:
            self.stats['events_sent'] += 1
            self.logger.debug(f"Event sent: {event['behavior']}")

            # Process any offline events if connection restored
            if self.offline_queue.qsize() > 0:
                self._process_offline_queue()

        else:
            self.stats['events_failed'] += 1

            # Store offline if configured
            if self.offline_storage:
                self._store_offline_event(event)

        return success

    def send_heartbeat(self) -> bool:
        """
        Send heartbeat to server

        Returns:
            True if successful
        """
        heartbeat_data = {
            'sensor_id': self.device_id,
            'location': self.location,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status': 'active',
            'uptime': time.time() - self.last_heartbeat if self.last_heartbeat else 0
        }

        success, response = self._make_request('POST', 'heartbeat', data=heartbeat_data)

        if success:
            self.last_heartbeat = time.time()
            self.logger.debug("Heartbeat sent successfully")
        else:
            self.logger.warning("Heartbeat failed")

        return success

    def get_status(self) -> Tuple[bool, Optional[Dict]]:
        """
        Get server status

        Returns:
            Tuple of (success, status_data)
        """
        return self._make_request('GET', 'status')

    def _store_offline_event(self, event: Dict):
        """
        Store event for offline processing

        Args:
            event: Event to store
        """
        try:
            # Add to queue
            self.offline_queue.put(event)
            self.stats['events_offline'] += 1

            # Persist to file
            self._save_offline_events()

            self.logger.info(f"Event stored offline: {event['behavior']} "
                           f"(queue size: {self.offline_queue.qsize()})")

        except Exception as e:
            self.logger.error(f"Failed to store offline event: {e}")

    def _save_offline_events(self):
        """Save offline events to file"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.offline_path), exist_ok=True)

            # Convert queue to list
            events = []
            temp_queue = Queue()

            while not self.offline_queue.empty():
                try:
                    event = self.offline_queue.get_nowait()
                    events.append(event)
                    temp_queue.put(event)
                except Empty:
                    break

            # Restore queue
            self.offline_queue = temp_queue

            # Save to file
            with open(self.offline_path, 'w') as f:
                json.dump(events, f, indent=2)

            self.logger.debug(f"Saved {len(events)} offline events")

        except Exception as e:
            self.logger.error(f"Failed to save offline events: {e}")

    def _load_offline_events(self):
        """Load offline events from file"""
        if not os.path.exists(self.offline_path):
            return

        try:
            with open(self.offline_path, 'r') as f:
                events = json.load(f)

            for event in events:
                self.offline_queue.put(event)

            self.logger.info(f"Loaded {len(events)} offline events")

            # Clear the file
            os.remove(self.offline_path)

        except Exception as e:
            self.logger.error(f"Failed to load offline events: {e}")

    def _process_offline_queue(self):
        """Process offline events when connection is restored"""
        if self.offline_queue.empty():
            return

        self.logger.info(f"Processing {self.offline_queue.qsize()} offline events...")

        processed = 0
        failed = 0

        while not self.offline_queue.empty():
            try:
                event = self.offline_queue.get_nowait()

                # Try to send
                success, _ = self._make_request('POST', 'behavior', data=event)

                if success:
                    processed += 1
                else:
                    # Put back in queue if failed
                    self.offline_queue.put(event)
                    failed += 1
                    break  # Stop processing if connection lost again

            except Empty:
                break

        self.logger.info(f"Processed {processed} offline events, {failed} failed")

        # Save remaining events
        if not self.offline_queue.empty():
            self._save_offline_events()

    def is_connected(self) -> bool:
        """
        Check if connected to server

        Returns:
            True if connected
        """
        return self.connected

    def get_statistics(self) -> Dict:
        """
        Get API client statistics

        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()
        stats['connected'] = self.connected
        stats['offline_queue_size'] = self.offline_queue.qsize()

        if self.last_heartbeat > 0:
            stats['last_heartbeat'] = time.time() - self.last_heartbeat

        return stats

    def test_connection(self) -> bool:
        """
        Test connection to server

        Returns:
            True if successful
        """
        self.logger.info(f"Testing connection to {self.base_url}...")

        success, response = self._make_request('GET', 'status')

        if success:
            self.logger.info("Connection test successful")
            if response:
                self.logger.info(f"Server response: {response}")
        else:
            self.logger.error("Connection test failed")

        return success

    def close(self):
        """Close API client and cleanup"""
        # Save any offline events
        if not self.offline_queue.empty():
            self._save_offline_events()

        # Close session
        self.session.close()

        self.logger.info("API client closed")