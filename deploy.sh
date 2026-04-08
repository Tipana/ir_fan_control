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
  --exclude=".git" \
  --exclude=".vscode" \
  --exclude="__pycache__" \
  "$SOURCE_DIR" "$TARGET_DIR"

echo "Deploy complete."
echo "Next: restart Home Assistant to load changes."
