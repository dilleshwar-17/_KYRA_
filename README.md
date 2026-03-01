# KYRA — AI Desktop Assistant

> **Knowledgeable Yet Responsive Assistant**  
> A personal AI assistant powered by **SambaNova AI** (Llama 3.3 70B) with a floating animated avatar, real-time facial expression detection, voice I/O, and a modern Electron + React UI.

---

## Features

- 💬 **Text chat** with SambaNova Llama 3.3 70B AI
- 🎤 **Voice input** via SpeechRecognition (press **Space** or the mic button)
- 🔊 **Voice output** via pyttsx3
- 🌟 **Animated SVG avatar** — 8 states: idle, listening, thinking, talking, happy, sad, angry, surprised
- 👁️ **Facial expression detection** — OpenCV + ONNX Runtime, drives avatar reactions in real time
- 🖥️ **Transparent floating overlay** — always-on-top, draggable avatar window
- 🧠 **Conversation memory** — KYRA remembers context within a session

---

## Quick Start

### 1. Configure the backend

Edit `backend/.env`:
```
SAMBANOVA_API_KEY=your_key_here
```
Get a free key at [cloud.sambanova.ai](https://cloud.sambanova.ai/)

### 2. Install & run the backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```
> Backend starts at `http://localhost:8000`

### 3. Install & run the Electron app
```bash
cd frontend
npm install
npm run electron:dev
```
> The **KYRA avatar** floats in the bottom-right corner of your screen.

### 4. (Optional) Browser-only mode
```bash
cd frontend
npm run dev
```
> Opens at `http://localhost:5173`

---

## Project Structure
```
jarvis/
├── backend/
│   ├── main.py               ← FastAPI server (REST + WebSocket)
│   ├── engine.py             ← SambaNova AI integration
│   ├── voice.py              ← STT (SpeechRecognition) + TTS (pyttsx3)
│   ├── expression_detector.py← OpenCV + ONNX emotion detection
│   ├── models/               ← emotion-ferplus-8.onnx (auto-downloaded)
│   ├── requirements.txt
│   └── .env                  ← ⚠️ Add your SambaNova API key here
└── frontend/
    ├── electron/             ← Electron main process (transparent window)
    ├── src/
    │   ├── App.tsx           ← Main UI + chat app
    │   ├── components/
    │   │   ├── AvatarFace.tsx    ← Animated SVG avatar
    │   │   └── AvatarOverlay.tsx ← Floating transparent window overlay
    │   └── index.css         ← Dark glassmorphism theme
    └── package.json
```

---

## Usage

| Action | Result |
|---|---|
| 😊 Smile at webcam | Avatar bounces happily, glows gold |
| 😲 Look surprised | Avatar widens eyes, glows orange |
| 😠 Frown | Avatar turns red |
| 😢 Sad face | Avatar shows tear effect, blue hue |
| **Drag** avatar | Moves the floating window |
| **Right-click** avatar | Opens full KYRA chat window |
| Press **Space** | Starts voice listening |
