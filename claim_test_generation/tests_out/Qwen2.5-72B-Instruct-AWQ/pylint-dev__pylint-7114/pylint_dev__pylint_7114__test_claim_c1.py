# Checklist TODO: Test must create a module with a file of the same name.
# Checklist TODO: Test must run pylint on the created module.
# Checklist TODO: Test must verify no errors are raised during pylint execution.
import pytest
from pylint.lint import PyLinter
from pylint.lint.expand_modules import expand_modules

@pytest.fixture
def tmp_module(tmpdir):
    module_dir = tmpdir.mkdir("identical")
    module_file = module_dir.join("identical.py")
    module_file.write("import imp")
    return str(module_dir)

def test_claim_c1(tmp_module, monkeypatch, capsys):
    # GIVEN: A module with a file of the same name exists.
    # WHEN: Running pylint on the module.
    with monkeypatch.context() as m:
        m.chdir(tmp_module)
        linter = PyLinter()
        linter.load_default_plugins()
        linter.check(["identical"])
    
    # THEN: No error is raised.
    captured = capsys.readouterr()
    assert "error while code parsing" not in captured.out
    assert "error while code parsing" not in captured.err

    # THEN: The module is correctly identified and processed.
    assert "deprecated-module" in linter.stats.by_msg

    # THEN: No file not found error is raised.
    assert "No such file or directory" not in captured.out
    assert "No such file or directory" not in captured.err
