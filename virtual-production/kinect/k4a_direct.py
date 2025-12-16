"""
Azure Kinect SDK 직접 ctypes 래퍼
pykinect_azure가 작동하지 않을 때 사용
"""
import ctypes
import os
import sys

# SDK 경로
SDK_PATH = r"C:\Program Files\Azure Kinect SDK v1.4.2\sdk\windows-desktop\amd64\release\bin"

# PATH에 추가
os.environ['PATH'] = SDK_PATH + ';' + os.environ.get('PATH', '')

try:
    # k4a.dll 로드
    k4a_dll = ctypes.CDLL(os.path.join(SDK_PATH, 'k4a.dll'))
    print("✅ k4a.dll loaded successfully with ctypes!")

    # k4a_device_get_installed_count 함수 정의
    k4a_device_get_installed_count = k4a_dll.k4a_device_get_installed_count
    k4a_device_get_installed_count.restype = ctypes.c_uint32

    # 장치 개수 확인
    device_count = k4a_device_get_installed_count()
    print(f"Detected {device_count} Kinect device(s)")

    if device_count > 0:
        print("✅ Direct ctypes wrapper works!")
        print()
        print("This confirms that:")
        print("1. DLL files are OK")
        print("2. SDK installation is OK")
        print("3. The problem is ONLY in pykinect_azure package")
        print()
        print("Solution: Reinstall pykinect-azure or use this direct wrapper")
    else:
        print("⚠️  No devices detected")
        print("Check USB connection")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
