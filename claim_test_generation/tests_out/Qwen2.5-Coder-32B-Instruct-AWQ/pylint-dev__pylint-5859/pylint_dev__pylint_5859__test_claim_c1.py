import pytest
from pylint.checkers.misc import MiscChecker
from pylint.testutils import CheckerTestCase, MessageTest, set_config
from pylint.utils import tokenize_module

class TestPylintFixmeWarning(CheckerTestCase):
    CHECKER_CLASS = MiscChecker

    @set_config(notes=["???"])
    def test_claim_c1(self, capsys):
        # Given: A note tag specified with the --notes option is entirely punctuation.
        code = """a = 1
                #???
                """
        # When: Running pylint with the --notes option.
        with self.assertAddsMessages(
            MessageTest(msg_id="fixme", line=2, args="???", col_offset=17)
        ):
            self.checker.process_tokens(tokenize_module(code))

        # Then: Pylint returns a fixme warning (W0511) for the note tag.
        captured = capsys.readouterr()
        assert "W0511: fixme" in captured.out

        # Test captures W0511 warning for punctuation-only note tags.
        # Verify no W0511 warning for non-punctuation note tags.
        code_no_punctuation = """a = 1
                                # TODO: fix this
                                """
        with self.assertNoMessages():
            self.checker.process_tokens(tokenize_module(code_no_punctuation))

        # Ensure correct handling of empty note tags.
        code_empty_tag = """a = 1
                            # 
                            """
        with self.assertNoMessages():
            self.checker.process_tokens(tokenize_module(code_empty_tag))
