# PR #5213 stack preview: offline issue drafts

2026-11-03. These findings are recorded locally because this round forbids
GitHub writes. They have not been filed or closed on GitHub. Only the isolated
preview branch is being changed; publication remains with the lead and AGY.

## R5-I1: BC1 public RunSpec helpers lack the D76 caller contracts

The pinned preview merge `66145c56d4654051d0d593765bbfc3d40d63b213`
fails `test_every_public_runspec_boundary_has_an_explicit_contract` for
sixteen new helpers: eleven in `bc1_runtime`, three in `bc1_selection`,
`bc1_registration.plan` and `bc1_context.downstream_schema_context`.
Failing-first evidence is retained under
`d4d-executions/plans/reviews/pr5213_stack_preview_2026-11-03/resume-task3-before-merge1/focused-baseline/`.

Disposition: document each validated-caller precondition, preserving executable
behavior and the existing inventory. Caller review found no newly independent
execution entry among these helpers. Constructor/replay-only uses and the
checked project-only offline sizing projection need distinct preconditions;
they must not claim an execution admission that has not occurred.

## R5-I2: the closed RunSpec roster does not classify bounded_carry_version

The same pinned baseline fails
`test_all_runspec_registration_and_version_axes_have_a_binding_classification`:
the new dataclass field is absent from `RUNSPEC_FIELDS` and `REGISTRATION_AXES`.
The exact roster assertion must continue to reject future unreviewed fields.

Disposition: explicitly classify and exercise `bounded_carry_version=1` as a
mode/contract selector that does not independently pin inputs. BC1 requires
shared generation 1; its enclosing shared registration already supplies D76's
input binding. The `bounded_carry` block has exactly `version`, `fan_in` and
`contract`. Its nested contract contains protocol limits, implementation hashes,
ontology syntax and calibration provenance, including a historical provider URL,
but no selected bundle, source-manifest or chunk-manifest input locator. The
enclosing registration's `inputs` carry those locators. No roster discovery or
assertion is weakened.

R5-I1 and R5-I2 validation: a clean archive of
`76274b4467e9ba60e72736085c788c1fd957902f` passed the same 141 selected tests,
with no failures/errors/skips. Its selected-node list is byte-identical to the
baseline. The source inventory has 235 candidates with no unresolved contract.
The write canary separately persisted and verified its registration artifact.

## R5-I3: the approved BC1 hook invalidates the protected sidecar's old pins

All readiness checks passed for AGY head
`0ff5c9ba7665eb51b69e597c391cb1ae6a07c44c`. Conflict-free preview merge2
`5ee008a65f0f4abfb60cda8b13bdff91be6cbd18` incorporates its approved source
SHA-256 `94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d`.
The unchanged sidecar still binds `8c799066…`; the single inventory witness
fails for all twenty shared-generation contracts. Three function bodies changed
(`select`, `schema_context`, `plan`); the other seventeen fail only the whole
source pin. Failure evidence SHA-256:
`391b5a272b870a493d58944b76692ecc0fbf5e51f0dae47bde6a0bc40bb243b5`.

Disposition: apply the lead-authorized exact sidecar rebind, retaining all
twenty-one identities, their caller preconditions, strict function/source checks
and refusal of undeclared helpers. Recompute current line locations, preserve
the original approval/proposal provenance, and distinguish the old latch-module
snapshot metadata from its unchanged enforced function pin. Neither the checker
nor protected source may be edited. Results of the rebind and integrated stack
validation belong in the final external review report; this records the finding
and authorized repair before that validation.

## R5-I4: the BC1 scanner rejects the required initial caller docstring

The first full scan of the no-overlay archive at
`1222b8ce398c112fdd81cd9e58bdceef38c07144` exited 2 and produced no audit:
`BC1 selector domain or read-only enabled helper changed`. The log is retained
at `plans/reviews/pr5213_stack_preview_2026-11-03/scanner-final/scan.log`,
SHA-256 `0f643247148bc89566388ff7db1c399a38cfbf8e000f40d2c6c3fcd8777ec141`.
The scanner compares every statement in `bc1_selection.enabled` to an exact
three-statement body; the required initial caller-contract docstring adds a
fourth AST node. This interaction is introduced by the preview integration.

Disposition: recognize only one initial literal-string docstring, then retain
the exact executable-body, selector-domain and rebinding checks. Positive
docstring/no-docstring controls and negative extra-statement/expression controls
must demonstrate that the fix does not hide changed executable behavior. The
original scanner failure and unexecuted final-test plan remain preserved.

## R5-I5: the planned canary did not use the parallel cohorts' concurrency mode

Independent review of the unexecuted `1222b8ce3` final plan found `workers=0`
for its single-case canary and `workers=2` for the main cohorts. A successful
serial canary does not verify the xdist launch and evidence path used by those
cohorts. The earlier serial task3 canaries and their results remain literal
evidence; they are not recast as parallel canaries.

Disposition: keep exactly one real test case but use two workers through the
same launcher, sandbox, environment and external artifact path as the parallel
cohorts. Verify its persisted registration before releasing those cohorts.
The three SG2 trials and the outer CI-sharding controller remain serial;
the first SG2 trial must pass and its persisted result be verified before the
remaining two. Preserve the old unexecuted plan and create a fresh final plan.

The evidence helper checks exact expected node multiplicity against pytest
setup/call/teardown events. It reports JUnit testcase totals and statuses; it
does not claim a per-node JUnit identity join. Final acceptance separately
checks every return code, any skip/failure, and exactly one strict Issue H xfail.
