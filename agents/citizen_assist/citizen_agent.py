"""
Poll-Rover Citizen Assist Agent
Helps voters find their polling station via natural language queries.
Multi-lingual, accessibility-aware, with map integration for the web widget.
"""

import math
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from agents.common.config import get_agent_config, get_paths, load_config
from agents.common.llm_client import LLMClient
from agents.common.logger import get_logger

logger = get_logger("citizen_assist")


class CitizenAssistAgent:
    """AI-powered citizen query assistant for polling station discovery.

    Capabilities:
    - Natural language station lookup (multi-lingual: en, hi, ta, te, kn)
    - Accessibility-aware recommendations
    - Proximity-based search ("stations near me")
    - Structured responses for web chat widget + map highlighting
    """

    SYSTEM_PROMPT = """You are a helpful civic assistant for Indian voters.
Your job is to help citizens find their assigned polling station and understand
accessibility features. You are part of the "Know Your Polling Station" initiative.

Rules:
- Be concise and clear
- Always mention accessibility features when relevant
- Provide station name, address, and key details
- If you don't know something, say so — never fabricate station data
- Respond in the same language the user writes in
- For location queries, recommend the nearest accessible station
- Include the station_id in your response for map linking

Format your response as:
📍 Station: [Name]
📫 Address: [Address]
♿ Accessibility: [Key features]
📅 Voting: [Date and time]
🗺️ Map: station_id=[ID]
"""

    def __init__(self, config: Optional[dict] = None):
        self._config = config or load_config()
        self._agent_config = get_agent_config("citizen_assist", self._config)
        self._paths = get_paths(self._config)
        self._llm = LLMClient()
        self._stations_cache: Optional[List[dict]] = None

    def query(
        self,
        user_query: str,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        language: str = "en",
        accessibility_filter: bool = False,
    ) -> dict:
        """Process a citizen query and return station recommendations.

        Args:
            user_query: Natural language query from the voter.
            user_lat: User's latitude (if location available).
            user_lng: User's longitude (if location available).
            language: Language code (en/hi/ta/te/kn).
            accessibility_filter: If True, prioritize accessible stations.

        Returns:
            Response dict with text, matched stations, and map data.
        """
        logger.info(f"🧑‍🤝‍🧑 Query [{language}]: {user_query[:80]}...")

        stations = self._load_stations()
        if not stations:
            return {
                "text": "No polling station data available yet. Please check back later.",
                "stations": [],
                "map_markers": [],
            }

        # Step 1: Parse query intent
        start_time = time.time()
        intent = self._parse_intent(user_query, language)

        # Step 2: Find matching stations
        matches = self._find_stations(
            intent=intent,
            user_lat=user_lat,
            user_lng=user_lng,
            accessibility_filter=accessibility_filter,
            limit=5,
        )

        # Step 3: Generate human response via LLM
        response_text = self._generate_response(
            user_query=user_query,
            matches=matches,
            language=language,
        )

        # Step 4: Prepare map markers for web widget
        map_markers = self._to_map_markers(matches)

        # Log KPIs
        duration = round((time.time() - start_time) * 1000, 2)
        from agents.common.logger import log_kpi
        log_kpi(logger, "response_time", duration, unit="ms", language=language)
        log_kpi(logger, "stations_found_per_query", len(matches), unit="count")

        result = {
            "text": response_text,
            "stations": matches,
            "map_markers": map_markers,
            "intent": intent,
            "language": language,
        }

        logger.info(f"  Found {len(matches)} matching stations")
        return result

    def _parse_intent(self, query: str, language: str) -> dict:
        """Parse the user's query into structured intent."""
        query_lower = query.lower().strip()

        intent = {
            "type": "general",  # general / location / accessibility / info
            "keywords": [],
            "constituency": None,
            "ward": None,
            "pin_code": None,
            "accessibility_focus": False,
        }

        # Detect accessibility intent
        accessibility_terms = [
            "wheelchair", "ramp", "accessible", "disability", "disabled",
            "braille", "audio", "blind", "deaf", "hearing",
            # Hindi
            "विकलांग", "व्हीलचेयर",
            # Tamil
            "மாற்றுத்திறனாளி", "சக்கரநாற்காலி",
        ]
        if any(term in query_lower for term in accessibility_terms):
            intent["type"] = "accessibility"
            intent["accessibility_focus"] = True

        # Detect location intent
        location_terms = ["near", "nearby", "closest", "nearest", "அருகில்", "पास"]
        if any(term in query_lower for term in location_terms):
            intent["type"] = "location"

        # Detect PIN code
        import re
        pin_match = re.search(r"\b(\d{6})\b", query)
        if pin_match:
            intent["pin_code"] = pin_match.group(1)

        # Extract keywords (simple tokenization)
        stop_words = {"the", "a", "an", "in", "at", "my", "where", "do",
                       "i", "vote", "polling", "station", "is", "find", "me"}
        words = query_lower.split()
        intent["keywords"] = [w for w in words if w not in stop_words and len(w) > 2]

        return intent

    def _find_stations(
        self,
        intent: dict,
        user_lat: Optional[float],
        user_lng: Optional[float],
        accessibility_filter: bool,
        limit: int = 5,
    ) -> List[dict]:
        """Find stations matching the query intent."""
        stations = self._load_stations()
        scored_stations = []

        for station in stations:
            score = 0.0

            # Keyword matching
            station_text = (
                f"{station.get('name', '')} {station.get('address', '')} "
                f"{station.get('assembly_constituency', '')} "
                f"{station.get('landmark', '')}"
            ).lower()

            for keyword in intent.get("keywords", []):
                if keyword in station_text:
                    score += 10.0

            # PIN code matching
            if intent.get("pin_code") and station.get("pin_code") == intent["pin_code"]:
                score += 50.0

            # Constituency matching
            if intent.get("constituency"):
                if intent["constituency"].lower() in station.get(
                    "assembly_constituency", ""
                ).lower():
                    score += 30.0

            # Proximity scoring (if user location available)
            if user_lat and user_lng:
                station_lat = station.get("latitude", 0)
                station_lng = station.get("longitude", 0)
                if station_lat and station_lng:
                    distance_km = self._haversine(
                        user_lat, user_lng, station_lat, station_lng
                    )
                    # Closer stations get higher scores (max 40 points within 5km)
                    if distance_km < 50:
                        score += max(0, 40 - (distance_km * 8))
                    station["_distance_km"] = round(distance_km, 1)

            # Accessibility bonus
            if accessibility_filter or intent.get("accessibility_focus"):
                acc = station.get("accessibility", {})
                if acc.get("wheelchair_ramp") == "yes":
                    score += 15.0
                if acc.get("audio_booth"):
                    score += 10.0
                if acc.get("braille_materials"):
                    score += 10.0
                acc_rating = acc.get("accessibility_rating", 0)
                score += acc_rating * 3  # Up to 15 points

            if score > 0:
                station["_relevance_score"] = round(score, 1)
                scored_stations.append(station)

        # Sort by score descending
        scored_stations.sort(key=lambda s: s.get("_relevance_score", 0), reverse=True)
        return scored_stations[:limit]

    def _generate_response(
        self,
        user_query: str,
        matches: List[dict],
        language: str,
    ) -> str:
        """Generate a human-readable response using LLM."""
        if not matches:
            return (
                "I couldn't find matching polling stations for your query. "
                "Try searching by PIN code, constituency name, or area name."
            )

        # Build context for LLM
        stations_context = ""
        for i, s in enumerate(matches[:3], 1):
            acc = s.get("accessibility", {})
            distance = s.get("_distance_km", "N/A")
            stations_context += f"""
Station {i}:
- ID: {s.get('station_id')}
- Name: {s.get('name')}
- Address: {s.get('address')}
- Constituency: {s.get('assembly_constituency')}
- Wheelchair Ramp: {acc.get('wheelchair_ramp', 'unknown')}
- Audio Booth: {acc.get('audio_booth', False)}
- Braille: {acc.get('braille_materials', False)}
- Accessibility Rating: {acc.get('accessibility_rating', 'N/A')}/5
- Distance: {distance} km
- Voting Date: {s.get('election_details', {}).get('voting_date', 'TBD')}
- Voting Time: {s.get('election_details', {}).get('start_time', '07:00')} - {s.get('election_details', {}).get('end_time', '18:00')}
"""

        lang_instruction = ""
        if language != "en":
            lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada"}
            lang_instruction = f"\nIMPORTANT: Respond in {lang_map.get(language, 'English')}."

        try:
            response = self._llm.generate(
                prompt=(
                    f"User query: {user_query}\n\n"
                    f"Matching polling stations:\n{stations_context}\n"
                    f"Provide a helpful response to the voter.{lang_instruction}"
                ),
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.4,
            )
            return response
        except Exception as e:
            logger.warning(f"LLM response failed: {e}. Using template response.")
            return self._template_response(matches[:1])

    def _template_response(self, matches: List[dict]) -> str:
        """Fallback template response when LLM is unavailable."""
        if not matches:
            return "No matching stations found."

        s = matches[0]
        acc = s.get("accessibility", {})
        return (
            f"📍 Station: {s.get('name')}\n"
            f"📫 Address: {s.get('address')}\n"
            f"♿ Wheelchair Ramp: {acc.get('wheelchair_ramp', 'N/A')}\n"
            f"📅 Voting Date: {s.get('election_details', {}).get('voting_date', 'TBD')}\n"
            f"🗺️ Map: station_id={s.get('station_id')}"
        )

    def _to_map_markers(self, stations: List[dict]) -> List[dict]:
        """Convert stations to map marker format for Leaflet.js."""
        markers = []
        for s in stations:
            acc = s.get("accessibility", {})
            rating = acc.get("accessibility_rating", 0)

            # Color coding by accessibility
            if rating >= 4.0:
                color = "green"
            elif rating >= 2.5:
                color = "orange"
            else:
                color = "red"

            markers.append({
                "station_id": s.get("station_id"),
                "lat": s.get("latitude"),
                "lng": s.get("longitude"),
                "name": s.get("name"),
                "address": s.get("address"),
                "color": color,
                "accessibility_rating": rating,
                "wheelchair": acc.get("wheelchair_ramp", "no"),
                "audio_booth": acc.get("audio_booth", False),
                "braille": acc.get("braille_materials", False),
                "popup_html": self._build_popup_html(s),
            })

        return markers

    def _build_popup_html(self, station: dict) -> str:
        """Build HTML popup content for a map marker."""
        acc = station.get("accessibility", {})
        icons = []
        if acc.get("wheelchair_ramp") in ("yes", "partial"):
            icons.append("♿")
        if acc.get("audio_booth"):
            icons.append("🔊")
        if acc.get("braille_materials"):
            icons.append("⠿")

        return (
            f"<b>{station.get('name', '')}</b><br>"
            f"{station.get('address', '')}<br>"
            f"{''.join(icons)}<br>"
            f"Rating: {'⭐' * int(acc.get('accessibility_rating', 0))}"
        )

    def _load_stations(self) -> List[dict]:
        """Load stations from YAML with caching."""
        if self._stations_cache is not None:
            return self._stations_cache

        yaml_path = Path(self._paths["polling_stations_file"])
        if not yaml_path.exists():
            return []

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._stations_cache = data.get("polling_stations", []) if data else []
        return self._stations_cache

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate great-circle distance between two points in km."""
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
