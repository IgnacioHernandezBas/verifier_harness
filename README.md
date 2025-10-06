# Verification Harness Repo

## Project Objective 

To design and implement a unified verification harness that evaluates the correctness of AI-generated
code (and in particular, patches) at multiple levels:
  • Syntactic and structural correctness using constructs such as Abstract Syntax Trees (ASTs)
  and Control Flow Graphs (CFGs).
  • Functional correctness and robustness using targeted dynamic analysis (like pytest or
  fuzzing).
  • Test suite effectiveness using carefully chosen coverage metrics and mutation scores.
  
The final system will take as input an agent-generated patch, run it through a pipeline of static and
dynamic verifiers, and output a composite verification report with pass/fail outcomes and coverage
metrics. This project can serve both for benchmarking (improving SWE-bench) and as a pre-commit
safety net in real-world Continuous Integration/Continuous Deployment pipelines.

## Project Structure (Guide)

verifier_harness/
├── verifier/
│ ├── patch_loader.py # Applies LLM-generated patches to the base code
│ ├── static_verifier.py # Runs flake8, mypy, and other static checks
│ ├── dynamic_verifier.py # Executes tests and fuzzing in sandboxed envs
│ ├── test_evaluator.py # Measures coverage and mutation score
│ ├── report_generator.py # Aggregates results into a final report
│ └── utils/
│ └── sandbox.py # Sandbox helpers and subprocess control
│
├── swebench_integration/
│ ├── dataset_loader.py # Loads SWE-bench Lite dataset and repositories
│ ├── patch_runner.py # Automates running the harness on each sample
│ └── results_aggregator.py # Collects and summarizes evaluation results
│
├── tests/ # Unit tests for harness modules
│ ├── test_patch_loader.py
│ ├── test_static_verifier.py
│ └── test_dynamic_verifier.py
│
├── requirements.txt # Pip dependencies
├── environment.yml # Conda environment file
├── .flake8 # Linting configuration
├── mypy.ini # Static typing configuration
├── .coveragerc # Coverage settings
├── pytest.ini # Pytest behavior configuration
├── .gitignore # Ignore cache, envs, IDE files
└── README.md # Project description and setup guide

## Cloning and set up

  git clone https://github.com/IgnacioHernandezBas/verifier_harness.git
  
  cd verifier_harness
  
  conda env create -f environment.yml (you must have conda installed) -> [miniconda installation](https://www.anaconda.com/docs/getting-started/miniconda/main)



