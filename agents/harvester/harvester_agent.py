"""
Poll-Rover Data Harvester Agent
Autonomously discovers, extracts, and normalizes polling station data
from authoritative Indian election sources.

Pipeline: ECI PDFs → State CEO Websites → OpenStreetMap → Normalized YAML
"""

import re
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from agents.common.config import get_agent_config, get_paths, load_config
from agents.common.llm_client import LLMClient
from agents.common.logger import get_logger, log_incident, log_kpi

# State-specific extractors
try:
    from agents.harvester.extractors.tn_election_pdf import extract_from_tn_pdf
    from agents.harvester.extractors.kl_ceo_scraper import scrape_kl_web
    from agents.harvester.extractors.pdy_pdf_extractor import extract_from_py_pdf
except ImportError:
    # Allow running without specialized extractors for simple tests
    extract_from_tn_pdf = None
    scrape_kl_web = None
    extract_from_py_pdf = None

logger = get_logger("harvester")


class DataHarvesterAgent:
    """Harvests polling station data from multiple authoritative sources.

    Trust hierarchy:
        1. ECI Official PDFs (trust=1.0)
        2. State CEO Websites (trust=0.8)
        3. OpenStreetMap/geocoding (trust=0.7)
        4. Community contributions (trust=0.4)
    """

    def __init__(self, config: Optional[dict] = None):
        self._config = config or load_config()
        self._agent_config = get_agent_config("harvester", self._config)
        self._paths = get_paths(self._config)
        self._llm = LLMClient()
        self._batch_size = self._agent_config.get("batch_size", 50)

    def run(self, states: Optional[List[str]] = None, dry_run: bool = False) -> dict:
        """Execute the full harvesting pipeline.

        Args:
            states: State codes to harvest (default: all pilot states).
            dry_run: If True, validate but don't write to YAML.

        Returns:
            Harvest report with counts and issues.
        """
        logger.info("🕷️  Data Harvester Agent starting...")
        start_time = time.time()

        if states is None:
            states = [s["state_code"] for s in self._config["pilot"]["states"]]

        report = {
            "states_processed": [],
            "stations_found": 0,
            "stations_added": 0,
            "stations_updated": 0,
            "errors": [],
            "timestamp": date.today().isoformat(),
        }

        existing_stations = self._load_existing_stations()
        new_stations = []

        for state_code in states:
            logger.info(f"Processing state: {state_code}")
            try:
                # Step 1: Extract raw data from sources
                state_start = time.time()
                raw_entries = self._extract_from_sources(state_code)
                report["stations_found"] += len(raw_entries)

                # Step 2: Normalize to schema
                normalized = self._normalize_entries(raw_entries, state_code)

                # Step 3: Geocode missing coordinates
                geocoded = self._geocode_entries(normalized)

                # Step 4: Deduplicate against existing data
                unique = self._deduplicate(geocoded, existing_stations)

                new_stations.extend(unique)
                report["stations_added"] += len(unique)
                report["states_processed"].append(state_code)

                # Performance tracking per station
                state_duration = time.time() - state_start
                if len(raw_entries) > 0:
                    time_per_station = round(state_duration / len(raw_entries), 3)
                    log_kpi(logger, "time_per_station", time_per_station, unit="seconds", state=state_code)

                logger.info(
                    f"  {state_code}: {len(raw_entries)} found → "
                    f"{len(unique)} new stations after dedup"
                )

            except Exception as e:
                error_msg = f"Failed to harvest {state_code}: {e}"
                logger.error(error_msg)
                report["errors"].append(error_msg)
                log_incident(
                    logger,
                    incident_type="harvest_failure",
                    message=error_msg,
                    action_taken="skipped_state",
                )

        # Step 5: Write to YAML (if not dry run)
        if not dry_run and new_stations:
            self._write_stations(new_stations, existing_stations)
            logger.info(f"✅ Wrote {len(new_stations)} new stations to YAML")
        elif dry_run:
            logger.info(f"🔍 Dry run: {len(new_stations)} stations would be added")

        logger.info(f"🕷️  Harvest complete: {report}")
        
        # Log KPIs
        execution_time = round(time.time() - start_time, 2)
        log_kpi(logger, "stations_found", report["stations_found"], unit="count")
        log_kpi(logger, "stations_added", report["stations_added"], unit="count")
        log_kpi(logger, "execution_time", execution_time, unit="seconds")
        
        if report["stations_found"] > 0:
            success_rate = round((report["stations_added"] / report["stations_found"]) * 100, 2)
            log_kpi(logger, "success_rate", success_rate, unit="percent")

        return report

    def _load_existing_stations(self) -> List[dict]:
        """Load existing stations from YAML file."""
        yaml_path = Path(self._paths["polling_stations_file"])
        if not yaml_path.exists():
            return []

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return data.get("polling_stations", []) if data else []

    def _extract_from_sources(self, state_code: str) -> List[dict]:
        """Extract raw polling station data from available sources.

        This method orchestrates extraction from multiple sources
        and merges results.
        """
        all_entries = []

        # State-specific logic
        if state_code == "TN" and extract_from_tn_pdf:
            logger.info("  Using specialized TN PDF extractor")
            pdf_dir = Path(self._paths["data_dir"]) / "source_pdfs" / "TN"
            if pdf_dir.exists():
                for pdf_file in pdf_dir.glob("*.pdf"):
                    logger.info(f"    Extracting from {pdf_file.name}...")
                    all_entries.extend(extract_from_tn_pdf(str(pdf_file)))
        
        elif state_code == "KL" and scrape_kl_web:
            logger.info("  Using specialized KL Web scraper")
            all_entries.extend(scrape_kl_web("TRIVANDRUM_PILOT_01"))

        elif state_code == "PY" and extract_from_py_pdf:
            logger.info("  Using specialized PY PDF extractor")
            all_entries.extend(extract_from_py_pdf("puducherry_roll.pdf"))

        # Fallback 1: Multi-state generic PDF extraction (LLM based)
        # Skip this expensive LLM call if specialized extractors already found data
        if not all_entries:
            pdf_entries = self._extract_from_pdfs(state_code)
            all_entries.extend(pdf_entries)

        # Fallback 2: Multi-state generic web scraping
        web_entries = self._extract_from_web(state_code)
        all_entries.extend(web_entries)

        return all_entries

    def _extract_from_pdfs(self, state_code: str) -> List[dict]:
        """Extract polling station data from ECI/CEO PDFs using LLM.

        Uses PyMuPDF for text extraction and LLM for structuring.
        """
        pdf_dir = Path(self._paths["data_dir"]) / "source_pdfs" / state_code
        if not pdf_dir.exists():
            logger.debug(f"No PDF directory found for {state_code}")
            return []

        entries = []
        for pdf_file in pdf_dir.glob("*.pdf"):
            try:
                text = self._extract_pdf_text(pdf_file)
                if text:
                    structured = self._llm_structure_pdf(text, state_code)
                    entries.extend(structured)
                    logger.info(f"  Extracted {len(structured)} entries from {pdf_file.name}")
            except Exception as e:
                logger.warning(f"  Failed to process {pdf_file.name}: {e}")

        return entries

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text content from a PDF file."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.warning(f"PDF extraction failed for {pdf_path}: {e}")
            return ""

    def _llm_structure_pdf(self, text: str, state_code: str) -> List[dict]:
        """Use LLM to structure raw PDF text into station entries."""
        system_prompt = """You are a data extraction agent for Indian polling stations.
Extract polling station information from the given text and return it as a YAML list.

For each station, extract:
- name: Station name / building name
- address: Full address
- assembly_constituency: AC name
- ward: Ward number (if available)
- number_of_booths: Number of booths (if available)
- estimated_voters: Number of voters (if available)

Return ONLY valid YAML, no explanations. Use this format:
- name: "Station Name"
  address: "Full Address"
  assembly_constituency: "AC Name"
  ward: "123"
"""
        # Truncate text to fit context window
        max_chars = 6000
        if len(text) > max_chars:
            text = text[:max_chars]

        try:
            response = self._llm.generate(
                prompt=f"Extract polling station data from this {state_code} document:\n\n{text}",
                system_prompt=system_prompt,
                temperature=0.1,
            )
            # Clean markdown formatting if the LLM wrapped the response
            clean_yaml = response.strip()
            match = re.search(r"```(?:yaml)?(.*?)```", clean_yaml, re.DOTALL | re.IGNORECASE)
            if match:
                clean_yaml = match.group(1).strip()

            # Parse LLM YAML response
            entries = yaml.safe_load(clean_yaml)
            if isinstance(entries, list):
                return entries
        except Exception as e:
            logger.warning(f"LLM structuring failed: {e}")

        return []

    def _extract_from_web(self, state_code: str) -> List[dict]:
        """Scrape polling station data from state CEO websites.

        Note: Actual scraping logic is state-specific.
        This is the extensible framework.
        """
        sources = self._config.get("data_sources", {}).get("state_ceo", {})
        url = sources.get("urls", {}).get(state_code)

        if not url:
            logger.debug(f"No CEO website configured for {state_code}")
            return []

        # Placeholder for state-specific scrapers
        # Each state will have its own scraper module
        logger.debug(f"Web scraping for {state_code} from {url} (TODO: implement scraper)")
        return []

    def _normalize_entries(self, raw_entries: List[dict], state_code: str) -> List[dict]:
        """Normalize raw extracted data to match the PollingStation schema."""
        state_info = self._get_state_info(state_code)
        normalized = []

        for i, entry in enumerate(raw_entries):
            try:
                station_id = self._generate_station_id(
                    state_code,
                    state_info.get("district_code", state_code[:3]),
                    len(normalized) + 1,
                )
                normalized_entry = {
                    "station_id": station_id,
                    "state": state_info.get("name", state_code),
                    "state_code": state_code,
                    "district": state_info.get("pilot_city", "Unknown"),
                    "district_code": state_info.get("district_code", state_code[:3]),
                    "name": entry.get("name", "Unknown Station"),
                    "address": entry.get("address", "Address not available"),
                    "assembly_constituency": entry.get("assembly_constituency", "Unknown"),
                    "parliamentary_constituency": entry.get("parliamentary_constituency", "Unknown"),
                    "latitude": entry.get("latitude", 0.0),
                    "longitude": entry.get("longitude", 0.0),
                    "metadata": {
                        "data_source": "ECI_official"
                        if entry.get("source") == "pdf"
                        else "state_CEO",
                        "confidence_score": 0.6,
                        "needs_update": True,
                    },
                }

                # Carry over any additional fields
                for key in ["ward", "landmark", "pin_code", "number_of_booths", "estimated_voters", "accessibility"]:
                    if key in entry:
                        if key in ("number_of_booths", "estimated_voters"):
                            normalized_entry.setdefault("election_details", {})[key] = entry[key]
                        else:
                            normalized_entry[key] = entry[key]

                # Update confidence if higher specificity is provided by extractor
                if "metadata" in entry and "confidence" in entry["metadata"]:
                    normalized_entry["metadata"]["confidence_score"] = entry["metadata"]["confidence"]

                normalized.append(normalized_entry)

            except Exception as e:
                logger.warning(f"Failed to normalize entry {i}: {e}")

        return normalized

    def _geocode_entries(self, entries: List[dict]) -> List[dict]:
        """Add coordinates to entries missing lat/lng using Nominatim."""
        try:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter
        except ImportError:
            logger.warning("geopy not installed, skipping geocoding")
            return entries

        geolocator = Nominatim(user_agent="poll-rover-civic-tech")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

        geocoded_count = 0
        for entry in entries:
            if entry.get("latitude", 0.0) == 0.0 or entry.get("longitude", 0.0) == 0.0:
                address = entry.get("address", "")
                if address:
                    try:
                        location = geocode(address + ", India")
                        if location:
                            entry["latitude"] = round(location.latitude, 4)
                            entry["longitude"] = round(location.longitude, 4)
                            geocoded_count += 1
                            logger.debug(
                                f"  Geocoded: {entry['name']} → "
                                f"({entry['latitude']}, {entry['longitude']})"
                            )
                    except Exception as e:
                        logger.debug(f"  Geocoding failed for {entry['name']}: {e}")

        if geocoded_count:
            logger.info(f"  Geocoded {geocoded_count} stations")

        return entries

    def _deduplicate(
        self, new_entries: List[dict], existing: List[dict]
    ) -> List[dict]:
        """Remove duplicates using fuzzy matching on name + address."""
        if not existing:
            return new_entries

        existing_ids = {s["station_id"] for s in existing}
        existing_names = {f"{s.get('district', '')} {s['name']}".lower().strip() for s in existing}

        unique = []
        for entry in new_entries:
            if entry["station_id"] in existing_ids:
                continue

            # Fuzzy name matching with district context
            name_lower = f"{entry.get('district', '')} {entry['name']}".lower().strip()
            is_duplicate = False

            try:
                from thefuzz import fuzz
                for existing_name in existing_names:
                    if fuzz.ratio(name_lower, existing_name) > 85:
                        is_duplicate = True
                        logger.debug(f"  Duplicate detected: {entry['name']}")
                        break
            except ImportError:
                if name_lower in existing_names:
                    is_duplicate = True

            if not is_duplicate:
                unique.append(entry)

        return unique

    def _write_stations(
        self, new_stations: List[dict], existing: List[dict]
    ) -> None:
        """Append new stations to the YAML file."""
        all_stations = existing + new_stations
        yaml_path = Path(self._paths["polling_stations_file"])
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"polling_stations": all_stations},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def _generate_station_id(
        self, state_code: str, district_code: str, seq: int
    ) -> str:
        """Generate a unique station ID in format: ST_DST_PSxxxxx."""
        return f"{state_code}_{district_code}_PS{seq:05d}"

    def _get_state_info(self, state_code: str) -> dict:
        """Get state configuration from pilot list."""
        for state in self._config.get("pilot", {}).get("states", []):
            if state["state_code"] == state_code:
                # Derive district code from city name
                city = state.get("pilot_city", "")
                district_code = city[:3].upper() if city else state_code[:3]
                return {**state, "district_code": district_code}
        return {"name": state_code, "pilot_city": "Unknown", "district_code": state_code[:3]}
