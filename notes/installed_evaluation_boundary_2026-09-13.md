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
