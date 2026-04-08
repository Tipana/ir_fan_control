#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/custom_components/ir_fan_control/"
TARGET_DIR="/Volumes/config/custom_components/ir_fan_control/"

if [[ ! -d "/Volumes/config/custom_components" ]]; then
  echo "HA share not mounted at /Volumes/config."
  echo "Mount the share, then run: ./deploy.sh"
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source not found: $SOURCE_DIR"
  exit 1
fi

mkdir -p "$TARGET_DIR"

rsync -a --delete \
  --inplace \
  --exclude=".git" \
  --exclude=".vscode" \
  --exclude="DO_NOT_EDIT_HERE.txt" \
  --exclude="__pycache__" \
  "$SOURCE_DIR" "$TARGET_DIR"

# Keep the warning file in the live runtime folder only.
cat > "$TARGET_DIR/DO_NOT_EDIT_HERE.txt" <<'EOF'
DO NOT EDIT THIS LIVE FOLDER DIRECTLY.

Edit in source repo:
/config/ha_vibecode_git/custom_components/ir_fan_control

Then deploy:
/config/ha_vibecode_git/deploy.sh
EOF

echo "Deploy complete."
echo "Next: restart Home Assistant to load changes."
