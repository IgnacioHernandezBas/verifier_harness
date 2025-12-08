#!/bin/bash
# Monitor the latest test_patch job

LATEST_LOG=$(ls -t logs/test_patch_real_*.out 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "No log files found yet"
    exit 1
fi

echo "Monitoring: $LATEST_LOG"
echo "Press Ctrl+C to stop"
echo "======================================================================"
tail -f "$LATEST_LOG"
