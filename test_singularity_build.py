#!/usr/bin/env python3
"""
Simple test to verify Singularity image building works.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.test_patch_singularity import build_singularity_image

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Singularity Image Build")
    print("=" * 60)

    try:
        image_path = build_singularity_image(
            image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
            python_version="3.11",
            force_rebuild=False,  # Set to True to force rebuild
        )
        print(f"\n✅ SUCCESS: Singularity image ready at: {image_path}")
        print("\nYou can now use this image to run tests!")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
