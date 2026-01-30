"""
Water gulp detection using MediaPipe Hands, Face Detection, and Object Detection
Updated for MediaPipe 0.10+ with new Tasks API

Smart detection to avoid false positives from:
- Touching beard
- Biting nails
- Scratching face

Now includes cup/bottle detection to require a drinking vessel for detection.
"""

import cv2
import time
import os
import sys
import urllib.request
from collections import deque
from config import CONFIG

# MediaPipe imports for new API
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class WaterGulpDetector:
    """
    Detects water drinking gestures using webcam and MediaPipe.

    Smart detection logic:
    1. Hand must be in "holding" pose (fingers curled, not pointing)
    2. Hand must move UPWARD toward mouth (drinking motion)
    3. Wrist must be below fingertips (tilted like drinking)
    4. Hand must stay near mouth for several frames
    5. Cooldown between detections
    """

    # Model URLs
    HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
    OBJECT_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite"

    # Object classes we care about (COCO dataset class names)
    DRINKING_VESSEL_CLASSES = {"cup", "bottle", "wine glass"}

    def __init__(self, camera_index: int = None):
        self.camera_index = camera_index if camera_index is not None else CONFIG["camera_index"]
        self.cap = None
        self.running = False

        # Detection state
        self.consecutive_frames = 0
        self.last_gulp_time = 0

        # Away detection
        self.last_face_seen_time = time.time()
        self.is_away = False
        self.away_timeout = CONFIG.get("away_timeout_seconds", 5)

        # Hand position history for motion tracking
        self.hand_history = deque(maxlen=10)  # Last 10 positions

        # Parameters
        self.frames_to_confirm = CONFIG.get("frames_to_confirm", 4)
        self.cooldown_seconds = CONFIG.get("cooldown_seconds", 10)
        self.proximity_threshold = CONFIG.get("proximity_threshold", 0.12)
        self.drinking_hand = CONFIG.get("drinking_hand", "both").lower()  # "right", "left", or "both"
        self.require_cup = CONFIG.get("require_cup", True)  # Require cup/bottle detection

        # Detection sensitivity
        sensitivity = CONFIG.get("detection_sensitivity", "medium").lower()
        if sensitivity == "easy":
            self.criteria_required = 2  # 2 de 4 critérios (mais fácil)
        elif sensitivity == "strict":
            self.criteria_required = 4  # 4 de 4 critérios (muito difícil)
        else:  # medium
            self.criteria_required = 3  # 3 de 4 critérios (padrão)

        # Cup detection state
        self.last_cup_detection = None  # Stores last detected cup bounding box

        # Bottle cache - mantém garrafa "em memória" por alguns segundos
        # Resolve o problema da garrafa virada não ser detectada durante o gole
        self.bottle_cache_timeout = CONFIG.get("bottle_cache_seconds", 5)
        self.bottle_cache_time = 0  # Timestamp de quando a garrafa foi detectada
        self.bottle_cache_position = None  # Posição normalizada da garrafa {x, y, width, height}
        self.bottle_cache_class = None  # Tipo do objeto (bottle, cup, etc)

        # Models directory - check bundled path first, then local
        bundled_models = get_resource_path("models")
        local_models = "models"

        if os.path.exists(bundled_models) and getattr(sys, 'frozen', False):
            self.models_dir = bundled_models
        else:
            self.models_dir = local_models
            os.makedirs(self.models_dir, exist_ok=True)

        # Download models if needed
        self._ensure_models()

        # Initialize MediaPipe
        self._init_mediapipe()

    def _ensure_models(self):
        """Download model files if they don't exist"""
        self.hand_model_path = os.path.join(self.models_dir, "hand_landmarker.task")
        self.face_model_path = os.path.join(self.models_dir, "blaze_face_short_range.tflite")
        self.object_model_path = os.path.join(self.models_dir, "efficientdet_lite0.tflite")

        if not os.path.exists(self.hand_model_path):
            print("Downloading hand landmarker model...")
            urllib.request.urlretrieve(self.HAND_MODEL_URL, self.hand_model_path)
            print("Hand model downloaded.")

        if not os.path.exists(self.face_model_path):
            print("Downloading face detector model...")
            urllib.request.urlretrieve(self.FACE_MODEL_URL, self.face_model_path)
            print("Face model downloaded.")

        if not os.path.exists(self.object_model_path):
            print("Downloading object detector model...")
            urllib.request.urlretrieve(self.OBJECT_MODEL_URL, self.object_model_path)
            print("Object model downloaded.")

    def _init_mediapipe(self):
        """Initialize MediaPipe hand, face, and object detection"""
        # Hand Landmarker
        hand_options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=self.hand_model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)

        # Face Detector
        face_options = vision.FaceDetectorOptions(
            base_options=python.BaseOptions(model_asset_path=self.face_model_path),
            running_mode=vision.RunningMode.IMAGE,
            min_detection_confidence=0.7
        )
        self.face_detector = vision.FaceDetector.create_from_options(face_options)

        # Object Detector (for cups, bottles, glasses)
        object_options = vision.ObjectDetectorOptions(
            base_options=python.BaseOptions(model_asset_path=self.object_model_path),
            running_mode=vision.RunningMode.IMAGE,
            max_results=5,
            score_threshold=0.25  # Threshold baixo para pegar garrafas com menos certeza
        )
        self.object_detector = vision.ObjectDetector.create_from_options(object_options)

    def start_camera(self) -> bool:
        """Initialize camera capture"""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False

        # Set lower resolution for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.running = True
        return True

    def stop_camera(self):
        """Release camera resources"""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def _get_wrist_position(self, hand_landmarks) -> tuple:
        """Get wrist position (landmark 0)"""
        wrist = hand_landmarks[0]
        return (wrist.x, wrist.y)

    def _get_palm_center(self, hand_landmarks) -> tuple:
        """Get center of palm for tracking"""
        # Use wrist (0) and middle finger MCP (9) to find palm center
        wrist = hand_landmarks[0]
        middle_mcp = hand_landmarks[9]
        return ((wrist.x + middle_mcp.x) / 2, (wrist.y + middle_mcp.y) / 2)

    def _get_fingertips_center(self, hand_landmarks) -> tuple:
        """Get average position of fingertips"""
        tip_indices = [4, 8, 12, 16, 20]  # All fingertips
        x_sum = sum(hand_landmarks[i].x for i in tip_indices)
        y_sum = sum(hand_landmarks[i].y for i in tip_indices)
        return (x_sum / len(tip_indices), y_sum / len(tip_indices))

    def _is_holding_pose(self, hand_landmarks) -> bool:
        """
        Check if hand is in a "holding" pose (like holding a cup/bottle).

        Criteria:
        - Fingers should be somewhat curled (not fully extended)
        - Thumb should be separated from other fingers (gripping)
        """
        # Get key landmarks
        wrist = hand_landmarks[0]

        # Fingertip and MCP (knuckle) positions
        index_tip = hand_landmarks[8]
        index_mcp = hand_landmarks[5]
        middle_tip = hand_landmarks[12]
        middle_mcp = hand_landmarks[9]
        ring_tip = hand_landmarks[16]
        ring_mcp = hand_landmarks[13]
        pinky_tip = hand_landmarks[20]
        pinky_mcp = hand_landmarks[17]

        # Check if fingers are curled (tip closer to wrist than MCP in y)
        # When fingers are extended, tips are far from wrist
        # When curled (holding), tips are closer to palm

        def finger_curl_ratio(tip, mcp, wrist):
            """Calculate how curled a finger is. Higher = more curled"""
            tip_to_wrist = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)**0.5
            mcp_to_wrist = ((mcp.x - wrist.x)**2 + (mcp.y - wrist.y)**2)**0.5
            if mcp_to_wrist == 0:
                return 0
            return mcp_to_wrist / (tip_to_wrist + 0.001)

        # Calculate curl for each finger
        index_curl = finger_curl_ratio(index_tip, index_mcp, wrist)
        middle_curl = finger_curl_ratio(middle_tip, middle_mcp, wrist)
        ring_curl = finger_curl_ratio(ring_tip, ring_mcp, wrist)
        pinky_curl = finger_curl_ratio(pinky_tip, pinky_mcp, wrist)

        avg_curl = (index_curl + middle_curl + ring_curl + pinky_curl) / 4

        # For nail biting: usually ONE finger is extended toward mouth
        # For holding cup: ALL fingers are somewhat curled together

        # Check finger spread (nail biting = one finger out, holding = fingers together)
        fingertip_xs = [index_tip.x, middle_tip.x, ring_tip.x, pinky_tip.x]
        finger_spread = max(fingertip_xs) - min(fingertip_xs)

        # Holding pose: moderate curl (0.6-1.5) and fingers not too spread
        is_holding = avg_curl > 0.5 and finger_spread < 0.15

        return is_holding

    def _is_drinking_orientation(self, hand_landmarks, mouth_y_normalized) -> bool:
        """
        Check if hand is oriented for drinking (tilted up).

        When drinking:
        - Wrist is typically BELOW the fingertips (hand tilted up)
        - Hand approaches from below the mouth
        """
        wrist = hand_landmarks[0]
        fingertips_y = self._get_fingertips_center(hand_landmarks)[1]

        # Wrist should be below fingertips (higher y value = lower on screen)
        # Allow some tolerance
        wrist_below_fingers = wrist.y > fingertips_y - 0.05

        # Hand should be coming from below mouth level (or at mouth level)
        palm_center = self._get_palm_center(hand_landmarks)
        hand_at_or_below_mouth = palm_center[1] >= mouth_y_normalized - 0.1

        return wrist_below_fingers and hand_at_or_below_mouth

    def _detect_upward_motion(self) -> bool:
        """
        Check if hand has been moving upward (toward mouth).

        Returns True if recent hand positions show upward movement.
        """
        if len(self.hand_history) < 4:
            return False

        # Compare recent positions - check if moving up (decreasing y)
        positions = list(self.hand_history)

        # Get y positions from oldest to newest
        y_positions = [p[1] for p in positions[-5:]]

        if len(y_positions) < 3:
            return False

        # Check if generally moving upward (y decreasing)
        upward_moves = 0
        for i in range(1, len(y_positions)):
            if y_positions[i] < y_positions[i-1]:
                upward_moves += 1

        # At least 50% of recent movement should be upward
        return upward_moves >= len(y_positions) // 2

    def _get_mouth_position(self, face_detection, frame_width, frame_height) -> tuple:
        """
        Get mouth position in normalized coordinates.
        """
        bbox = face_detection.bounding_box

        mouth_x = (bbox.origin_x + bbox.width / 2) / frame_width
        mouth_y = (bbox.origin_y + bbox.height * 0.75) / frame_height

        return (mouth_x, mouth_y)

    def _calculate_distance(self, pos1: tuple, pos2: tuple) -> float:
        """Calculate Euclidean distance between two normalized positions"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def _detect_drinking_vessels(self, object_results, frame_width, frame_height) -> list:
        """
        Find all drinking vessels (cups, bottles, glasses) in the frame.

        Returns list of dicts with normalized bounding boxes and class names.
        """
        vessels = []
        if not object_results.detections:
            return vessels

        for detection in object_results.detections:
            # Get category name
            category = detection.categories[0]
            class_name = category.category_name.lower()

            if class_name in self.DRINKING_VESSEL_CLASSES:
                bbox = detection.bounding_box
                # Normalize coordinates
                vessels.append({
                    "class": class_name,
                    "confidence": category.score,
                    "bbox": {
                        "x": bbox.origin_x / frame_width,
                        "y": bbox.origin_y / frame_height,
                        "width": bbox.width / frame_width,
                        "height": bbox.height / frame_height
                    },
                    "bbox_pixels": {
                        "x": bbox.origin_x,
                        "y": bbox.origin_y,
                        "width": bbox.width,
                        "height": bbox.height
                    }
                })

        return vessels

    def _is_hand_holding_cup(self, hand_landmarks, vessels, frame_width, frame_height) -> dict:
        """
        Check if the hand is holding/overlapping with any detected cup.

        Returns the cup info if hand is holding one, None otherwise.
        """
        if not vessels:
            return None

        # Get hand bounding box from landmarks
        xs = [lm.x for lm in hand_landmarks]
        ys = [lm.y for lm in hand_landmarks]
        hand_min_x, hand_max_x = min(xs), max(xs)
        hand_min_y, hand_max_y = min(ys), max(ys)

        # Add some margin to hand bbox
        margin = 0.05
        hand_min_x = max(0, hand_min_x - margin)
        hand_max_x = min(1, hand_max_x + margin)
        hand_min_y = max(0, hand_min_y - margin)
        hand_max_y = min(1, hand_max_y + margin)

        for vessel in vessels:
            bbox = vessel["bbox"]
            cup_min_x = bbox["x"]
            cup_max_x = bbox["x"] + bbox["width"]
            cup_min_y = bbox["y"]
            cup_max_y = bbox["y"] + bbox["height"]

            # Check for overlap between hand and cup bounding boxes
            overlap_x = max(0, min(hand_max_x, cup_max_x) - max(hand_min_x, cup_min_x))
            overlap_y = max(0, min(hand_max_y, cup_max_y) - max(hand_min_y, cup_min_y))

            if overlap_x > 0 and overlap_y > 0:
                # There's overlap - hand is touching/holding the cup
                return vessel

        return None

    def _update_bottle_cache(self, vessel: dict):
        """
        Salva a garrafa no cache quando detectada.
        Isso permite que o gole seja detectado mesmo quando a garrafa
        está virada (e não é mais reconhecida visualmente).
        """
        self.bottle_cache_time = time.time()
        self.bottle_cache_position = vessel["bbox"].copy()
        self.bottle_cache_class = vessel["class"]

    def _is_bottle_in_cache(self) -> bool:
        """Verifica se há uma garrafa válida no cache (dentro do timeout)."""
        if self.bottle_cache_time == 0:
            return False
        return (time.time() - self.bottle_cache_time) < self.bottle_cache_timeout

    def _is_hand_in_cached_bottle_region(self, hand_landmarks) -> bool:
        """
        Verifica se a mão está na região aproximada de onde a garrafa foi detectada.
        Usa uma margem generosa porque a mão se move durante o gole.
        """
        if not self._is_bottle_in_cache() or self.bottle_cache_position is None:
            return False

        # Pegar bounding box da mão
        xs = [lm.x for lm in hand_landmarks]
        ys = [lm.y for lm in hand_landmarks]
        hand_center_x = (min(xs) + max(xs)) / 2
        hand_center_y = (min(ys) + max(ys)) / 2

        # Posição da garrafa no cache
        bottle = self.bottle_cache_position
        bottle_center_x = bottle["x"] + bottle["width"] / 2
        bottle_center_y = bottle["y"] + bottle["height"] / 2

        # Margem generosa - a mão pode estar um pouco afastada da posição original
        # porque durante o gole ela se move pra cima
        margin = 0.25  # 25% da tela de margem

        distance_x = abs(hand_center_x - bottle_center_x)
        distance_y = abs(hand_center_y - bottle_center_y)

        # A mão pode estar acima (durante o gole) ou ao lado da posição original
        return distance_x < margin and distance_y < margin

    def _get_bottle_cache_info(self) -> dict:
        """Retorna info do cache para debug."""
        if not self._is_bottle_in_cache():
            return None
        remaining = self.bottle_cache_timeout - (time.time() - self.bottle_cache_time)
        return {
            "class": self.bottle_cache_class,
            "remaining_seconds": remaining,
            "position": self.bottle_cache_position
        }

    def process_frame(self) -> tuple:
        """
        Process a single frame and detect if drinking.

        Returns:
            tuple: (gulp_detected: bool, debug_info: dict)
        """
        if not self.cap or not self.running:
            return False, {"error": "Camera not running"}

        ret, frame = self.cap.read()
        if not ret:
            return False, {"error": "Failed to read frame"}

        frame_height, frame_width = frame.shape[:2]

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Process with MediaPipe
        hand_results = self.hand_detector.detect(mp_image)
        face_results = self.face_detector.detect(mp_image)
        object_results = self.object_detector.detect(mp_image)

        current_time = time.time()

        # Detect drinking vessels (cups, bottles, glasses)
        vessels = self._detect_drinking_vessels(object_results, frame_width, frame_height)

        # Info do cache de garrafa
        bottle_cache_info = self._get_bottle_cache_info()

        debug_info = {
            "hand_detected": False,
            "face_detected": False,
            "cup_detected": len(vessels) > 0,
            "cup_held": False,
            "vessels": vessels,
            "distance": None,
            "is_holding": False,
            "is_drinking_orientation": False,
            "upward_motion": False,
            "consecutive_frames": self.consecutive_frames,
            "cooldown_remaining": max(0, self.cooldown_seconds - (self.last_gulp_time and current_time - self.last_gulp_time or 0)),
            "is_away": self.is_away,
            "require_cup": self.require_cup,
            "bottle_cache_active": bottle_cache_info is not None,
            "bottle_cache_info": bottle_cache_info
        }

        # Check for face - update away status
        if face_results.detections:
            self.last_face_seen_time = current_time
            if self.is_away:
                self.is_away = False
                print("[STATUS] User returned - resuming detection")
        else:
            # No face detected
            if not self.is_away and (current_time - self.last_face_seen_time) > self.away_timeout:
                self.is_away = True
                print("[STATUS] User away - pausing detection")

        debug_info["is_away"] = self.is_away

        # If away, don't process hands
        if self.is_away:
            self.consecutive_frames = 0
            return False, debug_info

        # Check if both hand and face are detected
        if not hand_results.hand_landmarks:
            self.consecutive_frames = 0
            return False, debug_info

        if not face_results.detections:
            self.consecutive_frames = 0
            return False, debug_info

        debug_info["hand_detected"] = True
        debug_info["face_detected"] = True

        # Get mouth position (normalized)
        mouth_pos = self._get_mouth_position(face_results.detections[0], frame_width, frame_height)

        # Check each detected hand
        best_candidate = None
        min_distance = float('inf')

        for idx, hand_landmarks in enumerate(hand_results.hand_landmarks):
            # Check handedness if specified
            if self.drinking_hand != "both" and hand_results.handedness:
                handedness = hand_results.handedness[idx][0].category_name.lower()
                if handedness != self.drinking_hand:
                    continue  # Skip this hand
            # Get hand center for distance calculation
            palm_center = self._get_palm_center(hand_landmarks)
            distance = self._calculate_distance(palm_center, mouth_pos)

            # Check all criteria
            is_holding = self._is_holding_pose(hand_landmarks)
            is_drinking_orient = self._is_drinking_orientation(hand_landmarks, mouth_pos[1])

            # Check if hand is holding a cup
            held_cup = self._is_hand_holding_cup(hand_landmarks, vessels, frame_width, frame_height)

            # Se detectou garrafa sendo segurada, atualiza o cache
            if held_cup is not None:
                self._update_bottle_cache(held_cup)

            # Verifica se a mão está na região do cache (para quando a garrafa está virada)
            hand_in_cache_region = self._is_hand_in_cached_bottle_region(hand_landmarks)

            if distance < min_distance:
                min_distance = distance
                best_candidate = {
                    "landmarks": hand_landmarks,
                    "distance": distance,
                    "is_holding": is_holding,
                    "is_drinking_orientation": is_drinking_orient,
                    "palm_center": palm_center,
                    "held_cup": held_cup,
                    "hand_in_cache_region": hand_in_cache_region
                }

        if best_candidate is None:
            self.consecutive_frames = 0
            return False, debug_info

        # Update hand history for motion tracking
        self.hand_history.append(best_candidate["palm_center"])

        # Check for upward motion
        upward_motion = self._detect_upward_motion()

        debug_info["distance"] = best_candidate["distance"]
        debug_info["is_holding"] = best_candidate["is_holding"]
        debug_info["is_drinking_orientation"] = best_candidate["is_drinking_orientation"]
        debug_info["upward_motion"] = upward_motion
        debug_info["cup_held"] = best_candidate["held_cup"] is not None
        debug_info["held_cup_info"] = best_candidate["held_cup"]
        debug_info["hand_in_cache_region"] = best_candidate["hand_in_cache_region"]

        # DRINKING DETECTION CRITERIA:
        # 1. Hand is close to mouth
        # 2. Hand is in holding pose (not single finger extended)
        # 3. Hand is in drinking orientation (tilted up)
        # 4. Hand showed upward motion recently
        # 5. (Optional) Hand is holding a detected cup/bottle OR garrafa em cache

        is_close = min_distance < self.proximity_threshold
        is_holding = best_candidate["is_holding"]
        is_drinking = best_candidate["is_drinking_orientation"]

        # has_cup agora considera:
        # 1. Garrafa detectada em tempo real (held_cup)
        # 2. OU garrafa no cache + mão na região aproximada
        has_cup_realtime = best_candidate["held_cup"] is not None
        has_cup_from_cache = self._is_bottle_in_cache() and best_candidate["hand_in_cache_region"]
        has_cup = has_cup_realtime or has_cup_from_cache

        # If cup detection is required, hand must be holding a cup (real ou cache)
        if self.require_cup and not has_cup:
            # No cup detected (nem em tempo real nem no cache) - don't count as drinking
            self.consecutive_frames = max(0, self.consecutive_frames - 1)
            return False, debug_info

        # Check detection criteria based on sensitivity
        criteria_met = sum([is_close, is_holding, is_drinking, upward_motion])

        if criteria_met >= self.criteria_required and is_close:  # Must be close + outros critérios
            self.consecutive_frames += 1
            debug_info["consecutive_frames"] = self.consecutive_frames
            debug_info["criteria_required"] = self.criteria_required
            debug_info["criteria_met"] = criteria_met

            # Check if we have enough consecutive frames AND cooldown has passed
            if self.consecutive_frames >= self.frames_to_confirm:
                current_time = time.time()

                if current_time - self.last_gulp_time >= self.cooldown_seconds:
                    self.last_gulp_time = current_time
                    self.consecutive_frames = 0
                    self.hand_history.clear()
                    return True, debug_info
        else:
            # Reset if not meeting criteria
            if self.consecutive_frames > 0:
                self.consecutive_frames = max(0, self.consecutive_frames - 1)

        return False, debug_info

    def get_debug_frame(self) -> tuple:
        """
        Get current frame with debug visualization overlay.
        """
        if not self.cap or not self.running:
            return None, {"error": "Camera not running"}

        ret, frame = self.cap.read()
        if not ret:
            return None, {"error": "Failed to read frame"}

        frame_height, frame_width = frame.shape[:2]

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Process
        hand_results = self.hand_detector.detect(mp_image)
        face_results = self.face_detector.detect(mp_image)
        object_results = self.object_detector.detect(mp_image)

        # Detect drinking vessels
        vessels = self._detect_drinking_vessels(object_results, frame_width, frame_height)

        debug_info = {
            "hand_detected": False,
            "face_detected": False,
            "cup_detected": len(vessels) > 0,
            "vessels": vessels
        }

        # Draw face detection
        if face_results.detections:
            debug_info["face_detected"] = True
            for detection in face_results.detections:
                bbox = detection.bounding_box

                x = int(bbox.origin_x)
                y = int(bbox.origin_y)
                width = int(bbox.width)
                height = int(bbox.height)

                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)

                # Draw mouth position
                mouth_x = int(bbox.origin_x + bbox.width / 2)
                mouth_y = int(bbox.origin_y + bbox.height * 0.75)
                cv2.circle(frame, (mouth_x, mouth_y), 10, (0, 0, 255), -1)
                cv2.putText(frame, "MOUTH", (mouth_x + 15, mouth_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Draw detected cups/bottles/glasses
        for vessel in vessels:
            bbox = vessel["bbox_pixels"]
            x = int(bbox["x"])
            y = int(bbox["y"])
            w = int(bbox["width"])
            h = int(bbox["height"])

            # Cyan color for cups/bottles
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 3)

            # Label with class name and confidence
            label = f"{vessel['class'].upper()} {vessel['confidence']:.0%}"
            cv2.putText(frame, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Draw bottle cache region (se ativo e não há garrafa visível)
        cache_info = self._get_bottle_cache_info()
        if cache_info and not vessels:
            # Desenha a região do cache em amarelo tracejado
            pos = cache_info["position"]
            x = int(pos["x"] * frame_width)
            y = int(pos["y"] * frame_height)
            w = int(pos["width"] * frame_width)
            h = int(pos["height"] * frame_height)

            # Retângulo tracejado amarelo para indicar cache
            # (OpenCV não tem linha tracejada nativa, usamos cor diferente)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)  # Amarelo

            # Label indicando que é cache
            remaining = cache_info["remaining_seconds"]
            cache_label = f"CACHE: {cache_info['class'].upper()} ({remaining:.1f}s)"
            cv2.putText(frame, cache_label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Draw hand landmarks
        if hand_results.hand_landmarks:
            debug_info["hand_detected"] = True

            for idx, hand_landmarks in enumerate(hand_results.hand_landmarks):
                # Get handedness
                handedness = "unknown"
                is_drinking_hand = True
                if hand_results.handedness:
                    handedness = hand_results.handedness[idx][0].category_name.lower()
                    if self.drinking_hand != "both":
                        is_drinking_hand = (handedness == self.drinking_hand)

                # Check pose
                is_holding = self._is_holding_pose(hand_landmarks)

                # Check if holding a cup
                held_cup = self._is_hand_holding_cup(hand_landmarks, vessels, frame_width, frame_height)
                has_cup = held_cup is not None

                # Color: Cyan if holding cup, Green if holding pose, Orange if not holding, Gray if wrong hand
                if not is_drinking_hand:
                    color = (128, 128, 128)  # Gray for wrong hand
                elif has_cup:
                    color = (255, 255, 0)  # Cyan if holding a cup
                elif is_holding:
                    color = (0, 255, 0)  # Green if holding pose
                else:
                    color = (0, 165, 255)  # Orange if not holding

                # Draw connections
                connections = [
                    (0, 1), (1, 2), (2, 3), (3, 4),
                    (0, 5), (5, 6), (6, 7), (7, 8),
                    (0, 9), (9, 10), (10, 11), (11, 12),
                    (0, 13), (13, 14), (14, 15), (15, 16),
                    (0, 17), (17, 18), (18, 19), (19, 20),
                    (5, 9), (9, 13), (13, 17)
                ]

                for start_idx, end_idx in connections:
                    start = hand_landmarks[start_idx]
                    end = hand_landmarks[end_idx]
                    start_point = (int(start.x * frame_width), int(start.y * frame_height))
                    end_point = (int(end.x * frame_width), int(end.y * frame_height))
                    cv2.line(frame, start_point, end_point, color, 2)

                # Draw palm center
                palm = self._get_palm_center(hand_landmarks)
                palm_x = int(palm[0] * frame_width)
                palm_y = int(palm[1] * frame_height)
                cv2.circle(frame, (palm_x, palm_y), 12, (255, 0, 255), -1)

                # Show hand info
                hand_label = handedness.upper()
                if not is_drinking_hand:
                    status_text = f"{hand_label} (ignored)"
                elif has_cup:
                    status_text = f"{hand_label} + {held_cup['class'].upper()}"
                elif is_holding:
                    status_text = f"{hand_label} HOLDING"
                else:
                    status_text = f"{hand_label} not holding"
                cv2.putText(frame, status_text, (palm_x - 50, palm_y - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Add status text
        y_offset = 30
        cv2.putText(frame, f"Frames: {self.consecutive_frames}/{self.frames_to_confirm}",
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        y_offset += 30
        upward = self._detect_upward_motion()
        motion_text = "Motion: UPWARD" if upward else "Motion: --"
        motion_color = (0, 255, 0) if upward else (128, 128, 128)
        cv2.putText(frame, motion_text, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, motion_color, 2)

        # Cup detection status
        y_offset += 30
        if vessels:
            cup_names = ", ".join([v["class"] for v in vessels])
            cup_text = f"Cup: {cup_names}"
            cup_color = (255, 255, 0)  # Cyan
        else:
            cup_text = "Cup: not detected"
            cup_color = (128, 128, 128)
        cv2.putText(frame, cup_text, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, cup_color, 2)

        # Require cup mode indicator
        y_offset += 30
        mode_text = "Mode: CUP REQUIRED" if self.require_cup else "Mode: any gesture"
        mode_color = (255, 255, 0) if self.require_cup else (200, 200, 200)
        cv2.putText(frame, mode_text, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)

        # Bottle cache status
        y_offset += 30
        cache_info = self._get_bottle_cache_info()
        if cache_info:
            cache_text = f"Cache: {cache_info['class'].upper()} ({cache_info['remaining_seconds']:.1f}s)"
            cache_color = (0, 255, 255)  # Amarelo brilhante
        else:
            cache_text = "Cache: --"
            cache_color = (128, 128, 128)
        cv2.putText(frame, cache_text, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, cache_color, 2)

        cooldown_remaining = max(0, self.cooldown_seconds - (time.time() - self.last_gulp_time))
        if cooldown_remaining > 0:
            y_offset += 30
            cv2.putText(frame, f"Cooldown: {cooldown_remaining:.1f}s",
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        return frame, debug_info

    def __del__(self):
        """Cleanup on destruction"""
        self.stop_camera()


def main():
    """Test detector standalone with debug visualization"""
    print("=" * 50)
    print("Water Gulp Detector - Smart Detection Test")
    print("=" * 50)
    drinking_hand = CONFIG.get("drinking_hand", "both")
    require_cup = CONFIG.get("require_cup", True)
    print(f"\nTracking: {drinking_hand.upper()} hand only" if drinking_hand != "both" else "\nTracking: BOTH hands")
    print(f"Cup detection: {'REQUIRED' if require_cup else 'optional'}")
    print("\nDetection criteria:")
    print("  1. Hand close to mouth")
    print("  2. Hand in 'holding' pose (like holding a cup)")
    print("  3. Hand tilted up (drinking orientation)")
    print("  4. Upward hand motion detected")
    if require_cup:
        print("  5. Cup/bottle/glass detected in hand (REQUIRED)")
    if drinking_hand != "both":
        print(f"  6. Must be {drinking_hand.upper()} hand")
    print("\nPress 'q' to quit, 'c' to toggle cup requirement")
    print("-" * 50)

    detector = WaterGulpDetector()

    if not detector.start_camera():
        print("Failed to start camera!")
        return

    gulp_count = 0

    try:
        while True:
            # Get debug frame
            frame, debug_info = detector.get_debug_frame()

            if frame is None:
                print(f"Error: {debug_info.get('error')}")
                break

            # Also check for gulp
            gulp_detected, gulp_info = detector.process_frame()

            if gulp_detected:
                gulp_count += 1
                print(f"\n*** GULP DETECTED! *** Total: {gulp_count}")
                print(f"    Distance: {gulp_info.get('distance', 'N/A'):.3f}")
                print(f"    Holding pose: {gulp_info.get('is_holding')}")
                print(f"    Drinking orientation: {gulp_info.get('is_drinking_orientation')}")
                print(f"    Upward motion: {gulp_info.get('upward_motion')}")
                if gulp_info.get('held_cup_info'):
                    cup = gulp_info['held_cup_info']
                    print(f"    Cup detected: {cup['class']} ({cup['confidence']:.0%})")

            # Show the frame
            cv2.imshow("Water Gulp Detector - Debug View", frame)

            # Check for keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                # Toggle cup requirement
                detector.require_cup = not detector.require_cup
                status = "REQUIRED" if detector.require_cup else "optional"
                print(f"\n[CONFIG] Cup detection: {status}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        detector.stop_camera()
        cv2.destroyAllWindows()
        print(f"\nTotal gulps detected: {gulp_count}")


if __name__ == "__main__":
    main()
