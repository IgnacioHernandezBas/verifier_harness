#!/bin/bash
#SBATCH --job-name=atheris_fuzz
#SBATCH --output=logs/atheris_fuzz_%A_%a.out
#SBATCH --error=logs/atheris_fuzz_%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# ============================================================================
# Atheris Coverage-Guided Differential Fuzzing - SLURM Job Script
# ============================================================================
#
# This script runs the CORE NOVELTY: coverage-guided differential fuzzing
# using Google's Atheris library in Singularity containers.
#
# WHAT IT DOES:
# 1. Takes a patch (original + patched code)
# 2. Runs Atheris to generate coverage-guided inputs
# 3. Compares behavior: original vs patched
# 4. Classifies differences: expected fix / suspicious / regression
#
# USAGE:
#   # Single job (demo)
#   sbatch scripts/slurm/slurm_atheris_fuzzing.sh --demo
#
#   # Array job for multiple instances
#   sbatch --array=1-10%3 scripts/slurm/slurm_atheris_fuzzing.sh
#
#   # With custom instance file
#   FUZZ_INSTANCE_FILE=my_instances.txt sbatch --array=1-5 scripts/slurm/slurm_atheris_fuzzing.sh
#
# INSTANCE FILE FORMAT (one instance per line):
#   instance_id|function_name|class_name|param1:type,param2:type|changed_lines
#   Example: django__django-12345|parse_date|DateParser|date_str:str,format:str|45,46,47,48
#
# ============================================================================

echo "=========================================="
echo "Atheris Coverage-Guided Differential Fuzzing"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: ${SLURM_ARRAY_TASK_ID:-N/A}"
echo "Node: $SLURM_NODELIST"
echo "Started: $(date)"
echo ""

# Configuration (can be overridden via environment)
FUZZ_INSTANCE_FILE="${FUZZ_INSTANCE_FILE:-instance_ids_fuzz.txt}"
FUZZ_MAX_ITERATIONS="${FUZZ_MAX_ITERATIONS:-10000}"
FUZZ_TIMEOUT="${FUZZ_TIMEOUT:-300}"
FUZZ_OUTPUT_DIR="${FUZZ_OUTPUT_DIR:-results/atheris_fuzzing}"
FUZZ_DEMO_MODE="${FUZZ_DEMO_MODE:-0}"

# Check if demo mode requested
if [[ "$1" == "--demo" ]] || [[ "$FUZZ_DEMO_MODE" == "1" ]]; then
    FUZZ_DEMO_MODE=1
    echo "Running in DEMO mode"
fi

# Load conda environment
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh
conda activate verifier_env

# Resolve repository root
if [ -n "$SLURM_SUBMIT_DIR" ]; then
    REPO_ROOT="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

cd "$REPO_ROOT" || {
    echo "ERROR: Unable to cd into repository root: $REPO_ROOT"
    exit 1
}

# Create output directories
mkdir -p logs "$FUZZ_OUTPUT_DIR"

# Check Singularity image exists
SINGULARITY_IMAGE="/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif"
if [ ! -f "$SINGULARITY_IMAGE" ]; then
    echo "ERROR: Singularity image not found: $SINGULARITY_IMAGE"
    echo "Please build it first using: scripts/build_container.sh"
    exit 1
fi
echo "Singularity image: $SINGULARITY_IMAGE"
echo ""

# Demo mode: run the built-in demo
if [ "$FUZZ_DEMO_MODE" == "1" ]; then
    echo "Running Atheris fuzzing demo..."
    python scripts/run_atheris_fuzzing.py \
        --demo \
        --output-json "$FUZZ_OUTPUT_DIR/demo_results.json"

    EXIT_CODE=$?
    echo ""
    echo "Demo finished: $(date)"
    echo "Results saved to: $FUZZ_OUTPUT_DIR/demo_results.json"
    exit $EXIT_CODE
fi

# Array job mode: process instance from file
if [ -z "$SLURM_ARRAY_TASK_ID" ]; then
    echo "ERROR: Not running as array job and not in demo mode"
    echo "Use --demo flag or submit as array job:"
    echo "  sbatch --array=1-N scripts/slurm/slurm_atheris_fuzzing.sh"
    exit 1
fi

# Read instance configuration from file
# Format: instance_id|function_name|class_name|params|changed_lines
INSTANCE_LINE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$FUZZ_INSTANCE_FILE")

if [ -z "$INSTANCE_LINE" ]; then
    echo "ERROR: Could not read instance for task $SLURM_ARRAY_TASK_ID from $FUZZ_INSTANCE_FILE"
    exit 1
fi

# Parse the instance line
IFS='|' read -r INSTANCE_ID FUNCTION_NAME CLASS_NAME PARAMS_STR CHANGED_LINES <<< "$INSTANCE_LINE"

echo "Instance ID: $INSTANCE_ID"
echo "Function: $FUNCTION_NAME"
echo "Class: ${CLASS_NAME:-N/A}"
echo "Changed lines: $CHANGED_LINES"
echo ""

# Convert params string to JSON
# Format: param1:type,param2:type -> [{"name":"param1","type":"type"},...]
PARAMS_JSON="["
FIRST=1
IFS=',' read -ra PARAM_ARRAY <<< "$PARAMS_STR"
for PARAM in "${PARAM_ARRAY[@]}"; do
    IFS=':' read -r PARAM_NAME PARAM_TYPE <<< "$PARAM"
    if [ "$FIRST" -eq 1 ]; then
        FIRST=0
    else
        PARAMS_JSON+=","
    fi
    PARAMS_JSON+="{\"name\":\"$PARAM_NAME\",\"type\":\"$PARAM_TYPE\"}"
done
PARAMS_JSON+="]"

echo "Params JSON: $PARAMS_JSON"
echo ""

# Paths for this instance
# These should be set up by your SWE-bench infrastructure
ORIGINAL_CODE_PATH="repos_original/${INSTANCE_ID}/code.py"
PATCHED_CODE_PATH="repos_patched/${INSTANCE_ID}/code.py"
OUTPUT_JSON="$FUZZ_OUTPUT_DIR/${INSTANCE_ID}_fuzzing.json"

# Check if files exist
if [ ! -f "$ORIGINAL_CODE_PATH" ]; then
    echo "ERROR: Original code not found: $ORIGINAL_CODE_PATH"
    echo "Make sure to extract the code from SWE-bench instance first"
    exit 1
fi

if [ ! -f "$PATCHED_CODE_PATH" ]; then
    echo "ERROR: Patched code not found: $PATCHED_CODE_PATH"
    exit 1
fi

# Build command
CMD=(python scripts/run_atheris_fuzzing.py
    --original-file "$ORIGINAL_CODE_PATH"
    --patched-file "$PATCHED_CODE_PATH"
    --function-name "$FUNCTION_NAME"
    --params "$PARAMS_JSON"
    --changed-lines "$CHANGED_LINES"
    --max-iterations "$FUZZ_MAX_ITERATIONS"
    --timeout "$FUZZ_TIMEOUT"
    --output-json "$OUTPUT_JSON"
)

if [ -n "$CLASS_NAME" ] && [ "$CLASS_NAME" != "None" ]; then
    CMD+=(--class-name "$CLASS_NAME")
fi

echo "Executing: ${CMD[*]}"
echo ""

"${CMD[@]}"
EXIT_CODE=$?

echo ""
echo "Finished: $(date)"
echo "Exit code: $EXIT_CODE"
echo "Results: $OUTPUT_JSON"

exit $EXIT_CODE
