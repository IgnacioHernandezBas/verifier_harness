from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from jinja2 import Environment, FileSystemLoader

SYSTEM_PROMPT = (
    "You are a senior Python test engineer. You write minimal, deterministic pytest tests.\n"
    "Output ONLY valid Python code (no markdown, no explanations). Use pytest.\n"
    "Do not use network calls. Do not assume external files unless explicitly provided."
)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PROMPT_ENV = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)), autoescape=False)


def guess_import_from_path(path: Optional[str]) -> Optional[str]:
    """Convert repository file path to dotted import path."""
    if not path:
        return None
    cleaned = path.strip().replace("\\", "/")
    if not cleaned:
        return None
    if cleaned.endswith("__init__.py"):
        cleaned = cleaned[: -len("__init__.py")]
    elif cleaned.endswith(".py"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip("/").replace("/", ".")
    cleaned = re.sub(r"\.+", ".", cleaned).strip(".")
    return cleaned or None


def pick_primary_grounding_path(claim: Dict[str, Any]) -> Optional[str]:
    """Return the first grounding evidence path if present."""
    grounding = claim.get("grounding") or {}
    evidence = grounding.get("evidence") or []
    for ev in evidence:
        path = ev.get("path")
        if path:
            return path
    return None


def build_testgen_messages(claim: Dict[str, Any], repo: str, instance_id: str) -> List[Dict[str, str]]:
    claim_id = claim.get("claim_id") or "C1"
    claim_type = claim.get("claim_type") or "unknown"
    path = pick_primary_grounding_path(claim)
    suggested_module = guess_import_from_path(path) or "None"
    target_symbols = claim.get("target_symbols") or []
    tmpl = _PROMPT_ENV.get_template("testgen_prompt.jinja")
    user_content = tmpl.render(
        repo=repo,
        instance_id=instance_id,
        claim_id=claim_id,
        claim_type=claim_type,
        claim_text=claim.get("claim_text") or "",
        given_text=claim.get("given") or "",
        when_text=claim.get("when") or "",
        then_text=claim.get("then") or "",
        target_symbols=target_symbols,
        primary_file_path=path or "None",
        suggested_module=suggested_module,
        claim_slug=_claim_id_slug(claim_id),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


class VLLMClient:
    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout_s: int = 120,
        api_key: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]]) -> str:
        url = f"{self.endpoint}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def generate_pytest_for_claim(
    claim: Dict[str, Any],
    repo: str,
    instance_id: str,
    client: VLLMClient,
    extra_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    messages = build_testgen_messages(claim, repo=repo, instance_id=instance_id)
    if extra_messages:
        messages.extend(extra_messages)
    raw = client.chat(messages)
    code = extract_pytest_code(raw)
    claim_id = claim.get("claim_id") or "C1"
    slug = _claim_id_slug(claim_id)

    if "import pytest" not in code:
        code = "import pytest\n\n" + code

    fn_signature = f"def test_claim_{slug}"
    if fn_signature not in code:
        fallback = _build_fallback_test(claim, slug)
        code = f"import pytest\n\n{fallback}"

    return code.strip() + "\n"


def extract_pytest_code(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 3:
            stripped = parts[1]
            if stripped.startswith("python"):
                stripped = stripped[len("python") :]
    return stripped.strip()


def _claim_id_slug(claim_id: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", claim_id).strip("_")
    return slug.lower() or "c1"


def _build_fallback_test(claim: Dict[str, Any], slug: str) -> str:
    target_symbols = claim.get("target_symbols") or []
    primary_symbol = target_symbols[0] if target_symbols else None
    primary_path = pick_primary_grounding_path(claim)
    module_str = guess_import_from_path(primary_path)

    given = claim.get("given") or "Preconditions."
    when = claim.get("when") or "Action."
    then = claim.get("then") or "Expected outcome."

    lines: List[str] = []
    if module_str:
        lines.append(f"import importlib\nMODULE_PATH = \"{module_str}\"")
    else:
        lines.append("import importlib\nMODULE_PATH = None")

    lines.extend(
        [
            "",
            f"def test_claim_{slug}():",
            f"    # GIVEN: {given}",
            f"    # WHEN: {when}",
            f"    # THEN: {then}",
            "    if MODULE_PATH is None:",
            "        pytest.skip('No module path available for this claim.')",
            "    module = importlib.import_module(MODULE_PATH)",
        ]
    )

    if primary_symbol:
        lines.append(f"    assert hasattr(module, \"{primary_symbol}\"), \"Expected symbol not found\"")
    else:
        lines.append("    assert module is not None")
    lines.append("    # TODO: refine this test manually based on repository context.")

    return "\n".join(lines)
