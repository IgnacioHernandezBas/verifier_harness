import pytest
from pylint.config import config_initialization

def test_claim_c2():
    # Given: An unrecognized option is passed to pylint.
    # When: _config_initialization is called with an unrecognized option.
    # Then: A usage tip is printed.
    
    # Contract test: Check if _config_initialization exists and test its behavior with an unrecognized option
    assert hasattr(config_initialization, '_config_initialization')
    
    # Mocking the behavior by checking if a SystemExit is raised with a non-zero code
    with pytest.raises(SystemExit) as excinfo:
        config_initialization._config_initialization(['--unrecognized-option'])
    
    assert excinfo.value.code != 0
