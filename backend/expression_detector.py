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

import cv2  # type: ignore
import numpy as np  # type: ignore
import onnxruntime as ort  # type: ignore

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
    print("[INFO] Downloading emotion-ferplus ONNX model (~60 MB) …")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[OK] Emotion model downloaded")
    except Exception as e:
        print(f"[ERROR] Model download failed: {e}")
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
        self._current: str = "neutral"
        self._thread: threading.Thread | None = None
        self._session: ort.InferenceSession | None = None
        self._in: str = ""
        self._out: str = ""

    def start(self):
        t = self._thread
        if t is not None and t.is_alive():
            return
        self._stop.clear()
        thread = threading.Thread(target=self._run, daemon=True, name="ExprDetect")
        self._thread = thread
        thread.start()
        print("[INFO] Expression detector thread started")

    def stop(self):
        self._stop.set()

    def get_expression(self) -> str:
        with self._lock:
            res = str(self._current)
            return res

    def _set(self, val: str):
        with self._lock:
            self._current = str(val)

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
            # Type-safe access to inputs/outputs
            inputs = self._session.get_inputs()
            outputs = self._session.get_outputs()
            if inputs and outputs:
                self._in  = str(inputs[0].name)
                self._out = str(outputs[0].name)
            
            print("[OK] ONNX emotion model loaded")
            return True
        except Exception as e:
            print(f"[ERROR] ONNX model load failed: {e}")
            return False

    def _open_camera(self) -> cv2.VideoCapture | None:
        """Open webcam using DirectShow on Windows (avoids MSMF errors)."""
        # Try DirectShow first (Windows), then default
        for backend in [cv2.CAP_DSHOW, cv2.CAP_ANY]:
            cap = cv2.VideoCapture(CAMERA_INDEX + backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                cap.set(cv2.CAP_PROP_FPS, 15)
                print(f"[INFO] Camera opened with backend {backend}")
                return cap
            cap.release()
        return None

    def _infer(self, face_bgr: np.ndarray) -> str:
        try:
            sess = self._session
            if sess is None:
                return "neutral"
            inp    = _preprocess(face_bgr)
            out    = sess.run([self._out], {self._in: inp})
            idx    = int(np.argmax(out[0][0]))
            label  = FERPLUS_LABELS[idx] if idx < len(FERPLUS_LABELS) else "neutral"
            return EMOTION_MAP.get(label, "neutral")
        except Exception:
            return "neutral"

    def _run(self):
        if not self._load_model():
            print("[WARNING] Expression detection disabled — ONNX model unavailable")
            return

        cascade_xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_xml)

        cap: cv2.VideoCapture | None = None
        last_analysis = 0.0
        consecutive_fails = 0

        while not self._stop.is_set():  # type: ignore
            # (Re)open camera if needed
            c = cap
            if c is None or not c.isOpened():
                if c is not None:
                    try:
                        c.release()
                    except Exception:
                        pass
                new_cap = self._open_camera()
                cap = new_cap
                if cap is None:
                    print("[WARNING] Webcam unavailable — retrying in 5 s")
                    time.sleep(5)
                    continue
                consecutive_fails = 0

            c_active = cap
            if c_active is None:
                continue
            ret, frame = c_active.read()
            if not ret:
                consecutive_fails = consecutive_fails + 1  # type: ignore
                if consecutive_fails > 10:
                    print("[WARNING] Webcam read failing — reopening …")
                    curr_cap = cap
                    if curr_cap is not None:
                        try:
                            curr_cap.release()
                        except Exception:
                            pass
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
                    self._set("neutral")  # type: ignore
                else:
                    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                    sub_frame = frame[y:y+h, x:x+w]
                    # Direct call to result of _infer
                    new_emotion = self._infer(sub_frame)  # type: ignore
                    self._set(new_emotion)  # type: ignore
            except Exception:
                self._set("neutral")  # type: ignore

        c_final = cap
        if c_final is not None:
            try:
                c_final.release()
            except Exception:
                pass
        print("[INFO] Webcam released")


# ─── Singleton ────────────────────────────────────────────────────────────────

_detector: "ExpressionDetector | None" = None

def get_detector() -> ExpressionDetector:
    global _detector
    if _detector is None:
        _detector = ExpressionDetector()
    return _detector
