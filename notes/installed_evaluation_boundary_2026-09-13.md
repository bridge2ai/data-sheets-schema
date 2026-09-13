# Installed evaluation and rendering boundary — 2026-09-13

This implements #1457 on the generation, evaluation, profile and packaging
branches. It makes the explicit-file workflow usable from the actual installed
wheel. It does not register or execute a new production generation or rescore.

The implementations of presence evaluation, direct API evaluation, semantic
output validation and HTML rendering now live under data_sheets_schema.
Former source/script paths remain compatibility entry points. Resource reads
resolve shipped rubrics and schemas; validation uses the current interpreter.
The reference-rescore controller pins and copies the validator implementation,
its package initializer and resource resolver into its isolated workspace.
The completed CBORG condition still uses its archived implementation.

The accompanying JSON records 39 source/resource hashes and the actual new
presence implementation digest. The source rubric bytes, four evaluator
definitions, API system-prompt digests, scoring domains and applicability
rules remain those of the preceding evaluation boundary. The earlier boundary
file is preserved and identified by its own hash. New source paths and resource
resolution are implementation changes and receive a separate boundary record.
No evaluator quoted a definition in a new runtime: that field remains null.

Both generation arms and every evaluation style remain in the completion plan.
This acceptance run exercises the API generation path with a fake provider,
deterministic core derivation and real validation, both presence rubrics, both
direct API rubric contracts with fake replies, both semantic-output contracts
and rejection of changed input digests, full/core HTML and both evaluation
renderers. The fresh environment installs only the wheel and declared runtime
dependencies. It has no checkout, pyproject.toml or study corpus. Six release
checks pass. All code-module origins are checked against the installed package.

The local combined evaluation/controller/CLI lane passes 859 tests before one
obsolete validator mock target is corrected; its five named-output checks
then pass. The original source-command entry point remains covered by the
real isolated rescore subprocess tests. The preservation audit verifies all
56 existing ratings and 450 preservation hashes, with no new model requests.

Remaining installed-agentic command/helper work is tracked in #1556 and
manifest-relative corpus roots in #1523. These must be resolved before claiming
both generation arms and corpus operations are independent of a checkout.

## Review round 2 — 2026-09-13

Independent review found #1569: compatibility batch commands printed root
CLI help instead of dispatching renders. The source compatibility scripts
now retain batch drivers; the YAML drivers discover their input files rather
than naming study datasets. Installed reusable modules remain unchanged.
All four actual source-command subprocesses produce HTML from isolated
synthetic fixtures. Their combined rendering/provenance/CLI lane passes
47 tests. The 39-file boundary updates the four compatibility entry-point
hashes; no scoring or generation instrument changes in this round.

## Review round 3 — 2026-09-13

Round 2 confirms #1569 and finds #1580: API results use an adjusted
max_points and a separate fixed_max_points, while the renderer interpreted
max_points as fixed. Reporting now reads both denominators explicitly.
The API acceptance gate annotates each item's fixed maximum from the trusted
contract. Renderers adapt these item maxima on a copy; earlier API outputs
can recover them only from the rubric bytes matching their recorded hash.
Stored scores and historical semantic interpretations remain unchanged.

Five regression cases fail on the preceding head. The corrected focused
rendering/API/semantic lane passes 57 tests. The broader evaluation/controller/
CLI/inventory lane passes 877 tests. A fresh wheel install passes all six
release checks with nonzero fake API ratings and real N/A exclusions in both
rubrics. This explicitly checks both displayed percentages; zeros alone did
not reveal the earlier denominator error. The boundary now pins 40 files.
No new real ratings, generation runs or downloads are performed.
