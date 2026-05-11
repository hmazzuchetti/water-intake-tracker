"""
StatsDialog — janelinha de "menu de game".

Mostra level + barra de XP + grid de achievements (destravados em cor,
locked em cinza). Aberto via tray menu ou right-click no overlay.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QGridLayout, QProgressBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from game import GameStore, ACHIEVEMENTS, level_from_xp


class _AchievementCard(QFrame):
    """One achievement tile (locked or unlocked)."""

    def __init__(self, achievement: dict, unlocked: bool, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

        if unlocked:
            self.setStyleSheet(
                "QFrame { background: #FFF4A3; border: 1px solid #C9B260;"
                "         border-radius: 8px; padding: 6px; }"
            )
            text_color = "#2c2400"
            sub_color = "#5a4a00"
        else:
            self.setStyleSheet(
                "QFrame { background: #2a2a2a; border: 1px solid #444;"
                "         border-radius: 8px; padding: 6px; }"
            )
            text_color = "#888"
            sub_color = "#666"

        v = QVBoxLayout(self)
        v.setSpacing(2)

        head = QHBoxLayout()
        icon = QLabel(achievement.get("icon", "*"))
        icon.setFont(QFont("Segoe UI Emoji", 16))
        head.addWidget(icon)
        title = QLabel(achievement["name"])
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setStyleSheet(f"color: {text_color};")
        head.addWidget(title, 1)
        v.addLayout(head)

        desc = QLabel(achievement["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {sub_color}; font-size: 11px;")
        v.addWidget(desc)


class StatsDialog(QDialog):
    """Game stats + achievements modal."""

    def __init__(self, game_store: GameStore, storage, parent=None):
        super().__init__(parent)
        self.game = game_store
        self.storage = storage

        self.setWindowTitle("Estatísticas — Water Tracker")
        self.setMinimumWidth(540)
        self.setMinimumHeight(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Header: Level + XP bar ──────────────────────────────────────
        level = self.game.level()
        xp_in = self.game.xp_in_level()
        xp_total_for_level = self.game.xp_for_next_level()

        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0 y1:0 x2:0 y2:1,"
            "         stop:0 #3a78cc, stop:1 #1d4ea0);"
            "         border-radius: 10px; padding: 14px; }"
        )
        hf = QVBoxLayout(header_frame)

        lvl_row = QHBoxLayout()
        lvl_label = QLabel(f"Nível {level}")
        lvl_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        lvl_label.setStyleSheet("color: white;")
        lvl_row.addWidget(lvl_label)
        lvl_row.addStretch()
        xp_label = QLabel(f"{self.game.state.total_xp} XP total")
        xp_label.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px;")
        lvl_row.addWidget(xp_label)
        hf.addLayout(lvl_row)

        prog = QProgressBar()
        prog.setMinimum(0)
        prog.setMaximum(max(1, xp_total_for_level))
        prog.setValue(xp_in)
        prog.setFormat(f"%v / %m XP (próximo: nível {level + 1})")
        prog.setTextVisible(True)
        prog.setStyleSheet(
            "QProgressBar { background: rgba(0,0,0,0.3); border: none;"
            "               border-radius: 6px; height: 22px;"
            "               color: white; font-size: 11px;"
            "               text-align: center; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0 y1:0 x2:1 y2:0,"
            "                      stop:0 #ffd700, stop:1 #ffac3a);"
            "                      border-radius: 6px; }"
        )
        hf.addWidget(prog)

        layout.addWidget(header_frame)

        # ── Stats grid ──────────────────────────────────────────────────
        stats_box = QFrame()
        stats_box.setStyleSheet(
            "QFrame { background: #1f1f1f; border-radius: 8px; padding: 10px; }"
        )
        sg = QGridLayout(stats_box)

        def stat(row: int, col: int, label: str, value: str, accent: str = "#80cfff"):
            sg.addWidget(self._stat_label(label), row * 2, col)
            sg.addWidget(self._stat_value(value, accent), row * 2 + 1, col)

        stat(0, 0, "Goles totais", str(self.game.state.total_gulps))
        stat(0, 1, "Dias trackeados", str(self.game.state.days_played))
        stat(1, 0, "Streak atual", f"{self.game.state.current_streak} dias", "#ff8c4a")
        stat(1, 1, "Melhor streak", f"{self.game.state.best_streak} dias", "#ffd700")

        today_ml, goal_ml, today_pct = self.storage.get_progress()
        today_gulps = self.storage.get_glasses()
        stat(2, 0, "Hoje", f"{today_gulps} goles ({today_pct:.0f}%)", "#80cfff")
        stat(2, 1, "Meta diária", f"{goal_ml}ml", "#80cfff")

        layout.addWidget(stats_box)

        # ── Achievements section ────────────────────────────────────────
        ach_title = QLabel("Conquistas")
        ach_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        ach_title.setStyleSheet("color: #ddd; margin-top: 6px;")
        layout.addWidget(ach_title)

        unlocked_count = len(self.game.state.unlocked_achievements)
        total = len(ACHIEVEMENTS)
        ach_sub = QLabel(f"{unlocked_count} de {total} destravadas")
        ach_sub.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(ach_sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        ach_container = QWidget()
        ach_grid = QGridLayout(ach_container)
        ach_grid.setSpacing(8)

        for idx, ach in enumerate(ACHIEVEMENTS):
            row, col = divmod(idx, 2)
            unlocked = ach["id"] in self.game.state.unlocked_achievements
            ach_grid.addWidget(_AchievementCard(ach, unlocked), row, col)

        scroll.setWidget(ach_container)
        layout.addWidget(scroll, 1)

        # Close
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _stat_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #888; font-size: 11px;")
        return lbl

    def _stat_value(self, text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        return lbl
