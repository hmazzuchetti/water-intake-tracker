"""
Configuration settings for Water Intake Tracker
"""

CONFIG = {
    # Daily goal
    "goal_ml": 3000,           # Daily target in ml
    "ml_per_gulp": 100,        # ML counted per detected gulp

    # UI settings
    "bar_position": "right",   # "left" or "right"
    "bar_width": 30,           # Width in pixels
    "bar_margin": 0,           # Margin from screen edge (0 = glued to side)

    # Detection settings
    "detection_interval": 300,  # ms between frame captures
    "cooldown_seconds": 10,      # Minimum time between gulps
    "frames_to_confirm": 1,     # Consecutive frames to confirm gulp (1=mais sensível, 3=mais robusto)
    "proximity_threshold": 0.20, # Normalized hand-mouth distance (0.20=mais longe OK, 0.12=precisa estar perto)
    "drinking_hand": "right",   # Which hand to track: "right", "left", or "both"
    "require_cup": True,        # Require cup/bottle detection for gulp detection
    "detection_sensitivity": "medium",  # "easy", "medium", or "strict" - quantos critérios precisa

    # Other settings
    "sound_enabled": True,
    "camera_index": 0,         # Webcam index
    "away_timeout_seconds": 5, # Seconds without face before "away" mode
    "hover_opacity": 0.15,     # Bar opacity when hovering (0.0 - 1.0)

    # Reminder settings
    "reminder_interval_minutes": 30,  # Time between drink reminders
    "reminder_bar_width": 10,         # Width of the reminder bar
    "reminder_shake_threshold": 0, # Start shaking at 25%

    # AI Messages settings
    "ai_messages_enabled": True,       # Enable AI-generated messages
    "ai_message_interval_minutes": 5,  # Time between random messages (DEBUG: 1 min, prod: 45)
    "ai_message_duration_seconds": 8,  # How long to show each message
    "ai_personality_file": "personalities/default.txt",
    "ai_ollama_model": "llama3.1:latest",  # Lightweight Ollama model
    "mascot_enabled": True,            # Show mascot with messages
    "mascot_file": "mascots/default.png",  # Path to mascot image
    "mascot_sound": "pop.wav",         # Default sound when mascot appears
    "mascot_size": 300,                # Max size in pixels (square)

    # Sons por tipo de mensagem
    "sound_celebration": "celebration.wav",  # Meta atingida
    "sound_reminder": "reminder.wav",        # Lembrete
    "sound_achievement": "achievement.wav",  # Conquistas/milestones
    "sound_normal": "pop.wav",               # Mensagens normais
    "sound_funny": "funny.wav",              # Mensagens engraçadas

    # Paths
    "data_dir": "data",
    "sounds_dir": "sounds",
    "progress_file": "progress.json",
    "gulp_sound": "gulp.wav",
}
