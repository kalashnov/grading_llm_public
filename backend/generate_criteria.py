"""Generate criteria and few-shot examples for each exam question.

For each question (skipping ones that already have a criteria file), this opens
a multi-turn Claude session and sends two messages:

  turn 1 -> draft the criteria, given the question text of one
            variant and EVERY real student answer to that variant;
  turn 2 -> produce 5 diverse worked examples graded against those criteria.

It uses the Claude Agent SDK (`claude-agent-sdk`), which runs through Claude
Code and therefore authenticates with your Claude Code subscription — no metered
`ANTHROPIC_API_KEY` is needed. A multi-turn "session" is one `ClaudeSDKClient`.

The Agent SDK has no native structured-output / JSON-schema enforcement, so the
schema of each output is enforced SCRIPT-SIDE: the prompt specifies the exact
JSON shape, the script parses + validates the response, and retries once on a
malformed reply. The validated criteria become a grading spec written as YAML
(reference/spec-template.yaml shape) to `criteria/<exam>/criteria_<id>.yaml`; the
examples are saved to `few-shot/<exam>/few-shot_<id>.yaml`. Per-question
token/cost figures go to `costs/<exam>/<id>.json`.

The exam is chosen with `--exam` (a slug like `midterm-2` or `final`); its
display name (`Midterm 2`, `Final`) and `data/<name>/submissions` directory are
derived from it. `--variant` picks which variant's question + answers to feed
(default VA — one variant's file already aggregates the whole class).

Prerequisites:
    pip install claude-agent-sdk          # the SDK
    Claude Code installed and logged in   # provides the subscription auth

Usage:
    python generate_criteria.py --exam final            # every Final question missing criteria
    python generate_criteria.py --exam final 2.1 3.4    # only these ids
    python generate_criteria.py                          # defaults to --exam midterm-2 (VA)
"""
import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

# --- configuration ---------------------------------------------------------

MODEL = "claude-sonnet-4-6"
DEFAULT_EXAM = "midterm-2"   # overridable with --exam
DEFAULT_VARIANT = "VA"       # overridable with --variant

# --- paths (exam-independent) ----------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent           # grading_llm/backend
REPO_ROOT = BACKEND_DIR.parent                          # grading_llm
SKILL_DIR = REPO_ROOT / "skills" / "prompt-authoring"
REFERENCE_DIR = SKILL_DIR / "reference"
CRITERIA_PROMPT = REPO_ROOT / "generation-prompts" / "criteria-prompt.md"


# --- per-exam configuration ------------------------------------------------

@dataclass
class ExamConfig:
    """Everything that varies by exam (and chosen variant). Built once from
    --exam / --variant so the same engine serves any exam."""

    slug: str          # e.g. "midterm-2", "final"
    title: str         # display name, e.g. "Midterm 2", "Final"
    variant: str       # which variant's question + answers to feed
    merged_dir: Path
    submissions_dir: Path
    criteria_dir: Path
    fewshot_dir: Path
    costs_dir: Path


def exam_display_name(slug: str) -> str:
    """'midterm-2' -> 'Midterm 2', 'final' -> 'Final' (matches the data/ dirs)."""
    return slug.replace("-", " ").title()


def make_config(slug: str, variant: str) -> ExamConfig:
    title = exam_display_name(slug)
    return ExamConfig(
        slug=slug,
        title=title,
        variant=variant,
        merged_dir=SKILL_DIR / "merged" / slug,
        submissions_dir=BACKEND_DIR / "data" / title / "submissions",
        criteria_dir=SKILL_DIR / "criteria" / slug,
        fewshot_dir=SKILL_DIR / "few-shot" / slug,
        costs_dir=SKILL_DIR / "costs" / slug,
    )


# --- required JSON shapes (enforced script-side: prompt + parse + validate) -

# Criterion ids are short snake_case names — a human grader must understand the
# check from the id alone (e.g. `rejects_null`, `correct_interval_midpoint`).
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

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

SPEC_HEADER = (
    "# Grading spec — see reference/spec-template.yaml.\n"
    "# `criteria` is generated by the script.\n"
)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_system() -> str:
    """The system prompt: authoring rules + grading-philosophy examples.
    Identical for every question. (The rendered-prompt house format is the
    renderer's concern, not the criteria author's, so it is not included.)"""
    rules = load_text(CRITERIA_PROMPT)
    philosophy = load_text(REFERENCE_DIR / "grading-philosophy-examples.md")
    return (
        f"{rules}\n\n"
        f"# Grading philosophy — examples from Midterm 1 (reference)\n\n{philosophy}"
    )


# The question is the FIRST ```text block of a merged file; the SOLUTION block
# (a later ```text block) is intentionally left out of the criteria prompt.
_QUESTION_BLOCK = re.compile(r"```text\n(.*?)\n```", re.S)


def load_question(cfg: ExamConfig, qid: str) -> str:
    path = cfg.merged_dir / qid / f"merged_{qid}_{cfg.variant}.md"
    if not path.exists():
        raise FileNotFoundError(f"missing merged file: {path}")
    m = _QUESTION_BLOCK.search(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"no ```text question block in {path}")
    return m.group(1).strip()


def load_student_answers(cfg: ExamConfig, qid: str) -> list:
    """Every real student answer for this question + variant. The OCR pipeline
    stores them as one {image_name: text} JSON per question+variant."""
    cleaned = sorted(cfg.submissions_dir.glob(f"{cfg.variant}_*_q{qid}_*_ocr_cleaned.json"))
    gvision = sorted(cfg.submissions_dir.glob(f"{cfg.variant}_*_q{qid}_*_ocr_gvision.json"))
    answers = []
    for path in (cleaned or gvision):
        data = json.loads(path.read_text(encoding="utf-8"))
        for text in data.values():
            answers.append(text.strip() if text and text.strip() else "[blank answer]")
    return answers


def build_turn1(cfg: ExamConfig, question: str, answers: list) -> str:
    numbered = "\n\n".join(f"{i}. {a}" for i, a in enumerate(answers, 1))
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


def extract_json(text: str) -> dict:
    """Pull the JSON object out of a model response (tolerates stray prose or
    markdown fences by taking the first '{' to the last '}')."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in response")
    return json.loads(text[start:end + 1])


def validate_criteria(data: dict) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("criteria"), list) \
            or not data["criteria"]:
        raise ValueError("expected a non-empty 'criteria' list")
    seen = set()
    for c in data["criteria"]:
        cid = c.get("id")
        if not isinstance(cid, str) or not SNAKE_CASE.match(cid):
            raise ValueError(
                f"each criterion needs a snake_case string 'id' (lowercase "
                f"letters, digits and underscores); got {cid!r}")
        if cid in seen:
            raise ValueError(f"duplicate criterion id: {cid!r}")
        seen.add(cid)
        if not isinstance(c.get("question"), str) or not c["question"].strip():
            raise ValueError("each criterion needs a non-empty 'question' string")
        for key in ("accept", "reject"):
            if not isinstance(c.get(key), list) \
                    or not all(isinstance(x, str) for x in c[key]):
                raise ValueError(f"criterion '{key}' must be a list of strings")


def make_fewshot_validator(criteria_ids):
    """Build a few-shot validator bound to this question's criterion ids, so a
    grading entry that names an unknown criterion is rejected."""
    valid = set(criteria_ids)

    def validate_fewshot(data: dict) -> None:
        if not isinstance(data, dict) \
                or not isinstance(data.get("examples"), list) \
                or not data["examples"]:
            raise ValueError("expected a non-empty 'examples' list")
        for e in data["examples"]:
            if not isinstance(e.get("label"), str):
                raise ValueError("each example needs a 'label' string")
            if not isinstance(e.get("answer"), str):
                raise ValueError("each example needs an 'answer' string")
            if not isinstance(e.get("grading"), list) or not e["grading"]:
                raise ValueError("each example needs a non-empty 'grading' list")
            for g in e["grading"]:
                cid = g.get("criterion_id")
                if not isinstance(cid, str):
                    raise ValueError(
                        "each grading entry needs a string 'criterion_id'")
                if cid not in valid:
                    raise ValueError(
                        f"grading entry references unknown criterion id {cid!r}")
                if not isinstance(g.get("met"), bool):
                    raise ValueError("each grading entry needs a boolean 'met'")

    return validate_fewshot


def build_spec(cfg: ExamConfig, qid: str, criteria_data: dict) -> str:
    """Assemble the grading spec (reference/spec-template.yaml shape) and
    serialise it to YAML: exam/id from the config and criteria from the model."""
    spec = {
        "exam": cfg.title,
        "id": qid,
        "criteria": criteria_data["criteria"],
    }
    return SPEC_HEADER + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)


def usage_record(usage: dict, cost: float) -> dict:
    usage = usage or {}
    return {
        "input_tokens": usage.get("input_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": round(cost or 0.0, 6),
    }


async def ask_json(client, prompt: str, validate, label: str, attempts: int = 2):
    """Send `prompt`, collect the reply, parse + validate it as JSON. On a
    malformed reply, retry in the same session. Returns (data, usage)."""
    totals = {"input_tokens": 0, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    last_err = None
    for attempt in range(1, attempts + 1):
        message = prompt if attempt == 1 else (
            f"That response was not valid JSON of the required shape ({last_err}). "
            "Reply again with ONLY the JSON object — no prose, no markdown fences."
        )
        await client.query(message)

        parts, usage, cost = [], {}, 0.0
        async for m in client.receive_response():
            if isinstance(m, AssistantMessage):
                parts += [b.text for b in m.content if isinstance(b, TextBlock)]
            elif isinstance(m, ResultMessage):
                usage, cost = m.usage or {}, m.total_cost_usd or 0.0

        rec = usage_record(usage, cost)
        for k in totals:
            totals[k] += rec[k]

        try:
            data = extract_json("".join(parts))
            validate(data)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = str(e)
            print(f"    [{label}] attempt {attempt}: invalid response ({e})")
            continue

        totals["cost_usd"] = round(totals["cost_usd"], 6)
        print(f"    [{label}] input={totals['input_tokens']} "
              f"cache_read={totals['cache_read_input_tokens']} "
              f"cache_write={totals['cache_creation_input_tokens']} "
              f"output={totals['output_tokens']} (${totals['cost_usd']:.4f})")
        return data, totals

    raise RuntimeError(f"{label}: no valid JSON after {attempts} attempts ({last_err})")


def write_costs(cfg: ExamConfig, qid: str, turns: dict) -> None:
    keys = ["input_tokens", "cache_read_input_tokens",
            "cache_creation_input_tokens", "output_tokens", "cost_usd"]
    total = {k: sum(t[k] for t in turns.values()) for k in keys}
    total["cost_usd"] = round(total["cost_usd"], 6)
    record = {
        "question": qid,
        "model": MODEL,
        "turns": turns,
        "total": total,
        "note": "token counts and cost_usd as reported by the Claude Agent SDK.",
    }
    cfg.costs_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.costs_dir / f"{qid}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"    -> {path.relative_to(REPO_ROOT)}  (total ${total['cost_usd']:.4f})")


async def process_question(cfg: ExamConfig, options: ClaudeAgentOptions, qid: str) -> None:
    spec_path = cfg.criteria_dir / f"criteria_{qid}.yaml"
    if spec_path.exists():
        print(f"[skip] {qid} (spec already present)")
        return

    question = load_question(cfg, qid)
    answers = load_student_answers(cfg, qid)
    if not answers:
        print(f"[skip] {qid} (no student answers found in submissions)")
        return

    print(f"[run]  {qid} ({len(answers)} student answers)")

    # one multi-turn session per question
    async with ClaudeSDKClient(options=options) as client:
        crit_data, crit_usage = await ask_json(
            client, build_turn1(cfg, question, answers), validate_criteria, "criteria")
        validate_fewshot = make_fewshot_validator(
            c["id"] for c in crit_data["criteria"])
        fs_data, fs_usage = await ask_json(
            client, TURN2_PROMPT, validate_fewshot, "few-shot")

    cfg.criteria_dir.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(build_spec(cfg, qid, crit_data), encoding="utf-8")
    print(f"    -> {spec_path.relative_to(REPO_ROOT)}")

    cfg.fewshot_dir.mkdir(parents=True, exist_ok=True)
    fewshot_path = cfg.fewshot_dir / f"few-shot_{qid}.yaml"
    fewshot_path.write_text(
        yaml.safe_dump(fs_data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"    -> {fewshot_path.relative_to(REPO_ROOT)}")

    write_costs(cfg, qid, {"criteria": crit_usage, "few_shot": fs_usage})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate criteria + few-shot examples for an exam's questions.")
    parser.add_argument(
        "--exam", default=DEFAULT_EXAM,
        help=f"exam slug, e.g. midterm-2 or final (default: {DEFAULT_EXAM}). "
             "Display name and data/<name>/submissions dir are derived from it.")
    parser.add_argument(
        "--variant", default=DEFAULT_VARIANT,
        help=f"which variant's question + answers to feed (default: {DEFAULT_VARIANT})")
    parser.add_argument(
        "ids", nargs="*",
        help="question ids to process (default: every id under the exam's questions dir)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    cfg = make_config(args.exam, args.variant)

    if not cfg.merged_dir.is_dir():
        sys.exit(f"merged directory not found: {cfg.merged_dir}")

    qids = args.ids or sorted(d.name for d in cfg.merged_dir.iterdir() if d.is_dir())

    options = ClaudeAgentOptions(
        system_prompt=build_system(),
        model=MODEL,
        allowed_tools=[],                      # pure text generation, no tools
        permission_mode="bypassPermissions",   # nothing to permit anyway
    )

    print(f"Processing {len(qids)} question(s) for {cfg.slug}, "
          f"variant {cfg.variant}, model {MODEL}\n")
    for qid in qids:
        try:
            await process_question(cfg, options, qid)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"[skip] {qid} ({e})")


if __name__ == "__main__":
    asyncio.run(main())
