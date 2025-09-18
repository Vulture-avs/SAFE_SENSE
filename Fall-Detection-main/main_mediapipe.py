import cv2
import cvzone
import math
import mediapipe as mp
import numpy as np
import time
import os
from config import FallDetectionConfig

class MediaPipeFallDetectionSystem:
    def __init__(self, video_source=None):
        """Initialize the MediaPipe-based fall detection system"""
        self.config = FallDetectionConfig()
        self.setup_video_source(video_source)
        self.setup_mediapipe()
        self.setup_detection_parameters()
        
    def setup_video_source(self, video_source):
        """Setup video capture source"""
        if video_source is None:
            # Default to camera 0 (default camera)
            self.cap = cv2.VideoCapture(0)
            print("✅ Using default camera (index 0)")
        elif isinstance(video_source, int):
            # Ensure valid camera index, default to 0 if invalid
            if video_source < 0:
                video_source = 0
            self.cap = cv2.VideoCapture(video_source)
            print(f"✅ Using camera {video_source}")
        else:
            # Video file source
            script_dir = os.path.dirname(os.path.abspath(__file__))
            video_path = os.path.join(script_dir, video_source)
            if os.path.exists(video_path):
                self.cap = cv2.VideoCapture(video_path)
                print(f"✅ Using video file: {video_source}")
            else:
                # Fallback to default camera if video file not found
                print(f"⚠️  Video file {video_source} not found, using default camera")
                self.cap = cv2.VideoCapture(0)
            
    def setup_mediapipe(self):
        """Setup MediaPipe pose detection"""
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=self.config.MODEL_COMPLEXITY,
            smooth_landmarks=self.config.SMOOTH_LANDMARKS,
            enable_segmentation=False,
            smooth_segmentation=True,
            min_detection_confidence=self.config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=self.config.MIN_TRACKING_CONFIDENCE
        )
        print("MediaPipe pose detection initialized")
            
    def setup_detection_parameters(self):
        """Setup ENHANCED fall detection parameters with patience system"""
        # ENHANCED CONFIRMATION FRAMES SYSTEM
        self.fall_detection_frames = 0
        self.fall_threshold_frames = self.config.FALL_CONFIRMATION_FRAMES
        self.fall_detected = False
        self.fall_start_time = None
        self.last_detection_details = {}
        self.pose_history = []
        self.max_history = 10
        
        # NEW: Enhanced confirmation tracking for patience system
        self.lying_posture_frames = 0      # Track consecutive lying posture frames
        self.min_lying_frames = self.config.MIN_CONSECUTIVE_LYING_FRAMES    # From config
        self.max_lying_frames = self.config.MAX_LYING_FRAMES_WAIT           # From config
        self.confirmation_buffer = []      # Buffer to track recent detection states
        self.confirmation_buffer_size = self.config.CONFIRMATION_BUFFER_SIZE # From config
        
    def calculate_pose_metrics(self, landmarks):
        """Calculate comprehensive pose metrics for fall detection"""
        # Key landmarks
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value]
        right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE.value]
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        
        metrics = {}
        
        # Body centers
        shoulder_center = [(left_shoulder.x + right_shoulder.x) / 2, (left_shoulder.y + right_shoulder.y) / 2]
        hip_center = [(left_hip.x + right_hip.x) / 2, (left_hip.y + right_hip.y) / 2]
        knee_center = [(left_knee.x + right_knee.x) / 2, (left_knee.y + right_knee.y) / 2]
        ankle_center = [(left_ankle.x + right_ankle.x) / 2, (left_ankle.y + right_ankle.y) / 2]
        
        # 1. Torso angle from vertical
        torso_vector = [hip_center[0] - shoulder_center[0], hip_center[1] - shoulder_center[1]]
        torso_angle = abs(np.arctan2(torso_vector[0], torso_vector[1]) * 180 / np.pi)
        metrics['torso_angle'] = torso_angle
        
        # 2. Body aspect ratio
        body_height = abs(shoulder_center[1] - ankle_center[1])
        body_width = max(abs(left_shoulder.x - right_shoulder.x), abs(left_hip.x - right_hip.x))
        
        if body_height > 0:
            aspect_ratio = body_width / body_height
        else:
            aspect_ratio = 0
        metrics['aspect_ratio'] = aspect_ratio
        
        # 3. Head-to-hip angle (indicates body orientation)
        head_hip_vector = [hip_center[0] - nose.x, hip_center[1] - nose.y]
        head_hip_angle = abs(np.arctan2(head_hip_vector[0], head_hip_vector[1]) * 180 / np.pi)
        metrics['head_hip_angle'] = head_hip_angle
        
        # 4. Knee bend analysis
        left_knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
        metrics['avg_knee_angle'] = avg_knee_angle
        
        # 5. Body compactness
        vertical_span = abs(nose.y - ankle_center[1])
        horizontal_span = max(abs(left_shoulder.x - right_shoulder.x), 
                            abs(left_hip.x - right_hip.x))
        metrics['vertical_span'] = vertical_span
        metrics['horizontal_span'] = horizontal_span
        
        # 6. Center of mass position
        metrics['hip_center_y'] = hip_center[1]
        metrics['shoulder_center_y'] = shoulder_center[1]
        
        return metrics
    
    def calculate_angle(self, p1, p2, p3):
        """Calculate angle between three points"""
        a = np.array([p1.x, p1.y])
        b = np.array([p2.x, p2.y])
        c = np.array([p3.x, p3.y])
        
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle
    
    def detect_fall(self, landmarks, frame_height, frame_width):
        """Enhanced fall detection with sitting/kneeling prevention"""
        if not landmarks:
            return False
            
        metrics = self.calculate_pose_metrics(landmarks)
        
        # ENHANCED UPRIGHT CHECK - Prevention for Sitting/Kneeling/Bending
        # 1. Standing/Bending Check: torso angle < threshold AND hip not too low
        is_upright_posture = (
            metrics['torso_angle'] < self.config.UPRIGHT_TORSO_THRESHOLD and  # Torso relatively vertical
            metrics['hip_center_y'] < self.config.UPRIGHT_HIP_THRESHOLD       # Hip not in sitting/kneeling zone
        )
        
        # If clearly upright (standing/bending), immediately return False
        if is_upright_posture:
            return False
        
        # Fall detection conditions - ENHANCED with head position validation
        
        # 1. Torso orientation - horizontal indicates fall
        is_horizontal_torso = metrics['torso_angle'] > 65
        
        # 2. Body aspect ratio - wider than tall when fallen
        is_horizontal_body = metrics['aspect_ratio'] > 0.8
        
        # 3. Low position - hip in lower part of frame
        is_low_position = metrics['hip_center_y'] > 0.75
        
        # 4. Vertical compactness - small vertical span when fallen
        is_compact_vertically = metrics['vertical_span'] < 0.4
        
        # 5. Head-hip alignment - more horizontal when fallen
        is_head_hip_horizontal = metrics['head_hip_angle'] > 45
        
        # NEW: 6. Head Near Floor Check (Extra Safety for Lying Detection)
        # When lying, head should also be near ground, not just hips
        # Get head position from landmarks
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        is_head_near_floor = nose.y > self.config.HEAD_FLOOR_THRESHOLD  # Head near floor threshold
        
        # NEW: 7. Sitting/Kneeling Detection (to exclude from fall detection)
        # Low hips but head still up = sitting/kneeling, not fallen
        is_sitting_kneeling = (
            is_low_position and          # Hips are low
            not is_head_near_floor and   # But head is NOT near floor
            metrics['torso_angle'] < 80  # Not completely horizontal
        )
        
        # If detected as sitting/kneeling, return False
        if is_sitting_kneeling:
            return False
        
        # ENHANCED CONDITIONS - Multiple evidence paths with head validation
        fall_conditions = [
            is_horizontal_torso,
            is_horizontal_body,
            is_low_position and is_head_near_floor,  # Low position WITH head near floor
            is_compact_vertically,
            is_head_hip_horizontal
        ]
        
        conditions_met = sum(fall_conditions)
        
        # ENHANCED LOGIC: Need multiple conditions (3 out of 5) for fall detection
        # AND must not be sitting/kneeling
        is_potential_fall = conditions_met >= 3 and not is_sitting_kneeling
        
        # Store detailed metrics for debugging - ENHANCED
        self.last_detection_details = {
            **metrics,
            'is_horizontal_torso': is_horizontal_torso,
            'is_horizontal_body': is_horizontal_body,
            'is_low_position': is_low_position,
            'is_compact_vertically': is_compact_vertically,
            'is_head_hip_horizontal': is_head_hip_horizontal,
            'is_head_near_floor': is_head_near_floor,
            'is_sitting_kneeling': is_sitting_kneeling,
            'is_upright_posture': is_upright_posture,
            'conditions_met': conditions_met,
            'fall_detected': is_potential_fall,
            'head_y': nose.y
        }
        
        return is_potential_fall
    
    def process_frame(self, frame):
        """Process frame with MediaPipe pose detection"""
        frame_height, frame_width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        current_fall_detected = False
        
        if results.pose_landmarks:
            # Draw pose landmarks with custom colors
            self.mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=self.config.POSE_COLOR, thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=self.config.POSE_CONNECTION_COLOR, thickness=2)
            )
            
            # Detect fall
            is_fall = self.detect_fall(results.pose_landmarks.landmark, frame_height, frame_width)
            current_fall_detected = is_fall
            
            # Get person bounding box
            landmarks = results.pose_landmarks.landmark
            x_coords = [lm.x * frame_width for lm in landmarks if lm.visibility > 0.5]
            y_coords = [lm.y * frame_height for lm in landmarks if lm.visibility > 0.5]
            
            if x_coords and y_coords:
                x1, y1 = int(min(x_coords)) - 20, int(min(y_coords)) - 20
                x2, y2 = int(max(x_coords)) + 20, int(max(y_coords)) + 20
                
                # Ensure bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame_width, x2), min(frame_height, y2)
                
                # Draw bounding box
                box_color = self.config.FALL_COLOR if is_fall else self.config.NORMAL_COLOR
                cvzone.cornerRect(frame, [x1, y1, x2-x1, y2-y1], l=30, rt=6, colorR=box_color)
                
                # Status text
                status = "FALL DETECTED!" if is_fall else "NORMAL POSTURE"
                cvzone.putTextRect(frame, status, [x1 + 8, y1 - 12], 
                                 thickness=2, scale=1.5, colorR=box_color)
                
                # Display metrics
                self.draw_metrics(frame, x1, y2)
        else:
            cvzone.putTextRect(frame, 'No person detected', [50, 100], 
                             thickness=2, scale=1.5, colorR=(255, 255, 0))
        
        return frame, current_fall_detected
    
    def draw_metrics(self, frame, x, y):
        """Draw detection metrics on frame"""
        if not self.last_detection_details:
            return
            
        details = self.last_detection_details
        offset = 25
        
        # Torso angle
        cvzone.putTextRect(frame, f'Torso: {details["torso_angle"]:.1f}°', 
                         [x, y + offset], thickness=1, scale=0.8, colorR=self.config.INFO_COLOR)
        offset += 20
        
        # Aspect ratio
        cvzone.putTextRect(frame, f'AR: {details["aspect_ratio"]:.2f}', 
                         [x, y + offset], thickness=1, scale=0.8, colorR=self.config.INFO_COLOR)
        offset += 20
        
        # Conditions met
        color = self.config.NORMAL_COLOR if details['conditions_met'] < self.config.CONDITIONS_REQUIRED else self.config.ALERT_COLOR
        cvzone.putTextRect(frame, f'Conditions: {details["conditions_met"]}/5', 
                         [x, y + offset], thickness=1, scale=0.7, colorR=color)
        offset += 20
        
        # Hip position
        cvzone.putTextRect(frame, f'Hip Y: {details["hip_center_y"]:.2f}', 
                         [x, y + offset], thickness=1, scale=0.7, colorR=self.config.INFO_COLOR)
    
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
        overall_frames_confirmed = self.fall_detection_frames >= self.fall_threshold_frames
        
        # Method 3: Buffer analysis - check for consistent detection in recent frames
        recent_detections = self.confirmation_buffer[-8:] if len(self.confirmation_buffer) >= 8 else self.confirmation_buffer
        buffer_consistency = sum(recent_detections) >= len(recent_detections) * 0.75 if recent_detections else False
        
        # COMBINED CONFIRMATION LOGIC
        was_confirmed = self.fall_detected
        
        # Confirm fall if consecutive lying frames OR (overall frames AND consistency)
        self.fall_detected = (
            consecutive_lying_confirmed or 
            (overall_frames_confirmed and buffer_consistency)
        )
        
        # Alert on new fall confirmation
        if self.fall_detected and not was_confirmed:
            self.fall_start_time = time.time()
            print("🚨 FALL ALERT: Fall confirmed with patience system!")
            print(f"   Consecutive lying frames: {self.lying_posture_frames}/{self.min_lying_frames}")
            print(f"   Total detection frames: {self.fall_detection_frames}/{self.fall_threshold_frames}")
            print(f"   Buffer consistency: {sum(recent_detections)}/{len(recent_detections)} frames")
        
        # ENHANCED RESET LOGIC: Clear state when person is clearly upright
        clear_upright_frames = self.config.UPRIGHT_CLEAR_FRAMES  # From config
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
        if self.fall_detection_frames > self.fall_threshold_frames + 5:
            self.fall_detection_frames = self.fall_threshold_frames + 5
                
    def draw_status(self, frame):
        """Draw system status and alerts"""
        if self.fall_detected:
            # Flash alert
            flash = int(time.time() * self.config.FLASH_FREQUENCY) % 2
            alert_color = self.config.FALL_COLOR if flash else self.config.ALERT_COLOR
            
            cvzone.putTextRect(frame, 'FALL ALERT!', [50, 50], 
                             thickness=3, scale=3, colorR=alert_color)
            
            if self.fall_start_time:
                duration = time.time() - self.fall_start_time
                cvzone.putTextRect(frame, f'Duration: {duration:.1f}s', [50, 120], 
                                 thickness=2, scale=2, colorR=alert_color)
        
        # System status
        status_color = self.config.NORMAL_COLOR if not self.fall_detected else self.config.FALL_COLOR
        status_text = "MONITORING" if not self.fall_detected else "ALERT"
        cvzone.putTextRect(frame, f'Status: {status_text}', [frame.shape[1] - 250, 50], 
                         thickness=2, scale=1.5, colorR=status_color)
        
        # System info
        cvzone.putTextRect(frame, 'MediaPipe Fall Detection', [20, frame.shape[0] - 30], 
                         thickness=1, scale=1.2, colorR=self.config.INFO_COLOR)
    
    def run(self):
        """Main detection loop"""
        print("MediaPipe Fall Detection System Started")
        print("Press 'q' to quit, 'r' to reset fall detection")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("End of video or camera disconnected")
                break
                
            # Resize frame
            frame = cv2.resize(frame, (self.config.FRAME_WIDTH, self.config.FRAME_HEIGHT))
            
            # Process frame
            frame, current_fall_detected = self.process_frame(frame)
            
            # Update fall state
            self.update_fall_state(current_fall_detected)
            
            # Draw status
            self.draw_status(frame)
            
            # Display frame
            cv2.imshow('MediaPipe Fall Detection System', frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.fall_detected = False
                self.fall_detection_frames = 0
                self.fall_start_time = None
                print("Fall detection reset")
                
        self.cleanup()
        
    def cleanup(self):
        """Clean up resources"""
        self.cap.release()
        cv2.destroyAllWindows()
        self.pose.close()
        print("MediaPipe Fall Detection System Stopped")

if __name__ == "__main__":
    # Create and run MediaPipe fall detection system
    detector = MediaPipeFallDetectionSystem()
    detector.run()