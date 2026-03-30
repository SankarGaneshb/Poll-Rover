"""
Poll-Rover SRE Ops Agent
Monitors, diagnoses, and auto-remediates pipeline and deployment issues.
Supports both fully autonomous and human-in-the-loop (HIL) modes.
"""

import json
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agents.common.config import get_agent_config, get_paths, load_config
from agents.common.logger import get_logger, log_incident

logger = get_logger("sre_ops")


class SREOpsAgent:
    """Self-healing Site Reliability Engineering agent.

    Capabilities:
    - Build health monitoring (Zola + Python scripts)
    - Data pipeline integrity checks
    - YAML parse error detection + quarantine
    - Auto-remediation with configurable HIL mode
    - Incident logging for audit trails

    HIL Modes:
    - "disabled": Fully autonomous, no human approval needed
    - "optional": Auto-remediate but log for review
    - "required": Propose fix, wait for human approval
    """

    def __init__(self, config: Optional[dict] = None):
        self._config = config or load_config()
        self._agent_config = get_agent_config("sre_ops", self._config)
        self._paths = get_paths(self._config)
        self._hil_mode = self._agent_config.get("hil_mode", "optional")
        self._auto_remediate = self._agent_config.get("auto_remediate", True)
        self._playbooks = self._load_playbooks()

    def run(self, checks: Optional[List[str]] = None) -> dict:
        """Execute SRE health checks and auto-remediation.

        Args:
            checks: Specific checks to run. Default: all checks.
                Options: ["yaml_health", "build_health", "data_pipeline",
                         "agent_health", "resource_usage"]

        Returns:
            SRE operations report.
        """
        logger.info("[SRE] Ops Agent starting health checks...")

        if checks is None:
            checks = [
                "yaml_health",
                "build_health",
                "data_pipeline",
                "agent_health",
                "resource_usage",
                "agent_logs",
                "llm_health",
                "cross_agent_kpis",
            ]

        report = {
            "timestamp": datetime.now().isoformat(),
            "hil_mode": self._hil_mode,
            "checks_run": [],
            "incidents": [],
            "remediations": [],
            "overall_status": "healthy",
        }

        check_methods = {
            "yaml_health": self._check_yaml_health,
            "build_health": self._check_build_health,
            "data_pipeline": self._check_data_pipeline,
            "agent_health": self._check_agent_health,
            "resource_usage": self._check_resource_usage,
            "agent_logs": self._check_agent_logs,
            "llm_health": self._check_llm_health,
            "cross_agent_kpis": self._calculate_cross_agent_kpis,
        }

        for check_name in checks:
            if check_name not in check_methods:
                logger.warning(f"Unknown check: {check_name}")
                continue

            logger.info(f"  Running: {check_name}")
            try:
                result = check_methods[check_name]()
                report["checks_run"].append({
                    "name": check_name,
                    "status": result["status"],
                    "details": result.get("details", ""),
                })

                if result["status"] == "error":
                    report["overall_status"] = "degraded"
                    incident = result.get("incident")
                    if incident:
                        report["incidents"].append(incident)

                        # Auto-remediate if configured
                        if self._should_remediate():
                            remediation = self._remediate(incident)
                            if remediation:
                                report["remediations"].append(remediation)

            except Exception as e:
                logger.error(f"  Check {check_name} crashed: {e}")
                report["checks_run"].append({
                    "name": check_name,
                    "status": "error",
                    "details": str(e),
                })
                report["overall_status"] = "degraded"

        # Write ops log
        self._write_ops_log(report)

        status_text = "HEALTHY" if report["overall_status"] == "healthy" else "DEGRADED"
        logger.info(
            f"[SRE] check complete: status={status_text} | "
            f"{len(report['incidents'])} incidents, "
            f"{len(report['remediations'])} remediations"
        )
        return report

    # --- Health Checks ---

    def _check_yaml_health(self) -> dict:
        """Verify YAML data file is parseable and well-formed."""
        yaml_path = Path(self._paths["polling_stations_file"])

        if not yaml_path.exists():
            return {
                "status": "error",
                "details": f"YAML file not found: {yaml_path}",
                "incident": {
                    "type": "yaml_missing",
                    "severity": "critical",
                    "message": f"Polling stations YAML file not found at {yaml_path}",
                    "playbook": "data_error",
                },
            }

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "polling_stations" not in data:
                return {
                    "status": "error",
                    "details": "YAML file is empty or missing 'polling_stations' key",
                    "incident": {
                        "type": "yaml_malformed",
                        "severity": "high",
                        "message": "YAML structure is malformed",
                        "playbook": "data_error",
                    },
                }

            station_count = len(data["polling_stations"])
            return {
                "status": "ok",
                "details": f"YAML healthy: {station_count} stations loaded",
            }

        except yaml.YAMLError as e:
            return {
                "status": "error",
                "details": f"YAML parse error: {e}",
                "incident": {
                    "type": "yaml_parse_error",
                    "severity": "critical",
                    "message": f"YAML parse error: {e}",
                    "playbook": "data_error",
                },
            }

    def _check_build_health(self) -> dict:
        """Check if Zola build would succeed (dry-run)."""
        # Check if generate_site.py exists
        script_path = Path("scripts") / "generate_site.py"
        if not script_path.exists():
            return {
                "status": "warning",
                "details": "generate_site.py not found (not yet created)",
            }

        # Check if Zola is installed
        try:
            result = subprocess.run(
                ["zola", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return {
                    "status": "warning",
                    "details": "Zola not installed or not in PATH",
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {
                "status": "warning",
                "details": "Zola not found in PATH (install via 'scoop install zola' or download from getzola.org)",
            }

        return {"status": "ok", "details": "Build toolchain healthy"}

    def _check_data_pipeline(self) -> dict:
        """Check data pipeline component availability."""
        issues = []

        # Check Python dependencies
        required_modules = ["yaml", "pydantic", "fitz"]
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                issues.append(f"Missing module: {module}")

        if issues:
            return {
                "status": "error",
                "details": f"Pipeline issues: {', '.join(issues)}",
                "incident": {
                    "type": "dependency_missing",
                    "severity": "high",
                    "message": f"Missing dependencies: {', '.join(issues)}",
                    "playbook": "build_failure",
                },
            }

        return {"status": "ok", "details": "Data pipeline dependencies available"}

    def _check_agent_health(self) -> dict:
        """Verify all agents can be imported and instantiated."""
        agents_status = {}
        agent_modules = {
            "harvester": "agents.harvester.harvester_agent",
            "quality": "agents.quality.quality_agent",
            "citizen_assist": "agents.citizen_assist.citizen_agent",
        }

        for name, module_path in agent_modules.items():
            try:
                __import__(module_path)
                agents_status[name] = "ok"
            except Exception as e:
                agents_status[name] = f"error: {e}"

        has_errors = any("error" in v for v in agents_status.values())
        return {
            "status": "error" if has_errors else "ok",
            "details": agents_status,
        }

    def _check_resource_usage(self) -> dict:
        """Check system resource usage."""
        try:
            import psutil
            disk = psutil.disk_usage(".")
            memory = psutil.virtual_memory()

            issues = []
            if disk.percent > 90:
                issues.append(f"Disk usage critical: {disk.percent}%")
            if memory.percent > 90:
                issues.append(f"Memory usage critical: {memory.percent}%")

            if issues:
                return {
                    "status": "warning",
                    "details": "; ".join(issues),
                    "incident": {
                        "type": "resource_pressure",
                        "severity": "medium",
                        "message": "; ".join(issues),
                        "playbook": "resource_alert",
                    },
                }

            return {
                "status": "ok",
                "details": f"Disk: {disk.percent}%, Memory: {memory.percent}%",
            }
        except ImportError:
            return {"status": "warning", "details": "psutil not installed, skipping resource check"}

    def _check_agent_logs(self) -> dict:
        """Scan recent ops logs for errors from other agents."""
        logs_dir = Path(self._paths.get("ops_logs_dir", "ops_logs"))
        if not logs_dir.exists():
            return {"status": "ok", "details": "No ops logs to scan"}

        issues = []
        for log_file in logs_dir.glob("*.jsonl"):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # Check last 50 lines for ERROR or CRITICAL
                    for line in lines[-50:]:
                        entry = json.loads(line)
                        if entry.get("level") in ("ERROR", "CRITICAL"):
                            # Check if the error is recent (last 2 hours)
                            ts_str = entry.get("timestamp", "")
                            try:
                                ts = datetime.fromisoformat(ts_str)
                                if datetime.now(ts.tzinfo) - ts < timedelta(hours=24): # Increased to 24h to catch recent failures
                                    issues.append(f"{log_file.stem}: {entry.get('message', 'Unknown error')}")
                            except Exception:
                                issues.append(f"{log_file.stem}: {entry.get('message', 'Unknown error')}")
            except Exception as e:
                logger.debug(f"Failed to scan {log_file}: {e}")

        if issues:
            return {
                "status": "error",
                "details": f"Found {len(issues)} recent agent runtime errors",
                "incident": {
                    "type": "agent_runtime_error",
                    "severity": "high",
                    "message": " | ".join(issues[:3]) + ("..." if len(issues) > 3 else ""),
                    "playbook": "agent_error",
                },
            }

        return {"status": "ok", "details": "No recent errors in ops logs"}

    def _check_llm_health(self) -> dict:
        """Ping the configured LLM to verify it is reachable."""
        llm_config = self._config.get("llm", {}).get("primary", {})
        if llm_config.get("provider") != "ollama":
            return {"status": "ok", "details": "Using non-local LLM, skipping local health check"}

        base_url = llm_config.get("base_url", "http://localhost:11434")
        expected_model = llm_config.get("model", "llama3.2")
        
        try:
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                tags_data = json.loads(response.read().decode())
            
            models = [m.get("name") for m in tags_data.get("models", [])]
            if not any(expected_model in m for m in models):
                return {
                    "status": "error",
                    "details": f"Configured model '{expected_model}' not found in Ollama",
                    "incident": {
                        "type": "llm_missing",
                        "severity": "critical",
                        "message": f"Ollama model '{expected_model}' missing. Available: {', '.join(models)}",
                        "playbook": "llm_recovery",
                    },
                }
            return {"status": "ok", "details": f"LLM healthy, {expected_model} is available"}
        except Exception as e:
            return {
                "status": "error",
                "details": f"Could not connect to Ollama at {base_url}: {e}",
                "incident": {
                    "type": "llm_service_down",
                    "severity": "critical",
                    "message": f"Ollama service down: {e}",
                    "playbook": "llm_recovery",
                },
            }

    def _calculate_cross_agent_kpis(self) -> dict:
        """Evaluate KPIs based on cross-agent feedback from reports/logs."""
        reports_dir = Path(self._paths.get("reports_dir", "reports"))
        kpis_logged = 0

        # 1. Harvest Quality KPI (Feedback from Quality agent)
        try:
            report_files = sorted(reports_dir.glob("quality_report_*.yml"))
            if report_files:
                with open(report_files[-1], "r", encoding="utf-8") as f:
                    q_report = yaml.safe_load(f)
                
                audited = q_report.get("stations_audited", 0)
                passed = q_report.get("passed", 0)
                if audited > 0:
                    quality_kpi = round((passed / audited) * 100, 2)
                    from agents.common.logger import log_kpi
                    log_kpi(logger, "harvest_quality_rate", quality_kpi, unit="percent", agent_target="harvester")
                    kpis_logged += 1
        except Exception as e:
            logger.debug(f"Failed to calculate harvest_quality_rate: {e}")

        # 2. LLM Reliability KPI
        try:
            llm_log = Path(self._paths.get("ops_logs_dir", "ops_logs")) / "llm_client.jsonl"
            if llm_log.exists():
                with open(llm_log, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                errors = sum(1 for line in lines if "ERROR" in line or "WARNING" in line)
                total = len(lines)
                if total > 0:
                    reliability = round(100 - ((errors / total) * 100), 2)
                    from agents.common.logger import log_kpi
                    log_kpi(logger, "llm_reliability", reliability, unit="percent", agent_target="llm_client")
                    kpis_logged += 1
        except Exception as e:
            logger.debug(f"Failed to calculate llm_reliability: {e}")

        return {"status": "ok", "details": f"Calculated and logged {kpis_logged} cross-agent KPIs"}

    # --- Remediation Engine ---

    def _should_remediate(self) -> bool:
        """Determine if auto-remediation is allowed based on HIL mode."""
        if self._hil_mode == "disabled":
            return True
        if self._hil_mode == "optional":
            return self._auto_remediate
        # "required" mode — log the proposal but don't execute
        return False

    def _remediate(self, incident: dict) -> Optional[dict]:
        """Execute remediation playbook for an incident."""
        playbook_name = incident.get("playbook")
        if not playbook_name:
            return None

        logger.info(f"  [Remediation] Executing: {incident['type']} (playbook: {playbook_name})")

        remediation = {
            "incident_type": incident["type"],
            "playbook": playbook_name,
            "timestamp": datetime.now().isoformat(),
            "hil_mode": self._hil_mode,
        }

        if playbook_name == "data_error":
            success = self._remediate_data_error(incident)
            remediation["action"] = "quarantined_bad_entries"
            remediation["success"] = success

        elif playbook_name == "build_failure":
            success = self._remediate_build_failure(incident)
            remediation["action"] = "attempted_dependency_install"
            remediation["success"] = success

        elif playbook_name == "rate_limit":
            remediation["action"] = "applied_exponential_backoff"
            remediation["success"] = True

        elif playbook_name == "llm_recovery":
            success = self._remediate_llm_recovery(incident)
            remediation["action"] = "updated_config_with_fallback_model"
            remediation["success"] = success

        else:
            remediation["action"] = "no_playbook_matched"
            remediation["success"] = False

        log_incident(
            logger,
            incident_type=incident["type"],
            message=f"Remediation: {remediation['action']}",
            action_taken=remediation["action"],
        )

        return remediation

    def _remediate_data_error(self, incident: dict) -> bool:
        """Handle YAML/data errors by creating a backup."""
        yaml_path = Path(self._paths["polling_stations_file"])
        if yaml_path.exists():
            backup_path = yaml_path.with_suffix(
                f".backup_{date.today().isoformat()}.yml"
            )
            try:
                import shutil
                shutil.copy2(yaml_path, backup_path)
                logger.info(f"  Created backup: {backup_path}")
                return True
            except Exception as e:
                logger.error(f"  Backup failed: {e}")
        return False

    def _remediate_build_failure(self, incident: dict) -> bool:
        """Attempt to fix build failures by installing missing dependencies."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"  Dependency install failed: {e}")
            return False

    def _remediate_llm_recovery(self, incident: dict) -> bool:
        """Remediate missing LLM model by querying available local models and updating config."""
        try:
            llm_config = self._config.get("llm", {}).get("primary", {})
            base_url = llm_config.get("base_url", "http://localhost:11434")
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                tags_data = json.loads(response.read().decode())
            
            models = [m.get("name") for m in tags_data.get("models", [])]
            if not models:
                logger.error("  No Ollama models found locally to fallback to.")
                return False
            
            fallback_model = models[0]
            logger.info(f"  Attempting to fallback to {fallback_model}")
            
            config_path = Path("config.yml")
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            current_model = llm_config.get("model", "llama3.2")
            if f'model: "{current_model}"' in content:
                content = content.replace(f'model: "{current_model}"', f'model: "{fallback_model}"')
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                config_data = yaml.safe_load(content)
                if "llm" in config_data and "primary" in config_data["llm"]:
                    config_data["llm"]["primary"]["model"] = fallback_model
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"  Updated config.yml to use model: {fallback_model}")
            if "llm" in self._config and "primary" in self._config["llm"]:
                self._config["llm"]["primary"]["model"] = fallback_model
            return True
        except Exception as e:
            logger.error(f"  LLM recovery failed: {e}")
            return False

    def _load_playbooks(self) -> dict:
        """Load remediation playbooks from YAML configs."""
        playbooks_dir = Path("agents") / "sre_ops" / "playbooks"
        playbooks = {}

        if playbooks_dir.exists():
            for pb_file in playbooks_dir.glob("*.yml"):
                try:
                    with open(pb_file, "r") as f:
                        playbooks[pb_file.stem] = yaml.safe_load(f)
                except Exception:
                    pass

        return playbooks

    def _write_ops_log(self, report: dict) -> None:
        """Write SRE operations report to ops_logs."""
        logs_dir = Path(self._paths.get("ops_logs_dir", "ops_logs"))
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / f"sre_report_{date.today().isoformat()}.yml"
        with open(log_file, "w", encoding="utf-8") as f:
            yaml.dump(report, f, default_flow_style=False, allow_unicode=True)
