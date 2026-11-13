#!/usr/bin/env bash
# Grade the remaining ungraded questions (all with prompts except 4.2):
# 2.2, 3.1, 3.2, 3.3, 3.4, 3.5 — all versions VA-VD — via grade_all.py.
set -u
cd "$(dirname "$0")"

export OPENAI_API_KEY="$(tr -d '[:space:]' < ../openai_key)"
PY=../.venv/bin/python

SUB="data/Midterm 2/submissions"
QUESTIONS="2.2 3.1 3.2 3.3 3.4 3.5"
echo "=== grade rest started $(date) ==="

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
echo "=== grade rest finished $(date) ==="
