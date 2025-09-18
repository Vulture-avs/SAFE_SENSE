from flask import Flask, Response, jsonify, send_from_directory, request
from flask_cors import CORS
import cv2
import sys
import os
import time
import threading
import json
import numpy as np

# Add the Fall-Detection-main directory to Python path
sys.path.append('../Fall-Detection-main')
try:
    from main_mediapipe import MediaPipeFallDetectionSystem
except ImportError:
    from main import FallDetectionSystem as MediaPipeFallDetectionSystem

app = Flask(__name__)
CORS(app)

# Global variables
detector = None
fall_detected = False
detection_active = False
detection_stats = {
    "total_detections": 0,
    "falls_detected": 0,
    "current_risk": 0,
    "uptime": 0,
    "start_time": None
}

class WebFallDetector:
    def __init__(self, video_source=0):
        """Initialize web-based MediaPipe fall detector"""
        # Always default to camera 0 if not specified
        if video_source is None:
            video_source = 0
        self.video_source = video_source
        
        # Initialize MediaPipe components
        self.setup_video_source(video_source)
        self.setup_mediapipe()
        self.setup_detection_parameters()
        
        # Web-specific initialization
        self.frame_count = 0
        self.person_detections = 0
        
        # Create MediaPipe fall detector for the actual detection logic
        try:
            self.fall_detector = MediaPipeFallDetectionSystem(None)  # Don't initialize video source
            # Use our video source instead
            self.fall_detector.cap = self.cap
            print("✅ MediaPipe fall detector integrated successfully")
        except Exception as e:
            print(f"⚠️  Could not create MediaPipe detector: {e}")
            print("🔄 Using integrated web detection logic")
            self.fall_detector = None
            
    def setup_mediapipe(self):
        """Setup MediaPipe pose detection"""
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            smooth_segmentation=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        print("✅ MediaPipe pose detection initialized")
        
    def setup_detection_parameters(self):
        """Setup multi-condition fall detection parameters with ENHANCED confirmation system"""
        # ENHANCED CONFIRMATION FRAMES SYSTEM
        self.fall_detection_frames = 0
        self.fall_threshold_frames = 10  # ENHANCED: Require 10 consecutive frames (patience)
        self.fall_detected = False
        self.fall_start_time = None
        self.last_detection_details = {}
        
        # NEW: Enhanced confirmation tracking
        self.lying_posture_frames = 0      # Track consecutive lying posture frames
        self.min_lying_frames = 8          # Minimum consecutive lying frames required
        self.max_lying_frames = 12         # Maximum frames to wait for confirmation
        self.confirmation_buffer = []      # Buffer to track recent detection states
        self.confirmation_buffer_size = 15 # Keep last 15 detection results
        self.upright_clear_frames = 5      # Consecutive upright frames needed to clear
        
        # Multi-condition detection system
        self.setup_multi_condition_thresholds()
        
        # Optimized tracking buffers (minimal memory footprint)
        self.frame_timestamps = []
        self.head_positions = []
        self.torso_positions = []
        self.hip_positions = []
        self.body_ratios = []  # horizontal/vertical ratio tracking
        
        # Performance optimization - BALANCED FOR ACCURACY AND PERFORMANCE
        self.max_history = 8  # Reduced from 15 for better performance
        self.frame_skip_counter = 0
        self.analysis_frequency = 2  # Analyze every 2nd frame for balance
        self.min_frames_for_motion = 3  # Minimum frames needed for reliable detection
        
    def setup_multi_condition_thresholds(self):
        """Setup camera-dependent configurable thresholds for real-world deployment"""
        
        # CAMERA CONFIGURATION - Auto-detect or manual setup
        self.camera_config = self.detect_camera_setup()
        
        # Core thresholds - BALANCED FOR RELIABLE DETECTION
        self.SPEED_THR = 0.02       # hip/head drop per frame - BALANCED (original value)
        self.TORSO_THR = 70         # BALANCED - torso angle > 70° means lying down (reasonable)
        self.ASPECT_THR = 0.8       # BALANCED - if width/height > 0.8, lying posture (reasonable)
        self.FRAMES_CONFIRM = 10    # ENHANCED - 10 frames to confirm (~0.33s with patience)
        
        # CAMERA-DEPENDENT POSITION THRESHOLDS
        self.setup_camera_dependent_thresholds()
        
        # Enhanced thresholds for web system - BALANCED FOR DEMO
        self.HEAD_SPEED_THR = 0.025  # head drop threshold - balanced
        self.GROUND_LEVEL_THR = 0.85  # ground level threshold - balanced
        self.HEAD_LOW_THR = 0.75      # head low threshold - balanced
        
        # Multi-condition thresholds (enhanced system)
        self.thresholds = {
            # Core algorithm thresholds (MAINTAIN THESE)
            'speed_threshold': self.SPEED_THR,
            'torso_threshold': self.TORSO_THR,
            'aspect_threshold': self.ASPECT_THR,
            'frames_confirm': self.FRAMES_CONFIRM,
            
            # Enhanced motion-based thresholds - BALANCED FOR DEMO
            'head_velocity': 0.12,      # For advanced motion detection - BALANCED
            'torso_velocity': 0.10,     # For advanced motion detection - BALANCED
            'acceleration': 0.04,       # Sudden acceleration threshold - BALANCED
            
            # Position-based thresholds
            'low_position': self.LOW_POS_THR,
            'head_low': 0.55,
            'aspect_ratio': self.ASPECT_THR,
            
            # Temporal thresholds
            'rapid_motion_frames': 3,
            'pattern_window': 6,
            'confidence_frames': 5,
            
            # Combined scoring thresholds
            'high_confidence_motion': 2,
            'high_confidence_pose': 1,
            'medium_confidence_motion': 1,
            'medium_confidence_pose': 2,
        }
        
        # Core algorithm tracking (KEEP THESE)
        self.last_hip_y = None
        self.last_head_y = None
        self.vel_history = []
        self.head_vel_history = []
        self.torso_angle_history = []
        self.aspect_history = []
        self.HISTORY_SIZE = 5
        
        # Camera calibration tracking
        self.person_height_samples = []
        self.frame_analysis_count = 0
        
    def detect_camera_setup(self):
        """
        Detect camera mounting configuration for adaptive thresholds
        Returns camera configuration parameters
        """
        # Default configuration - can be overridden
        config = {
            'mounting_height': 'medium',  # low, medium, high
            'viewing_angle': 'normal',    # top-down, normal, low-angle
            'distance': 'medium',         # close, medium, far
            'auto_calibrate': True        # Enable automatic threshold adjustment
        }
        
        print(f"📹 Camera Configuration: {config['mounting_height']} height, {config['viewing_angle']} angle")
        return config
    
    def setup_camera_dependent_thresholds(self):
        """
        Setup position thresholds based on camera configuration
        Adaptive thresholds for different camera setups
        """
        mounting = self.camera_config['mounting_height']
        angle = self.camera_config['viewing_angle']
        
        # BASE THRESHOLDS - BALANCED FOR RELIABLE DETECTION
        base_thresholds = {
            'low_position': {'min': 0.70, 'max': 0.85},      # 70-85% - BALANCED for detection
            'ground_level': {'min': 0.80, 'max': 0.90},      # 80-90% - BALANCED for detection  
            'head_low': {'min': 0.70, 'max': 0.85},          # 70-85% - BALANCED for detection
        }
        
        # CAMERA HEIGHT ADJUSTMENTS
        height_adjustments = {
            'low': {'factor': 0.9, 'desc': 'Low mounted camera (more lenient)'},
            'medium': {'factor': 1.0, 'desc': 'Medium height camera (standard)'},
            'high': {'factor': 1.1, 'desc': 'High mounted camera (more strict)'}
        }
        
        # VIEWING ANGLE ADJUSTMENTS  
        angle_adjustments = {
            'top-down': {'factor': 1.15, 'desc': 'Top-down view (stricter position)'},
            'normal': {'factor': 1.0, 'desc': 'Normal viewing angle'},
            'low-angle': {'factor': 0.85, 'desc': 'Low angle view (more lenient)'}
        }
        
        # CALCULATE ADAPTIVE THRESHOLDS
        height_factor = height_adjustments[mounting]['factor']
        angle_factor = angle_adjustments[angle]['factor']
        combined_factor = (height_factor + angle_factor) / 2
        
        # Apply adjustments to base thresholds - BALANCED FOR RELIABLE DETECTION
        self.LOW_POS_THR = min(base_thresholds['low_position']['max'], 
                              max(base_thresholds['low_position']['min'],
                                  0.75 * combined_factor))  # BALANCED - 75% threshold (bottom 25%)
        
        self.GROUND_LEVEL_THR = min(base_thresholds['ground_level']['max'],
                                   max(base_thresholds['ground_level']['min'],
                                       0.85 * combined_factor))  # BALANCED - 85% threshold (bottom 15%)
        
        self.HEAD_LOW_THR = min(base_thresholds['head_low']['max'],
                               max(base_thresholds['head_low']['min'],
                                   0.75 * combined_factor))  # BALANCED - 75% threshold (bottom 25%)
        
        # Store configuration for display
        self.threshold_config = {
            'low_position': self.LOW_POS_THR,
            'ground_level': self.GROUND_LEVEL_THR,
            'head_low': self.HEAD_LOW_THR,
            'height_factor': height_factor,
            'angle_factor': angle_factor,
            'combined_factor': combined_factor
        }
        
        print(f"🎯 Adaptive Thresholds:")
        print(f"   Low Position: {self.LOW_POS_THR:.2f} (person in bottom {(1-self.LOW_POS_THR)*100:.0f}%)")
        print(f"   Ground Level: {self.GROUND_LEVEL_THR:.2f} (person in bottom {(1-self.GROUND_LEVEL_THR)*100:.0f}%)")
        print(f"   Head Low: {self.HEAD_LOW_THR:.2f} (head in bottom {(1-self.HEAD_LOW_THR)*100:.0f}%)")
        print(f"   Camera Factor: {combined_factor:.2f} ({height_adjustments[mounting]['desc']}, {angle_adjustments[angle]['desc']})")
    
    def auto_calibrate_thresholds(self, landmarks):
        """
        Automatically calibrate thresholds based on observed person positions
        Learns from actual usage patterns
        """
        if not self.camera_config['auto_calibrate']:
            return
            
        self.frame_analysis_count += 1
        
        # Sample person height every 60 frames for calibration
        if self.frame_analysis_count % 60 == 0:
            try:
                # Calculate person's apparent height in frame
                lm = landmarks
                head_y = lm[0].y  # nose
                foot_y = max(lm[29].y, lm[30].y)  # ankle positions
                person_height = foot_y - head_y
                
                if person_height > 0.1:  # Valid height measurement
                    self.person_height_samples.append({
                        'height': person_height,
                        'head_y': head_y,
                        'foot_y': foot_y,
                        'frame': self.frame_analysis_count
                    })
                    
                    # Keep only recent samples
                    if len(self.person_height_samples) > 10:
                        self.person_height_samples.pop(0)
                    
                    # Adjust thresholds based on observed patterns
                    if len(self.person_height_samples) >= 5:
                        self.adjust_thresholds_from_samples()
                        
            except Exception as e:
                pass  # Skip calibration on error
    
    def adjust_thresholds_from_samples(self):
        """
        Adjust thresholds based on collected person height samples
        """
        if len(self.person_height_samples) < 5:
            return
            
        # Analyze typical standing positions
        avg_standing_foot_y = sum(s['foot_y'] for s in self.person_height_samples) / len(self.person_height_samples)
        avg_standing_head_y = sum(s['head_y'] for s in self.person_height_samples) / len(self.person_height_samples)
        
        # Adjust thresholds based on typical standing positions
        # If people typically appear lower in frame, adjust thresholds accordingly
        if avg_standing_foot_y > 0.8:  # People appear very low when standing
            # Camera is high or angled - be more lenient
            adjustment_factor = 0.9
        elif avg_standing_foot_y < 0.6:  # People appear high when standing
            # Camera is low or close - be more strict
            adjustment_factor = 1.1
        else:
            adjustment_factor = 1.0
        
        # Apply gradual adjustment (don't change too quickly)
        self.LOW_POS_THR = self.LOW_POS_THR * 0.95 + (self.LOW_POS_THR * adjustment_factor) * 0.05
        self.GROUND_LEVEL_THR = self.GROUND_LEVEL_THR * 0.95 + (self.GROUND_LEVEL_THR * adjustment_factor) * 0.05
        
        # Ensure thresholds stay within reasonable bounds
        self.LOW_POS_THR = max(0.6, min(0.85, self.LOW_POS_THR))
        self.GROUND_LEVEL_THR = max(0.7, min(0.9, self.GROUND_LEVEL_THR))
        
        if self.frame_analysis_count % 300 == 0:  # Log every 300 frames
            print(f"🔧 Auto-calibrated thresholds: Low={self.LOW_POS_THR:.2f}, Ground={self.GROUND_LEVEL_THR:.2f}")
    
    def get_camera_config_display(self):
        """
        Get camera configuration for display in web interface
        """
        return {
            'mounting': self.camera_config['mounting_height'],
            'angle': self.camera_config['viewing_angle'],
            'thresholds': self.threshold_config,
            'samples': len(self.person_height_samples),
            'auto_calibrate': self.camera_config['auto_calibrate']
        }
        
    def detect_fall(self, landmarks, frame_height, frame_width):
        """Integrated fall detection: Core algorithm + Multi-condition enhancements"""
        if not landmarks:
            return False
        
        # Performance optimization: Skip analysis on some frames
        self.frame_skip_counter += 1
        if self.frame_skip_counter % self.analysis_frequency != 0:
            # Return previous detection result for skipped frames
            return hasattr(self, 'last_detection_details') and self.last_detection_details.get('fall_detected', False)
            
        current_time = time.time()
        
        try:
            # CORE ALGORITHM: Key landmarks calculation (KEEP THIS LOGIC)
            lm = landmarks
            
            # Key landmarks - CORE ALGORITHM
            sh = [(lm[11].x+lm[12].x)/2, (lm[11].y+lm[12].y)/2]  # shoulders
            hip = [(lm[23].x+lm[24].x)/2, (lm[23].y+lm[24].y)/2]  # hips
            ankle = [(lm[27].x+lm[28].x)/2, (lm[27].y+lm[28].y)/2]  # ankles
            nose = [lm[0].x, lm[0].y]  # head
            
            # CORE ALGORITHM: Torso angle calculation
            torso_vec = (hip[0]-sh[0], hip[1]-sh[1])
            torso_angle = abs(np.degrees(np.arctan2(*torso_vec[::-1])))
            
            # CORE ALGORITHM: Aspect ratio calculation
            body_h = abs(sh[1]-ankle[1])
            body_w = abs(lm[11].x-lm[12].x)
            aspect = body_w/body_h if body_h > 0 else 0
            
            # CORE ALGORITHM: Vertical speed tracking
            if self.last_hip_y is None:
                self.last_hip_y = hip[1]
            if self.last_head_y is None:
                self.last_head_y = nose[1]
            
            # CORE ALGORITHM: Speed calculations
            hip_speed = hip[1] - self.last_hip_y
            head_speed = nose[1] - self.last_head_y
            self.last_hip_y = hip[1]
            self.last_head_y = nose[1]
            
            # CORE ALGORITHM: Velocity history management
            self.vel_history.append(hip_speed)
            self.vel_history = self.vel_history[-self.HISTORY_SIZE:]
            
            self.head_vel_history.append(head_speed)
            self.head_vel_history = self.head_vel_history[-self.HISTORY_SIZE:]
            
            # Enhanced: Angle and aspect history for stability
            self.torso_angle_history.append(torso_angle)
            self.torso_angle_history = self.torso_angle_history[-3:]
            
            self.aspect_history.append(aspect)
            self.aspect_history = self.aspect_history[-3:]
            
            # CORE ALGORITHM: Average calculations
            avg_hip_speed = np.mean(self.vel_history)
            avg_head_speed = np.mean(self.head_vel_history) if self.head_vel_history else 0
            avg_torso_angle = np.mean(self.torso_angle_history) if self.torso_angle_history else torso_angle
            avg_aspect = np.mean(self.aspect_history) if self.aspect_history else aspect
            
            # ENHANCED UPRIGHT CHECK - Prevention for Sitting/Kneeling/Bending
            # 1. Standing/Bending Check: torso angle < 45° AND hip not too low (< 70%)
            is_upright_posture = (
                avg_torso_angle < 45 and  # Torso relatively vertical (bending forward is OK)
                hip[1] < 0.7              # Hip in upper 70% of frame (not sitting/kneeling)
            )
            
            # 2. Clear Standing Check: very vertical posture
            is_clearly_standing = (
                avg_torso_angle < 35 and  # Torso is mostly vertical
                avg_aspect < 0.7 and      # Person is taller than wide
                hip[1] < 0.8 and          # Hip not in bottom 20% of frame
                body_h > 0.3              # Person has good vertical height
            )
            
            # If clearly upright (standing/bending), immediately return False
            if is_upright_posture or is_clearly_standing:
                posture_type = "STANDING" if is_clearly_standing else "BENDING/UPRIGHT"
                self.last_detection_details = {
                    'torso_angle': torso_angle,
                    'aspect_ratio': aspect,
                    'hip_y': hip[1],
                    'head_y': nose[1],
                    'is_upright_posture': is_upright_posture,
                    'is_clearly_standing': is_clearly_standing,
                    'posture_type': posture_type,
                    'fall_detected': False
                }
                return False
            
            # CORE ALGORITHM: Main conditions - ENHANCED with motion analysis
            lying = avg_torso_angle > self.TORSO_THR or avg_aspect > self.ASPECT_THR  # Either condition (balanced)
            fast_drop = avg_hip_speed > self.SPEED_THR
            low_pos = hip[1] > self.LOW_POS_THR  # bottom portion of frame
            
            # ENHANCED CONDITIONS for better accuracy
            head_drop = avg_head_speed > self.HEAD_SPEED_THR
            
            # NEW: Head Near Floor Check (Extra Safety for Lying Detection)
            # When lying, head should also be near ground, not just hips
            # Sitting/kneeling → hips low but head still higher
            head_near_floor = nose[1] > 0.8  # Head in bottom 20% of frame
            
            # NEW: Motion Evidence (Differentiate Sitting vs Fall)
            # Fast motion suggests fall, slow motion suggests sitting/kneeling
            vertical_speed = max(avg_hip_speed, avg_head_speed)  # Use maximum speed
            is_fast_motion = vertical_speed > 0.03  # Possible fall motion
            is_slow_motion = vertical_speed <= 0.03  # Sitting/kneeling motion
            
            # AUTO-CALIBRATION: Learn from current frame
            self.auto_calibrate_thresholds(lm)
            
            # CAMERA-DEPENDENT STATIC FALL DETECTION
            
            # Method 1: Clearly horizontal body (aspect ratio indicates lying) - BALANCED
            horizontal_body = avg_aspect > 0.8  # Body is wider than tall (balanced)
            
            # Method 2: Severely tilted torso (person is lying down) - BALANCED
            severely_tilted = avg_torso_angle > 70  # Tilted torso (balanced)
            
            # Method 3: Camera-dependent position checks
            on_ground = hip[1] > self.GROUND_LEVEL_THR  # Using adaptive ground threshold
            head_very_low = nose[1] > self.HEAD_LOW_THR  # Using adaptive head threshold
            
            # Method 4: Combined lying indicators - ENHANCED with head position
            lying_posture = horizontal_body or severely_tilted  # Either condition (balanced)
            
            # ENHANCED STATIC FALL DETECTION with head position validation
            # Require head near floor for true lying detection (prevents sitting/kneeling false positives)
            static_fall = lying_posture and low_pos and head_near_floor  # Must be lying AND low position AND head low
            ground_level_fall = on_ground and lying_posture and head_near_floor  # On ground AND lying posture AND head low
            very_obvious_fall = horizontal_body and on_ground and head_near_floor  # Clearly horizontal AND on ground AND head low
            fallen_person = head_very_low and lying_posture  # Head low AND lying posture (already has head check)
            
            # NEW: Sitting/Kneeling Detection (to exclude from fall detection)
            # Low hips but head still up = sitting/kneeling, not fallen
            is_sitting_kneeling = (
                low_pos and  # Hips are low
                not head_near_floor and  # But head is NOT near floor
                is_slow_motion and  # Motion was slow (not a fall)
                avg_torso_angle < 80  # Not completely horizontal
            )
            
            # CAMERA HEIGHT COMPENSATION
            # For high cameras, also check if person appears "compressed" (smaller height)
            if hasattr(self, 'person_height_samples') and len(self.person_height_samples) > 0:
                avg_normal_height = sum(s['height'] for s in self.person_height_samples) / len(self.person_height_samples)
                current_height = abs(nose[1] - hip[1])
                height_compressed = current_height < avg_normal_height * 0.6  # Person appears 40% shorter
                compressed_fall = height_compressed and low_pos and lying_posture
            else:
                compressed_fall = False
            
            # ENHANCED FALL DETECTION LOGIC with motion and head position validation
            
            # Core dynamic fall: lying posture + fast motion (prevents slow sitting)
            core_dynamic_fall = lying and fast_drop and is_fast_motion
            
            # Core static fall: lying posture + low position + head near floor (prevents sitting)
            core_static_fall = lying and low_pos and head_near_floor
            
            # Combined core fall detection
            core_fall = core_dynamic_fall or core_static_fall
            
            # ENHANCED FALL DETECTION with sitting/kneeling prevention
            enhanced_fall = (
                core_fall or                           # Enhanced core fall (with motion + head validation)
                static_fall or                         # Static lying detection (with head validation)
                ground_level_fall or                   # Ground level detection (with head validation)
                very_obvious_fall or                   # Very obvious lying position (with head validation)
                fallen_person                          # Fallen person detection (already has head check)
            ) and not is_sitting_kneeling              # EXCLUDE sitting/kneeling positions
            
            # DEBUG: Print values for troubleshooting - ENHANCED with confirmation metrics
            if self.frame_skip_counter % 30 == 0:  # Print every 30 frames
                print(f"DEBUG - Torso: {avg_torso_angle:.1f}° (thr:{self.TORSO_THR}), Aspect: {avg_aspect:.3f} (thr:{self.ASPECT_THR})")
                print(f"DEBUG - Position: Hip Y: {hip[1]:.3f} (thr:{self.LOW_POS_THR}), Head Y: {nose[1]:.3f}")
                print(f"DEBUG - Motion: Hip_speed: {avg_hip_speed:.4f}, Head_speed: {avg_head_speed:.4f}, Vertical_speed: {vertical_speed:.4f}")
                print(f"DEBUG - Conditions: Lying: {lying}, Low_pos: {low_pos}, Head_near_floor: {head_near_floor}")
                print(f"DEBUG - Motion Type: Fast_motion: {is_fast_motion}, Slow_motion: {is_slow_motion}")
                print(f"DEBUG - Posture: Sitting/Kneeling: {is_sitting_kneeling}, Horizontal_body: {horizontal_body}")
                print(f"DEBUG - Detection: Core_fall: {core_fall}, Enhanced_fall: {enhanced_fall}")
                print(f"DEBUG - Confirmation: Lying_frames: {self.lying_posture_frames}/{self.min_lying_frames}, Detection_frames: {self.fall_detection_frames}/{self.FRAMES_CONFIRM}")
                print("---")
            
            # ENHANCED Multi-condition analysis with new metrics
            motion_conditions = [fast_drop, head_drop, is_fast_motion, avg_hip_speed > self.thresholds['head_velocity'], avg_head_speed > self.HEAD_SPEED_THR]
            pose_conditions = [lying, low_pos, horizontal_body, severely_tilted, on_ground, head_near_floor, static_fall, ground_level_fall, compressed_fall]
            prevention_conditions = [is_sitting_kneeling, is_slow_motion and low_pos]  # Conditions that prevent fall detection
            
            motion_score = sum(motion_conditions)
            pose_score = sum(pose_conditions)
            prevention_score = sum(prevention_conditions)
            
            # ENHANCED confidence level and detection type with prevention logic
            detection_type = "none"
            if is_sitting_kneeling:
                confidence_level = "none"
                detection_type = "sitting_kneeling"
            elif enhanced_fall:
                if compressed_fall:
                    confidence_level = "high"
                    detection_type = "compressed"
                elif very_obvious_fall:
                    confidence_level = "high"
                    detection_type = "obvious"
                elif ground_level_fall:
                    confidence_level = "high"
                    detection_type = "ground"
                elif fallen_person:
                    confidence_level = "high"
                    detection_type = "fallen"
                elif static_fall:
                    confidence_level = "high" 
                    detection_type = "static"
                elif core_dynamic_fall:
                    confidence_level = "high"
                    detection_type = "dynamic"
                elif core_static_fall:
                    confidence_level = "high"
                    detection_type = "static_validated"
                elif horizontal_body and low_pos and head_near_floor:
                    confidence_level = "medium"
                    detection_type = "horizontal_validated"
                elif severely_tilted and low_pos and head_near_floor:
                    confidence_level = "medium"
                    detection_type = "tilted_validated"
                else:
                    confidence_level = "low"
                    detection_type = "detected"
            else:
                confidence_level = "none"
            
            # Store comprehensive detection details with ENHANCED metrics
            self.last_detection_details = {
                # Core algorithm metrics
                'torso_angle': torso_angle,
                'aspect_ratio': aspect,
                'hip_speed': avg_hip_speed,
                'head_speed': avg_head_speed,
                'lying': lying,
                'fast_drop': fast_drop,
                'head_drop': head_drop,
                'low_pos': low_pos,
                'hip_y': hip[1],
                'head_y': nose[1],
                
                # NEW: Enhanced detection metrics
                'head_near_floor': head_near_floor,
                'vertical_speed': vertical_speed,
                'is_fast_motion': is_fast_motion,
                'is_slow_motion': is_slow_motion,
                'is_sitting_kneeling': is_sitting_kneeling,
                'is_upright_posture': is_upright_posture if 'is_upright_posture' in locals() else False,
                'is_clearly_standing': is_clearly_standing if 'is_clearly_standing' in locals() else False,
                
                # Enhanced fall detection types
                'core_dynamic_fall': core_dynamic_fall,
                'core_static_fall': core_static_fall,
                'static_fall': static_fall,
                'ground_level_fall': ground_level_fall,
                'very_obvious_fall': very_obvious_fall,
                'fallen_person': fallen_person,
                'compressed_fall': compressed_fall,
                'horizontal_body': horizontal_body,
                'severely_tilted': severely_tilted,
                'on_ground': on_ground,
                'head_very_low': head_very_low,
                'lying_posture': lying_posture,
                
                # Camera configuration
                'camera_config': self.get_camera_config_display(),
                'adaptive_thresholds': {
                    'low_pos': self.LOW_POS_THR,
                    'ground_level': self.GROUND_LEVEL_THR,
                    'head_low': self.HEAD_LOW_THR
                },
                
                # Enhanced multi-condition metrics
                'motion_score': motion_score,
                'pose_score': pose_score,
                'prevention_score': prevention_score,
                'confidence_level': confidence_level,
                'detection_type': detection_type,
                'fall_detected': enhanced_fall,
                'core_fall': core_fall,
                'analysis_frame': self.frame_skip_counter,
                
                # Enhanced motion features
                'head_velocity': avg_head_speed,
                'torso_velocity': avg_hip_speed,
                'head_acceleration': 0.0,  # Simplified for core algorithm
                'torso_acceleration': 0.0,  # Simplified for core algorithm
                'rapid_downward_motion': fast_drop,
                'sudden_acceleration': head_drop,
                'fall_motion_pattern': core_fall,
                'ratio_collapse': avg_aspect > self.ASPECT_THR,
                
                # Enhanced position details
                'is_low_position': low_pos,
                'is_horizontal': avg_aspect > self.ASPECT_THR,
                'is_head_low': nose[1] > 0.6,
                'is_head_near_floor': head_near_floor,
                'hip_center_y': hip[1],
                'posture_type': detection_type,
                
                # NEW: Confirmation system metrics
                'lying_posture_frames': self.lying_posture_frames,
                'min_lying_frames_required': self.min_lying_frames,
                'confirmation_buffer_size': len(self.confirmation_buffer),
                'recent_detections_count': sum(self.confirmation_buffer[-8:]) if len(self.confirmation_buffer) >= 8 else sum(self.confirmation_buffer),
                'confirmation_progress': min(1.0, self.lying_posture_frames / self.min_lying_frames) if self.min_lying_frames > 0 else 0.0
            }
            
            return enhanced_fall
            
        except Exception as e:
            print(f"Error in integrated fall detection: {e}")
            return False
    

            
    def update_fall_state(self, current_fall_detected):
        """ENHANCED fall state update with patience-based confirmation system"""
        
        # Add current detection to confirmation buffer
        self.confirmation_buffer.append(current_fall_detected)
        if len(self.confirmation_buffer) > self.confirmation_buffer_size:
            self.confirmation_buffer.pop(0)  # Remove oldest entry
        
        # ENHANCED CONFIRMATION LOGIC: Require consecutive lying posture frames
        if current_fall_detected:
            self.lying_posture_frames += 1
            self.fall_detection_frames += 1
        else:
            # PATIENCE SYSTEM: Don't immediately reset, allow brief interruptions
            if self.lying_posture_frames > 0:
                self.lying_posture_frames = max(0, self.lying_posture_frames - 2)  # Gradual decrease
            self.fall_detection_frames = max(0, self.fall_detection_frames - 1)
        
        # ENHANCED CONFIRMATION CRITERIA
        # Method 1: Consecutive lying frames (primary method)
        consecutive_lying_confirmed = self.lying_posture_frames >= self.min_lying_frames
        
        # Method 2: Overall detection frames (secondary method)
        overall_frames_confirmed = self.fall_detection_frames >= self.FRAMES_CONFIRM
        
        # Method 3: Buffer analysis - check for consistent detection in recent frames
        recent_detections = self.confirmation_buffer[-8:] if len(self.confirmation_buffer) >= 8 else self.confirmation_buffer
        buffer_consistency = sum(recent_detections) >= len(recent_detections) * 0.75 if recent_detections else False
        
        # COMBINED CONFIRMATION LOGIC (require multiple evidence)
        was_confirmed = self.fall_detected
        
        # Confirm fall if ANY of these conditions are met:
        # 1. Consecutive lying frames reached minimum threshold
        # 2. Overall frames confirmed AND buffer shows consistency
        # 3. Very high confidence with shorter confirmation (emergency cases)
        emergency_confirmation = (
            self.lying_posture_frames >= 6 and  # At least 6 consecutive frames
            buffer_consistency and               # Recent consistency
            hasattr(self, 'last_detection_details') and 
            self.last_detection_details.get('confidence_level') == 'high'
        )
        
        self.fall_detected = (
            consecutive_lying_confirmed or 
            (overall_frames_confirmed and buffer_consistency) or
            emergency_confirmation
        )
        
        # Alert on new fall confirmation
        if self.fall_detected and not was_confirmed:
            self.fall_start_time = time.time()
            confidence = self.last_detection_details.get('confidence_level', 'unknown') if hasattr(self, 'last_detection_details') else 'unknown'
            detection_type = self.last_detection_details.get('detection_type', 'unknown') if hasattr(self, 'last_detection_details') else 'unknown'
            
            print(f"🚨 FALL ALERT: Fall confirmed with patience system!")
            print(f"   Consecutive lying frames: {self.lying_posture_frames}/{self.min_lying_frames}")
            print(f"   Total detection frames: {self.fall_detection_frames}/{self.FRAMES_CONFIRM}")
            print(f"   Buffer consistency: {sum(recent_detections)}/{len(recent_detections)} frames")
            print(f"   Confidence: {confidence} | Type: {detection_type}")
            
            # Log core algorithm metrics
            if hasattr(self, 'last_detection_details') and self.last_detection_details:
                details = self.last_detection_details
                print(f"   Core Metrics: Torso={details.get('torso_angle', 0):.1f}° | Aspect={details.get('aspect_ratio', 0):.2f} | Speed={details.get('hip_speed', 0):.3f}")
        
        # ENHANCED RESET LOGIC: Clear state when person is clearly upright
        clear_upright_frames = self.upright_clear_frames  # Use instance variable
        if len(self.confirmation_buffer) >= clear_upright_frames:
            recent_non_detections = self.confirmation_buffer[-clear_upright_frames:]
            if not any(recent_non_detections):  # All recent frames show no fall
                if was_confirmed:
                    self.fall_detected = False
                    self.lying_posture_frames = 0
                    self.fall_detection_frames = 0
                    print("✅ Fall state cleared - person clearly upright")
        
        # Prevent indefinite accumulation
        if self.lying_posture_frames > self.max_lying_frames:
            self.lying_posture_frames = self.max_lying_frames
        if self.fall_detection_frames > self.FRAMES_CONFIRM + 5:
            self.fall_detection_frames = self.FRAMES_CONFIRM + 5
                
    def get_current_risk(self):
        """Calculate current risk level"""
        if self.fall_detected:
            return 1.0
        elif self.fall_detection_frames > 0:
            return self.fall_detection_frames / self.fall_threshold_frames
        else:
            return 0.0
        
    def setup_video_source(self, video_source):
        """Setup video capture source for web streaming"""
        try:
            if isinstance(video_source, int):
                # Camera source - always default to camera 0 if issues
                if video_source < 0:
                    video_source = 0
                self.cap = cv2.VideoCapture(video_source)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                print(f"✅ Using camera {video_source} (Default Camera)")
            else:
                # Video file source
                script_dir = os.path.dirname(os.path.abspath(__file__))
                video_path = os.path.join(script_dir, '..', 'Fall-Detection-main', video_source)
                self.cap = cv2.VideoCapture(video_path)
                print(f"✅ Using video file: {video_source}")
                
            if not self.cap.isOpened():
                raise Exception(f"Could not open video source: {video_source}")
                
        except Exception as e:
            print(f"⚠️  Error setting up video source: {e}")
            print("🔄 Falling back to default camera (index 0)")
            # Always fallback to default camera (index 0)
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                print("✅ Default camera (0) opened successfully")
            else:
                print("❌ Could not open default camera")
            
    def get_frame_for_web(self):
        """Get processed frame for web streaming"""
        global detection_stats, fall_detected
        
        ret, frame = self.cap.read()
        if not ret:
            return None
            
        # Resize for web streaming
        frame = cv2.resize(frame, (640, 480))
        self.frame_count += 1
        
        # Process frame for fall detection
        processed_frame, current_fall_detected = self.process_frame(frame)
        
        # Update fall state
        self.update_fall_state(current_fall_detected)
        
        # Update global stats
        if hasattr(self, 'person_detections'):
            detection_stats["total_detections"] = self.person_detections
        detection_stats["current_risk"] = self.get_current_risk()
        fall_detected = self.fall_detected
        
        if self.fall_detected and not fall_detected:
            detection_stats["falls_detected"] += 1
            
        # Draw status and alerts
        self.draw_status(processed_frame)
        
        # Add web-specific overlays
        self.draw_web_overlay(processed_frame)
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()
        
    def process_frame(self, frame):
        """MediaPipe-based frame processing with person detection"""
        frame_height, frame_width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        current_fall_detected = False
        person_count = 0
        
        if results.pose_landmarks:
            person_count = 1
            self.person_detections = person_count
            
            # Draw pose landmarks
            self.mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
            )
            
            # Check for fall
            is_fall = self.detect_fall(results.pose_landmarks.landmark, frame_height, frame_width)
            current_fall_detected = is_fall
            
            # Get bounding box of the person
            landmarks = results.pose_landmarks.landmark
            x_coords = [lm.x * frame_width for lm in landmarks if lm.visibility > 0.5]
            y_coords = [lm.y * frame_height for lm in landmarks if lm.visibility > 0.5]
            
            if x_coords and y_coords:
                x1, y1 = int(min(x_coords)) - 20, int(min(y_coords)) - 20
                x2, y2 = int(max(x_coords)) + 20, int(max(y_coords)) + 20
                
                # Ensure bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame_width, x2), min(frame_height, y2)
                
                # Draw bounding box with enhanced styling
                box_color = (0, 0, 255) if is_fall else (0, 255, 0)  # Red for fall, Green for normal
                
                # Draw rectangle and corner accents
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                
                # Draw corner accents
                corner_length = 20
                cv2.line(frame, (x1, y1), (x1 + corner_length, y1), box_color, 4)
                cv2.line(frame, (x1, y1), (x1, y1 + corner_length), box_color, 4)
                cv2.line(frame, (x2, y1), (x2 - corner_length, y1), box_color, 4)
                cv2.line(frame, (x2, y1), (x2, y1 + corner_length), box_color, 4)
                cv2.line(frame, (x1, y2), (x1 + corner_length, y2), box_color, 4)
                cv2.line(frame, (x1, y2), (x1, y2 - corner_length), box_color, 4)
                cv2.line(frame, (x2, y2), (x2 - corner_length, y2), box_color, 4)
                cv2.line(frame, (x2, y2), (x2, y2 - corner_length), box_color, 4)
                
                # Integrated algorithm enhanced label
                if is_fall and hasattr(self, 'last_detection_details') and self.last_detection_details:
                    confidence = self.last_detection_details.get('confidence_level', 'unknown')
                    motion_score = self.last_detection_details.get('motion_score', 0)
                    pose_score = self.last_detection_details.get('pose_score', 0)
                    detection_type = self.last_detection_details.get('detection_type', 'unknown')
                    
                    # Show detection type
                    type_map = {
                        'compressed': 'COMPRESS', 'obvious': 'OBVIOUS', 'ground': 'GROUND', 
                        'fallen': 'FALLEN', 'static': 'STATIC', 'dynamic': 'CORE', 
                        'horizontal': 'HORIZ', 'tilted': 'TILTED', 'detected': 'DETECT'
                    }
                    type_display = type_map.get(detection_type, 'FALL')
                    
                    status_text = f"FALL! {confidence.upper()} {type_display} (M:{motion_score}/P:{pose_score})"
                else:
                    status_text = "NORMAL POSTURE"
                
                label_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), (x1 + label_size[0] + 10, y1), box_color, -1)
                cv2.putText(frame, status_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Display core algorithm + enhanced metrics
                if hasattr(self, 'last_detection_details') and self.last_detection_details:
                    details = self.last_detection_details
                    # Core algorithm metrics (KEEP THESE)
                    core_metrics = f'T:{details.get("torso_angle", 0):.1f}° AR:{details.get("aspect_ratio", 0):.2f} V:{details.get("hip_speed", 0):.3f}'
                    cv2.putText(frame, core_metrics, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    
                    # Enhanced condition flags including static detection
                    lying = "L" if details.get("lying", False) else "-"
                    fast_drop = "F" if details.get("fast_drop", False) else "-"
                    head_drop = "H" if details.get("head_drop", False) else "-"
                    low_pos = "P" if details.get("low_pos", False) else "-"
                    static = "S" if details.get("static_fall", False) else "-"
                    ground = "G" if details.get("ground_level_fall", False) else "-"
                    
                    flags = f'Detect: [{lying}{fast_drop}{head_drop}{low_pos}{static}{ground}] | Frames: {self.fall_detection_frames}/{self.FRAMES_CONFIRM}'
                    cv2.putText(frame, flags, (x1, y2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame, current_fall_detected
        

            
    def draw_status(self, frame):
        """Draw system status and alerts with motion analysis"""
        if self.fall_detected:
            # Flash alert
            flash = int(time.time() * 4) % 2  # 4 flashes per second
            alert_color = (0, 0, 255) if flash else (0, 255, 255)  # Red/Yellow flash
            
            cv2.putText(frame, 'FALL ALERT!', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, alert_color, 3)
            
            if self.fall_start_time:
                duration = time.time() - self.fall_start_time
                cv2.putText(frame, f'Duration: {duration:.1f}s', (50, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, alert_color, 2)
                
            # Show confidence level
            if hasattr(self, 'last_detection_details') and self.last_detection_details:
                confidence = self.last_detection_details.get('confidence_level', 'unknown')
                cv2.putText(frame, f'Confidence: {confidence.upper()}', (50, 140), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, alert_color, 2)
        
        # System status
        status_color = (0, 255, 0) if not self.fall_detected else (0, 0, 255)
        status_text = "MONITORING" if not self.fall_detected else "ALERT"
        cv2.putText(frame, f'Status: {status_text}', (frame.shape[1] - 200, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        
        # Motion analysis display
        if hasattr(self, 'last_detection_details') and self.last_detection_details:
            details = self.last_detection_details
            y_offset = frame.shape[0] - 120
            
            # Motion indicators
            motion_color = (0, 255, 255)  # Yellow for motion data
            cv2.putText(frame, 'Motion Analysis:', (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, motion_color, 1)
            
            # Velocity
            head_vel = details.get('head_velocity', 0)
            cv2.putText(frame, f'Head Vel: {head_vel:.3f}', (10, y_offset + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, motion_color, 1)
            
            # Acceleration
            head_acc = details.get('head_acceleration', 0)
            cv2.putText(frame, f'Head Acc: {head_acc:.3f}', (10, y_offset + 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, motion_color, 1)
            
            # Motion flags
            rapid_motion = details.get('rapid_downward_motion', False)
            sudden_acc = details.get('sudden_acceleration', False)
            fall_pattern = details.get('fall_motion_pattern', False)
            
            flag_color = (0, 255, 0) if rapid_motion else (100, 100, 100)
            cv2.putText(frame, f'Rapid: {"YES" if rapid_motion else "NO"}', (150, y_offset + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, flag_color, 1)
            
            flag_color = (0, 255, 0) if sudden_acc else (100, 100, 100)
            cv2.putText(frame, f'Sudden: {"YES" if sudden_acc else "NO"}', (150, y_offset + 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, flag_color, 1)
            
            flag_color = (0, 255, 0) if fall_pattern else (100, 100, 100)
            cv2.putText(frame, f'Pattern: {"YES" if fall_pattern else "NO"}', (150, y_offset + 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, flag_color, 1)
        
        # System info
        cv2.putText(frame, 'SafeSense AI Fall Detection', (20, frame.shape[0] - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                   
    def draw_web_overlay(self, frame):
        """Draw web-specific overlay information"""
        h, w = frame.shape[:2]
        
        # Add SafeSense branding
        cv2.putText(frame, 'SafeSense', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (30, 60, 114), 2)
        cv2.putText(frame, 'Smart Fall Detection', (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add frame counter
        cv2.putText(frame, f'Frame: {self.frame_count}', (w - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add person count
        if hasattr(self, 'person_detections'):
            cv2.putText(frame, f'Persons: {self.person_detections}', (w - 150, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
    def configure_camera_setup(self, mounting_height='medium', viewing_angle='normal', distance='medium'):
        """
        Manually configure camera setup for optimal thresholds
        
        Args:
            mounting_height: 'low', 'medium', 'high'
            viewing_angle: 'top-down', 'normal', 'low-angle'  
            distance: 'close', 'medium', 'far'
        """
        self.camera_config.update({
            'mounting_height': mounting_height,
            'viewing_angle': viewing_angle,
            'distance': distance
        })
        
        # Recalculate thresholds with new configuration
        self.setup_camera_dependent_thresholds()
        
        print(f"📹 Camera reconfigured: {mounting_height} height, {viewing_angle} angle, {distance} distance")
        return self.threshold_config
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            print("Camera released")

# Serve static files
@app.route('/')
def index():
    return send_from_directory('../simple-frontend', 'login.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('../simple-frontend', filename)

# Video streaming
def generate_frames():
    global detector, detection_active
    while detector and detection_active:
        try:
            frame = detector.get_frame_for_web()
            if frame is None:
                time.sleep(0.1)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error generating frame: {e}")
            break

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera_list')
def camera_list():
    """Get list of available cameras"""
    cameras = []
    for i in range(5):  # Check first 5 camera indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append({
                'id': i,
                'name': f'Camera {i}',
                'description': f'USB Camera {i}' if i > 0 else 'Default Camera'
            })
            cap.release()
    
    # Add video file options
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_dir = os.path.join(script_dir, '..', 'Fall-Detection-main')
    video_files = ['VID-20250830-WA0018.mp4', 'fall.mp4', 'fall2.mp4']
    
    for video_file in video_files:
        video_path = os.path.join(video_dir, video_file)
        if os.path.exists(video_path):
            cameras.append({
                'id': video_file,
                'name': video_file,
                'description': f'Video File: {video_file}'
            })
    
    return jsonify(cameras)

# API endpoints
@app.route('/start', methods=['POST'])
def start_detection():
    global detector, detection_active, detection_stats
    try:
        # Get camera ID from request, default to camera 0
        data = request.get_json() if request.is_json else {}
        camera_source = data.get('camera', 0)
        
        # Ensure we always use a valid camera index (default to 0)
        if not isinstance(camera_source, int) or camera_source < 0:
            camera_source = 0
            print("🔄 Invalid camera source, defaulting to camera 0")
        
        # Stop existing detector
        if detector:
            detector.cleanup()
            
        # Create new detector with default camera
        print(f"🎥 Starting detection with camera {camera_source}")
        detector = WebFallDetector(camera_source)
        detection_active = True
        detection_stats["start_time"] = time.time()
        
        return jsonify({
            "success": True, 
            "message": f"Detection started with default camera {camera_source}",
            "camera": camera_source
        })
    except Exception as e:
        print(f"❌ Error starting detection: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/stop', methods=['POST'])
def stop_detection():
    global detector, detection_active
    try:
        detection_active = False
        if detector:
            detector.cleanup()
            detector = None
        return jsonify({"success": True, "message": "Detection stopped"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/reset', methods=['POST'])
def reset_detection():
    global detector, fall_detected, detection_stats
    try:
        if detector:
            detector.fall_detected = False
            detector.fall_detection_frames = 0
            detector.fall_start_time = None
        fall_detected = False
        detection_stats["falls_detected"] = 0
        return jsonify({"success": True, "message": "Detection reset"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/stats')
def get_stats():
    global detection_stats, fall_detected, detector
    
    # Calculate uptime
    if detection_stats.get("start_time"):
        detection_stats["uptime"] = int(time.time() - detection_stats["start_time"])
    
    # Get current risk from detector
    if detector:
        detection_stats["current_risk"] = detector.get_current_risk()
    
    # Add camera configuration to stats
    stats_response = {
        **detection_stats,
        "fall_detected": fall_detected,
        "detection_active": detection_active
    }
    
    if detector and hasattr(detector, 'get_camera_config_display'):
        stats_response["camera_config"] = detector.get_camera_config_display()
    
    return jsonify(stats_response)



@app.route('/camera_config', methods=['GET', 'POST'])
def camera_config():
    """Get or set camera configuration for adaptive thresholds"""
    global detector
    
    if not detector:
        return jsonify({"success": False, "error": "Detector not initialized"})
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            mounting = data.get('mounting_height', 'medium')
            angle = data.get('viewing_angle', 'normal')
            distance = data.get('distance', 'medium')
            
            # Validate inputs
            valid_heights = ['low', 'medium', 'high']
            valid_angles = ['top-down', 'normal', 'low-angle']
            valid_distances = ['close', 'medium', 'far']
            
            if mounting not in valid_heights:
                return jsonify({"success": False, "error": f"Invalid mounting_height. Use: {valid_heights}"})
            if angle not in valid_angles:
                return jsonify({"success": False, "error": f"Invalid viewing_angle. Use: {valid_angles}"})
            if distance not in valid_distances:
                return jsonify({"success": False, "error": f"Invalid distance. Use: {valid_distances}"})
            
            # Reconfigure camera setup
            new_config = detector.configure_camera_setup(mounting, angle, distance)
            
            return jsonify({
                "success": True,
                "message": f"Camera configured: {mounting} height, {angle} angle, {distance} distance",
                "config": new_config,
                "thresholds": {
                    "low_position": f"{(1-detector.LOW_POS_THR)*100:.0f}% from bottom",
                    "ground_level": f"{(1-detector.GROUND_LEVEL_THR)*100:.0f}% from bottom", 
                    "head_low": f"{(1-detector.HEAD_LOW_THR)*100:.0f}% from bottom"
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    else:  # GET request
        try:
            config = detector.get_camera_config_display()
            return jsonify({
                "success": True,
                "config": config,
                "available_options": {
                    "mounting_height": ["low", "medium", "high"],
                    "viewing_angle": ["top-down", "normal", "low-angle"],
                    "distance": ["close", "medium", "far"]
                },
                "current_thresholds": {
                    "low_position": f"{detector.LOW_POS_THR:.2f} ({(1-detector.LOW_POS_THR)*100:.0f}% from bottom)",
                    "ground_level": f"{detector.GROUND_LEVEL_THR:.2f} ({(1-detector.GROUND_LEVEL_THR)*100:.0f}% from bottom)",
                    "head_low": f"{detector.HEAD_LOW_THR:.2f} ({(1-detector.HEAD_LOW_THR)*100:.0f}% from bottom)"
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    print("🚀 Starting Simple AI Fall Detection System...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=5000, debug=False)