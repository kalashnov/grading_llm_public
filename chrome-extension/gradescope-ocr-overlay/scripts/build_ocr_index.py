#!/usr/bin/env python3
"""Build the bundled OCR index used by the Chrome extension."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SUBMISSIONS_DIR = ROOT / "backend" / "data" / "Final" / "submissions"
OUTPUT = ROOT / "chrome-extension" / "gradescope-ocr-overlay" / "data" / "ocr-index.json"
SOURCE_PATTERN = re.compile(
    r"^(?P<version>V[A-Z])_(?P<course_id>\d+)_q(?P<question>[\d.]+)_(?P<question_id>\d+)_ocr_cleaned\.json$"
)


def main() -> None:
    entries_by_submission_id: dict[str, dict[str, str | int]] = {}
    entries_by_page: dict[str, dict[str, str | int]] = {}
    source_files = 0

    for path in sorted(SUBMISSIONS_DIR.glob("*_ocr_cleaned.json")):
        match = SOURCE_PATTERN.match(path.name)
        if match is None:
            continue
        source_files += 1
        meta = match.groupdict()
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue

        for image_name, text in sorted(data.items()):
            submission_id = Path(image_name).stem
            entry = {
                "text": "" if text is None else str(text),
                "source_file": path.name,
                "version": meta["version"],
                "course_id": int(meta["course_id"]),
                "question": meta["question"],
                "question_id": int(meta["question_id"]),
                "submission_id": int(submission_id),
            }
            entries_by_submission_id[submission_id] = entry
            page_key = f"{meta['course_id']}:{meta['question_id']}:{submission_id}"
            entries_by_page[page_key] = entry

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": str(SUBMISSIONS_DIR.relative_to(ROOT)),
        "stats": {
            "source_files": source_files,
            "entries": len(entries_by_submission_id),
            "page_keys": len(entries_by_page),
        },
        "entriesBySubmissionId": entries_by_submission_id,
        "entriesByPage": entries_by_page,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"wrote {OUTPUT}")
    print(f"{source_files} source files, {len(entries_by_submission_id)} OCR entries")


if __name__ == "__main__":
    main()
