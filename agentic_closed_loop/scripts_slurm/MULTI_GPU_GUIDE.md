# Multi-GPU Configuration Guide

## Overview

The `run_agentic_loop_hybrid_multiple.sbatch` script automatically optimizes vLLM parameters based on:
- Number of GPUs allocated
- Model size (70B, 32B, 7B)
- Available memory

## Quick Start

### Using the Helper Script (Recommended)

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm

# 70B model with 2 GPUs (recommended)
./submit_multi_gpu.sh 70b astropy__astropy-7746

# 70B model with 4 GPUs (maximum throughput)
./submit_multi_gpu.sh 70b astropy__astropy-7746 --gpus 4

# Multimodal: Qwen for claims, Llama-70B for tests
./submit_multi_gpu.sh 70b pytest-dev__pytest-5413 \
  --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
```

### Direct sbatch Submission

```bash
# 2 GPUs (recommended for 70B)
sbatch --export=ALL,\
INSTANCE_ID=astropy__astropy-7746,\
TESTS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",\
CLAIMS_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",\
MAX_ATTEMPTS=10,\
USE_MODEL_SUBDIRS=true \
--gres=gpu:rtxa6000:2 \
--cpus-per-task=16 \
--mem=128G \
run_agentic_loop_hybrid_multiple.sbatch

# 4 GPUs (maximum throughput)
sbatch --export=ALL,\
INSTANCE_ID=astropy__astropy-7746,\
TESTS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",\
CLAIMS_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",\
MAX_ATTEMPTS=10 \
--gres=gpu:rtxa6000:4 \
--cpus-per-task=32 \
--mem=256G \
run_agentic_loop_hybrid_multiple.sbatch
```

## Configuration Matrix

### Meta-Llama-3.1-70B-Instruct-AWQ

| GPUs | Memory/GPU | Context | Throughput | Config | Use Case |
|------|------------|---------|------------|--------|----------|
| 1 | 48GB | 4096 | 15-25 tok/s | Budget | Limited resources |
| **2** | 24GB | **8192** | **30-45 tok/s** | **Recommended** | **Best balance** |
| 4 | 12GB | 12288 | 50-70 tok/s | Maximum | Batch processing |

### Qwen2.5-Coder-32B-Instruct-AWQ

| GPUs | Memory/GPU | Context | Throughput | Config | Use Case |
|------|------------|---------|------------|--------|----------|
| **1** | 20GB | **8192** | **40-60 tok/s** | **Optimal** | **Single instance** |
| 2 | 10GB | 12288 | 70-90 tok/s | High throughput | Batch processing |

### DeepSeek-Coder-V2-Lite-Instruct (16B)

| GPUs | Memory/GPU | Context | Throughput | Config | Use Case |
|------|------------|---------|------------|--------|----------|
| **1** | 12GB | **8192** | **60-80 tok/s** | **Optimal** | **Fast iteration** |

## Auto-Configuration Details

The script automatically adjusts these vLLM parameters:

### 1 GPU Configuration
```python
--gpu-memory-utilization 0.95        # Use almost all memory
--max-model-len 4096                 # Reduced context for 70B
--max-num-seqs 32                    # Lower batch size
--enforce-eager                       # Disable CUDA graphs (saves 2-3GB)
```

### 2 GPU Configuration (Recommended for 70B)
```python
--tensor-parallel-size 2             # Split model across GPUs
--gpu-memory-utilization 0.90        # Balanced utilization
--max-model-len 8192                 # Full context window
--max-num-seqs 64                    # Moderate batch size
```

### 4+ GPU Configuration
```python
--tensor-parallel-size 4             # Split across all GPUs
--gpu-memory-utilization 0.85        # More headroom
--max-model-len 12288                # Extended context
--max-num-seqs 128                   # High batch size
--enable-chunked-prefill             # Better throughput
```

## Manual Overrides

You can override auto-detected parameters via environment variables:

```bash
sbatch --export=ALL,\
INSTANCE_ID=astropy__astropy-7746,\
TESTS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",\
VLLM_MAX_MODEL_LEN=6144,\            # Override context length
VLLM_GPU_MEMORY_UTIL=0.92,\          # Override memory utilization
VLLM_MAX_NUM_SEQS=48 \               # Override batch size
--gres=gpu:rtxa6000:2 \
run_agentic_loop_hybrid_multiple.sbatch
```

## Monitoring

### Check Job Status
```bash
# Find your job
squeue -u $USER

# Watch specific job
watch -n 2 squeue -j JOB_ID
```

### Monitor vLLM Startup
```bash
# Watch vLLM server logs
tail -f agentic_closed_loop/scripts_slurm/logs/vllm_multi_*.log

# Check for errors during model loading
grep -i "error\|warning\|oom" agentic_closed_loop/scripts_slurm/logs/vllm_multi_*.log
```

### Monitor GPU Usage
```bash
# SSH to the compute node (check with squeue)
ssh NODE_NAME

# Watch GPU utilization
watch -n 1 nvidia-smi

# Check GPU memory usage
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv
```

### Check Output
```bash
# Follow job output
tail -f agentic_closed_loop/scripts_slurm/logs/agentic_multi_*.out

# Check for completion
grep -E "(✓|✗|complete|failed)" agentic_closed_loop/scripts_slurm/logs/agentic_multi_*.out
```

## Troubleshooting

### OOM (Out of Memory) on Startup

**Symptoms:** vLLM fails to load model, "CUDA out of memory" in logs

**Solutions:**
1. Reduce context length:
   ```bash
   VLLM_MAX_MODEL_LEN=3072  # For 70B on 1 GPU
   ```

2. Enable eager execution:
   ```bash
   # Automatically enabled for 70B on 1 GPU
   # Forces eager mode, saves 2-3GB
   ```

3. Use more GPUs:
   ```bash
   --gres=gpu:rtxa6000:2  # Instead of 1
   ```

### OOM During Inference

**Symptoms:** Model loads successfully but crashes during generation

**Solutions:**
1. Reduce batch size:
   ```bash
   VLLM_MAX_NUM_SEQS=16  # Lower than default
   ```

2. Reduce concurrent requests:
   - Process fewer instances simultaneously

3. Lower memory utilization:
   ```bash
   VLLM_GPU_MEMORY_UTIL=0.85
   ```

### Slow Performance

**Symptoms:** Low tokens/second, high latency

**Possible Causes & Solutions:**

1. **Single GPU with 70B model**
   - Expected: 15-25 tok/s
   - Solution: Use 2+ GPUs for 2-3x speedup

2. **Context length too long**
   - Reduce `--max-model-len` if you don't need full context

3. **High batch size on limited GPUs**
   - Reduce `VLLM_MAX_NUM_SEQS`

### Model Not Found

**Symptoms:** "Model not found" or download errors

**Solutions:**
1. Check HuggingFace cache:
   ```bash
   ls -lh /fs/cml-scratch/ihbas/cache/huggingface/hub/
   ```

2. Pre-download model:
   ```bash
   python -c "from huggingface_hub import snapshot_download; \
   snapshot_download('hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4')"
   ```

3. Check network access:
   ```bash
   curl -I https://huggingface.co
   ```

## Performance Benchmarks

Based on RTX A6000 (48GB) testing:

### Meta-Llama-3.1-70B-Instruct-AWQ

| Setup | Startup Time | Tokens/sec | Memory/GPU | Context | Recommended |
|-------|--------------|------------|------------|---------|-------------|
| 1 GPU | 2-3 min | 18-22 | 45-47 GB | 4096 | ⚠️ Tight fit |
| 2 GPU | 2-3 min | 35-42 | 23-26 GB | 8192 | ✅ **Best** |
| 4 GPU | 2-3 min | 55-68 | 12-14 GB | 12288 | 🚀 Maximum |

### Qwen2.5-Coder-32B-Instruct-AWQ

| Setup | Startup Time | Tokens/sec | Memory/GPU | Context | Recommended |
|-------|--------------|------------|------------|---------|-------------|
| 1 GPU | 1-2 min | 45-55 | 18-22 GB | 8192 | ✅ **Optimal** |
| 2 GPU | 1-2 min | 75-90 | 9-12 GB | 12288 | 🚀 Overkill |

## Best Practices

1. **For 70B Models:**
   - Use **2 GPUs** as default (best balance)
   - Use 4 GPUs for batch processing multiple instances
   - Avoid 1 GPU unless necessary (context limited to 4096)

2. **For 32B Models:**
   - Use **1 GPU** (optimal)
   - Only use 2+ GPUs if processing many instances in parallel

3. **Resource Allocation:**
   - 2 GPUs: 16 CPUs, 128GB RAM
   - 4 GPUs: 32 CPUs, 256GB RAM
   - Scale CPUs and RAM with GPU count

4. **Idle Node Targeting:**
   ```bash
   # Target specific idle nodes
   sbatch --nodelist=gammagpu[15-17] ...
   ```

5. **Queue Optimization:**
   - Check node availability: `sinfo -p scavenger -o "%N %t %G" | grep idle`
   - Request fewer GPUs for faster queue times
   - Use scavenger partition for long jobs

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `INSTANCE_ID` | SWE-bench instance | Required | `astropy__astropy-7746` |
| `CLAIM_ID` | Claim identifier | `C1` | `C2` |
| `CLAIMS_MODEL` | Claim extraction model | `Qwen/...` | Custom model |
| `TESTS_MODEL` | Test generation model | Same as claims | `meta-llama/...` |
| `MAX_ATTEMPTS` | Max refinement attempts | `4` | `10` |
| `USE_MODEL_SUBDIRS` | Organize by model | `false` | `true` |
| `VLLM_MAX_MODEL_LEN` | Context window override | Auto | `6144` |
| `VLLM_GPU_MEMORY_UTIL` | GPU memory % override | Auto | `0.92` |
| `VLLM_MAX_NUM_SEQS` | Batch size override | Auto | `48` |

## Example Workflows

### 1. Single Instance with 70B Model
```bash
./submit_multi_gpu.sh 70b astropy__astropy-7746 --max-attempts 10
```

### 2. Batch Processing Multiple Instances
```bash
for instance in astropy__astropy-7746 pytest-dev__pytest-5413 django__django-13321; do
  ./submit_multi_gpu.sh 70b "${instance}" --gpus 4
done
```

### 3. Multimodal Pipeline
```bash
# Use Qwen for claims, Llama-70B for tests
./submit_multi_gpu.sh 70b astropy__astropy-7746 \
  --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" \
  --tests-model "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4" \
  --gpus 2
```

### 4. Testing with Reduced Resources
```bash
# Quick test with 1 GPU
./submit_multi_gpu.sh 70b astropy__astropy-7746 \
  --gpus 1 \
  --max-attempts 2
```

## Cost-Benefit Analysis

**2 GPUs vs 1 GPU for 70B:**
- ✅ 2x faster inference (30-45 vs 15-25 tok/s)
- ✅ 2x context window (8192 vs 4096 tokens)
- ✅ More stable (50% memory per GPU vs 95%)
- ⚠️ 2x GPU allocation cost
- ⚠️ May wait longer in queue

**4 GPUs vs 2 GPUs for 70B:**
- ✅ 1.5-2x faster inference (55-70 vs 30-45 tok/s)
- ✅ 1.5x context window (12288 vs 8192 tokens)
- ✅ Best for batch jobs
- ⚠️ 2x GPU allocation cost vs 2 GPUs
- ⚠️ Significantly longer queue wait

**Recommendation:** Use **2 GPUs** for 70B as the default sweet spot.
