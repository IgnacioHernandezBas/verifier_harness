#!/bin/bash
# Pre-download models to cache before submitting GPU jobs
# This avoids wasting GPU allocation time on downloads
#
# Usage:
#   ./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
#   ./download_model.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [[ $# -lt 1 ]]; then
  echo -e "${RED}Error: Model name required${NC}" >&2
  echo ""
  echo "Usage: $(basename "$0") MODEL_NAME"
  echo ""
  echo "Examples:"
  echo "  $(basename "$0") hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
  echo "  $(basename "$0") Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
  echo "  $(basename "$0") deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
  exit 1
fi

MODEL_NAME="$1"

# Use same cache location as the job scripts
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Model Download to Cache${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Model:${NC}       ${MODEL_NAME}"
echo -e "${BLUE}Cache:${NC}       ${HF_HOME}"
echo ""

# Check available space
AVAILABLE_GB=$(df -BG /fs/cml-scratch | tail -1 | awk '{print $4}' | sed 's/G//')
echo -e "${BLUE}Available:${NC}   ${AVAILABLE_GB}GB"

if [[ ${AVAILABLE_GB} -lt 50 ]]; then
  echo -e "${YELLOW}Warning: Less than 50GB available. Large models may fail.${NC}"
fi

echo ""
echo -e "${GREEN}Starting download...${NC}"
echo -e "${YELLOW}Note: This may take 5-20 minutes depending on model size and network speed.${NC}"
echo ""

# Load conda environment
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh
conda activate verifier_llm 2>/dev/null || conda activate base

# Download with progress and resume support
python3 << EOF
import sys
from huggingface_hub import snapshot_download
from tqdm import tqdm

model_name = "${MODEL_NAME}"
cache_dir = "${HF_HOME}"

print(f"Downloading {model_name}...")
print(f"Cache: {cache_dir}")
print("")

try:
    # Download with resume support
    snapshot_download(
        repo_id=model_name,
        cache_dir=cache_dir,
        resume_download=True,  # Resume interrupted downloads
        local_files_only=False,
        ignore_patterns=["*.md", "*.txt", ".gitattributes"],  # Skip non-essential files
    )
    print("")
    print("✓ Download complete!")
    sys.exit(0)

except KeyboardInterrupt:
    print("")
    print("⚠ Download interrupted. Run again to resume.")
    sys.exit(1)

except Exception as e:
    print(f"✗ Download failed: {e}")
    sys.exit(1)
EOF

DOWNLOAD_EXIT=$?

if [[ ${DOWNLOAD_EXIT} -eq 0 ]]; then
  echo ""
  echo -e "${GREEN}=========================================${NC}"
  echo -e "${GREEN}Download Summary${NC}"
  echo -e "${GREEN}=========================================${NC}"

  # Show model size
  MODEL_SLUG=$(echo "${MODEL_NAME}" | sed 's/\//__/g')
  MODEL_PATH="${HF_HOME}/hub/models--${MODEL_SLUG}"

  if [[ -d "${MODEL_PATH}" ]]; then
    MODEL_SIZE=$(du -sh "${MODEL_PATH}" | cut -f1)
    echo -e "${BLUE}Model size:${NC}  ${MODEL_SIZE}"
    echo -e "${BLUE}Location:${NC}    ${MODEL_PATH}"
  fi

  # Show total cache usage
  TOTAL_CACHE=$(du -sh "${HF_HOME}" | cut -f1)
  echo -e "${BLUE}Total cache:${NC} ${TOTAL_CACHE}"

  echo ""
  echo -e "${GREEN}✓ Ready to use in GPU jobs!${NC}"
  exit 0
else
  echo ""
  echo -e "${RED}✗ Download failed or interrupted${NC}"
  echo -e "${YELLOW}You can run this script again to resume the download.${NC}"
  exit 1
fi
