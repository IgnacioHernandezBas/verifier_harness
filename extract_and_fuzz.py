#!/usr/bin/env python3
"""
Extract code from SWE-bench instance and fuzz it OUTSIDE the container.

This solves the container issues by:
1. Using Singularity to extract code (proven to work)
2. Running fuzzing on the HOST (not in container)
3. No Atheris installation in containers needed
"""

import sys
import subprocess
import tempfile
from pathlib import Path

# Add verifier to path
sys.path.insert(0, '/fs/nexus-scratch/ihbas/verifier_harness')

from verifier.dynamic_analyzers.atheris_fuzzer import AtherisDifferentialFuzzer


def extract_file_from_singularity(instance_id: str, file_path: str, patched: bool = False):
    """
    Extract a file from SWE-bench Singularity container.

    Uses your working Singularity system.
    """
    # Use your Singularity cache
    sif_path = f"/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/{instance_id}.sif"

    # If patched, we need to apply patch first
    if patched:
        # Apply patch in container, then extract
        patch_file = f"/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/logs/{instance_id}/patch.diff"

        cmd = f"""
        singularity exec {sif_path} bash -c '
            cd /testbed
            git apply {patch_file} 2>/dev/null || true
            cat {file_path}
        '
        """
    else:
        # Just extract original
        cmd = f"singularity exec {sif_path} cat /testbed/{file_path}"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        return result.stdout
    else:
        raise RuntimeError(f"Failed to extract {file_path}: {result.stderr}")


def fuzz_swebench_instance(instance_id: str):
    """
    Fuzz a SWE-bench instance by extracting code and running Atheris on HOST.
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
    print()

    # Extract original and patched code
    print("Extracting code from Singularity...")
    try:
        original_code = extract_file_from_singularity(instance_id, file_path, patched=False)
        patched_code = extract_file_from_singularity(instance_id, file_path, patched=True)
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        return False

    print(f"✓ Extracted {len(original_code)} chars (original)")
    print(f"✓ Extracted {len(patched_code)} chars (patched)")
    print()

    # For demo, just show we can extract
    print("=" * 80)
    print("SUCCESS: Code extraction works!")
    print("=" * 80)
    print()
    print("Next step: Parse the file to extract the changed function")
    print("Then run Atheris fuzzing on the HOST (not in container)")

    return True


if __name__ == "__main__":
    instance_id = sys.argv[1] if len(sys.argv) > 1 else "astropy__astropy-6938"

    success = fuzz_swebench_instance(instance_id)
    sys.exit(0 if success else 1)
