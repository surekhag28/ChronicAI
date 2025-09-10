import os
import time
from typing import Set, Optional
import yaml

from dotenv import load_dotenv

load_dotenv()

base_dir = os.path.dirname(__file__)
_yaml_path: Optional[str] = None
_ttl_seconds: int = 300
_cache: Set[str] = set()
_last_refresh: float = 0.0


def configure_policy(yaml_path: str, ttl_seconds: int = 300) -> None:
    """Configure YAML file path for getting list of allowed tables"""

    if not yaml_path:
        raise ValueError("yaml path is required to get list of allowed tables")

    global _yaml_path, _ttl_seconds
    _yaml_path = os.path.join(base_dir, yaml_path)
    _ttl_seconds = ttl_seconds


def _load_yaml() -> Set[str]:
    if not _yaml_path or not os.path.exists(_yaml_path):
        raise FileNotFoundError(f"Allow-list yaml file not found: {_yaml_path}")
    with open(_yaml_path, "r") as f:
        data = yaml.safe_load(f) or {}
    items = data.get("allowed_tables") or []
    if not items or not isinstance(items, list):
        raise ValueError("allowed-tables must be a non-empty list in YAML.")
    return {str(item).strip().lower() for item in items if str(item).strip()}


def allowed_tables() -> Set[str]:
    """Returns cached allowlist tables from YAML file, refreshing on TTL. Fail closed on errors"""
    global _cache, _last_refresh
    now = time.time()
    if _cache and now - _last_refresh < _ttl_seconds:
        return _cache

    tables = _load_yaml()
    _cache = tables
    _last_refresh = now
    return _cache
