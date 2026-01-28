"""
Generate a fun "pop" sound for mascot appearance
"""

import wave
import struct
import math
import os


def generate_pop_sound(filename="sounds/pop.wav", duration=0.15):
    """
    Generate a short, fun pop sound

    Args:
        filename: Output WAV file path
        duration: Duration in seconds (default 0.15s)
    """
    # Ensure sounds directory exists
    os.makedirs("sounds", exist_ok=True)

    # Audio parameters
    sample_rate = 44100  # CD quality
    num_samples = int(sample_rate * duration)

    # Open WAV file
    with wave.open(filename, 'w') as wav_file:
        # Set parameters (1 channel, 2 bytes per sample, sample rate)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        # Generate pop sound
        # Pop = quick frequency sweep from high to low
        for i in range(num_samples):
            t = i / sample_rate

            # Frequency sweep: starts at 800Hz, drops to 200Hz
            freq = 800 - (600 * (t / duration))

            # Amplitude envelope: quick attack, exponential decay
            amplitude = math.exp(-10 * t) * 32000

            # Generate sine wave
            value = int(amplitude * math.sin(2 * math.pi * freq * t))

            # Add slight noise for texture
            noise = int((math.sin(t * 10000) * 0.1) * amplitude)

            # Combine
            sample = max(-32767, min(32767, value + noise))

            # Write sample
            packed_value = struct.pack('h', sample)
            wav_file.writeframes(packed_value)

    print(f"Som criado: {filename}")
    print(f"Duracao: {duration}s")
    print(f"Taxa: {sample_rate}Hz")


if __name__ == "__main__":
    print("Gerando som de 'pop' para o mascote...")
    generate_pop_sound()
    print("\nPronto! O som está em: sounds/pop.wav")
