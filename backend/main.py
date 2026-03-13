"""
Iris — FastAPI Backend
Main entry point: WebSocket handler + REST endpoints
"""

import json
import logging
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from models import AgentContext, UserProfile
from agent import IrisAgent
from gemini_client import GeminiClient
from maps_client import MapsClient
from firestore_client import FirestoreClient

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Iris — AI Travel Companion",
    description="Real-time multimodal travel agent powered by Gemini",
    version="1.0.0",
)

# CORS — allow all origins during dev, lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared singletons (created once at startup) ───────────────────────────────
gemini_client: GeminiClient = None
maps_client: MapsClient = None
firestore_client: FirestoreClient = None

# Track active sessions: session_id → IrisAgent
active_sessions: dict[str, IrisAgent] = {}


@app.on_event("startup")
async def startup():
    global gemini_client, maps_client, firestore_client
    logger.info("Starting Iris backend...")
    
    gemini_client = GeminiClient()
    maps_client = MapsClient()
    firestore_client = FirestoreClient()
    
    logger.info("✅ Iris backend ready")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "iris-backend",
        "timestamp": datetime.utcnow().isoformat(),
        "gemini": "configured" if os.getenv("GEMINI_API_KEY") else "missing key",
        "maps": "configured" if os.getenv("GOOGLE_MAPS_API_KEY") else "disabled",
        "firestore": "connected" if firestore_client and firestore_client.is_available() else "in-memory fallback",
    }


# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.post("/users/{user_id}/profile")
async def upsert_profile(user_id: str, profile: UserProfile):
    await firestore_client.save_profile(user_id, profile)
    return {"status": "saved", "user_id": user_id}


@app.get("/users/{user_id}/history")
async def get_history(user_id: str, limit: int = 10):
    visits = await firestore_client.get_recent_visits(user_id, limit=limit)
    return {"user_id": user_id, "visits": [v.model_dump() for v in visits]}


@app.get("/users/{user_id}/suggestions")
async def get_suggestions(user_id: str):
    """
    Simple suggestion endpoint — Gemini generates suggestions based on history.
    """
    visits = await firestore_client.get_recent_visits(user_id, limit=5)
    prefs = await firestore_client.get_preferences(user_id)
    
    if not visits:
        return {"suggestions": ["Explore a local landmark!", "Try some street food!", "Visit a museum"]}
    
    place_names = [v.place_name for v in visits]
    prompt = (
        f"The user has visited: {', '.join(place_names)}. "
        f"Their preferences: {', '.join(prefs) if prefs else 'unknown'}. "
        "Suggest 3 personalized next travel activities in 1 sentence each."
    )
    
    suggestions = []
    full_text = ""
    async for chunk in gemini_client.send_text_only(prompt):
        full_text += chunk
    
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    suggestions = lines[:3] if lines else ["Keep exploring!"]
    return {"user_id": user_id, "suggestions": suggestions}


# ── WebSocket Handler ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = "anonymous"):
    await websocket.accept()
    
    session_id = str(uuid.uuid4())
    logger.info(f"New WebSocket session: {session_id} (user: {user_id})")

    context = AgentContext(
        user_id=user_id,
        session_id=session_id,
    )
    agent = IrisAgent(
        gemini=gemini_client,
        maps=maps_client,
        firestore=firestore_client,
        context=context,
    )
    active_sessions[session_id] = agent

    # Send welcome message
    await websocket.send_json({
        "type": "status",
        "state": "ready",
        "message": f"Iris connected. Session: {session_id}",
    })

    try:
        while True:
            # Receive message from frontend
            raw = await websocket.receive_text()
            
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "status", "state": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "interrupt":
                agent.interrupt()
                await websocket.send_json({"type": "status", "state": "ready", "message": "Interrupted"})
                continue

            if msg_type == "gps":
                await agent.update_gps(
                    lat=float(msg.get("lat", 0)),
                    lng=float(msg.get("lng", 0)),
                )
                continue  # GPS update doesn't trigger a response

            # For audio, frame, or text messages — run the agent
            frame_b64 = None
            audio_b64 = None
            user_text = None

            if msg_type == "frame":
                frame_b64 = msg.get("data")
            elif msg_type == "audio":
                audio_b64 = msg.get("data")
            elif msg_type == "text":
                user_text = msg.get("data", "")
            elif msg_type == "multimodal":
                # Frontend can batch all data in one message
                frame_b64 = msg.get("frame")
                audio_b64 = msg.get("audio")
                user_text = msg.get("text")
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                continue

            # Run agent decision loop and stream back responses
            async for response_msg in agent.process(
                frame_b64=frame_b64,
                audio_b64=audio_b64,
                user_text=user_text,
            ):
                await websocket.send_json(response_msg)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error [{session_id}]: {e}")
        try:
            await websocket.send_json({"type": "status", "state": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Clean up session
        if session_id in active_sessions:
            await active_sessions[session_id].on_session_end()
            del active_sessions[session_id]
        logger.info(f"Session cleaned up: {session_id}")


# ── Serve frontend static files ───────────────────────────────────────────────
import pathlib
FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    # Mount the whole frontend dir at /static so CSS/JS load at /static/<file>
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "message": "Iris backend running",
            "docs": "/docs",
            "health": "/health",
            "websocket": "ws://localhost:8000/ws?user_id=your_id",
        }
