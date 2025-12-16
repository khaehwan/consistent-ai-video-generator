"""
Movement Detection Module
Detects stop, walk, and run behaviors using IMU data
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, Optional, Callable, List, Tuple
from collections import deque
from enum import Enum


class MovementState(Enum):
    """Movement states"""
    STOP = "stop"
    WALK = "walk"
    RUN = "run"


class MovementDetector:
    """
    Detects movement patterns (stop, walk, run) using accelerometer data
    """

    def __init__(self, config: Dict, sense_hat_handler):
        """
        Initialize the movement detector

        Args:
            config: Configuration dictionary
            sense_hat_handler: Reference to SenseHatHandler instance
        """
        self.config = config
        self.sense_hat = sense_hat_handler
        self.logger = logging.getLogger(__name__)

        # Detection parameters
        self.enabled = config.get('behaviors', {}).get('movement', {}).get('enabled', True)
        self.sample_window = config.get('behaviors', {}).get('movement', {}).get('sample_window', 10)
        self.threshold_static = config.get('behaviors', {}).get('movement', {}).get('threshold_static', 0.1)
        self.threshold_walking = config.get('behaviors', {}).get('movement', {}).get('threshold_walking', 0.5)
        self.threshold_running = config.get('behaviors', {}).get('movement', {}).get('threshold_running', 1.5)
        self.cooldown = config.get('behaviors', {}).get('movement', {}).get('cooldown', 2)

        # State tracking
        self.current_state = MovementState.STOP
        self.previous_state = MovementState.STOP
        self.state_change_time = time.time()
        self.last_trigger_time = 0

        # Data buffers
        self.accel_buffer = deque(maxlen=self.sample_window)
        self.magnitude_buffer = deque(maxlen=self.sample_window)

        # Calibration data
        self.gravity_vector = np.array([0.0, 0.0, 1.0])
        self.calibrated = False

        # Callbacks
        self.state_callbacks = []

        # Thread control
        self.running = False
        self.detection_thread = None

        self.logger.info("Movement detector initialized")

    def start(self):
        """Start the movement detection thread"""
        if not self.enabled or not self.sense_hat.enabled:
            self.logger.warning("Movement detection disabled or Sense HAT not available")
            return

        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()

        # Calibrate gravity vector
        threading.Thread(target=self._calibrate, daemon=True).start()

        self.logger.info("Movement detection started")

    def stop(self):
        """Stop the movement detection thread"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        self.logger.info("Movement detection stopped")

    def _detection_worker(self):
        """Worker thread for continuous movement detection"""
        sample_rate = 30  # Hz
        sample_interval = 1.0 / sample_rate

        while self.running:
            try:
                start_time = time.time()

                # Get accelerometer data
                accel_data = self.sense_hat.get_accelerometer()

                if accel_data:
                    # Process acceleration data
                    self._process_acceleration(accel_data)

                    # Detect movement state
                    new_state = self._detect_movement_state()

                    # Handle state changes
                    if new_state != self.current_state:
                        self._handle_state_change(new_state)

                # Maintain sample rate
                elapsed = time.time() - start_time
                if elapsed < sample_interval:
                    time.sleep(sample_interval - elapsed)

            except Exception as e:
                self.logger.error(f"Movement detection error: {e}")
                time.sleep(0.1)

    def _calibrate(self):
        """Calibrate the gravity vector"""
        self.logger.info("Calibrating movement detector...")

        # Collect samples while stationary
        samples = []
        for _ in range(30):
            accel = self.sense_hat.get_accelerometer()
            if accel:
                samples.append([accel['x'], accel['y'], accel['z']])
            time.sleep(0.1)

        if samples:
            # Average to find gravity vector
            self.gravity_vector = np.mean(samples, axis=0)
            self.calibrated = True
            self.logger.info(f"Calibration complete. Gravity vector: {self.gravity_vector}")
        else:
            self.logger.error("Calibration failed - no samples collected")

    def _process_acceleration(self, accel_data: Dict):
        """
        Process raw acceleration data

        Args:
            accel_data: Dictionary with x, y, z acceleration values
        """
        # Convert to numpy array
        accel = np.array([accel_data['x'], accel_data['y'], accel_data['z']])

        # Remove gravity component
        accel_no_gravity = accel - self.gravity_vector

        # Calculate magnitude
        magnitude = np.linalg.norm(accel_no_gravity)

        # Add to buffers
        self.accel_buffer.append(accel)
        self.magnitude_buffer.append(magnitude)

    def _detect_movement_state(self) -> MovementState:
        """
        Detect current movement state based on acceleration patterns

        Returns:
            Detected movement state
        """
        if len(self.magnitude_buffer) < self.sample_window:
            return self.current_state

        # Calculate average magnitude
        avg_magnitude = np.mean(self.magnitude_buffer)

        # Determine state based on thresholds
        if avg_magnitude < self.threshold_static:
            return MovementState.STOP

        elif avg_magnitude < self.threshold_walking:
            # Additional check for walking pattern
            if self._has_walking_pattern():
                return MovementState.WALK
            else:
                return MovementState.STOP

        elif avg_magnitude < self.threshold_running:
            return MovementState.WALK

        else:
            # Additional check for running pattern
            if self._has_running_pattern():
                return MovementState.RUN
            else:
                return MovementState.WALK

    def _has_walking_pattern(self) -> bool:
        """
        Check if acceleration pattern matches walking

        Returns:
            True if walking pattern detected
        """
        if len(self.magnitude_buffer) < self.sample_window:
            return False

        try:
            # Look for periodic pattern typical of walking (1-3 Hz)
            # Using simple peak detection
            magnitudes = list(self.magnitude_buffer)

            # Count peaks (steps)
            peaks = 0
            for i in range(1, len(magnitudes) - 1):
                if magnitudes[i] > magnitudes[i-1] and magnitudes[i] > magnitudes[i+1]:
                    if magnitudes[i] > self.threshold_static:
                        peaks += 1

            # Walking typically has 1-3 steps per second
            # With our window size, expect 1-3 peaks
            return 1 <= peaks <= 4

        except Exception as e:
            self.logger.error(f"Walking pattern detection error: {e}")
            return False

    def _has_running_pattern(self) -> bool:
        """
        Check if acceleration pattern matches running

        Returns:
            True if running pattern detected
        """
        if len(self.magnitude_buffer) < self.sample_window:
            return False

        try:
            # Running has higher frequency and amplitude than walking
            magnitudes = list(self.magnitude_buffer)

            # Count peaks (steps)
            peaks = 0
            high_peaks = 0
            for i in range(1, len(magnitudes) - 1):
                if magnitudes[i] > magnitudes[i-1] and magnitudes[i] > magnitudes[i+1]:
                    peaks += 1
                    if magnitudes[i] > self.threshold_walking:
                        high_peaks += 1

            # Running typically has more frequent and higher peaks
            return peaks >= 3 and high_peaks >= 2

        except Exception as e:
            self.logger.error(f"Running pattern detection error: {e}")
            return False

    def _handle_state_change(self, new_state: MovementState):
        """
        Handle movement state change

        Args:
            new_state: New movement state
        """
        current_time = time.time()

        # Check cooldown period
        if current_time - self.last_trigger_time < self.cooldown:
            return

        # Update state
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_change_time = current_time
        self.last_trigger_time = current_time

        self.logger.info(f"Movement state changed: {self.previous_state.value} -> {new_state.value}")

        # Trigger callbacks
        for callback in self.state_callbacks:
            try:
                callback(new_state, self.previous_state)
            except Exception as e:
                self.logger.error(f"State callback error: {e}")

    def get_current_state(self) -> MovementState:
        """
        Get current movement state

        Returns:
            Current movement state
        """
        return self.current_state

    def get_activity_level(self) -> float:
        """
        Get current activity level

        Returns:
            Activity level (0.0 = no movement, higher = more movement)
        """
        if not self.magnitude_buffer:
            return 0.0

        return np.mean(self.magnitude_buffer)

    def get_step_count(self) -> int:
        """
        Get approximate step count from current buffer

        Returns:
            Estimated number of steps
        """
        if len(self.magnitude_buffer) < 3:
            return 0

        # Simple peak counting for steps
        magnitudes = list(self.magnitude_buffer)
        steps = 0

        for i in range(1, len(magnitudes) - 1):
            if magnitudes[i] > magnitudes[i-1] and magnitudes[i] > magnitudes[i+1]:
                if magnitudes[i] > self.threshold_static * 2:
                    steps += 1

        return steps

    def register_state_callback(self, callback: Callable[[MovementState, MovementState], None]):
        """
        Register a callback for state change events

        Args:
            callback: Function to call with (new_state, old_state) parameters
        """
        self.state_callbacks.append(callback)
        self.logger.debug(f"Registered state callback: {callback.__name__}")

    def get_movement_info(self) -> Dict:
        """
        Get movement detection information

        Returns:
            Dictionary with movement info
        """
        info = {
            'enabled': self.enabled,
            'current_state': self.current_state.value,
            'previous_state': self.previous_state.value,
            'state_duration': time.time() - self.state_change_time,
            'activity_level': self.get_activity_level(),
            'step_count': self.get_step_count(),
            'calibrated': self.calibrated,
            'running': self.running
        }

        if self.magnitude_buffer:
            info['current_magnitude'] = self.magnitude_buffer[-1]
            info['avg_magnitude'] = np.mean(self.magnitude_buffer)
            info['max_magnitude'] = np.max(self.magnitude_buffer)

        return info

    def reset_calibration(self):
        """Reset calibration and trigger recalibration"""
        self.calibrated = False
        self.gravity_vector = np.array([0.0, 0.0, 1.0])
        threading.Thread(target=self._calibrate, daemon=True).start()
        self.logger.info("Recalibration triggered")

    def recalibrate(self):
        """
        Recalibrate gravity vector (alias for reset_calibration)
        Useful when sensor orientation has changed
        """
        self.reset_calibration()

    def set_thresholds(self, static: Optional[float] = None,
                       walking: Optional[float] = None,
                       running: Optional[float] = None):
        """
        Adjust detection thresholds

        Args:
            static: Static threshold
            walking: Walking threshold
            running: Running threshold
        """
        if static is not None:
            self.threshold_static = static
        if walking is not None:
            self.threshold_walking = walking
        if running is not None:
            self.threshold_running = running

        self.logger.info(f"Thresholds updated - Static: {self.threshold_static}, "
                        f"Walking: {self.threshold_walking}, Running: {self.threshold_running}")