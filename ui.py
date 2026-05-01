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
    gulp_registered = pyqtSignal()  # emitted when user clicks to register a gulp
    gulp_detected = pyqtSignal()    # legacy alias for visual-only refresh
    away_status_changed = pyqtSignal(bool)
    settings_requested = pyqtSignal()

    def __init__(self, storage: Storage = None):
        super().__init__()
        self.storage = storage or Storage()
        self.drag_position = QPoint()

        # Click-vs-drag tracking (manual gulp button)
        self.click_start_global = QPoint()
        self.click_drag_threshold = 5   # px before a press becomes a drag
        self.dragging_real = False

        # Animation state
        self.wave_offset = 0
        self.bubbles = []
        self.max_bubbles = 8
        self.animation_tick = 0

        # Microinteraction state (dopamine button)
        self.ripples = []           # list of {"x": float, "y": float, "age": int}
        self.ripple_max_age = 25    # frames at 20 FPS ≈ 1.25s
        self.splash_boost = 0.0     # 0..1, decays per frame; boosts wave amplitude
        self.splash_decay = 0.90

        # Big fat gulp button (lives at the bottom of the overlay)
        self.button_height = 80
        self.button_gap = 6         # gap between bar and button
        self.button_hover = False
        self.button_pressed = False
        self.press_in_button = False
        self.button_anim_scale = 1.0    # animates on press/release
        self.button_anim_target = 1.0
        self.button_idle_pulse = 0.0    # subtle idle bob

        # Away mode state (legacy; nothing toggles it now that webcam is gone)
        self.is_away = False

        # Hover state
        self.is_hovered = False
        self.normal_opacity = 1.0
        self.current_opacity = 1.0

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

        self.bar_height = screen.height() - 2 * margin
        self.main_bar_width = bar_width

        if CONFIG["bar_position"] == "right":
            x = screen.width() - bar_width - margin
        else:
            x = margin

        self.setGeometry(x, margin, bar_width, self.bar_height)

    def _connect_signals(self):
        """Connect internal signals"""
        self.gulp_detected.connect(self._on_gulp_visual_burst)
        self.away_status_changed.connect(self._on_away_status_changed)

    def _setup_animation(self):
        """Setup animation timer"""
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate)
        self.animation_timer.start(50)  # 20 FPS

    def _animate(self):
        """Update animation state"""
        self.animation_tick += 1

        # Decay splash boost
        if self.splash_boost > 0:
            self.splash_boost *= self.splash_decay
            if self.splash_boost < 0.01:
                self.splash_boost = 0.0

        # Age ripples; drop dead ones
        if self.ripples:
            for r in self.ripples:
                r["age"] += 1
            self.ripples = [r for r in self.ripples if r["age"] < self.ripple_max_age]

        # Tween button scale toward target (snappy spring)
        if abs(self.button_anim_scale - self.button_anim_target) > 0.005:
            self.button_anim_scale += (self.button_anim_target - self.button_anim_scale) * 0.35
        # Subtle idle "breathing" pulse to draw attention
        self.button_idle_pulse = math.sin(self.animation_tick * 0.05) * 0.5 + 0.5

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

    def _on_gulp_visual_burst(self):
        """Visual-only burst (e.g. external trigger that wants the bar to react)."""
        for _ in range(5):
            self.bubbles.append(Bubble(self.main_bar_width, self.height() - 10))
        self.update()

    def _register_gulp(self, click_pos):
        """Register a gulp from a manual click and trigger the dopamine microinteraction."""
        self.storage.add_gulp()

        # Splash boost: temporarily increases wave amplitude
        self.splash_boost = 1.0

        # Ripple at click position (in widget coords)
        self.ripples.append({"x": float(click_pos.x()), "y": float(click_pos.y()), "age": 0})

        # Bubble burst
        for _ in range(8):
            self.bubbles.append(Bubble(self.main_bar_width, self.height() - 10))

        self.gulp_registered.emit()
        self.update()

    def paintEvent(self, event):
        """Draw everything"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self.current_opacity)

        height = self.height()
        bar_area_height = max(50, height - self.button_height - self.button_gap)

        # Main water bar (full width, no reminder bar anymore)
        self._draw_main_bar(painter, self.main_bar_width, bar_area_height)

        # Big gulp button at the bottom
        self._draw_button(painter, self._button_rect())

        # Draw click ripples on top of everything (widget coords)
        self._draw_ripples(painter)

    def _draw_main_bar(self, painter, width, height):
        """Draw the main water progress bar"""
        ml_total, goal_ml, percentage = self.storage.get_progress()

        if self.is_away:
            self._draw_away_mode(painter, width, height, percentage)
        else:
            self._draw_normal_mode(painter, width, height, percentage)

        # Markers com labels de ML
        markers_ml = 500
        num_markers = int(goal_ml / markers_ml)

        for i in range(1, num_markers + 1):
            ml_value = i * markers_ml
            marker_percentage = (ml_value / goal_ml) * 100
            marker_y = height - int((marker_percentage / 100) * height)

            # Linha do marcador
            pen = QPen(QColor(255, 255, 255, 60))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(5, marker_y, width - 5, marker_y)

            # Label de ML rotacionado (só mostra se não for o topo)
            if marker_percentage < 98:
                painter.save()
                painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
                painter.setFont(QFont("Arial", 6))
                painter.translate(width - 4, marker_y + 3)
                painter.rotate(-90)
                # Formata: 500, 1000, 1.5k, 2k, etc.
                if ml_value >= 1000:
                    if ml_value % 1000 == 0:
                        label = f"{ml_value // 1000}k"
                    else:
                        label = f"{ml_value / 1000:.1f}k"
                else:
                    label = str(ml_value)
                painter.drawText(0, 0, label)
                painter.restore()

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

            # Splash boost amplifies the wave temporarily after a gulp
            wave_height = 6 + self.splash_boost * 14
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

    def _button_rect(self) -> QRectF:
        """Bounding rect of the big gulp button (in widget coords)."""
        return QRectF(
            0,
            self.height() - self.button_height,
            self.width(),
            self.button_height
        )

    def _draw_button(self, painter, rect: QRectF):
        """Draw the big chunky gulp button: water drop + plus, with hover/press states."""
        # Inset so the button doesn't touch widget edges
        inset = QRectF(
            rect.x() + 1,
            rect.y() + 4,
            rect.width() - 2,
            rect.height() - 8
        )

        # Apply press scale (anchor at center)
        scale = self.button_anim_scale
        if scale != 1.0:
            cx = inset.center().x()
            cy = inset.center().y()
            new_w = inset.width() * scale
            new_h = inset.height() * scale
            inset = QRectF(cx - new_w / 2, cy - new_h / 2, new_w, new_h)

        # Color palette by state
        if self.button_pressed:
            top_col = QColor(40, 110, 180)
            bot_col = QColor(15, 60, 130)
            border_col = QColor(160, 210, 255, 220)
        elif self.button_hover:
            top_col = QColor(130, 210, 255)
            bot_col = QColor(60, 150, 230)
            border_col = QColor(220, 240, 255, 230)
        else:
            top_col = QColor(90, 180, 235)
            bot_col = QColor(40, 120, 200)
            border_col = QColor(170, 215, 255, 200)

        # Drop shadow (only when not pressed → "lifts off the surface")
        if not self.button_pressed:
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(
                inset.x() + 1, inset.y() + 4,
                inset.width(), inset.height(),
                14, 14
            )
            painter.fillPath(shadow_path, QColor(0, 0, 0, 110))

        # Background gradient
        gradient = QLinearGradient(inset.x(), inset.top(), inset.x(), inset.bottom())
        gradient.setColorAt(0, top_col)
        gradient.setColorAt(1, bot_col)

        path = QPainterPath()
        path.addRoundedRect(inset, 14, 14)
        painter.fillPath(path, gradient)

        # Idle pulse highlight (subtle, only when not interacting)
        if not self.button_pressed and not self.button_hover:
            pulse_alpha = int(40 + self.button_idle_pulse * 35)
            pulse_grad = QLinearGradient(inset.x(), inset.top(), inset.x(), inset.center().y())
            pulse_grad.setColorAt(0, QColor(255, 255, 255, pulse_alpha))
            pulse_grad.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillPath(path, pulse_grad)

        # Border
        painter.setPen(QPen(border_col, 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Water drop icon
        cx = inset.center().x()
        cy = inset.center().y() + 2
        drop_w = inset.width() * 0.55
        drop_h = inset.height() * 0.62
        top_y = cy - drop_h * 0.55
        bot_y = cy + drop_h * 0.45
        side = drop_w * 0.55

        drop_path = QPainterPath()
        drop_path.moveTo(cx, top_y)
        drop_path.cubicTo(
            cx + side, top_y + drop_h * 0.35,
            cx + side, bot_y - drop_h * 0.05,
            cx, bot_y
        )
        drop_path.cubicTo(
            cx - side, bot_y - drop_h * 0.05,
            cx - side, top_y + drop_h * 0.35,
            cx, top_y
        )
        drop_path.closeSubpath()

        # Drop fill
        drop_color = QColor(255, 255, 255, 235) if not self.button_pressed else QColor(255, 255, 255, 200)
        painter.fillPath(drop_path, drop_color)
        painter.setPen(QPen(QColor(255, 255, 255, 240), 1.2))
        painter.drawPath(drop_path)

        # "+" badge in upper area of the drop
        plus_size = max(7.0, min(inset.width(), inset.height()) * 0.18)
        plus_x = cx
        plus_y = top_y + drop_h * 0.30
        painter.setPen(QPen(QColor(30, 100, 180), 2.2))
        painter.drawLine(int(plus_x - plus_size / 2), int(plus_y), int(plus_x + plus_size / 2), int(plus_y))
        painter.drawLine(int(plus_x), int(plus_y - plus_size / 2), int(plus_x), int(plus_y + plus_size / 2))

    def _draw_ripples(self, painter):
        """Draw radial ripples emanating from recent click positions."""
        if not self.ripples:
            return
        painter.save()
        painter.setBrush(Qt.NoBrush)
        for r in self.ripples:
            progress = r["age"] / self.ripple_max_age  # 0..1
            radius = 6 + progress * 32
            alpha = int(200 * (1.0 - progress))
            if alpha <= 0:
                continue
            pen = QPen(QColor(180, 230, 255, alpha), 2)
            painter.setPen(pen)
            painter.drawEllipse(QRectF(
                r["x"] - radius, r["y"] - radius,
                radius * 2, radius * 2
            ))
        painter.restore()

    def enterEvent(self, event):
        """Mouse enter - show tooltip. Opacity stays full so the gulp button
        remains clearly visible/clickable. The original see-through behavior
        will become moot once the bar registers as a Windows AppBar."""
        self.is_hovered = True

        ml_total, goal_ml, percentage = self.storage.get_progress()
        glasses = self.storage.get_glasses()

        status = " (Away)" if self.is_away else ""
        tooltip = f"{ml_total}ml / {goal_ml}ml ({percentage:.1f}%){status}\n"
        tooltip += f"{glasses} goles registrados"

        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), tooltip, self)
        self.update()

    def mousePressEvent(self, event):
        """Press on button arms a gulp; press on bar arms a drag."""
        if event.button() == Qt.LeftButton:
            self.click_start_global = event.globalPos()
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.dragging_real = False
            self.press_in_button = self._button_rect().contains(event.pos())
            if self.press_in_button:
                self.button_pressed = True
                self.button_anim_target = 0.92  # squish on press
                self.update()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        """Update hover; once moved past threshold over the bar, treat as drag."""
        # Hover state for the button (works even without buttons pressed thanks to setMouseTracking)
        in_btn = self._button_rect().contains(event.pos())
        if in_btn != self.button_hover:
            self.button_hover = in_btn
            self.update()

        if not (event.buttons() & Qt.LeftButton):
            return

        # Pressed in the button area: cancel "press" if dragged off the button
        if self.press_in_button:
            if not in_btn and self.button_pressed:
                self.button_pressed = False
                self.button_anim_target = 1.0
                self.update()
            elif in_btn and not self.button_pressed:
                self.button_pressed = True
                self.button_anim_target = 0.92
                self.update()
            return  # button presses don't drag the window

        # Pressed in the bar area: promote to drag past threshold
        if not self.dragging_real:
            moved = (event.globalPos() - self.click_start_global).manhattanLength()
            if moved >= self.click_drag_threshold:
                self.dragging_real = True
        if self.dragging_real:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Release inside button = gulp registered; release after drag = nothing."""
        if event.button() != Qt.LeftButton:
            return

        if self.press_in_button:
            released_in_button = self._button_rect().contains(event.pos())
            self.button_pressed = False
            self.button_anim_target = 1.0
            if released_in_button:
                self._register_gulp(event.pos())
            self.update()

        self.press_in_button = False
        self.dragging_real = False
        event.accept()

    def leaveEvent(self, event):
        """Restore opacity AND clear button hover state."""
        self.is_hovered = False
        self.current_opacity = self.normal_opacity
        if self.button_hover:
            self.button_hover = False
        self.update()

    def _show_context_menu(self, position):
        """Show context menu"""
        menu = QMenu(self)

        ml_total, goal_ml, percentage = self.storage.get_progress()
        info_action = QAction(f"{ml_total}ml / {goal_ml}ml", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)

        menu.addSeparator()

        add_action = QAction("Add gulp (+100ml)", self)
        add_action.triggered.connect(self._manual_add_gulp)
        menu.addAction(add_action)

        undo_action = QAction("Undo last gulp (-100ml)", self)
        undo_action.triggered.connect(self._undo_gulp)
        if self.storage.get_glasses() == 0:
            undo_action.setEnabled(False)
        menu.addAction(undo_action)

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
        """Manually add gulp via context menu (uses same path as the click button)."""
        center = QPoint(self.width() // 2, self.height() // 2)
        self._register_gulp(center)

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
