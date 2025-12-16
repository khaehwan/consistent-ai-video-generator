#!/usr/bin/env python3
"""
뒤돌아보기(Turn) 감지 테스트 스크립트
실시간 자이로스코프 데이터와 회전 각도를 모니터링합니다
"""

import sys
import time
import yaml
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from behaviors.turn_detector import TurnDetector

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
print("뒤돌아보기(Turn Around) 감지 테스트")
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

# Show current configuration
print("=" * 70)
print("현재 설정값")
print("=" * 70)
turn_config = config.get('behaviors', {}).get('turn', {})
rotation_threshold = turn_config.get('rotation_threshold', 160)
rotation_time = turn_config.get('rotation_time', 2)
cooldown = turn_config.get('cooldown', 3)

print(f"회전 임계값:        {rotation_threshold}° (이 각도 이상 회전시 감지)")
print(f"최대 회전 시간:    {rotation_time}초 (이 시간 내에 회전 완료해야 함)")
print(f"쿨다운 시간:       {cooldown}초 (감지 후 이 시간동안 재감지 안됨)")
print(f"시작 임계값:       30°/s (수평면 회전 속도가 이 값을 넘으면 회전 시작)")
print(f"정지 임계값:       10°/s (수평면 회전 속도가 이 값 이하면 회전 정지)")
print("")
print("✓ 방향 독립적 감지: 센서를 어떤 방향으로 놓아도 작동합니다")
print("  시작 시 중력 방향을 자동으로 캘리브레이션합니다")
print("=" * 70)

# Turn detection callback
turn_count = 0
turn_history = []

def on_turn_detected(rotation: float, duration: float):
    global turn_count, turn_history
    turn_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print("\n" + "!" * 70)
    print(f"🔄 뒤돌아보기 감지! #{turn_count}")
    print(f"시간: {timestamp}")
    print(f"회전 각도: {rotation:.1f}°")
    print(f"소요 시간: {duration:.2f}초")
    print(f"방향: {'왼쪽' if rotation < 0 else '오른쪽'}")
    print("!" * 70 + "\n")

    turn_history.append({
        'timestamp': timestamp,
        'rotation': rotation,
        'duration': duration
    })

# Joystick recalibration callback
def on_joystick_recalibrate():
    """조이스틱 중앙 버튼으로 재캘리브레이션"""
    print("\n" + "!" * 70)
    print("🔘 조이스틱 중앙 버튼 누름 - Turn Detector 재캘리브레이션 중...")
    print("!" * 70)

    # Turn detector 리셋 및 재캘리브레이션
    turn_detector.reset()
    turn_detector.recalibrate()
    print("✓ Turn Detector 중력 벡터 재설정 완료")
    print("✓ 재캘리브레이션 완료!\n")

# Initialize turn detector
print("\n2. Turn Detector 초기화 중...")
turn_detector = TurnDetector(config, sense_hat)
turn_detector.register_turn_callback(on_turn_detected)

# Register joystick callback for recalibration
print("3. 조이스틱 재캘리브레이션 콜백 등록 중...")
sense_hat.register_joystick_callback('middle', on_joystick_recalibrate)
print("✓ 조이스틱 콜백 등록 완료!\n")

# Start detection
print("4. Turn Detector 시작...")
turn_detector.start()
time.sleep(0.5)
print("✓ 감지 시작!\n")

print("=" * 70)
print("실시간 모니터링 시작 (Ctrl+C로 종료)")
print("=" * 70)
print("\n사용 방법:")
print("1. 라즈베리파이를 들고 몸을 뒤돌아보세요 (180도 회전)")
print("2. 2초 안에 회전을 완료하세요")
print("3. 너무 천천히 돌거나 너무 빨리 돌면 감지 안될 수 있습니다")
print("4. 감지 후 3초는 쿨다운 시간입니다")
print("5. 🔘 조이스틱 가운데 버튼: 모든 센서 재캘리브레이션")
print("   (움직임/회전 감지 중력 벡터 재설정 + 상태 리셋)")
print("   센서 방향을 바꿨을 때 버튼을 눌러 새 기준 방향 설정\n")

# Display header
print("-" * 70)
print(f"{'시간':^12} | {'요(Yaw)':^8} | {'각속도(Z)':^12} | {'상태':^10} | {'진행':^12}")
print("-" * 70)

# Monitoring loop
update_interval = 0.2  # 5 Hz display update
last_update = time.time()
display_counter = 0

try:
    while running:
        current_time = time.time()

        # Update display at specified interval
        if current_time - last_update >= update_interval:
            # Get sensor data
            gyro = sense_hat.get_gyroscope()
            orientation = sense_hat.get_orientation()

            if gyro and orientation:
                # Get turn info
                turn_info = turn_detector.get_turn_info()

                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                yaw = orientation['yaw']
                yaw_velocity = gyro['z']

                # Determine status
                if turn_info['is_turning']:
                    status = "🔄 회전중"
                    progress = f"{turn_info['rotation_progress']:.1f}° / {rotation_threshold}°"
                elif turn_info.get('cooldown_remaining', 0) > 0:
                    status = "⏸️ 쿨다운"
                    progress = f"{turn_info['cooldown_remaining']:.1f}초 남음"
                else:
                    status = "⏺️ 대기"
                    progress = "-"

                # Color code yaw velocity
                velocity_str = f"{yaw_velocity:+7.1f}°/s"

                # Print update (every 5 lines, reprint header)
                if display_counter % 25 == 0 and display_counter > 0:
                    print("-" * 70)
                    print(f"{'시간':^12} | {'요(Yaw)':^8} | {'각속도(Z)':^12} | {'상태':^10} | {'진행':^12}")
                    print("-" * 70)

                print(f"{timestamp:^12} | {yaw:>7.1f}° | {velocity_str:^12} | {status:^12} | {progress:^12}")

                display_counter += 1

            last_update = current_time

        time.sleep(0.01)  # Small sleep to prevent CPU spin

except KeyboardInterrupt:
    pass

# Cleanup
print("\n\n" + "=" * 70)
print("테스트 종료")
print("=" * 70)

turn_detector.stop()
sense_hat.stop()

# Print summary
print(f"\n총 감지 횟수: {turn_count}")

if turn_history:
    print("\n감지 기록:")
    print("-" * 70)
    for i, turn in enumerate(turn_history, 1):
        print(f"{i}. [{turn['timestamp']}] {turn['rotation']:+7.1f}° in {turn['duration']:.2f}s")
    print("-" * 70)

print("\n문제 해결 팁:")
print("1. 감지가 안되는 경우:")
print("   - 회전 속도를 조금 빠르게 해보세요 (각속도 30°/s 이상 필요)")
print("   - 2초 안에 160° 이상 회전해야 합니다")
print("   - 회전을 부드럽게 멈추지 말고 명확하게 멈추세요")
print("")
print("2. 너무 자주 감지되는 경우:")
print("   - config.yaml에서 rotation_threshold를 높이세요 (예: 170)")
print("   - 또는 yaw_velocity 시작 임계값을 높이세요 (코드 수정)")
print("")
print("3. 감지 타이밍이 이상한 경우:")
print("   - rotation_time을 조정하세요 (더 길게: 3초)")
print("   - cooldown을 조정하세요 (3~5초)")

print("\n✓ 테스트 완료!")
