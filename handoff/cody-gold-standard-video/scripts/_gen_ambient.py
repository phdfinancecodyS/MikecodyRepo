#!/usr/bin/env python3
"""
Generate a soft ambient music bed for the campaign video.
Synthesizes a warm pad (no copyright issues).
"""
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "videos" / "ambient_pad.wav"
OUT.parent.mkdir(parents=True, exist_ok=True)

SR = 44100
DURATION = 28.0  # seconds, longer than video to allow fade
samples = int(SR * DURATION)
t = np.linspace(0, DURATION, samples, dtype=np.float64)

# Warm ambient pad: C3 + E3 + G3 + C4 with slow sine LFO
freqs = [130.81, 164.81, 196.00, 261.63]  # C3, E3, G3, C4
amplitudes = [0.25, 0.20, 0.18, 0.15]

signal = np.zeros(samples)
for freq, amp in zip(freqs, amplitudes):
    # Add slight detuning for warmth
    detune = 1.0 + np.sin(2 * np.pi * 0.1 * t) * 0.002
    signal += amp * np.sin(2 * np.pi * freq * detune * t)

# Add a subtle higher harmonic for shimmer
signal += 0.06 * np.sin(2 * np.pi * 523.25 * t) * np.sin(2 * np.pi * 0.15 * t)

# Slow amplitude envelope (swell in and out)
envelope = np.ones(samples)
# Fade in over 3 seconds
fade_in = int(3.0 * SR)
envelope[:fade_in] = np.linspace(0, 1, fade_in)
# Fade out over 4 seconds
fade_out = int(4.0 * SR)
envelope[-fade_out:] = np.linspace(1, 0, fade_out)
# Add gentle breathing LFO
envelope *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.08 * t)

signal *= envelope

# Soft low-pass effect: simple moving average
window = 80
kernel = np.ones(window) / window
signal = np.convolve(signal, kernel, mode='same')

# Normalize to 0.15 peak (quiet bed under VO)
signal = signal / np.max(np.abs(signal)) * 0.15

# Stereo
stereo = np.column_stack([signal, signal]).astype(np.float32)

# Write WAV
import wave
import struct

with wave.open(str(OUT), 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    # Convert float to int16
    int_data = (stereo * 32767).astype(np.int16)
    wf.writeframes(int_data.tobytes())

print(f"Ambient pad: {OUT}")
print(f"Duration: {DURATION}s, Size: {OUT.stat().st_size / 1024:.0f} KB")
