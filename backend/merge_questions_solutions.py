#!/usr/bin/env python3
"""Merge transcribed question texts with their official solutions.

For every version file under questions/<exam>/<id>/questions_<id>_V*.txt, look
for the matching file under solutions/<exam>/<id>/solutions_<id>_V*.txt and
write a combined file to merged/<exam>/<id>/merged_<id>_V*.md. The merged file
is written in the exact block format the grading prompt expects, so it can be
dropped into the prompt as-is — no parsing needed.

After a successful merge the original question and solution files are deleted
(pass --keep to retain them); any directories left empty are pruned.

Usage:
    python merge_questions_solutions.py [--out merged] [--keep]

Lives in backend/; resolves the prompt-authoring skill directory relative to
the repo root, so it can be run from anywhere.
"""
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "prompt-authoring"


def prune_empty_dirs(root: Path) -> None:
    """Remove now-empty directories under root, deepest first."""

    for directory in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", default="merged", help="output folder name (default: merged)"
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the original question/solution files instead of deleting them",
    )
    args = parser.parse_args()

    questions_dir = SKILL_DIR / "questions"
    solutions_dir = SKILL_DIR / "solutions"
    out_dir = SKILL_DIR / args.out

    merged, removed, missing = 0, 0, []
    for q_file in sorted(questions_dir.rglob("questions_*.txt")):
        rel = q_file.relative_to(questions_dir)          # <exam>/<id>/questions_<id>_V*.txt
        exam, qid = rel.parts[0], rel.parts[1]
        # questions_<id>_V*.txt -> V*
        version = q_file.stem.removeprefix(f"questions_{qid}_")

        s_file = solutions_dir / exam / qid / f"solutions_{qid}_{version}.txt"
        out_file = out_dir / exam / qid / f"merged_{qid}_{version}.md"

        question = q_file.read_text(encoding="utf-8").strip()
        if s_file.exists():
            solution = s_file.read_text(encoding="utf-8").strip()
        else:
            solution = "_No official solution found._"
            missing.append(str(rel))

        # Written in the prompt's block format so generate_grading_prompt.py
        # can paste the file in verbatim.
        content = (
            "Here is the problem that was given to the student:\n"
            f"```text\n{question}\n```\n\n"
            "SOLUTION:\n"
            f"```text\n{solution}\n```\n"
        )
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        merged += 1

        # The merged file now holds everything; drop the originals.
        if not args.keep:
            q_file.unlink()
            removed += 1
            if s_file.exists():
                s_file.unlink()
                removed += 1

    if not args.keep:
        prune_empty_dirs(questions_dir)
        prune_empty_dirs(solutions_dir)

    print(f"Merged {merged} file(s) into {out_dir}")
    if not args.keep:
        print(f"Removed {removed} original question/solution file(s)")
    if missing:
        print(f"{len(missing)} question(s) had no matching solution:")
        for m in missing:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
