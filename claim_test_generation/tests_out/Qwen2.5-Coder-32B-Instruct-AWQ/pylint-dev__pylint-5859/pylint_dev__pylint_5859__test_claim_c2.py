# Checklist TODO: Test file contains multiple note tags.
# Checklist TODO: Pylint command includes --notes option with multiple tags.
# Checklist TODO: Each note tag results in a W0511 warning.
import pytest
from pylint.checkers.misc import MiscChecker
from pylint.testutils import CheckerTestCase, MessageTest, set_config

def test_claim_c2(monkeypatch, capsys):
    # Test file contains multiple note tags.
    test_code = """
    a = 1  # FIXME
    b = 2  # TODO
    c = 3  # ???
    """

    # Pylint command includes --notes option with multiple tags.
    monkeypatch.setattr(MiscChecker, 'config', {'notes': ['FIXME', 'TODO', '???']})

    # Create a test case for the MiscChecker
    class TestMiscChecker(CheckerTestCase):
        CHECKER_CLASS = MiscChecker

        @set_config(notes=['FIXME', 'TODO', '???'])
        def test_multiple_note_tags(self):
            # Given: Multiple note tags are specified with the --notes option.
            # When: Running pylint with the --notes option.
            # Then: Pylint returns a fixme warning (W0511) for each note tag.
            with self.assertAddsMessages(
                MessageTest(msg_id="fixme", line=2, args="FIXME", col_offset=8),
                MessageTest(msg_id="fixme", line=3, args="TODO", col_offset=8),
                MessageTest(msg_id="fixme", line=4, args="???", col_offset=8),
            ):
                self.checker.process_tokens(_tokenize_str(test_code))

    # Run the test case
    test_case = TestMiscChecker()
    test_case.setUp()
    test_case.test_multiple_note_tags()
    test_case.tearDown()
