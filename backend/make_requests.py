"""Stage Gradescope group-assignment requests from new-format graded files.

For each *_graded.json in submissions/, this script buckets submissions by
each record's ``group`` field (written by assign_groups.py), matches each
bucket against a Gradescope answer group with that same title, and writes the
{stem}_requests.json payloads consumed by post_grades.py. Submissions the
model marked ``uncertain`` are left ungrouped for a TA.

Expected record shape::

    {
      "grade_parsed": {
        "comment": ..., "uncertain": <bool>, "comment_uncertainty": ...,
        "criteria": { "<criterion_id>": <bool>, ... }
      },
      "group": "<bucket label from groups_<id>.yaml or auto-fallback>"
    }

The ``group`` field is the source of truth for bucket-to-Gradescope-title
matching, so run assign_groups.py before this script.

Run from an exam data dir (e.g. ``data/Midterm 2``); the script reads
question_pages/ and submissions/ relative to cwd.
"""

from bs4 import BeautifulSoup
from collections import defaultdict
from pathlib import Path
import json


def extract_groups_from_html(html_path):
    """Parse Gradescope-rendered HTML and return its embedded answer groups."""
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    element = soup.find(attrs={"data-react-props": True})
    data = element.get("data-react-props").replace("&qquot;", '"')
    props = json.loads(data)
    return props['groups']


def collect_criterion_names(graded):
    """Ordered list of criterion ids seen across grade_parsed['criteria'] in graded."""
    names = []
    seen = set()
    for record in graded.values():
        gp = record.get('grade_parsed')
        if not isinstance(gp, dict):
            continue
        criteria = gp.get('criteria')
        if not isinstance(criteria, dict):
            continue
        for name in criteria:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def build_groups_lookup(pages_dir):
    """Build {(question_id, title): answer_group_id} from Gradescope HTML pages."""
    lookup = {}
    for html_file in Path(pages_dir).glob("*.html"):
        for group in extract_groups_from_html(html_file):
            title = group['title']
            if title is None:
                continue
            lookup[(group['question_id'], title)] = group['id']
    return lookup


def compute_group_name(record):
    """Return the bucket label written by assign_groups.py, or None if uncertain."""
    grade_parsed = record.get('grade_parsed')
    if isinstance(grade_parsed, dict) and grade_parsed.get('uncertain') is True:
        return None
    return record.get('group')


def question_id_for_file(stem):
    """VA_8068292_q2.1_70296511 -> 70296511 (the Gradescope question id)."""
    parts = stem.split('_')
    q_idx = next(i for i, p in enumerate(parts) if p.startswith('q'))
    return int(parts[q_idx + 1])


if __name__ == "__main__":
    pages_dir = "question_pages"
    submissions_dir = Path("submissions")

    graded_files = sorted(submissions_dir.glob("*_graded.json"))

    print("Loading groups from HTML pages...")
    groups_lookup = build_groups_lookup(pages_dir)
    print(f"  {len(groups_lookup)} groups loaded")

    total = 0
    for graded_file in graded_files:
        stem = graded_file.stem.removesuffix("_graded")
        question_id = question_id_for_file(stem)

        with open(graded_file, encoding='utf-8') as f:
            graded = json.load(f)

        criterion_names = collect_criterion_names(graded)
        if not criterion_names:
            print(f"  SKIP {graded_file.name}: no criteria found (old format?)")
            continue

        buckets = defaultdict(list)
        for img_key, submission in graded.items():
            if not isinstance(submission.get('grade_parsed'), dict):
                continue
            submission_id = int(Path(img_key).stem)
            group_name = compute_group_name(submission)
            if group_name is None:
                continue
            buckets[group_name].append(submission_id)

        requests_list = []
        for group_name, submission_ids in sorted(buckets.items()):
            answer_group_id = groups_lookup.get((question_id, group_name))
            if answer_group_id is None:
                print(f"  WARNING: no group '{group_name}' for question {question_id} ({graded_file.name})")
                continue
            requests_list.append({
                "question_id": question_id,
                "answer_group_id": answer_group_id,
                "submission_ids": submission_ids,
            })

        out_path = submissions_dir / f"{stem}_requests.json"
        with open(out_path, "w") as f:
            json.dump(requests_list, f, indent=2)

        total += len(requests_list)
        print(f"  {out_path.name}: {len(requests_list)} requests")

    print(f"\nWrote {total} total requests")
