#!/usr/bin/env bash
# Post only Final questions 3.2, 4.5, and 5.2 across VA-VD.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMISSIONS_DIR="$SCRIPT_DIR/data/Final/submissions"
LOG="$SCRIPT_DIR/post_grades_final_remaining.log"

if [ -x "$SCRIPT_DIR/../.venv/bin/python" ]; then
  PY="$SCRIPT_DIR/../.venv/bin/python"
else
  PY="python3"
fi

REQUEST_FILES=(
  "$SUBMISSIONS_DIR/VA_1288622_q3.2_72301404_requests.json"
  "$SUBMISSIONS_DIR/VB_1288622_q3.2_72301481_requests.json"
  "$SUBMISSIONS_DIR/VC_1288622_q3.2_72301523_requests.json"
  "$SUBMISSIONS_DIR/VD_1288622_q3.2_72302249_requests.json"
  "$SUBMISSIONS_DIR/VA_1288622_q4.5_72301414_requests.json"
  "$SUBMISSIONS_DIR/VB_1288622_q4.5_72301491_requests.json"
  "$SUBMISSIONS_DIR/VC_1288622_q4.5_72301533_requests.json"
  "$SUBMISSIONS_DIR/VD_1288622_q4.5_72302259_requests.json"
  "$SUBMISSIONS_DIR/VA_1288622_q5.2_72301418_requests.json"
  "$SUBMISSIONS_DIR/VB_1288622_q5.2_72301495_requests.json"
  "$SUBMISSIONS_DIR/VC_1288622_q5.2_72301537_requests.json"
  "$SUBMISSIONS_DIR/VD_1288622_q5.2_72302263_requests.json"
)

echo "=== post Final remaining started $(date) ===" | tee "$LOG"
echo "Files: ${#REQUEST_FILES[@]}" | tee -a "$LOG"

for f in "${REQUEST_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "Missing request file: $f" | tee -a "$LOG"
    exit 1
  fi
done

for f in "${REQUEST_FILES[@]}"; do
  echo | tee -a "$LOG"
  echo ">>> $(date '+%H:%M:%S') posting $(basename "$f")" | tee -a "$LOG"
  "$PY" "$SCRIPT_DIR/post_grades.py" "$f" 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  echo ">>> $(date '+%H:%M:%S') exit=$rc $(basename "$f")" | tee -a "$LOG"
  if [ "$rc" -ne 0 ]; then
    exit "$rc"
  fi
  sleep 3
done

echo | tee -a "$LOG"
echo "=== post Final remaining finished $(date) ===" | tee -a "$LOG"
