"""
Configuration defaults for Water Intake Tracker.

Pós-reformulação: webcam, IA, mascote, sub-barra de lembrete e
detecção de reunião foram removidos. As chaves correspondentes
podem ainda existir em user_config.json antigos (são ignoradas).

Persistência (v2.3.0): quando rodando como .exe (frozen), os dados
vivem em ``%APPDATA%/WaterIntakeTracker`` — fora do alcance do
uninstaller e gravável mesmo com o app em Program Files. Em dev,
continua ./data.
"""

import os
import sys


def _resolve_data_dir() -> str:
    """data/ local em dev; %APPDATA%\\WaterIntakeTracker\\data no .exe."""
    if getattr(sys, 'frozen', False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "WaterIntakeTracker", "data")
    return "data"


CONFIG = {
    # Daily goal
    "goal_ml": 3000,           # Daily target in ml

    # Gulp amounts — main button = gulp; satellites = glass and bottle.
    "ml_per_gulp": 100,        # default click of the main button
    "ml_per_glass": 300,       # "copo" satellite
    "ml_per_bottle": 500,      # "garrafa" satellite

    # UI
    "notes_visible": True,     # show notes column at startup

    # Sound
    "sound_enabled": True,
    "gulp_volume": 50,         # 0..100 — QSoundEffect volume
    "gulp_sound": "gulp.wav",
    "sounds_dir": "sounds",

    # Persistence
    "data_dir": _resolve_data_dir(),
    "progress_file": "progress.json",
    "history_file": "history.jsonl",   # append-only, um resumo por dia fechado
}
