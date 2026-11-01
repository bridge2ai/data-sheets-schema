# Offline CI scheduling estimates for #5364

Run 41148135309 at main `4c0798039`. Scheduling estimates in summed
case-seconds, **not wall-time predictions**. Refreshed-cost columns value
both layouts using the same new measurements, exposing stale-weight imbalance.

| Collection | Shards | Weights | Own-weight estimates by shard | Refreshed-cost estimates by shard | Report admission | API runner |
| --- | ---: | --- | --- | --- | ---: | ---: |
| main | 4 | old | 5,628.6, 5,628.6, 5,628.6, 5,628.6 | 4,445.2, 7,980.4, 7,973.2, 6,750.2 | 2 | 3 |
| main | 4 | new | 6,787.2, 6,787.2, 6,787.2, 6,787.2 | 6,787.2, 6,787.2, 6,787.2, 6,787.2 | 2 | 1 |
| main | 6 | old | 3,752.4, 3,752.4, 3,752.4, 3,752.4, 3,752.4, 3,752.4 | 2,885.5, 3,546.4, 4,124.2, 3,744.6, 6,335.4, 6,512.8 | 5 | 6 |
| main | 6 | new | 4,524.8, 4,524.8, 4,524.8, 4,524.8, 4,524.8, 4,524.8 | 4,524.8, 4,524.8, 4,524.8, 4,524.8, 4,524.8, 4,524.8 | 2 | 1 |
| main + v5 ten files | 4 | old | 5,636.4, 5,636.4, 5,636.4, 5,636.4 | 4,694.8, 4,981.9, 7,230.7, 10,266.9 | 4 | 3 |
| main + v5 ten files | 4 | new | 6,793.6, 6,793.6, 6,793.6, 6,793.6 | 6,793.6, 6,793.6, 6,793.6, 6,793.6 | 2 | 1 |
| main + v5 ten files | 6 | old | 3,757.6, 3,757.6, 3,757.6, 3,757.6, 3,757.6, 3,757.6 | 3,149.2, 3,798.4, 3,133.9, 6,190.8, 3,307.5, 7,594.5 | 4 | 6 |
| main + v5 ten files | 6 | new | 4,529.0, 4,529.0, 4,529.0, 4,529.0, 4,529.0, 4,529.0 | 4,529.0, 4,529.0, 4,529.0, 4,529.0, 4,529.0, 4,529.0 | 2 | 1 |

This main collection has 575 ordinary files; the earlier v5 investigation
used 567 files at `fa304cd80`. Its shard-2-to-6 report-admission
movement therefore does not describe this newer pinned collection. The old
four-shard reconstruction exactly matches all four supplied XMLs, including
the ordinary node-ID multiset. All ten new v5 files use fallback weights.

Collection: 20,805 before and after; identical node-ID multisets.
Ordinary union: 20,801 cases across four shards; no lost or extra occurrences.
Focused pytest: 47 passed, 1 failed, 0 errors and 0 skipped (exit 1). Full shard execution was not run.

The first nested four-worker canary passed and persisted all four shard XMLs,
preserving its complete 64-case synthetic multiset before the full focused run.

Local checks use the existing macOS Python 3.12 dependency environment,
with versions recorded in `shard-comparison.json`; this is not Linux CI.
Scratch XMLs, raw logs and node IDs remain uncommitted in `.ci-timing-41148135309/`.

The focused run had one fixture-path assertion failure: its nested
pytest inherited the repository root because all temporary files must stay
inside this checkout. The isolated case passed with `PYTEST_ADDOPTS=--rootdir=.`,
which makes each subprocess use its own cwd. The original focused-run failure
remains recorded; the complete suite was not rerun with that harness setting.
The ordinary shard collections use the unchanged CI options without that setting.
Initial failure details and hashes are retained in `shard-comparison.json`.
