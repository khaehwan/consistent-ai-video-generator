#!/usr/bin/env python3
"""
Dashboard Display 테스트 스크립트
다양한 레이아웃과 상태 변화를 테스트합니다
"""

import sys
import time
import yaml

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler
from utils.dashboard import DashboardDisplay, DashboardLayout

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=" * 60)
print("Dashboard Display Test")
print("=" * 60)

# Initialize Sense HAT
print("\n1. Sense HAT 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    sys.exit(1)

print("✓ Sense HAT 준비 완료!\n")

# Test each layout
layouts = [
    (DashboardLayout.QUAD, "Quad Layout (4x4 quadrants)"),
    (DashboardLayout.STRIP, "Strip Layout (horizontal bars)"),
    (DashboardLayout.COMPACT, "Compact Layout (2x2 indicators)")
]

for layout, description in layouts:
    print(f"\n{'='*60}")
    print(f"테스트: {description}")
    print(f"{'='*60}")

    # Create dashboard
    dashboard = DashboardDisplay(sense_hat, layout)
    dashboard.start()

    print("\n상태 변화 테스트:")

    # Test movement states
    print("  - 움직임: stop → walk → run")
    dashboard.update_movement('stop')
    time.sleep(2)
    dashboard.update_movement('walk')
    time.sleep(2)
    dashboard.update_movement('run')
    time.sleep(2)

    # Test fall
    print("  - 낙상 감지")
    dashboard.update_fall(True)
    time.sleep(2)
    dashboard.update_fall(False)
    time.sleep(1)

    # Test turn
    print("  - 회전 감지")
    dashboard.update_turn(True)
    time.sleep(2)
    dashboard.update_turn(False)
    time.sleep(1)

    # Test shout
    print("  - 소리 감지")
    dashboard.update_shout(True)
    time.sleep(2)
    dashboard.update_shout(False)
    time.sleep(1)

    # Test brightness
    print("  - 밝기 변화: dark → normal → bright")
    dashboard.update_brightness('dark')
    time.sleep(2)
    dashboard.update_brightness('normal')
    time.sleep(2)
    dashboard.update_brightness('bright')
    time.sleep(2)

    # Test combined states
    print("  - 복합 상태 (run + fall + shout)")
    dashboard.update_movement('run')
    dashboard.update_fall(True)
    dashboard.update_shout(True)
    time.sleep(3)

    # Reset
    print("  - 상태 초기화")
    dashboard.update_movement('stop')
    dashboard.update_fall(False)
    dashboard.update_shout(False)
    dashboard.update_turn(False)
    dashboard.update_brightness('normal')
    time.sleep(2)

    # Stop dashboard
    dashboard.stop()
    time.sleep(1)

print("\n" + "=" * 60)
print("모든 레이아웃 테스트 완료!")
print("=" * 60)

# Final test: Flash indicators
print("\n보너스: 개별 인디케이터 플래시 테스트")
dashboard = DashboardDisplay(sense_hat, DashboardLayout.QUAD)
dashboard.start()

indicators = ['movement', 'fall', 'turn', 'shout', 'brightness']
for indicator in indicators:
    print(f"  - {indicator} 플래시")
    dashboard.flash_indicator(indicator, duration=0.5)
    time.sleep(1)

dashboard.stop()

# Show current states
print("\n현재 대시보드 상태:")
states = dashboard.get_current_states()
for key, value in states.items():
    print(f"  {key}: {value}")

print("\n✓ 테스트 완료!")
sense_hat.stop()
