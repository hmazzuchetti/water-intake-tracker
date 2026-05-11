"""
Settings window for Water Intake Tracker.

Após a reformulação 2026-05 (refactor/cleanup-and-sticky-notes),
sobrou apenas General + Help. Webcam, mascote, IA, lembrete e tudo
relacionado foi removido.
"""

import sys
import os
import json
import winreg
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QMessageBox, QTabWidget, QWidget, QTextBrowser
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import CONFIG
from version import __version__


def get_config_path():
    """Return a writable path for the user config file."""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "user_config.json")
    return "user_config.json"


CONFIG_FILE = get_config_path()
APP_NAME = "WaterIntakeTracker"


def load_user_config() -> dict:
    """Load user configuration from file, merging with defaults."""
    config = CONFIG.copy()
    config_path = get_config_path()

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")

    return config


def save_user_config(config: dict) -> bool:
    """Persist the user-tweakable subset of the config."""
    saveable_keys = [
        "goal_ml", "ml_per_gulp",
        "bar_position", "bar_width",
        "sound_enabled",
        "start_with_windows", "first_run",
    ]
    to_save = {k: config[k] for k in saveable_keys if k in config}
    config_path = get_config_path()

    try:
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(to_save, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


def is_first_run() -> bool:
    config = load_user_config()
    return config.get("first_run", True)


def set_startup_with_windows(enable: bool) -> bool:
    """Add or remove app from Windows startup. Returns True on success."""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        if enable:
            if getattr(sys, 'frozen', False):
                app_path = f'"{sys.executable}"'
            else:
                app_path = f'pythonw "{os.path.abspath("main.py")}"'

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
        else:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, APP_NAME)
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
            except Exception:
                pass

        return True
    except PermissionError as e:
        print(f"Permission denied setting startup (this is normal): {e}")
        return False
    except Exception as e:
        print(f"Error setting startup: {e}")
        return False


def is_startup_enabled() -> bool:
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


class SettingsDialog(QDialog):
    """Settings dialog for configuring the water tracker."""

    def __init__(self, parent=None, first_run=False):
        super().__init__(parent)
        self.first_run = first_run
        self.config = load_user_config()

        self.setWindowTitle("Water Intake Tracker - Settings")
        self.setMinimumWidth(420)
        self.setMinimumHeight(360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("💧 Water Intake Tracker")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version_label = QLabel(f"v{__version__}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #999; font-size: 11px; margin-bottom: 4px;")
        layout.addWidget(version_label)

        if self.first_run:
            welcome = QLabel("Welcome! Let's configure your settings.")
            welcome.setAlignment(Qt.AlignCenter)
            welcome.setStyleSheet("color: #666; margin-bottom: 10px;")
            layout.addWidget(welcome)

        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_help_tab(), "How to Use")
        layout.addWidget(tabs)

        button_layout = QHBoxLayout()
        self.start_windows_check = QCheckBox("Start with Windows")
        self.start_windows_check.setChecked(is_startup_enabled())
        button_layout.addWidget(self.start_windows_check)
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save && Start" if self.first_run else "Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_accept)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px;")
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Daily goal
        goal_group = QGroupBox("Daily Goal")
        goal_layout = QGridLayout(goal_group)

        goal_layout.addWidget(QLabel("Target water intake:"), 0, 0)
        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(500, 10000)
        self.goal_spin.setSingleStep(100)
        self.goal_spin.setSuffix(" ml")
        goal_layout.addWidget(self.goal_spin, 0, 1)

        goal_layout.addWidget(QLabel("ML por gole (clique do botão):"), 1, 0)
        self.gulp_spin = QSpinBox()
        self.gulp_spin.setRange(50, 500)
        self.gulp_spin.setSingleStep(25)
        self.gulp_spin.setSuffix(" ml")
        goal_layout.addWidget(self.gulp_spin, 1, 1)

        layout.addWidget(goal_group)

        # Appearance
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QGridLayout(appearance_group)

        appearance_layout.addWidget(QLabel("Bar position:"), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Right", "Left"])
        appearance_layout.addWidget(self.position_combo, 0, 1)

        appearance_layout.addWidget(QLabel("Bar width:"), 1, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(20, 120)
        self.width_spin.setSuffix(" px")
        appearance_layout.addWidget(self.width_spin, 1, 1)

        layout.addWidget(appearance_group)

        # Sound
        self.sound_check = QCheckBox("Tocar som ao registrar gole")
        layout.addWidget(self.sound_check)

        # Note about restart
        note = QLabel("⚠️ Mudanças em posição / largura aplicam após reiniciar o app.")
        note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(note)

        layout.addStretch()
        return widget

    def _create_help_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml("""
        <h3>🚀 Como usar</h3>
        <p>O app fica como uma barra fina na lateral da tela. A barra mostra
        o progresso de hidratação do dia, e tem um botão grande embaixo:
        clique nele toda vez que você der um gole d'água.</p>

        <h3>📊 Barra de água</h3>
        <p>Sobe conforme você clica o botão. Reseta automaticamente à meia-noite.</p>

        <h3>🖱️ Controles do mouse</h3>
        <ul>
            <li><b>Clique no botão (gota d'água):</b> registra gole</li>
            <li><b>Clique e arrasta a barra:</b> move pra outra posição</li>
            <li><b>Clique direito:</b> menu (adicionar/remover gole, reset, settings, sair)</li>
            <li><b>Hover:</b> tooltip com status do dia</li>
        </ul>

        <h3>🔧 System Tray</h3>
        <p>Ícone na bandeja do sistema:</p>
        <ul>
            <li><b>Clique simples:</b> mostra/esconde a barra</li>
            <li><b>Clique duplo:</b> abre Configurações</li>
            <li><b>Clique direito:</b> menu de contexto</li>
        </ul>

        <h3>💾 Persistência</h3>
        <p>O progresso do dia fica salvo em <code>data/progress.json</code> e
        sobrevive a fechar/reabrir o app.</p>
        """)
        layout.addWidget(help_text)

        return widget

    def _load_values(self):
        self.goal_spin.setValue(self.config.get("goal_ml", 3000))
        self.gulp_spin.setValue(self.config.get("ml_per_gulp", 100))

        position = self.config.get("bar_position", "right").lower()
        self.position_combo.setCurrentIndex(0 if position == "right" else 1)

        self.width_spin.setValue(self.config.get("bar_width", 30))
        self.sound_check.setChecked(self.config.get("sound_enabled", True))

    def _save_and_accept(self):
        self.config["goal_ml"] = self.goal_spin.value()
        self.config["ml_per_gulp"] = self.gulp_spin.value()
        self.config["bar_position"] = "right" if self.position_combo.currentIndex() == 0 else "left"
        self.config["bar_width"] = self.width_spin.value()
        self.config["sound_enabled"] = self.sound_check.isChecked()
        self.config["first_run"] = False
        self.config["start_with_windows"] = self.start_windows_check.isChecked()

        if not save_user_config(self.config):
            QMessageBox.warning(
                self,
                "Save Error",
                "Could not save configuration file. Settings will be used for this session only."
            )

        try:
            set_startup_with_windows(self.start_windows_check.isChecked())
        except Exception as e:
            print(f"Could not set startup option: {e}")

        self.accept()

    def get_config(self) -> dict:
        return self.config


def show_settings(parent=None, first_run=False) -> dict:
    """Show settings dialog and return config if accepted, None if cancelled."""
    dialog = SettingsDialog(parent, first_run)
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_config()
    return None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    config = show_settings(first_run=True)
    if config:
        print("Settings saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print("Settings cancelled")
