# Supplementary Verification Rules

## Overview
- Provide practical verification rules that close gaps left by the existing static (`code_quality`, `syntax_structure`) and dynamic (coverage-focused) analyzers, targeting taxonomy classes from `papers/bug_taxonomy.pdf`.
- Use focused techniques from `papers/stt.pdf` (domain, logic-based, state, data-flow, stress/resource, robustness, transaction flow, syntax testing) with lightweight Python tooling (pytest + plugins, hypothesis, coverage/pytest-cov, pytest-xdist, pytest-timeout, monkeypatch, psutil) to keep runs efficient while improving defect detection.

## Rule Set

### Rule 1: Boundary and Intersection Probing
- **Bug Taxonomy Mapping:** 241x/242x/243x/244x – domain misunderstanding, boundary location/closure/intersection errors
- **Description:** Exercise just-below/at/just-above each modified boundary and each corner of multi-variable predicates to ensure routing to the intended branch after comparison edits.
- **Why It Matters:** Boundary slips silently misroute requests or bypass checks; these regressions are common when AI rewrites conditions.
- **Implementation Outline:**  
  - Tooling: `pytest`, `hypothesis` (strategies for edge values), `pytest-cov`, `pytest-xdist`  
  - Steps: extract changed predicates from the patch; enumerate boundary literals/expressions; generate tests hitting off/on/off points and intersection corners; assert branch outcomes or outputs; run with `pytest -q --cov --maxfail=1 -n auto` to keep fast feedback.
- **Technique from papers/stt:** Domain Testing (Ch. 6) – boundary value and worst-case corner selection expose domain partition faults.
- **Difference vs. Existing Analyzers:** Current analyzers measure syntax/coverage but don’t assert semantic correctness at boundary edges or intersections.
- **Efficiency Notes:** Limit to predicates touched by the patch; 3–5 cases per edge and a small set of corners keeps runtime low, parallelized via `pytest-xdist`.
- **Example Bug Caught:** Changed `if retries > 3:` to `>=` wrongly rejects exactly 3 attempts; on/off tests reveal the closure error (242x).

### Rule 2: Predicate Influence (MC/DC-Style)
- **Bug Taxonomy Mapping:** 312x – control predicates; 244x – boundary intersections
- **Description:** Build a compact decision table for each modified boolean expression and run tests where each atomic condition independently toggles the outcome while others are held enabling, ensuring no masked or duplicated logic.
- **Why It Matters:** Operator swaps or added flags can render clauses ineffective, skipping validations or triggering handlers incorrectly.
- **Implementation Outline:**  
  - Tooling: `pytest`, `pytest-subtests`, `hypothesis` for boolean/vector generation  
  - Steps: normalize changed predicates into atomic conditions; derive MC/DC cases; parametrize tests to show each condition’s effect; assert chosen branch or side effect; run in CI with `pytest -q --maxfail=1`.
- **Technique from papers/stt:** Logic-Based Testing with Cause-Effect Graphs/Decision Tables (Ch. 9) – exercises condition combinations with independence.
- **Difference vs. Existing Analyzers:** Coverage can hit lines without proving each clause affects flow; static checks don’t reason about semantic masking.
- **Efficiency Notes:** Use MC/DC instead of full truth tables; cap generated cases and shrink with hypothesis health checks.
- **Example Bug Caught:** New guard `if is_admin or (is_owner and not suspended):` still blocks suspended admins; MC/DC case `is_admin=True, suspended=True` exposes the logic error (312x).

### Rule 3: State Transition Tours
- **Bug Taxonomy Mapping:** 3154 – incorrect control state transition; 316x – exception flow misrouting
- **Description:** Model the touched states/flags as a minimal FSM and verify each new/changed transition and at least one two-step tour reaches the correct next state, including error exits.
- **Why It Matters:** Early returns or new flags can leave systems in wrong states, causing lockups, double work, or skipped cleanup.
- **Implementation Outline:**  
  - Tooling: `pytest`, `hypothesis` for event sequences, `pytest-timeout` for hang detection  
  - Steps: list state variables/events from the patch; draft a transition table; write tests to drive each transition and a two-step path involving new edges; assert resulting state and key side effects (e.g., lock released); enforce timeouts to catch dead-ends.
- **Technique from papers/stt:** State Testing (Ch. 10) – transition and tour coverage for state machines.
- **Difference vs. Existing Analyzers:** Line coverage doesn’t confirm correct multi-step state progressions; static checks don’t infer FSM intent.
- **Efficiency Notes:** Restrict FSM to states touched by the patch; transition-pair coverage keeps cases linear; parallelize with `-n auto`.
- **Example Bug Caught:** Error branch returns before setting `conn.state = CLOSED`; test driving CONNECTED → ERROR → CLOSE leaves state incorrect (3154).

### Rule 4: Definition–Use Execution
- **Bug Taxonomy Mapping:** 323x – processing initialization; 324x – cleanup; 4232 – dynamic initialization; 428x – access anomalies
- **Description:** For each variable/resource altered, execute every def–use chain, including early-return paths, to detect use-before-def and missing cleanup.
- **Why It Matters:** Conditional initialization or skipped teardown causes crashes, stale data, or leaks that evade structural analysis.
- **Implementation Outline:**  
  - Tooling: `pytest`, `hypothesis` (to steer branches), `coverage`/`pytest-cov` for path observation  
  - Steps: enumerate def/use sites of changed symbols; design tests that force each def–use path and each early exit; assert non-None/valid values and that cleanup hooks (close/free) run; run under coverage to ensure paths executed.
- **Technique from papers/stt:** Data Flow Testing (All-Defs/All-Uses, Ch. 7) – targets def–use anomalies directly.
- **Difference vs. Existing Analyzers:** Static analyzers flag limited anomalies but don’t guarantee runtime execution of each def–use chain; coverage alone lacks data-flow intent.
- **Efficiency Notes:** Scope to newly touched variables; typical 3–6 cases per symbol; reuse hypothesis examples to reduce manual enumeration.
- **Example Bug Caught:** Cache built only when `config.cache_enabled` is true but used unguarded later; test with flag false triggers `AttributeError` (428x).

### Rule 5: Resource Lifecycle Under Load
- **Bug Taxonomy Mapping:** 416x – static/dynamic resource mis-specification; 426x – runtime resource handling
- **Description:** Loop the patched operation to confirm allocations are paired with releases and caps are enforced, catching leaks introduced by retries or new buffers.
- **Why It Matters:** Leaks/exhaustion emerge only after repetition, degrading availability and stability.
- **Implementation Outline:**  
  - Tooling: `pytest`, `pytest-timeout`, `psutil` (fd/handle counts), `pytest-xdist` for sharding  
  - Steps: identify allocations/releases in diff (files/sockets/cursors/threads); run 50–200 iterations of the operation; assert handle counts remain stable and caps trigger expected errors; use timeouts to detect hangs.
- **Technique from papers/stt:** Storage/Resource Testing & Stress (Ch. 13 Implementation) – probes allocation/release balance under load.
- **Difference vs. Existing Analyzers:** Static checks don’t model lifecycles; coverage won’t expose cumulative leaks.
- **Efficiency Notes:** Bound iterations; monitor only relevant resources; shard iterations across workers to keep wall time low.
- **Example Bug Caught:** Retry loop adds HTTP call but forgets `resp.close()` inside loop; after ~80 iterations fds climb until failure (4262).

### Rule 6: Robust Exception and Message Paths
- **Bug Taxonomy Mapping:** 26xx – exception mishandling; 25xx – user messages/diagnostics
- **Description:** Force dependency failures and malformed inputs to verify specific exception types/status codes and message content introduced or modified by the patch.
- **Why It Matters:** Broad or missing handlers obscure root causes, mislead users, or trigger unintended retries.
- **Implementation Outline:**  
  - Tooling: `pytest`, `monkeypatch`, `pytest-httpx`/`responses` for fault injection, `pytest-timeout`  
  - Steps: list new/changed `raise`/`except`/logging sites; craft negative cases (missing file, timeout, bad payload); assert exact exception class/status and key message fields; verify logs include identifiers; enforce timeouts to catch swallowed hangs.
- **Technique from papers/stt:** Error Guessing & Robustness/Special-Value Testing (Ch. 3–4 heuristics) – targets invalid and failure conditions.
- **Difference vs. Existing Analyzers:** Linters ignore exception semantics; coverage can hit lines without checking handler correctness or messages.
- **Efficiency Notes:** Few targeted negatives per handler; use fakes/mocks to avoid heavy dependencies.
- **Example Bug Caught:** Patch collapses `FileNotFoundError` to generic `Exception`, returning 500 instead of 404; injected missing file shows wrong status (26xx/25xx).

### Rule 7: Transaction Order and Parameter Contracts
- **Bug Taxonomy Mapping:** 611x/612x – component invocation/parameter errors; 622x – external device/driver return misinterpretation
- **Description:** Validate the call sequence (init → use → teardown) and parameter ordering/defaults for interfaces touched, and ensure return/status codes are interpreted correctly.
- **Why It Matters:** Misordered calls or swapped parameters can succeed superficially but violate contracts, causing latent corruption or misreported success.
- **Implementation Outline:**  
  - Tooling: `pytest`, `pytest-subtests`, `pytest-mock`/`monkeypatch`, `pytest-cov`  
  - Steps: map intended transaction from docs or docstrings; add tests for (a) correct sequence with explicit param names, (b) one permuted/omitted step expecting failure, (c) return/status handling verification; integrate into CI stage for interface changes.
- **Technique from papers/stt:** Transaction Flow Testing (Ch. 5) – validates ordered control points and parameterized calls.
- **Difference vs. Existing Analyzers:** Static checks see signatures but not sequence; coverage doesn’t detect swapped parameters or misread statuses.
- **Efficiency Notes:** Three focused variants per interface change; stub external systems to keep fast.
- **Example Bug Caught:** New `connect(host, *, ssl=True)` called as `connect(True, host)` binds ssl incorrectly and disables TLS (6121).

### Rule 8: Structured Input and Conversion Validation
- **Bug Taxonomy Mapping:** 4214 – type transformation; 422x – dimension issues; 4285 – object boundary/structure access
- **Description:** Treat modified structured inputs as a grammar and test valid, near-miss, and malformed variants to verify parsing, type coercion, and bounds checks.
- **Why It Matters:** Renamed fields or assumed lengths lead to misparsed payloads or out-of-range access that unit happy-paths miss.
- **Implementation Outline:**  
  - Tooling: `pytest`, `hypothesis` (dict/list strategies), `jsonschema` (if available), `pytest-cov`  
  - Steps: extract changed fields/types/bounds from diff; define token/field expectations; generate cases: baseline valid, missing field, extra field, wrong type, empty vs. oversized collection, boundary index; assert parse results or explicit errors.
- **Technique from papers/stt:** Syntax Testing (Ch. 11) – model inputs as token sequences and probe malformed/near-miss cases.
- **Difference vs. Existing Analyzers:** Linters don’t check runtime schemas; coverage doesn’t stress malformed inputs or dimensional extremes.
- **Efficiency Notes:** Limit variants to fields touched by the patch; reuse hypothesis shrinking for quick failure isolation.
- **Example Bug Caught:** Field renamed `id` → `user_id`; payload `{ "id": 1 }` now becomes `None` silently, causing later crash (4214/4285).

### Rule 9: Concurrency and Interlock Order Checks
- **Bug Taxonomy Mapping:** 721x – interlocks/semaphores; 742x – response-time/order sensitivity
- **Description:** Stress the patched sections for ordering/race issues by exercising interleavings of lock acquisition/release and concurrent calls to ensure mutual exclusion and timely responses.
- **Why It Matters:** AI-generated patches may introduce or reorder locks/flags, causing deadlocks, missed wakeups, or stale reads under concurrency.
- **Implementation Outline:**  
  - Tooling: `pytest`, `pytest-xdist` (concurrent workers), `pytest-timeout`, `asyncio` or `threading`, `pytest-randomly` for schedule variation  
  - Steps: identify locks/flags or shared resources touched; craft concurrent tasks executing critical sections with varied start delays; assert no deadlock (timeout), correct ordering of state updates, and consistent results; repeat runs with randomized scheduling seeds.
- **Technique from papers/stt:** State/Transaction Flow Testing combined with Stress (Ch. 5 & 10) – exercising orderings and contention to expose interlock faults.
- **Difference vs. Existing Analyzers:** Static/dynamic analyzers are single-threaded; coverage ignores timing/order; linting won’t catch races.
- **Efficiency Notes:** Use short-lived tasks and capped iterations; rely on timeouts and parallel worker seeds instead of exhaustive interleavings.
- **Example Bug Caught:** Patch moves unlock after return in a fast path; concurrent calls deadlock when slow path holds the lock, detected by timed concurrent test (721x).
