"""
Azure Kinect 설치 상태 확인 스크립트
"""

import sys
import os

print("=" * 60)
print("Azure Kinect Installation Check")
print("=" * 60)
print()

# 1. Python 버전 및 아키텍처 확인
print("1. Python Version:")
print(f"   {sys.version}")
print(f"   {'✅ OK' if sys.version_info >= (3, 8) else '❌ Need Python 3.8+'}")

import platform
is_64bit = platform.machine().endswith('64')
print(f"   Architecture: {platform.machine()} ({'64-bit' if is_64bit else '32-bit'})")
if not is_64bit:
    print("   ⚠️  WARNING: Azure Kinect SDK requires 64-bit Python!")
print()

# 2. 필수 패키지 확인
print("2. Required Packages:")
packages = {
    'pykinect_azure': 'pykinect-azure',
    'cv2': 'opencv-python',
    'numpy': 'numpy',
    'websocket': 'websocket-client',
    'yaml': 'PyYAML'
}

missing_packages = []
for module_name, package_name in packages.items():
    try:
        __import__(module_name)
        print(f"   ✅ {package_name}")
    except ImportError:
        print(f"   ❌ {package_name} (NOT INSTALLED)")
        missing_packages.append(package_name)

print()

# 3. Azure Kinect SDK 경로 확인
print("3. Azure Kinect SDK:")

# 여러 버전 확인
sdk_versions = ['v1.4.2', 'v1.4.1', 'v1.4.0']
found_sdk_version = None
found_bt_sdk = False

for version in sdk_versions:
    sdk_path = rf"C:\Program Files\Azure Kinect SDK {version}"
    if os.path.exists(sdk_path):
        found_sdk_version = version
        print(f"   ✅ Azure Kinect SDK {version} found")

        # 하위 경로 확인
        bin_path = os.path.join(sdk_path, r"sdk\windows-desktop\amd64\release\bin")
        tools_path = os.path.join(sdk_path, "tools")

        if os.path.exists(bin_path):
            print(f"      ✅ bin folder: {bin_path}")
        else:
            print(f"      ❌ bin folder not found")

        if os.path.exists(tools_path):
            print(f"      ✅ tools folder: {tools_path}")
        else:
            print(f"      ❌ tools folder not found")
        break

if not found_sdk_version:
    print(f"   ❌ Azure Kinect SDK not found (checked versions: {', '.join(sdk_versions)})")
    print("      Download: https://learn.microsoft.com/en-us/azure/kinect-dk/sensor-sdk-download")

# Body Tracking SDK 확인
bt_sdk_path = r"C:\Program Files\Azure Kinect Body Tracking SDK"
if os.path.exists(bt_sdk_path):
    found_bt_sdk = True
    print(f"   ✅ Body Tracking SDK found")

    tools_path = os.path.join(bt_sdk_path, "tools")
    if os.path.exists(tools_path):
        print(f"      ✅ tools folder: {tools_path}")
    else:
        print(f"      ❌ tools folder not found")
else:
    print(f"   ❌ Body Tracking SDK not found")
    print("      Download: https://learn.microsoft.com/en-us/azure/kinect-dk/body-sdk-download")

print()

# 4. 환경 변수 확인
print("4. System PATH:")
system_path = os.environ.get('PATH', '')
sdk_paths_in_env = [p for p in system_path.split(';') if 'Azure Kinect' in p]

if sdk_paths_in_env:
    print("   ✅ Azure Kinect paths found in current PATH:")
    for p in sdk_paths_in_env:
        print(f"      {p}")
else:
    print("   ❌ Azure Kinect NOT in current PATH")
    print()
    print("   You need to add SDK bin folder to PATH:")
    if found_sdk_version:
        sdk_path = rf"C:\Program Files\Azure Kinect SDK {found_sdk_version}"
        bin_path = rf"{sdk_path}\sdk\windows-desktop\amd64\release\bin"
        print(f"      {bin_path}")
    print()
    print("   Run: setup_environment.bat")

print()

# 4-1. DLL 파일 존재 확인
print("4-1. DLL Files Check:")
if found_sdk_version:
    sdk_path = rf"C:\Program Files\Azure Kinect SDK {found_sdk_version}"
    bin_path = os.path.join(sdk_path, r"sdk\windows-desktop\amd64\release\bin")

    dll_files = ['k4a.dll', 'k4arecord.dll', 'depthengine_2_0.dll']

    for dll_name in dll_files:
        dll_path = os.path.join(bin_path, dll_name)
        if os.path.exists(dll_path):
            print(f"   ✅ {dll_name} found")
        else:
            print(f"   ❌ {dll_name} NOT found at {bin_path}")
else:
    print("   ⚠️  SDK not found, cannot check DLL files")

print()

# 5. PyKinect Azure 테스트
print("5. PyKinect Azure Import Test:")
try:
    import pykinect_azure as pykinect
    print("   ✅ pykinect_azure imported successfully")

    # 버전 확인
    if hasattr(pykinect, '__version__'):
        print(f"   Version: {pykinect.__version__}")

except ImportError as e:
    print(f"   ❌ Failed to import: {e}")
    print()
    print("   To install pykinect-azure:")
    print("   1. Install Visual C++ Redistributable 2015-2019")
    print("   2. Install Azure Kinect SDK")
    print("   3. Install Body Tracking SDK")
    print("   4. pip install pykinect-azure")
except Exception as e:
    print(f"   ⚠️  Import warning: {e}")

print()

# 6. Kinect 장치 감지 테스트
print("6. Kinect Device Detection:")
try:
    import pykinect_azure as pykinect
    from pykinect_azure.k4a import _k4a

    # _k4a 객체 확인 (더 안전한 방식)
    if _k4a is None or not hasattr(_k4a, 'k4a_device_get_installed_count'):
        print("   ❌ _k4a module is None or DLL functions not loaded")
        print()
        print("   >>> This means Azure Kinect SDK DLL files are NOT loaded! <<<")
        print()
        print("   Root Cause:")
        print("   - The pykinect-azure package imported successfully")
        print("   - But the underlying k4a.dll is not in your PATH")
        print()
        print("   ✅ SOLUTION (Choose ONE):")
        print()
        print("   Option A - Temporary (for this session only):")
        print("   1. Run: setup_environment.bat")
        print("   2. In the SAME CMD window that opens, run:")
        print("      python check_installation.py")
        print()
        print("   Option B - Permanent:")
        print("   1. Open: System Properties > Environment Variables")
        print("   2. Edit System 'Path' variable")
        print("   3. Add this path:")
        for version in sdk_versions:
            sdk_path = rf"C:\Program Files\Azure Kinect SDK {version}"
            if os.path.exists(sdk_path):
                print(f"      {sdk_path}\\sdk\\windows-desktop\\amd64\\release\\bin")
                break
        print("   4. Restart your computer")
        print()
        print("   Current PATH status:")
        current_path = os.environ.get('PATH', '')
        sdk_paths = [p for p in current_path.split(';') if 'Azure Kinect' in p]
        if sdk_paths:
            print("   ✅ Azure Kinect found in PATH:")
            for p in sdk_paths:
                print(f"      {p}")
            print("   (But DLLs still not loaded - try restarting Python)")
        else:
            print("   ❌ Azure Kinect SDK is NOT in current PATH")
    else:
        # DLL이 로드되었다고 판단 - 장치 개수 확인
        try:
            device_count = _k4a.k4a_device_get_installed_count()
            print(f"   Detected devices: {device_count}")

            if device_count > 0:
                print("   ✅ Kinect device detected!")
            else:
                print("   ❌ No Kinect devices found")
                print()
                print("   Troubleshooting:")
                print("   - Check USB 3.0 connection")
                print("   - Try different USB port")
                print("   - Check Device Manager for driver issues")
                print("   - Run Azure Kinect Viewer to verify hardware")
        except AttributeError as e:
            # 이 에러가 발생하면 DLL이 실제로 로드되지 않은 것
            print(f"   ❌ DLL not loaded: {e}")
            print()
            print("   >>> Azure Kinect SDK DLL files are NOT loaded! <<<")
            print()
            print("   Root Cause:")
            print("   - The pykinect-azure package imported successfully")
            print("   - But the underlying k4a.dll is not in your PATH")
            print()
            print("   ✅ SOLUTION (Choose ONE):")
            print()
            print("   Option A - Temporary (for this session only):")
            print("   1. Run: setup_environment.bat")
            print("   2. In the SAME CMD window that opens, run:")
            print("      python check_installation.py")
            print()
            print("   Option B - Permanent:")
            print("   1. Open: System Properties > Environment Variables")
            print("   2. Edit System 'Path' variable")
            print("   3. Add this path:")
            for version in sdk_versions:
                sdk_path = rf"C:\Program Files\Azure Kinect SDK {version}"
                if os.path.exists(sdk_path):
                    print(f"      {sdk_path}\\sdk\\windows-desktop\\amd64\\release\\bin")
                    break
            print("   4. Restart your computer")
            print()
            print("   Current PATH status:")
            current_path = os.environ.get('PATH', '')
            sdk_paths = [p for p in current_path.split(';') if 'Azure Kinect' in p]
            if sdk_paths:
                print("   ✅ Azure Kinect found in PATH:")
                for p in sdk_paths:
                    print(f"      {p}")
                print("   (But DLLs still not loaded - try restarting Python)")
            else:
                print("   ❌ Azure Kinect SDK is NOT in current PATH")
        except Exception as e:
            print(f"   ❌ Error calling k4a_device_get_installed_count: {e}")
            print()
            print("   This might mean:")
            print("   - Kinect driver not installed")
            print("   - Kinect not connected")

except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    print()
    print("   To install pykinect-azure:")
    print("   1. Install Visual C++ Redistributable 2015-2019")
    print("   2. Install Azure Kinect SDK")
    print("   3. Install Body Tracking SDK")
    print("   4. pip install pykinect-azure")

print()
print("=" * 60)

if missing_packages:
    print()
    print("Missing packages. Install with:")
    print(f"pip install {' '.join(missing_packages)}")
    print()

print("Test complete!")
print("=" * 60)
