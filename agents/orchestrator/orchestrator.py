"""
Poll-Rover Agent Orchestrator
Coordinates agent execution, manages scheduling, and handles
inter-agent communication for the agentic pipeline.

Pipeline: Harvester → Quality → Generate Site → SRE Checks
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agents.common.config import load_config, get_paths
from agents.common.logger import get_logger

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """Central coordinator for all Poll-Rover agents.

    Manages the execution pipeline:
    1. Data Harvester → scrape new station data
    2. Data Quality → validate and score
    3. Site Generator → rebuild Zola static pages
    4. SRE Ops → health checks + remediation
    5. Citizen Assist → on-demand queries

    Usage:
        orchestrator = AgentOrchestrator()
        orchestrator.run_pipeline()            # Full pipeline
        orchestrator.run_pipeline(dry_run=True) # Preview mode
        orchestrator.query("Where do I vote?")  # Citizen query
    """

    def __init__(self, config: Optional[dict] = None):
        self._config = config or load_config()
        self._paths = get_paths(self._config)

    def run_pipeline(
        self,
        stages: Optional[List[str]] = None,
        dry_run: bool = False,
        states: Optional[List[str]] = None,
    ) -> dict:
        """Execute the full agentic pipeline.

        Args:
            stages: Specific stages to run. Default: all stages.
                Options: ["harvest", "quality", "generate", "sre"]
            dry_run: Preview mode — no writes to data files.
            states: State codes to process (default: pilot states).

        Returns:
            Pipeline execution report.
        """
        logger.info("[OR] Orchestrator starting pipeline...")
        start_time = time.time()

        if stages is None:
            stages = ["harvest", "quality", "generate", "sre"]

        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "stages": {},
            "overall_status": "success",
            "duration_seconds": 0,
        }

        # --- Stage 1: Data Harvester ---
        if "harvest" in stages:
            logger.info("-" * 50)
            logger.info("[STAGE 1] Data Harvesting")
            try:
                from agents.harvester.harvester_agent import DataHarvesterAgent
                harvester = DataHarvesterAgent(self._config)
                harvest_result = harvester.run(states=states, dry_run=dry_run)
                report["stages"]["harvest"] = {
                    "status": "success",
                    "stations_found": harvest_result.get("stations_found", 0),
                    "stations_added": harvest_result.get("stations_added", 0),
                    "errors": harvest_result.get("errors", []),
                }
            except Exception as e:
                logger.error(f"Harvester failed: {e}")
                report["stages"]["harvest"] = {"status": "error", "error": str(e)}
                report["overall_status"] = "partial"

        # --- Stage 2: Data Quality ---
        if "quality" in stages:
            logger.info("-" * 50)
            logger.info("[STAGE 2] Data Quality Audit")
            try:
                from agents.quality.quality_agent import DataQualityAgent
                quality = DataQualityAgent(self._config)
                quality_result = quality.run(fix_issues=not dry_run)
                report["stages"]["quality"] = {
                    "status": "success",
                    "stations_audited": quality_result.get("stations_audited", 0),
                    "passed": quality_result.get("passed", 0),
                    "warnings": quality_result.get("warnings", 0),
                    "errors": quality_result.get("errors", 0),
                }
            except Exception as e:
                logger.error(f"Quality agent failed: {e}")
                report["stages"]["quality"] = {"status": "error", "error": str(e)}
                report["overall_status"] = "partial"

        # --- Stage 3: Site Generation ---
        if "generate" in stages:
            logger.info("-" * 50)
            logger.info("[STAGE 3] Site Generation")
            try:
                result = self._run_site_generator(dry_run)
                report["stages"]["generate"] = result
            except Exception as e:
                logger.error(f"Site generation failed: {e}")
                report["stages"]["generate"] = {"status": "error", "error": str(e)}
                report["overall_status"] = "partial"

        # --- Stage 4: SRE Health Checks ---
        if "sre" in stages:
            logger.info("-" * 50)
            logger.info("[STAGE 4] SRE Health Checks")
            try:
                from agents.sre_ops.sre_agent import SREOpsAgent
                sre = SREOpsAgent(self._config)
                sre_result = sre.run()
                report["stages"]["sre"] = {
                    "status": sre_result.get("overall_status", "unknown"),
                    "incidents": len(sre_result.get("incidents", [])),
                    "remediations": len(sre_result.get("remediations", [])),
                }
            except Exception as e:
                logger.error(f"SRE agent failed: {e}")
                report["stages"]["sre"] = {"status": "error", "error": str(e)}

        duration = round(time.time() - start_time, 2)
        report["duration_seconds"] = duration

        # Log Global KPIs
        from agents.common.logger import log_kpi
        log_kpi(logger, "pipeline_duration", duration, unit="seconds")
        
        # Track Payload Efficiency (Verification of Lazy-Loading)
        summary_path = Path("static") / "data" / "summary.json"
        if summary_path.exists():
            payload_size_kb = round(summary_path.stat().st_size / 1024, 2)
            log_kpi(logger, "initial_map_payload", payload_size_kb, unit="KB")
            # 27MB baseline
            efficiency = round((1 - (payload_size_kb / 27648)) * 100, 2)
            log_kpi(logger, "payload_reduction_efficiency", efficiency, unit="percent")

        logger.info("-" * 50)
        logger.info(
            f"[OR] Pipeline complete in {duration}s | "
            f"Status: {report['overall_status']}"
        )

        return report

    def query(
        self,
        user_query: str,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        language: str = "en",
    ) -> dict:
        """Route a citizen query to the Citizen Assist Agent.

        Args:
            user_query: Natural language query from voter.
            user_lat: User latitude (optional).
            user_lng: User longitude (optional).
            language: Language code.

        Returns:
            Query response with text and map markers.
        """
        from agents.citizen_assist.citizen_agent import CitizenAssistAgent
        assistant = CitizenAssistAgent(self._config)
        return assistant.query(
            user_query=user_query,
            user_lat=user_lat,
            user_lng=user_lng,
            language=language,
        )

    def _run_site_generator(self, dry_run: bool) -> dict:
        """Run the Zola site generation script."""
        script_path = Path("scripts") / "generate_site.py"
        if not script_path.exists():
            return {
                "status": "skipped",
                "details": "generate_site.py not yet created",
            }

        import subprocess
        cmd = [sys.executable, str(script_path)]
        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Site generation timed out"}

    def status(self) -> dict:
        """Get current system status."""
        yaml_path = Path(self._paths["polling_stations_file"])
        station_count = 0

        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    station_count = len(data.get("polling_stations", []))

        return {
            "project": "Poll-Rover",
            "version": self._config.get("project", {}).get("version", "0.1.0"),
            "stations_loaded": station_count,
            "pilot_states": [
                s["state_code"]
                for s in self._config.get("pilot", {}).get("states", [])
            ],
            "agents": {
                name: self._config.get("agents", {}).get(name, {}).get("enabled", False)
                for name in ["harvester", "quality", "sre_ops", "citizen_assist"]
            },
        }
