#!/bin/bash
# Run array job in batches to avoid Docker rate limit
# Free tier: 200 pulls per 6 hours

TOTAL_TASKS=300
BATCH_SIZE=50  # Conservative: 50 at a time
WAIT_TIME=3600  # Wait 1 hour between batches

for start in $(seq 0 $BATCH_SIZE $((TOTAL_TASKS - 1))); do
    end=$((start + BATCH_SIZE - 1))
    if [ $end -ge $TOTAL_TASKS ]; then
        end=$((TOTAL_TASKS - 1))
    fi
    
    echo "Submitting batch: tasks $start-$end"
    sbatch --array=$start-$end scripts/slurm_integrated_verification.sbatch
    
    if [ $end -lt $((TOTAL_TASKS - 1)) ]; then
        echo "Waiting $WAIT_TIME seconds before next batch..."
        sleep $WAIT_TIME
    fi
done
