"""
KYRA - SambaNova AI Engine
Knowledgeable Yet Responsive Assistant
Uses SambaNova's OpenAI-compatible API.
Base URL: https://api.sambanova.ai/v1
"""
import os
import sys
import time
import re
import threading
from openai import OpenAI  # type: ignore
from dotenv import load_dotenv  # type: ignore

def _find_and_load_env():
    """Find .env whether running from source, PyInstaller onedir, or installed."""
    mei = getattr(sys, "_MEIPASS", None)
    candidates = [
        # PyInstaller _internal folder (where datas land in onedir mode)
        os.path.join(mei, ".env") if mei else None,
        # Next to running exe (PyInstaller onedir)
        os.path.join(os.path.dirname(sys.executable), ".env"),
        # CWD — typically the folder the backend was launched from
        os.path.join(os.getcwd(), ".env"),
        # Script dir (dev mode)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            load_dotenv(dotenv_path=path, override=True)
            print(f"Loaded .env from: {path}")
            return
    load_dotenv(override=True)

_find_and_load_env()


SYSTEM_PROMPT = """You are KYRA (Knowledgeable Yet Responsive Assistant), an advanced, high-EQ AI assistant.

CORE PERSONA:
- Articulate, precise, and highly capable — you deliver exactly what's needed.
- Warm, empathetic, and subtly witty — intelligent without being cold.
- You refer to yourself as KYRA. Never break character or mention Llama/AI models.
- Address the user respectfully. If asked who made you, say you were built by Dilleshwar and his team.

INTELLIGENCE & BEHAVIOR:
- **Emotional Intelligence**: Deeper understanding of emotional cues. You will sometimes receive a [USER_EMOTION] tag (neutral, happy, sad, angry, surprised) or [USER_SENTIMENT] context. Use this to tailor your response with genuine empathy (e.g., offer comfort if they look sad, share their joy if they look happy).
- **Conversational Flow**: Engage in natural, fluid conversations. Use context from previous turns and frequently use open-ended follow-up questions to enhance the dialogue. Avoid one-word or dead-end answers.
- **Common Sense & Real-world Context**: Ground your logic in physical reality. Use real-world examples, scenarios, and case studies to explain complex situations or provide advice.
- **Domain-Specific Expertise**: You have expanded knowledge in specialized areas:
    - **Medicine**: Provide accurate biological and medical context (with a disclaimer to consult professionals).
    - **Law**: Understand legal principles and terminology (with a disclaimer that you are not a lawyer).
    - **Finance**: Offer informed perspectives on trends, breakthroughs, and financial logic.
- **Data Awareness**: You are a real-time assistant. For ANY question regarding current events, live scores, weather, latest news, or any data that might have changed since your training, you MUST use the search tool described below.

REAL-TIME SEARCH CAPABILITY:
You have the power to search the live web. Use the following format for ANY query requiring up-to-date facts:
<SEARCH>query</SEARCH>
Once you provide this tag, the system will provide results. You MUST summarize these results and provide the answer directly. 
**STRICT RULE**: NEVER use `<RUN_CMD>` to open a website just to show the user information. Your job is to read the information and tell the user the answer. Only open an app or URL if the user explicitly asks you to "open" or "launch" it.

RESPONSE STYLE:
- Keep responses concise and direct — usually under 3-4 sentences unless the topic (like a technical explanation) genuinely demands more.
- Use light technical precision in phrasing to feel authoritative and smart.

OS INTEGRATION CAPABILITIES:
You can open applications or launch websites on the user's Windows system ONLY when explicitly asked to "open" or "launch" them.
To open an app or URL, include this exact tag in your response:
<RUN_CMD>command</RUN_CMD>
For example, to open Notepad:
Opening Notepad. <RUN_CMD>start notepad</RUN_CMD>
To search or open a URL:
Opening YouTube. <RUN_CMD>start https://www.youtube.com</RUN_CMD>
Always use the 'start' command for opening apps or URLs on Windows.
"""

# SambaNova free-tier models (try in order on errors)
CANDIDATE_MODELS = [
    "Meta-Llama-3.1-8B-Instruct",
    "Meta-Llama-3.3-70B-Instruct",
    "Qwen2.5-72B-Instruct",
    "DeepSeek-R1-Distill-Llama-70B",
]

SAMBANOVA_BASE_URL = "https://api.sambanova.ai/v1"


class BaseEngine:
    """Base interface for chat engines."""

    def ask(self, user_message: str, emotion: str = "neutral", sentiment: float = 0.0) -> str:
        raise NotImplementedError

    def reset(self) -> str:
        raise NotImplementedError


class EchoEngine(BaseEngine):
    """Fallback engine when no AI API key is configured."""

    def __init__(self):
        self._history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("[WARNING] No AI API key found. Falling back to echo mode (local only).")

    def ask(self, user_message: str, emotion: str = "neutral", sentiment: float = 0.0) -> str:
        # Keep a short history for display purposes.
        self._history.append({"role": "user", "content": user_message})
        reply = (
            "I’m here and listening, but I don’t have an AI model configured yet. "
            "Set SAMBANOVA_API_KEY or OPENAI_API_KEY in backend/.env to enable full responses."
        )
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> str:
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]
        return "Conversation cleared. Ready when you are."


class OpenAIEngine(BaseEngine):
    """Engine that uses OpenAI API (or OpenAI-compatible endpoints)."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: str):
        self._client = OpenAI(api_key=api_key)
        self._history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._model = self.DEFAULT_MODEL
        print(f"[OK] KYRA Engine ready — OpenAI / {self._model}")

    def ask(self, user_message: str, emotion: str = "neutral", sentiment: float = 0.0) -> str:
        sent_label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
        full_message = f"[USER_EMOTION: {emotion}] [USER_SENTIMENT: {sent_label} ({sentiment:.1f})] {user_message}"
        self._history.append({"role": "user", "content": full_message})

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=self._history,
                temperature=0.7,
                max_tokens=512,
            )
            reply = resp.choices[0].message.content.strip()

            # --- Search Orchestration ---
            search_tags = re.findall(r'<SEARCH>(.*?)</SEARCH>', reply)
            if search_tags:
                from search_utils import search_web
                query = search_tags[0].strip()
                search_results = search_web(query)
                
                # Feed search results back
                self._history.append({"role": "assistant", "content": reply})
                self._history.append({"role": "user", "content": f"[SEARCH_RESULTS] for '{query}':\n{search_results}\n\nBased on these results, provide the final answer."})
                
                # Re-run the model
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=self._history,
                    temperature=0.7,
                    max_tokens=512,
                )
                reply = resp.choices[0].message.content.strip()

            # --- OS Integration ---
            if reply is not None:
                def execute_cmd(command):
                    try:
                        os.system(command)
                    except Exception as err:
                        print(f"Error executing OS command: {err}")

                commands = re.findall(r'<RUN_CMD>(.*?)</RUN_CMD>', reply)
                for cmd in commands:
                    threading.Thread(target=execute_cmd, args=(cmd.strip(),), daemon=True).start()

                clean_reply = re.sub(r'<RUN_CMD>.*?</RUN_CMD>', '', reply).strip()
                clean_reply = re.sub(r'<SEARCH>.*?</SEARCH>', '', clean_reply).strip()
                
                if not clean_reply and commands:
                    clean_reply = "Executing command."

                self._history.append({"role": "assistant", "content": clean_reply})
                return clean_reply
            else:
                print("Warning: Model returned None content.")
                self._history.pop()
                return "I'm sorry, I didn't get a clear response from the model. Please try again."

        except Exception as e:
            self._history.pop()
            return f"I'm sorry, I encountered an error: {e}"

    def reset(self) -> str:
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]
        return "Conversation cleared. Ready when you are."


class SambaNovaEngine(OpenAIEngine):
    """Engine that uses SambaNova's OpenAI-compatible API."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._client = OpenAI(api_key=api_key, base_url=SAMBANOVA_BASE_URL)
        self._candidate_models = CANDIDATE_MODELS
        self._model_idx = 0
        self._model = self._candidate_models[self._model_idx % len(self._candidate_models)]
        print(f"[OK] KYRA Engine ready — SambaNova / {self._model}")

    def ask(self, user_message: str, emotion: str = "neutral", sentiment: float = 0.0) -> str:
        sent_label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
        full_message = f"[USER_EMOTION: {emotion}] [USER_SENTIMENT: {sent_label} ({sentiment:.1f})] {user_message}"
        self._history.append({"role": "user", "content": full_message})

        for attempt in range(len(self._candidate_models)):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=self._history,
                    temperature=0.7,
                    max_tokens=512,
                )
                reply = resp.choices[0].message.content.strip()

                # --- Search Orchestration ---
                search_tags = re.findall(r'<SEARCH>(.*?)</SEARCH>', reply)
                if search_tags:
                    from search_utils import search_web
                    query = search_tags[0].strip()
                    search_results = search_web(query)
                    
                    # Feed search results back
                    self._history.append({"role": "assistant", "content": reply})
                    self._history.append({"role": "user", "content": f"[SEARCH_RESULTS] for '{query}':\n{search_results}\n\nBased on these results, provide the final answer."})
                    
                    # Re-run the model
                    resp = self._client.chat.completions.create(
                        model=self._model,
                        messages=self._history,
                        temperature=0.7,
                        max_tokens=512,
                    )
                    reply = resp.choices[0].message.content.strip()

                # --- OS Integration ---
                if reply is not None:
                    def execute_cmd(command):
                        try:
                            os.system(command)
                        except Exception as err:
                            print(f"Error executing OS command: {err}")

                    commands = re.findall(r'<RUN_CMD>(.*?)</RUN_CMD>', reply)
                    for cmd in commands:
                        threading.Thread(target=execute_cmd, args=(cmd.strip(),), daemon=True).start()

                    clean_reply = re.sub(r'<RUN_CMD>.*?</RUN_CMD>', '', reply).strip()
                    clean_reply = re.sub(r'<SEARCH>.*?</SEARCH>', '', clean_reply).strip()

                    if not clean_reply and commands:
                        clean_reply = "Executing command."

                    self._history.append({"role": "assistant", "content": clean_reply})
                    return clean_reply
                else:
                    print("Warning: Model returned None content.")
                    self._history.pop()
                    return "I'm sorry, I didn't get a clear response from the model. Please try again."

            except Exception as e:
                err_msg = str(e).lower()
                if len(err_msg) > 100:
                    short_err = "Error too long"
                else:
                    short_err = err_msg
                print(f"[WARNING] {self._model} error: {short_err}")

                if "429" in err_msg or "rate limit" in err_msg:
                    time.sleep(2)
                    self._model_idx += 1
                    self._model = self._candidate_models[self._model_idx % len(self._candidate_models)]
                    print(f"[INFO] Switching to {self._model}")
                    continue
                elif any(token in err_msg for token in ("404", "400", "not found", "not available", "deprecated")):
                    self._model_idx += 1
                    self._model = self._candidate_models[self._model_idx % len(self._candidate_models)]
                    print(f"[INFO] Model unavailable, switching to {self._model}")
                    continue
                else:
                    self._history.pop()
                    return f"I'm sorry, I encountered an error: {e}"

        self._history.pop()
        return "I'm a bit busy right now — please try again in a moment! ⏳"


_engine: "BaseEngine | None" = None


def get_engine() -> BaseEngine:
    global _engine
    if _engine is not None:
        return _engine

    sambanova_key = os.getenv("SAMBANOVA_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if sambanova_key:
        _engine = SambaNovaEngine(sambanova_key)
    elif openai_key:
        _engine = OpenAIEngine(openai_key)
    else:
        _engine = EchoEngine()

    return _engine
