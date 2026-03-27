# Checklist TODO: Verify no exceptions during directory analysis
# Checklist TODO: Confirm function handles same-name directory/module pairs
# Checklist TODO: Ensure test doesn't depend on specific error messages
import pytest
import os
import pylint.lint.expand_modules

def test_claim_c1(tmpdir):
    # Given: Create directory 'a' with a.py and b.py (empty files)
    dir_a = tmpdir.mkdir("a")
    dir_a.join("a.py").write("")
    dir_a.join("b.py").write("")
    
    # When: Call expand_modules with directory 'a' and required parameters
    try:
        pylint.lint.expand_modules.expand_modules(
            [str(dir_a)],  # The directory path as input
            [],           # ignore_list
            [],           # ignore_list_re
            []            # ignore_list_paths_re
        )
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e!r}")
    
    # Then: No exception is raised and function completes successfully
    # (No further assertions needed as the test passes if no exception occurs)
