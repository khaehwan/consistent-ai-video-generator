"""
Azure Kinect SDK 직접 ctypes 래퍼
pykinect_azure를 대체하는 간단한 구현
"""
import ctypes
import os
import sys
from enum import IntEnum
from typing import Optional

# SDK 경로 설정
SDK_VERSIONS = ['v1.4.2', 'v1.4.1', 'v1.4.0']
SDK_PATH = None
BT_SDK_PATH = r"C:\Program Files\Azure Kinect Body Tracking SDK"

# 각 버전 확인하면서 상세 정보 수집
checked_paths = []
for version in SDK_VERSIONS:
    path = rf"C:\Program Files\Azure Kinect SDK {version}\sdk\windows-desktop\amd64\release\bin"
    checked_paths.append(path)
    if os.path.exists(path):
        SDK_PATH = path
        break

if not SDK_PATH:
    error_msg = "Azure Kinect SDK not found!\n\nChecked paths:\n"
    for path in checked_paths:
        error_msg += f"  - {path}\n"
    error_msg += "\nPlease install Azure Kinect SDK from:\n"
    error_msg += "https://learn.microsoft.com/en-us/azure/kinect-dk/sensor-sdk-download"
    raise RuntimeError(error_msg)

# PATH에 추가
os.environ['PATH'] = SDK_PATH + ';' + os.environ.get('PATH', '')
if os.path.exists(BT_SDK_PATH):
    # Body Tracking SDK bin 경로들 추가
    bt_bin_paths = [
        os.path.join(BT_SDK_PATH, r"sdk\windows-desktop\amd64\release\bin"),
        os.path.join(BT_SDK_PATH, r"sdk\netstandard2.0\publish"),
        os.path.join(BT_SDK_PATH, r"tools"),
    ]
    for bt_bin in bt_bin_paths:
        if os.path.exists(bt_bin):
            os.environ['PATH'] = bt_bin + ';' + os.environ.get('PATH', '')

# DLL 로드
try:
    k4a = ctypes.CDLL(os.path.join(SDK_PATH, 'k4a.dll'))
except Exception as e:
    raise RuntimeError(f"Failed to load k4a.dll: {e}")

# Body Tracking DLL 로드 (선택적)
k4abt = None
BT_AVAILABLE = False
try:
    # 여러 경로 시도
    bt_dll_paths = [
        os.path.join(BT_SDK_PATH, r"sdk\windows-desktop\amd64\release\bin\k4abt.dll"),
        os.path.join(BT_SDK_PATH, r"sdk\netstandard2.0\publish\k4abt.dll"),
        os.path.join(BT_SDK_PATH, r"tools\k4abt.dll"),
        r"C:\Program Files\Azure Kinect Body Tracking SDK\sdk\windows-desktop\amd64\release\bin\k4abt.dll",
    ]

    for dll_path in bt_dll_paths:
        if os.path.exists(dll_path):
            k4abt = ctypes.CDLL(dll_path)
            BT_AVAILABLE = True
            print(f"✓ Body Tracking SDK loaded from: {dll_path}")
            break

    if not BT_AVAILABLE:
        print("Warning: Body Tracking SDK not found. Body tracking features will not be available.")
        print("Checked paths:")
        for path in bt_dll_paths:
            print(f"  - {path}")
except Exception as e:
    print(f"Warning: Failed to load Body Tracking DLL: {e}")
    print("Body tracking features will not be available.")


# Enums
class K4A_RESULT(IntEnum):
    SUCCEEDED = 0
    FAILED = 1


class K4A_WAIT_RESULT(IntEnum):
    SUCCEEDED = 0
    FAILED = 1
    TIMEOUT = 2


class K4A_DEPTH_MODE(IntEnum):
    OFF = 0
    NFOV_2X2BINNED = 1
    NFOV_UNBINNED = 2
    WFOV_2X2BINNED = 3
    WFOV_UNBINNED = 4


class K4A_COLOR_RESOLUTION(IntEnum):
    OFF = 0
    RES_720P = 1
    RES_1080P = 2
    RES_1440P = 3
    RES_1536P = 4
    RES_2160P = 5
    RES_3072P = 6


class K4A_FPS(IntEnum):
    FPS_5 = 0
    FPS_15 = 1
    FPS_30 = 2


class K4ABT_TRACKER_PROCESSING_MODE(IntEnum):
    GPU = 0
    CPU = 1
    GPU_CUDA = 2
    GPU_DIRECTML = 3
    GPU_TENSORRT = 4


class K4ABT_JOINT_ID(IntEnum):
    PELVIS = 0
    SPINE_NAVAL = 1
    SPINE_CHEST = 2
    NECK = 3
    CLAVICLE_LEFT = 4
    SHOULDER_LEFT = 5
    ELBOW_LEFT = 6
    WRIST_LEFT = 7
    HAND_LEFT = 8
    HANDTIP_LEFT = 9
    THUMB_LEFT = 10
    CLAVICLE_RIGHT = 11
    SHOULDER_RIGHT = 12
    ELBOW_RIGHT = 13
    WRIST_RIGHT = 14
    HAND_RIGHT = 15
    HANDTIP_RIGHT = 16
    THUMB_RIGHT = 17
    HIP_LEFT = 18
    KNEE_LEFT = 19
    ANKLE_LEFT = 20
    FOOT_LEFT = 21
    HIP_RIGHT = 22
    KNEE_RIGHT = 23
    ANKLE_RIGHT = 24
    FOOT_RIGHT = 25
    HEAD = 26
    NOSE = 27
    EYE_LEFT = 28
    EAR_LEFT = 29
    EYE_RIGHT = 30
    EAR_RIGHT = 31
    COUNT = 32


# Structures
class k4a_device_configuration_t(ctypes.Structure):
    _fields_ = [
        ("color_format", ctypes.c_int),
        ("color_resolution", ctypes.c_int),
        ("depth_mode", ctypes.c_int),
        ("camera_fps", ctypes.c_int),
        ("synchronized_images_only", ctypes.c_bool),
        ("depth_delay_off_color_usec", ctypes.c_int32),
        ("wired_sync_mode", ctypes.c_int),
        ("subordinate_delay_off_master_usec", ctypes.c_uint32),
        ("disable_streaming_indicator", ctypes.c_bool),
    ]


class k4a_float3_t(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
    ]


class k4a_quaternion_t(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("w", ctypes.c_float),
    ]


class k4abt_joint_t(ctypes.Structure):
    _fields_ = [
        ("position", k4a_float3_t),
        ("orientation", k4a_quaternion_t),
        ("confidence_level", ctypes.c_int),
    ]


class k4abt_skeleton_t(ctypes.Structure):
    _fields_ = [
        ("joints", k4abt_joint_t * 32),  # K4ABT_JOINT_COUNT
    ]


class k4abt_body_t(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("skeleton", k4abt_skeleton_t),
    ]


# Function definitions
k4a.k4a_device_get_installed_count.restype = ctypes.c_uint32
k4a.k4a_device_get_installed_count.argtypes = []

k4a.k4a_device_open.restype = ctypes.c_int
k4a.k4a_device_open.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]

k4a.k4a_device_close.restype = None
k4a.k4a_device_close.argtypes = [ctypes.c_void_p]

k4a.k4a_device_start_cameras.restype = ctypes.c_int
k4a.k4a_device_start_cameras.argtypes = [ctypes.c_void_p, ctypes.POINTER(k4a_device_configuration_t)]

k4a.k4a_device_stop_cameras.restype = None
k4a.k4a_device_stop_cameras.argtypes = [ctypes.c_void_p]

k4a.k4a_device_get_capture.restype = ctypes.c_int
k4a.k4a_device_get_capture.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_int32]

k4a.k4a_capture_release.restype = None
k4a.k4a_capture_release.argtypes = [ctypes.c_void_p]

# Image functions for depth/color access
k4a.k4a_capture_get_depth_image.restype = ctypes.c_void_p
k4a.k4a_capture_get_depth_image.argtypes = [ctypes.c_void_p]

k4a.k4a_image_release.restype = None
k4a.k4a_image_release.argtypes = [ctypes.c_void_p]

k4a.k4a_image_get_buffer.restype = ctypes.POINTER(ctypes.c_uint8)
k4a.k4a_image_get_buffer.argtypes = [ctypes.c_void_p]

k4a.k4a_image_get_size.restype = ctypes.c_size_t
k4a.k4a_image_get_size.argtypes = [ctypes.c_void_p]

k4a.k4a_image_get_width_pixels.restype = ctypes.c_int
k4a.k4a_image_get_width_pixels.argtypes = [ctypes.c_void_p]

k4a.k4a_image_get_height_pixels.restype = ctypes.c_int
k4a.k4a_image_get_height_pixels.argtypes = [ctypes.c_void_p]

k4a.k4a_image_get_stride_bytes.restype = ctypes.c_int
k4a.k4a_image_get_stride_bytes.argtypes = [ctypes.c_void_p]

# Body Tracking functions (only if available)
if BT_AVAILABLE and k4abt:
    k4abt.k4abt_tracker_create.restype = ctypes.c_int
    k4abt.k4abt_tracker_create.argtypes = [
        ctypes.c_void_p,  # k4a_calibration_t* (simplified)
        ctypes.c_void_p,  # k4abt_tracker_configuration_t*
        ctypes.POINTER(ctypes.c_void_p)  # k4abt_tracker_t*
    ]

    k4abt.k4abt_tracker_destroy.restype = None
    k4abt.k4abt_tracker_destroy.argtypes = [ctypes.c_void_p]

    k4abt.k4abt_tracker_enqueue_capture.restype = ctypes.c_int
    k4abt.k4abt_tracker_enqueue_capture.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]

    k4abt.k4abt_tracker_pop_result.restype = ctypes.c_int
    k4abt.k4abt_tracker_pop_result.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_int32]

    k4abt.k4abt_frame_release.restype = None
    k4abt.k4abt_frame_release.argtypes = [ctypes.c_void_p]

    k4abt.k4abt_frame_get_num_bodies.restype = ctypes.c_uint32
    k4abt.k4abt_frame_get_num_bodies.argtypes = [ctypes.c_void_p]

    k4abt.k4abt_frame_get_body_skeleton.restype = ctypes.c_int
    k4abt.k4abt_frame_get_body_skeleton.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(k4abt_skeleton_t)]

k4a.k4a_device_get_calibration.restype = ctypes.c_int
k4a.k4a_device_get_calibration.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,  # depth_mode
    ctypes.c_int,  # color_resolution
    ctypes.c_void_p  # calibration*
]


# Wrapper classes
class K4ADevice:
    """Azure Kinect Device wrapper"""

    def __init__(self, device_index: int = 0):
        self.device_handle = ctypes.c_void_p()
        self.device_index = device_index
        self.is_open = False
        self.is_started = False

    def open(self) -> bool:
        """Open device"""
        result = k4a.k4a_device_open(self.device_index, ctypes.byref(self.device_handle))
        self.is_open = (result == K4A_RESULT.SUCCEEDED)
        return self.is_open

    def close(self):
        """Close device"""
        if self.is_open and self.device_handle:
            if self.is_started:
                self.stop_cameras()
            k4a.k4a_device_close(self.device_handle)
            self.is_open = False

    def start_cameras(self, config: Optional[k4a_device_configuration_t] = None) -> bool:
        """Start cameras with configuration"""
        if not config:
            config = k4a_device_configuration_t()
            config.color_format = 0  # K4A_IMAGE_FORMAT_COLOR_MJPG
            config.color_resolution = K4A_COLOR_RESOLUTION.OFF
            config.depth_mode = K4A_DEPTH_MODE.NFOV_UNBINNED
            config.camera_fps = K4A_FPS.FPS_30
            config.synchronized_images_only = True
            config.depth_delay_off_color_usec = 0
            config.wired_sync_mode = 0
            config.subordinate_delay_off_master_usec = 0
            config.disable_streaming_indicator = False

        result = k4a.k4a_device_start_cameras(self.device_handle, ctypes.byref(config))
        self.is_started = (result == K4A_RESULT.SUCCEEDED)
        return self.is_started

    def stop_cameras(self):
        """Stop cameras"""
        if self.is_started:
            k4a.k4a_device_stop_cameras(self.device_handle)
            self.is_started = False

    def get_capture(self, timeout_ms: int = 1000):
        """Get a capture"""
        capture = ctypes.c_void_p()
        result = k4a.k4a_device_get_capture(self.device_handle, ctypes.byref(capture), timeout_ms)

        if result == K4A_WAIT_RESULT.SUCCEEDED:
            return K4ACapture(capture)
        return None

    def get_calibration(self, depth_mode: int, color_resolution: int):
        """Get device calibration (needed for body tracking)"""
        # Allocate calibration structure (simplified - 4KB buffer)
        calibration = ctypes.create_string_buffer(4096)
        result = k4a.k4a_device_get_calibration(
            self.device_handle,
            depth_mode,
            color_resolution,
            calibration
        )
        if result == K4A_RESULT.SUCCEEDED:
            return calibration
        return None


class K4AImage:
    """Image wrapper for depth/color images"""

    def __init__(self, image_handle):
        self.image_handle = image_handle

    def get_buffer(self):
        """Get image buffer as numpy array"""
        if not self.image_handle:
            return None

        try:
            import numpy as np

            # Get image properties
            width = k4a.k4a_image_get_width_pixels(self.image_handle)
            height = k4a.k4a_image_get_height_pixels(self.image_handle)
            stride = k4a.k4a_image_get_stride_bytes(self.image_handle)
            size = k4a.k4a_image_get_size(self.image_handle)

            # Get buffer pointer
            buffer = k4a.k4a_image_get_buffer(self.image_handle)

            if not buffer:
                return None

            # Convert to numpy array (depth is 16-bit)
            # Depth image is typically uint16
            data = np.ctypeslib.as_array(buffer, shape=(size,))

            # Reshape to 2D array (depth images are single channel, 16-bit)
            # stride is in bytes, depth pixel is 2 bytes
            img = np.frombuffer(data, dtype=np.uint16).reshape((height, width))

            return img.copy()  # Return a copy to avoid memory issues

        except Exception as e:
            print(f"Error converting image to numpy: {e}")
            return None

    def get_width(self) -> int:
        """Get image width"""
        if self.image_handle:
            return k4a.k4a_image_get_width_pixels(self.image_handle)
        return 0

    def get_height(self) -> int:
        """Get image height"""
        if self.image_handle:
            return k4a.k4a_image_get_height_pixels(self.image_handle)
        return 0

    def release(self):
        """Release image"""
        if self.image_handle:
            k4a.k4a_image_release(self.image_handle)
            self.image_handle = None

    def __del__(self):
        self.release()


class K4ACapture:
    """Capture wrapper"""

    def __init__(self, capture_handle):
        self.capture_handle = capture_handle

    def get_depth_image(self):
        """Get depth image from capture"""
        if not self.capture_handle:
            return None

        depth_image_handle = k4a.k4a_capture_get_depth_image(self.capture_handle)

        if depth_image_handle:
            return K4AImage(depth_image_handle)
        return None

    def release(self):
        """Release capture"""
        if self.capture_handle:
            k4a.k4a_capture_release(self.capture_handle)
            self.capture_handle = None

    def __del__(self):
        self.release()


class K4ABTTracker:
    """Body Tracking Tracker wrapper"""

    def __init__(self, calibration, processing_mode: int = K4ABT_TRACKER_PROCESSING_MODE.GPU):
        if not BT_AVAILABLE or not k4abt:
            raise RuntimeError("Body Tracking SDK not available")

        self.tracker_handle = ctypes.c_void_p()

        # Create tracker configuration (simplified)
        config = ctypes.create_string_buffer(64)  # Placeholder
        ctypes.memset(config, 0, 64)
        # First int in config is processing_mode
        ctypes.cast(config, ctypes.POINTER(ctypes.c_int))[0] = processing_mode

        result = k4abt.k4abt_tracker_create(calibration, config, ctypes.byref(self.tracker_handle))

        if result != K4A_RESULT.SUCCEEDED:
            raise RuntimeError(f"Failed to create body tracker: {result}")

    def enqueue_capture(self, capture: K4ACapture, timeout_ms: int = 0) -> bool:
        """Enqueue a capture for processing"""
        result = k4abt.k4abt_tracker_enqueue_capture(
            self.tracker_handle,
            capture.capture_handle,
            timeout_ms
        )
        return result == K4A_WAIT_RESULT.SUCCEEDED

    def pop_result(self, timeout_ms: int = 1000):
        """Pop body tracking result"""
        frame = ctypes.c_void_p()
        result = k4abt.k4abt_tracker_pop_result(
            self.tracker_handle,
            ctypes.byref(frame),
            timeout_ms
        )

        if result == K4A_WAIT_RESULT.SUCCEEDED:
            return K4ABTFrame(frame)
        return None

    def destroy(self):
        """Destroy tracker"""
        if self.tracker_handle:
            k4abt.k4abt_tracker_destroy(self.tracker_handle)
            self.tracker_handle = None

    def __del__(self):
        self.destroy()


class K4ABTFrame:
    """Body Tracking Frame wrapper"""

    def __init__(self, frame_handle):
        self.frame_handle = frame_handle

    def get_num_bodies(self) -> int:
        """Get number of bodies in frame"""
        return k4abt.k4abt_frame_get_num_bodies(self.frame_handle)

    def get_body_skeleton(self, body_id: int = 0):
        """Get skeleton for body"""
        skeleton = k4abt_skeleton_t()
        result = k4abt.k4abt_frame_get_body_skeleton(
            self.frame_handle,
            body_id,
            ctypes.byref(skeleton)
        )

        if result == K4A_RESULT.SUCCEEDED:
            return skeleton
        return None

    def release(self):
        """Release frame"""
        if self.frame_handle:
            k4abt.k4abt_frame_release(self.frame_handle)
            self.frame_handle = None

    def __del__(self):
        self.release()


# Utility functions
def device_get_installed_count() -> int:
    """Get number of installed Kinect devices"""
    return k4a.k4a_device_get_installed_count()


# Export joint enum for easy access
JointType = K4ABT_JOINT_ID
