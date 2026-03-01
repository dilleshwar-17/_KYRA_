"""
J.A.R.V.I.S - Voice Module
Speech-to-Text (microphone input) and Text-to-Speech (pyttsx3 output).
Gracefully handles missing PyAudio — falls back to text-only mode.
"""
import threading

# ─── TTS Setup ────────────────────────────────────────────────────────────────

_tts_engine = None

try:
    import pyttsx3
    _tts_engine = pyttsx3.init()

    def _configure_tts():
        voices = _tts_engine.getProperty("voices")
        for voice in voices:
            if any(k in voice.name.lower() for k in ("female", "zira", "hazel")):
                _tts_engine.setProperty("voice", voice.id)
                break
        _tts_engine.setProperty("rate", 175)
        _tts_engine.setProperty("volume", 1.0)

    _configure_tts()
    print("✅ TTS engine (pyttsx3) ready")
except Exception as e:
    print(f"⚠️  TTS unavailable: {e}")
    _tts_engine = None


def speak(text: str):
    """Convert text to speech (blocking). No-op if TTS unavailable."""
    if _tts_engine is None:
        print(f"[TTS disabled] {text}")
        return
    try:
        _tts_engine.say(text)
        _tts_engine.runAndWait()
    except Exception as e:
        print(f"TTS error: {e}")


def speak_async(text: str):
    """Non-blocking TTS. Returns a thread (joinable)."""
    t = threading.Thread(target=speak, args=(text,), daemon=True)
    t.start()
    return t


# ─── STT Setup ────────────────────────────────────────────────────────────────

_recognizer = None
_sr = None

try:
    import speech_recognition as sr
    _sr = sr
    _recognizer = sr.Recognizer()
    _recognizer.pause_threshold = 1.0

    # Quick check that PyAudio is present
    import pyaudio as _pa
    print("✅ STT (SpeechRecognition + PyAudio) ready")
except ImportError as e:
    print(f"⚠️  STT unavailable (missing dep): {e}")
    _recognizer = None
except Exception as e:
    print(f"⚠️  STT init error: {e}")
    _recognizer = None


def listen(timeout: int = 10) -> "str | None":
    """
    Capture audio from microphone and return transcribed text.
    Returns None if mic unavailable or nothing heard.
    """
    if _recognizer is None or _sr is None:
        print("⚠️  STT disabled — no microphone available")
        return None

    try:
        with _sr.Microphone() as source:
            print("🎤 Listening...")
            _recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
            except _sr.WaitTimeoutError:
                print("⏱️ Listen timeout — no speech detected")
                return None

        text = _recognizer.recognize_google(audio)
        print(f"🗣️ Heard: {text}")
        return text

    except _sr.UnknownValueError:
        print("❓ Could not understand audio")
        return None
    except _sr.RequestError as e:
        print(f"🚫 STT service error: {e}")
        return None
    except Exception as e:
        print(f"🚫 STT error: {e}")
        return None
