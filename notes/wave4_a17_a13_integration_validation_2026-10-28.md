# A17/A13 integration and staged-roster repair — 2026-10-28

The local integration passes its focused engineering suite: **270 passed, 2
optional historical-run checks skipped, 0 failures/errors**. The integration
exposed and repaired [#5235](https://github.com/bridge2ai/data-sheets-schema/issues/5235):
replacing a staged registration previously put the old registration's hash into
the v2 roster. Claude remains the lead and AGY owns publication. This packet is
local; it does not authorize generation or resolve D50.

## Source and ownership

- Isolated worktree:
  `/private/tmp/d4d-codex-wave4-a17-a13-integration-20261028`.
- Local branch: `codex/wave4-a17-a13-integration-20261028`.
- A17/#5211 parent: `fc9e1a5d89a7223d75fa1dc1c46f524fb51dea03`.
- A13/#5158 parent: `907b5b6545dcca06e16f89e4d2cb0550d5432d35`.
- Merge base: `f8c5ac73caba610d40c49aaceddb31ead3590a72`.
- Reviewed merge: `0459526d4577563cdf446e1779801a4f16ccbe87`.
- Causal regression tests: `295ab3ea12e26e7d4a267c8e18dcdc35e4e799ef`.
- Final tested production/helper/test source:
  `b369529b93b3d54a1730066003b8b8e799ab24bf`.

Only `scripts/build_api_registrations.py` had merge conflicts. The resulting
merge retains both original parents. A13's later evidence-only head
`04799422669fb2bd9f571bf8c0800dfc4b0ef008` was not merged into the frozen test
source; its production code is the tested `907b5b654` parent.

No protected-file conflict occurred. The protected generation implementation,
prompt files, canonical hashes, historical concatenated inputs and `data/ATTIC/`
are unchanged against A13 `907b5b654`. The inherited A13 prompt/hash changes from
the earlier A17 base were not manually edited or rolled back. No provider calls,
GitHub writes, pushes, main merges or owner-worktree changes were made by this
task. Root filed #5235 separately.

## Conflict resolution and retained contracts

- A17 retains its prepare-then-write transaction: registrations, generated
  contexts, sizing sidecars and roster are validated before output mutation.
- A13's worktree-resource wrapper now wraps `prepare_registration`; its thin
  `build_registration` caller writes the prepared absolute output paths after
  resource-context restoration. The new relative-path regression verifies the
  selected worktree remains authoritative and the caller's cwd is restored.
- Mandatory partition/limit resolution remains immediately after arm
  validation, before draft-context creation. This preserves the early-refusal
  repair rather than introducing incidental files on an invalid request.
- A13's selected-tree schema closure and routing pins, copied-script bootstrap,
  default-context precedence, context-dir handling and missing-resource refusal
  remain in place. `--check` executes both input-pin and A17 sizing validation.
- A17 retains explicit limits and input-sizing evidence outside the calibrated
  CHORUS profile. Its sizing and admission safeguards are unchanged.
- The A13 Kids First default-manifest mechanics fixture now supplies the
  required aggregate-input limit and explicitly marks its committed CHORUS
  sizing record as a stand-in. This tests resource authority without pretending
  to establish Kids First capacity or relaxing production admission.

## #5235: causal defect and repair

The A17 CLI stages a replacement registration and calls `build_roster` before
writing the transaction. A13's v2 roster builder preferred an already-existing
registration file when computing `registration_sha256`. A same-label rebuild
using `--replace --max-calls 20` therefore wrote the new registration with an
old digest in its roster, invalidating subsequent roster verification.

The retained regression is
`tests/test_wave4_a17_a13_integration.py::test_staged_replacement_roster_pins_the_new_registration`.
At `295ab3ea12e26e7d4a267c8e18dcdc35e4e799ef`, this case failed at the expected
digest comparison while both controls passed (**1 failed, 2 passed**). Source
attestation remained unchanged. The causal failure is retained, not overwritten.

The repair adds the explicit `pending_registration_writes` keyword to
`build_roster`, defaulting to false. Only the CLI's staging path sets it true,
hashing the same canonical registration bytes that `_write_outputs` will write.
Standalone calls on existing registrations continue to hash their actual
serialization, including noncanonical pretty JSON. The regression now confirms
the replacement bytes match the roster and `--check` succeeds. Separate controls
cover existing serialization and worktree-relative output authority.

## Validation

The retained `scripts/adhoc/validate_wave3_20261027.py` harness ran both stages
on clean committed source with protected/historical paths compared to A13
`907b5b6545dcca06e16f89e4d2cb0550d5432d35`. It captures tracked-source snapshots,
import origins before/after, exact invocation/environment controls, pytest log
and JUnit results. Both runs retained unchanged source.

| Focused module | Passed |
| --- | ---: |
| `test_build_api_registrations` | 34 |
| `test_registration_input_sizing` | 16 |
| `test_audit_batches` | 95 |
| `test_audit_batches_split` | 42 |
| `test_audit_batches_v2` | 28 |
| `test_audit_typed_format` | 7 |
| `test_preflight_resource_authority` | 31 |
| `test_wave4_5095_review` | 5 |
| `test_wave4_a17_a13_integration` | 3 |
| `test_build_draft_contexts` | 9 |
| **Total** | **270** |

Both optional skips require `D4D_CHORUS_V10_TYPED_RUN` pointing to the retained
2026-10-22a intermediate directory; it was not supplied in this run:

1. `test_registration_input_sizing::test_rendering_reproduces_the_chorus_v10_wire`.
2. `test_audit_batches_split::test_chorus_v10_saved_run_differs_only_by_the_reworded_worker_sentence`.

The final pytest duration was 98.29 seconds; the evidence driver measured
102.079142417002 seconds. These are run diagnostics, not host performance
benchmarks. The suite does not establish scientific acceptance, real-provider
tokenization, all-project capacity, historical wire parity, or live readiness.
It does not resolve the separate BC1 sizing or N2 recorder timing gates.

Commands, run from the isolated tree with the existing physical repository venv:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B \
  scripts/adhoc/validate_wave3_20261027.py \
  --output /private/tmp/d4d-wave4-a17-a13-causal-20261028 \
  --expect-head 295ab3ea12e26e7d4a267c8e18dcdc35e4e799ef \
  --base 907b5b6545dcca06e16f89e4d2cb0550d5432d35 \
  --module test_wave4_a17_a13_integration

/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B \
  scripts/adhoc/validate_wave3_20261027.py \
  --output /private/tmp/d4d-wave4-a17-a13-focused-20261028 \
  --expect-head b369529b93b3d54a1730066003b8b8e799ab24bf \
  --base 907b5b6545dcca06e16f89e4d2cb0550d5432d35 \
  --module test_build_api_registrations \
  --module test_registration_input_sizing \
  --module test_audit_batches --module test_audit_batches_split \
  --module test_audit_batches_v2 --module test_audit_typed_format \
  --module test_preflight_resource_authority --module test_wave4_5095_review \
  --module test_wave4_a17_a13_integration --module test_build_draft_contexts
```

The child disables site initialization, bytecode and pytest plugin autoload;
credentials are removed and Python network plus selected live-command hooks
are installed. Dependency bytes are not attested; the hooks are not an OS-wide
network sandbox. Exact evidence details remain available in the archived plan,
bootstrap and origin files.

## Retained evidence and recovery

Both original `/private/tmp/d4d-wave4-a17-a13-*` result directories remain
unchanged. Top-level JSON/log/XML evidence was copied byte-for-byte into the
committed `notes/wave4_a17_a13_validation_2026-10-28_evidence/` archives by
`scripts/adhoc/archive_n2_restack_validation_20261027.py`; its manifest records
the archive roundtrip, per-entry digests and excluded synthetic case directories.
These compressed archives include ignored `.log` files; no archive relies on
Git adding ignored loose logs. Sources and helper versions remain recoverable
from the named commits.

| Artifact | SHA-256 |
| --- | --- |
| evidence `manifest.json` | `13a0f06739c27b008e40f0a295f381088cd0547c72a81d7b3970fba87af70151` |
| causal `run-01.tar.gz` | `704550b45b1373d3124f9c27b6141d5272d614561df8040134498ca8496563ae` |
| final `run-02.tar.gz` | `0f3c1f47f08ba97a274094215288c202c925d22727d8720d502914295b1a5009` |
| `validate_wave3_20261027.py` | `cc1cf3c241bccd8af51bc6b747c961b16605f1a2e45612cadf7c74859fdf51ca` |
| `wave3_validation_common_20261027.py` | `f3e12dbd488941281cff46889ea48da32502e81db31f29020fe9177e20b5c229` |
| `archive_n2_restack_validation_20261027.py` | `58ed839ba30d30f1089741c0e233fba01477bade741ea6a0a3b8a6a59284f187` |

Publication and any subsequent stack integration remain with Claude/AGY. This
packet's evidence supports the reviewed local code integration and #5235 repair;
the two historical checks and the wider generation/evaluation gates stay open.
