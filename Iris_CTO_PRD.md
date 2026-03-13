# Iris — CTO-Level Master Document
### "See the World. Hear the World. Know the World."
> This document is the single source of truth for building Iris.
> Feed this to Cursor and build step by step.

---

## TABLE OF CONTENTS
1. [The Idea](#1-the-idea)
2. [Problem & Solution](#2-problem--solution)
3. [Core Features (PRD)](#3-core-features-prd)
4. [Tech Stack](#4-tech-stack)
5. [High-Level Architecture](#5-high-level-architecture)
6. [System Design](#6-system-design)
7. [Data Models](#7-data-models)
8. [API Design](#8-api-design)
9. [Agent Logic & Decision Flow](#9-agent-logic--decision-flow)
10. [Security & Best Practices](#10-security--best-practices)
11. [Folder Structure](#11-folder-structure)
12. [Step-by-Step Build Plan](#12-step-by-step-build-plan)
13. [Hackathon Checklist](#13-hackathon-checklist)

---

## 1. THE IDEA

**Iris** is a real-time AI travel companion that lives in your mobile browser.

You pull out your phone, point the camera at anything around you — a temple, a street food stall, a sign in a foreign language, a cave entrance — speak naturally, and the agent responds with:
- A spoken audio explanation (via your speaker)
- A crisp text overlay on the live camera feed
- Live AR navigation arrows overlaid on the real world when you want to move
- Personalized suggestions based on your travel history

**One line:** Point. Ask. Understand. Navigate. Remember.

---

## 2. PROBLEM & SOLUTION

### The Problem
- Tourists open 5 different apps to do what one should do (Maps, Translate, Wikipedia, TripAdvisor, Camera)
- Language barriers make cultural understanding surface-level
- Generic travel apps give the same recommendations to everyone
- No app truly understands what you're physically looking at right now

### The Solution
Iris collapses all of this into a single real-time voice + vision agent.
The agent sees what you see, hears what you say, knows where you are, and remembers who you are.

---

## 3. CORE FEATURES (PRD)

### MUST HAVE (Hackathon MVP)

| Feature | Description | Priority |
|---|---|---|
| Live Vision | Camera feed sent to Gemini in real-time | P0 |
| Voice Input | User speaks naturally, agent understands | P0 |
| Audio Response | Agent speaks back with explanation | P0 |
| Text Overlay | Crisp summary text on camera feed | P0 |
| GPS Context | Agent knows exactly where user is | P0 |
| Interruption Handling | User can cut agent off mid-sentence | P0 |
| Place Recognition | Identify landmarks, food, objects from camera | P1 |
| AR Navigation | Directional arrows overlaid on camera feed | P1 |
| Travel Memory | Saves places visited, food tried, preferences | P1 |
| Personalized Suggestions | Based on memory, suggest next things to do | P1 |

### NICE TO HAVE (Post-hackathon)
- Multi-language support
- Offline mode for remote areas
- Ticket/transport booking by voice
- Social sharing of discoveries
- Trip report generation

---

## 4. TECH STACK

### Why 100% Google Tech
The hackathon requires Google Cloud + Gemini. Using Google's full ecosystem also means:
- Better integration between services (auth, IAM, billing all in one place)
- Less debugging cross-platform auth issues
- Judges can verify Google usage easily

### Complete Stack

| Layer | Technology | Why This One |
|---|---|---|
| **AI Brain** | Gemini 2.0 Flash Live API | Real-time multimodal audio+vision, lowest latency |
| **Agent Framework** | Google GenAI SDK (Python) | Required by hackathon, handles Gemini connection |
| **Backend** | FastAPI (Python) | Async-first, perfect for WebSocket + streaming |
| **Frontend** | Vanilla HTML/CSS/JS | No build step, runs instantly, mobile-friendly |
| **Real-time Comms** | WebSocket | Persistent connection for live audio+video streaming |
| **Navigation** | Google Maps Directions API | Step-by-step walking directions as raw data |
| **Database** | Firestore (Google Cloud) | Real-time NoSQL, perfect for user memory/history |
| **File Storage** | Google Cloud Storage | Store session snapshots if needed |
| **Hosting** | Google Cloud Run | Serverless containers, scales to zero, free tier |
| **Containerization** | Docker | Required for Cloud Run deployment |
| **AR Overlay** | HTML5 Canvas API | Draw arrows on camera feed, no external library needed |
| **Environment** | Python 3.11+ | Stable, async support |

---

## 5. HIGH-LEVEL ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER'S MOBILE BROWSER                      │
│                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │  Camera  │   │    Mic   │   │   GPS    │   │   Speaker    │  │
│  │  Feed    │   │  Input   │   │ Location │   │   Output     │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────▲───────┘  │
│       │              │              │                 │          │
│  ┌────▼──────────────▼──────────────▼─────────────────┴───────┐  │
│  │                    FRONTEND (HTML/JS)                       │  │
│  │   Canvas Layer (AR arrows) + Text Overlay + Camera Feed     │  │
│  └────────────────────────────┬────────────────────────────────┘  │
└───────────────────────────────┼────────────────────────────────────┘
                                │
                         WebSocket (wss://)
                         Persistent Connection
                                │
┌───────────────────────────────▼────────────────────────────────────┐
│                    GOOGLE CLOUD RUN                                  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       IRIS AGENT                               │  │
│  │                   (FastAPI + Python)                          │  │
│  │                                                               │  │
│  │  1. RECEIVE    → Audio bytes + Camera frame + GPS coords      │  │
│  │  2. ENRICH     → Fetch user memory from Firestore             │  │
│  │  3. THINK      → Send everything to Gemini Live API           │  │
│  │  4. DECIDE     → Navigate? Explain? Remember? Suggest?        │  │
│  │  5. ACT        → Call Maps API / Write to Firestore           │  │
│  │  6. RESPOND    → Audio + Text + Navigation back to frontend   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│          │                    │                    │                 │
│          ▼                    ▼                    ▼                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │  Gemini      │   │  Google      │   │  Firestore           │    │
│  │  Live API    │   │  Maps API    │   │  (User Memory)       │    │
│  │  (AI Brain)  │   │  (Nav Data)  │   │  (Travel History)    │    │
│  └──────────────┘   └──────────────┘   └──────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. SYSTEM DESIGN

### 6.1 WebSocket Design
The WebSocket is the backbone. Everything flows through it.

```
Connection Lifecycle:
──────────────────────────────────────────────
1. User opens browser → Frontend connects to wss://backend/ws
2. Backend assigns session_id to this connection
3. Backend loads user history from Firestore
4. Connection stays OPEN for entire session
5. Data flows both directions continuously
6. On disconnect → Backend saves final session summary to Firestore
──────────────────────────────────────────────

Message Types (Frontend → Backend):
{
  "type": "audio",        // raw audio bytes as base64
  "type": "frame",        // camera frame as base64 JPEG
  "type": "gps",          // { lat: 20.02, lng: 75.17 }
  "type": "interrupt"     // user interrupted agent mid-speech
}

Message Types (Backend → Frontend):
{
  "type": "audio",        // agent voice as base64 audio bytes
  "type": "text",         // overlay text { summary, detail }
  "type": "navigation",   // { steps: [{direction, distance}] }
  "type": "status"        // { state: "thinking" | "speaking" | "ready" }
}
```

### 6.2 Streaming Architecture
Gemini Live API streams responses. This means:
- Agent starts speaking before it finishes thinking
- Frontend plays audio as chunks arrive, not after all of it is ready
- This makes the experience feel instant and natural

```
Gemini streams:    [chunk1][chunk2][chunk3][chunk4][done]
Frontend plays:    ▶chunk1 ▶chunk2 ▶chunk3 ▶chunk4
                   (starts playing before chunk4 even arrives)
```

### 6.3 Frame Sampling Strategy
Sending every camera frame to Gemini is wasteful and expensive.
Smart sampling:

```python
FRAME_INTERVAL = 2.0  # seconds between frames normally
FRAME_INTERVAL_ACTIVE = 0.5  # when user is speaking, sample faster

# Only send frame if it changed significantly from last frame
# Use pixel difference threshold to detect change
CHANGE_THRESHOLD = 0.15  # 15% pixel change triggers new frame send
```

### 6.4 Context Window Management
Gemini has a context window limit. Smart management:

```python
# Each message to Gemini includes:
context = {
    "system": SYSTEM_PROMPT,           # who the agent is (fixed)
    "location": current_gps,           # always fresh
    "current_frame": latest_frame,     # always fresh
    "user_history": last_5_visits,     # rolling window, not all history
    "conversation": last_3_exchanges,  # recent convo only
}
# DO NOT send entire conversation history every time
# It bloats cost and confuses the model
```

### 6.5 Session Management
```
Each user session:
  session_id = UUID generated on WebSocket connect
  session_data = {
      user_id,
      start_time,
      locations_seen: [],
      things_tried: [],
      conversation_turns: 0
  }
  
On session end → summarize + save to Firestore
```

---

## 7. DATA MODELS

### Firestore Collections

```
/users/{user_id}/
    profile: {
        name: string,
        preferences: string[],      // ["history", "vegetarian", "adventure"]
        home_country: string,
        created_at: timestamp
    }
    
/users/{user_id}/visits/{visit_id}/
    place_name: string,             // "Kailasa Temple, Ellora"
    place_type: string,             // "landmark" | "food" | "activity"
    lat: number,
    lng: number,
    timestamp: timestamp,
    liked: boolean,
    notes: string,                  // what Gemini said about it
    tags: string[]                  // ["ancient", "hindu", "cave", "8th century"]

/users/{user_id}/sessions/{session_id}/
    start_time: timestamp,
    end_time: timestamp,
    location_summary: string,       // "Ellora, Maharashtra, India"
    turns: number,                  // how many exchanges happened
    highlights: string[]            // top 3 things seen this session
```

### Why Firestore and not Postgres?
- No schema management needed — great for hackathon speed
- Real-time listeners built in
- Native Google Cloud integration
- Free tier: 50k reads/day, 20k writes/day — more than enough

---

## 8. API DESIGN

### Backend Endpoints

```
WebSocket:
  WS  /ws?user_id={id}          Main real-time connection

REST (for non-realtime operations):
  GET  /health                   Health check (for Cloud Run)
  POST /users/{id}/profile       Create/update user profile
  GET  /users/{id}/history       Get travel history
  GET  /users/{id}/suggestions   Get next trip suggestions
```

### System Prompt (The Agent's Personality)
This is what makes the agent intelligent. Feed this to Gemini:

```
You are Iris, a real-time AI travel companion.

You can see through the user's camera and hear their voice.
You know their GPS location at all times.
You have access to their travel history and preferences.

YOUR PERSONALITY:
- Warm, knowledgeable, like a local friend who knows everything
- Concise. Never speak for more than 30 seconds at a time
- Culturally sensitive and respectful
- Proactively suggest things without being pushy

YOUR CAPABILITIES:
- Identify any landmark, food, object, or place from camera
- Explain cultural/historical context in simple terms
- Provide navigation guidance when asked
- Remember what the user has seen and liked
- Suggest personalized next activities based on history

RESPONSE FORMAT:
- Always respond with spoken audio (natural conversational tone)
- Extract a 5-7 word crisp summary for screen display
- If navigation is needed, signal with [NAVIGATE: destination name]
- If something should be saved to memory, signal with [REMEMBER: item]

RULES:
- Never make up historical facts
- If unsure, say you're unsure
- Always be aware of user's current GPS location
- Keep responses under 60 words unless user asks for more detail
```

---

## 9. AGENT LOGIC & DECISION FLOW

This is the brain of the agent. Every incoming message goes through this:

```python
async def process_input(audio, frame, gps, user_id):
    
    # 1. ENRICH — add context
    user_history = await firestore.get_recent_visits(user_id, limit=5)
    user_prefs = await firestore.get_preferences(user_id)
    
    # 2. BUILD PROMPT — everything Gemini needs
    prompt = build_context(
        frame=frame,
        gps=gps,
        history=user_history,
        preferences=user_prefs
    )
    
    # 3. THINK — send to Gemini Live
    response = await gemini.send(audio=audio, image=frame, text=prompt)
    
    # 4. PARSE RESPONSE — what does agent want to do?
    if "[NAVIGATE:" in response.text:
        destination = extract_destination(response.text)
        nav_data = await maps.get_directions(gps, destination)
        await websocket.send_navigation(nav_data)
    
    if "[REMEMBER:" in response.text:
        item = extract_memory_item(response.text)
        await firestore.save_visit(user_id, item, gps)
    
    # 5. RESPOND — always send audio + text back
    await websocket.send_audio(response.audio)
    await websocket.send_text(response.summary)
```

---

## 10. SECURITY & BEST PRACTICES

### 10.1 Never Expose API Keys
```python
# BAD — never do this
GEMINI_API_KEY = "AIzaSy..."  # hardcoded in code

# GOOD — always use environment variables
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
```

Store all keys in `.env` file locally.
On Cloud Run, set them as **Secret Manager** secrets — never as plain env vars.

### 10.2 .gitignore (CRITICAL)
```gitignore
.env
*.env
__pycache__/
.DS_Store
node_modules/
*.pyc
service-account-key.json
```
**If you push API keys to GitHub, Google will detect and revoke them automatically. But don't do it anyway.**

### 10.3 Rate Limiting
Gemini API has rate limits. Protect yourself:
```python
# Max frames per second to Gemini
MAX_FRAMES_PER_SECOND = 0.5  # 1 frame every 2 seconds

# Max WebSocket connections per user
MAX_CONNECTIONS_PER_USER = 1

# Timeout idle sessions
SESSION_TIMEOUT_MINUTES = 30
```

### 10.4 CORS
Only allow your frontend domain:
```python
# During development
allow_origins=["*"]

# In production (Cloud Run)
allow_origins=["https://your-frontend-domain.com"]
```

### 10.5 Error Handling
Every external API call MUST be wrapped in try/except:
```python
try:
    response = await gemini.send(...)
except google.api_core.exceptions.ResourceExhausted:
    # Rate limit hit — send fallback response to user
    await websocket.send_text("Give me a moment...")
except Exception as e:
    logger.error(f"Iris agent error: {e}")
    await websocket.send_text("Something went wrong, try again")
```

### 10.6 Cloud Run Best Practices
```dockerfile
# Always pin versions
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m appuser
USER appuser

# Don't copy .env into Docker image
COPY requirements.txt .
COPY main.py .
# NOT: COPY .env .   ← never do this
```

### 10.7 Firestore Security Rules
```javascript
// Only authenticated users can read/write their own data
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null 
                         && request.auth.uid == userId;
    }
  }
}
```

---

## 11. FOLDER STRUCTURE

```
iris/
│
├── backend/
│   ├── main.py                  # FastAPI app + WebSocket handler
│   ├── agent.py                 # Core agent logic + decision flow
│   ├── gemini_client.py         # Gemini Live API connection
│   ├── maps_client.py           # Google Maps API calls
│   ├── firestore_client.py      # Firestore read/write
│   ├── models.py                # Pydantic data models
│   ├── prompts.py               # System prompt + prompt builders
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # For Cloud Run deployment
│   └── .env                     # API keys (never commit this)
│
├── frontend/
│   ├── index.html               # Main app UI
│   ├── app.js                   # WebSocket + camera + mic logic
│   ├── ar_overlay.js            # Canvas-based AR arrow drawing
│   └── styles.css               # Mobile-first styling
│
├── infra/
│   ├── deploy.sh                # One-command Cloud Run deploy
│   └── cloudbuild.yaml          # CI/CD config (bonus points)
│
├── docs/
│   ├── architecture.png         # Architecture diagram for submission
│   └── demo_script.md           # What to show in demo video
│
├── .gitignore
└── README.md                    # Spin-up instructions for judges
```

---

## 12. STEP-BY-STEP BUILD PLAN

### DAY 1 — Foundation (Backend + WebSocket)
**Goal: Frontend and backend can talk to each other**

```
Task 1: Create folder structure
Task 2: Write requirements.txt and pip install
Task 3: Write main.py with basic FastAPI + WebSocket
Task 4: Write index.html with WebSocket connect + send/receive
Task 5: Test: open browser → connect → send text → receive text back
```
✅ Done when: You see messages flowing both ways in browser console

---

### DAY 2 — Gemini Integration (The Brain)
**Goal: Backend talks to Gemini, Gemini responds**

```
Task 1: Get Gemini API key from Google AI Studio (free)
Task 2: Write gemini_client.py — connect to Gemini Live API
Task 3: Write prompts.py — system prompt
Task 4: In agent.py — send text to Gemini, get text response back
Task 5: Send Gemini's response back through WebSocket to browser
Task 6: Test: type a question → Gemini answers → see in browser
```
✅ Done when: Gemini answers your typed questions in the browser

---

### DAY 3 — Camera + Mic (Eyes and Ears)
**Goal: Real camera feed + voice input working**

```
Task 1: Add camera stream to frontend (getUserMedia)
Task 2: Capture frame every 2 seconds → send to backend as base64
Task 3: Add mic recording to frontend (MediaRecorder)
Task 4: Send audio chunks to backend over WebSocket
Task 5: In backend — pass frame + audio to Gemini together
Task 6: Gemini responds to what it SEES + HEARS
Task 7: Test: point camera at something, speak → Gemini describes it
```
✅ Done when: You point camera at your hand and Gemini describes what it sees

---

### DAY 4 — GPS + Maps + AR Navigation
**Goal: Agent knows where you are + can navigate**

```
Task 1: Add GPS capture to frontend (geolocation API)
Task 2: Send GPS coords with every WebSocket message
Task 3: Inject GPS into Gemini prompt context
Task 4: Get Google Maps API key + enable Directions API
Task 5: Write maps_client.py — get walking directions
Task 6: Parse Gemini response for [NAVIGATE: X] signals
Task 7: Call Maps API when navigation requested
Task 8: In frontend — draw arrows on canvas over camera feed
Task 9: Test: say "take me to the entrance" → arrows appear on screen
```
✅ Done when: Direction arrows appear overlaid on live camera feed

---

### DAY 5 — Memory (Firestore)
**Goal: Agent remembers you across sessions**

```
Task 1: Create Firestore database in Google Cloud Console
Task 2: Write firestore_client.py — read/write user history
Task 3: On session start — load last 5 visits from Firestore
Task 4: Inject history into Gemini prompt
Task 5: Parse [REMEMBER: X] signals from Gemini response
Task 6: Save to Firestore when agent signals memory
Task 7: Test: visit a "place" → refresh browser → agent remembers it
```
✅ Done when: Agent says "You visited X yesterday, want something similar?"

---

### DAY 6 — Deploy to Google Cloud Run
**Goal: App is live on the internet, not just localhost**

```
Task 1: Write Dockerfile
Task 2: Test Docker build locally: docker build + docker run
Task 3: Install Google Cloud CLI (gcloud)
Task 4: Run: gcloud auth login
Task 5: Run: gcloud run deploy iris --source .
Task 6: Set environment variables (API keys) in Cloud Run console
Task 7: Test deployed URL — everything still works
Task 8: Record GCP deployment proof screen recording
```
✅ Done when: App works on a live https:// URL from Cloud Run

---

### DAY 7 — Polish + Submission
**Goal: Submit a winner**

```
Task 1: Handle edge cases (no GPS, mic denied, bad connection)
Task 2: Test interruption handling — cut agent off mid-sentence
Task 3: Mobile browser test (this is a phone app!)
Task 4: Record 4-minute demo video (go outside, point at real things)
Task 5: Draw architecture diagram (use Excalidraw.com — free)
Task 6: Write README with clear spin-up instructions
Task 7: Make GitHub repo public
Task 8: Write text description for submission
Task 9: SUBMIT
```
✅ Done when: Submitted before deadline

---

## 13. HACKATHON CHECKLIST

### Mandatory Requirements
- [x] Uses Gemini model (Gemini 2.0 Flash Live)
- [x] Built with Google GenAI SDK
- [x] Uses Google Cloud service (Cloud Run + Firestore + Maps)
- [x] Live Agent track (real-time audio + vision + interruption)
- [x] Hosted on Google Cloud

### Submission Deliverables
- [ ] Text description (features, tech, learnings)
- [ ] Public GitHub repo with README spin-up instructions
- [ ] GCP deployment proof (screen recording of Cloud Run console)
- [ ] Architecture diagram (PNG in repo + submission)
- [ ] Demo video under 4 minutes, showing real multimodal features

### Bonus Points
- [ ] Blog post about how it was built (#GeminiLiveAgentChallenge)
- [ ] Automated deployment script (infra/deploy.sh)
- [ ] Google Developer Group signup

---

## ENVIRONMENT VARIABLES REFERENCE

```bash
# backend/.env
GEMINI_API_KEY=your_key_from_ai_studio
GOOGLE_MAPS_API_KEY=your_key_from_google_cloud_console
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
FIRESTORE_DATABASE=(default)
```

---

## README TEMPLATE (for judges)

```markdown
# Iris 🌍
### See the World. Hear the World. Know the World.

Real-time AI travel companion — point your camera, ask anything.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js (optional, for dev server)
- Google Cloud account

### Setup

1. Clone repo
   git clone https://github.com/yourname/iris

2. Install dependencies
   cd backend && pip install -r requirements.txt

3. Set environment variables
   cp .env.example .env
   # Fill in your API keys

4. Run locally
   uvicorn main:app --reload

5. Open frontend
   Open frontend/index.html in browser

### Deploy to Cloud Run
   chmod +x infra/deploy.sh
   ./infra/deploy.sh
```

---

*Document Version: 1.0*
*Project: Iris*
*Hackathon: Google Gemini Live Agent Challenge*
