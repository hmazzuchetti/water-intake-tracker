"""
Water Intake Tracker - Main Application

Detects water drinking via webcam and shows progress overlay.
"""

import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

from config import CONFIG
from storage import Storage
from detector import WaterGulpDetector
from ui import ProgressBarOverlay
from settings_ui import show_settings, load_user_config, save_user_config
from ai_messages import AIMessageGenerator
from message_bubble import MessageBubbleManager


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class DetectorThread(QThread):
    """
    Thread that runs the water gulp detector.
    Emits signal when gulp is detected.
    """

    gulp_detected = pyqtSignal()
    away_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, detector: WaterGulpDetector):
        super().__init__()
        self.detector = detector
        self.running = False
        self.last_away_state = False

    def run(self):
        """Main detection loop"""
        if not self.detector.start_camera():
            self.error_occurred.emit("Failed to start camera")
            return

        self.running = True
        config = load_user_config()
        interval_ms = config.get("detection_interval", 500)

        print(f"Detector started. Checking every {interval_ms}ms")
        print("-" * 40)

        while self.running:
            gulp_detected, debug_info = self.detector.process_frame()

            # Check for away status change
            current_away = debug_info.get("is_away", False)
            if current_away != self.last_away_state:
                self.last_away_state = current_away
                self.away_changed.emit(current_away)

            if gulp_detected:
                print(f"[GULP DETECTED] {debug_info}")
                self.gulp_detected.emit()

            self.msleep(interval_ms)

        self.detector.stop_camera()
        print("Detector stopped")

    def stop(self):
        """Stop the detection loop"""
        self.running = False


def play_sound(config):
    """Play gulp sound if enabled and file exists"""
    if not config.get("sound_enabled", True):
        return

    # Build sound path - use resource path for bundled exe
    sound_file = config.get("gulp_sound", "gulp.wav")
    sounds_dir = config.get("sounds_dir", "sounds")

    # Try bundled path first (for exe), then local path (for development)
    sound_path = get_resource_path(os.path.join(sounds_dir, sound_file))
    if not os.path.exists(sound_path):
        # Fallback to local path
        sound_path = os.path.join(sounds_dir, sound_file)

    if not os.path.exists(sound_path):
        print(f"Sound file not found: {sound_path}")
        return

    try:
        import winsound
        # Use winsound for Windows - more reliable in exe builds
        winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"Could not play sound: {e}")


class WaterTrackerApp:
    """Main application class"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.config = None
        self.storage = None
        self.detector = None
        self.detector_thread = None
        self.overlay = None

        # AI Messages
        self.ai_generator = None
        self.message_manager = None
        self.message_timer = None
        self.last_message_time = 0

    def _show_initial_settings(self) -> bool:
        """Show settings dialog on every startup for webcam verification"""
        existing_config = load_user_config()
        first_run = existing_config.get("first_run", True)

        # Always show settings dialog on startup for webcam verification
        print("Showing settings for webcam verification...")
        self.config = show_settings(first_run=first_run)

        if self.config is None:
            # User cancelled
            return False

        # Update the global CONFIG with user settings
        CONFIG.update(self.config)

        return True

    def _on_gulp_detected(self):
        """Handle gulp detection"""
        self.storage.add_gulp()
        self.overlay.gulp_detected.emit()
        play_sound(self.config)

        ml_total, goal_ml, percentage = self.storage.get_progress()
        print(f"Progress: {ml_total}ml / {goal_ml}ml ({percentage:.1f}%)")

        # Maybe show a message on milestone
        if self.config.get("ai_messages_enabled", True):
            # Show message on 50% and 100%
            if percentage >= 100 or (percentage >= 50 and percentage < 55):
                self._show_ai_message()

    def _on_detector_error(self, error_msg: str):
        """Handle detector errors"""
        print(f"Detector Error: {error_msg}")
        QMessageBox.warning(
            None,
            "Camera Error",
            f"Could not start camera: {error_msg}\n\n"
            "Please check that:\n"
            "• Your webcam is connected\n"
            "• No other app is using the camera\n"
            "• The correct camera index is selected in settings"
        )

    def _open_settings(self):
        """Open settings dialog"""
        # Stop detector while settings are open
        if self.detector_thread:
            self.detector_thread.stop()
            self.detector_thread.wait(5000)

        # Also stop the camera to release it for testing in settings
        if self.detector:
            self.detector.stop_camera()

        new_config = show_settings(first_run=False)

        if new_config:
            self.config = new_config
            CONFIG.update(self.config)

            # Check if camera index changed - need new detector
            old_camera = self.detector.camera_index if self.detector else 0
            new_camera = new_config.get("camera_index", 0)

            if old_camera != new_camera:
                print(f"Camera changed from {old_camera} to {new_camera} - creating new detector...")
                self.detector = WaterGulpDetector(camera_index=new_camera)

            # Restart with new settings
            print("Settings updated - restarting detector...")
            self._restart_detector()
        else:
            # User cancelled - restart detector with old settings
            print("Settings cancelled - restarting detector...")
            self._restart_detector()

    def _restart_detector(self):
        """Restart the detector with new settings"""
        # Update detector parameters
        self.detector.drinking_hand = self.config.get("drinking_hand", "right").lower()
        self.detector.cooldown_seconds = self.config.get("cooldown_seconds", 10)
        self.detector.proximity_threshold = self.config.get("proximity_threshold", 0.15)

        # Update overlay
        self.overlay.reminder_interval = self.config.get("reminder_interval_minutes", 30) * 60
        self.overlay.hover_opacity = self.config.get("hover_opacity", 0.15)

        # Restart detector thread
        self.detector_thread = DetectorThread(self.detector)
        self.detector_thread.gulp_detected.connect(self._on_gulp_detected)
        self.detector_thread.away_changed.connect(self.overlay.set_away)
        self.detector_thread.error_occurred.connect(self._on_detector_error)
        self.detector_thread.start()

    def _init_ai_messages(self):
        """Initialize AI message system"""
        if not self.config.get("ai_messages_enabled", True):
            print("[AI] Mensagens desabilitadas")
            return

        try:
            # Initialize AI generator
            personality_file = self.config.get("ai_personality_file", "personalities/default.txt")
            self.ai_generator = AIMessageGenerator(personality_file)

            # Initialize message manager
            self.message_manager = MessageBubbleManager()

            # Setup timer for random messages
            interval_minutes = self.config.get("ai_message_interval_minutes", 45)
            self.message_timer = QTimer()
            self.message_timer.timeout.connect(self._on_message_timer)
            self.message_timer.start(interval_minutes * 60 * 1000)  # Convert to ms

            self.last_message_time = time.time()

            print(f"[AI] Sistema de mensagens inicializado (intervalo: {interval_minutes} min)")

        except Exception as e:
            print(f"[AI] Erro ao inicializar sistema de mensagens: {e}")

    def _show_ai_message(self):
        """Generate and show an AI message"""
        if not self.message_manager or not self.ai_generator:
            return

        # Don't show if there's already a bubble
        if self.message_manager.has_active_bubble():
            return

        try:
            # Get current status
            ml_total, goal_ml, percentage = self.storage.get_progress()

            # Calculate minutes since last gulp
            if hasattr(self.overlay, 'last_gulp_time'):
                minutes_since = int((time.time() - self.overlay.last_gulp_time) / 60)
            else:
                minutes_since = 0

            # Generate message with type
            message, message_type = self.ai_generator.generate_message(ml_total, goal_ml, minutes_since)

            # Show bubble with appropriate sound
            duration_seconds = self.config.get("ai_message_duration_seconds", 8)
            self.message_manager.show_message(message, duration_seconds * 1000, message_type)

            self.last_message_time = time.time()

            print(f"[AI] Mensagem ({message_type}): \"{message}\"")

        except Exception as e:
            print(f"[AI] Erro ao gerar mensagem: {e}")

    def _on_message_timer(self):
        """Handle random message timer"""
        # Only show messages when user is present
        if hasattr(self.overlay, 'is_away') and self.overlay.is_away:
            return

        self._show_ai_message()

    def run(self):
        """Start the application"""
        print("=" * 50)
        print("Water Intake Tracker")
        print("=" * 50)

        # Show settings on first run
        if not self._show_initial_settings():
            print("Setup cancelled by user")
            return 0

        # Initialize components with user config
        self.storage = Storage()
        self.detector = WaterGulpDetector(camera_index=self.config.get("camera_index", 0))

        # Update detector with user settings
        self.detector.drinking_hand = self.config.get("drinking_hand", "right").lower()
        self.detector.cooldown_seconds = self.config.get("cooldown_seconds", 10)

        # Show current progress
        ml_total, goal_ml, percentage = self.storage.get_progress()
        print(f"Today's progress: {ml_total}ml / {goal_ml}ml ({percentage:.1f}%)")
        print(f"Gulps today: {self.storage.get_glasses()}")
        print(f"Drinking hand: {self.config.get('drinking_hand', 'right')}")
        print("-" * 50)

        # Create UI
        self.overlay = ProgressBarOverlay(self.storage)
        self.overlay.settings_requested.connect(self._open_settings)
        self.overlay.show()

        # Create and start detector thread
        self.detector_thread = DetectorThread(self.detector)
        self.detector_thread.gulp_detected.connect(self._on_gulp_detected)
        self.detector_thread.away_changed.connect(self.overlay.set_away)
        self.detector_thread.error_occurred.connect(self._on_detector_error)
        self.detector_thread.start()

        # Initialize AI messages
        self._init_ai_messages()

        print("Application running. Close the overlay or press Ctrl+C to exit.")
        print("Right-click the progress bar for options.")
        print("-" * 50)

        # Run Qt event loop
        exit_code = self.app.exec_()

        # Cleanup
        self._shutdown()

        return exit_code

    def _shutdown(self):
        """Clean shutdown"""
        print("\nShutting down...")

        if self.detector_thread:
            self.detector_thread.stop()
            self.detector_thread.wait(5000)

        print("Goodbye!")


def main():
    """Entry point"""
    # Ensure working directory is the application directory
    # This fixes issues when starting with Windows (startup shortcut)
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    try:
        app = WaterTrackerApp()
        sys.exit(app.run())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
