"""Render the criteria-generation prompts without calling Claude.

`generate_criteria.py` sends a system prompt and two sequential user prompts to
Claude. This helper writes those exact prompt bodies to markdown files so they
can be pasted into another model/session by hand.

Usage:
    python backend/export_criteria_prompts.py --exam final
    python backend/export_criteria_prompts.py --exam final 2.1 2.2
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXAM = "midterm-2"
DEFAULT_VARIANT = "VA"

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
SKILL_DIR = REPO_ROOT / "skills" / "prompt-authoring"
REFERENCE_DIR = SKILL_DIR / "reference"
CRITERIA_PROMPT = REPO_ROOT / "generation-prompts" / "criteria-prompt.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "generation-prompts" / "criteria-sessions"

CRITERIA_JSON_SHAPE = (
    '{"criteria": [{"id": "<short snake_case name a human grader instantly '
    'understands, e.g. rejects_null or correct_interval_midpoint — lowercase '
    'letters, digits and underscores only, unique within this question>", '
    '"question": "<the yes/no check the grader answers>", "accept": '
    '["<phrasing that gets credit>", ...], "reject": ["<phrasing/condition '
    'that does not get credit>", ...]}, ...]}'
)
FEWSHOT_JSON_SHAPE = (
    '{"examples": [{"label": "<short tag, e.g. full credit / no credit>", '
    '"answer": "<transcribed student answer text>", "grading": '
    '[{"criterion_id": "<the snake_case id of the criterion being graded>", '
    '"met": <true|false>}, ...]}, ...]}'
)

TURN2_PROMPT = (
    "Now produce 5 example student answers, each graded against the criteria "
    "you just wrote. The 5 examples must be DIVERSE and REPRESENTATIVE: "
    "together they should cover the most common mistakes students actually "
    "make on this question — judged from the real student answers above — "
    "alongside a fully correct answer. Span the range from a perfect answer "
    "through partial-credit / edge cases to clearly failing ones.\n\n"
    "Grade every example against every criterion, and use the exact "
    "snake_case `criterion_id` values from the criteria you just wrote.\n\n"
    "Respond with ONLY a JSON object of exactly this shape, and nothing else — "
    "no prose, no markdown fences:\n"
    f"{FEWSHOT_JSON_SHAPE}"
)

_QUESTION_BLOCK = re.compile(r"```text\n(.*?)\n```", re.S)


@dataclass
class ExamConfig:
    slug: str
    title: str
    variant: str
    merged_dir: Path
    submissions_dir: Path


def exam_display_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def make_config(slug: str, variant: str) -> ExamConfig:
    title = exam_display_name(slug)
    return ExamConfig(
        slug=slug,
        title=title,
        variant=variant,
        merged_dir=SKILL_DIR / "merged" / slug,
        submissions_dir=BACKEND_DIR / "data" / title / "submissions",
    )


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_system() -> str:
    rules = load_text(CRITERIA_PROMPT)
    philosophy = load_text(REFERENCE_DIR / "grading-philosophy-examples.md")
    return (
        f"{rules}\n\n"
        f"# Grading philosophy — examples from Midterm 1 (reference)\n\n{philosophy}"
    )


def load_question(cfg: ExamConfig, qid: str) -> str:
    path = cfg.merged_dir / qid / f"merged_{qid}_{cfg.variant}.md"
    if not path.exists():
        raise FileNotFoundError(f"missing merged file: {path}")
    match = _QUESTION_BLOCK.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"no ```text question block in {path}")
    return match.group(1).strip()


def load_student_answers(cfg: ExamConfig, qid: str) -> list[str]:
    cleaned = sorted(
        cfg.submissions_dir.glob(f"{cfg.variant}_*_q{qid}_*_ocr_cleaned.json")
    )
    gvision = sorted(
        cfg.submissions_dir.glob(f"{cfg.variant}_*_q{qid}_*_ocr_gvision.json")
    )
    answers: list[str] = []
    for path in cleaned or gvision:
        data = json.loads(path.read_text(encoding="utf-8"))
        for text in data.values():
            answers.append(text.strip() if text and text.strip() else "[blank answer]")
    return answers


def build_turn1(cfg: ExamConfig, question: str, answers: list[str]) -> str:
    numbered = "\n\n".join(f"{i}. {answer}" for i, answer in enumerate(answers, 1))
    return (
        f"Here is one exam question (variant {cfg.variant}) and every real student "
        f"answer to it.\n\n"
        f"QUESTION:\n```\n{question}\n```\n\n"
        f"STUDENT ANSWERS ({len(answers)} answers, one per student):\n"
        f"{numbered}\n\n"
        "Write the criteria for this question. Use the real "
        "answers above to design criteria with good coverage of the mistakes "
        "students actually make.\n\n"
        "Respond with ONLY a JSON object of exactly this shape, and nothing "
        "else — no prose, no markdown fences:\n"
        f"{CRITERIA_JSON_SHAPE}"
    )


def write_question_prompts(
    cfg: ExamConfig,
    qid: str,
    output_root: Path,
    system_prompt: str,
) -> tuple[Path, int]:
    question = load_question(cfg, qid)
    answers = load_student_answers(cfg, qid)
    if not answers:
        raise ValueError(f"no student answers found in {cfg.submissions_dir}")

    qdir = output_root / cfg.slug / qid
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / "00_system.md").write_text(system_prompt, encoding="utf-8")
    (qdir / "01_turn1_criteria.md").write_text(
        build_turn1(cfg, question, answers),
        encoding="utf-8",
    )
    (qdir / "02_turn2_few_shot.md").write_text(TURN2_PROMPT, encoding="utf-8")
    return qdir, len(answers)


def write_readme(output_root: Path, cfg: ExamConfig, qids: list[str]) -> None:
    readme = output_root / cfg.slug / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n".join(f"- `{qid}/`" for qid in qids)
    readme.write_text(
        "\n".join(
            [
                f"# Criteria Prompt Sessions: {cfg.title}",
                "",
                "Each question directory contains the prompt bodies used by",
                "`backend/generate_criteria.py`, rendered without calling Claude.",
                "",
                "Feed them in this order:",
                "",
                "1. Use `00_system.md` as the system/developer instruction if your",
                "   chat surface supports that. Otherwise paste it before Turn 1.",
                "2. Send `01_turn1_criteria.md` and save the returned JSON criteria.",
                "3. In the same conversation, send `02_turn2_few_shot.md` and save",
                "   the returned JSON few-shot examples.",
                "",
                "Rendered question directories:",
                rendered,
                "",
            ]
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the sequential criteria-generation prompts to files."
    )
    parser.add_argument(
        "--exam",
        default=DEFAULT_EXAM,
        help=f"exam slug, e.g. midterm-2 or final (default: {DEFAULT_EXAM})",
    )
    parser.add_argument(
        "--variant",
        default=DEFAULT_VARIANT,
        help=f"which variant's question + answers to render (default: {DEFAULT_VARIANT})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"output root (default: {DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "ids",
        nargs="*",
        help="question ids to render (default: every id under the exam merged dir)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = make_config(args.exam, args.variant)
    if not cfg.merged_dir.is_dir():
        sys.exit(f"merged directory not found: {cfg.merged_dir}")

    qids = args.ids or sorted(d.name for d in cfg.merged_dir.iterdir() if d.is_dir())
    system_prompt = build_system()

    rendered: list[str] = []
    for qid in qids:
        try:
            qdir, answer_count = write_question_prompts(
                cfg,
                qid,
                args.out_dir,
                system_prompt,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"[skip] {qid} ({exc})")
            continue
        rendered.append(qid)
        print(
            f"[write] {qid}: {answer_count} answers -> "
            f"{qdir.relative_to(REPO_ROOT)}"
        )

    if rendered:
        write_readme(args.out_dir, cfg, rendered)
        print(f"\nRendered {len(rendered)} prompt session(s).")
    else:
        print("\nNo prompt sessions rendered.")


if __name__ == "__main__":
    main()
