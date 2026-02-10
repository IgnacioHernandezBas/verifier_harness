from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

try:  # requests is optional inside the Singularity container
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None

try:  # jinja2 may be absent inside the runtime image
    from jinja2 import Environment, FileSystemLoader  # type: ignore
except ImportError:  # pragma: no cover
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore

SYSTEM_PROMPT = (
    "You are a senior Python test engineer. You write minimal, deterministic pytest tests.\n"
    "Output ONLY valid Python code (no markdown, no explanations). Use pytest.\n"
    "Do not use network calls. Do not assume external files unless explicitly provided."
)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
if Environment is not None:
    _PROMPT_ENV = Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)), autoescape=False
    )
else:
    _PROMPT_ENV = None
    _PROMPT_TEXT = (PROMPTS_DIR / "testgen_prompt.jinja").read_text(encoding="utf-8")


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
    template_vars = {
        "repo": repo,
        "instance_id": instance_id,
        "claim_id": claim_id,
        "claim_type": claim_type,
        "claim_text": claim.get("claim_text") or "",
        "given_text": claim.get("given") or "",
        "when_text": claim.get("when") or "",
        "then_text": claim.get("then") or "",
        "target_symbols": target_symbols,
        "primary_file_path": path or "None",
        "suggested_module": suggested_module,
        "claim_slug": _claim_id_slug(claim_id),
    }
    user_content = _render_prompt(template_vars)
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
        data = self._post_json(url, payload)
        return data["choices"][0]["message"]["content"]

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if requests is not None:
            resp = requests.post(
                url, json=payload, headers=headers, timeout=self.timeout_s
            )
            resp.raise_for_status()
            return resp.json()

        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_s) as response:
                response_body = response.read()
                encoding = response.headers.get_content_charset("utf-8")
                return json.loads(response_body.decode(encoding))
        except urllib_error.HTTPError as exc:  # pragma: no cover
            error_body = exc.read().decode("utf-8", "ignore")
            raise RuntimeError(
                f"vLLM request failed with HTTP {exc.code}: {error_body}"
            ) from None
        except urllib_error.URLError as exc:  # pragma: no cover
            raise RuntimeError(f"Unable to reach vLLM server: {exc.reason}") from exc


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


def _render_prompt(context: Dict[str, Any]) -> str:
    if _PROMPT_ENV is not None:
        tmpl = _PROMPT_ENV.get_template("testgen_prompt.jinja")
        return tmpl.render(**context)

    rendered = _PROMPT_TEXT
    for key, value in context.items():
        placeholder = f"{{{{ {key} }}}}"
        rendered = rendered.replace(placeholder, _stringify_prompt_value(value))
    return rendered


def _stringify_prompt_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
