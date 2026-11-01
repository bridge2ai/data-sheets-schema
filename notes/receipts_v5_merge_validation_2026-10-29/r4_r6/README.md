# R4/R6 validation, 2026-10-29

Offline follow-up to claude's independent re-review of `e8e033bf6`.
Production/test bytes have been stable since R4 commit `e754b790d`.
Acceptance ran at `00854fbe2`. Inertness began at `3997aff96`; the path-spelling
correction in `00854fbe2` was committed before either CHORUS probe executed.
It changes only displayed checkout-path metadata and verifies the actual
import root first. No measured production code or input data changed mid-run.

## R4 causal evidence

The identical five tests in `tests/test_receipts_v5_merge_r4.py` gave
**3 failed / 2 passed before** the fix and **5 passed after** it.

- A copy of CHORUS `2026-09-12_claude-opus-5-api-generic-v9_rep1`, with
  `receipt_format_version: 5` prepended, retains coverage 115/129, reports the
  mismatch, has zero gated findings, and exits 0 through the real strict CLI.
- Registered v4 fixtures with string `"4"` or integer `3` report the mismatch
  with zero gated findings and pass strict/canary receipt floors.
- Explicit v5 fixtures with string `"5"` or integer `4` retain one gated
  mismatch and fail strict. Both controls passed before the fix as well.

Only pytest scratch copies were edited. The production fix adds the finding
to `reported_kinds` when `instrument_version != 5`.

## Acceptance

**899 passed, 19 skipped, zero failures**, in 71.23 seconds. This is the
original selected 18-module suite plus the R4 module, not the entire repo
suite. The skips are the existing native-runtime cases. No timing failure
occurred and no isolated retry was needed. Python 3.13.12 and source/artifact
hashes are recorded in `validation.json`.

All R4/follow-up pytest runs used `--basetemp="$TMPDIR/codex-v5r4-pt"` with the
cache provider disabled. JUnit XML was written outside the worktree and
copied into this ledger after pytest's notes-directory guard completed.

## Fresh A13 inertness proof

Each proof invocation builds `148c869dd` with `git archive` under `$TMPDIR`.
The two CHORUS canaries are reconstructed from local commit `5457b71b4`.
No earlier temporary tree, saved raw baseline or bare clone is required.
Fresh base/head outputs compare exactly after replacing only the checkout
path with `<TREE>`, and their hashes match the original committed ledger.

| Surface | Result |
| --- | --- |
| Receipt corpus: backfill, explicit v3/v4, D37, claims, planner | 54 records, 48 checked, 36 snapshots; equal, SHA-256 `52b997f6f75365ac7d80400ddf7aca145f062f0c3edff82b76dccecd84fa7ed7` |
| `report_claims`, both v7/v8 | 335 records, 325 checked at each version; equal, SHA-256 `c659ce494b0545a077abcae29a593ad0dff572a1cbb9ab99f25370ce91c65018` |
| CHORUS v10, 10-20a and 10-22a | Request bytes equal to A13 and saved requests; results/checks equal; D37 58/58 and 64/64; output SHA-256 `830eb7055ba303dc03ee40352b61552d0ca1308a82f93a5a18aebe5a3f07f3d6` |
| generic_v10/A21 assembly | Unchanged SHA-256 `9e59f3db581c168d397793848579c62a9462e8a2e4236101af05f48803baa90e` |

Before the full replay, one checked receipt record and one report record ran
through the same launcher and output path in both trees. All four outputs
persisted, were non-empty and matched. The full invocation repeated those
canaries on its newly built archive. This proves local imports, git-backed
reads and persistence; no provider behavior was exercised.

Shared-generation v2's routing assembly identity still changes with source
bytes (N11); it is recorded separately in `inertness.json`. No protected pin
file was edited. R1–R3 and R5 remain untouched; v5 remains inactive.

## Reproduction and review

From this worktree, using the existing local project virtualenv:

```bash
D4D_PYTHON="../../data-sheets-schema/.venv/bin/python"
"$D4D_PYTHON" -S -B scripts/adhoc/prove_receipts_v5_inertness_20261029.py canary
"$D4D_PYTHON" -S -B scripts/adhoc/prove_receipts_v5_inertness_20261029.py full
"$D4D_PYTHON" -S -B scripts/adhoc/validate_receipts_v5_r4_r6_20261029.py tests
"$D4D_PYTHON" -S -B scripts/adhoc/validate_receipts_v5_r4_r6_20261029.py summarize
```

`review.md` records the separate read-only review. Two offline issue drafts
retain the deferred routing-worker pin concern and the resolved TMPDIR
spelling finding. No GitHub action, push, network or provider call occurred.
The protected-path check passed. Raw JSON remains locally in ignored `raw/`;
the committed XML, logs and ledgers retain counts and hashes.
