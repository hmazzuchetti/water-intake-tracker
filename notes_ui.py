"""
Sticky notes widgets — embedded next to the water bar.

NotesColumn = container, alinhada à direita ao lado da barra. Hover
na coluna expande largura e cards (todos juntos). Click num card
abre edição; click no "✓" completa a nota; "+" no rodapé cria.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLineEdit,
    QPlainTextEdit, QRadioButton, QButtonGroup, QCheckBox, QDateTimeEdit,
    QLabel, QDialogButtonBox, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QRectF, QSize, QPoint,
    QDateTime, QTimer, pyqtSignal
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QFont, QPainterPath, QBrush,
    QLinearGradient, QFontMetrics
)

from notes import (
    Note, NotesStore,
    PRIORITY_NOW, PRIORITY_TODAY, PRIORITY_LATER,
    PRIORITIES, PRIORITY_LABEL, PRIORITY_COLOR
)


STICKY_BG = QColor("#FFF4A3")
STICKY_BG_HOVER = QColor("#FFEC7C")
STICKY_BORDER = QColor(180, 160, 60, 200)
COMPLETE_BTN_BG = QColor(70, 160, 90, 220)
COMPLETE_BTN_BG_HOVER = QColor(90, 200, 110, 240)


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _humanize_deadline(deadline_iso: Optional[str]) -> Optional[str]:
    """Return a short human deadline string ('3h', 'amanhã', '12/05', ...) or None."""
    dt = _parse_iso(deadline_iso)
    if dt is None:
        return None
    now = datetime.now()
    delta = dt - now
    if delta.total_seconds() < 0:
        return "atrasada"
    if delta < timedelta(hours=1):
        mins = max(1, int(delta.total_seconds() // 60))
        return f"{mins}min"
    if delta < timedelta(hours=24):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours}h"
    if delta < timedelta(days=2):
        return "amanhã"
    if delta < timedelta(days=7):
        return dt.strftime("%a").lower()
    return dt.strftime("%d/%m")


def _is_urgent_deadline(deadline_iso: Optional[str]) -> bool:
    dt = _parse_iso(deadline_iso)
    if dt is None:
        return False
    return (dt - datetime.now()) < timedelta(hours=24)


# ---------------------------------------------------------------------------
# NoteCard
# ---------------------------------------------------------------------------


class NoteCard(QWidget):
    """A single sticky note card. Collapsed = title only; expanded = body + deadline + ✓."""

    COLLAPSED_HEIGHT = 36
    EXPANDED_HEIGHT = 92
    LEFT_BORDER_WIDTH = 4

    completed = pyqtSignal(str)        # note id
    edit_requested = pyqtSignal(str)   # note id

    def __init__(self, note: Note, parent=None):
        super().__init__(parent)
        self.note = note
        self.expanded = False
        self._complete_hover = False
        self._press_started_on_complete = False

        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self.COLLAPSED_HEIGHT)

        self._height_anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._height_anim.setDuration(220)
        self._height_anim.setEasingCurve(QEasingCurve.InOutCubic)

    def set_expanded(self, expanded: bool):
        if expanded == self.expanded:
            return
        self.expanded = expanded
        target = self.EXPANDED_HEIGHT if expanded else self.COLLAPSED_HEIGHT

        # Drive both min and max so the layout settles cleanly.
        self._height_anim.stop()
        self._height_anim.setStartValue(self.height())
        self._height_anim.setEndValue(target)
        self._height_anim.start()
        self.setMinimumHeight(target)
        self.update()

    # -- painting --------------------------------------------------------

    def _complete_btn_rect(self) -> QRectF:
        """Where the ✓ button lives inside the expanded card."""
        size = 24
        margin = 6
        w = self.width()
        h = self.height()
        return QRectF(w - size - margin, h - size - margin, size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(0, 1, -1, -1)
        priority_color = QColor(PRIORITY_COLOR.get(self.note.priority, PRIORITY_COLOR[PRIORITY_TODAY]))

        # Collapsed = priority chip only. Just enough color to say "tem nota
        # ativa aqui". No text, no badge, no buttons. Hover expands to reveal.
        if not self.expanded:
            chip_path = QPainterPath()
            chip_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height())
            chip_path.addRoundedRect(chip_rect, 5, 5)
            painter.fillPath(chip_path, priority_color)
            # Subtle inner highlight for a tactile look
            highlight = QPainterPath()
            highlight.addRoundedRect(QRectF(rect.x() + 1, rect.y() + 1, rect.width() - 2, max(1, rect.height() // 3)), 4, 4)
            painter.fillPath(highlight, QColor(255, 255, 255, 50))
            return

        # Expanded = full sticky-note look with title, body, deadline, ✓.
        # Drop shadow
        shadow = QPainterPath()
        shadow.addRoundedRect(QRectF(rect.x() + 1, rect.y() + 2, rect.width(), rect.height()), 6, 6)
        painter.fillPath(shadow, QColor(0, 0, 0, 50))

        # Sticky background
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(rect), 6, 6)
        painter.fillPath(bg_path, STICKY_BG)

        # Left priority border
        painter.fillRect(
            QRectF(rect.x(), rect.y(), self.LEFT_BORDER_WIDTH, rect.height()),
            priority_color
        )

        # Card outline
        painter.setPen(QPen(STICKY_BORDER, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(bg_path)

        pad_l = self.LEFT_BORDER_WIDTH + 8
        pad_r = 8
        pad_t = 6
        text_width = max(20, rect.width() - pad_l - pad_r)

        # Title (no truncation; word-wrap inside the title row)
        title_font = QFont("Segoe UI", 9)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(40, 40, 40)))
        fm = QFontMetrics(title_font)
        title_rect = QRectF(rect.x() + pad_l, rect.y() + pad_t, text_width, fm.height() + 2)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self.note.title or "(sem título)")

        # Deadline badge (top-right) — urgent only
        deadline_human = _humanize_deadline(self.note.deadline)
        if deadline_human and _is_urgent_deadline(self.note.deadline):
            badge_font = QFont("Segoe UI", 7, QFont.Bold)
            painter.setFont(badge_font)
            bfm = QFontMetrics(badge_font)
            text_w = bfm.horizontalAdvance(deadline_human) + 8
            badge_rect = QRectF(rect.right() - text_w - 4, rect.y() + 4, text_w, 14)
            badge_path = QPainterPath()
            badge_path.addRoundedRect(badge_rect, 3, 3)
            painter.fillPath(badge_path, QColor(231, 76, 60, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignCenter, deadline_human)

        # Body
        if rect.height() > 50:
            body_font = QFont("Segoe UI", 8)
            painter.setFont(body_font)
            painter.setPen(QPen(QColor(70, 70, 70)))
            body_rect = QRectF(
                rect.x() + pad_l,
                rect.y() + pad_t + fm.height() + 2,
                text_width - 30,  # leave room for ✓ button
                rect.height() - pad_t - fm.height() - 6 - 4
            )
            painter.drawText(body_rect, Qt.AlignLeft | Qt.TextWordWrap, self.note.body or "")

            # Complete button (✓)
            btn_rect = self._complete_btn_rect()
            btn_path = QPainterPath()
            btn_path.addEllipse(btn_rect)
            btn_color = COMPLETE_BTN_BG_HOVER if self._complete_hover else COMPLETE_BTN_BG
            painter.fillPath(btn_path, btn_color)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            check_pad = 6
            painter.drawLine(
                int(btn_rect.left() + check_pad), int(btn_rect.center().y() + 1),
                int(btn_rect.center().x() - 1), int(btn_rect.bottom() - check_pad)
            )
            painter.drawLine(
                int(btn_rect.center().x() - 1), int(btn_rect.bottom() - check_pad),
                int(btn_rect.right() - check_pad + 1), int(btn_rect.top() + check_pad)
            )

    # -- mouse -----------------------------------------------------------

    def mouseMoveEvent(self, event):
        # Track hover over the ✓ button
        in_btn = self.expanded and self._complete_btn_rect().contains(event.pos())
        if in_btn != self._complete_hover:
            self._complete_hover = in_btn
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        if self.expanded and self._complete_btn_rect().contains(event.pos()):
            self._press_started_on_complete = True
        else:
            self._press_started_on_complete = False
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        if self._press_started_on_complete and self.expanded and self._complete_btn_rect().contains(event.pos()):
            self.completed.emit(self.note.id)
        else:
            # Treated as a click on the card → request edit
            if not self._press_started_on_complete:
                self.edit_requested.emit(self.note.id)
        self._press_started_on_complete = False
        event.accept()


# ---------------------------------------------------------------------------
# NoteEditDialog
# ---------------------------------------------------------------------------


class NoteEditDialog(QDialog):
    """Modal form: create or edit a Note."""

    def __init__(self, note: Optional[Note] = None, parent=None):
        super().__init__(parent)
        self._creating = note is None
        self.note = note or Note()

        self.setWindowTitle("Nova nota" if self._creating else "Editar nota")
        self.setMinimumWidth(360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        # Title
        layout.addWidget(QLabel("Título:"))
        self.title_edit = QLineEdit(self.note.title)
        self.title_edit.setPlaceholderText("ex: Revisar PR #42")
        self.title_edit.setMaxLength(120)
        layout.addWidget(self.title_edit)

        # Body
        layout.addWidget(QLabel("Detalhes (opcional):"))
        self.body_edit = QPlainTextEdit(self.note.body)
        self.body_edit.setPlaceholderText("Notas, contexto, links...")
        self.body_edit.setMaximumHeight(120)
        layout.addWidget(self.body_edit)

        # Priority
        layout.addWidget(QLabel("Prioridade:"))
        self.priority_group = QButtonGroup(self)
        priority_row = QHBoxLayout()
        self._priority_buttons = {}
        for p in PRIORITIES:
            rb = QRadioButton(PRIORITY_LABEL[p])
            self._priority_buttons[p] = rb
            self.priority_group.addButton(rb)
            priority_row.addWidget(rb)
        priority_row.addStretch()
        layout.addLayout(priority_row)
        # Default selection
        current = self.note.priority if self.note.priority in PRIORITIES else PRIORITY_TODAY
        self._priority_buttons[current].setChecked(True)

        # Deadline
        deadline_row = QHBoxLayout()
        self.deadline_check = QCheckBox("Tem prazo:")
        self.deadline_edit = QDateTimeEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        existing = _parse_iso(self.note.deadline)
        if existing:
            self.deadline_check.setChecked(True)
            # Build QDateTime safely from components — passing a Python
            # datetime to QDateTime() works in some PyQt5 builds but not all,
            # and on bundled PyInstaller .exes this is a common crash source.
            self.deadline_edit.setDateTime(QDateTime(
                existing.year, existing.month, existing.day,
                existing.hour, existing.minute, existing.second
            ))
        else:
            self.deadline_check.setChecked(False)
            self.deadline_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
            self.deadline_edit.setEnabled(False)
        self.deadline_check.toggled.connect(self.deadline_edit.setEnabled)
        deadline_row.addWidget(self.deadline_check)
        deadline_row.addWidget(self.deadline_edit, 1)
        layout.addLayout(deadline_row)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if not self._creating:
            self.delete_btn = buttons.addButton("Excluir", QDialogButtonBox.DestructiveRole)
            self.delete_btn.clicked.connect(self._on_delete)
            self._delete_requested = False
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_delete(self):
        self._delete_requested = True
        self.done(QDialog.Accepted + 1)  # custom code interpretable by caller

    def collect(self) -> Note:
        """Read fields into the Note instance and return it."""
        self.note.title = self.title_edit.text().strip()
        self.note.body = self.body_edit.toPlainText().strip()
        for p, rb in self._priority_buttons.items():
            if rb.isChecked():
                self.note.priority = p
                break
        if self.deadline_check.isChecked():
            # Build ISO string via QDateTime.toString — avoids relying on
            # PyQt5's toPyDateTime() which behaves inconsistently across
            # bundled vs source builds.
            qdt = self.deadline_edit.dateTime()
            self.note.deadline = qdt.toString("yyyy-MM-ddTHH:mm:ss")
        else:
            self.note.deadline = None
        return self.note

    @property
    def delete_requested(self) -> bool:
        return getattr(self, "_delete_requested", False)


# ---------------------------------------------------------------------------
# NotesColumn
# ---------------------------------------------------------------------------


class NotesColumn(QWidget):
    """The column embedded next to the water bar.

    Hover anywhere over the column → expand width AND each card.
    Mouse leave → collapse back. Children handle their own clicks.
    """

    COLLAPSED_WIDTH = 44
    EXPANDED_WIDTH = 200

    notes_changed = pyqtSignal()       # let the overlay refresh tray tooltips, etc.
    geometry_changed = pyqtSignal(int) # emitted with the current width during animation

    def __init__(self, store: Optional[NotesStore] = None, parent=None):
        super().__init__(parent)
        self.store = store or NotesStore()
        self.expanded = False
        self.cards: List[NoteCard] = []

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.setAttribute(Qt.WA_StyledBackground, False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 4, 2, 4)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignTop)

        self._width_anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._width_anim.setDuration(280)
        self._width_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._width_anim.valueChanged.connect(self._on_width_anim_tick)

        # Debounced collapse: leaveEvent schedules a collapse, enterEvent
        # cancels it. Kills brief leave→enter flicker at edges and during
        # animation transitions.
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(180)
        self._collapse_timer.timeout.connect(lambda: self._set_expanded(False))

        # The "+" button is anchored to the TOP of the column so it never
        # moves when cards expand on hover (which would otherwise create a
        # nasty hover-flicker loop).
        self.add_btn = QPushButton("+", self)
        self.add_btn.setToolTip("Nova nota")
        self.add_btn.setFixedHeight(30)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(255, 244, 163, 130);"
            "  color: #7a6a20;"
            "  border: 1px solid rgba(180, 160, 60, 120);"
            "  border-radius: 5px;"
            "  font-size: 18px;"
            "  font-weight: bold;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(255, 244, 163, 230);"
            "  color: #4a3a00;"
            "  border: 1px solid rgba(180, 160, 60, 220);"
            "}"
            "QPushButton:pressed {"
            "  background: rgba(240, 220, 130, 240);"
            "}"
        )
        self.add_btn.clicked.connect(self._on_create)

        self.refresh()

    def _on_width_anim_tick(self, val):
        w = int(val)
        self.setMinimumWidth(w)
        self.geometry_changed.emit(w)

    # Public alias so the overlay context menu can trigger creation.
    def create_new_note(self):
        self._on_create()

    def refresh(self):
        """Rebuild the column from scratch. Cheap for small note counts."""
        # Clear every layout item (cards + add button + stretches).
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self.add_btn:
                widget.deleteLater()
        self.cards.clear()

        # Top: "+" button — fixed position, doesn't move when cards expand.
        self._layout.addWidget(self.add_btn)

        # Cards in priority order, below the +.
        for note in self.store.list_active():
            card = NoteCard(note, self)
            card.completed.connect(self._on_card_completed)
            card.edit_requested.connect(self._on_card_edit)
            card.set_expanded(self.expanded)
            self._layout.addWidget(card)
            self.cards.append(card)

        # Stretch at the bottom so cards stay anchored to the top.
        self._layout.addStretch(1)

    def _set_expanded(self, expanded: bool):
        if expanded == self.expanded:
            return
        self.expanded = expanded
        target = self.EXPANDED_WIDTH if expanded else self.COLLAPSED_WIDTH

        self._width_anim.stop()
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(target)
        self._width_anim.start()
        # Also set hard min so layout reflows immediately when shrinking
        self.setMaximumWidth(max(self.width(), target))

        for card in self.cards:
            card.set_expanded(expanded)

    def enterEvent(self, event):
        # Cancel any pending collapse (we're back inside the column).
        self._collapse_timer.stop()
        self._set_expanded(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Don't collapse immediately. If we re-enter within the debounce
        # window (mouse jitter, animation transition, brief excursion to a
        # child boundary), the timer is cancelled and the column stays open.
        self._collapse_timer.start()
        super().leaveEvent(event)

    # -- actions ---------------------------------------------------------

    def _on_card_completed(self, note_id: str):
        self.store.complete(note_id)
        self.refresh()
        self.notes_changed.emit()

    def _on_card_edit(self, note_id: str):
        note = next((n for n in self.store.notes if n.id == note_id), None)
        if note is None:
            return
        self._open_dialog(note, creating=False)

    def _on_create(self):
        self._open_dialog(Note(), creating=True)

    def _open_dialog(self, note: Note, creating: bool):
        # Parent intentionally None — the overlay uses Qt.Tool flags which
        # can interfere with modal dialog focus and lifecycle on Windows.
        # A standalone dialog is more predictable.
        dlg = NoteEditDialog(note, parent=None)
        result = dlg.exec_()
        if dlg.delete_requested and not creating:
            self.store.delete(note.id)
        elif result == QDialog.Accepted:
            updated = dlg.collect()
            if not updated.title.strip():
                # Empty title → ignore creation; for edits, keep old title untouched.
                if creating:
                    return
            if creating:
                self.store.add(updated)
            else:
                self.store.update(
                    updated.id,
                    title=updated.title,
                    body=updated.body,
                    priority=updated.priority,
                    deadline=updated.deadline,
                )
        else:
            return
        self.refresh()
        self.notes_changed.emit()
