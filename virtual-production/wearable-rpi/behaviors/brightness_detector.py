"""
Brightness Detection Module
Detects brightness changes (dark/bright) using camera data
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, Optional, Callable, List, Tuple
from enum import Enum


class BrightnessState(Enum):
    """Brightness states"""
    NORMAL = "normal"
    DARK = "dark"
    BRIGHT = "bright"


class BrightnessDetector:
    """
    Detects brightness changes using camera handler
    """

    def __init__(self, config: Dict, camera_handler):
        """
        Initialize the brightness detector

        Args:
            config: Configuration dictionary
            camera_handler: Reference to CameraHandler instance
        """
        self.config = config
        self.camera = camera_handler
        self.logger = logging.getLogger(__name__)

        # Detection parameters
        self.enabled = config.get('behaviors', {}).get('brightness', {}).get('enabled', True)
        self.dark_threshold = config.get('behaviors', {}).get('brightness', {}).get('dark_threshold', 50)
        self.bright_threshold = config.get('behaviors', {}).get('brightness', {}).get('bright_threshold', 200)
        self.change_rate = config.get('behaviors', {}).get('brightness', {}).get('change_rate', 30)
        self.sample_window = config.get('behaviors', {}).get('brightness', {}).get('sample_window', 5)
        self.cooldown = config.get('behaviors', {}).get('brightness', {}).get('cooldown', 5)

        # State tracking
        self.current_state = BrightnessState.NORMAL
        self.previous_state = BrightnessState.NORMAL
        self.state_change_time = time.time()
        self.last_trigger_time = 0

        # Brightness tracking
        self.current_brightness = 128
        self.baseline_brightness = 128
        self.max_brightness = 0
        self.min_brightness = 255

        # Callbacks
        self.state_callbacks = []
        self.change_callbacks = []

        # Register with camera handler
        if self.camera and self.camera.enabled:
            self.camera.register_brightness_callback(self._on_brightness_change)

        self.logger.info("Brightness detector initialized")

    def _on_brightness_change(self, brightness: float, change: float):
        """
        Callback from camera handler when brightness changes

        Args:
            brightness: Current brightness level (0-255)
            change: Brightness change amount
        """
        self.current_brightness = brightness

        # Update min/max
        self.min_brightness = min(self.min_brightness, brightness)
        self.max_brightness = max(self.max_brightness, brightness)

        # Check for significant change
        if abs(change) >= self.change_rate:
            self._handle_brightness_change(brightness, change)

        # Check for state transitions
        self._check_state_transition(brightness)

    def _handle_brightness_change(self, brightness: float, change: float):
        """
        Handle significant brightness change

        Args:
            brightness: Current brightness
            change: Amount of change
        """
        current_time = time.time()

        # Check cooldown
        if current_time - self.last_trigger_time < self.cooldown:
            return

        self.logger.info(f"Brightness change detected: {brightness:.1f} (change: {change:+.1f})")

        # Trigger change callbacks
        for callback in self.change_callbacks:
            try:
                callback(brightness, change)
            except Exception as e:
                self.logger.error(f"Brightness change callback error: {e}")

        self.last_trigger_time = current_time

    def _check_state_transition(self, brightness: float):
        """
        Check for state transitions based on brightness level

        Args:
            brightness: Current brightness level
        """
        new_state = self._determine_state(brightness)

        if new_state != self.current_state:
            self._handle_state_change(new_state)

    def _determine_state(self, brightness: float) -> BrightnessState:
        """
        Determine brightness state based on thresholds

        Args:
            brightness: Current brightness level

        Returns:
            Brightness state
        """
        if brightness < self.dark_threshold:
            return BrightnessState.DARK
        elif brightness > self.bright_threshold:
            return BrightnessState.BRIGHT
        else:
            return BrightnessState.NORMAL

    def _handle_state_change(self, new_state: BrightnessState):
        """
        Handle brightness state change

        Args:
            new_state: New brightness state
        """
        current_time = time.time()

        # Check cooldown for state changes
        if current_time - self.state_change_time < 2:  # Minimum 2 seconds between state changes
            return

        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_change_time = current_time

        self.logger.info(f"Brightness state changed: {self.previous_state.value} -> {new_state.value}")

        # Trigger state callbacks
        for callback in self.state_callbacks:
            try:
                callback(new_state, self.previous_state)
            except Exception as e:
                self.logger.error(f"State callback error: {e}")

    def get_current_state(self) -> BrightnessState:
        """
        Get current brightness state

        Returns:
            Current brightness state
        """
        return self.current_state

    def get_brightness(self) -> float:
        """
        Get current brightness level

        Returns:
            Brightness level (0-255)
        """
        if self.camera and self.camera.enabled:
            return self.camera.get_brightness()
        return self.current_brightness

    def is_dark(self) -> bool:
        """
        Check if currently dark

        Returns:
            True if dark
        """
        return self.current_state == BrightnessState.DARK

    def is_bright(self) -> bool:
        """
        Check if currently bright

        Returns:
            True if bright
        """
        return self.current_state == BrightnessState.BRIGHT

    def get_brightness_range(self) -> Tuple[float, float]:
        """
        Get brightness range observed

        Returns:
            Tuple of (min_brightness, max_brightness)
        """
        return (self.min_brightness, self.max_brightness)

    def register_state_callback(self, callback: Callable[[BrightnessState, BrightnessState], None]):
        """
        Register a callback for state change events

        Args:
            callback: Function to call with (new_state, old_state) parameters
        """
        self.state_callbacks.append(callback)
        self.logger.debug(f"Registered brightness state callback: {callback.__name__}")

    def register_change_callback(self, callback: Callable[[float, float], None]):
        """
        Register a callback for brightness change events

        Args:
            callback: Function to call with (brightness, change) parameters
        """
        self.change_callbacks.append(callback)
        self.logger.debug(f"Registered brightness change callback: {callback.__name__}")

    def get_brightness_info(self) -> Dict:
        """
        Get brightness detection information

        Returns:
            Dictionary with brightness info
        """
        info = {
            'enabled': self.enabled and self.camera.enabled,
            'current_state': self.current_state.value,
            'previous_state': self.previous_state.value,
            'current_brightness': self.get_brightness(),
            'is_dark': self.is_dark(),
            'is_bright': self.is_bright(),
            'min_brightness': self.min_brightness,
            'max_brightness': self.max_brightness,
            'dark_threshold': self.dark_threshold,
            'bright_threshold': self.bright_threshold
        }

        if self.camera and self.camera.enabled:
            brightness_history = self.camera.get_brightness_history()
            if brightness_history:
                info['avg_brightness'] = np.mean(brightness_history)
                info['brightness_std'] = np.std(brightness_history)

        if self.state_change_time:
            info['state_duration'] = time.time() - self.state_change_time

        if self.last_trigger_time > 0:
            info['time_since_last_change'] = time.time() - self.last_trigger_time
            info['cooldown_remaining'] = max(0, self.cooldown - (time.time() - self.last_trigger_time))

        return info

    def set_thresholds(self, dark: Optional[float] = None, bright: Optional[float] = None):
        """
        Adjust brightness thresholds

        Args:
            dark: Dark threshold (0-255)
            bright: Bright threshold (0-255)
        """
        if dark is not None:
            self.dark_threshold = dark
        if bright is not None:
            self.bright_threshold = bright

        self.logger.info(f"Brightness thresholds updated - Dark: {self.dark_threshold}, "
                        f"Bright: {self.bright_threshold}")

    def calibrate(self):
        """Calibrate brightness detection based on current conditions"""
        if not self.camera or not self.camera.enabled:
            self.logger.warning("Cannot calibrate - camera not available")
            return

        # Get current brightness as baseline
        self.baseline_brightness = self.camera.get_brightness()

        # Set thresholds relative to baseline
        self.dark_threshold = max(10, self.baseline_brightness - 50)
        self.bright_threshold = min(245, self.baseline_brightness + 50)

        self.logger.info(f"Brightness calibrated. Baseline: {self.baseline_brightness:.1f}, "
                        f"Dark threshold: {self.dark_threshold}, Bright threshold: {self.bright_threshold}")

    def enable_night_mode(self, enabled: bool = True):
        """
        Enable or disable night mode on camera

        Args:
            enabled: True to enable night mode
        """
        if self.camera and self.camera.enabled:
            self.camera.enable_night_mode(enabled)
            self.logger.info(f"Night mode {'enabled' if enabled else 'disabled'}")

    def reset(self):
        """Reset brightness detection state"""
        self.current_state = BrightnessState.NORMAL
        self.previous_state = BrightnessState.NORMAL
        self.min_brightness = 255
        self.max_brightness = 0
        self.last_trigger_time = 0
        self.logger.info("Brightness detector reset")