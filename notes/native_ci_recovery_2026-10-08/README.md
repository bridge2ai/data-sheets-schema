# Retained synthetic native CI evidence

This package preserves and checks the saved artifacts from [PR #4659, run 37759818157](https://github.com/bridge2ai/data-sheets-schema/actions/runs/37759818157). It does not run native code, replay the cases, or establish whole-path acceptance. The neutral case stopped on a stream-change refusal; the omission case reached the existing deadline. Both failed outcomes are retained.

The tools address [#4679](https://github.com/bridge2ai/data-sheets-schema/issues/4679). The early stream failure is tracked separately in [#4680](https://github.com/bridge2ai/data-sheets-schema/issues/4680), with diagnostic work in [#4682](https://github.com/bridge2ai/data-sheets-schema/issues/4682); [#4537](https://github.com/bridge2ai/data-sheets-schema/issues/4537) and [#4354](https://github.com/bridge2ai/data-sheets-schema/issues/4354) remain open. No native production modules, acceptance assertions, workflow scheduling, or 900/180/120-second bounds are changed by this evidence package.

## Identity and retained bytes

The tested PR head is `aa845f2e083185707feab0ee8b090d6d9c9f52ef`. GitHub tested merge `cfe68ee650e3de0f775bd476f055f25c29eb7a72`, tree `8bdb68b58a410756871bf5b99cba90fbc8d6581b`. This historical identity is independent of the main branch containing these notes.

`evidence/run-37759818157/` retains each recovered native case ZIP, its GitHub artifact metadata and offline verification report, matching JUnit ZIPs, and literal inspection summaries for the two failed cases. Small archives are committed to preserve the evidence after GitHub artifact expiration. ZIP/tar contents are inspected as bytes and are never extracted or imported. GitHub runner paths within original artifacts are historical declarations, not local input paths.

`expected.json` declares the tested merge, tree, PR head and eight selected source-file pins. `source-pin-provenance.json` records their Git blob IDs and retained source bytes under `source-bytes/`. These bytes were downloaded at the explicit merge and compared with `git show` of that same fetched commit; tree and PR-parent linkage were checked independently of the case manifests. Retained source files have `.txt` names and are not loaded as code. This is a selected source identity, not the complete runtime import closure or authenticated execution.

## Saved outcomes

| Case | Shard / worker | JUnit duration | Saved first stop |
| --- | --- | ---: | --- |
| `test_actual_public_correction_three_workers_and_saved_completion` | 1 / `gw3` | 253.860 s | `native shared observation failed: ValueError: live native stream changed without appending bytes` |
| `test_actual_public_merged_omissions_and_all_chunk_statuses` | 3 / `gw3` | 1006.478 s | `native attempt deadline elapsed; retain all incomplete charge reservations` |

For both cases, the JUnit failure's embedded result equals the archived `actual-result.json`, the worker's setup/call/teardown durations match the rounded JUnit duration, and all five saved capture pins match the actual archived bytes. The archived inventories include the root directory and its observed mode. Before, archived, and after inventories agree. These facts mean the snapshot was retained consistently; case completeness remains `not_assessed`.

The neutral live summary leaves tool 4 pending. Its final transcript has a successful result for tool 4 followed by the next tool 5 callback request; control decisions stop at tool 4. The saved failure does not retain the stream role or earlier/later metadata pair that triggered the refusal. Final capture can include later bytes, and it does not establish a rewrite or race. The existing reader's equal-size/changed-mtime assumption requires separate investigation; Linux permits fields in one stat result to reflect different moments ([stat(2)](https://man7.org/linux/man-pages/man2/stat.2.html)).

The omission case records sealed phase 1 and core, pending tool 19 (`native_shared_stage advance`), and no completed assembly or native terminal. Its JUnit time includes fixture setup and cleanup and is not an attempt-only measurement. Neither case supplies scientific, billing, provider, or full performance acceptance.

The completed run failed. Shards 1 and 3 failed on the cases above; shards 2, 4, 5 and 6 passed. The six shard JUnit files contain 15,091 cases: 15,054 passed, 2 failed, 35 skipped and no errors. These totals exclude the separate offline evaluation, audit and canary jobs. `summary.json` records exact per-shard counts, artifact and XML pins, and controller outcomes. All six retained ZIPs were rechecked using the packaged verifier, reproducing their saved verification reports byte-for-byte. No artifact's absence from one worker implies that the node was globally unselected or unrun.

## Recheck without native code or network access

From the repository root, select a **new** output directory:

```bash
NATIVE_EVIDENCE_OUT=$(mktemp -d)
NATIVE_EVIDENCE_NOTES=notes/native_ci_recovery_2026-10-08
NATIVE_EVIDENCE_RUN="$NATIVE_EVIDENCE_NOTES/evidence/run-37759818157"
for shard in 1 2 3 4 5 6; do
  python3 -I -B -S "$NATIVE_EVIDENCE_NOTES/verify_native_ci_artifact.py" \
    --archive "$NATIVE_EVIDENCE_RUN/shard${shard}.zip" \
    --metadata "$NATIVE_EVIDENCE_RUN/shard${shard}-metadata.json" \
    --expected "$NATIVE_EVIDENCE_RUN/expected.json" \
    --output "$NATIVE_EVIDENCE_OUT/shard${shard}-verified.json"
done
```

The standalone verifier uses only Python's standard library. It checks finite ZIP/tar membership and byte bounds, canonical member names, root/child modes and types, file digests, link targets, three inventories, exact source declarations, and fixed artifact availability. It follows no JSON authority paths, loads no archived Python, and performs no network or subprocess calls. Each output is created exclusively; an existing destination is refused. Saved application JSON is a separate diagnostic layer: malformed or partial results preserve an otherwise verified archive and produce `diagnostic_error` without inventing completion.

Worker outcomes are retained by the verifier. JUnit-to-worker/result comparisons are separately recorded in the literal inspection summaries; the verifier itself does not certify pytest scheduling, JUnit completeness, or process execution authenticity.

## Verifier regression controls

Seven saved controls in `evidence/controls/controls.json` passed against the exact retained verifier and control-source hashes:

- Stable archives with malformed JSON, truncated JSON, or a null live result retain their inventory checks and report a diagnostic error, while the second valid case is still inspected.
- Valid local metadata at exactly 32 MiB is accepted; valid metadata at 32 MiB plus one byte is refused for size.
- An overflowing numeric exponent (`1e999`) is refused; an ordinary finite duration is preserved.

The three small synthetic ZIPs and their declarations/results are retained. Their source identities are explicitly invented and do not attest to repository or hosted execution. The two large size-bound JSON files are reproducible from the control script and are not committed.

To rerun the controls outside the checkout, copy the two exact tools into another new directory:

```bash
NATIVE_CONTROL_OUT=$(mktemp -d)
cp "$NATIVE_EVIDENCE_NOTES/verify_native_ci_artifact.py" \
   "$NATIVE_EVIDENCE_NOTES/native_ci_verifier_controls.py" "$NATIVE_CONTROL_OUT/"
python3 -I -B -S "$NATIVE_CONTROL_OUT/native_ci_verifier_controls.py"
```

The control script leaves a new directory containing all invented fixtures and the result ledger. It executes only the sibling verifier; it does not import repository modules or run the native acceptance cases. ZIP/gzip timestamps may make newly generated fixture hashes differ; each run records its own exact hashes.
