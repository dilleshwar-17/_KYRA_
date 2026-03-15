import asyncio
import time
import wakeword

# Create a mock loop and client set
loop = asyncio.new_event_loop()
clients = set()

print("Starting wakeword test...")
wakeword.start(loop, clients)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping wakeword test.")
    wakeword.stop()
