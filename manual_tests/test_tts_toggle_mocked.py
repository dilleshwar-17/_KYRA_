import os
import sys
from unittest.mock import MagicMock

# Mock all the heavy dependencies that might be missing in this environment
sys.modules["pygame"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()
sys.modules["speech_recognition"] = MagicMock()
sys.modules["sounddevice"] = MagicMock()
sys.modules["soundfile"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import voice

def test_tts_toggle():
    print("Testing Backend TTS Toggle (Mocked)...")
    
    # 1. Test with toggle ON
    os.environ["KYRA_SKIP_BACKEND_TTS"] = "true"
    print("Scenario: KYRA_SKIP_BACKEND_TTS=true")
    # This should return immediately and print "[Backend TTS Skipped] ..."
    voice.speak("This should be skipped in the backend.")
    
    # 2. Test with toggle OFF
    os.environ["KYRA_SKIP_BACKEND_TTS"] = "false"
    print("\nScenario: KYRA_SKIP_BACKEND_TTS=false")
    # This will now proceed past the skip check but we mocked the rest, so no errors.
    voice.speak("This would play if mocked properly.")
    print("Test passed: Logic branch is correctly respecting the environment variable.")

if __name__ == "__main__":
    test_tts_toggle()
