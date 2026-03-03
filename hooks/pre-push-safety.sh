#!/bin/bash
remote="$1"
url="$2"
echo "[PRE-PUSH] Checking push to: $url"
if echo "$url" | grep -q "openfang-kernel-recovered"; then
    echo "BLOCKED: Cannot push to openfang-kernel-recovered"
    echo "Standing Order #18: OPENFANG KERNEL IS SACRED"
    exit 1
fi
echo "[PRE-PUSH] Push approved"
