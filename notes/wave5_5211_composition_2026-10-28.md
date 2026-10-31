# Wave 5 #5211 composition onto reviewed A13

The requested composition passes **270 tests, with two optional historical-input
checks skipped and no failures**. This is a local integration packet for AGY;
it is not published and does not approve a launch or historical wire parity.

- Branch: `codex/wave5-5211-composition-20261028`.
- Worktree: `/private/tmp/d4d-codex-wave5-5211-20261028`.
- Original A17 owner: `fc9e1a5d89a7223d75fa1dc1c46f524fb51dea03`.
- Previous reviewed A17/A13 packet: `dcc621a2721027b208a4b47b384d5d2dd697e94e`.
- Requested A13 parent: `04799422669fb2bd9f571bf8c0800dfc4b0ef008`.
- Merge and tested source: `496edfa081035933437f96f9b36c903b7ed0f36b`.
  Its parents are the previous A17 packet and requested A13 parent, in that order.

The merge was conflict-free: there is no resolved conflict hunk. The previous
packet already contained A13's tested production commit `907b5b654`; this merge
adds its three review/evidence files. All production and test bytes remain equal
to `dcc621a27`. The staged-registration roster repair for #5235 is retained,
including canonical pending-write hashes and existing-file serialization control.
No new protected source, prompt, decision-record, existing run or ATTIC change
was made. No owner worktree was modified.

## Fresh validation

The committed `scripts/adhoc/validate_wave3_20261027.py` ran the following modules
on the clean, exact merge head, comparing protected/historical paths to A13.
Pytest's basetemp was outside the worktree in
`/private/tmp/d4d-wave5-5211-validation-20261028/cases`.

| Module | Passed |
|---|---:|
| test_build_api_registrations | 34 |
| test_registration_input_sizing | 16 |
| test_audit_batches | 95 |
| test_audit_batches_split | 42 |
| test_audit_batches_v2 | 28 |
| test_audit_typed_format | 7 |
| test_preflight_resource_authority | 31 |
| test_wave4_5095_review | 5 |
| test_wave4_a17_a13_integration | 3 |
| test_build_draft_contexts | 9 |

Both skipped checks require `D4D_CHORUS_V10_TYPED_RUN`: historical CHORUS wire
reproduction and the historical worker-sentence comparison. No such input was
supplied. The suite verifies current synthetic mechanics; it does not establish
those two historical properties or all-project model fit.

Exit status was zero, source snapshots matched, and before/after imported origins
were verified. Driver wall time was 151.506 seconds; this is not quiet-host
benchmark evidence. The driver removes credentials, disables site startup and
pytest plugin autoload, and uses Python network/live-command refusal hooks.
Those hooks do not attest dependency bytes or arbitrary child-binary isolation.
No provider or GitHub calls were made.

## Evidence and publication

Exact command/environment/source records remain in the original external result
directory. `notes/wave5_5211_validation_2026-10-28/` contains compact result
files copied verbatim, plus SHA-256 references to the full external source and
origin inventories. Its manifest SHA-256 is
`65c82bf89c9b64038d2a5b71bb95bb0102b980ab65fb23343b4f0857c8305df6`.
No new compressed source inventories were added to this publication packet.
The explicitly requested merge retains existing A13 evidence in its ancestry.

The retained preservation command is:

```sh
python -B scripts/adhoc/preserve_wave5_validation_20261028.py \
  --evidence /private/tmp/d4d-wave5-5211-validation-20261028 \
  --output /private/tmp/d4d-codex-wave5-5211-20261028/notes/wave5_5211_validation_2026-10-28
```

It requires a fresh output path, verifies copied bytes/modes and unchanged
original evidence, and keeps the original outcome without promoting skipped or
failed cases. The compact helper was independently reviewed; it was committed
after the frozen tests and changes no tested production or test bytes.

AGY should compose this packet onto the new #5158 head as directed by Claude,
then run applicable integration checks and CI. Do not infer readiness of that
later composition from this test of the explicitly requested A13 parent.
