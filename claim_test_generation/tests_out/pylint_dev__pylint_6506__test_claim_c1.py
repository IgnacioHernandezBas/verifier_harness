import pytest
from pylint.config import config_initialization

def test_claim_c1():
    # Given: An unrecognized option is passed to pylint.
    # When: _config_initialization is called with an unrecognized option.
    # Then: _UnrecognizedOptionError is raised without printing a traceback.
    assert hasattr(config_initialization, '_config_initialization')
    with pytest.raises(config_initialization._UnrecognizedOptionError):
        config_initialization._config_initialization(['--unrecognized-option'])
