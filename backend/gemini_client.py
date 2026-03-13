"""
Iris — Gemini Client (google-genai SDK)

Uses the new google-genai SDK (replaces deprecated google-generativeai).
Model: gemini-3-flash-preview
"""

import asyncio
import base64
import logging
import os
from typing import AsyncGenerator, Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT

load_dotenv()
logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Wraps the new google-genai SDK for Iris.
    Uses gemini-3-flash-preview with streaming for low-latency responses.
    Supports text + image (camera frame) + audio inputs.
    """

    MODEL = "gemini-3-flash-preview"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("⚠️  GEMINI_API_KEY not set — Gemini calls will return placeholder responses")
            self._client = None
            return

        self._client = genai.Client(api_key=api_key)
        logger.info(f"✅ GeminiClient initialized | model: {self.MODEL}")

    def is_available(self) -> bool:
        return self._client is not None

    async def send_multimodal(
        self,
        text_context: str,
        frame_b64: Optional[str] = None,
        audio_b64: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send text + optional image frame + optional audio to Gemini,
        yielding text chunks as they stream back.

        Args:
            text_context: Enriched context string (location, history, user message)
            frame_b64:    Base64-encoded JPEG camera frame (optional)
            audio_b64:    Base64-encoded WebM audio (optional)

        Yields:
            Text chunks from Gemini's streaming response
        """
        if not self._client:
            yield "Iris is not fully configured yet. Please set GEMINI_API_KEY in backend/.env"
            return

        # ── Build content parts ──────────────────────────────────────────────
        parts = []

        # Camera frame → image/jpeg Part
        if frame_b64:
            try:
                parts.append(
                    types.Part.from_bytes(
                        data=base64.b64decode(frame_b64),
                        mime_type="image/jpeg",
                    )
                )
            except Exception as e:
                logger.warning(f"Could not decode camera frame: {e}")

        # Audio → audio/webm Part
        if audio_b64:
            try:
                parts.append(
                    types.Part.from_bytes(
                        data=base64.b64decode(audio_b64),
                        mime_type="audio/webm",
                    )
                )
            except Exception as e:
                logger.warning(f"Could not decode audio: {e}")

        # Text context (always last)
        parts.append(types.Part.from_text(text=text_context))

        contents = [types.Content(role="user", parts=parts)]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=512,
        )

        # ── Stream response ──────────────────────────────────────────────────
        try:
            # SDK streaming is synchronous — run in thread to not block event loop
            response_iter = await asyncio.to_thread(
                self._client.models.generate_content_stream,
                model=self.MODEL,
                contents=contents,
                config=config,
            )

            for chunk in response_iter:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            yield f"I'm having trouble reaching Gemini right now. ({type(e).__name__})"

    async def send_text_only(self, message: str) -> AsyncGenerator[str, None]:
        """Simple text-only streaming call (for suggestions, health checks)."""
        async for chunk in self.send_multimodal(text_context=message):
            yield chunk

    async def health_check(self) -> bool:
        """Verify Gemini connectivity — returns True if model responds."""
        if not self._client:
            return False
        try:
            result = ""
            async for chunk in self.send_text_only("Reply with exactly one word: OK"):
                result += chunk
            return "ok" in result.lower()
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
