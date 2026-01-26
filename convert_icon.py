"""
Convert icon.webp to icon.ico for Windows executable
Run this before building the exe: python convert_icon.py
"""

import os
import sys

def convert_webp_to_ico():
    """Convert webp image to Windows ico format"""
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed. Installing...")
        os.system(f"{sys.executable} -m pip install Pillow")
        from PIL import Image

    # Check for source files
    source_files = ['icon.webp', 'dist/icon.webp']
    source_path = None

    for path in source_files:
        if os.path.exists(path):
            source_path = path
            break

    if not source_path:
        print("Error: No icon.webp found in current directory or dist/")
        print("Please place your icon.webp file in the project root.")
        return False

    output_path = 'icon.ico'

    print(f"Converting {source_path} to {output_path}...")

    try:
        # Open the image
        img = Image.open(source_path)

        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Create multiple sizes for the ico file
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        # Resize to each size
        images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)

        # Save as ICO
        images[0].save(
            output_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )

        print(f"Successfully created {output_path}")
        print(f"Icon sizes: {', '.join([f'{s[0]}x{s[1]}' for s in sizes])}")
        return True

    except Exception as e:
        print(f"Error converting icon: {e}")
        return False


if __name__ == "__main__":
    success = convert_webp_to_ico()
    sys.exit(0 if success else 1)
