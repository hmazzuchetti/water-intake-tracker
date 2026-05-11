"""
Gamification: XP, levels, streaks, achievements.

Cada gole vira XP. XP vira level. Bater meta diária vira bônus + streak.
Achievements destravam ao longo do tempo. Tudo persistido em data/game.json
(separado de progress.json e notes.json — ciclo de vida distinto, nunca
reseta).
"""

from __future__ import annotations

import json
import os
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from typing import List, Optional


# ─── Tuning ────────────────────────────────────────────────────────────────

XP_PER_GULP = 10
GOAL_BONUS_XP = 100      # bônus quando bate meta diária
STREAK_DAY_XP = 50       # bônus por dia consecutivo (a partir do 2º)


def level_from_xp(xp: int) -> int:
    """Quadratic curve — fica gostoso de evoluir cedo, mais espaçado depois."""
    return 1 + int(math.sqrt(max(0, xp) / 100))


def xp_for_level(level: int) -> int:
    """XP cumulativo necessário pra atingir esse level."""
    return ((level - 1) ** 2) * 100


# ─── State ─────────────────────────────────────────────────────────────────


@dataclass
class GameState:
    total_xp: int = 0
    total_gulps: int = 0           # all-time
    days_played: int = 0
    current_streak: int = 0        # dias consecutivos batendo meta
    best_streak: int = 0
    last_goal_date: str = ""       # ISO date — dia que mais recentemente bateu meta
    last_active_date: str = ""     # ISO date — dia que mais recentemente fez algo
    unlocked_achievements: List[str] = field(default_factory=list)


# ─── Achievements ──────────────────────────────────────────────────────────

# Cada achievement: id estável, nome curto, descrição, função de check.
# check recebe (state, ctx) onde ctx tem chaves: daily_gulps, daily_percentage,
# hour, etc. Retorna True se deve destravar.

ACHIEVEMENTS = [
    {"id": "first_sip", "name": "Primeiro Gole", "icon": "🥤",
     "desc": "Registrou seu primeiro gole",
     "check": lambda s, ctx: s.total_gulps >= 1},

    {"id": "hydrated", "name": "Hidratado", "icon": "💧",
     "desc": "10 goles num dia só",
     "check": lambda s, ctx: ctx.get("daily_gulps", 0) >= 10},

    {"id": "goal_smasher", "name": "Meta Batida", "icon": "🎯",
     "desc": "Atingiu a meta diária",
     "check": lambda s, ctx: ctx.get("daily_percentage", 0) >= 100},

    {"id": "double_goal", "name": "Camelo de Volta", "icon": "🐪",
     "desc": "200% da meta num dia",
     "check": lambda s, ctx: ctx.get("daily_percentage", 0) >= 200},

    {"id": "streak_3", "name": "Streak 3", "icon": "🔥",
     "desc": "3 dias seguidos batendo a meta",
     "check": lambda s, ctx: s.current_streak >= 3},

    {"id": "streak_7", "name": "Streak 7", "icon": "🔥🔥",
     "desc": "7 dias seguidos batendo a meta",
     "check": lambda s, ctx: s.current_streak >= 7},

    {"id": "streak_30", "name": "Streak 30", "icon": "🔥🔥🔥",
     "desc": "30 dias seguidos — você é uma máquina",
     "check": lambda s, ctx: s.current_streak >= 30},

    {"id": "centurion", "name": "Centurião", "icon": "💯",
     "desc": "100 goles totais",
     "check": lambda s, ctx: s.total_gulps >= 100},

    {"id": "millennial", "name": "Mil Goles", "icon": "🌊",
     "desc": "1000 goles totais",
     "check": lambda s, ctx: s.total_gulps >= 1000},

    {"id": "early_bird", "name": "Madrugador", "icon": "🌅",
     "desc": "Gole antes das 7h",
     "check": lambda s, ctx: ctx.get("hour", 12) < 7},

    {"id": "night_owl", "name": "Coruja", "icon": "🌙",
     "desc": "Gole depois das 23h",
     "check": lambda s, ctx: ctx.get("hour", 12) >= 23},

    {"id": "level_5", "name": "Nível 5", "icon": "⭐",
     "desc": "Atingiu nível 5",
     "check": lambda s, ctx: level_from_xp(s.total_xp) >= 5},

    {"id": "level_10", "name": "Nível 10", "icon": "⭐⭐",
     "desc": "Atingiu nível 10",
     "check": lambda s, ctx: level_from_xp(s.total_xp) >= 10},

    {"id": "level_25", "name": "Nível 25", "icon": "⭐⭐⭐",
     "desc": "Atingiu nível 25 — meio mestre",
     "check": lambda s, ctx: level_from_xp(s.total_xp) >= 25},
]


def get_achievement(achievement_id: str) -> Optional[dict]:
    for ach in ACHIEVEMENTS:
        if ach["id"] == achievement_id:
            return ach
    return None


# ─── Store ─────────────────────────────────────────────────────────────────


class GameStore:
    """JSON-backed gamification state. Append-only-ish (no reset). Cheap I/O."""

    def __init__(self, path: Optional[str] = None):
        if path is None:
            from config import CONFIG
            path = os.path.join(CONFIG.get("data_dir", "data"), "game.json")
        self.path = path
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.state = GameState()
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Be defensive: only keep known fields
            self.state = GameState(
                total_xp=int(data.get("total_xp", 0)),
                total_gulps=int(data.get("total_gulps", 0)),
                days_played=int(data.get("days_played", 0)),
                current_streak=int(data.get("current_streak", 0)),
                best_streak=int(data.get("best_streak", 0)),
                last_goal_date=str(data.get("last_goal_date", "")),
                last_active_date=str(data.get("last_active_date", "")),
                unlocked_achievements=list(data.get("unlocked_achievements", [])),
            )
        except (json.JSONDecodeError, IOError, ValueError) as e:
            print(f"[Game] Erro ao carregar {self.path}: {e}")

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.state), f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Game] Erro ao salvar: {e}")

    # ── Queries ────────────────────────────────────────────────────────

    def level(self) -> int:
        return level_from_xp(self.state.total_xp)

    def xp_in_level(self) -> int:
        cur_level = self.level()
        return self.state.total_xp - xp_for_level(cur_level)

    def xp_for_next_level(self) -> int:
        cur_level = self.level()
        return xp_for_level(cur_level + 1) - xp_for_level(cur_level)

    def level_progress(self) -> float:
        """0..1 progresso até o próximo level."""
        needed = self.xp_for_next_level()
        if needed <= 0:
            return 1.0
        return min(1.0, self.xp_in_level() / needed)

    # ── Mutation ───────────────────────────────────────────────────────

    def record_gulp(self, daily_gulps: int, daily_percentage: float) -> dict:
        """Aplica os efeitos de um gole. Retorna eventos pra UI animar.

        Eventos:
            xp_gained: int (total XP ganho neste evento, incluindo bônus)
            leveled_up: bool
            new_level: int (se leveled_up)
            unlocked: list[ach dict] (achievements destravados)
            streak_extended: bool
            goal_hit_now: bool (atingiu a meta neste gole)
        """
        events = {
            "xp_gained": 0,
            "leveled_up": False,
            "new_level": 0,
            "unlocked": [],
            "streak_extended": False,
            "goal_hit_now": False,
        }
        old_level = self.level()
        now = datetime.now()
        today_str = now.date().isoformat()

        # Base XP por gole
        self.state.total_xp += XP_PER_GULP
        events["xp_gained"] += XP_PER_GULP
        self.state.total_gulps += 1

        # Days played (se primeiro gole do dia)
        if self.state.last_active_date != today_str:
            self.state.days_played += 1
            self.state.last_active_date = today_str

        # Goal hit + streak (só conta uma vez por dia)
        if daily_percentage >= 100 and self.state.last_goal_date != today_str:
            self.state.total_xp += GOAL_BONUS_XP
            events["xp_gained"] += GOAL_BONUS_XP
            events["goal_hit_now"] = True

            # Streak: era ontem? incrementa. Senão, reseta pra 1.
            yesterday_iso = (now.date() - timedelta(days=1)).isoformat()
            if self.state.last_goal_date == yesterday_iso:
                self.state.current_streak += 1
            else:
                self.state.current_streak = 1

            if self.state.current_streak > self.state.best_streak:
                self.state.best_streak = self.state.current_streak

            # Bônus por dia de streak (a partir do segundo)
            if self.state.current_streak > 1:
                streak_bonus = STREAK_DAY_XP * (self.state.current_streak - 1)
                self.state.total_xp += streak_bonus
                events["xp_gained"] += streak_bonus
                events["streak_extended"] = True

            self.state.last_goal_date = today_str

        # Level up check (depois de todos os ganhos de XP)
        new_level = self.level()
        if new_level > old_level:
            events["leveled_up"] = True
            events["new_level"] = new_level

        # Achievement checks
        ctx = {
            "daily_gulps": daily_gulps,
            "daily_percentage": daily_percentage,
            "hour": now.hour,
        }
        for ach in ACHIEVEMENTS:
            if ach["id"] in self.state.unlocked_achievements:
                continue
            try:
                if ach["check"](self.state, ctx):
                    self.state.unlocked_achievements.append(ach["id"])
                    events["unlocked"].append(ach)
            except Exception:
                pass  # achievement checks devem ser robustas

        self.save()
        return events


# ─── Self-test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_path = "/tmp/game_test.json" if os.name != "nt" else "data/game_test.json"
    if os.path.exists(test_path):
        os.remove(test_path)
    g = GameStore(test_path)
    print(f"Start: lvl={g.level()}, xp={g.state.total_xp}")
    for i in range(1, 26):
        events = g.record_gulp(daily_gulps=i, daily_percentage=i * 4)
        if events["leveled_up"]:
            print(f"  Gulp {i}: LEVEL UP! now lvl {events['new_level']}")
        if events["unlocked"]:
            for a in events["unlocked"]:
                print(f"  Gulp {i}: ACHIEVEMENT! [{a['id']}] {a['name']}")
    print(f"End: lvl={g.level()}, xp={g.state.total_xp}, progress={g.level_progress():.0%}")
    print(f"Unlocked: {g.state.unlocked_achievements}")
    if os.path.exists(test_path):
        os.remove(test_path)
