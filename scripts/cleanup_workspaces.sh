#!/bin/bash

# Cleanup script for .khive/workspaces
# Removes directories that only contain standard MCP config files

WORKSPACES="/Users/lion/khived/.khive/workspaces"
DRY_RUN=${1:-""}
REMOVED_COUNT=0
KEPT_COUNT=0

echo "🧹 Cleaning up workspace folders with only standard config files..."
echo "Workspace: $WORKSPACES"
echo ""

if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "🔍 DRY RUN MODE - No directories will be removed"
    echo ""
fi

# Find all directories in workspaces (depth 1 only)
for dir in "$WORKSPACES"/*; do
    if [[ -d "$dir" ]]; then
        dir_name=$(basename "$dir")

        # Check if directory contains any files other than standard MCP files
        has_custom_files=false

        # Find all files in the directory (recursively)
        while IFS= read -r file; do
            filename=$(basename "$file")
            # Check if file is NOT a standard MCP config file
            if [[ "$filename" != ".mcp.json" && \
                  "$filename" != "CLAUDE.md" && \
                  "$filename" != "settings.json" && \
                  "$filename" != ".DS_Store" ]]; then
                has_custom_files=true
                break
            fi
        done < <(find "$dir" -type f 2>/dev/null)

        if [[ "$has_custom_files" == true ]]; then
            echo "✅ KEEP: $dir_name (contains custom files)"
            ((KEPT_COUNT++))
        else
            if [[ "$DRY_RUN" == "--dry-run" ]]; then
                echo "❌ WOULD REMOVE: $dir_name (only standard MCP files)"
            else
                echo "❌ REMOVING: $dir_name (only standard MCP files)"
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
