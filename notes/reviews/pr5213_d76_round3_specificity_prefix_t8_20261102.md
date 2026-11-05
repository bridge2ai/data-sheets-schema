# D76-R3-T8 — specificity derivation rejects the input precondition

Status: OPEN. The revised scanner repair is ready for independent review;
after-repair and full validation remain pending. This is an offline local issue
draft for PR #5213, 2026-11-02.

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
initialization, its sole writer and weakref cleanup, record constructors, capture,
both copy routes and every lookup consumer; alpha-renamed source roles preserve
function and comprehension scope boundaries. Dynamic field
rosters come from the capture's literal names and ordinary RunSpec declarations.
A smaller finite grammar admits primitive checks and fresh local containers.
It carries ownership through each finite iteration, with a shared 4,096-visit
statement/expression budget across helper calls and the whole prefix sequence.
Module binding checks include compound statements, imports and wildcard-import
refusal; callable/member aliases and outer-scope default captures cannot borrow
an obsolete definition's proof. Relevant class bodies, defaults, method
definition expressions and read protocols must have supported behavior.
Certified functions cannot escape through annotations. Plain class and standard
Path roles may use restricted type expressions; eager type annotations with
visible `__annotations__` attribute or literal-name access refuse. This includes
literal-key and `getattr` spellings, without claiming to analyze arbitrary
dynamic reflection or downstream runtime type-introspection consumers.
Supported postponed type expressions are treated as stored text rather than
eager class lookups; this preserves the existing runner's union annotations
without an identifier exception.
Imported defaults are followed in the supplied source root: the actual `AUTO`
binding resolves to `registry.py`'s plain `object()` sentinel, rather than being
trusted by its name or a path outside that root.
The scanner does not execute production helpers.

This certificate is explicitly bounded to source-declared primitive values,
standard paths/containers, plain dataclasses, non-reflective type annotations and
trusted standard-library semantics. It is not a universal runtime-purity assertion. In particular,
malformed/custom runtime values can overload truthiness or comparison, and
arbitrary hostile Python can mutate module state. Those cases are excluded in
the returned evidence. Visible descriptors, custom dispatch, mutations,
rebinding and unproved callable values in the inspected source remain refusals.
The runtime precondition and its order are unchanged.

`tests/test_wave7_5213_d76_specificity_prefix.py` covers the real source closure,
renamed equivalent functions, simple observational guards, fresh local lists,
hostile closure changes and preservation of the existing adapter constraints.
Positive fixtures are intended before-repair regressions; refusal controls can
already pass on the old scanner. The retained before results below distinguish
those roles. No after-repair outcome is claimed here.

The frozen 52-case before-run at
`6d84904369e89d3f4232d39408b2b90aa11b9954` completed with 46 passing refusal
controls and 6 intended positive failures in 7.677551 seconds, with strict source
and phase proofs valid and no fixture errors. Retained evidence is
`pr5213_d76_round3_2026-11-02/t8-before-6d849/`:

- `outcome.json`: `48afbde759da63185ea2dd76adc084acdb276125011c85c6360cbc556e106137`
- `pytest.xml`: `598521129383bc560330e107af38648cc2c6a5bebf126740aeb307b67e2b9925`
- Test source: `96478e9e774f2154529b36e9ab466dda19f30a2412d8ed068f0d574318a2eab4`

The first scanner draft, SHA-256
`b69a4333acdfd5adee5d09111b90cc36d8d3c9f025225d652fc65fa86dd3f08f`, passed
the original 52 cases but adversarial review found gaps documented in
[the R1–R7 review ledger](pr5213_d76_round3_specificity_prefix_review_20261102.md).
It is retained as a known-unapproved before state. After adding the real
`registry.py` fixture dependency without changing the original assertions, the
same draft's revised before cohorts were:

| Cohort | Frozen test SHA-256 | Result |
| --- | --- | --- |
| Base 52 | `9af3d57f6dc6bffbee76bab83fa2d80330507d126e884b33be7cbfe963f33aa7` | 52 passed |
| Review 22 | `cfd9fd371537a782c129849eee6512dc50528f55ae7cbf029521075833febe08` | 1 passed, 21 failed |
| Follow-up 9 | `b33defd477704e7edbeda813d096483f78ff76c6feac570ad332497d38ebabf7` | 9 failed |

The follow-up's six- and eight-case versions remain retained as historical
evidence. The final nine-case before run used committed source
`44b3dd8a1fdbb8bc22fa8691b84b2cc15a58a9d0`, still containing the known-unapproved
scanner draft, and completed in 6.327598 seconds. Its three additional controls
cover direct and stored callable annotation escapes plus an eager class
annotation whose metadata is used to install a descriptor.

Every unsuccessful review/follow-up case first calibrated its unchanged fixture,
then reached its intended missing-refusal assertion. None is a fixture or
calibration error. The finite-loop budget case is a deterministic contract
control, not a timing measurement or a claim that fixture code executed.
The review cohorts preserve separate occurrence counts and are not an overall
repository acceptance result. Retained outcome digests:

- `t8-revised-before-35719-review22/outcome.json`:
  `7689cc99712d23c7e51f4245478e17f6daea04b357dd284cb944b9f09fb034a1`
- `t8-followup9-before-44b3d/outcome.json`:
  `3081238103597286aa6565f9c6e9be7d4c05ea64f346b94379d8e84740cf7300`

The current repair draft has scanner SHA-256
`1c6b726abeb089f1508344b0feaf217949ed1c4b3c54383d09b5052abf862902`.
It adds certificate details to the selected-adaptation evidence while leaving
the existing adapter, policy, body and version proof intact. These remain
implementation claims awaiting independent source review and after-tests,
followed by the original specificity suite and required final-head coverage.
No runtime guard, protected production file, provider or GitHub action changed.
