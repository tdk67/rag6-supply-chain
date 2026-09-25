"""Configuration manager for Aethelgard Infra-GraphRAG.

Loads operational configurations from config.json and private secrets strictly from .env.
Ensures clean separation of concerns and zero hardcoded configuration parameters.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

_CACHED_CONFIG: Optional[Dict[str, Any]] = None
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return _PROJECT_ROOT


def load_config(config_path: Optional[str | Path] = None, force_reload: bool = False) -> Dict[str, Any]:
    """Load configuration from config.json and initialize environment variables.

    Args:
        config_path: Optional custom path to config.json.
        force_reload: If True, reload from disk ignoring cache.

    Returns:
        Dict containing operational configuration settings.
    """
    global _CACHED_CONFIG
    if _CACHED_CONFIG is not None and not force_reload:
        return _CACHED_CONFIG

    # Load environment variables strictly from .env
    env_file = _PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    target_config = Path(config_path) if config_path else _PROJECT_ROOT / "config.json"
    if not target_config.exists():
        raise FileNotFoundError(f"Configuration file not found at: {target_config}")

    with open(target_config, "r", encoding="utf-8") as f:
        data = json.load(f)

    _CACHED_CONFIG = data
    return _CACHED_CONFIG


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve a private secret strictly from the environment/.env.

    Args:
        key: Environment variable name.
        default: Fallback value if not found.

    Returns:
        Secret string or default.
    """
    return os.environ.get(key, default)


def resolve_path(relative_or_absolute: str | Path) -> Path:
    """Resolve a path relative to the project root if it is not absolute.

    Args:
        relative_or_absolute: Path string or Path object.

    Returns:
        Resolved absolute Path.
    """
    path_obj = Path(relative_or_absolute)
    if path_obj.is_absolute():
        return path_obj
    return (_PROJECT_ROOT / path_obj).resolve()
