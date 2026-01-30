# claim_extraction/llm/factory.py
from __future__ import annotations
from typing import Any, Dict
from claim_extraction.llm.base import LLMClient
from claim_extraction.llm.vllm_client import VLLMClient

def build_llm_client(cfg: Dict[str, Any]) -> LLMClient:
    backend = (cfg.get("backend") or "vllm").lower()
    if backend == "vllm":
        api_key = cfg.get("api_key") or None
        return VLLMClient(
            endpoint=cfg["endpoint"],
            model=cfg["model"],
            timeout_s=int(cfg.get("timeout_s", 120)),
            api_key=api_key,
        )
    raise ValueError(f"Unsupported LLM backend: {backend}")
