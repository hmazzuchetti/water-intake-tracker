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
    "frames_to_confirm": 2,     # Consecutive frames to confirm gulp
    "proximity_threshold": 0.15, # Normalized hand-mouth distance
    "drinking_hand": "right",   # Which hand to track: "right", "left", or "both"
    "require_cup": True,        # Require cup/bottle detection for gulp detection

    # Other settings
    "sound_enabled": True,
    "camera_index": 0,         # Webcam index
    "away_timeout_seconds": 5, # Seconds without face before "away" mode
    "hover_opacity": 0.15,     # Bar opacity when hovering (0.0 - 1.0)

    # Reminder settings
    "reminder_interval_minutes": 30,  # Time between drink reminders
    "reminder_bar_width": 10,         # Width of the reminder bar
    "reminder_shake_threshold": 0.25, # Start shaking at 25%

    # Paths
    "data_dir": "data",
    "sounds_dir": "sounds",
    "progress_file": "progress.json",
    "gulp_sound": "gulp.wav",
}
