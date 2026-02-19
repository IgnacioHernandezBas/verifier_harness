# Checklist TODO: Test module imports correctly.
# Checklist TODO: Verify fixme warnings are generated for specified tags.
# Checklist TODO: Ensure no false positives for non-matching tags.
import pytest
from pylint.checkers.misc import MiscChecker
from pylint.lint import PyLinter
from pylint.utils import tokenize_module

def test_claim_c1(tmpdir):
    # Test module imports correctly.
    from pylint.checkers.misc import MiscChecker

    # Create a temporary file with contents '# YES: yes' and '# ???: no'.
    test_file = tmpdir.join("test.py")
    test_file.write("# YES: yes\n# ???: no\n")

    # Set the --notes option to include 'YES,???' in the pylint configuration.
    linter = PyLinter()
    linter.load_default_plugins()
    linter.set_option('notes', ['YES', '???'])
    checker = MiscChecker(linter)
    linter.register_checker(checker)

    # Given: The --notes option is set to include 'YES,???' and the source file contains '# YES: yes' and '# ???: no'.
    # When: pylint.process_tokens is called with tokens containing '# YES: yes' and '# ???: no'.
    with open(test_file, 'r') as f:
        tokens = tokenize_module(f.read(), test_file.strpath)

    # Then: pylint should return fixme warnings for both lines.
    with pytest.raises(AssertionError) as excinfo:
        linter.check([test_file.strpath])
    assert "W0511: YES: yes (fixme)" in str(excinfo.value)
    assert "W0511: ???: no (fixme)" in str(excinfo.value)

    # Ensure no false positives for non-matching tags.
    test_file.write("# OTHER: no\n")
    with open(test_file, 'r') as f:
        tokens = tokenize_module(f.read(), test_file.strpath)
    with pytest.raises(AssertionError) as excinfo:
        linter.check([test_file.strpath])
    assert "W0511: OTHER: no (fixme)" not in str(excinfo.value)
