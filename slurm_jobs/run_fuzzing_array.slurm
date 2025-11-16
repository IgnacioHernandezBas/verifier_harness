#!/bin/bash
#SBATCH --job-name=fuzzing_array
#SBATCH --output=logs/fuzzing_%A_%a.out
#SBATCH --error=logs/fuzzing_%A_%a.err
#SBATCH --array=0-9%5
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --partition=general
# NO GPU NEEDED - CPU only workload
# %5 limits to 5 concurrent jobs

# ============================================
# Dynamic Fuzzing - Parallel Array Job
# ============================================
# Processes patches in parallel across multiple nodes
# Usage: sbatch --export=PREDICTIONS_FILE=predictions.json,NUM_CHUNKS=10 run_fuzzing_array.slurm

echo "=============================================="
echo "Array Job ID: $SLURM_ARRAY_JOB_ID"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Start Time: $(date)"
echo "=============================================="

# Create directories
mkdir -p logs results chunks

# Load environment
source ~/.bashrc
conda activate verifier_fuzzing || conda activate verifier_env

cd /fs/nexus-scratch/ihbas/verifier_harness

# Parameters
PREDICTIONS_FILE=${PREDICTIONS_FILE:-"predictions.json"}
NUM_CHUNKS=${NUM_CHUNKS:-${SLURM_ARRAY_TASK_COUNT:-10}}
TASK_ID=$SLURM_ARRAY_TASK_ID
IMAGE_PATH="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif"

echo ""
echo "Configuration:"
echo "  Predictions: $PREDICTIONS_FILE"
echo "  Total chunks: $NUM_CHUNKS"
echo "  Processing chunk: $TASK_ID"
echo ""

# Split predictions into chunks (only task 0 does this)
if [ $TASK_ID -eq 0 ]; then
    echo "Splitting predictions file into $NUM_CHUNKS chunks..."

    python - << PYEOF
import json
import math
from pathlib import Path

# Load predictions
with open('${PREDICTIONS_FILE}', 'r') as f:
    predictions = json.load(f)

print(f"Total predictions: {len(predictions)}")

# Create chunks
Path('chunks').mkdir(exist_ok=True)
chunk_size = math.ceil(len(predictions) / ${NUM_CHUNKS})

for i in range(${NUM_CHUNKS}):
    start = i * chunk_size
    end = min((i + 1) * chunk_size, len(predictions))
    chunk = predictions[start:end]

    chunk_file = f'chunks/chunk_{i}.json'
    with open(chunk_file, 'w') as f:
        json.dump(chunk, f, indent=2)

    print(f"  {chunk_file}: {len(chunk)} predictions")

print(f"✓ Created {${NUM_CHUNKS}} chunk files")
PYEOF

    # Create a marker file to signal completion
    touch chunks/.split_complete
    sleep 2
fi

# Wait for splitting to complete
echo "Waiting for chunks to be created..."
for i in {1..60}; do
    if [ -f "chunks/.split_complete" ]; then
        break
    fi
    sleep 2
done

# Verify chunk file exists
CHUNK_FILE="chunks/chunk_${TASK_ID}.json"
if [ ! -f "$CHUNK_FILE" ]; then
    echo "ERROR: Chunk file not found: $CHUNK_FILE"
    ls -la chunks/
    exit 1
fi

CHUNK_SIZE=$(jq length "$CHUNK_FILE")
echo "✓ Processing $CHUNK_FILE ($CHUNK_SIZE predictions)"
echo ""

# Run evaluation on this chunk
python eval_cli.py \
    --predictions "$CHUNK_FILE" \
    --dataset "princeton-nlp/SWE-bench_Verified" \
    --output "results/fuzzing_${SLURM_ARRAY_JOB_ID}_task${TASK_ID}.json" \
    --image "$IMAGE_PATH" \
    --timeout 180 \
    --static-threshold 0.5 \
    --coverage-threshold 0.5 \
    --verbose

EXIT_CODE=$?

echo ""
echo "=============================================="
echo "Task $TASK_ID completed: $EXIT_CODE"
echo "Processed: $CHUNK_SIZE predictions"
echo "Output: results/fuzzing_${SLURM_ARRAY_JOB_ID}_task${TASK_ID}.json"
echo "End Time: $(date)"
echo "=============================================="

exit $EXIT_CODE
