# verifier/dynamic_analyzers/change-aware-test-generation.py
"""
Change-Aware Test Generation (Property-based + Templates)

What this module does (in short):
1) Reads a unified diff to find changed Python files and functions.
2) Imports those functions from two repo snapshots (e.g., oracle vs. generated).
3) Uses Hypothesis to generate *targeted inputs* around common boundary cases.
4) Runs lock-step tests: for each input, compare behavior on both snapshots.
   - Same return value (by type + normalized representation) OR same exception type
   - If they differ consistently, we report a *behavioral delta*.
5) Emits minimized counterexamples (shrunk inputs) you can turn into unit tests.

You can call `ChangeAwareGenerator.run_lockstep(repo_left, repo_right, diff_text)`
from your Dynamic Verification Layer. A "Standalone Test Mode" is provided at the
bottom to demo the approach without touching external repos.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# Project-root relative imports
CURRENT_DIR = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_DIR.parents[2]  # verifier/dynamic_analyzers → verifier → project root
sys.path.append(str(PROJECT_ROOT))

from verifier.utils.diff_utils import parse_unified_diff, filter_paths_to_py
from swebench_integration.dataset_loader import DatasetLoader
from verifier.patch_loader import PatchLoader

# Hypothesis is declared in environment.yml/requirements.txt
from hypothesis import given, settings, strategies as st, HealthCheck, Phase, Verbosity

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------

@dataclass
class TargetFunction:
    module_path: str   # repo-relative path like "pkg/mod/file.py"
    qualname: str      # function name (no methods for now)
    abs_left: Path     # absolute path in left repo (e.g., oracle)
    abs_right: Path    # absolute path in right repo (e.g., generated)
    module_name: str   # importable module name derived from repo layout


def _module_name_from_file(repo_path: Path, file_path: Path) -> str:
    """
    Convert a file path under repo_path into a Python module name.
    Example: repo_path=/tmp/repo, file=src/pkg/foo/bar.py -> "src.pkg.foo.bar"
    """
    rel = file_path.relative_to(repo_path).with_suffix("")
    parts = list(rel.parts)
    # Drop obvious non-package folders if present (optional)
    return ".".join(parts)


def _extract_changed_functions(abs_file: Path, diff_ranges: List[Tuple[int, int]]) -> List[str]:
    """
    Parse a Python file and return simple function names whose
    [lineno, end_lineno] overlaps with any diff range.
    """
    try:
        src = abs_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    changed: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", start)
            if start is None or end is None:
                continue
            for (d0, d1) in diff_ranges:
                if not (end < d0 or start > d1):
                    changed.append(node.name)
                    break
    return changed


def _load_object_from(repo_path: Path, module_name: str, qualname: str) -> Optional[Callable[..., Any]]:
    """
    Dynamically load a top-level function object `qualname` from `module_name`
    using the module file found in `repo_path`.
    """
    # Resolve module file (best-effort)
    file_guess = Path(repo_path, *module_name.split("."))  # .../a/b/c
    py_path = file_guess.with_suffix(".py")
    if not py_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(module_name, py_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[arg-type]
    except Exception:
        return None

    obj = getattr(mod, qualname, None)
    if callable(obj):
        # Skip bound methods or instance methods for now
        if inspect.isfunction(obj) and obj.__qualname__ == obj.__name__:
            return obj
    return None


def _strategy_for_param(p: inspect.Parameter) -> st.SearchStrategy[Any]:
    """
    Heuristic mapping from annotations/defaults to Hypothesis strategies.
    Intentionally conservative; fallbacks cover common Python inputs.
    """
    anno = p.annotation
    default = p.default

    # If there's a default, sometimes it's informative
    if default is not inspect._empty:
        if isinstance(default, bool):
            return st.booleans()
        if isinstance(default, int):
            return st.integers(min_value=-2, max_value=2)
        if isinstance(default, float):
            return st.floats(allow_nan=False, allow_infinity=False, width=32)
        if isinstance(default, str):
            return st.text(max_size=8)
        if default is None:
            return st.none() | st.integers(-1, 1) | st.text(max_size=3)

    # Annotations
    if anno in (int, "int"):
        return st.integers(min_value=-2, max_value=2)
    if anno in (float, "float"):
        return st.floats(allow_nan=False, allow_infinity=False, width=32)
    if anno in (str, "str"):
        return st.text(max_size=8)
    if anno in (bool, "bool"):
        return st.booleans()

    # Fallback: small cartesian
    return st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-2, max_value=2),
        st.text(max_size=4),
        st.lists(st.integers(-1, 1), max_size=2),
        st.dictionaries(st.text(max_size=3), st.integers(-1, 1), max_size=1),
    )


def _build_call_strategy(fn: Callable[..., Any]) -> Optional[st.SearchStrategy[Tuple[tuple, dict]]]:
    """
    Create a Hypothesis strategy that yields (args, kwargs) for calling fn.
    Skip var-positional/var-keyword for now to keep it simple and robust.
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return None

    arg_strats: List[st.SearchStrategy[Any]] = []
    kw_strats: Dict[str, st.SearchStrategy[Any]] = {}

    for name, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            # Skip *args/**kwargs to avoid brittle calls in arbitrary repos
            continue
        s = _strategy_for_param(p)
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            arg_strats.append(s)
        elif p.kind is inspect.Parameter.KEYWORD_ONLY:
            kw_strats[name] = s

    if not arg_strats and not kw_strats:
        # Zero-arg function → trivial
        return st.just((tuple(), {}))

    def to_kwargs(kwargs_items: List[Tuple[str, Any]]) -> Dict[str, Any]:
        return {k: v for k, v in kwargs_items}

    if kw_strats:
        kw_items = st.fixed_dictionaries(kw_strats).map(lambda d: list(d.items()))
    else:
        kw_items = st.just([])

    return st.tuples(st.tuples(*arg_strats) if arg_strats else st.just(tuple()), kw_items).map(
        lambda t: (t[0], to_kwargs(t[1]))
    )


def _normalize_result(x: Any) -> Tuple[str, str]:
    """
    Normalize return values for comparison across two repos.
    We compare by (type name, JSON-ish representation).
    """
    tname = type(x).__name__
    try:
        # Try to serialize simple shapes
        return (tname, json.dumps(x, sort_keys=True, default=str)[:4000])
    except Exception:
        return (tname, str(x)[:4000])


def _call_and_capture(fn: Callable[..., Any], args: tuple, kwargs: dict) -> Tuple[str, Any]:
    """
    Call fn safely; return ('ok', normalized_value) or ('exc', exception_type_name)
    """
    try:
        out = fn(*args, **kwargs)
        return ("ok", _normalize_result(out))
    except Exception as e:
        return ("exc", type(e).__name__)


# --------------------------------------------------------------------------------------
# Core generator
# --------------------------------------------------------------------------------------

class ChangeAwareGenerator:
    """
    Change-aware differential runner:
    - parse diff → pick changed .py files and functions
    - load those functions from both repos
    - hypothesis-driven lock-step calls to detect behavior differences
    """

    def __init__(self, max_examples: int = 50, deadline_ms: Optional[int] = 400):
        self.max_examples = max_examples
        self.deadline_ms = deadline_ms

    def _discover_targets(
        self, repo_left: Path, repo_right: Path, diff_text: str
    ) -> List[TargetFunction]:
        parsed = parse_unified_diff(diff_text)
        py_files = filter_paths_to_py(list(parsed.keys()))
        targets: List[TargetFunction] = []

        for rel in py_files:
            ranges = parsed.get(rel, [])
            left_abs = repo_left / rel
            right_abs = repo_right / rel
            if not left_abs.exists() or not right_abs.exists():
                continue

            changed_fns = _extract_changed_functions(left_abs, ranges)
            if not changed_fns:
                # no function-level overlap → still allow module-level smoke
                changed_fns = []

            modname = _module_name_from_file(repo_left, left_abs)
            for fn in changed_fns or ["__module_smoke__"]:
                targets.append(
                    TargetFunction(
                        module_path=rel,
                        qualname=fn,
                        abs_left=left_abs,
                        abs_right=right_abs,
                        module_name=modname,
                    )
                )
        return targets

    def _compare_function(self, left_repo: Path, right_repo: Path, t: TargetFunction) -> Dict[str, Any]:
        """
        Compare a single function under randomized inputs. If `__module_smoke__`,
        we attempt to import the module to catch import-time errors.
        """
        result: Dict[str, Any] = {
            "module": t.module_name,
            "file": t.module_path,
            "function": t.qualname,
            "differential_found": False,
            "counterexample": None,
            "notes": "",
        }

        if t.qualname == "__module_smoke__":
            # Try importing both modules; report if left vs right import behavior differs.
            left_ok = _load_object_from(left_repo, t.module_name, "__name__") is not None
            right_ok = _load_object_from(right_repo, t.module_name, "__name__") is not None
            if left_ok != right_ok:
                result["differential_found"] = True
                result["counterexample"] = {"import_left": left_ok, "import_right": right_ok}
                result["notes"] = "Module import behavior differs (smoke)."
            return result

            # (No further action if both import identically.)

        # Load functions
        f_left = _load_object_from(left_repo, t.module_name, t.qualname)
        f_right = _load_object_from(right_repo, t.module_name, t.qualname)

        if f_left is None or f_right is None:
            result["notes"] = "Function missing from one or both repos; skipping."
            return result

        call_strat = _build_call_strategy(f_left)
        if call_strat is None:
            result["notes"] = "Unable to build call strategy; skipping."
            return result

        # Local closure so Hypothesis can run with decorated test
        def property_call(args_kwargs: Tuple[tuple, dict]) -> Optional[Dict[str, Any]]:
            args, kwargs = args_kwargs
            l_status, l_val = _call_and_capture(f_left, args, kwargs)
            r_status, r_val = _call_and_capture(f_right, args, kwargs)

            # Accept equivalence if both raised same exc type OR both returned same normalized shape
            if l_status == r_status:
                if l_status == "exc":
                    if l_val == r_val:
                        return None  # same exception type
                else:
                    if l_val == r_val:
                        return None  # same normalized result

            # Otherwise → difference!
            return {
                "args": args,
                "kwargs": kwargs,
                "left": (l_status, l_val),
                "right": (r_status, r_val),
            }

        # Run Hypothesis in-process and stop on first counterexample
        ce_holder: Dict[str, Any] = {}

        @settings(
            max_examples=self.max_examples,
            deadline=None if self.deadline_ms is None else self.deadline_ms,
            suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
            phases=(Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink),
            verbosity=Verbosity.quiet,
        )
        @given(call_strat)
        def _check(args_kwargs):
            nonlocal ce_holder
            diff = property_call(args_kwargs)
            if diff is not None:
                ce_holder = diff
                # Hypothesis will try to shrink by re-raising an assertion
                assert False, "Behavioral difference detected"

        try:
            _check()
        except AssertionError:
            # We expect this when a difference is found; ce_holder contains the shrunk example
            if ce_holder:
                result["differential_found"] = True
                result["counterexample"] = ce_holder
                result["notes"] = "Shrunk counterexample produced by Hypothesis."
        except Exception as e:
            result["notes"] = f"Error during differential run: {e!r}"

        return result

    # Public API --------------------------------------------------------------

    def run_lockstep(self, repo_left: str | Path, repo_right: str | Path, diff_text: str) -> List[Dict[str, Any]]:
        """
        Main entry point:
        - repo_left: path to "oracle"/baseline snapshot
        - repo_right: path to "generated"/candidate snapshot
        - diff_text: unified diff string that created repo_right (or a hand-crafted diff)
        Returns a list of per-target reports with any counterexamples found.
        """
        repo_left = Path(repo_left).resolve()
        repo_right = Path(repo_right).resolve()

        targets = self._discover_targets(repo_left, repo_right, diff_text)
        reports: List[Dict[str, Any]] = []
        for t in targets:
            rep = self._compare_function(repo_left, repo_right, t)
            reports.append(rep)
        return reports


# --------------------------------------------------------------------------------------
# Standalone Test Mode
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Demo usage without needing a full SWE-bench instance:

    1) We load a small dataset sample (HuggingFace or local JSON via DatasetLoader).
    2) Clone a repo and apply its patch (PatchLoader).
    3) Duplicate the repo to create a "left" (oracle-ish) and a "right" (generated) snapshot.
    4) Inject a tiny demo module that differs in behavior under x==0 between left and right.
    5) Provide a minimal diff that points to that module so the generator targets it.
    6) Run the change-aware generator and pretty-print the results.

    NOTE:
    - This keeps the demo fully self-contained and reproducible.
    - It does NOT depend on the repo's own code successfully importing.
    """

    import argparse
    from textwrap import dedent

    parser = argparse.ArgumentParser(description="Standalone demo for change-aware test generation")
    parser.add_argument("--limit", type=int, default=1, help="Limit dataset samples (only for patch clone step)")
    parser.add_argument("--repos_root", type=str, default="./repos_temp", help="Where to clone repos")
    parser.add_argument("--max_examples", type=int, default=50, help="Hypothesis max examples per target")
    args = parser.parse_args()

    # 1) Load any sample (we only use it to exercise PatchLoader)
    loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True)    # or ("swebench_integration/data/swebench_sample.json")?: local sample included in repo
    sample = next(loader.iter_samples(limit=args.limit), None)
    if sample is None:
        print("No dataset sample available.")
        sys.exit(0)

    # 2) Clone and apply patch
    patcher = PatchLoader(sample, repos_root=args.repos_root)
    try:
        patcher.cleanup_old_repos()
    except Exception:
        pass

    try:
        res = patcher.load_and_apply()
        base_repo = Path(res["repo_path"]).resolve()
    except Exception as e:
        print(f"❌ Patch clone/apply failed: {e}")
        sys.exit(1)

    print(f"📦 Base repository prepared at: {base_repo}")

    # 3) Duplicate for left/right snapshots
    left_repo = Path(tempfile.mkdtemp(prefix="repo_left_", dir=args.repos_root))
    right_repo = Path(tempfile.mkdtemp(prefix="repo_right_", dir=args.repos_root))
    shutil.copytree(base_repo, left_repo, dirs_exist_ok=True)
    shutil.copytree(base_repo, right_repo, dirs_exist_ok=True)

    # 4) Inject a tiny module that behaves differently on x == 0
    demo_rel = Path("verifier_demo/demo.py")
    (left_repo / demo_rel.parent).mkdir(parents=True, exist_ok=True)
    (right_repo / demo_rel.parent).mkdir(parents=True, exist_ok=True)

    left_src = dedent(
        """
        def add_one(x):
            # identity for zero, +1 otherwise
            if x == 0:
                return 0
            return x + 1
        """
    ).strip()

    right_src = dedent(
        """
        def add_one(x):
            # bug: always adds one (even for zero)
            return x + 1
        """
    ).strip()

    (left_repo / demo_rel).write_text(left_src, encoding="utf-8")
    (right_repo / demo_rel).write_text(right_src, encoding="utf-8")

    # 5) Provide a minimal diff pointing to the changed function
    #    The actual ranges just need to include the function lines; here we use a small fabricated diff.
    diff_text = dedent(
        """
        diff --git a/verifier_demo/demo.py b/verifier_demo/demo.py
        index 111111..222222 100644
        --- a/verifier_demo/demo.py
        +++ b/verifier_demo/demo.py
        @@ -1,4 +1,4 @@
        -def add_one(x):
        -    if x == 0:
        -        return 0
        -    return x + 1
        +def add_one(x):
        +    # bug: always adds one (even for zero)
        +    return x + 1
        """
    ).strip()

    # 6) Run the generator
    gen = ChangeAwareGenerator(max_examples=args.max_examples, deadline_ms=200)
    report = gen.run_lockstep(left_repo, right_repo, diff_text)

    # Pretty print result
    print("\n🔎 Change-Aware Differential Report")
    print("=" * 72)
    for r in report:
        print(f"- Module:   {r['module']}")
        print(f"  File:      {r['file']}")
        print(f"  Function:  {r['function']}")
        print(f"  Differential: {r['differential_found']}")
        if r["counterexample"]:
            ce = r["counterexample"]
            print("  Counterexample:")
            print(f"    args   = {ce.get('args')}")
            print(f"    kwargs = {ce.get('kwargs')}")
            print(f"    left   = {ce.get('left')}")
            print(f"    right  = {ce.get('right')}")
        if r["notes"]:
            print(f"  Notes: {r['notes']}")
        print("-" * 72)

    print("\n✅ Standalone demo complete. You can now promote the minimized counterexample to a unit test.")
