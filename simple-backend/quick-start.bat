@echo off
title SafeSense - Quick Start from Backend Directory
color 0B
echo ========================================
echo     🛡️  SafeSense Fall Detection  🛡️
echo     Quick Start from Backend Directory
echo ========================================
echo.

echo 📍 Current location: simple-backend directory
echo 🔄 Installing dependencies and starting server...
echo.

REM Install Flask dependencies
echo 📦 Installing Flask...
pip install flask>=2.0.0 flask-cors>=3.0.0

REM Install MediaPipe dependencies
echo 📦 Installing MediaPipe dependencies...
pip install opencv-python>=4.8.0 mediapipe>=0.10.0 cvzone>=1.5.6 numpy>=1.21.0

REM Test installations
echo.
echo 🧪 Testing installations...
python -c "import flask; print('✅ Flask installed')" 2>nul || echo "❌ Flask failed"
python -c "import mediapipe; print('✅ MediaPipe installed')" 2>nul || echo "❌ MediaPipe failed"
python -c "import cv2; print('✅ OpenCV installed')" 2>nul || echo "❌ OpenCV failed"

echo.
echo 🚀 Starting SafeSense Backend Server...
echo 📱 Open your browser and go to: http://localhost:5000
echo 🔧 Press Ctrl+C to stop the server
echo.

REM Start the Flask application
if exist "simple_app.py" (
    python simple_app.py
) else (
    echo ❌ Error: simple_app.py not found!
    echo Make sure you're in the simple-backend directory
    pause
    exit /b 1
)

echo.
echo 🛑 SafeSense Server Stopped
pause