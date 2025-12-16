"""
Azure Kinect 자세 감지 및 Virtual Production 연동 메인 프로그램
"""

import logging
import yaml
import time
import signal
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from kinect_handler import KinectHandler
from posture_detector import PostureDetector, PostureType
from websocket_client import KinectWebSocketClient
from simulator import KinectSimulator, AutoSimulator


class KinectVPSystem:
    """Kinect Virtual Production 시스템 메인 클래스"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: 설정 파일 경로
        """
        # 설정 로드
        self.config = self._load_config(config_path)

        # 로깅 설정
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # 시뮬레이션 모드 확인
        simulation_config = self.config.get('simulation', {})
        self.use_simulator = simulation_config.get('enabled', False)
        self.auto_mode = simulation_config.get('auto_mode', False)
        self.auto_interval = simulation_config.get('auto_interval', 5.0)

        # 컴포넌트 초기화
        self.kinect_handler = None
        self.posture_detector = None
        self.simulator = None
        self.ws_client = KinectWebSocketClient(self.config)

        # 실행 상태
        self.is_running = False

        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("🚀 Kinect VP System initialized")

    def _load_config(self, config_path: str) -> dict:
        """
        설정 파일 로드

        Args:
            config_path: 설정 파일 경로

        Returns:
            설정 딕셔너리
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _setup_logging(self):
        """로깅 설정"""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file = log_config.get('file', 'kinect.log')
        log_console = log_config.get('console', True)
        max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
        backup_count = log_config.get('backup_count', 3)

        # 로그 레벨 설정
        level = getattr(logging, log_level.upper(), logging.INFO)

        # 포맷 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 파일 핸들러
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 콘솔 핸들러
        if log_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

    def _signal_handler(self, signum, frame):
        """
        시그널 핸들러

        Args:
            signum: 시그널 번호
            frame: 프레임
        """
        self.logger.info(f"Signal {signum} received, shutting down...")
        self.stop()
        sys.exit(0)

    def _on_posture_change(self, new_posture: PostureType, old_posture: PostureType):
        """
        자세 변경 콜백

        Args:
            new_posture: 새로운 자세
            old_posture: 이전 자세
        """
        self.logger.info(f"🔄 Posture changed: {old_posture.value} → {new_posture.value}")

        # WebSocket으로 이벤트 전송
        metadata = {
            'previous_posture': old_posture.value,
            'sensor_type': 'azure_kinect'
        }

        success = self.ws_client.send_posture_event(new_posture.value, metadata)

        if not success:
            self.logger.warning("Failed to send posture event via WebSocket")

    def start(self):
        """시스템 시작"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Kinect VP System")
        self.logger.info("=" * 60)

        # 시뮬레이션 모드 확인
        if self.use_simulator:
            self.logger.info("🎮 Running in SIMULATION mode (configured)")
            return self._start_simulator()

        # Kinect 실제 연결 시도
        self.logger.info("1. Starting Azure Kinect...")
        self.kinect_handler = KinectHandler(self.config)

        if not self.kinect_handler.start():
            self.logger.error("❌ Failed to start Kinect")
            self.logger.error("")
            self.logger.error("Please check:")
            self.logger.error("  1. Kinect is connected to USB 3.0 port")
            self.logger.error("  2. Azure Kinect SDK is installed")
            self.logger.error("  3. Environment variables are set (run: setup_environment.bat)")
            self.logger.error("  4. Run 'python check_installation.py' for diagnosis")
            self.logger.error("")
            self.logger.error("To use simulation mode, set 'simulation.enabled: true' in config.yaml")
            return False

        # Kinect 연결 성공 - Posture Detector 초기화
        self.logger.info("✅ Kinect started successfully")
        self.posture_detector = PostureDetector(self.config, self.kinect_handler)

        # WebSocket 연결
        self.logger.info("2. Connecting to VP server via WebSocket...")
        self.ws_client.connect()

        # 자세 변경 콜백 등록
        self.posture_detector.register_posture_callback(self._on_posture_change)

        # 연결 대기
        self.logger.info("3. Waiting for WebSocket connection...")
        for i in range(10):
            if self.ws_client.is_connected():
                break
            time.sleep(1)
            self.logger.info(f"   Waiting... ({i+1}/10)")

        if not self.ws_client.is_connected():
            self.logger.warning("⚠️ WebSocket not connected, but continuing...")

        # 메인 루프 시작
        self.logger.info("=" * 60)
        self.logger.info("✅ System started successfully (Real Kinect)")
        self.logger.info("=" * 60)
        self.logger.info("")
        self.logger.info("Detecting postures:")
        self.logger.info("  - standing: 서있음")
        self.logger.info("  - sitting: 앉음")
        self.logger.info("  - lying: 누움")
        self.logger.info("  - left_arm_up: 왼팔 들기")
        self.logger.info("  - right_arm_up: 오른팔 들기")
        self.logger.info("")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 60)

        self.is_running = True
        self._main_loop()

        return True

    def _start_simulator(self):
        """시뮬레이터 모드로 시작"""
        self.logger.info("=" * 60)
        self.logger.info("Starting in SIMULATOR mode")
        self.logger.info("=" * 60)

        # WebSocket 연결
        self.logger.info("1. Connecting to VP server via WebSocket...")
        self.ws_client.connect()

        # 시뮬레이터 모드 선택
        if self.auto_mode:
            self.logger.info(f"2. Starting Auto Simulator (interval: {self.auto_interval}s)...")
            self.simulator = AutoSimulator(interval=self.auto_interval)
        else:
            self.logger.info("2. Starting Keyboard Simulator...")
            self.simulator = KinectSimulator()

        # 콜백 등록
        self.simulator.register_callback(self._on_posture_change)

        # 시뮬레이터 시작
        self.simulator.start()

        # 연결 대기
        self.logger.info("3. Waiting for WebSocket connection...")
        for i in range(10):
            if self.ws_client.is_connected():
                break
            time.sleep(1)
            self.logger.info(f"   Waiting... ({i+1}/10)")

        if not self.ws_client.is_connected():
            self.logger.warning("⚠️ WebSocket not connected, but continuing...")

        # 완료
        self.logger.info("=" * 60)
        mode_text = "Auto" if self.auto_mode else "Keyboard"
        self.logger.info(f"✅ System started successfully ({mode_text} Simulator)")
        self.logger.info("=" * 60)

        self.is_running = True

        # 키보드 모드는 시뮬레이터가 블로킹하므로 대기만
        if not self.auto_mode:
            self._wait_for_simulator()
        else:
            self._main_loop_auto_simulator()

        return True

    def _main_loop(self):
        """메인 감지 루프"""
        frame_count = 0
        last_stats_time = time.time()
        stats_interval = 10.0  # 10초마다 통계 출력

        # 시각화 설정 확인
        debug_config = self.config.get('debug', {})
        show_skeleton = debug_config.get('show_skeleton', False)

        if show_skeleton:
            import cv2
            self.logger.info("🎨 Skeleton visualization enabled")
            window_name = "Kinect Skeleton Visualization"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 640, 480)

        while self.is_running:
            try:
                # 자세 감지 업데이트 (항상 실행)
                self.posture_detector.update()

                # 시각화 추가 처리
                if show_skeleton:
                    # depth 이미지와 함께 body 데이터 가져오기 (시각화용)
                    result = self.kinect_handler.get_body_frame_with_depth()

                    if result:
                        body_data, depth_image = result

                        # 현재 자세 가져오기
                        current_posture = self.posture_detector.get_current_posture()

                        # 스켈레톤 시각화
                        vis_image = self.kinect_handler.visualize_skeleton(
                            body_data,
                            depth_image,
                            current_posture.value
                        )

                        if vis_image is not None:
                            cv2.imshow(window_name, vis_image)

                    # OpenCV 이벤트 처리 (필수)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # 'q' 또는 ESC
                        self.logger.info("Visualization window closed")
                        break

                frame_count += 1

                # 통계 출력
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    current_posture = self.posture_detector.get_current_posture()
                    ws_stats = self.ws_client.get_statistics()

                    self.logger.info("=" * 60)
                    self.logger.info("System Status:")
                    self.logger.info(f"  Current posture: {current_posture.value}")
                    self.logger.info(f"  Frames processed: {frame_count}")
                    self.logger.info(f"  WebSocket connected: {ws_stats['connected']}")
                    self.logger.info(f"  Events sent: {ws_stats['events_sent']}")
                    self.logger.info(f"  Events failed: {ws_stats['events_failed']}")
                    if show_skeleton:
                        self.logger.info(f"  Visualization: Enabled (Press 'q' to close)")
                    self.logger.info("=" * 60)

                    last_stats_time = current_time

                # 프레임 레이트 조절 (30 FPS)
                if not show_skeleton:
                    time.sleep(1.0 / 30.0)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(1.0)

        # 종료 시 OpenCV 윈도우 정리
        if show_skeleton:
            import cv2
            cv2.destroyAllWindows()
            self.logger.info("Visualization windows closed")

    def _wait_for_simulator(self):
        """키보드 시뮬레이터 대기 (블로킹)"""
        try:
            while self.is_running and self.simulator.is_running:
                time.sleep(0.5)

                # 주기적으로 통계 출력
                if hasattr(self, '_last_sim_stats_time'):
                    if time.time() - self._last_sim_stats_time >= 30.0:
                        ws_stats = self.ws_client.get_statistics()
                        self.logger.info(f"📊 Events sent: {ws_stats['events_sent']}, Failed: {ws_stats['events_failed']}")
                        self._last_sim_stats_time = time.time()
                else:
                    self._last_sim_stats_time = time.time()

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")

    def _main_loop_auto_simulator(self):
        """자동 시뮬레이터 메인 루프"""
        last_stats_time = time.time()
        stats_interval = 10.0

        while self.is_running:
            try:
                # 통계 출력
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    current_posture = self.simulator.get_current_posture()
                    ws_stats = self.ws_client.get_statistics()

                    self.logger.info("=" * 60)
                    self.logger.info("System Status (Auto Simulator):")
                    self.logger.info(f"  Current posture: {current_posture.value}")
                    self.logger.info(f"  WebSocket connected: {ws_stats['connected']}")
                    self.logger.info(f"  Events sent: {ws_stats['events_sent']}")
                    self.logger.info(f"  Events failed: {ws_stats['events_failed']}")
                    self.logger.info("=" * 60)

                    last_stats_time = current_time

                time.sleep(1.0)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in simulator loop: {e}", exc_info=True)
                time.sleep(1.0)

    def stop(self):
        """시스템 중지"""
        self.logger.info("Stopping Kinect VP System...")

        self.is_running = False

        # Kinect 중지
        if self.kinect_handler:
            self.kinect_handler.stop()

        # 시뮬레이터 중지
        if self.simulator:
            self.simulator.stop()

        # WebSocket 닫기
        self.ws_client.close()

        self.logger.info("✅ System stopped")

    def get_status(self) -> dict:
        """
        시스템 상태 반환

        Returns:
            상태 딕셔너리
        """
        return {
            'running': self.is_running,
            'kinect_running': self.kinect_handler.is_running,
            'websocket_connected': self.ws_client.is_connected(),
            'current_posture': self.posture_detector.get_current_posture().value,
            'websocket_stats': self.ws_client.get_statistics()
        }


def main():
    """메인 함수"""
    print("=" * 60)
    print("Azure Kinect Virtual Production System")
    print("=" * 60)
    print()

    # 설정 파일 경로
    config_path = Path(__file__).parent / "config.yaml"

    try:
        # 시스템 생성 및 시작
        system = KinectVPSystem(str(config_path))
        system.start()

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Please create config.yaml file")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
