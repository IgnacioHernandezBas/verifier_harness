# Checklist TODO: Verify fixme warnings are generated for both specified note tags.
# Checklist TODO: Ensure no other warnings or errors are reported.
# Checklist TODO: Test with various configurations to confirm robustness.
import pytest
from pylint.checkers.misc import NotesChecker
from pylint.lint import PyLinter

def test_claim_c1(tmp_path):
    # Verify module path or update PYTHONPATH before running tests.
    # Create a temporary Python file with contents '# YES: yes' and '# ???: no'.
    test_file = tmp_path / "test.py"
    test_file.write_text("# YES: yes\n# ???: no\n")

    # Set the --notes option to include 'YES,???' in the pylint configuration.
    linter = PyLinter()
    linter.config.notes = ['YES', '???']
    notes_checker = NotesChecker(linter)
    linter.register_checker(notes_checker)

    # WHEN: pylint.process_tokens is called with tokens containing '# YES: yes' and '# ???: no'.
    linter.check([str(test_file)])

    # THEN: pylint should return fixme warnings for both lines containing '# YES: yes' and '# ???: no'.
    messages = linter.reporter.messages
    assert len(messages) == 2
    assert messages[0].msg_id == 'fixme'
    assert messages[0].line == 1
    assert messages[0].msg == 'YES: yes'
    assert messages[1].msg_id == 'fixme'
    assert messages[1].line == 2
    assert messages[1].msg == '???: no'

    # Ensure no other warnings or errors are reported.
    assert len(linter.reporter.messages) == 2

    # Test with empty lines in the source file.
    test_file.write_text("# YES: yes\n\n# ???: no\n")
    linter.check([str(test_file)])
    messages = linter.reporter.messages
    assert len(messages) == 4

    # Test with multiple occurrences of '# YES: yes' and '# ???: no'.
    test_file.write_text("# YES: yes\n# ???: no\n# YES: yes\n# ???: no\n")
    linter.check([str(test_file)])
    messages = linter.reporter.messages
    assert len(messages) == 8

    # Test with different casing for the note tags.
    test_file.write_text("# yes: yes\n# ????: no\n")
    linter.check([str(test_file)])
    messages = linter.reporter.messages
    assert len(messages) == 8  # No new fixme warnings should be generated
