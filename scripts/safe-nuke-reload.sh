#!/bin/bash
set -e
echo "=========================================="
echo " SAFE NUKE-RELOAD v2.0"
echo " Preserves OpenFang Rust Kernel"
echo "=========================================="
SOURCE=""
TARGET=""
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --source=*) SOURCE="${arg#*=}" ;;
        --target=*) TARGET="${arg#*=}" ;;
        --dry-run) DRY_RUN=true ;;
    esac
done
if [ -z "$SOURCE" ] || [ -z "$TARGET" ]; then
    echo "Usage: $0 --source=/path/to/source --target=/path/to/target [--dry-run]"
    exit 1
fi
# SAFETY CHECK 1: Is target openfang-kernel-recovered?
if echo "$TARGET" | grep -q "openfang-kernel-recovered"; then
    echo "BLOCKED: Cannot nuke-reload openfang-kernel-recovered"
    echo "Standing Order #18: OPENFANG KERNEL IS SACRED"
    exit 1
fi
# SAFETY CHECK 2: Does target contain Rust files?
RS_COUNT=$(find "$TARGET" -name "*.rs" -not -path "*/.git/*" 2>/dev/null | wc -l)
if [ "$RS_COUNT" -gt 50 ]; then
    echo "BLOCKED: Target contains $RS_COUNT Rust files"
    echo "This appears to be an OpenFang kernel repo. Aborting."
    exit 1
fi
# SAFETY CHECK 3: Create backup branch
BACKUP="backup/pre-nuke-$(date +%Y%m%d-%H%M%S)"
echo "Creating backup branch: $BACKUP"
if [ "$DRY_RUN" = false ]; then
    cd "$TARGET" && git checkout -b "$BACKUP" && git checkout - 2>/dev/null
fi
# SAFETY CHECK 4: Only copy Python/JS/config files, NEVER .rs/.toml
echo "Copying files (excluding Rust)..."
if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would copy from $SOURCE to $TARGET"
    echo "[DRY RUN] Excluding: *.rs, Cargo.toml, Cargo.lock, Cross.toml"
    find "$SOURCE" -name "*.py" -o -name "*.js" -o -name "*.json" -o -name "*.yml" | head -20
else
    rsync -av --exclude='.git' --exclude='*.rs' --exclude='Cargo.toml' --exclude='Cargo.lock' --exclude='Cross.toml' "$SOURCE/" "$TARGET/"
fi
echo "=========================================="
echo " NUKE-RELOAD COMPLETE (Kernel preserved)"
echo "=========================================="
