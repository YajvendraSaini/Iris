# Iris 🌍
### See the World. Hear the World. Know the World.

Real-time AI travel companion — point your camera, speak naturally, and Iris explains the world around you.

Built for the **Google Gemini Live Agent Challenge** using 100% Google Cloud + Gemini 2.0 Flash.

---

## What Iris Does

- 📸 **Live Vision** — Camera feed sent to Gemini in real-time
- 🎙️ **Voice Input** — Speak naturally, agent understands
- 🔊 **Audio Response** — Agent speaks back with explanation  
- 📝 **Text Overlay** — Crisp summary on camera feed
- 📍 **GPS Context** — Agent knows exactly where you are
- ✋ **Interruption** — Cut the agent off mid-sentence
- 🏛️ **Place Recognition** — Identify landmarks, food, objects
- 🗺️ **AR Navigation** — Directional arrows overlaid on camera
- 🧠 **Travel Memory** — Saves visited places and preferences

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.11+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/) (free)

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys:
# GEMINI_API_KEY=your_key_from_ai_studio
```

### 3. Run the backend

```bash
# From the backend/ directory:
uvicorn main:app --reload --port 8000
```

### 4. Open the frontend

Open `frontend/index.html` directly in a browser, **or** visit:
```
http://localhost:8000
```
(The backend also serves the frontend as static files.)

### 5. Test in browser
- Allow camera + microphone when prompted
- Hold the purple mic button to speak
- Point camera at anything — Iris will describe it
- Type messages in the bottom input (desktop fallback)

---

## Running & Testing — Quick Reference

> **This section is repeated in every response. Here's how to run Iris at each stage:**

| Stage | Command |
|---|---|
| Install deps | `cd backend && pip install -r requirements.txt` |
| Run backend  | `cd backend && uvicorn main:app --reload` |
| Open frontend | Browse to `http://localhost:8000` |
| Health check | `curl http://localhost:8000/health` |
| API docs | Browse to `http://localhost:8000/docs` |

---

## Project Structure

```
iris_Agent/
├── backend/
│   ├── main.py             # FastAPI + WebSocket handler
│   ├── agent.py            # Core agent decision loop
│   ├── gemini_client.py    # Gemini 2.0 Flash API
│   ├── maps_client.py      # Google Maps Directions
│   ├── firestore_client.py # Firestore memory
│   ├── models.py           # Pydantic data models
│   ├── prompts.py          # System prompt + builders
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html          # Mobile-first UI
│   ├── app.js              # WebSocket + camera + mic
│   ├── ar_overlay.js       # Canvas AR arrows
│   └── styles.css
├── infra/
│   ├── deploy.sh           # Cloud Run deploy script
│   └── cloudbuild.yaml     # CI/CD config
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Brain | Gemini 2.0 Flash (Google GenAI SDK) |
| Backend | FastAPI + Python 3.11 |
| Frontend | Vanilla HTML/CSS/JS |
| Real-time | WebSocket |
| Navigation | Google Maps Directions API |
| Memory | Firestore (Google Cloud) |
| Hosting | Google Cloud Run |
| AR Overlay | HTML5 Canvas API |

---

## Environment Variables

```bash
# backend/.env
GEMINI_API_KEY=your_key_from_ai_studio
GOOGLE_MAPS_API_KEY=your_key_from_google_cloud_console  # optional
GOOGLE_CLOUD_PROJECT=your_gcp_project_id                # optional (in-memory fallback if missing)
FIRESTORE_DATABASE=(default)
```

> **Note:** Only `GEMINI_API_KEY` is required to run locally. Maps and Firestore gracefully fall back if not configured.

---

## Deploy to Cloud Run

```bash
chmod +x infra/deploy.sh
# Edit PROJECT_ID in infra/deploy.sh first
./infra/deploy.sh
```

Then set secret env vars in [Cloud Run Console](https://console.cloud.google.com/run).

---

## Hackathon: Google Gemini Live Agent Challenge

- Uses **Gemini 2.0 Flash** multimodal model
- Built with **Google GenAI SDK**
- Deployed on **Google Cloud Run**
- Uses **Firestore** for persistent memory
- Uses **Google Maps API** for navigation
