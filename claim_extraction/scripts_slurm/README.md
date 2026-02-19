# Multi-GPU Claim Extraction Scripts

## Quick Start

Extract claims using Llama 70B with 2 GPUs (recommended):

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness/claim_extraction/scripts_slurm
./submit_claim_extraction.sh 70b
```

## Usage

### Basic Examples

```bash
# Extract all instances with Llama 70B (2 GPUs)
./submit_claim_extraction.sh 70b

# Use 4 GPUs for maximum throughput
./submit_claim_extraction.sh 70b --gpus 4

# Test with just first 5 instances
./submit_claim_extraction.sh 70b --limit 5

# Extract with Qwen 32B (1 GPU)
./submit_claim_extraction.sh 32b
```

### Advanced Options

```bash
# Use custom minimum claim score
./submit_claim_extraction.sh 70b --min-score 3

# Process specific instances file
./submit_claim_extraction.sh 70b --instances my_instances.json

# Custom output directory
./submit_claim_extraction.sh 70b --output-dir /path/to/output

# Dry run to see command without submitting
./submit_claim_extraction.sh 70b --dry-run
```

## Model Configurations

### Llama 70B (Recommended for High Quality)
- **Model**: `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4`
- **Config**: `claim_extraction/configs/claim_extraction_llama70b.yaml`
- **Recommended GPUs**: 2
- **Memory**: 128GB RAM
- **Use case**: High-quality claim extraction

### Qwen 32B (Fast & Efficient)
- **Model**: `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`
- **Config**: `claim_extraction/configs/claim_extraction_v2_2.yaml`
- **Recommended GPUs**: 1
- **Memory**: 64GB RAM
- **Use case**: Quick iteration, testing

## Output Structure

Claims are automatically organized by model:

```
claim_extraction/claims_out/
├── Meta-Llama-3.1-70B-Instruct-AWQ-INT4/
│   ├── astropy__astropy-7746.json
│   ├── pytest-dev__pytest-5413.json
│   ├── ...
│   └── summary.json
└── Qwen2.5-Coder-32B-Instruct-AWQ/
    ├── astropy__astropy-7746.json
    ├── pytest-dev__pytest-5413.json
    ├── ...
    └── summary.json
```

## Monitoring Jobs

After submission, monitor your job:

```bash
# Check job status
squeue -j JOB_ID

# Follow claim extraction output
tail -f logs/claim_extract_JOB_ID.out

# Follow vLLM server logs
tail -f logs/vllm_claim_JOB_ID.log
```

## GPU Configuration

The script automatically optimizes vLLM parameters based on GPU count:

| GPUs | Context | Throughput | Config | Use Case |
|------|---------|------------|--------|----------|
| 1 | 4096 | 15-25 tok/s | Budget | Limited resources |
| **2** | **8192** | **30-45 tok/s** | **Recommended** | **Best balance** |
| 4 | 12288 | 50-70 tok/s | Maximum | Batch processing |

## Troubleshooting

### vLLM fails to start
- Check GPU availability: `nvidia-smi`
- Check logs: `tail -n 100 logs/vllm_claim_JOB_ID.log`
- Try with fewer GPUs or reduce context length

### Out of memory
```bash
# Use eager execution (saves 2-3GB)
export ENFORCE_EAGER=true
./submit_claim_extraction.sh 70b --gpus 1
```

### Port already in use
The script automatically finds a free port. Check logs for the actual port used.

## Files

- **submit_claim_extraction.sh**: Helper script for job submission
- **run_claim_extraction_multi_gpu.sbatch**: SLURM batch script
- **configs/claim_extraction_llama70b.yaml**: Llama 70B configuration
- **configs/claim_extraction_v2_2.yaml**: Qwen 32B configuration

## Next Steps

After claim extraction completes:

1. Check the summary:
   ```bash
   cat claim_extraction/claims_out/Meta-Llama-3.1-70B-Instruct-AWQ-INT4/summary.json
   ```

2. Run test generation using the extracted claims:
   ```bash
   cd ../agentic_closed_loop/scripts_slurm
   ./submit_multi_gpu.sh 70b INSTANCE_ID --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
   ```
