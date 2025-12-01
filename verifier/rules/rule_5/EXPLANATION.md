# Rule 5 – Resource Lifecycle Under Load

## Concept
Rule 5 repeatedly executes patched operations while watching resource collections (handles, connections, open sets) for unbounded growth. It mirrors the load-focused techniques described in `@papers/stt`.

## Why it matters
Leaks and missing release paths rarely appear in unit tests but manifest under repetition. Tracking resource growth across iterations exposes regressions that static analyzers and single-pass tests miss.

## Example bug
```python
OPEN_CONNECTIONS = []

def connect():
    OPEN_CONNECTIONS.append(object())  # never removed under retries
```
Repeated calls grow `OPEN_CONNECTIONS` without ever releasing entries.

## Difference vs. existing analyzers
Static analyzers cannot observe runtime growth, and coverage only marks execution. This rule adds lightweight resource accounting under load to flag leaks early.

## How to run
```
python -m verifier.rules.runner --rule rule_5 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_5_resource_lifecycle_under_load.py

or to test them all:

pytest -q -o addopts='' tests/rules

```
