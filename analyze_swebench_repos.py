#!/usr/bin/env python3
"""
Analyze SWE-bench-verified repositories to understand installation requirements.

This script categorizes repositories based on:
- Use of setuptools-scm
- C extensions
- Build requirements
- Compatibility with editable install vs PYTHONPATH mode
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict
import subprocess
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from swebench_integration.dataset_loader import DatasetLoader


def clone_repo(repo_url: str, base_commit: str, target_dir: Path) -> bool:
    """Clone a repository at a specific commit."""
    try:
        # Clone with depth 1 for efficiency
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
            capture_output=True,
            text=True,
            timeout=120,
            check=True
        )

        # Fetch the specific commit if needed
        subprocess.run(
            ["git", "-C", str(target_dir), "fetch", "origin", base_commit],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Checkout the commit
        subprocess.run(
            ["git", "-C", str(target_dir), "checkout", base_commit],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"  Failed to clone {repo_url}: {e}")
        return False


def analyze_repo_setup(repo_path: Path) -> Dict[str, Any]:
    """Analyze repository setup files and requirements."""
    analysis = {
        "has_setup_py": False,
        "has_pyproject_toml": False,
        "has_setup_cfg": False,
        "uses_setuptools_scm": False,
        "has_c_extensions": False,
        "build_system": "unknown",
        "build_requires": [],
        "has_lib_dir": False,
        "package_name": None,
    }

    # Check for setup files
    setup_py = repo_path / "setup.py"
    pyproject_toml = repo_path / "pyproject.toml"
    setup_cfg = repo_path / "setup.cfg"

    analysis["has_setup_py"] = setup_py.exists()
    analysis["has_pyproject_toml"] = pyproject_toml.exists()
    analysis["has_setup_cfg"] = setup_cfg.exists()
    analysis["has_lib_dir"] = (repo_path / "lib").is_dir() if (repo_path / "lib").exists() else False

    # Analyze setup.py
    if setup_py.exists():
        try:
            content = setup_py.read_text(encoding="utf-8", errors="ignore")

            # Check for setuptools-scm
            if "setuptools_scm" in content or "setuptools-scm" in content:
                analysis["uses_setuptools_scm"] = True

            # Check for C extensions
            if "Extension" in content or "ext_modules" in content:
                analysis["has_c_extensions"] = True

            # Try to extract package name
            for line in content.split("\n"):
                if "name=" in line or 'name =' in line:
                    # Simple extraction - may not work for complex cases
                    try:
                        name_part = line.split("name")[1].split("=")[1].strip()
                        name_part = name_part.strip("\"'(),")
                        if name_part and not name_part.startswith("f") and " " not in name_part:
                            analysis["package_name"] = name_part
                            break
                    except:
                        pass
        except Exception as e:
            print(f"  Warning: Could not read setup.py: {e}")

    # Analyze pyproject.toml
    if pyproject_toml.exists():
        try:
            content = pyproject_toml.read_text(encoding="utf-8", errors="ignore")

            # Check for setuptools-scm
            if "setuptools_scm" in content or "setuptools-scm" in content:
                analysis["uses_setuptools_scm"] = True

            # Check for build system
            if "[build-system]" in content:
                if "setuptools" in content:
                    analysis["build_system"] = "setuptools"
                elif "poetry" in content:
                    analysis["build_system"] = "poetry"
                elif "flit" in content:
                    analysis["build_system"] = "flit"
                elif "hatchling" in content:
                    analysis["build_system"] = "hatchling"

            # Extract build requires
            in_build_system = False
            for line in content.split("\n"):
                if "[build-system]" in line:
                    in_build_system = True
                elif in_build_system and line.startswith("["):
                    in_build_system = False
                elif in_build_system and "requires" in line and "=" in line:
                    # Extract requires list
                    requires_str = line.split("=", 1)[1].strip()
                    if requires_str.startswith("["):
                        # Simple extraction of package names
                        requires_str = requires_str.strip("[]")
                        for req in requires_str.split(","):
                            req = req.strip().strip("\"'")
                            if req:
                                analysis["build_requires"].append(req)
        except Exception as e:
            print(f"  Warning: Could not read pyproject.toml: {e}")

    # Analyze setup.cfg
    if setup_cfg.exists():
        try:
            content = setup_cfg.read_text(encoding="utf-8", errors="ignore")

            # Check for setuptools-scm
            if "setuptools_scm" in content or "setuptools-scm" in content:
                analysis["uses_setuptools_scm"] = True
        except Exception as e:
            print(f"  Warning: Could not read setup.cfg: {e}")

    return analysis


def categorize_repo(analysis: Dict[str, Any]) -> str:
    """Categorize repository based on analysis."""

    # No setup files - pure Python with direct imports
    if not any([analysis["has_setup_py"], analysis["has_pyproject_toml"], analysis["has_setup_cfg"]]):
        return "no_install_needed"

    # Has C extensions - will likely need PYTHONPATH mode
    if analysis["has_c_extensions"]:
        return "c_extensions"

    # Uses setuptools-scm - will benefit from the git tag fix
    if analysis["uses_setuptools_scm"]:
        return "setuptools_scm"

    # Pure Python with setup files - should work with editable install
    return "pure_python"


def main():
    """Main analysis function."""
    print("=" * 80)
    print("SWE-bench-verified Repository Installation Analysis")
    print("=" * 80)
    print()

    # Load dataset
    print("Loading SWE-bench-verified dataset...")
    loader = DatasetLoader(
        source="princeton-nlp/SWE-bench_Verified",
        hf_mode=True,
        split="test"
    )

    # Collect unique repositories
    repo_info = {}  # repo_name -> {url, commits[], samples[]}

    for sample in loader.iter_samples():
        repo_name = sample["repo"]
        base_commit = sample["base_commit"]
        instance_id = sample["metadata"].get("instance_id", "unknown")

        if repo_name not in repo_info:
            # Convert repo name to URL
            repo_url = f"https://github.com/{repo_name}.git"
            repo_info[repo_name] = {
                "url": repo_url,
                "commits": set(),
                "instances": []
            }

        repo_info[repo_name]["commits"].add(base_commit)
        repo_info[repo_name]["instances"].append(instance_id)

    print(f"Found {len(repo_info)} unique repositories")
    print(f"Total instances: {sum(len(info['instances']) for info in repo_info.values())}")
    print()

    # Analyze each repository
    results = {}
    categories = defaultdict(list)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        for idx, (repo_name, info) in enumerate(repo_info.items(), 1):
            print(f"[{idx}/{len(repo_info)}] Analyzing {repo_name}...")

            # Use the first commit for analysis
            base_commit = list(info["commits"])[0]
            repo_dir = tmpdir_path / repo_name.replace("/", "_")

            # Clone repository
            if not clone_repo(info["url"], base_commit, repo_dir):
                results[repo_name] = {
                    "error": "Failed to clone",
                    "category": "error",
                    "instances": len(info["instances"]),
                    "commits": len(info["commits"])
                }
                categories["error"].append(repo_name)
                print(f"  Status: ERROR - Failed to clone")
                print()
                continue

            # Analyze setup
            analysis = analyze_repo_setup(repo_dir)
            category = categorize_repo(analysis)

            results[repo_name] = {
                **analysis,
                "category": category,
                "instances": len(info["instances"]),
                "commits": len(info["commits"]),
                "repo_url": info["url"]
            }
            categories[category].append(repo_name)

            # Clean up
            shutil.rmtree(repo_dir, ignore_errors=True)

            # Print status
            status_emoji = {
                "pure_python": "✅",
                "setuptools_scm": "🔧",
                "c_extensions": "⚙️",
                "no_install_needed": "📦",
                "error": "❌"
            }.get(category, "❓")

            print(f"  Status: {status_emoji} {category.upper()}")
            if analysis["uses_setuptools_scm"]:
                print(f"    - Uses setuptools-scm (will benefit from git tag fix)")
            if analysis["has_c_extensions"]:
                print(f"    - Has C extensions (will use PYTHONPATH mode)")
            if analysis["has_lib_dir"]:
                print(f"    - Has lib/ directory")
            if analysis["package_name"]:
                print(f"    - Package: {analysis['package_name']}")
            print()

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    print("Category Breakdown:")
    print("-" * 80)
    for category in ["pure_python", "setuptools_scm", "c_extensions", "no_install_needed", "error"]:
        count = len(categories[category])
        total_instances = sum(results[r]["instances"] for r in categories[category])

        emoji = {
            "pure_python": "✅",
            "setuptools_scm": "🔧",
            "c_extensions": "⚙️",
            "no_install_needed": "📦",
            "error": "❌"
        }.get(category, "❓")

        description = {
            "pure_python": "Pure Python (editable install should work)",
            "setuptools_scm": "Uses setuptools-scm (benefits from git tag fix)",
            "c_extensions": "Has C extensions (will use PYTHONPATH fallback)",
            "no_install_needed": "No setup files (direct import)",
            "error": "Failed to analyze"
        }.get(category, "Unknown")

        print(f"{emoji} {category.upper()}: {count} repos, {total_instances} instances")
        print(f"   {description}")
        if categories[category]:
            for repo in sorted(categories[category]):
                instances = results[repo]["instances"]
                print(f"     - {repo} ({instances} instances)")
        print()

    print("-" * 80)
    print(f"Total: {len(results)} repositories, {sum(r['instances'] for r in results.values())} instances")
    print()

    # Detailed breakdown for setuptools-scm users
    if categories["setuptools_scm"]:
        print("=" * 80)
        print("SETUPTOOLS-SCM USERS (Will benefit from git tag fix)")
        print("=" * 80)
        print()
        for repo in sorted(categories["setuptools_scm"]):
            info = results[repo]
            print(f"📦 {repo}")
            print(f"   Instances: {info['instances']}")
            print(f"   Build system: {info['build_system']}")
            if info['build_requires']:
                print(f"   Build requires: {', '.join(info['build_requires'][:3])}")
            print()

    # Detailed breakdown for C extension repos
    if categories["c_extensions"]:
        print("=" * 80)
        print("C EXTENSION REPOS (Will use PYTHONPATH fallback)")
        print("=" * 80)
        print()
        for repo in sorted(categories["c_extensions"]):
            info = results[repo]
            print(f"⚙️  {repo}")
            print(f"   Instances: {info['instances']}")
            if info['uses_setuptools_scm']:
                print(f"   Note: Also uses setuptools-scm")
            print()

    # Save detailed results
    output_file = PROJECT_ROOT / "swebench_repo_analysis.json"
    import json
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
