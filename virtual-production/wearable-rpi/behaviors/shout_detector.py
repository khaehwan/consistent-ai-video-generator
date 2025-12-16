"""
Shout Detection Module
Detects shouting behavior using microphone audio data
"""

import logging
import threading
import time
from typing import Dict, Optional, Callable, List


class ShoutDetector:
    """
    Detects shouting using microphone handler
    """

    def __init__(self, config: Dict, microphone_handler):
        """
        Initialize the shout detector

        Args:
            config: Configuration dictionary
            microphone_handler: Reference to MicrophoneHandler instance
        """
        self.config = config
        self.microphone = microphone_handler
        self.logger = logging.getLogger(__name__)

        # Detection parameters
        self.enabled = config.get('behaviors', {}).get('shout', {}).get('enabled', True)
        self.volume_threshold = config.get('behaviors', {}).get('shout', {}).get('volume_threshold', 70)
        self.duration_min = config.get('behaviors', {}).get('shout', {}).get('duration_min', 500) / 1000.0
        self.cooldown = config.get('behaviors', {}).get('shout', {}).get('cooldown', 2)

        # State tracking
        self.is_shouting = False
        self.shout_start_time = None
        self.last_shout_time = 0
        self.shout_count = 0
        self.max_volume = 0

        # Callbacks
        self.shout_callbacks = []

        # Register with microphone handler
        if self.microphone and self.microphone.enabled:
            self.microphone.register_shout_callback(self._on_microphone_shout)

        self.logger.info("Shout detector initialized")

    def _on_microphone_shout(self, volume: float, duration: float):
        """
        Callback from microphone handler when shout is detected

        Args:
            volume: Volume level in dB
            duration: Duration of shout in seconds
        """
        current_time = time.time()

        # Check cooldown
        if current_time - self.last_shout_time < self.cooldown:
            self.logger.debug(f"Shout ignored due to cooldown ({self.cooldown}s)")
            return

        # Record shout
        self.is_shouting = True
        self.shout_start_time = current_time
        self.last_shout_time = current_time
        self.shout_count += 1
        self.max_volume = volume

        self.logger.info(f"SHOUT DETECTED! Volume: {volume:.1f} dB, Duration: {duration:.2f}s, "
                        f"Count: {self.shout_count}")

        # Trigger callbacks
        for callback in self.shout_callbacks:
            try:
                callback(volume, duration)
            except Exception as e:
                self.logger.error(f"Shout callback error: {e}")

        # Reset shouting state after brief delay
        threading.Timer(0.5, self._reset_shouting).start()

    def _reset_shouting(self):
        """Reset shouting state"""
        self.is_shouting = False
        self.max_volume = 0

    def is_currently_shouting(self) -> bool:
        """
        Check if currently shouting

        Returns:
            True if shouting
        """
        return self.is_shouting

    def get_shout_count(self) -> int:
        """
        Get total number of shouts detected

        Returns:
            Shout count
        """
        return self.shout_count

    def get_time_since_last_shout(self) -> float:
        """
        Get time since last shout

        Returns:
            Time in seconds, or -1 if no shouts detected
        """
        if self.last_shout_time > 0:
            return time.time() - self.last_shout_time
        return -1

    def register_shout_callback(self, callback: Callable[[float, float], None]):
        """
        Register a callback for shout detection events

        Args:
            callback: Function to call with (volume, duration) parameters
        """
        self.shout_callbacks.append(callback)
        self.logger.debug(f"Registered shout callback: {callback.__name__}")

    def get_shout_info(self) -> Dict:
        """
        Get shout detection information

        Returns:
            Dictionary with shout detection info
        """
        info = {
            'enabled': self.enabled and self.microphone.enabled,
            'is_shouting': self.is_shouting,
            'shout_count': self.shout_count,
            'volume_threshold': self.volume_threshold,
            'max_volume': self.max_volume
        }

        if self.microphone and self.microphone.enabled:
            info['current_volume'] = self.microphone.get_volume()
            info['is_loud'] = self.microphone.is_loud()

        if self.last_shout_time > 0:
            info['time_since_last_shout'] = self.get_time_since_last_shout()
            info['cooldown_remaining'] = max(0, self.cooldown - self.get_time_since_last_shout())

        return info

    def set_threshold(self, volume_threshold: float):
        """
        Adjust volume threshold for shout detection

        Args:
            volume_threshold: New threshold in dB
        """
        self.volume_threshold = volume_threshold
        if self.microphone:
            self.microphone.shout_threshold = volume_threshold
        self.logger.info(f"Shout threshold set to {volume_threshold} dB")

    def reset_count(self):
        """Reset shout counter"""
        self.shout_count = 0
        self.logger.info("Shout counter reset")

    def calibrate(self, duration: float = 3.0):
        """
        Calibrate shout detection based on ambient noise

        Args:
            duration: Calibration duration in seconds
        """
        if self.microphone and self.microphone.enabled:
            noise_floor = self.microphone.calibrate_noise_floor(duration)
            # Shout threshold is automatically adjusted in microphone handler
            self.volume_threshold = self.microphone.shout_threshold
            self.logger.info(f"Shout detector calibrated. New threshold: {self.volume_threshold} dB")