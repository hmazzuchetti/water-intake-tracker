"""
Storage module for persisting daily water intake progress
"""

import json
import os
from datetime import datetime
from config import CONFIG


class Storage:
    def __init__(self):
        self.data_dir = CONFIG["data_dir"]
        self.progress_file = os.path.join(self.data_dir, CONFIG["progress_file"])
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

    def _load(self) -> dict:
        """Load progress from file or create new if doesn't exist/new day"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if it's a new day - reset if so
                if data.get("date") != self._get_today():
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

        # Check for day change
        if self.data["date"] != self._get_today():
            self.data = self._default_data()

        self.data["glasses"] += 1
        self.data["ml_total"] += ml
        self.data["history"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "ml": ml
        })

        self.save()

    def get_progress(self) -> tuple:
        """Get current progress (ml_total, goal_ml, percentage)"""
        # Check for day change
        if self.data["date"] != self._get_today():
            self.data = self._default_data()

        ml_total = self.data["ml_total"]
        goal = CONFIG["goal_ml"]
        percentage = min(100, (ml_total / goal) * 100)

        return ml_total, goal, percentage

    def reset(self):
        """Reset today's progress"""
        self.data = self._default_data()
        self.save()

    def undo_gulp(self) -> bool:
        """Remove the last gulp. Returns True if successful."""
        if self.data["date"] != self._get_today():
            self.data = self._default_data()
            return False

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
        if self.data["date"] != self._get_today():
            self.data = self._default_data()
        return self.data["glasses"]


if __name__ == "__main__":
    # Test storage
    storage = Storage()
    print(f"Current progress: {storage.get_progress()}")
    print(f"Glasses: {storage.get_glasses()}")

    # Test adding a gulp
    storage.add_gulp()
    print(f"After gulp: {storage.get_progress()}")
