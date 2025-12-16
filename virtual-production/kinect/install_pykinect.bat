@echo off
REM PyKinect Azure 설치 스크립트

echo ========================================
echo Installing PyKinect Azure
echo ========================================
echo.

echo Step 1: Installing Visual C++ Redistributable dependencies...
echo Please download and install if not already installed:
echo https://aka.ms/vs/16/release/vc_redist.x64.exe
echo.
pause

echo Step 2: Upgrading pip...
python -m pip install --upgrade pip
echo.

echo Step 3: Installing dependencies...
pip install numpy opencv-python
echo.

echo Step 4: Installing pykinect-azure...
pip install pykinect-azure
echo.

echo Step 5: Installing other requirements...
pip install websocket-client PyYAML python-json-logger requests
echo.

echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Now run: python check_installation.py
echo.
pause
