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

# LAZY IMPORTS for fuzzer modules to avoid unnecessary dependencies
# These are only loaded when explicitly imported by name
def __getattr__(name):
    """Lazy import fuzzer modules to avoid hypothesis dependency when not needed."""
    if name == "CoverageGuidedDifferentialFuzzer":
        from verifier.dynamic_analyzers.coverage_guided_fuzzer import CoverageGuidedDifferentialFuzzer
        return CoverageGuidedDifferentialFuzzer
    elif name == "CoverageGuidedFuzzingResult":
        from verifier.dynamic_analyzers.coverage_guided_fuzzer import CoverageGuidedFuzzingResult
        return CoverageGuidedFuzzingResult
    elif name == "BehavioralDivergence":
        from verifier.dynamic_analyzers.coverage_guided_fuzzer import BehavioralDivergence
        return BehavioralDivergence
    elif name == "DivergenceType":
        from verifier.dynamic_analyzers.coverage_guided_fuzzer import DivergenceType
        return DivergenceType
    elif name == "ChangeClassification":
        from verifier.dynamic_analyzers.coverage_guided_fuzzer import ChangeClassification
        return ChangeClassification
    elif name == "run_coverage_guided_fuzzing":
        from verifier.dynamic_analyzers.coverage_guided_fuzzer import run_coverage_guided_fuzzing
        return run_coverage_guided_fuzzing
    elif name == "AtherisDifferentialFuzzer":
        from verifier.dynamic_analyzers.atheris_fuzzer import AtherisDifferentialFuzzer
        return AtherisDifferentialFuzzer
    elif name == "AtherisFuzzingResult":
        from verifier.dynamic_analyzers.atheris_fuzzer import AtherisFuzzingResult
        return AtherisFuzzingResult
    elif name == "DifferentialResult":
        from verifier.dynamic_analyzers.atheris_fuzzer import DifferentialResult
        return DifferentialResult
    elif name == "run_atheris_fuzzing":
        from verifier.dynamic_analyzers.atheris_fuzzer import run_atheris_fuzzing
        return run_atheris_fuzzing
    elif name == "test_patch_singularity":
        # Import the module (not a function - it's a .py file with multiple functions)
        import verifier.dynamic_analyzers.test_patch_singularity as test_patch_singularity
        return test_patch_singularity
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
