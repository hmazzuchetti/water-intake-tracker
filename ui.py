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
from PyQt5.QtCore import Qt, QPoint, QPointF, QTimer, pyqtSignal, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QFont,
    QBrush, QPainterPath, QRadialGradient
)

from config import CONFIG
from storage import Storage
from notes import NotesStore
from notes_ui import NotesColumn
from game import GameStore


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

    def __init__(self, storage: Storage = None, notes_store: NotesStore = None,
                 game_store: GameStore = None):
        super().__init__()
        self.storage = storage or Storage()
        self.notes_store = notes_store or NotesStore()
        self.game_store = game_store or GameStore()
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

        # Big circular gulp button (lives at the bottom-right of the overlay).
        # Diameter is max(60, bar_width) so the button stays chunky even when
        # the bar itself is narrow.
        self.button_diameter = max(60, CONFIG.get("bar_width", 30))
        self.button_gap = 6
        self.button_hover = False
        self.button_pressed = False
        self.press_in_button = False
        self.button_anim_scale = 1.0    # animates on press/release
        self.button_anim_target = 1.0
        self.button_idle_pulse = 0.0    # subtle idle bob

        # Counter pop (number scales up briefly after gulp)
        self.number_pop = 0.0
        # Goal glow (golden flash when daily goal is hit / level up)
        self.goal_glow = 0.0

        # Latest event payload from GameStore.record_gulp — read by main.py
        # to drive tray notifications (level up, achievements, streak).
        self.recent_events: dict = {}

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
        """Set window size and position.

        The overlay reserves room for the notes column at its expanded width
        even when the column is collapsed; the unused area on the side is
        kept transparent. The water bar itself stays glued to the screen edge.
        """
        screen = QApplication.primaryScreen().geometry()
        bar_width = CONFIG["bar_width"]
        margin = CONFIG["bar_margin"]

        self.bar_height = screen.height() - 2 * margin
        self.main_bar_width = bar_width
        self.notes_reserved_width = NotesColumn.EXPANDED_WIDTH

        total_width = self.notes_reserved_width + bar_width

        if CONFIG["bar_position"] == "right":
            x = screen.width() - total_width - margin
        else:
            x = margin

        self.setGeometry(x, margin, total_width, self.bar_height)

    def _connect_signals(self):
        """Connect internal signals"""
        self.gulp_detected.connect(self._on_gulp_visual_burst)
        self.away_status_changed.connect(self._on_away_status_changed)

        # Notes column lives to the left of the water bar
        self.notes_column = NotesColumn(self.notes_store, parent=self)
        self.notes_column.geometry_changed.connect(self._relayout_notes_column)
        self._relayout_notes_column(NotesColumn.COLLAPSED_WIDTH)
        self.notes_column.show()

    def _relayout_notes_column(self, current_width: int):
        """Keep the notes column glued to the right edge of its reserved area
        (i.e. immediately to the left of the water bar) as it animates width."""
        if not hasattr(self, "notes_column"):
            return
        col_h = max(50, self.height() - self.button_diameter - self.button_gap)
        x = self.width() - self.main_bar_width - current_width
        self.notes_column.setGeometry(x, 0, current_width, col_h)

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

        # Counter pop decay (quick spring back to 0)
        if self.number_pop > 0:
            self.number_pop *= 0.82
            if self.number_pop < 0.01:
                self.number_pop = 0.0

        # Goal/level-up glow decay (slower than pop for celebratory dwell)
        if self.goal_glow > 0:
            self.goal_glow *= 0.97
            if self.goal_glow < 0.02:
                self.goal_glow = 0.0

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
        """Register a gulp from a manual click and trigger the dopamine microinteraction.

        Also updates GameStore (XP, level, streak, achievements). The events
        from record_gulp are stored in self.recent_events so main.py can
        surface them as tray notifications when handling gulp_registered.
        """
        self.storage.add_gulp()

        # Gamification — XP, level, achievements
        events = {}
        try:
            ml, goal, pct = self.storage.get_progress()
            daily_gulps = self.storage.get_glasses()
            events = self.game_store.record_gulp(daily_gulps, pct)
        except Exception as e:
            print(f"[Game] Erro ao registrar gole: {e}")
        self.recent_events = events

        # Visual feedback — chunkier on celebratory events
        self.splash_boost = 1.0
        self.number_pop = 1.0
        if events.get("goal_hit_now") or events.get("leveled_up"):
            self.goal_glow = 1.0
            for _ in range(14):  # extra bubble burst on milestones
                self.bubbles.append(Bubble(self.main_bar_width, self.height() - 10))

        # Ripple at click position (in widget coords)
        self.ripples.append({"x": float(click_pos.x()), "y": float(click_pos.y()), "age": 0})

        # Standard bubble burst
        for _ in range(8):
            self.bubbles.append(Bubble(self.main_bar_width, self.height() - 10))

        self.gulp_registered.emit()
        self.update()

    def paintEvent(self, event):
        """Draw the water bar + gulp button. Notes column is a child widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self.current_opacity)

        height = self.height()
        bar_area_height = max(50, height - self.button_diameter - self.button_gap)
        bar_x = self.width() - self.main_bar_width

        # Water bar (right edge)
        painter.save()
        painter.translate(bar_x, 0)
        self._draw_main_bar(painter, self.main_bar_width, bar_area_height)
        painter.restore()

        # Big circular gulp button at the bottom-right
        self._draw_button(painter, self._button_rect())

        # Click ripples (rendered over the button)
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
        """Bounding square of the circular gulp button (in widget coords).

        Sits at the bottom-right corner. May be wider than the water bar
        (chunky button > thin bar) — extends leftward into the empty space
        below the notes column."""
        d = self.button_diameter
        return QRectF(
            self.width() - d,
            self.height() - d,
            d, d
        )

    def _point_in_button(self, pos) -> bool:
        """Click hit-test: inside the actual circle, not the bounding square."""
        br = self._button_rect()
        cx = br.center().x()
        cy = br.center().y()
        r = br.width() / 2
        dx = pos.x() - cx
        dy = pos.y() - cy
        return (dx * dx + dy * dy) <= r * r

    def _ring_color(self, percentage: float) -> QColor:
        """Progress-ring color, scaling from cyan to blue to gold."""
        if percentage < 30:
            return QColor(120, 210, 255)   # light cyan
        if percentage < 70:
            return QColor(70, 175, 240)    # blue
        if percentage < 100:
            return QColor(40, 145, 230)    # deeper blue
        return QColor(255, 215, 50)        # gold (goal hit)

    def _draw_button(self, painter, rect: QRectF):
        """Circular dopamine button: glassy gradient + progress ring + counter."""
        ml_total, goal_ml, percentage = self.storage.get_progress()
        pct_norm = min(1.0, percentage / 100.0)
        glasses = self.storage.get_glasses()
        glow = self.goal_glow  # 0..1

        # Apply press scale around center
        s = self.button_anim_scale
        cx0 = rect.center().x()
        cy0 = rect.center().y()
        d = min(rect.width(), rect.height()) * s
        inset = QRectF(cx0 - d / 2, cy0 - d / 2, d, d)
        cx = inset.center().x()
        cy = inset.center().y()

        # ── 1. Drop shadow ────────────────────────────────────────────────
        if not self.button_pressed:
            shadow_offset = 4
            shadow_path = QPainterPath()
            shadow_path.addEllipse(inset.translated(0, shadow_offset))
            painter.fillPath(shadow_path, QColor(0, 0, 0, 130))

        # ── 2. Outer glow (hover OR near-goal OR celebrating) ─────────────
        glow_strength = 0.0
        glow_color = QColor(0, 0, 0, 0)
        if glow > 0:
            glow_strength = max(glow_strength, glow)
            glow_color = QColor(255, 215, 80, int(120 * glow))
        elif self.button_hover:
            glow_strength = 0.7
            glow_color = QColor(180, 230, 255, 90)
        elif percentage >= 90:
            glow_strength = 0.5
            glow_color = QColor(255, 215, 80, 70)

        if glow_strength > 0:
            gg_rect = QRectF(
                cx - d * 0.95, cy - d * 0.95,
                d * 1.9, d * 1.9
            )
            gg = QRadialGradient(QPointF(cx, cy), d * 0.95)
            gg.setColorAt(0.45, glow_color)
            gg.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(gg)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(gg_rect)

        # ── 3. Body — radial gradient (glassy 3D look) ────────────────────
        if self.button_pressed:
            top = QColor(50, 120, 180)
            bot = QColor(20, 60, 110)
        elif self.button_hover:
            top = QColor(120, 210, 255)
            bot = QColor(50, 140, 220)
        else:
            top = QColor(90, 180, 240)
            bot = QColor(35, 120, 210)
        body_grad = QRadialGradient(QPointF(cx - d * 0.22, cy - d * 0.28), d * 0.85)
        body_grad.setColorAt(0, top)
        body_grad.setColorAt(1, bot)
        painter.setBrush(body_grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(inset)

        # ── 4. Progress ring (background full circle + colored arc) ───────
        ring_w = max(5, int(d * 0.08))
        ring_pad = ring_w / 2 + 1
        ring_rect = inset.adjusted(ring_pad, ring_pad, -ring_pad, -ring_pad)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 90), ring_w, Qt.SolidLine, Qt.FlatCap))
        painter.drawArc(ring_rect, 0, 360 * 16)

        if percentage > 0:
            ring_color = self._ring_color(percentage)
            painter.setPen(QPen(ring_color, ring_w, Qt.SolidLine, Qt.RoundCap))
            # Start at 12 o'clock (Qt: 90°); negative span = clockwise
            painter.drawArc(ring_rect, 90 * 16, -int(360 * 16 * pct_norm))

        # ── 5. Inner top highlight (glass shine) ──────────────────────────
        if not self.button_pressed:
            hl_rect = QRectF(
                inset.x() + d * 0.18,
                inset.y() + d * 0.10,
                d * 0.64,
                d * 0.42
            )
            hl_path = QPainterPath()
            hl_path.addEllipse(hl_rect)
            hl_grad = QLinearGradient(0, hl_rect.top(), 0, hl_rect.bottom())
            alpha = 120 + int(self.button_idle_pulse * 40)
            hl_grad.setColorAt(0, QColor(255, 255, 255, alpha))
            hl_grad.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillPath(hl_path, hl_grad)

        # ── 6. Counter (today's gulps) ────────────────────────────────────
        # Base font scales with diameter; pop animation grows it briefly.
        base_size = max(11, int(d * 0.38))
        pop_scale = 1.0 + self.number_pop * 0.30
        font_size = max(11, int(base_size * pop_scale))

        font = QFont("Segoe UI", font_size, QFont.Bold)
        painter.setFont(font)
        text = str(glasses)

        # Soft text shadow
        painter.setPen(QColor(0, 0, 0, 160))
        painter.drawText(inset.translated(1, 2), Qt.AlignCenter, text)
        # Fill — gold during goal_glow, white otherwise
        if glow > 0.05:
            text_color = QColor(
                255,
                int(255 - 30 * glow),
                int(150 - 100 * glow),
                250
            )
        else:
            text_color = QColor(255, 255, 255, 250)
        painter.setPen(text_color)
        painter.drawText(inset, Qt.AlignCenter, text)

        # ── 7. Small "Lv. N" label under the counter (tiny, soft) ─────────
        try:
            level = self.game_store.level()
        except Exception:
            level = 1
        lvl_size = max(8, int(d * 0.14))
        lvl_font = QFont("Segoe UI", lvl_size, QFont.DemiBold)
        painter.setFont(lvl_font)
        lvl_rect = QRectF(inset.x(), cy + d * 0.20, inset.width(), d * 0.20)
        painter.setPen(QColor(255, 255, 255, 180))
        painter.drawText(lvl_rect, Qt.AlignCenter, f"Lv. {level}")

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
        """Mouse enter — no tooltip (it conflicts visually with the notes
        column overlay). Stats are still available in the tray icon."""
        self.is_hovered = True
        self.update()

    def _is_in_bar_zone(self, pos) -> bool:
        """True if pos hits an interactive area: water bar strip or the
        circular gulp button. Everything else (the empty/transparent space
        reserved for the notes column) is non-interactive at the overlay
        level — the notes column is a child widget with its own events."""
        bar_x = self.width() - self.main_bar_width
        if pos.x() >= bar_x:
            return True
        return self._point_in_button(pos)

    def mousePressEvent(self, event):
        """Press on the button arms a gulp; press on the bar arms a drag.
        Clicks in the transparent left area are ignored."""
        if not self._is_in_bar_zone(event.pos()):
            return
        if event.button() == Qt.LeftButton:
            self.click_start_global = event.globalPos()
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.dragging_real = False
            self.press_in_button = self._point_in_button(event.pos())
            if self.press_in_button:
                self.button_pressed = True
                self.button_anim_target = 0.92  # squish on press
                self.update()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        """Update hover; once moved past threshold over the bar, treat as drag."""
        in_btn = self._point_in_button(event.pos())
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
            released_in_button = self._point_in_button(event.pos())
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

        stats_action = QAction("📊 Estatísticas...", self)
        stats_action.triggered.connect(self._open_stats)
        menu.addAction(stats_action)

        new_note_action = QAction("📝 Nova nota...", self)
        new_note_action.triggered.connect(self._open_new_note)
        menu.addAction(new_note_action)

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

    def _open_new_note(self):
        """Open the new-note dialog via the notes column."""
        if hasattr(self, "notes_column"):
            self.notes_column.create_new_note()

    def _open_stats(self):
        """Open the gamification stats dialog."""
        try:
            from game_ui import StatsDialog
            dlg = StatsDialog(self.game_store, self.storage, parent=None)
            dlg.exec_()
        except Exception as e:
            print(f"[Stats] Erro: {e}")

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
