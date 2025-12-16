"""
Sense HAT Handler Module
Manages Sense HAT v2 hardware including LED display and IMU sensors
"""

import logging
import threading
import time
from typing import Dict, List, Tuple, Optional
from queue import Queue, Empty

try:
    from sense_hat import SenseHat
except ImportError:
    # For development/testing without actual hardware
    logging.warning("SenseHat library not available. Using mock implementation.")

    class MockJoystick:
        """Mock Joystick for development"""
        def __init__(self):
            self.direction_up = None
            self.direction_down = None
            self.direction_left = None
            self.direction_right = None
            self.direction_middle = None

    class SenseHat:
        """Mock SenseHat class for development"""
        def __init__(self):
            self.rotation = 0
            self.low_light = True
            self.stick = MockJoystick()

        def get_accelerometer_raw(self):
            return {'x': 0.0, 'y': 0.0, 'z': 1.0}

        def get_gyroscope_raw(self):
            return {'x': 0.0, 'y': 0.0, 'z': 0.0}

        def get_orientation(self):
            return {'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}

        def get_compass(self):
            return 0.0  # North

        def get_magnetometer(self):
            return {'x': 0.0, 'y': 1.0, 'z': 0.0}

        def get_magnetometer_raw(self):
            return {'x': 0.0, 'y': 1.0, 'z': 0.0}

        def get_compass_raw(self):
            return 0.0

        def show_message(self, message, **kwargs):
            print(f"SenseHAT Display: {message}")

        def clear(self, color=[0, 0, 0]):
            pass

        def set_pixels(self, pixels):
            pass

        def get_temperature(self):
            return 20.0

        def get_humidity(self):
            return 50.0

        def get_pressure(self):
            return 1013.25


class SenseHatHandler:
    """
    Handles Sense HAT v2 operations including:
    - LED matrix display
    - IMU sensor readings (accelerometer, gyroscope, magnetometer)
    - Environmental sensors (temperature, humidity, pressure)
    """

    def __init__(self, config: Dict):
        """
        Initialize the Sense HAT handler

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize Sense HAT
        try:
            self.sense = SenseHat()
            self.sense.rotation = config.get('sensors', {}).get('sense_hat', {}).get('rotation', 0)
            self.sense.low_light = config.get('sensors', {}).get('sense_hat', {}).get('low_light', True)
            self.enabled = config.get('sensors', {}).get('sense_hat', {}).get('enabled', True)
            self.logger.info("Sense HAT initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Sense HAT: {e}")
            self.enabled = False
            self.sense = None

        # Display queue for managing messages
        self.display_queue = Queue()
        self.display_thread = None
        self.running = False

        # Color configurations
        self.colors = config.get('display', {}).get('colors', {})
        self.text_color = config.get('display', {}).get('text_color', [255, 255, 255])
        self.bg_color = config.get('display', {}).get('background_color', [0, 0, 0])
        self.scroll_speed = config.get('display', {}).get('scroll_speed', 0.1)

        # Sensor data cache
        self.sensor_data = {
            'accelerometer': {'x': 0, 'y': 0, 'z': 0},
            'gyroscope': {'x': 0, 'y': 0, 'z': 0},
            'orientation': {'pitch': 0, 'roll': 0, 'yaw': 0},
            'magnetometer': {'x': 0, 'y': 0, 'z': 0},
            'compass': 0,
            'temperature': 0,
            'humidity': 0,
            'pressure': 0
        }

        # Sensor polling thread (centralized I2C access)
        self.sensor_polling_thread = None
        self.sensor_polling_rate = config.get('system', {}).get('sensor_polling_rate', 30)  # Hz

        # Joystick callbacks
        self.joystick_callbacks = {
            'up': [],
            'down': [],
            'left': [],
            'right': [],
            'middle': []
        }

        # Start display thread
        if self.enabled:
            self.start()

    def start(self):
        """Start the display handler thread and sensor polling thread"""
        if not self.enabled:
            return

        self.running = True

        # Start display thread
        self.display_thread = threading.Thread(target=self._display_worker, daemon=True)
        self.display_thread.start()

        # Start sensor polling thread (centralized I2C access)
        self.sensor_polling_thread = threading.Thread(target=self._sensor_polling_worker, daemon=True)
        self.sensor_polling_thread.start()
        self.logger.info(f"Sensor polling thread started at {self.sensor_polling_rate}Hz")

        # Register joystick event handlers
        if self.sense and hasattr(self.sense, 'stick'):
            self.sense.stick.direction_up = self._on_joystick_up
            self.sense.stick.direction_down = self._on_joystick_down
            self.sense.stick.direction_left = self._on_joystick_left
            self.sense.stick.direction_right = self._on_joystick_right
            self.sense.stick.direction_middle = self._on_joystick_middle
            self.logger.info("Joystick event handlers registered")

        self.logger.info("Sense HAT handler started")

    def stop(self):
        """Stop the display handler thread and sensor polling thread"""
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=2)
        if self.sensor_polling_thread:
            self.sensor_polling_thread.join(timeout=2)
        if self.sense:
            self.sense.clear()
        self.logger.info("Sense HAT handler stopped")

    def _display_worker(self):
        """Worker thread for handling display messages"""
        while self.running:
            try:
                # Get message from queue with timeout
                message = self.display_queue.get(timeout=0.5)
                if message is None:
                    continue

                # Handle different message types
                if isinstance(message, str):
                    self.show_text(message)
                elif isinstance(message, dict):
                    if 'text' in message:
                        # Display text with color
                        self.show_text(
                            message['text'],
                            color=message.get('color'),
                            bg_color=message.get('bg_color')
                        )
                    elif 'pattern' in message:
                        self.show_pattern(message['pattern'])
                    elif 'icon' in message:
                        self.show_icon(message['icon'])
                    elif 'pixels' in message:
                        self.sense.set_pixels(message['pixels'])

            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Display worker error: {e}")

    def _sensor_polling_worker(self):
        """
        Worker thread for polling sensors and updating cache
        Centralizes I2C access to prevent bus contention
        """
        sample_interval = 1.0 / self.sensor_polling_rate
        self.logger.info(f"Sensor polling worker started (rate: {self.sensor_polling_rate}Hz, interval: {sample_interval*1000:.1f}ms)")

        while self.running:
            try:
                start_time = time.time()

                # Read all IMU sensors in one batch (minimizes I2C transactions)
                if self.sense:
                    try:
                        # Read accelerometer
                        accel_raw = self.sense.get_accelerometer_raw()
                        if accel_raw:
                            self.sensor_data['accelerometer'] = accel_raw

                        # Read gyroscope and convert to degrees/sec
                        import math
                        gyro_raw = self.sense.get_gyroscope_raw()
                        if gyro_raw:
                            self.sensor_data['gyroscope'] = {
                                'x': gyro_raw['x'] * 57.2958,
                                'y': gyro_raw['y'] * 57.2958,
                                'z': gyro_raw['z'] * 57.2958
                            }

                        # Read orientation
                        orientation = self.sense.get_orientation()
                        if orientation:
                            self.sensor_data['orientation'] = orientation

                        # Read compass (magnetometer direction)
                        # Note: Sense HAT doesn't expose raw magnetometer data via API
                        # Only compass heading is available
                        compass = self.sense.get_compass()
                        if compass is not None:
                            self.sensor_data['compass'] = compass

                    except Exception as e:
                        self.logger.error(f"Sensor polling error: {e}")

                # Maintain sample rate
                elapsed = time.time() - start_time
                if elapsed < sample_interval:
                    time.sleep(sample_interval - elapsed)
                elif elapsed > sample_interval * 2:
                    self.logger.warning(f"Sensor polling falling behind: {elapsed*1000:.1f}ms > {sample_interval*1000:.1f}ms")

            except Exception as e:
                self.logger.error(f"Sensor polling worker error: {e}")
                time.sleep(0.1)

    def display_behavior(self, behavior: str, duration: float = 2.0):
        """
        Display a behavior indicator on the LED matrix

        Args:
            behavior: The behavior to display (stop, walk, run, fall, turn, shout, dark, bright)
            duration: How long to display the message (seconds)
        """
        if not self.enabled:
            return

        # Get color for behavior
        color = self.colors.get(behavior.lower(), self.text_color)

        # Create display message
        message = {
            'text': behavior.upper(),
            'color': color,
            'duration': duration
        }

        # Add to display queue
        self.display_queue.put(message)

        self.logger.debug(f"Queued behavior display: {behavior}")

    def show_text(self, text: str, color: Optional[List[int]] = None,
                  bg_color: Optional[List[int]] = None):
        """
        Show scrolling text on the LED matrix

        Args:
            text: Text to display
            color: RGB color for text
            bg_color: RGB color for background
        """
        if not self.enabled or not self.sense:
            return

        try:
            self.sense.show_message(
                text,
                text_colour=color or self.text_color,
                back_colour=bg_color or self.bg_color,
                scroll_speed=self.scroll_speed
            )
        except Exception as e:
            self.logger.error(f"Failed to show text: {e}")

    def show_pattern(self, pattern: List[List[int]]):
        """
        Display a pattern on the LED matrix

        Args:
            pattern: 64-element list of RGB values
        """
        if not self.enabled or not self.sense:
            return

        try:
            if len(pattern) == 64:
                self.sense.set_pixels(pattern)
            else:
                self.logger.error(f"Invalid pattern length: {len(pattern)}")
        except Exception as e:
            self.logger.error(f"Failed to show pattern: {e}")

    def show_icon(self, icon_name: str):
        """
        Display a predefined icon for a behavior

        Args:
            icon_name: Name of the icon to display
        """
        # Icon definitions (8x8 pixel patterns)
        icons = {
            'stop': self._create_stop_icon(),
            'walk': self._create_walk_icon(),
            'run': self._create_run_icon(),
            'fall': self._create_fall_icon(),
            'turn': self._create_turn_icon(),
            'shout': self._create_shout_icon(),
            'dark': self._create_dark_icon(),
            'bright': self._create_bright_icon(),
        }

        if icon_name in icons:
            self.show_pattern(icons[icon_name])
        else:
            self.logger.warning(f"Unknown icon: {icon_name}")

    def clear_display(self):
        """Clear the LED matrix"""
        if self.enabled and self.sense:
            self.sense.clear()

    # IMU Sensor Methods

    def get_accelerometer(self) -> Dict[str, float]:
        """
        Get accelerometer readings (from cache, updated by polling thread)

        Returns:
            Dictionary with x, y, z acceleration values in g
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['accelerometer'].copy()

    def get_gyroscope(self) -> Dict[str, float]:
        """
        Get gyroscope readings (from cache, updated by polling thread)

        Returns:
            Dictionary with x, y, z angular velocity in degrees/sec
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['gyroscope'].copy()

    def get_orientation(self) -> Dict[str, float]:
        """
        Get orientation readings (from cache, updated by polling thread)

        Returns:
            Dictionary with pitch, roll, yaw in degrees
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['orientation'].copy()

    def get_all_sensors(self) -> Dict:
        """
        Get all sensor readings at once (from cache, updated by polling thread)

        Returns:
            Dictionary with all sensor data
        """
        # Return cached sensor data (all from cache to avoid I2C contention)
        return {
            'accelerometer': self.sensor_data['accelerometer'].copy(),
            'gyroscope': self.sensor_data['gyroscope'].copy(),
            'orientation': self.sensor_data['orientation'].copy(),
            'magnetometer': self.sensor_data['magnetometer'].copy(),
            'compass': self.sensor_data['compass'],
            'temperature': self.sensor_data['temperature'],
            'humidity': self.sensor_data['humidity'],
            'pressure': self.sensor_data['pressure'],
            'timestamp': time.time()
        }

    # Environmental Sensor Methods

    def get_temperature(self) -> float:
        """Get temperature in Celsius"""
        if not self.enabled or not self.sense:
            return 20.0

        try:
            return self.sense.get_temperature()
        except Exception as e:
            self.logger.error(f"Failed to read temperature: {e}")
            return 20.0

    def get_humidity(self) -> float:
        """Get humidity percentage"""
        if not self.enabled or not self.sense:
            return 50.0

        try:
            return self.sense.get_humidity()
        except Exception as e:
            self.logger.error(f"Failed to read humidity: {e}")
            return 50.0

    def get_pressure(self) -> float:
        """Get atmospheric pressure in millibars"""
        if not self.enabled or not self.sense:
            return 1013.25

        try:
            return self.sense.get_pressure()
        except Exception as e:
            self.logger.error(f"Failed to read pressure: {e}")
            return 1013.25

    def get_compass(self) -> float:
        """
        Get compass heading from magnetometer (from cache, updated by polling thread)

        Returns:
            Heading in degrees (0-360)
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['compass']

    def get_magnetometer(self) -> Dict[str, float]:
        """
        Get magnetometer readings (from cache, updated by polling thread)

        Returns:
            Dictionary with x, y, z magnetic field values in microteslas
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['magnetometer'].copy()

    def get_compass_raw(self) -> float:
        """
        Get raw compass heading (from cache, updated by polling thread)

        Returns:
            Raw heading in degrees (0-360)
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['compass']

    def get_magnetometer_raw(self) -> Dict[str, float]:
        """
        Get raw magnetometer readings (from cache, updated by polling thread)

        Returns:
            Dictionary with x, y, z raw magnetic field values
        """
        # Return cached data (updated by polling thread)
        # This prevents I2C bus contention
        return self.sensor_data['magnetometer'].copy()

    # Icon Creation Methods

    def _create_stop_icon(self) -> List:
        """Create STOP icon pattern"""
        R = self.colors.get('stop', [255, 0, 0])
        O = [0, 0, 0]
        return [
            O, R, R, R, R, R, R, O,
            R, R, R, R, R, R, R, R,
            R, R, O, O, O, O, R, R,
            R, R, O, O, O, O, R, R,
            R, R, O, O, O, O, R, R,
            R, R, O, O, O, O, R, R,
            R, R, R, R, R, R, R, R,
            O, R, R, R, R, R, R, O,
        ]

    def _create_walk_icon(self) -> List:
        """Create walking person icon"""
        G = self.colors.get('walk', [0, 255, 0])
        O = [0, 0, 0]
        return [
            O, O, G, G, G, O, O, O,
            O, O, G, G, G, O, O, O,
            O, O, O, G, O, O, O, O,
            O, G, G, G, G, G, O, O,
            O, O, O, G, O, O, O, O,
            O, O, G, O, G, O, O, O,
            O, G, O, O, O, G, O, O,
            O, G, O, O, O, G, O, O,
        ]

    def _create_run_icon(self) -> List:
        """Create running person icon"""
        Y = self.colors.get('run', [255, 255, 0])
        O = [0, 0, 0]
        return [
            O, O, Y, Y, Y, O, O, O,
            O, O, Y, Y, Y, O, O, O,
            O, O, O, Y, O, O, O, O,
            O, Y, Y, Y, Y, O, O, O,
            O, O, O, Y, O, Y, O, O,
            O, O, Y, O, O, O, Y, O,
            O, Y, O, O, O, O, O, Y,
            Y, O, O, O, O, Y, O, O,
        ]

    def _create_fall_icon(self) -> List:
        """Create falling person icon"""
        R = self.colors.get('fall', [255, 0, 0])
        O = [0, 0, 0]
        return [
            O, O, O, O, O, O, O, O,
            O, O, O, O, O, O, O, O,
            O, O, O, O, O, R, R, O,
            O, O, O, O, R, R, R, O,
            R, R, R, R, R, R, O, O,
            R, O, R, O, O, O, O, O,
            O, R, O, O, O, O, O, O,
            R, R, R, R, R, R, R, R,
        ]

    def _create_turn_icon(self) -> List:
        """Create turn around arrow icon"""
        C = self.colors.get('turn', [0, 255, 255])
        O = [0, 0, 0]
        return [
            O, O, C, C, C, C, O, O,
            O, C, O, O, O, C, O, O,
            C, O, O, O, C, O, O, O,
            C, O, O, C, O, O, O, O,
            C, O, O, O, C, O, O, O,
            C, O, O, O, O, C, O, O,
            O, C, O, O, O, C, O, O,
            O, O, C, C, C, C, O, O,
        ]

    def _create_shout_icon(self) -> List:
        """Create shouting mouth icon"""
        M = self.colors.get('shout', [255, 0, 255])
        O = [0, 0, 0]
        return [
            O, O, M, M, M, M, O, O,
            O, M, O, O, O, O, M, O,
            M, O, M, M, M, M, O, M,
            M, O, M, M, M, M, O, M,
            M, O, M, M, M, M, O, M,
            M, O, O, O, O, O, O, M,
            O, M, O, O, O, O, M, O,
            O, O, M, M, M, M, O, O,
        ]

    def _create_dark_icon(self) -> List:
        """Create moon/dark icon"""
        D = self.colors.get('dark', [64, 64, 64])
        O = [0, 0, 0]
        return [
            O, O, O, D, D, O, O, O,
            O, O, D, O, O, D, O, O,
            O, D, O, O, O, D, O, O,
            D, O, O, O, O, D, O, O,
            D, O, O, O, D, O, O, O,
            D, O, O, O, D, O, O, O,
            O, D, O, D, O, O, O, O,
            O, O, D, D, O, O, O, O,
        ]

    def _create_bright_icon(self) -> List:
        """Create sun/bright icon"""
        W = self.colors.get('bright', [255, 255, 255])
        Y = [255, 255, 0]
        O = [0, 0, 0]
        return [
            O, W, O, W, W, O, W, O,
            W, O, Y, Y, Y, Y, O, W,
            O, Y, Y, Y, Y, Y, Y, O,
            W, Y, Y, Y, Y, Y, Y, W,
            W, Y, Y, Y, Y, Y, Y, W,
            O, Y, Y, Y, Y, Y, Y, O,
            W, O, Y, Y, Y, Y, O, W,
            O, W, O, W, W, O, W, O,
        ]

    # Joystick event handlers

    def _on_joystick_up(self, event):
        """Handle joystick up event"""
        if event.action == 'pressed':
            self.logger.debug("Joystick UP pressed")
            for callback in self.joystick_callbacks['up']:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Joystick UP callback error: {e}")

    def _on_joystick_down(self, event):
        """Handle joystick down event"""
        if event.action == 'pressed':
            self.logger.debug("Joystick DOWN pressed")
            for callback in self.joystick_callbacks['down']:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Joystick DOWN callback error: {e}")

    def _on_joystick_left(self, event):
        """Handle joystick left event"""
        if event.action == 'pressed':
            self.logger.debug("Joystick LEFT pressed")
            for callback in self.joystick_callbacks['left']:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Joystick LEFT callback error: {e}")

    def _on_joystick_right(self, event):
        """Handle joystick right event"""
        if event.action == 'pressed':
            self.logger.debug("Joystick RIGHT pressed")
            for callback in self.joystick_callbacks['right']:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Joystick RIGHT callback error: {e}")

    def _on_joystick_middle(self, event):
        """Handle joystick middle button event"""
        if event.action == 'pressed':
            self.logger.info("Joystick MIDDLE pressed")
            for callback in self.joystick_callbacks['middle']:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Joystick MIDDLE callback error: {e}")

    def register_joystick_callback(self, direction: str, callback):
        """
        Register a callback for joystick events

        Args:
            direction: Direction ('up', 'down', 'left', 'right', 'middle')
            callback: Function to call when button is pressed
        """
        if direction in self.joystick_callbacks:
            self.joystick_callbacks[direction].append(callback)
            self.logger.info(f"Registered joystick {direction} callback: {callback.__name__}")
        else:
            self.logger.warning(f"Invalid joystick direction: {direction}")