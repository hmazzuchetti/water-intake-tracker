"""
Configuration defaults for Water Intake Tracker.

Pós-reformulação: webcam, IA, mascote, sub-barra de lembrete e
detecção de reunião foram removidos. As chaves correspondentes
podem ainda existir em user_config.json antigos (são ignoradas).
"""

CONFIG = {
    # Daily goal
    "goal_ml": 3000,           # Daily target in ml
    "ml_per_gulp": 100,        # ml counted per click on the gulp button

    # UI
    "bar_position": "right",   # "left" or "right"
    "bar_width": 30,           # Width in pixels
    "bar_margin": 0,           # Margin from screen edge (0 = glued to side)

    # Sound
    "sound_enabled": True,
    "gulp_volume": 50,         # 0..100 — QSoundEffect volume
    "gulp_sound": "gulp.wav",
    "sounds_dir": "sounds",

    # Persistence
    "data_dir": "data",
    "progress_file": "progress.json",
}
