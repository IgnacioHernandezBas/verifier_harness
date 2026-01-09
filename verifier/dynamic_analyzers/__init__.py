"""Dynamic analysis and fuzzing modules."""

# Modules contain functions and classes
# Import directly when needed:
# from verifier.dynamic_analyzers import patch_analyzer, test_patch_singularity

# Podman executor for SWE-bench test execution
from verifier.dynamic_analyzers.podman_executor import (
    PodmanTestExecutor,
    IntegratedTestRunner,
    TestType,
    ExecutionResult
)

# Coverage-guided differential fuzzer - Hypothesis-based (simple, in-process)
from verifier.dynamic_analyzers.coverage_guided_fuzzer import (
    CoverageGuidedDifferentialFuzzer,
    CoverageGuidedFuzzingResult,
    BehavioralDivergence,
    DivergenceType,
    ChangeClassification,
    run_coverage_guided_fuzzing,
)

# Atheris-based coverage-guided fuzzer (CORE NOVELTY - container-based, true coverage-guided)
from verifier.dynamic_analyzers.atheris_fuzzer import (
    AtherisDifferentialFuzzer,
    AtherisFuzzingResult,
    DifferentialResult,
    run_atheris_fuzzing,
)
