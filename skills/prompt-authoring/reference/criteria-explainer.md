**How grading works here — two pieces: criteria, then groups.**

**Criteria** — a numbered list of simple yes/no checks about a student's
answer ("did they state the correct interval midpoint?", "did they use the right
units?").

- The LLM grader answers each one true or false for every submission.
- Keep them small and single-fact — one idea per check.
- Write them so they work for every version of the question (refer to "this
  version's answer", never a hard number).
- It's fine, and encouraged, to check the same thing more than once: when
  redundant checks disagree, this way we check that the LLM is consistent.

**Groups** — turn those true/false answers into an actual group.

- We create groups based on the answers of the questions
- A rule with AND/OR/NOT logical operators are supported. You will explain this to the LLM in a freeform and they will create the rule for you
- It might be a good idea to flag the LLM if some combinations of answers create a contradiction. So that they account for that in rules.

**You may simplify if you'd like**: Use only a few rules (no more than 3) and do not provide any groups. Then you will recieve 2^(number of rules) groups as before.