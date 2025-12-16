"""
Dashboard Display Module
Provides dashboard-style display for showing multiple sensor states simultaneously
"""

import logging
import threading
import time
from typing import Dict, List, Optional
from enum import Enum


class DashboardLayout(Enum):
    """Dashboard layout types"""
    QUAD = "quad"  # 4 quadrants (4x4 each)
    STRIP = "strip"  # 8 horizontal strips (8x1 each)
    COMPACT = "compact"  # Compact 2x2 indicators


class DashboardDisplay:
    """
    Manages dashboard-style display on 8x8 LED matrix
    Shows multiple sensor states simultaneously
    """

    def __init__(self, sense_hat_handler, layout: DashboardLayout = DashboardLayout.QUAD):
        """
        Initialize dashboard display

        Args:
            sense_hat_handler: Reference to SenseHatHandler
            layout: Dashboard layout type
        """
        self.sense_hat = sense_hat_handler
        self.layout = layout
        self.logger = logging.getLogger(__name__)

        # Current state for each sensor/behavior
        self.states = {
            'movement': 'stop',  # stop, walk, run
            'fall': False,       # True/False
            'turn': False,       # True/False
            'shout': False,      # True/False
            'brightness': 'normal',  # dark, normal, bright
        }

        # Color definitions for dashboard
        self.colors = {
            # Movement colors
            'stop': [0, 255, 0],      # Green
            'walk': [255, 255, 0],    # Yellow
            'run': [255, 128, 0],     # Orange

            # Status colors
            'active': [255, 0, 0],    # Red (fall, turn, shout active)
            'inactive': [0, 64, 0],   # Dark green (inactive)

            # Brightness colors
            'dark': [64, 64, 64],     # Dark gray
            'normal': [128, 128, 128], # Gray
            'bright': [255, 255, 255], # White

            'off': [0, 0, 0]          # Black/off
        }

        # Update thread
        self.running = False
        self.update_thread = None
        self.update_interval = 0.1  # 100ms refresh rate

        self.logger.info(f"Dashboard display initialized with {layout.value} layout")

    def start(self):
        """Start dashboard update thread"""
        if not self.sense_hat.enabled:
            self.logger.warning("Sense HAT not available for dashboard")
            return

        self.running = True
        self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self.update_thread.start()
        self.logger.info("Dashboard update thread started")

    def stop(self):
        """Stop dashboard update thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1)
        self.sense_hat.clear_display()
        self.logger.info("Dashboard stopped")

    def _update_worker(self):
        """Worker thread for updating dashboard display"""
        while self.running:
            try:
                # Generate dashboard pixels based on current states
                pixels = self._generate_dashboard()

                # Display on LED matrix
                if self.sense_hat.sense:
                    self.sense_hat.sense.set_pixels(pixels)

                time.sleep(self.update_interval)

            except Exception as e:
                self.logger.error(f"Dashboard update error: {e}")
                time.sleep(1)

    def _generate_dashboard(self) -> List:
        """
        Generate 64-pixel array for dashboard display

        Returns:
            List of 64 RGB values
        """
        if self.layout == DashboardLayout.QUAD:
            return self._generate_quad_layout()
        elif self.layout == DashboardLayout.STRIP:
            return self._generate_strip_layout()
        elif self.layout == DashboardLayout.COMPACT:
            return self._generate_compact_layout()
        else:
            return [self.colors['off']] * 64

    def _generate_quad_layout(self) -> List:
        """
        Generate quad layout (4 quadrants, 4x4 each)

        Layout:
        ┌─────────┬─────────┐
        │ Movement│  Fall   │
        │  (4x4)  │  (4x4)  │
        ├─────────┼─────────┤
        │  Turn   │  Shout  │
        │  (4x4)  │  (4x4)  │
        └─────────┴─────────┘
        """
        pixels = [self.colors['off']] * 64

        # Top-left: Movement (rows 0-3, cols 0-3)
        movement_color = self.colors.get(self.states['movement'], self.colors['off'])
        for row in range(4):
            for col in range(4):
                pixels[row * 8 + col] = movement_color

        # Top-right: Fall (rows 0-3, cols 4-7)
        fall_color = self.colors['active'] if self.states['fall'] else self.colors['inactive']
        for row in range(4):
            for col in range(4, 8):
                pixels[row * 8 + col] = fall_color

        # Bottom-left: Turn (rows 4-7, cols 0-3)
        turn_color = self.colors['active'] if self.states['turn'] else self.colors['inactive']
        for row in range(4, 8):
            for col in range(4):
                pixels[row * 8 + col] = turn_color

        # Bottom-right: Shout (rows 4-7, cols 4-7)
        shout_color = self.colors['active'] if self.states['shout'] else self.colors['inactive']
        for row in range(4, 8):
            for col in range(4, 8):
                pixels[row * 8 + col] = shout_color

        return pixels

    def _generate_strip_layout(self) -> List:
        """
        Generate strip layout (horizontal bars)

        Layout:
        Row 0-1: Movement (stop=green, walk=yellow, run=orange)
        Row 2-3: Fall status (red=fallen, dark green=normal)
        Row 4-5: Turn/Shout combined
        Row 6-7: Brightness
        """
        pixels = [self.colors['off']] * 64

        # Row 0-1: Movement
        movement_color = self.colors.get(self.states['movement'], self.colors['off'])
        for row in range(2):
            for col in range(8):
                pixels[row * 8 + col] = movement_color

        # Row 2-3: Fall
        fall_color = self.colors['active'] if self.states['fall'] else self.colors['inactive']
        for row in range(2, 4):
            for col in range(8):
                pixels[row * 8 + col] = fall_color

        # Row 4-5: Turn (left half) and Shout (right half)
        turn_color = self.colors['active'] if self.states['turn'] else self.colors['inactive']
        shout_color = self.colors['active'] if self.states['shout'] else self.colors['inactive']
        for row in range(4, 6):
            for col in range(4):
                pixels[row * 8 + col] = turn_color
            for col in range(4, 8):
                pixels[row * 8 + col] = shout_color

        # Row 6-7: Brightness
        brightness_color = self.colors.get(self.states['brightness'], self.colors['normal'])
        for row in range(6, 8):
            for col in range(8):
                pixels[row * 8 + col] = brightness_color

        return pixels

    def _generate_compact_layout(self) -> List:
        """
        Generate compact layout (2x2 indicators with labels)

        Layout:
        ┌──┬──┬──┬──┬──┬──┬──┬──┐
        │M │M │F │F │T │T │S │S │  M=Movement, F=Fall
        │M │M │F │F │T │T │S │S │  T=Turn, S=Shout
        ├──┼──┼──┼──┼──┼──┼──┼──┤
        │B │B │  │  │  │  │  │  │  B=Brightness
        │B │B │  │  │  │  │  │  │
        └──┴──┴──┴──┴──┴──┴──┴──┘
        """
        pixels = [self.colors['off']] * 64

        # Movement (2x2, top-left)
        movement_color = self.colors.get(self.states['movement'], self.colors['off'])
        for row in range(2):
            for col in range(2):
                pixels[row * 8 + col] = movement_color

        # Fall (2x2, top 2nd from left)
        fall_color = self.colors['active'] if self.states['fall'] else self.colors['inactive']
        for row in range(2):
            for col in range(2, 4):
                pixels[row * 8 + col] = fall_color

        # Turn (2x2, top 3rd from left)
        turn_color = self.colors['active'] if self.states['turn'] else self.colors['inactive']
        for row in range(2):
            for col in range(4, 6):
                pixels[row * 8 + col] = turn_color

        # Shout (2x2, top-right)
        shout_color = self.colors['active'] if self.states['shout'] else self.colors['inactive']
        for row in range(2):
            for col in range(6, 8):
                pixels[row * 8 + col] = shout_color

        # Brightness (2x2, bottom-left)
        brightness_color = self.colors.get(self.states['brightness'], self.colors['normal'])
        for row in range(2, 4):
            for col in range(2):
                pixels[row * 8 + col] = brightness_color

        return pixels

    def update_state(self, sensor: str, value):
        """
        Update sensor state

        Args:
            sensor: Sensor name (movement, fall, turn, shout, brightness)
            value: New state value
        """
        if sensor in self.states:
            self.states[sensor] = value
            self.logger.debug(f"Dashboard state updated: {sensor} = {value}")
        else:
            self.logger.warning(f"Unknown sensor: {sensor}")

    def update_movement(self, state: str):
        """Update movement state (stop, walk, run)"""
        self.update_state('movement', state)

    def update_fall(self, is_fallen: bool):
        """Update fall state"""
        self.update_state('fall', is_fallen)

    def update_turn(self, is_turning: bool):
        """Update turn state"""
        self.update_state('turn', is_turning)

    def update_shout(self, is_shouting: bool):
        """Update shout state"""
        self.update_state('shout', is_shouting)

    def update_brightness(self, state: str):
        """Update brightness state (dark, normal, bright)"""
        self.update_state('brightness', state)

    def get_current_states(self) -> Dict:
        """
        Get current dashboard states

        Returns:
            Dictionary of current states
        """
        return self.states.copy()

    def set_layout(self, layout: DashboardLayout):
        """
        Change dashboard layout

        Args:
            layout: New layout type
        """
        self.layout = layout
        self.logger.info(f"Dashboard layout changed to {layout.value}")

    def flash_indicator(self, sensor: str, duration: float = 0.5):
        """
        Flash a specific indicator

        Args:
            sensor: Sensor to flash
            duration: Flash duration in seconds
        """
        # Store original state
        original_state = self.states.get(sensor)

        # Flash on
        if sensor in ['fall', 'turn', 'shout']:
            self.update_state(sensor, True)
        elif sensor == 'movement':
            self.update_state(sensor, 'run')
        elif sensor == 'brightness':
            self.update_state(sensor, 'bright')

        # Wait
        time.sleep(duration)

        # Restore
        if original_state is not None:
            self.update_state(sensor, original_state)
