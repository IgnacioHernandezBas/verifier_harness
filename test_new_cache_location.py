#!/usr/bin/env python3
"""
Test script to verify model download and inference from /fs/cml-scratch
"""
import os
import sys

# Set cache to new location BEFORE importing transformers
os.environ['HF_HOME'] = '/fs/cml-scratch/ihbas/cache/huggingface_test'
os.environ['TRANSFORMERS_CACHE'] = '/fs/cml-scratch/ihbas/cache/huggingface_test'

print(f"Testing model cache at: {os.environ['HF_HOME']}")
print(f"Free space check...")
os.system("df -h /fs/cml-scratch | tail -1")
print()

# Small test model: ~500MB, fast to download
TEST_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

print(f"Downloading test model: {TEST_MODEL}")
print("This will take 1-2 minutes...")
print()

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

    # Download tokenizer and model
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(TEST_MODEL)

    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        TEST_MODEL,
        torch_dtype=torch.float16,
        device_map="cpu"  # CPU only for quick test
    )

    # Quick inference test
    print("\n" + "="*60)
    print("Running quick inference test...")
    print("="*60)

    prompt = "Write a Python function to add two numbers:"
    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            temperature=0.7,
            do_sample=True
        )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")

    # Check cache location
    print("\n" + "="*60)
    print("Verifying cache location...")
    print("="*60)
    cache_path = os.environ['HF_HOME']
    print(f"Cache directory: {cache_path}")
    os.system(f"du -sh {cache_path}")
    os.system(f"ls -lh {cache_path}/hub/ | head -5")

    print("\n" + "="*60)
    print("✅ SUCCESS! Model download and inference work from /fs/cml-scratch")
    print("="*60)
    print("\nYou can now safely migrate your main cache to /fs/cml-scratch")
    print(f"Test cache location: {cache_path}")
    print("\nTo clean up this test:")
    print(f"  rm -rf {cache_path}")

    sys.exit(0)

except Exception as e:
    print("\n" + "="*60)
    print("❌ ERROR during test")
    print("="*60)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
