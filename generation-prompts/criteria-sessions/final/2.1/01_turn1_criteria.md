Here is one exam question (variant VA) and every real student answer to it.

QUESTION:
```
Economists are interested in the relationship between firm size – often
measured by annual sales – and spending in research and development (R&D).
Using data on US firms in the chemical industry, we regress rdintens, R&D
spending as a percent of sales, on sales (firm sales in billions of dollars)
and sales^2. The variable rdintens is measured in percentage points; for
example, rdintens = 9 means that R&D spending is 9% of the firm's sales. The
following estimated regression was obtained:

  rdintens_hat = 2.613 + 0.301*sales - 0.0070*sales^2
      standard errors:  intercept 0.324,  sales 0.131,  sales^2 0.0033
  R^2 = 0.148,  SER = 1.788

Is the marginal effect of firm size (measured by sales) on rdintens constant,
or does it change with firm size (sales)? Justify. Set up and perform the
necessary hypothesis test. Use a 5% significance level for the test.
```

STUDENT ANSWERS (N answers, one per student):
[real student answers removed from public repo]

Write the criteria for this question. Use the real answers above to design criteria with good coverage of the mistakes students actually make.

Respond with ONLY a JSON object of exactly this shape, and nothing else — no prose, no markdown fences:
{"criteria": [{"id": "<short snake_case name a human grader instantly understands, e.g. rejects_null or correct_interval_midpoint — lowercase letters, digits and underscores only, unique within this question>", "question": "<the yes/no check the grader answers>", "accept": ["<phrasing that gets credit>", ...], "reject": ["<phrasing/condition that does not get credit>", ...]}, ...]}