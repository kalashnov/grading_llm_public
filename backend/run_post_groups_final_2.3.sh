#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-python3}"
SUBMISSIONS_DIR="$SCRIPT_DIR/data/Final/submissions"

requests=(
  "$SUBMISSIONS_DIR/VA_1288622_q2.3_72301399_requests.json"
  "$SUBMISSIONS_DIR/VB_1288622_q2.3_72301476_requests.json"
  "$SUBMISSIONS_DIR/VC_1288622_q2.3_72301518_requests.json"
  "$SUBMISSIONS_DIR/VD_1288622_q2.3_72302244_requests.json"
)

for file in "${requests[@]}"; do
  if [ ! -f "$file" ]; then
    echo "Missing request file: $file" >&2
    exit 1
  fi
done

for file in "${requests[@]}"; do
  echo "Posting $(basename "$file")"
  "$PY" "$SCRIPT_DIR/post_grades.py" "$file"
  sleep 3
done
