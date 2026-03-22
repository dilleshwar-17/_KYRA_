import sys
import traceback

print("Checking STT/TTS dependencies...")

deps = [
    "edge_tts",
    "pyttsx3",
    "speech_recognition",
    "sounddevice",
    "soundfile",
    "numpy",
    "torch",
    "openai",
    "dotenv"
]

for dep in deps:
    try:
        __import__(dep)
        print(f"[OK] {dep}")
    except ImportError as e:
        print(f"[MISSING] {dep}: {e}")
    except Exception as e:
        print(f"[ERROR] {dep}: {e}")
