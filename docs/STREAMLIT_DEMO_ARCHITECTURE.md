# Streamlit Demo App Architecture

## Overview

The E6 Verifier Harness Demo App is a Streamlit-based web application that allows users to test code patches using comprehensive static analysis and unit testing. It supports two modes of operation:

1. **SWE-bench Instance Testing**: Select and test patches from the SWE-bench Verified dataset
2. **Custom Codebase Testing**: Upload custom codebases and patches for analysis

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Interface                   │
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  SWE-bench Mode  │         │   Custom Mode    │          │
│  │                  │         │                  │          │
│  │ • Load Instances │         │ • Upload ZIP     │          │
│  │ • Select Instance│         │ • Paste Patch    │          │
│  │ • View Patch     │         │ • Configure Tests│          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                            │                     │
│           └────────────┬───────────────┘                     │
│                        │                                     │
│                        ▼                                     │
│           ┌────────────────────────┐                         │
│           │  Analysis Orchestrator │                         │
│           │                        │                         │
│           │ • Clone/Extract Repo   │                         │
│           │ • Apply Patch          │                         │
│           │ • Run Static Analysis  │                         │
│           │ • Run Unit Tests       │                         │
│           └───────────┬────────────┘                         │
│                       │                                      │
└───────────────────────┼──────────────────────────────────────┘
                        │
          ┌─────────────┴──────────────┐
          │                            │
          ▼                            ▼
┌──────────────────┐         ┌──────────────────┐
│ Static Analyzers │         │  Test Executor   │
│                  │         │                  │
│ • Pylint         │         │ • Pytest         │
│ • Flake8         │         │ • Django Tests   │
│ • Radon          │         │ • Unittest       │
│ • Mypy           │         │                  │
│ • Bandit         │         │ • Parse Results  │
└──────────────────┘         └──────────────────┘
          │                            │
          └─────────────┬──────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │   Results Aggregator    │
          │                         │
          │ • SQI Score             │
          │ • Test Pass/Fail        │
          │ • Issue Breakdown       │
          │ • History Tracking      │
          └─────────────────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │  Visualization Layer    │
          │                         │
          │ • Metrics Display       │
          │ • Issue Lists           │
          │ • Test Output           │
          │ • Analysis History      │
          └─────────────────────────┘
```

## Component Breakdown

### 1. Frontend Layer (Streamlit UI)

#### SWE-bench Mode
- **Instance Loader**: Loads instances from HuggingFace dataset
- **Instance Selector**: Browse and select specific instances
- **Patch Viewer**: Display problem statements and patches

#### Custom Mode
- **File Upload**: Accept ZIP archives of Git repositories
- **Patch Input**: Support both file upload and text paste
- **Test Configuration**: Optional custom test commands

### 2. Analysis Orchestrator

Central component that coordinates the entire analysis workflow:

```python
def analyze_patch(repo_path: Path, patch_str: str) -> Dict:
    """
    Orchestrates the complete analysis pipeline:
    1. Static analysis
    2. Unit test execution
    3. Result aggregation
    """
```

Key responsibilities:
- Repository setup (clone or extract)
- Patch application using `git apply`
- Coordination of analysis modules
- Result aggregation and storage

### 3. Static Analysis Module

Uses the existing `verifier/static_analyzers/code_quality.py` module:

```python
from verifier.static_analyzers.code_quality import analyze as run_static_analysis

static_results = run_static_analysis(str(repo_path), patch_str)
```

#### Analyzers Included:

1. **Pylint** (Weight: 50%)
   - Code quality and style issues
   - Returns score 0-10 and detailed issue list

2. **Radon** (Weight: 25%)
   - Cyclomatic complexity per function
   - Maintainability Index (MI) per file

3. **Flake8** (Weight: 15%)
   - PEP8 style compliance
   - Categorized by error codes (F, E, W, C, N, D)

4. **Mypy** (Weight: 5%)
   - Type checking errors
   - Optional type hints validation

5. **Bandit** (Weight: 5%)
   - Security vulnerability detection
   - Severity levels: HIGH, MEDIUM, LOW

#### Static Quality Index (SQI)

Aggregate metric computed as weighted average:

```
SQI = Σ(weight_i × normalized_score_i)

where:
- Each analyzer score is normalized to [0, 100]
- Weights sum to 1.0
- Final SQI ranges from 0 to 100
```

Classification:
- **Excellent**: SQI ≥ 85
- **Good**: 70 ≤ SQI < 85
- **Fair**: 50 ≤ SQI < 70
- **Poor**: SQI < 50

### 4. Test Execution Module

Automatic test framework detection and execution:

```python
def run_tests_in_repo(repo_path: Path, test_command: Optional[str] = None) -> Dict:
    """
    Detects and runs tests using appropriate framework:
    - Pytest (if pytest.ini or setup.py exists)
    - Django (if manage.py exists)
    - Custom command (if provided)
    """
```

#### Features:
- **Framework Auto-detection**: Pytest, Django, Unittest
- **Timeout Protection**: 5-minute timeout per test run
- **Result Parsing**: Extracts pass/fail/error counts
- **Output Capture**: Full stdout/stderr for debugging

### 5. Results Display Module

Comprehensive visualization of analysis results:

#### Static Analysis Display
- **SQI Score Card**: Overall quality metric
- **Component Breakdown**: Individual analyzer scores
- **Issue Lists**: Expandable sections for each analyzer
- **File-level Details**: Issues grouped by file

#### Test Results Display
- **Test Summary**: Pass/fail/error counts
- **Pass Rate**: Visual progress bar
- **Test Output**: Full stdout/stderr in expandable sections

### 6. Session State Management

Streamlit session state tracks:
- `analysis_results`: History of all analyses
- `swebench_instances`: Loaded SWE-bench instances
- User selections and configurations

## Data Flow

### SWE-bench Mode Flow

```
User → Select Instance → Load from Dataset → Clone Repo →
Apply Patch → Run Analysis → Display Results → Store in History
```

1. **Load Instances**: Query HuggingFace dataset
2. **Select Instance**: User chooses from dropdown
3. **Clone Repository**: Use `PatchLoader` to clone at specific commit
4. **Apply Patch**: Use existing patch application logic
5. **Analyze**: Run static analysis + unit tests
6. **Display**: Show comprehensive results
7. **Store**: Add to session history

### Custom Mode Flow

```
User → Upload ZIP + Patch → Extract Repo → Apply Patch →
Run Analysis → Display Results → Store in History → Cleanup
```

1. **Upload Files**: ZIP archive + patch file/text
2. **Extract**: Unzip to temporary directory
3. **Detect Repo**: Find `.git` directory in extracted files
4. **Apply Patch**: Use `git apply` command
5. **Analyze**: Run static analysis + unit tests
6. **Display**: Show comprehensive results
7. **Store**: Add to session history
8. **Cleanup**: Remove temporary files

## File Structure

```
streamlit/
├── app.py                          # Main Streamlit application
├── modules/
│   ├── loading/
│   │   ├── dataset_loader.py       # (Legacy) SWE-bench loading
│   │   └── patch_loader.py         # (Legacy) Patch application
│   ├── static_eval/
│   │   └── static_modules/
│   │       ├── code_quality.py     # (Legacy) Static analyzers
│   │       └── syntax_structure.py # (Legacy) Syntax checking
│   └── utils/
│       └── diff_utils.py           # (Legacy) Diff parsing
└── pages/                          # (Legacy) Multi-page structure
    ├── data_loader_patcher.py
    ├── results_viewer.py
    └── static_verifier.py
```

**Note**: The new `app.py` consolidates functionality and uses the main verifier modules directly.

## Integration Points

### With Existing Verifier Harness

1. **Static Analysis**: Uses `verifier.static_analyzers.code_quality`
2. **Dataset Loading**: Uses `swebench_integration.DatasetLoader`
3. **Patch Application**: Uses `swebench_integration.PatchLoader`

### Future Integration Opportunities

1. **Singularity Containers**: For isolated test execution
2. **Dynamic Fuzzing**: Add Hypothesis-based fuzzing tests
3. **Verification Rules**: Add 9 verification rules
4. **Cluster Jobs**: Submit long-running analyses to SLURM
5. **Results Database**: Persist results across sessions

## Configuration

### Environment Requirements

```bash
# Required packages
streamlit>=1.28.0
pylint>=2.17.0
flake8>=6.0.0
radon>=5.1.0
mypy>=1.0.0
bandit>=1.7.0
pytest>=7.0.0  # For test execution
```

### Run Commands

```bash
# Development mode (auto-reload)
streamlit run streamlit/app.py

# Production mode (with port)
streamlit run streamlit/app.py --server.port 8501

# With custom config
streamlit run streamlit/app.py --server.maxUploadSize 200
```

## Security Considerations

### Patch Application Safety

- **Git Operations**: All patches applied via `git apply` in isolated directories
- **Temporary Files**: Custom codebases extracted to temp directories
- **Cleanup**: Automatic cleanup of temporary files after analysis

### Code Execution Safety

- **Test Timeouts**: 5-minute timeout prevents infinite loops
- **Sandboxing**: Tests run in repository directory only
- **No Arbitrary Code**: Static analysis doesn't execute user code

### Upload Limits

- **File Size**: Streamlit default max upload size (200MB)
- **File Types**: Restricted to `.zip` for codebases, `.diff/.patch/.txt` for patches

## Performance Considerations

### Static Analysis

- **Time**: ~10-30 seconds per patch (depends on file count)
- **Memory**: ~100-500MB (depends on repository size)
- **Parallelization**: Analyzers run sequentially within single patch

### Test Execution

- **Time**: 30 seconds - 5 minutes (depends on test suite)
- **Timeout**: Hard limit at 5 minutes
- **Output Size**: Limited to last 5000 characters in display

### Scalability

Current limitations:
- **Sequential Processing**: One analysis at a time per user
- **No Queueing**: No job queue for multiple analyses
- **Session Storage**: Results lost on app restart

Future improvements:
- **Background Jobs**: Queue analyses using SLURM
- **Persistent Storage**: Database for results
- **Multi-user Support**: Isolated workspaces per user

## Troubleshooting

### Common Issues

1. **Patch Application Fails**
   - Ensure repository is a valid Git repo
   - Check patch format (unified diff)
   - Verify patch applies to correct commit

2. **Static Analysis Errors**
   - Ensure all analyzers are installed
   - Check file permissions in repo directory
   - Verify Python files are valid syntax

3. **Test Execution Fails**
   - Check test framework is installed
   - Verify test command is correct
   - Ensure dependencies are installed

4. **Upload Errors**
   - Check file size limits
   - Ensure ZIP is valid
   - Verify patch encoding (UTF-8)

## Future Enhancements

### Short Term
1. **Job Queue**: Background processing for long analyses
2. **Result Persistence**: Database storage
3. **Export Results**: Download JSON/PDF reports

### Medium Term
1. **Singularity Integration**: Isolated test execution
2. **Fuzzing Integration**: Add dynamic fuzzing tests
3. **Rules Integration**: Add 9 verification rules
4. **Comparison View**: Compare multiple patch versions

### Long Term
1. **Multi-user Support**: User authentication and workspaces
2. **Cluster Integration**: SLURM job submission and monitoring
3. **CI/CD Integration**: Webhook support for GitHub/GitLab
4. **ML Insights**: Pattern detection and recommendations

## Monitoring and Logging

### Application Logs

Streamlit generates logs in:
```
~/.streamlit/logs/
```

### Error Handling

All errors are caught and displayed to user:
- **Static Analysis Errors**: Show error message, continue to tests
- **Test Execution Errors**: Show timeout/exception, mark as failed
- **Patch Application Errors**: Show git error, abort analysis

### Performance Metrics

Track in session state:
- Analysis duration
- File sizes processed
- Number of issues found
- Test execution time

## References

### Internal Documentation
- [INTEGRATED_PIPELINE_GUIDE.md](./INTEGRATED_PIPELINE_GUIDE.md) - Full pipeline documentation
- [SWEBENCH_SINGULARITY_RUNNER.md](./SWEBENCH_SINGULARITY_RUNNER.md) - Container execution

### External Resources
- [Streamlit Documentation](https://docs.streamlit.io)
- [SWE-bench Dataset](https://github.com/princeton-nlp/SWE-bench)
- [Static Analyzer Tools](../verifier/static_analyzers/README.md)

## Contact and Support

For issues or questions:
- Check existing documentation in `docs/`
- Review code comments in `streamlit/app.py`
- Examine example results in `results/`
