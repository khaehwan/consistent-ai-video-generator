@echo off
REM 환경 변수 PATH에 Azure Kinect SDK 경로 추가 (현재 세션만)

echo ========================================
echo Azure Kinect Environment Setup
echo ========================================
echo.

REM SDK 버전 자동 감지
set KINECT_SDK=
if exist "C:\Program Files\Azure Kinect SDK v1.4.2" (
    set "KINECT_SDK=C:\Program Files\Azure Kinect SDK v1.4.2"
    echo Found Azure Kinect SDK v1.4.2
) else if exist "C:\Program Files\Azure Kinect SDK v1.4.1" (
    set "KINECT_SDK=C:\Program Files\Azure Kinect SDK v1.4.1"
    echo Found Azure Kinect SDK v1.4.1
) else if exist "C:\Program Files\Azure Kinect SDK v1.4.0" (
    set "KINECT_SDK=C:\Program Files\Azure Kinect SDK v1.4.0"
    echo Found Azure Kinect SDK v1.4.0
) else (
    echo ERROR: Azure Kinect SDK not found!
    echo Please install from: https://learn.microsoft.com/en-us/azure/kinect-dk/sensor-sdk-download
    pause
    exit /b 1
)

set "KINECT_BT_SDK=C:\Program Files\Azure Kinect Body Tracking SDK"
if exist "%KINECT_BT_SDK%" (
    echo Found Body Tracking SDK
) else (
    echo WARNING: Body Tracking SDK not found
    echo Please install from: https://learn.microsoft.com/en-us/azure/kinect-dk/body-sdk-download
)

echo.
echo Setting up environment variables...

REM PATH에 추가 (현재 세션만)
set "PATH=%KINECT_SDK%\sdk\windows-desktop\amd64\release\bin;%PATH%"
set "PATH=%KINECT_SDK%\tools;%PATH%"
if exist "%KINECT_BT_SDK%" (
    set "PATH=%KINECT_BT_SDK%\sdk\windows-desktop\amd64\release\bin;%PATH%"
    set "PATH=%KINECT_BT_SDK%\sdk\netstandard2.0\publish;%PATH%"
    set "PATH=%KINECT_BT_SDK%\tools;%PATH%"
)

echo.
echo ✅ Environment variables set for current session
echo.
echo SDK Path: %KINECT_SDK%
echo Body Tracking SDK Path: %KINECT_BT_SDK%
echo.
echo Now you can run: python main.py
echo.
echo ========================================
echo Note: This is temporary!
echo ========================================
echo To make permanent:
echo 1. Open System Properties ^> Environment Variables
echo 2. Edit System "Path" variable
echo 3. Add the following paths:
echo.
echo    %KINECT_SDK%\sdk\windows-desktop\amd64\release\bin
echo    %KINECT_SDK%\tools
if exist "%KINECT_BT_SDK%" (
    echo    %KINECT_BT_SDK%\tools
)
echo.
echo ========================================
echo.

REM Python 스크립트 실행용 셸 유지
cmd /k
