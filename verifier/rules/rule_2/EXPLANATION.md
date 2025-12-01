# Rule 2 – Predicate Influence (MC/DC Style)

## Concept
Rule 2 decomposes changed boolean expressions into atomic clauses and checks whether each clause can independently toggle the result (MC/DC-style influence). It maps to taxonomy classes 312x and 244x and leverages the `@papers/stt` emphasis on clause-level independence.

## Why it matters
Masked conditions, duplicated clauses, or misplaced operators often survive code review because the predicate still looks reasonable. Without clause-level tests, these mistakes reduce coverage and hide reachable bugs.

## Example bug
```python
# Introduced duplication that masks the second input
return is_authorized and is_authorized
```
Here `is_authorized` masks the `has_quota` signal that was supposed to gate the operation.

## Difference vs. existing analyzers
Static analyzers flag syntax or style issues but not clause influence; coverage merely notes execution. This rule executes targeted combinations and inspects boolean structures to catch masked clauses and constant operands.

## How to run
```
python -m verifier.rules.runner --rule rule_2 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_2_predicate_influence.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
```
