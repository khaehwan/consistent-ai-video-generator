"""
LED Display Module - Complete Redesign
8x8 LED 매트릭스를 효율적으로 사용하여 모든 센서 상태를 동시에 표시

Layout Design:
  0 1 2 3 4 5 6 7
0 C C C C C C C C  (C = Compass edge)
1 C M M M T T T C
2 C M M M T T T C
3 C M M M T T T C
4 C S S S B B B C
5 C S S S B B B C
6 C S S S B B B C
7 C C C C C C C C

M = Movement (3x3) - Stop/Walk/Run icons
T = Turn/Fall (3x3) - Fall status + Turn status
S = Shout (3x3) - Shout wave pattern
B = Brightness (3x3) - Bar graph
C = Compass - Blue dot tracking North on edge
"""

import logging
import threading
import time
from typing import Dict, List, Optional


class LEDDisplay:
    """
    8x8 LED 매트릭스 디스플레이 관리
    모든 센서 상태를 4개 영역으로 분할하여 동시 표시
    """

    # 색상 정의
    OFF = [0, 0, 0]

    # Movement colors
    COLOR_STOP = [0, 255, 0]        # Green
    COLOR_WALK = [255, 255, 0]      # Yellow
    COLOR_RUN = [255, 100, 0]       # Orange

    # Fall colors
    COLOR_FALL = [255, 0, 0]        # Red
    COLOR_NO_FALL = [0, 50, 0]      # Dark green

    # Turn colors
    COLOR_TURN_LEFT = [255, 100, 0]   # Orange (left)
    COLOR_TURN_RIGHT = [0, 255, 255]  # Cyan (right)
    COLOR_NO_TURN = [0, 0, 50]        # Dark blue

    # Shout colors
    COLOR_SHOUT = [255, 0, 255]     # Magenta
    COLOR_NO_SHOUT = [30, 0, 30]    # Dark purple

    # Brightness colors (for graph)
    COLOR_BRIGHT_LOW = [0, 0, 255]      # Blue (dark)
    COLOR_BRIGHT_MED = [0, 255, 0]      # Green (normal)
    COLOR_BRIGHT_HIGH = [255, 255, 0]   # Yellow (bright)

    # Compass color
    COLOR_COMPASS = [0, 0, 255]     # Blue

    # System colors
    COLOR_READY = [0, 255, 255]     # Cyan
    COLOR_CALIBRATING = [255, 255, 0]  # Yellow
    COLOR_COMPLETE = [0, 255, 0]    # Green

    def __init__(self, sense_hat_handler):
        """
        Initialize LED display

        Args:
            sense_hat_handler: Reference to SenseHatHandler
        """
        self.sense_hat = sense_hat_handler
        self.logger = logging.getLogger(__name__)

        # Current states
        self.states = {
            'movement': 'stop',      # stop, walk, run
            'fall': False,           # True/False
            'turn': None,            # None, 'left', 'right'
            'shout': False,          # True/False
            'brightness_level': 0.5, # 0.0-1.0 (0=dark, 0.5=normal, 1.0=bright)
            'compass': 0.0,          # Heading in degrees (0-360)
        }

        # LED edge positions (clockwise from top-left)
        # Same as official Sense HAT compass example
        self.led_edge = [4, 5, 6, 7, 15, 23, 31, 39, 47, 55, 63, 62, 61, 60, 59, 58, 57, 56, 48, 40, 32, 24, 16, 8, 0, 1, 2, 3]
        self.led_degree_ratio = len(self.led_edge) / 360.0

        # Movement icons (3x3)
        self.ICON_STOP = [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0]
        ]

        self.ICON_WALK = [
            [0, 1, 0],
            [1, 1, 1],
            [1, 0, 1]
        ]

        self.ICON_RUN = [
            [1, 1, 1],
            [1, 1, 1],
            [1, 0, 1]
        ]

        # Fall icon (3x2 top half)
        self.ICON_FALL = [
            [1, 0, 1],
            [0, 1, 0]
        ]

        self.ICON_NO_FALL = [
            [0, 1, 0],
            [1, 0, 1]
        ]

        # Turn icon (3x1 bottom half) - direction arrows
        self.ICON_TURN_LEFT = [
            [0, 1, 1]  # Arrow pointing left
        ]

        self.ICON_TURN_RIGHT = [
            [1, 1, 0]  # Arrow pointing right
        ]

        self.ICON_NO_TURN = [
            [0, 0, 0]
        ]

        # Shout wave pattern (3x3)
        self.ICON_SHOUT = [
            [0, 1, 0],
            [1, 0, 1],
            [0, 1, 0]
        ]

        self.ICON_NO_SHOUT = [
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0]
        ]

        # Update control
        self.running = False
        self.update_thread = None
        self.update_interval = 0.05  # 20 Hz

        # Lock for thread-safe state updates
        self.state_lock = threading.Lock()

        # Pause flag for animations
        self.paused = False

        self.logger.info("LED Display initialized")

    def start(self):
        """Start LED display update thread"""
        if not self.sense_hat or not self.sense_hat.enabled:
            self.logger.warning("Sense HAT not available")
            return

        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("LED Display started")

    def stop(self):
        """Stop LED display"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1)

        if self.sense_hat and self.sense_hat.sense:
            self.sense_hat.sense.clear()

        self.logger.info("LED Display stopped")

    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                # Skip update if paused (during animations)
                if self.paused:
                    time.sleep(0.1)
                    continue

                # Generate display
                pixels = self._generate_display()

                # Update LED matrix
                if self.sense_hat and self.sense_hat.sense:
                    self.sense_hat.sense.set_pixels(pixels)

                time.sleep(self.update_interval)

            except Exception as e:
                self.logger.error(f"Display update error: {e}")
                time.sleep(1)

    def _generate_display(self) -> List:
        """
        Generate 64-pixel array for LED display

        Returns:
            List of 64 RGB values
        """
        # Initialize all pixels to off
        pixels = [self.OFF[:] for _ in range(64)]

        with self.state_lock:
            # Draw regions first
            # Region 1: Movement (rows 1-3, cols 1-3)
            self._draw_movement(pixels)

            # Region 2: Turn/Fall (rows 1-3, cols 4-6)
            self._draw_turn_fall(pixels)

            # Region 3: Shout (rows 4-6, cols 1-3)
            self._draw_shout(pixels)

            # Region 4: Brightness (rows 4-6, cols 4-6)
            self._draw_brightness(pixels)

            # Draw compass LAST so it's always visible on top of other elements
            heading = self.states['compass']
            dir_inverted = 360 - heading
            led_index = int(self.led_degree_ratio * dir_inverted) % len(self.led_edge)
            compass_offset = self.led_edge[led_index]

            # Only draw compass on edge pixels (row 0, 7 or col 0, 7)
            # This prevents compass from overwriting content areas
            compass_row = compass_offset // 8
            compass_col = compass_offset % 8
            if compass_row == 0 or compass_row == 7 or compass_col == 0 or compass_col == 7:
                pixels[compass_offset] = self.COLOR_COMPASS[:]

        return pixels

    def _draw_movement(self, pixels: List):
        """Draw movement icon (3x3 region at rows 1-3, cols 1-3)"""
        movement = self.states['movement']

        # Select icon and color
        if movement == 'stop':
            icon = self.ICON_STOP
            color = self.COLOR_STOP
        elif movement == 'walk':
            icon = self.ICON_WALK
            color = self.COLOR_WALK
        else:  # run
            icon = self.ICON_RUN
            color = self.COLOR_RUN

        # Draw 3x3 icon
        for row in range(3):
            for col in range(3):
                if icon[row][col]:
                    pixel_idx = (row + 1) * 8 + (col + 1)
                    pixels[pixel_idx] = color[:]

    def _draw_turn_fall(self, pixels: List):
        """Draw turn/fall status (3x3 region at rows 1-3, cols 4-6)"""
        fall = self.states['fall']
        turn = self.states['turn']

        # Top 2 rows: Fall status
        fall_icon = self.ICON_FALL if fall else self.ICON_NO_FALL
        fall_color = self.COLOR_FALL if fall else self.COLOR_NO_FALL

        for row in range(2):
            for col in range(3):
                if fall_icon[row][col]:
                    pixel_idx = (row + 1) * 8 + (col + 4)
                    pixels[pixel_idx] = fall_color[:]

        # Bottom row: Turn status with direction
        if turn == 'left':
            turn_icon = self.ICON_TURN_LEFT
            turn_color = self.COLOR_TURN_LEFT
        elif turn == 'right':
            turn_icon = self.ICON_TURN_RIGHT
            turn_color = self.COLOR_TURN_RIGHT
        else:
            turn_icon = self.ICON_NO_TURN
            turn_color = self.COLOR_NO_TURN

        for col in range(3):
            if turn_icon[0][col]:
                pixel_idx = 3 * 8 + (col + 4)
                pixels[pixel_idx] = turn_color[:]

    def _draw_shout(self, pixels: List):
        """Draw shout wave pattern (3x3 region at rows 4-6, cols 1-3)"""
        shout = self.states['shout']

        icon = self.ICON_SHOUT if shout else self.ICON_NO_SHOUT
        color = self.COLOR_SHOUT if shout else self.COLOR_NO_SHOUT

        for row in range(3):
            for col in range(3):
                if icon[row][col]:
                    pixel_idx = (row + 4) * 8 + (col + 1)
                    pixels[pixel_idx] = color[:]

    def _draw_brightness(self, pixels: List):
        """Draw brightness bar graph (3x3 region at rows 4-6, cols 4-6)"""
        brightness = self.states['brightness_level']

        # 3 vertical bars (each 1x3)
        # Bar positions: col 4, col 5, col 6
        # Each bar is 3 pixels tall (rows 4, 5, 6)

        # Determine how many bars to light based on brightness level
        if brightness < 0.33:
            # Dark: 1 bar (blue)
            bars = [self.COLOR_BRIGHT_LOW, self.OFF, self.OFF]
        elif brightness < 0.67:
            # Normal: 2 bars (blue + green)
            bars = [self.COLOR_BRIGHT_LOW, self.COLOR_BRIGHT_MED, self.OFF]
        else:
            # Bright: 3 bars (blue + green + yellow)
            bars = [self.COLOR_BRIGHT_LOW, self.COLOR_BRIGHT_MED, self.COLOR_BRIGHT_HIGH]

        # Draw bars (bottom to top)
        for col_offset, bar_color in enumerate(bars):
            col = 4 + col_offset
            for row in range(4, 7):  # rows 4, 5, 6
                pixel_idx = row * 8 + col
                pixels[pixel_idx] = bar_color[:]

    # State update methods

    def update_movement(self, state: str):
        """
        Update movement state

        Args:
            state: stop, walk, or run
        """
        with self.state_lock:
            self.states['movement'] = state

    def update_fall(self, is_fallen: bool):
        """Update fall state"""
        with self.state_lock:
            self.states['fall'] = is_fallen

    def update_turn(self, direction: str = None):
        """
        Update turn state with direction

        Args:
            direction: None (no turn), 'left', or 'right'
        """
        with self.state_lock:
            self.states['turn'] = direction

    def update_shout(self, is_shouting: bool):
        """Update shout state"""
        with self.state_lock:
            self.states['shout'] = is_shouting

    def update_brightness(self, level: float):
        """
        Update brightness level

        Args:
            level: 0.0-1.0 (0=dark, 0.5=normal, 1.0=bright)
        """
        with self.state_lock:
            self.states['brightness_level'] = max(0.0, min(1.0, level))

    def update_compass(self, heading: float):
        """
        Update compass heading

        Args:
            heading: Heading in degrees (0-360)
        """
        with self.state_lock:
            self.states['compass'] = heading

    # Animation methods

    def show_ready(self):
        """Show READY message on startup"""
        if not self.sense_hat or not self.sense_hat.sense:
            return

        self.paused = True

        # Show "READY" text
        self.sense_hat.sense.show_message(
            "READY",
            text_colour=self.COLOR_READY,
            scroll_speed=0.05
        )

        self.paused = False

    def show_startup_animation(self):
        """Show startup animation - test each region"""
        if not self.sense_hat or not self.sense_hat.sense:
            return

        self.paused = True

        # Test sequence - light up each region one by one
        test_frames = [
            # Frame 1: Movement region (green)
            self._create_test_frame([(1,1), (1,2), (1,3), (2,1), (2,2), (2,3), (3,1), (3,2), (3,3)], self.COLOR_STOP),

            # Frame 2: Turn/Fall region (red/cyan)
            self._create_test_frame([(1,4), (1,5), (1,6), (2,4), (2,5), (2,6), (3,4), (3,5), (3,6)], self.COLOR_FALL),

            # Frame 3: Shout region (magenta)
            self._create_test_frame([(4,1), (4,2), (4,3), (5,1), (5,2), (5,3), (6,1), (6,2), (6,3)], self.COLOR_SHOUT),

            # Frame 4: Brightness region (yellow)
            self._create_test_frame([(4,4), (4,5), (4,6), (5,4), (5,5), (5,6), (6,4), (6,5), (6,6)], self.COLOR_BRIGHT_HIGH),

            # Frame 5: Compass edge (blue)
            self._create_compass_test_frame(),
        ]

        for frame in test_frames:
            self.sense_hat.sense.set_pixels(frame)
            time.sleep(0.2)

        # Clear
        self.sense_hat.sense.clear()
        time.sleep(0.1)

        self.paused = False

    def _create_test_frame(self, positions: List, color: List) -> List:
        """Create test frame with specific positions lit"""
        pixels = [self.OFF[:] for _ in range(64)]
        for row, col in positions:
            pixels[row * 8 + col] = color[:]
        return pixels

    def _create_compass_test_frame(self) -> List:
        """Create test frame showing compass edge"""
        pixels = [self.OFF[:] for _ in range(64)]
        # Light up all edge pixels
        for offset in self.led_edge:
            pixels[offset] = self.COLOR_COMPASS[:]
        return pixels

    def show_calibration_complete(self):
        """Show calibration complete animation"""
        if not self.sense_hat or not self.sense_hat.sense:
            return

        self.paused = True

        # Define check mark pattern (✓)
        G = self.COLOR_COMPLETE
        O = self.OFF

        check_pattern = [
            O, O, O, O, O, O, O, G,
            O, O, O, O, O, O, G, G,
            O, O, O, O, O, G, G, O,
            G, O, O, O, G, G, O, O,
            G, G, O, G, G, O, O, O,
            O, G, G, G, O, O, O, O,
            O, O, G, O, O, O, O, O,
            O, O, O, O, O, O, O, O
        ]

        # Animation sequence
        # 1. Flash yellow 2 times (calibrating)
        for _ in range(2):
            self.sense_hat.sense.set_pixels([self.COLOR_CALIBRATING[:] for _ in range(64)])
            time.sleep(0.1)
            self.sense_hat.sense.clear()
            time.sleep(0.1)

        # 2. Show green check mark (complete)
        self.sense_hat.sense.set_pixels(check_pattern)
        time.sleep(1.0)

        # 3. Fade out effect
        for brightness_factor in [0.8, 0.6, 0.4, 0.2, 0.0]:
            dimmed_pattern = []
            for pixel in check_pattern:
                if pixel == G:
                    dimmed_pattern.append([int(c * brightness_factor) for c in G])
                else:
                    dimmed_pattern.append(O[:])
            self.sense_hat.sense.set_pixels(dimmed_pattern)
            time.sleep(0.05)

        # 4. Clear display
        self.sense_hat.sense.clear()
        time.sleep(0.1)

        self.paused = False

    def flash_event(self, event_type: str, duration: float = 1.0, direction: str = None):
        """
        Flash an event indicator

        Args:
            event_type: fall, turn, or shout
            duration: Flash duration in seconds
            direction: For turn events, 'left' or 'right'
        """
        if event_type == 'fall':
            self.logger.info(f"LED flash_event: FALL - setting to True for {duration}s")
            self.update_fall(True)
            threading.Timer(duration, lambda: self.update_fall(False)).start()
            self.logger.debug(f"LED fall state: {self.states['fall']}")
        elif event_type == 'turn':
            self.logger.info(f"LED flash_event: TURN {direction} - setting for {duration}s")
            self.update_turn(direction)  # 'left' or 'right'
            threading.Timer(duration, lambda: self.update_turn(None)).start()
        elif event_type == 'shout':
            self.logger.info(f"LED flash_event: SHOUT - setting to True for {duration}s")
            self.update_shout(True)
            threading.Timer(duration, lambda: self.update_shout(False)).start()

    def get_states(self) -> Dict:
        """
        Get current display states

        Returns:
            Dictionary of current states
        """
        with self.state_lock:
            return self.states.copy()
