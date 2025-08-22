#!/bin/bash

# Cleanup script for .khive/workspace
# Removes directories that don't contain .md files

WORKSPACE="/Users/lion/khived/.khive/workspace"
DRY_RUN=${1:-""}
REMOVED_COUNT=0
KEPT_COUNT=0

echo "🧹 Cleaning up workspace directories without .md files..."
echo "Workspace: $WORKSPACE"
echo ""

if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "🔍 DRY RUN MODE - No directories will be removed"
    echo ""
fi

# Find all directories in workspace (depth 1 only)
for dir in "$WORKSPACE"/*; do
    if [[ -d "$dir" ]]; then
        dir_name=$(basename "$dir")

        # Check if directory contains any .md files
        if find "$dir" -name "*.md" -type f | grep -q .; then
            echo "✅ KEEP: $dir_name (contains .md files)"
            ((KEPT_COUNT++))
        else
            if [[ "$DRY_RUN" == "--dry-run" ]]; then
                echo "❌ WOULD REMOVE: $dir_name (no .md files)"
            else
                echo "❌ REMOVING: $dir_name (no .md files)"
                rm -rf "$dir"
            fi
            ((REMOVED_COUNT++))
        fi
    fi
done

echo ""
echo "📊 Summary:"
echo "  Directories kept: $KEPT_COUNT"
if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "  Directories to remove: $REMOVED_COUNT"
    echo ""
    echo "Run without --dry-run to actually remove directories:"
    echo "  bash $0"
else
    echo "  Directories removed: $REMOVED_COUNT"
fi
