import base64
import json
import os
import re
import sys
import tempfile
import time

from openai import OpenAI

from batch_registry import clear_batch_id, get_or_submit_batch

client = OpenAI()


def _image_url(path):
    """Return a base64 data URL for an image, for inlining in a chat request."""
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"

# Suffix of the OCR files that grading consumes (the GPT-cleaned transcription
# produced by ocr_cleanup.py). The matching graded output replaces it below.
OCR_SUFFIX = "_ocr_cleaned.json"
GRADED_SUFFIX = "_graded.json"

CHUNK_SIZE = 256
WINDOW = 4
POLL_INTERVAL = 5
DEAD_STATUSES = ("failed", "expired", "cancelled")


def resolve_dirs(ocr_path):
    """Locate the prompts/ and schemas/ folders for an OCR file.

    OCR files live in ``<midterm>/submissions/``; prompts and schemas are
    sibling folders ``<midterm>/prompts/`` and ``<midterm>/schemas/``.
    """
    submissions_dir = os.path.dirname(os.path.abspath(ocr_path))
    midterm_dir = os.path.dirname(submissions_dir)
    return (
        os.path.join(midterm_dir, "prompts"),
        os.path.join(midterm_dir, "schemas"),
    )


def already_done(ocr_path):
    return os.path.exists(ocr_path.replace(OCR_SUFFIX, GRADED_SUFFIX))


def parse_ocr_filename(ocr_path):
    name = os.path.basename(ocr_path)
    pattern = r"^(V[A-Z])_\d+_q([\d.]+)_\d+" + re.escape(OCR_SUFFIX) + r"$"
    match = re.match(pattern, name)
    if not match:
        raise ValueError(f"Unexpected OCR filename format: {name}")
    version, question = match.group(1), match.group(2)
    return version, question


def prompt_path_for(ocr_path, version, question):
    prompts_dir, _ = resolve_dirs(ocr_path)
    return os.path.join(prompts_dir, f"prompt_{question}_{version}.txt")


def load_prompt(ocr_path, version, question):
    prompt_path = prompt_path_for(ocr_path, version, question)
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path) as f:
        return f.read()


def load_schema(ocr_path, version, question):
    _, schemas_dir = resolve_dirs(ocr_path)
    schema_path = os.path.join(schemas_dir, f"schema_{question}.json")
    if not os.path.exists(schema_path):
        return None
    with open(schema_path) as f:
        return json.load(f)


def build_batch_requests(ocr_data, prompt, images_dir, schema=None):
    requests = []
    for image_name, ocr_text in ocr_data.items():
        second_content = [{"type": "text", "text": f"Here is the student's answer: {ocr_text}"}]
        image_path = os.path.join(images_dir, image_name)
        if os.path.exists(image_path):
            second_content.append({"type": "image_url", "image_url": {"url": _image_url(image_path), "detail": "low"}})
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "user", "content": second_content},
            ],
            "max_tokens": 1024,
        }
        if schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "grade_result",
                    "strict": True,
                    "schema": schema,
                },
            }
        requests.append({
            "custom_id": image_name,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        })
    return requests


def submit_batch(requests):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as f:
            batch_file = client.files.create(file=f, purpose="batch")
    finally:
        os.unlink(tmp_path)

    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    return batch.id


def wait_for_batch(batch_id):
    while True:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"  [batch] status={batch.status} completed={counts.completed}/{counts.total}", flush=True)
        if batch.status in ("completed", "failed", "expired", "cancelled"):
            return batch
        time.sleep(POLL_INTERVAL)


def parse_batch_output(batch):
    if batch.status != "completed":
        if batch.errors:
            for e in batch.errors.data:
                print(f"  [error] code={e.code} message={e.message}", flush=True)
        if batch.error_file_id:
            error_output = client.files.content(batch.error_file_id).text
            for line in error_output.splitlines():
                if line.strip():
                    print(f"  [error detail] {line}", flush=True)
        raise RuntimeError(f"Batch ended with status: {batch.status}")

    output = client.files.content(batch.output_file_id).text
    results = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        image_name = item["custom_id"]
        response_body = item["response"]["body"]
        grade_text = response_body["choices"][0]["message"]["content"]

        usage = response_body.get("usage", {})
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
        total = usage.get("prompt_tokens", 0) or 0
        ratio = cached / total if total > 0 else 0.0
        print(f"  {image_name}: cached={cached}, prompt={total}, ratio={ratio:.3f}")

        try:
            grade_parsed = json.loads(grade_text)
        except json.JSONDecodeError:
            grade_parsed = None

        results[image_name] = {"grade": grade_text, "grade_parsed": grade_parsed}
    return results


def output_path_for(ocr_path):
    return ocr_path.replace(OCR_SUFFIX, GRADED_SUFFIX)


def write_grade_results(out_path, ocr_data, grade_results):
    results = {
        image_name: {"ocr": ocr_text, **grade_results.get(image_name, {"grade": None, "grade_parsed": None})}
        for image_name, ocr_text in ocr_data.items()
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"  -> {os.path.basename(out_path)} ({len(results)} results)\n")


def submit_ocr_file(ocr_path):
    """Submit batch(es) for an OCR file and return immediately.

    Returns a job tuple or None if the file is skipped.
    """
    if already_done(ocr_path):
        print(f"[skip]    {os.path.basename(ocr_path)} (already done)")
        return None

    version, question = parse_ocr_filename(ocr_path)
    prompt_path = prompt_path_for(ocr_path, version, question)
    if not os.path.exists(prompt_path):
        print(f"[skip]    {os.path.basename(ocr_path)} (no prompt: {os.path.basename(prompt_path)})")
        return None

    with open(prompt_path) as f:
        prompt = f.read()
    schema = load_schema(ocr_path, version, question)

    with open(ocr_path) as f:
        ocr_data = json.load(f)

    images_dir = ocr_path.replace(OCR_SUFFIX, "")
    registry_dir = os.path.dirname(os.path.abspath(ocr_path))
    label = os.path.basename(ocr_path)

    requests = build_batch_requests(ocr_data, prompt, images_dir, schema=schema)
    if not requests:
        print(f"[skip]    {label} (no OCR entries)")
        return None

    chunks = [requests[i:i + CHUNK_SIZE] for i in range(0, len(requests), CHUNK_SIZE)]
    print(f"[submit]  {label} ({len(requests)} answers, {len(chunks)} batches)")

    batch_ids = []
    for i, chunk in enumerate(chunks, 1):
        key = f"grade::{label}::{i}"
        batch_id = get_or_submit_batch(
            client, registry_dir, key, lambda chunk=chunk: submit_batch(chunk)
        )
        print(f"  Batch {i}/{len(chunks)} ID: {batch_id}")
        batch_ids.append(batch_id)

    return (output_path_for(ocr_path), label, batch_ids, registry_dir, ocr_data)


def collect_ocr_file(out_path, label, batch_ids, registry_dir, ocr_data):
    """Wait for all batches of an OCR file, write output, and clear registry."""
    grade_results = {}
    for i, batch_id in enumerate(batch_ids, 1):
        key = f"grade::{label}::{i}"
        batch = wait_for_batch(batch_id)
        grade_results.update(parse_batch_output(batch))
        clear_batch_id(registry_dir, key)

    write_grade_results(out_path, ocr_data, grade_results)


def grade_ocr_file(ocr_path):
    """Submit and collect a single OCR file."""
    job = submit_ocr_file(ocr_path)
    if job:
        collect_ocr_file(*job)


def run_staggered(ocr_files):
    ocr_iter = iter(ocr_files)
    # Each entry: {out_path, label, batch_ids, registry_dir, ocr_data, results, pending}
    in_flight = []

    def try_submit_next():
        for ocr_path in ocr_iter:
            job = submit_ocr_file(ocr_path)
            if job:
                out_path, label, batch_ids, registry_dir, ocr_data = job
                in_flight.append({
                    "out_path": out_path,
                    "label": label,
                    "batch_ids": batch_ids,
                    "registry_dir": registry_dir,
                    "ocr_data": ocr_data,
                    "results": {},
                    "pending": set(range(len(batch_ids))),
                })
                return

    for _ in range(WINDOW):
        try_submit_next()

    while in_flight:
        any_progress = False
        for job in list(in_flight):
            label = job["label"]
            n = len(job["batch_ids"])
            for i in list(job["pending"]):
                batch_id = job["batch_ids"][i]
                batch = client.batches.retrieve(batch_id)
                counts = batch.request_counts
                print(f"  [{label} {i+1}/{n}] status={batch.status} completed={counts.completed}/{counts.total}", flush=True)
                if batch.status == "completed":
                    job["results"].update(parse_batch_output(batch))
                    clear_batch_id(job["registry_dir"], f"grade::{label}::{i+1}")
                    job["pending"].discard(i)
                    any_progress = True
                elif batch.status in DEAD_STATUSES:
                    parse_batch_output(batch)

            if not job["pending"]:
                in_flight.remove(job)
                write_grade_results(job["out_path"], job["ocr_data"], job["results"])
                try_submit_next()

        if not any_progress:
            time.sleep(POLL_INTERVAL)


def run_all(submissions_dir):
    ocr_files = sorted(
        os.path.join(submissions_dir, name)
        for name in os.listdir(submissions_dir)
        if name.endswith(OCR_SUFFIX)
    )

    print(f"Found {len(ocr_files)} OCR files in {submissions_dir}\n")
    run_staggered(ocr_files)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python grade_all.py <ocr_file_or_submissions_dir>")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isfile(target):
        print(f"Grading: {os.path.basename(target)}")
        grade_ocr_file(target)
    elif os.path.isdir(target):
        run_all(target)
    else:
        print(f"Not a file or directory: {target}")
        sys.exit(1)
