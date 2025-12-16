#!/usr/bin/env python3
"""
조이스틱 테스트 스크립트
Sense HAT 조이스틱의 모든 방향을 테스트합니다
"""

import sys
import time
import yaml
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler

# Global flag for clean exit
running = True

def signal_handler(sig, frame):
    global running
    print("\n\n프로그램 종료 중...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=" * 70)
print("Sense HAT 조이스틱 테스트")
print("=" * 70)

# Initialize Sense HAT
print("\n1. Sense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

sense_hat.start()
time.sleep(0.5)
print("✓ Sense HAT 준비 완료!\n")

# LED patterns for each direction
# 8x8 LED matrix patterns

# Arrow UP (blue)
PATTERN_UP = [
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 255], [0, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 0],
    [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255],
    [0, 0, 0], [0, 0, 0], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
]

# Arrow DOWN (cyan)
PATTERN_DOWN = [
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 0, 0], [0, 0, 0],
    [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255],
    [0, 0, 0], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 255, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 255, 255], [0, 255, 255], [0, 0, 0], [0, 0, 0], [0, 0, 0],
]

# Arrow LEFT (yellow)
PATTERN_LEFT = [
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 255, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 255, 0], [255, 255, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0],
    [0, 0, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0],
    [0, 0, 0], [0, 0, 0], [255, 255, 0], [255, 255, 0], [255, 255, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 255, 0], [255, 255, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 255, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
]

# Arrow RIGHT (magenta)
PATTERN_RIGHT = [
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 255], [255, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 255], [255, 0, 255], [255, 0, 255], [0, 0, 0], [0, 0, 0],
    [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [0, 0, 0],
    [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [255, 0, 255], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 255], [255, 0, 255], [255, 0, 255], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 255], [255, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 0, 255], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
]

# Circle MIDDLE (green)
PATTERN_MIDDLE = [
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 0, 0],
    [0, 0, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 0, 0],
    [0, 0, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 0, 0],
    [0, 0, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 255, 0], [0, 0, 0], [0, 0, 0],
    [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
]

# Event tracking
events = {
    'up': 0,
    'down': 0,
    'left': 0,
    'right': 0,
    'middle': 0
}

event_history = []

def show_pattern_temporary(pattern, duration=0.5):
    """Show a pattern temporarily"""
    if sense_hat.sense:
        sense_hat.sense.set_pixels(pattern)
        time.sleep(duration)
        sense_hat.sense.clear()

def on_joystick_up():
    """조이스틱 UP 콜백"""
    global events, event_history
    events['up'] += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n[{timestamp}] 🔼 UP 감지! (총 {events['up']}회)")
    event_history.append({'timestamp': timestamp, 'direction': 'UP'})

    # Show pattern on LED
    show_pattern_temporary(PATTERN_UP, 0.3)

def on_joystick_down():
    """조이스틱 DOWN 콜백"""
    global events, event_history
    events['down'] += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n[{timestamp}] 🔽 DOWN 감지! (총 {events['down']}회)")
    event_history.append({'timestamp': timestamp, 'direction': 'DOWN'})

    # Show pattern on LED
    show_pattern_temporary(PATTERN_DOWN, 0.3)

def on_joystick_left():
    """조이스틱 LEFT 콜백"""
    global events, event_history
    events['left'] += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n[{timestamp}] ◀️  LEFT 감지! (총 {events['left']}회)")
    event_history.append({'timestamp': timestamp, 'direction': 'LEFT'})

    # Show pattern on LED
    show_pattern_temporary(PATTERN_LEFT, 0.3)

def on_joystick_right():
    """조이스틱 RIGHT 콜백"""
    global events, event_history
    events['right'] += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n[{timestamp}] ▶️  RIGHT 감지! (총 {events['right']}회)")
    event_history.append({'timestamp': timestamp, 'direction': 'RIGHT'})

    # Show pattern on LED
    show_pattern_temporary(PATTERN_RIGHT, 0.3)

def on_joystick_middle():
    """조이스틱 MIDDLE 콜백"""
    global events, event_history
    events['middle'] += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"\n[{timestamp}] 🔘 MIDDLE 감지! (총 {events['middle']}회)")
    event_history.append({'timestamp': timestamp, 'direction': 'MIDDLE'})

    # Show pattern on LED
    show_pattern_temporary(PATTERN_MIDDLE, 0.3)

# Register joystick callbacks
print("2. 조이스틱 콜백 등록 중...")
sense_hat.register_joystick_callback('up', on_joystick_up)
sense_hat.register_joystick_callback('down', on_joystick_down)
sense_hat.register_joystick_callback('left', on_joystick_left)
sense_hat.register_joystick_callback('right', on_joystick_right)
sense_hat.register_joystick_callback('middle', on_joystick_middle)
print("✓ 콜백 등록 완료!\n")

print("=" * 70)
print("조이스틱 테스트 시작 (Ctrl+C로 종료)")
print("=" * 70)

print("\n사용 방법:")
print("1. 조이스틱을 위/아래/좌/우로 움직여보세요")
print("2. 조이스틱 가운데 버튼을 눌러보세요")
print("3. 각 방향마다 LED에 화살표가 표시됩니다")
print("4. 콘솔에 실시간으로 이벤트가 출력됩니다")

print("\nLED 색상 안내:")
print("  🔼 UP:     파란색 (Blue)")
print("  🔽 DOWN:   청록색 (Cyan)")
print("  ◀️  LEFT:   노란색 (Yellow)")
print("  ▶️  RIGHT:  자홍색 (Magenta)")
print("  🔘 MIDDLE: 녹색 (Green)")

print("\n대기 중... 조이스틱을 사용해보세요!\n")

# Main loop
try:
    while running:
        # Just wait for joystick events
        time.sleep(0.1)

except KeyboardInterrupt:
    pass

# Cleanup
print("\n\n" + "=" * 70)
print("테스트 종료")
print("=" * 70)

sense_hat.stop()

# Print summary
total_events = sum(events.values())
print(f"\n총 조이스틱 이벤트: {total_events}회")
print("\n방향별 통계:")
print(f"  🔼 UP:     {events['up']:3d}회")
print(f"  🔽 DOWN:   {events['down']:3d}회")
print(f"  ◀️  LEFT:   {events['left']:3d}회")
print(f"  ▶️  RIGHT:  {events['right']:3d}회")
print(f"  🔘 MIDDLE: {events['middle']:3d}회")

if event_history:
    print(f"\n최근 이벤트 기록 (최대 20개):")
    print("-" * 70)
    for i, event in enumerate(event_history[-20:], 1):
        direction_emoji = {
            'UP': '🔼',
            'DOWN': '🔽',
            'LEFT': '◀️ ',
            'RIGHT': '▶️ ',
            'MIDDLE': '🔘'
        }.get(event['direction'], '  ')
        print(f"{i:2d}. [{event['timestamp']}] {direction_emoji} {event['direction']}")
    print("-" * 70)

print("\n조이스틱 테스트 팁:")
print("1. 버튼이 반응하지 않는 경우:")
print("   - Sense HAT이 제대로 연결되었는지 확인하세요")
print("   - 라즈베리파이를 재부팅해보세요")
print("")
print("2. LED가 표시되지 않는 경우:")
print("   - Sense HAT LED 밝기 설정을 확인하세요")
print("   - config.yaml의 led_brightness 값을 높여보세요")
print("")
print("3. 이벤트가 중복으로 감지되는 경우:")
print("   - 정상입니다! 조이스틱을 누를 때 'pressed'와 'released' 이벤트가 모두 발생할 수 있습니다")
print("   - 현재는 'pressed' 이벤트만 처리하도록 설정되어 있습니다")

print("\n✓ 테스트 완료!")
