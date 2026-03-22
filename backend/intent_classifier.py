import re
import datetime
import os
import subprocess
import urllib.parse
import psutil # type: ignore
from search_utils import search_web # type: ignore

class IntentClassifier:
    """
    Offline keyword and regex based intent classifier.
    Catches deterministic commands (like 'open youtube' or 'search for dogs')
    before they are sent to the LLM to guarantee execution.
    """
    
    def __init__(self):
        # We define a few patterns for common OS tasks.
        self.rules = [
            (re.compile(r'\b(open|launch|start)\s+(.+)', re.IGNORECASE), self._handle_open),
            (re.compile(r'\b(what|tell|get)\s+(is\s+)?(the\s+)?time\b', re.IGNORECASE), self._handle_time),
            (re.compile(r'\b(what|tell|get)\s+(is\s+)?(the\s+)?date\b', re.IGNORECASE), self._handle_date),
            (re.compile(r'\b(current|today\'s)\s+date\b', re.IGNORECASE), self._handle_date),
            (re.compile(r'\b(battery)\s+(percentage|level|status)\b', re.IGNORECASE), self._handle_battery),
            (re.compile(r'\b(how\s+much)\s+battery\b', re.IGNORECASE), self._handle_battery),
            (re.compile(r'\b(system|pc|computer)\s+(stats|status|performance)\b', re.IGNORECASE), self._handle_stats),
            (re.compile(r'\b(cpu|ram|memory)\s+(usage|status)\b', re.IGNORECASE), self._handle_stats),
            (re.compile(r'\b(search for|search|google|look up)\s+(.+)', re.IGNORECASE), self._handle_search),
        ]
        
    def classify_and_execute(self, query: str):
        """
        Tests the query against the rules.
        If a rule matches, executes the corresponding handler and returns the response string.
        If no rules match, returns None so it can fallback to the LLM.
        """
        # Strip punctuation 
        clean_query = re.sub(r'[^\w\s]', '', query).strip()
        
        for pattern, handler in self.rules:
            match = pattern.search(query)
            if match:
                try:
                    return handler(match, query)
                except Exception as e:
                    print(f"[IntentClassifier] Handler error: {e}")
                    return None
        return None

    def _handle_open(self, match, original_query: str) -> str:
        target = match.group(2).strip().lower()
        print(f"[FAST-PATH] Opening '{target}'")
        
        # Some mappings for common websites
        websites = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "facebook": "https://www.facebook.com",
            "mail": "mailto:",
            "gmail": "https://mail.google.com"
        }
        
        # If it's a known website
        if target in websites:
            os.system(f"start {websites[target]}")
            return f"Opening {target}."
            
        # If it looks like a URL
        if target.endswith(".com") or target.endswith(".org") or target.endswith(".net"):
            url = target if target.startswith("http") else f"https://{target}"
            os.system(f"start {url}")
            return f"Opening {target}."
            
        # Otherwise assume it's a local app (like 'notepad', 'calculator' etc)
        # Using start command on Windows attempts to find it in PATH
        os.system(f"start {target}")
        return f"Opening application: {target}."

    def _handle_time(self, match, original_query: str) -> str:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        print(f"[FAST-PATH] Time query")
        return f"The current time is {time_str}."

    def _handle_date(self, match, original_query: str) -> str:
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        print(f"[FAST-PATH] Date query")
        return f"Today is {date_str}."

    def _handle_battery(self, match, original_query: str) -> str:
        print(f"[FAST-PATH] Battery query")
        battery = psutil.sensors_battery()
        if battery is None:
            return "I couldn't detect a battery on this system."
        
        percent = battery.percent
        plugged = battery.power_plugged
        status = "charging" if plugged else "discharging"
        
        if plugged and percent == 100:
            return "Your battery is fully charged and plugged in."
            
        return f"Your battery is at {percent} percent and is currently {status}."

    def _handle_stats(self, match, original_query: str) -> str:
        print(f"[FAST-PATH] System stats query")
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        return f"System status: CPU usage is {cpu}%, and RAM usage is at {ram}%."

    def _handle_search(self, match, original_query: str) -> str:
        target_query = match.group(2).strip()
        print(f"[FAST-PATH] Searching for '{target_query}'")
        
        # 1. Open the search in the user's default browser so they can see the full results
        encoded_query = urllib.parse.quote_plus(target_query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        os.system(f"start {search_url}")
        
        # 2. Also try to fetch a brief summary to speak out loud
        try:
            results = search_web(target_query, max_results=1)
            if "No Title" not in results and "Error" not in results:
                # Keep it very brief since it will be spoken
                lines = results.split('\n')
                if len(lines) > 1:
                    summary = lines[1].strip()
                    # Limit to ~2 sentences
                    sentences = [s.strip() for s in summary.split('.') if s.strip()]
                    brief = '. '.join(sentences[:2]) + '.' # type: ignore
                    return f"Here is what I found for {target_query}: {brief}"
        except Exception as e:
            print(f"Error fetching search summary: {e}")
            
        return f"I've opened the search results for {target_query} in your browser."

# Singleton instance
fast_path_engine = IntentClassifier()

if __name__ == "__main__":
    # Test cases
    print(fast_path_engine.classify_and_execute("open notepad"))
    print(fast_path_engine.classify_and_execute("what time is it?"))
    print(fast_path_engine.classify_and_execute("search for python programming"))
    print(fast_path_engine.classify_and_execute("how do airplanes fly?")) # Should return None (LLM fallback)
