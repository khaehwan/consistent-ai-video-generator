"""
Microphone Handler Module
Manages USB microphone for sound detection and audio analysis
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, Optional, Callable, List, Tuple
from queue import Queue, Empty
import struct
import math

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    logging.warning("PyAudio library not available. Using mock implementation.")
    PYAUDIO_AVAILABLE = False


class MicrophoneHandler:
    """
    Handles USB microphone operations including:
    - Sound level detection
    - Shout/loud noise detection
    - Frequency analysis
    - Audio recording (optional)
    """

    def __init__(self, config: Dict):
        """
        Initialize the microphone handler

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Microphone configuration
        self.enabled = config.get('sensors', {}).get('microphone', {}).get('enabled', True)
        self.sample_rate = config.get('sensors', {}).get('microphone', {}).get('sample_rate', 44100)
        self.chunk_size = config.get('sensors', {}).get('microphone', {}).get('chunk_size', 1024)
        self.channels = config.get('sensors', {}).get('microphone', {}).get('channels', 1)
        self.audio_format = getattr(pyaudio, 'paInt16', 8) if PYAUDIO_AVAILABLE else 8

        # Audio processing
        self.audio = None
        self.stream = None
        self.capture_thread = None
        self.running = False
        self.audio_queue = Queue(maxsize=10)

        # Sound level tracking
        self.current_volume = 0.0  # Current volume in dB
        self.volume_history = []
        self.peak_volume = 0.0
        self.volume_lock = threading.Lock()

        # Shout detection parameters
        self.shout_threshold = config.get('behaviors', {}).get('shout', {}).get('volume_threshold', 70)
        self.shout_duration_min = config.get('behaviors', {}).get('shout', {}).get('duration_min', 500) / 1000.0
        self.shout_frequency_range = config.get('behaviors', {}).get('shout', {}).get('frequency_range', [200, 2000])

        # Callbacks for sound events
        self.volume_callbacks = []
        self.shout_callbacks = []

        # Shout detection state
        self.shout_start_time = None
        self.is_shouting = False

        # Initialize audio system
        if self.enabled:
            self._initialize_audio()

    def _initialize_audio(self):
        """Initialize the audio system and microphone"""
        if not PYAUDIO_AVAILABLE:
            self.logger.warning("PyAudio not available. Microphone disabled.")
            self.enabled = False
            return

        try:
            self.audio = pyaudio.PyAudio()

            # Find USB microphone or use default input
            device_index = self._find_usb_microphone()

            # Open audio stream
            self.stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )

            self.logger.info(f"Microphone initialized: {self.sample_rate}Hz, {self.channels} channel(s)")

        except Exception as e:
            self.logger.error(f"Failed to initialize microphone: {e}")
            self.enabled = False
            self.audio = None
            self.stream = None

    def _find_usb_microphone(self) -> Optional[int]:
        """
        Find USB microphone device index

        Returns:
            Device index or None for default
        """
        if not self.audio:
            return None

        try:
            # List all audio devices
            device_count = self.audio.get_device_count()

            for i in range(device_count):
                info = self.audio.get_device_info_by_index(i)

                # Check if it's an input device
                if info['maxInputChannels'] > 0:
                    name = info['name'].lower()

                    # Look for USB microphone keywords
                    if any(keyword in name for keyword in ['usb', 'microphone', 'mic', 'audio']):
                        self.logger.info(f"Found USB microphone: {info['name']} (index {i})")
                        return i

            # No USB microphone found, use default
            default_info = self.audio.get_default_input_device_info()
            self.logger.info(f"Using default microphone: {default_info['name']}")
            return None

        except Exception as e:
            self.logger.error(f"Error finding USB microphone: {e}")
            return None

    def start(self):
        """Start the audio capture thread"""
        if not self.enabled or not self.stream:
            self.logger.warning("Microphone is disabled or not initialized")
            return

        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.capture_thread.start()
        self.logger.info("Microphone capture thread started")

    def stop(self):
        """Stop the audio capture thread and release resources"""
        self.running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=5)

        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                self.logger.error(f"Error stopping audio stream: {e}")

        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                self.logger.error(f"Error terminating PyAudio: {e}")

        self.logger.info("Microphone handler stopped")

    def _capture_worker(self):
        """Worker thread for continuous audio capture and analysis"""
        while self.running:
            try:
                # Read audio chunk
                audio_data = self._read_audio_chunk()
                if audio_data is None:
                    time.sleep(0.01)
                    continue

                # Calculate volume
                volume = self._calculate_volume(audio_data)
                self._update_volume(volume)

                # Check for shouting
                self._check_shout(volume, audio_data)

                # Add to queue for other processing
                if not self.audio_queue.full():
                    self.audio_queue.put({
                        'data': audio_data,
                        'volume': volume,
                        'timestamp': time.time()
                    })

            except Exception as e:
                self.logger.error(f"Audio capture error: {e}")
                time.sleep(0.1)

    def _read_audio_chunk(self) -> Optional[np.ndarray]:
        """
        Read a chunk of audio data from the microphone

        Returns:
            Numpy array of audio samples or None if failed
        """
        if not self.stream:
            return None

        try:
            # Read raw audio data
            raw_data = self.stream.read(self.chunk_size, exception_on_overflow=False)

            # Convert to numpy array
            audio_data = np.frombuffer(raw_data, dtype=np.int16)

            # Normalize to float32 (-1.0 to 1.0)
            audio_data = audio_data.astype(np.float32) / 32768.0

            return audio_data

        except Exception as e:
            self.logger.error(f"Audio read error: {e}")
            return None

    def _calculate_volume(self, audio_data: np.ndarray) -> float:
        """
        Calculate volume level in decibels

        Args:
            audio_data: Audio samples as numpy array

        Returns:
            Volume level in dB
        """
        if audio_data is None or len(audio_data) == 0:
            return self.current_volume

        try:
            # Calculate RMS (Root Mean Square)
            rms = np.sqrt(np.mean(audio_data ** 2))

            # Convert to decibels
            if rms > 0:
                db = 20 * np.log10(rms)
                # Normalize to 0-100 scale (approximately)
                db = max(0, db + 100)
            else:
                db = 0

            return float(db)

        except Exception as e:
            self.logger.error(f"Volume calculation error: {e}")
            return self.current_volume

    def _update_volume(self, volume: float):
        """
        Update volume tracking

        Args:
            volume: New volume value in dB
        """
        with self.volume_lock:
            # Update current volume
            self.current_volume = volume

            # Store in history (keep last 50 samples)
            self.volume_history.append(volume)
            if len(self.volume_history) > 50:
                self.volume_history.pop(0)

            # Update peak volume
            if volume > self.peak_volume:
                self.peak_volume = volume

            # Trigger volume callbacks
            for callback in self.volume_callbacks:
                try:
                    callback(volume)
                except Exception as e:
                    self.logger.error(f"Volume callback error: {e}")

    def _check_shout(self, volume: float, audio_data: np.ndarray):
        """
        Check if shouting is detected

        Args:
            volume: Current volume level
            audio_data: Audio samples for frequency analysis
        """
        current_time = time.time()

        # Check if volume exceeds shout threshold
        if volume >= self.shout_threshold:
            # Check frequency content (human voice range)
            if self._is_human_voice_frequency(audio_data):
                if not self.is_shouting:
                    # Start of shout detected
                    self.shout_start_time = current_time
                    self.is_shouting = True
                    self.logger.debug(f"Shout started at volume {volume:.1f} dB")

                # Check if shout duration is sufficient
                elif current_time - self.shout_start_time >= self.shout_duration_min:
                    # Valid shout detected
                    self.logger.info(f"Shout detected! Volume: {volume:.1f} dB, Duration: {current_time - self.shout_start_time:.2f}s")

                    # Trigger shout callbacks
                    for callback in self.shout_callbacks:
                        try:
                            callback(volume, current_time - self.shout_start_time)
                        except Exception as e:
                            self.logger.error(f"Shout callback error: {e}")

                    # Reset after callback to avoid repeated triggers
                    self.shout_start_time = current_time

        else:
            # Volume below threshold
            if self.is_shouting:
                duration = current_time - self.shout_start_time
                self.logger.debug(f"Shout ended. Duration: {duration:.2f}s")
                self.is_shouting = False
                self.shout_start_time = None

    def _is_human_voice_frequency(self, audio_data: np.ndarray) -> bool:
        """
        Check if audio contains frequencies in human voice range

        Args:
            audio_data: Audio samples

        Returns:
            True if human voice frequencies detected
        """
        try:
            # Perform FFT
            fft = np.fft.rfft(audio_data)
            frequencies = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
            magnitude = np.abs(fft)

            # Find dominant frequencies
            min_freq, max_freq = self.shout_frequency_range

            # Get frequencies in voice range
            voice_mask = (frequencies >= min_freq) & (frequencies <= max_freq)
            voice_magnitude = magnitude[voice_mask]

            if len(voice_magnitude) > 0:
                # Check if significant energy in voice range
                voice_energy = np.mean(voice_magnitude)
                total_energy = np.mean(magnitude)

                # Voice should have significant portion of energy
                return voice_energy > (total_energy * 0.3)

            return False

        except Exception as e:
            self.logger.error(f"Frequency analysis error: {e}")
            return True  # Assume voice on error

    def get_volume(self) -> float:
        """
        Get current volume level

        Returns:
            Current volume in dB
        """
        with self.volume_lock:
            return self.current_volume

    def get_volume_history(self) -> List[float]:
        """
        Get volume history

        Returns:
            List of recent volume values
        """
        with self.volume_lock:
            return self.volume_history.copy()

    def get_average_volume(self, duration: float = 1.0) -> float:
        """
        Get average volume over specified duration

        Args:
            duration: Time period in seconds

        Returns:
            Average volume in dB
        """
        with self.volume_lock:
            if not self.volume_history:
                return 0.0

            # Calculate how many samples to average
            samples_per_second = self.sample_rate / self.chunk_size
            num_samples = min(int(samples_per_second * duration), len(self.volume_history))

            if num_samples > 0:
                recent_samples = self.volume_history[-num_samples:]
                return np.mean(recent_samples)

            return self.current_volume

    def is_loud(self) -> bool:
        """
        Check if current sound level is loud

        Returns:
            True if volume exceeds shout threshold
        """
        return self.current_volume >= self.shout_threshold

    def is_quiet(self) -> bool:
        """
        Check if environment is quiet

        Returns:
            True if volume is below 30 dB
        """
        return self.current_volume < 30

    def register_volume_callback(self, callback: Callable[[float], None]):
        """
        Register a callback for volume change events

        Args:
            callback: Function to call with volume parameter
        """
        self.volume_callbacks.append(callback)
        self.logger.debug(f"Registered volume callback: {callback.__name__}")

    def register_shout_callback(self, callback: Callable[[float, float], None]):
        """
        Register a callback for shout detection events

        Args:
            callback: Function to call with (volume, duration) parameters
        """
        self.shout_callbacks.append(callback)
        self.logger.debug(f"Registered shout callback: {callback.__name__}")

    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[Dict]:
        """
        Get the latest audio chunk with metadata

        Args:
            timeout: Maximum time to wait

        Returns:
            Dictionary with audio data, volume, and timestamp
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_microphone_info(self) -> Dict:
        """
        Get microphone information and status

        Returns:
            Dictionary with microphone info
        """
        info = {
            'enabled': self.enabled,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_size': self.chunk_size,
            'current_volume': self.current_volume,
            'peak_volume': self.peak_volume,
            'is_loud': self.is_loud(),
            'is_quiet': self.is_quiet(),
            'is_shouting': self.is_shouting,
            'running': self.running
        }

        if self.volume_history:
            info['avg_volume'] = np.mean(self.volume_history)
            info['volume_std'] = np.std(self.volume_history)

        if self.audio and PYAUDIO_AVAILABLE:
            try:
                default_device = self.audio.get_default_input_device_info()
                info['device_name'] = default_device.get('name', 'Unknown')
            except:
                info['device_name'] = 'Unknown'

        return info

    def calibrate_noise_floor(self, duration: float = 3.0) -> float:
        """
        Calibrate the noise floor by sampling ambient noise

        Args:
            duration: Calibration duration in seconds

        Returns:
            Average noise floor in dB
        """
        if not self.enabled:
            return 0.0

        self.logger.info(f"Calibrating noise floor for {duration} seconds...")

        start_time = time.time()
        samples = []

        while time.time() - start_time < duration:
            samples.append(self.current_volume)
            time.sleep(0.1)

        if samples:
            noise_floor = np.mean(samples)
            self.logger.info(f"Noise floor calibrated: {noise_floor:.1f} dB")

            # Adjust shout threshold based on noise floor
            self.shout_threshold = max(noise_floor + 20, self.shout_threshold)
            self.logger.info(f"Shout threshold adjusted to: {self.shout_threshold:.1f} dB")

            return noise_floor

        return 0.0

    def reset_peak_volume(self):
        """Reset the peak volume tracker"""
        with self.volume_lock:
            self.peak_volume = self.current_volume
            self.logger.debug("Peak volume reset")