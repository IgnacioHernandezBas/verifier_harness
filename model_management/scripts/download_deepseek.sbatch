#!/bin/bash
#SBATCH --job-name=download-deepseek
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/download_deepseek_%j.log

set -e

export HOME=/fs/nexus-scratch/ihbas
export TMPDIR=/fs/nexus-scratch/ihbas/tmp
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

mkdir -p "${TMPDIR}"

echo "Starting DeepSeek-Coder-V2-Instruct-AWQ download..."
echo "Model: casperhansen/deepseek-coder-v2-instruct-awq"
echo "Size: ~40GB (236B MoE, 21B active params)"
echo "Cache: ${HF_HOME}"
echo ""

python3 << 'PYEOF'
from huggingface_hub import snapshot_download
import sys
import time

start_time = time.time()

try:
    print("Starting download...")
    path = snapshot_download(
        repo_id='casperhansen/deepseek-coder-v2-instruct-awq',
        cache_dir='/fs/cml-scratch/ihbas/cache/huggingface',
        resume_download=True
    )

    elapsed = time.time() - start_time
    print(f'\n✓ Download complete in {elapsed/60:.1f} minutes!')
    print(f'Model cached at: {path}')

except Exception as e:
    print(f'\n✗ Error during download: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "========================================="
echo "DeepSeek-Coder-V2-Instruct-AWQ Download Complete"
echo "========================================="
echo ""
echo "You can now use this model with:"
echo "  Model ID: casperhansen/deepseek-coder-v2-instruct-awq"
echo ""
echo "Storage summary:"
du -sh /fs/cml-scratch/ihbas/cache/huggingface/hub/models--casperhansen--deepseek-coder-v2-instruct-awq/ 2>/dev/null || echo "  Model directory not found in expected location"
echo ""
df -h /fs/cml-scratch/ | grep cml-scratch
