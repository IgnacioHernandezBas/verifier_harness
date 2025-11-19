#!/usr/bin/env python3
"""
Test script to verify Docker authentication support implementation.
"""
import sys
from swebench_singularity.singularity_builder import SingularityBuilder

def test_builder_methods():
    """Test that the new methods exist and are callable."""
    print("Testing SingularityBuilder implementation...")

    builder = SingularityBuilder()

    # Check that new methods exist
    assert hasattr(builder, 'check_docker_available'), "Missing check_docker_available method"
    assert hasattr(builder, 'docker_pull'), "Missing docker_pull method"
    assert hasattr(builder, 'build_from_docker_daemon'), "Missing build_from_docker_daemon method"

    print("✓ All new methods exist")

    # Test check_docker_available
    docker_available = builder.check_docker_available()
    print(f"✓ check_docker_available() returned: {docker_available}")

    # Test check_singularity_available
    singularity_available = builder.check_singularity_available()
    print(f"✓ check_singularity_available() returned: {singularity_available}")

    print("\n✓ All basic tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_builder_methods()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
