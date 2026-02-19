# Model Reference Guide

## Available Models for Test Generation

### Meta Llama 3.1 70B (AWQ Quantized)

**Correct Model Name:**
```
hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
```

**Properties:**
- Size: ~35-40GB (4-bit quantized)
- Downloads: 84,083+ (very popular)
- Gated: No (no authentication required)
- Provider: hugging-quants (official quantization org)

**NOT:** `meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ` ❌

**GPU Requirements:**
- Minimum: 1x RTX A6000 (48GB) - context limited to 4096
- Recommended: 2x RTX A6000 (48GB) - full 8192 context
- Maximum: 4x RTX A6000 (48GB) - extended context

**Download:**
```bash
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
```

**Use in jobs:**
```bash
./submit_multi_gpu.sh 70b astropy__astropy-7746
```

---

### Qwen 2.5 Coder 32B (AWQ Quantized)

**Model Name:**
```
Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
```

**Properties:**
- Size: ~18-20GB (4-bit quantized)
- Gated: No
- Provider: Qwen (official)

**GPU Requirements:**
- Recommended: 1x RTX A6000 (48GB) - optimal
- Can use: 2x RTX A6000 for higher throughput

**Download:**
```bash
./download_model.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
```

**Use in jobs:**
```bash
./submit_multi_gpu.sh 32b astropy__astropy-7746
```

---

### DeepSeek Coder V2 Lite (16B)

**Model Name:**
```
deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
```

**Properties:**
- Size: ~28-30GB (FP16, not quantized)
- Gated: No
- Provider: deepseek-ai (official)

**GPU Requirements:**
- Recommended: 1x RTX A6000 (48GB) - optimal

**Download:**
```bash
./download_model.sh deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
```

**Use in jobs:**
```bash
./submit_multi_gpu.sh 7b astropy__astropy-7746  # Script accepts 7b/8b for small models
```

---

## Alternative 70B Models

If you want to try other 70B variants:

### Llama 3.1 Nemotron 70B (Nvidia Fine-tuned)
```
ibnzterrell/Nvidia-Llama-3.1-Nemotron-70B-Instruct-HF-AWQ-INT4
```
- Downloads: 488
- Optimized by Nvidia for improved instruction following

### Hermes 3 Llama 3.1 70B (NousResearch)
```
mbley/NousResearch-Hermes-3-Llama-3.1-70B-AWQ
```
- Downloads: 210
- Fine-tuned by NousResearch for better reasoning

---

## Quick Command Reference

### Download Models

```bash
# 70B model (recommended for high quality)
./download_model.sh hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4

# 32B model (good balance)
./download_model.sh Qwen/Qwen2.5-Coder-32B-Instruct-AWQ

# 16B model (fast iteration)
./download_model.sh deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
```

### Submit Jobs

```bash
# 70B with 2 GPUs (recommended)
./submit_multi_gpu.sh 70b astropy__astropy-7746

# 32B with 1 GPU
./submit_multi_gpu.sh 32b astropy__astropy-7746

# Multimodal: Qwen claims + Llama tests
./submit_multi_gpu.sh 70b astropy__astropy-7746 \
  --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
```

### Direct sbatch (Advanced)

```bash
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
```

---

## Model Size Comparison

| Model | Size | GPU Memory | Speed (tok/s) | Quality |
|-------|------|------------|---------------|---------|
| Llama 3.1 70B AWQ | 35-40GB | 48GB (1 GPU) or 24GB/GPU (2 GPU) | 30-45 | Excellent |
| Qwen 2.5 32B AWQ | 18-20GB | 20GB | 40-60 | Very Good |
| DeepSeek V2 Lite 16B | 28-30GB | 30GB | 60-80 | Good |

---

## Common Mistakes

❌ **Wrong model path:**
```bash
meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ
# Error: 401 Repository Not Found
```

✅ **Correct model path:**
```bash
hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
# Works! No authentication needed
```

❌ **Missing organization prefix:**
```bash
Meta-Llama-3.1-70B-Instruct-AWQ-INT4
# Error: Invalid model name
```

✅ **With organization:**
```bash
hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
# Correct format: organization/model-name
```

---

## Why hugging-quants?

The `hugging-quants` organization provides:

1. **Official quantizations** of popular models
2. **AWQ (Activation-aware Weight Quantization)** - best quality at 4-bit
3. **No gating** - unlike official Meta repos which require licenses
4. **Popular & tested** - 84k+ downloads for Llama 3.1 70B
5. **Optimized for vLLM** - works perfectly with your setup

Meta's official models (`meta-llama/...`) are usually:
- Gated (require HuggingFace token + license acceptance)
- Full precision (BF16/FP16, much larger)
- Not quantized (would need ~140GB for 70B)

---

## Checking Model Availability

Before downloading, verify the model exists:

```bash
python3 << 'EOF'
from huggingface_hub import model_info

model = "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
info = model_info(model)

print(f"Model: {info.id}")
print(f"Downloads: {info.downloads:,}")
print(f"Likes: {info.likes}")
print(f"Tags: {info.tags[:5]}")
EOF
```

---

## Need Help?

- Check `MULTI_GPU_GUIDE.md` for GPU configuration
- Check `CACHE_MANAGEMENT.md` for download issues
- Check vLLM logs: `agentic_closed_loop/scripts_slurm/logs/vllm_multi_*.log`
