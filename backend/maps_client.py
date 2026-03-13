"""
Iris — Google Maps Client

Fetches walking directions from the Maps Directions API.
"""

import logging
import os
from typing import List, Optional

import googlemaps
from dotenv import load_dotenv
from models import NavigationStep

load_dotenv()
logger = logging.getLogger(__name__)


class MapsClient:
    def __init__(self):
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not set — navigation will be disabled")
            self._client = None
        else:
            self._client = googlemaps.Client(key=api_key)
            logger.info("MapsClient initialized")

    def is_available(self) -> bool:
        return self._client is not None

    async def get_walking_directions(
        self,
        origin_lat: float,
        origin_lng: float,
        destination: str,
    ) -> Optional[List[NavigationStep]]:
        """
        Get walking directions from current GPS coords to a named destination.
        
        Returns a list of NavigationStep objects, or None if unavailable.
        """
        if not self._client:
            return None

        try:
            import asyncio
            origin = f"{origin_lat},{origin_lng}"
            directions_result = await asyncio.to_thread(
                self._client.directions,
                origin,
                destination,
                mode="walking",
            )

            if not directions_result:
                logger.warning(f"No directions found to: {destination}")
                return None

            steps = []
            legs = directions_result[0].get("legs", [])
            for leg in legs:
                for step in leg.get("steps", []):
                    # Strip HTML tags from instruction
                    instruction = step.get("html_instructions", "")
                    instruction = _strip_html(instruction)
                    distance = step.get("distance", {}).get("text", "")
                    
                    # Determine direction from maneuver
                    maneuver = step.get("maneuver", "straight")
                    direction = _maneuver_to_direction(maneuver)
                    
                    steps.append(NavigationStep(
                        direction=direction,
                        distance=distance,
                        instruction=instruction,
                    ))

            return steps if steps else None

        except Exception as e:
            logger.error(f"Maps API error: {e}")
            return None


def _strip_html(text: str) -> str:
    """Remove HTML tags from directions text."""
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


def _maneuver_to_direction(maneuver: str) -> str:
    """Convert Maps maneuver code to a simple direction string."""
    mapping = {
        "turn-left": "left",
        "turn-right": "right",
        "turn-sharp-left": "sharp-left",
        "turn-sharp-right": "sharp-right",
        "turn-slight-left": "slight-left",
        "turn-slight-right": "slight-right",
        "straight": "straight",
        "uturn-left": "u-turn",
        "uturn-right": "u-turn",
        "roundabout-left": "roundabout",
        "roundabout-right": "roundabout",
        "merge": "merge",
        "fork-left": "fork-left",
        "fork-right": "fork-right",
        "ramp-left": "ramp-left",
        "ramp-right": "ramp-right",
    }
    return mapping.get(maneuver, "straight")
