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
    QGroupBox, QMessageBox, QTabWidget, QWidget, QTextBrowser,
    QSlider
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import CONFIG
from version import __version__


def get_config_path():
    """Return a writable path for the user config file.

    v2.3.0: no .exe o config mora em %APPDATA%\\WaterIntakeTracker —
    ao lado do exe falhava silenciosamente em Program Files e o
    uninstaller apagava. Em dev, continua no diretório do projeto."""
    if getattr(sys, 'frozen', False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "WaterIntakeTracker", "user_config.json")
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
        "goal_ml", "ml_per_gulp", "ml_per_glass", "ml_per_bottle",
        "notes_visible", "overlay_x", "overlay_y",
        "sound_enabled", "gulp_volume",
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

        self.setWindowTitle("Water Intake Tracker — Configurações")
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
            welcome = QLabel("Bem-vindo! Vamos configurar o app.")
            welcome.setAlignment(Qt.AlignCenter)
            welcome.setStyleSheet("color: #666; margin-bottom: 10px;")
            layout.addWidget(welcome)

        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "Geral")
        tabs.addTab(self._create_help_tab(), "Como usar")
        layout.addWidget(tabs)

        button_layout = QHBoxLayout()
        self.start_windows_check = QCheckBox("Iniciar com o Windows")
        self.start_windows_check.setChecked(is_startup_enabled())
        button_layout.addWidget(self.start_windows_check)
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Salvar && Iniciar" if self.first_run else "Salvar")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_accept)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px;")
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Daily goal
        goal_group = QGroupBox("Meta diária")
        goal_layout = QGridLayout(goal_group)

        goal_layout.addWidget(QLabel("Meta diária:"), 0, 0)
        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(500, 10000)
        self.goal_spin.setSingleStep(100)
        self.goal_spin.setSuffix(" ml")
        goal_layout.addWidget(self.goal_spin, 0, 1)

        layout.addWidget(goal_group)

        # Gulp amounts (main button + satellites)
        amounts_group = QGroupBox("Tamanhos de gole")
        amounts_layout = QGridLayout(amounts_group)

        amounts_layout.addWidget(QLabel("💧 Gole (botão principal):"), 0, 0)
        self.gulp_spin = QSpinBox()
        self.gulp_spin.setRange(25, 500)
        self.gulp_spin.setSingleStep(25)
        self.gulp_spin.setSuffix(" ml")
        amounts_layout.addWidget(self.gulp_spin, 0, 1)

        amounts_layout.addWidget(QLabel("🥤 Copo:"), 1, 0)
        self.glass_spin = QSpinBox()
        self.glass_spin.setRange(50, 1000)
        self.glass_spin.setSingleStep(50)
        self.glass_spin.setSuffix(" ml")
        amounts_layout.addWidget(self.glass_spin, 1, 1)

        amounts_layout.addWidget(QLabel("🍶 Garrafa:"), 2, 0)
        self.bottle_spin = QSpinBox()
        self.bottle_spin.setRange(100, 2000)
        self.bottle_spin.setSingleStep(50)
        self.bottle_spin.setSuffix(" ml")
        amounts_layout.addWidget(self.bottle_spin, 2, 1)

        layout.addWidget(amounts_group)

        # Sound (checkbox + volume slider)
        sound_group = QGroupBox("Som")
        sound_layout = QGridLayout(sound_group)

        self.sound_check = QCheckBox("Tocar som ao registrar gole")
        sound_layout.addWidget(self.sound_check, 0, 0, 1, 3)

        sound_layout.addWidget(QLabel("Volume:"), 1, 0)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        sound_layout.addWidget(self.volume_slider, 1, 1)

        self.volume_label = QLabel("50%")
        self.volume_label.setMinimumWidth(40)
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        # Preview: soltar o slider toca o som no volume escolhido — sem
        # isso calibrar exigia salvar, fechar e clicar no botão pra ouvir.
        self.volume_slider.sliderReleased.connect(self._preview_volume)
        self._preview_effect = None
        sound_layout.addWidget(self.volume_label, 1, 2)

        layout.addWidget(sound_group)

        layout.addStretch()
        return widget

    def _preview_volume(self):
        """Toca o gulp.wav no volume atual do slider."""
        sound_path = os.path.join(
            CONFIG.get("sounds_dir", "sounds"), CONFIG.get("gulp_sound", "gulp.wav")
        )
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(sys._MEIPASS, sound_path)
            if os.path.exists(bundled):
                sound_path = bundled
        if not os.path.exists(sound_path):
            return
        try:
            from PyQt5.QtMultimedia import QSoundEffect
            from PyQt5.QtCore import QUrl
            if self._preview_effect is None:
                self._preview_effect = QSoundEffect(self)
                self._preview_effect.setSource(
                    QUrl.fromLocalFile(os.path.abspath(sound_path))
                )
            self._preview_effect.setVolume(self.volume_slider.value() / 100.0)
            self._preview_effect.play()
        except Exception:
            try:
                import winsound
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    def _create_help_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml("""
        <h3>🚀 Como usar</h3>
        <p>O app é um botão circular no canto da tela. Clique nele toda vez
        que der um gole d'água — o anel ao redor mostra o progresso do dia
        e o número central conta os goles.</p>

        <h3>🛰️ Satélites (hover)</h3>
        <p>Passe o mouse sobre o botão para revelar os atalhos:</p>
        <ul>
            <li><b>💧 Gole:</b> registra o valor do botão principal</li>
            <li><b>🥤 Copo:</b> registra um copo (configurável)</li>
            <li><b>🍶 Garrafa:</b> registra uma garrafa (configurável)</li>
            <li><b>📝 Notas:</b> mostra/esconde a coluna de sticky notes</li>
        </ul>

        <h3>🏜️ O botão "seca"</h3>
        <p>Quanto mais tempo sem registrar um gole, mais o botão perde a cor
        — de azul vivo a cinza-seco em ~2h. É o lembrete silencioso: sem
        popup, sem som. Beber (e clicar) devolve a cor. Meta batida = botão
        vivo pelo resto do dia.</p>

        <h3>📝 Sticky notes</h3>
        <p>Coluna à esquerda do botão, com 3 prioridades (Agora / Hoje /
        Depois). Hover expande; "+" cria; clique num card edita; ✓ completa.</p>

        <h3>🖱️ Mouse</h3>
        <ul>
            <li><b>Clique no botão:</b> registra gole</li>
            <li><b>Arrastar área vazia:</b> move o overlay (posição é salva)</li>
            <li><b>Clique direito:</b> menu (estatísticas, desfazer, zerar,
                configurações, sair)</li>
        </ul>

        <h3>🔧 Bandeja do sistema</h3>
        <ul>
            <li><b>Clique simples:</b> mostra/esconde o overlay</li>
            <li><b>Clique duplo:</b> abre Configurações</li>
            <li><b>Clique direito:</b> menu de contexto</li>
        </ul>

        <h3>🎮 Gamificação</h3>
        <p>Cada gole vira XP; bater a meta rende bônus e estende a streak.
        Estatísticas e conquistas ficam no menu (📊 Estatísticas).</p>

        <h3>💾 Dados</h3>
        <p>No .exe instalado, tudo fica em
        <code>%APPDATA%\\WaterIntakeTracker</code> — sobrevive a atualizações
        e reinstalações. O dia reseta à meia-noite e o histórico diário é
        arquivado em <code>history.jsonl</code>.</p>
        """)
        layout.addWidget(help_text)

        return widget

    def _load_values(self):
        self.goal_spin.setValue(self.config.get("goal_ml", 3000))
        self.gulp_spin.setValue(self.config.get("ml_per_gulp", 100))
        self.glass_spin.setValue(self.config.get("ml_per_glass", 300))
        self.bottle_spin.setValue(self.config.get("ml_per_bottle", 500))

        self.sound_check.setChecked(self.config.get("sound_enabled", True))
        vol = int(self.config.get("gulp_volume", 50))
        self.volume_slider.setValue(vol)
        self.volume_label.setText(f"{vol}%")

    def _save_and_accept(self):
        self.config["goal_ml"] = self.goal_spin.value()
        self.config["ml_per_gulp"] = self.gulp_spin.value()
        self.config["ml_per_glass"] = self.glass_spin.value()
        self.config["ml_per_bottle"] = self.bottle_spin.value()
        self.config["sound_enabled"] = self.sound_check.isChecked()
        self.config["gulp_volume"] = self.volume_slider.value()
        self.config["first_run"] = False
        self.config["start_with_windows"] = self.start_windows_check.isChecked()

        if not save_user_config(self.config):
            QMessageBox.warning(
                self,
                "Erro ao salvar",
                "Não foi possível salvar o arquivo de configuração. "
                "As escolhas valem só para esta sessão."
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
