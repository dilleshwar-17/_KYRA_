import time
import threading
import requests
import re
from database import init_db, DB_PATH
import sqlite3

# Simple Public RSS to JSON conversion or direct RSS parsing
# We'll use a common news RSS feed (BBC World News)
NEWS_RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"

def fetch_and_store_news():
    """
    Fetch news from RSS and store in SQLite.
    Simplified version using regex to parse RSS XML without extra dependencies.
    """
    try:
        response = requests.get(NEWS_RSS_URL, timeout=10)
        if response.status_code != 200:
            return

        # Find all <item> blocks
        items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        count = 0
        for item in items[:10]: # Store top 10
            title = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
            if not title:
                title = re.search(r'<title>(.*?)</title>', item)
            
            desc = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item)
            if not desc:
                desc = re.search(r'<description>(.*?)</description>', item)
                
            link = re.search(r'<link>(.*?)</link>', item)
            
            title_text = title.group(1).strip() if title else "No Title"
            desc_text = desc.group(1).strip() if desc else ""
            source = "BBC News"
            
            # Check if exists
            cursor.execute("SELECT id FROM news_feed WHERE title = ?", (title_text,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO news_feed (title, content, source) VALUES (?, ?, ?)",
                               (title_text, desc_text, source))
                count += 1
        
        conn.commit()
        conn.close()
        if count > 0:
            print(f"[NewsWorker] Stored {count} new headlines.")
            
    except Exception as e:
        print(f"[NewsWorker] Error: {e}")

def start_news_worker(interval_seconds=3600):
    """Start the news harvesting loop in a background thread."""
    def loop():
        while True:
            fetch_and_store_news()
            time.sleep(interval_seconds)
            
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    init_db()
    fetch_and_store_news()
    print("Test fetch complete.")
