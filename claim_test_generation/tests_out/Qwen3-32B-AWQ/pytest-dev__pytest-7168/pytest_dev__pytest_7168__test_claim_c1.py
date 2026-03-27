# Checklist TODO: Test demonstrates safe handling of bad __repr__
# Checklist TODO: Output contains formatted exception information
# Checklist TODO: Pytest process remains stable after encountering error
import pytest
import os
import sys
import types

def test_claim_c1(tmpdir, capsys):
    # GIVEN: Create module with class having __repr__ that raises Exception
    test_module = tmpdir.join("test_bad_repr.py")
    test_module.write_text('''
        class BadRepr:
            def __repr__(self):
                raise Exception("test error")
        def test_bad_repr():
            obj = BadRepr()
    ''', encoding='utf-8')
    
    # WHEN: Run pytest on the module
    sys.path.insert(0, str(tmpdir))
    try:
        pytest.main([str(test_module)])
    finally:
        sys.path.pop(0)
    
    # THEN: Capture output and verify exception handling
    out, err = capsys.readouterr()
    combined = out + err
    
    # Check for exception type and value in output
    assert "Exception: test error" in combined
    
    # Verify pytest process stability (test collection completed)
    assert "collected 1 item" in combined
    
    # Verify _format_repr_exception processing indicator
    assert "saferepr" in combined.lower()
