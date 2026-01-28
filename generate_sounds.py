"""
Gerador de Sons - Cria sons WAV para diferentes tipos de mensagens
Execute: python generate_sounds.py
"""

import wave
import struct
import math
import os


def generate_wav(filename, samples, sample_rate=44100):
    """Salva samples como arquivo WAV"""
    os.makedirs("sounds", exist_ok=True)

    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for sample in samples:
            value = max(-32767, min(32767, int(sample)))
            wav_file.writeframes(struct.pack('h', value))

    print(f"  Criado: {filename}")


def generate_celebration_sound():
    """Som de celebração - fanfarra alegre para meta atingida"""
    sample_rate = 44100
    duration = 0.6
    samples = []

    # Três notas alegres subindo (like achievement sound)
    notes = [
        (523.25, 0.0, 0.15),   # C5
        (659.25, 0.15, 0.30),  # E5
        (783.99, 0.30, 0.60),  # G5 (mais longa)
    ]

    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        value = 0

        for freq, start, end in notes:
            if start <= t <= end:
                # Envelope
                note_t = t - start
                note_dur = end - start
                attack = min(1.0, note_t / 0.02)
                decay = math.exp(-3 * max(0, note_t - 0.1))
                envelope = attack * decay * 20000

                # Sine wave com harmônicos
                value += envelope * (
                    math.sin(2 * math.pi * freq * t) * 0.7 +
                    math.sin(2 * math.pi * freq * 2 * t) * 0.2 +
                    math.sin(2 * math.pi * freq * 3 * t) * 0.1
                )

        samples.append(value)

    generate_wav("sounds/celebration.wav", samples, sample_rate)


def generate_reminder_sound():
    """Som suave de lembrete - sino gentil"""
    sample_rate = 44100
    duration = 0.4
    samples = []

    freq = 880  # A5 - tom suave

    for i in range(int(sample_rate * duration)):
        t = i / sample_rate

        # Envelope suave
        attack = min(1.0, t / 0.05)
        decay = math.exp(-5 * t)
        envelope = attack * decay * 18000

        # Sino (fundamental + harmônicos com decay mais rápido)
        value = envelope * (
            math.sin(2 * math.pi * freq * t) * 0.6 +
            math.sin(2 * math.pi * freq * 2.4 * t) * math.exp(-10 * t) * 0.25 +
            math.sin(2 * math.pi * freq * 5.95 * t) * math.exp(-15 * t) * 0.15
        )

        samples.append(value)

    generate_wav("sounds/reminder.wav", samples, sample_rate)


def generate_achievement_sound():
    """Som de conquista - dois tons rápidos"""
    sample_rate = 44100
    duration = 0.35
    samples = []

    notes = [
        (698.46, 0.0, 0.12),   # F5
        (880.00, 0.12, 0.35),  # A5
    ]

    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        value = 0

        for freq, start, end in notes:
            if start <= t <= end:
                note_t = t - start
                attack = min(1.0, note_t / 0.015)
                decay = math.exp(-4 * max(0, note_t - 0.05))
                envelope = attack * decay * 22000

                value += envelope * (
                    math.sin(2 * math.pi * freq * t) * 0.8 +
                    math.sin(2 * math.pi * freq * 2 * t) * 0.15 +
                    math.sin(2 * math.pi * freq * 3 * t) * 0.05
                )

        samples.append(value)

    generate_wav("sounds/achievement.wav", samples, sample_rate)


def generate_pop_sound():
    """Som de pop - aparição do mascote"""
    sample_rate = 44100
    duration = 0.12
    samples = []

    for i in range(int(sample_rate * duration)):
        t = i / sample_rate

        # Frequency sweep: high to low
        freq = 900 - (700 * (t / duration))

        # Quick decay
        amplitude = math.exp(-15 * t) * 28000

        # Sine wave
        value = amplitude * math.sin(2 * math.pi * freq * t)

        samples.append(value)

    generate_wav("sounds/pop.wav", samples, sample_rate)


def generate_water_drop_sound():
    """Som de gota d'água - plim suave"""
    sample_rate = 44100
    duration = 0.25
    samples = []

    for i in range(int(sample_rate * duration)):
        t = i / sample_rate

        # Frequência que sobe rapidamente e depois cai
        if t < 0.02:
            freq = 400 + (600 * (t / 0.02))
        else:
            freq = 1000 - (600 * ((t - 0.02) / (duration - 0.02)))

        # Envelope com decay
        amplitude = math.exp(-8 * t) * 20000

        # Sine wave limpo
        value = amplitude * math.sin(2 * math.pi * freq * t)

        samples.append(value)

    generate_wav("sounds/water_drop.wav", samples, sample_rate)


def generate_funny_sound():
    """Som engraçado - boing!"""
    sample_rate = 44100
    duration = 0.3
    samples = []

    for i in range(int(sample_rate * duration)):
        t = i / sample_rate

        # Frequência oscilante (boing effect)
        base_freq = 300
        wobble = 200 * math.sin(30 * t) * math.exp(-5 * t)
        freq = base_freq + wobble

        # Envelope
        amplitude = math.exp(-6 * t) * 22000

        value = amplitude * math.sin(2 * math.pi * freq * t)

        samples.append(value)

    generate_wav("sounds/funny.wav", samples, sample_rate)


def main():
    """Gera todos os sons"""
    print("=" * 50)
    print("GERADOR DE SONS")
    print("=" * 50)

    print("\nGerando sons...")

    generate_pop_sound()
    generate_celebration_sound()
    generate_reminder_sound()
    generate_achievement_sound()
    generate_water_drop_sound()
    generate_funny_sound()

    print("\n" + "=" * 50)
    print("Sons criados com sucesso!")
    print("")
    print("Sons disponíveis:")
    print("  pop.wav        - Aparição do mascote")
    print("  celebration.wav - Meta atingida")
    print("  reminder.wav    - Lembrete suave")
    print("  achievement.wav - Conquistas")
    print("  water_drop.wav  - Gota d'água")
    print("  funny.wav       - Som engraçado")
    print("=" * 50)


if __name__ == "__main__":
    main()
