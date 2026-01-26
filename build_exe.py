"""
Build script for creating Water Intake Tracker executable

Requirements:
    pip install pyinstaller pillow

Usage:
    python build_exe.py
"""

import subprocess
import sys
import os


def convert_icon():
    """Convert webp icon to ico if needed"""
    # Check for source files
    source_files = ['icon.webp', 'dist/icon.webp']
    source_path = None

    for path in source_files:
        if os.path.exists(path):
            source_path = path
            break

    if not source_path:
        print("No icon.webp found - building without custom icon")
        return None

    if os.path.exists('icon.ico'):
        print("icon.ico already exists")
        return 'icon.ico'

    try:
        from PIL import Image
    except ImportError:
        print("Installing Pillow for icon conversion...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image

    print(f"Converting {source_path} to icon.ico...")

    try:
        img = Image.open(source_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        images = [img.resize(size, Image.Resampling.LANCZOS) for size in sizes]

        images[0].save(
            'icon.ico',
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        print("Icon converted successfully")
        return 'icon.ico'
    except Exception as e:
        print(f"Could not convert icon: {e}")
        return None


def main():
    print("=" * 50)
    print("Building Water Intake Tracker Executable")
    print("=" * 50)

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Convert icon
    icon_path = convert_icon()

    # Build using spec file if it exists (preferred method)
    if os.path.exists("WaterIntakeTracker.spec"):
        print("\nUsing WaterIntakeTracker.spec file...")
        cmd = [sys.executable, "-m", "PyInstaller", "WaterIntakeTracker.spec", "--noconfirm"]
    else:
        # Build command (fallback)
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name=WaterIntakeTracker",
            "--onefile",              # Single executable
            "--windowed",             # No console window
            "--add-data=sounds;sounds",  # Include sounds folder
            "--add-data=data;data",      # Include data folder
            "--hidden-import=winsound",
            "--hidden-import=mediapipe",
            "--hidden-import=cv2",
            "--hidden-import=PyQt5",
            "--collect-data=mediapipe",
        ]

        # Add icon if available
        if icon_path:
            cmd.append(f"--icon={icon_path}")
        else:
            cmd.append("--icon=NONE")

        # Add models folder if it exists
        if os.path.exists("models"):
            cmd.append("--add-data=models;models")

        cmd.append("main.py")

    print("\nRunning PyInstaller...")
    print(" ".join(cmd))
    print()

    try:
        subprocess.check_call(cmd)
        print("\n" + "=" * 50)
        print("BUILD SUCCESSFUL!")
        print("=" * 50)
        print("\nExecutable location:")
        print("  dist/WaterIntakeTracker.exe")
        print("\nThe exe is self-contained - just share WaterIntakeTracker.exe")
        print("\nNote: Users need a webcam for the app to work.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        print("\nTry running manually:")
        print("  pip install pyinstaller")
        print("  pyinstaller WaterIntakeTracker.spec --noconfirm")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
