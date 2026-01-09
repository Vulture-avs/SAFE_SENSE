# SAFE_SENSE
# 🚨 AI Fall Detection System

**Real-time Fall Detection using Computer Vision & AI**

An intelligent fall detection system that uses MediaPipe pose estimation and advanced algorithms to detect falls in real-time through webcam or video input.

## 🎯 Project Exhibition Overview

This is a complete AI-powered fall detection system designed for real-world applications like elderly care, hospitals, and safety monitoring. The system combines computer vision, machine learning, and web technologies to provide accurate, real-time fall detection.

## ✨ Key Features

### 🔥 Core Capabilities
- **Real-time Fall Detection** - Instant detection through webcam
- **Multi-condition Validation** - Motion + Posture + Position analysis
- **Camera-adaptive Thresholds** - Automatically adjusts to different camera setups
- **Auto-calibration** - Learns from usage patterns for better accuracy
- **Web-based Interface** - Easy-to-use browser interface
- **Confidence Scoring** - High/Medium/Low detection confidence levels
- **Static Fall Detection** - Detects people already lying on the ground


## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │◄──►│  Flask Backend   │◄──►│ MediaPipe Core  │
│  (HTML/JS/CSS)  │    │  (Python/Flask)  │    │ (Pose Detection)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ User Interface  │    │ Fall Detection   │    │ Computer Vision │
│ • Live Video    │    │ • Multi-condition│    │ • Pose Landmarks│
│ • Statistics    │    │ • Auto-calibrate │    │ • Real-time Proc│
│ • Controls      │    │ • Confidence     │    │ • Optimization  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Installation

#### Quick Installation (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd AI-Fall-Detection-System

# Install Python dependencies (choose one)
pip install -r requirements.txt          # Standard installation
pip install -r requirements-minimal.txt  # Lightweight installation
pip install -r requirements-full.txt     # Complete with all features
```

#### Alternative Installation Methods
```bash
# Method 1: Auto-install using batch script (Windows)
START_DEMO.bat

# Method 2: Step-by-step installation (if bulk install fails)
pip install numpy>=1.24.0
pip install opencv-python>=4.8.1
pip install mediapipe>=0.10.9
pip install flask>=3.0.0 flask-cors>=4.0.0
pip install cvzone>=1.6.1 pillow>=10.0.0
```

### 2. Run the System
```bash
# Start the web application
cd simple-backend
python simple_app.py
```

### 3. Access the Interface
- Open your browser and go to: **http://localhost:5000**
- Click "Start Detection" to begin monitoring
- The system will automatically detect and highlight any falls

## 📁 Project Structure

```
AI-Fall-Detection-System/
├── simple-backend/           # Main Flask web application
│   ├── simple_app.py        # Main application server
│   ├── requirements.txt     # Python dependencies
│   ├── quick-start.bat      # Windows quick start
│   └── start-here.bat       # Alternative start script
├── simple-frontend/         # Web interface files
│   ├── index.html          # Main dashboard
│   ├── login.html          # Login page
│   ├── style.css           # Styling
│   ├── script.js           # Frontend logic
│   └── login.js/css        # Login interface
├── Fall-Detection-main/     # Core detection algorithms
│   ├── main_mediapipe.py   # MediaPipe implementation
│   ├── config.py           # Detection parameters
│   ├── requirements.txt    # Core dependencies
│   ├── fall.mp4           # Demo video 1
│   ├── fall2.mp4          # Demo video 2
│   └── README.md          # Core module documentation
├── camera-config.json      # Camera configuration
├── requirements.txt        # Main project dependencies
└── README.md              # This file
```


#### Requirements Files Available:
- `requirements.txt` - Standard installation
- `requirements-minimal.txt` - Lightweight (core only)
- `requirements-full.txt` - Complete with all features
- `requirements-dev.txt ` - Development tools



## 🔮 Future Enhancements

- Mobile app integration
- Cloud-based monitoring
- Multiple camera support
- Advanced analytics dashboard
- Integration with emergency services
- Wearable device compatibility


**Built with ❤️ for safety and innovation**
