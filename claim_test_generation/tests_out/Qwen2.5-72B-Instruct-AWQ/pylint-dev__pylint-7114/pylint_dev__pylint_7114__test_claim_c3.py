# Checklist TODO: Create a module with a file of the same name in a temp dir.
# Checklist TODO: Run pylint on the module and capture the output.
# Checklist TODO: Assert no fatal error is raised in the output.
import pytest
from pylint.lint import PyLinter
from pylint.lint.expand_modules import expand_modules

@pytest.fixture
def initialized_linter():
    linter = PyLinter()
    linter.load_default_config()
    return linter

def test_claim_c3(tmpdir, initialized_linter):
    # GIVEN: A module with a file of the same name exists.
    module_dir = tmpdir.mkdir("identical")
    module_file = module_dir.join("identical.py")
    module_file.write("import imp")

    # WHEN: Running pylint on the module.
    with tmpdir.as_cwd():
        initialized_linter.check(["identical"])

    # THEN: No fatal error is raised.
    assert not initialized_linter.stats.by_msg.get("F0010")
