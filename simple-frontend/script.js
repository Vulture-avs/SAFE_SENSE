// Global variables
let isDetecting = false;
let startTime = null;
let uptimeInterval = null;
let statsInterval = null;
let currentCamera = 0;
let userData = null;

// API Base URL
const API_BASE = 'http://localhost:5000';

// DOM Elements
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const videoFeed = document.getElementById('videoFeed');
const noVideo = document.getElementById('noVideo');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const resetBtn = document.getElementById('resetBtn');
const alertSection = document.getElementById('alertSection');
const alertTime = document.getElementById('alertTime');
const connectionStatus = document.getElementById('connectionStatus');
const alertSound = document.getElementById('alertSound');
const alertAudio = document.getElementById('alertAudio');

// Create alert sound using Web Audio API
let audioContext;
let alertSoundBuffer;

// Initialize audio context
function initAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        createAlertSound();
    }
}

// Create emergency alert sound
function createAlertSound() {
    const sampleRate = audioContext.sampleRate;
    const duration = 2; // 2 seconds
    const buffer = audioContext.createBuffer(1, sampleRate * duration, sampleRate);
    const data = buffer.getChannelData(0);
    
    // Generate emergency siren sound
    for (let i = 0; i < buffer.length; i++) {
        const t = i / sampleRate;
        const frequency = 800 + Math.sin(t * 4) * 400; // Oscillating frequency
        data[i] = Math.sin(2 * Math.PI * frequency * t) * 0.3 * Math.exp(-t * 0.5);
    }
    
    alertSoundBuffer = buffer;
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 AI Fall Detection System Initialized');
    
    // Check if user is logged in
    checkUserLogin();
    
    // Load user data
    loadUserData();
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize audio on first user interaction
    document.addEventListener('click', initAudio, { once: true });
    
    // Check server connection
    checkConnection();
    
    // Update connection status periodically
    setInterval(checkConnection, 5000);
});

// Check user login
function checkUserLogin() {
    const userData = localStorage.getItem('fallDetectionUser');
    if (!userData) {
        window.location.href = 'login.html';
        return;
    }
}

// Load user data
function loadUserData() {
    const userDataStr = localStorage.getItem('fallDetectionUser');
    if (userDataStr) {
        userData = JSON.parse(userDataStr);
        
        // Update UI with user data
        document.getElementById('userName').textContent = userData.username;
        currentCamera = parseInt(userData.camera) || 0;
        updateCameraDisplay();
        
        // Apply dark mode if enabled
        if (userData.darkMode) {
            document.body.classList.add('dark-mode');
            document.getElementById('themeToggle').textContent = '☀️';
        }
        
        // Set camera selection
        const cameraSelect = document.getElementById('cameraSelect');
        if (cameraSelect) {
            cameraSelect.value = currentCamera;
        }
    }
}

// Setup event listeners
function setupEventListeners() {
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleDarkMode);
    
    // Camera switch
    document.getElementById('cameraSwitch').addEventListener('click', showCameraModal);
    
    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', logout);
    
    // Camera selection
    document.getElementById('cameraSelect').addEventListener('change', function() {
        switchCamera(parseInt(this.value));
    });
    
    // Modal events
    document.getElementById('modalClose').addEventListener('click', hideCameraModal);
    document.getElementById('cameraModal').addEventListener('click', function(e) {
        if (e.target === this) {
            hideCameraModal();
        }
    });
    
    // Camera option selection
    document.querySelectorAll('.camera-option').forEach(option => {
        option.addEventListener('click', function() {
            const cameraId = parseInt(this.dataset.camera);
            selectCamera(cameraId);
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === ' ') { // Spacebar
            e.preventDefault();
            if (isDetecting) {
                stopDetection();
            } else {
                startDetection();
            }
        } else if (e.key === 'r' || e.key === 'R') { // R key
            resetDetection();
        } else if (e.key === 'd' || e.key === 'D') { // D key for dark mode
            toggleDarkMode();
        } else if (e.key === 'c' || e.key === 'C') { // C key for camera
            showCameraModal();
        }
    });
}

// Check server connection
async function checkConnection() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        if (response.ok) {
            connectionStatus.textContent = 'Connected';
            connectionStatus.className = 'connected';
        } else {
            throw new Error('Server not responding');
        }
    } catch (error) {
        connectionStatus.textContent = 'Disconnected';
        connectionStatus.className = 'disconnected';
        console.error('Connection error:', error);
    }
}

// Start detection
async function startDetection() {
    try {
        showStatus('🔄 Starting detection...', 'loading');
        
        const response = await fetch(`${API_BASE}/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                camera: currentCamera
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            isDetecting = true;
            startTime = new Date();
            
            // Update UI
            videoFeed.src = `${API_BASE}/video_feed?t=${Date.now()}`;
            videoFeed.style.display = 'block';
            noVideo.style.display = 'none';
            
            // Update buttons
            startBtn.disabled = true;
            stopBtn.disabled = false;
            
            // Update status
            statusIndicator.className = 'status-indicator active';
            showStatus('🟢 Detection Active - Monitoring for falls', 'active');
            
            // Start timers
            startUptime();
            startStatsUpdate();
            
            console.log('✅ Detection started successfully');
        } else {
            throw new Error(data.error || 'Failed to start detection');
        }
    } catch (error) {
        console.error('❌ Error starting detection:', error);
        showStatus('❌ Failed to start detection', 'error');
        alert('Failed to start detection. Please check if the camera is connected and the server is running.');
    }
}

// Stop detection
async function stopDetection() {
    try {
        showStatus('🔄 Stopping detection...', 'loading');
        
        const response = await fetch(`${API_BASE}/stop`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            isDetecting = false;
            
            // Update UI
            videoFeed.style.display = 'none';
            noVideo.style.display = 'block';
            
            // Update buttons
            startBtn.disabled = false;
            stopBtn.disabled = true;
            
            // Update status
            statusIndicator.className = 'status-indicator';
            showStatus('⏹️ Detection Stopped', 'stopped');
            
            // Stop timers
            stopUptime();
            stopStatsUpdate();
            
            // Hide alert if showing
            hideAlert();
            
            console.log('⏹️ Detection stopped successfully');
        } else {
            throw new Error(data.error || 'Failed to stop detection');
        }
    } catch (error) {
        console.error('❌ Error stopping detection:', error);
        showStatus('❌ Failed to stop detection', 'error');
    }
}

// Reset detection
async function resetDetection() {
    try {
        const response = await fetch(`${API_BASE}/reset`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            hideAlert();
            if (isDetecting) {
                statusIndicator.className = 'status-indicator active';
                showStatus('🟢 Alert Reset - Monitoring resumed', 'active');
            }
            console.log('🔄 Detection reset successfully');
        } else {
            throw new Error(data.error || 'Failed to reset detection');
        }
    } catch (error) {
        console.error('❌ Error resetting detection:', error);
    }
}

// Update statistics
async function updateStats() {
    if (!isDetecting) return;
    
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        // Update stat displays
        document.getElementById('totalDetections').textContent = data.total_detections || 0;
        document.getElementById('fallsDetected').textContent = data.falls_detected || 0;
        document.getElementById('currentRisk').textContent = Math.round((data.current_risk || 0) * 100) + '%';
        
        // Check for fall detection
        if (data.fall_detected) {
            showAlert();
            statusIndicator.className = 'status-indicator alert';
            showStatus('🚨 FALL DETECTED! Alert activated', 'alert');
        } else if (isDetecting) {
            hideAlert();
            statusIndicator.className = 'status-indicator active';
            showStatus('🟢 Detection Active - Monitoring for falls', 'active');
        }
        
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Show status message
function showStatus(message, type) {
    statusText.textContent = message;
    statusText.className = `status-text ${type}`;
}

// Show fall alert
function showAlert() {
    alertSection.style.display = 'block';
    alertTime.textContent = `Detected at: ${new Date().toLocaleTimeString()}`;
    
    // Play alert sound if enabled
    if (alertSound.checked) {
        playAlertSound();
    }
    
    // Browser notification
    if (Notification.permission === 'granted') {
        new Notification('Fall Detected!', {
            body: 'A potential fall has been detected. Please check immediately.',
            icon: '🚨'
        });
    }
}

// Hide fall alert
function hideAlert() {
    alertSection.style.display = 'none';
}

// Play alert sound
function playAlertSound() {
    try {
        if (!audioContext) {
            initAudio();
        }
        
        if (alertSoundBuffer && audioContext) {
            const source = audioContext.createBufferSource();
            source.buffer = alertSoundBuffer;
            source.connect(audioContext.destination);
            source.start();
            
            // Play multiple times for urgency
            setTimeout(() => {
                if (alertSection.style.display !== 'none') {
                    const source2 = audioContext.createBufferSource();
                    source2.buffer = alertSoundBuffer;
                    source2.connect(audioContext.destination);
                    source2.start();
                }
            }, 500);
        }
    } catch (error) {
        console.log('Alert sound not available:', error);
    }
}

// Start uptime counter
function startUptime() {
    uptimeInterval = setInterval(updateUptime, 1000);
}

// Stop uptime counter
function stopUptime() {
    if (uptimeInterval) {
        clearInterval(uptimeInterval);
        uptimeInterval = null;
    }
    document.getElementById('systemUptime').textContent = '00:00';
}

// Update uptime display
function updateUptime() {
    if (!startTime) return;
    
    const now = new Date();
    const diff = Math.floor((now - startTime) / 1000);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    
    document.getElementById('systemUptime').textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// Start stats update interval
function startStatsUpdate() {
    statsInterval = setInterval(updateStats, 2000);
}

// Stop stats update interval
function stopStatsUpdate() {
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Handle page visibility change
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden - reducing update frequency');
    } else {
        console.log('Page visible - resuming normal updates');
        if (isDetecting) {
            updateStats();
        }
    }
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    if (isDetecting) {
        stopDetection();
    }
});

// Utility functions
function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// New feature functions
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    
    // Update button icon
    document.getElementById('themeToggle').textContent = isDark ? '☀️' : '🌙';
    
    // Save preference
    if (userData) {
        userData.darkMode = isDark;
        localStorage.setItem('fallDetectionUser', JSON.stringify(userData));
    }
}

function showCameraModal() {
    document.getElementById('cameraModal').style.display = 'flex';
    
    // Update selected camera
    document.querySelectorAll('.camera-option').forEach(option => {
        option.classList.remove('selected');
        if (parseInt(option.dataset.camera) === currentCamera) {
            option.classList.add('selected');
        }
    });
}

function hideCameraModal() {
    document.getElementById('cameraModal').style.display = 'none';
}

function selectCamera(cameraId) {
    // Update selection
    document.querySelectorAll('.camera-option').forEach(option => {
        option.classList.remove('selected');
        if (parseInt(option.dataset.camera) === cameraId) {
            option.classList.add('selected');
        }
    });
    
    // Switch camera
    switchCamera(cameraId);
    
    // Close modal
    setTimeout(() => {
        hideCameraModal();
    }, 500);
}

function switchCamera(cameraId) {
    currentCamera = cameraId;
    updateCameraDisplay();
    
    // Update select dropdown
    const cameraSelect = document.getElementById('cameraSelect');
    if (cameraSelect) {
        cameraSelect.value = cameraId;
    }
    
    // Save preference
    if (userData) {
        userData.camera = cameraId;
        localStorage.setItem('fallDetectionUser', JSON.stringify(userData));
    }
    
    // Restart detection with new camera if currently detecting
    if (isDetecting) {
        stopDetection().then(() => {
            setTimeout(() => {
                startDetection();
            }, 1000);
        });
    }
    
    showNotification(`Switched to Camera ${cameraId}`, 'success');
}

function updateCameraDisplay() {
    const cameraNames = ['Default', 'Camera 1', 'Camera 2', 'Camera 3'];
    document.getElementById('cameraName').textContent = cameraNames[currentCamera] || 'Unknown';
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        // Stop detection if running
        if (isDetecting) {
            stopDetection();
        }
        
        // Clear user data
        localStorage.removeItem('fallDetectionUser');
        
        // Redirect to login
        window.location.href = 'login.html';
    }
}

function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    const colors = {
        success: { bg: '#c6f6d5', border: '#48bb78', text: '#2f855a' },
        error: { bg: '#fed7d7', border: '#f56565', text: '#c53030' },
        warning: { bg: '#faf089', border: '#ecc94b', text: '#744210' },
        info: { bg: '#bee3f8', border: '#4299e1', text: '#2c5282' }
    };
    
    const color = colors[type] || colors.info;
    
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${icons[type] || icons.info}</span>
            <span class="notification-message">${message}</span>
        </div>
    `;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${color.bg};
        color: ${color.text};
        padding: 15px 20px;
        border-radius: 10px;
        border: 2px solid ${color.border};
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        z-index: 1000;
        animation: slideInRight 0.3s ease;
        max-width: 300px;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 3000);
}

// Console welcome message
console.log(`
🤖 AI Fall Detection System
============================
Keyboard Shortcuts:
- Spacebar: Start/Stop Detection
- R: Reset Alert
- D: Toggle Dark Mode
- C: Camera Selection

User: ${userData?.username || 'Unknown'}
Camera: ${currentCamera}
Status: Ready
`);