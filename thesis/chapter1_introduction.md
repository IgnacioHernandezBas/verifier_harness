# Chapter 1 — Introduction

## 1.1 Motivation

Software maintenance is one of the most resource-intensive activities in software engineering. Developers spend a significant portion of their working time not writing new functionality but understanding, debugging, and fixing existing code. The cost of software bugs is substantial: a defect found in production is estimated to be ten to one hundred times more expensive to fix than one caught during development [REF: Boehm & Basili, 2001]. The ability to automatically detect, localise, and repair defects has therefore long been a goal of the research community.

The emergence of large language models (LLMs) capable of understanding and generating code has dramatically accelerated this agenda. Models trained on vast corpora of source code — such as the GPT family, Code Llama, DeepSeek-Coder, and the Qwen-Coder series — can now produce plausible code patches for real-world bug reports with surprising frequency. The SWE-bench benchmark [REF: Jimenez et al., 2023] formalised this capability into a reproducible evaluation: given a GitHub issue and the repository at the state before a human fix was committed, can an LLM generate a patch that passes the repository's test suite? State-of-the-art agents now resolve a non-trivial fraction of these instances [REF: latest SWE-bench leaderboard], suggesting that LLM-assisted software repair is transitioning from academic curiosity to engineering reality.

However, the dominant evaluation protocol in SWE-bench — running the project's pre-existing test suite — carries a fundamental limitation: it conflates test passage with correctness. A patch that passes all existing tests may still introduce subtle regressions, fix the bug for the specific inputs exercised by the test suite while leaving the underlying defect present in other code paths, or resolve the symptom (the failing test) without addressing the root cause. In other words, the existing tests were written to capture known expected behaviour, not to characterise the specific behavioural change introduced by a given bug fix. A patch that is wrong but clever enough to satisfy those tests will appear indistinguishable from a correct one.

This creates a verification gap: we need tests that are specifically targeted at the behavioural claim made by a patch. A meaningful patch to a sorting function that previously returned unsorted output should be verified by a test that confirms the sorted property — not by whatever unrelated tests happen to live in `tests/test_utils.py`. More precisely, we want tests that are _discriminative_: they should fail on the buggy version of the code and pass on the patched version, thereby confirming that the patch does what it claims to do.

Writing such targeted tests manually for every patch under evaluation is impractical at scale. The natural question is therefore: can we automate this process using the same LLMs that generated the patch in the first place? And if we can, how do we ensure that the generated tests are trustworthy — that they are neither trivially passing (non-discriminative) nor testing implementation details that are irrelevant to the claim (overconstrained)?

## 1.2 Problem Statement

This work addresses the following core problem:

> **Given** a code patch (represented as a commit diff applied to a repository), automatically generate a behavioural test that (a) fails on the pre-patch (buggy) version of the code and (b) passes on the post-patch (fixed) version, thereby verifying that the patch correctly implements its intended behavioural change.

We decompose this problem into three sub-problems:

1. **Claim extraction**: From a commit diff and associated metadata (issue title, issue body, changed files), extract a precise natural-language claim about the behavioural change introduced by the patch. This claim serves as the specification that the test must verify.

2. **Test synthesis**: Given a claim, the repository context, and a set of structural constraints, generate a pytest test that operationalises the claim as an executable assertion.

3. **Discriminability verification**: Execute the generated test against both the buggy (pre-patch) and fixed (post-patch) versions of the repository. Classify the result and, if the test is not discriminative, generate targeted feedback to guide the next synthesis attempt.

The third sub-problem introduces a closed-loop structure: synthesis and verification alternate until a discriminative test is found or a maximum number of attempts is exhausted.

## 1.3 Contributions

This thesis makes the following contributions:

1. **A claim extraction pipeline** that uses an LLM to distil the behavioural intent of a commit diff into a structured natural-language specification. The pipeline produces grounded claims linked to specific symbols (functions, classes, methods) and the source excerpts that define them, providing verifiable context for downstream test generation.

2. **A multi-layer verification harness** combining static guardrail checks with dynamic execution-based verification. The static layer (signature checks, import checks, probe checks) intercepts structural errors before any test is executed, reducing wasted inference calls and providing more actionable feedback. The dynamic layer executes generated tests against both code variants and classifies the outcome.

3. **An agentic closed-loop test generation system** in which an LLM generates tests, a verifier classifies the result, a diagnostician produces structured feedback, and the LLM uses that feedback to improve the next attempt. The loop supports up to ten refinement iterations per claim.

4. **A taxonomy of failure modes** for LLM-generated discriminative tests, derived empirically from 219 verification runs across 19 SWE-bench instances and 11 model combinations. The taxonomy identifies four primary failure modes — OVERCONSTRAINED, NON_DISCRIMINATIVE, UNRESOLVED, and INVERTED — and quantifies their relative prevalence.

5. **An empirical evaluation** of the pipeline across four open-weight instruction-tuned LLMs (Qwen2.5-72B-Instruct, Qwen2.5-Coder-32B-Instruct, Meta-Llama-3.1-70B-Instruct, DeepSeek-Coder-V2-Lite) in all pairwise combinations of claim-extraction model and test-synthesis model, providing the first systematic multi-model study of this pipeline design.

## 1.4 Scope and Limitations

The system is designed and evaluated on a curated subset of SWE-bench instances drawn from seven Python repositories: `astropy`, `django`, `pylint-dev`, `psf/requests`, `pytest-dev`, `scikit-learn`, and `sympy`. These repositories were selected to represent a range of domains (scientific computing, web frameworks, linters, testing frameworks, mathematics libraries) and bug types.

The evaluation focuses on open-weight models deployable on a single multi-GPU node, motivated by the reproducibility requirements of academic research and the practical constraints of university compute clusters. Proprietary models (GPT-4, Claude, Gemini) are not evaluated, though the pipeline is model-agnostic in design.

The system targets Python repositories that use pytest as their testing framework. Extension to other languages or testing frameworks is left as future work.

## 1.5 Thesis Structure

The remainder of this thesis is organised as follows:

- **Chapter 2 (State of the Art)** reviews the literature on automated program repair, LLM-based code generation, test generation, and agentic AI systems, situating this work within the broader research landscape.
- **Chapter 3 (Problem Formulation)** provides a formal definition of discriminative test generation and introduces the key concepts used throughout the system.
- **Chapter 4 (System Architecture)** describes the full pipeline in detail: claim extraction, test planning, multi-layer verification, and the agentic feedback loop.
- **Chapter 5 (Implementation)** covers the engineering decisions, infrastructure choices, and model deployment strategy used to realise the system.
- **Chapter 6 (Experiments and Results)** presents the empirical evaluation: experimental setup, metrics, results by model combination, failure mode analysis, and ablation of the OVERCONSTRAINED feedback fix.
- **Chapter 7 (Conclusions and Future Work)** summarises the findings, reflects on the limitations, and outlines directions for future research.
