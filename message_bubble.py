"""
Message Bubble Widget - Floating message display with mascot
Shows AI-generated messages with an animated mascot character
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QPoint
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFont, QPen, QPixmap

from config import CONFIG


class MessageBubble(QWidget):
    """
    Floating message bubble with animated mascot
    Mascot slides in from the side, message fades in, then both slide out
    """

    closed = pyqtSignal()  # Emitted when bubble closes

    def __init__(self, message: str, duration_ms: int = 8000, message_type: str = "normal"):
        super().__init__()
        self.message = message
        self.duration_ms = duration_ms
        self.message_type = message_type  # "celebration", "achievement", "reminder", "normal", "funny"

        # Visual settings
        self.padding = 20
        self.max_width = 600
        self.min_width = 250
        self.spacing = 15  # Space between mascot and bubble

        # Mascot settings
        self.mascot_enabled = CONFIG.get("mascot_enabled", True)
        self.mascot_size = CONFIG.get("mascot_size", 150)
        self.mascot_file = CONFIG.get("mascot_file", "mascots/default.png")
        self.mascot_pixmap = None

        # Load mascot
        if self.mascot_enabled:
            self._load_mascot()

        self._setup_window()
        self._setup_ui()
        self._setup_animations()

    def _load_mascot(self):
        """Load mascot image"""
        if os.path.exists(self.mascot_file):
            pixmap = QPixmap(self.mascot_file)
            if not pixmap.isNull():
                # Scale to max size while maintaining aspect ratio
                self.mascot_pixmap = pixmap.scaled(
                    self.mascot_size,
                    self.mascot_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            else:
                print(f"[Mascot] Erro ao carregar imagem: {self.mascot_file}")
        else:
            print(f"[Mascot] Arquivo não encontrado: {self.mascot_file}")
            print(f"[Mascot] Coloque uma imagem PNG em: {self.mascot_file}")

    def _setup_window(self):
        """Configure window properties"""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

    def _setup_ui(self):
        """Setup the message label and mascot"""
        # Calculate bubble size
        font = QFont("Segoe UI", 10)
        font.setBold(False)

        self.label = QLabel(self.message, self)
        self.label.setFont(font)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setStyleSheet("color: white; background: transparent;")

        # Calculate text size
        available_width = self.max_width - 2 * self.padding
        self.label.setMaximumWidth(available_width)
        self.label.setMinimumWidth(self.min_width - 2 * self.padding)
        self.label.adjustSize()

        # Bubble dimensions
        self.bubble_width = self.label.width() + 2 * self.padding
        self.bubble_height = self.label.height() + 2 * self.padding + 10

        # Total widget size (bubble + mascot if enabled)
        if self.mascot_enabled and self.mascot_pixmap:
            mascot_width = self.mascot_pixmap.width()
            mascot_height = self.mascot_pixmap.height()

            # Widget width = mascot + spacing + bubble
            total_width = mascot_width + self.spacing + self.bubble_width
            total_height = max(mascot_height, self.bubble_height)

            self.setFixedSize(total_width, total_height)

            # Position mascot (left side) and bubble (right side)
            self.mascot_x = 0
            self.mascot_y = (total_height - mascot_height) // 2

            bubble_x = mascot_width + self.spacing
            bubble_y = (total_height - self.bubble_height) // 2

            # Position label inside bubble area
            self.bubble_x = bubble_x
            self.bubble_y = bubble_y
            self.label.move(bubble_x + self.padding, bubble_y + self.padding)

        else:
            # No mascot - just bubble
            self.setFixedSize(self.bubble_width, self.bubble_height)
            self.bubble_x = 0
            self.bubble_y = 0
            self.label.move(self.padding, self.padding)

        # Position window on screen (starts off-screen for animation)
        self._position_window_offscreen()

    def _position_window_offscreen(self):
        """Position bubble off-screen (right side) for slide-in animation"""
        screen = QApplication.primaryScreen().geometry()

        # Final position (on-screen)
        margin = 50
        bar_width = 50

        self.final_x = max(10, screen.width() - self.width() - margin - bar_width)
        self.final_y = max(10, screen.height() - self.height() - margin)

        # Start position (off-screen to the right)
        self.start_x = screen.width()  # Completely off-screen
        self.start_y = self.final_y

        # Set initial position
        self.move(self.start_x, self.start_y)

    def _setup_animations(self):
        """Setup slide and fade animations"""
        # Slide in animation (from right to final position)
        self.slide_in_animation = QPropertyAnimation(self, b"pos")
        self.slide_in_animation.setDuration(600)
        self.slide_in_animation.setStartValue(QPoint(self.start_x, self.start_y))
        self.slide_in_animation.setEndValue(QPoint(self.final_x, self.final_y))
        self.slide_in_animation.setEasingCurve(QEasingCurve.OutBack)  # Bouncy effect

        # Fade in animation (opacity)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(400)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Slide out animation (from final position to right off-screen)
        self.slide_out_animation = QPropertyAnimation(self, b"pos")
        self.slide_out_animation.setDuration(500)
        self.slide_out_animation.setStartValue(QPoint(self.final_x, self.final_y))
        self.slide_out_animation.setEndValue(QPoint(self.start_x, self.start_y))
        self.slide_out_animation.setEasingCurve(QEasingCurve.InBack)

        # Fade out animation
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(400)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Connect fade out completion to close
        self.slide_out_animation.finished.connect(self._on_animation_finished)

        # Auto-close timer
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.start_slide_out)

    def show_animated(self):
        """Show with slide-in and fade-in animations"""
        self.show()

        # Play sound
        self._play_mascot_sound()

        # Start animations simultaneously
        self.slide_in_animation.start()
        self.fade_in_animation.start()

        # Start close timer
        self.close_timer.start(self.duration_ms)

    def start_slide_out(self):
        """Start slide-out and fade-out animations"""
        self.slide_out_animation.start()
        self.fade_out_animation.start()

    def _on_animation_finished(self):
        """Handle animation completion"""
        self.close()
        self.closed.emit()

    def _play_mascot_sound(self):
        """Play sound based on message type"""
        sounds_dir = CONFIG.get("sounds_dir", "sounds")

        # Map message type to sound file
        sound_map = {
            "celebration": CONFIG.get("sound_celebration", "celebration.wav"),
            "achievement": CONFIG.get("sound_achievement", "achievement.wav"),
            "reminder": CONFIG.get("sound_reminder", "reminder.wav"),
            "funny": CONFIG.get("sound_funny", "funny.wav"),
            "normal": CONFIG.get("sound_normal", "pop.wav"),
        }

        sound_file = sound_map.get(self.message_type, CONFIG.get("mascot_sound", "pop.wav"))
        sound_path = os.path.join(sounds_dir, sound_file)

        if not os.path.exists(sound_path):
            # Fallback to pop.wav
            sound_path = os.path.join(sounds_dir, "pop.wav")
            if not os.path.exists(sound_path):
                return  # No sound file, skip

        try:
            import winsound
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            pass  # Silently fail if sound doesn't work

    def paintEvent(self, event):
        """Draw mascot and bubble"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw mascot
        if self.mascot_enabled and self.mascot_pixmap:
            painter.drawPixmap(self.mascot_x, self.mascot_y, self.mascot_pixmap)

        # Draw bubble
        self._draw_bubble(painter)

    def _draw_bubble(self, painter):
        """Draw the speech bubble"""
        bubble_rect = QRect(
            self.bubble_x + 4,
            self.bubble_y + 4,
            self.bubble_width - 8,
            self.bubble_height - 8
        )

        # Shadow
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(
            bubble_rect.x() + 2,
            bubble_rect.y() + 2,
            bubble_rect.width(),
            bubble_rect.height(),
            15, 15
        )
        painter.fillPath(shadow_path, QColor(0, 0, 0, 80))

        # Main bubble
        bubble_path = QPainterPath()
        bubble_path.addRoundedRect(
            bubble_rect.x(),
            bubble_rect.y(),
            bubble_rect.width(),
            bubble_rect.height(),
            15, 15
        )

        # Background
        painter.fillPath(bubble_path, QColor(30, 100, 180, 230))

        # Border
        painter.setPen(QPen(QColor(100, 180, 255, 180), 2))
        painter.drawPath(bubble_path)

        # Draw speech bubble pointer (pointing to mascot if enabled)
        if self.mascot_enabled and self.mascot_pixmap:
            self._draw_bubble_pointer(painter, bubble_rect)

    def _draw_bubble_pointer(self, painter, bubble_rect):
        """Draw the triangular pointer from bubble to mascot"""
        # Triangle pointing left toward mascot
        pointer = QPainterPath()

        # Start point (left side of bubble, middle)
        start_x = bubble_rect.x()
        start_y = bubble_rect.y() + bubble_rect.height() // 2

        # Triangle points
        pointer.moveTo(start_x, start_y - 10)
        pointer.lineTo(start_x - 15, start_y)
        pointer.lineTo(start_x, start_y + 10)
        pointer.closeSubpath()

        # Fill and draw
        painter.fillPath(pointer, QColor(30, 100, 180, 230))
        painter.setPen(QPen(QColor(100, 180, 255, 180), 2))
        painter.drawPath(pointer)

    def mousePressEvent(self, event):
        """Click to dismiss"""
        if event.button() == Qt.LeftButton:
            self.start_slide_out()
            event.accept()


class MessageBubbleManager:
    """
    Manages showing message bubbles
    Ensures only one bubble is shown at a time
    """

    def __init__(self):
        self.current_bubble = None

    def show_message(self, message: str, duration_ms: int = 8000, message_type: str = "normal"):
        """
        Show a message bubble with mascot

        Args:
            message: Message text to display
            duration_ms: How long to show the message (default 8 seconds)
            message_type: Type of message for sound selection
                         ("celebration", "achievement", "reminder", "normal", "funny")
        """
        # Close existing bubble if any
        if self.current_bubble is not None:
            try:
                self.current_bubble.close()
            except:
                pass

        # Create and show new bubble
        self.current_bubble = MessageBubble(message, duration_ms, message_type)
        self.current_bubble.closed.connect(self._on_bubble_closed)
        self.current_bubble.show_animated()

    def _on_bubble_closed(self):
        """Handle bubble closure"""
        self.current_bubble = None

    def has_active_bubble(self) -> bool:
        """Check if there's a bubble currently showing"""
        return self.current_bubble is not None


def test_bubble():
    """Test the message bubble with mascot"""
    app = QApplication(sys.argv)

    manager = MessageBubbleManager()

    # Test messages
    messages = [
        "Bora começar o dia hidratado! 💧",
        "Seus rins agradecem essa hidratação 🎉",
        "Vai morrer desidratado em... brincadeira, bebe água aí! Seus rins vão gostar muito 😄",
        "META BATIDA! Você é incrível! 🏆 Continue assim e vai virar uma fonte ambulante!",
    ]

    print("=" * 60)
    print("TESTE DO BALÃO COM MASCOTE")
    print("=" * 60)
    print(f"Mascot habilitado: {CONFIG.get('mascot_enabled', True)}")
    print(f"Mascot arquivo: {CONFIG.get('mascot_file', 'mascots/default.png')}")
    print()
    print("Mostrando balões de teste...")
    print("Clique no balão para fechá-lo")
    print("=" * 60)

    # Show messages in sequence
    current_msg = [0]

    def show_next():
        if current_msg[0] < len(messages):
            print(f"\n[{current_msg[0] + 1}/{len(messages)}] Mostrando: {messages[current_msg[0]]}")
            manager.show_message(messages[current_msg[0]], duration_ms=4000)
            current_msg[0] += 1

            # Schedule next message
            if current_msg[0] < len(messages):
                QTimer.singleShot(5000, show_next)
        else:
            print("\n" + "=" * 60)
            print("✅ TESTE CONCLUÍDO!")
            print("=" * 60)
            QTimer.singleShot(5000, app.quit)

    # Start showing messages
    QTimer.singleShot(500, show_next)

    sys.exit(app.exec_())


if __name__ == "__main__":
    test_bubble()
