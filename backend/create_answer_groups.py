"""Create Gradescope answer groups from local group YAML files.

This mirrors the local grouping definitions onto Gradescope. It is intentionally
additive: existing answer groups are left in place, and only missing group
titles are created.

Usage:
    python create_answer_groups.py data/Final --dry-run
    python create_answer_groups.py data/Final
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

from post_grades import COURSE_ID, SESSION_COOKIE


GRADED_SUFFIX = "_graded.json"
CONTROL_GROUP = "control"


def build_session():
    session = requests.Session()
    cookie_header = os.environ.get("GRADESCOPE_SESSION_COOKIE", SESSION_COOKIE)
    for cookie in cookie_header.split("; "):
        name, _, value = cookie.partition("=")
        session.cookies.set(name.strip(), value.strip(), domain="www.gradescope.com")
    return session


def parse_graded_filename(path):
    match = re.match(
        r"^(V[A-Z])_\d+_q([\d.]+)_(\d+)" + re.escape(GRADED_SUFFIX) + r"$",
        path.name,
    )
    if not match:
        raise ValueError(f"Unexpected graded filename format: {path.name}")
    return match.group(1), match.group(2), int(match.group(3))


def group_titles_for(exam_dir, question, include_control):
    groups_path = exam_dir / "groups" / f"groups_{question}.yaml"
    with groups_path.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    titles = [group["name"] for group in spec.get("groups", [])]
    if include_control:
        titles.append(CONTROL_GROUP)
    return titles


def csrf_from_response(resp):
    soup = BeautifulSoup(resp.text, "html.parser")
    token = soup.find("meta", {"name": "csrf-token"})
    if token is None:
        raise RuntimeError("Could not find CSRF token; session may be expired")
    return token["content"]


def fetch_existing_groups(session, question_id):
    url = f"https://www.gradescope.com/courses/{COURSE_ID}/questions/{question_id}/answer_groups"
    resp = session.get(url)
    resp.raise_for_status()
    csrf = csrf_from_response(resp)

    soup = BeautifulSoup(resp.text, "html.parser")
    element = soup.find(attrs={"data-react-props": True})
    groups = []
    if element is not None:
        props = json.loads(element.get("data-react-props").replace("&qquot;", '"'))
        groups = props.get("groups") or []
    return csrf, groups


def set_complex_grouping(session, question_id, csrf):
    url = f"https://www.gradescope.com/courses/{COURSE_ID}/questions/{question_id}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRF-Token": csrf,
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {"question": {"assisted_grading_type": "complex"}}
    resp = session.patch(url, headers=headers, json=payload)
    return resp.status_code


def create_group(session, question_id, csrf, title):
    url = f"https://www.gradescope.com/courses/{COURSE_ID}/questions/{question_id}/answer_groups"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRF-Token": csrf,
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {"title": title, "internal_title": None}
    resp = session.post(url, headers=headers, json=payload)
    return resp.status_code


def create_for_file(session, exam_dir, graded_path, include_control, dry_run):
    _version, question, question_id = parse_graded_filename(graded_path)
    target_titles = group_titles_for(exam_dir, question, include_control)

    if dry_run:
        print(f"{graded_path.name}: would ensure {len(target_titles)} groups")
        for title in target_titles:
            print(f"  {title}")
        return 0, 0

    csrf, existing = fetch_existing_groups(session, question_id)
    existing_titles = {group.get("title") for group in existing}

    type_status = set_complex_grouping(session, question_id, csrf)
    print(f"{graded_path.name}: set complex -> {type_status}")

    created = 0
    skipped = 0
    for title in target_titles:
        if title in existing_titles:
            print(f"  exists  {title}")
            skipped += 1
            continue
        status = create_group(session, question_id, csrf, title)
        print(f"  create  {status}  {title}")
        if 200 <= status < 300:
            created += 1
        time.sleep(0.2)

    return created, skipped


def main():
    parser = argparse.ArgumentParser(description="Create missing Gradescope answer groups.")
    parser.add_argument("exam_dir", help="Exam data directory, e.g. backend/data/Final")
    parser.add_argument("--dry-run", action="store_true", help="Print planned groups only")
    parser.add_argument(
        "--no-control",
        action="store_true",
        help=f"Do not create the '{CONTROL_GROUP}' answer group title",
    )
    args = parser.parse_args()

    exam_dir = Path(args.exam_dir)
    graded_files = sorted((exam_dir / "submissions").glob(f"*{GRADED_SUFFIX}"))
    if not graded_files:
        raise SystemExit(f"No {GRADED_SUFFIX} files found in {exam_dir / 'submissions'}")

    session = None if args.dry_run else build_session()
    total_created = 0
    total_skipped = 0
    include_control = not args.no_control

    for graded_path in graded_files:
        created, skipped = create_for_file(
            session,
            exam_dir,
            graded_path,
            include_control=include_control,
            dry_run=args.dry_run,
        )
        total_created += created
        total_skipped += skipped

    print(f"\nDone. Created {total_created}, already existed {total_skipped}.")


if __name__ == "__main__":
    main()
