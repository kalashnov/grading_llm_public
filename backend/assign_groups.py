"""Assign a rubric "group" (bucket) to each graded answer.

A groups file (YAML) defines an ordered list of buckets, each with a boolean
``rule`` over the per-answer criteria booleans produced by grade_all.py, e.g.

    groups:
      - name: "All correct"
        rule: "ovb_framework_stated AND teachers_cond1_reasoned"
      - name: "Wrong / blank"
        rule: "NOT teachers_cond1_reasoned AND NOT studying_cond1_reasoned"

Each answer is assigned the FIRST group whose rule evaluates true (groups are
ordered from most to least credit). The assigned name is written back into the
graded JSON under a top-level ``group`` key per answer.

Usage:
    python assign_groups.py <graded_file_or_submissions_dir> [--groups <path>]
                            [--dry-run]

If --groups is omitted, the groups file is auto-located at
``<midterm>/groups/groups_<question>.yaml`` (sibling of submissions/).
"""

import argparse
import ast
import json
import os
import re
import sys

import yaml

GRADED_SUFFIX = "_graded.json"

# Operator words in rules -> Python boolean operators.
_OP_WORDS = {"AND": "and", "OR": "or", "NOT": "not"}


def parse_graded_filename(path):
    """Return (version, question) from a *_graded.json filename."""
    name = os.path.basename(path)
    match = re.match(r"^(V[A-Z])_\d+_q([\d.]+)_\d+" + re.escape(GRADED_SUFFIX) + r"$", name)
    if not match:
        raise ValueError(f"Unexpected graded filename format: {name}")
    return match.group(1), match.group(2)


def groups_path_for(graded_path, question):
    """Auto-locate the groups YAML: <midterm>/groups/groups_<question>.yaml."""
    submissions_dir = os.path.dirname(os.path.abspath(graded_path))
    midterm_dir = os.path.dirname(submissions_dir)
    return os.path.join(midterm_dir, "groups", f"groups_{question}.yaml")


def _ruletext_to_python(rule):
    """Turn a rule string into a Python boolean expression.

    Replaces the AND/OR/NOT keywords (whole words only) and collapses the
    folded-YAML whitespace; criterion names are already valid identifiers.
    """
    expr = " ".join(rule.split())
    for word, py in _OP_WORDS.items():
        expr = re.sub(rf"\b{word}\b", py, expr)
    return expr


def eval_rule(expr, env):
    """Safely evaluate a boolean expression of names against ``env``.

    Only boolean operators, NOT, names and literals are allowed — anything
    else (calls, attributes, comparisons) raises, so an untrusted rule cannot
    do more than combine the criteria flags.
    """
    tree = ast.parse(expr, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.BoolOp):
            vals = [ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise KeyError(node.id)
            return bool(env[node.id])
        if isinstance(node, ast.Constant):
            return bool(node.value)
        raise ValueError(f"Unsupported element in rule: {ast.dump(node)}")

    return ev(tree)


def load_groups(groups_path):
    """Load and pre-compile the ordered groups from a YAML file."""
    with open(groups_path) as f:
        spec = yaml.safe_load(f)
    groups = []
    for g in spec.get("groups", []):
        name = g["name"]
        rule = g["rule"]
        groups.append({"name": name, "expr": _ruletext_to_python(rule)})
    if not groups:
        raise ValueError(f"No groups defined in {groups_path}")
    return groups


def classify(criteria, groups, groups_path):
    """Return the name of the first group whose rule matches ``criteria``."""
    for g in groups:
        try:
            if eval_rule(g["expr"], criteria):
                return g["name"]
        except KeyError as e:
            raise KeyError(
                f"Rule for group '{g['name']}' in {os.path.basename(groups_path)} "
                f"references unknown criterion {e}. "
                f"Available: {sorted(criteria)}"
            )
    return None  # no bucket matched


def assign_file(graded_path, groups_path=None, dry_run=False):
    version, question = parse_graded_filename(graded_path)
    if groups_path is None:
        groups_path = groups_path_for(graded_path, question)

    auto_group = not os.path.exists(groups_path)
    groups = None if auto_group else load_groups(groups_path)

    with open(graded_path) as f:
        data = json.load(f)

    counts = {}
    ungraded = unmatched = 0
    for record in data.values():
        gp = record.get("grade_parsed")
        if not gp or not isinstance(gp.get("criteria"), dict):
            record["group"] = None
            ungraded += 1
            continue
        if auto_group:
            met = [k for k, v in gp["criteria"].items() if v]
            group = "+".join(sorted(met)) if met else "blank/wrong"
        else:
            group = classify(gp["criteria"], groups, groups_path)
        record["group"] = group
        if group is None:
            unmatched += 1
        counts[group] = counts.get(group, 0) + 1

    if not dry_run:
        with open(graded_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    total = len(data)
    label = "<auto: met-criteria concat>" if auto_group else os.path.basename(groups_path)
    print(f"{os.path.basename(graded_path)}  ({total} answers, groups: {label})")
    if auto_group:
        for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"   {n:4d}  {n/total*100:5.1f}%  {name}")
    else:
        for g in groups:  # report in rubric order
            n = counts.get(g["name"], 0)
            print(f"   {n:4d}  {n/total*100:5.1f}%  {g['name']}")
    if unmatched:
        print(f"   {unmatched:4d}  {unmatched/total*100:5.1f}%  <no bucket matched>")
    if ungraded:
        print(f"   {ungraded:4d}  {ungraded/total*100:5.1f}%  <no grade — skipped>")
    if dry_run:
        print("   (dry-run: graded file not modified)")
    print()
    return counts


def main():
    ap = argparse.ArgumentParser(description="Assign rubric groups to graded answers.")
    ap.add_argument("target", help="A *_graded.json file or a submissions directory.")
    ap.add_argument("--groups", help="Path to a groups YAML (default: auto-locate per question).")
    ap.add_argument("--dry-run", action="store_true", help="Compute and print but do not write.")
    args = ap.parse_args()

    if os.path.isfile(args.target):
        targets = [args.target]
    elif os.path.isdir(args.target):
        targets = sorted(
            os.path.join(args.target, name)
            for name in os.listdir(args.target)
            if name.endswith(GRADED_SUFFIX)
        )
        if not targets:
            print(f"No {GRADED_SUFFIX} files in {args.target}")
            sys.exit(1)
    else:
        print(f"Not a file or directory: {args.target}")
        sys.exit(1)

    for path in targets:
        assign_file(path, groups_path=args.groups, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
