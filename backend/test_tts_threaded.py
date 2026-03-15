import pyttsx3
import threading
import time

def speak_worker(text):
    print(f"Thread starting: speaking '{text}'")
    try:
        # Initializing inside the thread to see if it makes a difference
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        print("Thread finished: speak complete.")
    except Exception as e:
        print(f"Thread error: {e}")

def test_threaded_tts():
    print("Main: Starting TTS thread...")
    t = threading.Thread(target=speak_worker, args=("This is a test from a background thread.",))
    t.start()
    print("Main: Waiting for thread to join...")
    t.join(timeout=10)
    if t.is_alive():
        print("Main: WARNING! Thread timed out. TTS might be hanging.")
    else:
        print("Main: Thread joined successfully.")

if __name__ == "__main__":
    test_threaded_tts()
