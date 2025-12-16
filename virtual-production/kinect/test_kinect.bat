@echo off
REM Azure Kinect 연결 테스트 스크립트

echo ========================================
echo Azure Kinect Connection Test
echo ========================================
echo.

echo 1. Checking Azure Kinect SDK installation...

REM SDK 버전 자동 감지
set SDK_PATH=
if exist "C:\Program Files\Azure Kinect SDK v1.4.2\tools\k4aviewer.exe" (
    set SDK_PATH=C:\Program Files\Azure Kinect SDK v1.4.2
    echo [OK] Azure Kinect SDK v1.4.2 found
) else if exist "C:\Program Files\Azure Kinect SDK v1.4.1\tools\k4aviewer.exe" (
    set SDK_PATH=C:\Program Files\Azure Kinect SDK v1.4.1
    echo [OK] Azure Kinect SDK v1.4.1 found
) else if exist "C:\Program Files\Azure Kinect SDK v1.4.0\tools\k4aviewer.exe" (
    set SDK_PATH=C:\Program Files\Azure Kinect SDK v1.4.0
    echo [OK] Azure Kinect SDK v1.4.0 found
) else (
    echo [ERROR] Azure Kinect SDK not found
    echo Please install from: https://learn.microsoft.com/en-us/azure/kinect-dk/sensor-sdk-download
    pause
    exit /b 1
)

echo.
echo 2. Checking Body Tracking SDK installation...
if exist "C:\Program Files\Azure Kinect Body Tracking SDK\tools" (
    echo [OK] Body Tracking SDK found
) else (
    echo [ERROR] Body Tracking SDK not found
    echo Please install from: https://learn.microsoft.com/en-us/azure/kinect-dk/body-sdk-download
    pause
    exit /b 1
)

echo.
echo 3. Launching Azure Kinect Viewer...
echo SDK Path: %SDK_PATH%
echo Please check if Kinect is detected in the viewer
echo.
"%SDK_PATH%\tools\k4aviewer.exe"

pause
