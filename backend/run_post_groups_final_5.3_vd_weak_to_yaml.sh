#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-python3}"
REQUEST_FILE="$SCRIPT_DIR/data/Final/submissions/VD_1288622_q5.3_72302264_weak_to_yaml_requests.json"

if [ ! -f "$REQUEST_FILE" ]; then
  echo "Missing request file: $REQUEST_FILE" >&2
  exit 1
fi

echo "Posting VD q5.3 weak-to-full override back to current YAML classification"
"$PY" "$SCRIPT_DIR/post_grades.py" "$REQUEST_FILE"
