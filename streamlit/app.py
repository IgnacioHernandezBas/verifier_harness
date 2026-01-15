"""
SWE-bench Verification Demo App

A Streamlit application for:
- Testing patches on SWE-bench instances OR custom codebases
- Running static analysis and unit tests
- Displaying comprehensive verification results
"""

import streamlit as st
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from swebench_integration import DatasetLoader, PatchLoader
from verifier.static_analyzers.code_quality import analyze as run_static_analysis
from swebench_singularity import Config, SingularityBuilder, InstanceRunner
from verifier.dynamic_analyzers import test_patch_singularity

# Set page config
st.set_page_config(
    page_title="E6 Verifier Harness",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []


def apply_patch_to_repo(repo_path: Path, patch_str: str) -> bool:
    """Apply a patch to a repository."""
    try:
        # Write patch to temp file
        patch_file = repo_path / ".temp_patch.diff"
        patch_file.write_text(patch_str)

        # Apply patch
        result = subprocess.run(
            ["git", "apply", "--ignore-whitespace", str(patch_file)],
            cwd=str(repo_path),
            capture_output=True,
            text=True
        )

        patch_file.unlink()  # Clean up

        if result.returncode == 0:
            return True
        else:
            st.error(f"Patch application failed: {result.stderr}")
            return False

    except Exception as e:
        st.error(f"Error applying patch: {e}")
        return False

def sync_claim_tests_into_repo(
    instance_id: str,
    repo_path: Path,
    claim_tests_root: Path = Path("/fs/nexus-scratch/ihbas/verifier_harness/claim-tests"),
) -> Optional[Path]:
    """
    Copy claim-tests for this instance into the repo checkout so they are visible
    inside Singularity (repo is bound to /workspace).
    Returns the destination directory path (inside repo) if copied, else None.
    """
    src_dir = claim_tests_root / instance_id
    if not src_dir.exists():
        return None

    dest_dir = repo_path / "claim_tests" / instance_id
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    # Replace existing copy to avoid stale tests
    if dest_dir.exists():
        shutil.rmtree(dest_dir)

    shutil.copytree(src_dir, dest_dir)
    return dest_dir


def run_tests_in_repo(repo_path: Path, test_command: Optional[str] = None,
                       use_container: bool = False, container_path: Optional[Path] = None,
                       sample: Optional[Dict] = None) -> Dict:
    """Run tests in a repository, optionally using Singularity container."""

    # If using container, delegate to Singularity execution
    if use_container and container_path:
        return run_tests_in_singularity(repo_path, container_path, test_command, sample)

    # Otherwise, run tests directly on host
    try:
        # Default test command if not provided
        if not test_command:
            # Try to detect test framework
            if (repo_path / "pytest.ini").exists() or (repo_path / "setup.py").exists():
                test_command = "python -m pytest -v --tb=short"
            elif (repo_path / "manage.py").exists():
                test_command = "python manage.py test"
            else:
                test_command = "python -m pytest -v --tb=short"

        # Run tests
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Parse output
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode

        # Extract test counts
        passed = 0
        failed = 0
        errors = 0

        # Try to parse pytest output
        import re
        match = re.search(r'(\d+) passed', stdout)
        if match:
            passed = int(match.group(1))

        match = re.search(r'(\d+) failed', stdout)
        if match:
            failed = int(match.group(1))

        match = re.search(r'(\d+) error', stdout)
        if match:
            errors = int(match.group(1))

        return {
            'success': returncode == 0,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'total': passed + failed + errors,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': returncode,
            'execution_mode': 'host'
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0,
            'stdout': '',
            'stderr': 'Test execution timeout (5 minutes)',
            'returncode': -1,
            'execution_mode': 'host'
        }
    except Exception as e:
        return {
            'success': False,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
            'execution_mode': 'host'
        }


def run_tests_in_singularity(repo_path: Path, container_path: Path,
                             test_command: Optional[str] = None, sample: Optional[Dict] = None) -> Dict:
    """Run tests inside a Singularity container - SAME AS SLURM WORKER."""
    try:
        st.write(f"🐳 Using Singularity container: {container_path.name}")

        # Install package dependencies in container
        st.write("📦 Installing dependencies...")
        install_result = test_patch_singularity.install_package_in_singularity(
            repo_path=repo_path,
            image_path=str(container_path)
        )

        if install_result.get('returncode') != 0:
            st.warning(f"⚠️ Dependency installation had warnings")

        # Determine tests to run - SAME AS SLURM WORKER
        if test_command:
            # User provided custom command
            tests = [test_command]
            framework_hint = None
        elif sample:
            # SWE-bench mode: Load FAIL_TO_PASS and PASS_TO_PASS tests
            st.write("📋 Loading test list from instance metadata...")
            import ast

            fail_to_pass = sample.get('metadata', {}).get('FAIL_TO_PASS', '[]')
            pass_to_pass = sample.get('metadata', {}).get('PASS_TO_PASS', '[]')

            try:
                f2p = ast.literal_eval(fail_to_pass) if isinstance(fail_to_pass, str) else fail_to_pass
                p2p = ast.literal_eval(pass_to_pass) if isinstance(pass_to_pass, str) else pass_to_pass
            except Exception as e:
                st.warning(f"⚠️ Failed to parse test metadata: {e}")
                st.text(f"FAIL_TO_PASS: {fail_to_pass[:200]}")
                st.text(f"PASS_TO_PASS: {pass_to_pass[:200]}")
                f2p, p2p = [], []

            all_tests = [t for t in (f2p + p2p) if isinstance(t, str)]

            if not all_tests:
                st.warning("⚠️ No tests found in instance metadata (FAIL_TO_PASS + PASS_TO_PASS)")
            else:
                st.info(f"ℹ️ Found {len(f2p)} FAIL_TO_PASS and {len(p2p)} PASS_TO_PASS tests")

            # Detect framework type - SAME AS SLURM WORKER
            django_like = sum(1 for t in all_tests if '(' in t and ')' in t and '::' not in t)
            pytest_like = sum(1 for t in all_tests if '::' in t or t.endswith('.py'))
            prefer_django = django_like > 0 and django_like >= pytest_like

            # Filter malformed tests - SAME AS SLURM WORKER
            filtered_tests = []
            malformed_tests = []

            if prefer_django:
                filtered_tests = [t.strip() for t in all_tests if t.strip()]
            else:
                for test_name in all_tests:
                    if not isinstance(test_name, str):
                        continue
                    test_name = test_name.strip()
                    if not test_name:
                        continue

                    # Keep Django/unittest style
                    if '(' in test_name and ')' in test_name:
                        filtered_tests.append(test_name)
                        continue

                    # Filter unbalanced brackets
                    if '[' in test_name:
                        open_count = test_name.count('[')
                        close_count = test_name.count(']')
                        if open_count > close_count:
                            malformed_tests.append(test_name)
                            continue

                    filtered_tests.append(test_name)

            if not filtered_tests and all_tests:
                st.warning("⚠️ No tests left after filtering, using unfiltered list")
                filtered_tests = [t.strip() for t in all_tests if isinstance(t, str)]

            if malformed_tests:
                st.warning(f"⚠️ Filtered out {len(malformed_tests)} malformed test names")
                with st.expander("View malformed tests"):
                    st.code("\n".join(malformed_tests[:20]), language="text")

            tests = filtered_tests
            framework_hint = 'django' if prefer_django else None

            if framework_hint == 'django':
                st.info(f"ℹ️ Detected Django-style tests ({django_like} entries)")

            st.write(f"📝 Running {len(tests)} tests from instance metadata")

            # Show test list for debugging
            if tests:
                with st.expander(f"📋 View test list ({len(tests)} tests)"):
                    if len(tests) <= 20:
                        st.code("\n".join(tests), language="text")
                    else:
                        st.code("\n".join(tests[:20]) + f"\n\n... and {len(tests)-20} more tests", language="text")
        else:
            # Auto-detect: run all tests
            tests = []
            framework_hint = None

        # Run tests in container - SAME AS SLURM WORKER
        st.write("🧪 Running tests in container...")
        test_result = test_patch_singularity.run_tests_in_singularity(
            repo_path=repo_path,
            tests=tests,
            image_path=str(container_path),
            collect_coverage=False,
            test_framework_hint=framework_hint,
            verbose=True
        )

        # Parse output
        stdout = test_result.get('stdout', '')
        stderr = test_result.get('stderr', '')
        returncode = test_result.get('returncode', -1)

        # Extract test counts
        import re
        passed = 0
        failed = 0
        errors = 0

        match = re.search(r'(\d+) passed', stdout)
        if match:
            passed = int(match.group(1))

        match = re.search(r'(\d+) failed', stdout)
        if match:
            failed = int(match.group(1))

        match = re.search(r'(\d+) error', stdout)
        if match:
            errors = int(match.group(1))

        return {
            'success': returncode == 0,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'total': passed + failed + errors,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': returncode,
            'execution_mode': 'singularity',
            'container': str(container_path),
            'tests_run': len(tests) if tests else 0
        }

    except Exception as e:
        st.error(f"❌ Container execution failed: {e}")
        import traceback
        st.code(traceback.format_exc(), language='text')
        return {
            'success': False,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'total': 0,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
            'execution_mode': 'singularity',
            'container': str(container_path) if container_path else None
        }


def get_or_build_container(instance_id: Optional[str] = None,
                           docker_image: Optional[str] = None,
                           container_file: Optional[str] = None) -> Optional[Path]:
    """Get or build a Singularity container."""
    try:
        config = Config()
        builder = SingularityBuilder(config)

        # Case 1: SWE-bench instance - build from instance
        if instance_id:
            st.write(f"🔨 Building container for {instance_id}...")
            result = builder.build_instance(
                instance_id=instance_id,
                force_rebuild=False,
                check_docker_exists=False
            )

            if result.success:
                from_cache = " (cached)" if result.from_cache else " (newly built)"
                st.success(f"✅ Container ready{from_cache}")
                return result.sif_path
            else:
                st.error(f"❌ Container build failed: {result.error_message}")
                return None

        # Case 2: Docker image - convert to Singularity
        elif docker_image:
            st.write(f"🔨 Converting Docker image: {docker_image}...")
            # Use a hash of the image name as instance ID
            import hashlib
            pseudo_id = hashlib.md5(docker_image.encode()).hexdigest()[:12]

            result = builder.build_from_docker(
                docker_image=docker_image,
                output_name=f"custom_{pseudo_id}.sif"
            )

            if result.success:
                st.success("✅ Container built from Docker image")
                return result.sif_path
            else:
                st.error(f"❌ Build failed: {result.error_message}")
                return None

        # Case 3: Uploaded SIF file
        elif container_file:
            st.success("✅ Using uploaded container")
            return Path(container_file)

        return None

    except Exception as e:
        st.error(f"❌ Container setup failed: {e}")
        return None


def list_cached_containers() -> List[Dict]:
    """List all cached Singularity containers."""
    try:
        # Check multiple possible cache locations
        possible_paths = [
            Path("/fs/nexus-scratch/ihbas/.cache/swebench_singularity"),  # Primary cache
            Path("/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache"),  # Config default
            Path.home() / ".cache" / "swebench_singularity",  # User home
        ]

        # Try to get from config first
        try:
            config = Config()
            config_path = Path(config.get("singularity.cache_dir"))
            if config_path not in possible_paths:
                possible_paths.insert(0, config_path)
        except Exception:
            pass

        # Find the first path that exists and has .sif files
        cache_dir = None
        for path in possible_paths:
            if path.exists():
                # Check if it has any .sif files
                sif_files = list(path.rglob("*.sif"))
                if sif_files:
                    cache_dir = path
                    break

        if not cache_dir:
            return []

        # Collect all containers
        containers = []
        for sif_file in cache_dir.rglob("*.sif"):
            try:
                stat = sif_file.stat()
                containers.append({
                    'name': sif_file.name,
                    'path': str(sif_file),
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception:
                continue

        return sorted(containers, key=lambda x: x['modified'], reverse=True)

    except Exception:
        return []


def analyze_patch(repo_path: Path, patch_str: str,
                  use_container: bool = False, container_path: Optional[Path] = None,
                  test_command: Optional[str] = None, sample: Optional[Dict] = None) -> Dict:
    """Run comprehensive analysis on a patched repository."""
    results = {
        'timestamp': datetime.now().isoformat(),
        'repo_path': str(repo_path),
        'static_analysis': None,
        'test_results': None,
        'success': False,
        'use_container': use_container
    }

    # Run static analysis
    st.write("🔍 Running static analysis...")
    try:
        static_results = run_static_analysis(str(repo_path), patch_str)
        results['static_analysis'] = static_results
        st.success("✅ Static analysis complete")
    except Exception as e:
        st.error(f"❌ Static analysis failed: {e}")
        results['static_analysis'] = {'error': str(e)}

    # Run tests
    st.write("🧪 Running unit tests...")
    try:
        test_results = run_tests_in_repo(
            repo_path,
            test_command=test_command,
            use_container=use_container,
            container_path=container_path,
            sample=sample  # Pass sample for test metadata
        )
        results['test_results'] = test_results

        exec_mode = test_results.get('execution_mode', 'host')
        if test_results['success']:
            st.success(f"✅ Tests passed: {test_results['passed']}/{test_results['total']} ({exec_mode})")
        else:
            st.warning(f"⚠️ Tests failed: {test_results['failed']} failures, {test_results['errors']} errors ({exec_mode})")
    except Exception as e:
        st.error(f"❌ Test execution failed: {e}")
        results['test_results'] = {'error': str(e)}

    results['success'] = (
        results['static_analysis'] is not None and
        results['test_results'] is not None and
        results['test_results'].get('success', False)
    )
    # NEW: Claim-tests phase (only meaningful if SWE-bench tests passed)
    results["claim_test_results"] = None

    if (
        test_results.get("success")
        and use_container
        and container_path is not None
        and sample is not None
    ):
        instance_id = sample.get("metadata", {}).get("instance_id")
        if instance_id:
            copied_dir = sync_claim_tests_into_repo(instance_id, repo_path)
            if copied_dir:
                st.write("🧾 Running claim-tests (Singularity)...")

                claim_run = test_patch_singularity.run_tests_in_singularity(
                    repo_path=repo_path,
                    tests=[str(Path("claim_tests") / instance_id)],  # relative path inside /workspace
                    image_path=str(container_path),
                    collect_coverage=False,
                    verbose=True,
                    test_framework_hint="pytest",
                )

                # Parse counts similarly (optional)
                stdout = claim_run.get("stdout", "")
                import re
                c_passed = int(re.search(r"(\d+) passed", stdout).group(1)) if re.search(r"(\d+) passed", stdout) else 0
                c_failed = int(re.search(r"(\d+) failed", stdout).group(1)) if re.search(r"(\d+) failed", stdout) else 0
                c_errors = int(re.search(r"(\d+) error", stdout).group(1)) if re.search(r"(\d+) error", stdout) else 0

                results["claim_test_results"] = {
                    "success": claim_run.get("returncode", 1) == 0,
                    "passed": c_passed,
                    "failed": c_failed,
                    "errors": c_errors,
                    "total": c_passed + c_failed + c_errors,
                    "stdout": claim_run.get("stdout", ""),
                    "stderr": claim_run.get("stderr", ""),
                    "returncode": claim_run.get("returncode", -1),
                    "execution_mode": "singularity",
                    "tests_target": f"claim_tests/{instance_id}",
                }
            else:
                st.info(f"ℹ️ No claim-tests found for {instance_id} at {Path('/fs/nexus-scratch/ihbas/verifier_harness/claim-tests')}")

    return results


def display_static_analysis(static_results: Dict):
    """Display static analysis results."""
    st.subheader("📊 Static Analysis Results")

    if 'error' in static_results:
        st.error(f"Static analysis error: {static_results['error']}")
        return

    # SQI Score
    sqi = static_results.get('sqi', {})
    sqi_score = sqi.get('SQI', 0)
    classification = sqi.get('classification', 'Unknown')

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.metric("Static Quality Index (SQI)", f"{sqi_score:.1f}/100", classification)

    with col2:
        modified_files = static_results.get('modified_files', [])
        st.metric("Modified Files", len(modified_files))

    with col3:
        # Count total issues
        total_issues = 0
        if 'flake8' in static_results:
            total_issues += len(static_results['flake8'])
        if 'mypy' in static_results:
            total_issues += static_results['mypy'].get('error_count', 0)
        st.metric("Total Issues", total_issues)

    # Component breakdown
    st.write("**Component Breakdown:**")
    components = sqi.get('components', {})

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Pylint", f"{components.get('pylint', 0):.1f}")

    with col2:
        st.metric("Radon", f"{components.get('radon', 0):.1f}")

    with col3:
        st.metric("Flake8", f"{components.get('flake8', 0):.1f}")

    with col4:
        st.metric("Mypy", f"{components.get('mypy', 0):.1f}")

    with col5:
        st.metric("Bandit", f"{components.get('bandit', 0):.1f}")

    # Detailed results in expanders
    st.divider()

    # Pylint issues
    if 'pylint' in static_results:
        pylint_issues = static_results['pylint']
        total_pylint = sum(len(issues) for issues in pylint_issues.values())
        with st.expander(f"Pylint Issues ({total_pylint})"):
            for file_path, issues in pylint_issues.items():
                if issues:
                    st.markdown(f"**{file_path}**")
                    for issue in issues[:5]:  # Show first 5
                        st.write(f"- Line {issue.get('line')}: [{issue.get('type')}] {issue.get('message')}")

    # Flake8 issues
    if 'flake8' in static_results:
        flake8_issues = static_results['flake8']
        with st.expander(f"Flake8 Issues ({len(flake8_issues)})"):
            for issue in flake8_issues[:10]:  # Show first 10
                st.write(f"- Line {issue.get('line')}: [{issue.get('code')}] {issue.get('message')}")

    # Radon complexity
    if 'radon' in static_results:
        radon = static_results['radon']
        with st.expander(f"Radon Complexity (MI: {radon.get('mi_avg', 0):.1f})"):
            complexity = radon.get('complexity', {})
            for file_path, functions in complexity.items():
                if functions:
                    st.markdown(f"**{file_path}**")
                    for func in functions:
                        st.write(f"- {func.get('name')}: Complexity {func.get('complexity')}")

    # Mypy errors
    if 'mypy' in static_results:
        mypy = static_results['mypy']
        error_count = mypy.get('error_count', 0)
        with st.expander(f"Mypy Type Errors ({error_count})"):
            errors = mypy.get('errors', [])
            for error in errors[:10]:  # Show first 10
                st.write(f"- Line {error.get('line')}: {error.get('message')}")

    # Bandit security issues
    if 'bandit' in static_results:
        bandit = static_results['bandit']
        total_bandit = sum(bandit.values())
        with st.expander(f"Bandit Security Issues ({total_bandit})"):
            st.write(f"- High: {bandit.get('HIGH', 0)}")
            st.write(f"- Medium: {bandit.get('MEDIUM', 0)}")
            st.write(f"- Low: {bandit.get('LOW', 0)}")


def display_test_results(test_results: Dict):
    """Display test results."""
    st.subheader("🧪 Test Results")

    if 'error' in test_results:
        st.error(f"Test execution error: {test_results['error']}")
        return

    # Show execution mode
    exec_mode = test_results.get('execution_mode', 'host')
    if exec_mode == 'singularity':
        container_name = Path(test_results.get('container', '')).name
        st.info(f"🐳 Tests executed in Singularity container: `{container_name}`")
    else:
        st.info(f"💻 Tests executed on host system")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = test_results.get('total', 0)
        st.metric("Total Tests", total)

    with col2:
        passed = test_results.get('passed', 0)
        st.metric("Passed", passed, delta="✅")

    with col3:
        failed = test_results.get('failed', 0)
        st.metric("Failed", failed, delta="❌" if failed > 0 else None)

    with col4:
        errors = test_results.get('errors', 0)
        st.metric("Errors", errors, delta="⚠️" if errors > 0 else None)

    # Pass rate
    if total > 0:
        pass_rate = (passed / total) * 100
        st.progress(pass_rate / 100)
        st.write(f"**Pass Rate:** {pass_rate:.1f}%")
    elif test_results.get('tests_run', 0) > 0:
        st.warning(f"⚠️ {test_results['tests_run']} tests attempted but no results parsed from output")

    # Show output
    stdout = test_results.get('stdout', '')
    with st.expander("📄 Test Output (stdout)" + (" - Click to view" if stdout else " - Empty")):
        if stdout:
            st.code(stdout[-10000:] if len(stdout) > 10000 else stdout, language='text')
        else:
            st.write("No stdout captured")

    if test_results.get('stderr'):
        with st.expander("Test Errors (stderr)"):
            stderr = test_results.get('stderr', '')
            st.code(stderr[-5000:] if len(stderr) > 5000 else stderr, language='text')


# Main app
st.title("🔬 E6 Verifier Harness Demo")
st.markdown("Test your code patches with comprehensive static analysis and unit testing")

# Sidebar - Configuration
st.sidebar.header("Configuration")

mode = st.sidebar.radio(
    "Analysis Mode",
    ["SWE-bench Instance", "Custom Codebase"],
    help="Choose whether to test a SWE-bench instance or upload your own code"
)

st.sidebar.divider()

# Container configuration
st.sidebar.subheader("🐳 Container Settings")
use_container = st.sidebar.checkbox(
    "Use Singularity Container",
    value=True,
    help="Run tests in isolated Singularity container (recommended)"
)

container_source = None
container_path = None
docker_image = None
container_file_path = None

if use_container:
    if mode == "SWE-bench Instance":
        st.sidebar.info("Container will be auto-built from SWE-bench instance")

        # Show cache info
        cached = list_cached_containers()
        if cached:
            st.sidebar.success(f"✅ {len(cached)} cached containers available")
            with st.sidebar.expander("📦 View Cache"):
                st.write(f"**Total cache size**: {sum(c['size_mb'] for c in cached):.1f} MB")
                for c in cached[:5]:
                    st.text(f"• {c['name'][:40]}")
    else:  # Custom mode
        container_source = st.sidebar.radio(
            "Container Source",
            ["Browse Cache", "Docker Image", "Upload .sif", "None (Host)"],
            help="Choose how to provide the container"
        )

        if container_source == "Browse Cache":
            cached = list_cached_containers()
            if cached:
                st.sidebar.success(f"Found {len(cached)} cached containers")

                # Group by repository
                repos = {}
                for c in cached:
                    parts = Path(c['name']).stem.split('__')
                    repo = parts[0] if len(parts) > 0 else "other"
                    if repo not in repos:
                        repos[repo] = []
                    repos[repo].append(c)

                # Select repository
                selected_repo = st.sidebar.selectbox(
                    "Repository",
                    options=list(repos.keys())
                )

                # Select container
                repo_containers = repos[selected_repo]
                selected_container = st.sidebar.selectbox(
                    "Container",
                    options=range(len(repo_containers)),
                    format_func=lambda i: f"{repo_containers[i]['name']} ({repo_containers[i]['size_mb']:.0f}MB)"
                )

                container_file_path = repo_containers[selected_container]['path']
                st.sidebar.info(f"Using: {Path(container_file_path).name}")
            else:
                st.sidebar.warning("No cached containers found")
                container_source = "Docker Image"  # Fall back

        elif container_source == "Docker Image":
            docker_image = st.sidebar.text_input(
                "Docker Image",
                placeholder="python:3.9-slim",
                help="e.g., python:3.9, ubuntu:22.04"
            )
        elif container_source == "Upload .sif":
            container_file = st.sidebar.file_uploader(
                "Upload Singularity Image",
                type=['sif'],
                help="Upload a pre-built .sif file"
            )
            if container_file:
                # Save uploaded file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sif') as f:
                    f.write(container_file.read())
                    container_file_path = f.name
        elif container_source == "None (Host)":
            use_container = False

# Main content
if mode == "SWE-bench Instance":
    st.header("🔍 SWE-bench Instance Testing")

    col1, col2 = st.columns([3, 1])

    with col1:
        repo_filter = st.text_input(
            "Filter by repository",
            placeholder="e.g., scikit-learn/scikit-learn",
            help="Leave empty to show all repositories"
        )

    with col2:
        limit = st.number_input("Limit", 1, 100, 20, help="Maximum instances to load")

    if st.button("🔄 Load Instances", type="primary"):
        with st.spinner("Loading SWE-bench instances..."):
            try:
                #loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True, split="test")
                loader = DatasetLoader("princeton-nlp/SWE-bench_Lite", hf_mode=True, split="test")
                instances = []

                for sample in loader.iter_samples(limit=limit, filter_repo=repo_filter or None):
                    instance_id = sample.get('metadata', {}).get('instance_id')
                    if instance_id:
                        instances.append({
                            'instance_id': instance_id,
                            'repo': sample.get('repo', 'unknown'),
                            'problem_statement': sample.get('problem_statement', '')[:200] + '...',
                            'patch': sample.get('patch', ''),
                            'sample': sample
                        })

                st.session_state.swebench_instances = instances
                st.success(f"✅ Loaded {len(instances)} instances")

            except Exception as e:
                st.error(f"❌ Failed to load instances: {e}")

    # Instance selection
    if 'swebench_instances' in st.session_state:
        instances = st.session_state.swebench_instances

        if instances:
            st.subheader(f"Select Instance ({len(instances)} available)")

            selected_idx = st.selectbox(
                "Choose an instance",
                range(len(instances)),
                format_func=lambda i: f"{instances[i]['instance_id']} - {instances[i]['repo']}"
            )

            selected_instance = instances[selected_idx]

            st.info(f"**Selected:** {selected_instance['instance_id']}")
            st.markdown(f"**Repository:** {selected_instance['repo']}")

            with st.expander("View Problem Statement"):
                st.write(selected_instance['problem_statement'])

            with st.expander("View Patch"):
                st.code(selected_instance['patch'], language='diff')

            # Run analysis button
            if st.button("🚀 Run Analysis", type="primary"):
                st.write("---")
                st.header("Analysis Results")

                with st.spinner("Setting up repository..."):
                    try:
                        sample = selected_instance['sample']
                        patcher = PatchLoader(sample=sample, repos_root="repos_temp_demo")

                        # Clone
                        repo_path = patcher.clone_repository()
                        st.success(f"✅ Repository cloned to {repo_path}")

                        # Apply patch
                        st.write("📝 Applying patch...")
                        patch_result = patcher.apply_patch()

                        if not patch_result['applied']:
                            st.error("❌ Failed to apply patch")
                        else:
                            st.success("✅ Patch applied successfully")

                            # Apply test patch if exists
                            test_patch = sample.get('metadata', {}).get('test_patch', '')
                            if test_patch and test_patch.strip():
                                st.write("📝 Applying test patch...")
                                try:
                                    patcher.apply_additional_patch(test_patch)
                                    st.success("✅ Test patch applied")
                                except Exception as e:
                                    st.warning(f"⚠️ Test patch failed: {e}")

                            # Setup container if enabled
                            container_path_to_use = None
                            if use_container:
                                instance_id = selected_instance['instance_id']
                                container_path_to_use = get_or_build_container(instance_id=instance_id)

                                if not container_path_to_use:
                                    st.error("❌ Failed to build container, running on host instead")
                                    use_container_for_run = False
                                else:
                                    use_container_for_run = True
                            else:
                                use_container_for_run = False

                            # Run analysis with instance metadata
                            results = analyze_patch(
                                Path(repo_path),
                                selected_instance['patch'],
                                use_container=use_container_for_run,
                                container_path=container_path_to_use,
                                sample=sample  # Pass full sample for test metadata
                            )

                            # Store results
                            st.session_state.analysis_results.append(results)

                            # Display results
                            if results.get('static_analysis'):
                                display_static_analysis(results['static_analysis'])

                            st.divider()

                            if results.get('test_results'):
                                display_test_results(results['test_results'])

                            st.divider()

                            if results.get('claim_test_results'):
                                st.subheader("🧾 Claim-Test Results")
                                display_test_results(results['claim_test_results'])

                    except Exception as e:
                        st.error(f"❌ Analysis failed: {e}")
                        import traceback
                        st.code(traceback.format_exc(), language='text')

else:  # Custom Codebase
    st.header("📦 Custom Codebase Testing")

    st.markdown("""
    Upload your codebase and patch to run static analysis and unit tests.

    **Requirements:**
    - Codebase should be a Git repository (zipped)
    - Patch should be in unified diff format
    - Repository should have tests (pytest or unittest)
    """)

    # File uploads
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Upload Codebase")
        repo_zip = st.file_uploader(
            "Upload repository (ZIP)",
            type=['zip'],
            help="Upload a zipped Git repository"
        )

    with col2:
        st.subheader("2. Provide Patch")
        patch_input_method = st.radio(
            "Patch input method",
            ["Upload File", "Paste Text"]
        )

        if patch_input_method == "Upload File":
            patch_file = st.file_uploader(
                "Upload patch file",
                type=['diff', 'patch', 'txt']
            )
            patch_str = patch_file.read().decode('utf-8') if patch_file else None
        else:
            patch_str = st.text_area(
                "Paste patch (unified diff format)",
                height=200,
                placeholder="diff --git a/file.py b/file.py\n..."
            )

    # Test command
    st.subheader("3. Test Command (Optional)")
    test_command = st.text_input(
        "Custom test command",
        placeholder="e.g., python -m pytest tests/",
        help="Leave empty to auto-detect"
    )

    # Run analysis
    if st.button("🚀 Run Analysis", type="primary", disabled=not (repo_zip and patch_str)):
        st.write("---")
        st.header("Analysis Results")

        # Extract repository
        with st.spinner("Extracting repository..."):
            try:
                # Create temp directory
                temp_dir = tempfile.mkdtemp(prefix="verifier_custom_")
                repo_path = Path(temp_dir) / "repo"
                repo_path.mkdir()

                # Extract ZIP
                import zipfile
                with zipfile.ZipFile(repo_zip) as zf:
                    zf.extractall(repo_path)

                st.success(f"✅ Repository extracted to {repo_path}")

                # Find actual repo root (might be in a subdirectory)
                git_dirs = list(repo_path.rglob('.git'))
                if git_dirs:
                    repo_path = git_dirs[0].parent
                    st.info(f"Found Git repository at: {repo_path}")

                # Apply patch
                st.write("📝 Applying patch...")
                if apply_patch_to_repo(repo_path, patch_str):
                    st.success("✅ Patch applied successfully")

                    # Setup container if enabled
                    container_path_to_use = None
                    if use_container:
                        if docker_image:
                            container_path_to_use = get_or_build_container(docker_image=docker_image)
                        elif container_file_path:
                            container_path_to_use = get_or_build_container(container_file=container_file_path)

                        if not container_path_to_use:
                            st.warning("⚠️ Container setup failed, running on host instead")
                            use_container_for_run = False
                        else:
                            use_container_for_run = True
                    else:
                        use_container_for_run = False

                    # Run analysis
                    results = analyze_patch(
                        repo_path,
                        patch_str,
                        use_container=use_container_for_run,
                        container_path=container_path_to_use,
                        test_command=test_command if test_command else None
                    )

                    # Store results
                    st.session_state.analysis_results.append(results)

                    # Display results
                    if results.get('static_analysis'):
                        display_static_analysis(results['static_analysis'])

                    st.divider()

                    if results.get('test_results'):
                        display_test_results(results['test_results'])
                    
                    st.divider()

                    if results.get("claim_test_results"):
                        st.subheader("🧾 Claim-Test Results")
                        display_test_results(results["claim_test_results"])

                    # Clean up
                    shutil.rmtree(temp_dir, ignore_errors=True)

                else:
                    st.error("❌ Failed to apply patch")
                    shutil.rmtree(temp_dir, ignore_errors=True)

            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                import traceback
                st.code(traceback.format_exc(), language='text')

# Analysis History
if st.session_state.analysis_results:
    st.divider()
    st.header("📊 Analysis History")

    st.write(f"Total analyses: {len(st.session_state.analysis_results)}")

    for i, result in enumerate(reversed(st.session_state.analysis_results)):
        with st.expander(f"Analysis {len(st.session_state.analysis_results) - i} - {result['timestamp']}"):
            st.json({
                'timestamp': result['timestamp'],
                'repo_path': result['repo_path'],
                'success': result['success'],
                'sqi_score': result.get('static_analysis', {}).get('sqi', {}).get('SQI'),
                'tests_passed': result.get('test_results', {}).get('passed'),
                'tests_failed': result.get('test_results', {}).get('failed'),
            })

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    """
    **E6 Verifier Harness**

    A comprehensive patch verification system featuring:
    - **Static Analysis**: Pylint, Flake8, Radon, Mypy, Bandit
    - **Dynamic Testing**: Unit test execution
    - **SQI Scoring**: Aggregate quality metrics

    Supports both SWE-bench instances and custom codebases.
    """
)
