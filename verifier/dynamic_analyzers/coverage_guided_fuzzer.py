"""
Coverage-Guided Differential Fuzzer for Patch Verification.

This is the CORE NOVELTY of the verification harness:
- Coverage-guided input generation targeting changed code
- Differential testing (original vs patched) with behavioral classification
- Semantic difference classification (expected fix vs suspicious regression)

Key differentiators from existing work:
- vs PATCH-SIM: Coverage-guided (not random), multi-level comparison
- vs Opad: Detects logic bugs (not just crashes), classifies changes
- vs FuzzRepair: Verifies external patches (not generates patches)
- vs UTBoost: Deterministic (not LLM-dependent)
"""

import ast
import sys
import time
import json
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import traceback

# Try to import Atheris for coverage-guided fuzzing
try:
    import atheris
    ATHERIS_AVAILABLE = True
except ImportError:
    ATHERIS_AVAILABLE = False

# Hypothesis for structured input generation
from hypothesis import given, strategies as st, settings, Phase, Verbosity
from hypothesis.database import InMemoryExampleDatabase

import coverage


class DivergenceType(Enum):
    """Classification of behavioral divergences."""
    EXPECTED_FIX = "expected_fix"           # Behavior change matches issue description
    EXPECTED_SIDE_EFFECT = "expected_side_effect"  # Reasonable consequence of fix
    SUSPICIOUS = "suspicious"               # Unexplained behavior change
    REGRESSION = "regression"               # Previously working case now fails
    PERFORMANCE = "performance_regression"  # Significant slowdown


class ChangeClassification(Enum):
    """Classification of whether a behavioral change is expected."""
    EXPECTED = "expected"      # Change aligns with patch purpose
    SUSPICIOUS = "suspicious"  # Change not explained by patch
    REGRESSION = "regression"  # Clearly unintended breakage


@dataclass
class ExecutionResult:
    """Result of executing code with a given input."""
    result: Any = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    execution_time_ms: float = 0.0
    covered_lines: Set[int] = field(default_factory=set)
    stdout: str = ""
    stderr: str = ""

    def __eq__(self, other):
        if not isinstance(other, ExecutionResult):
            return False
        # Compare results, handling None and exceptions
        if self.exception_type != other.exception_type:
            return False
        if self.exception_type is None:
            return self.result == other.result
        return True  # Both raised same exception type


@dataclass
class BehavioralDivergence:
    """
    Record of a behavioral difference between original and patched code.

    Enhanced from the basic version to include:
    - Classification of divergence type
    - Coverage information
    - Confidence scoring
    """
    input_data: Dict[str, Any]
    original: ExecutionResult
    patched: ExecutionResult
    divergence_type: DivergenceType
    classification: ChangeClassification
    confidence: float  # 0.0 to 1.0 - how confident we are in the classification
    explanation: str
    changed_lines_hit: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return {
            'input_data': self.input_data,
            'original_result': str(self.original.result),
            'original_exception': self.original.exception_type,
            'patched_result': str(self.patched.result),
            'patched_exception': self.patched.exception_type,
            'divergence_type': self.divergence_type.value,
            'classification': self.classification.value,
            'confidence': self.confidence,
            'explanation': self.explanation,
            'changed_lines_hit': self.changed_lines_hit,
        }


@dataclass
class FuzzingCorpusEntry:
    """An input in the fuzzing corpus with its coverage information."""
    input_data: Dict[str, Any]
    covered_lines: Set[int]
    covered_changed_lines: Set[int]  # Intersection with changed lines
    is_interesting: bool  # Did this input discover new coverage?
    generation: int  # Which fuzzing iteration found this
    parent_hash: Optional[str] = None  # Hash of parent input (for mutation tracking)

    def input_hash(self) -> str:
        """Hash the input for deduplication."""
        return hashlib.md5(json.dumps(self.input_data, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass
class CoverageGuidedFuzzingResult:
    """Complete result of coverage-guided differential fuzzing."""
    # Core metrics
    total_inputs_generated: int
    unique_inputs_tested: int
    changed_line_coverage: float  # 0.0 to 1.0
    total_changed_lines: int
    covered_changed_lines: int

    # Divergences found
    divergences: List[BehavioralDivergence]
    expected_divergences: int
    suspicious_divergences: int
    regressions: int

    # Corpus information
    corpus_size: int
    interesting_inputs: int  # Inputs that discovered new coverage

    # Timing
    fuzzing_duration_seconds: float

    # Verdict
    verdict: str  # "PASS", "WARNING", "FAIL"
    verdict_explanation: str

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return {
            'total_inputs_generated': self.total_inputs_generated,
            'unique_inputs_tested': self.unique_inputs_tested,
            'changed_line_coverage': self.changed_line_coverage,
            'total_changed_lines': self.total_changed_lines,
            'covered_changed_lines': self.covered_changed_lines,
            'divergences': [d.to_dict() for d in self.divergences],
            'expected_divergences': self.expected_divergences,
            'suspicious_divergences': self.suspicious_divergences,
            'regressions': self.regressions,
            'corpus_size': self.corpus_size,
            'interesting_inputs': self.interesting_inputs,
            'fuzzing_duration_seconds': self.fuzzing_duration_seconds,
            'verdict': self.verdict,
            'verdict_explanation': self.verdict_explanation,
        }


class CoverageGuidedDifferentialFuzzer:
    """
    Coverage-guided differential fuzzer for patch verification.

    This is the MAIN NOVELTY:
    1. Uses coverage feedback to guide input generation toward changed code
    2. Compares original vs patched behavior (differential testing)
    3. Classifies behavioral differences as expected/suspicious/regression

    Architecture:
    - Maintains a corpus of interesting inputs (those that hit new coverage)
    - Mutates corpus entries to explore new paths
    - Uses Hypothesis for structured input generation
    - Tracks coverage specifically for changed lines
    """

    def __init__(
        self,
        original_code: str,
        patched_code: str,
        changed_lines: List[int],
        function_name: str,
        issue_description: str = "",
        patch_description: str = "",
        class_name: Optional[str] = None,
    ):
        """
        Initialize the coverage-guided differential fuzzer.

        Args:
            original_code: Python code before patch
            patched_code: Python code after patch
            changed_lines: Line numbers that were modified
            function_name: Name of function to test
            issue_description: GitHub issue description (for classification)
            patch_description: Commit message or PR description
            class_name: Class name if testing a method
        """
        self.original_code = original_code
        self.patched_code = patched_code
        self.changed_lines = set(changed_lines)
        self.function_name = function_name
        self.issue_description = issue_description.lower()
        self.patch_description = patch_description.lower()
        self.class_name = class_name

        # Coverage tracking
        self.global_covered_lines: Set[int] = set()
        self.global_covered_changed_lines: Set[int] = set()

        # Corpus of interesting inputs
        self.corpus: List[FuzzingCorpusEntry] = []
        self.seen_input_hashes: Set[str] = set()

        # Divergences found
        self.divergences: List[BehavioralDivergence] = []

        # Statistics
        self.total_inputs = 0
        self.generation = 0

        # Extract function signature for strategy generation
        self.function_signature = self._extract_signature(patched_code, function_name)

    def _extract_signature(self, code: str, func_name: str) -> Dict[str, Any]:
        """Extract function signature for intelligent strategy generation."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == func_name:
                        params = []
                        type_hints = {}
                        defaults = {}

                        for arg in node.args.args:
                            if arg.arg not in ('self', 'cls'):
                                params.append(arg.arg)
                                if arg.annotation:
                                    try:
                                        type_hints[arg.arg] = ast.unparse(arg.annotation)
                                    except:
                                        pass

                        # Extract defaults
                        num_defaults = len(node.args.defaults)
                        for i, default in enumerate(node.args.defaults):
                            param_idx = len(params) - num_defaults + i
                            if 0 <= param_idx < len(params):
                                try:
                                    defaults[params[param_idx]] = ast.literal_eval(default)
                                except:
                                    pass

                        return {
                            'params': params,
                            'type_hints': type_hints,
                            'defaults': defaults,
                            'has_args': node.args.vararg is not None,
                            'has_kwargs': node.args.kwarg is not None,
                        }
        except SyntaxError:
            pass
        return {'params': [], 'type_hints': {}, 'defaults': {}, 'has_args': False, 'has_kwargs': False}

    def _execute_with_coverage(
        self,
        code: str,
        func_name: str,
        input_data: Dict[str, Any],
        timeout_seconds: float = 5.0
    ) -> ExecutionResult:
        """
        Execute function with coverage tracking.

        Args:
            code: Python code containing the function
            func_name: Name of function to call
            input_data: Arguments to pass to function
            timeout_seconds: Maximum execution time

        Returns:
            ExecutionResult with result/exception and coverage info
        """
        cov = coverage.Coverage(branch=True)
        result = ExecutionResult()

        start_time = time.time()

        try:
            # Load the function
            namespace = {'__name__': '__main__'}
            exec(code, namespace)

            func = namespace.get(func_name)
            if func is None and self.class_name:
                # Try to get method from class
                cls = namespace.get(self.class_name)
                if cls:
                    instance = cls(**{k: v for k, v in input_data.items()
                                     if k in self.function_signature.get('params', [])})
                    func = getattr(instance, func_name, None)

            if func is None:
                result.exception_type = "FunctionNotFound"
                result.exception_message = f"Function {func_name} not found"
                return result

            # Execute with coverage
            cov.start()
            try:
                if self.class_name and func_name == '__init__':
                    # For __init__, create instance
                    cls = namespace.get(self.class_name)
                    result.result = cls(**input_data)
                else:
                    result.result = func(**input_data)
            finally:
                cov.stop()

            # Extract covered lines
            cov_data = cov.get_data()
            for filename in cov_data.measured_files():
                lines = cov_data.lines(filename)
                if lines:
                    result.covered_lines.update(lines)

        except Exception as e:
            result.exception_type = type(e).__name__
            result.exception_message = str(e)
            # Still try to get coverage
            try:
                cov.stop()
                cov_data = cov.get_data()
                for filename in cov_data.measured_files():
                    lines = cov_data.lines(filename)
                    if lines:
                        result.covered_lines.update(lines)
            except:
                pass

        result.execution_time_ms = (time.time() - start_time) * 1000
        return result

    def _classify_divergence(
        self,
        input_data: Dict[str, Any],
        original: ExecutionResult,
        patched: ExecutionResult,
    ) -> Tuple[DivergenceType, ChangeClassification, float, str]:
        """
        Classify a behavioral divergence.

        This is KEY for distinguishing expected fixes from regressions.

        Returns:
            (divergence_type, classification, confidence, explanation)
        """
        # Determine basic divergence type
        if original.exception_type != patched.exception_type:
            if original.exception_type and not patched.exception_type:
                # Original raised, patched doesn't - likely a fix
                divergence_type = DivergenceType.EXPECTED_FIX

                # Check if this exception type is mentioned in issue
                exc_lower = original.exception_type.lower()
                if exc_lower in self.issue_description or exc_lower in self.patch_description:
                    classification = ChangeClassification.EXPECTED
                    confidence = 0.9
                    explanation = f"Patch fixes {original.exception_type} (mentioned in issue)"
                else:
                    classification = ChangeClassification.SUSPICIOUS
                    confidence = 0.6
                    explanation = f"Patch prevents {original.exception_type} but not mentioned in issue"

            elif not original.exception_type and patched.exception_type:
                # Original worked, patched raises - regression!
                divergence_type = DivergenceType.REGRESSION
                classification = ChangeClassification.REGRESSION
                confidence = 0.95
                explanation = f"REGRESSION: Input that worked now raises {patched.exception_type}"

            else:
                # Both raise but different exceptions
                divergence_type = DivergenceType.SUSPICIOUS
                classification = ChangeClassification.SUSPICIOUS
                confidence = 0.7
                explanation = f"Exception type changed: {original.exception_type} -> {patched.exception_type}"

        elif original.result != patched.result:
            # Results differ
            divergence_type = DivergenceType.EXPECTED_SIDE_EFFECT

            # Try to determine if this is expected
            # Check for common fix patterns in descriptions
            fix_keywords = ['fix', 'correct', 'handle', 'return', 'should', 'now']
            if any(kw in self.patch_description for kw in fix_keywords):
                classification = ChangeClassification.EXPECTED
                confidence = 0.7
                explanation = f"Result changed: {original.result} -> {patched.result} (patch mentions fix)"
            else:
                classification = ChangeClassification.SUSPICIOUS
                confidence = 0.5
                explanation = f"Result changed: {original.result} -> {patched.result} (not explained in patch)"

        else:
            # No divergence (shouldn't reach here)
            divergence_type = DivergenceType.EXPECTED_SIDE_EFFECT
            classification = ChangeClassification.EXPECTED
            confidence = 1.0
            explanation = "No behavioral difference"

        # Check for performance regression
        if patched.execution_time_ms > original.execution_time_ms * 10:  # 10x slower
            if divergence_type != DivergenceType.REGRESSION:
                divergence_type = DivergenceType.PERFORMANCE
                if classification != ChangeClassification.REGRESSION:
                    classification = ChangeClassification.SUSPICIOUS
                confidence = min(confidence, 0.8)
                explanation += f" | Performance: {original.execution_time_ms:.1f}ms -> {patched.execution_time_ms:.1f}ms"

        return divergence_type, classification, confidence, explanation

    def _is_interesting_input(self, covered_lines: Set[int]) -> bool:
        """
        Determine if an input is "interesting" (discovers new coverage).

        An input is interesting if it covers changed lines we haven't seen before.
        """
        covered_changed = covered_lines & self.changed_lines
        new_coverage = covered_changed - self.global_covered_changed_lines
        return len(new_coverage) > 0

    def _add_to_corpus(self, input_data: Dict[str, Any], covered_lines: Set[int], parent_hash: Optional[str] = None):
        """Add an interesting input to the corpus."""
        covered_changed = covered_lines & self.changed_lines

        entry = FuzzingCorpusEntry(
            input_data=input_data,
            covered_lines=covered_lines,
            covered_changed_lines=covered_changed,
            is_interesting=True,
            generation=self.generation,
            parent_hash=parent_hash,
        )

        input_hash = entry.input_hash()
        if input_hash not in self.seen_input_hashes:
            self.corpus.append(entry)
            self.seen_input_hashes.add(input_hash)
            self.global_covered_lines.update(covered_lines)
            self.global_covered_changed_lines.update(covered_changed)
            return True
        return False

    def _generate_strategy_for_param(self, param_name: str) -> st.SearchStrategy:
        """
        Generate a Hypothesis strategy for a parameter.

        Uses type hints and defaults when available, falls back to heuristics.
        """
        type_hints = self.function_signature.get('type_hints', {})
        defaults = self.function_signature.get('defaults', {})

        # Check type hint
        hint = type_hints.get(param_name, '').lower()
        default = defaults.get(param_name)

        # Type-hint based strategies
        if 'int' in hint:
            if 'optional' in hint or default is None:
                return st.one_of(st.none(), st.integers(min_value=-1000, max_value=1000))
            return st.integers(min_value=-1000, max_value=1000)
        elif 'float' in hint:
            if 'optional' in hint or default is None:
                return st.one_of(st.none(), st.floats(min_value=-1000, max_value=1000, allow_nan=False))
            return st.floats(min_value=-1000, max_value=1000, allow_nan=False)
        elif 'str' in hint:
            return st.text(min_size=0, max_size=50)
        elif 'bool' in hint:
            return st.booleans()
        elif 'list' in hint:
            return st.lists(st.integers(), min_size=0, max_size=20)
        elif 'dict' in hint:
            return st.dictionaries(st.text(min_size=1, max_size=10), st.integers())

        # Default-based strategies
        if default is not None:
            if isinstance(default, bool):
                return st.booleans()
            elif isinstance(default, int):
                return st.integers(min_value=default-100, max_value=default+100)
            elif isinstance(default, float):
                return st.floats(min_value=max(-1000, default-100), max_value=min(1000, default+100), allow_nan=False)
            elif isinstance(default, str):
                return st.text(min_size=0, max_size=50)
            elif isinstance(default, (list, tuple)):
                return st.lists(st.integers(), min_size=0, max_size=20)

        # Name-based heuristics
        param_lower = param_name.lower()
        if any(x in param_lower for x in ['size', 'count', 'num', 'n_']):
            return st.integers(min_value=0, max_value=100)
        elif any(x in param_lower for x in ['flag', 'enable', 'disable', 'verbose', 'debug']):
            return st.booleans()
        elif any(x in param_lower for x in ['name', 'key', 'id', 'path']):
            return st.text(min_size=0, max_size=30)
        elif any(x in param_lower for x in ['items', 'list', 'values', 'data']):
            return st.lists(st.integers(), min_size=0, max_size=20)

        # Generic fallback - mix of common types
        return st.one_of(
            st.none(),
            st.booleans(),
            st.integers(min_value=-100, max_value=100),
            st.text(min_size=0, max_size=20),
            st.lists(st.integers(), min_size=0, max_size=10),
        )

    def _mutate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mutate an existing input to explore nearby input space.

        Mutations:
        - Numeric: add/subtract small amounts, negate, set to boundary values
        - String: add/remove chars, swap chars
        - List: add/remove elements, shuffle
        - Bool: flip
        """
        import random

        mutated = input_data.copy()

        if not mutated:
            return mutated

        # Pick a random parameter to mutate
        param = random.choice(list(mutated.keys()))
        value = mutated[param]

        if isinstance(value, bool):
            mutated[param] = not value
        elif isinstance(value, int):
            mutations = [
                value + 1,
                value - 1,
                value * 2,
                value // 2 if value != 0 else 0,
                -value,
                0,
                1,
                -1,
                value + random.randint(-10, 10),
            ]
            mutated[param] = random.choice(mutations)
        elif isinstance(value, float):
            mutations = [
                value + 0.1,
                value - 0.1,
                value * 2,
                value / 2 if value != 0 else 0.0,
                -value,
                0.0,
                1.0,
                -1.0,
                value + random.uniform(-1, 1),
            ]
            mutated[param] = random.choice(mutations)
        elif isinstance(value, str):
            if len(value) == 0:
                mutated[param] = "a"
            else:
                mutations = [
                    value + "x",
                    value[:-1] if len(value) > 1 else "",
                    value.upper(),
                    value.lower(),
                    "",
                    value[::-1],
                ]
                mutated[param] = random.choice(mutations)
        elif isinstance(value, list):
            if len(value) == 0:
                mutated[param] = [0]
            else:
                mutations = [
                    value + [random.randint(-10, 10)],
                    value[:-1],
                    value[::-1],
                    [],
                    [value[0]] if value else [],
                ]
                mutated[param] = random.choice(mutations)
        elif value is None:
            # Try replacing None with a concrete value
            mutated[param] = random.choice([0, 1, "", [], True, False])

        return mutated

    def fuzz(
        self,
        max_iterations: int = 10000,
        timeout_seconds: float = 300.0,
        coverage_target: float = 0.9,
    ) -> CoverageGuidedFuzzingResult:
        """
        Run coverage-guided differential fuzzing.

        Args:
            max_iterations: Maximum number of inputs to generate
            timeout_seconds: Maximum fuzzing time
            coverage_target: Stop early if this coverage of changed lines is reached

        Returns:
            CoverageGuidedFuzzingResult with all findings
        """
        start_time = time.time()
        params = self.function_signature.get('params', [])

        if not params and self.function_name != '__init__':
            # No parameters to fuzz
            return CoverageGuidedFuzzingResult(
                total_inputs_generated=0,
                unique_inputs_tested=0,
                changed_line_coverage=0.0,
                total_changed_lines=len(self.changed_lines),
                covered_changed_lines=0,
                divergences=[],
                expected_divergences=0,
                suspicious_divergences=0,
                regressions=0,
                corpus_size=0,
                interesting_inputs=0,
                fuzzing_duration_seconds=0.0,
                verdict="SKIP",
                verdict_explanation="No parameters to fuzz",
            )

        # Build composite strategy for all parameters
        strategies = {param: self._generate_strategy_for_param(param) for param in params}

        # Phase 1: Initial exploration with Hypothesis
        print(f"  Phase 1: Initial exploration with Hypothesis...")

        @given(st.fixed_dictionaries(strategies))
        @settings(
            max_examples=min(1000, max_iterations // 2),
            deadline=None,
            database=InMemoryExampleDatabase(),
            phases=[Phase.generate],
            verbosity=Verbosity.quiet,
        )
        def explore_input_space(input_data):
            nonlocal self
            self.total_inputs += 1

            # Execute on both versions
            original_result = self._execute_with_coverage(
                self.original_code, self.function_name, input_data
            )
            patched_result = self._execute_with_coverage(
                self.patched_code, self.function_name, input_data
            )

            # Check if this input hits new coverage
            combined_coverage = original_result.covered_lines | patched_result.covered_lines
            if self._is_interesting_input(combined_coverage):
                self._add_to_corpus(input_data, combined_coverage)

            # Check for divergence
            if original_result != patched_result:
                div_type, classification, confidence, explanation = self._classify_divergence(
                    input_data, original_result, patched_result
                )

                divergence = BehavioralDivergence(
                    input_data=input_data,
                    original=original_result,
                    patched=patched_result,
                    divergence_type=div_type,
                    classification=classification,
                    confidence=confidence,
                    explanation=explanation,
                    changed_lines_hit=list(combined_coverage & self.changed_lines),
                )
                self.divergences.append(divergence)

        try:
            explore_input_space()
        except Exception as e:
            print(f"  Warning: Hypothesis exploration error: {e}")

        print(f"  After Phase 1: {len(self.corpus)} corpus entries, {len(self.divergences)} divergences")

        # Phase 2: Coverage-guided mutation
        print(f"  Phase 2: Coverage-guided mutation...")
        self.generation = 1

        while self.total_inputs < max_iterations:
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                print(f"  Timeout reached after {self.total_inputs} inputs")
                break

            # Check coverage target
            current_coverage = (
                len(self.global_covered_changed_lines) / len(self.changed_lines)
                if self.changed_lines else 1.0
            )
            if current_coverage >= coverage_target:
                print(f"  Coverage target {coverage_target:.0%} reached")
                break

            # Select input to mutate (prefer inputs with high changed-line coverage)
            if self.corpus:
                # Weighted selection by changed line coverage
                weights = [len(e.covered_changed_lines) + 1 for e in self.corpus]
                import random
                parent = random.choices(self.corpus, weights=weights, k=1)[0]
                input_data = self._mutate_input(parent.input_data)
                parent_hash = parent.input_hash()
            else:
                # No corpus yet, generate random
                input_data = {param: self._generate_strategy_for_param(param).example()
                             for param in params}
                parent_hash = None

            self.total_inputs += 1

            # Execute on both versions
            original_result = self._execute_with_coverage(
                self.original_code, self.function_name, input_data
            )
            patched_result = self._execute_with_coverage(
                self.patched_code, self.function_name, input_data
            )

            # Check coverage
            combined_coverage = original_result.covered_lines | patched_result.covered_lines
            if self._is_interesting_input(combined_coverage):
                self._add_to_corpus(input_data, combined_coverage, parent_hash)
                self.generation += 1

            # Check divergence
            if original_result != patched_result:
                div_type, classification, confidence, explanation = self._classify_divergence(
                    input_data, original_result, patched_result
                )

                divergence = BehavioralDivergence(
                    input_data=input_data,
                    original=original_result,
                    patched=patched_result,
                    divergence_type=div_type,
                    classification=classification,
                    confidence=confidence,
                    explanation=explanation,
                    changed_lines_hit=list(combined_coverage & self.changed_lines),
                )
                self.divergences.append(divergence)

            # Progress update
            if self.total_inputs % 1000 == 0:
                print(f"    {self.total_inputs} inputs, {len(self.corpus)} corpus, "
                      f"{current_coverage:.1%} coverage, {len(self.divergences)} divergences")

        # Compute final results
        elapsed = time.time() - start_time
        final_coverage = (
            len(self.global_covered_changed_lines) / len(self.changed_lines)
            if self.changed_lines else 1.0
        )

        expected = sum(1 for d in self.divergences if d.classification == ChangeClassification.EXPECTED)
        suspicious = sum(1 for d in self.divergences if d.classification == ChangeClassification.SUSPICIOUS)
        regressions = sum(1 for d in self.divergences if d.classification == ChangeClassification.REGRESSION)

        # Determine verdict
        if regressions > 0:
            verdict = "FAIL"
            verdict_explanation = f"Found {regressions} regression(s) - previously working inputs now fail"
        elif suspicious > 5:
            verdict = "WARNING"
            verdict_explanation = f"Found {suspicious} suspicious behavioral changes not explained by patch"
        elif final_coverage < 0.5:
            verdict = "WARNING"
            verdict_explanation = f"Low coverage ({final_coverage:.0%}) of changed lines - may have missed issues"
        else:
            verdict = "PASS"
            verdict_explanation = f"No regressions found, {expected} expected changes, {final_coverage:.0%} coverage"

        return CoverageGuidedFuzzingResult(
            total_inputs_generated=self.total_inputs,
            unique_inputs_tested=len(self.seen_input_hashes),
            changed_line_coverage=final_coverage,
            total_changed_lines=len(self.changed_lines),
            covered_changed_lines=len(self.global_covered_changed_lines),
            divergences=self.divergences,
            expected_divergences=expected,
            suspicious_divergences=suspicious,
            regressions=regressions,
            corpus_size=len(self.corpus),
            interesting_inputs=sum(1 for e in self.corpus if e.is_interesting),
            fuzzing_duration_seconds=elapsed,
            verdict=verdict,
            verdict_explanation=verdict_explanation,
        )

    def generate_report(self, result: CoverageGuidedFuzzingResult) -> str:
        """Generate a human-readable report of fuzzing results."""
        lines = [
            "=" * 80,
            "COVERAGE-GUIDED DIFFERENTIAL FUZZING REPORT",
            "=" * 80,
            "",
            f"Function: {self.class_name + '.' if self.class_name else ''}{self.function_name}",
            f"Changed Lines: {sorted(self.changed_lines)}",
            "",
            "--- COVERAGE ---",
            f"Changed Line Coverage: {result.changed_line_coverage:.1%} ({result.covered_changed_lines}/{result.total_changed_lines})",
            f"Lines Covered: {sorted(self.global_covered_changed_lines)}",
            f"Lines NOT Covered: {sorted(self.changed_lines - self.global_covered_changed_lines)}",
            "",
            "--- FUZZING STATS ---",
            f"Total Inputs: {result.total_inputs_generated}",
            f"Unique Inputs: {result.unique_inputs_tested}",
            f"Corpus Size: {result.corpus_size}",
            f"Interesting Inputs: {result.interesting_inputs}",
            f"Duration: {result.fuzzing_duration_seconds:.1f}s",
            "",
            "--- DIVERGENCES ---",
            f"Total Divergences: {len(result.divergences)}",
            f"  Expected (fixes): {result.expected_divergences}",
            f"  Suspicious: {result.suspicious_divergences}",
            f"  REGRESSIONS: {result.regressions}",
            "",
        ]

        # Detail divergences
        if result.divergences:
            lines.append("--- DIVERGENCE DETAILS ---")
            for i, div in enumerate(result.divergences[:20], 1):  # Limit to 20
                lines.extend([
                    f"",
                    f"[{i}] {div.classification.value.upper()} - {div.divergence_type.value}",
                    f"    Input: {div.input_data}",
                    f"    Original: {div.original.exception_type or div.original.result}",
                    f"    Patched:  {div.patched.exception_type or div.patched.result}",
                    f"    Explanation: {div.explanation}",
                    f"    Changed lines hit: {div.changed_lines_hit}",
                    f"    Confidence: {div.confidence:.0%}",
                ])

            if len(result.divergences) > 20:
                lines.append(f"... and {len(result.divergences) - 20} more divergences")

        lines.extend([
            "",
            "--- VERDICT ---",
            f"  {result.verdict}: {result.verdict_explanation}",
            "",
            "=" * 80,
        ])

        return "\n".join(lines)


# Convenience function for integration
def run_coverage_guided_fuzzing(
    original_code: str,
    patched_code: str,
    changed_lines: List[int],
    function_name: str,
    class_name: Optional[str] = None,
    issue_description: str = "",
    patch_description: str = "",
    max_iterations: int = 10000,
    timeout_seconds: float = 300.0,
) -> CoverageGuidedFuzzingResult:
    """
    Run coverage-guided differential fuzzing on a patch.

    This is the main entry point for the novel fuzzing approach.

    Args:
        original_code: Code before patch
        patched_code: Code after patch
        changed_lines: Line numbers that changed
        function_name: Function to test
        class_name: Class name if testing a method
        issue_description: GitHub issue text (for classification)
        patch_description: Commit message (for classification)
        max_iterations: Max inputs to generate
        timeout_seconds: Max fuzzing time

    Returns:
        CoverageGuidedFuzzingResult with all findings
    """
    fuzzer = CoverageGuidedDifferentialFuzzer(
        original_code=original_code,
        patched_code=patched_code,
        changed_lines=changed_lines,
        function_name=function_name,
        class_name=class_name,
        issue_description=issue_description,
        patch_description=patch_description,
    )

    result = fuzzer.fuzz(
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )

    # Print report
    print(fuzzer.generate_report(result))

    return result


# Example usage and testing
if __name__ == "__main__":
    # Example: Testing a simple patch
    original = """
def divide(a, b):
    return a / b
"""

    patched = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""

    changed_lines = [2, 3, 4]

    print("Running coverage-guided differential fuzzing...")
    result = run_coverage_guided_fuzzing(
        original_code=original,
        patched_code=patched,
        changed_lines=changed_lines,
        function_name="divide",
        issue_description="Fix division by zero error",
        patch_description="Handle zero divisor with proper error",
        max_iterations=1000,
        timeout_seconds=30.0,
    )

    print(f"\nFinal verdict: {result.verdict}")
