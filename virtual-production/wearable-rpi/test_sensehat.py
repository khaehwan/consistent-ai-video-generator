#!/usr/bin/env python3
"""
Sense HAT 테스트 스크립트
"""

import time

try:
    from sense_hat import SenseHat

    print("Sense HAT 초기화 중...")
    sense = SenseHat()

    print("1. LED 매트릭스 테스트 - 빨간색 화면")
    sense.clear([255, 0, 0])
    time.sleep(2)

    print("2. LED 매트릭스 테스트 - 녹색 화면")
    sense.clear([0, 255, 0])
    time.sleep(2)

    print("3. LED 매트릭스 테스트 - 파란색 화면")
    sense.clear([0, 0, 255])
    time.sleep(2)

    print("4. 텍스트 표시 테스트")
    sense.show_message("TEST", text_colour=[255, 255, 255], scroll_speed=0.05)

    print("5. 화면 지우기")
    sense.clear()

    print("\n테스트 완료!")
    print("LED가 표시되었나요? (y/n)")

except ImportError:
    print("ERROR: sense-hat 라이브러리를 찾을 수 없습니다.")
    print("설치: sudo apt-get install sense-hat")
    print("또는: pip install sense-hat")

except Exception as e:
    print(f"ERROR: {e}")
    print("\n가능한 원인:")
    print("1. Sense HAT이 제대로 연결되지 않음")
    print("2. I2C가 활성화되지 않음 (sudo raspi-config에서 활성화)")
    print("3. 권한 문제 (sudo로 실행 시도)")
