"""
expression_detector.py – OpenCV + ONNX Runtime expression detection

Zero TensorFlow dependency – fully compatible with Python 3.14.

Fixes:
  - Uses CAP_DSHOW backend on Windows to avoid MSMF errors
  - Resilient: if webcam fails, retries every 5 seconds
  - Never crashes the backend process
"""

import threading
import queue
import time
import urllib.request
import pathlib
import logging

import cv2
import numpy as np
import onnxruntime as ort

log = logging.getLogger("expression")

# ─── Model config ─────────────────────────────────────────────────────────────

MODEL_URL  = (
    "https://github.com/onnx/models/raw/main/validated/vision/"
    "body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
)
MODEL_DIR  = pathlib.Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "emotion-ferplus-8.onnx"

# FERPlus output label order
FERPLUS_LABELS = [
    "neutral", "happy", "surprised", "sad",
    "angry", "disgust", "fear", "contempt",
]

EMOTION_MAP = {
    "happy":     "happy",
    "sad":       "sad",
    "angry":     "angry",
    "surprised": "surprised",
    "neutral":   "neutral",
    "disgust":   "neutral",
    "fear":      "neutral",
    "contempt":  "neutral",
}

ANALYSIS_INTERVAL = 0.5   # seconds between inferences
CAMERA_INDEX      = 0     # default webcam


# ─── Model download ───────────────────────────────────────────────────────────

def _download_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists():
        return
    print("📥 Downloading emotion-ferplus ONNX model (~60 MB) …")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("✅ Emotion model downloaded")
    except Exception as e:
        print(f"⚠️  Model download failed: {e}")
        raise


def _preprocess(face_bgr: np.ndarray) -> np.ndarray:
    gray    = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64))
    return resized.astype(np.float32).reshape(1, 1, 64, 64)


# ─── Detector ─────────────────────────────────────────────────────────────────

class ExpressionDetector:
    def __init__(self):
        self._stop   = threading.Event()
        self._lock   = threading.Lock()
        self._current = "neutral"
        self._thread: threading.Thread | None = None
        self._session: ort.InferenceSession | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ExprDetect")
        self._thread.start()
        print("🎥 Expression detector thread started")

    def stop(self):
        self._stop.set()

    def get_expression(self) -> str:
        with self._lock:
            return self._current

    def _set(self, val: str):
        with self._lock:
            self._current = val

    # ── Core loop ─────────────────────────────────────────────────────────────

    def _load_model(self) -> bool:
        try:
            _download_model()
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            self._session = ort.InferenceSession(
                str(MODEL_PATH), sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
            self._in  = self._session.get_inputs()[0].name
            self._out = self._session.get_outputs()[0].name
            print("✅ ONNX emotion model loaded")
            return True
        except Exception as e:
            print(f"⚠️  ONNX model load failed: {e}")
            return False

    def _open_camera(self):
        """Open webcam using DirectShow on Windows (avoids MSMF errors)."""
        # Try DirectShow first (Windows), then default
        for backend in [cv2.CAP_DSHOW, cv2.CAP_ANY]:
            cap = cv2.VideoCapture(CAMERA_INDEX + backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                cap.set(cv2.CAP_PROP_FPS, 15)
                print(f"🎥 Camera opened with backend {backend}")
                return cap
            cap.release()
        return None

    def _infer(self, face_bgr: np.ndarray) -> str:
        try:
            inp    = _preprocess(face_bgr)
            out    = self._session.run([self._out], {self._in: inp})
            idx    = int(np.argmax(out[0][0]))
            label  = FERPLUS_LABELS[idx] if idx < len(FERPLUS_LABELS) else "neutral"
            return EMOTION_MAP.get(label, "neutral")
        except Exception:
            return "neutral"

    def _run(self):
        if not self._load_model():
            print("⚠️  Expression detection disabled — ONNX model unavailable")
            return

        cascade_xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_xml)

        cap = None
        last_analysis = 0.0
        consecutive_fails = 0

        while not self._stop.is_set():
            # (Re)open camera if needed
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                cap = self._open_camera()
                if cap is None:
                    print("⚠️  Webcam unavailable — retrying in 5 s")
                    time.sleep(5)
                    continue
                consecutive_fails = 0

            ret, frame = cap.read()
            if not ret:
                consecutive_fails += 1
                if consecutive_fails > 10:
                    print("⚠️  Webcam read failing — reopening …")
                    cap.release()
                    cap = None
                    consecutive_fails = 0
                time.sleep(0.05)
                continue

            consecutive_fails = 0

            now = time.time()
            if now - last_analysis < ANALYSIS_INTERVAL:
                time.sleep(0.02)
                continue
            last_analysis = now

            try:
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48)
                )
                if len(faces) == 0:
                    self._set("neutral")
                else:
                    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                    self._set(self._infer(frame[y:y+h, x:x+w]))
            except Exception:
                self._set("neutral")

        if cap:
            cap.release()
        print("🎥 Webcam released")


# ─── Singleton ────────────────────────────────────────────────────────────────

_detector: "ExpressionDetector | None" = None

def get_detector() -> ExpressionDetector:
    global _detector
    if _detector is None:
        _detector = ExpressionDetector()
    return _detector
