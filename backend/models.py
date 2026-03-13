from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── WebSocket message types (Frontend → Backend) ──────────────────────────────

class AudioMessage(BaseModel):
    type: str = "audio"
    data: str  # base64-encoded audio bytes


class FrameMessage(BaseModel):
    type: str = "frame"
    data: str  # base64-encoded JPEG


class GpsMessage(BaseModel):
    type: str = "gps"
    lat: float
    lng: float


class InterruptMessage(BaseModel):
    type: str = "interrupt"


# ── WebSocket message types (Backend → Frontend) ──────────────────────────────

class AudioResponse(BaseModel):
    type: str = "audio"
    data: str  # base64-encoded audio bytes


class TextResponse(BaseModel):
    type: str = "text"
    summary: str           # 5-7 word crisp summary for screen overlay
    detail: Optional[str] = None


class NavigationStep(BaseModel):
    direction: str
    distance: str
    instruction: str


class NavigationResponse(BaseModel):
    type: str = "navigation"
    destination: str
    steps: List[NavigationStep]


class StatusResponse(BaseModel):
    type: str = "status"
    state: str  # "thinking" | "speaking" | "ready" | "error"
    message: Optional[str] = None


# ── Firestore data models ─────────────────────────────────────────────────────

class UserProfile(BaseModel):
    name: Optional[str] = None
    preferences: List[str] = []
    home_country: Optional[str] = None
    created_at: Optional[datetime] = None


class Visit(BaseModel):
    place_name: str
    place_type: str  # "landmark" | "food" | "activity"
    lat: float
    lng: float
    timestamp: Optional[datetime] = None
    liked: bool = True
    notes: Optional[str] = None
    tags: List[str] = []


class Session(BaseModel):
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location_summary: Optional[str] = None
    turns: int = 0
    highlights: List[str] = []


# ── Internal agent context ────────────────────────────────────────────────────

class AgentContext(BaseModel):
    user_id: str
    session_id: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    recent_visits: List[Visit] = []
    preferences: List[str] = []
    conversation_turns: int = 0
