# Assignment to AGY1: the open ratification items of native amendment N1, as data

From the Claude lead, 2026-11-12. Read-only.

## Why

The owner directed on 2026-11-12 (D134): the native agentic arm is the main result. Before the first native canary the owner has to ratify amendment N1 (PR 5542, head `754fbfdae10dbe9fe3f4443725cf0fa2a696b49e`, file `notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`). The lead wants to bring the owner one short page: each item still open, with a recommendation.

## What I need

Read the amendment with `git show 754fbfdae10dbe9fe3f4443725cf0fa2a696b49e:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` in the primary repository's object store (fetch the branch `agy/native-amendment-n1-20261108` if the commit is missing). Do not check anything out.

1. Every lettered ratification item in the amendment's closing list (the list that includes "(o) Freshness" and "(u) Freshness margin"): its letter, its full text, and its line number.
2. For each item: whether the amendment marks the matching clause `[proposed]` anywhere in the body (give the line numbers), and every owner decision number (`D` followed by digits) the item's text or its matching clause names.
3. For each decision number named: whether `data-sheets-schema/notes/coordination/STATUS.md` has a heading or bullet that records it as decided by the owner (give the STATUS line number), found with `grep -n`.
4. Every line of the amendment that contains `[proposed]`, with its line number and the first 200 characters.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `scripts/adhoc/n1_ratification_items_20261112.py`: does the extraction and writes the JSON. Header comment with purpose, inputs, outputs, date.
- `notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.json`
- `notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.md`: the tables printed by the script from the JSON, the command, and the counts (items, items with a `[proposed]` clause, items naming a recorded decision, items naming none). No row written by hand, no recommendation of your own.

## Rules

- No edit of the amendment, no GitHub write, no commit or push, no checkout in any existing worktree, nothing in `d4d-executions/launch-a21`.
- Quote text exactly as the script extracted it. Every path in backticks must exist.
- No at-sign characters.
- Stop when the three files are written. Print their paths and SHA-256.
