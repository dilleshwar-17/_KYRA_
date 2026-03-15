import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/.env")

api_key = os.getenv("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"

client = OpenAI(api_key=api_key, base_url=base_url)

def list_models():
    try:
        models = client.models.list()
        for m in models:
            print(m.id)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
