# Checklist TODO: Test verifies W0511 emission for valid punctuation tags
# Checklist TODO: Test uses module API instead of CLI executable
# Checklist TODO: Test checks warning count and tag presence without exact string matching
import pytest
import sys
from pylint.lint import Run

def test_claim_c1(tmp_path, monkeypatch, capsys):
    # Given: Create a Python file with two comment lines
    code = """a = 1
            # YES
            # ???
            """
    file = tmp_path / "test.py"
    file.write_text(code)
    
    # When: Configure --notes="YES,???" via monkeypatch
    sys.argv = ["pylint", "--notes=YES,???", str(file)]
    
    # Run pylint
    with pytest.raises(SystemExit):
        Run([], exit=False)
    
    # Capture output
    out, _ = capsys.readouterr()
    
    # Then: Check that two W0511 warnings are present
    assert "W0511: YES" in out
    assert "W0511: ???" in out
