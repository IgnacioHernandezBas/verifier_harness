# Model Cache Management Guide

## Overview

Models are cached in `/fs/cml-scratch/ihbas/cache/huggingface/` to avoid re-downloading on every job.

**Current Status:**
- Cache location: `/fs/cml-scratch/ihbas/cache/huggingface/`
- Available space: 39TB
- Current usage: 77GB (2 models)

## Problem: Downloading During GPU Jobs

❌ **Bad Practice:** Let vLLM download during GPU job
```bash
# Job starts with 2 GPUs allocated
# vLLM tries to load model → not in cache → starts 40GB download
# 10-15 minutes pass with GPUs idle
# You pay for GPU time while downloading!
```

✅ **Best Practice:** Pre-download before submitting job
```bash
# Download on login node (no GPU allocation)
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4

# Then submit job → instant model loading
sbatch ...
```

## Pre-Download Models

### Quick Start

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm

# Download Meta-Llama-3.1-70B-Instruct-AWQ (~35-40GB)
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4

# Download Qwen2.5-Coder-32B-Instruct-AWQ (~19GB)
./download_model.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ

# Download DeepSeek-Coder-V2-Lite-Instruct (~30GB)
./download_model.sh deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
```

### What Happens During Download

1. **Connection:** Script connects to HuggingFace Hub
2. **Enumeration:** Lists all files in the model repo
3. **Download:** Downloads model weights in chunks
4. **Verification:** Checks file integrity
5. **Cache:** Stores in `/fs/cml-scratch/ihbas/cache/huggingface/hub/`

**Typical download times:**
- 70B-AWQ (35-40GB): 8-15 minutes
- 32B-AWQ (18-20GB): 5-10 minutes
- 16B (30GB): 7-12 minutes

### Resume Interrupted Downloads

HuggingFace automatically resumes interrupted downloads:

```bash
# Download starts
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4

# You press Ctrl+C or connection drops
^C
⚠ Download interrupted. Run again to resume.

# Run again → resumes from where it stopped
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
# Downloading... (resuming from 15GB/40GB)
```

**How resume works:**
- HuggingFace uses HTTP range requests
- Partial files are stored with `.incomplete` suffix
- On resume, checks what's already downloaded
- Downloads only missing chunks

## Check What's Cached

### List All Cached Models

```bash
ls -lh /fs/cml-scratch/ihbas/cache/huggingface/hub/

# Output:
# models--meta-llama--Meta-Llama-3.1-70B-Instruct-AWQ
# models--Qwen--Qwen2.5-Coder-32B-Instruct-AWQ
# models--deepseek-ai--DeepSeek-Coder-V2-Lite-Instruct
```

### Check Model Sizes

```bash
du -sh /fs/cml-scratch/ihbas/cache/huggingface/hub/models--*
```

### Check Total Cache Usage

```bash
du -sh /fs/cml-scratch/ihbas/cache/huggingface/
# Output: 115G (after downloading 70B model)

# Check available space
df -h /fs/cml-scratch | grep cml-scratch
# Output: 39T available
```

### Verify Model is Complete

```bash
# Check for incomplete files
find /fs/cml-scratch/ihbas/cache/huggingface/hub/ -name "*.incomplete"

# No output = all downloads complete
# Files listed = incomplete downloads
```

## Clean Up Cache

### Remove a Specific Model

```bash
# Find the model directory
MODEL_DIR="/fs/cml-scratch/ihbas/cache/huggingface/hub/models--meta-llama--Meta-Llama-3.1-70B-Instruct-AWQ"

# Check size before deleting
du -sh "${MODEL_DIR}"

# Remove it
rm -rf "${MODEL_DIR}"
```

### Clean Incomplete Downloads

```bash
# Remove all incomplete downloads
find /fs/cml-scratch/ihbas/cache/huggingface/hub/ -name "*.incomplete" -delete

# Remove temporary files
find /fs/cml-scratch/ihbas/cache/huggingface/hub/ -name "*.tmp" -delete
```

### Clean Old Models (if space needed)

```bash
# List models by last access time (oldest first)
ls -ltu /fs/cml-scratch/ihbas/cache/huggingface/hub/

# Remove models you no longer use
rm -rf /fs/cml-scratch/ihbas/cache/huggingface/hub/models--OLD_MODEL_NAME
```

## Job Scenarios

### Scenario 1: Model Already Cached ✅

```bash
# Check if cached
ls /fs/cml-scratch/ihbas/cache/huggingface/hub/ | grep Meta-Llama-3.1-70B

# Found! Submit job immediately
sbatch --export=...,TESTS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4" ...

# Job starts → vLLM loads from cache → instant (30 seconds)
# No download time, no GPU waste
```

### Scenario 2: Model NOT Cached ❌

```bash
# Check if cached
ls /fs/cml-scratch/ihbas/cache/huggingface/hub/ | grep Meta-Llama-3.1-70B
# (no output)

# Option A: Pre-download first (RECOMMENDED)
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
# Wait 10-15 minutes
# Then submit job

# Option B: Let job download (NOT RECOMMENDED)
sbatch ...
# Job allocates 2 GPUs
# vLLM starts download
# 10-15 minutes of idle GPU time ($$$)
# Model finally loads
# Job runs
```

### Scenario 3: Download Interrupted During Job 🔄

```bash
# Job starts
sbatch --time=02:00:00 ...

# vLLM starts downloading 70B model
# 10 minutes in, job hits time limit or is killed
# Partial download in cache

# Re-submit job
sbatch --time=03:00:00 ...

# vLLM resumes download from 25GB/40GB
# 5 more minutes to finish download
# Model loads, job runs

# Total waste: 15 minutes of GPU time across 2 jobs
```

### Scenario 4: Parallel Downloads (Multiple Jobs) ⚠️

```bash
# Job 1 starts downloading 70B model
# Job 2 starts while Job 1 is downloading
# Both jobs try to download the same model

# HuggingFace hub library uses file locks
# Job 2 will wait for Job 1's download to complete
# Both jobs waste GPU time

# Solution: Pre-download once, then submit all jobs
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
sbatch ... # Job 1
sbatch ... # Job 2
sbatch ... # Job 3
# All jobs start immediately with cached model
```

## Expected Disk Usage

After downloading all common models:

| Model | Size | Purpose |
|-------|------|---------|
| Meta-Llama-3.1-70B-Instruct-AWQ | 35-40GB | High-quality test generation |
| Qwen2.5-Coder-32B-Instruct-AWQ | 18-20GB | Claim extraction, medium tests |
| DeepSeek-Coder-V2-Lite-Instruct | 28-30GB | Fast iteration, development |
| **Total** | **~85-90GB** | All models cached |

**Available after all downloads:** 38.9TB (99.8% free)

## Best Practices

1. **Pre-download before batch jobs:**
   ```bash
   # Download once
   ./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4

   # Run many jobs
   for instance in instance1 instance2 instance3; do
     sbatch --export=...,INSTANCE_ID="${instance}" ...
   done
   ```

2. **Verify cache before job submission:**
   ```bash
   # Quick check
   MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
   MODEL_SLUG=$(echo "${MODEL}" | sed 's/\//__/g')

   if [[ -d "/fs/cml-scratch/ihbas/cache/huggingface/hub/models--${MODEL_SLUG}" ]]; then
     echo "✓ Model cached, safe to submit job"
     sbatch ...
   else
     echo "⚠ Model not cached, downloading first"
     ./download_model.sh "${MODEL}"
   fi
   ```

3. **Run downloads in background:**
   ```bash
   # Start download in background
   nohup ./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4 > download.log 2>&1 &

   # Check progress
   tail -f download.log

   # Check if complete
   tail -1 download.log | grep "✓ Download complete"
   ```

4. **Download multiple models in parallel:**
   ```bash
   # Download 3 models simultaneously
   ./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4 > dl_70b.log 2>&1 &
   ./download_model.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ > dl_32b.log 2>&1 &
   ./download_model.sh deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct > dl_ds.log 2>&1 &

   # Monitor all
   tail -f dl_*.log
   ```

## Troubleshooting

### "No space left on device"

```bash
# Check available space
df -h /fs/cml-scratch

# If truly full, clean old models
du -sh /fs/cml-scratch/ihbas/cache/huggingface/hub/models--* | sort -h

# Remove largest unused model
rm -rf /fs/cml-scratch/ihbas/cache/huggingface/hub/models--UNUSED_MODEL
```

### "Connection timeout" during download

```bash
# HuggingFace hub might be slow or down
# Retry with the same command (will resume)
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4

# Or check HuggingFace status
curl -I https://huggingface.co
```

### Stuck download (no progress)

```bash
# Kill the download
Ctrl+C

# Remove incomplete files
find /fs/cml-scratch/ihbas/cache/huggingface/hub/ -name "*.incomplete" -delete

# Retry
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
```

### vLLM can't find cached model

```bash
# Check environment variables match
echo $HF_HOME
echo $TRANSFORMERS_CACHE

# Should both be: /fs/cml-scratch/ihbas/cache/huggingface

# Verify model directory exists
MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
MODEL_SLUG=$(echo "${MODEL}" | sed 's/\//__/g')
ls -lh /fs/cml-scratch/ihbas/cache/huggingface/hub/models--${MODEL_SLUG}/
```

### Corrupted download

```bash
# Symptoms: vLLM crashes with "Invalid file" or "Unexpected EOF"

# Remove the model entirely
rm -rf /fs/cml-scratch/ihbas/cache/huggingface/hub/models--meta-llama--Meta-Llama-3.1-70B-Instruct-AWQ

# Re-download
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
```

## Quick Reference Commands

```bash
# Download model
./download_model.sh MODEL_NAME

# Check what's cached
ls -lh /fs/cml-scratch/ihbas/cache/huggingface/hub/

# Check sizes
du -sh /fs/cml-scratch/ihbas/cache/huggingface/hub/models--*

# Check total usage
du -sh /fs/cml-scratch/ihbas/cache/huggingface/

# Check available space
df -h /fs/cml-scratch

# Remove a model
rm -rf /fs/cml-scratch/ihbas/cache/huggingface/hub/models--MODEL_SLUG

# Clean incomplete downloads
find /fs/cml-scratch/ihbas/cache/huggingface/ -name "*.incomplete" -delete
```
