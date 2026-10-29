# Independent #5210 CHORUS wire baseline diagnosis

2026-10-28. Refs #5210 / #5157; inherited D38 prompt changes.

**The historical fixture's three hashes reproduce exactly on its original
`f8c5ac73c` base. The incoming A13 base produces three different hashes without
the #5210 admission implementation. Every changed byte is explained by the
inherited D38 v10 prompt spelling and wrapping changes.** This supports a
baseline-specific fixture update, not a blind replacement with the failing
branch's observed output.

The #5210 owner retains responsibility for the unchanged full-suite result,
the final failure trace, any fixture-only repair, and the repaired test's
admission-on/off and exact count-to-dispatch checks. This diagnosis does not
replace those checks or establish that the composed admission implementation
passes them.

## Pinned sources and independent execution

| Role | Commit |
| --- | --- |
| Historical production/assets | `f8c5ac73caba610d40c49aaceddb31ead3590a72` |
| Incoming A13 production/assets | `04799422669fb2bd9f571bf8c0800dfc4b0ef008` |
| Historical control plus identical committed harness | `e5fdedb109fabf84cf4839fd1180733e70dc09fe` |
| A13 baseline plus committed harness | `b6bd3ef94daf3e22d93f11be00f7bb6ded7073a1` |
| Reversible comparison helper | `6453f9dabbce8065bed171d7fb20b5e261ffddda` |
| Original #5210 fixture source | `aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4:tests/test_report_admission.py` |

The original fixture source SHA-256 is
`1cf90e19274cccbd1fff2f41dab3a03ce726109198e839e5c14443c2f544ed08`.
Its module is copied verbatim after a provenance-comment header to
`scripts/adhoc/wave5_5210_fixture_20261028.py`. The preparation helper checks
that exact relationship before either capture. Only its `ROOT` and
`CHORUS_BUNDLE` constants are relocated to the selected baseline checkout;
the fixture functions, fake client, scripted records and old goldens are
unchanged. The original #5210 worktree and running suite were not edited.

The two fresh branches/worktrees are:

- `codex/wave5-5210-wire-baseline-20261028` at
  `/private/tmp/d4d-codex-wave5-5210-wire-baseline-20261028`;
- `codex/wave5-5210-wire-old-control-20261028` at
  `/private/tmp/d4d-codex-wave5-5210-wire-old-control-20261028`.

Each run verifies clean committed source and unchanged `src/`, `tests/`,
`data/` and `.claude/` against its exact base, then explicitly refuses a runtime
that has `_admit_shared_context`. Both source/import-origin checks pass before
and after the scripted pipeline. Both pipelines finish with no validation
problems and the expected final `reconcile_full`, `report`, `report_regate`
phase sequence. These are **two successful offline derivations, not six pytest
passes**. A13 took 141.474229917 seconds; the old control took 133.440813459
seconds. They ran serially in the assigned test slot.

## Exact normalized request identities

Normalization is the unchanged fixture algorithm: compact sorted-key JSON,
UTF-8 without ASCII escaping, with the synthetic run root replaced by `<root>`
and schema checkout root replaced by `<repo>`. Actual normalized canonical
request bytes were saved for all six captures. The helper verifies their hashes
against the fixture's own `wire_sha256` result.

| Phase | Bytes, unchanged | Original f8 golden, independently reproduced | Incoming A13 baseline |
| --- | ---: | --- | --- |
| `reconcile_full` | 190453 | `b4f8f925e29b54d80cc95ad7c5bbe3f170e7295ccb1c8b8eb3a3dcaf97421daa` | `31340b31d787baa1da17c2b738c99d21efd2a1db9150eb0d0aaf917f1ac6160c` |
| `report` | 193993 | `9a13ed423b0c5bb7c0da908100ead81128f713dfc0dc0b565ecd4bd11c8bfbe8` | `eea1fe34d3de44efbc85a681b5b2d58c0f66bcc70f7b64450378db75fc996749` |
| `report_regate` | 194777 | `300b1213e94825e41fc22a38bb4100aabebbb533ec0de49487485dfac49a79a9` | `d085cabccdc8d0b7e1e99d498e6f3cfe59b80322c907d3e8d49b177aaf672f1d` |

For every phase, the **only changed JSON leaf** is
`messages[0].content[2].text`. Applying the three exact changed hunks from
`src/download/prompts/d4d_generic_arm_prompt_v10.md` reconstructs that string
and the entire new canonical request byte-for-byte:

- old lines 392–393: two `licence` → `license` spellings;
- old line 398: the third `licence` → `license` spelling;
- old lines 430–438: the existing R9 tail is rewrapped.

These edits were inherited from
`6a0f8acfed6d58fac8747d891b8a05975534a5c5`; corresponding asset pins were updated
by `f73764e0685f436a07e802766e16030572d29a18`. The protected delta also includes
the uniform-rules spelling changes and the matching `shared_generation.py`
and canonical-registry pins. Only the v10 generic prompt hunks account for the
observed model-facing request delta in this fixture. No schema files differ
between these two bases. No other model-facing fields differ.

`comparison.json` contains the exact protected-file diff and inherited commit
list, original/new asset hashes, reversible character edits with UTF-8 byte
offsets and old/new text, and each whole-request hash. It independently checks
that replaying the recorded edits reproduces the complete new canonical bytes,
then separately verifies that only the inherited prompt hunks are needed.
All three `canonical_patch_replay_byte_identical`, `only_inherited_asset_hunks`
and `old_golden_reproduced` flags are true.

## Evidence and reproduction

Committed helpers are `derive_5210_wire_baseline_20261028.py`,
`compare_5210_wire_lineage_20261028.py`, the copied fixture, and reused
source/origin and compact-preservation utilities under `scripts/adhoc/`.
The compact preservation helper differs from the earlier Wave 5 helper only
in wording for externally retained artifacts, to include canonical requests.

Complete raw captures remain outside the worktrees:

- `/private/tmp/d4d-wave5-5210-wire-old-control-20261028`;
- `/private/tmp/d4d-wave5-5210-wire-baseline-20261028`.

`validation/` retains the exact outcomes and plans, including the commands,
source pins and fixture hashes. Its manifest records SHA-256 and byte counts
for the external canonical request files, source/origin inventories and phase
records. The compact reversible byte comparison is committed here; no large
source inventories are added. Hash references do not replace retained raw
artifacts or reconstruct transient dependency state.

Reproduce from clean worktrees at the two harness heads, using fresh external
output paths. For the A13 capture:

```sh
env -u PYTHONHOME PYTHONPATH='' \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B \
  scripts/adhoc/derive_5210_wire_baseline_20261028.py \
  --base 04799422669fb2bd9f571bf8c0800dfc4b0ef008 \
  --head b6bd3ef94daf3e22d93f11be00f7bb6ded7073a1 \
  --output /private/tmp/d4d-wave5-5210-wire-baseline-20261028
```

For the control, substitute its exact historical base and harness head above
and a separate fresh output. Then run `compare_5210_wire_lineage_20261028.py`
with `--old OLD_CAPTURE --new NEW_CAPTURE --output FRESH_COMPARISON_JSON`.

Capture startup disables site/`.pth` and plugin loading, uses the physical
Python 3.13 environment and explicit selected-tree source paths, removes
provider credentials, and installs a Python network/live-command refusal hook.
Only the existing fake client dispatches requests. These guards do not attest
dependency bytes or isolate arbitrary child binaries. No provider/native calls,
GitHub actions, pushes, or production/protected-file edits occurred.

| Artifact | SHA-256 |
| --- | --- |
| Reversible comparison | `0e952e20c5830ce19d4720e7d05767479952a78c629c5f64b87c53a9cc8159ef` |
| Compact validation manifest | `22202e8c39fcdb00d454dded2a90290502c78a02b9707b6924f7e83eef6069fd` |
| Original-control outcome | `11f687e8bc65a168d7a1b08114147ae63d26cd195cfa2a7e1859fc261d85aafb` |
| Incoming-A13 outcome | `c8866ed889a96ed221501e26f58e779f14bf4101e5d5f79249289cd82bc64d60` |

Recommended next action: after preserving its original full-run failure,
the #5210 owner can name the incoming A13 base in the fixture and use these
independently derived hashes, retaining the original f8 hashes as historical
metadata. Keep every counted-request, saved measurement and admission-on/off
assertion intact, and run the complete affected CHORUS test on the frozen
fixture repair. This report does not change the fixture or any scoring rule.
