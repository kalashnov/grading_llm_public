# How grading groups work

Read this before defining groups for a question. It explains how the criteria a
TA authors actually bucket submissions into groups.

## The chain: criteria -> booleans -> group

1. **Criteria.** The TA authors a numbered list of yes/no criteria (see
   `house-format.md`).
3. **Groups.** A **group** is a bucket of submissions that all match the same
   **boolean rule** over the criteria — built from `AND`, `OR`, `NOT`.

The criteria are NOT the final categorization. They are the inputs to the group
logic. How many criteria to write, and which, is driven by which groups need to be
told apart.

## Boolean rules

A rule is an expression over the criterion numbers. For a 2-criterion question:

- `1 AND 2`         — both criteria met
- `1 AND NOT 2`     — criterion 1 met, criterion 2 not
- `NOT 1 AND NOT 2` — neither met
- `1 OR 2`          — at least one met

## Groups must not cover every case. The remaining will be ungrouped

## Example:

```
groups:
  - name: "Correct"
    rule: "((slope AND intercept) OR alternative_solution)"
  - name: "Slope only"
    rule: "slope AND NOT criteria_inconsistency"
  - name: "Intercept only"
    rule: "intercept AND NOT criteria_inconsistency"
  - name: "Inconsistently graded"
    rule: "criteria_inconsistency"
  - name: "wrong/empty"
    rule: (NOT slope) AND (NOT intercept) AND (NOT alternative_solution) and (NOT criteria_inconsistency)
```