#!/bin/bash
set -e

export HOME=/fs/nexus-scratch/ihbas
export TMPDIR=/fs/nexus-scratch/ihbas/tmp
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

mkdir -p "${TMPDIR}"

echo "Starting DeepSeek-Coder-V2-Instruct-AWQ download..."
echo "Model: casperhansen/deepseek-coder-v2-instruct-awq"
echo "Size: ~40GB (236B MoE, 21B active params)"
echo "This will take 10-30 minutes depending on network speed"
echo ""

python3 << 'PYEOF'
from huggingface_hub import snapshot_download
import sys

try:
    path = snapshot_download(
        repo_id='casperhansen/deepseek-coder-v2-instruct-awq',
        cache_dir='/fs/cml-scratch/ihbas/cache/huggingface',
        resume_download=True
    )
    print(f'\n✓ Download complete!')
    print(f'Model path: {path}')
except Exception as e:
    print(f'\n✗ Error during download: {e}')
    sys.exit(1)
PYEOF

echo ""
echo "✓ DeepSeek-Coder-V2-Instruct-AWQ successfully downloaded!"
