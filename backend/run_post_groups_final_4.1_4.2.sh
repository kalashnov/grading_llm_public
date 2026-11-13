#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-python3}"
SUBMISSIONS_DIR="$SCRIPT_DIR/data/Final/submissions"

shopt -s nullglob

requests=(
  "$SUBMISSIONS_DIR"/VB_*_q3.3_*_requests.json
  "$SUBMISSIONS_DIR"/VC_*_q3.3_*_requests.json
  "$SUBMISSIONS_DIR"/VD_*_q3.3_*_requests.json
  "$SUBMISSIONS_DIR"/*_q4.1_*_requests.json
  "$SUBMISSIONS_DIR"/*_q4.2_*_requests.json
)

if [ "${#requests[@]}" -eq 0 ]; then
  echo "No target request files found in $SUBMISSIONS_DIR" >&2
  exit 1
fi

for file in "${requests[@]}"; do
  echo "Posting $(basename "$file")"
  "$PY" "$SCRIPT_DIR/post_grades.py" "$file"
  sleep 3
done
