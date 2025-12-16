#!/usr/bin/env python3
"""
뒤돌아보기 감지 대화형 테스트
설정을 조정하면서 실시간으로 테스트할 수 있습니다
"""

import sys
import time
import yaml
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from behaviors.turn_detector import TurnDetector

print("=" * 70)
print("뒤돌아보기 감지 - 대화형 테스트")
print("=" * 70)

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize Sense HAT
print("\nSense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

sense_hat.start()
time.sleep(0.5)
print("✓ 준비 완료!\n")

# Detection state
turn_count = 0
monitoring = False
monitor_thread = None

def on_turn_detected(rotation: float, duration: float):
    global turn_count
    turn_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S")

    print("\n" + "!" * 60)
    print(f"🔄 감지! #{turn_count} [{timestamp}] {rotation:+.1f}° in {duration:.2f}s")
    print("!" * 60)

# Initialize turn detector
turn_detector = TurnDetector(config, sense_hat)
turn_detector.register_turn_callback(on_turn_detected)

# Joystick recalibration callback
def on_joystick_recalibrate():
    """조이스틱 중앙 버튼으로 재캘리브레이션"""
    print("\n" + "!" * 60)
    print("🔘 조이스틱 중앙 버튼 - Turn Detector 재캘리브레이션!")
    print("!" * 60)

    # Turn detector 리셋 및 재캘리브레이션
    turn_detector.reset()
    turn_detector.recalibrate()
    print("✓ 중력 벡터 재설정 완료!\n")

# Register joystick callback for recalibration
sense_hat.register_joystick_callback('middle', on_joystick_recalibrate)

# Get initial settings
rotation_threshold = config.get('behaviors', {}).get('turn', {}).get('rotation_threshold', 160)
rotation_time = config.get('behaviors', {}).get('turn', {}).get('rotation_time', 2)
cooldown = config.get('behaviors', {}).get('turn', {}).get('cooldown', 3)

def monitor_worker():
    """Background thread to monitor sensor data"""
    global monitoring
    last_print = time.time()

    while monitoring:
        if time.time() - last_print > 0.5:  # Print every 0.5 seconds
            gyro = sense_hat.get_gyroscope()
            orientation = sense_hat.get_orientation()

            if gyro and orientation:
                turn_info = turn_detector.get_turn_info()

                yaw_vel = gyro['z']
                yaw_angle = orientation['yaw']

                status = ""
                if turn_info['is_turning']:
                    progress = turn_info['rotation_progress']
                    status = f"🔄 회전중: {progress:.1f}° / {rotation_threshold}°"
                elif turn_info.get('cooldown_remaining', 0) > 0:
                    remaining = turn_info['cooldown_remaining']
                    status = f"⏸️ 쿨다운: {remaining:.1f}초"
                else:
                    status = "⏺️ 대기중"

                vel_indicator = "→" if abs(yaw_vel) > 30 else " "
                print(f"[Yaw: {yaw_angle:>6.1f}° | 각속도: {vel_indicator}{yaw_vel:+7.1f}°/s{vel_indicator}] {status}")

                last_print = time.time()

        time.sleep(0.05)

def show_menu():
    print("\n" + "=" * 70)
    print("메뉴")
    print("=" * 70)
    print("1. 감지 시작/중지")
    print("2. 실시간 모니터링 시작/중지")
    print("3. 현재 설정 보기")
    print("4. 회전 임계값 변경 (현재: {}°)".format(rotation_threshold))
    print("5. 최대 회전 시간 변경 (현재: {}초)".format(rotation_time))
    print("6. 쿨다운 시간 변경 (현재: {}초)".format(cooldown))
    print("7. 센서 상태 확인")
    print("8. 통계 보기")
    print("0. 종료")
    print("")
    print("💡 팁: 조이스틱 가운데 버튼 → 모든 센서 재캘리브레이션")
    print("       움직임/회전 감지 중력 벡터 재설정 + 상태 리셋")
    print("       센서 방향을 바꿨을 때 유용합니다")
    print("=" * 70)

def show_settings():
    print("\n현재 설정:")
    print(f"  회전 임계값:     {rotation_threshold}° (이 각도 이상 회전시 감지)")
    print(f"  최대 회전 시간:  {rotation_time}초")
    print(f"  쿨다운 시간:     {cooldown}초")
    print(f"  시작 각속도:     30°/s (코드 내 고정값)")
    print(f"  정지 각속도:     10°/s (코드 내 고정값)")

def show_sensor_status():
    print("\n센서 상태:")
    gyro = sense_hat.get_gyroscope()
    orientation = sense_hat.get_orientation()

    if gyro and orientation:
        print("  자이로스코프:")
        print(f"    Pitch(X): {gyro['x']:+7.2f}°/s")
        print(f"    Roll(Y):  {gyro['y']:+7.2f}°/s")
        print(f"    Yaw(Z):   {gyro['z']:+7.2f}°/s  ← 뒤돌아보기 감지용")
        print("  방향:")
        print(f"    Pitch: {orientation['pitch']:>6.1f}°")
        print(f"    Roll:  {orientation['roll']:>6.1f}°")
        print(f"    Yaw:   {orientation['yaw']:>6.1f}°")
    else:
        print("  ✗ 센서 데이터를 읽을 수 없습니다!")

def show_statistics():
    print("\n통계:")
    print(f"  총 감지 횟수: {turn_count}")

    turn_info = turn_detector.get_turn_info()
    print(f"  감지기 실행 중: {'예' if turn_info['running'] else '아니오'}")
    print(f"  현재 회전 중: {'예' if turn_info['is_turning'] else '아니오'}")

    if turn_info.get('time_since_last_turn'):
        print(f"  마지막 감지 후 경과: {turn_info['time_since_last_turn']:.1f}초")

# Main loop
try:
    while True:
        show_menu()

        try:
            choice = input("\n선택 (0-8): ").strip()
        except EOFError:
            break

        if choice == '1':
            # Start/Stop detection
            turn_info = turn_detector.get_turn_info()
            if turn_info['running']:
                turn_detector.stop()
                print("\n✓ 감지 중지됨")
            else:
                turn_detector.start()
                print("\n✓ 감지 시작됨")
                print("라즈베리파이를 들고 몸을 180도 회전해보세요!")

        elif choice == '2':
            # Start/Stop monitoring
            if monitoring:
                monitoring = False
                if monitor_thread:
                    monitor_thread.join(timeout=1)
                print("\n✓ 모니터링 중지됨")
            else:
                monitoring = True
                monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
                monitor_thread.start()
                print("\n✓ 실시간 모니터링 시작됨")
                print("(아무 키나 누르고 Enter를 치면 메뉴로 돌아갑니다)\n")

        elif choice == '3':
            # Show settings
            show_settings()

        elif choice == '4':
            # Change rotation threshold
            try:
                new_value = float(input(f"새로운 회전 임계값 입력 (현재 {rotation_threshold}°): "))
                if 90 <= new_value <= 360:
                    rotation_threshold = new_value
                    turn_detector.set_threshold(rotation_threshold)
                    print(f"\n✓ 회전 임계값을 {rotation_threshold}°로 변경했습니다")
                else:
                    print("\n✗ 값은 90~360 사이여야 합니다")
            except ValueError:
                print("\n✗ 올바른 숫자를 입력하세요")

        elif choice == '5':
            # Change rotation time
            try:
                new_value = float(input(f"새로운 최대 회전 시간 입력 (현재 {rotation_time}초): "))
                if 0.5 <= new_value <= 10:
                    rotation_time = new_value
                    turn_detector.rotation_time = rotation_time
                    print(f"\n✓ 최대 회전 시간을 {rotation_time}초로 변경했습니다")
                else:
                    print("\n✗ 값은 0.5~10 사이여야 합니다")
            except ValueError:
                print("\n✗ 올바른 숫자를 입력하세요")

        elif choice == '6':
            # Change cooldown
            try:
                new_value = float(input(f"새로운 쿨다운 시간 입력 (현재 {cooldown}초): "))
                if 0 <= new_value <= 10:
                    cooldown = new_value
                    turn_detector.cooldown = cooldown
                    print(f"\n✓ 쿨다운 시간을 {cooldown}초로 변경했습니다")
                else:
                    print("\n✗ 값은 0~10 사이여야 합니다")
            except ValueError:
                print("\n✗ 올바른 숫자를 입력하세요")

        elif choice == '7':
            # Show sensor status
            show_sensor_status()

        elif choice == '8':
            # Show statistics
            show_statistics()

        elif choice == '0':
            # Exit
            break

        else:
            print("\n✗ 올바른 선택이 아닙니다")

except KeyboardInterrupt:
    print("\n\n프로그램 중단...")

# Cleanup
monitoring = False
if monitor_thread:
    monitor_thread.join(timeout=1)

turn_detector.stop()
sense_hat.stop()

print("\n" + "=" * 70)
print("테스트 종료")
print("=" * 70)
print(f"총 {turn_count}번 감지되었습니다.")
print("\n권장 설정:")
print("  - 일반적인 경우: 160° 임계값, 2초 시간, 3초 쿨다운")
print("  - 빠른 회전: 150° 임계값, 1.5초 시간, 2초 쿨다운")
print("  - 느린 회전: 170° 임계값, 3초 시간, 4초 쿨다운")
print("\n✓ 완료!")
