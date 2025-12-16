"""
Azure Kinect DK SDK 래퍼 클래스
Body Tracking을 사용하여 사람의 관절 위치를 추적합니다.
"""

import logging
import numpy as np
from typing import Optional, Dict, Tuple
from enum import Enum

try:
    from k4a_wrapper import (
        K4ADevice,
        K4ABTTracker,
        K4ABT_TRACKER_PROCESSING_MODE,
        K4A_DEPTH_MODE,
        K4A_COLOR_RESOLUTION,
        K4A_FPS,
        k4a_device_configuration_t,
        device_get_installed_count,
        JointType as K4AJointType,
    )

    K4A_AVAILABLE = True
except Exception as e:
    K4A_AVAILABLE = False
    import traceback

    logging.error(f"Failed to import k4a_wrapper: {e}")
    logging.debug("Detailed traceback:")
    logging.debug(traceback.format_exc())


class JointType(Enum):
    """관절 타입 (Azure Kinect Body Tracking 기준)"""

    PELVIS = 0
    SPINE_NAVAL = 1
    SPINE_CHEST = 2
    NECK = 3
    HEAD = 26

    LEFT_SHOULDER = 5
    LEFT_ELBOW = 6
    LEFT_WRIST = 7
    LEFT_HAND = 8

    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 13
    RIGHT_WRIST = 14
    RIGHT_HAND = 15

    LEFT_HIP = 18
    LEFT_KNEE = 19
    LEFT_ANKLE = 20

    RIGHT_HIP = 22
    RIGHT_KNEE = 23
    RIGHT_ANKLE = 24


class KinectHandler:
    """Azure Kinect DK 핸들러"""

    def __init__(self, config: Dict):
        """
        Args:
            config: 설정 딕셔너리
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.device = None
        self.body_tracker = None
        self.calibration = None
        self.is_running = False

        # Kinect 설정
        self.frame_rate = config.get("kinect", {}).get("frame_rate", 30)
        self.enable_body_tracking = config.get("kinect", {}).get(
            "enable_body_tracking", True
        )

        # 디버그 설정
        self.debug_config = config.get("debug", {})

        if not K4A_AVAILABLE:
            self.logger.warning(
                "k4a_wrapper not available. Handler will run in simulation mode."
            )

    def start(self) -> bool:
        """
        Kinect 디바이스 초기화 및 시작

        Returns:
            성공 여부
        """
        if not K4A_AVAILABLE:
            self.logger.error("Cannot start: k4a_wrapper not available")
            return False

        try:
            # 장치 개수 확인
            device_count = device_get_installed_count()
            self.logger.info(f"Found {device_count} Kinect device(s)")

            if device_count == 0:
                self.logger.error("No Kinect devices detected")
                return False

            # Kinect 디바이스 생성 및 열기
            self.logger.info("Opening Kinect device...")
            self.device = K4ADevice(device_index=0)

            if not self.device.open():
                self.logger.error("Failed to open Kinect device")
                return False

            # 카메라 설정
            config = k4a_device_configuration_t()
            config.color_format = 0  # K4A_IMAGE_FORMAT_COLOR_MJPG
            config.color_resolution = K4A_COLOR_RESOLUTION.OFF
            config.depth_mode = K4A_DEPTH_MODE.NFOV_UNBINNED
            config.camera_fps = K4A_FPS.FPS_30
            config.synchronized_images_only = (
                False  # Color camera OFF이므로 False로 설정
            )
            config.depth_delay_off_color_usec = 0
            config.wired_sync_mode = 0
            config.subordinate_delay_off_master_usec = 0
            config.disable_streaming_indicator = False

            self.logger.info("Starting Kinect cameras...")
            if not self.device.start_cameras(config):
                self.logger.error("Failed to start cameras")
                return False

            if self.enable_body_tracking:
                self.logger.info("Initializing Body Tracking...")

                # Get calibration for body tracking
                self.calibration = self.device.get_calibration(
                    K4A_DEPTH_MODE.NFOV_UNBINNED, K4A_COLOR_RESOLUTION.OFF
                )

                if not self.calibration:
                    self.logger.error("Failed to get calibration")
                    return False

                # Create body tracker
                self.body_tracker = K4ABTTracker(
                    self.calibration, K4ABT_TRACKER_PROCESSING_MODE.GPU
                )

            self.is_running = True
            self.logger.info("✅ Azure Kinect started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start Kinect: {e}")
            import traceback

            traceback.print_exc()
            return False

    def stop(self):
        """Kinect 디바이스 중지"""
        self.is_running = False

        try:
            if self.body_tracker:
                self.body_tracker.destroy()
                self.logger.info("Body tracker stopped")
                self.body_tracker = None

            if self.device:
                self.device.close()
                self.logger.info("Kinect device stopped")
                self.device = None

        except Exception as e:
            self.logger.error(f"Error stopping Kinect: {e}")

    def get_body_frame(self) -> Optional[Dict]:
        """
        Body Tracking 프레임 가져오기

        Returns:
            관절 데이터 딕셔너리 또는 None
            {
                'joints': {joint_id: {'position': (x, y, z), 'confidence': float}},
                'body_id': int,
                'timestamp': int
            }
        """
        if not self.is_running or not self.body_tracker:
            return None

        try:
            # Get capture from device
            capture = self.device.get_capture(timeout_ms=1000)

            if not capture:
                return None

            # Enqueue capture for body tracking
            if not self.body_tracker.enqueue_capture(capture, timeout_ms=0):
                capture.release()
                return None

            # Get body tracking result
            body_frame = self.body_tracker.pop_result(timeout_ms=1000)

            # Release capture
            capture.release()

            if not body_frame:
                return None

            # Check if any bodies detected
            num_bodies = body_frame.get_num_bodies()

            if num_bodies == 0:
                body_frame.release()
                return None

            # Get first body skeleton
            skeleton = body_frame.get_body_skeleton(body_id=0)

            if not skeleton:
                body_frame.release()
                return None

            # Extract joint data
            joint_data = {}
            for joint_id in JointType:
                joint = skeleton.joints[joint_id.value]

                joint_data[joint_id.value] = {
                    "position": (joint.position.x, joint.position.y, joint.position.z),
                    "confidence": joint.confidence_level,
                }

            # Release frame
            body_frame.release()

            return {"joints": joint_data, "body_id": 0, "timestamp": 0}

        except Exception as e:
            self.logger.error(f"Error getting body frame: {e}")
            import traceback

            traceback.print_exc()
            return None

    def get_joint_position(
        self, body_data: Dict, joint_type: JointType
    ) -> Optional[Tuple[float, float, float]]:
        """
        특정 관절의 3D 위치 가져오기

        Args:
            body_data: get_body_frame()의 반환값
            joint_type: 관절 타입

        Returns:
            (x, y, z) 또는 None
        """
        if not body_data or "joints" not in body_data:
            return None

        joints = body_data["joints"]
        joint_id = joint_type.value

        if joint_id not in joints:
            return None

        return joints[joint_id]["position"]

    def get_joint_confidence(
        self, body_data: Dict, joint_type: JointType
    ) -> Optional[float]:
        """
        특정 관절의 신뢰도 가져오기

        Args:
            body_data: get_body_frame()의 반환값
            joint_type: 관절 타입

        Returns:
            신뢰도 (0.0 ~ 1.0) 또는 None
        """
        if not body_data or "joints" not in body_data:
            return None

        joints = body_data["joints"]
        joint_id = joint_type.value

        if joint_id not in joints:
            return None

        return joints[joint_id]["confidence"]

    def is_joint_valid(
        self, body_data: Dict, joint_type: JointType, threshold: float = 0.5
    ) -> bool:
        """
        관절이 유효한지 확인 (신뢰도 기준)

        Args:
            body_data: get_body_frame()의 반환값
            joint_type: 관절 타입
            threshold: 신뢰도 임계값

        Returns:
            유효 여부
        """
        confidence = self.get_joint_confidence(body_data, joint_type)
        return confidence is not None and confidence >= threshold

    def simulate_body_frame(self, posture: str = "standing") -> Dict:
        """
        시뮬레이션용 Body Frame 생성 (테스트용)

        Args:
            posture: 시뮬레이션할 자세 (standing, sitting, lying, left_arm_up, right_arm_up)

        Returns:
            관절 데이터 딕셔너리
        """
        joints = {}

        # 기본 서 있는 자세
        if posture == "standing":
            positions = {
                JointType.HEAD.value: (0, -0.2, 2.0),
                JointType.NECK.value: (0, 0.0, 2.0),
                JointType.SPINE_CHEST.value: (0, 0.2, 2.0),
                JointType.PELVIS.value: (0, 0.8, 2.0),
                JointType.LEFT_SHOULDER.value: (-0.2, 0.1, 2.0),
                JointType.LEFT_ELBOW.value: (-0.3, 0.4, 2.0),
                JointType.LEFT_HAND.value: (-0.3, 0.6, 2.0),
                JointType.RIGHT_SHOULDER.value: (0.2, 0.1, 2.0),
                JointType.RIGHT_ELBOW.value: (0.3, 0.4, 2.0),
                JointType.RIGHT_HAND.value: (0.3, 0.6, 2.0),
                JointType.LEFT_HIP.value: (-0.1, 0.8, 2.0),
                JointType.LEFT_KNEE.value: (-0.1, 1.2, 2.0),
                JointType.LEFT_ANKLE.value: (-0.1, 1.6, 2.0),
                JointType.RIGHT_HIP.value: (0.1, 0.8, 2.0),
                JointType.RIGHT_KNEE.value: (0.1, 1.2, 2.0),
                JointType.RIGHT_ANKLE.value: (0.1, 1.6, 2.0),
            }

        elif posture == "sitting":
            positions = {
                JointType.HEAD.value: (0, 0.2, 2.0),
                JointType.NECK.value: (0, 0.4, 2.0),
                JointType.SPINE_CHEST.value: (0, 0.5, 2.0),
                JointType.PELVIS.value: (0, 0.8, 2.0),
                JointType.LEFT_SHOULDER.value: (-0.2, 0.5, 2.0),
                JointType.LEFT_ELBOW.value: (-0.3, 0.7, 2.0),
                JointType.LEFT_HAND.value: (-0.3, 0.9, 2.0),
                JointType.RIGHT_SHOULDER.value: (0.2, 0.5, 2.0),
                JointType.RIGHT_ELBOW.value: (0.3, 0.7, 2.0),
                JointType.RIGHT_HAND.value: (0.3, 0.9, 2.0),
                JointType.LEFT_HIP.value: (-0.1, 0.8, 2.0),
                JointType.LEFT_KNEE.value: (-0.1, 0.9, 2.0),
                JointType.LEFT_ANKLE.value: (-0.1, 1.2, 2.0),
                JointType.RIGHT_HIP.value: (0.1, 0.8, 2.0),
                JointType.RIGHT_KNEE.value: (0.1, 0.9, 2.0),
                JointType.RIGHT_ANKLE.value: (0.1, 1.2, 2.0),
            }

        elif posture == "lying":
            positions = {
                JointType.HEAD.value: (0, 0.8, 2.0),
                JointType.NECK.value: (0, 0.9, 2.0),
                JointType.SPINE_CHEST.value: (0, 1.0, 2.0),
                JointType.PELVIS.value: (0, 1.2, 2.0),
                JointType.LEFT_SHOULDER.value: (-0.2, 1.0, 2.0),
                JointType.LEFT_ELBOW.value: (-0.3, 1.1, 2.0),
                JointType.LEFT_HAND.value: (-0.4, 1.2, 2.0),
                JointType.RIGHT_SHOULDER.value: (0.2, 1.0, 2.0),
                JointType.RIGHT_ELBOW.value: (0.3, 1.1, 2.0),
                JointType.RIGHT_HAND.value: (0.4, 1.2, 2.0),
                JointType.LEFT_HIP.value: (-0.1, 1.2, 2.0),
                JointType.LEFT_KNEE.value: (-0.1, 1.3, 2.0),
                JointType.LEFT_ANKLE.value: (-0.1, 1.4, 2.0),
                JointType.RIGHT_HIP.value: (0.1, 1.2, 2.0),
                JointType.RIGHT_KNEE.value: (0.1, 1.3, 2.0),
                JointType.RIGHT_ANKLE.value: (0.1, 1.4, 2.0),
            }

        elif posture == "left_arm_up":
            positions = {
                JointType.HEAD.value: (0, -0.2, 2.0),
                JointType.NECK.value: (0, 0.0, 2.0),
                JointType.SPINE_CHEST.value: (0, 0.2, 2.0),
                JointType.PELVIS.value: (0, 0.8, 2.0),
                JointType.LEFT_SHOULDER.value: (-0.2, 0.1, 2.0),
                JointType.LEFT_ELBOW.value: (-0.3, -0.1, 2.0),
                JointType.LEFT_HAND.value: (-0.3, -0.4, 2.0),  # 위로
                JointType.RIGHT_SHOULDER.value: (0.2, 0.1, 2.0),
                JointType.RIGHT_ELBOW.value: (0.3, 0.4, 2.0),
                JointType.RIGHT_HAND.value: (0.3, 0.6, 2.0),
                JointType.LEFT_HIP.value: (-0.1, 0.8, 2.0),
                JointType.LEFT_KNEE.value: (-0.1, 1.2, 2.0),
                JointType.LEFT_ANKLE.value: (-0.1, 1.6, 2.0),
                JointType.RIGHT_HIP.value: (0.1, 0.8, 2.0),
                JointType.RIGHT_KNEE.value: (0.1, 1.2, 2.0),
                JointType.RIGHT_ANKLE.value: (0.1, 1.6, 2.0),
            }

        elif posture == "right_arm_up":
            positions = {
                JointType.HEAD.value: (0, -0.2, 2.0),
                JointType.NECK.value: (0, 0.0, 2.0),
                JointType.SPINE_CHEST.value: (0, 0.2, 2.0),
                JointType.PELVIS.value: (0, 0.8, 2.0),
                JointType.LEFT_SHOULDER.value: (-0.2, 0.1, 2.0),
                JointType.LEFT_ELBOW.value: (-0.3, 0.4, 2.0),
                JointType.LEFT_HAND.value: (-0.3, 0.6, 2.0),
                JointType.RIGHT_SHOULDER.value: (0.2, 0.1, 2.0),
                JointType.RIGHT_ELBOW.value: (0.3, -0.1, 2.0),
                JointType.RIGHT_HAND.value: (0.3, -0.4, 2.0),  # 위로
                JointType.LEFT_HIP.value: (-0.1, 0.8, 2.0),
                JointType.LEFT_KNEE.value: (-0.1, 1.2, 2.0),
                JointType.LEFT_ANKLE.value: (-0.1, 1.6, 2.0),
                JointType.RIGHT_HIP.value: (0.1, 0.8, 2.0),
                JointType.RIGHT_KNEE.value: (0.1, 1.2, 2.0),
                JointType.RIGHT_ANKLE.value: (0.1, 1.6, 2.0),
            }

        else:
            positions = {}

        # 관절 데이터 생성
        for joint_id, position in positions.items():
            joints[joint_id] = {
                "position": position,
                "confidence": 1.0,  # 시뮬레이션에서는 항상 신뢰도 1.0
            }

        return {"joints": joints, "body_id": 0, "timestamp": 0}

    def get_body_frame_with_depth(self) -> Optional[Tuple[Dict, np.ndarray]]:
        """
        Body Tracking 프레임과 depth 이미지 함께 가져오기

        Returns:
            Tuple of (body_data, depth_image_array) or None
        """
        if not self.is_running or not self.body_tracker:
            return None

        try:
            # Get capture from device
            capture = self.device.get_capture(timeout_ms=1000)

            if not capture:
                return None

            # Get depth image first
            depth_image_obj = capture.get_depth_image()
            depth_array = None

            if depth_image_obj:
                depth_array = depth_image_obj.get_buffer()
                depth_image_obj.release()

            # Enqueue capture for body tracking
            if not self.body_tracker.enqueue_capture(capture, timeout_ms=0):
                capture.release()
                return None

            # Get body tracking result
            body_frame = self.body_tracker.pop_result(timeout_ms=1000)

            # Release capture
            capture.release()

            if not body_frame:
                return None

            # Check if any bodies detected
            num_bodies = body_frame.get_num_bodies()

            if num_bodies == 0:
                body_frame.release()
                return None

            # Get first body skeleton
            skeleton = body_frame.get_body_skeleton(body_id=0)

            if not skeleton:
                body_frame.release()
                return None

            # Extract joint data
            joint_data = {}
            for joint_id in JointType:
                joint = skeleton.joints[joint_id.value]

                joint_data[joint_id.value] = {
                    "position": (joint.position.x, joint.position.y, joint.position.z),
                    "confidence": joint.confidence_level,
                }

            # Release frame
            body_frame.release()

            body_data = {"joints": joint_data, "body_id": 0, "timestamp": 0}

            return (body_data, depth_array)

        except Exception as e:
            self.logger.error(f"Error getting body frame with depth: {e}")
            import traceback

            traceback.print_exc()
            return None

    def visualize_skeleton(
        self,
        body_data: Dict,
        depth_image: Optional[np.ndarray] = None,
        current_posture: str = "unknown",
    ) -> Optional[np.ndarray]:
        """
        스켈레톤을 OpenCV로 시각화

        Args:
            body_data: get_body_frame() 또는 get_body_frame_with_depth()의 반환값
            depth_image: Depth 이미지 numpy 배열 (optional)
            current_posture: 현재 감지된 자세 문자열

        Returns:
            시각화된 이미지 (numpy array) 또는 None
        """
        try:
            import cv2

            # Create visualization image
            if depth_image is not None:
                # Normalize depth image to 8-bit for display
                depth_normalized = cv2.normalize(
                    depth_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
                )
                # Apply color map for better visualization
                vis_image = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
            else:
                # Create blank image
                vis_image = np.zeros((480, 640, 3), dtype=np.uint8)

            if not body_data or "joints" not in body_data:
                return vis_image

            joints = body_data["joints"]

            # Define skeleton connections (Azure Kinect body structure)
            # Format: (joint_id_1, joint_id_2)
            skeleton_connections = [
                # Spine
                (JointType.PELVIS.value, JointType.SPINE_NAVAL.value),
                (JointType.SPINE_NAVAL.value, JointType.SPINE_CHEST.value),
                (JointType.SPINE_CHEST.value, JointType.NECK.value),
                (JointType.NECK.value, JointType.HEAD.value),
                # Left arm (direct connection from chest to shoulder)
                (JointType.SPINE_CHEST.value, JointType.LEFT_SHOULDER.value),
                (JointType.LEFT_SHOULDER.value, JointType.LEFT_ELBOW.value),
                (JointType.LEFT_ELBOW.value, JointType.LEFT_WRIST.value),
                (JointType.LEFT_WRIST.value, JointType.LEFT_HAND.value),
                # Right arm (direct connection from chest to shoulder)
                (JointType.SPINE_CHEST.value, JointType.RIGHT_SHOULDER.value),
                (JointType.RIGHT_SHOULDER.value, JointType.RIGHT_ELBOW.value),
                (JointType.RIGHT_ELBOW.value, JointType.RIGHT_WRIST.value),
                (JointType.RIGHT_WRIST.value, JointType.RIGHT_HAND.value),
                # Left leg
                (JointType.PELVIS.value, JointType.LEFT_HIP.value),
                (JointType.LEFT_HIP.value, JointType.LEFT_KNEE.value),
                (JointType.LEFT_KNEE.value, JointType.LEFT_ANKLE.value),
                # Right leg
                (JointType.PELVIS.value, JointType.RIGHT_HIP.value),
                (JointType.RIGHT_HIP.value, JointType.RIGHT_KNEE.value),
                (JointType.RIGHT_KNEE.value, JointType.RIGHT_ANKLE.value),
            ]

            # 3D to 2D projection with perspective
            def project_to_2d(position_3d):
                """Project 3D coordinates to 2D screen coordinates"""
                x, y, z = position_3d

                # Avoid division by zero
                if z <= 0.1:
                    z = 0.1

                # Perspective projection with focal length
                focal_length = 500  # Approximate focal length for Azure Kinect
                screen_x = int(320 + (x * focal_length / z))
                screen_y = int(
                    320 + (y * focal_length / z)
                )  # Adjusted Y offset for alignment

                # Clamp to image bounds to keep points visible
                screen_x = max(0, min(639, screen_x))
                screen_y = max(0, min(479, screen_y))

                return (screen_x, screen_y)

            # Draw skeleton connections
            for joint1_id, joint2_id in skeleton_connections:
                if joint1_id in joints and joint2_id in joints:
                    joint1 = joints[joint1_id]
                    joint2 = joints[joint2_id]

                    # Check confidence
                    if joint1["confidence"] > 0 and joint2["confidence"] > 0:
                        p1 = project_to_2d(joint1["position"])
                        p2 = project_to_2d(joint2["position"])

                        # Draw line
                        cv2.line(vis_image, p1, p2, (0, 255, 0), 2)

            # Draw joint points
            for joint_id, joint_data in joints.items():
                if joint_data["confidence"] > 0:
                    position_2d = project_to_2d(joint_data["position"])

                    # Color based on confidence
                    confidence = joint_data["confidence"]
                    if confidence > 0.8:
                        color = (0, 255, 0)  # Green - high confidence
                    elif confidence > 0.5:
                        color = (0, 255, 255)  # Yellow - medium confidence
                    else:
                        color = (0, 165, 255)  # Orange - low confidence

                    cv2.circle(vis_image, position_2d, 5, color, -1)

            # Display current posture
            posture_labels = {
                "standing": "Standing",
                "sitting": "Sitting",
                "lying": "Lying",
                "left_arm_up": "Left Arm Up",
                "right_arm_up": "Right Arm Up",
                "unknown": "Unknown",
            }

            posture_text = posture_labels.get(current_posture, current_posture)

            # Add text background for readability
            text = f"Posture: {posture_text}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            thickness = 2

            (text_width, text_height), baseline = cv2.getTextSize(
                text, font, font_scale, thickness
            )

            # Draw background rectangle
            cv2.rectangle(
                vis_image,
                (10, 10),
                (10 + text_width + 10, 10 + text_height + baseline + 10),
                (0, 0, 0),
                -1,
            )

            # Draw text
            cv2.putText(
                vis_image,
                text,
                (15, 10 + text_height + 5),
                font,
                font_scale,
                (0, 255, 0),
                thickness,
            )

            return vis_image

        except Exception as e:
            self.logger.error(f"Error visualizing skeleton: {e}")
            import traceback

            traceback.print_exc()
            return None
