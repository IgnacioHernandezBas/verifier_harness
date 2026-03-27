import pytest
from pylint.checkers.misc import MiscChecker
from pylint.lint import PyLinter
from pylint.reporters import CollectingReporter

@pytest.fixture
def linter():
    linter = PyLinter()
    linter.set_reporter(CollectingReporter())
    linter.register_checker(MiscChecker(linter))
    return linter

def test_claim_c1(tmpdir, linter, capsys):
    # Given: A Python file containing a comment line with a note tag consisting entirely of punctuation (e.g., '???')
    test_file = tmpdir.join("test.py")
    test_file.write("""# YES: yes
# ???: no
""")

    # When: Running pylint with --notes="YES,???" on the file
    linter.load_default_plugins()
    linter.configure_from_command_line(['--notes=YES,???'])
    linter.check([str(test_file)])

    # Then: Pylint outputs a W0511 warning for both the 'YES' and '???' note tags
    captured = capsys.readouterr()
    assert "W0511: YES: yes" in captured.out
    assert "W0511: ???: no" in captured.out

    # Test captures W0511 warnings for both 'YES' and '???' tags.
    messages = linter.reporter.messages
    assert any(msg.msg == "YES: yes" for msg in messages)
    assert any(msg.msg == "???: no" for msg in messages)

    # Test handles files without relevant comments gracefully.
    test_file_no_comments = tmpdir.join("test_no_comments.py")
    test_file_no_comments.write("""a = 1""")
    linter.check([str(test_file_no_comments)])
    messages = linter.reporter.messages
    assert not any(msg.msg_id == "W0511" for msg in messages)

    # Test confirms multiple occurrences of the same tag are reported.
    test_file_multiple_tags = tmpdir.join("test_multiple_tags.py")
    test_file_multiple_tags.write("""# YES: first
# YES: second
# ???: first
# ???: second
""")
    linter.check([str(test_file_multiple_tags)])
    messages = linter.reporter.messages
    assert sum(1 for msg in messages if msg.msg == "YES: first") == 1
    assert sum(1 for msg in messages if msg.msg == "YES: second") == 1
    assert sum(1 for msg in messages if msg.msg == "???: first") == 1
    assert sum(1 for msg in messages if msg.msg == "???: second") == 1
