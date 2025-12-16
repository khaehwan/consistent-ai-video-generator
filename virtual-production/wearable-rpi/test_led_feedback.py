#!/usr/bin/env python3
"""
LED 피드백 애니메이션 테스트
조이스틱 버튼 재캘리브레이션 시 LED 피드백 확인
"""

import sys
import time
import yaml

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from utils.led_display import LEDDisplay

print("=" * 70)
print("LED 피드백 애니메이션 테스트")
print("=" * 70)
print("\n이 테스트는 재캘리브레이션 완료 시 LED 피드백을 확인합니다.")

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
print("✓ Sense HAT 준비 완료!")

# Initialize LED Display
led_display = LEDDisplay(sense_hat)
print("✓ LED Display 준비 완료!")

print("\n" + "=" * 70)
print("테스트 항목")
print("=" * 70)

print("\n1. 시작 애니메이션")
print("   LED 매트릭스의 각 행을 순서대로 테스트합니다.")
input("   Enter를 눌러 시작...")
led_display.show_startup_animation()
print("   ✓ 완료!")

print("\n2. 캘리브레이션 완료 애니메이션")
print("   노란색 플래시 → 초록색 체크마크 → 페이드아웃")
input("   Enter를 눌러 시작...")
led_display.show_calibration_complete()
print("   ✓ 완료!")

print("\n3. 조이스틱 버튼 테스트")
print("   조이스틱 가운데 버튼을 누르면 캘리브레이션 애니메이션이 표시됩니다.")
print("   (Ctrl+C로 종료)")

# Joystick callback
def on_joystick_middle():
    """조이스틱 중앙 버튼 콜백"""
    print("\n🔘 조이스틱 중앙 버튼 눌림!")
    print("   캘리브레이션 애니메이션 표시 중...")
    led_display.show_calibration_complete()
    print("   ✓ 애니메이션 완료!")

# Register joystick callback
sense_hat.register_joystick_callback('middle', on_joystick_middle)
print("\n조이스틱 콜백 등록 완료!")
print("조이스틱 가운데 버튼을 눌러보세요...")

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\n프로그램 종료...")

# Cleanup
sense_hat.stop()
print("\n✓ 테스트 완료!")