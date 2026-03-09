import pytest
from pylint.checkers import misc
from pylint import lint

# Checklist
# Test returns fixme warnings for both lines
# Fixme warnings contain correct note tags
# Test handles edge cases correctly

def test_claim_c1(capsys):
    # Given
    # The --notes option is set to include 'YES,???' and the source file contains '# YES: yes' and '# ???: no'.
    notes = ['YES', '???']
    code = """# YES: yes
# ???: no"""

    # When
    # pylint.process_tokens is called with tokens containing '# YES: yes' and '# ???: no'.
    linter = lint.PyLinter()
    linter.set_option('notes', notes)
    linter.check([misc.MiscChecker(linter)])
    linter.feed(code)
    linter.feed('')
    linter.close()

    # Then
    # pylint should return fixme warnings for both lines.
    captured = capsys.readouterr()
    assert "fixme" in captured.out
    assert "YES" in captured.out
    assert "???" in captured.out

    # Edge cases
    # Empty --notes option
    linter.set_option('notes', [])
    linter.feed(code)
    linter.feed('')
    linter.close()
    captured = capsys.readouterr()
    assert "fixme" not in captured.out

    # Tokens without note tags
    code = """# foo: bar"""
    linter.set_option('notes', notes)
    linter.feed(code)
    linter.feed('')
    linter.close()
    captured = capsys.readouterr()
    assert "fixme" not in captured.out

    # Tokens with invalid note tags
    code = """# invalid: note"""
    linter.set_option('notes', notes)
    linter.feed(code)
    linter.feed('')
    linter.close()
    captured = capsys.readouterr()
    assert "fixme" not in captured.out
