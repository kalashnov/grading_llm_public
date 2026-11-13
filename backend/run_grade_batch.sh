#!/usr/bin/env bash
# Grade questions 2.1, 3.7, 4.1, 4.3 (all versions VA-VD) via grade_all.py.
set -u
cd "$(dirname "$0")"

export OPENAI_API_KEY="$(tr -d '[:space:]' < ../openai_key)"
PY=../.venv/bin/python

SUB="data/Midterm 2/submissions"
QUESTIONS="2.1 3.7 4.1 4.3"
echo "=== grade batch started $(date) ==="

for q in $QUESTIONS; do
  echo
  echo "########## question $q ##########"
  for f in "$SUB"/*q${q}_*_ocr_cleaned.json; do
    echo
    echo ">>> $(date '+%H:%M:%S') grading $(basename "$f")"
    "$PY" grade_all.py "$f"
    rc=$?
    echo ">>> $(date '+%H:%M:%S') exit=$rc $(basename "$f")"
  done
done

echo
echo "=== grade batch finished $(date) ==="
