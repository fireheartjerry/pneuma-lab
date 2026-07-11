"""Model + host resolution for the optional local elaboration layer.

Voice and judge models are configured INDEPENDENTLY. Each resolves through
CLI arg -> environment -> optional project config file -> fallback. The config
file is optional JSON (stdlib only); absent/malformed tiers are skipped. Nothing
here contacts a network or requires Ollama to be installed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_DEFAULT_MODEL = "llama3.1"
_DEFAULT_HOST = "http://localhost:11434"


def _load_config() -> dict:
    path = os.environ.get("PNEUMA_VOICE_CONFIG") or "pneuma-voice.config.json"
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve(cli: str | None, env_key: str, config_key: str, default: str) -> str:
    if cli:
        return cli
    env = os.environ.get(env_key)
    if env:
        return env
    cfg = _load_config().get(config_key)
    if isinstance(cfg, str) and cfg:
        return cfg
    return default


def resolve_voice_model(cli: str | None = None) -> str:
    return _resolve(cli, "PNEUMA_VOICE_MODEL", "voice_model", _DEFAULT_MODEL)


def resolve_judge_model(cli: str | None = None) -> str:
    return _resolve(cli, "PNEUMA_JUDGE_MODEL", "judge_model", _DEFAULT_MODEL)


def resolve_ollama_host(cli: str | None = None) -> str:
    return _resolve(cli, "PNEUMA_OLLAMA_HOST", "ollama_host", _DEFAULT_HOST)


__all__ = ["resolve_voice_model", "resolve_judge_model", "resolve_ollama_host"]
