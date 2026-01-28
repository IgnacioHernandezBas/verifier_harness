# claim_extraction/parsing/json_repair.py
from __future__ import annotations
import json, re
from typing import Any, Dict, List, Tuple

def parse_json_array_with_fallbacks(text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    details = {"attempts": []}
    s = (text or "").strip()

    # strip fences
    s = re.sub(r"^```json\s*\n?", "", s)
    s = re.sub(r"^```\s*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s)

    start = s.find("[")
    end = s.rfind("]") + 1
    if start < 0 or end <= 0:
        details["attempts"].append({"method": "find_array", "success": False})
        return [], details

    chunk = s[start:end]

    # direct
    try:
        obj = json.loads(chunk)
        if isinstance(obj, list):
            details["attempts"].append({"method": "direct", "success": True})
            return obj, details
    except Exception as e:
        details["attempts"].append({"method": "direct", "success": False, "error": str(e)[:80]})

    # repair trailing commas
    repaired = re.sub(r",(\s*[}\]])", r"\1", chunk)
    try:
        obj = json.loads(repaired)
        if isinstance(obj, list):
            details["attempts"].append({"method": "repaired", "success": True})
            return obj, details
    except Exception as e:
        details["attempts"].append({"method": "repaired", "success": False, "error": str(e)[:80]})

    return [], details
