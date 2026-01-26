"""
Generate a simple gulp sound effect
Run this once to create the sounds/gulp.wav file
"""

import struct
import wave
import math
import os


def generate_gulp_sound(filename: str, duration: float = 0.3):
    """
    Generate a simple 'blip' sound that simulates a gulp notification.

    Parameters:
        filename: Output WAV file path
        duration: Sound duration in seconds
    """
    sample_rate = 44100
    num_samples = int(sample_rate * duration)

    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)

        samples = []

        for i in range(num_samples):
            t = i / sample_rate

            # Create a descending frequency chirp (like a water drop)
            # Frequency drops from 800Hz to 300Hz
            freq = 800 - (500 * t / duration)

            # Amplitude envelope (quick attack, slow decay)
            envelope = math.exp(-t * 8) * (1 - math.exp(-t * 50))

            # Generate sample
            sample = math.sin(2 * math.pi * freq * t) * envelope

            # Add a subtle second harmonic
            sample += 0.3 * math.sin(4 * math.pi * freq * t) * envelope

            # Normalize and convert to 16-bit integer
            sample_int = int(sample * 32767 * 0.5)
            sample_int = max(-32768, min(32767, sample_int))

            samples.append(struct.pack('<h', sample_int))

        wav_file.writeframes(b''.join(samples))

    print(f"Generated: {filename}")


def main():
    sound_path = os.path.join("sounds", "gulp.wav")
    generate_gulp_sound(sound_path)
    print("Sound generation complete!")


if __name__ == "__main__":
    main()
