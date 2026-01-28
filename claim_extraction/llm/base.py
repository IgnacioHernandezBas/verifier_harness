# claim_extraction/llm/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

@dataclass
class LLMResponse:
    text: str
    raw: Optional[Dict[str, Any]] = None

class LLMClient:
    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        raise NotImplementedError
