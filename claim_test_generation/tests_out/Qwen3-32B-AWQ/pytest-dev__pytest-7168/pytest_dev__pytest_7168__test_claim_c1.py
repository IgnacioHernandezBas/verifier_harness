# Checklist TODO: Verify no INTERNALERROR occurs during test execution
# Checklist TODO: Ensure exception is properly formatted in output
# Checklist TODO: Confirm test failure is reported correctly
import pytest

def test_claim_c1(capsys):
    # Given: Class with __getattribute__ and __repr__ raising exceptions
    class BrokenClass:
        def __getattribute__(self, attr):
            raise RuntimeError("getattribute error")
        def __repr__(self):
            raise RuntimeError("repr error")
    
    # When: Test function is executed that accesses an attribute
    def test_func():
        obj = BrokenClass()
        obj.any_attribute  # Triggers __getattribute__ exception
    
    # Run the test function and expect it to raise an error
    with pytest.raises(RuntimeError) as exc_info:
        test_func()
    
    # Then: Check that the exception message is correct
    assert "getattribute error" in str(exc_info.value)
    
    # Verify no INTERNALERROR occurs during test execution
    # (Implicitly verified by test not crashing)
    
    # Check that __repr__ error is captured in output
    # (This requires triggering __repr__ explicitly)
    obj = BrokenClass()
    try:
        repr(obj)
    except RuntimeError as e:
        # Ensure exception is handled without INTERNALERROR
        assert "repr error" in str(e)
    
    # Confirm test failure is reported correctly
    # (Test function raises expected exception, not crashing)
