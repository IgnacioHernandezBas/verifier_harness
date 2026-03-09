import pytest
from pylint.checkers.misc import NotesChecker
from pylint.lint import PyLinter
from pylint.config import PylintrcConfig

# Test must import pylint.checkers.misc successfully.
# Test must set up the --notes option and source file content.
# Test must verify fixme warnings for specified notes.

@pytest.fixture
def linter():
    linter = PyLinter()
    linter.load_default_config()
    linter.load_plugin_configuration()
    return linter

@pytest.fixture
def checker(linter):
    checker = NotesChecker(linter)
    linter.register_checker(checker)
    return checker

def test_claim_c1(tmpdir, monkeypatch, capsys, linter, checker):
    # Create a temporary source file with '# YES: yes' and '# ???: no'.
    source_file = tmpdir.join("test.py")
    source_file.write("# YES: yes\n# ???: no\n")

    # Set the --notes option to include 'YES,???'.
    monkeypatch.setattr(PylintrcConfig, 'notes', ['YES', '???'])

    # Configure the environment to mimic the repository setup.
    linter.set_option('notes', ['YES', '???'])

    # Process the tokens from the source file.
    with source_file.open() as f:
        linter.process_module(f, source_file.basename)

    # Capture the output to check for warnings.
    captured = capsys.readouterr()

    # Test must verify fixme warnings for specified notes.
    assert "W0511: YES: yes (fixme)" in captured.out
    assert "W0511: ???: no (fixme)" in captured.out

    # No other warnings are generated.
    assert len(captured.out.splitlines()) == 2

# Test with an empty source file.
def test_empty_source_file(tmpdir, monkeypatch, capsys, linter, checker):
    source_file = tmpdir.join("test.py")
    source_file.write("")

    monkeypatch.setattr(PylintrcConfig, 'notes', ['YES', '???'])
    linter.set_option('notes', ['YES', '???'])

    with source_file.open() as f:
        linter.process_module(f, source_file.basename)

    captured = capsys.readouterr()
    assert captured.out == ""

# Test with a source file that does not contain any notes.
def test_no_notes(tmpdir, monkeypatch, capsys, linter, checker):
    source_file = tmpdir.join("test.py")
    source_file.write("a = 1\nb = 2")

    monkeypatch.setattr(PylintrcConfig, 'notes', ['YES', '???'])
    linter.set_option('notes', ['YES', '???'])

    with source_file.open() as f:
        linter.process_module(f, source_file.basename)

    captured = capsys.readouterr()
    assert captured.out == ""

# Test with a note that is not specified in the --notes option.
def test_unspecified_note(tmpdir, monkeypatch, capsys, linter, checker):
    source_file = tmpdir.join("test.py")
    source_file.write("# TODO: do something")

    monkeypatch.setattr(PylintrcConfig, 'notes', ['YES', '???'])
    linter.set_option('notes', ['YES', '???'])

    with source_file.open() as f:
        linter.process_module(f, source_file.basename)

    captured = capsys.readouterr()
    assert captured.out == ""
