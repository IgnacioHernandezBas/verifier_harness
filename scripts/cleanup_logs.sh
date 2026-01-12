#!/bin/bash
#
# Log Cleanup Script
# Cleans old SLURM logs to free disk space
#

set -e

LOGS_DIR="logs"
DRY_RUN=false
KEEP_LATEST=2  # Keep logs from latest N job IDs

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -d, --dry-run       Show what would be deleted without deleting
    -k, --keep N        Keep logs from latest N jobs (default: 2)
    -a, --all           Delete all logs except current job
    -h, --help          Show this help message

Examples:
    $0 --dry-run        # See what would be deleted
    $0 --keep 3         # Keep latest 3 job runs
    $0 --all            # Delete all old logs
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -k|--keep)
            KEEP_LATEST="$2"
            shift 2
            ;;
        -a|--all)
            KEEP_LATEST=1
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo "========================================"
echo "Log Cleanup Tool"
echo "========================================"
echo "Logs directory: $LOGS_DIR"
echo "Keep latest: $KEEP_LATEST job(s)"
echo "Dry run: $DRY_RUN"
echo ""

# Get current stats
total_files=$(find $LOGS_DIR -type f | wc -l)
total_size=$(du -sh $LOGS_DIR | cut -f1)
echo -e "${YELLOW}Current stats:${NC}"
echo "  Total files: $total_files"
echo "  Total size: $total_size"
echo ""

# Find all unique array job IDs (sorted by job ID, newest first)
echo -e "${YELLOW}Finding array jobs...${NC}"
job_ids=$(ls $LOGS_DIR/array_*.out 2>/dev/null | \
    sed 's/.*array_\([0-9]*\)_.*/\1/' | \
    sort -rn -u)

if [ -z "$job_ids" ]; then
    echo "No array job logs found."
else
    echo "Found job IDs:"
    count=0
    for job in $job_ids; do
        count=$((count + 1))
        file_count=$(ls $LOGS_DIR/array_${job}_*.{out,err} 2>/dev/null | wc -l)
        if [ $count -le $KEEP_LATEST ]; then
            echo -e "  ${GREEN}[KEEP]${NC} Job $job: $file_count files"
        else
            echo -e "  ${RED}[DELETE]${NC} Job $job: $file_count files"
        fi
    done
    echo ""
fi

# Delete old array job logs
if [ "$DRY_RUN" = false ]; then
    echo -e "${YELLOW}Deleting old array job logs...${NC}"
    count=0
    for job in $job_ids; do
        count=$((count + 1))
        if [ $count -gt $KEEP_LATEST ]; then
            echo "  Deleting job $job..."
            rm -f $LOGS_DIR/array_${job}_*.out $LOGS_DIR/array_${job}_*.err
        fi
    done
fi

# Clean up old non-array logs (fuzzing, integrated, etc.)
echo ""
echo -e "${YELLOW}Old standalone logs:${NC}"
old_logs=$(find $LOGS_DIR -type f \
    -name "*.out" -o -name "*.err" | \
    grep -v "array_" | \
    wc -l)

if [ $old_logs -gt 0 ]; then
    echo "  Found $old_logs old standalone log files"

    # List the types
    echo "  Types:"
    find $LOGS_DIR -type f \( -name "*.out" -o -name "*.err" \) | \
        grep -v "array_" | \
        sed 's/.*\///' | \
        sed 's/_[0-9]*.*//' | \
        sort | uniq -c | \
        awk '{printf "    %s: %d files\n", $2, $1}'

    if [ "$DRY_RUN" = false ]; then
        read -p "  Delete these standalone logs? (y/N): " confirm
        if [[ $confirm == [yY] ]]; then
            echo "  Deleting standalone logs..."
            find $LOGS_DIR -type f \( -name "*.out" -o -name "*.err" \) | \
                grep -v "array_" | \
                xargs rm -f
        fi
    fi
else
    echo "  No old standalone logs found."
fi

echo ""
echo "========================================"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN COMPLETE${NC}"
    echo "Run without --dry-run to actually delete files"
else
    # Show new stats
    new_total_files=$(find $LOGS_DIR -type f | wc -l)
    new_total_size=$(du -sh $LOGS_DIR | cut -f1)
    deleted=$((total_files - new_total_files))

    echo -e "${GREEN}CLEANUP COMPLETE${NC}"
    echo "  Files deleted: $deleted"
    echo "  New file count: $new_total_files"
    echo "  New total size: $new_total_size"
fi
echo "========================================"
