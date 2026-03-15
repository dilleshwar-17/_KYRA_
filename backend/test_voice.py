try:
    from voice import speak, listen # type: ignore
except ImportError:
    from backend.voice import speak, listen # type: ignore

def test_tts():
    print("\n--- Testing Text-to-Speech ---")
    message = "Hello, I am Kyra. Testing the text to speech system."
    print(f"I should say: '{message}'")
    speak(message)
    print("TTS test complete.")

def test_stt():
    print("\n--- Testing Speech-to-Text ---")
    print("Please say something after the microphone prompt...")
    result = listen(timeout=5)
    if result:
        print(f"STT Result: Success! I heard: '{result}'")
    else:
        print("STT Result: Failed or no audio heard.")

if __name__ == "__main__":
    print("KYRA Voice Module Test")
    
    # Test TTS
    test_tts()
    
    # Test STT
    test_stt()
    
    print("\nTests complete.")
