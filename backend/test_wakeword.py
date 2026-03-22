import asyncio
import time
import os
import sys

# Ensure we can find backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wakeword

# Create a mock loop and client set
loop = asyncio.new_event_loop()
clients = set()

def test_callback(command):
    print(f"\n[DETECTED] Wake word triggered! Command: {command}")

print("Starting wakeword test (Passive Mode)...")
print("Please say 'Hey Kyra' now.")
wakeword.start(loop, clients, callback=test_callback)

try:
    # Run for 20 seconds
    for _ in range(20):
        time.sleep(1)
        if _ % 5 == 0:
            print(f"Still listening... ({20-_}s remaining)")
except KeyboardInterrupt:
    print("\nStopping wakeword test.")
    wakeword.stop()
