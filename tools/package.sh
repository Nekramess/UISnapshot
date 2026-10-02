#!/usr/bin/env bash
# Builds UISnapshot-v<Version>-forever.zip from the version in the .toc.
set -euo pipefail
cd "$(dirname "$0")/.."
ver=$(grep -m1 '^## Version:' UISnapshot/UISnapshot.toc | sed 's/^## Version:[[:space:]]*//' | tr -d '\r')
[ -n "$ver" ] || { echo "no ## Version in .toc" >&2; exit 1; }
out="UISnapshot-v${ver}-forever.zip"
rm -f "$out"
zip -r "$out" UISnapshot -x '*.DS_Store' >/dev/null
echo "$out"
