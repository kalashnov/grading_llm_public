Now produce 5 example student answers, each graded against the criteria you just wrote. The 5 examples must be DIVERSE and REPRESENTATIVE: together they should cover the most common mistakes students actually make on this question — judged from the real student answers above — alongside a fully correct answer. Span the range from a perfect answer through partial-credit / edge cases to clearly failing ones.

Grade every example against every criterion, and use the exact snake_case `criterion_id` values from the criteria you just wrote.

Respond with ONLY a JSON object of exactly this shape, and nothing else — no prose, no markdown fences:
{"examples": [{"label": "<short tag, e.g. full credit / no credit>", "answer": "<transcribed student answer text>", "grading": [{"criterion_id": "<the snake_case id of the criterion being graded>", "met": <true|false>}, ...]}, ...]}