"""
Gulp control widget — the chunky main button + satellite quick-actions.

Substitui a antiga barra de água vertical. Filosofia "clicker hero":
o widget é compacto, fica num canto da tela, e ao hover revela 4
satélites (Gole / Copo / Garrafa / Notas).

Layout:
    [Notas    ]   ← top
    [Garrafa  ]
    [Copo     ]
    [Gole     ]
    [MAIN BTN ]   ← bottom, sempre visível
"""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import (
    Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtSignal, pyqtProperty
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QFont, QPainterPath, QRadialGradient,
    QLinearGradient
)

import math


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    """Interpolação linear entre duas cores (t em 0..1)."""
    t = max(0.0, min(1.0, t))
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


# ─── Icon drawing helpers ────────────────────────────────────────────────


def draw_drop_icon(painter: QPainter, rect: QRectF, color: QColor):
    """Stylized water drop centered in rect."""
    w = rect.width()
    h = rect.height()
    cx = rect.center().x()
    cy = rect.center().y()
    drop_w = w * 0.50
    drop_h = h * 0.66
    top_y = cy - drop_h * 0.55
    bot_y = cy + drop_h * 0.45
    side = drop_w * 0.55

    path = QPainterPath()
    path.moveTo(cx, top_y)
    path.cubicTo(cx + side, top_y + drop_h * 0.40,
                 cx + side, bot_y - drop_h * 0.05,
                 cx, bot_y)
    path.cubicTo(cx - side, bot_y - drop_h * 0.05,
                 cx - side, top_y + drop_h * 0.40,
                 cx, top_y)
    path.closeSubpath()
    painter.fillPath(path, color)


def draw_glass_icon(painter: QPainter, rect: QRectF, color: QColor):
    """Drinking glass (slight taper, with water line)."""
    w = rect.width()
    h = rect.height()
    cx = rect.center().x()
    cy = rect.center().y()

    top_w = w * 0.55
    bot_w = w * 0.42
    glass_h = h * 0.66
    top_y = cy - glass_h / 2
    bot_y = cy + glass_h / 2

    path = QPainterPath()
    path.moveTo(cx - top_w / 2, top_y)
    path.lineTo(cx + top_w / 2, top_y)
    path.lineTo(cx + bot_w / 2, bot_y)
    path.lineTo(cx - bot_w / 2, bot_y)
    path.closeSubpath()

    painter.setPen(QPen(color, 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)

    # Water line at ~60% height
    wl_y = top_y + glass_h * 0.40
    # Glass width at this height
    t = (wl_y - top_y) / glass_h
    wl_w = top_w + (bot_w - top_w) * t
    fill_path = QPainterPath()
    fill_path.moveTo(cx - wl_w / 2 + 1, wl_y)
    fill_path.lineTo(cx + wl_w / 2 - 1, wl_y)
    fill_path.lineTo(cx + bot_w / 2 - 1, bot_y - 1)
    fill_path.lineTo(cx - bot_w / 2 + 1, bot_y - 1)
    fill_path.closeSubpath()
    fill_color = QColor(color)
    fill_color.setAlpha(120)
    painter.fillPath(fill_path, fill_color)


def draw_bottle_icon(painter: QPainter, rect: QRectF, color: QColor):
    """Bottle silhouette with neck."""
    w = rect.width()
    h = rect.height()
    cx = rect.center().x()
    cy = rect.center().y()

    bottle_h = h * 0.78
    bottle_w = w * 0.46
    neck_w = w * 0.20
    neck_h = bottle_h * 0.22
    cap_h = bottle_h * 0.06

    top_y = cy - bottle_h / 2
    bot_y = cy + bottle_h / 2

    path = QPainterPath()
    # Cap on top
    path.moveTo(cx - neck_w / 2, top_y)
    path.lineTo(cx + neck_w / 2, top_y)
    path.lineTo(cx + neck_w / 2, top_y + cap_h)
    path.lineTo(cx - neck_w / 2, top_y + cap_h)
    path.closeSubpath()

    # Body
    body_path = QPainterPath()
    body_path.moveTo(cx - neck_w / 2, top_y + cap_h)
    body_path.lineTo(cx + neck_w / 2, top_y + cap_h)
    body_path.lineTo(cx + neck_w / 2, top_y + cap_h + neck_h)
    # Shoulder curve out
    body_path.cubicTo(
        cx + bottle_w / 2, top_y + cap_h + neck_h + 4,
        cx + bottle_w / 2, top_y + cap_h + neck_h + 10,
        cx + bottle_w / 2, top_y + cap_h + neck_h + 14
    )
    body_path.lineTo(cx + bottle_w / 2, bot_y - 3)
    body_path.cubicTo(
        cx + bottle_w / 2, bot_y,
        cx + bottle_w / 2 - 3, bot_y,
        cx, bot_y
    )
    body_path.cubicTo(
        cx - bottle_w / 2 + 3, bot_y,
        cx - bottle_w / 2, bot_y,
        cx - bottle_w / 2, bot_y - 3
    )
    body_path.lineTo(cx - bottle_w / 2, top_y + cap_h + neck_h + 14)
    body_path.cubicTo(
        cx - bottle_w / 2, top_y + cap_h + neck_h + 10,
        cx - bottle_w / 2, top_y + cap_h + neck_h + 4,
        cx - neck_w / 2, top_y + cap_h + neck_h
    )
    body_path.closeSubpath()

    painter.setPen(QPen(color, 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)
    painter.drawPath(body_path)

    # Water inside (lower 55%)
    fill_top_y = top_y + cap_h + neck_h + 14 + (bot_y - top_y - cap_h - neck_h - 14) * 0.30
    fill_path = QPainterPath()
    fill_path.moveTo(cx - bottle_w / 2 + 2, fill_top_y)
    fill_path.lineTo(cx + bottle_w / 2 - 2, fill_top_y)
    fill_path.lineTo(cx + bottle_w / 2 - 2, bot_y - 4)
    fill_path.cubicTo(
        cx + bottle_w / 2 - 2, bot_y - 2,
        cx + bottle_w / 2 - 4, bot_y - 2,
        cx, bot_y - 2
    )
    fill_path.cubicTo(
        cx - bottle_w / 2 + 4, bot_y - 2,
        cx - bottle_w / 2 + 2, bot_y - 2,
        cx - bottle_w / 2 + 2, bot_y - 4
    )
    fill_path.closeSubpath()
    fc = QColor(color)
    fc.setAlpha(120)
    painter.fillPath(fill_path, fc)


def draw_notes_icon(painter: QPainter, rect: QRectF, color: QColor):
    """Small sticky note with corner fold."""
    w = rect.width()
    h = rect.height()
    cx = rect.center().x()
    cy = rect.center().y()

    note_w = w * 0.62
    note_h = h * 0.62
    left = cx - note_w / 2
    top = cy - note_h / 2
    right = cx + note_w / 2
    bot = cy + note_h / 2
    fold = min(note_w, note_h) * 0.30

    # Main paper shape with corner fold (top-right cut)
    paper = QPainterPath()
    paper.moveTo(left, top)
    paper.lineTo(right - fold, top)
    paper.lineTo(right, top + fold)
    paper.lineTo(right, bot)
    paper.lineTo(left, bot)
    paper.closeSubpath()

    painter.setPen(QPen(color, 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(paper)

    # Fold triangle
    fold_path = QPainterPath()
    fold_path.moveTo(right - fold, top)
    fold_path.lineTo(right - fold, top + fold)
    fold_path.lineTo(right, top + fold)
    painter.drawPath(fold_path)

    # Two lines representing text
    line_y1 = top + note_h * 0.50
    line_y2 = top + note_h * 0.70
    painter.drawLine(int(left + 4), int(line_y1), int(right - 6), int(line_y1))
    painter.drawLine(int(left + 4), int(line_y2), int(right - 12), int(line_y2))


# ─── Satellite button ────────────────────────────────────────────────────


class SatelliteButton(QWidget):
    """Small circular satellite that hovers near the main gulp button.

    Has a fade-in/fade-out opacity animation and its own hover/press
    feedback. Emits `clicked` when released inside its circle while
    sufficiently visible (avoids accidental clicks during fade-out)."""

    clicked = pyqtSignal()

    DIAMETER = 50

    def __init__(self, icon_fn, tone: QColor, tooltip: str, parent=None):
        super().__init__(parent)
        self.icon_fn = icon_fn
        self.tone = QColor(tone)
        self.setToolTip(tooltip)
        self.setFixedSize(self.DIAMETER, self.DIAMETER)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._opacity = 0.0
        self._hover = False
        self._pressed = False
        self._press_inside = False

        self._anim = QPropertyAnimation(self, b"opacity_value", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

    # Qt property for animation
    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float):
        self._opacity = float(value)
        self.update()

    opacity_value = pyqtProperty(float, _get_opacity, _set_opacity)

    def set_visible_animated(self, visible: bool):
        target = 1.0 if visible else 0.0
        if abs(self._opacity - target) < 0.01 and not self._anim.state():
            return
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(target)
        self._anim.start()

    def _is_active(self) -> bool:
        """True if the satellite is visible enough to accept clicks."""
        return self._opacity > 0.5

    def _point_inside_circle(self, pos) -> bool:
        cx = self.width() / 2
        cy = self.height() / 2
        r = min(self.width(), self.height()) / 2
        dx = pos.x() - cx
        dy = pos.y() - cy
        return (dx * dx + dy * dy) <= r * r

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self._is_active():
            event.ignore()
            return
        if self._point_inside_circle(event.pos()):
            self._pressed = True
            self._press_inside = True
            self.update()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        was_pressed = self._pressed
        self._pressed = False
        self.update()
        if (was_pressed and self._press_inside
                and self._point_inside_circle(event.pos())
                and self._is_active()):
            self.clicked.emit()
        self._press_inside = False

    def paintEvent(self, event):
        if self._opacity <= 0.01:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        # Inset for soft padding
        inset = QRectF(2, 2, self.width() - 4, self.height() - 4)

        # Press scale
        if self._pressed:
            cx = inset.center().x()
            cy = inset.center().y()
            scale = 0.92
            nw = inset.width() * scale
            nh = inset.height() * scale
            inset = QRectF(cx - nw / 2, cy - nh / 2, nw, nh)

        # Background gradient
        bg_top = self.tone.lighter(135 if self._hover else 110)
        bg_bot = self.tone.darker(115 if self._hover else 130)

        gradient = QRadialGradient(
            QPointF(inset.center().x() - inset.width() * 0.2,
                    inset.center().y() - inset.height() * 0.25),
            inset.width() * 0.8
        )
        gradient.setColorAt(0, bg_top)
        gradient.setColorAt(1, bg_bot)

        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        if not self._pressed:
            # Shadow first
            shadow = QPainterPath()
            shadow.addEllipse(inset.translated(0, 2))
            painter.fillPath(shadow, QColor(0, 0, 0, 100))
            painter.setBrush(gradient)
        painter.drawEllipse(inset)

        # Border ring
        ring_color = QColor(255, 255, 255, 180 if self._hover else 90)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(ring_color, 1.5))
        painter.drawEllipse(inset)

        # Glassy highlight
        if not self._pressed:
            hl_rect = QRectF(
                inset.x() + inset.width() * 0.20,
                inset.y() + inset.height() * 0.12,
                inset.width() * 0.60,
                inset.height() * 0.36
            )
            hl_path = QPainterPath()
            hl_path.addEllipse(hl_rect)
            hl_grad = QLinearGradient(0, hl_rect.top(), 0, hl_rect.bottom())
            hl_grad.setColorAt(0, QColor(255, 255, 255, 130))
            hl_grad.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillPath(hl_path, hl_grad)

        # Icon
        icon_color = QColor(255, 255, 255, 245)
        if self._pressed:
            icon_color.setAlpha(200)
        self.icon_fn(painter, inset, icon_color)


# ─── Main gulp button ────────────────────────────────────────────────────


class GulpButton(QWidget):
    """The big chunky main button — circular, paints progress ring + counter
    + level. Click = default gole (CONFIG['ml_per_gulp']).

    Visual state is driven from outside (number_pop, goal_glow) by the
    container so multiple buttons could share animation state if needed."""

    clicked = pyqtSignal()

    DIAMETER = 84

    # "Botão que seca" — cue ambiente de hidratação. Começa a dessaturar
    # após DRY_START_MIN minutos sem gole e fica totalmente "seco" em
    # DRY_FULL_MIN. Sem popup, sem som: só o estado visual comunicando
    # "faz tempo" pela visão periférica.
    DRY_START_MIN = 45.0
    DRY_FULL_MIN = 120.0

    def __init__(self, storage, game_store, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.game_store = game_store

        self.setFixedSize(self.DIAMETER, self.DIAMETER)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Animation state (driven by 20fps timer in container)
        self.number_pop = 0.0     # 0..1, decays per frame
        self.goal_glow = 0.0      # 0..1
        self.button_idle_pulse = 0.0
        self.button_hover = False
        self.button_pressed = False
        self.press_inside = False

    # ── Helpers ────────────────────────────────────────────────────────

    def _dryness(self) -> float:
        """0..1 — quanto o botão está 'seco' (tempo sem gole).

        Regras: meta batida → nunca seca (dia vencido). Nenhum gole hoje
        → totalmente seco (manhã começa convidando o primeiro gole)."""
        try:
            _, _, percentage = self.storage.get_progress()
            if percentage >= 100:
                return 0.0
            mins = self.storage.minutes_since_last_gulp()
        except Exception:
            return 0.0
        if mins is None:
            return 1.0
        if mins <= self.DRY_START_MIN:
            return 0.0
        if mins >= self.DRY_FULL_MIN:
            return 1.0
        return (mins - self.DRY_START_MIN) / (self.DRY_FULL_MIN - self.DRY_START_MIN)

    def _point_inside_circle(self, pos) -> bool:
        cx = self.width() / 2
        cy = self.height() / 2
        r = min(self.width(), self.height()) / 2 - 2
        dx = pos.x() - cx
        dy = pos.y() - cy
        return (dx * dx + dy * dy) <= r * r

    def _ring_color(self, percentage: float) -> QColor:
        if percentage < 30:
            return QColor(120, 210, 255)
        if percentage < 70:
            return QColor(70, 175, 240)
        if percentage < 100:
            return QColor(40, 145, 230)
        return QColor(255, 215, 50)

    # ── Mouse ──────────────────────────────────────────────────────────

    def enterEvent(self, event):
        self.button_hover = True
        self.update()

    def leaveEvent(self, event):
        self.button_hover = False
        self.button_pressed = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        if self._point_inside_circle(event.pos()):
            self.button_pressed = True
            self.press_inside = True
            self.update()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        was_pressed = self.button_pressed
        self.button_pressed = False
        if was_pressed and self.press_inside and self._point_inside_circle(event.pos()):
            self.clicked.emit()
        self.press_inside = False
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        ml_total, goal_ml, percentage = self.storage.get_progress()
        pct_norm = min(1.0, percentage / 100.0)
        glasses = self.storage.get_glasses()
        glow = self.goal_glow
        dry = self._dryness()

        # Tooltip sempre com o dado que importa (o número central é contagem
        # de cliques, ambíguo entre gole de 100ml e garrafa de 500ml).
        tip = f"{ml_total} / {goal_ml} ml — {percentage:.0f}%"
        if self.toolTip() != tip:
            self.setToolTip(tip)

        rect = QRectF(0, 0, self.width(), self.height())
        inset = rect.adjusted(3, 3, -3, -3)

        d = min(inset.width(), inset.height())
        cx = inset.center().x()
        cy = inset.center().y()

        # Apply press scale around center
        s = 0.92 if self.button_pressed else 1.0
        if s != 1.0:
            nd = d * s
            inset = QRectF(cx - nd / 2, cy - nd / 2, nd, nd)
            d = nd

        # Drop shadow
        if not self.button_pressed:
            shadow = QPainterPath()
            shadow.addEllipse(inset.translated(0, 4))
            painter.fillPath(shadow, QColor(0, 0, 0, 130))

        # Outer glow (hover / near-goal / celebration)
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
            gg_rect = QRectF(cx - d * 0.95, cy - d * 0.95, d * 1.9, d * 1.9)
            gg = QRadialGradient(QPointF(cx, cy), d * 0.95)
            gg.setColorAt(0.45, glow_color)
            gg.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(gg)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(gg_rect)

        # Body gradient — em idle, dessatura conforme o tempo sem gole
        # ("secando"). Hover/press mantêm as cores vivas: a atenção do
        # usuário já chegou, o cue cumpriu o papel.
        if self.button_pressed:
            top = QColor(50, 120, 180)
            bot = QColor(20, 60, 110)
        elif self.button_hover:
            top = QColor(120, 210, 255)
            bot = QColor(50, 140, 220)
        else:
            top = _lerp_color(QColor(90, 180, 240), QColor(128, 142, 150), dry)
            bot = _lerp_color(QColor(35, 120, 210), QColor(70, 84, 94), dry)
        body = QRadialGradient(
            QPointF(cx - d * 0.22, cy - d * 0.28), d * 0.85
        )
        body.setColorAt(0, top)
        body.setColorAt(1, bot)
        painter.setBrush(body)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(inset)

        # Progress ring (background full circle + colored arc)
        ring_w = max(5, int(d * 0.08))
        ring_pad = ring_w / 2 + 1
        ring_rect = inset.adjusted(ring_pad, ring_pad, -ring_pad, -ring_pad)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 90), ring_w, Qt.SolidLine, Qt.FlatCap))
        painter.drawArc(ring_rect, 0, 360 * 16)

        if percentage > 0:
            painter.setPen(QPen(self._ring_color(percentage), ring_w,
                                Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(ring_rect, 90 * 16, -int(360 * 16 * pct_norm))

        # Inner top highlight (glassy)
        if not self.button_pressed:
            hl = QRectF(
                inset.x() + d * 0.18, inset.y() + d * 0.10,
                d * 0.64, d * 0.42
            )
            hl_path = QPainterPath()
            hl_path.addEllipse(hl)
            hl_grad = QLinearGradient(0, hl.top(), 0, hl.bottom())
            # Botão seco perde o brilho "molhado" — highlight esmaece junto
            alpha = int((120 + self.button_idle_pulse * 40) * (1.0 - 0.65 * dry))
            hl_grad.setColorAt(0, QColor(255, 255, 255, alpha))
            hl_grad.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillPath(hl_path, hl_grad)

        # Counter (today's gulps), with pop animation
        base_size = max(13, int(d * 0.38))
        pop_scale = 1.0 + self.number_pop * 0.30
        font_size = max(13, int(base_size * pop_scale))
        painter.setFont(QFont("Segoe UI", font_size, QFont.Bold))

        text = str(glasses)
        painter.setPen(QColor(0, 0, 0, 160))
        painter.drawText(inset.translated(1, 2), Qt.AlignCenter, text)
        if glow > 0.05:
            text_color = QColor(255, int(255 - 30 * glow), int(150 - 100 * glow), 250)
        else:
            text_color = QColor(255, 255, 255, 250)
        painter.setPen(text_color)
        painter.drawText(inset, Qt.AlignCenter, text)

        # Lv. N label
        try:
            level = self.game_store.level()
        except Exception:
            level = 1
        lvl_size = max(9, int(d * 0.14))
        painter.setFont(QFont("Segoe UI", lvl_size, QFont.DemiBold))
        lvl_rect = QRectF(inset.x(), cy + d * 0.20, inset.width(), d * 0.20)
        painter.setPen(QColor(255, 255, 255, 180))
        painter.drawText(lvl_rect, Qt.AlignCenter, f"Lv. {level}")


# ─── Gulp control widget (container) ─────────────────────────────────────


class GulpControlWidget(QWidget):
    """Container: main button at bottom, satellites stacked above. Hover
    expands the satellites; mouse leave collapses them (debounced)."""

    # Signal emitted with ml when a gulp is registered (main click or satellite)
    gulp_registered = pyqtSignal(int)
    # Signal to toggle notes column visibility
    notes_toggle_requested = pyqtSignal()

    SATELLITE_SPACING = 8       # px between satellites
    GAP_MAIN_TO_SATELLITE = 14  # px between main button and first satellite

    def __init__(self, storage, game_store, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.game_store = game_store

        # Compute total size
        main_d = GulpButton.DIAMETER
        sat_d = SatelliteButton.DIAMETER
        n_sat = 4
        sat_total_h = n_sat * sat_d + (n_sat - 1) * self.SATELLITE_SPACING
        total_h = sat_total_h + self.GAP_MAIN_TO_SATELLITE + main_d
        total_w = max(main_d, sat_d) + 8  # small padding

        self.setFixedSize(total_w, total_h)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Main button (at the bottom)
        self.main_btn = GulpButton(storage, game_store, parent=self)
        main_x = (total_w - main_d) // 2
        main_y = total_h - main_d
        self.main_btn.move(main_x, main_y)
        self.main_btn.clicked.connect(self._on_main_clicked)

        # Satellites — placed bottom-up so visual order from main upward is:
        # Gole (closest), Copo, Garrafa, Notas (farthest).
        sat_x = (total_w - sat_d) // 2

        from config import CONFIG  # late import to avoid cycle issues

        self.sat_gole = SatelliteButton(
            draw_drop_icon, QColor("#7fd3ff"),
            f"Gole ({CONFIG.get('ml_per_gulp', 100)} ml)", parent=self
        )
        self.sat_gole.clicked.connect(
            lambda: self.gulp_registered.emit(CONFIG.get("ml_per_gulp", 100))
        )

        self.sat_copo = SatelliteButton(
            draw_glass_icon, QColor("#92ddff"),
            f"Copo ({CONFIG.get('ml_per_glass', 300)} ml)", parent=self
        )
        self.sat_copo.clicked.connect(
            lambda: self.gulp_registered.emit(CONFIG.get("ml_per_glass", 300))
        )

        self.sat_garrafa = SatelliteButton(
            draw_bottle_icon, QColor("#a7e4ff"),
            f"Garrafa ({CONFIG.get('ml_per_bottle', 500)} ml)", parent=self
        )
        self.sat_garrafa.clicked.connect(
            lambda: self.gulp_registered.emit(CONFIG.get("ml_per_bottle", 500))
        )

        self.sat_notas = SatelliteButton(
            draw_notes_icon, QColor("#fff0a0"),
            "Mostrar/esconder notas", parent=self
        )
        self.sat_notas.clicked.connect(self.notes_toggle_requested.emit)

        # Order, from closest to main button upward:
        ordered_sats = [self.sat_gole, self.sat_copo, self.sat_garrafa, self.sat_notas]
        self.satellites = ordered_sats

        # Position each satellite
        first_sat_y = main_y - self.GAP_MAIN_TO_SATELLITE - sat_d
        for i, sat in enumerate(ordered_sats):
            y = first_sat_y - i * (sat_d + self.SATELLITE_SPACING)
            sat.move(sat_x, y)

        # Animation timer (drives main button pop/glow/pulse decay)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)  # 20 fps
        self._tick_count = 0

        # Collapse debounce — keeps satellites open through brief mouse exits
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(220)
        self._collapse_timer.timeout.connect(self._collapse_now)

        # Start with satellites hidden
        self._expanded = False

    # ── Animation tick ─────────────────────────────────────────────────

    def _tick(self):
        self._tick_count += 1
        m = self.main_btn

        # Number pop
        if m.number_pop > 0:
            m.number_pop *= 0.82
            if m.number_pop < 0.01:
                m.number_pop = 0.0

        # Goal glow (slower decay)
        if m.goal_glow > 0:
            m.goal_glow *= 0.97
            if m.goal_glow < 0.02:
                m.goal_glow = 0.0

        # Idle pulse
        m.button_idle_pulse = math.sin(self._tick_count * 0.05) * 0.5 + 0.5
        m.update()

    # ── Public — called by overlay after a gulp registers ──────────────

    def trigger_gulp_animation(self, events: dict):
        """Visual response to a registered gulp.

        Pops the number, fires goal glow on milestones."""
        m = self.main_btn
        m.number_pop = 1.0
        if events.get("goal_hit_now") or events.get("leveled_up"):
            m.goal_glow = 1.0
        m.update()

    def refresh_tooltips(self):
        """Re-read CONFIG (in case user changed ml values via settings)
        and update tooltips on the satellites."""
        from config import CONFIG
        self.sat_gole.setToolTip(f"Gole ({CONFIG.get('ml_per_gulp', 100)} ml)")
        self.sat_copo.setToolTip(f"Copo ({CONFIG.get('ml_per_glass', 300)} ml)")
        self.sat_garrafa.setToolTip(f"Garrafa ({CONFIG.get('ml_per_bottle', 500)} ml)")

    # ── Hover handling ─────────────────────────────────────────────────

    def _on_main_clicked(self):
        from config import CONFIG
        self.gulp_registered.emit(CONFIG.get("ml_per_gulp", 100))

    def enterEvent(self, event):
        self._collapse_timer.stop()
        if not self._expanded:
            self._expanded = True
            self._expand()

    def leaveEvent(self, event):
        # Debounce — give the user 220ms to come back (e.g. during animation)
        self._collapse_timer.start()

    def _expand(self):
        for i, sat in enumerate(self.satellites):
            QTimer.singleShot(i * 40, lambda s=sat: s.set_visible_animated(True))

    def _collapse_now(self):
        self._expanded = False
        for i, sat in enumerate(reversed(self.satellites)):
            QTimer.singleShot(i * 30, lambda s=sat: s.set_visible_animated(False))
