#!/usr/bin/env python3
"""
Sense HAT 디스플레이 테스트 - 행동별 표시 확인
"""

import sys
import time
import yaml

# Add project root to path
sys.path.insert(0, '.')

from sensors.sense_hat_handler import SenseHatHandler

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("Sense HAT 핸들러 초기화 중...")
sense_hat = SenseHatHandler(config)

if not sense_hat.enabled:
    print("ERROR: Sense HAT이 비활성화되어 있습니다!")
    print("하드웨어 연결을 확인하세요.")
    sys.exit(1)

print("Sense HAT 준비 완료!\n")

# Test all behaviors
behaviors = ['stop', 'walk', 'run', 'fall', 'turn', 'shout', 'dark', 'bright']

print("모든 행동 표시 테스트 시작...\n")

for behavior in behaviors:
    print(f"표시 중: {behavior.upper()}")
    sense_hat.display_behavior(behavior, duration=2.0)
    time.sleep(3)  # 표시 + 대기

print("\n아이콘 테스트...")
for behavior in behaviors:
    print(f"아이콘 표시: {behavior}")
    sense_hat.show_icon(behavior)
    time.sleep(2)

print("\n텍스트 테스트...")
sense_hat.show_text("OK!", color=[0, 255, 0])

print("\n화면 지우기...")
time.sleep(1)
sense_hat.clear_display()

print("\n테스트 완료!")
sense_hat.stop()
