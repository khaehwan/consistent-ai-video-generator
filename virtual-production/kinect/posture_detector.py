"""
자세 감지 및 분류 모듈
Azure Kinect Body Tracking 데이터를 기반으로 사용자의 자세를 분류합니다.
"""

import logging
import time
from typing import Optional, Callable, Dict
from enum import Enum
from kinect_handler import KinectHandler, JointType


class PostureType(Enum):
    """감지 가능한 자세 타입"""
    STANDING = "standing"
    SITTING = "sitting"
    LYING = "lying"
    LEFT_ARM_UP = "left_arm_up"
    RIGHT_ARM_UP = "right_arm_up"
    UNKNOWN = "unknown"


class PostureDetector:
    """자세 감지 및 분류 클래스"""

    def __init__(self, config: Dict, kinect_handler: KinectHandler):
        """
        Args:
            config: 설정 딕셔너리
            kinect_handler: Kinect 핸들러 인스턴스
        """
        self.config = config
        self.kinect = kinect_handler
        self.logger = logging.getLogger(__name__)

        # 감지 임계값
        detection_config = config.get('posture_detection', {})
        self.arm_raise_threshold = detection_config.get('arm_raise_threshold', 0.2)
        self.sitting_threshold = detection_config.get('sitting_threshold', 0.5)
        self.lying_threshold = detection_config.get('lying_threshold', 0.3)
        self.joint_confidence_threshold = detection_config.get('joint_confidence_threshold', 0.5)

        # Debounce 설정
        self.debounce_seconds = config.get('kinect', {}).get('debounce_seconds', 0.0)

        # 현재 상태
        self.current_posture = PostureType.UNKNOWN
        self.last_posture_change_time = 0
        self.pending_posture = None
        self.pending_posture_start_time = 0

        # 콜백 함수들
        self.posture_callbacks = []

        # 디버그 설정
        self.debug_config = config.get('debug', {})

    def register_posture_callback(self, callback: Callable[[PostureType, PostureType], None]):
        """
        자세 변경 콜백 등록

        Args:
            callback: 콜백 함수 (new_posture, old_posture) -> None
        """
        self.posture_callbacks.append(callback)

    def detect_posture(self) -> Optional[PostureType]:
        """
        현재 프레임에서 자세 감지

        Returns:
            감지된 자세 또는 None
        """
        # Body frame 가져오기
        body_data = self.kinect.get_body_frame()

        if not body_data:
            return None

        # 디버그: 관절 위치 출력
        if self.debug_config.get('print_joint_positions', False):
            self._print_joint_positions(body_data)

        # 자세 분류 (우선순위: 팔들기 > 누움 > 앉음 > 서있음)
        posture = self._classify_posture(body_data)

        return posture

    def _classify_posture(self, body_data: Dict) -> PostureType:
        """
        관절 데이터를 기반으로 자세 분류

        Args:
            body_data: Kinect 관절 데이터

        Returns:
            분류된 자세
        """
        # 필요한 관절들 확인
        required_joints = [
            JointType.HEAD,
            JointType.NECK,
            JointType.SPINE_CHEST,
            JointType.PELVIS,
            JointType.LEFT_SHOULDER,
            JointType.LEFT_HAND,
            JointType.RIGHT_SHOULDER,
            JointType.RIGHT_HAND,
            JointType.LEFT_HIP,
            JointType.LEFT_KNEE,
            JointType.RIGHT_HIP,
            JointType.RIGHT_KNEE
        ]

        # 모든 필요한 관절이 유효한지 확인
        for joint_type in required_joints:
            if not self.kinect.is_joint_valid(body_data, joint_type, self.joint_confidence_threshold):
                self.logger.debug(f"Joint {joint_type.name} not valid")
                return PostureType.UNKNOWN

        # 1. 팔 들기 확인 (최우선)
        arm_posture = self._check_arm_raise(body_data)
        if arm_posture != PostureType.UNKNOWN:
            return arm_posture

        # 2. 누움 확인
        if self._check_lying(body_data):
            return PostureType.LYING

        # 3. 앉음 확인
        if self._check_sitting(body_data):
            return PostureType.SITTING

        # 4. 기본값: 서있음
        return PostureType.STANDING

    def _check_arm_raise(self, body_data: Dict) -> PostureType:
        """
        팔 들기 확인

        Args:
            body_data: Kinect 관절 데이터

        Returns:
            LEFT_ARM_UP, RIGHT_ARM_UP, 또는 UNKNOWN
        """
        # 왼손과 왼쪽 어깨 위치
        left_hand = self.kinect.get_joint_position(body_data, JointType.LEFT_HAND)
        left_shoulder = self.kinect.get_joint_position(body_data, JointType.LEFT_SHOULDER)

        # 오른손과 오른쪽 어깨 위치
        right_hand = self.kinect.get_joint_position(body_data, JointType.RIGHT_HAND)
        right_shoulder = self.kinect.get_joint_position(body_data, JointType.RIGHT_SHOULDER)

        if not all([left_hand, left_shoulder, right_hand, right_shoulder]):
            return PostureType.UNKNOWN

        # Y축 좌표 비교 (Y가 작을수록 위)
        left_hand_y = left_hand[1]
        left_shoulder_y = left_shoulder[1]
        right_hand_y = right_hand[1]
        right_shoulder_y = right_shoulder[1]

        # 어깨 높이 차이 계산
        shoulder_height = abs(left_shoulder_y - right_shoulder_y)
        threshold_height = shoulder_height * self.arm_raise_threshold if shoulder_height > 0 else self.arm_raise_threshold

        # 왼팔 들기 확인 (손이 어깨보다 위)
        left_arm_raised = (left_shoulder_y - left_hand_y) > threshold_height

        # 오른팔 들기 확인 (손이 어깨보다 위)
        right_arm_raised = (right_shoulder_y - right_hand_y) > threshold_height

        # 디버그 로그
        if self.debug_config.get('print_joint_positions', False):
            self.logger.debug(f"Left arm raised: {left_arm_raised} (hand_y={left_hand_y:.2f}, shoulder_y={left_shoulder_y:.2f})")
            self.logger.debug(f"Right arm raised: {right_arm_raised} (hand_y={right_hand_y:.2f}, shoulder_y={right_shoulder_y:.2f})")

        # 우선순위: 왼팔 > 오른팔 (동시에 들면 왼팔로 감지)
        if left_arm_raised:
            return PostureType.LEFT_ARM_UP
        elif right_arm_raised:
            return PostureType.RIGHT_ARM_UP

        return PostureType.UNKNOWN

    def _check_sitting(self, body_data: Dict) -> bool:
        """
        앉음 자세 확인

        Args:
            body_data: Kinect 관절 데이터

        Returns:
            앉아있는지 여부
        """
        # 필요한 관절 위치
        pelvis = self.kinect.get_joint_position(body_data, JointType.PELVIS)
        left_knee = self.kinect.get_joint_position(body_data, JointType.LEFT_KNEE)
        right_knee = self.kinect.get_joint_position(body_data, JointType.RIGHT_KNEE)
        left_hip = self.kinect.get_joint_position(body_data, JointType.LEFT_HIP)
        right_hip = self.kinect.get_joint_position(body_data, JointType.RIGHT_HIP)

        if not all([pelvis, left_knee, right_knee, left_hip, right_hip]):
            return False

        pelvis_y = pelvis[1]
        avg_knee_y = (left_knee[1] + right_knee[1]) / 2.0
        avg_hip_y = (left_hip[1] + right_hip[1]) / 2.0

        # 전체 신체 높이 계산 (참고용)
        head = self.kinect.get_joint_position(body_data, JointType.HEAD)
        left_ankle = self.kinect.get_joint_position(body_data, JointType.LEFT_ANKLE)
        right_ankle = self.kinect.get_joint_position(body_data, JointType.RIGHT_ANKLE)

        if head and left_ankle and right_ankle:
            max_ankle_y = max(left_ankle[1], right_ankle[1])
            total_body_height = abs(max_ankle_y - head[1])
        else:
            total_body_height = 1.0  # fallback

        # 앉음 감지 조건:
        # 1. 엉덩이/골반이 무릎보다 낮거나 비슷한 높이 (앉으면 엉덩이가 내려감)
        # 2. 무릎-엉덩이 높이 차이가 전체 키의 일정 비율 이하

        # 엉덩이가 무릎보다 얼마나 높은지 (양수면 엉덩이가 위, 음수면 무릎이 위)
        pelvis_above_knee = avg_knee_y - pelvis_y

        # 전체 키 대비 비율로 계산
        height_ratio = abs(pelvis_above_knee) / total_body_height if total_body_height > 0 else 0

        # 앉아있으면: 엉덩이가 무릎과 비슷하거나 살짝 위 (전체 키의 15% 이내)
        is_sitting = height_ratio < self.sitting_threshold

        if self.debug_config.get('print_joint_positions', False):
            self.logger.debug(f"Sitting check: pelvis_y={pelvis_y:.2f}, avg_knee_y={avg_knee_y:.2f}, "
                            f"pelvis_above_knee={pelvis_above_knee:.2f}, height_ratio={height_ratio:.2f}, "
                            f"total_height={total_body_height:.2f}, sitting={is_sitting}")

        return is_sitting

    def _check_lying(self, body_data: Dict) -> bool:
        """
        누움 자세 확인

        Args:
            body_data: Kinect 관절 데이터

        Returns:
            누워있는지 여부
        """
        # 핵심 관절들 (머리-목-척추-엉덩이)
        joints_to_check = [
            JointType.HEAD,
            JointType.NECK,
            JointType.SPINE_CHEST,
            JointType.PELVIS
        ]

        positions = []
        for joint_type in joints_to_check:
            pos = self.kinect.get_joint_position(body_data, joint_type)
            if pos:
                positions.append(pos)

        if len(positions) < 3:  # 최소 3개 관절 필요
            return False

        # Y축 범위 계산 (높이 차이)
        y_coords = [pos[1] for pos in positions]
        y_range = max(y_coords) - min(y_coords)

        # Z축 범위 계산 (깊이 차이 - 앞뒤로 누우면 큼)
        z_coords = [pos[2] for pos in positions]
        z_range = max(z_coords) - min(z_coords)

        # X축 범위 계산 (좌우 차이 - 옆으로 누우면 큼)
        x_coords = [pos[0] for pos in positions]
        x_range = max(x_coords) - min(x_coords)

        # 전체 신체 높이 계산 (서있을 때 기준)
        head = self.kinect.get_joint_position(body_data, JointType.HEAD)
        left_ankle = self.kinect.get_joint_position(body_data, JointType.LEFT_ANKLE)
        right_ankle = self.kinect.get_joint_position(body_data, JointType.RIGHT_ANKLE)

        if head and left_ankle and right_ankle:
            max_ankle_y = max(left_ankle[1], right_ankle[1])
            total_body_height = abs(max_ankle_y - head[1])
        else:
            total_body_height = 1.0  # fallback

        # 누움 판단 조건:
        # 1. Y축 범위가 전체 키의 일정 비율 이하 (몸통이 수평)
        # 2. Z축 또는 X축 범위가 Y축 범위보다 훨씬 큼 (몸이 길게 뻗음)

        y_ratio = y_range / total_body_height if total_body_height > 0 else 1.0
        max_horizontal_range = max(z_range, x_range)

        # 조건 1: Y축 범위가 전체 키의 25% 이하 (몸통이 거의 수평)
        is_horizontal = y_ratio < self.lying_threshold

        # 조건 2: 수평 범위가 수직 범위보다 2배 이상 큼 (몸이 길게 뻗음)
        is_extended = max_horizontal_range > (y_range * 2.0) if y_range > 0 else False

        # 두 조건 중 하나만 만족해도 누움으로 판단
        is_lying = is_horizontal or is_extended

        if self.debug_config.get('print_joint_positions', False):
            self.logger.debug(f"Lying check: y_range={y_range:.2f}, z_range={z_range:.2f}, x_range={x_range:.2f}, "
                            f"y_ratio={y_ratio:.2f}, total_height={total_body_height:.2f}, "
                            f"is_horizontal={is_horizontal}, is_extended={is_extended}, lying={is_lying}")

        return is_lying

    def _print_joint_positions(self, body_data: Dict):
        """디버그용: 주요 관절 위치 출력"""
        joints_to_print = [
            JointType.HEAD,
            JointType.PELVIS,
            JointType.LEFT_SHOULDER,
            JointType.LEFT_HAND,
            JointType.RIGHT_SHOULDER,
            JointType.RIGHT_HAND,
            JointType.LEFT_KNEE,
            JointType.RIGHT_KNEE
        ]

        self.logger.debug("=== Joint Positions ===")
        for joint_type in joints_to_print:
            pos = self.kinect.get_joint_position(body_data, joint_type)
            conf = self.kinect.get_joint_confidence(body_data, joint_type)
            if pos and conf:
                self.logger.debug(f"{joint_type.name}: x={pos[0]:.2f}, y={pos[1]:.2f}, z={pos[2]:.2f}, conf={conf:.2f}")

    def update(self):
        """
        자세 감지 업데이트 (매 프레임마다 호출)
        Debounce 로직 포함
        """
        # 현재 자세 감지
        detected_posture = self.detect_posture()

        if detected_posture is None or detected_posture == PostureType.UNKNOWN:
            return

        current_time = time.time()

        # Debounce가 0이면 즉시 전환
        if self.debounce_seconds <= 0:
            if detected_posture != self.current_posture:
                self._change_posture(detected_posture)
            return

        # Debounce 로직
        if detected_posture != self.current_posture:
            # 새로운 자세가 감지됨
            if detected_posture == self.pending_posture:
                # 이미 대기 중인 자세와 같으면 시간 확인
                elapsed = current_time - self.pending_posture_start_time
                if elapsed >= self.debounce_seconds:
                    # Debounce 시간이 지나면 자세 변경
                    self._change_posture(detected_posture)
                    self.pending_posture = None
            else:
                # 새로운 pending 자세 설정
                self.pending_posture = detected_posture
                self.pending_posture_start_time = current_time
                self.logger.debug(f"Pending posture: {detected_posture.value}")
        else:
            # 현재 자세와 같으면 pending 취소
            self.pending_posture = None

    def _change_posture(self, new_posture: PostureType):
        """
        자세 변경 및 콜백 호출

        Args:
            new_posture: 새로운 자세
        """
        old_posture = self.current_posture
        self.current_posture = new_posture
        self.last_posture_change_time = time.time()

        self.logger.info(f"Posture changed: {old_posture.value} → {new_posture.value}")

        # 콜백 호출
        for callback in self.posture_callbacks:
            try:
                callback(new_posture, old_posture)
            except Exception as e:
                self.logger.error(f"Error in posture callback: {e}")

    def get_current_posture(self) -> PostureType:
        """현재 자세 반환"""
        return self.current_posture
