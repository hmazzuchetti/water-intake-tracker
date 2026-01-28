"""
Settings window for Water Intake Tracker
Shown on first run or when accessing settings from menu
"""

import sys
import os
import json
import winreg
import cv2
import glob
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QFrame, QMessageBox, QTabWidget, QWidget, QTextBrowser,
    QPlainTextEdit, QFileDialog, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap

from config import CONFIG


def get_config_path():
    """Get the path for the config file - writable location"""
    if getattr(sys, 'frozen', False):
        # Running as exe - use the directory where the exe is located
        return os.path.join(os.path.dirname(sys.executable), "user_config.json")
    else:
        # Running as script
        return "user_config.json"


CONFIG_FILE = get_config_path()
APP_NAME = "WaterIntakeTracker"


def enumerate_cameras(max_index=10):
    """Find available cameras and return list of (index, name) tuples"""
    available = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Try to get camera name (not always available on Windows)
            available.append((i, f"Camera {i}"))
            cap.release()
    return available


def test_camera(camera_index, timeout_ms=3000):
    """Test if a camera can be opened and read from. Returns (success, message)"""
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return False, f"Could not open camera {camera_index}"

        # Set a short timeout and try to read a frame
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Try to read a frame
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            return True, f"Camera {camera_index} is working"
        else:
            return False, f"Camera {camera_index} opened but could not read frame"
    except Exception as e:
        return False, f"Error testing camera: {e}"


def load_user_config() -> dict:
    """Load user configuration from file, merging with defaults"""
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
    """Save user configuration to file. Returns True on success."""
    # Only save user-configurable options
    saveable_keys = [
        "goal_ml", "ml_per_gulp", "bar_position", "bar_width",
        "detection_interval", "cooldown_seconds", "frames_to_confirm",
        "proximity_threshold", "drinking_hand", "sound_enabled",
        "camera_index", "away_timeout_seconds", "hover_opacity",
        "reminder_interval_minutes", "reminder_bar_width",
        "reminder_shake_threshold", "start_with_windows", "first_run",
        "require_cup",
        # AI and Mascot settings
        "ai_messages_enabled", "ai_ollama_model", "ai_message_interval_minutes",
        "ai_personality_file", "mascot_enabled", "mascot_file", "mascot_size"
    ]

    to_save = {k: config[k] for k in saveable_keys if k in config}
    config_path = get_config_path()

    try:
        # Ensure directory exists
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
    """Check if this is the first time running the app"""
    config = load_user_config()
    return config.get("first_run", True)


def set_startup_with_windows(enable: bool) -> bool:
    """Add or remove app from Windows startup. Returns True on success."""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        if enable:
            # Get the path to the current executable or script
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                app_path = f'"{sys.executable}"'
            else:
                # Running as script
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
                pass  # Key doesn't exist, that's fine
            except Exception:
                pass  # Ignore errors when removing

        return True
    except PermissionError as e:
        print(f"Permission denied setting startup (this is normal): {e}")
        return False
    except Exception as e:
        print(f"Error setting startup: {e}")
        return False


def is_startup_enabled() -> bool:
    """Check if app is set to start with Windows"""
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
    """Settings dialog for configuring the water tracker"""

    def __init__(self, parent=None, first_run=False):
        super().__init__(parent)
        self.first_run = first_run
        self.config = load_user_config()

        self.setWindowTitle("Water Intake Tracker - Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("💧 Water Intake Tracker")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        if self.first_run:
            welcome = QLabel("Welcome! Let's configure your settings.")
            welcome.setAlignment(Qt.AlignCenter)
            welcome.setStyleSheet("color: #666; margin-bottom: 10px;")
            layout.addWidget(welcome)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_detection_tab(), "Detection")
        tabs.addTab(self._create_reminder_tab(), "Reminder")
        tabs.addTab(self._create_mascot_tab(), "Mascote & IA")
        tabs.addTab(self._create_help_tab(), "How to Use")
        layout.addWidget(tabs)

        # Buttons
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
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Daily Goal Group
        goal_group = QGroupBox("Daily Goal")
        goal_layout = QGridLayout(goal_group)

        goal_layout.addWidget(QLabel("Target water intake:"), 0, 0)
        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(500, 10000)
        self.goal_spin.setSingleStep(100)
        self.goal_spin.setSuffix(" ml")
        goal_layout.addWidget(self.goal_spin, 0, 1)

        goal_layout.addWidget(QLabel("ML per detected gulp:"), 1, 0)
        self.gulp_spin = QSpinBox()
        self.gulp_spin.setRange(50, 500)
        self.gulp_spin.setSingleStep(25)
        self.gulp_spin.setSuffix(" ml")
        goal_layout.addWidget(self.gulp_spin, 1, 1)

        layout.addWidget(goal_group)

        # Appearance Group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QGridLayout(appearance_group)

        appearance_layout.addWidget(QLabel("Bar position:"), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Right", "Left"])
        appearance_layout.addWidget(self.position_combo, 0, 1)

        appearance_layout.addWidget(QLabel("Bar width:"), 1, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(20, 100)
        self.width_spin.setSuffix(" px")
        appearance_layout.addWidget(self.width_spin, 1, 1)

        appearance_layout.addWidget(QLabel("Hover opacity:"), 2, 0)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(5, 100)
        self.opacity_spin.setSuffix(" %")
        appearance_layout.addWidget(self.opacity_spin, 2, 1)

        layout.addWidget(appearance_group)

        # Sound
        self.sound_check = QCheckBox("Enable gulp sound")
        layout.addWidget(self.sound_check)

        layout.addStretch()
        return widget

    def _create_detection_tab(self) -> QWidget:
        """Create detection settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Camera Selection Group (moved to top - most important for setup)
        camera_group = QGroupBox("Camera Selection")
        camera_layout = QGridLayout(camera_group)

        camera_layout.addWidget(QLabel("Select webcam:"), 0, 0)
        self.camera_combo = QComboBox()
        camera_layout.addWidget(self.camera_combo, 0, 1)

        # Refresh and Test buttons
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_cameras)
        btn_layout.addWidget(self.refresh_btn)

        self.test_btn = QPushButton("Test Camera")
        self.test_btn.clicked.connect(self._test_camera)
        btn_layout.addWidget(self.test_btn)
        camera_layout.addLayout(btn_layout, 1, 0, 1, 2)

        # Status label - must be created before _populate_cameras()
        self.camera_status = QLabel("Scanning for cameras...")
        self.camera_status.setStyleSheet("color: #666; font-size: 11px;")
        camera_layout.addWidget(self.camera_status, 2, 0, 1, 2)

        # Now populate cameras (uses self.camera_status)
        self._populate_cameras()

        layout.addWidget(camera_group)

        # Hand Detection Group
        hand_group = QGroupBox("Hand Detection")
        hand_layout = QGridLayout(hand_group)

        hand_layout.addWidget(QLabel("Drinking hand:"), 0, 0)
        self.hand_combo = QComboBox()
        self.hand_combo.addItems(["Right", "Left", "Both"])
        hand_layout.addWidget(self.hand_combo, 0, 1)

        hand_note = QLabel("Select which hand you typically use to drink water")
        hand_note.setStyleSheet("color: #666; font-size: 11px;")
        hand_layout.addWidget(hand_note, 1, 0, 1, 2)

        layout.addWidget(hand_group)

        # Detection Settings Group
        detection_group = QGroupBox("Detection Settings")
        detection_layout = QGridLayout(detection_group)

        detection_layout.addWidget(QLabel("Cooldown between gulps:"), 0, 0)
        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setRange(3, 60)
        self.cooldown_spin.setSuffix(" seconds")
        detection_layout.addWidget(self.cooldown_spin, 0, 1)

        detection_layout.addWidget(QLabel("Away timeout:"), 1, 0)
        self.away_spin = QSpinBox()
        self.away_spin.setRange(3, 30)
        self.away_spin.setSuffix(" seconds")
        detection_layout.addWidget(self.away_spin, 1, 1)

        layout.addWidget(detection_group)

        # Cup Detection Group
        cup_group = QGroupBox("Cup/Bottle Detection")
        cup_layout = QVBoxLayout(cup_group)

        self.require_cup_check = QCheckBox("Require cup/bottle in hand to detect gulp")
        cup_layout.addWidget(self.require_cup_check)

        cup_note = QLabel(
            "💡 When enabled, a cup, bottle, or glass must be detected\n"
            "   in your hand to register a gulp. This reduces false positives\n"
            "   from touching your face, beard, or hair."
        )
        cup_note.setStyleSheet("color: #666; font-size: 11px;")
        cup_layout.addWidget(cup_note)

        layout.addWidget(cup_group)

        # Advanced note
        advanced_note = QLabel(
            "⚠️ Advanced: Detection sensitivity can be adjusted in config.py\n"
            "(proximity_threshold, frames_to_confirm)"
        )
        advanced_note.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(advanced_note)

        layout.addStretch()
        return widget

    def _create_reminder_tab(self) -> QWidget:
        """Create reminder settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Reminder Group
        reminder_group = QGroupBox("Drink Reminder")
        reminder_layout = QGridLayout(reminder_group)

        reminder_layout.addWidget(QLabel("Reminder interval:"), 0, 0)
        self.reminder_spin = QSpinBox()
        self.reminder_spin.setRange(5, 120)
        self.reminder_spin.setSuffix(" minutes")
        reminder_layout.addWidget(self.reminder_spin, 0, 1)

        reminder_layout.addWidget(QLabel("Reminder bar width:"), 1, 0)
        self.reminder_width_spin = QSpinBox()
        self.reminder_width_spin.setRange(5, 30)
        self.reminder_width_spin.setSuffix(" px")
        reminder_layout.addWidget(self.reminder_width_spin, 1, 1)

        layout.addWidget(reminder_group)

        # Explanation
        explanation = QLabel(
            "The reminder bar fills up over time:\n"
            "• Green (0-25%): All good\n"
            "• Yellow (25-50%): Consider drinking soon\n"
            "• Orange (50-75%): Time to drink!\n"
            "• Red (75-100%): Drink water now! (bar shakes)\n\n"
            "The bar resets when you drink water."
        )
        explanation.setStyleSheet("color: #555; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(explanation)

        layout.addStretch()
        return widget

    def _create_mascot_tab(self) -> QWidget:
        """Create mascot and AI settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # AI Messages Group
        ai_group = QGroupBox("Mensagens com IA")
        ai_layout = QGridLayout(ai_group)

        self.ai_enabled_check = QCheckBox("Habilitar mensagens com IA")
        ai_layout.addWidget(self.ai_enabled_check, 0, 0, 1, 2)

        ai_layout.addWidget(QLabel("Modelo Ollama:"), 1, 0)
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(True)
        self.ollama_model_combo.addItems([
            "llama3.2:1b",
            "llama3.2:3b",
            "llama3.1:latest",
            "mistral:latest",
            "phi3:mini",
            "gemma2:2b",
        ])
        ai_layout.addWidget(self.ollama_model_combo, 1, 1)

        ai_layout.addWidget(QLabel("Intervalo mensagens:"), 2, 0)
        self.ai_interval_spin = QSpinBox()
        self.ai_interval_spin.setRange(1, 120)
        self.ai_interval_spin.setSuffix(" min")
        ai_layout.addWidget(self.ai_interval_spin, 2, 1)

        layout.addWidget(ai_group)

        # Personality Group
        personality_group = QGroupBox("Personalidade")
        personality_layout = QVBoxLayout(personality_group)

        # Personality selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Personalidade:"))
        self.personality_combo = QComboBox()
        self._populate_personalities()
        self.personality_combo.currentIndexChanged.connect(self._on_personality_changed)
        selector_layout.addWidget(self.personality_combo, 1)

        self.new_personality_btn = QPushButton("Nova")
        self.new_personality_btn.setMaximumWidth(60)
        self.new_personality_btn.clicked.connect(self._create_new_personality)
        selector_layout.addWidget(self.new_personality_btn)
        personality_layout.addLayout(selector_layout)

        # Personality editor
        self.personality_edit = QPlainTextEdit()
        self.personality_edit.setPlaceholderText("Escreva as instruções de personalidade para a IA...")
        self.personality_edit.setMinimumHeight(120)
        self.personality_edit.setMaximumHeight(180)
        personality_layout.addWidget(self.personality_edit)

        # Save button
        save_personality_btn = QPushButton("💾 Salvar Personalidade")
        save_personality_btn.clicked.connect(self._save_personality)
        personality_layout.addWidget(save_personality_btn)

        layout.addWidget(personality_group)

        # Mascot Group
        mascot_group = QGroupBox("Mascote")
        mascot_layout = QGridLayout(mascot_group)

        self.mascot_enabled_check = QCheckBox("Mostrar mascote com mensagens")
        mascot_layout.addWidget(self.mascot_enabled_check, 0, 0, 1, 2)

        mascot_layout.addWidget(QLabel("Mascote atual:"), 1, 0)

        # Mascot preview and selector
        mascot_preview_layout = QHBoxLayout()

        self.mascot_preview = QLabel()
        self.mascot_preview.setFixedSize(80, 80)
        self.mascot_preview.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        self.mascot_preview.setAlignment(Qt.AlignCenter)
        mascot_preview_layout.addWidget(self.mascot_preview)

        mascot_buttons = QVBoxLayout()
        self.mascot_combo = QComboBox()
        self._populate_mascots()
        self.mascot_combo.currentIndexChanged.connect(self._on_mascot_changed)
        mascot_buttons.addWidget(self.mascot_combo)

        browse_mascot_btn = QPushButton("📁 Escolher arquivo...")
        browse_mascot_btn.clicked.connect(self._browse_mascot)
        mascot_buttons.addWidget(browse_mascot_btn)
        mascot_preview_layout.addLayout(mascot_buttons)
        mascot_preview_layout.addStretch()

        mascot_layout.addLayout(mascot_preview_layout, 1, 1)

        mascot_layout.addWidget(QLabel("Tamanho:"), 2, 0)
        self.mascot_size_spin = QSpinBox()
        self.mascot_size_spin.setRange(50, 400)
        self.mascot_size_spin.setSuffix(" px")
        mascot_layout.addWidget(self.mascot_size_spin, 2, 1)

        layout.addWidget(mascot_group)

        layout.addStretch()
        return widget

    def _populate_personalities(self):
        """Populate personality combo with available files"""
        self.personality_combo.clear()

        # Ensure directory exists
        os.makedirs("personalities", exist_ok=True)

        # Find all .txt files in personalities folder
        personality_files = glob.glob("personalities/*.txt")

        if not personality_files:
            # Create default if none exist
            self.personality_combo.addItem("default", "personalities/default.txt")
        else:
            for filepath in sorted(personality_files):
                name = os.path.splitext(os.path.basename(filepath))[0]
                display_name = name.replace("_", " ").title()
                self.personality_combo.addItem(display_name, filepath)

    def _on_personality_changed(self, index):
        """Load selected personality into editor"""
        filepath = self.personality_combo.currentData()
        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.personality_edit.setPlainText(f.read())
            except Exception as e:
                print(f"Erro ao carregar personalidade: {e}")

    def _create_new_personality(self):
        """Create a new personality file"""
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "Nova Personalidade",
            "Nome da personalidade (sem espaços ou acentos):"
        )

        if ok and name:
            # Sanitize name
            safe_name = "".join(c for c in name if c.isalnum() or c == "_").lower()
            if not safe_name:
                safe_name = "nova"

            filepath = f"personalities/{safe_name}.txt"

            # Check if exists
            if os.path.exists(filepath):
                QMessageBox.warning(self, "Erro", f"Já existe uma personalidade com esse nome!")
                return

            # Create file with template
            template = """Você é um assistente que ajuda o usuário a se manter hidratado.

ESTILO:
- Descreva o tom e estilo das mensagens aqui
- Seja breve (máximo 1-2 frases)
- Use emojis ocasionalmente

EXEMPLOS DE TOM:
- "Exemplo de mensagem 1"
- "Exemplo de mensagem 2"

IMPORTANTE:
- NÃO use formatação Markdown
- Retorne APENAS a mensagem, nada mais
- Máximo de 100 caracteres
"""
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(template)

                # Refresh combo and select new
                self._populate_personalities()
                for i in range(self.personality_combo.count()):
                    if self.personality_combo.itemData(i) == filepath:
                        self.personality_combo.setCurrentIndex(i)
                        break

                QMessageBox.information(self, "Sucesso", f"Personalidade '{safe_name}' criada!")

            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao criar arquivo: {e}")

    def _save_personality(self):
        """Save current personality text to file"""
        filepath = self.personality_combo.currentData()
        if not filepath:
            QMessageBox.warning(self, "Erro", "Nenhuma personalidade selecionada!")
            return

        text = self.personality_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Erro", "O texto da personalidade não pode estar vazio!")
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, "Salvo!", f"Personalidade salva em:\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar: {e}")

    def _populate_mascots(self):
        """Populate mascot combo with available images"""
        self.mascot_combo.clear()

        # Ensure directory exists
        os.makedirs("mascots", exist_ok=True)

        # Find image files
        mascot_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif']:
            mascot_files.extend(glob.glob(f"mascots/{ext}"))

        if not mascot_files:
            self.mascot_combo.addItem("(nenhum mascote)", "")
        else:
            for filepath in sorted(mascot_files):
                name = os.path.splitext(os.path.basename(filepath))[0]
                display_name = name.replace("_", " ").title()
                self.mascot_combo.addItem(display_name, filepath)

    def _on_mascot_changed(self, index):
        """Update mascot preview"""
        filepath = self.mascot_combo.currentData()
        self._update_mascot_preview(filepath)

    def _update_mascot_preview(self, filepath):
        """Update the mascot preview image"""
        if filepath and os.path.exists(filepath):
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    76, 76,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.mascot_preview.setPixmap(scaled)
                return

        self.mascot_preview.setText("🐸")
        self.mascot_preview.setStyleSheet(
            "border: 1px solid #ccc; background: #f5f5f5; font-size: 32px;"
        )

    def _browse_mascot(self):
        """Open file dialog to select custom mascot"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher Mascote",
            "mascots/",
            "Imagens (*.png *.jpg *.jpeg *.gif)"
        )

        if filepath:
            # Copy to mascots folder if not already there
            if not filepath.startswith("mascots"):
                import shutil
                filename = os.path.basename(filepath)
                dest = f"mascots/{filename}"
                try:
                    shutil.copy2(filepath, dest)
                    filepath = dest
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Erro ao copiar arquivo: {e}")
                    return

            # Refresh and select
            self._populate_mascots()
            for i in range(self.mascot_combo.count()):
                if self.mascot_combo.itemData(i) == filepath:
                    self.mascot_combo.setCurrentIndex(i)
                    break

    def _create_help_tab(self) -> QWidget:
        """Create help/tutorial tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setHtml("""
        <h3>🚀 Getting Started</h3>
        <p>The water tracker uses your webcam to detect when you drink water and tracks your daily intake.</p>

        <h3>📊 Main Bar (Blue)</h3>
        <p>Shows your daily water intake progress. Fills up as you drink.</p>

        <h3>⏰ Reminder Bar (Green→Red)</h3>
        <p>Shows time since your last drink. Changes color and shakes to remind you to drink.</p>

        <h3>🖱️ Mouse Controls</h3>
        <ul>
            <li><b>Right-click:</b> Open menu (add gulp, undo, settings, etc.)</li>
            <li><b>Double-click:</b> Undo last detected gulp</li>
            <li><b>Drag:</b> Move the bar to a different position</li>
            <li><b>Hover:</b> Bar becomes transparent to not block your view</li>
        </ul>

        <h3>🎯 Detection Tips</h3>
        <ul>
            <li>Make sure your webcam can see your face and hands</li>
            <li>Hold your cup/bottle normally when drinking</li>
            <li>The app detects the "drinking motion" - hand raised to mouth</li>
            <li>If false positives occur, enable "Require cup/bottle" in Detection settings</li>
            <li>The cup detection recognizes cups, bottles, and wine glasses</li>
        </ul>

        <h3>🌙 Away Mode</h3>
        <p>When you leave your desk, the bar turns gray and pauses tracking.
        It automatically resumes when you return.</p>

        <h3>💡 Tips</h3>
        <ul>
            <li>Double-click to quickly undo accidental detections</li>
            <li>Use "Reset reminder timer" if you drank without detection</li>
            <li>The reminder doesn't count time when you're away</li>
        </ul>
        """)
        layout.addWidget(help_text)

        return widget

    def _populate_cameras(self):
        """Populate the camera combo box with detected cameras"""
        self.camera_combo.clear()
        self.available_cameras = enumerate_cameras()

        if not self.available_cameras:
            self.camera_combo.addItem("No cameras detected", -1)
            self.camera_status.setText("⚠️ No cameras found. Please connect a webcam.")
            self.camera_status.setStyleSheet("color: #c00; font-size: 11px;")
        else:
            for cam_index, cam_name in self.available_cameras:
                self.camera_combo.addItem(cam_name, cam_index)
            self.camera_status.setText(f"✓ Found {len(self.available_cameras)} camera(s)")
            self.camera_status.setStyleSheet("color: #080; font-size: 11px;")

    def _refresh_cameras(self):
        """Refresh the camera list"""
        self.camera_status.setText("Scanning for cameras...")
        self.camera_status.setStyleSheet("color: #666; font-size: 11px;")
        QApplication.processEvents()  # Update UI
        self._populate_cameras()

        # Try to select the previously configured camera
        saved_index = self.config.get("camera_index", 0)
        for i in range(self.camera_combo.count()):
            if self.camera_combo.itemData(i) == saved_index:
                self.camera_combo.setCurrentIndex(i)
                break

    def _test_camera(self):
        """Test the currently selected camera"""
        camera_index = self.camera_combo.currentData()
        if camera_index is None or camera_index < 0:
            QMessageBox.warning(self, "No Camera", "No camera selected to test.")
            return

        self.camera_status.setText(f"Testing camera {camera_index}...")
        self.camera_status.setStyleSheet("color: #666; font-size: 11px;")
        self.test_btn.setEnabled(False)
        QApplication.processEvents()  # Update UI

        success, message = test_camera(camera_index)

        if success:
            self.camera_status.setText(f"✓ {message}")
            self.camera_status.setStyleSheet("color: #080; font-size: 11px;")
            QMessageBox.information(self, "Camera Test", f"Success!\n\n{message}")
        else:
            self.camera_status.setText(f"✗ {message}")
            self.camera_status.setStyleSheet("color: #c00; font-size: 11px;")
            QMessageBox.warning(self, "Camera Test Failed", f"{message}\n\nTry selecting a different camera or check your webcam connection.")

        self.test_btn.setEnabled(True)

    def _load_values(self):
        """Load current config values into UI"""
        self.goal_spin.setValue(self.config.get("goal_ml", 3000))
        self.gulp_spin.setValue(self.config.get("ml_per_gulp", 100))

        position = self.config.get("bar_position", "right").lower()
        self.position_combo.setCurrentIndex(0 if position == "right" else 1)

        self.width_spin.setValue(self.config.get("bar_width", 30))
        self.opacity_spin.setValue(int(self.config.get("hover_opacity", 0.15) * 100))
        self.sound_check.setChecked(self.config.get("sound_enabled", True))

        hand = self.config.get("drinking_hand", "right").lower()
        hand_index = {"right": 0, "left": 1, "both": 2}.get(hand, 0)
        self.hand_combo.setCurrentIndex(hand_index)

        self.cooldown_spin.setValue(self.config.get("cooldown_seconds", 10))
        self.away_spin.setValue(self.config.get("away_timeout_seconds", 5))

        # Set camera combo to saved value
        saved_camera = self.config.get("camera_index", 0)
        for i in range(self.camera_combo.count()):
            if self.camera_combo.itemData(i) == saved_camera:
                self.camera_combo.setCurrentIndex(i)
                break

        self.reminder_spin.setValue(self.config.get("reminder_interval_minutes", 30))
        self.reminder_width_spin.setValue(self.config.get("reminder_bar_width", 10))

        self.require_cup_check.setChecked(self.config.get("require_cup", True))

        # AI and Mascot settings
        self.ai_enabled_check.setChecked(self.config.get("ai_messages_enabled", True))
        self.ai_interval_spin.setValue(self.config.get("ai_message_interval_minutes", 45))
        self.mascot_enabled_check.setChecked(self.config.get("mascot_enabled", True))
        self.mascot_size_spin.setValue(self.config.get("mascot_size", 150))

        # Set Ollama model
        model = self.config.get("ai_ollama_model", "llama3.2:1b")
        idx = self.ollama_model_combo.findText(model)
        if idx >= 0:
            self.ollama_model_combo.setCurrentIndex(idx)
        else:
            self.ollama_model_combo.setCurrentText(model)

        # Set personality
        personality_file = self.config.get("ai_personality_file", "personalities/default.txt")
        for i in range(self.personality_combo.count()):
            if self.personality_combo.itemData(i) == personality_file:
                self.personality_combo.setCurrentIndex(i)
                break
        self._on_personality_changed(0)  # Load text

        # Set mascot
        mascot_file = self.config.get("mascot_file", "mascots/default.png")
        for i in range(self.mascot_combo.count()):
            if self.mascot_combo.itemData(i) == mascot_file:
                self.mascot_combo.setCurrentIndex(i)
                break
        self._update_mascot_preview(mascot_file)

    def _save_and_accept(self):
        """Save settings and close dialog"""
        # Validate camera selection
        camera_index = self.camera_combo.currentData()
        if camera_index is None or camera_index < 0:
            reply = QMessageBox.warning(
                self,
                "No Camera Selected",
                "No camera is selected. The app requires a webcam to work.\n\nDo you want to continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Update config
        self.config["goal_ml"] = self.goal_spin.value()
        self.config["ml_per_gulp"] = self.gulp_spin.value()
        self.config["bar_position"] = "right" if self.position_combo.currentIndex() == 0 else "left"
        self.config["bar_width"] = self.width_spin.value()
        self.config["hover_opacity"] = self.opacity_spin.value() / 100.0
        self.config["sound_enabled"] = self.sound_check.isChecked()

        hand_options = ["right", "left", "both"]
        self.config["drinking_hand"] = hand_options[self.hand_combo.currentIndex()]

        self.config["cooldown_seconds"] = self.cooldown_spin.value()
        self.config["away_timeout_seconds"] = self.away_spin.value()
        self.config["camera_index"] = camera_index if camera_index is not None and camera_index >= 0 else 0

        self.config["reminder_interval_minutes"] = self.reminder_spin.value()
        self.config["reminder_bar_width"] = self.reminder_width_spin.value()

        self.config["require_cup"] = self.require_cup_check.isChecked()

        # AI and Mascot settings
        self.config["ai_messages_enabled"] = self.ai_enabled_check.isChecked()
        self.config["ai_ollama_model"] = self.ollama_model_combo.currentText()
        self.config["ai_message_interval_minutes"] = self.ai_interval_spin.value()
        self.config["ai_personality_file"] = self.personality_combo.currentData() or "personalities/default.txt"
        self.config["mascot_enabled"] = self.mascot_enabled_check.isChecked()
        self.config["mascot_file"] = self.mascot_combo.currentData() or "mascots/default.png"
        self.config["mascot_size"] = self.mascot_size_spin.value()

        self.config["first_run"] = False
        self.config["start_with_windows"] = self.start_windows_check.isChecked()

        # Save to file
        if not save_user_config(self.config):
            QMessageBox.warning(
                self,
                "Save Error",
                "Could not save configuration file. Settings will be used for this session only."
            )

        # Set Windows startup (don't fail on error)
        try:
            set_startup_with_windows(self.start_windows_check.isChecked())
        except Exception as e:
            print(f"Could not set startup option: {e}")

        self.accept()

    def get_config(self) -> dict:
        """Get the current configuration"""
        return self.config


def show_settings(parent=None, first_run=False) -> dict:
    """Show settings dialog and return config if accepted"""
    dialog = SettingsDialog(parent, first_run)

    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_config()

    return None


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Test the settings dialog
    config = show_settings(first_run=True)

    if config:
        print("Settings saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print("Settings cancelled")
