"""
Fall Detection Module
Detects falling behavior using accelerometer and gyroscope data
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, Optional, Callable, List
from collections import deque
from enum import Enum


class FallState(Enum):
    """Fall detection states"""
    NORMAL = "normal"
    FALLING = "falling"
    FALLEN = "fallen"
    RECOVERING = "recovering"


class FallDetector:
    """
    Detects falling events using IMU sensors
    """

    def __init__(self, config: Dict, sense_hat_handler):
        """
        Initialize the fall detector

        Args:
            config: Configuration dictionary
            sense_hat_handler: Reference to SenseHatHandler instance
        """
        self.config = config
        self.sense_hat = sense_hat_handler
        self.logger = logging.getLogger(__name__)

        # Detection parameters
        self.enabled = config.get('behaviors', {}).get('fall', {}).get('enabled', True)
        self.acceleration_threshold = config.get('behaviors', {}).get('fall', {}).get('acceleration_threshold', 2.0)
        self.angle_threshold = config.get('behaviors', {}).get('fall', {}).get('angle_threshold', 45)
        self.impact_duration = config.get('behaviors', {}).get('fall', {}).get('impact_duration', 0.5)
        self.recovery_time = config.get('behaviors', {}).get('fall', {}).get('recovery_time', 3)

        # State tracking
        self.current_state = FallState.NORMAL
        self.fall_start_time = None
        self.fall_detected_time = None
        self.last_trigger_time = 0

        # Data buffers (10 samples = 1 second at 10Hz from SenseHatHandler polling)
        self.accel_buffer = deque(maxlen=10)  # 1 second at 10Hz
        self.gyro_buffer = deque(maxlen=10)
        self.orientation_buffer = deque(maxlen=10)

        # Reference orientation
        self.reference_orientation = {'pitch': 0, 'roll': 0, 'yaw': 0}
        self.calibrated = False

        # Fall detection metrics
        self.max_acceleration = 0
        self.orientation_change = 0

        # Callbacks
        self.fall_callbacks = []

        # Thread control
        self.running = False
        self.detection_thread = None

        self.logger.info("Fall detector initialized")

    def start(self):
        """Start the fall detection thread"""
        if not self.enabled or not self.sense_hat.enabled:
            self.logger.warning("Fall detection disabled or Sense HAT not available")
            return

        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()

        # Calibrate reference orientation
        threading.Thread(target=self._calibrate, daemon=True).start()

        self.logger.info(f"✅ Fall detector started (threshold: {self.acceleration_threshold}g, angle: {self.angle_threshold}°)")

    def stop(self):
        """Stop the fall detection thread"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        self.logger.info("Fall detection stopped")

    def _detection_worker(self):
        """Worker thread for continuous fall detection"""
        sample_rate = 10  # Hz - Matches SenseHatHandler polling rate (cached sensor data)
        sample_interval = 1.0 / sample_rate

        self.logger.info(f"Fall detector worker started at {sample_rate}Hz (using cached sensor data)")

        while self.running:
            try:
                start_time = time.time()

                # Get sensor data from cache (no I2C contention)
                # SenseHatHandler polling thread updates cache at configured rate
                accel_data = self.sense_hat.get_accelerometer()

                # Only get gyro/orientation if we have acceleration data
                if accel_data:
                    gyro_data = self.sense_hat.get_gyroscope()
                    orientation_data = self.sense_hat.get_orientation()

                    # Add to buffers
                    self.accel_buffer.append(accel_data)
                    if gyro_data:
                        self.gyro_buffer.append(gyro_data)
                    if orientation_data:
                        self.orientation_buffer.append(orientation_data)

                    # Detect fall (priority task)
                    self._detect_fall()

                    # Handle state transitions
                    self._handle_state_transitions()

                # Maintain sample rate (but don't sleep if we're already behind)
                elapsed = time.time() - start_time
                if elapsed < sample_interval:
                    time.sleep(sample_interval - elapsed)
                elif elapsed > sample_interval * 2:
                    # Log if we're falling behind significantly
                    self.logger.warning(f"Fall detector falling behind: {elapsed:.3f}s > {sample_interval:.3f}s")

            except Exception as e:
                self.logger.error(f"Fall detection error: {e}")
                time.sleep(0.1)

    def _calibrate(self):
        """Calibrate reference orientation"""
        self.logger.info("Calibrating fall detector...")

        time.sleep(1)  # Wait for initial data

        # Get current orientation as reference
        orientation = self.sense_hat.get_orientation()
        if orientation:
            self.reference_orientation = orientation.copy()
            self.calibrated = True
            self.logger.info(f"Calibration complete. Reference orientation: {self.reference_orientation}")
        else:
            self.logger.error("Calibration failed - no orientation data")

    def _detect_fall(self):
        """Detect fall based on sensor data"""
        if len(self.accel_buffer) < 10:
            return

        if not self.calibrated:
            return

        current_time = time.time()

        # Calculate acceleration magnitude
        accel = self.accel_buffer[-1]
        accel_vector = np.array([accel['x'], accel['y'], accel['z']])
        accel_magnitude = np.linalg.norm(accel_vector)

        # Check for free fall (low acceleration)
        if accel_magnitude < 0.5 and self.current_state == FallState.NORMAL:
            # Possible free fall detected
            if self.fall_start_time is None:
                self.fall_start_time = current_time

        # Check for impact (high acceleration)
        if accel_magnitude > self.acceleration_threshold:
            self.max_acceleration = max(self.max_acceleration, accel_magnitude)

            # Check if this follows a free fall
            if self.fall_start_time and (current_time - self.fall_start_time < self.impact_duration):
                # Fall pattern detected
                if self.current_state == FallState.NORMAL:
                    self._confirm_fall()

        # Check orientation change
        if self.orientation_buffer:
            current_orientation = self.orientation_buffer[-1]
            self.orientation_change = self._calculate_orientation_change(current_orientation)

            # Large orientation change indicates fall
            if self.orientation_change > self.angle_threshold and self.current_state == FallState.NORMAL:
                # Lower acceleration threshold when there's clear orientation change
                if self.max_acceleration > 1.5:
                    self._confirm_fall()

    def _calculate_orientation_change(self, current_orientation: Dict) -> float:
        """
        Calculate orientation change from reference

        Args:
            current_orientation: Current orientation data

        Returns:
            Orientation change in degrees
        """
        # Calculate angular difference
        pitch_diff = abs(current_orientation['pitch'] - self.reference_orientation['pitch'])
        roll_diff = abs(current_orientation['roll'] - self.reference_orientation['roll'])

        # Normalize angles to 0-180 range
        pitch_diff = min(pitch_diff, 360 - pitch_diff)
        roll_diff = min(roll_diff, 360 - roll_diff)

        # Combined orientation change
        return np.sqrt(pitch_diff**2 + roll_diff**2)

    def _confirm_fall(self):
        """Confirm fall detection"""
        current_time = time.time()

        # Avoid duplicate detections
        if current_time - self.last_trigger_time < 2:
            return

        self.current_state = FallState.FALLING
        self.fall_detected_time = current_time
        self.last_trigger_time = current_time

        self.logger.warning(f"FALL DETECTED! Max acceleration: {self.max_acceleration:.2f}g, "
                           f"Orientation change: {self.orientation_change:.1f}°")

        # Trigger fall callbacks
        for callback in self.fall_callbacks:
            try:
                callback(self.max_acceleration, self.orientation_change)
            except Exception as e:
                self.logger.error(f"Fall callback error: {e}")

        # Transition to fallen state
        self.current_state = FallState.FALLEN

    def _handle_state_transitions(self):
        """Handle state transitions for recovery"""
        current_time = time.time()

        if self.current_state == FallState.FALLEN:
            # Check if person is recovering (movement detected)
            if self._detect_recovery():
                self.current_state = FallState.RECOVERING
                self.logger.info("Recovery movement detected")

        elif self.current_state == FallState.RECOVERING:
            # Check if recovered (upright and stable)
            if self._is_upright():
                self.current_state = FallState.NORMAL
                self.fall_start_time = None
                self.fall_detected_time = None
                self.max_acceleration = 0
                self.logger.info("Recovery complete")

        # Timeout recovery if too long
        if self.fall_detected_time:
            if current_time - self.fall_detected_time > self.recovery_time:
                if self.current_state != FallState.NORMAL:
                    self.current_state = FallState.NORMAL
                    self.fall_start_time = None
                    self.fall_detected_time = None
                    self.max_acceleration = 0
                    self.logger.info("Fall state reset after timeout")

    def _detect_recovery(self) -> bool:
        """
        Detect recovery movement

        Returns:
            True if recovery movement detected
        """
        if len(self.gyro_buffer) < 5:
            return False

        # Check for significant rotation (trying to get up)
        recent_gyro = list(self.gyro_buffer)[-5:]
        total_rotation = sum(
            np.linalg.norm([g['x'], g['y'], g['z']])
            for g in recent_gyro
        )

        return total_rotation > 50  # Degrees

    def _is_upright(self) -> bool:
        """
        Check if person is upright

        Returns:
            True if upright position detected
        """
        if not self.orientation_buffer:
            return False

        current_orientation = self.orientation_buffer[-1]

        # Check if orientation is close to reference (upright)
        orientation_diff = self._calculate_orientation_change(current_orientation)

        return orientation_diff < 30  # Within 30 degrees of reference

    def get_current_state(self) -> FallState:
        """
        Get current fall detection state

        Returns:
            Current fall state
        """
        return self.current_state

    def is_fallen(self) -> bool:
        """
        Check if currently in fallen state

        Returns:
            True if fallen
        """
        return self.current_state == FallState.FALLEN

    def register_fall_callback(self, callback: Callable[[float, float], None]):
        """
        Register a callback for fall detection events

        Args:
            callback: Function to call with (max_acceleration, orientation_change) parameters
        """
        self.fall_callbacks.append(callback)
        self.logger.debug(f"Registered fall callback: {callback.__name__}")

    def get_fall_info(self) -> Dict:
        """
        Get fall detection information

        Returns:
            Dictionary with fall detection info
        """
        info = {
            'enabled': self.enabled,
            'current_state': self.current_state.value,
            'is_fallen': self.is_fallen(),
            'max_acceleration': self.max_acceleration,
            'orientation_change': self.orientation_change,
            'calibrated': self.calibrated,
            'running': self.running
        }

        if self.fall_detected_time:
            info['time_since_fall'] = time.time() - self.fall_detected_time

        if self.accel_buffer:
            recent_accel = self.accel_buffer[-1]
            accel_magnitude = np.linalg.norm([recent_accel['x'], recent_accel['y'], recent_accel['z']])
            info['current_acceleration'] = accel_magnitude

        if self.orientation_buffer:
            info['current_orientation'] = self.orientation_buffer[-1]

        return info

    def reset(self):
        """Reset fall detection state"""
        self.current_state = FallState.NORMAL
        self.fall_start_time = None
        self.fall_detected_time = None
        self.max_acceleration = 0
        self.orientation_change = 0
        self.logger.info("Fall detector reset")

    def recalibrate(self):
        """Recalibrate reference orientation"""
        self.calibrated = False
        threading.Thread(target=self._calibrate, daemon=True).start()
        self.logger.info("Recalibration triggered")