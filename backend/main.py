"""
KYRA - FastAPI Backend Server  v1.2
REST + WebSocket APIs for the Electron frontend.
  /health            – health check
  /chat              – text chat  
  /reset             – clear memory
  /ws                – voice loop WebSocket
  /ws/expression     – OpenCV + ONNX expression stream
"""
import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kyra")

app = FastAPI(title="KYRA AI Backend", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Lazy imports (won't crash startup if deps missing) ───────────────────────

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
        return {"status": "ok", "model": "Meta-Llama-3.3-70B", "name": "KYRA"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        engine = _get_engine()
        loop   = asyncio.get_event_loop()
        res    = await loop.run_in_executor(None, engine.ask, request.message)
        return ChatResponse(response=res)
    except Exception as e:
        return ChatResponse(response=f"Error: {e}", status="error")

@app.post("/reset")
async def reset_conversation():
    try:
        engine = _get_engine()
        msg    = engine.reset()
        return {"status": "ok", "message": msg}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ─── WebSocket: Voice Loop ────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    log.info("🔌 WebSocket /ws connected")

    try:
        engine = _get_engine()
    except Exception as e:
        await websocket.send_text(json.dumps({"event": "error", "message": str(e)}))
        await websocket.close()
        return

    from voice import listen, speak_async

    try:
        while True:
            raw    = await websocket.receive_text()
            payload = json.loads(raw)
            action  = payload.get("action")

            if action == "listen":
                await websocket.send_text(json.dumps({"event": "state", "state": "listening"}))
                loop       = asyncio.get_event_loop()
                transcript = await loop.run_in_executor(None, listen)

                if not transcript:
                    await websocket.send_text(json.dumps({
                        "event": "error", "message": "I didn't catch that. Try again?"}))
                    await websocket.send_text(json.dumps({"event": "state", "state": "idle"}))
                    continue

                await websocket.send_text(json.dumps({"event": "transcript", "text": transcript}))
                await websocket.send_text(json.dumps({"event": "state", "state": "thinking"}))
                response = await loop.run_in_executor(None, engine.ask, transcript)
                await websocket.send_text(json.dumps({"event": "response", "text": response}))
                await websocket.send_text(json.dumps({"event": "state", "state": "talking"}))
                t = speak_async(response)
                await loop.run_in_executor(None, t.join)
                await websocket.send_text(json.dumps({"event": "state", "state": "idle"}))

            elif action == "chat":
                msg  = payload.get("message", "")
                await websocket.send_text(json.dumps({"event": "state", "state": "thinking"}))
                loop = asyncio.get_event_loop()
                res  = await loop.run_in_executor(None, engine.ask, msg)
                await websocket.send_text(json.dumps({"event": "response", "text": res}))
                await websocket.send_text(json.dumps({"event": "state", "state": "idle"}))

            elif action == "reset":
                engine.reset()
                await websocket.send_text(json.dumps({"event": "reset"}))

    except WebSocketDisconnect:
        log.info("🔌 WebSocket /ws disconnected")
    except Exception as e:
        log.error(f"WebSocket /ws error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass

# ─── WebSocket: Expression Stream ─────────────────────────────────────────────

@app.websocket("/ws/expression")
async def expression_endpoint(websocket: WebSocket):
    await websocket.accept()
    log.info("😊 /ws/expression connected")

    try:
        detector = _get_detector()
        detector.start()
    except Exception as e:
        log.warning(f"⚠️  Expression detector unavailable: {e}")
        # Keep sending neutral so frontend doesn't hang on reconnect loop
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
        log.info(f"😊 /ws/expression closed: {type(e).__name__}")

# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting KYRA backend on http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
