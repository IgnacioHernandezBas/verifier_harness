# verifier/utils/diff_utils.py
from typing import Dict, List, Tuple
import re
import argparse
import json
from pathlib import Path

# Regular expression to detect diff hunk line info like "@@ -10,7 +10,8 @@"
HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

def parse_unified_diff(diff_text: str) -> Dict[str, List[Tuple[int, int]]]:
  """
      Lightweight parser for Git unified diff text focused on code changes.

      This function extracts only the essential structural information from a diff:
      - The path of each modified file (from the "+++ b/..." header).
      - The line ranges of modified regions in the *new version* of each file
        (from hunk headers of the form "@@ -a,b +c,d @@").

      It intentionally ignores non-code elements such as:
      - File metadata (index hashes, permissions, etc.)
      - Merge conflict markers (<<<<<<, ======, >>>>>>)
      - Renames, binary diffs, or non-textual metadata lines.

      This design makes it suitable for static analysis pipelines that only need
      to locate where code has been changed (e.g., syntax or AST verification),
      without applying or merging patches.

      Args:
          diff_text (str): The unified diff string (e.g., from Git or an LLM patch).

      Returns:
          Dict[str, List[Tuple[int, int]]]: A dictionary mapping each modified file
          path to a list of (start_line, end_line) tuples representing modified
          regions in the *new* file version.
  """
  
  result = {}
  current_file = None

  for line in diff_text.splitlines():
      if line.startswith("+++ "):  # new file header
          path = line[4:].strip()
          if path.startswith("b/"):  # Git diffs usually prefix new files with b/
              path = path[2:]
          current_file = path
          result.setdefault(current_file, [])
      elif line.startswith("@@"):  # hunk header with line info
          match = HUNK_RE.search(line)
          if match and current_file:
              start = int(match.group(1))
              length = int(match.group(2) or "1")
              result[current_file].append((start, start + length - 1))

  return result

def filter_paths_to_py(paths: List[str]) -> List[str]:
    """
      Return only Python (.py) files from a list. 
      We will be analyzing only Python code.
      Args:
          paths (List[str]): List of file paths.
      Returns:
          List[str]: Filtered list containing only .py files.

    """
    return [p for p in paths if p.endswith(".py")]

# ---------------------------------------------------
# Standalone test mode
# ---------------------------------------------------
if __name__ == "__main__":
  # Load your sample JSON (the one you pasted)
  data = json.load(open("swebench_integration/data/swebench_sample.json", encoding="utf-8"))[0]

  # Extract the patch string
  diff_text = data["patch"]

  # Parse the diff
  parsed = parse_unified_diff(diff_text)
  print("Parsed diff:")
  print(json.dumps(parsed, indent=2))

  # Filter to .py files
  print("Python files only:", filter_paths_to_py(list(parsed.keys())))

