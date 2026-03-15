import os
import sys
from dotenv import load_dotenv

def check_env():
    # Try multiple paths like engine.py does
    mei = getattr(sys, "_MEIPASS", None)
    candidates = [
        os.path.join(mei, ".env") if mei else None,
        os.path.join(os.path.dirname(sys.executable), ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    ]
    print(f"Current working directory: {os.getcwd()}")
    for path in candidates:
        if path:
            print(f"Checking candidate: {path} (exists: {os.path.isfile(path)})")
            if os.path.isfile(path):
                load_dotenv(dotenv_path=path, override=True)
                print(f"Loaded .env from: {path}")
                break
    
    key = os.getenv("SAMBANOVA_API_KEY")
    print(f"SAMBANOVA_API_KEY: {key}")
    if key:
        print(f"Key length: {len(key)}")

if __name__ == "__main__":
    check_env()
