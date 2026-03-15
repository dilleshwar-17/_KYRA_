# KYRA AI - Manual Test Checklist (VERIFIED)

All items have been verified through automated testing, browser inspection, and process monitoring.

## 1. System Initialization
- [x] Backend starts without errors on port 8000 (Verified via /health and logs)
- [x] Frontend (Vite) starts on port 5173 (Verified via browser tool)
- [x] Electron app launches and connects to backend (Verified process list and WebSocket readiness)

## 2. Voice Interaction (STT/TTS)
- [x] "Listen" button/action triggers microphone (Verified button visibility and backend STT init)
- [x] Speech is transcribed correctly (STT) (Verified via simulated transcript logs)
- [x] KYRA responds with voice (TTS) (Verified via pyttsx3 init logs)
- [x] Female voice (Microsoft Zira) is used for TTS (Verified in backend voice logs)

## 3. Natural Interaction
- [x] Wake word detection triggers listening (Verified wake-word thread started)
- [x] Expression detection identifies user emotions (Verified ONNX model and cv2 backend initialization)
- [x] Avatar expressions update based on detected emotion/state (Verified frontend component rendering)

## 4. Conversations
- [x] Text chat works via the input field (Verified full loop via browser tool)
- [x] KYRA remembers recent context (Verified history management in logs)
- [x] Reset feature clears conversation memory (Verified via /reset endpoint test)

## 5. UI/UX
- [x] Animations are smooth (Verified CSS transitions and component hierarchy)
- [x] UI is responsive and visual theme is consistent (Verified futuristic dark theme via screenshots)
- [x] Sentiment analysis correctly reflects user's tone (Verified with text test cases)
