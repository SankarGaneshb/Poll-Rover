"""
Poll-Rover Structured Logger
Provides consistent, structured logging across all agents with
incident-level tagging for SRE ops.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


IST = timezone(offset=__import__("datetime").timedelta(hours=5, minutes=30))


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for machine-readable ops logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(IST).isoformat(),
            "level": record.levelname,
            "agent": getattr(record, "agent", "system"),
            "message": record.getMessage(),
        }

        # Add optional structured fields
        if hasattr(record, "station_id"):
            log_entry["station_id"] = record.station_id
        if hasattr(record, "incident_type"):
            log_entry["incident_type"] = record.incident_type
        if hasattr(record, "action_taken"):
            log_entry["action_taken"] = record.action_taken
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        
        # KPI fields
        if hasattr(record, "kpi_name"):
            log_entry["kpi_name"] = record.kpi_name
        if hasattr(record, "kpi_value"):
            log_entry["kpi_value"] = record.kpi_value
        if hasattr(record, "kpi_unit"):
            log_entry["kpi_unit"] = record.kpi_unit

        return json.dumps(log_entry, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Human-readable colored formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    AGENTS = {
        "harvester": "[HV]",
        "quality": "[QA]",
        "sre_ops": "[SRE]",
        "citizen_assist": "[CA]",
        "orchestrator": "[OR]",
        "system": "[SYS]",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        agent = getattr(record, "agent", "system")
        icon = self.AGENTS.get(agent, "[SYS]")
        timestamp = datetime.now(IST).strftime("%H:%M:%S")
        return (
            f"{color}[{timestamp}] {icon} {agent:>15} | "
            f"{record.levelname:<8} | {record.getMessage()}{self.RESET}"
        )


def get_logger(
    agent_name: str,
    log_dir: Optional[str] = None,
    console_level: int = logging.INFO,
) -> logging.Logger:
    """Create a logger for an agent with both console and file outputs.

    Args:
        agent_name: Name of the agent (e.g., 'harvester', 'sre_ops').
        log_dir: Directory for log files. Defaults to 'ops_logs/'.
        console_level: Console logging level.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(f"poll_rover.{agent_name}")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(HumanFormatter())
    logger.addHandler(console_handler)

    # File handler (structured JSON)
    if log_dir is None:
        project_root = Path(__file__).parent.parent.parent
        log_dir = str(project_root / "ops_logs")

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(
        log_path / f"{agent_name}.jsonl",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredFormatter())
    logger.addHandler(file_handler)

    # Add agent name to all records from this logger
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "agent"):
            record.agent = agent_name
        return record

    logging.setLogRecordFactory(record_factory)

    return logger


def log_incident(
    logger: logging.Logger,
    incident_type: str,
    message: str,
    action_taken: Optional[str] = None,
    station_id: Optional[str] = None,
    **extra_data,
) -> None:
    """Log a structured SRE incident.

    Args:
        logger: Logger instance.
        incident_type: Type of incident (e.g., 'build_failure', 'data_error').
        message: Human-readable incident description.
        action_taken: What remediation was performed.
        station_id: Related polling station ID if applicable.
        **extra_data: Additional context data.
    """
    logger.warning(
        message,
        extra={
            "incident_type": incident_type,
            "action_taken": action_taken or "none",
            "station_id": station_id or "N/A",
            "extra_data": extra_data if extra_data else None,
        },
    )


def log_kpi(
    logger: logging.Logger,
    kpi_name: str,
    value: float,
    unit: str = "count",
    **extra_data,
) -> None:
    """Log a structured KPI metric.

    Args:
        logger: Logger instance.
        kpi_name: Name of the KPI (e.g., 'success_rate', 'latency').
        value: Numeric value of the KPI.
        unit: Unit of measurement (e.g., 'percent', 'ms', 'count').
        **extra_data: Additional context data.
    """
    logger.info(
        f"KPI: {kpi_name} = {value} {unit}",
        extra={
            "kpi_name": kpi_name,
            "kpi_value": value,
            "kpi_unit": unit,
            "extra_data": extra_data if extra_data else None,
        },
    )
