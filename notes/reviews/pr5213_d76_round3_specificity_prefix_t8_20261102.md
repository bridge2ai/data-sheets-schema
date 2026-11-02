# D76-R3-T8 — specificity derivation rejects the input precondition

Status: OPEN. The scanner repair is drafted for independent review; after-repair
and final validation are pending. This is an offline local issue draft for PR
#5213, 2026-11-02.

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

The repair derives a **source-domain precondition certificate** from its actual
closure before applying the existing exact body/adaptation proof. It refuses
unsupported call/control shapes, mutations through borrowed aliases, global or
attribute/item writes, unknown/dynamic calls, rebinding/decorators, opaque I/O,
replacement results and unproven callable registry values. A weak reference is
recognized only from its import and registry construction/writes, never from a
validator name or annotation alone. A closed structural grammar checks registry
initialization, its sole writer and weakref cleanup, record constructors, capture
and both copy routes; alpha-renamed source roles are supported. Dynamic field
rosters come from the capture's literal names and ordinary RunSpec declarations.
A smaller finite grammar admits primitive checks and fresh local containers.
The scanner does not execute production helpers.

This certificate is explicitly bounded to source-declared primitive values,
standard paths/containers, plain dataclasses and trusted standard-library
semantics. It is not a universal runtime-purity assertion. In particular,
malformed/custom runtime values can overload truthiness or comparison, and
arbitrary hostile Python can mutate module state. Those cases are excluded in
the returned evidence. Visible descriptors, custom dispatch, mutations,
rebinding and unproved callable values in the inspected source remain refusals.
The runtime precondition and its order are unchanged.

`tests/test_wave7_5213_d76_specificity_prefix.py` covers the real source closure,
renamed equivalent functions, simple observational guards, fresh local lists,
hostile closure changes and preservation of the existing adapter constraints.
Positive fixtures are intended before-repair regressions; refusal controls can already
pass on the old scanner. Exact before/after counts, source SHAs and artifact
digests will be recorded after the validation owner runs the frozen tests.

The frozen 52-case before-run at
`6d84904369e89d3f4232d39408b2b90aa11b9954` completed with 46 passing refusal
controls and 6 intended positive failures in 7.677551 seconds, with strict source
and phase proofs valid and no fixture errors. Retained evidence is
`pr5213_d76_round3_2026-11-02/t8-before-6d849/`:

- `outcome.json`: `48afbde759da63185ea2dd76adc084acdb276125011c85c6360cbc556e106137`
- `pytest.xml`: `598521129383bc560330e107af38648cc2c6a5bebf126740aeb307b67e2b9925`
- Test source: `96478e9e774f2154529b36e9ab466dda19f30a2412d8ed068f0d574318a2eab4`

The draft adds certificate details to the selected-adaptation evidence while
leaving the existing adapter, policy, body and version proof intact. These are
implementation claims awaiting independent source review and after-tests, not a
passing acceptance result.
