# claim_extraction/pipeline/stacktrace.py
from __future__ import annotations

import re
from typing import Dict, List


def extract_stacktrace_info(problem_statement: str) -> List[Dict]:
    """
    Extract stacktrace file+line+function from issue text.
    Format: File "path.py", line N, in func
    """
    ps = problem_statement or ""
    results: List[Dict] = []
    pattern = r'File ["\']([^"\']+\.py)["\'],\s*line\s*(\d+)(?:,\s*in\s+(\w+))?'

    for m in re.finditer(pattern, ps):
        filepath = m.group(1)
        if "site-packages" in filepath or "venv" in filepath:
            continue
        results.append({
            "file": filepath,
            "line": int(m.group(2)),
            "function": m.group(3),
        })

    return results
