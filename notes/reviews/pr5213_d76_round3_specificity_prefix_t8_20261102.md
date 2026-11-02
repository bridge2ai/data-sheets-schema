# D76-R3-T8 — specificity derivation rejects the input precondition

Status: OPEN. Regression tests are prepared; scanner repair and final validation
are pending. This is an offline local issue draft for PR #5213, 2026-11-02.

At candidate `fc055cc5742d99cee34017f7571e73de5ed0a4a5`, ordinary shard 5
reported 3,997 passing, 7 failing, 21 errored and 2 skipped tests. All 28 failures
and errors in `tests/test_generation_specificity_skill.py` report the selected
prompt-adaptation derivation error: the base prompt does not enter an unchanged
body. Fresh unchanged selections of those 28 tests pass at both original
`0fa106e4d558c1c119e8f386222e225ac3acca24` and cached main
`87a8e7a80a8c215335ede4774e07193940f155fb` under the same validation harness.
These baseline results establish an integration regression, not a passing final
candidate or a disposition of unrelated failures.

The scanner at `scan.py:14115` requires the first statement of `resolve_prompt`
to be `body = prompt_body(spec.base_prompt)`. The round-3 execution-boundary
repair adds `_require_registered_input_spellings(spec)` first at
`api_runner.py:1484`. That check must remain before prompt-file reads and
authority checks. The scanner itself is unchanged across the compared heads.

The proposed repair derives an observational precondition from its actual source
closure before applying the existing exact body/adaptation proof. It must refuse
unsupported call/control shapes, mutations through borrowed aliases, global or
attribute/item writes, unknown/dynamic calls, rebinding/decorators, opaque I/O,
replacement results and unproven callable registry values. A weak reference is
recognized only from its import and registry construction/writes, never from a
validator name or annotation alone. Fresh local containers may be built without
changing the prompt or spec. The scanner does not execute production helpers.

`tests/test_wave7_5213_d76_specificity_prefix.py` covers the real source closure,
renamed equivalent functions, simple observational guards, fresh local lists,
hostile closure changes and preservation of the existing adapter constraints.
Positive fixtures are intended before-repair regressions; refusal controls can already
pass on the old scanner. Exact before/after counts, source SHAs and artifact
digests will be recorded after the validation owner runs the frozen tests.
