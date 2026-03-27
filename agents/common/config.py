"""
Poll-Rover Configuration Loader
Loads global config from config.yml with environment variable overrides.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file with env var overrides.
    
    Args:
        config_path: Path to config.yml. Defaults to project root.
    
    Returns:
        Configuration dictionary.
    """
    global _CONFIG_CACHE
    
    if _CONFIG_CACHE is not None and config_path is None:
        return _CONFIG_CACHE

    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = str(project_root / "config.yml")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Environment variable overrides
    _apply_env_overrides(config)

    if config_path is None:
        _CONFIG_CACHE = config

    return config


def _apply_env_overrides(config: Dict[str, Any]) -> None:
    """Override config values from environment variables."""
    
    # LLM keys
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        config.setdefault("llm", {}).setdefault("fallback", {})["api_key"] = gemini_key

    # Ollama URL override
    ollama_url = os.environ.get("OLLAMA_BASE_URL")
    if ollama_url:
        config.setdefault("llm", {}).setdefault("primary", {})["base_url"] = ollama_url

    # HIL mode override
    hil_mode = os.environ.get("SRE_HIL_MODE")
    if hil_mode and hil_mode in ("required", "optional", "disabled"):
        config.setdefault("agents", {}).setdefault("sre_ops", {})["hil_mode"] = hil_mode


def get_pilot_states(config: Optional[Dict[str, Any]] = None) -> list:
    """Get list of pilot state configurations."""
    if config is None:
        config = load_config()
    return config.get("pilot", {}).get("states", [])


def get_agent_config(agent_name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get configuration for a specific agent."""
    if config is None:
        config = load_config()
    return config.get("agents", {}).get(agent_name, {})


def get_llm_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get LLM configuration."""
    if config is None:
        config = load_config()
    return config.get("llm", {})


def get_paths(config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Get configured paths."""
    if config is None:
        config = load_config()
    return config.get("paths", {})
