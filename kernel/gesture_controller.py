#!/usr/bin/env python3
"""
PortAIOS Gesture Controller
Real-time hand, face, and eye tracking for multimodal interaction
Uses MediaPipe for computer vision and gesture recognition
"""

import logging
import cv2
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import threading
from collections import deque

logger = logging.getLogger("AIOS.GestureController")

# Try to import MediaPipe
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("MediaPipe not installed. Install with: pip install mediapipe")

# Try to import Eel for web integration
try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logger.warning("Eel not available - gesture controller will run in limited mode")


class GestureType(Enum):
    """Supported gesture types"""
    # Hand gestures
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PEACE_SIGN = "peace_sign"
    OK_SIGN = "ok_sign"
    POINTING = "pointing"
    FIST = "fist"
    OPEN_PALM = "open_palm"
    PINCH = "pinch"
    GRAB = "grab"
    
    # Dynamic gestures
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    WAVE = "wave"
    CIRCLE_CW = "circle_clockwise"
    CIRCLE_CCW = "circle_counterclockwise"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    
    # Face gestures
    SMILE = "smile"
    FROWN = "frown"
    EYEBROW_RAISE = "eyebrow_raise"
    HEAD_NOD = "head_nod"
    HEAD_SHAKE = "head_shake"
    HEAD_TILT_LEFT = "head_tilt_left"
    HEAD_TILT_RIGHT = "head_tilt_right"
    
    # Eye gestures
    LOOK_LEFT = "look_left"
    LOOK_RIGHT = "look_right"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"
    BLINK = "blink"
    DOUBLE_BLINK = "double_blink"
    WINK_LEFT = "wink_left"
    WINK_RIGHT = "wink_right"
    
    # Mouth gestures
    MOUTH_OPEN = "mouth_open"
    KISS = "kiss"
    
    # Special
    NONE = "none"
    UNKNOWN = "unknown"


@dataclass
class GestureEvent:
    """Represents a detected gesture"""
    gesture_type: GestureType
    confidence: float
    timestamp: float
    hand: Optional[str] = None  # "left" or "right"
    position: Optional[Tuple[float, float]] = None  # (x, y) normalized coordinates
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandLandmarks:
    """Hand tracking data"""
    landmarks: List[Tuple[float, float, float]]  # (x, y, z) for each of 21 points
    handedness: str  # "left" or "right"
    confidence: float
    bounding_box: Tuple[float, float, float, float]  # (x, y, width, height)


@dataclass
class FaceLandmarks:
    """Face tracking data"""
    landmarks: List[Tuple[float, float, float]]  # Face mesh points
    head_rotation: Tuple[float, float, float]  # (pitch, yaw, roll)
    eye_left: Tuple[float, float]  # Normalized gaze direction
    eye_right: Tuple[float, float]
    mouth_openness: float
    confidence: float


class GestureRecognizer:
    """
    Recognizes gestures from hand and face landmarks
    Uses geometric analysis and pattern matching
    """
    
    def __init__(self):
        self.gesture_history = deque(maxlen=30)  # Last 30 frames (~1 second at 30fps)
        
    def recognize_hand_gesture(self, hand: HandLandmarks) -> GestureEvent:
        """Recognize static hand gesture from landmarks"""
        landmarks = hand.landmarks
        
        # Calculate finger states (extended or bent)
        fingers_extended = self._get_fingers_extended(landmarks, hand.handedness)
        
        # Pattern matching for static gestures
        gesture_type = GestureType.NONE
        confidence = 0.0
        
        # Thumbs up: thumb extended, others bent
        if fingers_extended[0] and not any(fingers_extended[1:]):
            if self._is_thumb_up_orientation(landmarks):
                gesture_type = GestureType.THUMBS_UP
                confidence = 0.9
        
        # Thumbs down
        elif fingers_extended[0] and not any(fingers_extended[1:]):
            if self._is_thumb_down_orientation(landmarks):
                gesture_type = GestureType.THUMBS_DOWN
                confidence = 0.9
        
        # Peace sign: index and middle extended
        elif fingers_extended[1] and fingers_extended[2] and not any([fingers_extended[0], fingers_extended[3], fingers_extended[4]]):
            gesture_type = GestureType.PEACE_SIGN
            confidence = 0.95
        
        # OK sign: thumb and index forming circle
        elif self._is_ok_sign(landmarks):
            gesture_type = GestureType.OK_SIGN
            confidence = 0.85
        
        # Pointing: only index extended
        elif fingers_extended[1] and not any([fingers_extended[0], fingers_extended[2], fingers_extended[3], fingers_extended[4]]):
            gesture_type = GestureType.POINTING
            confidence = 0.9
        
        # Fist: all fingers bent
        elif not any(fingers_extended):
            gesture_type = GestureType.FIST
            confidence = 0.95
        
        # Open palm: all fingers extended
        elif all(fingers_extended[1:]):  # Thumb doesn't need to be extended
            gesture_type = GestureType.OPEN_PALM
            confidence = 0.9
        
        # Pinch: thumb and index close together
        elif self._is_pinching(landmarks):
            gesture_type = GestureType.PINCH
            confidence = 0.85
        
        # Get hand center position
        center_x = np.mean([lm[0] for lm in landmarks])
        center_y = np.mean([lm[1] for lm in landmarks])
        
        return GestureEvent(
            gesture_type=gesture_type,
            confidence=confidence,
            timestamp=time.time(),
            hand=hand.handedness,
            position=(center_x, center_y),
            metadata={"fingers_extended": fingers_extended}
        )
    
    def recognize_dynamic_gesture(self, gesture_history: List[GestureEvent]) -> Optional[GestureEvent]:
        """Recognize dynamic gestures from movement patterns"""
        if len(gesture_history) < 10:
            return None
        
        # Extract positions over time
        positions = [g.position for g in gesture_history if g.position]
        if len(positions) < 10:
            return None
        
        # Calculate movement vector
        start_pos = positions[0]
        end_pos = positions[-1]
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = np.sqrt(dx**2 + dy**2)
        
        # Minimum movement threshold
        if distance < 0.15:
            return None
        
        # Determine direction
        angle = np.arctan2(dy, dx) * 180 / np.pi
        
        gesture_type = GestureType.NONE
        confidence = 0.0
        
        # Swipe gestures (horizontal/vertical movement)
        if abs(dx) > abs(dy) * 2:  # Horizontal
            if dx > 0:
                gesture_type = GestureType.SWIPE_RIGHT
                confidence = 0.8
            else:
                gesture_type = GestureType.SWIPE_LEFT
                confidence = 0.8
        elif abs(dy) > abs(dx) * 2:  # Vertical
            if dy > 0:
                gesture_type = GestureType.SWIPE_DOWN
                confidence = 0.8
            else:
                gesture_type = GestureType.SWIPE_UP
                confidence = 0.8
        
        # Wave detection (oscillating x-position)
        if self._is_waving(positions):
            gesture_type = GestureType.WAVE
            confidence = 0.85
        
        # Circle detection
        circle_result = self._detect_circle(positions)
        if circle_result:
            gesture_type, confidence = circle_result
        
        # Zoom gestures (two-hand pinch, handled separately)
        
        if gesture_type != GestureType.NONE:
            return GestureEvent(
                gesture_type=gesture_type,
                confidence=confidence,
                timestamp=time.time(),
                position=end_pos,
                metadata={"distance": distance, "angle": angle}
            )
        
        return None
    
    def recognize_face_gesture(self, face: FaceLandmarks) -> List[GestureEvent]:
        """Recognize facial expressions and head movements"""
        gestures = []
        
        # Head nod (pitch movement)
        pitch, yaw, roll = face.head_rotation
        if abs(pitch) > 15:
            if pitch > 0:
                gestures.append(GestureEvent(
                    gesture_type=GestureType.HEAD_NOD,
                    confidence=min(abs(pitch) / 30, 1.0),
                    timestamp=time.time()
                ))
        
        # Head shake (yaw movement)
        if abs(yaw) > 20:
            gestures.append(GestureEvent(
                gesture_type=GestureType.HEAD_SHAKE,
                confidence=min(abs(yaw) / 40, 1.0),
                timestamp=time.time()
            ))
        
        # Head tilt
        if abs(roll) > 15:
            if roll > 0:
                gesture_type = GestureType.HEAD_TILT_RIGHT
            else:
                gesture_type = GestureType.HEAD_TILT_LEFT
            gestures.append(GestureEvent(
                gesture_type=gesture_type,
                confidence=min(abs(roll) / 30, 1.0),
                timestamp=time.time()
            ))
        
        # Mouth gestures
        if face.mouth_openness > 0.3:
            gestures.append(GestureEvent(
                gesture_type=GestureType.MOUTH_OPEN,
                confidence=min(face.mouth_openness, 1.0),
                timestamp=time.time()
            ))
        
        # Eye gaze
        eye_left_x, eye_left_y = face.eye_left
        eye_right_x, eye_right_y = face.eye_right
        avg_eye_x = (eye_left_x + eye_right_x) / 2
        avg_eye_y = (eye_left_y + eye_right_y) / 2
        
        if abs(avg_eye_x) > 0.3:
            gesture_type = GestureType.LOOK_RIGHT if avg_eye_x > 0 else GestureType.LOOK_LEFT
            gestures.append(GestureEvent(
                gesture_type=gesture_type,
                confidence=min(abs(avg_eye_x) / 0.5, 1.0),
                timestamp=time.time()
            ))
        
        if abs(avg_eye_y) > 0.3:
            gesture_type = GestureType.LOOK_DOWN if avg_eye_y > 0 else GestureType.LOOK_UP
            gestures.append(GestureEvent(
                gesture_type=gesture_type,
                confidence=min(abs(avg_eye_y) / 0.5, 1.0),
                timestamp=time.time()
            ))
        
        return gestures
    
    # Helper methods
    def _get_fingers_extended(self, landmarks: List[Tuple[float, float, float]], handedness: str) -> List[bool]:
        """Determine which fingers are extended [thumb, index, middle, ring, pinky]"""
        # Finger tip and pip (proximal interphalangeal) joint indices
        finger_tips = [4, 8, 12, 16, 20]
        finger_pips = [2, 6, 10, 14, 18]
        
        extended = []
        
        # Thumb (different logic due to sideways orientation)
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]
        
        if handedness == "right":
            thumb_extended = thumb_tip[0] < thumb_ip[0] < thumb_mcp[0]
        else:
            thumb_extended = thumb_tip[0] > thumb_ip[0] > thumb_mcp[0]
        extended.append(thumb_extended)
        
        # Other fingers (compare tip y-coordinate with pip)
        for tip_idx, pip_idx in zip(finger_tips[1:], finger_pips[1:]):
            tip_y = landmarks[tip_idx][1]
            pip_y = landmarks[pip_idx][1]
            extended.append(tip_y < pip_y)  # Lower y = extended (in image coordinates)
        
        return extended
    
    def _is_thumb_up_orientation(self, landmarks: List[Tuple[float, float, float]]) -> bool:
        """Check if thumb is pointing upward"""
        thumb_tip = landmarks[4]
        wrist = landmarks[0]
        return thumb_tip[1] < wrist[1] - 0.1
    
    def _is_thumb_down_orientation(self, landmarks: List[Tuple[float, float, float]]) -> bool:
        """Check if thumb is pointing downward"""
        thumb_tip = landmarks[4]
        wrist = landmarks[0]
        return thumb_tip[1] > wrist[1] + 0.1
    
    def _is_ok_sign(self, landmarks: List[Tuple[float, float, float]]) -> bool:
        """Check if thumb and index form a circle"""
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        distance = np.sqrt((thumb_tip[0] - index_tip[0])**2 + (thumb_tip[1] - index_tip[1])**2)
        return distance < 0.05
    
    def _is_pinching(self, landmarks: List[Tuple[float, float, float]]) -> bool:
        """Check if thumb and index are pinching"""
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        distance = np.sqrt((thumb_tip[0] - index_tip[0])**2 + (thumb_tip[1] - index_tip[1])**2)
        return distance < 0.08
    
    def _is_waving(self, positions: List[Tuple[float, float]]) -> bool:
        """Detect wave pattern (oscillating x-position)"""
        if len(positions) < 15:
            return False
        
        x_positions = [p[0] for p in positions[-15:]]
        # Look for at least 2 direction changes
        direction_changes = 0
        for i in range(1, len(x_positions) - 1):
            if (x_positions[i] - x_positions[i-1]) * (x_positions[i+1] - x_positions[i]) < 0:
                direction_changes += 1
        
        return direction_changes >= 2
    
    def _detect_circle(self, positions: List[Tuple[float, float]]) -> Optional[Tuple[GestureType, float]]:
        """Detect circular motion"""
        if len(positions) < 20:
            return None
        
        # Use last 20 positions
        recent = positions[-20:]
        
        # Calculate center
        center_x = np.mean([p[0] for p in recent])
        center_y = np.mean([p[1] for p in recent])
        
        # Calculate angles from center
        angles = []
        for x, y in recent:
            angle = np.arctan2(y - center_y, x - center_x)
            angles.append(angle)
        
        # Check if angles increase monotonically (after unwrapping)
        angles_unwrapped = np.unwrap(angles)
        total_rotation = angles_unwrapped[-1] - angles_unwrapped[0]
        
        if abs(total_rotation) > np.pi * 1.5:  # More than 270 degrees
            if total_rotation > 0:
                return (GestureType.CIRCLE_CCW, 0.85)
            else:
                return (GestureType.CIRCLE_CW, 0.85)
        
        return None


class GestureController:
    """
    Main gesture control system
    Manages camera, tracking, and gesture recognition
    """
    
    def __init__(self):
        self.enabled = False
        self.camera_active = False
        self.camera_index = 0
        self.capture = None
        self.processing_thread = None
        self.running = False
        
        # MediaPipe components
        self.mp_hands = None
        self.mp_face_mesh = None
        self.mp_face_detection = None
        self.hands_detector = None
        self.face_mesh_detector = None
        
        # Gesture recognition
        self.recognizer = GestureRecognizer()
        
        # Command callbacks
        self.gesture_callbacks: Dict[GestureType, List[Callable]] = {}
        
        # State tracking
        self.current_gestures: List[GestureEvent] = []
        self.gesture_history = deque(maxlen=30)
        
        # Performance metrics
        self.fps = 0
        self.frame_count = 0
        self.last_fps_update = time.time()
        
        # Initialize MediaPipe if available
        if MEDIAPIPE_AVAILABLE:
            self._init_mediapipe()
        else:
            logger.error("MediaPipe not available - gesture control disabled")
    
    def _init_mediapipe(self):
        """Initialize MediaPipe models"""
        try:
            self.mp_hands = mp.solutions.hands
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_face_detection = mp.solutions.face_detection
            
            # Initialize hands detector
            self.hands_detector = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            
            # Initialize face mesh detector
            self.face_mesh_detector = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            logger.info("MediaPipe initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe: {e}")
            raise
    
    def start_camera(self, camera_index: int = 0) -> Dict[str, Any]:
        """Start camera capture"""
        if not MEDIAPIPE_AVAILABLE:
            return {"success": False, "error": "MediaPipe not available"}
        
        try:
            self.camera_index = camera_index
            self.capture = cv2.VideoCapture(camera_index)
            
            if not self.capture.isOpened():
                return {"success": False, "error": "Failed to open camera"}
            
            # Set camera properties
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_FPS, 30)
            
            self.camera_active = True
            self.enabled = True
            
            # Start processing thread
            self.running = True
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
            
            logger.info(f"Camera started on device {camera_index}")
            return {
                "success": True,
                "camera_index": camera_index,
                "resolution": (640, 480)
            }
        
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_camera(self) -> Dict[str, Any]:
        """Stop camera capture"""
        try:
            self.running = False
            self.enabled = False
            
            if self.processing_thread:
                self.processing_thread.join(timeout=2.0)
            
            if self.capture:
                self.capture.release()
                self.capture = None
            
            self.camera_active = False
            logger.info("Camera stopped")
            
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Failed to stop camera: {e}")
            return {"success": False, "error": str(e)}
    
    def _processing_loop(self):
        """Main processing loop (runs in separate thread)"""
        logger.info("Gesture processing loop started")
        
        while self.running and self.capture:
            try:
                ret, frame = self.capture.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    continue
                
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process frame
                gestures = self._process_frame(rgb_frame)
                
                # Update state
                self.current_gestures = gestures
                
                # Trigger callbacks
                for gesture in gestures:
                    self._trigger_callbacks(gesture)
                
                # Update FPS
                self.frame_count += 1
                now = time.time()
                if now - self.last_fps_update >= 1.0:
                    self.fps = self.frame_count
                    self.frame_count = 0
                    self.last_fps_update = now
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(0.1)
        
        logger.info("Gesture processing loop stopped")
    
    def _process_frame(self, frame: np.ndarray) -> List[GestureEvent]:
        """Process a single frame and detect gestures"""
        gestures = []
        
        # Detect hands
        hands_results = self.hands_detector.process(frame)
        if hands_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                hands_results.multi_hand_landmarks,
                hands_results.multi_handedness
            ):
                hand_data = self._extract_hand_data(hand_landmarks, handedness)
                gesture = self.recognizer.recognize_hand_gesture(hand_data)
                
                if gesture.gesture_type != GestureType.NONE:
                    gestures.append(gesture)
                    self.gesture_history.append(gesture)
        
        # Check for dynamic gestures
        dynamic_gesture = self.recognizer.recognize_dynamic_gesture(list(self.gesture_history))
        if dynamic_gesture:
            gestures.append(dynamic_gesture)
        
        # Detect face
        face_results = self.face_mesh_detector.process(frame)
        if face_results.multi_face_landmarks:
            for face_landmarks in face_results.multi_face_landmarks:
                face_data = self._extract_face_data(face_landmarks, frame.shape)
                face_gestures = self.recognizer.recognize_face_gesture(face_data)
                gestures.extend(face_gestures)
        
        return gestures
    
    def _extract_hand_data(self, landmarks, handedness) -> HandLandmarks:
        """Extract hand landmark data"""
        hand_label = handedness.classification[0].label.lower()
        confidence = handedness.classification[0].score
        
        # Extract landmarks
        lm_list = []
        x_coords = []
        y_coords = []
        
        for lm in landmarks.landmark:
            lm_list.append((lm.x, lm.y, lm.z))
            x_coords.append(lm.x)
            y_coords.append(lm.y)
        
        # Calculate bounding box
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        
        return HandLandmarks(
            landmarks=lm_list,
            handedness=hand_label,
            confidence=confidence,
            bounding_box=bbox
        )
    
    def _extract_face_data(self, landmarks, frame_shape) -> FaceLandmarks:
        """Extract face landmark data"""
        h, w = frame_shape[:2]
        
        # Extract landmarks
        lm_list = []
        for lm in landmarks.landmark:
            lm_list.append((lm.x, lm.y, lm.z))
        
        # Estimate head rotation (simplified)
        # Using specific landmarks for nose, chin, and forehead
        nose_tip = lm_list[1]
        chin = lm_list[152]
        forehead = lm_list[10]
        
        # Calculate pitch (up/down)
        pitch = (nose_tip[1] - forehead[1]) * 90
        
        # Calculate yaw (left/right) - simplified
        yaw = (nose_tip[0] - 0.5) * 90
        
        # Calculate roll (tilt) - simplified
        roll = 0.0  # Would need more sophisticated calculation
        
        # Eye gaze estimation (simplified)
        left_eye = lm_list[33]
        right_eye = lm_list[263]
        eye_left_gaze = ((left_eye[0] - 0.3) * 2, (left_eye[1] - 0.4) * 2)
        eye_right_gaze = ((right_eye[0] - 0.7) * 2, (right_eye[1] - 0.4) * 2)
        
        # Mouth openness
        upper_lip = lm_list[13]
        lower_lip = lm_list[14]
        mouth_openness = abs(upper_lip[1] - lower_lip[1]) * 10
        
        return FaceLandmarks(
            landmarks=lm_list,
            head_rotation=(pitch, yaw, roll),
            eye_left=eye_left_gaze,
            eye_right=eye_right_gaze,
            mouth_openness=mouth_openness,
            confidence=0.8
        )
    
    def register_gesture_callback(self, gesture_type: GestureType, callback: Callable):
        """Register a callback for a specific gesture"""
        if gesture_type not in self.gesture_callbacks:
            self.gesture_callbacks[gesture_type] = []
        self.gesture_callbacks[gesture_type].append(callback)
        logger.info(f"Registered callback for gesture: {gesture_type.value}")
    
    def _trigger_callbacks(self, gesture: GestureEvent):
        """Trigger callbacks for a detected gesture"""
        if gesture.gesture_type in self.gesture_callbacks:
            for callback in self.gesture_callbacks[gesture.gesture_type]:
                try:
                    callback(gesture)
                except Exception as e:
                    logger.error(f"Error in gesture callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            "enabled": self.enabled,
            "camera_active": self.camera_active,
            "camera_index": self.camera_index,
            "fps": self.fps,
            "mediapipe_available": MEDIAPIPE_AVAILABLE,
            "current_gestures": [
                {
                    "type": g.gesture_type.value,
                    "confidence": g.confidence,
                    "hand": g.hand,
                    "position": g.position
                }
                for g in self.current_gestures
            ]
        }


# Global instance
_gesture_controller = None


def get_gesture_controller() -> GestureController:
    """Get or create global gesture controller instance"""
    global _gesture_controller
    if _gesture_controller is None:
        _gesture_controller = GestureController()
    return _gesture_controller


# Eel integration
if EEL_AVAILABLE:
    def setup_gesture_eel_api():
        """Setup Eel-exposed functions for gesture control"""
        controller = get_gesture_controller()
        
        @eel.expose
        def start_gesture_camera(camera_index: int = 0) -> Dict[str, Any]:
            """Start gesture camera"""
            return controller.start_camera(camera_index)
        
        @eel.expose
        def stop_gesture_camera() -> Dict[str, Any]:
            """Stop gesture camera"""
            return controller.stop_camera()
        
        @eel.expose
        def get_gesture_status() -> Dict[str, Any]:
            """Get gesture controller status"""
            return controller.get_status()
        
        @eel.expose
        def get_available_gestures() -> List[str]:
            """Get list of available gesture types"""
            return [g.value for g in GestureType if g not in [GestureType.NONE, GestureType.UNKNOWN]]
        
        logger.info("Gesture controller Eel API initialized")
        return controller


__all__ = [
    'GestureController',
    'GestureType',
    'GestureEvent',
    'GestureRecognizer',
    'get_gesture_controller',
    'setup_gesture_eel_api'
]
