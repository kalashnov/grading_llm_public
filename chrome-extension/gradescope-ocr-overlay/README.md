# Gradescope OCR Overlay

Chrome extension for showing locally generated OCR text on Gradescope grading pages.

## Build OCR Data

From the repository root:

```bash
python3 chrome-extension/gradescope-ocr-overlay/scripts/build_ocr_index.py
```

This writes `data/ocr-index.json` from `backend/data/Final/submissions/*_ocr_cleaned.json`.

## Load In Chrome

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select `chrome-extension/gradescope-ocr-overlay`.

On a grading page like:

```text
https://www.gradescope.com/courses/1288622/questions/72302264/submissions/<submission_id>/grade?group_mode=true
```

the extension shows a floating OCR panel for submission `<submission_id>`.

On an answer-group page like:

```text
https://www.gradescope.com/courses/1288622/questions/72302264/answer_groups/<answer_group_id>
```

the extension reads the submissions embedded in the Gradescope page and inserts OCR transcription cards next to the matching visible answers. The floating OCR panel is hidden on answer-group pages.

The extension intentionally stays dormant on `/answer_groups`, `/answer_groups/`, and `/answer_groups/ungrouped` pages.

Clicking a visible answer tile keeps Gradescope's default behavior. Use the OCR card's `Move to` selector when you want to move that submission to a different answer group.

## Notes

- Viewing OCR is read-only. Selecting a different group in `Move to` posts a single Gradescope group-membership update for that submission.
- The panel uses the bundled OCR index. Re-run the build script after OCR files change, then reload the extension in Chrome.
- On answer-group pages, OCR cards sync after page render or URL navigation, then respond to Gradescope answer-grid changes and viewport changes. Existing cards are preserved when possible; the extension does not run a continuous background refresh loop.
- OCR text is rendered with a lightweight built-in LaTeX renderer for common math patterns such as `\frac{}`, `\hat{}`, Greek letters, subscripts, superscripts, and `\[...\]` display math.
- The panel can be dragged, collapsed, copied, or reloaded on individual grading pages. On answer-group pages, each inline OCR card has its own copy button.
