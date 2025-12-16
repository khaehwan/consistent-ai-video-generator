#!/usr/bin/env python3
"""
자력계(Magnetometer) 기능 테스트
Sense HAT의 자력계와 나침반 기능을 테스트합니다
"""

import sys
import time
import yaml

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler

print("=" * 70)
print("자력계(Magnetometer) 기능 테스트")
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
print("✓ Sense HAT 준비 완료!\n")

print("=" * 70)
print("센서 지원 확인")
print("=" * 70)

# Check if magnetometer methods exist
has_magnetometer = hasattr(sense_hat, 'get_magnetometer')
has_compass = hasattr(sense_hat, 'get_compass')
has_raw_magnetometer = hasattr(sense_hat, 'get_magnetometer_raw')
has_raw_compass = hasattr(sense_hat, 'get_compass_raw')

print(f"get_magnetometer() 메서드: {'✓ 있음' if has_magnetometer else '✗ 없음'}")
print(f"get_compass() 메서드: {'✓ 있음' if has_compass else '✗ 없음'}")
print(f"get_magnetometer_raw() 메서드: {'✓ 있음' if has_raw_magnetometer else '✗ 없음'}")
print(f"get_compass_raw() 메서드: {'✓ 있음' if has_raw_compass else '✗ 없음'}")

if not has_magnetometer or not has_compass:
    print("\n⚠️  경고: 필요한 메서드가 누락되었습니다!")
    print("SenseHatHandler에 자력계 지원을 추가해야 합니다.")

print("\n" + "=" * 70)
print("자력계 데이터 읽기 테스트")
print("=" * 70)

# Test reading magnetometer data
try:
    # Test magnetometer
    print("\n1. get_magnetometer() 테스트:")
    mag = sense_hat.get_magnetometer()
    print(f"   자기장: X={mag['x']:.2f}µT, Y={mag['y']:.2f}µT, Z={mag['z']:.2f}µT")

    # Test raw magnetometer
    print("\n2. get_magnetometer_raw() 테스트:")
    mag_raw = sense_hat.get_magnetometer_raw()
    print(f"   원시값: X={mag_raw['x']:.2f}, Y={mag_raw['y']:.2f}, Z={mag_raw['z']:.2f}")

    # Test compass
    print("\n3. get_compass() 테스트:")
    compass = sense_hat.get_compass()
    print(f"   방위각: {compass:.1f}°")

    # Test raw compass
    print("\n4. get_compass_raw() 테스트:")
    compass_raw = sense_hat.get_compass_raw()
    print(f"   원시 방위각: {compass_raw:.1f}°")

    print("\n✓ 모든 테스트 통과!")

except AttributeError as e:
    print(f"\n✗ AttributeError 발생: {e}")
    print("SenseHatHandler에 자력계 메서드가 구현되지 않았습니다.")

except Exception as e:
    print(f"\n✗ 예외 발생: {e}")

print("\n" + "=" * 70)
print("실시간 모니터링 (Ctrl+C로 종료)")
print("=" * 70)
print("\n라즈베리파이를 회전시켜 보세요.")
print("자력계 값과 나침반 방위가 변화합니다.\n")

# Display header
print("-" * 70)
print(f"{'시간':^10} | {'자기장 X':^10} | {'자기장 Y':^10} | {'자기장 Z':^10} | {'방위':^8}")
print("-" * 70)

try:
    while True:
        # Get sensor data
        mag = sense_hat.get_magnetometer()
        compass = sense_hat.get_compass()

        # Current time
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Direction names
        directions = {
            (337.5, 360): "북(N)",
            (0, 22.5): "북(N)",
            (22.5, 67.5): "북동(NE)",
            (67.5, 112.5): "동(E)",
            (112.5, 157.5): "남동(SE)",
            (157.5, 202.5): "남(S)",
            (202.5, 247.5): "남서(SW)",
            (247.5, 292.5): "서(W)",
            (292.5, 337.5): "북서(NW)"
        }

        direction = "?"
        for (low, high), name in directions.items():
            if low <= compass < high or (low > high and (compass >= low or compass < high)):
                direction = name
                break

        print(f"{timestamp:^10} | {mag['x']:>9.2f} | {mag['y']:>9.2f} | {mag['z']:>9.2f} | {compass:>6.1f}° {direction}")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n\n프로그램 종료...")

# Cleanup
sense_hat.stop()

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)

print("\n문제 해결:")
print("1. AttributeError가 발생한 경우:")
print("   - SenseHatHandler에 자력계 메서드를 추가해야 합니다")
print("   - sense_hat_handler.py 파일을 업데이트하세요")
print("")
print("2. 자력계 값이 0으로 나오는 경우:")
print("   - Sense HAT v2가 제대로 연결되었는지 확인하세요")
print("   - i2cdetect -y 1 명령으로 I2C 장치를 확인하세요")
print("")
print("3. 나침반이 부정확한 경우:")
print("   - 자석이나 금속 물체에서 멀리 떨어뜨리세요")
print("   - 캘리브레이션이 필요할 수 있습니다")

print("\n✓ 완료!")