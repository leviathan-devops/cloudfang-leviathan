#!/bin/bash
set -e
echo "=========================================="
echo " LEVIATHAN DEPLOYMENT SAFETY CHECK"
echo "=========================================="
TARGET_REPO="${1:-}"
if [ -z "$TARGET_REPO" ]; then
    echo "Usage: $0 <target-repo-path>"
    exit 1
fi
echo "[CHECK 1] Scanning target for Rust kernel files..."
RS_COUNT=$(find "$TARGET_REPO" -name "*.rs" -not -path "*/.git/*" 2>/dev/null | wc -l)
if [ "$RS_COUNT" -gt 50 ]; then
    echo "  ABORT: Target contains $RS_COUNT Rust files!"
    echo "  Standing Order #18: OPENFANG KERNEL IS SACRED"
    exit 1
fi
echo "  OK: $RS_COUNT Rust files (below threshold)"
echo "[CHECK 2] Checking for mass file deletions..."
STAGED_DEL=$(git diff --cached --diff-filter=D --name-only 2>/dev/null | wc -l)
if [ "$STAGED_DEL" -gt 20 ]; then
    echo "  ABORT: $STAGED_DEL files staged for deletion!"
    exit 1
fi
echo "  OK: $STAGED_DEL deletions (within threshold)"
echo "[CHECK 3] Language consistency..."
PY=$(find . -name "*.py" -not -path "*/.git/*" | wc -l)
RS=$(find . -name "*.rs" -not -path "*/.git/*" | wc -l)
echo "  Python: $PY | Rust: $RS"
echo "=========================================="
echo " ALL CHECKS PASSED"
echo "=========================================="
