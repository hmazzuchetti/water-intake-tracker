"""
Water Intake Tracker - Main Application

Manual gulp tracking with a clickable bar + dopamine microinteraction.
Webcam detection / mascot / AI messages were removed during the
"refactor/cleanup-and-sticky-notes" reformulation (see docs/REFORMULACAO.md).
"""

import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, QSharedMemory
from PyQt5.QtGui import QIcon

from config import CONFIG
from storage import Storage
from ui import ProgressBarOverlay
from settings_ui import show_settings, load_user_config


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def play_sound(config):
    """Play gulp sound if enabled and file exists"""
    if not config.get("sound_enabled", True):
        return

    sound_file = config.get("gulp_sound", "gulp.wav")
    sounds_dir = config.get("sounds_dir", "sounds")

    sound_path = get_resource_path(os.path.join(sounds_dir, sound_file))
    if not os.path.exists(sound_path):
        sound_path = os.path.join(sounds_dir, sound_file)

    if not os.path.exists(sound_path):
        print(f"Sound file not found: {sound_path}")
        return

    try:
        import winsound
        winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"Could not play sound: {e}")


class WaterTrackerApp:
    """Main application class"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Single instance check
        self._shared_mem = QSharedMemory("WaterIntakeTracker_SingleInstance")
        if self._shared_mem.attach():
            self._shared_mem.detach()
        if not self._shared_mem.create(1):
            print("Outra instância já está rodando. Saindo...")
            sys.exit(0)

        self.config = None
        self.storage = None
        self.overlay = None

        # System Tray
        self.tray_icon = None
        self.tray_update_timer = None

    def _show_initial_settings(self) -> bool:
        """Show settings dialog on every startup"""
        existing_config = load_user_config()
        first_run = existing_config.get("first_run", True)

        print("Showing settings dialog...")
        self.config = show_settings(first_run=first_run)

        if self.config is None:
            return False

        CONFIG.update(self.config)
        return True

    def _on_gulp_registered(self):
        """Handle a manual gulp registered by the overlay button.

        Storage was already updated by the overlay; here we play sound
        and refresh the tray."""
        ml_total, goal_ml, percentage = self.storage.get_progress()
        print(f"[Gulp] {ml_total}ml / {goal_ml}ml ({percentage:.1f}%)")

        play_sound(self.config)
        self._update_tray_tooltip()

    def _open_settings(self):
        """Open settings dialog and apply changes that don't need a restart."""
        new_config = show_settings(first_run=False)

        if new_config:
            self.config = new_config
            CONFIG.update(self.config)
            # bar_width / bar_position changes still need an app restart.

    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[Tray] System tray not available")
            return

        self.tray_icon = QSystemTrayIcon(self.app)

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

        tray_menu = QMenu()

        self.status_action = QAction("Water Tracker", self.app)
        self.status_action.setEnabled(False)
        tray_menu.addAction(self.status_action)

        tray_menu.addSeparator()

        self.visibility_action = QAction("Esconder Barra", self.app)
        self.visibility_action.triggered.connect(self._toggle_overlay_visibility)
        tray_menu.addAction(self.visibility_action)

        tray_menu.addSeparator()

        settings_action = QAction("Configurações...", self.app)
        settings_action.triggered.connect(self._open_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        quit_action = QAction("Sair", self.app)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        self.tray_update_timer = QTimer()
        self.tray_update_timer.timeout.connect(self._update_tray_tooltip)
        self.tray_update_timer.start(30000)
        self._update_tray_tooltip()

        print("[Tray] System tray initialized")

    def _update_tray_tooltip(self):
        if not self.tray_icon or not self.storage:
            return

        ml_total, goal_ml, percentage = self.storage.get_progress()
        glasses = self.storage.get_glasses()

        tooltip = (
            f"Water Tracker\n"
            f"{glasses} goles ({ml_total}ml / {goal_ml}ml)\n"
            f"{percentage:.0f}% da meta"
        )
        self.tray_icon.setToolTip(tooltip)
        self.status_action.setText(f"{glasses} goles - {percentage:.0f}%")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._open_settings()
        elif reason == QSystemTrayIcon.Trigger:
            self._toggle_overlay_visibility()

    def _toggle_overlay_visibility(self):
        if not self.overlay:
            return
        if self.overlay.isVisible():
            self.overlay.hide()
            self.visibility_action.setText("Mostrar Barra")
        else:
            self.overlay.show()
            self.visibility_action.setText("Esconder Barra")

    def _quit_app(self):
        print("[Tray] Quit requested")
        self._shutdown()
        self.app.quit()

    def run(self):
        """Start the application"""
        print("=" * 50)
        print("Water Intake Tracker (manual mode)")
        print("=" * 50)

        if not self._show_initial_settings():
            print("Setup cancelled by user")
            return 0

        self.storage = Storage()

        ml_total, goal_ml, percentage = self.storage.get_progress()
        print(f"Today's progress: {ml_total}ml / {goal_ml}ml ({percentage:.1f}%)")
        print(f"Goles today: {self.storage.get_glasses()}")
        print("-" * 50)

        # UI
        self.overlay = ProgressBarOverlay(self.storage)
        self.overlay.settings_requested.connect(self._open_settings)
        self.overlay.gulp_registered.connect(self._on_gulp_registered)
        self.overlay.show()

        # Tray
        self._setup_system_tray()

        print("Application running. Click the bar to register a gulp.")
        print("Right-click the bar for options. Tray icon for menu.")
        print("-" * 50)

        if self.tray_icon:
            self.tray_icon.showMessage(
                "Water Tracker",
                f"Modo manual ativo.\n{percentage:.0f}% da meta de hoje.",
                QSystemTrayIcon.Information,
                3000
            )

        exit_code = self.app.exec_()
        self._shutdown()
        return exit_code

    def _shutdown(self):
        print("\nShutting down...")
        if self.tray_update_timer:
            self.tray_update_timer.stop()
        if self.tray_icon:
            self.tray_icon.hide()
        print("Goodbye!")


def main():
    """Entry point"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
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
