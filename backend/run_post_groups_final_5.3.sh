#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-python3}"
SUBMISSIONS_DIR="$SCRIPT_DIR/data/Final/submissions"

requests=(
  "$SUBMISSIONS_DIR/VA_1288622_q5.3_72301419_requests.json"
  "$SUBMISSIONS_DIR/VB_1288622_q5.3_72301496_requests.json"
  "$SUBMISSIONS_DIR/VC_1288622_q5.3_72301538_requests.json"
  "$SUBMISSIONS_DIR/VD_1288622_q5.3_72302264_requests.json"
)

for file in "${requests[@]}"; do
  if [ ! -f "$file" ]; then
    echo "Missing request file: $file" >&2
    exit 1
  fi
done

echo "Posting ${#requests[@]} Final q5.3 request files (updated 8-group spec)"

for file in "${requests[@]}"; do
  echo "Posting $(basename "$file")"
  "$PY" "$SCRIPT_DIR/post_grades.py" "$file"
  sleep 3
done
