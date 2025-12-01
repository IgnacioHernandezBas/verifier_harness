# Rule 6 – Robust Exception and Message Paths

## Concept
Rule 6 inspects new `raise`, `except`, and logging paths to ensure specific exception types and informative messages are used. It injects negative scenarios conceptually aligned with `@papers/stt` resilience checks.

## Why it matters
Broad `except` blocks, generic exceptions, and uninformative logs obscure root causes. These regressions rarely surface in happy-path tests and easily bypass static style checks.

## Example bug
```python
try:
    risky()
except Exception:
    raise Exception("failed")
```
The code collapses error details and omits identifiers that aid diagnosis.

## Difference vs. existing analyzers
Static analyzers may tolerate broad catches or generic raises; coverage confirms execution but not specificity. This rule flags broad handlers and low-context messages that weaken observability.

## How to run
```
python -m verifier.rules.runner --rule rule_6 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_6_robust_exception_paths.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
