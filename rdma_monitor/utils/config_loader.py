"""Configuration loader with environment variable override support."""

import os
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parent.parent / "config.yaml",
    Path("/etc/rdma_monitor/config.yaml"),
    Path.home() / ".rdma_monitor" / "config.yaml",
]


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (base is mutated)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _apply_env_overrides(cfg: dict) -> dict:
    """Override config values with RDMA_MON_<SECTION>__<KEY> env vars.

    Example: RDMA_MON_PROMETHEUS__PORT=9100 sets cfg["prometheus"]["port"]=9100
    """
    prefix = "RDMA_MON_"
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        parts = env_key[len(prefix):].lower().split("__")
        node = cfg
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        # Try to preserve types (int, float, bool)
        final_key = parts[-1]
        if env_val.lower() in ("true", "false"):
            node[final_key] = env_val.lower() == "true"
        else:
            try:
                node[final_key] = int(env_val)
            except ValueError:
                try:
                    node[final_key] = float(env_val)
                except ValueError:
                    node[final_key] = env_val
    return cfg


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file, with env-var overrides.

    Resolution order:
    1. Explicit *path* argument
    2. RDMA_MON_CONFIG environment variable
    3. Default search paths
    """
    config_path: Path | None = None

    if path:
        config_path = Path(path)
    elif "RDMA_MON_CONFIG" in os.environ:
        config_path = Path(os.environ["RDMA_MON_CONFIG"])
    else:
        for p in _DEFAULT_CONFIG_PATHS:
            if p.is_file():
                config_path = p
                break

    if config_path is None or not config_path.is_file():
        logger.warning("No config file found; using built-in defaults.")
        # Return minimal defaults so the monitor can still start
        cfg: dict[str, Any] = {}
    else:
        logger.info("Loading config from %s", config_path)
        with open(config_path, "r") as fh:
            cfg = yaml.safe_load(fh) or {}

    cfg = _apply_env_overrides(cfg)
    return cfg
