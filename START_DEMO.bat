@echo off
echo ========================================
echo    AI Fall Detection System - DEMO
echo         Updated Tech Stack 2025
echo ========================================
echo.
echo Starting the fall detection system...
echo.

echo 1. Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo.
echo 2. Checking requirements...
if exist check_requirements.py (
    python check_requirements.py
) else (
    echo Requirements checker not found, proceeding with installation...
)

echo.
echo 3. Installing/updating dependencies...
echo    This may take a few minutes on first run...
pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo Installation failed! Trying minimal installation...
    pip install -r requirements-minimal.txt
    
    if %errorlevel% neq 0 (
        echo.
        echo Minimal installation also failed! Trying step-by-step...
        pip install numpy>=1.24.0
        pip install opencv-python>=4.8.1
        pip install mediapipe>=0.10.9
        pip install flask>=3.0.0 flask-cors>=4.0.0
        pip install cvzone>=1.6.1 pillow>=10.0.0
    )
)

echo.
echo 4. Starting web server...
cd simple-backend
echo    Server starting at: http://localhost:5000
echo    Press Ctrl+C to stop the server
echo.
python simple_app.py

echo.
echo 5. Open your browser and go to: http://localhost:5000
echo.
pause