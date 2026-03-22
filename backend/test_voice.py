import os
import sys
# Ensure we can find backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("--- Testing TTS ---")
try:
    from voice import speak, speak_async
    print("[1] Testing edge-tts (Network TTS)...")
    # Temporarily force edge-tts if available
    speak("This is a test of the edge T T S system.")
    time.sleep(3)
    
    print("[2] Testing pyttsx3 (Offline TTS)...")
    # We can force pyttsx3 by temporarily disabling edge_tts flag in the module
    import voice
    original_tts = voice._tts_available
    voice._tts_available = False
    speak("This is a test of the offline text to speech system.")
    voice._tts_available = original_tts
    time.sleep(3)
    print("[OK] TTS tests completed.")
except Exception as e:
    print(f"[ERROR] TTS test failed: {e}")

print("\n--- Testing STT ---")
try:
    from voice import listen
    print("Please say something into the microphone now... (Listening for up to 5 seconds)")
    text = listen(timeout=5)
    if text:
        print(f"[OK] STT heard: '{text}'")
        speak(f"I heard you say: {text}")
    else:
        print("[WARNING] STT did not hear anything or returned None.")
except Exception as e:
    print(f"[ERROR] STT test failed: {e}")

print("\n--- Diagnostics Complete ---")
