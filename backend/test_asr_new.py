from voice import listen
import time

def test_new_asr():
    print("Starting ASR test with new robust logic...")
    print("Please say 'Hello Kyra, how are you today?' clearly.")
    time.sleep(1)
    
    result = listen(timeout=5)
    
    if result:
        print(f"\n[SUCCESS] ASR Transcription: '{result}'")
    else:
        print("\n[FAILED] ASR did not return any text. Check logs for SR errors or volume warnings.")

if __name__ == "__main__":
    test_new_asr()
