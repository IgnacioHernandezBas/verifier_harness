#!/usr/bin/env python3
"""
Debug script to examine the patch from a SWE-bench instance.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from swebench_integration.dataset_loader import DatasetLoader

def main():
    print("="*80)
    print("Examining SWE-bench patch structure")
    print("="*80)

    loader = DatasetLoader(
        source="princeton-nlp/SWE-bench_Verified",
        hf_mode=True,
        split="test",
    )

    # Get the first sample
    for sample in loader.iter_samples(limit=1):
        instance_id = sample["metadata"].get("instance_id")
        print(f"\nInstance ID: {instance_id}")
        print(f"Repo: {sample['repo']}")
        print(f"Base Commit: {sample['base_commit']}")

        patch = sample["patch"]
        print(f"\nPatch type: {type(patch)}")
        print(f"Patch length: {len(patch)}")
        print(f"\nFirst 500 chars of patch:")
        print("-"*80)
        print(repr(patch[:500]))
        print("-"*80)

        # Check for line endings
        has_crlf = '\r\n' in patch
        has_lf = '\n' in patch
        print(f"\nLine endings: CRLF={has_crlf}, LF={has_lf}")

        # Count lines
        lines = patch.split('\n')
        print(f"Number of lines: {len(lines)}")

        # Show lines around line 36
        if len(lines) > 36:
            print(f"\nLines 34-38 around problematic line 36:")
            print("-"*80)
            for i in range(max(0, 34), min(len(lines), 39)):
                print(f"Line {i}: {repr(lines[i])}")
            print("-"*80)

        # Save to file for inspection
        patch_file = Path("/tmp/debug_patch.patch")
        patch_file.write_text(patch, encoding="utf-8")
        print(f"\n✅ Patch saved to: {patch_file}")

        # Try to validate patch format
        if patch.startswith("diff --git"):
            print("✅ Patch starts with 'diff --git' (looks like valid unified diff)")
        else:
            print(f"⚠️  Patch starts with: {repr(patch[:50])}")

        break

if __name__ == "__main__":
    main()
