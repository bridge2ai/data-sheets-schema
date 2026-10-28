# Deferred #5094 N2/N3 snapshot repairs — 2026-10-28

The two deferred snapshot-selection defects are repaired locally and verified offline. The focused suite passed **100 tests, zero failures, errors or skips** at `de56f9dd7efc9009704dec2e24cc3378dbb24f32`. The separate fixed canary passed the same case already included in that suite, so there are **100 distinct passing cases**, not 101.

This changes selection for freshly computed audit-total checks. It does not rewrite stored measurements or historical generation/evaluation evidence. No backfill application, provider call, GitHub operation, push or merge was performed.

## Exact history and independent review

- Base: `3f202bd3e320672fed8a49b0c4b82ef7e124a43f` (Claude's round-two #5094 repair).
- Baseline causal tests and retained driver: `dfd0b9d4b0932cf6990971db6d70d39109e404af`; production bytes still equal the base.
- Two-file repair and compatibility tests: `94484d0a9fab8c47f54ffe732b5393fe0c502bbe`.
- Frozen tested head: `de56f9dd7efc9009704dec2e24cc3378dbb24f32`; the additional commit only adds the malformed-but-validly-attested JSON test.
- Branch: `codex/wave5-5094-legacy-snapshots-20261028`.
- Worktree: `/private/tmp/d4d-codex-wave5-5094-legacy-20261028`.

The Codex parent session performed a separate read-only review of the implementation sub-agent's two-file production delta at `94484d0a9`: exception scope, unchecked-block shape, prior-result preservation, strict snapshot authority, legacy fallback and portable-only discovery. No additional source defect was identified. The production bytes did not change afterward. Claude is the orchestrator and lead; Claude's external review and publication remain pending. The original findings are draft Issues 11/N2 and 12/N3 in the lead's `notes/coordination/2026-10-28-issues-from-pr5094-review.md`; the self-contained drafts in this directory record them without inventing GitHub issue numbers.

## What changed

`api_runner.report_audit_totals_block` catches `UsageLedgerError` only when resolving a saved audit without explicit live carry. It returns a normal `not_checked` block with the refusal reason. `_current_report_audit_totals` can therefore retain an already checked result rather than failing the resume path. Explicit live carry still bypasses saved-snapshot lookup.

`backfill_checks.compute` resolves audit bytes through `snapshot_store.read_latest(..., record=record)` when a record or index declares snapshot ownership. The latest byte-attested phase wins; missing, altered, foreign or ambiguous evidence produces `not_checked`, never a fallback to the first audit. Malformed JSON with a valid byte attestation also remains unmeasured. Default computation now discovers a retained portable audit even when the original unnumbered filename is absent.

Compatibility is deliberately narrow: a standalone record with neither `run` nor `intermediates`, and no current or previous snapshot index, can still use exactly one legacy audit file. Any ownership/index claim enters strict resolution. Multiple unowned numbered files never justify picking the first one.

Only `src/data_sheets_schema/api_runner.py` and `src/data_sheets_schema/backfill_checks.py` changed in production. Snapshot authority, report parsing/instrument version, protected prompts, canonical hashes, schema, decisions and historical data remain byte-identical to the base. Related deferred parsing issues N1 and N4 are outside this task.

## Causal validation

The representative fixture uses the committed VOICE v4 record under `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1`. Its two audits have 21 and 18 findings; the report states 18. Its portable inventory lacks phase/generation identities, so selecting one audit as current would be a guess.

The test copies the record, report and two audit files into an external basetemp. Only the copied inventory's two audit paths are rebased. It verifies the original audit SHA-256 attestations and asserts that original and copied bytes remain unchanged by the computation.

| Run | Frozen head | Result | Purpose |
| --- | --- | --- | --- |
| Baseline canary | `dfd0b9d4b` | 1 expected failure | Captures both N2's `UsageLedgerError` and N3's false 18-versus-21 mismatch in one assertion |
| Fixed identical canary | `de56f9dd7` | 1 passed | Both fresh checks become unmeasured; the checked prior remains intact |
| Focused suite | `de56f9dd7` | 100 passed | 16 new causal cases, 16 report-total, 44 round-two, 19 backfill and 5 snapshot-attestation cases |

The final suite took 53.67 seconds of pytest time, 59.78 seconds including driver checks. Its 12 warnings were existing LinkML/Pydantic deprecation warnings. No expensive full API-runner suite or live generation was run.

The retained summarizer independently verified the persisted external copies after the tests, the equality of the baseline/fixed canary function, the full tracked-source before/after inventories, the targeted case set, and the bounded production diff. The baseline assertion stops before the test's final byte checks, so the post-run summarizer supplies that persisted-copy verification for the expected failure too.

## Evidence and reproduction

Full raw evidence remains at:

- `/private/tmp/d4d-wave5-5094-legacy-baseline-20261028`
- `/private/tmp/d4d-wave5-5094-legacy-canary-20261028`
- `/private/tmp/d4d-wave5-5094-legacy-targeted-20261028`

`validation/run-01` through `run-03` retain compact logs, JUnit, outcomes, commands, bootstrap metadata and plans verbatim, including the expected failure. Large source/origin inventories are referenced by hashes rather than republished. The committed historical files and exact Git heads are recovery anchors if temporary directories expire. Python network audit guards, removed provider credentials, disabled automatic plugins/site startup and external basetemps constrained validation; these are application-level guards, not an OS-level network sandbox. Dependency bytes were not independently attested.

From a clean checkout of the relevant frozen head, reproduce each run using the repository venv and fresh external output path:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B scripts/adhoc/validate_wave5_5094_legacy_20261028.py --root CHECKOUT --output FRESH_EXTERNAL_OUTPUT --head FROZEN_HEAD --group canary
```

Use baseline `dfd0b9d4b0932cf6990971db6d70d39109e404af` for the expected failure, then tested head `de56f9dd7efc9009704dec2e24cc3378dbb24f32` for the passing canary and `--group targeted`. The helper requires an exact clean checkout; publication-only evidence added later is deliberately excluded from those historical test claims. `preserve_wave5_validation_20261028.py` retains compact results, and `summarize_wave5_5094_legacy_20261028.py` reconstructs the case/digest checks.

SHA-256 anchors:

- `summary.json`: `0b67520eb38e241e0b61a25478ea296edac473cf9825fd1441f74596d9e28687`
- `validation/manifest.json`: `b579f5c671907818875c0b0cac3140bec803486588c00e502d61f4745536e332`
- Tested validation driver: `896ee83291f53741b05c581939d501dce2713046a9b68df4ca0f4b8c476f0b08`
- Summary helper: `4d256a6f9f281892cf8f2e496e44444fd16ccee8ba550e69310bb5769bde70fc`

This is local engineering validation. Scientific acceptance and historical scoring decisions were not assessed.
