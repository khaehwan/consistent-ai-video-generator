#!/usr/bin/env python3
"""
나침반(Compass) 감지 테스트 스크립트
실시간 방위각을 모니터링하고 LED에 북쪽 방향을 표시합니다
"""

import sys
import time
import yaml
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from behaviors.compass_detector import CompassDetector

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
print("나침반(Compass) 감지 테스트")
print("=" * 70)

# Initialize Sense HAT
print("\n1. Sense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

# LED edge positions (same as official example)
led_edge = [4, 5, 6, 7, 15, 23, 31, 39, 47, 55, 63, 62, 61, 60, 59, 58, 57, 56, 48, 40, 32, 24, 16, 8, 0, 1, 2, 3]
led_degree_ratio = len(led_edge) / 360.0

prev_x = 0
prev_y = 0

# Joystick recalibration callback
def on_joystick_recalibrate():
    """조이스틱 중앙 버튼으로 재캘리브레이션"""
    print("\n" + "!" * 70)
    print("🔘 조이스틱 중앙 버튼 누름 - 나침반 재캘리브레이션 중...")
    print("!" * 70)

    compass_detector.recalibrate()
    print("✓ 나침반 재캘리브레이션 완료")
    print("✓ 재캘리브레이션 완료!\n")

    # Show calibration complete animation on LED
    if sense_hat.sense:
        # Define check mark pattern (✓)
        G = [0, 255, 0]   # Green
        O = [0, 0, 0]     # Off

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

        # Quick flash yellow (캘리브레이션 중)
        yellow = [255, 255, 0]
        for _ in range(2):
            sense_hat.sense.set_pixels([yellow] * 64)
            time.sleep(0.1)
            sense_hat.sense.clear()
            time.sleep(0.1)

        # Show green check mark
        sense_hat.sense.set_pixels(check_pattern)
        time.sleep(1.0)
        sense_hat.sense.clear()

sense_hat.start()
time.sleep(0.5)
print("✓ Sense HAT 준비 완료!\n")

# Show current configuration
print("=" * 70)
print("현재 설정값")
print("=" * 70)

# Compass config
compass_config = config.get('behaviors', {}).get('compass', {})
change_threshold = compass_config.get('change_threshold', 15)

print("\n[나침반 감지]")
print(f"  변화 임계값:      {change_threshold}° (이 각도 이상 변하면 로그 기록)")
print(f"  업데이트 주기:    10Hz (0.1초마다)")
print(f"  방위각 범위:      0-360°")
print(f"  LED 표시:        테두리에 북쪽 방향 파란색 점으로 표시")
print("=" * 70)

# Event tracking
heading_count = 0

def on_heading_update(heading: float):
    """방위각 업데이트 콜백 (연속적)"""
    global heading_count, prev_x, prev_y
    heading_count += 1

    # Update LED display
    if sense_hat.sense:
        # Calculate north position on LED edge (same as official example)
        dir_inverted = 360 - heading  # Invert so LED follows North
        led_index = int(led_degree_ratio * dir_inverted) % len(led_edge)
        offset = led_edge[led_index]

        y = offset // 8  # row
        x = offset % 8  # column

        # Clear previous LED
        if x != prev_x or y != prev_y:
            sense_hat.sense.set_pixel(prev_x, prev_y, 0, 0, 0)

        # Set new LED (blue)
        sense_hat.sense.set_pixel(x, y, 0, 0, 255)

        prev_x = x
        prev_y = y

# Initialize compass detector
print("\n2. Compass Detector 초기화 중...")
compass_detector = CompassDetector(config, sense_hat)
compass_detector.register_heading_callback(on_heading_update)

# Register joystick callback for recalibration
print("3. 조이스틱 재캘리브레이션 콜백 등록 중...")
sense_hat.register_joystick_callback('middle', on_joystick_recalibrate)
print("✓ 조이스틱 콜백 등록 완료!\n")

# Start detector
print("4. Compass Detector 시작...")
compass_detector.start()
time.sleep(1)
print("✓ 감지 시작!\n")

print("=" * 70)
print("실시간 모니터링 시작 (Ctrl+C로 종료)")
print("=" * 70)
print("\n사용 방법:")
print("1. 라즈베리파이를 수평으로 놓고 회전시켜보세요")
print("2. LED 매트릭스 테두리에 파란색 점이 북쪽을 가리킵니다")
print("3. 🔘 조이스틱 가운데 버튼: 나침반 재캘리브레이션")
print("   (주변 자기장 환경이 바뀌었을 때 사용)\n")

# Display header
print("-" * 70)
header = f"{'시간':^12} | {'방위각':^10} | {'방향':^10} | {'업데이트':^15}"
print(header)
print("-" * 70)

# Direction names
def get_direction_name(heading: float) -> str:
    """Get cardinal direction name from heading"""
    directions = [
        ("북 (N)", 0, 22.5),
        ("북동 (NE)", 22.5, 67.5),
        ("동 (E)", 67.5, 112.5),
        ("남동 (SE)", 112.5, 157.5),
        ("남 (S)", 157.5, 202.5),
        ("남서 (SW)", 202.5, 247.5),
        ("서 (W)", 247.5, 292.5),
        ("북서 (NW)", 292.5, 337.5),
        ("북 (N)", 337.5, 360)
    ]

    for name, low, high in directions:
        if low <= heading < high:
            return name
    return "북 (N)"

# Monitoring loop
update_interval = 0.5  # 2 Hz display update
last_update = time.time()
display_counter = 0

try:
    while running:
        current_time = time.time()

        # Update display at specified interval
        if current_time - last_update >= update_interval:
            # Get compass info
            compass_info = compass_detector.get_compass_info()

            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            heading = compass_info['current_heading']
            direction_name = get_direction_name(heading)

            # Print update (every 25 lines, reprint header)
            if display_counter % 25 == 0 and display_counter > 0:
                print("-" * 70)
                print(header)
                print("-" * 70)

            print(f"{timestamp:^12} | {heading:>9.1f}° | {direction_name:^10} | {heading_count:>14} 회")

            display_counter += 1
            last_update = current_time

        time.sleep(0.01)  # Small sleep to prevent CPU spin

except KeyboardInterrupt:
    pass

# Cleanup
print("\n\n" + "=" * 70)
print("테스트 종료")
print("=" * 70)

compass_detector.stop()
sense_hat.stop()

# Print summary
print(f"\n총 방위각 업데이트: {heading_count} 회")

print("\n문제 해결 팁:")
print("\n1. 방향이 정확하지 않은 경우:")
print("   - 조이스틱 가운데 버튼을 눌러 재캘리브레이션하세요")
print("   - 주변에 자석이나 금속 물체를 멀리 하세요")
print("   - 라즈베리파이를 수평으로 놓으세요")
print("")
print("2. LED가 표시되지 않는 경우:")
print("   - Sense HAT이 제대로 연결되었는지 확인하세요")
print("   - 자력계가 작동하는지 test_magnetometer.py로 확인하세요")
print("")
print("3. 북쪽 방향 확인:")
print("   - 실제 나침반이나 스마트폰 나침반 앱과 비교해보세요")
print("   - 파란색 LED 점이 북쪽을 가리킵니다")

print("\n✓ 테스트 완료!")
