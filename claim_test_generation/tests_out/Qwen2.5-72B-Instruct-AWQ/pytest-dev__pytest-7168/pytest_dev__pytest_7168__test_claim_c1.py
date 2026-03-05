import pytest
from src._pytest._io.saferepr import SafeRepr

# Test SafeRepr handling of exceptions in __repr__
def test_claim_c1(monkeypatch):
    # Create an object with a __repr__ method that raises an exception
    class BrokenRepr:
        def __repr__(self):
            raise ValueError("This is a test exception")

    # Define the exception to be raised (e.g., ValueError with a specific message)
    obj = BrokenRepr()

    # Test must import SafeRepr from src._pytest._io.saferepr
    saferepr = SafeRepr()

    # Test must create an object that raises an exception on __repr__
    result = saferepr.repr(obj)

    # Test must verify the output string contains exception info
    assert "ValueError" in result  # String contains the type of the exception
    assert "This is a test exception" in result  # String contains the message of the exception

    # Test with an object that raises a different exception (e.g., TypeError)
    class BrokenReprTypeError:
        def __repr__(self):
            raise TypeError("This is a TypeError test exception")

    obj_type_error = BrokenReprTypeError()
    result_type_error = saferepr.repr(obj_type_error)
    assert "TypeError" in result_type_error  # String contains the type of the exception
    assert "This is a TypeError test exception" in result_type_error  # String contains the message of the exception

    # Test with an object that raises a SystemExit or KeyboardInterrupt
    class BrokenReprSystemExit:
        def __repr__(self):
            raise SystemExit("This is a SystemExit test exception")

    obj_system_exit = BrokenReprSystemExit()
    result_system_exit = saferepr.repr(obj_system_exit)
    assert "SystemExit" in result_system_exit  # String contains the type of the exception
    assert "This is a SystemExit test exception" in result_system_exit  # String contains the message of the exception

    class BrokenReprKeyboardInterrupt:
        def __repr__(self):
            raise KeyboardInterrupt("This is a KeyboardInterrupt test exception")

    obj_keyboard_interrupt = BrokenReprKeyboardInterrupt()
    result_keyboard_interrupt = saferepr.repr(obj_keyboard_interrupt)
    assert "KeyboardInterrupt" in result_keyboard_interrupt  # String contains the type of the exception
    assert "This is a KeyboardInterrupt test exception" in result_keyboard_interrupt  # String contains the message of the exception

    # Test with an object that has no __repr__ method
    class NoRepr:
        pass

    obj_no_repr = NoRepr()
    result_no_repr = saferepr.repr(obj_no_repr)
    assert "<NoRepr object at" in result_no_repr  # Default representation for objects without __repr__
