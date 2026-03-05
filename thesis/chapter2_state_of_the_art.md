# Chapter 2 — State of the Art

This chapter reviews the research areas most relevant to this work: automated program repair, LLM-based code generation and patching, automated test generation, and agentic AI systems for software engineering. We conclude by positioning our contribution relative to the existing literature.

---

## 2.1 Automated Program Repair

Automated program repair (APR) is the task of automatically generating a modification to a software artefact that causes it to satisfy a given correctness criterion, typically a test suite. Early APR approaches relied on genetic programming [REF: Le Goues et al., 2012 — GenProg], search-based techniques [REF: Weimer et al., 2009], or template-based strategies [REF: Kim et al., 2013 — PAR], exploiting common edit patterns observed in human-written patches.

A key limitation of test-suite-driven APR is _overfitting_: a generated patch may pass all provided tests while being semantically incorrect (e.g., by deleting the code under test or by special-casing test inputs). This problem, sometimes called the _patch correctness problem_ [REF: Smith et al., 2015; Qi et al., 2015], is directly relevant to this work: our system generates _tests_, not patches, but it faces the symmetric problem — a generated test may be formally valid (it does distinguish bug from fix) while being semantically fragile (it tests implementation detail rather than behavioural intent).

Semantic APR approaches attempted to address overfitting by incorporating formal specifications [REF: Nguyen et al., 2013 — SemFix], developer-written invariants [REF: Gopinath et al., 2011], or information from bug reports [REF: Liu et al., 2019 — AVATAR]. The recent shift to LLM-based APR has introduced a different and largely orthogonal source of semantic constraint: the natural language description of the intended fix.

## 2.2 LLM-Based Code Generation and Patch Synthesis

The introduction of Codex [REF: Chen et al., 2021] demonstrated that large language models trained on code could synthesise non-trivial programs from natural-language docstrings. Subsequent work applied similar models to the specific task of bug fixing, exploiting the observation that a commit diff and its associated commit message constitute a natural training signal for patch generation.

InCoder [REF: Fried et al., 2022], AlphaCode [REF: Li et al., 2022], and Code Llama [REF: Roziere et al., 2023] scaled this capability further. The Qwen-Coder series [REF: Hui et al., 2024] and DeepSeek-Coder [REF: Guo et al., 2024] brought high-quality open-weight models to academic and industrial practitioners. These models form the inference backbone of the pipeline evaluated in this thesis.

A critical development was the formalisation of patch quality through SWE-bench [REF: Jimenez et al., 2023]. SWE-bench collected 2,294 GitHub issues from twelve popular Python repositories, paired each with the human-authored fix commit and the repository's test suite. A proposed patch is deemed correct if and only if it passes all tests in the provided test suite, including a set of "fail-to-pass" tests that were explicitly failing before the fix. SWE-bench-Lite [REF: same source] and SWE-bench-Verified [REF: OpenAI, 2024] provide smaller, more tractable subsets. Our evaluation uses instances drawn from SWE-bench, making direct comparison of _patch_ generation performance straightforward.

SWE-bench revealed that even state-of-the-art LLMs — when used naively — resolve only a small fraction of instances (early baselines: below 5%). More recent agentic approaches such as SWE-agent [REF: Yang et al., 2024], AutoCodeRover [REF: Zhang et al., 2024], and Agentless [REF: Xia et al., 2024] have pushed resolution rates substantially higher by incorporating repository navigation, fault localisation, and multi-step planning. However, all of these systems are evaluated using the _existing_ test suite — the verification gap identified in Section 1.1 applies equally to all of them.

## 2.3 Automated Test Generation

Automated test generation has a long history in software engineering. Coverage-driven approaches such as EvoSuite [REF: Fraser & Arcuri, 2011] and Randoop [REF: Pacheco et al., 2007] optimise for structural coverage metrics (branch coverage, statement coverage) rather than for behavioural discrimination. While effective at maximising coverage of existing code, they are not designed to capture the _intent_ of a specific change.

Mutation testing [REF: DeMillo et al., 1978; Offutt & Untch, 2001] provides a framework for evaluating test quality based on the ability to distinguish a program from mutants (small syntactic modifications). A test suite that kills many mutants is considered to be high-quality. Our discriminative test generation task can be viewed as a special case of mutation testing where the "mutant" is the pre-patch (buggy) version of the code and the "ground truth" is the post-patch (fixed) version — except that in our setting, the bug is a real defect rather than an artificial syntactic perturbation.

The application of LLMs to test generation has produced a wave of recent work. ChatUniTest [REF: Chen et al., 2023], AthenaTest [REF: Tufano et al., 2021], and A3Test [REF: Alagarsamy et al., 2023] use sequence-to-sequence models or instruction-tuned LLMs to generate unit tests from method signatures and docstrings. TELPA [REF: 2024] extends this to test evolution. CoverAgent [REF: 2024] uses GPT-4 with coverage feedback to iteratively improve a test suite.

Most closely related to our work is the line of research on _differential_ or _regression_ test generation: generating tests that distinguish a new version of code from a reference version. Evosuite-regressions [REF: Fraser & Zeller, 2011], Sapienz [REF: Mao et al., 2016], and DiffTGen [REF: Tian & Nagappan, 2015] address related problems in classical settings. The LLM-based analogue — using natural language to guide the generation of discriminating tests for a specific change — is the focus of this work and remains underexplored in the literature.

The most closely adjacent recent work is EvoEval [REF: Xia et al., 2023] and the EvalPlus framework [REF: Liu et al., 2023], which curate harder test cases to evaluate LLM-generated code. However, these focus on evaluating the LLM's code quality rather than verifying a specific patch's behavioural change.

## 2.4 Specification Extraction and Behavioural Claims

A recurrent challenge in test generation is the absence of a machine-readable specification. Property-based testing frameworks such as Hypothesis [REF: MacIver et al., 2019] and QuickCheck [REF: Claessen & Hughes, 2000] require developers to manually write generators and properties. Specification mining [REF: Daikon, Ernst et al., 2001; Ammons et al., 2002] attempts to infer invariants dynamically, but the resulting specifications are execution-specific and may miss rare behaviours.

Recent work has explored using LLMs to generate specifications from natural-language descriptions. DocTer [REF: Xie et al., 2022] extracts argument constraints from API documentation. TitanFuzz [REF: Deng et al., 2023] and FuzzGPT [REF: Deng et al., 2023] use LLMs to guide fuzzing campaigns. Clover [REF: Ye et al., 2024] uses GPT-4 to generate formal contracts from docstrings for Dafny programs.

Our claim extraction component occupies a similar niche: we use an instruction-tuned LLM to extract a natural-language behavioural claim from a commit diff. The key distinction is that our claims are grounded — they reference specific symbols in the repository and are linked to source excerpts — which provides a verifiable bridge between the natural-language specification and the generated test code. This grounding mechanism draws inspiration from retrieval-augmented generation (RAG) [REF: Lewis et al., 2020] applied to code understanding [REF: Parvez et al., 2021].

## 2.5 Agentic AI Systems for Software Engineering

The term "agent" in AI has been used loosely, but in the software engineering context it typically refers to a system in which an LLM operates within a loop: it takes an action, observes a result, and uses the observation to decide its next action. This tool-use paradigm was popularised by ReAct [REF: Yao et al., 2022] and has since been instantiated in coding-specific agents including SWE-agent [REF: Yang et al., 2024], which provides a structured shell environment to GPT-4 for the purpose of resolving GitHub issues.

The closed-loop structure of our test generation system follows this paradigm. The LLM generates a test; the verifier executes it against both code variants; the diagnostician classifies the failure; the feedback is incorporated into the next generation prompt. This is structurally identical to the generate-and-debug pattern studied in Self-Debug [REF: Chen et al., 2023], Reflexion [REF: Shinn et al., 2023], and LATS [REF: Zhou et al., 2023], adapted to the specific task of discriminative test generation.

A key contribution of our work relative to these frameworks is the _multi-layer_ structure: the static guardrail layer intercepts structural errors (import failures, signature mismatches) _before_ the expensive dynamic execution step, functioning as a fast-fail mechanism. This design choice is motivated by the observation that many early failures in test generation are due to syntactic or import-level errors that can be detected without running Docker containers. The feedback from guardrails is more precise than execution feedback because the error is intercepted closer to its source.

A related design is the use of structured feedback — rather than raw stack traces — to guide the LLM's next attempt. LLM-based debuggers [REF: Zhong et al., 2024] have shown that structured, natural-language explanations of errors are more effective than raw error output for guiding code repair. Our diagnosis module follows this principle, converting raw test run results into labelled diagnoses (OVERCONSTRAINED, NON_DISCRIMINATIVE, etc.) with targeted remediation guidance.

## 2.6 Evaluation of Patch Correctness

Beyond SWE-bench, several frameworks have been proposed for evaluating the correctness of LLM-generated patches. LIBRO [REF: Kang et al., 2023] uses LLM-generated test cases to validate patches for Defects4J instances. FixEval [REF: Haque et al., 2022] evaluates patches on competitive programming problems using hidden test cases. These approaches rely on pre-existing or author-generated test suites and do not address the problem of generating claim-targeted tests.

RepoCoder [REF: Zhang et al., 2023] and Agentless [REF: Xia et al., 2024] incorporate test-suite execution as part of their patch selection strategy (choosing the patch that passes the most tests), but this remains bounded by the quality and coverage of the existing test suite.

The closest evaluation methodology to ours is found in the differential testing literature. DECKARD [REF: Jiang et al., 2007] and related clone detection tools produce tests that distinguish functionally similar but distinct code fragments. Shen et al. [REF: 2022] propose using mutation testing as a signal for patch ranking in APR. Our system makes this intuition concrete and LLM-native: we generate tests not to rank patches but to verify a single specific patch against its behavioural claim.

## 2.7 Summary and Positioning

Table 2.1 positions this work relative to the most closely related systems.

| System | Task | Test generation | Claim-grounded | Closed-loop | Multi-model |
|---|---|---|---|---|---|
| SWE-agent [Yang et al., 2024] | Patch generation | ✗ | ✗ | ✓ | ✗ |
| Agentless [Xia et al., 2024] | Patch generation | ✗ | ✗ | ✗ | ✗ |
| ChatUniTest [Chen et al., 2023] | Unit test gen | ✓ | ✗ | ✗ | ✗ |
| LIBRO [Kang et al., 2023] | Patch validation | ✓ | ✗ | ✗ | ✗ |
| CoverAgent [2024] | Test improvement | ✓ | ✗ | ✓ | ✗ |
| Self-Debug [Chen et al., 2023] | Code repair | ✗ | ✗ | ✓ | ✗ |
| **This work** | **Discriminative test gen** | **✓** | **✓** | **✓** | **✓** |

The key differentiators of this work are (1) the explicit focus on _discriminative_ tests anchored to a natural-language behavioural claim, (2) the multi-layer verification architecture that combines static guardrails with dynamic execution-based feedback, and (3) the systematic multi-model evaluation that decouples the claim-extraction and test-synthesis roles.
