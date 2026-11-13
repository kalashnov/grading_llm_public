Here is the problem that was given to the student:
```text
You have a dataset with information on course evaluations, course
characteristics, and professor characteristics for 462 courses at the
University of Texas, Austin. You want to analyze the determinants of teachers'
evaluations. In your initial specification, you regress course evaluations on
five regressors and obtain the following results:

  Linear regression                 Number of obs =     462
                                    F(5, 456)     =   21.52
                                    Prob > F      =  0.0000
                                    R-squared     =  0.1700
                                    Root MSE      =  .48566

               |              Robust
   course_eval | Coefficient  std. err.     t    P>|t|   [95% conf. interval]
  -------------+----------------------------------------------------------------
        beauty |  .1647695   .0308499    5.34   0.000    .104144     .225395
        female | -.2517388   .0471784   -5.34   0.000   -.3444528   -.1590247
      minority | -.1708324   .0643869   -2.65   0.008   -.2973642   -.0443006
     nnenglish | -.2175982   .0762312   -2.85   0.005   -.3674063   -.0677901
     onecredit |  .6022955   .121487     4.96   0.000    .3635517    .8410394
         _cons |  4.115747   .028349   145.18   0.000    4.060036    4.171458

where course_eval is a teaching evaluation score, from 1 (very unsatisfactory)
to 5 (excellent), and
- beauty is an average rating of the instructor's physical appearance by a
  panel of six students, shifted to have mean zero (beauty = 0 means average
  looks). In your sample, beauty ranges from -1.5 to +2.
- female is a binary variable that takes a value of 1 when the teacher is a
  woman,
- minority is a binary variable that takes a value of 1 when the teacher is NOT
  white,
- nnenglish is a binary variable that takes a value of 1 when the teacher is NOT
  a native English speaker, and
- onecredit is a binary variable that takes a value of 1 when the course is a
  single credit elective (such as yoga, dance, etc).

You introduce an interaction term min_fem = minority*female. The estimation
yields the following results:

  Linear regression                 Number of obs =     462
                                    F(6, 455)     =   21.38
                                    Prob > F      =  0.0000
                                    R-squared     =  0.1758
                                    Root MSE      =  .48447

               |              Robust
   course_eval | Coefficient  std. err.     t    P>|t|   [95% conf. interval]
  -------------+----------------------------------------------------------------
        beauty |  .1770669   .0322771    5.49   0.000    .1136362    .2404976
        female | -.2173182   .0530569   -4.10   0.000   -.3215853   -.1130511
      minority | -.0393463   .0854207   -0.46   0.645   -.2072144    .1285218
     nnenglish | -.2507944   .0719954   -3.48   0.001   -.3922791   -.1093098
     onecredit |  .5678335   .1208712    4.70   0.000    .3302984    .8053686
       min_fem | -.2469421   .1167427   -2.12   0.035   -.476364    -.0175203
         _cons |  4.103867   .0294904  139.16   0.000    4.045913    4.161821

Is there evidence, at the 5% significance level, that the difference in average
course evaluations between female and male instructors depends on minority
status? State the null and alternative hypotheses, compute the appropriate test
statistic, and state your conclusion.
```

SOLUTION:
```text
The min_fem coefficient tests whether the female-male difference depends on
minority status.

  H0: beta_min_fem = 0
  H1: beta_min_fem != 0

  t = -0.2469421 / 0.1167427 = -2.12

|t| = 2.12 > 1.96 (and p = 0.035 < 0.05), so reject H0. There is evidence at the
5% level that the difference in average course evaluations between female and
male instructors depends on minority status.
```
