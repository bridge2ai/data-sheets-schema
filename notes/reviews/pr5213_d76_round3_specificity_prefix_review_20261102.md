# D76 T8 source-certificate review: R1–R7

Offline issue drafts for PR #5213 and AGY publication, 2026-11-02. No GitHub
issues have been created. Findings below refer to scanner draft SHA-256
`b69a4333acdfd5adee5d09111b90cc36d8d3c9f025225d652fc65fa86dd3f08f`.
Status: static adversarial review; supplemental regressions prepared; runtime
reproduction and repairs pending. Do not close these from this document alone.

The bounded certificate explicitly assumes primitive/standard-Path fields,
ordinary dataclasses and trusted standard-library semantics. These findings
concern visible source bindings or behavior inside that scope, not arbitrary
hostile Python outside the inspected source.

## R1 — finite-loop analysis loses ownership after the first iteration

Priority: high; must address. `simple()` analyzes a finite loop body only once.
A fresh list may be appended to, then rebound to a declared borrowed list field;
the second actual iteration mutates the borrowed list. The supplemental fixture
uses a valid `inputs: list` field, avoiding an unrelated invalid dict method.
Require stable ownership across iterations or bounded abstract unrolling.

## R2 — keyword-only and variadic resolver parameters shadow the source callee

Priority: high; must address. `certify()` checks positional resolver arguments
but omits keyword-only, vararg and kwargs bindings. A keyword-only callable can
therefore replace the analyzed top-level helper. Variadic bindings are additional
refusal controls: their tuple/dict values are not certified callables, and must
not borrow a same-named global function's proof.

## R3 — callable and class aliases can invalidate the analyzed definition

Priority: high; must address. `unique()` checks Name stores but misses visible
callable attribute mutation such as replacing a helper's `__code__`, including
through an alias or a receiving helper. An imported predicate member can also
escape to an alias whose `__code__` is replaced by a function that mutates the
selection dictionary. The old pure AST is then no longer the callee's behavior.
Class aliases can similarly install field descriptors beyond
the direct `RunSpec.field` check. A module-alias `os.fspath` replacement control
is included; an already-conservative refusal of that control is not a newly
reproduced hole. Close the relevant explicit mutation and escape paths.

## R4 — literal field rosters and standard path roles have unexamined writers

Priority: high; must address. `global_value()` considers only direct module-body
assignments and explicit `global` declarations. Compound-statement assignments
and imports can replace a roster after its accepted literal initialization.
The roster substitutions select the existing `RunSpec.base_prompt` property,
rather than an ordinary declared field; no nonexistent attribute is needed.
The standard path-type role can also be replaced or have `__fspath__` changed
while the certificate continues citing the original declaration. The tests use
a real adjacent source module for import rebinding, and valid path subclasses.
Verify all source bindings and visible member mutation of these trusted roles.

## R5 — field annotations and frozen dataclasses do not rule out descriptors

Priority: high; must address. `record_fields()` misses descriptor-valued field
defaults, later class assignments and behavior-bearing class expressions.
It also permits a custom `__dict__` descriptor although the certified predicate
uses `vars(spec)`. A frozen record may acquire custom dispatch through a class
expression. The descriptor fixture raises `AttributeError` for class access,
so dataclasses treats it as a required field; no invalid default-ordering trick
is used. Validate class-body/default behavior and every relevant read protocol.
An additional control imports such a descriptor-valued default from an adjacent
source module. Imported defaults require source resolution too; recognizing a
default's identifier or import statement alone does not prove it inert.

## R6 — the registry lookup result can escape its supposedly closed writers

Priority: high; must address. Direct registry-name references are closed, but an
extra caller can obtain the record through the approved lookup and mutate it
using `object.__setattr__`, without naming the registry. The record is therefore
not protected by checking only the writer and raw dictionary accesses. Prove
the lookup caller/consumer closure as well as construction and copy paths.

## R7 — alpha normalization conflates nested and captured bindings

Priority: medium; must address certificate correctness. Every nested function
reuses `_local_0`, `_local_1`, and so on. Replacing weakref-cleanup comparison
`saved[0] is reference` with `saved[0] is spec` gives the same normalized name for
the inner parameter and captured outer spec. They are not alpha-equivalent:
the altered closure retains the spec and no longer performs the intended
identity-checked cleanup. Use lexical scope-qualified identities; preserve
comprehension/captured-variable boundaries too.

## Supplemental evidence contract

`tests/test_wave7_5213_d76_specificity_prefix_review.py` now defines 22 source-only
cases covering these seven families. The initial frozen 52-case module's
assertions and case roster are unchanged; its `_real_fixture` now also copies
`src/data_sheets_schema/registry.py` so the real `AUTO` default can be resolved
from source rather than trusted by identifier. This is a fixture-dependency
change with a new file hash, not a claim that the previous frozen bytes changed.
The original 52- and 21-case versions and their retained outcomes remain
historical evidence; the revised 52+22 fixtures require a new before run against
the unchanged scanner draft. Every mutation first derives the unchanged fixture and compares its
adapted output with the established no-prefix fixture. A failed calibration
means the unsafe mutation has not yet been tested; it must not be reported as
proof of either acceptance or refusal. In particular, real-registry controls
may need the positive calibration repaired before their attack is reachable.

No production validators, network requests or provider calls run in these
fixtures. The validation owner will record the exact before/after source and
test hashes, node identities and outcomes. No tests were launched by this
review author, and no scanner or runtime implementation was changed here.

## Follow-up review of repair draft b04: R1/R3/R4/R5

The following static findings refer specifically to repair draft SHA-256
`b04cff3e8a3209d514d568ade3a306127127124a4b77067ce411db0c52362a5a`.
They remain within the declared source domain and do not expand the claim to
arbitrary runtime objects. The separate six-case source-only module
`tests/test_wave7_5213_d76_specificity_prefix_followup.py` preserves the frozen
52+22 cases; each follow-up calibrates its unchanged source first. Reproduction
and repair verification are pending with the validation owner.

### R1 follow-up — aggregate abstract work must be bounded

The repair unrolls each finite loop but has no shared abstract-work budget.
Nested finite loops multiply analyzer work despite the 64-element per-loop
limit. Add a shared, conservative visit budget across nested loops and helper
calls; exhaustion must refuse the certificate. The new test calibrates a small
nested loop, then requests refusal of a modest source fixture with 8,192 inner
passes against a budget of at most 4,096 visits. No production fixture code is
executed and no wall-clock performance claim is made.

### R3 follow-up — default expressions use the containing scope

`global_reads()` applies a function's local-parameter shadowing to expressions
in its defaults. In `def redirect(validate=validate)`, the default captures the
module's certified callable before the same-named local formal exists. The
receiving body can change that callable's `__code__`; treating the default read
as local hides the visible alias escape. Resolve defaults and related
definition-time expressions in their actual enclosing scope.

### R3/R4 follow-up — wildcard imports make the trusted binding ambiguous

`stable_binding()` does not reject a module-level wildcard import, whose AST
alias is `*` instead of the affected trusted name. A real adjacent source module
can export a replacement `validate` callable after its certified declaration.
Either derive the complete imported binding closure or conservatively refuse
wildcard imports in the relevant source module; do not retain the earlier AST
as proof of the current binding.

### R5 follow-up — method definition expressions can alter class fields

The repaired class-body check inspects method decorators but omits positional
defaults, keyword-only defaults and method annotations. With eager annotations,
each can run `locals().__setitem__('base_prompt', PromptDescriptor())` during
class creation, installing a descriptor despite the plain annotated field.
The three controls use a valid required-field descriptor and an otherwise inert
method body; the annotation fixture has no postponed-annotations import. Prove
these definition-time expressions inert or conservatively reject unsupported
behavior, while preserving ordinary existing method defaults and annotations.

No scanner implementation was edited or tests launched by this follow-up
review author. These are additional issue details for AGY, not new GitHub
publications or claims that the repaired certificate is accepted.

### R3 follow-up revision — eager annotations are not inert callable metadata

Review of the subsequent held repair SHA-256
`533abc46a8be207e54cf8efd8a3b06c10e340631ecf26a0f6e63a8eaa8a08098`
found that `callable_uses()` still exempts every name inside annotations.
In a module without postponed annotations, a function annotation can execute
`setattr(validate, '__code__', mutate.__code__)` at definition time. Even an
annotation with no Call node can retain the callable: `def keep(value: validate)`
exposes it through `keep.__annotations__['value']` for a subsequent visible code
mutation. Both invalidate the old source proof without changing the declared
primitive input domain. Relevant definition-time annotations also belong in
the module binding analysis; they must not be skipped when they rebind a trusted
name.

Two calibrated controls are appended to the separate follow-up module, making
its new roster eight cases. The prior six assertions are unchanged, and its
historical six-case hash
`51caab53119ed8cbc371389a99adf1ec31b2e672a55d14a58571eef67362dcb2`
and retained six-failure before evidence remain intact. This additive revision
requires a separately pinned eight-case before/after run; no results are claimed
for the new bytes here. Resolve or conservatively reject eager executable
annotations and callable-value escapes while retaining valid source type
annotations. No scanner edits or tests were performed by this review author.
