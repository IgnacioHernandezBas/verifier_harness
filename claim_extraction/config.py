# claim_extraction/config.py
from __future__ import annotations
import os
import yaml
from typing import Any, Dict

def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a YAML mapping")
    return apply_env_overrides(cfg)

def apply_env_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:
    llm = cfg.setdefault("llm", {})
    backend = os.getenv("CLAIM_LLM_BACKEND")
    endpoint = os.getenv("CLAIM_LLM_ENDPOINT")
    model = os.getenv("CLAIM_LLM_MODEL")

    if backend:
        llm["backend"] = backend
    if endpoint:
        llm["endpoint"] = endpoint
    if model:
        llm["model"] = model
    return cfg
