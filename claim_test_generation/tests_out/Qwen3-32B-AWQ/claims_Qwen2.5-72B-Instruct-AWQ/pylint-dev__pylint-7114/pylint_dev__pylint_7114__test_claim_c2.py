# Checklist TODO: Verify directory is processed without __init__.py
# Checklist TODO: Confirm output includes both a.py and b.py modules
# Checklist TODO: Ensure no parsing errors for missing __init__.py
import pytest
import pylint.lint.expand_modules as expand_modules

def test_claim_c2(tmpdir, capsys):
    # Given: Create directory 'a' with a.py and b.py, no __init__.py
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("")

    # When: Call expand_modules with directory 'a' and required parameters
    try:
        result = expand_modules.expand_modules(
            ["a"],  # modules
            [],     # ignore_list
            [],     # ignore_list_re
            []      # ignore_list_paths_re
        )
    except Exception as e:
        pytest.fail(f"Function raised unexpected exception: {e!r}")

    # Then: Verify no errors about missing __init__.py in output
    captured = capsys.readouterr()
    assert "error while code parsing" not in captured.err
    assert "no __init__.py" not in captured.err
    assert "F0010" not in captured.err  # Pylint error code for parsing errors
