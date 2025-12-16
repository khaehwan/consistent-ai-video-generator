#!/usr/bin/env python3
"""
LED Display 테스트 스크립트
새로운 zone-based LED 디스플레이를 테스트합니다
"""

import sys
import time
import yaml

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from utils.led_display import LEDDisplay

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=" * 60)
print("LED Display Test - Zone-based Layout")
print("=" * 60)
print("\nLED 매트릭스 레이아웃:")
print("Row 0-1: 움직임 상태 (녹색=정지, 노란색=걷기, 주황색=달리기)")
print("Row 2-3: 이벤트 인디케이터")
print("  - Col 0-1: 낙상 (빨강=감지, 어두운 녹색=정상)")
print("  - Col 2-3: 회전 (빨강=감지, 어두운 녹색=정상)")
print("  - Col 4-5: 소리 (빨강=감지, 어두운 녹색=정상)")
print("Row 4-5: 밝기 레벨 (어두운 회색/회색/흰색)")
print("Row 6-7: 시스템 상태 (중앙 4픽셀)")
print("=" * 60)

# Initialize Sense HAT
print("\n1. Sense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

print("✓ Sense HAT 준비 완료!\n")

# Create LED display
print("2. LED Display 생성 중...")
led_display = LEDDisplay(sense_hat)
print("✓ LED Display 준비 완료!\n")

# Show startup animation
print("3. 시작 애니메이션...")
led_display.show_startup_animation()
time.sleep(1)

# Start LED display
print("4. LED Display 시작...")
led_display.start()
time.sleep(0.5)
print("✓ LED Display 시작됨 (20Hz 업데이트)\n")

print("=" * 60)
print("상태 변화 테스트 시작")
print("=" * 60)

# Test movement states
print("\n[1/8] 움직임 상태 테스트")
print("  - STOP (녹색)")
led_display.update_movement('stop')
time.sleep(2)

print("  - WALK (노란색)")
led_display.update_movement('walk')
time.sleep(2)

print("  - RUN (주황색)")
led_display.update_movement('run')
time.sleep(2)

# Test fall event
print("\n[2/8] 낙상 이벤트 테스트")
print("  - 낙상 감지 (빨간색으로 3초간 표시)")
led_display.flash_event('fall', duration=3.0)
time.sleep(3.5)

# Test turn event
print("\n[3/8] 회전 이벤트 테스트")
print("  - 회전 감지 (빨간색으로 2초간 표시)")
led_display.flash_event('turn', duration=2.0)
time.sleep(2.5)

# Test shout event
print("\n[4/8] 소리 이벤트 테스트")
print("  - 소리 감지 (빨간색으로 1초간 표시)")
led_display.flash_event('shout', duration=1.0)
time.sleep(1.5)

# Test brightness states
print("\n[5/8] 밝기 상태 테스트")
print("  - DARK (어두운 회색)")
led_display.update_brightness('dark')
time.sleep(2)

print("  - NORMAL (회색)")
led_display.update_brightness('normal')
time.sleep(2)

print("  - BRIGHT (흰색)")
led_display.update_brightness('bright')
time.sleep(2)

# Test system status
print("\n[6/8] 시스템 상태 테스트")
print("  - WARNING (어두운 노란색)")
led_display.update_system_status('warning')
time.sleep(2)

print("  - OK (어두운 녹색)")
led_display.update_system_status('ok')
time.sleep(2)

# Test combined states
print("\n[7/8] 복합 상태 테스트")
print("  - 달리기 + 모든 이벤트 활성 + 밝음")
led_display.update_movement('run')
led_display.update_fall(True)
led_display.update_turn(True)
led_display.update_shout(True)
led_display.update_brightness('bright')
time.sleep(4)

print("  - 상태 초기화")
led_display.update_movement('stop')
led_display.update_fall(False)
led_display.update_turn(False)
led_display.update_shout(False)
led_display.update_brightness('normal')
time.sleep(2)

# Run full test sequence
print("\n[8/8] 전체 테스트 시퀀스 실행")
led_display.test_display()

# Show current states
print("\n" + "=" * 60)
print("현재 LED Display 상태:")
print("=" * 60)
states = led_display.get_states()
for key, value in states.items():
    print(f"  {key:12s}: {value}")

# Show message test
print("\n메시지 표시 테스트...")
led_display.show_message("OK!", color=[0, 255, 0], duration=2.0)

# Stop display
print("\nLED Display 종료 중...")
led_display.stop()

print("\n" + "=" * 60)
print("✓ 모든 테스트 완료!")
print("=" * 60)

sense_hat.stop()
