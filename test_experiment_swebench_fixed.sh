#!/bin/bash
set -euo pipefail

# SWE-bench Testing Script (FIXED VERSION)
# Matches official SWE-bench evaluation methodology EXACTLY:
# - Apply code patch
# - Run eval.sh which handles test patches and runs tests
# - Check exit code: 0 = RESOLVED, non-zero = NOT RESOLVED

# Configuration
EXPERIMENT_NAME="${1:-}"
EXPERIMENT_DIR="/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/${EXPERIMENT_NAME}/logs"
OUTPUT_BASE_DIR="/scratch0/ihbas/podman_test_results/${EXPERIMENT_NAME}"
MAX_PARALLEL="${MAX_PARALLEL:-4}"

# Set TMPDIR to local scratch for Podman (required - NFS doesn't support xattr)
export TMPDIR='/scratch0/ihbas/tmp'
mkdir -p "${TMPDIR}"

# Verify Podman storage configuration
if [ ! -f "${HOME}/.config/containers/storage.conf" ]; then
    echo "ERROR: Podman storage configuration not found at ${HOME}/.config/containers/storage.conf"
    echo "Please ensure your Podman configuration is set up correctly."
    exit 1
fi

# Verify /scratch0/ is accessible (only available on compute nodes)
if [ ! -d "/scratch0/ihbas" ]; then
    echo "ERROR: /scratch0/ihbas is not accessible. Are you running on a compute node?"
    echo "Podman requires local scratch storage, which is only available on compute nodes."
    exit 1
fi

# Skip migration - it can cause crashes with leftover containers
# Just proceed directly to testing
echo "Skipping Podman migration to avoid crashes..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ -z "${EXPERIMENT_NAME}" ]; then
    echo "Usage: $0 <experiment_name>"
    exit 1
fi

echo "=================================="
echo "SWE-bench Testing (FIXED)"
echo "=================================="
echo "Experiment: ${EXPERIMENT_NAME}"
echo "Experiment DIR: ${EXPERIMENT_DIR}"
echo ""

# Check if experiment directory exists
if [ ! -d "${EXPERIMENT_DIR}" ]; then
    echo -e "${RED}Error: Experiment directory not found: ${EXPERIMENT_DIR}${NC}"
    exit 1
fi
echo "Directory check passed"

# Function to convert instance directory to Docker image name
get_docker_image() {
    local instance_id="$1"
    local org="${instance_id%%__*}"
    local repo_and_num="${instance_id#*__}"
    echo "docker.io/swebench/sweb.eval.x86_64.${org}_1776_${repo_and_num}:latest"
}

# Function to test a single instance using SWE-bench methodology
test_instance_swebench() {
    local instance_dir="$1"
    local instance_id=$(basename "${instance_dir}")
    local output_dir="${OUTPUT_BASE_DIR}/${instance_id}"

    mkdir -p "${output_dir}"

    # Check if patch exists
    if [ ! -f "${instance_dir}/patch.diff" ]; then
        echo "SKIP"
        return 1
    fi

    # Copy instance files to scratch (NFS paths cannot be mounted into containers)
    local scratch_input_dir="${OUTPUT_BASE_DIR}/_inputs/${instance_id}"
    mkdir -p "${scratch_input_dir}"
    cp "${instance_dir}/patch.diff" "${scratch_input_dir}/" 2>/dev/null || {
        echo "FAIL"
        return 1
    }
    [ -f "${instance_dir}/eval.sh" ] && cp "${instance_dir}/eval.sh" "${scratch_input_dir}/"
    [ -f "${instance_dir}/report.json" ] && cp "${instance_dir}/report.json" "${scratch_input_dir}/"

    # Get Docker image name
    local image=$(get_docker_image "${instance_id}")

    # Pull image if needed
    if ! podman images --format "{{.Repository}}:{{.Tag}}" | grep -Fq "${image}"; then
        podman pull "${image}" > "${output_dir}/pull.log" 2>&1 || {
            echo "FAIL"
            return 1
        }
    fi

    # Run SWE-bench evaluation: Apply code patch, then run eval.sh
    podman run --rm \
        -v "${scratch_input_dir}:/patch" \
        -v "${output_dir}:/output" \
        "${image}" \
        bash -c '
            set +e  # Dont exit on error, we want to capture exit codes
            export LANG=en_US.UTF-8
            export LANGUAGE=en_US:en
            export LC_ALL=en_US.UTF-8

            cd /testbed

            # Apply the code patch first
            if ! git apply -v /patch/patch.diff > /output/patch.log 2>&1; then
                echo "PATCH_FAILED" > /output/status.txt
                echo 999 > /output/exit_code.txt
                exit 0
            fi

            # Run test setup and tests from eval.sh
            if [ -f /patch/eval.sh ]; then
                # Activate environment
                source /opt/miniconda3/bin/activate 2>/dev/null || true
                conda activate testbed 2>/dev/null || true

                # Apply test patches (git checkout + git apply commands before test marker)
                grep "^git checkout .* tests/" /patch/eval.sh | while read -r cmd; do
                    eval "$cmd" >> /output/patch.log 2>&1 || true
                done

                # Apply inline git patches
                sed -n "/git apply -v - <<'\''EOF_/,/^EOF_/p" /patch/eval.sh | \
                    sed "1d;\$d" | git apply -v >> /output/patch.log 2>&1 || true

                # Extract and run the test command (between >>>>> markers)
                test_cmd=$(sed -n "/>>>>> Start Test Output/,/>>>>> End Test Output/p" /patch/eval.sh | \
                           grep -v ">>>>>" | grep -v "^:" | grep -v "^$" | head -1)

                if [ -n "$test_cmd" ]; then
                    eval "$test_cmd" > /output/test_output.txt 2>&1
                    exit_code=$?
                else
                    pytest > /output/test_output.txt 2>&1
                    exit_code=$?
                fi
            else
                # Fallback: just run pytest
                source /opt/miniconda3/bin/activate 2>/dev/null || true
                conda activate testbed 2>/dev/null || true
                pytest > /output/test_output.txt 2>&1
                exit_code=$?
            fi

            echo $exit_code > /output/exit_code.txt
            exit 0
        ' > /dev/null 2>&1

    # Read exit code
    local exit_code=1
    if [ -f "${output_dir}/exit_code.txt" ]; then
        exit_code=$(cat "${output_dir}/exit_code.txt")
    fi

    # SWE-bench methodology: Resolution based ONLY on exit code
    # Exit code 0 = all tests passed = RESOLVED
    # Any other exit code = some tests failed = NOT RESOLVED
    local result="FAIL"
    local resolved="false"

    if [ "${exit_code}" -eq 999 ]; then
        # Patch application failed
        result="PATCH_FAILED"
        resolved="false"
    elif [ "${exit_code}" -eq 0 ]; then
        # All tests passed - RESOLVED
        result="PASS"
        resolved="true"
    else
        # Tests failed - NOT RESOLVED
        result="FAIL"
        resolved="false"
    fi

    # Save results (simplified format matching SWE-bench)
    cat > "${output_dir}/results.json" << EOF
{
  "resolved": ${resolved},
  "exit_code": ${exit_code},
  "result_category": "${result}"
}
EOF

    echo "${result}" > "${output_dir}/status.txt"

    # Clean up scratch input directory immediately after test completes to save space
    rm -rf "${scratch_input_dir}" 2>/dev/null || true

    # Return status
    if [ "${resolved}" = "true" ]; then
        echo "PASS"
        return 0
    else
        echo "FAIL"
        return 1
    fi
}

# Get all instance directories
echo "Running find command..."
# Temporarily disable pipefail for head command (causes SIGPIPE with large directories)
set +o pipefail
INSTANCE_DIRS=($(find "${EXPERIMENT_DIR}" -mindepth 1 -maxdepth 1 -type d | sort))
set -o pipefail
TOTAL_INSTANCES=${#INSTANCE_DIRS[@]}
echo "Find completed"

echo "Found ${TOTAL_INSTANCES} instances"
echo "Testing with SWE-bench methodology..."
echo ""

# Stats
PASSED=0
FAILED=0

# Process instances in parallel
process_batch() {
    local batch=("$@")
    local pids=()

    for instance_dir in "${batch[@]}"; do
        (
            instance_id=$(basename "${instance_dir}")
            printf "Testing: %-50s " "${instance_id}"
            result=$(test_instance_swebench "${instance_dir}")

            if [ "${result}" = "PASS" ]; then
                echo -e "${GREEN}PASS${NC}"
                exit 0
            else
                echo -e "${RED}FAIL${NC}"
                exit 1
            fi
        ) &
        pids+=($!)
    done

    # Wait for all processes in batch
    for pid in "${pids[@]}"; do
        if wait "${pid}"; then
            ((PASSED++)) || true
        else
            ((FAILED++)) || true
        fi
    done
}

# Process in batches
batch=()
for instance_dir in "${INSTANCE_DIRS[@]}"; do
    batch+=("${instance_dir}")

    if [ ${#batch[@]} -eq ${MAX_PARALLEL} ]; then
        process_batch "${batch[@]}"
        batch=()
    fi
done

# Process remaining instances
if [ ${#batch[@]} -gt 0 ]; then
    process_batch "${batch[@]}"
fi

# Print summary
echo ""
echo "=================================="
echo "Results"
echo "=================================="
echo "Total: ${TOTAL_INSTANCES}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

# Calculate success rate
if [ ${TOTAL_INSTANCES} -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", (${PASSED}/${TOTAL_INSTANCES})*100}")
    echo "Success rate: ${SUCCESS_RATE}%"
fi

echo ""

# Clean up temporary input directories from /scratch0
echo "Cleaning up temporary input files from /scratch0..."
rm -rf "${OUTPUT_BASE_DIR}/_inputs" 2>/dev/null || true

# Copy results from /scratch0 to NFS for permanent storage
NFS_OUTPUT_DIR="/fs/nexus-scratch/ihbas/podman_test_results/${EXPERIMENT_NAME}"
echo "Copying results from /scratch0 to NFS..."
mkdir -p "${NFS_OUTPUT_DIR}"
# Copy all directories except _inputs
for dir in "${OUTPUT_BASE_DIR}"/*; do
    if [ -d "${dir}" ] && [ "$(basename "${dir}")" != "_inputs" ]; then
        cp -r "${dir}" "${NFS_OUTPUT_DIR}/" 2>/dev/null || true
    fi
done
echo "Results copied to: ${NFS_OUTPUT_DIR}"
echo ""
