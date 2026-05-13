"""
Compact overlay window for Water Intake Tracker.

Pós v2.2.0: a barra de água vertical foi removida. O overlay agora é
um widget pequeno no canto inferior direito da tela, contendo apenas:

  - GulpControlWidget (main button + 4 satellites)
  - NotesColumn (esquerda, hover-expand, ocultável)

Sem ondas, sem bolhas, sem altura total da tela. Clicker-hero feel.
"""

import math
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMenu, QAction
)
from PyQt5.QtCore import Qt, QPoint, QPointF, QTimer, pyqtSignal, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QPainterPath
)

from config import CONFIG
from storage import Storage
from notes import NotesStore
from notes_ui import NotesColumn
from game import GameStore
from gulp_control_ui import GulpControlWidget


class ProgressBarOverlay(QWidget):
    """Compact overlay window. Hosts the gulp control + notes column.

    The class name is kept for backwards compatibility, even though it no
    longer paints a progress bar — main.py and other consumers still call
    ProgressBarOverlay()."""

    # Signals
    gulp_registered = pyqtSignal()
    settings_requested = pyqtSignal()

    # Layout constants
    MARGIN_FROM_SCREEN = 16
    HORIZONTAL_GAP = 8         # gap between notes column and gulp control

    def __init__(self, storage: Storage = None, notes_store: NotesStore = None,
                 game_store: GameStore = None):
        super().__init__()
        self.storage = storage or Storage()
        self.notes_store = notes_store or NotesStore()
        self.game_store = game_store or GameStore()

        # Drag-the-window state (right-click area or empty corner drag)
        self.drag_position = QPoint()
        self.dragging = False
        self.click_start_global = QPoint()
        self.click_drag_threshold = 5

        # Notes column visibility (persisted via in-memory state for now)
        self.notes_visible = bool(CONFIG.get("notes_visible", True))

        # Click ripples (used over the main button area)
        self.ripples = []
        self.ripple_max_age = 25

        # Latest events from GameStore for main.py to surface as notifications
        self.recent_events: dict = {}

        self._setup_window()
        self._build_children()
        self._setup_geometry()

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start(50)  # 20 FPS — drives ripples only

    # ─── Setup ─────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

    def _build_children(self):
        # Gulp control (main button + satellites)
        self.gulp_control = GulpControlWidget(self.storage, self.game_store, parent=self)
        self.gulp_control.gulp_registered.connect(self._on_gulp_amount)
        self.gulp_control.notes_toggle_requested.connect(self._toggle_notes_visibility)

        # Notes column
        self.notes_column = NotesColumn(self.notes_store, parent=self)
        self.notes_column.geometry_changed.connect(self._relayout_notes_column)

        if not self.notes_visible:
            self.notes_column.hide()

    def _setup_geometry(self):
        """Size the overlay and place it. Tries saved (x, y) from config
        first; falls back to bottom-right of the screen *available* area
        (which excludes the Windows taskbar). Always clamps to safe bounds."""
        gulp_w = self.gulp_control.width()
        gulp_h = self.gulp_control.height()

        # Reserve room for notes (even when collapsed/hidden) so geometry
        # doesn't reflow when the user toggles them.
        notes_reserved_w = NotesColumn.EXPANDED_WIDTH

        total_w = notes_reserved_w + self.HORIZONTAL_GAP + gulp_w
        total_h = gulp_h

        # Find target position: saved one, or default bottom-right of available area
        saved_x = CONFIG.get("overlay_x", None)
        saved_y = CONFIG.get("overlay_y", None)
        x, y = self._compute_position(total_w, total_h, saved_x, saved_y)

        self.setGeometry(x, y, total_w, total_h)

        # Place gulp control flush right
        self.gulp_control.move(total_w - gulp_w, 0)

        # Notes column starts at far-left of overlay
        self._relayout_notes_column(NotesColumn.COLLAPSED_WIDTH)
        self.notes_column.show() if self.notes_visible else self.notes_column.hide()

    def _available_screen(self):
        """Usable screen rect — excludes the Windows taskbar and reserved
        system areas. Falls back to full geometry if unavailable."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return None
        try:
            return screen.availableGeometry()
        except Exception:
            return screen.geometry()

    def _compute_position(self, w: int, h: int, saved_x, saved_y):
        """Decide where to place the overlay. Honors saved coords if they
        keep the overlay sufficiently on-screen; otherwise snaps to the
        bottom-right of the available area."""
        avail = self._available_screen()
        if avail is None:
            # Without screen info, just put it at 0,0 — won't crash.
            return 0, 0

        # Default bottom-right inside available area (taskbar respected).
        default_x = avail.right() - w - self.MARGIN_FROM_SCREEN + 1
        default_y = avail.bottom() - h - self.MARGIN_FROM_SCREEN + 1

        if isinstance(saved_x, int) and isinstance(saved_y, int):
            x, y = self._clamp_to_safe(saved_x, saved_y, w, h)
            return x, y
        return default_x, default_y

    def _clamp_to_safe(self, x: int, y: int, w: int, h: int):
        """Ensure at least 100×100 of the overlay stays inside the available
        screen, even if user drags toward the edges."""
        avail = self._available_screen()
        if avail is None:
            return x, y
        VISIBLE_MIN = 100
        min_x = avail.left() - (w - VISIBLE_MIN)
        max_x = avail.right() - VISIBLE_MIN + 1
        min_y = avail.top() - (h - VISIBLE_MIN)
        max_y = avail.bottom() - VISIBLE_MIN + 1
        x = max(min_x, min(x, max_x))
        y = max(min_y, min(y, max_y))
        return int(x), int(y)

    def reset_position(self):
        """Snap back to the default bottom-right corner of the available
        screen area. Useful when the overlay ends up somewhere awkward."""
        avail = self._available_screen()
        if avail is None:
            return
        w, h = self.width(), self.height()
        x = avail.right() - w - self.MARGIN_FROM_SCREEN + 1
        y = avail.bottom() - h - self.MARGIN_FROM_SCREEN + 1
        self.move(x, y)
        self._save_position(x, y)

    def _relayout_notes_column(self, current_width: int):
        """Keep the notes column right-aligned to its reserved slot, just
        left of the gulp control widget."""
        if not hasattr(self, "notes_column"):
            return
        gulp_w = self.gulp_control.width()
        col_h = self.height()
        reserved_right = self.width() - gulp_w - self.HORIZONTAL_GAP
        x = reserved_right - current_width
        self.notes_column.setGeometry(x, 0, current_width, col_h)

    # ─── Notes visibility toggle ──────────────────────────────────────

    def _toggle_notes_visibility(self):
        self.notes_visible = not self.notes_visible
        if self.notes_visible:
            self.notes_column.show()
            self.notes_column.refresh()
        else:
            self.notes_column.hide()
        # Persist preference
        try:
            CONFIG["notes_visible"] = self.notes_visible
            from settings_ui import load_user_config, save_user_config
            cfg = load_user_config()
            cfg["notes_visible"] = self.notes_visible
            save_user_config(cfg)
        except Exception:
            pass
        self.update()

    # ─── Gulp registration ─────────────────────────────────────────────

    def _on_gulp_amount(self, ml: int):
        """A gulp of `ml` milliliters was requested via the gulp control."""
        try:
            self.storage.add_gulp(ml)
        except Exception as e:
            print(f"[Storage] Erro ao registrar gole: {e}")
            return

        # Game state update
        events = {}
        try:
            _, _, pct = self.storage.get_progress()
            daily_gulps = self.storage.get_glasses()
            events = self.game_store.record_gulp(daily_gulps, pct)
        except Exception as e:
            print(f"[Game] Erro: {e}")
        self.recent_events = events

        # Tell the button to animate
        self.gulp_control.trigger_gulp_animation(events)

        # Ripple at the main button center (widget coords)
        try:
            btn_local_center = self.gulp_control.main_btn.geometry().center() + self.gulp_control.pos()
            self.ripples.append({
                "x": float(btn_local_center.x()),
                "y": float(btn_local_center.y()),
                "age": 0
            })
        except Exception:
            pass

        self.gulp_registered.emit()

    # ─── Animation tick — just ripples now ─────────────────────────────

    def _animate(self):
        if self.ripples:
            for r in self.ripples:
                r["age"] += 1
            self.ripples = [r for r in self.ripples if r["age"] < self.ripple_max_age]
            self.update()

    # ─── Paint — only ripples; children paint themselves ──────────────

    def paintEvent(self, event):
        if not self.ripples:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.NoBrush)
        for r in self.ripples:
            progress = r["age"] / self.ripple_max_age
            radius = 6 + progress * 40
            alpha = int(180 * (1.0 - progress))
            if alpha <= 0:
                continue
            painter.setPen(QPen(QColor(180, 230, 255, alpha), 2))
            painter.drawEllipse(QRectF(
                r["x"] - radius, r["y"] - radius,
                radius * 2, radius * 2
            ))

    # ─── Window-level mouse: drag from empty area; right-click menu ────

    def _is_interactive_pos(self, pos) -> bool:
        """True if pos lies on any child widget that takes its own events.
        Used to decide whether mouse events here belong to the overlay
        (window drag, context menu) or should be passed through."""
        children = [self.gulp_control]
        if self.notes_visible:
            children.append(self.notes_column)
        for ch in children:
            if ch.isVisible() and ch.geometry().contains(pos):
                return True
        return False

    def mousePressEvent(self, event):
        # Right-click anywhere on the overlay → context menu
        if event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
            return

        # Left-click on an empty area → potential window drag
        if event.button() == Qt.LeftButton and not self._is_interactive_pos(event.pos()):
            self.click_start_global = event.globalPos()
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.dragging:
            moved = (event.globalPos() - self.click_start_global).manhattanLength()
            if moved >= self.click_drag_threshold:
                self.dragging = True
        if self.dragging:
            target = event.globalPos() - self.drag_position
            x, y = self._clamp_to_safe(target.x(), target.y(),
                                       self.width(), self.height())
            self.move(x, y)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.dragging:
            # Persist the new position so next launch starts here.
            self._save_position(self.x(), self.y())
        self.dragging = False

    def _save_position(self, x: int, y: int):
        """Persist overlay coordinates to user_config so they survive a
        restart. Clamps first as a defensive measure."""
        x, y = self._clamp_to_safe(x, y, self.width(), self.height())
        try:
            CONFIG["overlay_x"] = int(x)
            CONFIG["overlay_y"] = int(y)
            from settings_ui import load_user_config, save_user_config
            cfg = load_user_config()
            cfg["overlay_x"] = int(x)
            cfg["overlay_y"] = int(y)
            save_user_config(cfg)
        except Exception as e:
            print(f"[Overlay] Erro ao salvar posição: {e}")

    # ─── Context menu (right-click) ────────────────────────────────────

    def _show_context_menu(self, position):
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

        toggle_notes_action = QAction(
            "Esconder notas" if self.notes_visible else "Mostrar notas", self
        )
        toggle_notes_action.triggered.connect(self._toggle_notes_visibility)
        menu.addAction(toggle_notes_action)

        reset_pos_action = QAction("📍 Resetar posição", self)
        reset_pos_action.triggered.connect(self.reset_position)
        menu.addAction(reset_pos_action)

        menu.addSeparator()

        add_action = QAction("Add gulp (manual)", self)
        add_action.triggered.connect(self._manual_add_gulp)
        menu.addAction(add_action)

        undo_action = QAction("Undo last gulp", self)
        undo_action.triggered.connect(self._undo_gulp)
        if self.storage.get_glasses() == 0:
            undo_action.setEnabled(False)
        menu.addAction(undo_action)

        menu.addSeparator()

        reset_action = QAction("Reset today", self)
        reset_action.triggered.connect(self._reset_progress)
        menu.addAction(reset_action)

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
        ml = CONFIG.get("ml_per_gulp", 100)
        self._on_gulp_amount(ml)

    def _undo_gulp(self):
        if self.storage.undo_gulp():
            print("[UNDO] Removed last gulp")
            self.update()
            self.gulp_control.main_btn.update()

    def _open_new_note(self):
        if hasattr(self, "notes_column"):
            if not self.notes_visible:
                self._toggle_notes_visibility()  # show first
            self.notes_column.create_new_note()

    def _open_stats(self):
        try:
            from game_ui import StatsDialog
            dlg = StatsDialog(self.game_store, self.storage, parent=None)
            dlg.exec_()
        except Exception as e:
            print(f"[Stats] Erro: {e}")

    def _reset_progress(self):
        self.storage.reset()
        self.update()
        self.gulp_control.main_btn.update()

    def _open_settings(self):
        self.settings_requested.emit()

    # ─── Settings hot-reload after config changes ──────────────────────

    def reload_after_settings(self):
        """Called by main.py after the settings dialog saves. Re-reads any
        live-updatable values."""
        self.gulp_control.refresh_tooltips()


def main():
    """Standalone test of the overlay."""
    import sys
    app = QApplication(sys.argv)
    overlay = ProgressBarOverlay()
    overlay.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
