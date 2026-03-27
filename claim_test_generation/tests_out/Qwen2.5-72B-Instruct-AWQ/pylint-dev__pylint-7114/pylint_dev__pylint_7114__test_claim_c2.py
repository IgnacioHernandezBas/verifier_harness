# Checklist TODO: Test setup creates required directory structure.
# Checklist TODO: expand_modules processes the directory without raising F0010.
# Checklist TODO: Output confirms no F0010 errors.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c2(tmpdir, monkeypatch, capsys):
    # Given: A directory 'a' containing 'a.py' but no __init__.py
    a_dir = tmpdir.mkdir('a')
    a_py = a_dir.join('a.py')
    a_py.write('print("Hello, world!")')

    # When: Processing the directory through expand_modules' file resolution logic
    with monkeypatch.context() as m:
        m.chdir(tmpdir)
        modules = expand_modules(['a'])

    # Then: No F0010 exceptions are raised about missing __init__.py
    captured = capsys.readouterr()
    assert "F0010" not in captured.out
    assert "F0010" not in captured.err
    assert modules == ['a.a']
