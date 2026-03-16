import asyncio
import edge_tts
import pygame
import tempfile
import os

async def save_audio(text, output_file):
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(output_file)

def test_tts():
    text = "Hello, this is a test of the Edge TTS engine. I hope you can hear me."
    print("Generating audio...")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_name = f.name
    
    asyncio.run(save_audio(text, tmp_name))
    print("Audio generated. Playing...")
    
    pygame.mixer.init()
    pygame.mixer.music.load(tmp_name)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        
    print("Playback finished.")
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    os.remove(tmp_name)

if __name__ == "__main__":
    test_tts()
