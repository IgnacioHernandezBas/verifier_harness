# claim_extraction/llm/vllm_client.py
from __future__ import annotations
import requests
from typing import Optional, List
from claim_extraction.llm.base import LLMClient, LLMResponse

class VLLMClient(LLMClient):
    def __init__(self, endpoint: str, model: str, timeout_s: int = 120,
                 api_key: Optional[str] = None):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.api_key = api_key

    def generate(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 2048,
                 stop: Optional[List[str]] = None) -> LLMResponse:
        url = f"{self.endpoint}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop

        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(text=text, raw=data)
