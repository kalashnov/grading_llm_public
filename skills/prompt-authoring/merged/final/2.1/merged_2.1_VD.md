Here is the problem that was given to the student:
```text
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

SOLUTION:
```text
The marginal effect is not constant; it changes with firm size because of the
quadratic term:

  d(rdintens)/d(sales) = 0.301 - 2*(0.0070)*sales = 0.301 - 0.014*sales

This depends on sales, so the relationship is nonlinear. Test the quadratic
coefficient:

  H0: beta_2 = 0   (marginal effect is constant / linear)
  H1: beta_2 != 0  (marginal effect changes with sales)

  t = -0.0070 / 0.0033 = -2.12

|t| = 2.12 > 1.96 (5% two-sided critical value), so reject H0. The coefficient on
sales^2 is statistically significant: the marginal effect of sales on rdintens is
not constant.
```
