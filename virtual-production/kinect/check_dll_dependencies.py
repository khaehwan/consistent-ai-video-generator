"""
DLL 의존성 확인 스크립트
"""
import os
import sys
import ctypes

print("=" * 60)
print("DLL Dependencies Check")
print("=" * 60)
print()

# SDK 경로
sdk_versions = ['v1.4.2', 'v1.4.1', 'v1.4.0']
found_sdk_version = None

for version in sdk_versions:
    sdk_path = rf"C:\Program Files\Azure Kinect SDK {version}"
    if os.path.exists(sdk_path):
        found_sdk_version = version
        break

if not found_sdk_version:
    print("❌ SDK not found")
    sys.exit(1)

sdk_path = rf"C:\Program Files\Azure Kinect SDK {found_sdk_version}"
bin_path = os.path.join(sdk_path, r"sdk\windows-desktop\amd64\release\bin")

print(f"SDK Path: {sdk_path}")
print(f"Bin Path: {bin_path}")
print()

# DLL 직접 로드 테스트
print("Testing DLL loading with ctypes:")
print()

dll_files = [
    'k4a.dll',
    'k4arecord.dll',
    'depthengine_2_0.dll'
]

for dll_name in dll_files:
    dll_path = os.path.join(bin_path, dll_name)
    print(f"Testing {dll_name}...")
    print(f"  Path: {dll_path}")
    print(f"  Exists: {os.path.exists(dll_path)}")

    try:
        # PATH에 bin 폴더 추가
        os.environ['PATH'] = bin_path + ';' + os.environ.get('PATH', '')

        # DLL 로드 시도
        dll = ctypes.CDLL(dll_path)
        print(f"  ✅ Successfully loaded with ctypes")
    except Exception as e:
        print(f"  ❌ Failed to load: {e}")
        print()
        print("  This error usually means:")
        print("  - Visual C++ Redistributable not installed")
        print("  - Missing dependent DLLs")
        print("  - CUDA runtime not installed (for Body Tracking)")
        print()
        print("  Solution:")
        print("  1. Install Visual C++ Redistributable 2015-2022 (x64)")
        print("     Download: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        print("  2. Restart your computer")
        print()

    print()

print("=" * 60)
