# Rule 7 – Transaction Order and Parameter Contracts

## Concept
Rule 7 models patched operations as ordered transactions (init → use → teardown) and validates that observed sequences match declared expectations such as `EXPECTED_SEQUENCE`. It also guards against silent success when parameters are misordered.

## Why it matters
Misordered steps and swapped parameters often appear to work until exercised in a specific order. Static analyzers and simple coverage do not assert that the intended ordering or binding is respected.

## Example bug
```python
EXPECTED_SEQUENCE = ["connect", "send", "close"]

def run_flow():
    return ["connect", "close", "send"]  # teardown happens too early
```
The transaction closes before sending, violating the contract.

## Difference vs. existing analyzers
Existing analyzers confirm syntax and execution; they do not compare observed sequences to contractual orderings. This rule explicitly checks order and presence of required steps.

## How to run
```
python -m verifier.rules.runner --rule rule_7 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_7_transaction_order_and_params.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
