"""
Overlay progress bar UI for Water Intake Tracker
Water-like visual with waves and bubbles
Includes reminder bar that fills over time
"""

import sys
import math
import random
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QAction, QToolTip
)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QFont,
    QBrush, QPainterPath, QRadialGradient
)

from config import CONFIG
from storage import Storage


class Bubble:
    """A single animated bubble"""
    def __init__(self, width, start_y):
        self.x = random.randint(5, width - 5)
        self.y = start_y
        self.size = random.randint(3, 8)
        self.speed = random.uniform(0.5, 2.0)
        self.wobble_offset = random.uniform(0, math.pi * 2)
        self.wobble_speed = random.uniform(0.05, 0.15)

    def update(self, min_y):
        """Move bubble up and wobble"""
        self.y -= self.speed
        self.wobble_offset += self.wobble_speed
        return self.y > min_y

    def get_x(self):
        """Get x position with wobble"""
        return self.x + math.sin(self.wobble_offset) * 3


class ProgressBarOverlay(QWidget):
    """Transparent overlay widget showing water intake progress"""

    # Signals
    gulp_detected = pyqtSignal()
    away_status_changed = pyqtSignal(bool)
    settings_requested = pyqtSignal()

    def __init__(self, storage: Storage = None):
        super().__init__()
        self.storage = storage or Storage()
        self.dragging = False
        self.drag_position = QPoint()

        # Animation state
        self.wave_offset = 0
        self.bubbles = []
        self.max_bubbles = 8
        self.animation_tick = 0

        # Away mode state
        self.is_away = False

        # Hover state
        self.is_hovered = False
        self.hover_opacity = CONFIG.get("hover_opacity", 0.15)
        self.normal_opacity = 1.0
        self.current_opacity = 1.0

        # Reminder bar state
        self.last_gulp_time = time.time()
        self.reminder_interval = CONFIG.get("reminder_interval_minutes", 30) * 60  # Convert to seconds
        self.reminder_bar_width = CONFIG.get("reminder_bar_width", 10)
        self.shake_threshold = CONFIG.get("reminder_shake_threshold", 0.25)
        self.shake_offset = 0

        self._setup_window()
        self._setup_geometry()
        self._connect_signals()
        self._setup_animation()

    def _setup_window(self):
        """Configure window properties"""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

    def _setup_geometry(self):
        """Set window size and position"""
        screen = QApplication.primaryScreen().geometry()
        bar_width = CONFIG["bar_width"]
        margin = CONFIG["bar_margin"]

        # Add space for reminder bar
        total_width = bar_width + self.reminder_bar_width + 2  # 2px gap

        self.bar_height = screen.height() - 2 * margin
        self.main_bar_width = bar_width

        if CONFIG["bar_position"] == "right":
            x = screen.width() - total_width - margin
        else:
            x = margin

        self.setGeometry(x, margin, total_width, self.bar_height)

    def _connect_signals(self):
        """Connect internal signals"""
        self.gulp_detected.connect(self._on_gulp_detected)
        self.away_status_changed.connect(self._on_away_status_changed)

    def _setup_animation(self):
        """Setup animation timer"""
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate)
        self.animation_timer.start(50)  # 20 FPS

    def _get_reminder_percentage(self) -> float:
        """Get reminder bar fill percentage (0-100)"""
        if self.is_away:
            return 0  # Don't count time when away

        elapsed = time.time() - self.last_gulp_time
        percentage = min(100, (elapsed / self.reminder_interval) * 100)
        return percentage

    def _animate(self):
        """Update animation state"""
        self.animation_tick += 1

        # Calculate shake for reminder bar
        reminder_pct = self._get_reminder_percentage()
        if reminder_pct >= self.shake_threshold * 100:
            # Shake intensity increases from threshold to 100%
            intensity_range = 100 - (self.shake_threshold * 100)
            intensity = (reminder_pct - self.shake_threshold * 100) / intensity_range

            # Shake frequency and amplitude increase with intensity
            shake_speed = 0.3 + intensity * 0.5
            shake_amplitude = 1 + intensity * 4

            self.shake_offset = math.sin(self.animation_tick * shake_speed) * shake_amplitude
        else:
            self.shake_offset = 0

        # Don't animate bubbles when away
        if self.is_away:
            self.update()
            return

        # Wave animation
        self.wave_offset += 0.15

        # Get current water level
        ml_total, goal_ml, percentage = self.storage.get_progress()
        height = self.height()
        progress_height = int((percentage / 100) * height)
        water_top = height - progress_height

        # Update bubbles
        self.bubbles = [b for b in self.bubbles if b.update(water_top)]

        # Spawn new bubbles
        if len(self.bubbles) < self.max_bubbles and progress_height > 20:
            if random.random() < 0.1:
                self.bubbles.append(Bubble(self.main_bar_width, height - 10))

        self.update()

    def reset_reminder(self):
        """Reset the reminder timer"""
        self.last_gulp_time = time.time()

    def set_away(self, is_away: bool):
        """Set away status"""
        if self.is_away != is_away:
            self.is_away = is_away
            self.away_status_changed.emit(is_away)

    def _on_away_status_changed(self, is_away: bool):
        """Handle away status change"""
        self.is_away = is_away
        if is_away:
            self.bubbles.clear()
        self.update()

    def _on_gulp_detected(self):
        """Handle gulp detection"""
        # Reset reminder timer
        self.reset_reminder()

        # Add bubbles
        for _ in range(5):
            self.bubbles.append(Bubble(self.main_bar_width, self.height() - 10))
        self.update()

    def paintEvent(self, event):
        """Draw everything"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self.current_opacity)

        total_width = self.width()
        height = self.height()

        # Draw reminder bar on the left
        self._draw_reminder_bar(painter, height)

        # Draw main water bar on the right
        painter.save()
        painter.translate(self.reminder_bar_width + 2, 0)
        self._draw_main_bar(painter, self.main_bar_width, height)
        painter.restore()

    def _get_reminder_color(self, percentage: float) -> QColor:
        """Get color for reminder bar based on percentage"""
        if percentage < 25:
            # Green
            return QColor(76, 175, 80)
        elif percentage < 50:
            # Green to Yellow
            ratio = (percentage - 25) / 25
            return QColor(
                int(76 + (255 - 76) * ratio),
                int(175 + (235 - 175) * ratio),
                int(80 - 80 * ratio)
            )
        elif percentage < 75:
            # Yellow to Orange
            ratio = (percentage - 50) / 25
            return QColor(
                255,
                int(235 - (235 - 152) * ratio),
                0
            )
        else:
            # Orange to Red
            ratio = (percentage - 75) / 25
            return QColor(
                255,
                int(152 - 152 * ratio),
                0
            )

    def _draw_reminder_bar(self, painter, height):
        """Draw the reminder/timer bar"""
        width = self.reminder_bar_width
        percentage = self._get_reminder_percentage()

        # Apply shake offset
        painter.save()
        painter.translate(self.shake_offset, 0)

        # Background
        bg_color = QColor(30, 30, 30, 200)
        painter.fillRect(0, 0, width, height, bg_color)

        if percentage > 0:
            # Fill height (from bottom)
            fill_height = int((percentage / 100) * height)
            fill_y = height - fill_height

            # Create gradient based on urgency
            fill_gradient = QLinearGradient(0, fill_y, 0, height)

            # Top color (current urgency level)
            top_color = self._get_reminder_color(percentage)

            # Bottom is always green (where we started)
            fill_gradient.setColorAt(0, top_color)
            fill_gradient.setColorAt(0.3, self._get_reminder_color(percentage * 0.7))
            fill_gradient.setColorAt(0.6, self._get_reminder_color(percentage * 0.4))
            fill_gradient.setColorAt(1, self._get_reminder_color(0))

            painter.fillRect(0, fill_y, width, fill_height, fill_gradient)

            # Pulsing glow effect when urgent (>75%)
            if percentage >= 75:
                pulse = (math.sin(self.animation_tick * 0.2) + 1) / 2  # 0 to 1
                glow_alpha = int(50 + pulse * 100)

                glow_color = QColor(255, 50, 0, glow_alpha)
                painter.fillRect(0, fill_y, width, min(50, fill_height), glow_color)

            # Warning icon at 100%
            if percentage >= 100:
                # Draw exclamation mark
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setFont(QFont("Arial", 12, QFont.Bold))

                # Pulsing exclamation
                pulse = (math.sin(self.animation_tick * 0.3) + 1) / 2
                painter.setOpacity(0.7 + pulse * 0.3)

                # Draw multiple exclamation marks vertically
                for y_pos in range(30, height - 30, 60):
                    painter.drawText(QRectF(0, y_pos, width, 20), Qt.AlignCenter, "!")

                painter.setOpacity(self.current_opacity)

        # Border
        border_color = self._get_reminder_color(percentage) if percentage > 50 else QColor(80, 80, 80)
        border_color.setAlpha(150)
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(0, 0, width - 1, height - 1)

        # Time remaining text (rotated, shown at bottom)
        remaining_seconds = max(0, self.reminder_interval - (time.time() - self.last_gulp_time))
        remaining_minutes = int(remaining_seconds // 60)
        remaining_secs = int(remaining_seconds % 60)

        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setFont(QFont("Arial", 7))
        painter.save()
        painter.translate(width / 2, height - 10)
        painter.rotate(-90)
        time_text = f"{remaining_minutes}:{remaining_secs:02d}"
        painter.drawText(-20, 3, time_text)
        painter.restore()

        painter.restore()  # Restore from shake transform

    def _draw_main_bar(self, painter, width, height):
        """Draw the main water progress bar"""
        ml_total, goal_ml, percentage = self.storage.get_progress()

        if self.is_away:
            self._draw_away_mode(painter, width, height, percentage)
        else:
            self._draw_normal_mode(painter, width, height, percentage)

        # Markers
        pen = QPen(QColor(255, 255, 255, 60))
        pen.setWidth(1)
        painter.setPen(pen)

        markers_ml = 500
        num_markers = int(goal_ml / markers_ml)

        for i in range(1, num_markers):
            marker_percentage = (i * markers_ml / goal_ml) * 100
            marker_y = height - int((marker_percentage / 100) * height)
            painter.drawLine(5, marker_y, width - 5, marker_y)

        # Glass edge highlight
        edge_gradient = QLinearGradient(0, 0, 8, 0)
        edge_gradient.setColorAt(0, QColor(255, 255, 255, 50))
        edge_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(0, 0, 8, height, edge_gradient)

        # Border
        border_color = QColor(80, 80, 80, 150) if self.is_away else QColor(100, 150, 180, 150)
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(0, 0, width - 1, height - 1)

        # Away indicator
        if self.is_away:
            painter.setPen(QPen(QColor(150, 150, 150)))
            painter.setFont(QFont("Arial", 8))
            painter.save()
            painter.translate(width / 2, height / 2)
            painter.rotate(-90)
            painter.drawText(-20, 4, "AWAY")
            painter.restore()

    def _draw_away_mode(self, painter, width, height, percentage):
        """Draw grey bar when away"""
        glass_gradient = QLinearGradient(0, 0, width, 0)
        glass_gradient.setColorAt(0, QColor(30, 30, 30, 200))
        glass_gradient.setColorAt(0.3, QColor(40, 40, 40, 180))
        glass_gradient.setColorAt(0.7, QColor(40, 40, 40, 180))
        glass_gradient.setColorAt(1, QColor(30, 30, 30, 200))
        painter.fillRect(0, 0, width, height, glass_gradient)

        if percentage > 0:
            progress_height = int((percentage / 100) * height)
            water_top = height - progress_height

            grey_gradient = QLinearGradient(0, water_top, 0, height)
            grey_gradient.setColorAt(0, QColor(100, 100, 100, 180))
            grey_gradient.setColorAt(0.5, QColor(80, 80, 80, 190))
            grey_gradient.setColorAt(1, QColor(60, 60, 60, 200))

            painter.fillRect(0, water_top, width, progress_height, grey_gradient)

    def _draw_normal_mode(self, painter, width, height, percentage):
        """Draw normal blue water"""
        glass_gradient = QLinearGradient(0, 0, width, 0)
        glass_gradient.setColorAt(0, QColor(20, 30, 40, 200))
        glass_gradient.setColorAt(0.3, QColor(30, 40, 50, 180))
        glass_gradient.setColorAt(0.7, QColor(30, 40, 50, 180))
        glass_gradient.setColorAt(1, QColor(20, 30, 40, 200))
        painter.fillRect(0, 0, width, height, glass_gradient)

        if percentage > 0:
            progress_height = int((percentage / 100) * height)
            water_top = height - progress_height

            water_path = QPainterPath()
            water_path.moveTo(0, height)

            wave_height = 6
            wave_frequency = 0.15

            water_path.lineTo(0, water_top + wave_height)

            for x in range(0, width + 1, 2):
                wave_y = water_top + math.sin(x * wave_frequency + self.wave_offset) * wave_height
                water_path.lineTo(x, wave_y)

            water_path.lineTo(width, height)
            water_path.closeSubpath()

            water_gradient = QLinearGradient(0, water_top, 0, height)
            water_gradient.setColorAt(0, QColor(100, 180, 255, 220))
            water_gradient.setColorAt(0.3, QColor(50, 140, 220, 230))
            water_gradient.setColorAt(0.7, QColor(30, 100, 180, 240))
            water_gradient.setColorAt(1, QColor(20, 70, 140, 250))

            painter.fillPath(water_path, water_gradient)

            # Highlight
            highlight_path = QPainterPath()
            highlight_path.moveTo(3, water_top + wave_height + 5)
            for x in range(3, width - 3, 2):
                wave_y = water_top + math.sin(x * wave_frequency + self.wave_offset) * wave_height + 3
                highlight_path.lineTo(x, wave_y)
            highlight_path.lineTo(width - 3, water_top + wave_height + 15)
            highlight_path.lineTo(3, water_top + wave_height + 15)
            highlight_path.closeSubpath()

            highlight_gradient = QLinearGradient(0, water_top, 0, water_top + 20)
            highlight_gradient.setColorAt(0, QColor(255, 255, 255, 80))
            highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillPath(highlight_path, highlight_gradient)

            # Bubbles
            for bubble in self.bubbles:
                if bubble.y > water_top:
                    bx = bubble.get_x()
                    by = bubble.y

                    bubble_gradient = QRadialGradient(
                        bx - bubble.size * 0.3,
                        by - bubble.size * 0.3,
                        bubble.size
                    )
                    bubble_gradient.setColorAt(0, QColor(255, 255, 255, 180))
                    bubble_gradient.setColorAt(0.5, QColor(150, 200, 255, 100))
                    bubble_gradient.setColorAt(1, QColor(100, 150, 220, 50))

                    painter.setBrush(QBrush(bubble_gradient))
                    painter.setPen(QPen(QColor(200, 230, 255, 100), 1))
                    painter.drawEllipse(
                        QRectF(bx - bubble.size, by - bubble.size,
                               bubble.size * 2, bubble.size * 2)
                    )

            # Reflection
            reflection_gradient = QLinearGradient(0, 0, width * 0.4, 0)
            reflection_gradient.setColorAt(0, QColor(255, 255, 255, 40))
            reflection_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillRect(0, water_top, int(width * 0.4), progress_height, reflection_gradient)

    def enterEvent(self, event):
        """Mouse enter - reduce opacity"""
        self.is_hovered = True
        self.current_opacity = self.hover_opacity

        ml_total, goal_ml, percentage = self.storage.get_progress()
        glasses = self.storage.get_glasses()
        reminder_pct = self._get_reminder_percentage()
        remaining = max(0, self.reminder_interval - (time.time() - self.last_gulp_time))
        remaining_min = int(remaining // 60)

        status = " (Away)" if self.is_away else ""
        tooltip = f"{ml_total}ml / {goal_ml}ml ({percentage:.1f}%){status}\n"
        tooltip += f"{glasses} gulps detected\n"
        tooltip += f"Next reminder: {remaining_min} min"

        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), tooltip, self)
        self.update()

    def leaveEvent(self, event):
        """Mouse leave - restore opacity"""
        self.is_hovered = False
        self.current_opacity = self.normal_opacity
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        """Handle dragging"""
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.dragging = False

    def mouseDoubleClickEvent(self, event):
        """Double-click to undo"""
        if event.button() == Qt.LeftButton:
            self._undo_gulp()
            event.accept()

    def _show_context_menu(self, position):
        """Show context menu"""
        menu = QMenu(self)

        ml_total, goal_ml, percentage = self.storage.get_progress()
        status = " (Away)" if self.is_away else ""
        info_action = QAction(f"{ml_total}ml / {goal_ml}ml{status}", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)

        # Reminder info
        remaining = max(0, self.reminder_interval - (time.time() - self.last_gulp_time))
        remaining_min = int(remaining // 60)
        remaining_sec = int(remaining % 60)
        reminder_action = QAction(f"Reminder in: {remaining_min}:{remaining_sec:02d}", self)
        reminder_action.setEnabled(False)
        menu.addAction(reminder_action)

        menu.addSeparator()

        add_action = QAction("Add gulp (+100ml)", self)
        add_action.triggered.connect(self._manual_add_gulp)
        menu.addAction(add_action)

        undo_action = QAction("Undo last gulp (-100ml)", self)
        undo_action.triggered.connect(self._undo_gulp)
        if self.storage.get_glasses() == 0:
            undo_action.setEnabled(False)
        menu.addAction(undo_action)

        # Reset reminder
        reset_reminder_action = QAction("Reset reminder timer", self)
        reset_reminder_action.triggered.connect(self.reset_reminder)
        menu.addAction(reset_reminder_action)

        menu.addSeparator()

        reset_action = QAction("Reset today", self)
        reset_action.triggered.connect(self._reset_progress)
        menu.addAction(reset_action)

        menu.addSeparator()

        move_action = QAction("Move to other side", self)
        move_action.triggered.connect(self._move_to_other_side)
        menu.addAction(move_action)

        menu.addSeparator()

        settings_action = QAction("⚙️ Settings...", self)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        menu.exec_(position)

    def _manual_add_gulp(self):
        """Manually add gulp"""
        self.storage.add_gulp()
        self.reset_reminder()
        for _ in range(5):
            self.bubbles.append(Bubble(self.main_bar_width, self.height() - 10))
        self.update()

    def _undo_gulp(self):
        """Undo last gulp"""
        if self.storage.undo_gulp():
            print("[UNDO] Removed last gulp")
            self.update()
        else:
            print("[UNDO] Nothing to undo")

    def _reset_progress(self):
        """Reset today's progress"""
        self.storage.reset()
        self.bubbles.clear()
        self.reset_reminder()
        self.update()

    def _move_to_other_side(self):
        """Move to opposite side"""
        screen = QApplication.primaryScreen().geometry()
        margin = CONFIG["bar_margin"]

        if self.x() > screen.width() / 2:
            new_x = margin
        else:
            new_x = screen.width() - self.width() - margin

        self.move(new_x, self.y())

    def _open_settings(self):
        """Request to open settings"""
        self.settings_requested.emit()


def main():
    """Test UI standalone"""
    app = QApplication(sys.argv)

    storage = Storage()
    overlay = ProgressBarOverlay(storage)
    overlay.show()

    print("UI Test Mode")
    print("Right-click for menu")
    print("Double-click to undo")
    print("Hover to see stats")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
