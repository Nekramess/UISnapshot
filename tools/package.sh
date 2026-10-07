#!/usr/bin/env bash
# Builds UISnapshot-v<Version>-forever.zip from the version in the .toc.
# Usage: tools/package.sh [output-dir]   (default: the repo root). Prints the path of the zip.
# tools/release.sh calls this and keeps the result in releases/.
set -euo pipefail
cd "$(dirname "$0")/.."
ver=$(grep -m1 '^## Version:' UISnapshot/UISnapshot.toc | sed 's/^## Version:[[:space:]]*//' | tr -d '\r')
[ -n "$ver" ] || { echo "no ## Version in .toc" >&2; exit 1; }
out_dir="${1:-.}"
mkdir -p "$out_dir"
out_dir=$(cd "$out_dir" && pwd)
out="$out_dir/UISnapshot-v${ver}-forever.zip"
rm -f "$out"
zip -r "$out" UISnapshot -x '*.DS_Store' >/dev/null
echo "$out"
