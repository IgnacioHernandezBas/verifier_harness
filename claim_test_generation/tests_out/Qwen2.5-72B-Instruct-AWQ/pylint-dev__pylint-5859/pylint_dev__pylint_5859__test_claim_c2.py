# Checklist TODO: Test file contains multiple note tags.
# Checklist TODO: Pylint is called with the --notes option.
# Checklist TODO: Each note tag triggers a W0511 warning.
import pytest
from pylint.checkers.misc import MiscChecker
from pylint.lint import PyLinter
from pylint.config import PylintrcConfig

@pytest.fixture
def linter():
    linter = PyLinter()
    linter.load_default_config()
    linter.load_plugin_configuration()
    return linter

@pytest.fixture
def checker(linter):
    checker = MiscChecker(linter)
    linter.register_checker(checker)
    return checker

def test_claim_c2(tmpdir, monkeypatch, capsys, linter, checker):
    # GIVEN: Multiple note tags are specified with the --notes option.
    note_tags = ["TODO", "FIXME", "???"]
    monkeypatch.setattr(linter.config, 'notes', note_tags)

    # Create a test file with multiple note tags in the tmpdir.
    test_file = tmpdir.join("test.py")
    test_file.write("""
    a = 1
    #TODO: This is a todo
    b = 2
    #FIXME: This is a fixme
    c = 3
    #??? This is a question
    """)

    # WHEN: Running pylint with the --notes option.
    linter.check([str(test_file)])

    # THEN: Pylint returns a fixme warning (W0511) for each note tag.
    captured = capsys.readouterr()
    warnings = [line for line in captured.out.splitlines() if "W0511" in line]

    # The number of warnings matches the number of note tags.
    assert len(warnings) == len(note_tags)

    # Warnings contain the correct note tag content.
    for tag in note_tags:
        assert any(tag in warning for warning in warnings)

    # Edge cases
    # Test with no note tags specified.
    monkeypatch.setattr(linter.config, 'notes', [])
    linter.check([str(test_file)])
    captured = capsys.readouterr()
    warnings = [line for line in captured.out.splitlines() if "W0511" in line]
    assert len(warnings) == 0

    # Test with an empty note tag.
    monkeypatch.setattr(linter.config, 'notes', [""])
    linter.check([str(test_file)])
    captured = capsys.readouterr()
    warnings = [line for line in captured.out.splitlines() if "W0511" in line]
    assert len(warnings) == 0

    # Test with a very long note tag.
    long_tag = "A" * 100
    monkeypatch.setattr(linter.config, 'notes', [long_tag])
    linter.check([str(test_file)])
    captured = capsys.readouterr()
    warnings = [line for line in captured.out.splitlines() if "W0511" in line]
    assert len(warnings) == 1
    assert long_tag in warnings[0]
