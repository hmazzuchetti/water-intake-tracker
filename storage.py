"""
Storage module for persisting daily water intake progress.

v2.3.0: rollover de dia centralizado em _ensure_today(), que ARQUIVA o
dia encerrado em data/history.jsonl (append-only, uma linha JSON por dia)
antes de resetar. Antes disso, o dia anterior era simplesmente descartado
— zero memória histórica.
"""

import json
import os
from datetime import datetime
from config import CONFIG


class Storage:
    def __init__(self):
        self.data_dir = CONFIG["data_dir"]
        self.progress_file = os.path.join(self.data_dir, CONFIG["progress_file"])
        self.history_file = os.path.join(self.data_dir, CONFIG.get("history_file", "history.jsonl"))
        self._ensure_data_dir()
        self.data = self._load()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_today(self) -> str:
        """Get today's date as string"""
        return datetime.now().strftime("%Y-%m-%d")

    def _default_data(self) -> dict:
        """Return default data structure for a new day"""
        return {
            "date": self._get_today(),
            "glasses": 0,
            "ml_total": 0,
            "history": []
        }

    def _archive_day(self, day_data: dict):
        """Append o resumo de um dia encerrado em history.jsonl.
        Dias sem gole não geram linha (não há o que lembrar)."""
        if not day_data.get("glasses"):
            return
        goal = CONFIG.get("goal_ml", 3000)
        summary = {
            "date": day_data.get("date"),
            "ml_total": day_data.get("ml_total", 0),
            "glasses": day_data.get("glasses", 0),
            "goal_ml": goal,
            "pct": round(day_data.get("ml_total", 0) / goal * 100, 1) if goal else 0,
        }
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        except IOError as e:
            print(f"[Storage] Erro ao arquivar dia: {e}")

    def _ensure_today(self):
        """Ponto único de rollover: se o dado em memória é de outro dia,
        arquiva esse dia e começa um novo. Persiste imediatamente para que
        um crash pós-meia-noite não deixe progress.json no dia velho."""
        if self.data.get("date") != self._get_today():
            self._archive_day(self.data)
            self.data = self._default_data()
            self.save()

    def _load(self) -> dict:
        """Load progress from file; archive + reset if it's from a past day."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if data.get("date") != self._get_today():
                    self._archive_day(data)
                    return self._default_data()

                return data
            except (json.JSONDecodeError, IOError):
                return self._default_data()

        return self._default_data()

    def save(self):
        """Save current progress to file"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving progress: {e}")

    def add_gulp(self, ml: int = None):
        """Add a gulp to today's progress"""
        if ml is None:
            ml = CONFIG["ml_per_gulp"]

        self._ensure_today()

        self.data["glasses"] += 1
        self.data["ml_total"] += ml
        self.data["history"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "ml": ml
        })

        self.save()

    def get_progress(self) -> tuple:
        """Get current progress (ml_total, goal_ml, percentage).

        percentage é o valor REAL, sem cap — pode passar de 100. Quem
        desenha o anel clampa na renderização. O cap antigo aqui tornava
        o achievement de 200% matematicamente impossível."""
        self._ensure_today()

        ml_total = self.data["ml_total"]
        goal = CONFIG["goal_ml"]
        percentage = (ml_total / goal) * 100 if goal else 0.0

        return ml_total, goal, percentage

    def minutes_since_last_gulp(self):
        """Minutos desde o último gole de HOJE, ou None se ainda não houve.
        Usado pelo botão pra 'secar' visualmente com o tempo."""
        self._ensure_today()
        if not self.data["history"]:
            return None
        last_time = self.data["history"][-1].get("time")
        try:
            t = datetime.strptime(last_time, "%H:%M:%S").time()
            last_dt = datetime.combine(datetime.now().date(), t)
            delta = (datetime.now() - last_dt).total_seconds() / 60.0
            return max(0.0, delta)
        except (ValueError, TypeError):
            return None

    def reset(self):
        """Reset today's progress"""
        self.data = self._default_data()
        self.save()

    def undo_gulp(self) -> bool:
        """Remove the last gulp. Returns True if successful."""
        self._ensure_today()

        if self.data["glasses"] <= 0 or not self.data["history"]:
            return False

        # Remove last entry
        last_gulp = self.data["history"].pop()
        self.data["glasses"] -= 1
        self.data["ml_total"] -= last_gulp["ml"]

        # Ensure we don't go negative
        self.data["ml_total"] = max(0, self.data["ml_total"])
        self.data["glasses"] = max(0, self.data["glasses"])

        self.save()
        return True

    def get_glasses(self) -> int:
        """Get number of glasses/gulps today"""
        self._ensure_today()
        return self.data["glasses"]


if __name__ == "__main__":
    # Test storage
    storage = Storage()
    print(f"Current progress: {storage.get_progress()}")
    print(f"Glasses: {storage.get_glasses()}")

    # Test adding a gulp
    storage.add_gulp()
    print(f"After gulp: {storage.get_progress()}")
    print(f"Minutes since last gulp: {storage.minutes_since_last_gulp()}")
