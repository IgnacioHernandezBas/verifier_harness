# Agentic Closed Loop (Prototype)

This module houses an experimental claim-test synthesis loop that builds on top
of the zero-shot pipeline. It keeps the existing extraction → generation →
verification workflow intact and layers an *agentic* controller on top:

1. **Planning** – reason about target modules/symbols, expected signatures, and
   inputs before touching the LLM.
2. **Guardrails** – import target modules, inspect call signatures, and bail out
   early if required preconditions are missing.
3. **Generation** – reuse the zero-shot `generate_pytest_for_claim`
   implementation, but enrich the prompt with the current plan, guardrail
   findings, and previous failure diagnoses.
4. **Verification** – call the existing `verify_instance` harness.
5. **Diagnostics** – classify failures (signature mismatch, import error,
   fixture missing, assertion failure, non-discriminative, etc.) and use that
   label to steer the next attempt.

Each attempt is recorded in a structured JSON log (plan, guardrail output,
generated code, verification outcome, failure classification) so runs can back
future few-shot prompts.

> ⚠️ This is a research prototype. It targets a single claim at a time and
> should not be considered a replacement for the zero-shot workflows.
