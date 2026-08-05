"""
Water Intake Tracker - Main Application

Manual gulp tracking with a clickable bar + dopamine microinteraction.
Webcam detection / mascot / AI messages were removed during the
"refactor/cleanup-and-sticky-notes" reformulation (see docs/REFORMULACAO.md).
"""

import sys
import os
import time
import traceback
import datetime
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtCore import QTimer, QSharedMemory
from PyQt5.QtGui import QIcon

from config import CONFIG
from storage import Storage
from ui import ProgressBarOverlay
from settings_ui import show_settings, load_user_config
from game import GameStore
from game_ui import StatsDialog
from version import __version__


def get_user_data_dir() -> str:
    """Per-user writable directory for logs and crash dumps.

    On Windows this is %APPDATA%\\WaterIntakeTracker.
    """
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "WaterIntakeTracker")
    os.makedirs(path, exist_ok=True)
    return path


def _install_crash_handler():
    """Capture any uncaught exception and write it to a log file. Without
    this, .exe (windowed) crashes are invisible — stderr is discarded and
    the process just disappears."""
    log_path = os.path.join(get_user_data_dir(), "crash.log")

    def _handler(exc_type, exc_value, exc_tb):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n=== CRASH {datetime.datetime.now().isoformat()} (v{__version__}) ===\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
                f.write("\n")
        except Exception:
            pass
        try:
            QMessageBox.critical(
                None, "Water Intake Tracker — erro inesperado",
                f"Erro: {exc_value}\n\nLog salvo em:\n{log_path}"
            )
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def _resolve_sound_path(config) -> str:
    """Resolve the gulp.wav location (PyInstaller bundle or local). Returns '' if missing."""
    sound_file = config.get("gulp_sound", "gulp.wav")
    sounds_dir = config.get("sounds_dir", "sounds")
    candidate = get_resource_path(os.path.join(sounds_dir, sound_file))
    if not os.path.exists(candidate):
        candidate = os.path.join(sounds_dir, sound_file)
    return candidate if os.path.exists(candidate) else ""


def play_sound_winsound_fallback(config):
    """Plain winsound playback — no volume control. Used as fallback when
    QSoundEffect isn't available in the runtime."""
    if not config.get("sound_enabled", True):
        return
    sound_path = _resolve_sound_path(config)
    if not sound_path:
        return
    try:
        import winsound
        winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"[Sound] winsound fallback failed: {e}")


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
        self.game_store = None
        self.overlay = None

        # Sound
        self._sound_effect = None  # QSoundEffect instance (volume-controlled)

        # System Tray
        self.tray_icon = None
        self.tray_update_timer = None

    def _show_initial_settings(self) -> bool:
        """Load config silently; only show the settings dialog on the very
        first run. Um app de ambiente não pode pedir permissão pra existir
        a cada boot — o dialog fica acessível via tray/menu."""
        existing_config = load_user_config()
        first_run = existing_config.get("first_run", True)

        if first_run:
            print("First run — showing settings dialog...")
            self.config = show_settings(first_run=True)
            if self.config is None:
                return False
        else:
            self.config = existing_config

        CONFIG.update(self.config)
        return True

    def _gulp_volume_norm(self) -> float:
        return max(0.0, min(1.0, self.config.get("gulp_volume", 50) / 100.0))

    def _setup_sound(self):
        """Try to set up QSoundEffect for volume-controlled playback.
        Falls back to winsound (no volume) if QtMultimedia isn't available."""
        sound_path = _resolve_sound_path(self.config)
        if not sound_path:
            print("[Sound] gulp.wav não encontrado")
            return
        try:
            from PyQt5.QtMultimedia import QSoundEffect
            from PyQt5.QtCore import QUrl
            eff = QSoundEffect()
            eff.setSource(QUrl.fromLocalFile(os.path.abspath(sound_path)))
            eff.setVolume(self._gulp_volume_norm())
            self._sound_effect = eff
            print(f"[Sound] QSoundEffect ok (volume {self._gulp_volume_norm():.2f})")
        except Exception as e:
            print(f"[Sound] QSoundEffect indisponível, usando winsound: {e}")
            self._sound_effect = None

    def _play_gulp_sound(self):
        if not self.config.get("sound_enabled", True):
            return
        if self._sound_effect is not None:
            # Pick up live volume changes from settings dialog
            self._sound_effect.setVolume(self._gulp_volume_norm())
            self._sound_effect.play()
        else:
            play_sound_winsound_fallback(self.config)

    def _on_gulp_registered(self):
        """Handle a manual gulp registered by the overlay button.

        Storage was already updated by the overlay; here we play sound,
        refresh the tray, and surface gamification events (level-up,
        achievements, streak) as tray notifications."""
        ml_total, goal_ml, percentage = self.storage.get_progress()
        print(f"[Gulp] {ml_total}ml / {goal_ml}ml ({percentage:.1f}%)")

        self._play_gulp_sound()
        self._update_tray_tooltip()

        # Game feedback: o overlay celebra no próprio botão (EffectsLayer).
        # Tray toast é só fallback pra quando a barra está escondida.
        overlay_visible = self.overlay is not None and self.overlay.isVisible()
        if overlay_visible or not self.tray_icon:
            return

        events = getattr(self.overlay, "recent_events", {}) or {}
        if events.get("leveled_up"):
            new_lvl = events.get("new_level", 0)
            self.tray_icon.showMessage(
                f"Nível {new_lvl}!",
                "Você subiu de nível bebendo água.",
                QSystemTrayIcon.Information, 4000
            )
        for ach in events.get("unlocked", []):
            self.tray_icon.showMessage(
                f"Conquista: {ach.get('name', 'Nova conquista')}",
                ach.get("desc", ""),
                QSystemTrayIcon.Information, 4000
            )
        if events.get("streak_extended") and self.game_store:
            streak = self.game_store.state.current_streak
            self.tray_icon.showMessage(
                f"Streak {streak}!",
                f"{streak} dias seguidos batendo a meta",
                QSystemTrayIcon.Information, 3000
            )

    def _open_settings(self):
        """Open settings dialog and apply changes that don't need a restart."""
        new_config = show_settings(first_run=False)

        if new_config:
            self.config = new_config
            CONFIG.update(self.config)
            # Live-applicable: gulp/glass/bottle amounts → update satellite tooltips
            if self.overlay is not None:
                try:
                    self.overlay.reload_after_settings()
                except Exception as e:
                    print(f"[Settings] Erro ao recarregar overlay: {e}")

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

        stats_action = QAction("📊 Estatísticas...", self.app)
        stats_action.triggered.connect(self._open_stats)
        tray_menu.addAction(stats_action)

        reset_pos_action = QAction("📍 Resetar posição", self.app)
        reset_pos_action.triggered.connect(self._reset_overlay_position)
        tray_menu.addAction(reset_pos_action)

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

        level_str = ""
        if self.game_store is not None:
            try:
                level_str = f" · Lv. {self.game_store.level()}"
            except Exception:
                pass

        tooltip = (
            f"Water Tracker v{__version__}{level_str}\n"
            f"{glasses} goles ({ml_total}ml / {goal_ml}ml)\n"
            f"{percentage:.0f}% da meta"
        )
        self.tray_icon.setToolTip(tooltip)
        self.status_action.setText(f"{glasses} goles · {percentage:.0f}%{level_str}")

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

    def _reset_overlay_position(self):
        """Bring the overlay back to its default corner (taskbar-safe)."""
        if self.overlay is None:
            return
        try:
            self.overlay.reset_position()
            if not self.overlay.isVisible():
                self.overlay.show()
                if hasattr(self, "visibility_action"):
                    self.visibility_action.setText("Esconder Barra")
        except Exception as e:
            print(f"[Tray] Reset posição falhou: {e}")

    def _open_stats(self):
        """Open the gamification stats dialog."""
        if self.game_store is None or self.storage is None:
            return
        try:
            dlg = StatsDialog(self.game_store, self.storage, parent=None)
            dlg.exec_()
        except Exception as e:
            print(f"[Stats] Erro ao abrir diálogo: {e}")

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
        self.game_store = GameStore()

        ml_total, goal_ml, percentage = self.storage.get_progress()
        print(f"Today's progress: {ml_total}ml / {goal_ml}ml ({percentage:.1f}%)")
        print(f"Goles today: {self.storage.get_glasses()}")
        print(f"Game state: Lv. {self.game_store.level()} ({self.game_store.state.total_xp} XP, "
              f"streak: {self.game_store.state.current_streak} dias)")
        print("-" * 50)

        # Sound setup (QSoundEffect with volume control, winsound fallback)
        self._setup_sound()

        # UI — share game_store with overlay so the button paints level/progress
        self.overlay = ProgressBarOverlay(self.storage, game_store=self.game_store)
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


def _migrate_data_to_appdata():
    """One-shot: instalações antigas guardavam tudo ao lado do .exe (onde o
    uninstaller apagava e Program Files bloqueia escrita). Copia pro APPDATA
    na primeira execução da versão nova; nunca sobrescreve destino existente."""
    if not getattr(sys, 'frozen', False):
        return
    import shutil
    exe_dir = os.path.dirname(sys.executable)
    dest_root = get_user_data_dir()
    dest_data = os.path.join(dest_root, "data")
    os.makedirs(dest_data, exist_ok=True)

    for name in ("progress.json", "game.json", "notes.json"):
        src = os.path.join(exe_dir, "data", name)
        dst = os.path.join(dest_data, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                print(f"[Migrate] {name} -> APPDATA")
            except OSError as e:
                print(f"[Migrate] Falha ao copiar {name}: {e}")

    src_cfg = os.path.join(exe_dir, "user_config.json")
    dst_cfg = os.path.join(dest_root, "user_config.json")
    if os.path.exists(src_cfg) and not os.path.exists(dst_cfg):
        try:
            shutil.copy2(src_cfg, dst_cfg)
            print("[Migrate] user_config.json -> APPDATA")
        except OSError as e:
            print(f"[Migrate] Falha ao copiar user_config.json: {e}")


def main():
    """Entry point"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    _install_crash_handler()
    _migrate_data_to_appdata()

    try:
        app = WaterTrackerApp()
        sys.exit(app.run())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
