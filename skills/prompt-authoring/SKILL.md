---
name: grading-prompt-authoring
description: >-
  Helps a teaching assistant turn an exam question into a structured grading-prompt
  spec for the LLM grading pipeline. Use when a TA wants to create or revise the
  grading criteria for an exam question — it interviews the TA about how the question
  should be graded and outputs a YAML spec plus a human-readable preview of the
  rendered grading prompt.
---
 
# Grading Prompt Authoring
 
## Purpose
 
A TA brings one exam question. Through a short conversation, this skill produces a
**spec** (YAML) that captures the grading criteria and the groups that bucket
submissions by those criteria, then uses those outputs to assemble the final
grading prompt and matching JSON schema.

## Scope: one question at a time
 
The skill works on **exactly one question per run** — but on **all of its versions
(VA–VD) at once**. The very first thing it does is ask the TA which question. It
never tries to handle several questions in one conversation.

## How submissions are bucketed (criteria -> groups)

The criteria a TA writes are **not** the final categorization. For each submission
the grading LLM answers every criterion true/false; then **groups** — boolean rules
over those criteria (`AND`/`OR`/`NOT`) — bucket the submission. The TA authors both
the criteria and the groups. See `reference/groups.md`; explain this to the TA so
they understand why and how many criteria are needed.
 
## Shipped reference, and why it must be verified
 
Five things are shipped with the skill, per question:
- `merged/<exam>/<id>/merged_<id>_V*.md` — the merged question and solution, per version.
- `criteria/<exam>/criteria_<id>.yaml` — Stub criteria shipped with the skill.
- `few-shot/<exam>/few-shot_<id>.yaml` — Few-shot examples shipped with the skill.
- `schemas/<exam>/schema_<id>.json` — The JSON schema that the grader must output.
- `prompts/<exam>/<id>/prompt_<id>_V*.txt` — The final grading prompts, one per version.

The SKILL should return all of the same files in the same structure with the same names, edited with the help of the TA. Additionally they should return

- `groups/<exam>/groups_<id>.yaml`

**All four were produced by an LLM and may contain errors**

## Rendering printed student answers

Whenever you print a student answer into the chat (steps 2 and 4), choose how to
render it based on whether it contains LaTeX:

- **No LaTeX** — wrap the answer verbatim in a fenced markdown code block
  (` ``` ` … ` ``` `). This preserves the student's exact text, spacing, and
  characters without the chat client interpreting any of it.
- **Contains LaTeX** — render the answer as LaTeX (inline `$…$` / display
  `$$…$$`) so the math displays as the student wrote it. Do not put a
  LaTeX-bearing answer inside a code block — that would show raw markup instead
  of the rendered math.

## Presenting artifacts

Whenever you present a file to the TA as an artifact (or canvas), tell them they
have two ways to make changes: discuss the corrections with you and let you edit
the file, or download the file and edit it themselves.

## Workflow
 
1. **Ask which question.** The first message asks the TA which question they want
   to work on (exam + question id, e.g. Midterm 2 / `2.3`). One question per run;
   all of its versions are handled together. Provide them with a list of all available questions. Then load every
   `questions/<exam>/<id>/questions_<id>_V*.txt` and every
   `solutions/<exam>/<id>/solutions_<id>_V*.txt` file for that question. If any are
   missing, ask the TA to provide them.



2. **Verify the transcription and the solution — the FIRST interview question.**
   Show the TA the transcribed question text and the solution from folder `merged/<exam>/<id>/` (if you are Claude show as ARTIFACTS, if you are GPT show as CANVAS). State plainly that both were produced by an LLM and may be wrong. Ask
   directly: *"Is anything transcribed or answered incorrectly here?"* Address the TA's feedback.

   Suggest them to report that they are done to proceed to the next step.

3. **Explain the TA the grading points and grouping:** Explain the TA that they will now create criteria for the groups. Send the TA the contents of `reference/criteria-explainer.md` verbatim as a literal message. Show the TA the contents of the criteria for their question (if you are Claude do it through ARTIFACTS, if you are ChatGPT do it through CANVAS, use the same filenames is in the original, neither do merge files!). Draft what kind of sensible groups can be made out of these rules. Create and maintain `groups_<id>.yaml` for them, following the schema defined in `reference/groups.md`. 

As a reference provide them with 5 examples of student answers sourced from `few-shot_<id>.yaml` (also include the example grades), rendering each per "Rendering printed student answers" above. Tell them that if any grading is wrong, they will have opportunity to correct later.

Propose them to: 1) suggest edits to rules/propose new ones, delete any rules they don't want; 2) suggest what kind of groups would we create from these rules. 

Suggest them to report that they are done to proceed to the next step.

4. **Validating the few-shot examples:** Explain to the TA that the prompt will contain examples of real students. Show them the few-shot examples from the `few-shot/<exam>/few-shot_<id>.yaml` (if you are Claude show as ARTIFACTS, if you are ChatGPT show as CANVAS) file and ask them to recheck them for accuracy. Also for readability, print the 5 answers into the chat, rendering each per "Rendering printed student answers" above. Suggest them to update the few-shot grading from the criteria they just edited. Then ask them to check the grading of the few shot examples. Address any corrections they suggest. 

Suggest them to report that they are done to proceed to the next step.

5. **Assemble the deliverables:** Once the criteria, few-shot examples and groups
   are finalized, run `generate_grading_prompt.py` (in this skill folder). It
   renders the per-version grading prompt(s) and the matching JSON schema, then
   writes two things under `./output`:
   - `<exam>_<id>_deliverables.zip` — every deliverable in the skill-source
     layout, for the TA to download.
   - `backend/data/<Exam Name>/prompts/prompt_<id>_<ver>.txt` and
     `.../schemas/schema_<id>.json` — prompt and schema files in the pipeline
     layout.

   The TA's edits live in artifacts/canvas, not on disk — so first **write the
   edited content to working files**, then point the script at them. Any input
   left unspecified falls back to the shipped stub, so only override what the TA
   actually changed. `groups` has no shipped stub, so `--groups` is always
   required:

   ```
   python3 generate_grading_prompt.py <exam-slug> <question-id> \
       --criteria ./work/criteria_<id>.yaml \
       --few-shot ./work/few-shot_<id>.yaml \
       --groups   ./work/groups_<id>.yaml \
       --out ./output
   ```
 
   Pass `--stdout` to preview the rendered prompt and schema without writing
   files, and `--question-dir` / `--solution-dir` if the TA edited the question
   or model answer. The schema follows the fixed JSON shape: `comment`, top-level
   `uncertain`, `comment_uncertainty`, and a nested `criteria` object keyed by
   criterion id. Show the TA the final prompt and schema for review.

6. **Hand the zip to the TA.** Give the TA `output/<exam>_<id>_deliverables.zip`
   to download. This single zip holds every deliverable in the correct folder
   structure — the TA downloads that one file and unzips it directly. Deliverables
   in the zip:
   - `merged/<exam>/<id>/merged_<id>_V*.txt` — The question and the solution.
   - `criteria/<exam>/criteria_<id>.yaml` — The edited grading criteria.
   - `few-shot/<exam>/few-shot_<id>.yaml` — The edited few-shot examples.
   - `groups/<exam>/groups_<id>.yaml` — The groups authored together.
   - `schemas/<exam>/schema_<id>.json` — The final JSON schema with top-level `uncertain` and nested `criteria`.
   - `prompts/<exam>/<id>/prompt_<id>_V*.txt` — The final grading prompts.