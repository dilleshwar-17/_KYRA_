import os
import sys
import datetime

# Ensure we can find backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import get_engine
from intent_classifier import fast_path_engine

def run_time_test():
    print("--- KYRA Time-Telling Test Case ---")
    query = "what is the time?"
    print(f"User Command: '{query}'")
    
    # 1. Test Fast-Path directly
    print("\n[DEBUG] Testing Intent Classifier (Fast-Path)...")
    fast_res = fast_path_engine.classify_and_execute(query)
    if fast_res:
        print(f"Fast-Path Result: {fast_res}")
    else:
        print("Fast-Path missed (Falling back to LLM).")

    # 2. Test Engine ask()
    print("\n[DEBUG] Testing Full Engine Response...")
    engine = get_engine()
    # Note: Engine will try to use AI but we already verified it has a fast-path bypass
    full_res = engine.ask(query)
    print(f"Engine Final Response: {full_res}")

    # 3. Verify against actual system time
    now = datetime.datetime.now()
    expected = now.strftime("%I:%M %p").lstrip("0")
    print(f"\nSystem Clock: {expected}")
    
    if expected in full_res:
        print("\n[SUCCESS] KYRA correctly identified the time.")
    else:
        print("\n[FAILED] Response did not match system time.")

if __name__ == "__main__":
    run_time_test()
