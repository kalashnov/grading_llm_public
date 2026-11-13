Here is one exam question (variant VA) and every real student answer to it.

QUESTION:
```
A labor economist studies annual earnings of recent college graduates. The
following model is estimated:

  Earnings = beta_0 + beta_1*GPA + beta_2*STEM + beta_3*Business
             + beta_4*SocialSci + u

where
  Earnings  = annual earnings (in thousands of dollars)
  GPA       = college GPA
  STEM      = binary variable that equals 1 if STEM major, 0 otherwise
  Business  = binary variable that equals 1 if Business major, 0 otherwise
  SocialSci = binary variable that equals 1 if Social Science major, 0 otherwise

Humanities majors are omitted from the regression. Assume that these four
majors are mutually exclusive and collectively exhaustive. In other words,
assume that college graduates must have one and only one of these four majors.

The estimated equation is:

  Earnings_hat = 22.5 + 8.1*GPA + 12.4*STEM + 7.8*Business + 3.2*SocialSci
      standard errors:  intercept 4.0,  GPA 1.5,  STEM 3.1,  Business 2.8,
      SocialSci 2.6

(In brackets are the appropriate standard errors.)

What is the estimated difference in average earnings between a STEM and a
business major? Show your work.
```

STUDENT ANSWERS (N answers, one per student):
[real student answers removed from public repo]

Write the criteria for this question. Use the real answers above to design criteria with good coverage of the mistakes students actually make.

Respond with ONLY a JSON object of exactly this shape, and nothing else — no prose, no markdown fences:
{"criteria": [{"id": "<short snake_case name a human grader instantly understands, e.g. rejects_null or correct_interval_midpoint — lowercase letters, digits and underscores only, unique within this question>", "question": "<the yes/no check the grader answers>", "accept": ["<phrasing that gets credit>", ...], "reject": ["<phrasing/condition that does not get credit>", ...]}, ...]}