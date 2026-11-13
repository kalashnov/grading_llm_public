# Grading exams with LLMs

Here I publish my LLM pipeline for grading handwritten exam answers on [Gradescope](https://www.gradescope.com).

The repo includes: 1) the grading pipeline, 2) a helper LLM skill for writing the rubric, and
3) a Chrome extension that displays the transcription of students' handwriting in Gradescope.

The grading is designed to handle free response answer questions, those could include math and/or plots. It is designed as a helper for the TA grader.

This is an ad hoc pipeline I made for myself, and making it easy for other people to use would take some extra work on my side.
Instead, I am publishing it (almost) as is, with low-effort, LLM-assisted instructions below.
I suggest using it as a source of ideas. If you want to use it, I would suggest to use Claude Opus to navigate through these instructions, and perform all of the steps. Expect to put some time into it: it is only worth it for large courses (>200 students).

Having said that, even the first low effort step "OCR" + chrome extension helps with grading a lot.

There are some parts requiring an update. The pipeline is using older versions of models. Now the new cheaper and better models are released, so you might want to update this part.
The script also handles scheduling around quotas that were active for individual users for OpenAI API in May 2026, which results in it running for some time (a few hours for a ~400 students course). Modern models are faster, so some of these scheduling parts are not needed anymore.



## Pipeline overview

The whole idea is to ask LLM a few question about the student's response and then group the answers using Gradescope groups.
After that, a TA is reviewing those groups. We found that the groups labeled as "correct" or "wrong" require almost no review.
The partial points are subject to some judgement call, and we disagree with the model more often.

Here are the stages of the grading process with LLM we do.

| Stage | Script(s) | What happens |
|---|---|---|
| Fetch | `fetch_submissions.py` | Reads a saved Gradescope *answer groups* page and downloads one image crop per student answer. |
| OCR | `ocr_gvision.py`, `ocr_cleanup.py` | Google Vision transcribes the handwriting. GPT-4o then compares that text with the image and fixes dropped decimals, garbled math and crossed-out work. |
| Rubric | `generate_criteria.py`, `skills/prompt-authoring/` | Claude reads every answer to a question and drafts criteria plus 5 graded examples. A TA refines them in a chat with the skill and writes the group rules. `generate_grading_prompt.py` renders one prompt per exam version and a JSON schema. |
| Grade | `grade_all.py` | GPT-4o gets the prompt, the transcription and the low-detail image, and returns a JSON object: true/false per criterion, a comment, and an `uncertain` flag. It runs through the OpenAI Batch API (half price, resumable). |
| Group | `assign_groups.py` | Each answer gets the first group whose rule is true. |
| Post | `create_answer_groups.py`, `make_requests.py`, `post_grades.py` | Creates the groups in Gradescope and posts each answer into its group. |
| Review | Gradescope, optional Chrome extension | TAs check each group and apply a rubric item to it. The extension shows the OCR text next to each answer. |

Each question can have several versions (VA–VD). They share one set of criteria and
groups, but each version gets its own prompt with its own numbers and solution.
[`backend/data/Final/`](backend/data/Final/) contains three fully worked example questions (2.1, 3.3, 4.3)
with every rubric file and rendered prompt.


## Setup

Requires Python 3.10+, an OpenAI API key and a Gradescope instructor/TA account.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
export OPENAI_API_KEY=sk-...
export GRADESCOPE_SESSION_COOKIE='...'  # see below
```

Gradescope has no API, so the scripts act as you in the browser, using your login cookie:

1. Log in to gradescope.com in Chrome with an account that can grade the course, and open any course page.
2. Open DevTools (`⌥⌘I` / `Ctrl+Shift+I`) ▸ **Network**, then reload the page.
3. Click the first `gradescope.com` request (the page itself). Under **Headers ▸ Request Headers**,
   find `Cookie`, right-click it and choose *Copy value*. It's a long `name=value; name=value; …` string.
4. Paste it between the single quotes above.

The cookie gives full access to your account, so treat it like a password.

Set `COURSE_ID` in `backend/post_grades.py` to your Gradescope course ID.

## Part 1: Fetch and OCR

**Download submissions.** For each question version, open
`gradescope.com/courses/<course>/questions/<question_id>/answer_groups`, save the
page HTML as `backend/data/<Exam>/question_pages/<V>_<assignment_id>_q<q>_<question_id>.html`, then:

```bash
python backend/fetch_submissions.py "data/<Exam>"     # answer crops → data/<Exam>/submissions/
```

**OCR.** Google Vision first (`gcloud auth application-default login`), then a GPT cleanup pass that also sees the image:

```bash
python backend/ocr_gvision.py "backend/data/<Exam>/submissions"
python backend/ocr_cleanup.py "backend/data/<Exam>/submissions"
```

## Part 2: Rubric, grade, group

**The rubric format.** Each question has two YAML files. The criteria file lists
yes/no checks the model answers for every response, with examples of what does and
doesn't count. The groups file turns those answers into answer groups. See
[`criteria_2.1.yaml`](backend/data/Final/criteria/criteria_2.1.yaml) and
[`groups_2.1.yaml`](backend/data/Final/groups/groups_2.1.yaml) for an example.

**Prepare the rubric-writing skill.** The skill in `skills/prompt-authoring/`
walks a TA through writing the rubric for one question. Before that, it needs a
draft to start from, for every question:

```
skills/prompt-authoring/
  merged/<exam>/<q>/merged_<q>_<V>.md     question + official solution, per version
  criteria/<exam>/criteria_<q>.yaml       draft criteria
  few-shot/<exam>/few-shot_<q>.yaml       5 real-looking answers graded against them
```

1. *Questions and solutions.* Paste the exam PDF into an LLM with
   `generation-prompts/transcription-prompt.md`, and the solution key with
   `generation-prompts/solution-prompt.md`. Save the results as
   `skills/prompt-authoring/questions/<exam>/<q>/questions_<q>_<V>.txt` and
   `.../solutions/<exam>/<q>/solutions_<q>_<V>.txt`, then run
   `python backend/merge_questions_solutions.py` to produce `merged/`.
2. *Draft criteria and few-shot examples.* This step reads the OCR'd answers from
   Part 1. Each question gets a Claude session that sees the question and every
   student answer to it:
   ```bash
   pip install claude-agent-sdk   # uses your Claude Code login, no API key needed
   python backend/generate_criteria.py --exam <exam>            # all questions, or list ids: 2.1 3.4
   ```
   Without Claude Code, run `python backend/export_criteria_prompts.py --exam <exam>`
   and paste the rendered prompts into any chat model by hand.
3. *Install the skill.* Zip the folder so `prompt-authoring/SKILL.md` is inside the
   zip, then upload it in Claude (**Settings ▸ Capabilities ▸ Skills**). For
   Claude Code, copy the folder to `~/.claude/skills/` instead.
   ```bash
   cd skills && zip -r prompt-authoring.zip prompt-authoring -x '*/__pycache__/*'
   ```
   The draft files include student answer text, so share the zip only with your
   course staff.

**Write the rubric with the skill.** A TA starts a chat and asks it to write the grading
criteria. The skill asks which question, then goes through it with the TA. At the end it hands over
`<exam>_<q>_deliverables.zip`. Unzip it, then copy `criteria/`, `few-shot/`, `groups/`,
`schemas/` and `prompts/` into `backend/data/<Exam>/`, as in
[`backend/data/Final/`](backend/data/Final/).

**Render the prompts.** The skill builds the grading prompts with
`generate_grading_prompt.py`, and you can run it yourself after editing a rubric. To see
what it produces, try it on a shipped example:

```bash
python skills/prompt-authoring/generate_grading_prompt.py final 2.1 --stdout   # print the prompt + schema
python skills/prompt-authoring/generate_grading_prompt.py final 2.1 \
    --groups backend/data/Final/groups/groups_2.1.yaml --out ./output       # write files + deliverables zip
```

**Grade and group.** This uses the OpenAI Batch API. If it's interrupted, re-running re-attaches to batches already submitted.

```bash
python backend/grade_all.py     "backend/data/<Exam>/submissions"   # → *_graded.json
python backend/assign_groups.py "backend/data/<Exam>/submissions"   # adds "group" to each answer
```

## Part 3: Post and review

**Post the groups to Gradescope.**

```bash
python backend/create_answer_groups.py "backend/data/<Exam>" --dry-run   # then without --dry-run
# re-save the question_pages/*.html so they contain the new group IDs, then:
cd "backend/data/<Exam>" && python ../../make_requests.py                # → *_requests.json
python ../../post_grades.py "submissions/<file>_requests.json"           # once per file
```

Answers the model marked `uncertain` are not posted. They stay ungrouped for TAs to
grade by hand.

**Review in Gradescope.** TAs open each answer group, skim the answers in it, move
any misplaced ones, and apply a rubric item to the whole group. "Correct" and "wrong"
groups usually need little more than a skim. Partial-credit groups deserve a closer
look.

**Chrome extension (optional).** Gradescope shows only the scanned handwriting. The
extension in `chrome-extension/gradescope-ocr-overlay/` adds the cleaned OCR text from
Part 1, which is easier to skim:

- On an *answer group* page, it puts an OCR card next to every answer. The card's
  **Move to** menu moves that submission to another group.
- On a single submission's *grade* page, it shows the text in a floating panel that
  you can drag, collapse or copy from.

To set it up:

```bash
python chrome-extension/gradescope-ocr-overlay/scripts/build_ocr_index.py   # → data/ocr-index.json
```

The script reads `backend/data/Final/submissions/`. For another exam, change
`SUBMISSIONS_DIR` at the top of the script. Then open `chrome://extensions`, turn on
**Developer mode**, click **Load unpacked** and pick `chrome-extension/gradescope-ocr-overlay/`.
The OCR text is bundled into the extension, so rebuild it and click reload on the
extension whenever the OCR changes. Viewing is read-only; only **Move to** writes to
Gradescope.

## License

[MIT](LICENSE)
