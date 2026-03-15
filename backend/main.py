"""
KYRA - FastAPI Backend Server  v1.3
REST + WebSocket APIs for the Electron frontend.
  /health            - health check
  /chat              - text chat
  /reset             - clear memory
  /ws                - voice loop WebSocket (also receives wake_command events)
  /ws/expression     - OpenCV + ONNX expression stream
"""
import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kyra")

app = FastAPI(title="KYRA AI Backend", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Shared WebSocket client set (used by wakeword broadcaster) ───────────────
_ws_clients: set = set()

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

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        engine = _get_engine()
        loop   = asyncio.get_event_loop()
        res    = await loop.run_in_executor(None, engine.ask, request.message)
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

# ─── Startup / Shutdown ───────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    try:
        import wakeword
        wakeword.start(loop=loop, clients=_ws_clients)
        log.info("Wake word listener started.")
    except Exception as e:
        log.warning(f"Wake word listener failed to start: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        import wakeword
        wakeword.stop()
    except Exception:
        pass

# ─── WebSocket helper ─────────────────────────────────────────────────────────

async def _process_command(websocket: WebSocket, msg: str, engine, loop):
    """Ask engine, reply via TTS, broadcast response to all clients."""
    from voice import speak_async

    # Show transcript to the sender
    await websocket.send_text(json.dumps({"event": "transcript", "text": msg}))

    # Broadcast sentiment and 'thinking' to ALL clients
    from voice import get_sentiment
    sentiment = get_sentiment(msg)
    
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(json.dumps({"event": "sentiment", "score": sentiment}))
            await ws.send_text(json.dumps({"event": "state", "state": "thinking"}))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)

    # Get current expression from computer vision
    from expression_detector import get_detector
    detector = get_detector()
    user_expr = detector.get_expression()

    res = await loop.run_in_executor(None, engine.ask, msg, user_expr, sentiment)

    # Broadcast response + talking to ALL clients
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(json.dumps({"event": "response", "text": res}))
            await ws.send_text(json.dumps({"event": "state", "state": "talking"}))
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)

    t = speak_async(res)
    await loop.run_in_executor(None, t.join)

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

    from voice import listen, speak_async

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

                await _process_command(websocket, transcript, engine, loop)

            elif action in ("chat", "voice_command"):
                msg = payload.get("message", "")
                await _process_command(websocket, msg, engine, loop)

            elif action == "reset":
                engine.reset()
                await websocket.send_text(json.dumps({"event": "reset"}))

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
    port = int(os.getenv("KYRA_PORT", "8000"))

    print(f"Starting KYRA backend on http://{host}:{port}")
    try:
        uvicorn.run("main:app", host=host, port=port, reload=False)
    except OSError as server_error:
        error_str = str(server_error).lower()
        if "address already in use" in error_str or "10048" in error_str:
            print(f"⚠️  Port {port} is already in use. Try setting KYRA_PORT to another value and restart.")
        raise server_error
