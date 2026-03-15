import sounddevice as sd
import numpy as np
import torch
import time

# Load Silero VAD
print("Loading Silero VAD...")
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

# VAD Parameters
SAMPLING_RATE = 16000
CHUNK_DURATION_MS = 30  # Silero VAD usually takes 30ms or 512/1024/1536 samples
CHUNK_SIZE = int(SAMPLING_RATE * CHUNK_DURATION_MS / 1000) # 480 samples, padding to 512 later if needed. Silero accepts 512.

# let's use exactly 512 for stability with silero
CHUNK_SIZE = 512 

def test_vad():
    print(f"Starting VAD test. Speak into the microphone. Press Ctrl+C to stop.")
    
    vad_iterator = VADIterator(model)
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)
        
        # Convert to float32 tensor
        audio_chunk = indata[:, 0].astype(np.float32)

        # Normalize the chunk slightly just in case it's too quiet (optional, might mess with VAD)
        # But for Silero, it expects typical float32 audio [-1, 1]
        
        audio_tensor = torch.from_numpy(audio_chunk)
        
        # Determine speech
        speech_dict = vad_iterator(audio_tensor, return_seconds=True)
        
        if speech_dict:
            if 'start' in speech_dict:
                print(f"🗣️ Speech started at {speech_dict['start']:.2f}s")
            if 'end' in speech_dict:
                print(f"🛑 Speech ended at {speech_dict['end']:.2f}s")

    try:
        with sd.InputStream(samplerate=SAMPLING_RATE, channels=1, blocksize=CHUNK_SIZE, callback=audio_callback):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping VAD test.")

if __name__ == "__main__":
    test_vad()
