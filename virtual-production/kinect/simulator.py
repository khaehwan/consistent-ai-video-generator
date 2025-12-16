"""
Kinect 시뮬레이터 - Kinect 없이 자세 감지 테스트
키보드 입력으로 자세를 수동으로 전환합니다.
"""

import logging
import threading
import time
from typing import Optional, Callable
from posture_detector import PostureType


class KinectSimulator:
    """Kinect 시뮬레이터 - 키보드 입력으로 자세 제어"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_posture = PostureType.STANDING
        self.callbacks = []
        self.is_running = False
        self.input_thread = None

    def register_callback(self, callback: Callable[[PostureType, PostureType], None]):
        """자세 변경 콜백 등록"""
        self.callbacks.append(callback)

    def start(self):
        """시뮬레이터 시작"""
        self.is_running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        self.logger.info("✅ Kinect Simulator started")

    def _input_loop(self):
        """키보드 입력 루프"""
        print("\n" + "=" * 60)
        print("Kinect Simulator - Keyboard Controls:")
        print("=" * 60)
        print("  1: standing (서있음)")
        print("  2: sitting (앉음)")
        print("  3: lying (누움)")
        print("  4: left_arm_up (왼팔 들기)")
        print("  5: right_arm_up (오른팔 들기)")
        print("  q: quit")
        print("=" * 60)
        print()

        while self.is_running:
            try:
                user_input = input("자세 선택 (1-5, q): ").strip().lower()

                if user_input == 'q':
                    self.logger.info("Quit command received")
                    break
                elif user_input == '1':
                    self._change_posture(PostureType.STANDING)
                elif user_input == '2':
                    self._change_posture(PostureType.SITTING)
                elif user_input == '3':
                    self._change_posture(PostureType.LYING)
                elif user_input == '4':
                    self._change_posture(PostureType.LEFT_ARM_UP)
                elif user_input == '5':
                    self._change_posture(PostureType.RIGHT_ARM_UP)
                else:
                    print("잘못된 입력입니다. 1-5 또는 q를 입력하세요.")

            except EOFError:
                break
            except Exception as e:
                self.logger.error(f"Input error: {e}")

    def _change_posture(self, new_posture: PostureType):
        """자세 변경 및 콜백 호출"""
        if new_posture == self.current_posture:
            print(f"이미 {new_posture.value} 자세입니다.")
            return

        old_posture = self.current_posture
        self.current_posture = new_posture

        print(f"🔄 자세 변경: {old_posture.value} → {new_posture.value}")
        self.logger.info(f"Posture changed: {old_posture.value} → {new_posture.value}")

        # 콜백 호출
        for callback in self.callbacks:
            try:
                callback(new_posture, old_posture)
            except Exception as e:
                self.logger.error(f"Error in callback: {e}")

    def stop(self):
        """시뮬레이터 중지"""
        self.is_running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1)
        self.logger.info("Simulator stopped")

    def get_current_posture(self) -> PostureType:
        """현재 자세 반환"""
        return self.current_posture


class AutoSimulator:
    """자동 시뮬레이터 - 자세를 자동으로 순환"""

    def __init__(self, interval: float = 5.0):
        """
        Args:
            interval: 자세 변경 간격 (초)
        """
        self.logger = logging.getLogger(__name__)
        self.interval = interval
        self.current_posture = PostureType.STANDING
        self.callbacks = []
        self.is_running = False
        self.auto_thread = None

        # 자세 순서
        self.postures = [
            PostureType.STANDING,
            PostureType.SITTING,
            PostureType.LYING,
            PostureType.LEFT_ARM_UP,
            PostureType.RIGHT_ARM_UP
        ]
        self.posture_index = 0

    def register_callback(self, callback: Callable[[PostureType, PostureType], None]):
        """자세 변경 콜백 등록"""
        self.callbacks.append(callback)

    def start(self):
        """시뮬레이터 시작"""
        self.is_running = True
        self.auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
        self.auto_thread.start()
        self.logger.info(f"✅ Auto Simulator started (interval: {self.interval}s)")
        print(f"\n자동 시뮬레이터 시작 - {self.interval}초마다 자세 변경\n")

    def _auto_loop(self):
        """자동 자세 변경 루프"""
        while self.is_running:
            time.sleep(self.interval)

            if not self.is_running:
                break

            # 다음 자세로 변경
            self.posture_index = (self.posture_index + 1) % len(self.postures)
            new_posture = self.postures[self.posture_index]

            old_posture = self.current_posture
            self.current_posture = new_posture

            print(f"🔄 [자동] 자세 변경: {old_posture.value} → {new_posture.value}")
            self.logger.info(f"Auto posture change: {old_posture.value} → {new_posture.value}")

            # 콜백 호출
            for callback in self.callbacks:
                try:
                    callback(new_posture, old_posture)
                except Exception as e:
                    self.logger.error(f"Error in callback: {e}")

    def stop(self):
        """시뮬레이터 중지"""
        self.is_running = False
        if self.auto_thread and self.auto_thread.is_alive():
            self.auto_thread.join(timeout=2)
        self.logger.info("Auto simulator stopped")

    def get_current_posture(self) -> PostureType:
        """현재 자세 반환"""
        return self.current_posture


# 간단한 테스트
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    def on_posture_change(new_posture, old_posture):
        print(f"콜백: {old_posture.value} → {new_posture.value}")

    # 키보드 모드
    print("=== Keyboard Simulator Test ===")
    sim = KinectSimulator()
    sim.register_callback(on_posture_change)
    sim.start()

    try:
        while sim.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n종료합니다...")

    sim.stop()
