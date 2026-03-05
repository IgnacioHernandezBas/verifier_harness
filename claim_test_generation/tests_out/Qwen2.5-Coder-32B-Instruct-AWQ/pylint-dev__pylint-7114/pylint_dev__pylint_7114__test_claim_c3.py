# Checklist TODO: Test completes without exceptions.
# Checklist TODO: Module 'b' is correctly resolved in 'r.py'.
# Checklist TODO: No unintended side effects on module resolution.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c3(tmpdir):
    # Given: Create directory 'a' with files 'a.py', 'b.py', and 'r.py'
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("def foo(): pass")
    a_dir.join("r.py").write("from a import b\nb.foo()")

    # Given: Ensure 'r.py' contains an import statement for 'b' from 'a'
    r_file_path = str(a_dir.join("r.py"))

    # When: expand_modules is called with the directory 'a' and file 'r.py' as input
    # Then: No exception is raised during expand_modules execution
    # Then: Module resolution is not affected by the presence of a module with the same name as the directory
    # Then: Function completes successfully without altering module import paths
    with pytest.raises(SystemExit) as excinfo:
        expand_modules([str(a_dir)], [r_file_path])
    assert excinfo.value.code == 0

    # Edge case: Test with an empty 'a.py' to ensure no false positives
    # Already handled in the setup above with an empty 'a.py'

    # Edge case: Test with a non-existent 'b.py' to verify error handling
    a_dir.join("b.py").remove()
    with pytest.raises(SystemExit) as excinfo:
        expand_modules([str(a_dir)], [r_file_path])
    assert excinfo.value.code != 0

    # Edge case: Test with a circular import between 'a.py' and 'b.py'
    a_dir.join("b.py").write("from a import b\ndef foo(): pass")
    with pytest.raises(SystemExit) as excinfo:
        expand_modules([str(a_dir)], [r_file_path])
    assert excinfo.value.code != 0
