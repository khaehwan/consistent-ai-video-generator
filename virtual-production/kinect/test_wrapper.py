"""
k4a_wrapper import 테스트 스크립트
정확한 오류 원인 파악용
"""

print("=" * 60)
print("k4a_wrapper Import Test")
print("=" * 60)
print()

print("1. Testing k4a_wrapper import...")
try:
    import k4a_wrapper
    print("   ✅ k4a_wrapper imported successfully!")
    print()

    # 주요 클래스 확인
    print("2. Checking classes...")
    print(f"   K4ADevice: {hasattr(k4a_wrapper, 'K4ADevice')}")
    print(f"   K4ABTTracker: {hasattr(k4a_wrapper, 'K4ABTTracker')}")
    print(f"   JointType: {hasattr(k4a_wrapper, 'JointType')}")
    print()

    # 장치 개수 확인
    print("3. Testing device detection...")
    device_count = k4a_wrapper.device_get_installed_count()
    print(f"   Device count: {device_count}")
    print()

    if device_count > 0:
        print("✅ All tests passed!")
    else:
        print("⚠️  Wrapper loaded but no devices detected")

except Exception as e:
    print(f"   ❌ Failed to import: {e}")
    print()
    print("Detailed error:")
    import traceback
    traceback.print_exc()
    print()

    print("=" * 60)
    print("Troubleshooting:")
    print("=" * 60)
    print()
    print("1. Check if Azure Kinect SDK is installed:")
    print("   - C:\\Program Files\\Azure Kinect SDK v1.4.2\\")
    print("   - C:\\Program Files\\Azure Kinect SDK v1.4.1\\")
    print("   - C:\\Program Files\\Azure Kinect SDK v1.4.0\\")
    print()
    print("2. Check SDK bin folder exists:")
    print("   - ...\\sdk\\windows-desktop\\amd64\\release\\bin\\")
    print()
    print("3. Check if DLL files exist:")
    print("   - k4a.dll")
    print("   - k4abt.dll")
    print()
    print("4. Run: python check_installation.py")
    print()

print("=" * 60)
