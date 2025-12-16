#!/usr/bin/env python3
"""
Compass Heading Detector
Detects compass heading changes using magnetometer (0-360 degrees)

Author: CAVG Team
Date: 2024
"""

import time
import threading
import logging
import numpy as np
from typing import Dict, Callable, Optional
from collections import deque

from sensors.sense_hat_handler import SenseHatHandler


class CompassDetector:
    """
    Detector for compass heading changes using magnetometer
    Provides continuous heading in degrees (0-360)
    """

    def __init__(self, config: Dict, sense_hat: SenseHatHandler):
        """
        Initialize the compass detector

        Args:
            config: Configuration dictionary
            sense_hat: SenseHat handler instance
        """
        self.config = config
        self.sense_hat = sense_hat
        self.logger = logging.getLogger(__name__)

        # Configuration
        compass_config = config.get('behaviors', {}).get('compass', {})
        self.enabled = compass_config.get('enabled', True)
        self.change_threshold = compass_config.get('change_threshold', 15)  # degrees
        self.update_interval = 0.1  # 10 Hz update rate

        # State tracking
        self.current_heading = 0.0  # degrees (0-360)
        self.last_reported_heading = 0.0
        self.last_trigger_time = 0

        # Data buffers for smoothing
        self.heading_buffer = deque(maxlen=5)  # Short buffer for smoothing

        # Callbacks
        self.heading_callbacks = []

        # Thread control
        self.running = False
        self.detection_thread = None

        self.logger.info("Compass detector initialized (continuous heading mode)")

    def start(self):
        """Start the compass detection thread"""
        if not self.enabled:
            self.logger.warning("Compass detector is disabled")
            return

        if not self.running:
            self.running = True
            self.detection_thread = threading.Thread(target=self._detection_worker)
            self.detection_thread.daemon = True
            self.detection_thread.start()
            self.logger.info("Compass detection started")

    def stop(self):
        """Stop the compass detection thread"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        self.logger.info("Compass detection stopped")

    def _detection_worker(self):
        """Worker thread for continuous compass detection"""
        while self.running:
            try:
                start_time = time.time()

                # Get compass heading directly from Sense HAT
                heading = self.sense_hat.get_compass()

                if heading is not None:
                    # Add to buffer for smoothing
                    self.heading_buffer.append(heading)

                    # Calculate smoothed heading
                    if len(self.heading_buffer) > 0:
                        self.current_heading = self._smooth_heading(list(self.heading_buffer))

                    # Check for significant heading change
                    self._detect_heading_change(self.current_heading)

                    # Always call heading callbacks for continuous updates
                    for callback in self.heading_callbacks:
                        try:
                            callback(self.current_heading)
                        except Exception as e:
                            self.logger.error(f"Heading callback error: {e}")

                # Maintain update rate
                elapsed = time.time() - start_time
                if elapsed < self.update_interval:
                    time.sleep(self.update_interval - elapsed)

            except Exception as e:
                self.logger.error(f"Compass detection error: {e}")
                time.sleep(0.1)

    def _smooth_heading(self, headings):
        """
        Smooth heading values accounting for 0/360 wrap-around

        Args:
            headings: List of heading values

        Returns:
            Smoothed heading
        """
        if not headings:
            return 0.0

        # Convert to unit vectors to handle wrap-around
        x_sum = sum(np.cos(np.radians(h)) for h in headings)
        y_sum = sum(np.sin(np.radians(h)) for h in headings)

        # Calculate average angle
        avg_angle = np.degrees(np.arctan2(y_sum, x_sum))

        # Normalize to 0-360
        if avg_angle < 0:
            avg_angle += 360

        return avg_angle

    def _detect_heading_change(self, heading: float):
        """
        Detect significant heading changes

        Args:
            heading: Current heading in degrees
        """
        # Calculate angular difference (shortest path)
        diff = abs(heading - self.last_reported_heading)
        if diff > 180:
            diff = 360 - diff

        # Check if change is significant
        if diff >= self.change_threshold:
            self.last_reported_heading = heading
            self.last_trigger_time = time.time()

            self.logger.debug(f"Significant heading change: {heading:.1f}° (change: {diff:.1f}°)")

    def register_heading_callback(self, callback: Callable):
        """
        Register callback for continuous heading updates

        Args:
            callback: Function(heading: float) - heading in degrees (0-360)
        """
        if callback not in self.heading_callbacks:
            self.heading_callbacks.append(callback)
            self.logger.info("Heading callback registered")

    def get_current_heading(self) -> float:
        """
        Get current compass heading

        Returns:
            Heading in degrees (0-360)
        """
        return self.current_heading

    def get_compass_info(self) -> Dict:
        """
        Get comprehensive compass information

        Returns:
            Dictionary with compass status
        """
        return {
            'running': self.running,
            'current_heading': self.current_heading,
            'buffer_size': len(self.heading_buffer)
        }

    def recalibrate(self):
        """Recalibrate compass (placeholder for future implementation)"""
        self.logger.info("Compass recalibration requested")
        # Clear buffer to reset smoothing
        self.heading_buffer.clear()
        self.logger.info("Compass recalibrated (buffer cleared)")

    def reset(self):
        """Reset compass detector state"""
        self.current_heading = 0.0
        self.last_reported_heading = 0.0
        self.last_trigger_time = 0
        self.heading_buffer.clear()
        self.logger.info("Compass detector reset")

    def set_change_threshold(self, threshold: float):
        """
        Set heading change threshold

        Args:
            threshold: Threshold in degrees
        """
        self.change_threshold = threshold
        self.logger.info(f"Change threshold set to {threshold}°")
