from pathlib import Path
import zipfile

zip_path = Path("/mnt/data/prompt-authoring.zip")
extract_dir = Path("/mnt/data/prompt-authoring")

extract_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(str(zip_path), "r") as zf:
    zf.extractall(str(extract_dir))

print("Extraction complete.")
print(f"Extracted into: {extract_dir}")

top_level = sorted([p.name for p in extract_dir.iterdir()])
print("Top-level contents:")
for item in top_level[:50]:
    print("-", item)