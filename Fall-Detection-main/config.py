# MediaPipe Fall Detection Configuration

class FallDetectionConfig:
    # Camera Settings
    DEFAULT_CAMERA_INDEX = 0       # Always use default camera (index 0)
    CAMERA_FALLBACK_INDEX = 0      # Fallback to default camera if issues
    # MediaPipe Pose Detection Settings
    MIN_DETECTION_CONFIDENCE = 0.7  # Minimum confidence for pose detection
    MIN_TRACKING_CONFIDENCE = 0.5   # Minimum confidence for pose tracking
    MODEL_COMPLEXITY = 1            # 0=Lite, 1=Full, 2=Heavy
    SMOOTH_LANDMARKS = True         # Enable landmark smoothing
    
    # Fall Detection Thresholds - ENHANCED FOR ACCURATE DETECTION
    TORSO_ANGLE_THRESHOLD = 70      # Degrees from vertical indicating fall (BALANCED - reasonable tilt)
    ASPECT_RATIO_THRESHOLD = 0.8    # Width/Height ratio for horizontal body (BALANCED - reasonable width)
    LOW_POSITION_THRESHOLD = 0.75   # Hip position threshold (bottom 25% of frame, BALANCED)
    VERTICAL_SPAN_THRESHOLD = 0.4   # Maximum vertical span for fallen person (BALANCED)
    SPEED_THRESHOLD = 0.02          # Movement speed threshold for fast drop detection
    
    # NEW: Enhanced Detection Thresholds
    UPRIGHT_TORSO_THRESHOLD = 45    # Degrees - below this is considered upright/bending (not fall)
    UPRIGHT_HIP_THRESHOLD = 0.7     # Hip position - above this is considered sitting/kneeling
    HEAD_FLOOR_THRESHOLD = 0.8      # Head position - below this head is near floor (lying)
    FAST_MOTION_THRESHOLD = 0.03    # Vertical speed - above this is fast motion (fall vs sitting)
    
    # Position Thresholds - BALANCED FOR RELIABLE DETECTION
    GROUND_LEVEL_THRESHOLD = 0.85   # Ground level detection (bottom 15%, BALANCED)
    HEAD_DROP_THRESHOLD = 0.75      # Head drop detection (bottom 25%, BALANCED)
    
    # Temporal filtering - ENHANCED WITH PATIENCE SYSTEM
    FALL_CONFIRMATION_FRAMES = 10   # Frames needed to confirm fall (patient ~0.33s)
    CONDITIONS_REQUIRED = 3         # Multiple conditions required (BALANCED)
    
    # NEW: Enhanced Confirmation System
    MIN_CONSECUTIVE_LYING_FRAMES = 8    # Minimum consecutive lying posture frames
    MAX_LYING_FRAMES_WAIT = 12          # Maximum frames to wait for confirmation
    CONFIRMATION_BUFFER_SIZE = 15       # Size of detection history buffer
    UPRIGHT_CLEAR_FRAMES = 5           # Consecutive upright frames needed to clear fall
    
    # Video settings
    FRAME_WIDTH = 980
    FRAME_HEIGHT = 740
    
    # Alert settings
    FLASH_FREQUENCY = 4  # Flashes per second for alert
    
    # Colors (BGR format)
    NORMAL_COLOR = (0, 255, 0)      # Green
    FALL_COLOR = (0, 0, 255)        # Red
    ALERT_COLOR = (0, 255, 255)     # Yellow
    INFO_COLOR = (255, 255, 255)    # White
    POSE_COLOR = (0, 255, 0)        # Green for pose landmarks
    POSE_CONNECTION_COLOR = (0, 0, 255)  # Red for pose connections