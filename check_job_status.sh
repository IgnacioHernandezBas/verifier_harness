#!/bin/bash
#
# Check status of SLURM jobs and results
#

echo "=========================================="
echo "📊 SLURM Job Status"
echo "=========================================="
echo ""

# Show running/pending jobs
echo "🔄 Your active jobs:"
squeue -u $USER --format="%.18i %.9P %.30j %.8T %.10M %.6D %R"
echo ""

# Show recent completed jobs
echo "📜 Recent completed jobs (last 5):"
sacct -u $USER --format="JobID,JobName%30,State,ExitCode,Elapsed" -n | tail -5
echo ""

echo "=========================================="
echo "📁 Recent Results"
echo "=========================================="
echo ""

# Show most recent result files
echo "🎯 Latest result files (last 5):"
ls -lht results/*.json 2>/dev/null | head -5 || echo "No results found yet"
echo ""

echo "=========================================="
echo "📝 Recent Logs"
echo "=========================================="
echo ""

# Show most recent logs
echo "📄 Latest log files (last 5):"
ls -lht logs/*.out 2>/dev/null | head -5 || echo "No logs found yet"
echo ""

echo "💡 Tips:"
echo "  - Watch live logs: bash scripts/monitor_job.sh"
echo "  - Cancel job: scancel <JOB_ID>"
echo "  - View specific log: tail -f logs/<filename>"
echo "  - View result: cat results/<instance_id>.json | python -m json.tool"
