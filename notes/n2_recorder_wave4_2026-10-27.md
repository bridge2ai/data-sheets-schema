# Wave 4 N2 unit-4 recorder: idle gate blocked

2026-10-27 PDT / 2026-10-28 UTC. Refs #5149, #5212, #4354.
**The 60-second gate failed; zero recorder trials were launched.** The requested
paired N=10 control/treatment measurements remain unrun. Proceed to Priority 2
without attributing historical recorder timeouts to this new host sample.

This report and its helpers/evidence reside in the isolated
`/private/tmp/d4d-codex-recorder-wave4-20261027` checkout, branch
`codex/n2-recorder-wave4-20261027`, based on
`5dbd02f469735ed1b4392ecba6dd4a06713d3832`. The unchanged measurement driver
observed the preserved historical source checkout at
`01969cbed8eed93f420c640c1f1c306e5f58b033`; it did not execute a test child.

## Gate result and exact sample

The retained thresholds were unchanged: mean CPU ≤15%, peak CPU ≤35%, maximum
one-minute load/logical CPU ≤0.5, and no reported foreign process ≥5% CPU.

| Metric | Observed | Result |
|---|---:|---|
| Samples | 60 | Full requested window sampled |
| Mean host CPU | 57.04833333333333% | Above 15% |
| Peak host CPU | 87.3% | Above 35% |
| Maximum one-minute load/logical CPU | 1.049853515625 | Above 0.5 |
| Samples containing reported competitors | 60 | Foreign-process condition failed |
| Driver wall time | 66.83092983299866 seconds | Sampling/driver time only |
| Exit/status | 3 / `blocked_host_busy` | No trial launched |

The first sample was at **2026-10-28T01:44:52.653579+00:00**, host CPU
**50.3%**, load **10.009765625 / 6.29443359375 / 5.8017578125**, **10** logical
CPUs. Its largest reported process readings were:

| Executable basename | PID | PPID | Process CPU |
|---|---:|---:|---:|
| python3 | 177 | 73906 | 98.9% |
| soffice | 4205 | 4204 | 95.0% |
| Terminal | 3231 | 1 | 33.8% |
| WindowServer | 429 | 1 | 29.0% |
| WindowManager | 684 | 1 | 19.6% |
| corespotlightd | 784 | 1 | 16.7% |
| Safari | 33000 | 1 | 12.0% |
| rsync | 5106 | 5105 | 10.6% |
| spotlightknowledged.updater | 37307 | 1 | 10.0% |
| agy | 87673 | 3720 | 9.5% |

The peak host-CPU sample was **2026-10-28T01:45:05.557306+00:00**. Its exact
top-process readings and all 60 original process tables are retained in the
summary/archive. No separate `uptime-before-tests.txt` was collected, and none
has been synthesized after the fact.

Ranked by the sum of above-threshold reported CPU percentages across this window:

| Executable basename | PID | Above-threshold samples | Mean when reported | Peak when reported |
|---|---:|---:|---:|---:|
| python3 | 4247 | 51 | 93.3804% | 103.0% |
| python3 | 177 | 24 | 93.5667% | 100.0% |
| Terminal | 3231 | 60 | 36.3833% | 75.1% |
| WindowServer | 429 | 60 | 31.9417% | 47.0% |
| ninjarmm-macagent | 554 | 15 | 86.5133% | 97.8% |

These are process-CPU statistics, not percentages of total host capacity or
elapsed CPU time. The summary checks each reported competitor against its raw
sample and threshold; it does not independently recompute the driver's ownership
exclusions. Names do not establish whether Python/AGY processes were running
tests, their task owners, or the cause of earlier timeouts. Desktop/service
contention is visible, but this report does not claim that it was the only load.
No other process was stopped.

## Preserved source and unrun work

The source-before/source-after inventories are byte-identical and report pristine
tracked source at the exact historical head. `outcome.json` records
`source_unchanged: true`, null child return code and no child PID.

| Requested work | Status |
|---|---|
| 60-second idle gate | Completed and failed |
| Control recorder trials, N=10 | Not launched; no recorder timing or RSS measured |
| Treatment recorder trials, N=10 | Not launched; no recorder timing or RSS measured |
| Unit-4 test-path and D38 harness-pin corrections | Not applied; explicitly conditional on a passing gate |
| Paired performance/causal conclusion | Not available |

No test timeout, acceptance guard, production code, protected file, provider
configuration, historical evidence, or owner worktree was changed. No provider,
network, GitHub, push or main-merge action was made. This is measurement-status
evidence, not native launch or scientific approval.

## Reproduction and evidence digests

The measurement driver is retained as
`scripts/adhoc/native_recorder_measure_20261026.py`, SHA-256
`2f77329c51fc27f8f7e5f7157643f47c43b6e7a94872e3e5e292bb1817806169`.
Its recorded plan specifies `--idle-only --idle-seconds 60 --mode idle` against
the historical source checkout. Original evidence remains at
`/private/tmp/d4d-recorder-measurements-wave4-20261027/idle-check-wave4-20261027`.

`scripts/adhoc/summarize_wave4_recorder_gate_20261027.py` is an explicit copy of
the reviewed Wave 2 summarizer, adapted to this window's exact six-file roster,
Wave 4 labels and requested trial count. It recomputes gate aggregates, verifies
saved source/driver identities and all reported process observations, archives
every original file, round-trip checks bytes and modes, then rereads originals
unchanged. It does not sample the host or run tests.

| Artifact | SHA-256 |
|---|---|
| Summary helper | `95fbdf0a39a645046d49b8ef3ed6e370fedf40df983b16f43c0fec0436727009` |
| `notes/recorder_wave4_20261027/gate1_summary.json` | `1a99555bac22fcf4c3a3c4339552addc0a1e038441edd4b3221304e8aa6f569b` |
| `notes/recorder_wave4_20261027/gate1_originals.tar.gz` | `76b6067f3986d6230833116a3ca0ec831abcc44a244d8eff424c926bbfe7c307` |
| Original `outcome.json` | `bf90fa29404a37442f479135d3b979288491813dc3c8414c4c070f1ec3880b22` |
| Original `host.jsonl` | `e42d69df6cdc56fe1bfef32fe76c42f49e84a3174f391248d03b48688cfa98d9` |
| Each source inventory | `80d306d4768a311959c807229d838c7f2f9c7929925271ed9bd21047e9e5788b` |

Run the summarizer with `--gate` pointing to the original evidence directory,
`--label gate1`, and `--output` pointing to a new absolute directory under this
checkout's `notes/`. Existing outputs are refused. Resume recorder trials only
after a fresh qualifying host window; the old failed window stays preserved.
