# KYRA System Manual

Welcome to the comprehensive guide for KYRA.

## 1. Architecture Overview
KYRA is built as a modular AI assistant combining:
- **Frontend**: Electron/React for a premium desktop experience.
- **Backend**: FastAPI for high-performance AI orchestration.
- **Intelligence**: SambaNova/OpenAI LLMs with real-time search and OS integration.
- **Persistence**: SQLite for long-term memory of conversations and news.

*Detailed design can be found in [system_design.md](system_design.md).*

## 2. Configuration Guide

### 2.1 Environment Variables
All configurations are stored in `backend/.env` or the project root `.env`:
- `SAMBANOVA_API_KEY`: Required for the primary AI engine.
- `KYRA_SKIP_BACKEND_TTS`: Set to `true` to use the premium browser voice.
- `OPENAI_API_KEY`: Optional fallback for GPT-4o models.

### 2.2 Database
The system uses SQLite (`backend/kyra.db`). No external database installation is required for the prototype. For "server-grade" production, the connection string in `database.py` can be pointed to a PostgreSQL instance.

## 3. Usage Guide

### 3.1 Voice Interaction
- Click the **Microphone** button to start listening.
- KYRA uses browser-native ASR (Speech-to-Text) for near-instant transcription.
- Responses are spoken using high-quality neural-style voices.

### 3.2 Real-time News
KYRA automatically harvests world news in the background. You can ask:
- *"What's the latest news?"*
- *"Tell me about current events."*

### 3.3 System Commands
You can command KYRA to control your OS:
- *"Open Notepad"*
- *"Launch YouTube"*

## 4. Troubleshooting
- **API Errors**: Ensure your `SAMBANOVA_API_KEY` is active and correct.
- **Voice Issues**: Check browser microphone permissions in the Electron window.
- **Dependency Errors**: Run `pip install -r backend/requirements.txt` to ensure `pygame` and `requests` are present.
