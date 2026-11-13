"""Experimental OCR using Google Cloud Vision (DOCUMENT_TEXT_DETECTION).

This is a comparison/experiment script — it does NOT replace ocr_all.py. It runs
pure handwriting OCR with Google Vision and writes to <folder>_ocr_gvision.json,
next to the existing <folder>_ocr.json, so the two transcriptions can be diffed.

Differences from the GPT pipeline (by design — Vision is a pure OCR engine):
  - no prompt, no problem-context prior
  - no semantic "Highlighted: <...>" detection
  - returns the raw transcription only

Auth: Application Default Credentials (gcloud auth application-default login).
Needs the Cloud Vision API enabled on the active project:
    gcloud services enable vision.googleapis.com

A folder whose <folder>_ocr_gvision.json already exists is skipped, so a re-run
only processes new/unfinished folders. To force a re-run, delete that json file.

Usage:
    python ocr_gvision.py "<submission_folder>"     # one folder
    python ocr_gvision.py "<submissions_dir>"       # every subfolder
"""
import json
import os
import sys

from google.cloud import vision

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
BATCH_SIZE = 16  # Vision batch_annotate_images caps at 16 images per request

client = vision.ImageAnnotatorClient()


def ocr_folder(folder):
    files = sorted(
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
    )
    results = {}
    for start in range(0, len(files), BATCH_SIZE):
        chunk = files[start:start + BATCH_SIZE]
        requests = []
        for filename in chunk:
            with open(os.path.join(folder, filename), "rb") as f:
                content = f.read()
            requests.append(vision.AnnotateImageRequest(
                image=vision.Image(content=content),
                features=[vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)],
                image_context=vision.ImageContext(language_hints=["en"]),
            ))
        response = client.batch_annotate_images(requests=requests)
        for filename, resp in zip(chunk, response.responses):
            if resp.error.message:
                print(f"  ! {filename}: {resp.error.message}")
                results[filename] = ""
            else:
                results[filename] = resp.full_text_annotation.text
        print(f"  {start + len(chunk)}/{len(files)} images", flush=True)
    return results


def process_folder(folder):
    folder = folder.rstrip("/")
    out_path = folder + "_ocr_gvision.json"
    if os.path.exists(out_path):
        print(f"[skip]    {os.path.basename(folder)} (already done -> {os.path.basename(out_path)})")
        return
    print(f"[gvision] {os.path.basename(folder)}")
    results = ocr_folder(folder)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  -> {os.path.basename(out_path)} ({len(results)} images)\n")


def has_images(path):
    return any(
        os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        for f in os.listdir(path)
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_gvision.py <submission_folder | submissions_dir>")
        sys.exit(1)

    target = sys.argv[1].rstrip("/")
    if not os.path.isdir(target):
        print(f"Not a directory: {target}")
        sys.exit(1)

    if has_images(target):
        process_folder(target)
    else:
        subfolders = sorted(
            os.path.join(target, name)
            for name in os.listdir(target)
            if os.path.isdir(os.path.join(target, name))
        )
        print(f"Found {len(subfolders)} folders in {target}\n")
        for sub in subfolders:
            process_folder(sub)
