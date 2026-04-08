#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$SCRIPT_DIR/custom_components/ir_fan_control"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Target not found: $TARGET_DIR"
  exit 1
fi

echo "Running syntax check..."
python3 - "$TARGET_DIR" <<'PY'
import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
errors = 0

for path in sorted(root.rglob("*.py")):
    if "__pycache__" in path.parts:
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        print(f"Syntax error in {path}:{exc.lineno}:{exc.offset} {exc.msg}")
        errors += 1

if errors:
    raise SystemExit(1)

print("Syntax check passed.")
PY

if command -v ruff >/dev/null 2>&1; then
  echo "Running ruff..."
  ruff check "$TARGET_DIR"
  ruff format --check "$TARGET_DIR"
else
  echo "ruff not installed; skipped style lint."
  echo "Install with: pipx install ruff  (or: pip3 install ruff)"
fi

echo "Lint complete."
