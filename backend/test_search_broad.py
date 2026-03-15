import os
import sys
from dotenv import load_dotenv

# Mocking the environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Manually setting the key for the test
os.environ["SAMBANOVA_API_KEY"] = "d6bda083-67f1-42da-82f7-4caa28e02bd9"

from engine import get_engine

def test_broad_search_integration():
    print("Initializing engine...")
    engine = get_engine()
    
    # Test a different real-time query
    queries = [
        "What is the top news headline in India right now?",
        "What is the current price of Bitcoin?"
    ]
    
    for query in queries:
        print(f"\nUser: {query}")
        response = engine.ask(query)
        print(f"KYRA: {response}")

if __name__ == "__main__":
    test_broad_search_integration()
