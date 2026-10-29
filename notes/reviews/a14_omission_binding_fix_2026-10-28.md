# A14 omission binding repair: final engineering handoff

Reviewed owner head: `7408b177deba883c57fbbf11d0e64ba2b6345bfc` (#5162).
Final tested implementation: `0ea31f45b263b2771dc3251edcd20cf485e0e3af`, on
`codex/wave4-a14-binding-fix-20261028`.

**The reproduced binding defect is fixed. All 362 final selected test cases pass,
with no failures or skips.** The root agent independently reviewed the three
production changes and the schema constraints retained by the projection. This is
a local engineering handoff to Claude, not a merge, launch, or scientific approval.

## What changed and why

The prior `Prepared.check` accepted either the original request hash or a different
trimmed-schema hash even for callers that had selected no shared-generation route.
The retained independent test proved that a response naming an unsent projection
could receive `protocol_complete: true` despite an exact original `saved_request`.

The repair changes only three production files:

- `audit_omissions.py` again requires the single exact prepared request identity.
  There is no alternative-hash allowlist or response-driven mode inference.
- `typed_audit.py` supports one explicit, closed packet selector,
  `omission_wire: shared_generation_s7_v2`. Its value is validated, sealed into
  the packet and reconstructed during checking. The default omits this field and
  retains the original unprojected request. The selected request is deterministically
  derived from the captured original using the existing schema projection, then
  checked by the same strict `Prepared` checker. Its original packet hash remains
  separately identified; selected lineage also records the actual wire-request hash.
- `typed_audit_runtime.py` selects that contract only on the shared runtime path
  that already emitted the S7 projection, and emits the exact request returned by
  the new derivation helper. Index, assembly, resume and independent completed
  checks all follow the sealed packet selector.

The changed files already belong to `shared_generation.REQUEST_CODE` through
`ROUTING_CODE`; the descriptor hashes their actual bytes. No protected hook or pin
addition was needed. `shared_generation.py`, `canonical_hashes.yaml`, all prompts,
decision records, `data/ATTIC/` and existing generation directories remain unchanged.

## Compatibility and registration boundary

The canonical S7 omission **inner payload** remains byte-preserved: its SHA-256
uses the omission JSON format, without the typed-packet serializer's trailing newline.
The original public omission request format and released-request fixture remain
unchanged. Default typed packets omit the new selector.

The new sealed selector **changes the packet and outer request-binding identities**.
Do not describe the whole outer wire as unchanged. Rebuild registrations and pins
through normal integration before a new run; the changed captured source-code
hashes intentionally prevent reusing stale registrations.

**Old unflagged packets do not gain retroactive authorization to accept projected
responses.** No fallback infers this selector from a historical response hash.
Old saved source-projected runs are not claimed to replay unchanged under the
new implementation. Historical evidence and experimental conditions were not
rewritten or reclassified. Their original commits and declared limitations remain
the appropriate context for historical interpretation.

## Test evidence and independent review

The retained validation helpers require clean, exact committed source, attest
project/test import origins, disable site startup, and check source stability before
and after every run. They remove provider credentials and use offline Python hooks;
the physical dependency packages are identified, but their bytes are not attested.

| Archive | Tested commit | Result and role |
|---|---|---|
| `run-01.tar.gz` | `0d3d7d46afcb18754dfa671b897d90dd69f4c6d2` | Original owner code plus validation helpers: **202 passed**, zero failures/skips. |
| `run-02.tar.gz` | `f79ab0a6e6f0f029a3316bd5a3107a823e11e9a0` | Independent original defect: **1 passed, 1 failed**, zero skips. |
| `run-03.tar.gz` | `ef259028d2a9c5e92d8994012a7a49904fc1bd12` | Initial repair: **195 passed, 1 failed**. Exact-wire test found a real trailing-newline serialization mistake; preserved as failed evidence. |
| `run-04.tar.gz` | `0ea31f45b263b2771dc3251edcd20cf485e0e3af` | Corrected focused suite: **196 passed**, zero failures/skips; 62.117 seconds including source checks. |
| `run-05.tar.gz` | `0ea31f45b263b2771dc3251edcd20cf485e0e3af` | Runtime/completed/legacy suite: **166 passed**, zero failures/skips; 1502.487 seconds including source checks. Twelve LinkML/Pydantic deprecation warnings. |

All runs verified unchanged tracked source and valid import origins. Final focused
counts: `test_wave4_a14_review` 2; `test_typed_audit_omission_wire` 21;
`test_typed_audit` 100; `test_audit_omissions` 73. Final runtime counts:
`test_shared_generation_runtime` 10; `test_shared_generation_scope_context` 13;
`test_shared_generation_completed_replay` 32; `test_source_heading_completed` 11;
`test_shared_generation_assets` 100.

The new cases cover valid legacy and selected assembly with fresh independent
checking, cross-identity rejection in both directions, unknown selector values,
resealed selector removal failing to rebind workers, and saved-request substitution.
The existing runtime tests exercise actual mocked delivery, saved-response recovery,
omission merging/dropping, report regating, completed-replay mutations, terminal
failure without repurchase, CLI execution and completed reuse refusal.

The root agent reviewed the production diff independently and confirmed that the
projection preserves the semantic constraints read by `_target`, `_slot` and
`_class`. No additional code defect remained in that bounded review.

## Retained artifacts and lead actions

The byte-verified archives, complete source/import attestations, logs, JUnit XML,
outcomes and execution plans are under
`notes/reviews/a14_binding_validation_2026-10-28/`. Its manifest SHA-256 is
`0d048023dddef73bb8cefdcd8abcddcb5097f406828a2d8788c2df42d8393bb7`.
The original synthetic case directories remain outside the repository and are
explicitly excluded from these result archives. The diagnostic process sample is
also excluded and is not used as evidence for any acceptance claim here.

The archive helper is retained at
`scripts/adhoc/archive_n2_restack_validation_20261027.py`, SHA-256
`58ed839ba30d30f1089741c0e233fba01477bade741ea6a0a3b8a6a59284f187`.
The existing validation helpers and original failing causal test remain committed.

Claude should review and integrate the tested production commits `ef259028d` and
`0ea31f45b` with their tests/evidence in dependency order, then verify the integrated
head through the normal review/CI process. AGY remains responsible for authorized
publication under Claude's coordination. No push, GitHub write, provider call or
merge was performed by this review/repair task.

The earlier A14 registration sizing/cap checks remain launch-fit obligations on
the integrated BC1/cap stack. Passing these mechanical checks does not supply
human evaluation review, scientific acceptance or authorization to generate.
