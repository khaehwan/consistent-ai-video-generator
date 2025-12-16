"""
Turn Detection Module
Detects turning around behavior using gyroscope and orientation data
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, Optional, Callable, List
from collections import deque


class TurnDetector:
    """
    Detects turning around (180-degree rotation) using gyroscope data
    """

    def __init__(self, config: Dict, sense_hat_handler):
        """
        Initialize the turn detector

        Args:
            config: Configuration dictionary
            sense_hat_handler: Reference to SenseHatHandler instance
        """
        self.config = config
        self.sense_hat = sense_hat_handler
        self.logger = logging.getLogger(__name__)

        # Detection parameters
        self.enabled = config.get('behaviors', {}).get('turn', {}).get('enabled', True)
        self.rotation_threshold = config.get('behaviors', {}).get('turn', {}).get('rotation_threshold', 160)
        self.rotation_time = config.get('behaviors', {}).get('turn', {}).get('rotation_time', 2)
        self.cooldown = config.get('behaviors', {}).get('turn', {}).get('cooldown', 3)

        # State tracking
        self.is_turning = False
        self.turn_start_time = None
        self.turn_start_yaw = None
        self.total_rotation = 0
        self.integrated_rotation = 0  # Real-time integrated rotation
        self.last_trigger_time = 0
        self.last_sample_time = None  # For accurate time intervals

        # Data buffers (increased size for 60Hz sampling)
        self.gyro_buffer = deque(maxlen=120)  # 2 seconds at 60Hz
        self.accel_buffer = deque(maxlen=120)  # For gravity direction
        self.orientation_buffer = deque(maxlen=120)
        self.yaw_history = deque(maxlen=120)

        # Gravity direction (for orientation-independent detection)
        self.gravity_vector = None
        self.calibration_samples = 30  # Number of samples for calibration

        # Callbacks
        self.turn_callbacks = []

        # Thread control
        self.running = False
        self.detection_thread = None

        self.logger.info("Turn detector initialized")

    def start(self):
        """Start the turn detection thread"""
        if not self.enabled or not self.sense_hat.enabled:
            self.logger.warning("Turn detection disabled or Sense HAT not available")
            return

        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()

        self.logger.info("Turn detection started")

    def stop(self):
        """Stop the turn detection thread"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        self.logger.info("Turn detection stopped")

    def _detection_worker(self):
        """Worker thread for continuous turn detection"""
        sample_rate = 60  # Hz (increased from 30Hz for better fast rotation detection)
        sample_interval = 1.0 / sample_rate

        # Calibrate gravity direction
        self._calibrate_gravity()

        while self.running:
            try:
                start_time = time.time()

                # Get sensor data
                gyro_data = self.sense_hat.get_gyroscope()
                accel_data = self.sense_hat.get_accelerometer()
                orientation_data = self.sense_hat.get_orientation()

                if gyro_data and accel_data and orientation_data:
                    # Add to buffers
                    self.gyro_buffer.append(gyro_data)
                    self.accel_buffer.append(accel_data)
                    self.orientation_buffer.append(orientation_data)
                    self.yaw_history.append(orientation_data['yaw'])

                    # Detect turn with actual time interval
                    self._detect_turn(start_time)

                # Maintain sample rate
                elapsed = time.time() - start_time
                if elapsed < sample_interval:
                    time.sleep(sample_interval - elapsed)

            except Exception as e:
                self.logger.error(f"Turn detection error: {e}")
                time.sleep(0.1)

    def _calibrate_gravity(self):
        """
        Calibrate gravity direction at startup
        This allows orientation-independent turn detection
        """
        self.logger.info("Calibrating gravity direction...")
        gravity_samples = []

        for _ in range(self.calibration_samples):
            accel = self.sense_hat.get_accelerometer()
            if accel:
                gravity_samples.append([accel['x'], accel['y'], accel['z']])
            time.sleep(0.05)  # 50ms between samples

        if gravity_samples:
            # Average all samples
            avg_gravity = np.mean(gravity_samples, axis=0)
            # Normalize to unit vector
            magnitude = np.linalg.norm(avg_gravity)
            if magnitude > 0:
                self.gravity_vector = avg_gravity / magnitude
                self.logger.info(f"Gravity calibrated: [{self.gravity_vector[0]:.2f}, "
                               f"{self.gravity_vector[1]:.2f}, {self.gravity_vector[2]:.2f}]")
            else:
                self.gravity_vector = np.array([0, 0, 1])  # Default: Z-up
                self.logger.warning("Gravity calibration failed, using default Z-up")
        else:
            self.gravity_vector = np.array([0, 0, 1])
            self.logger.warning("No accelerometer data, using default Z-up")

    def _get_vertical_axis_rotation(self, gyro_data: Dict[str, float]) -> float:
        """
        Get rotation rate around vertical axis (gravity direction)
        This is the yaw rotation regardless of sensor orientation
        Returns signed value - positive/negative indicates direction

        Args:
            gyro_data: Gyroscope data with x, y, z angular velocities

        Returns:
            Rotation rate around vertical axis (degrees/second, signed)
        """
        if self.gravity_vector is None:
            # Fallback: use Z-axis
            return gyro_data['z']

        # Convert gyro data to numpy array
        gyro_vector = np.array([gyro_data['x'], gyro_data['y'], gyro_data['z']])

        # Project gyro vector onto gravity vector
        # This gives rotation around the vertical axis (yaw)
        vertical_axis_rotation = np.dot(gyro_vector, self.gravity_vector)

        return vertical_axis_rotation

    def _detect_turn(self, current_time: float):
        """
        Detect turning around behavior

        Args:
            current_time: Current timestamp for accurate interval calculation
        """
        if len(self.gyro_buffer) < 5:
            return

        # Get current gyroscope data
        current_gyro = self.gyro_buffer[-1]
        current_orientation = self.orientation_buffer[-1]

        # Get orientation-independent vertical axis rotation (signed)
        yaw_velocity = self._get_vertical_axis_rotation(current_gyro)

        # Detect start of turn (significant rotation speed)
        if abs(yaw_velocity) > 30 and not self.is_turning:  # degrees/second
            # Check cooldown
            if current_time - self.last_trigger_time < self.cooldown:
                return

            self.is_turning = True
            self.turn_start_time = current_time
            self.last_sample_time = current_time
            self.turn_start_yaw = current_orientation['yaw']
            self.total_rotation = 0
            self.integrated_rotation = 0  # Reset real-time accumulator
            self.logger.debug(f"Turn started at yaw {self.turn_start_yaw:.1f}°")

        # Track ongoing turn and accumulate rotation in real-time
        elif self.is_turning:
            # Calculate actual time interval since last sample
            if self.last_sample_time is not None:
                dt = current_time - self.last_sample_time
            else:
                dt = 1.0 / 60  # Fallback to expected rate

            self.last_sample_time = current_time

            # Accumulate rotation from current sample (already signed)
            rotation_rate = self._get_vertical_axis_rotation(current_gyro)

            # Accumulate rotation using actual time interval
            self.integrated_rotation += rotation_rate * dt
            self.total_rotation = self.integrated_rotation

            # Check if turn is taking too long
            if current_time - self.turn_start_time > self.rotation_time:
                self.logger.debug("Turn timeout - resetting")
                self._reset_turn()
                return

            # Check if turn is complete (approximately 180 degrees)
            if abs(self.total_rotation) >= self.rotation_threshold:
                self._confirm_turn()

            # Check if rotation has stopped
            elif abs(yaw_velocity) < 10:  # Rotation stopped
                if abs(self.total_rotation) < 90:  # Not enough rotation
                    self.logger.debug(f"Turn stopped early at {self.total_rotation:.1f}°")
                    self._reset_turn()

    def _calculate_total_rotation(self) -> float:
        """
        Calculate total rotation from start

        Returns:
            Total rotation in degrees
        """
        if not self.orientation_buffer or self.turn_start_yaw is None:
            return 0

        # Primary method: integrate gyroscope data (most accurate for large rotations)
        if len(self.gyro_buffer) > 1:
            # Sum up angular velocities in horizontal plane
            integrated_rotation = 0
            sample_time = 1.0 / 30  # Sample rate

            for gyro in list(self.gyro_buffer):
                # Use orientation-independent horizontal rotation
                horizontal_rate = self._get_horizontal_rotation_rate(gyro)
                # Determine sign based on gravity-aligned rotation
                # Use dot product of gyro and gravity to determine rotation direction
                if self.gravity_vector is not None:
                    gyro_vec = np.array([gyro['x'], gyro['y'], gyro['z']])
                    # Rotation around gravity vector (vertical)
                    vertical_rotation = np.dot(gyro_vec, self.gravity_vector)
                    sign = 1 if vertical_rotation >= 0 else -1
                else:
                    # Fallback: use Z-axis
                    sign = 1 if gyro['z'] >= 0 else -1
                integrated_rotation += horizontal_rate * sign * sample_time

            # Secondary method: yaw angle difference (for verification)
            current_yaw = self.orientation_buffer[-1]['yaw']
            rotation = current_yaw - self.turn_start_yaw

            # Normalize to -180 to 180 range
            if rotation > 180:
                rotation -= 360
            elif rotation < -180:
                rotation += 360

            # Use integrated value as primary, yaw difference for small corrections
            # If they agree (within 30°), average them
            # If they disagree significantly, trust gyroscope integration
            if abs(integrated_rotation - rotation) < 30:
                # They agree - average for best accuracy
                final_rotation = (rotation + integrated_rotation) / 2
                self.logger.debug(f"Rotation agreed: Yaw={rotation:.1f}°, Gyro={integrated_rotation:.1f}°, Final={final_rotation:.1f}°")
            else:
                # They disagree - use gyroscope (better for large rotations and wrap-around)
                final_rotation = integrated_rotation
                self.logger.debug(f"Rotation disagreed: Yaw={rotation:.1f}°, Gyro={integrated_rotation:.1f}° → Using Gyro")

            return final_rotation
        else:
            # Fallback: use yaw difference only (not enough gyro samples)
            current_yaw = self.orientation_buffer[-1]['yaw']
            rotation = current_yaw - self.turn_start_yaw

            # Normalize to -180 to 180 range
            if rotation > 180:
                rotation -= 360
            elif rotation < -180:
                rotation += 360

            return rotation

    def _confirm_turn(self):
        """Confirm turn around detection"""
        current_time = time.time()
        turn_duration = current_time - self.turn_start_time

        self.logger.info(f"TURN AROUND DETECTED! Rotation: {self.total_rotation:.1f}°, "
                        f"Duration: {turn_duration:.2f}s")

        # Trigger callbacks
        for callback in self.turn_callbacks:
            try:
                callback(self.total_rotation, turn_duration)
            except Exception as e:
                self.logger.error(f"Turn callback error: {e}")

        # Reset and set cooldown
        self.last_trigger_time = current_time
        self._reset_turn()

    def _reset_turn(self):
        """Reset turn detection state"""
        self.is_turning = False
        self.turn_start_time = None
        self.turn_start_yaw = None
        self.total_rotation = 0
        self.integrated_rotation = 0
        self.last_sample_time = None

    def is_currently_turning(self) -> bool:
        """
        Check if currently turning

        Returns:
            True if turn is in progress
        """
        return self.is_turning

    def get_rotation_progress(self) -> float:
        """
        Get current rotation progress

        Returns:
            Current rotation in degrees (0 if not turning)
        """
        if self.is_turning:
            return self.total_rotation
        return 0

    def register_turn_callback(self, callback: Callable[[float, float], None]):
        """
        Register a callback for turn detection events

        Args:
            callback: Function to call with (rotation_degrees, duration) parameters
        """
        self.turn_callbacks.append(callback)
        self.logger.debug(f"Registered turn callback: {callback.__name__}")

    def get_turn_info(self) -> Dict:
        """
        Get turn detection information

        Returns:
            Dictionary with turn detection info
        """
        info = {
            'enabled': self.enabled,
            'is_turning': self.is_turning,
            'rotation_progress': self.get_rotation_progress(),
            'running': self.running
        }

        if self.is_turning and self.turn_start_time:
            info['turn_duration'] = time.time() - self.turn_start_time

        if self.gyro_buffer:
            current_gyro = self.gyro_buffer[-1]
            info['current_yaw_velocity'] = current_gyro['z']
            info['current_pitch_velocity'] = current_gyro['x']
            info['current_roll_velocity'] = current_gyro['y']

        if self.orientation_buffer:
            info['current_orientation'] = self.orientation_buffer[-1]

        if self.last_trigger_time > 0:
            info['time_since_last_turn'] = time.time() - self.last_trigger_time
            info['cooldown_remaining'] = max(0, self.cooldown - (time.time() - self.last_trigger_time))

        return info

    def set_threshold(self, rotation_threshold: float):
        """
        Adjust rotation threshold

        Args:
            rotation_threshold: New threshold in degrees (e.g., 160 for turn around)
        """
        self.rotation_threshold = rotation_threshold
        self.logger.info(f"Rotation threshold set to {rotation_threshold}°")

    def reset(self):
        """Reset turn detection state"""
        self._reset_turn()
        self.last_trigger_time = 0
        self.logger.info("Turn detector reset")

    def recalibrate(self):
        """
        Recalibrate gravity direction
        Useful if sensor orientation has changed
        """
        self.logger.info("Recalibrating turn detector...")
        if self.running:
            # Calibrate in background
            self._calibrate_gravity()
        else:
            self.logger.warning("Turn detector not running, calibration skipped")
        self.logger.info("Turn detector recalibrated")