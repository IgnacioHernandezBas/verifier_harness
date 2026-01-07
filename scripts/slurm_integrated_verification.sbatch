#!/bin/bash
#SBATCH --job-name=integrated_verify
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/logs/integrated_%A.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/logs/integrated_%A.err
#SBATCH --time=6:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# =============================================================================
# Integrated Verification SLURM Job
# =============================================================================
#
# This script runs the integrated verification pipeline on a compute node.
# It requires:
#   - /scratch0 for Podman storage
#   - Network access for pulling Docker images
#
# Usage:
#   sbatch --export=EXPERIMENT=<name>,LIMIT=<n> slurm_integrated_verification.sbatch
#
# Examples:
#   sbatch --export=EXPERIMENT=20250911_isea_claude-3.5-sonnet-20241022,LIMIT=10 slurm_integrated_verification.sbatch
#   sbatch --export=EXPERIMENT=20250911_isea_claude-3.5-sonnet-20241022,INSTANCE=django__django-12345 slurm_integrated_verification.sbatch
# =============================================================================

# Configuration
EXPERIMENT="${EXPERIMENT:-20250911_isea_claude-3.5-sonnet-20241022}"
INSTANCE="${INSTANCE:-}"
LIMIT="${LIMIT:-}"
ENABLE_STATIC="${ENABLE_STATIC:-false}"
ENABLE_SWEBENCH="${ENABLE_SWEBENCH:-true}"
ENABLE_FUZZING="${ENABLE_FUZZING:-true}"
ENABLE_INVARIANCE="${ENABLE_INVARIANCE:-false}"

# Paths
HARNESS_DIR="/fs/nexus-scratch/ihbas/verifier_harness"
OUTPUT_DIR="${HARNESS_DIR}/results/integrated_${SLURM_JOB_ID}"

echo "=========================================="
echo "Integrated Verification Pipeline"
echo "=========================================="
echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Experiment: ${EXPERIMENT}"
echo "Instance: ${INSTANCE:-all}"
echo "Limit: ${LIMIT:-none}"
echo ""
echo "Analysis enabled:"
echo "  Static: ${ENABLE_STATIC}"
echo "  SWE-bench: ${ENABLE_SWEBENCH}"
echo "  Fuzzing: ${ENABLE_FUZZING}"
echo "  Invariance: ${ENABLE_INVARIANCE}"
echo ""
echo "Start time: $(date)"
echo "=========================================="

# Verify we're on a compute node with /scratch0
if [ ! -d "/scratch0" ]; then
    echo "ERROR: /scratch0 not found. This job must run on a compute node."
    exit 1
fi

# Setup scratch directory
mkdir -p /scratch0/ihbas
mkdir -p "${OUTPUT_DIR}"

# Create logs directory if needed
mkdir -p "${HARNESS_DIR}/logs"

# Setup Podman storage on scratch0 (required for rootless containers)
export CONTAINERS_STORAGE_CONF=/scratch0/ihbas/containers_storage.conf
cat > "${CONTAINERS_STORAGE_CONF}" << 'EOF'
[storage]
driver = "overlay"
runroot = "/scratch0/ihbas/podman_runroot"
graphroot = "/scratch0/ihbas/podman_graphroot"

[storage.options.overlay]
mount_program = "/usr/bin/fuse-overlayfs"
EOF

mkdir -p /scratch0/ihbas/podman_runroot
mkdir -p /scratch0/ihbas/podman_graphroot

# Run podman system migrate to initialize storage
echo "Initializing Podman storage..."
podman system migrate 2>&1 | grep -v "subuid\|subgid\|single mapping" || true

# Activate conda environment
source /fs/nexus-scratch/ihbas/miniconda3/bin/activate
conda activate verifier_env

# Build command
CMD="python ${HARNESS_DIR}/scripts/run_integrated_verification.py"
CMD="${CMD} --experiment ${EXPERIMENT}"

if [ -n "${INSTANCE}" ]; then
    CMD="${CMD} --instance ${INSTANCE}"
    OUTPUT_FILE="${OUTPUT_DIR}/${INSTANCE}.json"
else
    OUTPUT_FILE="${OUTPUT_DIR}/results.json"
fi

if [ -n "${LIMIT}" ]; then
    CMD="${CMD} --limit ${LIMIT}"
fi

CMD="${CMD} --output ${OUTPUT_FILE}"

if [ "${ENABLE_STATIC}" != "true" ]; then
    CMD="${CMD} --no-static"
fi
if [ "${ENABLE_SWEBENCH}" != "true" ]; then
    CMD="${CMD} --no-swebench"
fi
if [ "${ENABLE_FUZZING}" != "true" ]; then
    CMD="${CMD} --no-fuzzing"
fi
if [ "${ENABLE_INVARIANCE}" != "true" ]; then
    CMD="${CMD} --no-invariance"
fi

echo ""
echo "Running: ${CMD}"
echo ""

# Run the verification
cd "${HARNESS_DIR}"
eval "${CMD}"
EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Job Complete"
echo "=========================================="
echo "Exit code: ${EXIT_CODE}"
echo "End time: $(date)"
echo "Results saved to: ${OUTPUT_FILE}"
echo "=========================================="

exit ${EXIT_CODE}
