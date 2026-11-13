import requests
import json
import time
import os
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
import io

# Working directory for the current grading round. Override with a CLI arg:
#   python fetch_submissions.py "Midterm 1"
# It is resolved relative to this script's folder unless an absolute path is given.
DEFAULT_WORKING_DIR = "Midterm 2"


def resolve_working_dir(name: str) -> Path:
    p = Path(name)
    return p if p.is_absolute() else Path(__file__).parent / p


def process_html_file(html_path: Path, output_dir: Path):
    html_path = Path(html_path)
    stem = html_path.stem

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    element = soup.find(attrs={"data-react-props": True})
    data = element.get("data-react-props").replace("&qquot;", '"')
    props = json.loads(data)

    submissions = []
    for s in props.get("submissions", []):
        if not s.get("masked_crop"):
            continue
        submissions.append({
            "id": s["id"],
            "crop": s["masked_crop"]["url"],
            "question_id": s["question_id"],
            "assignment_submission_id": s["assignment_submission_id"],
        })

    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{stem}.json"
    with open(json_path, "w") as f:
        json.dump(submissions, f, indent=2)
    print(f"  Saved {len(submissions)} entries -> {json_path}")

    img_dir = output_dir / stem
    if img_dir.exists():
        print(f"  Skipping images (folder exists) -> {img_dir}/")
        return False
    img_dir.mkdir(exist_ok=True)

    fetched = 0
    for sub in submissions:
        img_path = img_dir / f"{sub['id']}.png"
        if img_path.exists():
            continue
        try:
            r = requests.get(sub["crop"], stream=True, timeout=15)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            img.save(img_path)
            fetched += 1
            if fetched % 20 == 0:
                time.sleep(0.2)
        except Exception as e:
            print(f"  Warning: failed to fetch image {sub['id']}: {e}")

    print(f"  Images saved -> {img_dir}/")
    return True


def parse_submissions(html_path: Path):
    """Parse all submissions from an HTML question page."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    element = soup.find(attrs={"data-react-props": True})
    data = element.get("data-react-props").replace("&qquot;", '"')
    props = json.loads(data)
    submissions = []
    for s in props.get("submissions", []):
        if not s.get("masked_crop"):
            continue
        submissions.append({
            "id": s["id"],
            "crop": s["masked_crop"]["url"],
            "question_id": s["question_id"],
            "assignment_submission_id": s["assignment_submission_id"],
        })
    return submissions


def download_images(submissions, img_dir: Path, lag_every: int = 20, lag: float = 0.2):
    img_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for sub in submissions:
        img_path = img_dir / f"{sub['id']}.png"
        if img_path.exists():
            continue
        try:
            r = requests.get(sub["crop"], stream=True, timeout=15)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            img.save(img_path)
            fetched += 1
            if fetched % lag_every == 0:
                time.sleep(lag)
        except Exception as e:
            print(f"  Warning: failed to fetch image {sub['id']}: {e}")
    return fetched


def process_html_file(html_path: Path, output_dir: Path):
    html_path = Path(html_path)
    stem = html_path.stem

    submissions = parse_submissions(html_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{stem}.json"
    with open(json_path, "w") as f:
        json.dump(submissions, f, indent=2)
    print(f"  Saved {len(submissions)} entries -> {json_path}")

    img_dir = output_dir / stem
    if img_dir.exists():
        print(f"  Skipping images (folder exists) -> {img_dir}/")
        return False

    download_images(submissions, img_dir)
    print(f"  Images saved -> {img_dir}/")
    return True


def process_html_file_delta(html_path: Path, existing_dir: Path, extra_dir: Path):
    """Fetch only submissions not present in existing_dir, saving into extra_dir."""
    html_path = Path(html_path)
    stem = html_path.stem

    existing_json = existing_dir / f"{stem}.json"
    if existing_json.exists():
        with open(existing_json) as f:
            existing_ids = {s["id"] for s in json.load(f)}
    else:
        existing_ids = set()

    all_submissions = parse_submissions(html_path)
    new_submissions = [s for s in all_submissions if s["id"] not in existing_ids]

    if not new_submissions:
        print(f"  No new submissions.")
        return False

    extra_dir.mkdir(parents=True, exist_ok=True)
    json_path = extra_dir / f"{stem}.json"
    with open(json_path, "w") as f:
        json.dump(new_submissions, f, indent=2)
    print(f"  {len(new_submissions)} new (of {len(all_submissions)}) -> {json_path}")

    img_dir = extra_dir / stem
    download_images(new_submissions, img_dir)
    print(f"  Images saved -> {img_dir}/")
    return True


def process_all_files(working_dir: Path, lag: float = 1.0):
    question_pages_dir = working_dir / "question_pages"
    output_dir = working_dir / "submissions"

    html_files = sorted(question_pages_dir.glob("*.html"))
    print(f"Working dir: {working_dir}")
    print(f"Found {len(html_files)} HTML files in {question_pages_dir}\n")

    for i, html_path in enumerate(html_files):
        print(f"[{i + 1}/{len(html_files)}] Processing {html_path.name}")
        fetched = process_html_file(html_path, output_dir)
        if fetched and i < len(html_files) - 1:
            print(f"  Waiting {lag}s...\n")
            time.sleep(lag)

    print("\nDone.")


def process_all_files_delta(working_dir: Path, lag: float = 0.1):
    """Fetch only new submissions (delta) into submissions_extra/."""
    question_pages_dir = working_dir / "question_pages"
    existing_dir = working_dir / "submissions"
    extra_dir = working_dir / "submissions_extra"

    html_files = sorted(question_pages_dir.glob("*.html"))
    print(f"Working dir: {working_dir}")
    print(f"Found {len(html_files)} HTML files in {question_pages_dir}\n")

    for i, html_path in enumerate(html_files):
        print(f"[{i + 1}/{len(html_files)}] {html_path.name}")
        fetched = process_html_file_delta(html_path, existing_dir, extra_dir)
        if fetched and i < len(html_files) - 1:
            print(f"  Waiting {lag}s...\n")
            time.sleep(lag)

    print("\nDone.")


if __name__ == "__main__":
    delta = "--delta" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    working_dir_name = args[0] if args else DEFAULT_WORKING_DIR
    working_dir = resolve_working_dir(working_dir_name)
    if delta:
        process_all_files_delta(working_dir)
    else:
        process_all_files(working_dir)
