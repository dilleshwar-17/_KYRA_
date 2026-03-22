import os
import sys
import sqlite3
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import init_db, save_message, get_messages, DB_PATH
from news_worker import fetch_and_store_news

def validate_system():
    print("--- KYRA System Validation ---")
    
    # 1. Database Init
    init_db()
    if os.path.exists(DB_PATH):
        print(f"[OK] Database exists at {DB_PATH}")
    else:
        print("[FAIL] Database not found")
        return

    # 2. Persistence Test
    test_msg = "Validation Test Message"
    save_message("user", test_msg)
    history = get_messages(1)
    if history and history[0]["content"] == test_msg:
        print("[OK] Message persistence working")
    else:
        print("[FAIL] Message persistence failed")

    # 3. News Feed Test
    print("[INFO] Testing news fetch (requires internet)...")
    fetch_and_store_news()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM news_feed")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count > 0:
        print(f"[OK] News harvesting working (Found {count} items)")
    else:
        print("[FAIL] News harvesting failed or no news found")

    print("--- Validation Complete ---")

if __name__ == "__main__":
    validate_system()
