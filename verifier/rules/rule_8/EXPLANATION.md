# Rule 8 – Structured Input and Conversion Validation

## Concept
Rule 8 treats modified structured inputs as a small schema (`EXPECTED_FIELDS`) and exercises valid, missing-field, and wrong-type payloads. It checks that valid payloads succeed and malformed ones raise explicit errors.

## Why it matters
Schema evolution regressions (missing fields, silent defaults, wrong dimensions) commonly slip past tests. Static analyzers do not reason about runtime input validation, and coverage does not guarantee defensive behavior.

## Example bug
```python
EXPECTED_FIELDS = {"name": str, "count": int}

def parse(payload):
    return {"name": payload.get("name", ""), "count": payload.get("count", 0)}  # silently defaults
```
The parser accepts missing fields instead of failing fast.

## Difference vs. existing analyzers
Existing static checks cannot infer schema intent; dynamic coverage only shows execution. This rule actively mutates structured inputs to ensure strict validation.

## How to run
```
python -m verifier.rules.runner --rule rule_8 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_8_structured_input_validation.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
