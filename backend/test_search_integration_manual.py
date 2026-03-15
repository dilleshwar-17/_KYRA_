import os
import sys
from dotenv import load_dotenv

# Mocking the environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Manually setting the key for the test
os.environ["SAMBANOVA_API_KEY"] = "d6bda083-67f1-42da-82f7-4caa28e02bd9"

from engine import get_engine

def test_search_integration():
    print("Initializing engine...")
    engine = get_engine()
    
    # Test a query that should trigger search
    query = "What is the current IPL score today?"
    print(f"User: {query}")
    
    response = engine.ask(query)
    print(f"KYRA: {response}")

if __name__ == "__main__":
    test_search_integration()
