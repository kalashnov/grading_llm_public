#!/usr/bin/env bash
# Grade question 3.6 (all versions VA-VD) via grade_all.py.
set -u
cd "$(dirname "$0")"

export OPENAI_API_KEY="$(tr -d '[:space:]' < ../openai_key)"
PY=../.venv/bin/python

SUB="data/Midterm 2/submissions"
echo "=== grade 3.6 started $(date) ==="

for f in "$SUB"/*q3.6_*_ocr_cleaned.json; do
  echo
  echo ">>> $(date '+%H:%M:%S') grading $(basename "$f")"
  "$PY" grade_all.py "$f"
  rc=$?
  echo ">>> $(date '+%H:%M:%S') exit=$rc $(basename "$f")"
done

echo
echo "=== grade 3.6 finished $(date) ==="
