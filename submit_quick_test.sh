#!/bin/bash
#
# Quick test script - Run ONE instance via SLURM
#

cd /home/user/verifier_harness

echo "🚀 Submitting quick test instance: astropy__astropy-12907"
echo "📊 This will run with all 3 phases (static, fuzzing, rules)"
echo ""

# Submit batch job with limit 1
python scripts/submit_integrated_batch.py \
  --instance-file quick_test_instance.txt \
  --enable-static \
  --enable-fuzzing \
  --enable-rules \
  --cpus 4 \
  --mem 8 \
  --time 30 \
  --max-parallel 1

echo ""
echo "✅ Job submitted!"
echo ""
echo "To monitor the job:"
echo "  squeue -u \$USER"
echo ""
echo "To watch the log in real-time:"
echo "  bash scripts/monitor_job.sh"
echo ""
echo "To check results:"
echo "  ls -lh results/astropy__astropy-12907.json"
