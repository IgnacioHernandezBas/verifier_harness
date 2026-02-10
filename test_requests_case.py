#!/usr/bin/env python3
"""
Test the specific case that was failing: requests.models.Response.iter_content
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, "/fs/nexus-scratch/ihbas/repos_claim_cache/psf__requests/fe693c492242ae532211e0c173324f09ca8cf227")

from agentic_closed_loop.guardrails import _execute_probe

try:
    import requests.models

    print("=" * 70)
    print("TESTING ACTUAL requests.models.Response.iter_content")
    print("=" * 70)

    # Get the iter_content method the same way the guardrail does
    Response = requests.models.Response
    iter_content_method = getattr(Response, 'iter_content')

    print(f"\nMethod: {iter_content_method}")
    print(f"Type: {type(iter_content_method)}")

    # Test the probe
    probe_ok, message = _execute_probe('iter_content', iter_content_method)

    print(f"\nProbe result: {probe_ok}")
    print(f"Message: {message}")

    if probe_ok and "Instance/class method" in message:
        print("\n✓ SUCCESS: Instance method correctly detected and skipped!")
        sys.exit(0)
    elif probe_ok:
        print("\n✓ ACCEPTABLE: Method skipped (though not flagged as instance method)")
        sys.exit(0)
    else:
        print(f"\n✗ FAILURE: Probe failed when it should have been skipped")
        print(f"   This means the guardrail would still block test generation!")
        sys.exit(1)

except ImportError as e:
    print(f"Could not import requests.models: {e}")
    print("This is expected if the repo is not at the specified path.")
    print("Skipping this test.")
    sys.exit(0)
