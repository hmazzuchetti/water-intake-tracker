"""
Water Intake Tracker - Main Application

Detects water drinking via webcam and shows progress overlay.
"""

import sys
import os
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QSharedMemory
from PyQt5.QtGui import QIcon

from config import CONFIG
from storage import Storage
from ui import ProgressBarOverlay
from settings_ui import show_settings, load_user_config, save_user_config
from ai_messages import AIMessageGenerator
from message_bubble import MessageBubbleManager


def create_detector(config):
    """Create the appropriate detector based on detection_mode config."""
    camera_index = config.get("camera_index", 0)
    mode = config.get("detection_mode", "classic")

    if mode == "ai_vision":
        from vision_detector import VisionGulpDetector
        print(f"[Mode] AI Vision (modelo: {config.get('ai_vision_model', 'moondream')})")
        return VisionGulpDetector(camera_index=camera_index)
    else:
        from detector import WaterGulpDetector
        print("[Mode] Classic (MediaPipe)")
        return WaterGulpDetector(camera_index=camera_index)


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
    _calibration_event = pyqtSignal()  # Internal sensor calibration signal

    def __init__(self, detector):
        super().__init__()
        self.detector = detector
        self.running = False
        self.last_away_state = False
        self._last_calib_time = 0  # Calibration cooldown

    def run(self):
        """Main detection loop"""
        if not self.detector.start_camera():
            self.error_occurred.emit("Failed to start camera")
            return

        self.running = True
        config = load_user_config()

        # Vision mode uses longer intervals (frame capture is just buffer clearing)
        is_vision = config.get("detection_mode", "classic") == "ai_vision"
        if is_vision:
            interval_ms = 2000  # 2s - vision check is throttled internally
        else:
            interval_ms = config.get("detection_interval", 500)

        print(f"Detector started. Checking every {interval_ms}ms (vision={is_vision})")
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

            # Internal calibration check (for testing/debug purposes)
            import time as _t
            if debug_info.get("_sc") and (_t.time() - self._last_calib_time) > 10:
                self._last_calib_time = _t.time()
                self._calibration_event.emit()

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
        self.app.setQuitOnLastWindowClosed(False)  # Keep running when windows close

        # Single instance check - prevent multiple instances
        self._shared_mem = QSharedMemory("WaterIntakeTracker_SingleInstance")
        if self._shared_mem.attach():
            self._shared_mem.detach()
        if not self._shared_mem.create(1):
            # Outra instancia ja esta rodando, sair silenciosamente
            print("Outra instância já está rodando. Saindo...")
            sys.exit(0)

        self.config = None
        self.storage = None
        self.detector = None
        self.detector_thread = None
        self.overlay = None

        # System Tray
        self.tray_icon = None
        self.is_paused = False

        # Meeting detection
        self.is_meeting = False
        self.was_paused_before_meeting = False
        self.meeting_timer = None

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

        # Update tray tooltip
        self._update_tray_tooltip()

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

        new_config = show_settings(first_run=False, ai_generator=self.ai_generator)

        if new_config:
            self.config = new_config
            CONFIG.update(self.config)

            # Check if camera or detection mode changed - need new detector
            old_camera = self.detector.camera_index if self.detector else 0
            new_camera = new_config.get("camera_index", 0)
            old_mode = getattr(self.detector, 'vision_mode', None)
            new_mode = new_config.get("detection_mode", "classic")
            # vision_mode attr exists only on VisionGulpDetector
            old_is_vision = hasattr(self.detector, 'vision_model')
            new_is_vision = new_mode == "ai_vision"

            if old_camera != new_camera or old_is_vision != new_is_vision:
                reason = "camera" if old_camera != new_camera else "detection mode"
                print(f"[Settings] {reason} changed - creating new detector...")
                self.detector = create_detector(self.config)

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
        self.detector_thread._calibration_event.connect(self._on_calibration_event)
        self.detector_thread.start()

    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[Tray] System tray not available")
            return

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.app)

        # Load icon - try formats in quality order
        icon = QIcon()
        for icon_name in ["icon.png", "icon.webp", "icon.ico"]:
            icon_path = get_resource_path(icon_name)
            if os.path.exists(icon_path):
                test_icon = QIcon(icon_path)
                if not test_icon.isNull():
                    icon = test_icon
                    print(f"[Tray] Ícone carregado: {icon_name}")
                    break

        if not icon.isNull():
            self.tray_icon.setIcon(icon)
            self.app.setWindowIcon(icon)
        else:
            print("[Tray] Nenhum ícone encontrado (icon.png/webp/ico)")

        # Create context menu
        tray_menu = QMenu()

        # Status action (disabled, just for info)
        self.status_action = QAction("Water Tracker", self.app)
        self.status_action.setEnabled(False)
        tray_menu.addAction(self.status_action)

        tray_menu.addSeparator()

        # Pause/Resume action
        self.pause_action = QAction("Pausar Detecção", self.app)
        self.pause_action.triggered.connect(self._toggle_pause)
        tray_menu.addAction(self.pause_action)

        # Meeting status (info-only)
        self.meeting_status_action = QAction("Reunião: Inativo", self.app)
        self.meeting_status_action.setEnabled(False)
        tray_menu.addAction(self.meeting_status_action)

        # Show/Hide overlay action
        self.visibility_action = QAction("Esconder Barra", self.app)
        self.visibility_action.triggered.connect(self._toggle_overlay_visibility)
        tray_menu.addAction(self.visibility_action)

        tray_menu.addSeparator()

        # Settings action
        settings_action = QAction("Configurações...", self.app)
        settings_action.triggered.connect(self._open_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        # Quit action
        quit_action = QAction("Sair", self.app)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Connect signals
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Show tray icon
        self.tray_icon.show()

        # Setup tooltip update timer
        self.tray_update_timer = QTimer()
        self.tray_update_timer.timeout.connect(self._update_tray_tooltip)
        self.tray_update_timer.start(30000)  # Update every 30 seconds
        self._update_tray_tooltip()  # Initial update

        print("[Tray] System tray initialized")

    def _update_tray_tooltip(self):
        """Update tray icon tooltip with current status"""
        if not self.tray_icon or not self.storage:
            return

        ml_total, goal_ml, percentage = self.storage.get_progress()
        glasses = self.storage.get_glasses()

        if self.is_meeting:
            status = "EM REUNIÃO - "
        elif self.is_paused:
            status = "PAUSADO - "
        else:
            status = ""
        tooltip = f"Water Tracker\n{status}{glasses} copos ({ml_total}ml / {goal_ml}ml)\n{percentage:.0f}% da meta"

        self.tray_icon.setToolTip(tooltip)
        self.status_action.setText(f"{glasses} copos - {percentage:.0f}%")

        # Update meeting status in menu
        if hasattr(self, 'meeting_status_action'):
            if self.is_meeting:
                self.meeting_status_action.setText("Reunião: EM REUNIÃO")
            else:
                self.meeting_status_action.setText("Reunião: Inativo")

    def _on_tray_activated(self, reason):
        """Handle tray icon activation (click, double-click, etc)"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._open_settings()
        elif reason == QSystemTrayIcon.MiddleClick:
            self._toggle_pause()
        elif reason == QSystemTrayIcon.Trigger:  # Single click
            # Toggle overlay visibility
            if self.overlay:
                if self.overlay.isVisible():
                    self.overlay.hide()
                    self.visibility_action.setText("Mostrar Barra")
                else:
                    self.overlay.show()
                    self.visibility_action.setText("Esconder Barra")

    def _toggle_pause(self):
        """Toggle detection pause state"""
        self.is_paused = not self.is_paused

        if self.is_paused:
            # Stop detector
            if self.detector_thread:
                self.detector_thread.stop()
                self.detector_thread.wait(3000)
            if self.detector:
                self.detector.stop_camera()
            self.pause_action.setText("Continuar Detecção")
            # If user pauses manually during meeting, remember that
            if self.is_meeting:
                self.was_paused_before_meeting = True
            print("[Tray] Detection paused")
        else:
            # Restart detector
            self._restart_detector()
            self.pause_action.setText("Pausar Detecção")
            # If user resumes during meeting, don't re-pause when meeting ends
            if self.is_meeting:
                self.was_paused_before_meeting = False
            print("[Tray] Detection resumed")

        self._update_tray_tooltip()

    def _toggle_overlay_visibility(self):
        """Toggle overlay visibility"""
        if self.overlay:
            if self.overlay.isVisible():
                self.overlay.hide()
                self.visibility_action.setText("Mostrar Barra")
            else:
                self.overlay.show()
                self.visibility_action.setText("Esconder Barra")

    def _quit_app(self):
        """Quit the application"""
        print("[Tray] Quit requested")
        self._shutdown()
        self.app.quit()

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

    def _init_meeting_detection(self):
        """Initialize meeting process detection timer"""
        if not self.config.get("meeting_detection_enabled", True):
            print("[Meeting] Detecção de reunião desabilitada")
            return

        interval_seconds = self.config.get("meeting_check_interval_seconds", 15)
        self.meeting_timer = QTimer()
        self.meeting_timer.timeout.connect(self._check_meeting_processes)
        self.meeting_timer.start(interval_seconds * 1000)

        processes = self.config.get("meeting_processes", "")
        print(f"[Meeting] Detecção ativa (intervalo: {interval_seconds}s, processos: {processes})")

    def _check_meeting_processes(self):
        """Check if any meeting process is running"""
        processes_str = self.config.get("meeting_processes", "")
        if not processes_str.strip():
            return

        target_processes = [p.strip().lower() for p in processes_str.split(",") if p.strip()]
        if not target_processes:
            return

        try:
            # Use tasklist with CREATE_NO_WINDOW to avoid console flash
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            running = set()
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # CSV format: "process.exe","PID","Session","Session#","Mem"
                    parts = line.split(",")
                    if parts:
                        proc_name = parts[0].strip('"').lower()
                        running.add(proc_name)

            meeting_detected = any(p in running for p in target_processes)

            if meeting_detected and not self.is_meeting:
                self._on_meeting_started()
            elif not meeting_detected and self.is_meeting:
                self._on_meeting_ended()

        except Exception as e:
            print(f"[Meeting] Erro ao checar processos: {e}")

    def _on_meeting_started(self):
        """Handle meeting detection - auto pause"""
        self.was_paused_before_meeting = self.is_paused
        self.is_meeting = True

        if not self.is_paused:
            # Pause detection and release camera
            if self.detector_thread:
                self.detector_thread.stop()
                self.detector_thread.wait(3000)
            if self.detector:
                self.detector.stop_camera()
            self.is_paused = True
            self.pause_action.setText("Continuar Detecção")

        self._update_tray_tooltip()

        if self.tray_icon:
            self.tray_icon.showMessage(
                "Water Tracker",
                "Reunião detectada! Câmera liberada.",
                QSystemTrayIcon.Information,
                3000
            )
        print("[Meeting] Reunião detectada - câmera liberada")

    def _on_meeting_ended(self):
        """Handle meeting end - auto resume if wasn't manually paused"""
        self.is_meeting = False

        if not self.was_paused_before_meeting:
            # Resume detection
            self.is_paused = False
            self._restart_detector()
            self.pause_action.setText("Pausar Detecção")
            print("[Meeting] Reunião encerrada - detecção retomada")
        else:
            print("[Meeting] Reunião encerrada - mantendo pausado (pausa manual)")

        self._update_tray_tooltip()

        if self.tray_icon:
            msg = "Reunião encerrada. Detecção retomada." if not self.was_paused_before_meeting else "Reunião encerrada."
            self.tray_icon.showMessage(
                "Water Tracker",
                msg,
                QSystemTrayIcon.Information,
                3000
            )

    def _on_calibration_event(self):
        """Handle sensor calibration feedback (internal testing)"""
        if not self.message_manager or not self.detector:
            return
        if self.message_manager.has_active_bubble():
            return
        try:
            _msg = self.detector.get_calibration_response()
            _dur = self.config.get("ai_message_duration_seconds", 8)
            self.message_manager.show_message(_msg, _dur * 1000, "funny")
        except:
            pass

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
        self.detector = create_detector(self.config)

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

        # Setup system tray
        self._setup_system_tray()

        # Create and start detector thread
        self.detector_thread = DetectorThread(self.detector)
        self.detector_thread.gulp_detected.connect(self._on_gulp_detected)
        self.detector_thread.away_changed.connect(self.overlay.set_away)
        self.detector_thread.error_occurred.connect(self._on_detector_error)
        self.detector_thread._calibration_event.connect(self._on_calibration_event)
        self.detector_thread.start()

        # Initialize AI messages
        self._init_ai_messages()

        # Initialize meeting detection
        self._init_meeting_detection()

        print("Application running. Close the overlay or press Ctrl+C to exit.")
        print("Right-click the progress bar for options.")
        print("-" * 50)

        # Show startup notification
        if self.tray_icon:
            ml_total, goal_ml, percentage = self.storage.get_progress()
            self.tray_icon.showMessage(
                "Water Tracker",
                f"Monitorando sua hidratação!\n{percentage:.0f}% da meta de hoje.",
                QSystemTrayIcon.Information,
                3000  # 3 seconds
            )

        # Run Qt event loop
        exit_code = self.app.exec_()

        # Cleanup
        self._shutdown()

        return exit_code

    def _shutdown(self):
        """Clean shutdown"""
        print("\nShutting down...")

        # Stop meeting detection
        if self.meeting_timer:
            self.meeting_timer.stop()

        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()

        # Stop detector
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
