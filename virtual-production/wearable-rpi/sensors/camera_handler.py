"""
Camera Handler Module
Manages Raspberry Pi NoIR Camera v2 for brightness detection and video capture
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, Optional, Callable, Tuple
from queue import Queue, Empty
import cv2

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
    PICAMERA_AVAILABLE = True
except ImportError:
    logging.warning("Picamera2 library not available. Using OpenCV for USB camera or mock implementation.")
    PICAMERA_AVAILABLE = False


class CameraHandler:
    """
    Handles Raspberry Pi NoIR Camera v2 operations including:
    - Brightness level detection
    - Motion detection (optional)
    - Frame capture for analysis
    """

    def __init__(self, config: Dict):
        """
        Initialize the camera handler

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Camera configuration
        self.enabled = config.get('sensors', {}).get('camera', {}).get('enabled', True)
        self.resolution = tuple(config.get('sensors', {}).get('camera', {}).get('resolution', [640, 480]))
        self.framerate = config.get('sensors', {}).get('camera', {}).get('framerate', 10)
        self.brightness_sample_rate = config.get('sensors', {}).get('camera', {}).get('brightness_sample_rate', 2)

        # Initialize camera
        self.camera = None
        self.capture_thread = None
        self.running = False
        self.frame_queue = Queue(maxsize=10)

        # Brightness tracking
        self.current_brightness = 128  # Mid-range default
        self.brightness_history = []
        self.brightness_lock = threading.Lock()

        # Callbacks for brightness changes
        self.brightness_callbacks = []

        # Initialize camera based on available hardware
        if self.enabled:
            self._initialize_camera()

    def _initialize_camera(self):
        """Initialize the camera hardware"""
        try:
            if PICAMERA_AVAILABLE:
                # Use Raspberry Pi camera
                self.camera = Picamera2()

                # Configure camera
                camera_config = self.camera.create_still_configuration(
                    main={"size": self.resolution},
                    lores={"size": (320, 240)},
                    display="lores"
                )
                self.camera.configure(camera_config)
                self.camera.start()

                self.logger.info(f"Raspberry Pi camera initialized at {self.resolution}")
            else:
                # Fallback to OpenCV (USB camera or built-in camera)
                self.camera = cv2.VideoCapture(0)

                if self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                    self.camera.set(cv2.CAP_PROP_FPS, self.framerate)
                    self.logger.info(f"OpenCV camera initialized at {self.resolution}")
                else:
                    raise Exception("Failed to open camera with OpenCV")

        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {e}")
            self.enabled = False
            self.camera = None

    def start(self):
        """Start the camera capture thread"""
        if not self.enabled:
            self.logger.warning("Camera is disabled")
            return

        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.capture_thread.start()
        self.logger.info("Camera capture thread started")

    def stop(self):
        """Stop the camera capture thread and release resources"""
        self.running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=5)

        if self.camera:
            try:
                if PICAMERA_AVAILABLE and hasattr(self.camera, 'stop'):
                    self.camera.stop()
                    self.camera.close()
                elif hasattr(self.camera, 'release'):
                    self.camera.release()
            except Exception as e:
                self.logger.error(f"Error stopping camera: {e}")

        self.logger.info("Camera handler stopped")

    def _capture_worker(self):
        """Worker thread for continuous frame capture and brightness analysis"""
        sample_interval = 1.0 / self.brightness_sample_rate
        last_sample_time = 0

        while self.running:
            try:
                current_time = time.time()

                # Capture frame
                frame = self._capture_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                # Add frame to queue for other processing
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)

                # Analyze brightness at sample rate
                if current_time - last_sample_time >= sample_interval:
                    brightness = self._calculate_brightness(frame)
                    self._update_brightness(brightness)
                    last_sample_time = current_time

                # Small delay to prevent CPU overload
                time.sleep(1.0 / self.framerate)

            except Exception as e:
                self.logger.error(f"Camera capture error: {e}")
                time.sleep(1)

    def _capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from the camera

        Returns:
            Numpy array of the captured frame or None if failed
        """
        if not self.camera:
            return None

        try:
            if PICAMERA_AVAILABLE:
                # Capture using Picamera2
                frame = self.camera.capture_array("main")
                # Convert to BGR for OpenCV compatibility
                if len(frame.shape) == 3 and frame.shape[2] == 4:  # RGBA
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                elif len(frame.shape) == 3 and frame.shape[2] == 3:  # RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return frame
            else:
                # Capture using OpenCV
                ret, frame = self.camera.read()
                if ret:
                    return frame
                else:
                    self.logger.warning("Failed to capture frame from OpenCV camera")
                    return None

        except Exception as e:
            self.logger.error(f"Frame capture error: {e}")
            return None

    def _calculate_brightness(self, frame: np.ndarray) -> float:
        """
        Calculate the average brightness of a frame

        Args:
            frame: Input frame as numpy array

        Returns:
            Average brightness value (0-255)
        """
        if frame is None or frame.size == 0:
            return self.current_brightness

        try:
            # Convert to grayscale if needed
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Calculate average brightness
            brightness = np.mean(gray)

            return float(brightness)

        except Exception as e:
            self.logger.error(f"Brightness calculation error: {e}")
            return self.current_brightness

    def _update_brightness(self, brightness: float):
        """
        Update brightness tracking and trigger callbacks if significant change

        Args:
            brightness: New brightness value
        """
        with self.brightness_lock:
            # Store in history (keep last 10 samples)
            self.brightness_history.append(brightness)
            if len(self.brightness_history) > 10:
                self.brightness_history.pop(0)

            # Update current brightness (smoothed)
            if self.brightness_history:
                self.current_brightness = np.mean(self.brightness_history)

            # Check for significant changes
            if len(self.brightness_history) >= 3:
                recent_avg = np.mean(self.brightness_history[-3:])
                older_avg = np.mean(self.brightness_history[:-3]) if len(self.brightness_history) > 3 else recent_avg

                change_threshold = self.config.get('behaviors', {}).get('brightness', {}).get('change_rate', 30)

                if abs(recent_avg - older_avg) > change_threshold:
                    # Trigger callbacks
                    for callback in self.brightness_callbacks:
                        try:
                            callback(self.current_brightness, recent_avg - older_avg)
                        except Exception as e:
                            self.logger.error(f"Brightness callback error: {e}")

    def get_brightness(self) -> float:
        """
        Get current brightness level

        Returns:
            Current brightness value (0-255)
        """
        with self.brightness_lock:
            return self.current_brightness

    def get_brightness_history(self) -> list:
        """
        Get brightness history

        Returns:
            List of recent brightness values
        """
        with self.brightness_lock:
            return self.brightness_history.copy()

    def is_dark(self) -> bool:
        """
        Check if current environment is dark

        Returns:
            True if brightness is below dark threshold
        """
        dark_threshold = self.config.get('behaviors', {}).get('brightness', {}).get('dark_threshold', 50)
        return self.current_brightness < dark_threshold

    def is_bright(self) -> bool:
        """
        Check if current environment is bright

        Returns:
            True if brightness is above bright threshold
        """
        bright_threshold = self.config.get('behaviors', {}).get('brightness', {}).get('bright_threshold', 200)
        return self.current_brightness > bright_threshold

    def register_brightness_callback(self, callback: Callable[[float, float], None]):
        """
        Register a callback for brightness change events

        Args:
            callback: Function to call with (brightness, change) parameters
        """
        self.brightness_callbacks.append(callback)
        self.logger.debug(f"Registered brightness callback: {callback.__name__}")

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Get the latest captured frame

        Args:
            timeout: Maximum time to wait for a frame

        Returns:
            Captured frame or None if timeout
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def capture_image(self, filepath: str) -> bool:
        """
        Capture and save a single image

        Args:
            filepath: Path to save the image

        Returns:
            True if successful
        """
        frame = self._capture_frame()
        if frame is not None:
            try:
                cv2.imwrite(filepath, frame)
                self.logger.info(f"Image saved to {filepath}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to save image: {e}")
                return False
        return False

    def get_camera_info(self) -> Dict:
        """
        Get camera information and status

        Returns:
            Dictionary with camera info
        """
        info = {
            'enabled': self.enabled,
            'resolution': self.resolution,
            'framerate': self.framerate,
            'current_brightness': self.current_brightness,
            'is_dark': self.is_dark(),
            'is_bright': self.is_bright(),
            'camera_type': 'Picamera2' if PICAMERA_AVAILABLE else 'OpenCV',
            'running': self.running
        }

        if self.brightness_history:
            info['avg_brightness'] = np.mean(self.brightness_history)
            info['brightness_std'] = np.std(self.brightness_history)

        return info

    def adjust_exposure(self, compensation: int = 0):
        """
        Adjust camera exposure compensation

        Args:
            compensation: Exposure compensation value (-25 to 25)
        """
        if not self.enabled or not self.camera:
            return

        try:
            if PICAMERA_AVAILABLE:
                # Set exposure compensation for Picamera2
                self.camera.set_controls({"ExposureValue": compensation})
                self.logger.info(f"Exposure compensation set to {compensation}")
            else:
                # OpenCV doesn't have direct exposure compensation
                # But we can try to adjust exposure time if supported
                if self.camera.set(cv2.CAP_PROP_EXPOSURE, compensation):
                    self.logger.info(f"Exposure adjusted to {compensation}")
                else:
                    self.logger.warning("Exposure adjustment not supported on this camera")
        except Exception as e:
            self.logger.error(f"Failed to adjust exposure: {e}")

    def enable_night_mode(self, enabled: bool = True):
        """
        Enable or disable night mode for NoIR camera

        Args:
            enabled: True to enable night mode
        """
        if not self.enabled or not self.camera:
            return

        try:
            if PICAMERA_AVAILABLE:
                if enabled:
                    # Adjust for low light conditions
                    self.camera.set_controls({
                        "AnalogueGain": 8.0,
                        "ExposureTime": 40000,
                        "AeEnable": False
                    })
                    self.logger.info("Night mode enabled")
                else:
                    # Return to auto mode
                    self.camera.set_controls({
                        "AeEnable": True
                    })
                    self.logger.info("Night mode disabled")
            else:
                self.logger.warning("Night mode not available for OpenCV camera")
        except Exception as e:
            self.logger.error(f"Failed to set night mode: {e}")