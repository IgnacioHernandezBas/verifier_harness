# Rule 9 – Concurrency and Interlock Order Checks

## Concept
Rule 9 executes patched critical sections concurrently, looking for deadlocks, lost wakeups, and inconsistent state updates (e.g., missed counter increments). It mirrors the interlock testing guidance from `@papers/stt`.

## Why it matters
Lock ordering mistakes and missing releases rarely trigger in single-threaded tests. Concurrency bugs manifest as hangs or silent data loss that static analyzers and simple coverage cannot expose.

## Example bug
```python
LOCK = threading.Lock()
COUNTER = 0

def increment():
    LOCK.acquire()
    # bug: no release, later threads hang
    global COUNTER
    COUNTER += 1
```
Concurrent callers block forever or lose updates.

## Difference vs. existing analyzers
Static tools may warn about locks but cannot prove runtime behavior. Coverage confirms execution but not liveness. This rule drives concurrent workers with timeouts and checks shared counters for lost updates.

## How to run
```
python -m verifier.rules.runner --rule rule_9 --repo /path/to/repo --patch-file tests/rules/r1/patch.diff
```

## How to test
```
pytest -q -o addopts='' tests/rules/test_rule_9_concurrency_and_interlocks.py

or to test them all:

pytest -q -o addopts='' tests/rules
```
