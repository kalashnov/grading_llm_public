# Solution generation prompt

Use this to (re)generate the per-version model answers in
`skills/prompt-authoring/solutions/<exam>/<id>/solutions_<id>_V*.txt`.

## Input

- The transcribed question files (`questions/<exam>/<id>/questions_<id>_V*.txt`).
- The exam's appendix — the critical-value table and the formula sheet.

## Task

For each question and each version, produce a concise **model answer**.

## Output layout

```
solutions/<exam>/<id>/solutions_<id>_VA.txt  ..._VB.txt  ..._VC.txt  ..._VD.txt
```

One file per version, **even when the answer is identical** across versions. The
filename is prefixed with its type (`solutions_`) and the question id so it is
unambiguous when shown as an artifact — e.g. `solutions_2.1_VA.txt`.

## Content rules

1. Content = **only what an A-grade student answer would contain**: the correct
   final result, the key steps the question expects a student to show, and any
   definitions the question explicitly asks for.
2. Do **not** restate the question.
3. No commentary, no meta-notes, no reasoning beyond what belongs in an A
   answer.
4. Compute version-specific numbers **per version** — the questions differ in
   their numbers. Use the critical values from the exam appendix.
5. Plain-text math, same conventions as the transcription prompt (`beta_0`,
   `R^2`, `hrwage_hat`, etc.).
6. If a question depends on a figure that was only transcribed approximately,
   give the most likely intended answer, and report separately to the maintainer
   that it needs verification (do not put that note inside the answer file).
