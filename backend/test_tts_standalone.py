import pyttsx3
import time

def test_tts():
    print("Initializing TTS engine...")
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        print(f"Found {len(voices)} voices.")
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name} ({voice.id})")
        
        # Test default voice
        print("Testing default voice...")
        engine.say("Hello, I am testing the text to speech engine.")
        engine.runAndWait()
        print("Default voice test complete.")
        
        # Test specific voice if available
        if len(voices) > 1:
            print(f"Testing voice 1: {voices[1].name}")
            engine.setProperty("voice", voices[1].id)
            engine.say("This is a test of a different voice.")
            engine.runAndWait()
            print("Voice 1 test complete.")
            
    except Exception as e:
        print(f"Error during TTS test: {e}")

if __name__ == "__main__":
    test_tts()
