#!/bin/bash
#
# Quick cache inspection script
#

echo "=========================================="
echo "📦 Singularity Image Cache Status"
echo "=========================================="
echo ""

CACHE_DIR="/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache"

# Check if cache directory exists
if [ ! -d "$CACHE_DIR" ]; then
    echo "⚠️  Cache directory doesn't exist: $CACHE_DIR"
    echo ""
    echo "This is normal if you haven't run any instances yet."
    echo "Images will be cached here after first execution."
    exit 0
fi

# Total cache size
echo "📊 Cache Statistics:"
echo "-------------------"
TOTAL_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
echo "Total Size: $TOTAL_SIZE"

TOTAL_FILES=$(find "$CACHE_DIR" -name "*.sif" 2>/dev/null | wc -l)
echo "Total Images: $TOTAL_FILES"
echo ""

# By repository
echo "📁 By Repository:"
echo "-------------------"
for repo_dir in "$CACHE_DIR"/*/ ; do
    if [ -d "$repo_dir" ]; then
        repo_name=$(basename "$repo_dir")
        repo_size=$(du -sh "$repo_dir" 2>/dev/null | cut -f1)
        repo_count=$(find "$repo_dir" -name "*.sif" 2>/dev/null | wc -l)
        echo "  $repo_name: $repo_count images, $repo_size"
    fi
done
echo ""

# Recent images
echo "🕐 Most Recent Images (last 5):"
echo "-------------------"
find "$CACHE_DIR" -name "*.sif" -type f -printf '%T@ %p\n' 2>/dev/null | \
    sort -rn | head -5 | \
    while read timestamp filepath; do
        filename=$(basename "$filepath" .sif)
        size=$(du -h "$filepath" | cut -f1)
        date=$(date -d "@${timestamp%.*}" '+%Y-%m-%d %H:%M' 2>/dev/null || echo "N/A")
        echo "  $filename ($size) - $date"
    done
echo ""

# Largest images
echo "💾 Largest Images (top 5):"
echo "-------------------"
find "$CACHE_DIR" -name "*.sif" -type f -exec du -h {} \; 2>/dev/null | \
    sort -rh | head -5 | \
    while read size filepath; do
        filename=$(basename "$filepath" .sif)
        echo "  $filename: $size"
    done
echo ""

# Disk space
echo "💽 Disk Space Available:"
echo "-------------------"
df -h /fs/nexus-scratch 2>/dev/null | tail -1 | awk '{print "  Available: " $4 " (" $5 " used)"}'
echo ""

echo "💡 Tips:"
echo "  - View full cache report: python -c 'from swebench_singularity import CacheManager; print(CacheManager().get_cache_report())'"
echo "  - Clean old images: python scripts/swebench_cache_manager.py cleanup --days 30"
echo "  - Remove specific image: python scripts/swebench_cache_manager.py remove <instance_id>"
echo "  - See IMAGES_EXPLAINED.md for more details"
