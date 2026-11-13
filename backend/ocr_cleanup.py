"""Pipeline stage 2: clean up Google Vision OCR output with a GPT model.

Google Vision (ocr_gvision.py) does the raw OCR -> <folder>_ocr_gvision.json.
This script refines that output with a GPT model that ALSO sees the image at
low detail. It fixes Vision's known failure modes (dropped decimals, garbled
2-D math, transcribed crossed-out text) and produces a clean transcription of
the student's final answer.

Input  per image: the image (detail set by IMAGE_DETAIL) + the Vision transcription.
Output per folder: <folder>_ocr_cleaned.json   -> {image_name: cleaned_text}

A folder whose <folder>_ocr_cleaned.json already exists is skipped.

Usage:
    python ocr_cleanup.py "<submission_folder | submissions_dir>" [model]
e.g.
    python ocr_cleanup.py "Midterm 2/submissions"
    python ocr_cleanup.py "Midterm 2/submissions/VA_8169253_q2.1_71833036" gpt-4o
"""
import base64
import json
import os
import sys
import tempfile
import time

from openai import OpenAI

from batch_registry import clear_batch_id, get_or_submit_batch

client = OpenAI()

DEFAULT_MODEL = "gpt-4o"
IMAGE_DETAIL = "high"  # "low" or "high" — high lets the model actually read digits
# Keep one batch well under the gpt-4o Batch enqueued-token limit (90k tokens):
# ~2.5k input tokens/image, so 24 images ~= 60k tokens per batch.
CHUNK_SIZE = 256
POLL_INTERVAL = 5  # seconds between batch-status polls

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Blank answers: the cleanup model is told to emit an empty string for a blank
# submission. We replace that with an explicit placeholder so downstream grading
# sees clear text for a blank page instead of an empty string (which the grader
# tends to hallucinate work for).
EMPTY_PLACEHOLDER = "student provided no comment"


# --- helpers copied from the now-removed ocr_gpt_api / ocr_all modules ---

def _image_url(path):
    """Return a base64 data URL for an image, for inlining in a chat request."""
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"


def submit_batch(requests):
    """Write requests to a temp JSONL, upload it, and create a batch job."""
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


def wait_for_batch(batch_id, label=""):
    """Poll a batch until it finishes; return it, or raise on failure."""
    while True:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"  [{label}] status={batch.status} completed={counts.completed}/{counts.total}", flush=True)
        if batch.status == "completed":
            return batch
        if batch.status in ("failed", "expired", "cancelled"):
            raise RuntimeError(f"Batch for {label} ended with status: {batch.status}")
        time.sleep(POLL_INTERVAL)

CLEANUP_PROMPT = """You are cleaning up a raw OCR transcription of one handwritten answer from a student exam.

You are given two things:
1. An IMAGE of the student's handwritten answer.
2. A raw OCR transcription of that image produced by Google Cloud Vision.

The Vision transcription is a starting point only. It has known, systematic flaws:
- it gets handwritten NUMBERS wrong in several ways:
    * drops or misplaces the decimal point:  "0.439" -> "0439" or "439";  "0.05" -> "095";  "0.013" -> "0013";
    * turns the leading "0." into a digit:  "0.489" -> "6489";
    * merges two adjacent numbers into one run of digits:  "0.439  0.489" -> "0439 0489" or "6928";
    * splits one number into pieces across lines/tokens:  "0.01276" -> "0" / "01276";
    * misreads single digits, producing a plausible but WRONG number:  "0.464" -> "0.444",
      "0.439" -> "0.937", "0.013" -> "0.913", "0.489" -> "0.989", "26.81" -> "26.31"
      (common digit confusions: 4<->9, 9<->0<->6, 1<->7, 3<->8, 5<->6);
- it garbles 2-D math (stacked fractions, exponents, subscripts) into scattered, out-of-order tokens;
- it transcribes crossed-out text and mixes it in with the final answer;
- it does not handle math symbols (e.g. writes "B" for the Greek letter beta).

The IMAGE is the source of truth. Use the Vision text only as a hint -- and if the Vision text
for this answer is too garbled to reconstruct confidently (scattered nonsense tokens, no
recoverable structure), IGNORE the Vision text entirely and transcribe directly from the image.
Never invent equations, numbers, words, or structure to force garbled Vision text to make sense.
Transcribe only what you can actually read in the image; if a part is genuinely illegible, write
[illegible] for that part rather than guessing.

Produce a clean, faithful transcription of what the student actually wrote, following these rules:

1. MATH. Reconstruct the 2-D math that Vision scrambled -- fractions, exponents, subscripts,
   roots, and Greek letters (beta, beta_0, beta_1) -- into correct, readable math. LaTeX is prefered, but Linear
   notation is fine; just make it accurate, and keep hypotheses, formulas and
   work in the order the student wrote them.

2. NUMBERS. Numbers are the most error-prone part of the Vision text -- treat EVERY number as
   suspect. Read each digit and decimal point directly off the IMAGE; do not trust Vision's
   version of a number. Put decimal points back exactly where the student placed them, and
   correct any digits Vision misread. Still transcribe EXACTLY what the student wrote -- do NOT
   fix the student's arithmetic or reasoning. If the student genuinely wrote a wrong number,
   keep it wrong.

3. CROSSED-OUT TEXT. REMOVE anything the student struck through, scribbled out, or cancelled.
   Transcribe only what the student left standing as their final answer.
   EXCEPTION: if the student explicitly marks struck text to be kept (writes "stet", "keep",
   "leave it", draws it back in, etc.), then keep that text.

4. HIGHLIGHTED / BOXED CONTENT. Some students mark their final answer with a highlighter pen, a hand-drawn box, a circle, or a heavy
   underline. ONLY when you can clearly see such a mark in the IMAGE, put exactly ONE final line per each marked answer:
       Highlighted: <the marked content, cleaned>
   If nothing in the image is highlighted, boxed, or circled, DO NOT add a "Highlighted:" line
   at all. Never invent one, and never just grab the last number or last line and call it
   highlighted -- the line must correspond to a real mark you can see.

5. PLOTS. If the student drew a graph, chart, or scatter plot, describe it rather than trying to
   transcribe it as text. Capture:
   - axis labels and any scale markings the student wrote (e.g. "x-axis: Age, y-axis: Income, scale 0–100");
   - the shape of any drawn line or curve (e.g. "upward-sloping line", "U-shaped curve", "roughly flat");
   - any data points the student plotted, if individually marked;
   - any annotations, arrows, or labels the student added to the plot.
   Use a compact format: "Plot: [x-axis] vs [y-axis]; [description of what is drawn]".
   If axes are unlabeled, note that. Do not invent labels or values you cannot see in the image.

6. You are TRANSCRIBING, not grading. Preserve the student's own mistakes. Add no commentary.

7. If the answer is blank, output an empty string.

Output only the cleaned transcription."""


def build_requests(folder, vision_data, model):
    requests = []
    for image_name, vision_text in vision_data.items():
        image_path = os.path.join(folder, image_name)
        if not os.path.exists(image_path):
            continue
        content = [
            {"type": "text", "text": f"Google Vision OCR output:\n{vision_text}"},
            {"type": "image_url", "image_url": {"url": _image_url(image_path), "detail": IMAGE_DETAIL}},
        ]
        requests.append({
            "custom_id": image_name,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "messages": [
                    {"role": "user", "content": CLEANUP_PROMPT},
                    {"role": "user", "content": content},
                ],
                "max_tokens": 1024,
            },
        })
    return requests


def parse_output(batch):
    output = client.files.content(batch.output_file_id).text
    results = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        content = item["response"]["body"]["choices"][0]["message"]["content"]
        results[item["custom_id"]] = content if content.strip() else EMPTY_PLACEHOLDER
    return results


WINDOW = 20  # number of batches live at the same time
DEAD_STATUSES = ("failed", "expired", "cancelled")


def submit_folder(folder, model):
    """Submit batch(es) for a folder and return immediately (don't wait).

    Returns (out_path, label, batch_ids) or None if the folder is skipped.
    """
    folder = folder.rstrip("/")
    out_path = folder + "_ocr_cleaned.json"
    if os.path.exists(out_path):
        print(f"[skip]    {os.path.basename(folder)} (already done)")
        return None

    vision_path = folder + "_ocr_gvision.json"
    if not os.path.exists(vision_path):
        print(f"[skip]    {os.path.basename(folder)} (no {os.path.basename(vision_path)})")
        return None

    with open(vision_path, encoding="utf-8") as f:
        vision_data = json.load(f)

    requests = build_requests(folder, vision_data, model)
    if not requests:
        print(f"[skip]    {os.path.basename(folder)} (no images)")
        return None

    label = os.path.basename(folder)
    chunks = [requests[i:i + CHUNK_SIZE] for i in range(0, len(requests), CHUNK_SIZE)]
    print(f"[submit]  {label} ({len(requests)} images, model={model}, {len(chunks)} batches)")

    registry_dir = os.path.dirname(os.path.abspath(folder))
    batch_ids = []
    for i, chunk in enumerate(chunks, 1):
        key = f"{label}:chunk{i}"
        bid = get_or_submit_batch(client, registry_dir, key, lambda c=chunk: submit_batch(c))
        print(f"  Batch {i}/{len(chunks)} ID: {bid}")
        batch_ids.append(bid)

    return (out_path, label, batch_ids, registry_dir)


def collect_folder(out_path, label, batch_ids, registry_dir):
    """Wait for all batches of a folder, write the output file, and clear registry keys."""
    results = {}
    for i, bid in enumerate(batch_ids, 1):
        key = f"{label}:chunk{i}"
        batch = wait_for_batch(bid, label=f"{label} {i}/{len(batch_ids)}")
        results.update(parse_output(batch))
        clear_batch_id(registry_dir, key)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  -> {os.path.basename(out_path)} ({len(results)} images)\n")


def process_folder(folder, model):
    """Submit and collect a single folder (used when targeting one folder directly)."""
    job = submit_folder(folder, model)
    if job:
        collect_folder(*job)


def run_staggered(subfolders, model):
    folder_iter = iter(subfolders)
    # Each entry: {out_path, label, batch_ids, registry_dir, results, pending}
    in_flight = []

    def try_submit_next():
        for sub in folder_iter:
            job = submit_folder(sub, model)
            if job:
                out_path, label, batch_ids, registry_dir = job
                in_flight.append({
                    "out_path": out_path,
                    "label": label,
                    "batch_ids": batch_ids,
                    "registry_dir": registry_dir,
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
                bid = job["batch_ids"][i]
                batch = client.batches.retrieve(bid)
                counts = batch.request_counts
                print(f"  [{label} {i+1}/{n}] status={batch.status} completed={counts.completed}/{counts.total}", flush=True)
                if batch.status == "completed":
                    job["results"].update(parse_output(batch))
                    clear_batch_id(job["registry_dir"], f"{label}:chunk{i+1}")
                    job["pending"].discard(i)
                    any_progress = True
                elif batch.status in DEAD_STATUSES:
                    raise RuntimeError(f"Batch {bid} for {label} ended with status: {batch.status}")

            if not job["pending"]:
                in_flight.remove(job)
                with open(job["out_path"], "w", encoding="utf-8") as f:
                    json.dump(job["results"], f, indent=2, ensure_ascii=False)
                print(f"  -> {os.path.basename(job['out_path'])} ({len(job['results'])} images)\n")
                try_submit_next()

        if not any_progress:
            time.sleep(POLL_INTERVAL)


def has_images(path):
    return any(
        os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        for f in os.listdir(path)
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_cleanup.py <submission_folder | submissions_dir> [model]")
        sys.exit(1)

    target = sys.argv[1].rstrip("/")
    model = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL

    if not os.path.isdir(target):
        print(f"Not a directory: {target}")
        sys.exit(1)

    if has_images(target):
        process_folder(target, model)
    else:
        subfolders = sorted(
            os.path.join(target, name)
            for name in os.listdir(target)
            if os.path.isdir(os.path.join(target, name))
        )
        print(f"Found {len(subfolders)} folders in {target}\n")
        run_staggered(subfolders, model)
