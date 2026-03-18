"""
Vision-based water drinking detection using Ollama vision models.

Alternative to MediaPipe-based detection (detector.py).
Instead of tracking hand landmarks and heuristics, this sends periodic
camera snapshots to a vision model and asks "is this person drinking?".

Benefits over MediaPipe approach:
- More robust to lighting conditions
- Fewer false positives (understands context, not just geometry)
- Lighter on CPU (one check every N seconds vs 3 models every 300ms)
- Simpler logic
"""

import cv2
import time
import base64
from config import CONFIG


class VisionGulpDetector:
    """
    Detects water drinking by analyzing camera frames with Ollama vision model.

    Same interface as WaterGulpDetector for drop-in replacement.
    """

    def __init__(self, camera_index: int = None):
        self.camera_index = camera_index if camera_index is not None else CONFIG["camera_index"]
        self.cap = None
        self.running = False

        # Detection state
        self.last_gulp_time = 0
        self.cooldown_seconds = CONFIG.get("cooldown_seconds", 10)

        # Compatibility with main.py (used in _restart_detector)
        self.drinking_hand = CONFIG.get("drinking_hand", "both").lower()
        self.proximity_threshold = CONFIG.get("proximity_threshold", 0.12)

        # Vision settings
        self.vision_model = CONFIG.get("ai_vision_model", "moondream")
        self.vision_interval = CONFIG.get("ai_vision_interval_seconds", 10)
        self.last_vision_check = 0

        # Away detection (basic)
        self.is_away = False
        self.last_face_seen_time = time.time()
        self.away_timeout = CONFIG.get("away_timeout_seconds", 5)

        # Ollama
        self.ollama = None
        self.ollama_available = False
        self._init_ollama()

    def _init_ollama(self):
        """Connect to Ollama and verify vision model."""
        try:
            import ollama
            self.ollama = ollama

            models_response = ollama.list()
            model_names = []

            if hasattr(models_response, 'models'):
                for m in models_response.models:
                    name = getattr(m, 'model', None) or getattr(m, 'name', str(m))
                    model_names.append(name)
            elif isinstance(models_response, dict) and 'models' in models_response:
                for m in models_response['models']:
                    name = m.get('name') or m.get('model') or str(m)
                    model_names.append(name)

            model_found = self.vision_model in model_names or any(
                self.vision_model in name for name in model_names
            )

            if model_found:
                print(f"[Vision] Modelo {self.vision_model} encontrado")
            else:
                print(f"[Vision] AVISO - Modelo {self.vision_model} nao encontrado")
                print(f"[Vision] Modelos disponiveis: {model_names}")
                print(f"[Vision] Execute: ollama pull {self.vision_model}")

            self.ollama_available = True
            print(f"[Vision] Ollama conectado (modelo: {self.vision_model}, intervalo: {self.vision_interval}s)")

        except ImportError:
            print("[Vision] Biblioteca ollama nao instalada (pip install ollama)")
            self.ollama_available = False
        except Exception as e:
            print(f"[Vision] Erro ao conectar com Ollama: {e}")
            self.ollama_available = False

    def start_camera(self) -> bool:
        """Initialize camera capture."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # Buffer size 1 = always get latest frame
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.running = True
        return True

    def stop_camera(self):
        """Release camera resources."""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def process_frame(self) -> tuple:
        """
        Process a frame: capture and periodically analyze with vision model.

        Returns:
            tuple: (gulp_detected: bool, debug_info: dict)
        """
        if not self.cap or not self.running:
            return False, {"error": "Camera not running"}

        # Always read to keep buffer fresh
        ret, frame = self.cap.read()
        if not ret:
            return False, {"error": "Failed to read frame"}

        current_time = time.time()

        debug_info = {
            "hand_detected": False,
            "face_detected": not self.is_away,
            "cup_detected": False,
            "cup_held": False,
            "vessels": [],
            "distance": None,
            "is_holding": False,
            "is_drinking_orientation": False,
            "upward_motion": False,
            "consecutive_frames": 0,
            "cooldown_remaining": max(0, self.cooldown_seconds - (current_time - self.last_gulp_time)) if self.last_gulp_time else 0,
            "is_away": self.is_away,
            "require_cup": False,
            "bottle_cache_active": False,
            "bottle_cache_info": None,
            "_sc": False,
            "vision_mode": True,
            "vision_model": self.vision_model,
            "next_check_in": max(0, self.vision_interval - (current_time - self.last_vision_check)),
        }

        # Not time for vision check yet
        if current_time - self.last_vision_check < self.vision_interval:
            return False, debug_info

        # Cooldown check
        if self.last_gulp_time and current_time - self.last_gulp_time < self.cooldown_seconds:
            self.last_vision_check = current_time
            return False, debug_info

        # Ollama not available
        if not self.ollama_available:
            self.last_vision_check = current_time
            return False, debug_info

        self.last_vision_check = current_time

        # Encode frame to JPEG base64
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 70]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        image_b64 = base64.b64encode(buffer).decode()

        try:
            response = self.ollama.generate(
                model=self.vision_model,
                prompt="What is the person doing in this image? One sentence.",
                images=[image_b64],
                options={
                    "temperature": 0.1,
                    "num_predict": 60,
                }
            )

            answer = response['response'].strip()
            answer_lower = answer.lower()
            is_drinking = any(word in answer_lower for word in [
                "drinking", "sipping", "gulping", "beverage",
                "water bottle", "taking a drink", "hydrating",
            ])

            debug_info["vision_response"] = answer
            debug_info["face_detected"] = True

            # Reset away state on successful response
            self.last_face_seen_time = current_time
            if self.is_away:
                self.is_away = False
                debug_info["is_away"] = False

            if is_drinking:
                self.last_gulp_time = current_time
                print(f"[Vision] GULP DETECTED! Response: {answer}")
                return True, debug_info
            else:
                print(f"[Vision] Check: {answer}")

        except Exception as e:
            error_msg = str(e)
            print(f"[Vision] Erro: {error_msg}")
            debug_info["vision_error"] = error_msg

            # Mark as away if Ollama fails for too long
            if current_time - self.last_face_seen_time > self.away_timeout * 3:
                self.is_away = True
                debug_info["is_away"] = True

        return False, debug_info

    def get_calibration_response(self) -> str:
        """Stub for compatibility with main.py."""
        return ""

    def __del__(self):
        """Cleanup."""
        self.stop_camera()
