@echo off
title SafeSense Backend - Quick Start
color 0B
echo ========================================
echo     🛡️  SafeSense Backend Server  🛡️
echo     Quick Start from Backend Directory
echo ========================================
echo.

echo 📍 Current directory: %CD%
echo.

echo 📦 Installing Python dependencies...
echo.

REM Install Flask and other dependencies
echo Installing Flask...
pip install flask>=2.0.0
if errorlevel 1 (
    echo ⚠️  Flask installation failed, trying alternative...
    pip install flask
)

echo Installing Flask-CORS...
pip install flask-cors>=3.0.0
if errorlevel 1 (
    echo ⚠️  Flask-CORS installation failed, trying alternative...
    pip install flask-cors
)

echo Installing OpenCV...
pip install opencv-python>=4.8.0
if errorlevel 1 (
    echo ⚠️  OpenCV installation failed, trying alternative...
    pip install opencv-python-headless
)

echo Installing MediaPipe...
pip install mediapipe>=0.10.0
if errorlevel 1 (
    echo ⚠️  MediaPipe installation failed, trying specific version...
    pip install mediapipe==0.10.9
)

echo Installing CVZone...
pip install cvzone>=1.5.6
if errorlevel 1 (
    echo ⚠️  CVZone installation failed, trying alternative...
    pip install cvzone
)

echo Installing NumPy...
pip install numpy>=1.21.0
if errorlevel 1 (
    echo ⚠️  NumPy installation failed, trying alternative...
    pip install numpy
)

echo.
echo 🧪 Testing installations...
python -c "import flask; print('✅ Flask:', flask.__version__)" 2>nul || echo "❌ Flask not working"
python -c "import flask_cors; print('✅ Flask-CORS: OK')" 2>nul || echo "❌ Flask-CORS not working"
python -c "import cv2; print('✅ OpenCV:', cv2.__version__)" 2>nul || echo "❌ OpenCV not working"
python -c "import mediapipe as mp; print('✅ MediaPipe:', mp.__version__)" 2>nul || echo "❌ MediaPipe not working"
python -c "import cvzone; print('✅ CVZone: OK')" 2>nul || echo "❌ CVZone not working"
python -c "import numpy as np; print('✅ NumPy:', np.__version__)" 2>nul || echo "❌ NumPy not working"

echo.
echo 🚀 Starting SafeSense Backend Server...
echo 📱 Open your browser and go to: http://localhost:5000
echo 🔧 Press Ctrl+C to stop the server
echo.

if exist "simple_app.py" (
    python simple_app.py
) else (
    echo ❌ Error: simple_app.py not found in current directory!
    echo Current directory contents:
    dir /b
    pause
    exit /b 1
)

echo.
echo 🛑 SafeSense Backend Server Stopped
pause