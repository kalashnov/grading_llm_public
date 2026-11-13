#!/usr/bin/env python3
"""Render grading prompts/schemas, zip the deliverables, stage the PR files.

This is the tool Claude runs at the "assemble the prompt" step of the
grading-prompt-authoring skill. It takes the (TA-edited) merged question +
solution, grading criteria, few-shot examples and groups, and:

1. Renders the final per-version grading prompt(s) and the JSON schema.
2. Bundles every deliverable into a zip in the skill-source layout, for
   the TA to download as a complete record.
3. Stages the prompts + schema in the `backend/data` pipeline layout, so
   the skill can open a pull request adding them to the grading repo.

Inputs default to the stub files shipped with the skill, so the script
runs out-of-the-box for any shipped question:

    python3 generate_grading_prompt.py midterm-2 2.1 --stdout

During a skill run the TA edits the criteria / few-shot / merged
question+solution / groups in artifacts. To render *those* edits, write the
edited content to files first and point the matching flag at them:

    python3 generate_grading_prompt.py midterm-2 2.1 \\
        --criteria  ./work/criteria.yaml \\
        --few-shot  ./work/few-shot.yaml \\
        --groups    ./work/groups.yaml \\
        --merged-dir ./work/merged \\
        --out ./output

Any flag left out falls back to the shipped stub for that input, so you
only need to override what the TA actually changed. `groups` has no
shipped stub — pass `--groups` to include it in the deliverables zip.

Outputs under --out (default ./output):

  <exam>_<id>_deliverables.zip   skill-source layout, every deliverable:
      merged/<exam>/<id>/merged_<id>_V*.md
      criteria/<exam>/criteria_<id>.yaml
      few-shot/<exam>/few-shot_<id>.yaml
      groups/<exam>/groups_<id>.yaml
      schemas/<exam>/schema_<id>.json
      prompts/<exam>/<id>/prompt_<id>_V*.txt

  backend/data/<Exam Name>/prompts/prompt_<id>_<ver>.txt
  backend/data/<Exam Name>/schemas/schema_<id>.json
      pipeline layout — repo-relative paths to commit in the PR.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any
from textwrap import indent

import yaml


# Resolve the skill directory from this file's location so the script works
# no matter where the skill is unpacked (repo checkout, uploaded skill, etc.).
SKILL_DIR = Path(__file__).resolve().parent


def load_text(path: Path) -> str:
    """Read a UTF-8 text file and strip trailing whitespace."""

    return path.read_text(encoding="utf-8").strip()


def load_yaml(path: Path) -> Any:
    """Read a YAML file."""

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def exam_display_name(exam_slug: str) -> str:
    """Convert an exam slug like 'midterm-1' into 'Midterm 1'."""

    return exam_slug.replace("-", " ").title()


def find_versioned_files(directory: Path, pattern: str = "*_V*.txt") -> dict[str, Path]:
    """Map each version id (VA, VB, …) to its prefixed file.

    Files are named like `merged_2.1_VA.md`; the version is the last
    underscore-separated token of the stem.
    """

    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no versioned files matching {pattern} in {directory}")
    return {path.stem.rsplit("_", 1)[-1]: path for path in files}


def render_code_block(text: str, language: str = "text") -> str:
    """Wrap text in a fenced code block."""

    return f"```{language}\n{text}\n```"


def render_criteria(criteria: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Render numbered rubric criteria and return their ids in order."""

    blocks: list[str] = []
    criterion_ids: list[str] = []
    for index, criterion in enumerate(criteria, start=1):
        criterion_id = criterion["id"]
        criterion_ids.append(criterion_id)
        question = criterion["question"].strip()
        blocks.append(f"  {index}. [{criterion_id}] {question}")
        for accept in criterion.get("accept", []):
            blocks.append(f"     - ACCEPT: {accept}")
        for reject in criterion.get("reject", []):
            blocks.append(f"     - REJECT: {reject}")
        blocks.append("")
    return "\n".join(blocks).rstrip(), criterion_ids


def render_few_shot_example(example: dict[str, Any], criterion_ids: list[str]) -> str:
    """Render one few-shot example using the final output schema shape."""

    grading_lookup = {entry["criterion_id"]: entry["met"] for entry in example["grading"]}
    missing = [criterion_id for criterion_id in criterion_ids if criterion_id not in grading_lookup]
    extra = [criterion_id for criterion_id in grading_lookup if criterion_id not in criterion_ids]
    if missing or extra:
        raise ValueError(
            f"few-shot example {example.get('label')!r} does not match the criteria ids; "
            f"missing={missing}, extra={extra}"
        )

    grading_object: dict[str, Any] = {
        "comment": (
            f"{example['label'].strip()[0].upper()}{example['label'].strip()[1:].rstrip('.')}."
        ),
        "uncertain": False,
        "comment_uncertainty": "",
        "criteria": {criterion_id: bool(grading_lookup[criterion_id]) for criterion_id in criterion_ids},
    }

    rendered_grading = json.dumps(grading_object, indent=2, ensure_ascii=False)
    return (
        f"- label: {example['label']}\n"
        f"  answer:\n{indent(render_code_block(example['answer'], language='text'), '    ')}\n"
        f"  grading:\n{indent(render_code_block(rendered_grading, language='json'), '    ')}"
    )


def render_schema(criterion_ids: list[str]) -> dict[str, Any]:
    """Build the JSON schema expected by the grading pipeline."""

    properties: dict[str, Any] = {
        "comment": {"type": "string"},
        "uncertain": {"type": "boolean"},
        "comment_uncertainty": {"type": "string"},
        "criteria": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    }
    required = ["comment", "uncertain", "comment_uncertainty", "criteria"]
    for criterion_id in criterion_ids:
        properties["criteria"]["properties"][criterion_id] = {"type": "boolean"}
        properties["criteria"]["required"].append(criterion_id)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_prompt(
    merged_text: str,
    philosophy_text: str,
    criteria_text: str,
    few_shot_examples: list[str],
) -> str:
    """Assemble the final grading prompt.

    `merged_text` is the merged question+solution file, already written in the
    prompt's block format (see backend/merge_questions_solutions.py), so it is
    pasted in verbatim. The JSON output shape is conveyed by the few-shot
    examples and the closing instruction — the schema itself is a separate
    pipeline deliverable and is not embedded in the prompt.
    """

    sections = [
        merged_text.strip(),
        "",
        philosophy_text.strip(),
        "",
        "I want you to grade the answer of the student you just transcribed according to the following criteria:",
        criteria_text,
        "",
        "FEW-SHOT EXAMPLES:",
        *few_shot_examples,
        "",
        "Return only a valid JSON object in exactly the format shown in the few-shot examples above. Put all rubric booleans under the top-level 'criteria' object, include the top-level 'uncertain' boolean for the whole grading decision, and do not include markdown fences or extra keys.",
    ]
    return "\n".join(sections).rstrip() + "\n"


def build_deliverables_zip(
    out_dir: Path,
    exam_slug: str,
    question_id: str,
    versions: list[str],
    inputs: dict[str, Path],
    merged_files: dict[str, Path],
    prompt_versions: dict[str, str],
    schema_text: str,
) -> Path:
    """Bundle every deliverable into a zip using the skill-source layout.

    Every entry keeps the type-prefixed filename the skill ships, so the zip
    can be unpacked straight back over the skill folder. Returns the zip path.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{exam_slug}_{question_id}_deliverables.zip"
    qid = question_id
    qdir = f"{exam_slug}/{qid}"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        # Per-version files: merged question+solution and rendered prompt.
        for version in versions:
            archive.write(
                merged_files[version], f"merged/{qdir}/merged_{qid}_{version}.md"
            )
            archive.writestr(
                f"prompts/{qdir}/prompt_{qid}_{version}.txt", prompt_versions[version]
            )

        # Single-file deliverables: criteria, few-shot, groups, schema.
        archive.write(inputs["criteria"], f"criteria/{exam_slug}/criteria_{qid}.yaml")
        archive.write(inputs["few_shot"], f"few-shot/{exam_slug}/few-shot_{qid}.yaml")
        archive.write(inputs["groups"], f"groups/{exam_slug}/groups_{qid}.yaml")
        archive.writestr(f"schemas/{exam_slug}/schema_{qid}.json", schema_text + "\n")

    return zip_path


def stage_pipeline_files(
    out_dir: Path,
    exam_slug: str,
    question_id: str,
    prompt_versions: dict[str, str],
    schema_text: str,
) -> list[Path]:
    """Write prompts + schema in the backend/data pipeline layout for the PR.

    Files are written under out_dir mirroring their repo paths — everything
    below out_dir is the repo-relative path — so the skill can commit them to
    the grading repo unchanged. Returns the list of staged paths.
    """

    exam_name = exam_display_name(exam_slug)
    prompt_dir = out_dir / "backend" / "data" / exam_name / "prompts"
    schema_dir = out_dir / "backend" / "data" / exam_name / "schemas"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    schema_dir.mkdir(parents=True, exist_ok=True)

    staged: list[Path] = []
    for version, text in prompt_versions.items():
        path = prompt_dir / f"prompt_{question_id}_{version}.txt"
        path.write_text(text, encoding="utf-8")
        staged.append(path)
    schema_path = schema_dir / f"schema_{question_id}.json"
    schema_path.write_text(schema_text + "\n", encoding="utf-8")
    staged.append(schema_path)
    return staged


def parse_args() -> argparse.Namespace:
    """Define the command-line interface."""

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("exam_slug", help="Exam slug such as midterm-1")
    parser.add_argument("question_id", help="Question id such as 1a or 2.3")
    parser.add_argument(
        "--merged-dir",
        type=Path,
        default=None,
        help="Directory of merged_<id>_V*.md files (default: shipped merged/<exam>/<id>).",
    )
    parser.add_argument(
        "--criteria",
        type=Path,
        default=None,
        help="Criteria YAML file (default: shipped criteria/<exam>/criteria_<id>.yaml).",
    )
    parser.add_argument(
        "--few-shot",
        type=Path,
        default=None,
        help="Few-shot examples YAML file (default: shipped few-shot/<exam>/few-shot_<id>.yaml).",
    )
    parser.add_argument(
        "--groups",
        type=Path,
        default=None,
        help="Groups YAML file (default: groups/<exam>/groups_<id>.yaml; required for the zip).",
    )
    parser.add_argument(
        "--philosophy",
        type=Path,
        default=None,
        help="Grading-philosophy markdown file (default: shipped reference file).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output"),
        help="Directory for the deliverables zip and staged PR files (default: ./output).",
    )
    parser.add_argument(
        "--versions",
        nargs="*",
        help="Optional list of version ids to generate (default: all V*.txt files).",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the generated prompts and schema instead of writing files.",
    )
    return parser.parse_args()


def resolve_inputs(args: argparse.Namespace) -> dict[str, Path]:
    """Fill in defaults for any input path the caller did not override."""

    exam = args.exam_slug
    qid = args.question_id
    return {
        "merged_dir": args.merged_dir or SKILL_DIR / "merged" / exam / qid,
        "criteria": args.criteria or SKILL_DIR / "criteria" / exam / f"criteria_{qid}.yaml",
        "few_shot": args.few_shot or SKILL_DIR / "few-shot" / exam / f"few-shot_{qid}.yaml",
        "groups": args.groups or SKILL_DIR / "groups" / exam / f"groups_{qid}.yaml",
        "philosophy": args.philosophy
        or SKILL_DIR / "reference" / "grading-philosophy-examples.md",
    }


def main() -> int:
    """CLI entry point."""

    args = parse_args()
    inputs = resolve_inputs(args)

    # `groups` is only needed for the zip; everything else is needed to render.
    render_inputs = {name: path for name, path in inputs.items() if name != "groups"}
    missing = [f"{name}: {path}" for name, path in render_inputs.items() if not path.exists()]
    if missing:
        print("error: input(s) not found:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    merged_files = find_versioned_files(inputs["merged_dir"], pattern="*_V*.md")
    merged_texts = {version: load_text(path) for version, path in merged_files.items()}

    if args.versions:
        versions = [version if version.startswith("V") else f"V{version}" for version in args.versions]
    else:
        versions = sorted(merged_texts)

    missing_versions = [version for version in versions if version not in merged_texts]
    if missing_versions:
        raise FileNotFoundError(f"missing requested versions: {missing_versions}")

    criteria_data = load_yaml(inputs["criteria"])
    few_shot_data = load_yaml(inputs["few_shot"])
    philosophy_text = load_text(inputs["philosophy"])

    criteria = criteria_data["criteria"]
    criteria_text, criterion_ids = render_criteria(criteria)
    schema = render_schema(criterion_ids)
    schema_text = json.dumps(schema, indent=2, ensure_ascii=False)

    few_shot_examples = [render_few_shot_example(example, criterion_ids) for example in few_shot_data["examples"]]

    prompt_versions: dict[str, str] = {}
    for version in versions:
        prompt_versions[version] = build_prompt(
            merged_text=merged_texts[version],
            philosophy_text=philosophy_text,
            criteria_text=criteria_text,
            few_shot_examples=few_shot_examples,
        )

    if args.stdout:
        for version, text in prompt_versions.items():
            print(f"===== {version} =====")
            print(text)
            print()
        print("===== SCHEMA =====")
        print(schema_text)
        return 0

    # Zip mode needs the groups deliverable, which has no shipped stub.
    if not inputs["groups"].exists():
        print(
            f"error: groups file not found: {inputs['groups']}\n"
            "Write the TA's groups YAML to a file and pass it with --groups.",
            file=sys.stderr,
        )
        return 1

    zip_path = build_deliverables_zip(
        args.out, args.exam_slug, args.question_id, versions, inputs,
        merged_files, prompt_versions, schema_text,
    )
    staged = stage_pipeline_files(
        args.out, args.exam_slug, args.question_id, prompt_versions, schema_text
    )

    print(f"Deliverables zip (for the TA to download): {zip_path}")
    print("PR files staged (commit these at their repo-relative paths below ./output/):")
    for path in staged:
        print(f"  {path.relative_to(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
