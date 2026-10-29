# #5211 final packet: A23 composition and F5/F7

2026-10-29. Local branch `codex/wave7-5211-final-20261029` in
`/private/tmp/d4d-codex-wave7-5211-final-20261029`.

## Composition and scope

The exact first parent is the required A14 × A17 sizing packet
`c4772694588b2b14c6377803cceeffb8c80b1392`. A23
`90312e30e8d957e3b79510abe9ea768967983224` was merged with `--no-ff`, producing
`ece52016669ead35b02e9022a1f6b85e3726690f`. The single conflict and its stage
blobs are retained verbatim in `wave7_5211_a23_merge_2026-10-29.md`. Its
resolution keeps A23's `serialize_draft_context` import and A17's comment
about deferring writes until all checks pass. No other manual merge
resolution was made.

F5 copies the exact helper blob
`09c84644d1a372e36a2dacaf3b001117cb220e06`; only the external-artifact
description changes. The helper was not executed and evidence was not
regenerated.

F7 changes only the builder's explanation of the existing owner-padding
allowance. The exact `missing explicitly supplied vocabulary` refusal now
names the registration's context and adds a warning that a live record
carrying those slots, including null-valued slots, would be refused during
strict traversal. The warning reaches `size_typed_audit_input`'s `warnings`.
Other owner/schema errors keep the historical-drift explanation. Padding,
wire formatting, token arithmetic, partition rules and strict runtime
validation are unchanged. This neither supplies a vocabulary nor removes a
field, and makes no new scientific support or live admission claim.

The prior read-only finding is retained in
`wave7_5211_f7_review_2026-10-29.md`. Claude's independent packet review
identified F7. The Codex parent separately reviewed this implementation
read-only, found no blocker, and requested the absent-slot positive control
included below. Claude's external review of the final packet remains pending.

Protected `src/data_sheets_schema/shared_generation.py` remains first-parent
blob `f0b55f73e6e9e5bdc9cbb42b175b9a7bdff9d839`. A23 context and decision
changes are inherited automatically from its exact commit; none was manually
edited. No existing run, ATTIC, source input, historical measurement or
owner worktree was changed. All Wave-6 refs remain intact.

## Written regressions and pending validation

`tests/test_wave7_a17_vocabulary_warning.py` contains five cases (one
two-value parametrization plus three single cases), all synthetic:

- Populated and null-valued vocabulary slots: sizing names the missing
  vocabulary, preserves record bytes and padding, and strict execution still
  refuses. Adding the explicitly declared vocabulary is a positive control.
- Own-project/arm sizing: the warning and specific cause reach the public
  sizing result without claiming a stand-in or historical-schema cause.
- An absent slot: no vocabulary warning or allowance, and strict preparation
  succeeds with the unchanged empty vocabulary.
- Unrelated historical schema drift: the original explanation and strict
  refusal remain distinct from missing vocabulary.

These are written tests, not results. No tests were imported, collected or
executed in this preparation; executed test count is zero. `git diff --check`
passes. The Codex parent owns the serial test slot. Targeted validation,
full collection and the full CI-shard run are required before final review;
this packet is not claimed merge-ready.

The addendum's minimum affected selection is:

```text
tests/test_build_api_registrations.py
tests/test_build_draft_contexts.py
tests/test_preflight_resource_authority.py
tests/test_registration_input_sizing.py
tests/test_audit_batches.py
tests/test_audit_batches_split.py
tests/test_audit_batches_v2.py
tests/test_audit_typed_format.py
tests/test_wave4_a17_a13_integration.py
tests/test_wave6_a14_a17_sizing.py
tests/test_wave7_a17_vocabulary_warning.py
```

The retained Task-4 preparation also calls for the shared omission formatter,
typed-audit, specificity/generality and composed D41/runtime checks. The new
diagnostic cases do not replace those, current-runtime five-call sizing
parity, or the eventual full suite. Historical-wire tests requiring
`D4D_CHORUS_V10_TYPED_RUN` remain optional with their existing reasons; their
absence must not be presented as measured historical parity.

No provider, network, GitHub, push or main merge occurred. Shared STATUS and
the tools tree were not edited. Publication remains with AGY under Claude.
