# Water Intake Tracker

A desktop app that uses your webcam to detect when you drink water and tracks your daily hydration.

## Features

- Automatic drink detection using computer vision
- Daily progress tracking with visual overlay
- Reminder system that alerts you to drink
- Cup/bottle detection to reduce false positives
- Away detection (pauses when you leave your desk)

## Download

Download the latest release from the [Releases page](../../releases).

## Windows Security Note

When you first run the app, Windows SmartScreen may show a warning. This is normal for any software without an expensive code signing certificate.

**To run:**
1. Right-click `WaterIntakeTracker.exe`
2. Click **Properties**
3. Check **Unblock** at the bottom
4. Click **OK**
5. Double-click to run

Or when you see the blue SmartScreen:
- Click **More info** → **Run anyway**

## Requirements

- Windows 10/11
- Webcam

## Usage

1. Launch the app - a settings window will appear
2. Select your webcam and click **Test Camera** to verify
3. Configure your daily water goal
4. Click **Save & Start**

The app shows a progress bar on your screen:
- **Blue bar**: Your daily water intake progress
- **Green→Red bar**: Time since last drink (reminder)

**Controls:**
- Right-click for menu
- Double-click to undo last detection
- Drag to move the bar

## Building from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable
python build_exe.py
```

## License

MIT License - Feel free to use and modify!
