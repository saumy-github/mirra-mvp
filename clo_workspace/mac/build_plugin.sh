#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$WORKSPACE_DIR/build_plugin.py" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$WORKSPACE_DIR/build_plugin.py" "$@"
fi

echo "ERROR: Python was not found in PATH." >&2
echo "Run the shared build entry point manually once Python is available:" >&2
echo "  python3 \"$WORKSPACE_DIR/build_plugin.py\"" >&2
exit 1
