"""
Configuration defaults for Water Intake Tracker.

Pós-reformulação: webcam, IA, mascote, sub-barra de lembrete e
detecção de reunião foram removidos. As chaves correspondentes
podem ainda existir em user_config.json antigos (são ignoradas).
"""

CONFIG = {
    # Daily goal
    "goal_ml": 3000,           # Daily target in ml

    # Gulp amounts — main button = gulp; satellites = glass and bottle.
    "ml_per_gulp": 100,        # default click of the main button
    "ml_per_glass": 300,       # "copo" satellite
    "ml_per_bottle": 500,      # "garrafa" satellite

    # UI
    "bar_position": "right",   # legacy; unused after v2.2.0 (overlay is fixed corner)
    "bar_width": 30,           # legacy; unused after v2.2.0
    "bar_margin": 0,           # legacy; unused after v2.2.0
    "notes_visible": True,     # show notes column at startup

    # Sound
    "sound_enabled": True,
    "gulp_volume": 50,         # 0..100 — QSoundEffect volume
    "gulp_sound": "gulp.wav",
    "sounds_dir": "sounds",

    # Persistence
    "data_dir": "data",
    "progress_file": "progress.json",
}
