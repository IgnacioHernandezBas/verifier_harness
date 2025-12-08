# Running Rules Inside Singularity Container

## Problem

The verification rules system was originally designed to run on the host machine, but this causes issues for projects with C extensions (like sklearn):

- **C extensions are incompatible**: Built for Python 3.6 (container) vs Python 3.11 (host)
- **Dependencies missing**: Rules need scipy and other sklearn dependencies
- **Import errors**: Relative imports fail when modules are loaded directly

## Solution

Rules now execute **inside the Singularity container** where the project is properly set up.

## Implementation

### New Function: `run_rules_in_singularity()`

Location: `verifier/dynamic_analyzers/test_patch_singularity.py`

```python
def run_rules_in_singularity(
    repo_path: Path,
    patch_str: str,
    rule_ids: Optional[List[str]] = None,
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
    verifier_harness_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run verification rules inside a Singularity container."""
```

### How It Works

1. **Mounts two directories**:
   - `/workspace` → The patched repository (e.g., sklearn)
   - `/verifier_harness` → Your rules code

2. **Sets PYTHONPATH** to include both:
   ```
   PYTHONPATH=/workspace/.pip_packages:/workspace:/verifier_harness
   ```

3. **Executes rules CLI** inside container:
   ```bash
   singularity exec \
     --bind repo:/workspace \
     --bind verifier_harness:/verifier_harness \
     --env PYTHONPATH=... \
     image.sif \
     /opt/miniconda3/envs/testbed/bin/python \
     -m verifier.rules.runner \
     --rule all \
     --repo /workspace \
     --patch-file /workspace/.patch_for_rules.diff
   ```

4. **Parses JSON output** from rules and returns structured results

## Notebook Usage

### Updated Imports

```python
from verifier.dynamic_analyzers.test_patch_singularity import (
    run_rules_in_singularity,  # NEW!
    # ... other imports
)
from verifier.rules import RULE_IDS
```

### Updated Rules Cell

```python
if ANALYSIS_CONFIG['enable_rules']:
    # Run rules inside container
    rules_result = run_rules_in_singularity(
        repo_path=Path(repo_path),
        patch_str=sample['patch'],
        rule_ids=RULE_IDS,
        image_path=str(CONTAINER_IMAGE_PATH),
        verifier_harness_path=Path.cwd(),
    )

    # Parse and display results
    rules_results = rules_result['results']
    # ... process findings
```

## Benefits

✅ **Works with C extensions** - sklearn loads properly in container
✅ **No host dependencies** - scipy, numpy, etc. already in container
✅ **Proper imports** - sklearn modules import correctly
✅ **Dynamic execution** - Rules can call functions (rule 1, 2, 5, 7-9)
✅ **Isolated environment** - No pollution of host Python

## Rules That Benefit

- **Rule 1**: Boundary probing - executes `func(*args)`
- **Rule 2**: Predicate/MC/DC - executes functions
- **Rule 3**: State transitions - loads modules
- **Rule 4**: Definition-use - loads modules
- **Rule 5**: Resource lifecycle - executes under load
- **Rule 6**: Exception paths - loads modules
- **Rule 7**: Transaction order - executes functions
- **Rule 8**: Input validation - executes functions
- **Rule 9**: Concurrency - executes functions

## Testing

Run the updated notebook cell-26 to test. You should see:

```
================================================================================
MODULE 3: SUPPLEMENTARY VERIFICATION RULES
================================================================================

🔍 Running 9 verification rules...

🔍 Running rules in Singularity container...
  Rules: all
  Repo: scikit-learn__scikit-learn
✓ Rules executed successfully: 9 rule(s) ran
✓ Rules execution complete
  Total rules: 9
  Passed: X
  Failed: Y
  Findings: Z
```

## Troubleshooting

If rules fail:
1. Check `rules_result['stderr']` for errors
2. Verify container path is correct
3. Ensure verifier_harness directory structure is intact
4. Test rules CLI manually:
   ```bash
   cd /fs/nexus-scratch/ihbas/verifier_harness
   python -m verifier.rules.runner --rule all --repo ./repos_temp/... --patch-stdin < patch.diff
   ```
