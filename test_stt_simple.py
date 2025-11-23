#!/usr/bin/env python3
"""
Simple fixed-duration STT test.
Records for 3 seconds, then transcribes.
"""

import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

print("=" * 60)
print("Simple STT Test - Fixed Duration")
print("=" * 60)
print()

# Load model
print("Loading Whisper model...")
model = WhisperModel("base.en", device="cpu", compute_type="int8")
print("✅ Model loaded")
print()

# Record
sample_rate = 16000
duration = 3

print(f"🎤 Recording for {duration} seconds...")
print("SPEAK NOW!")
print()

audio_data = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype=np.float32
)
sd.wait()

print("✅ Recording complete")
print()

# Check audio levels
audio_flat = audio_data[:, 0]
max_level = np.max(np.abs(audio_flat))
avg_level = np.mean(np.abs(audio_flat))

print(f"Audio stats:")
print(f"  Max level: {max_level:.4f}")
print(f"  Avg level: {avg_level:.4f}")
print(f"  Duration: {len(audio_flat) / sample_rate:.2f}s")
print()

if max_level < 0.01:
    print("⚠️  Very low audio levels!")
    print("Make sure to speak directly into the microphone")
    exit(1)

# Transcribe
print("🔄 Transcribing...")
print()

segments, info = model.transcribe(
    audio_flat,
    beam_size=1,
    language="en",
    vad_filter=False,  # Disable VAD to force transcription
)

segments_list = list(segments)

print(f"Found {len(segments_list)} segment(s)")
print()

if segments_list:
    for i, segment in enumerate(segments_list):
        print(f"Segment {i+1}:")
        print(f"  Time: {segment.start:.2f}s - {segment.end:.2f}s")
        print(f"  Text: {segment.text}")
        print()
    
    full_text = " ".join([s.text.strip() for s in segments_list])
    print("=" * 60)
    print(f"✅ FINAL TRANSCRIPTION: {full_text}")
    print("=" * 60)
else:
    print("❌ No transcription produced")
    print()
    print("Possible issues:")
    print("  1. No speech detected in audio")
    print("  2. Background noise too high")
    print("  3. Microphone permissions not granted")
