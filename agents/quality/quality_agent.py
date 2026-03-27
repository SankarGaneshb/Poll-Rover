"""
Poll-Rover Data Quality Agent
Continuously validates data integrity, detects anomalies, and ensures
every polling station entry is trustworthy.

Runs as: post-harvest event trigger or standalone audit.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import ValidationError

from agents.common.config import get_agent_config, get_paths, load_config
from agents.common.logger import get_logger, log_incident
from data.models.polling_station import PollingStation

logger = get_logger("quality")


class DataQualityAgent:
    """Validates and scores polling station data quality.

    Checks performed:
    1. Schema validation (Pydantic model conformance)
    2. Geo-fencing (coordinates within state boundaries)
    3. Freshness (staleness detection)
    4. Accessibility completeness scoring
    5. Anomaly detection (voter/booth ratio outliers)
    6. Confidence scoring (weighted trust model)
    """

    # India state bounding boxes (approximate lat/lng)
    STATE_BOUNDS = {
        "TN": {"lat_min": 8.0, "lat_max": 13.6, "lng_min": 76.2, "lng_max": 80.4},
        "KL": {"lat_min": 8.2, "lat_max": 12.8, "lng_min": 74.8, "lng_max": 77.4},
        "PY": {"lat_min": 10.8, "lat_max": 12.1, "lng_min": 79.6, "lng_max": 80.0},
    }

    def __init__(self, config: Optional[dict] = None):
        self._config = config or load_config()
        self._agent_config = get_agent_config("quality", self._config)
        self._paths = get_paths(self._config)
        self._staleness_days = self._agent_config.get("staleness_threshold_days", 90)
        self._confidence_weights = self._config.get("confidence", {})

    def run(self, fix_issues: bool = False) -> dict:
        """Execute the full data quality audit.

        Args:
            fix_issues: If True, auto-fix correctable issues and rewrite YAML.

        Returns:
            Quality report with per-station results.
        """
        logger.info("[Quality Audit] Starting...")

        stations_data = self._load_stations()
        if not stations_data:
            logger.warning("No stations found to audit.")
            return {"stations_audited": 0, "issues": []}

        report = {
            "timestamp": date.today().isoformat(),
            "stations_audited": len(stations_data),
            "passed": 0,
            "warnings": 0,
            "errors": 0,
            "issues": [],
            "per_station": {},
        }

        fixed_stations = []

        for station_dict in stations_data:
            station_id = station_dict.get("station_id", "UNKNOWN")
            station_report = {
                "schema_valid": False,
                "geo_valid": False,
                "fresh": False,
                "accessibility_score": 0.0,
                "confidence_score": 0.0,
                "issues": [],
            }

            # --- Check 1: Schema Validation ---
            try:
                station = PollingStation.from_yaml_dict(station_dict)
                station_report["schema_valid"] = True
            except ValidationError as e:
                error_msg = f"Schema error in {station_id}: {e.error_count()} issues"
                station_report["issues"].append({
                    "type": "schema_error",
                    "severity": "error",
                    "details": str(e),
                })
                report["errors"] += 1
                logger.error(error_msg)
                log_incident(
                    logger,
                    incident_type="schema_validation_error",
                    message=error_msg,
                    station_id=station_id,
                )
                if fix_issues:
                    station_dict = self._attempt_schema_fix(station_dict)
                fixed_stations.append(station_dict)
                report["per_station"][station_id] = station_report
                continue

            # --- Check 2: Geo-fencing ---
            geo_valid, geo_issue = self._check_geofence(station)
            station_report["geo_valid"] = geo_valid
            if not geo_valid:
                station_report["issues"].append(geo_issue)
                report["warnings"] += 1

            # --- Check 3: Freshness ---
            fresh, fresh_issue = self._check_freshness(station)
            station_report["fresh"] = fresh
            if not fresh:
                station_report["issues"].append(fresh_issue)
                report["warnings"] += 1
                if fix_issues:
                    station_dict["metadata"]["needs_update"] = True

            # --- Check 4: Accessibility Completeness ---
            acc_score = self._score_accessibility(station)
            station_report["accessibility_score"] = acc_score

            # --- Check 5: Anomaly Detection ---
            anomalies = self._detect_anomalies(station)
            station_report["issues"].extend(anomalies)
            report["warnings"] += len(anomalies)

            # --- Check 6: Confidence Score ---
            confidence = self._calculate_confidence(station)
            station_report["confidence_score"] = confidence
            if fix_issues:
                station_dict["metadata"]["confidence_score"] = confidence
                station_dict["metadata"]["last_audit"] = date.today().isoformat()

            if not station_report["issues"]:
                report["passed"] += 1

            fixed_stations.append(station_dict)
            report["per_station"][station_id] = station_report

        # Write fixes if requested
        if fix_issues:
            self._write_stations(fixed_stations)
            logger.info("Applied auto-fixes and updated confidence scores.")

        # Write quality report
        self._write_report(report)

        logger.info(
            f"[Quality Audit] complete: {report['passed']}/{report['stations_audited']} passed, "
            f"{report['warnings']} warnings, {report['errors']} errors"
        )
        return report

    def _load_stations(self) -> List[dict]:
        """Load stations from YAML."""
        yaml_path = Path(self._paths["polling_stations_file"])
        if not yaml_path.exists():
            return []
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("polling_stations", []) if data else []

    def _check_geofence(self, station: PollingStation) -> Tuple[bool, Optional[dict]]:
        """Verify coordinates fall within declared state boundaries."""
        bounds = self.STATE_BOUNDS.get(station.state_code)
        if not bounds:
            return True, None  # No bounds defined, skip check

        lat_ok = bounds["lat_min"] <= station.latitude <= bounds["lat_max"]
        lng_ok = bounds["lng_min"] <= station.longitude <= bounds["lng_max"]

        if lat_ok and lng_ok:
            return True, None

        return False, {
            "type": "geo_fence_violation",
            "severity": "warning",
            "details": (
                f"Coordinates ({station.latitude}, {station.longitude}) "
                f"outside {station.state_code} bounds"
            ),
        }

    def _check_freshness(self, station: PollingStation) -> Tuple[bool, Optional[dict]]:
        """Check if station data is stale (not verified recently)."""
        verified_date = station.accessibility.last_verified
        audit_date = station.metadata.last_audit

        latest = verified_date or audit_date
        if latest is None:
            return False, {
                "type": "never_verified",
                "severity": "warning",
                "details": "Station has never been verified.",
            }

        days_old = (date.today() - latest).days
        if days_old > self._staleness_days:
            return False, {
                "type": "stale_data",
                "severity": "warning",
                "details": f"Last verified {days_old} days ago (threshold: {self._staleness_days}).",
            }

        return True, None

    def _score_accessibility(self, station: PollingStation) -> float:
        """Score accessibility feature completeness (0.0 to 1.0)."""
        acc = station.accessibility
        checks = [
            acc.wheelchair_ramp.value != "no",
            acc.accessible_parking.value != "no",
            acc.audio_booth,
            acc.braille_materials,
            len(acc.assistance_services) > 0,
            acc.accessibility_rating > 0,
            acc.last_verified is not None,
            acc.verified_by.value != "unverified",
        ]
        return round(sum(checks) / len(checks), 2)

    def _detect_anomalies(self, station: PollingStation) -> List[dict]:
        """Detect statistical anomalies in station data."""
        anomalies = []

        # Anomaly: Too many voters per booth
        ed = station.election_details
        if ed.estimated_voters and ed.number_of_booths:
            voters_per_booth = ed.estimated_voters / ed.number_of_booths
            if voters_per_booth > 1500:
                anomalies.append({
                    "type": "high_voter_density",
                    "severity": "warning",
                    "details": (
                        f"{voters_per_booth:.0f} voters/booth "
                        f"(recommended max: 1500)"
                    ),
                })

        # Anomaly: Perfect accessibility rating but missing features
        if (
            station.accessibility.accessibility_rating == 5.0
            and not station.accessibility.audio_booth
        ):
            anomalies.append({
                "type": "suspicious_rating",
                "severity": "warning",
                "details": "5.0 rating but audio booth not available.",
            })

        return anomalies

    def _calculate_confidence(self, station: PollingStation) -> float:
        """Calculate weighted confidence score.

        Formula:
        confidence = (
            0.4 × source_trust +
            0.3 × verification_recency +
            0.2 × field_completeness +
            0.1 × cross_reference
        )
        """
        weights = self._confidence_weights

        # Source trust
        source_trust_map = {
            "ECI_official": 1.0,
            "state_CEO": 0.8,
            "NGO_report": 0.6,
            "OpenStreetMap": 0.7,
            "community": 0.4,
            "mixed": 0.7,
        }
        source_trust = source_trust_map.get(
            station.metadata.data_source.value, 0.5
        )

        # Verification recency (1.0 = today, decays over staleness_threshold)
        latest_date = station.accessibility.last_verified or station.metadata.last_audit
        if latest_date:
            days_old = max(0, (date.today() - latest_date).days)
            recency = max(0.0, 1.0 - (days_old / self._staleness_days))
        else:
            recency = 0.0

        # Field completeness
        completeness = self._score_accessibility(station)

        # Cross-reference (placeholder — would check against other sources)
        cross_ref = 0.5

        confidence = (
            weights.get("source_trust_weight", 0.4) * source_trust
            + weights.get("verification_recency_weight", 0.3) * recency
            + weights.get("field_completeness_weight", 0.2) * completeness
            + weights.get("cross_reference_weight", 0.1) * cross_ref
        )

        return round(min(1.0, max(0.0, confidence)), 2)

    def _attempt_schema_fix(self, station_dict: dict) -> dict:
        """Attempt to fix common schema errors."""
        # Ensure required nested objects exist
        station_dict.setdefault("accessibility", {})
        station_dict.setdefault("election_details", {})
        station_dict.setdefault("contact", {})
        station_dict.setdefault("community_data", {})
        station_dict.setdefault("metadata", {})
        return station_dict

    def _write_stations(self, stations: List[dict]) -> None:
        """Write updated stations back to YAML."""
        yaml_path = Path(self._paths["polling_stations_file"])
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"polling_stations": stations},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def _write_report(self, report: dict) -> None:
        """Write quality report to reports directory."""
        reports_dir = Path(self._paths.get("reports_dir", "reports"))
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_path = reports_dir / f"quality_report_{report['timestamp']}.yml"
        # Write a simplified version (exclude per_station to keep it readable)
        summary = {k: v for k, v in report.items() if k != "per_station"}
        with open(report_path, "w", encoding="utf-8") as f:
            yaml.dump(summary, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Report saved to {report_path}")
