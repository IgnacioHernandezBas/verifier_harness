# Checklist TODO: Verify W0511 is raised for each note tag
# Checklist TODO: Confirm output capture contains exact warning messages
# Checklist TODO: Ensure import path uses correct module structure
import pytest
from pylint.checkers.misc import Checker
from pylint.testutils import set_config

def test_claim_c2(capsys):
    # Given: Multiple note tags are specified with --notes
    code = """a = 1
            # TODO
            # FIXME
            """
    # Create checker instance with configured note tags
    checker = Checker()
    with set_config(notes=["TODO", "FIXME"])(checker):
        # When: Process tokens with note tags
        checker.process_tokens([("comment", "# TODO", 2, 0),
                               ("comment", "# FIXME", 3, 0)])
        
        # Then: Verify W0511 warnings for each note tag
        messages = checker.linter.msgs
        assert len(messages) == 2
        for msg_id, line, _ in messages:
            assert msg_id == "fixme"
            assert line in (2, 3)
