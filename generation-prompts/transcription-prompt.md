# Transcription generation prompt

Use this to (re)generate the per-version question texts in
`skills/prompt-authoring/questions/<exam>/<id>/questions_<id>_V*.txt`.

## Input

The exam PDFs — one per version (VA, VB, VC, VD).

## Task

Transcribe the **Part II short-answer questions**. SKIP Part I (multiple-choice).

For each short-answer question and each of its subparts, produce one plain-text
file per version containing the transcribed problem statement.

## Question id convention

Part II's questions map onto q-groups; subparts map onto the decimal:

- Part II Question 1 -> id group `2`; subparts a, b, c, ... -> `2.1, 2.2, 2.3, ...`
- Part II Question 2 -> id group `3`; subparts a, b, ...    -> `3.1, 3.2, ...`
- Part II Question 3 -> id group `4`; subparts a, b, c      -> `4.1, 4.2, 4.3`

(This matches the existing `prompt_*` / `schema_*` file ids in the pipeline.)

## Output layout

```
questions/<exam>/<id>/questions_<id>_VA.txt  ..._VB.txt  ..._VC.txt  ..._VD.txt
```

One file per version, **even when the versions are identical**. The filename is
prefixed with its type (`questions_`) and the question id so it is unambiguous
when shown as an artifact — e.g. `questions_2.1_VA.txt`.

## Transcription rules

1. Each file must be **self-contained**: include the question's shared stem (the
   setup, the model, any reported regression results) followed by that subpart's
   specific ask. A grader should need only this one file for full context.
2. No grading instructions, no point values (`(6 pts)`), no commentary — only
   the problem statement as the student saw it.
3. Math in plain text: `beta_0`, `beta_1`, `R^2`, `hrwage_hat`,
   `voteA = beta_0 + beta_1 * shareA + u`. Reconstruct stacked / 2-D math
   linearly.
4. **Numbers are critical.** The PDF text layer garbles digits, decimal points
   and standard errors. Read every number off the **rendered page image**, not
   the text layer. Capture each version's numbers exactly — they differ between
   versions.
5. **Figures** (scatter plots, graphs): the student saw an image. Transcribe it
   as a bracketed text description of what the figure shows, and flag that this
   is approximate and must be verified against the real image.
6. Versions usually differ only in numbers, but occasionally a version adds a
   minor instruction (e.g. "Round to 4 decimal places."). Capture such wording
   differences verbatim, in that version's file only.
