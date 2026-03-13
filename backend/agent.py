"""
Iris — Core Agent Logic

Orchestrates the full decision loop:
  RECEIVE → ENRICH → THINK → DECIDE → ACT → RESPOND
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from models import (
    AgentContext, Visit,
    NavigationResponse, TextResponse, StatusResponse, NavigationStep
)
from prompts import (
    build_full_context,
    extract_navigate_signal,
    extract_remember_signal,
    extract_summary,
    clean_response_text,
)
from gemini_client import GeminiClient
from maps_client import MapsClient
from firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class IrisAgent:
    """
    The brain of Iris. One instance lives per WebSocket session.
    """

    def __init__(
        self,
        gemini: GeminiClient,
        maps: MapsClient,
        firestore: FirestoreClient,
        context: AgentContext,
    ):
        self.gemini = gemini
        self.maps = maps
        self.firestore = firestore
        self.context = context
        self._interrupted = False
        self._full_response_buffer = ""

    # ── Public API (called by WebSocket handler) ───────────────────────────────

    def interrupt(self):
        """Signal that the user interrupted the agent mid-speech."""
        self._interrupted = True
        logger.info(f"[{self.context.session_id}] Agent interrupted")

    async def update_gps(self, lat: float, lng: float):
        """Update the agent's current GPS position."""
        self.context.lat = lat
        self.context.lng = lng

    async def process(
        self,
        frame_b64: Optional[str] = None,
        audio_b64: Optional[str] = None,
        user_text: Optional[str] = None,
    ):
        """
        Main entry point. Processes a combined input (frame + audio + text),
        runs the decision loop, and yields response messages as dicts.
        
        Yields dicts matching backend→frontend message schemas.
        """
        self._interrupted = False
        self._full_response_buffer = ""

        # 1. STATUS — let frontend know we're thinking
        yield StatusResponse(state="thinking").model_dump()

        # 2. ENRICH — load user context from Firestore
        if not self.context.recent_visits:
            self.context.recent_visits = await self.firestore.get_recent_visits(
                self.context.user_id, limit=5
            )
        if not self.context.preferences:
            self.context.preferences = await self.firestore.get_preferences(
                self.context.user_id
            )

        # 3. BUILD prompt context
        context_text = build_full_context(
            lat=self.context.lat,
            lng=self.context.lng,
            visits=self.context.recent_visits,
            preferences=self.context.preferences,
        )
        if user_text:
            context_text += f"\n\nUser says: {user_text}"

        # 4. THINK — stream from Gemini
        yield StatusResponse(state="speaking").model_dump()

        full_text = ""
        async for chunk in self.gemini.send_multimodal(
            text_context=context_text,
            frame_b64=frame_b64,
            audio_b64=audio_b64,
        ):
            if self._interrupted:
                logger.info("Response interrupted — stopping stream")
                break
            full_text += chunk

        self._full_response_buffer = full_text
        self.context.conversation_turns += 1

        # 5. DECIDE — parse signals from response
        navigate_dest = extract_navigate_signal(full_text)
        remember_item = extract_remember_signal(full_text)
        summary = extract_summary(full_text)
        clean_text = clean_response_text(full_text)

        # 6. ACT — navigation
        if navigate_dest and self.context.lat and self.context.lng:
            steps = await self.maps.get_walking_directions(
                origin_lat=self.context.lat,
                origin_lng=self.context.lng,
                destination=navigate_dest,
            )
            if steps:
                yield NavigationResponse(
                    destination=navigate_dest,
                    steps=steps,
                ).model_dump()
            else:
                logger.warning(f"No navigation steps found for: {navigate_dest}")

        # 6b. ACT — memory
        if remember_item:
            visit = _parse_remember_to_visit(remember_item, self.context)
            await self.firestore.save_visit(self.context.user_id, visit)
            # Also update local cache
            self.context.recent_visits.append(visit)
            if len(self.context.recent_visits) > 5:
                self.context.recent_visits = self.context.recent_visits[-5:]

        # 7. RESPOND — text overlay
        yield TextResponse(
            summary=summary,
            detail=clean_text,
        ).model_dump()

        # 8. STATUS — ready for next input
        yield StatusResponse(state="ready").model_dump()

    async def on_session_end(self):
        """Called when WebSocket closes — save session summary."""
        from models import Session
        session = Session(
            session_id=self.context.session_id,
            user_id=self.context.user_id,
            start_time=datetime.utcnow(),  # approximate
            turns=self.context.conversation_turns,
        )
        await self.firestore.save_session(session)
        logger.info(f"Session saved: {self.context.session_id}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_remember_to_visit(item_description: str, context: AgentContext) -> Visit:
    """
    Convert a [REMEMBER: ...] string into a Visit object.
    Best-effort parsing — falls back to generic values if unsure.
    """
    place_type = "landmark"
    tags = []
    
    lower = item_description.lower()
    if any(word in lower for word in ["food", "eat", "restaurant", "street food", "chai", "biryani", "dosa"]):
        place_type = "food"
        tags.append("food")
    elif any(word in lower for word in ["temple", "mosque", "church", "monument", "fort", "cave", "museum"]):
        place_type = "landmark"
        tags.append("cultural")
    elif any(word in lower for word in ["hike", "trek", "adventure", "beach", "waterfall"]):
        place_type = "activity"
        tags.append("outdoor")

    return Visit(
        place_name=item_description[:100],  # cap length
        place_type=place_type,
        lat=context.lat or 0.0,
        lng=context.lng or 0.0,
        liked=True,
        notes=item_description,
        tags=tags,
    )
