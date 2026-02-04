from __future__ import annotations

from claim_extraction.pipeline.issue_context import (
    build_issue_context,
    link_claim_to_issue_context,
)


def test_issue_context_extraction_and_linking() -> None:
    problem_statement = """
Steps to reproduce

```python
def buggy():
    print("bad output")
```

Run `pylint test.py --notes="YES,???"`
$ pytest tests/test_cli.py

Expected behavior:
************* Module pylint.test
W0511 TODO

Traceback (most recent call last):
  File "pkg/module.py", line 10, in run
    raise ValueError("boom")
ValueError: boom

The crash happens inside Foo.bar defined in pkg/module.py
"""

    issue_context = build_issue_context(problem_statement)

    assert len(issue_context["code_blocks"]) == 1
    assert issue_context["code_blocks"][0]["lang"] == "python"
    assert len(issue_context["cli_commands"]) == 2
    assert issue_context["cli_commands"][0]["command"] == 'pylint test.py --notes="YES,???"'
    assert len(issue_context["expected_output_blocks"]) == 1
    assert "W0511" in issue_context["expected_output_blocks"][0]["content"]
    assert len(issue_context["tracebacks"]) == 1
    assert "pkg/module.py" in issue_context["inline_code_refs"]["paths"]
    assert "Foo.bar" in issue_context["inline_code_refs"]["symbols"]

    claim = {
        "claim_id": "C1",
        "claim_type": "exception",
        "claim_text": "Running pylint should not emit W0511 or raise ValueError.",
        "given": "Buggy setup with `pylint test.py --notes=\"YES,???\"`",
        "when": "execute pytest after linting",
        "then": "no traceback is shown",
        "target_symbols": ["Foo.bar"],
        "confidence": "high",
        "evidence": {
            "spans": [
                "`pylint test.py --notes=\"YES,???\"`",
                "************* Module pylint.test\\nW0511 TODO",
                "Traceback (most recent call last):\\n  File \"pkg/module.py\", line 10, in run\\n    raise ValueError(\"boom\")",
                "def buggy():\\n    print(\"bad output\")",
            ]
        },
    }

    refs = link_claim_to_issue_context(claim, issue_context)
    assert refs["cli_command_ids"] == [0]
    assert refs["expected_output_block_ids"] == [0]
    assert refs["traceback_ids"] == [0]
    assert refs["code_block_ids"] == [0]
