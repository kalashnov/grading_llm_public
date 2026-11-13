# Criteria — EXAMPLES

Example criteria sections, one file per question. Each file is the
numbered criteria block of the rubric — the yes/no checks with ACCEPT/REJECT
examples — modeled on the existing Midterm 1 rubrics.

## Layout

```
criteria/<exam>/criteria_<id>.yaml   — one file per question
```

Each file is named with its type prefix and question id (e.g. `criteria_2.1.yaml`)
so it stays unambiguous as an artifact.

For now there is ONE criteria file per question, shared across all versions
(VA-VD), matching the design rule that criteria are version-independent. Where a
correct answer differs across versions (e.g. Midterm 2 question 1), the criteria
are phrased generically ("the midpoint of this version's interval") rather than
hard-coding a number. Per-version specialization can be added later.

## These are examples, not the actual criteria

They illustrate the structure and the kind of checks, not the final rubric the
course will use. The skill's criteria-drafting step refines or replaces them
with the TA.

Two patterns are intentional, not mistakes:

- **Decomposition** — a complex criterion is split into several small,
  single-fact boolean criteria, each easy for the grading model to judge.
- **Redundancy** — the same thing may be checked from more than one angle (e.g.
  the correct value, and separately the correct sign). Redundant criteria that
  agree raise confidence in the model's judgement; when they disagree, the group
  rules can route that submission to human review.

So some duplication across criteria is expected and welcome.

The number of numbered criteria in each file determines the schema field count.
