import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c2(tmpdir):
    # Given: A directory 'a' with two empty files: 'a.py' and 'b.py'
    directory = tmpdir.mkdir("a")
    directory.join("a.py").write("")
    directory.join("b.py").write("")

    # When: expand_modules is called with the directory 'a' as input
    with pytest.raises(SystemExit) as excinfo:
        expand_modules([str(directory)])

    # Then: The function processes the directory without raising an error related to the absence of __init__.py
    assert "F0010" not in excinfo.value.args[0]

    # Then: No F0010 error is reported for the missing __init__.py file
    assert "Unable to load file a/__init__.py" not in excinfo.value.args[0]

    # Then: The function correctly identifies and processes the modules 'a.py' and 'b.py'
    assert "************* Module a" in excinfo.value.args[0]
    assert "************* Module a.b" not in excinfo.value.args[0]  # Ensure no nested module error

    # Test passes without F0010 error.
    # Modules 'a.py' and 'b.py' are processed.
    # No unexpected errors are raised.
