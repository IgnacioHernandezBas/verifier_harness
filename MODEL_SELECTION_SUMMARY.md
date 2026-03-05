# Model Selection Summary

## Final Model Recommendation (Gemini-Approved)

Based on your constraints and Gemini's analysis, here's the optimized setup:

### Models to Use:

1. **DeepSeek-Coder-V2-Instruct-AWQ** (~40GB)
   - **Model ID**: `casperhansen/deepseek-coder-v2-instruct-awq`
   - **Architecture**: 236B total params (MoE), 21B active per token
   - **Use for**: Test generation in hybrid agent loop
   - **Why**: Best-in-class for complex reasoning and cross-file dependencies
   - **Status**: ⏳ Ready to download

2. **Qwen2.5-Coder-32B-Instruct-AWQ** (19GB)
   - **Model ID**: `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`
   - **Architecture**: 32B dense params
   - **Use for**: Claim extraction
   - **Why**: Excellent instruction following, strict JSON schema adherence
   - **Status**: ✅ Already downloaded

3. **Meta-Llama-3.1-70B-Instruct-AWQ** (38GB)
   - **Model ID**: `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4`
   - **Architecture**: 70B dense params
   - **Use for**: Baseline comparison for claim extraction
   - **Status**: ✅ Already downloaded

**Total Storage**: 19GB + 40GB + 38GB = **97GB**

## Storage Status

- **Available**: 79GB free space
- **Qwen-32B**: Already in cache (19GB)
- **Llama-70B**: Already in cache (38GB)
- **Need**: ~40GB for DeepSeek-V2
- **Verdict**: ✅ Sufficient space for all models

## Hardware Configuration

- **GPUs**: 2x A6000 (48GB each) or 2x L40S (48GB each)
- **Total VRAM**: 96GB
- **Model VRAM Usage**:
  - DeepSeek-V2 (40GB model) → ~42-45GB VRAM with tensor parallelism across 2 GPUs
  - Qwen-32B (19GB model) → ~22-25GB VRAM on single GPU
  - Llama-70B (38GB model) → ~40-44GB VRAM with tensor parallelism across 2 GPUs

All models fit comfortably in your 96GB VRAM budget.

## Why This Setup Over Gemini's Original Suggestions

Gemini recommended checking:
1. ❌ **DeepSeek-V3** (671B/37B active) - No readily available AWQ quantization found
2. ❌ **GLM-4.7** - Model version doesn't exist (only GLM-4-9B)
3. ❌ **Qwen3-Coder-Next** - Not released as of Feb 2026
4. ❌ **Qwen2.5-Coder-72B-AWQ** - Qwen only released up to 32B for Coder series

However, these DO exist and are worth considering later:
- ✅ **Qwen2.5-72B-Instruct-AWQ** (standard, not Coder) - ~40GB
- ✅ **casperhansen/llama-3.3-70b-instruct-awq** - Upgrade from 3.1

## Gemini's Key Insights

### MoE vs Dense Models
- **DeepSeek-V2 (236B MoE)** is faster than dense 70B (only 21B active)
- **Trade-off**: Larger disk footprint but better throughput
- **Best for**: Complex reasoning, cross-file dependencies

### Task Allocation
- **Claim Extraction**: Qwen-32B (fast, precise, excellent instruction following)
- **Test Generation**: DeepSeek-V2 (deep reasoning, repository-level understanding)
- **Baseline**: Llama-3.1-70B (for comparison)

### Why Avoid Smaller Models (7B-14B)
- Lack complex reasoning for cross-file dependencies
- Will worsen test generation edge case handling
- Good for autocomplete, not agentic loops

## Next Steps

### 1. Download DeepSeek-V2

**Option A: Manual download** (run in terminal):
```bash
bash /fs/nexus-scratch/ihbas/verifier_harness/download_deepseek.sh
```

**Option B: SLURM job** (recommended for reliability):
```bash
sbatch /fs/nexus-scratch/ihbas/verifier_harness/download_deepseek.sbatch
```

The download will take 10-30 minutes depending on network speed.

### 2. Update Your Scripts

For claim extraction with **Qwen-32B**:
```bash
cd /fs/nexus-scratch/ihbas/verifier_harness
./claim_extraction/scripts_slurm/submit_claim_extraction.sh 32b
```

For claim extraction with **DeepSeek-V2** (after download):
```bash
./claim_extraction/scripts_slurm/submit_claim_extraction.sh custom \
  --model "casperhansen/deepseek-coder-v2-instruct-awq" \
  --gpus 2 \
  --config claim_extraction/configs/claim_extraction_v2_2.yaml
```

### 3. Test and Compare

Run claim extraction with all three models on a small sample:
```bash
# Qwen-32B (1 GPU)
./claim_extraction/scripts_slurm/submit_claim_extraction.sh 32b --limit 10

# Llama-70B (2 GPUs)
./claim_extraction/scripts_slurm/submit_claim_extraction.sh 70b --limit 10

# DeepSeek-V2 (2 GPUs) - after download completes
./claim_extraction/scripts_slurm/submit_claim_extraction.sh custom \
  --model "casperhansen/deepseek-coder-v2-instruct-awq" \
  --gpus 2 --limit 10 \
  --config claim_extraction/configs/claim_extraction_v2_2.yaml
```

Compare:
- Claim extraction accuracy
- JSON schema adherence
- Inference speed
- Test discrimination quality

## Future Considerations

If you need to free up more space later:
1. Remove Llama-3.1-70B (saves 38GB)
2. Consider upgrading to **Llama-3.3-70B-AWQ** (same size, better performance)
3. Try **Qwen2.5-72B-Instruct-AWQ** (standard version) for comparison

## Alternative Quantization Strategies (Gemini's Advice)

If performance isn't satisfactory:
- **EXL2 format**: Better quality preservation than AWQ at 4.5-bit
- **GGUF**: Can use CPU offloading but will be slower
- **Avoid**: Base/completion models like StarCoder2 (need instruct models)

## Questions?

Monitor download progress:
```bash
tail -f /fs/nexus-scratch/ihbas/verifier_harness/download_deepseek_*.log
```

Check available space:
```bash
df -h /fs/cml-scratch/
```

List all cached models:
```bash
ls -lh /fs/cml-scratch/ihbas/cache/huggingface/hub/models--*/
```
