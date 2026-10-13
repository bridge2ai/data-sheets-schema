# Reproducing the saved numeric summaries

The [metadata verifier](../../scripts/adhoc/2026-10-12_trace_verify_performance_evidence.py)
was **reconstructed after the original analysis** to preserve the reporting
procedure for [#5014](https://github.com/bridge2ai/data-sheets-schema/issues/5014),
[#5015](https://github.com/bridge2ai/data-sheets-schema/issues/5015) and
[#5016](https://github.com/bridge2ai/data-sheets-schema/issues/5016). It is not
presented as the original generator of the published JSON files.

It reads retained local receipts and historical Git objects using only the
standard library. It does not import project modules, run tests or benchmarks,
contact GitHub, regenerate schemas or overwrite existing evidence.

The procedure checks:

- Original receipt hashes and the published 50-run / 20-documentation-run
  tables; successful feedback statistics; both critical-test log excerpts.
- Seven saved artifact archives against downloaded GitHub digest metadata and
  their eight XML members. The four core XML reports independently reproduce
  all 18,848 timing occurrences, 18,847 labels and 524 file weights, including
  legitimate repeated labels, skipped cases, largest cases/files, new-file
  coverage and the recorded scheduling estimates.
- The raw baseline profile's source pins, phase outcomes, restoration/error
  records, displayed pytest duration and 14 function aggregates. This includes
  the 19 measured API execute entries; it does not infer the separate 21
  attempted-operation explanation from missing events.

The completed metadata-only run passed **130 comparisons**. The compact
[verification receipt](metadata-verification.json) pins the helper, four
published inputs and the detailed external result. Large raw logs, archives,
private paths and the repeated detailed comparison rows remain external.

To repeat the check, provide the retained raw audit directory described in the
helper header and a fresh output path. `PERFORMANCE_RAW` below is an input
location supplied by the caller, not a required private path:

```sh
python3 scripts/adhoc/2026-10-12_trace_verify_performance_evidence.py \
  --repo . --raw-root "$PERFORMANCE_RAW" \
  --output "$NEW_VERIFICATION_JSON" \
  --summary-output "$NEW_COMPACT_RECEIPT_JSON"
```

These are historical arithmetic and byte-identity checks. Host/workspace
observations are hash-bound rather than remeasured. Narrative recommendations,
scientific coverage, later test pass claims and final PR acceptance are outside
this verification. Summed JUnit times, overlapping inclusive profile times and
workflow feedback are different measurements; none alone establishes speedup.
