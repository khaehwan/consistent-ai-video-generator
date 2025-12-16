#!/usr/bin/env python3
"""
자이로스코프 원시 데이터 모니터링
회전 감지 문제를 디버깅하기 위한 간단한 스크립트
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

print("=" * 80)
print("자이로스코프 원시 데이터 모니터링")
print("=" * 80)

# Initialize Sense HAT
print("\nSense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

sense_hat.start()
time.sleep(0.5)
print("✓ 준비 완료!\n")

print("=" * 80)
print("실시간 센서 데이터 (Ctrl+C로 종료)")
print("=" * 80)
print("\n센서를 천천히 회전시켜 보세요. 각 축의 각속도 변화를 관찰하세요.")
print("- X축(Pitch): 앞뒤 회전 (고개 끄덕임)")
print("- Y축(Roll):  좌우 회전 (고개 갸우뚱)")
print("- Z축(Yaw):   수평 회전 (고개 좌우 돌림) ← 뒤돌아보기는 이것을 사용\n")

# Display header
print("-" * 80)
print(f"{'시간':^12} | {'Pitch(X)':^12} | {'Roll(Y)':^12} | {'Yaw(Z)':^12} | {'Yaw 각도':^12}")
print("-" * 80)

# Track max values
max_values = {'x': 0, 'y': 0, 'z': 0}
samples = []

try:
    counter = 0
    while running:
        # Get sensor data
        gyro = sense_hat.get_gyroscope()
        orientation = sense_hat.get_orientation()

        if gyro and orientation:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Update max values
            max_values['x'] = max(max_values['x'], abs(gyro['x']))
            max_values['y'] = max(max_values['y'], abs(gyro['y']))
            max_values['z'] = max(max_values['z'], abs(gyro['z']))

            # Format values
            x_str = f"{gyro['x']:+7.1f}°/s"
            y_str = f"{gyro['y']:+7.1f}°/s"
            z_str = f"{gyro['z']:+7.1f}°/s"
            yaw_str = f"{orientation['yaw']:>7.1f}°"

            # Highlight high values
            if abs(gyro['z']) > 30:
                z_str = f"→{z_str}←"  # Mark high yaw velocity

            print(f"{timestamp:^12} | {x_str:^12} | {y_str:^12} | {z_str:^12} | {yaw_str:^12}")

            # Store sample
            samples.append({
                'time': time.time(),
                'gyro': gyro.copy(),
                'yaw': orientation['yaw']
            })

            # Keep only last 60 samples (2 seconds at 30Hz)
            if len(samples) > 60:
                samples.pop(0)

            counter += 1

            # Reprint header every 20 lines
            if counter % 20 == 0:
                print("-" * 80)
                print(f"{'시간':^12} | {'Pitch(X)':^12} | {'Roll(Y)':^12} | {'Yaw(Z)':^12} | {'Yaw 각도':^12}")
                print("-" * 80)

        time.sleep(0.1)  # 10 Hz update rate

except KeyboardInterrupt:
    pass

# Cleanup
print("\n\n" + "=" * 80)
print("테스트 종료")
print("=" * 80)

sense_hat.stop()

# Print summary
print("\n측정된 최대 각속도:")
print(f"  X축(Pitch): {max_values['x']:.1f}°/s")
print(f"  Y축(Roll):  {max_values['y']:.1f}°/s")
print(f"  Z축(Yaw):   {max_values['z']:.1f}°/s")

# Analyze recent data for turn detection
if len(samples) >= 10:
    print("\n최근 데이터 분석:")

    # Calculate total yaw change
    if len(samples) > 1:
        yaw_start = samples[0]['yaw']
        yaw_end = samples[-1]['yaw']
        yaw_change = yaw_end - yaw_start

        # Normalize to -180 to 180
        if yaw_change > 180:
            yaw_change -= 360
        elif yaw_change < -180:
            yaw_change += 360

        duration = samples[-1]['time'] - samples[0]['time']
        avg_velocity = yaw_change / duration if duration > 0 else 0

        print(f"  최근 {duration:.1f}초 동안 요(Yaw) 변화: {yaw_change:+.1f}°")
        print(f"  평균 회전 속도: {avg_velocity:+.1f}°/s")

        # Check if it would have triggered turn detection
        high_velocity_count = sum(1 for s in samples if abs(s['gyro']['z']) > 30)
        print(f"  높은 각속도 샘플(>30°/s): {high_velocity_count}/{len(samples)}")

        if abs(yaw_change) >= 160 and high_velocity_count > 5:
            print("\n  ✓ 이 데이터는 뒤돌아보기로 감지되었을 것입니다!")
        else:
            print("\n  ✗ 이 데이터는 감지 조건을 충족하지 못했습니다.")
            if abs(yaw_change) < 160:
                print(f"     - 회전 각도 부족: {abs(yaw_change):.1f}° < 160°")
            if high_velocity_count <= 5:
                print(f"     - 각속도가 충분히 높지 않음: {high_velocity_count} 샘플만 30°/s 초과")

print("\n디버깅 팁:")
print("1. Z축(Yaw) 각속도가 30°/s 이상 나오는지 확인하세요")
print("   - 더 빠르게 회전해야 합니다")
print("")
print("2. 총 Yaw 각도 변화가 160° 이상인지 확인하세요")
print("   - 거의 180도 회전해야 합니다")
print("")
print("3. 회전이 2초 안에 완료되는지 확인하세요")
print("   - 너무 천천히 돌면 타임아웃됩니다")

print("\n✓ 테스트 완료!")
