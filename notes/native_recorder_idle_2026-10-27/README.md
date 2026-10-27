# Recorder idle gate — 2026-10-27 UTC

**The quiet-host gate did not pass. No recorder pytest was launched.** The three
unchanged recorder trials, paired diagnosis against the original implementation,
and any resulting fix remain pending a qualified quiet-host window. Neither
attempt establishes why the earlier recorder timed out.

| Attempt | Exact outcome | Host samples |
|---|---|---:|
| `idle-check-20261027-queue` | `measurement_error`: `PermissionError: [Errno 1] Operation not permitted: 'ps'` | 0 |
| `idle-check-20261027-queue-ps` | `blocked_host_busy` | 60 |

The first attempt ended at 05:50:42 UTC before host sampling could complete.
The second sampled from the 05:51:08–05:52:14 UTC driver interval. Its mean CPU
was **51.776666666666664%** against a 15% maximum; peak CPU was **100%** against
35%; maximum one-minute load per logical CPU was **0.913134765625** against
0.5. The recorded decision also identified competing-process observations in
all 60 samples using its 5% per-process threshold. These observations describe
this gate window; they are not attribution of the earlier timeout to a process.

Both runs used `--idle-only`. Their plans contain a prospective worker command,
but the driver returns before launching it. Both outcomes have no child return
code and report unchanged source. The captured before/after source inventories
are byte-identical, identifying baseline
`01969cbed8eed93f420c640c1f1c306e5f58b033` (tree
`d92f24c84aad9161457930a4b191564868ac0676`). No production, baseline or measurement
driver source was changed; the 180-second recorder-helper and 900-second
registered-test limits were not relaxed.

[summary.json](summary.json) retains both exact outcomes, the concise gate
decision, archive hashes and every original file's size/SHA-256. The lossless
archives preserve all original input files, including raw process samples and
source inventories:

- [First attempt](idle-check-20261027-queue.tar.gz): SHA-256
  `d43539b48cc57e1d57ebddddaa9fbacf99a9118f498c6698969c3f2247433d7c`.
- [Completed gate](idle-check-20261027-queue-ps.tar.gz): SHA-256
  `9189136597c1848d3f1293ec852762324e59350e1190f902b38e28d47734fb59`.

The archival helper
[`archive_native_recorder_idle_20261027.py`](../../scripts/adhoc/archive_native_recorder_idle_20261027.py)
verified every decompressed member against its original bytes, rechecked that
the originals were unchanged, and checked the recorded CPU/load aggregates
against the 60 retained samples. It did not rerun the measurement, recompute
process ownership exclusions, or claim scientific acceptance. Its own SHA and
the unchanged measurement-driver SHA are recorded in the summary.

Reproduction: from this tooling checkout, run
`python3 scripts/adhoc/archive_native_recorder_idle_20261027.py --output-dir notes/<new-exclusive-directory>`
while the two original directories under
`/private/tmp/d4d-recorder-measurements-20261026/` remain available. Existing
outputs are refused. This archival verification required no new tests.

Refs #4354; P4 recorder timeout investigation. Tooling source before this
evidence-only addition: `bb43d797709e1376e92c22b9f239a6c59fdf88bc`.
