"""
KYRA - SambaNova AI Engine
Knowledgeable Yet Responsive Assistant
Uses SambaNova's OpenAI-compatible API.
Base URL: https://api.sambanova.ai/v1
"""
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

SYSTEM_PROMPT = """You are KYRA (Knowledgeable Yet Responsive Assistant), an advanced AI assistant.
Your personality:
- Articulate, precise, and highly capable — you deliver exactly what's needed.
- Warm, friendly, and subtly witty — intelligent without being cold.
- You refer to yourself as KYRA. Never break character or mention Llama/AI models.
- Keep responses concise and direct — under 3 sentences unless the topic genuinely demands more.
- Address the user respectfully. If asked who made you, say you were built by your user as their personal AI system.
- Occasionally use light technical precision in phrasing to feel authoritative and smart.
"""

# SambaNova free-tier models (try in order on errors)
CANDIDATE_MODELS = [
    "Meta-Llama-3.3-70B-Instruct",
    "Meta-Llama-3.1-8B-Instruct",
    "Qwen2.5-72B-Instruct",
    "DeepSeek-R1-Distill-Llama-70B",
]

SAMBANOVA_BASE_URL = "https://api.sambanova.ai/v1"


class KYRAEngine:
    def __init__(self):
        load_dotenv(override=True)
        api_key = os.getenv("SAMBANOVA_API_KEY")
        if not api_key:
            raise ValueError(
                "SAMBANOVA_API_KEY not set in backend/.env"
            )

        self._client = OpenAI(
            api_key=api_key,
            base_url=SAMBANOVA_BASE_URL,
        )
        self._history: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._model_idx = 0
        print(f"✅ KYRA Engine ready — SambaNova / {CANDIDATE_MODELS[0]}")

    @property
    def _model(self) -> str:
        return CANDIDATE_MODELS[self._model_idx % len(CANDIDATE_MODELS)]

    def ask(self, user_message: str) -> str:
        """Send a message and get KYRA's response."""
        self._history.append({"role": "user", "content": user_message})

        for attempt in range(len(CANDIDATE_MODELS)):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=self._history,
                    temperature=0.7,
                    max_tokens=512,
                )
                reply = resp.choices[0].message.content.strip()
                self._history.append({"role": "assistant", "content": reply})
                return reply

            except Exception as e:
                err = str(e).lower()
                print(f"⚠️  {self._model} error: {err[:100]}")

                if "429" in err or "rate limit" in err:
                    # Rate limit — wait briefly then try next model
                    time.sleep(2)
                    self._model_idx += 1
                    print(f"↪ Switching to {self._model}")
                    continue
                elif "404" in err or "400" in err or "not found" in err or "not available" in err or "deprecated" in err:
                    self._model_idx += 1
                    print(f"↪ Model unavailable, switching to {self._model}")
                    continue
                else:
                    self._history.pop()
                    return f"I'm sorry, I encountered an error: {e}"

        # All models exhausted
        self._history.pop()
        return "I'm a bit busy right now — please try again in a moment! ⏳"

    def reset(self) -> str:
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]
        return "Conversation cleared. Ready when you are."


_engine: "KYRAEngine | None" = None

def get_engine() -> KYRAEngine:
    global _engine
    if _engine is None:
        _engine = KYRAEngine()
    return _engine
