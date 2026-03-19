#!/usr/bin/env python3
"""Download Qwen2.5-Coder-72B-Instruct-AWQ-INT4 model to cache."""

import os
from huggingface_hub import snapshot_download

# Set cache directory
cache_dir = "/fs/cml-scratch/ihbas/cache/huggingface"
os.environ["HF_HOME"] = cache_dir
os.environ["TRANSFORMERS_CACHE"] = cache_dir

model_name = "Qwen/Qwen3-32B-AWQ"

print(f"Downloading {model_name}...")
print(f"Cache directory: {cache_dir}")
print()

try:
    snapshot_download(
        repo_id=model_name,
        cache_dir=cache_dir,
        resume_download=True,
        local_files_only=False,
    )
    print(f"\n✓ Successfully downloaded {model_name}")
except Exception as e:
    print(f"\n✗ Error downloading model: {e}")
    raise
