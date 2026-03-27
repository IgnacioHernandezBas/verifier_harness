# Checklist TODO: Uses tmpdir for isolated file creation
# Checklist TODO: Runs pylint with --notes="YES,???" argument
# Checklist TODO: Verifies presence of both expected W0511 warnings
import pytest
import pylint.lint

def test_claim_c1(tmpdir, capsys):
    # Given: Create a test file with note tags
    test_file = tmpdir.join("test.py")
    test_file.write_text(
        "# TODO: YES\n"
        "# NOTE: ???\n"
        "a = 1",
        encoding="utf-8"
    )
    
    # When: Run pylint with --notes="YES,???"
    args = [
        f"--notes=YES,???",
        str(test_file)
    ]
    pylint.lint.Run(args, exit=False)
    
    # Then: Check output contains W0511 for both tags
    captured = capsys.readouterr()
    assert "W0511: 1:0: TODO: YES" in captured.out
    assert "W0511: 2:0: NOTE: ??" in captured.out
