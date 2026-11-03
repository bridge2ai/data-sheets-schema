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
nor protected source may be edited. Validation remains pending for this rebind
and the integrated stack.
