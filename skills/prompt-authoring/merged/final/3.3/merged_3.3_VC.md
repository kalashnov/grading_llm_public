Here is the problem that was given to the student:
```text
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

SOLUTION:
```text
Both coefficients are measured relative to the Humanities base, so the
STEM-vs-Business difference is

  beta_STEM - beta_Business = 12.4 - 7.8 = 4.6

STEM majors earn on average 4.6 thousand dollars more than business majors,
holding GPA constant.
```
