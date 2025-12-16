"""
Display Utilities Module
Provides display helpers and patterns for Sense HAT LED matrix
"""

import time
from typing import List, Tuple, Optional


class DisplayPatterns:
    """
    Predefined display patterns for behaviors
    """

    # Color definitions
    COLORS = {
        'red': [255, 0, 0],
        'green': [0, 255, 0],
        'blue': [0, 0, 255],
        'yellow': [255, 255, 0],
        'cyan': [0, 255, 255],
        'magenta': [255, 0, 255],
        'white': [255, 255, 255],
        'orange': [255, 128, 0],
        'purple': [128, 0, 255],
        'gray': [64, 64, 64],
        'black': [0, 0, 0]
    }

    @staticmethod
    def get_arrow_up() -> List:
        """Get up arrow pattern"""
        W = DisplayPatterns.COLORS['white']
        O = DisplayPatterns.COLORS['black']
        return [
            O, O, O, W, W, O, O, O,
            O, O, W, W, W, W, O, O,
            O, W, W, W, W, W, W, O,
            W, O, O, W, W, O, O, W,
            O, O, O, W, W, O, O, O,
            O, O, O, W, W, O, O, O,
            O, O, O, W, W, O, O, O,
            O, O, O, W, W, O, O, O,
        ]

    @staticmethod
    def get_arrow_down() -> List:
        """Get down arrow pattern"""
        W = DisplayPatterns.COLORS['white']
        O = DisplayPatterns.COLORS['black']
        return [
            O, O, O, W, W, O, O, O,
            O, O, O, W, W, O, O, O,
            O, O, O, W, W, O, O, O,
            O, O, O, W, W, O, O, O,
            W, O, O, W, W, O, O, W,
            O, W, W, W, W, W, W, O,
            O, O, W, W, W, W, O, O,
            O, O, O, W, W, O, O, O,
        ]

    @staticmethod
    def get_checkmark() -> List:
        """Get checkmark pattern"""
        G = DisplayPatterns.COLORS['green']
        O = DisplayPatterns.COLORS['black']
        return [
            O, O, O, O, O, O, O, O,
            O, O, O, O, O, O, O, G,
            O, O, O, O, O, O, G, G,
            O, O, O, O, O, G, G, O,
            G, O, O, O, G, G, O, O,
            G, G, O, G, G, O, O, O,
            O, G, G, G, O, O, O, O,
            O, O, G, O, O, O, O, O,
        ]

    @staticmethod
    def get_cross() -> List:
        """Get X/cross pattern"""
        R = DisplayPatterns.COLORS['red']
        O = DisplayPatterns.COLORS['black']
        return [
            R, R, O, O, O, O, R, R,
            R, R, R, O, O, R, R, R,
            O, R, R, R, R, R, R, O,
            O, O, R, R, R, R, O, O,
            O, O, R, R, R, R, O, O,
            O, R, R, R, R, R, R, O,
            R, R, R, O, O, R, R, R,
            R, R, O, O, O, O, R, R,
        ]

    @staticmethod
    def get_heart() -> List:
        """Get heart pattern"""
        R = DisplayPatterns.COLORS['red']
        O = DisplayPatterns.COLORS['black']
        return [
            O, R, R, O, O, R, R, O,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            O, R, R, R, R, R, R, O,
            O, O, R, R, R, R, O, O,
            O, O, O, R, R, O, O, O,
            O, O, O, O, O, O, O, O,
        ]

    @staticmethod
    def get_smiley() -> List:
        """Get smiley face pattern"""
        Y = DisplayPatterns.COLORS['yellow']
        O = DisplayPatterns.COLORS['black']
        return [
            O, O, Y, Y, Y, Y, O, O,
            O, Y, Y, Y, Y, Y, Y, O,
            Y, Y, O, Y, Y, O, Y, Y,
            Y, Y, Y, Y, Y, Y, Y, Y,
            Y, Y, Y, Y, Y, Y, Y, Y,
            Y, O, Y, Y, Y, Y, O, Y,
            O, Y, O, Y, Y, O, Y, O,
            O, O, Y, Y, Y, Y, O, O,
        ]

    @staticmethod
    def get_warning() -> List:
        """Get warning triangle pattern"""
        Y = DisplayPatterns.COLORS['yellow']
        B = DisplayPatterns.COLORS['black']
        O = DisplayPatterns.COLORS['orange']
        return [
            B, B, B, O, O, B, B, B,
            B, B, O, Y, Y, O, B, B,
            B, B, O, Y, Y, O, B, B,
            B, O, Y, Y, Y, Y, O, B,
            B, O, Y, O, O, Y, O, B,
            O, Y, Y, Y, Y, Y, Y, O,
            O, Y, Y, O, O, Y, Y, O,
            O, O, O, O, O, O, O, O,
        ]

    @staticmethod
    def get_loading_frame(frame: int) -> List:
        """
        Get loading animation frame

        Args:
            frame: Frame number (0-7)

        Returns:
            Pattern for the frame
        """
        C = DisplayPatterns.COLORS['cyan']
        O = DisplayPatterns.COLORS['black']

        # Create rotating loading pattern
        patterns = []
        for i in range(8):
            pattern = [O] * 64

            # Light up segments in sequence
            positions = [
                [3, 2], [4, 2], [5, 3], [5, 4],  # Top and right
                [5, 5], [4, 5], [3, 5], [2, 5],  # Bottom and left
                [2, 4], [2, 3]  # Complete circle
            ]

            # Light up based on frame
            for j in range(3):
                pos_idx = (frame + j) % len(positions)
                x, y = positions[pos_idx]
                pattern[y * 8 + x] = C

            patterns.append(pattern)

        return patterns[frame % 8]


class AnimationController:
    """
    Controls animations on Sense HAT display
    """

    def __init__(self, sense_hat_handler):
        """
        Initialize animation controller

        Args:
            sense_hat_handler: Reference to SenseHatHandler
        """
        self.sense_hat = sense_hat_handler
        self.running = False
        self.current_animation = None

    def pulse_color(self, color: List[int], duration: float = 2.0, steps: int = 20):
        """
        Pulse a color on the display

        Args:
            color: RGB color to pulse
            duration: Total duration of pulse
            steps: Number of brightness steps
        """
        if not self.sense_hat.enabled:
            return

        step_duration = duration / steps

        for i in range(steps):
            # Calculate brightness (0 to 1 and back)
            if i < steps / 2:
                brightness = i / (steps / 2)
            else:
                brightness = 2 - (i / (steps / 2))

            # Apply brightness to color
            current_color = [int(c * brightness) for c in color]

            # Create solid color pattern
            pattern = [current_color] * 64

            self.sense_hat.show_pattern(pattern)
            time.sleep(step_duration)

        self.sense_hat.clear_display()

    def scroll_text(self, text: str, color: List[int] = None, speed: float = 0.1):
        """
        Scroll text across display

        Args:
            text: Text to scroll
            color: Text color
            speed: Scroll speed
        """
        if not self.sense_hat.enabled:
            return

        color = color or DisplayPatterns.COLORS['white']
        self.sense_hat.show_text(text, color=color)

    def flash_pattern(self, pattern: List, count: int = 3, interval: float = 0.5):
        """
        Flash a pattern on the display

        Args:
            pattern: Pattern to flash
            count: Number of flashes
            interval: Time between flashes
        """
        if not self.sense_hat.enabled:
            return

        for _ in range(count):
            self.sense_hat.show_pattern(pattern)
            time.sleep(interval / 2)
            self.sense_hat.clear_display()
            time.sleep(interval / 2)

    def loading_animation(self, duration: float = 3.0):
        """
        Show loading animation

        Args:
            duration: Duration of animation
        """
        if not self.sense_hat.enabled:
            return

        frames = 8
        frame_duration = duration / (duration * 10)  # 10 fps

        start_time = time.time()
        frame = 0

        while time.time() - start_time < duration:
            pattern = DisplayPatterns.get_loading_frame(frame)
            self.sense_hat.show_pattern(pattern)
            frame = (frame + 1) % frames
            time.sleep(frame_duration)

        self.sense_hat.clear_display()

    def behavior_animation(self, behavior: str):
        """
        Show animation for specific behavior

        Args:
            behavior: Behavior type
        """
        animations = {
            'stop': lambda: self.flash_pattern(
                self._create_solid_color(DisplayPatterns.COLORS['red']), 2, 0.5
            ),
            'walk': lambda: self.pulse_color(DisplayPatterns.COLORS['green'], 1.5),
            'run': lambda: self.pulse_color(DisplayPatterns.COLORS['orange'], 1.0, steps=30),
            'fall': lambda: self.flash_pattern(
                DisplayPatterns.get_warning(), 5, 0.3
            ),
            'turn': lambda: self.scroll_text("TURN", DisplayPatterns.COLORS['cyan'], 0.05),
            'shout': lambda: self.flash_pattern(
                self._create_solid_color(DisplayPatterns.COLORS['magenta']), 3, 0.2
            ),
            'dark': lambda: self.pulse_color(DisplayPatterns.COLORS['gray'], 2.0),
            'bright': lambda: self.flash_pattern(
                self._create_solid_color(DisplayPatterns.COLORS['white']), 2, 0.3
            )
        }

        if behavior in animations:
            animations[behavior]()
        else:
            # Default animation
            self.scroll_text(behavior.upper(), DisplayPatterns.COLORS['white'])

    def _create_solid_color(self, color: List[int]) -> List:
        """
        Create solid color pattern

        Args:
            color: RGB color

        Returns:
            64-element pattern
        """
        return [color] * 64


def format_time(seconds: float) -> str:
    """
    Format time duration

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_status_color(status: str) -> List[int]:
    """
    Get color for status

    Args:
        status: Status string

    Returns:
        RGB color
    """
    status_colors = {
        'active': DisplayPatterns.COLORS['green'],
        'warning': DisplayPatterns.COLORS['yellow'],
        'error': DisplayPatterns.COLORS['red'],
        'idle': DisplayPatterns.COLORS['blue'],
        'disabled': DisplayPatterns.COLORS['gray']
    }

    return status_colors.get(status.lower(), DisplayPatterns.COLORS['white'])