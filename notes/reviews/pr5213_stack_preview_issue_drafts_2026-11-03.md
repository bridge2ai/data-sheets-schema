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

Validation is pending until the corresponding unchanged tests pass on a clean
committed archive of the repair. The lead-ruling's protected sidecar rebind and
the integrated stack suite remain conditional on AGY's publication-readiness gate.
