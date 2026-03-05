#!/usr/bin/env python3
import os
from huggingface_hub import snapshot_download

# Set environment
os.environ['HF_HOME'] = '/fs/cml-scratch/ihbas/cache/huggingface'
os.environ['HOME'] = '/fs/nexus-scratch/ihbas'

print('Starting DeepSeek-Coder-V2-Instruct-AWQ download...')
print('Model: casperhansen/deepseek-coder-v2-instruct-awq')
print('Size: ~40GB (236B MoE, 21B active params)\n')

try:
    path = snapshot_download(
        repo_id='casperhansen/deepseek-coder-v2-instruct-awq',
        cache_dir='/fs/cml-scratch/ihbas/cache/huggingface',
        resume_download=True
    )
    print(f'\n✓ Download complete!')
    print(f'Model path: {path}')
except Exception as e:
    print(f'✗ Error during download: {e}')
    import sys
    sys.exit(1)
