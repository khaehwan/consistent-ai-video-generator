#!/usr/bin/env python3
"""
움직임(Movement) 및 낙상(Fall) 감지 테스트 스크립트
실시간 가속도계 데이터와 감지 이벤트를 모니터링합니다
"""

import sys
import time
import yaml
import signal
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from behaviors.movement_detector import MovementDetector, MovementState
from behaviors.fall_detector import FallDetector

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
print("움직임(Movement) 및 낙상(Fall) 감지 테스트")
print("=" * 70)

# Initialize Sense HAT
print("\n1. Sense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

# Register joystick callback for recalibration
def on_joystick_recalibrate():
    """조이스틱 중앙 버튼으로 재캘리브레이션"""
    global movement_detector, fall_detector
    print("\n" + "!" * 70)
    print("🔘 조이스틱 중앙 버튼 누름 - 센서 재캘리브레이션 중...")
    print("!" * 70)

    # Movement detector 재캘리브레이션
    movement_detector.recalibrate()
    print("✓ 움직임 감지기 중력 벡터 재설정 완료")

    # Fall detector 재캘리브레이션
    fall_detector.recalibrate()
    print("✓ 낙상 감지기 재설정 완료")

    print("✓ 재캘리브레이션 완료!\n")

sense_hat.start()
time.sleep(0.5)
print("✓ Sense HAT 준비 완료!\n")

# Show current configuration
print("=" * 70)
print("현재 설정값")
print("=" * 70)

# Movement config
movement_config = config.get('behaviors', {}).get('movement', {})
threshold_static = movement_config.get('threshold_static', 0.1)
threshold_walking = movement_config.get('threshold_walking', 0.5)
threshold_running = movement_config.get('threshold_running', 1.5)
movement_cooldown = movement_config.get('cooldown', 2)

print("\n[움직임 감지]")
print(f"  정지 임계값:     {threshold_static} (이 값 이하면 STOP)")
print(f"  걷기 임계값:     {threshold_walking} (이 값 이상이면 WALK)")
print(f"  달리기 임계값:   {threshold_running} (이 값 이상이면 RUN)")
print(f"  쿨다운:          {movement_cooldown}초")
print(f"  자동 캘리브레이션: 시작 시 중력 방향 자동 감지")

# Fall config
fall_config = config.get('behaviors', {}).get('fall', {})
fall_accel_threshold = fall_config.get('acceleration_threshold', 2.0)
fall_angle_threshold = fall_config.get('angle_threshold', 45)
fall_cooldown = fall_config.get('cooldown', 5)

print("\n[낙상 감지]")
print(f"  가속도 임계값:   {fall_accel_threshold}g (이 값 이상이면 낙상 의심)")
print(f"  각도 임계값:     {fall_angle_threshold}° (자세 변화가 이 값 이상이면 낙상)")
print(f"  쿨다운:          {fall_cooldown}초")

print("\n✓ 방향 독립적 감지: 센서를 어떤 방향으로 놓아도 작동합니다")
print("=" * 70)

# Event tracking
movement_changes = []
fall_events = []
movement_count = 0
fall_count = 0

def on_movement_state_change(new_state: MovementState, old_state: MovementState):
    """움직임 상태 변화 콜백"""
    global movement_count, movement_changes
    movement_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print("\n" + "!" * 70)
    print(f"🚶 움직임 상태 변화! #{movement_count}")
    print(f"시간: {timestamp}")
    print(f"변화: {old_state.value.upper()} → {new_state.value.upper()}")
    print(f"활동 레벨: {movement_detector.get_activity_level():.3f}")
    print("!" * 70 + "\n")

    movement_changes.append({
        'timestamp': timestamp,
        'old_state': old_state.value,
        'new_state': new_state.value,
        'activity_level': movement_detector.get_activity_level()
    })

def on_fall_detected(max_acceleration: float, orientation_change: float):
    """낙상 감지 콜백"""
    global fall_count, fall_events
    fall_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print("\n" + "!" * 70)
    print(f"⚠️  낙상 감지! #{fall_count}")
    print(f"시간: {timestamp}")
    print(f"최대 가속도: {max_acceleration:.2f}g")
    print(f"자세 변화: {orientation_change:.1f}°")
    print(f"심각도: {'높음 (HIGH)' if max_acceleration > 3.0 else '보통 (MODERATE)'}")
    print("!" * 70 + "\n")

    fall_events.append({
        'timestamp': timestamp,
        'max_acceleration': max_acceleration,
        'orientation_change': orientation_change
    })

# Initialize detectors
print("\n2. Movement Detector 초기화 중...")
movement_detector = MovementDetector(config, sense_hat)
movement_detector.register_state_callback(on_movement_state_change)

print("3. Fall Detector 초기화 중...")
fall_detector = FallDetector(config, sense_hat)
fall_detector.register_fall_callback(on_fall_detected)

# Register joystick callback for recalibration
print("4. 조이스틱 재캘리브레이션 콜백 등록 중...")
sense_hat.register_joystick_callback('middle', on_joystick_recalibrate)
print("✓ 조이스틱 콜백 등록 완료!\n")

# Start detectors
print("5. Detectors 시작...")
movement_detector.start()
fall_detector.start()
time.sleep(1)
print("✓ 감지 시작!\n")

print("=" * 70)
print("실시간 모니터링 시작 (Ctrl+C로 종료)")
print("=" * 70)
print("\n사용 방법:")
print("1. [움직임 감지] 라즈베리파이를 들고 걸어보세요")
print("2. [움직임 감지] 빠르게 움직이면 달리기로 감지됩니다")
print("3. [움직임 감지] 멈추면 정지로 감지됩니다")
print("4. [낙상 감지] 라즈베리파이를 떨어뜨리거나 급격히 기울이세요")
print("5. 🔘 조이스틱 가운데 버튼: 모든 센서 재캘리브레이션")
print("   (움직임/낙상 감지 중력 벡터 재설정)")
print("   센서 방향을 바꿨을 때 버튼을 눌러 새 기준 방향 설정\n")

# Display header
print("-" * 70)
header = f"{'시간':^12} | {'가속도(XYZ)':^24} | {'크기':^8} | {'활동':^8} | {'상태':^8}"
print(header)
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
            accel = sense_hat.get_accelerometer()

            if accel:
                # Get movement info
                movement_info = movement_detector.get_movement_info()

                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                accel_x = accel['x']
                accel_y = accel['y']
                accel_z = accel['z']

                # Calculate magnitude
                import math
                magnitude = math.sqrt(accel_x**2 + accel_y**2 + accel_z**2)

                activity = movement_info.get('activity_level', 0.0)
                state = movement_info.get('current_state', 'unknown').upper()

                # Format acceleration values
                accel_str = f"{accel_x:+5.2f} {accel_y:+5.2f} {accel_z:+5.2f}"

                # Colorize state
                state_emoji = {
                    'STOP': '⏺️ ',
                    'WALK': '🚶',
                    'RUN': '🏃'
                }.get(state, '  ')

                # Print update (every 25 lines, reprint header)
                if display_counter % 25 == 0 and display_counter > 0:
                    print("-" * 70)
                    print(header)
                    print("-" * 70)

                print(f"{timestamp:^12} | {accel_str:^24} | {magnitude:>7.2f}g | {activity:>7.3f} | {state_emoji}{state:<6}")

                display_counter += 1

            last_update = current_time

        time.sleep(0.01)  # Small sleep to prevent CPU spin

except KeyboardInterrupt:
    pass

# Cleanup
print("\n\n" + "=" * 70)
print("테스트 종료")
print("=" * 70)

movement_detector.stop()
fall_detector.stop()
sense_hat.stop()

# Print summary
print(f"\n총 움직임 상태 변화: {movement_count}")
print(f"총 낙상 감지: {fall_count}")

if movement_changes:
    print("\n움직임 상태 변화 기록:")
    print("-" * 70)
    for i, change in enumerate(movement_changes, 1):
        print(f"{i}. [{change['timestamp']}] {change['old_state'].upper()} → {change['new_state'].upper()} (활동: {change['activity_level']:.3f})")
    print("-" * 70)

if fall_events:
    print("\n낙상 감지 기록:")
    print("-" * 70)
    for i, event in enumerate(fall_events, 1):
        print(f"{i}. [{event['timestamp']}] 가속도: {event['max_acceleration']:.2f}g, 자세 변화: {event['orientation_change']:.1f}°")
    print("-" * 70)

print("\n문제 해결 팁:")
print("\n1. 움직임 감지가 안되는 경우:")
print("   - 조금 더 크게 움직여보세요")
print("   - config.yaml에서 threshold_walking을 낮춰보세요 (예: 0.3)")
print("   - 센서를 흔들거나 걸어다니면서 테스트하세요")
print("")
print("2. 너무 민감하게 감지되는 경우:")
print("   - config.yaml에서 threshold 값들을 높여보세요")
print("   - cooldown 시간을 늘려보세요 (예: 3초)")
print("")
print("3. 낙상 감지가 안되는 경우:")
print("   - 더 급격하게 움직이거나 떨어뜨려보세요")
print("   - config.yaml에서 acceleration_threshold를 낮춰보세요 (예: 1.5)")
print("   - angle_threshold를 낮춰보세요 (예: 30)")
print("")
print("4. 센서 방향을 바꿨을 때:")
print("   - 조이스틱 가운데 버튼을 눌러 재캘리브레이션하세요")
print("   - 중력 벡터가 새로운 방향으로 재설정됩니다")

print("\n✓ 테스트 완료!")
