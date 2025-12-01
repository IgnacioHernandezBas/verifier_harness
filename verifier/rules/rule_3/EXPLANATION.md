# Rule 3 – State Transition Tours

## Concept
Rule 3 models modified states and events as a small finite state machine and drives each transition plus a two-step tour. It highlights discrepancies between expected next states and observed execution, aligning with `@papers/stt` transition-touring techniques.

## Why it matters
Missing state updates, unexpected next-state assignments, and unreachable transitions frequently surface only under specific sequences. Traditional analyzers rarely exercise multi-hop paths, letting these regressions escape.

## Example bug
```python
TRANSITIONS = {("CONNECTED", "close"): "CLOSED"}

def advance_state(state, event):
    # Bug: forgets to move to CLOSED
    return state
```
The transition table promises `CLOSED`, but execution keeps the connection stuck.

## Difference vs. existing analyzers
Static checks confirm the table structure; coverage confirms a line ran. This rule asserts that observed transitions match the declared graph and that multi-hop tours succeed, surfacing dead-ends and incorrect destinations.

## How to run
```
python -m verifier.rules.runner --rule rule_3 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_3_state_transition_tours.py

or to test them all:

pytest -q -o addopts='' tests/rules

```
