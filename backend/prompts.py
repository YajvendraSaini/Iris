"""
Iris — System Prompt & Prompt Builders
"""

from typing import List, Optional
from models import Visit


# ── Core system prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Iris, a real-time AI travel companion.

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
- Extract a 5-7 word crisp summary for screen display after your spoken response, on a new line prefixed with SUMMARY:
- If navigation is needed, signal with [NAVIGATE: destination name]
- If something should be saved to memory, signal with [REMEMBER: item description]

RULES:
- Never make up historical facts
- If unsure, say you're unsure
- Always be aware of user's current GPS location
- Keep responses under 60 words unless user asks for more detail
- Do NOT include [NAVIGATE:] or [REMEMBER:] tags in your spoken audio — they are metadata signals only
"""


# ── Context builders ──────────────────────────────────────────────────────────

def build_location_context(lat: Optional[float], lng: Optional[float]) -> str:
    if lat is None or lng is None:
        return "GPS location: unknown"
    return f"GPS coordinates: {lat:.6f}, {lng:.6f} — use these to provide hyper-local context"


def build_history_context(visits: List[Visit]) -> str:
    if not visits:
        return "User travel history: none yet — this might be their first trip with Iris"
    
    lines = ["User's recent travel history (use this to personalize responses):"]
    for v in visits:
        tags = ", ".join(v.tags) if v.tags else "no tags"
        liked = "✓ liked" if v.liked else "✗ did not like"
        lines.append(f"  • {v.place_name} ({v.place_type}) — {liked} — tags: {tags}")
        if v.notes:
            lines.append(f"    Notes: {v.notes}")
    return "\n".join(lines)


def build_preferences_context(preferences: List[str]) -> str:
    if not preferences:
        return "User preferences: unknown"
    return f"User preferences: {', '.join(preferences)}"


def build_full_context(
    lat: Optional[float],
    lng: Optional[float],
    visits: List[Visit],
    preferences: List[str],
) -> str:
    """Build the full text context injected into every Gemini request."""
    parts = [
        "=== IRIS CONTEXT ===",
        build_location_context(lat, lng),
        build_history_context(visits),
        build_preferences_context(preferences),
        "===================",
    ]
    return "\n".join(parts)


# ── Response parsers ──────────────────────────────────────────────────────────

def extract_navigate_signal(text: str) -> Optional[str]:
    """Extract destination from [NAVIGATE: <destination>] signal."""
    import re
    match = re.search(r'\[NAVIGATE:\s*(.+?)\]', text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_remember_signal(text: str) -> Optional[str]:
    """Extract item from [REMEMBER: <item>] signal."""
    import re
    match = re.search(r'\[REMEMBER:\s*(.+?)\]', text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_summary(text: str) -> Optional[str]:
    """Extract SUMMARY: line from response text."""
    for line in text.splitlines():
        if line.strip().upper().startswith("SUMMARY:"):
            return line.split(":", 1)[1].strip()
    # Fallback: first non-empty line truncated
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("["):
            words = stripped.split()
            return " ".join(words[:7])
    return "Iris is looking..."


def clean_response_text(text: str) -> str:
    """Remove signal tags from text before sending to TTS."""
    import re
    text = re.sub(r'\[NAVIGATE:\s*.+?\]', '', text)
    text = re.sub(r'\[REMEMBER:\s*.+?\]', '', text)
    text = re.sub(r'SUMMARY:.*', '', text)
    return text.strip()
