# Checklist TODO: Test verifies expand_modules completes without exceptions
# Checklist TODO: Test uses tmpdir to create required directory structure
# Checklist TODO: Test checks function returns valid result (not None)
import pytest
import os
from pylint.lint import expand_modules

def test_claim_c1(tmpdir):
    # Given: Create directory 'a' with a.py and b.py (all empty)
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("")

    # When: Call expand_modules with directory 'a' and required arguments
    try:
        result = expand_modules(
            str(a_dir),
            ignore_list=[],
            ignore_list_re=[],
            ignore_list_paths_re=[]
        )
    except Exception as e:
        pytest.fail(f"expand_modules raised unexpected exception: {e!r}")

    # Then: Function returns a valid result (non-None)
    assert result is not None, "Function returned None unexpectedly"
