"""
KYRA - FastAPI Backend Server  v1.3
"""
import sys
import os

# Ensure the backend directory is in sys.path (needed for portable Python environments with ._pth files)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import logging
import subprocess
import traceback
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from news_worker import start_news_worker
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kyra")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    loop = asyncio.get_event_loop()
    try:
        from engine import get_engine
        engine = get_engine()
        import wakeword
        
        def wakeword_callback(command: str):
            if not _wakeword_enabled:
                return
            asyncio.run_coroutine_threadsafe(_process_command_global(command, engine, loop), loop)
            
        wakeword.start(loop=loop, clients=_ws_clients, callback=wakeword_callback)
        log.info("Wake word listener started.")
    except Exception as e:
        log.warning(f"Wake word listener failed to start: {e}")

    # --- Start News Worker ---
    try:
        start_news_worker(interval_seconds=3600)  # Harvest every hour
        log.info("[OK] News Worker started in background")
    except Exception as e:
        log.error(f"Failed to start news worker: {e}")

    yield # --- App is running ---

    # --- Shutdown ---
    try:
        import wakeword
        wakeword.stop()
        log.info("Wake word listener stopped.")
    except Exception:
        pass

app = FastAPI(title="KYRA AI Backend", version="1.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Shared WebSocket client set (used by wakeword broadcaster) ───────────────
_ws_clients: set = set()
_wakeword_enabled: bool = True

# ─── Lazy imports ─────────────────────────────────────────────────────────────

def _get_engine():
    from engine import get_engine
    return get_engine()

def _get_detector():
    from expression_detector import get_detector
    return get_detector()



# ─── Models ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    status: str = "ok"

# ─── REST ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        engine = _get_engine()
        return {"status": "ok", "model": engine.__class__.__name__, "name": "KYRA"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/mic-check")
async def mic_check():
    try:
        import sounddevice as sd
        device_id = int(os.getenv("KYRA_MIC_DEVICE", "0"))
        # Try to open for 0.5s
        try:
            with sd.InputStream(device=device_id, channels=1, samplerate=16000):
                pass
            return {"status": "ok", "device": device_id, "name": sd.query_devices(device_id)['name']}
        except Exception as e:
            return {"status": "error", "message": str(e), "device": device_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        engine = _get_engine()
        loop   = asyncio.get_event_loop()
        res    = await loop.run_in_executor(None, engine.ask, request.message)
        from voice import speak_async, get_sentiment
        sentiment = get_sentiment(request.message)
        async def _broadcast(event: dict):
            dead = set()
            for ws in list(_ws_clients):
                try:
                    await ws.send_text(json.dumps(event))
                except Exception:
                    dead.add(ws)
            _ws_clients.difference_update(dead)
        async def _tts_task(text: str):
            await _broadcast({"event": "sentiment", "score": sentiment})
            await _broadcast({"event": "state", "state": "talking"})
            t = speak_async(text)
            await loop.run_in_executor(None, t.join)
            await _broadcast({"event": "state", "state": "idle"})
        asyncio.create_task(_tts_task(res))
        return {"response": res, "status": "ok"}
    except Exception as e:
        return {"response": f"Error: {e}", "status": "error"}

@app.post("/reset")
async def reset_conversation():
    try:
        engine = _get_engine()
        msg    = engine.reset()
        return {"status": "ok", "message": msg}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── WebSocket helper ─────────────────────────────────────────────────────────

import os
import subprocess
import re
import sys

class AgenticHandler:
    """Handles autonomous CRUD, Terminal, and Python operations requested by KYRA."""
    
    @staticmethod
    async def process_tags(text: str, ws_clients: set) -> List[str]:
        """Finds and executes <FILE_*>, <CMD_*>, and <PY_EXEC> tags in the AI response."""
        results: List[str] = []
        
        # 1. FILE_LIST
        for match in re.finditer(r'<FILE_LIST\s+path="([^"]*)"\s*/>', text, re.I):
            path = match.group(1) or "."
            try:
                files = os.listdir(path)
                res = f"Contents of {path}: {files}"
            except Exception as e:
                res = f"Error listing {path}: {e}"
            results.append(res)
            await AgenticHandler.broadcast_status(ws_clients, f"Listed files in {path}")

        # 2. FILE_READ
        for match in re.finditer(r'<FILE_READ\s+path="([^"]*)"\s*/>', text, re.I):
            path = match.group(1)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                res = f"Read {path}: {len(content)} chars"
            except Exception as e:
                res = f"Error reading {path}: {e}"
            results.append(res)
            await AgenticHandler.broadcast_status(ws_clients, f"Read file {path}")

        # 3. FILE_WRITE
        for match in re.finditer(r'<FILE_WRITE\s+path="([^"]*)"\s*>(.*?)</FILE_WRITE>', text, re.S | re.I):
            path, content = match.groups()
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                res = f"Successfully wrote to {path}"
            except Exception as e:
                res = f"Error writing to {path}: {e}"
            results.append(res)
            await AgenticHandler.broadcast_status(ws_clients, f"Wrote to file {path}")

        # 4. FILE_DELETE
        for match in re.finditer(r'<FILE_DELETE\s+path="([^"]*)"\s*/>', text, re.I):
            path = match.group(1)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    res = f"Deleted {path}"
                else:
                    res = f"{path} does not exist"
            except Exception as e:
                res = f"Error deleting {path}: {e}"
            results.append(res)
            await AgenticHandler.broadcast_status(ws_clients, f"Deleted file {path}")

        # 5. CMD_EXEC
        for match in re.finditer(r'<CMD_EXEC\s+cmd="([^"]*)"\s*/>', text, re.I):
            cmd = match.group(1)
            try:
                await AgenticHandler.broadcast_status(ws_clients, f"Executing: {cmd}")
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout_b, stderr_b = await process.communicate()
                stdout = stdout_b.decode().strip()
                stderr = stderr_b.decode().strip()
                res = f"Command: {cmd}\nOutput: {stdout}\nError: {stderr}"
            except Exception as e:
                res = f"Error executing {cmd}: {e}"
            results.append(res)

        # 6. PY_EXEC (Advanced Code Execution)
        for match in re.finditer(r'<PY_EXEC>(.*?)</PY_EXEC>', text, re.S | re.I):
            code = match.group(1).strip()
            tmp_file = "tmp_agent_task.py"
            try:
                await AgenticHandler.broadcast_status(ws_clients, "Running autonomous Python script...")
                with open(tmp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                # Use sys.executable to ensure we use the same environment
                process = await asyncio.create_subprocess_exec(
                    sys.executable, tmp_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout_b, stderr_b = await process.communicate()
                stdout = stdout_b.decode().strip()
                stderr = stderr_b.decode().strip()
                res = f"Python Execution Output: {stdout}\nError: {stderr}"
                if os.path.exists(tmp_file): os.remove(tmp_file)
            except Exception as e:
                res = f"Error in PY_EXEC: {e}"
            results.append(res)
            await AgenticHandler.broadcast_status(ws_clients, "Python script completed.")

        return results

    @staticmethod
    async def broadcast_status(clients: set, status: str):
        dead = set()
        for ws in list(clients):
            try:
                await ws.send_text(json.dumps({"event": "agentic_action", "status": status}))
            except Exception:
                dead.add(ws)
        clients.difference_update(dead)

async def _process_command_global(msg: str, engine, loop):
    """Ask engine, reply via TTS, broadcast response globally (for wake words)."""
    from voice import speak_async, get_sentiment
    from database import save_message
    
    sentiment = get_sentiment(msg)
    user_msg_id = save_message("user", msg)
    
    # Broadcast transcript & thinking
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(json.dumps({"event": "transcript", "text": msg, "id": user_msg_id}))
            await ws.send_text(json.dumps({"event": "sentiment", "score": sentiment}))
            await ws.send_text(json.dumps({"event": "state", "state": "thinking"}))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)

    from expression_detector import get_detector
    detector = get_detector()
    res = await loop.run_in_executor(None, engine.ask, msg, detector.get_expression(), sentiment)
    
    # Save assistant message
    assistant_msg_id = save_message("assistant", res)

    # Broadcast response
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(json.dumps({"event": "response", "text": res, "id": assistant_msg_id}))
            await ws.send_text(json.dumps({"event": "state", "state": "talking"}))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)

    # Trigger Browser TTS (handled by frontend, here we trigger backend TTS if needed or just joint)
    t = speak_async(res)
    await loop.run_in_executor(None, t.join)

    # ─── New: Level 8 Recursive Agentic Loop ───
    loop_count = 0
    max_loops = 10
    current_response = res
    
    while loop_count < max_loops:
        agentic_results = await AgenticHandler.process_tags(current_response, _ws_clients)
        if not agentic_results:
            break
            
        loop_count += 1
        summary = "\n".join(agentic_results)
        log.info(f"Agentic Loop {loop_count} Summary: {summary}")
        
        # Prepare tool feedback for engine
        tool_feedback = f"TOOL_RESULTS:\n{summary}\n\nContinue with the next steps if the goal is not yet achieved."
        
        # Call engine again with results
        current_response = await loop.run_in_executor(None, engine.ask, tool_feedback, detector.get_expression(), sentiment)
        
        # Save and broadcast intermediate response
        assistant_msg_id = save_message("assistant", current_response)
        for ws in list(_ws_clients):
            try:
                await ws.send_text(json.dumps({"event": "response", "text": current_response, "id": assistant_msg_id}))
            except Exception:
                pass
        
        # TTS for the new step
        t = speak_async(current_response)
        await loop.run_in_executor(None, t.join)

    await AgenticHandler.broadcast_status(_ws_clients, "Agentic goal reached.")

    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(json.dumps({"event": "state", "state": "idle"}))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)




# ─── WebSocket: Voice Loop ────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    log.info("WebSocket /ws connected")

    try:
        engine = _get_engine()
    except Exception as e:
        await websocket.send_text(json.dumps({"event": "error", "message": str(e)}))
        await websocket.close()
        _ws_clients.discard(websocket)
        return

    from voice import listen

    try:
        while True:
            raw     = await websocket.receive_text()
            payload = json.loads(raw)
            action  = payload.get("action")
            loop    = asyncio.get_event_loop()

            if action == "listen":
                await websocket.send_text(json.dumps({"event": "state", "state": "listening"}))
                transcript = await loop.run_in_executor(None, listen)

                if not transcript:
                    await websocket.send_text(json.dumps({
                        "event": "error", "message": "I didn't catch that. Try again?"}))
                    await websocket.send_text(json.dumps({"event": "state", "state": "idle"}))
                    continue

                await _process_command_global(transcript, engine, loop)

            elif action in ("chat", "voice_command"):
                msg = payload.get("message", "")
                await _process_command_global(msg, engine, loop)

            elif action == "reset":
                engine.reset()
                await websocket.send_text(json.dumps({"event": "reset"}))

            elif action == "pause_wakeword":
                global _wakeword_enabled
                _wakeword_enabled = False
                log.info("Wake word listener paused by client")

            elif action == "resume_wakeword":
                _wakeword_enabled = True
                log.info("Wake word listener resumed by client")

    except WebSocketDisconnect:
        log.info("WebSocket /ws disconnected")
    except Exception as e:
        log.error(f"WebSocket /ws error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        _ws_clients.discard(websocket)

# ─── WebSocket: Expression Stream ─────────────────────────────────────────────

@app.websocket("/ws/expression")
async def expression_endpoint(websocket: WebSocket):
    await websocket.accept()
    log.info("/ws/expression connected")

    try:
        detector = _get_detector()
        detector.start()
    except Exception as e:
        log.warning(f"Expression detector unavailable: {e}")
        try:
            while True:
                await websocket.send_text(json.dumps({"expression": "neutral"}))
                await asyncio.sleep(2)
        except (WebSocketDisconnect, Exception):
            return

    try:
        while True:
            emotion = detector.get_expression()
            await websocket.send_text(json.dumps({"expression": emotion}))
            await asyncio.sleep(0.5)
    except (WebSocketDisconnect, Exception) as e:
        log.info(f"/ws/expression closed: {type(e).__name__}")



# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("KYRA_HOST", "0.0.0.0")
    port = int(os.getenv("KYRA_PORT", "8088")) # Default to 8088 now to be safe

    print(f"Starting KYRA backend on http://{host}:{port}")
    try:
        uvicorn.run("main:app", host=host, port=port, reload=False)
    except OSError:
        if "address already in use" in traceback.format_exc().lower() or "10048" in traceback.format_exc().lower():
            print(f"⚠️  Port {port} is already in use. Try setting KYRA_PORT to another value and restart.")
        raise
