"""
Iris — Firestore Client

Reads and writes user memory (visits, preferences, sessions) to Firestore.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from models import UserProfile, Visit, Session

load_dotenv()
logger = logging.getLogger(__name__)


class FirestoreClient:
    def __init__(self):
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        db_name = os.getenv("FIRESTORE_DATABASE", "(default)")
        
        if not project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set — Firestore will be disabled (in-memory fallback active)")
            self._db = None
            self._memory: dict = {}  # in-memory fallback for local dev
        else:
            try:
                from google.cloud import firestore
                self._db = firestore.AsyncClient(project=project_id, database=db_name)
                logger.info(f"FirestoreClient connected to project: {project_id}")
            except Exception as e:
                logger.warning(f"Firestore init failed: {e} — using in-memory fallback")
                self._db = None
                self._memory = {}

    def is_available(self) -> bool:
        return self._db is not None

    # ── User Profile ──────────────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        if not self._db:
            return None
        try:
            doc = await self._db.collection("users").document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                profile_data = data.get("profile", {})
                return UserProfile(**profile_data)
        except Exception as e:
            logger.error(f"Firestore get_profile error: {e}")
        return None

    async def save_profile(self, user_id: str, profile: UserProfile) -> None:
        if not self._db:
            return
        try:
            await self._db.collection("users").document(user_id).set(
                {"profile": profile.model_dump()}, merge=True
            )
        except Exception as e:
            logger.error(f"Firestore save_profile error: {e}")

    # ── Visits / Travel Memory ────────────────────────────────────────────────

    async def get_recent_visits(self, user_id: str, limit: int = 5) -> List[Visit]:
        if not self._db:
            # In-memory fallback
            visits = self._memory.get(f"{user_id}_visits", [])
            return visits[-limit:]

        try:
            from google.cloud.firestore import Query
            query = (
                self._db.collection("users")
                .document(user_id)
                .collection("visits")
                .order_by("timestamp", direction=Query.DESCENDING)
                .limit(limit)
            )
            docs = query.stream()
            visits = []
            async for doc in docs:
                data = doc.to_dict()
                visits.append(Visit(**data))
            return visits
        except Exception as e:
            logger.error(f"Firestore get_recent_visits error: {e}")
            return []

    async def save_visit(self, user_id: str, visit: Visit) -> None:
        if not self._db:
            # In-memory fallback
            key = f"{user_id}_visits"
            if key not in self._memory:
                self._memory[key] = []
            visit.timestamp = datetime.utcnow()
            self._memory[key].append(visit)
            logger.info(f"[IN-MEMORY] Saved visit: {visit.place_name}")
            return

        try:
            visit_id = str(uuid.uuid4())
            visit.timestamp = datetime.utcnow()
            await (
                self._db.collection("users")
                .document(user_id)
                .collection("visits")
                .document(visit_id)
                .set(visit.model_dump())
            )
            logger.info(f"Saved visit to Firestore: {visit.place_name}")
        except Exception as e:
            logger.error(f"Firestore save_visit error: {e}")

    # ── Sessions ──────────────────────────────────────────────────────────────

    async def save_session(self, session: Session) -> None:
        if not self._db:
            logger.info(f"[IN-MEMORY] Session ended: {session.session_id} ({session.turns} turns)")
            return

        try:
            session.end_time = datetime.utcnow()
            await (
                self._db.collection("users")
                .document(session.user_id)
                .collection("sessions")
                .document(session.session_id)
                .set(session.model_dump())
            )
        except Exception as e:
            logger.error(f"Firestore save_session error: {e}")

    async def get_preferences(self, user_id: str) -> List[str]:
        profile = await self.get_profile(user_id)
        if profile:
            return profile.preferences
        return []
