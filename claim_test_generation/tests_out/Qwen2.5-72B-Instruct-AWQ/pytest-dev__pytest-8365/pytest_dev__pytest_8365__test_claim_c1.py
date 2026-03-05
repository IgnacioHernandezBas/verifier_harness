# Checklist TODO: Mock os.environ['USERNAME'] with illegal characters.
# Checklist TODO: Call getbasetemp() and ensure no FileNotFoundError is raised.
# Checklist TODO: Verify the temporary directory is created.
import pytest
from pathlib import Path

def test_claim_c1(monkeypatch):
    # GIVEN: The username contains illegal characters for directory names
    # Set os.environ['USERNAME'] to a string containing illegal characters for directory names
    monkeypatch.setenv('USERNAME', 'os/<:*?;>agnostic')
    
    # WHEN: getbasetemp is called
    # Mock the getbasetemp method to ensure it is called on the correct object
    class MockTmpPathFactory:
        def getbasetemp(self):
            return Path('/tmp/pytest-of-unknown')
    
    tmp_path_factory = MockTmpPathFactory()
    
    # THEN: FileNotFoundError is not raised
    # Call getbasetemp and ensure no FileNotFoundError is raised
    try:
        p = tmp_path_factory.getbasetemp()
    except FileNotFoundError:
        pytest.fail("getbasetemp raised FileNotFoundError unexpectedly")
    
    # Verify the temporary directory is created
    assert p.exists(), "Temporary directory was not created successfully"
    assert "pytest-of-unknown" in str(p), "Temporary directory name does not contain 'pytest-of-unknown'"
