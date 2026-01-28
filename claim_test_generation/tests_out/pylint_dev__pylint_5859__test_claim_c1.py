import pytest
import pylint.checkers.misc

def test_claim_c1():
    # Given: The --notes option is set to 'YES,???'
    notes_option = 'YES,???'
    
    # When: The _fixme_pattern is compiled with the given notes
    _fixme_pattern = pylint.checkers.misc._fixme_pattern(notes_option)
    
    # Then: The _fixme_pattern should match lines starting with '# ???:'
    assert _fixme_pattern.match('# ???:')
