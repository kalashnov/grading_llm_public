# Generation prompts

Reusable prompts for (re)generating the contents shipped with the
`skills/prompt-authoring/` skill. Each prompt is self-contained: paste it into an
LLM together with the required input and follow it.

Run them in order — each step uses the output of the previous one.

| Step | Prompt | Produces |
|------|--------|----------|
| 1 | `transcription-prompt.md` | `skills/prompt-authoring/questions/<exam>/<id>/questions_<id>_V*.txt` |
| 2 | `solution-prompt.md` | `skills/prompt-authoring/solutions/<exam>/<id>/solutions_<id>_V*.txt` |
| 3 | `criteria-prompt.md` | `skills/prompt-authoring/criteria/<exam>/criteria_<id>.yaml` and `skills/prompt-authoring/few-shot/<exam>/few-shot_<id>.yaml` |
| 4 | `skills/prompt-authoring/generate_grading_prompt.py` | `backend/data/<exam>/prompts/prompt_<question-id>_V*.txt` and `backend/data/<exam>/schemas/schema_<question-id>.json` |

`<exam>` is a slug like `midterm-2`. `<id>` is a question id like `2.3`. Every
file is prefixed with its type (`questions_`, `solutions_`, `criteria_`,
`few-shot_`, `prompt_`, `schema_`) so it stays unambiguous when shown as an
artifact in the authoring skill.

`criteria-prompt.md` is also read directly by
`code/python/backend/generate_criteria.py`, which generates the criteria
(and matching few-shot examples) from real student answers via the Claude API.

`skills/prompt-authoring/generate_grading_prompt.py` is the final assembly step:
it combines the question, reference answer, grading philosophy, criteria,
few-shot examples, and the nested-criteria schema into the exact prompt the
grading model receives.
