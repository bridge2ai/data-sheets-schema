# Structured issue taxonomy Figure 11

`report_semantic_taxonomy.py` renders a new SVG Figure 11 and joined CSV/JSON
sidecars from explicitly selected structured semantic ratings. It reads the
shared evaluator-declared category vocabulary and issue-to-item links; it does
not classify prose, score records, execute an evaluator, or revise historical
figures. The protected legacy Figure 11 reproduction script and its 56 selected
ratings remain unchanged.

Use the repository development environment, which already includes matplotlib:

```sh
PYTHONPATH=src poetry run python scripts/report_semantic_taxonomy.py \
  --selection /absolute/path/selection.json \
  --output-dir /absolute/path/new-figure-directory
```

The destination must not exist. This command is offline. A missing plotting
dependency is a refusal; it does not install anything.

## Explicit ordered selection

```json
{
  "kind": "semantic_taxonomy_figure_selection",
  "version": 1,
  "ratings": [
    {
      "rating": "ratings/example-semantic.json",
      "group": "caller-declared selection",
      "input": "records/example.yaml",
      "context": "contexts/example.yaml"
    },
    {
      "rating": "ratings/another-semantic.json",
      "group": "caller-declared selection"
    }
  ]
}
```

Paths resolve relative to the selection file. These are illustrative paths;
select the actual raw rating files and, when available, their exact input and
independent caller context. `input` and `context` are optional, but context
without input is refused. With input and no context, applicability predicates
are unknown, not copied from the evaluator's declarations. The example does
not imply that any particular recorded rating has a validated input binding.

Every array occurrence is retained, including repeated files and ratings with
zero issues. Counts use **selection occurrences**, not independently sampled
ratings. Group labels are caller declarations; the consumer does not discover
files or infer cohorts, generators, repetitions or scientific membership.
Unknown selection keys, duplicate JSON/YAML keys, YAML merges/cycles, nonfinite
values and malformed paths/documents refuse. Bounds are 256 occurrences, 24
distinct groups, 512 characters per group/evaluator label, 16 MiB per captured
file, 256 MiB total, 250,000 parsed nodes and depth 64. Exceeding a bound refuses;
no rows or text are truncated.

## What is checked

Only rubric10-semantic 3.0 and rubric20-semantic 3.0/4.0 are supported. Legacy
ratings refuse; use their existing reproduction workflows without rewriting
them. The trusted instrument selector chooses the exact schema, rubric, agent
definition and evidence-name authority. The consumer captures each resource and
checks the recorded definition, rubric and authority SHA256 values against it;
the captured schema validates the rating. It checks scope, arithmetic and
applicability, then uses the shared issue-link checker to reject unknown or
non-applicable item IDs and lowered issues with no below-maximum linked item.
It never treats a saved `passed` or acceptance field as proof.

Two explicitly displayed states remain distinct:

- **Declaration shape and links checked:** no authoritative input supplied.
  Applicability and scope are checked for internal consistency only; quotations,
  absences, counts, coverage and actual resource identities are not verified.
- **Input-bound mechanical checks passed:** exact captured input bytes and
  independent context match the rating's recorded identities. The existing
  evidence checker recomputes quotations, absences, counts and coverage. Errors
  refuse publication; warnings remain in JSON and the per-rating warning count.

Both states describe evaluator declarations. Neither establishes that cited
material supports a scientific inference, authenticates evaluator execution,
or constitutes human approval. A group's SVG label and aggregate CSV rows
show the number of input-bound and declaration-only occurrences separately.

## Groups, count units and artifacts

Groups are separated by caller label, rubric, version, all four selected
resource digests, declared evaluator identity/type and the full model declaration
digest. The evaluator key uses the existing `evaluator_model`, `model_id`, then
`name` precedence. A missing identity is explicitly unknown and gets its own
occurrence group. Different model declarations are never silently pooled.

The output contains:

- `fig11_semantic_taxonomy.svg`: category counts and high-severity lowered issue
  counts per group, including groups with zero issues.
- `ratings.csv`: every occurrence and validation state, including zero issues.
- `issues.csv`: one row per issue occurrence, with its declared category/type,
  severity, effect and JSON-encoded item list.
- `categories.csv`: every vocabulary category per group, including zero counts.
- `item_links.csv`: one row per issue-to-item link; one issue linked to two items
  contributes one issue and two links.
- `lowered.csv`: high-severity issues declared to lower scores, counted once per
  issue regardless of link count. High-severity `noted_only` issues do not count.
- `report.json`: complete payload, captured source/resource paths, raw SHA256 and
  byte counts, local file identities, warnings, group keys and artifact hashes.

CSV joins use the selection index, group ID and original issue index. Group IDs
follow first occurrence, and the report retains the full model declaration and
ordered selection. The SVG and all sidecars come from the same prepared payload.

## Capture and publication boundary

`prepare(selection_path)` captures bytes before parsing and returns an immutable
`PreparedFigure`. `publish(prepared, output_dir)` renders only that captured
payload. Shared validation still resolves its usual rubric/authority resources;
the consumer verifies their captured bytes and identities after validation and
again before publication. Rendering never reparses a selected live rating,
record or context. All inputs/resources are checked for drift before and after
rendering and before the final manifest. This is a local consistency check, not
a lock against arbitrary concurrent external writers.

Publication reserves a fresh directory, creates artifacts exclusively, verifies
their written bytes and writes `report.json` last. A complete report has
`state: complete`, a SHA256 for the canonical prepared payload and exact hashes
for every artifact. A directory without this complete manifest is a partial
failure and must not be used as a complete figure. Retain such a directory for
inspection and choose a different fresh destination; the tool does not clean or
replace it. Existing directories, symlinks, input aliases and overwrite attempts
refuse. Historical outputs and frozen registrations are never refreshed.

This implements the structured figure consumer for [#4333](https://github.com/bridge2ai/data-sheets-schema/issues/4333).
The parent [#2920](https://github.com/bridge2ai/data-sheets-schema/issues/2920)
remains subject to its full acceptance review; this guide does not declare it
closed or introduce a new scoring instrument.
