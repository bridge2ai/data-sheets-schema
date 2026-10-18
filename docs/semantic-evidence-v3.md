# Semantic evidence contract v3

New rubric10-semantic and rubric20-semantic outputs use version `3.0`.
Historical semantic versions 1.x and 2.0 retain their classification rules;
field-agent rubric10 and rubric20 outputs still use version 2.0. No recorded
scores or frozen registrations are migrated by this change. A future run needs
a new registration with the v3 definition, validator support files and authority
artifact pinned before any evaluator call.

The exact-file validator requires the original input, caller-supplied context
(omission means unknown), current agent definition and their recorded digests.
After the existing shape, applicability, scope and arithmetic checks, it checks
the structured claims against that input. Each resource score has `cited`,
`absent`, `counts` and `considered` arrays. A deduction must name a path in at
least one of them. False counts, unresolved or empty citations, fabricated
quotes and false absences fail acceptance. Errors carry structured item,
resource and path findings. Coverage gaps and deductions without a linked issue
or explicit `no_issue_reason` are visible warnings; neither rewrites scores.

Issues record a category, type, score effect and unique item IDs. A `lowered`
issue must link to at least one applicable item below its maximum. A
`noted_only` issue has no item IDs. These are evaluator declarations, not a
mechanical adjudication of semantic correctness.

## Frozen absence-name authority

`data/rubric/semantic_evidence_authority_v3.json` freezes the union of declared
slot and class attribute names from the full and core merged schemas, dotted
field tokens from both rubrics, and names from the existing field-alias table.
The artifact records the SHA256 of each source. The evaluator records the
artifact's SHA256 as `metadata.evidence_authority_sha256`, and acceptance checks
that digest against the installed artifact. Isolated reference-rescore sessions
copy and pin both the artifact and its loader.

`scripts/build_semantic_evidence_authority.py` is an explicit offline release
tool. Acceptance never rebuilds the authority from whatever schema is current.
A changed authority needs a separately identified instrument and registration.

Release reproduction uses the hash-verified gzip source snapshots in
`tests/fixtures/semantic_evidence_authority_v3`, also recoverable from commit
`b36bb067641467b7e14bea42fa378ac06167d68f`. The builder reads aliases from those
source bytes as a literal mapping without executing them. Current schema,
rubric or alias maintenance must not regenerate the released v3 authority;
even a comment edit changes source hashes while leaving the names unchanged.
Historical v3 ratings continue to use the released authority digest.

This authority validates token names, not their complete class/range traversal.
It rejects undeclared names even after a missing parent. JSON-pointer tokens
are decoded literally: `/version_access.version_details` does not mean the
nested path `/version_access/version_details`. Numeric tokens are list indices
on observed lists; after a missing parent, class information is unknown and
canonical indices remain possible. Combinations of individually declared names
may still be inappropriate for a class; that remains outside this contract.

The acceptance fixture for a declared but absent field uses `errata` in the
pinned CM4AI v7 rep2 input. `was_generated_by` is not declared by these authority
sources and is rejected in v3; no provenance-only allowlist is added. Historical
v2 behavior is preserved.

## Reporting and structured Figure 11

`scripts/report_semantic_comparison.py` accepts repeated
`--evidence-input EVALUATION INPUT` and `--evidence-context EVALUATION CONTEXT`
arguments. It recomputes v3 findings from those explicit inputs and displays
errors and warnings beside the rating and input identity. Missing inputs are
reported as unchecked. Model-written acceptance flags are never used.

`data_sheets_schema.semantic_evidence_reporting` exposes structured findings
and directly recorded v3 taxonomy. Legacy prose remains explicitly unclassified
unless a caller supplies a legacy classifier. Report generation preserves its
input files.

`scripts/report_semantic_taxonomy.py` provides the standalone structured
Figure 11 consumer described in the [selection and publication guide](semantic-taxonomy-figure.md).
It accepts explicitly selected rubric10-semantic 3.0 and rubric20-semantic
3.0/4.0 ratings, counts declared categories and item links directly, and reports
high-severity issues declared to lower scores. Repeated selections and zero-issue
ratings remain visible; groups separate instruments and evaluators. Plot and
sidecars distinguish input-bound mechanical checks from declaration-only shape
and link checks. Neither state establishes semantic correctness.

The protected legacy Figure 11 reproduction, its prose coding, selected ratings
and historical outputs remain unchanged. The standalone consumer handles new
structured outputs without reinterpreting those legacy results. The complete
#2920 acceptance criteria receive a separate review; this guide does not declare
the parent issue closed or imply scientific adjudication.
