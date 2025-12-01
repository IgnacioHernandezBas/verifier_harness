# Rule 4 – Definition–Use Execution

## Concept
Rule 4 traces changed variables and resources through their definition and use sites, flagging conditional initialization and missing cleanup across altered paths. It follows def–use analysis patterns referenced in `@papers/stt`.

## Why it matters
Use-before-def, skipped initialization, and forgotten cleanup often hide in early returns or new branches added by a patch. Standard static analyzers may not pair definitions with downstream uses, leaving runtime failures or leaks undetected.

## Example bug
```python
def load(flag):
    if flag:
        handle = open_resource()
    return handle  # fails when flag is False
```
The resource is only initialized conditionally, leading to a runtime error on the false branch.

## Difference vs. existing analyzers
Existing static analyzers check syntax and style; coverage ensures execution but not variable lifecycles. This rule inspects def–use chains and resource cleanup obligations for changed symbols.

## How to run
```
python -m verifier.rules.runner --rule rule_4 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_4_definition_use_execution.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
