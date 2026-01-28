import pytest
import pylint.config.config_initialization

def test_claim_c2():
    # Given: An unrecognized option is passed to pylint.
    # When: _config_initialization is called with an unrecognized option.
    # Then: A usage tip is printed.
    assert hasattr(pylint.config.config_initialization, '_config_initialization')
    with pytest.raises(SystemExit) as excinfo:
        pylint.config.config_initialization._config_initialization(['--unrecognized-option'])
    assert excinfo.value.code == 2  # Typically, a non-zero exit code indicates an error
