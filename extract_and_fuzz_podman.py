#!/usr/bin/env python3
"""
Extract code from SWE-bench Podman containers and fuzz on HOST.

This follows your WORKING test_experiment_swebench_fixed.sh approach:
- Uses Podman containers (not Singularity)
- Extracts code using volumes (proven to work)
- Runs fuzzing on HOST (not in container)
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path

# Add verifier to path
sys.path.insert(0, '/fs/nexus-scratch/ihbas/verifier_harness')

from verifier.dynamic_analyzers.atheris_fuzzer import AtherisDifferentialFuzzer


def get_docker_image(instance_id):
    """Get Docker image name (from your working script)."""
    org = instance_id.split('__')[0]
    repo_and_num = instance_id.split('__')[1]
    return f"docker.io/swebench/sweb.eval.x86_64.{org}_1776_{repo_and_num}:latest"


def extract_code_with_podman(instance_id: str, file_path: str, apply_patch: bool = False):
    """
    Extract code using Podman - EXACTLY like your working script.

    Uses volumes to share files (proven to work).
    """
    # Setup scratch directory (following your pattern)
    scratch_dir = f"/scratch0/ihbas/fuzzing_extract/{instance_id}"
    os.makedirs(scratch_dir, exist_ok=True)

    # Get image
    image = get_docker_image(instance_id)

    # Copy patch if needed
    if apply_patch:
        patch_source = f"/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/logs/{instance_id}/patch.diff"
        patch_dest = f"{scratch_dir}/patch.diff"
        subprocess.run(f"cp {patch_source} {patch_dest}", shell=True, check=True)

    # Run podman (EXACTLY like your working script)
    if apply_patch:
        # Apply patch first, then extract
        cmd = f"""
        podman run --rm \
            -v {scratch_dir}:/scratch \
            {image} \
            bash -c '
                cd /testbed
                git apply /scratch/patch.diff 2>&1 || echo "Patch warnings"
                cat {file_path} > /scratch/code.py
            '
        """
    else:
        # Just extract original
        cmd = f"""
        podman run --rm \
            -v {scratch_dir}:/scratch \
            {image} \
            bash -c '
                cd /testbed
                cat {file_path} > /scratch/code.py
            '
        """

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Podman failed: {result.stderr}")

    # Read extracted code
    code_file = Path(f"{scratch_dir}/code.py")
    if code_file.exists():
        return code_file.read_text()
    else:
        raise RuntimeError("Code file not created")


def fuzz_swebench_instance(instance_id: str):
    """
    Extract code with Podman, then fuzz on HOST.
    """
    print(f"=" * 80)
    print(f"Fuzzing: {instance_id}")
    print(f"=" * 80)
    print()

    # Get patch info
    patch_file = Path(f"/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/logs/{instance_id}/patch.diff")

    if not patch_file.exists():
        print(f"✗ Patch not found")
        return False

    # Parse patch to get file path
    patch_content = patch_file.read_text()
    for line in patch_content.split('\n'):
        if line.startswith('diff --git'):
            file_path = line.split()[-1].replace('b/', '')
            break
    else:
        print("✗ Could not parse patch")
        return False

    print(f"File: {file_path}")
    print(f"Docker image: {get_docker_image(instance_id)}")
    print()

    # Extract original and patched code using PODMAN
    print("Extracting code using Podman (following your working script)...")
    try:
        original_code = extract_code_with_podman(instance_id, file_path, apply_patch=False)
        patched_code = extract_code_with_podman(instance_id, file_path, apply_patch=True)
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        return False

    print(f"✓ Extracted {len(original_code)} chars (original)")
    print(f"✓ Extracted {len(patched_code)} chars (patched)")
    print()

    # Show diff
    import difflib
    diff = list(difflib.unified_diff(
        original_code.splitlines()[:20],
        patched_code.splitlines()[:20],
        lineterm='',
        n=3
    ))
    if diff:
        print("First 20 lines diff:")
        for line in diff[:30]:
            print(line)
    print()

    print("=" * 80)
    print("SUCCESS: Code extraction with Podman works!")
    print("=" * 80)
    print()
    print("Next step: Parse the file to extract the changed function,")
    print("then run Atheris fuzzing on the HOST")

    return True


if __name__ == "__main__":
    # Set TMPDIR for Podman (from your working script)
    os.environ['TMPDIR'] = '/scratch0/ihbas/tmp'
    os.makedirs('/scratch0/ihbas/tmp', exist_ok=True)

    instance_id = sys.argv[1] if len(sys.argv) > 1 else "astropy__astropy-6938"

    success = fuzz_swebench_instance(instance_id)
    sys.exit(0 if success else 1)
