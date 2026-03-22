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
import datetime
import platform
from openai import OpenAI  # type: ignore
from dotenv import load_dotenv  # type: ignore
import sys
import os
# Help IDE find adjacent modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import save_message, get_messages, clear_messages, init_db
import intent_classifier
import search_utils

# Initialize DB on load
init_db()

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


SYSTEM_PROMPT = """You are KYRA, a helpful and highly concise AI assistant developed by Dilleshwar and his team.

CORE RULES:
- **Be Extremely Concise**: Give short, on-point answers by default. Only provide details if explicitly asked.
- **Never Repeat Metadata**: You will receive [SYSTEM_AWARENESS] or System Context hints. DO NOT acknowledge or repeat this information.
- **System Awareness**: You have direct access to local system tools (like battery, CPU, RAM stats). If the user asks for these, assume your system has them.
- **Persona**: Efficient and professional. Like JARVIS, you are here to serve with minimal filler.
"""

def get_realtime_context():
    """Returns a string containing current time, date, and system info."""
    now = datetime.datetime.now()
    return f"[REALTIME_CONTEXT] Date: {now.strftime('%Y-%m-%d')}, Time: {now.strftime('%H:%M:%S')}, Day: {now.strftime('%A')}, OS: {platform.system()} {platform.release()}"

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
        # --- Local Fast-Path Execution First ---
        try:
            fast_response = intent_classifier.fast_path_engine.classify_and_execute(user_message)
            if fast_response:
                # Bypass the echo entirely
                save_message("user", user_message)
                save_message("assistant", fast_response)
                self._history.append({"role": "user", "content": user_message})
                self._history.append({"role": "assistant", "content": fast_response})
                return fast_response
        except Exception as e:
            print(f"[Engine] Echo fast-path routing error: {e}")

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
        self._model = self.DEFAULT_MODEL
        
        # Hydrate history from DB
        db_history = get_messages(20)
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}] + db_history
        print(f"[OK] KYRA Engine ready — OpenAI / {self._model} (History loaded: {len(db_history)} msgs)")

    def ask(self, user_message: str, emotion: str = "neutral", sentiment: float = 0.0) -> str:
        # --- Local Fast-Path Execution First ---
        try:
            fast_response = intent_classifier.fast_path_engine.classify_and_execute(user_message)
            if fast_response:
                # Bypass the LLM entirely, it's been handled locally!
                save_message("user", user_message)
                save_message("assistant", fast_response)
                self._history.append({"role": "user", "content": user_message})
                self._history.append({"role": "assistant", "content": fast_response})
                return fast_response
        except Exception as e:
            print(f"[Engine] Fast-path routing error: {e}")

        sent_label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
        context = get_realtime_context()
        metadata = f"System Context: {context} | User Emotion: {emotion} | Sentiment: {sent_label}"
        
        # Save user message to DB
        save_message("user", user_message)
        
        # Insert metadata as a subtle system hint
        self._history.append({"role": "system", "content": metadata})
        self._history.append({"role": "user", "content": user_message})

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=self._history,
                temperature=0.7,
                max_tokens=512,
                timeout=10.0,
            )
            reply = resp.choices[0].message.content.strip()

            # --- Search Orchestration ---
            search_tags = re.findall(r'<SEARCH>(.*?)</SEARCH>', reply)
            if search_tags:
                query = search_tags[0].strip()
                search_results = search_utils.search_web(query)
                
                # Feed search results back
                self._history.append({"role": "assistant", "content": reply})
                self._history.append({"role": "user", "content": f"[SEARCH_RESULTS] for '{query}':\n{search_results}\n\nBased on these results, provide the final answer."})
                
                # Re-run the model
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=self._history,
                    temperature=0.7,
                    max_tokens=512,
                    timeout=10.0,
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
                
                if clean_reply:
                    save_message("assistant", clean_reply)
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
        clear_messages()
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]
        return "Conversation cleared. Ready when you are."


class SambaNovaEngine(OpenAIEngine):
    """Engine that uses SambaNova's OpenAI-compatible API."""

    def __init__(self, api_key: str):
        # Base constructor handles hydration
        super().__init__(api_key)
        self._client = OpenAI(api_key=api_key, base_url=SAMBANOVA_BASE_URL)
        self._candidate_models = CANDIDATE_MODELS
        self._model_idx = 0
        self._model = self._candidate_models[self._model_idx % len(self._candidate_models)]
        print(f"[OK] KYRA Engine ready — SambaNova / {self._model}")

    def ask(self, user_message: str, emotion: str = "neutral", sentiment: float = 0.0) -> str:
        # --- Local Fast-Path Execution First ---
        try:
            fast_response = intent_classifier.fast_path_engine.classify_and_execute(user_message)
            if fast_response:
                # Bypass the LLM entirely, it's been handled locally!
                save_message("user", user_message)
                save_message("assistant", fast_response)
                self._history.append({"role": "user", "content": user_message})
                self._history.append({"role": "assistant", "content": fast_response})
                return fast_response
        except Exception as e:
            print(f"[Engine] Fast-path routing error: {e}")

        sent_label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
        context = get_realtime_context()
        metadata = f"System Context: {context} | User Emotion: {emotion} | Sentiment: {sent_label}"
        
        # Save user message to DB
        save_message("user", user_message)
        
        # Insert metadata as a subtle system hint
        self._history.append({"role": "system", "content": metadata})
        self._history.append({"role": "user", "content": user_message})

        for attempt in range(min(2, len(self._candidate_models))):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=self._history,
                    temperature=0.7,
                    max_tokens=1024,
                    timeout=10.0,
                )
                reply = resp.choices[0].message.content.strip()

                # --- Search Orchestration ---
                search_tags = re.findall(r'<SEARCH>(.*?)</SEARCH>', reply)
                if search_tags:
                    query = search_tags[0].strip()
                    search_results = search_utils.search_web(query)
                    
                    # Feed search results back
                    self._history.append({"role": "assistant", "content": reply})
                    self._history.append({"role": "user", "content": f"[SEARCH_RESULTS] for '{query}':\n{search_results}\n\nBased on these results, provide the final answer."})
                    
                    # Re-run the model
                    resp = self._client.chat.completions.create(
                        model=self._model,
                        messages=self._history,
                        temperature=0.7,
                        max_tokens=1024,
                        timeout=10.0,
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
                    
                    if clean_reply:
                        save_message("assistant", clean_reply)
                        self._history.append({"role": "assistant", "content": clean_reply})

                return clean_reply
                
            except Exception as e:
                print(f"[Engine] {self._model} failed: {e}. Trying next model...")
                self._model_idx += 1
                self._model = self._candidate_models[self._model_idx % len(self._candidate_models)]

        self._history.pop()  # Remove user message
        self._history.pop()  # Remove metadata system hint
        return "I'm sorry, I encountered an error with all available models. Please check your API key and connection."


def get_engine() -> BaseEngine:
    """Returns the appropriate engine based on environment variables."""
    openai_key = os.getenv("OPENAI_API_KEY")
    samba_key = os.getenv("SAMBANOVA_API_KEY")

    if samba_key:
        return SambaNovaEngine(samba_key)
    elif openai_key:
        return OpenAIEngine(openai_key)
    else:
        return EchoEngine()
