import sys
import os

# Add the backend path so we can import modules
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

try:
    import wakeword
    
    # Let's monkey-patch _transcribe_chunk to print what it's transcribing
    original_transcribe = wakeword._transcribe_chunk
    
    def debug_transcribe(audio_data, fs):
        res = original_transcribe(audio_data, fs)
        print(f"[DEBUG-STT] Audio chunk (length={len(audio_data)}) -> '{res}'")
        return res
        
    wakeword._transcribe_chunk = debug_transcribe
    
    print("Testing listener loop for 5 seconds...")
    import threading
    t = threading.Thread(target=wakeword._listen_loop, daemon=True)
    wakeword._active = True
    t.start()
    
    import time
    time.sleep(10)
    wakeword._active = False
    print("Test finished.")
except Exception as e:
    import traceback
    traceback.print_exc()
