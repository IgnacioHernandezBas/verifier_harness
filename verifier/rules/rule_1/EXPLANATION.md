# Rule 1 – Boundary and Intersection Probing

## Concept
This rule looks for patches that shift inclusive/exclusive predicates or change numeric thresholds without exercising the edge inputs. It is aligned with taxonomy classes in the 31xx family and the `@papers/stt` boundary-probing technique.

## Why it matters
Off-by-one and closure mistakes frequently slip past traditional static analyzers because the syntax is valid and test suites rarely hit “just below / at / just above” inputs. This rule highlights boundary shifts and verifies that edge points route to distinct outcomes.

## Example bug
```python
# Patch changed the boundary:
if retries > 3:      # expected >= 3
    raise BackoffError()
```
The change silently drops the `retries == 3` case; boundary probing surfaces the missing branch.

## Difference vs. existing analyzers
Static analyzers in `static_analyzers` and coverage tools only confirm execution, not boundary sensitivity. This rule inspects predicate shifts and executes boundary probes to detect collapsed edges or intersecting conditions that stay untested.

## How to run
```
python -m verifier.rules.runner --rule rule_1 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_1_boundary_and_intersections.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
