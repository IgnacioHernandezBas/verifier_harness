#!/bin/bash
#SBATCH --job-name=test_cache
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm/logs/test_cache_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm/logs/test_cache_%j.err
#SBATCH --time=00:30:00
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:l40s:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

# Quick test to verify /fs/cml-scratch works for model caching

echo "=========================================="
echo "Testing Model Cache on /fs/cml-scratch"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "=========================================="
echo ""

# Set new cache location for this test
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface_test
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface_test

# Check space
echo "Current space on /fs/cml-scratch:"
df -h /fs/cml-scratch | tail -1
echo ""

# Test model (small and fast)
TEST_MODEL="Qwen/Qwen2.5-Coder-1.5B-Instruct"

echo "Downloading test model: $TEST_MODEL"
echo "Cache location: $HF_HOME"
echo ""

# Run quick inference test
conda run -n verifier_llm python << 'PYTHON_EOF'
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-1.5B-Instruct")

print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)

print("\n" + "="*60)
print("Running quick inference test...")
print("="*60)

prompt = "def add(a, b):"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=30,
        temperature=0.7,
        do_sample=True
    )

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(f"\nPrompt: {prompt}")
print(f"Response:\n{response}")

print("\n" + "="*60)
print("✅ SUCCESS! Model works from /fs/cml-scratch")
print("="*60)
PYTHON_EOF

exit_code=$?

echo ""
echo "=========================================="
if [ $exit_code -eq 0 ]; then
    echo "✅ Test PASSED"
    echo "=========================================="
    echo ""
    echo "Cache location verified: $HF_HOME"
    echo "Cache size:"
    du -sh $HF_HOME
    echo ""
    echo "Next steps:"
    echo "1. Clean up test cache: rm -rf $HF_HOME"
    echo "2. Update your sbatch scripts to use:"
    echo "   export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface"
    echo "   export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface"
else
    echo "❌ Test FAILED (exit code: $exit_code)"
    echo "=========================================="
fi
