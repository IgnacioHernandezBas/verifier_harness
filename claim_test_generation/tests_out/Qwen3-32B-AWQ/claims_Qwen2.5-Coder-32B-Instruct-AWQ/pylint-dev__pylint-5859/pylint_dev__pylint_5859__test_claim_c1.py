# Checklist TODO: Verify both fixme warnings are emitted for specified tags
# Checklist TODO: Confirm tmpfile contents match input tokens
# Checklist TODO: Validate output format matches pylint warning structure
import pytest
import tokenize
from io import StringIO
from pylint.checkers.misc import MiscChecker
from pylint.lint import PyLinter

def test_claim_c1(tmpdir, capsys):
    # Given: Create a temporary file with the code
    code = """a = 1
# YES: yes
# ???: no
"""
    tmpfile = tmpdir.join("test.py")
    tmpfile.write(code)

    # When: Configure linter and process tokens
    linter = PyLinter()
    linter.set_option("notes", ["YES", "???"])
    checker = MiscChecker()
    checker.linter = linter
    linter.add_checker(checker)

    # Tokenize the code
    with StringIO(code) as f:
        tokens = list(tokenize.generate_tokens(f.readline))

    # Process tokens
    checker.process_tokens(tokens)

    # Then: Check output for both warnings
    captured = capsys.readouterr()
    assert "W0511: YES: yes (fixme)" in captured.out
    assert "W0511: ???: no (fixme)" in captured.out
