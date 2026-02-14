#!/bin/bash
#
# Quick test to verify /fs/cml-scratch works for model caching
#

echo "=========================================="
echo "Testing Model Cache on /fs/cml-scratch"
echo "=========================================="
echo ""

# Check available space first
echo "Current space on /fs/cml-scratch:"
df -h /fs/cml-scratch | tail -1
echo ""

# Run the test
conda run -n verifier_llm python /fs/nexus-scratch/ihbas/verifier_harness/test_new_cache_location.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Test PASSED - /fs/cml-scratch works!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Clean up test cache: rm -rf /fs/cml-scratch/ihbas/cache/huggingface_test"
    echo "2. Update your environment variables in .bashrc or sbatch scripts:"
    echo "   export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface"
    echo "   export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface"
    echo "3. Optionally move existing models:"
    echo "   mv /fs/nexus-scratch/ihbas/cache/huggingface/* /fs/cml-scratch/ihbas/cache/huggingface/"
else
    echo ""
    echo "=========================================="
    echo "❌ Test FAILED"
    echo "=========================================="
    echo ""
    echo "Check the error above. Possible issues:"
    echo "- Permission problems on /fs/cml-scratch"
    echo "- Network issues downloading model"
    echo "- Missing conda environment 'verifier_llm'"
fi
