"""
Sticky notes model + storage.

Notas ficam em data/notes.json (separado de progress.json para não
serem afetadas pelo reset diário). Três níveis de prioridade —
"now" (Agora), "today" (Hoje), "later" (Depois) — porque seis
níveis (P0–P5) viram tudo P3 na prática para uso pessoal.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional


PRIORITY_NOW = "now"
PRIORITY_TODAY = "today"
PRIORITY_LATER = "later"
PRIORITIES = (PRIORITY_NOW, PRIORITY_TODAY, PRIORITY_LATER)

PRIORITY_ORDER = {
    PRIORITY_NOW: 0,
    PRIORITY_TODAY: 1,
    PRIORITY_LATER: 2,
}

PRIORITY_LABEL = {
    PRIORITY_NOW: "Agora",
    PRIORITY_TODAY: "Hoje",
    PRIORITY_LATER: "Depois",
}

# Hex colors used for the left border indicator on each card.
PRIORITY_COLOR = {
    PRIORITY_NOW: "#E74C3C",
    PRIORITY_TODAY: "#F39C12",
    PRIORITY_LATER: "#95A5A6",
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Note:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    body: str = ""
    priority: str = PRIORITY_TODAY
    deadline: Optional[str] = None     # ISO 8601 string or None
    created_at: str = field(default_factory=_now_iso)
    completed_at: Optional[str] = None

    def is_done(self) -> bool:
        return self.completed_at is not None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        # Tolerate unknown / missing keys.
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            title=data.get("title", ""),
            body=data.get("body", ""),
            priority=data.get("priority", PRIORITY_TODAY) if data.get("priority") in PRIORITIES else PRIORITY_TODAY,
            deadline=data.get("deadline"),
            created_at=data.get("created_at") or _now_iso(),
            completed_at=data.get("completed_at"),
        )

    def sort_key(self):
        """Lower = closer to top of the column.

        Order: by priority bucket, then by deadline (sooner first;
        notes without deadline come after dated ones inside the same
        bucket), then by creation time (oldest first as a tie-breaker).
        """
        return (
            PRIORITY_ORDER.get(self.priority, 99),
            self.deadline or "9999-12-31T23:59:59",
            self.created_at,
        )


class NotesStore:
    """JSON-backed CRUD for sticky notes. No daily reset."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Optional[str] = None):
        if path is None:
            from config import CONFIG
            path = os.path.join(CONFIG.get("data_dir", "data"), "notes.json")
        self.path = path
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.notes: List[Note] = []
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.notes = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_notes = data.get("notes", []) if isinstance(data, dict) else []
            self.notes = [Note.from_dict(n) for n in raw_notes]
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Notes] Erro ao carregar {self.path}: {e}")
            self.notes = []

    def save(self) -> None:
        try:
            payload = {
                "version": self.SCHEMA_VERSION,
                "notes": [n.to_dict() for n in self.notes],
            }
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Notes] Erro ao salvar: {e}")

    def add(self, note: Note) -> None:
        self.notes.append(note)
        self.save()

    def update(self, note_id: str, **fields) -> Optional[Note]:
        for n in self.notes:
            if n.id == note_id:
                for k, v in fields.items():
                    if hasattr(n, k):
                        setattr(n, k, v)
                self.save()
                return n
        return None

    def delete(self, note_id: str) -> bool:
        for i, n in enumerate(self.notes):
            if n.id == note_id:
                del self.notes[i]
                self.save()
                return True
        return False

    def complete(self, note_id: str) -> Optional[Note]:
        return self.update(note_id, completed_at=_now_iso())

    def reopen(self, note_id: str) -> Optional[Note]:
        return self.update(note_id, completed_at=None)

    def list_active(self) -> List[Note]:
        return sorted([n for n in self.notes if not n.is_done()], key=lambda n: n.sort_key())

    def list_completed(self) -> List[Note]:
        return sorted(
            [n for n in self.notes if n.is_done()],
            key=lambda n: n.completed_at or "",
            reverse=True
        )


if __name__ == "__main__":
    # quick manual test
    store = NotesStore("/tmp/notes_test.json" if os.name != "nt" else "data/notes_test.json")
    store.notes = []
    store.add(Note(title="Comprar pão", priority=PRIORITY_TODAY))
    store.add(Note(title="Pagar IPVA", priority=PRIORITY_NOW, deadline="2026-05-10T18:00:00"))
    store.add(Note(title="Estudar Rust", priority=PRIORITY_LATER))
    for n in store.list_active():
        print(f"[{PRIORITY_LABEL[n.priority]}] {n.title} (deadline={n.deadline})")
