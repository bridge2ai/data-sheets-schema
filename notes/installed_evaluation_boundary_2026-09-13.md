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

## CI correction round 4 — 2026-09-13

CI on the prior head passes 4,338 tests and finds #1599 and #1600. The
installed HTML renderer now uses the shared captured-schema view. Third-party
runtime library files retain absolute identities when the environment is
inside a checkout; package resources and corpus identities retain their
existing normalization. A new regression stages that runtime layout. The
symlink/parent-path fixture now creates its own two distinct parents instead
of assuming a developer virtualenv's parent contains pyproject.toml.

The source/schema/resource/legacy-render lane passes 39 tests, with only that
pre-existing fixture assumption failing; its replacement and the additional
renderer checks pass 11 tests. A fresh wheel passes all six workflow checks.
The boundary now pins 42 files, including the shared view and snapshot modules.
No scoring rules, source rubrics, evaluator definitions or measured artifacts
change in this correction.

## Combined dependency review — 2026-09-13

The branch now includes published profile/packaging head
805ff3eb01bc08ceef715e6c92e1fcf0122f0007. The integration preserves recorded
profile choices during replay and keeps current resource ownership alongside
the installed evaluation/rendering entry points. Its 965 profile, resource,
evaluation and reference-controller tests pass (one existing skip), and all
six fresh-wheel acceptance checks pass with declared runtime dependencies.
The read-only historical audit verifies all 56 accepted ratings and 450
preservation hashes. No new model call, generated record or rescore occurred.
The adjacent JSON refreshes the implementation pins for this combined tree.
An independent review and CI on the resulting head remain merge gates.

## Final profile and packaging integration — 2026-09-13

The branch includes profile head 4fb2949f6 and packaging head d770703b0.
The merge retains the installed renderer CSS, the exact Anthropic 0.72.0
runtime pin and declared httpx dependency, and both protections for resource
identity: one selected checkout and absolute third-party library paths.
Semantic scope keeps its direct resolver import; this installed workflow's
frozen controller already copies that resolver, while archived instruments
remain unchanged.

The combined profile/resource/classification/evaluation lane passes 870 tests
with one existing skip. All seven fresh-wheel workflows pass (89.05 seconds),
and all 42 frozen-controller/audit/validator-status checks pass. The preservation
audit verifies 56 accepted ratings, 259 prior evaluations and 450 file hashes.
The dependency lock check passes. These are implementation changes with no
new production model call, generation output, score or quoted definition.
The JSON pins the combined implementation for review and exact-head CI.

## Executable compatibility correction — 2026-09-13

Round-6 review found #1662: the executable legacy evaluator lost its Python
shebang when replaced by a compatibility wrapper. Direct subprocess execution
reproduced errno 8. The original shebangs are restored on all six affected
wrappers, retaining their existing modes. Direct evaluator --help succeeds,
and all seven legacy-renderer/evaluation CLI checks pass. Packaged scoring
implementation and instrument texts are unchanged.

## Profile and packaging review integration — 2026-09-13

The combined implementation includes profile 27b627fa2 and packaging 2a840076a.
The earlier installed-evaluation head 1a9a1a348 passed Codex round 7 and CI
34760898615. The subsequent resource/profile/evaluation integration passes
1050 checks (one existing skip), followed by 337 resource, review, receipt and
selection checks after the packaging corrections. The receipt assertion uses
the playbook's corrected American spelling. All seven fresh-wheel workflows
pass after that integration (93.31 seconds). The latest profile/backfill/resume
changes pass 157 checks. The dependency lock remains valid.

The parent-targeted PR #1692 carries the already reviewed runtime-path fix
into packaging so its sole CI failure can clear. This implementation keeps
source and installed evaluation entry points aligned, recorded instrument
attributions intact, and the existing measured archive unchanged. No new
production model call, generation output, score or definition quotation occurs.
The refreshed JSON describes the committed implementation for the next review
and exact-head CI.

## Review round 8 — 2026-09-13

Codex found #1694: the legacy validator batch script used the caller's
evaluation directory after delegation to the installed implementation. The
wrapper now supplies its own repository's evaluation directory for batch
invocations. Explicit `--file` paths retain caller ownership. Four actual
subprocess cases cover opposing valid/invalid corpora and explicit-file
selection; the focused validator and semantic-contract lane passes 38 tests.
Only the compatibility dispatch changes; recorded scores and instrument
definitions remain untouched. The JSON refreshes the two implementation pins.

## Review round 9 — 2026-09-13

Codex confirmed the corpus selection fix and found #1713: a legacy batch
audit could still read semantic schemas from the caller's checkout. The
wrapper now supplies both its repository's corpus and schema directory.
Two real subprocess cases reproduce acceptance under permissive caller
schemas before the fix; both rubrics now reject those malformed assessments.
The complete focused validator lane passes 40 tests. Explicit-file input
ownership and the installed interface remain covered. The other finding,
malformed prompt blocks in profile consistency checks, is tracked on the
profile parent as #1700 and still awaits integration.
