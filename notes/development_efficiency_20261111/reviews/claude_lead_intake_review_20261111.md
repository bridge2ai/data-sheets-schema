# Lead intake review after the transfer to Claude, 2026-11-11

Written by the incoming Claude lead. It records what was collected from the
five workers at the transfer, what the lead checked first-hand, and what was
corrected. Times in the evidence files are generated, not typed.

## Collected

| Worker | Report | Where it is kept |
|---|---|---|
| AGY1 | CI bottleneck assessment (terminal only) | `handoffs/captures-20261111/agy1-tab-20261111T072934Z.txt` |
| AGY2 | PR 5808 readiness review (terminal only) | `handoffs/captures-20261111/agy2-tab-20261111T072933Z.txt` |
| AGY3 | API-only critical-path reconciliation (terminal only) | `handoffs/captures-20261111/agy3-tab-20261111T072933Z.txt` |
| AGY4 | Diagnostic deadline assessment | `handoffs/agy4-cpu-diagnostic.md` section 7 |
| Native Codex | Idle; no evidence-backed optimization | fleet viewport, 07:26Z |

The captures were read with `scripts/adhoc/read_worker_tab_history_20261111.applescript`.

## PR 5808: checked first-hand

- Head `6792947ea6558d10c85106065b023cb57838835a`, open, not a draft, CLEAN and
  MERGEABLE; run 42916359440 succeeded on that head (base `7233f193`).
- Main is `925d726d67cdd03fe28fdeafdde60fa27df57205`; its push run 42966025224
  succeeded.
- The PR's 68 files and the 22 files main gained since `7233f193` share no
  path. No protected file is in the PR (`api_runner.py`,
  `shared_generation.py`, `canonical_hashes.yaml`, the boundary contracts, the
  scanner, prompts, `pyproject.toml`, `poetry.lock`).
- **Combined head.** A local, unpushed merge preview
  (`44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9`, tree `3bb94f5c…`, parents main
  and the PR head) in the sparse worktree
  `d4d-executions/claude-pr5808-combined-20261111`. The six test files either
  side touched hold 116 tests and all pass there: 34 in the first run
  (release identity 16, acceptance 2, component limits 2, CI timing update
  14), 81 of the other 82 in `rerun`, and the last in `rerun2`.
  - Two failures were the lead's own invocation and are kept as evidence:
    `focused.log` (76 errors and 1 failure: `-o tmp_path_retention_policy=none`
    leaves pytest's base temp unlocked and the nested sessions deleted it) and
    `rerun.log` (1 failure: a base temp inside the worktree changed the nested
    sessions' rootdir, so node ids came back with a path prefix).
  - The collect-only pass is **not** a full-collection proof: 22,535 tests
    collected and 5 files not collectable because the sparse checkout omits
    their data. Full collection rests on each parent's own hosted run.
  - Script: `scripts/adhoc/pr5808_combined_head_check_20261111.sh`. Evidence:
    `claude-pr5808-combined-20261111/tmp/combined-head-20261111/`.
- Not rerun: the full suite on the combined head. The post-merge main run is
  the first full run of it, and the first run of the push-only
  `schema-examples` job at schema 3.2.1.

## Corrections to the worker reports

1. AGY2 section 1 says the ledger findings including 5582 to 5590 "are
   resolved". They are not: the specificity scan exits 1 with nine
   `run_controllers` violations (zero under `api`), issues 5582 to 5590 are
   open and retained, and issues 5792 to 5807 are dispositioned in the ledger
   but open on GitHub. AGY2's own section 3 states the retained findings
   correctly.
2. AGY3 says the specificity scan "already passes" on PR 5808. Same
   correction. The recorded scan is at `2e9469852b…`, an ancestor of the head;
   the later commits add evidence, handoffs and the product-check helper.
3. AGY3 carries D88's $60 slice and $51 stop as the A21 budget. D88 was given
   for the M4 registration `d4ac7f88…`, was suspended by D89, and under D93
   applies only if the owner reinstates it. D129 names a "~$25 slice" for the
   rebuilt registration, while the M4 packet sized the run at $31.66 expected
   and $43 to $44 at caps. The figure is an owner choice at the launch word.
4. **D89, D93 and D129 hold A21 behind native integration, and STATUS.md
   records no release.** The readiness plan records the user's direction that
   broader assessment machinery, Core expansion and historical migration are
   not prerequisites; it does not record a release of the native-first order.
   The lead is asking the owner.

## Dispositions

- AGY1's recommendation (sub-file chunk sharding plus parametrizing the
  journal loop): released as one local slice, no push. Its own limit stands:
  on pull requests the gain is capped near 1m30s by the `routing-portable`
  lane. AGY2 reviews the design adversarially; AGY4 designs that lane's split.
- AGY4's proposed witness (one more `cpu-monitoring` run under low host
  load): a genuine native diagnostic needing the private configuration armed
  again. Not released; an option for the owner.
- AGY3: writing the A21 rebuild runbook for the route, read-only.
- Native Codex: left idle. No evidence-backed task exists for it.
- Outgoing Codex lead: no channel from this session (no `codex_tui` tool and
  its terminal is not identified), so no assignment was sent.

## Host

About 12 GB free on the data volume and 97 worktrees. New worktrees are
sparse. No cleanup was done; none is authorized while evidence is retained.

## Second round, same day

**Final-generation track**

- AGY3's runbook `handoffs/agy3-a21-rebuild-runbook.md` is accepted as the
  working runbook. One error was sent back and fixed: it had placed the nine
  retained specificity findings in two `src/` modules; they are in
  `notes/claudecode_direct/prepare_direct.py` and
  `notes/matched_cborg_2026-09-13/prepare_registration.py`.
- **Builder rehearsal, no writes.** `scripts/build_api_registrations.py
  --dry-run` on the merge preview `44b8a6595c2a…` (schema 3.2.1), scratch
  label, API keys removed from the environment, inputs read from
  `launch-a21/data/`: exit 0, no warnings, same plan as M4 (3 workers, 2
  integration groups, 1 final check, 7 calls). The lead read the dry-run code
  path first and checked the evidence afterwards: `launch-a21` still at
  `673838c51` with only `?? poetry.toml`, the preview tree clean, no output
  directory created. Evidence:
  `claude-pr5808-combined-20261111/tmp/a21-builder-rehearsal-20261111/`.
  It does not give the real hashes, does not write the sizing record, and
  does not exercise the launcher's dry-run.

**CI track**

- **Chunk sharding is stopped.** AGY1's `balanced_nodeids` replayed on the
  per-test durations of run 42947560899 (out of sample): slowest of eight
  shards 7,434 s with the existing partition, 8,534 s chunked; of six, 9,351 s
  and 11,079 s. AGY2's pre-review predicted it. Kept as local commit
  `bc4649524238…` on `agy/ci-chunk-sharding-20261111`, unpushed. Recorded as
  issue 5872. Script `scripts/adhoc/replay_chunk_sharding_true_load_20261111.py`,
  output `tmp/chunk-replay-20261111/`.
- AGY1's handoff table named 23 files that do not exist (rows 9 to 31); its
  machine-written proof JSON has the real ones. Sent back for regeneration.
  Its earlier assessment had also described a seven-iteration loop in the
  journal test that is not there; it stopped correctly when it looked.
- **Where the spread comes from.** In that run shards 2 and 3 took about 0.63
  of their predicted time across nearly all files, shard 8 about 1.17: the
  runner, not the partition. The lever that scales is the shard count
  (existing partition, same durations: 8 shards 7,434 s slowest, 10 shards
  5,484 s, 12 shards 4,951 s; the longest single test is 1,416.6 s). Shard
  counts are owner decision D81. AGY2 is sizing the option read-only.
- **Lane split (A2).** AGY4's `e999aa7453ff…` on
  `agy/ci-routing-portable-split-20261111` is a faithful move of all 21
  checks into two single-process lanes; `tests/test_ci_sharding.py` passes
  (77). Neither new function has executed yet: the lane canary stopped at
  full-tree collection in the sparse checkout. AGY4 is running each once by
  node id. With eight shards this split alone changes little, because the
  slowest ordinary shard sets the wall time; it matters if the count rises.
  Nothing is pushed.

## Third round, same day

- **Shard counts stay at 8 and 6.** AGY2's sizing
  (`handoffs/agy2-shard-count-option.md`) found three things the lead's replay
  table did not show. The repository's notes record a runner pool of about 20
  jobs (`notes/ci_efficiency_review_2026-09-15.md` line 88, issue 1872); a
  pull-request run already uses 19, and ten shards plus a split lane would be
  22. The replay at other counts mixed files recorded on fast and slow
  runners, so ten shards is nearer 28 minutes than 26. And
  `tests/test_report_admission.py` (5,162.8 s) fills a shard alone from ten
  shards up, so twelve buys nothing. No change to D81 is proposed.
- **Lane split (A2) executed and parked.** On `e999aa7453ff…` both new
  functions passed once by node id on this host, run side by side: tamper
  half 654.8 s, portable half 830.5 s (JUnit files under the AGY4 worktree's
  `tmp/`, read by the lead). The lane command itself has not run end to end
  anywhere: full-tree collection needs paths the sparse checkout omits. Not
  pushed; it matters only if the ordinary shards get faster.
- **Not delegated, for the owner:** the workflow runs the complete suite on
  draft pull requests (policy from issue 1361). Of the last 46 pull-request
  runs of the build workflow, 20 ended cancelled.
- AGY2 is now checking the A21 pinned-file closure against the bytes
  (`assignments/claude-lead-agy2-a21-pinned-closure-check.md`).

## Fourth round, same day

- **A21 re-review scope is checked against the bytes.** AGY2's script and an
  independent lead script (`scripts/adhoc/lead_check_a21_pins_20261111.py`)
  agree: the M4 registration and its sizing record pin 82 repository paths
  the lead's walk can pair with a hash, all 82 equal the bytes at
  `673838c51`, and exactly six differ at the merge preview `44b8a6595`: the
  two merged schema files, `api_runner.py`, `schema_digest.py`,
  `bc1_audit.py` and `bc1_context.py`. 61 unique Python files are pinned; 57
  are unchanged. AGY2 also reports the 32 computed contract and instruction
  hashes unchanged when recomputed; the lead has not re-derived those.
- AGY2's first handoff had the right verdict and invented file names and
  hashes in its "unchanged" lists (for example a wrong hash for
  `shared_generation.py`). It was regenerated from its JSON by
  `scripts/adhoc/render_a21_pinned_closure_handoff_20261111.py`; the lead
  then checked that every path it names exists at the preview commit (bar
  the two untracked calibration notes and the new render script) and that no
  line cites a hash other than the pin for its path.
- AGY3 corrected the runbook's counts (61 pinned Python files, 57 unchanged;
  the CHORUS inputs are tracked in git; the two calibration notes are an
  open item). The lead checked its 14 abbreviated hash citations against
  the pins: all match.
- **Rule adopted for assignments from here on:** tables are generated from a
  data file by a script and the command is shown; the lead checks handoffs
  mechanically and re-derives any verdict that matters.

## Evidence kept outside git (the worktree's `tmp/` is ignored)

Hashes generated when this section was written:

- `tmp/chunk-replay-20261111/replay-42947560899.json` sha256 `ea523f94301800b676a86f2247827e02d1ee91033d573115fc5dd7fa449d27b8`
- `tmp/chunk-replay-20261111/replay-42916359440.json` sha256 `4b1583974277e0f19d85e948a951eaf863797be7b6db1c1176d3914df731a0aa`
- `tmp/chunk-replay-20261111/replay-42947560899-totals.json` sha256 `71193722ce41c1d4bc6667f31df6e4baeaae0908024e7e213a376112633d371b`
- `tmp/a21-pinned-closure-20261111/lead_independent_check.json` sha256 `41c6da03f23f4ee43d66461f878f224a4e1bc858b74a21e87dc44e1a6378d103`
- `tmp/a21-pinned-closure-20261111/a21_pinned_closure_check.json` sha256 `fe1deb62d092ece4b646c6575cdb8cbaf5e929ae850df9b165faa468c565627e`
- `claude-pr5808-combined-20261111/tmp/combined-head-20261111/identity.txt` sha256 `6fbfa9a48f43d6e8efcd35a2a738aa9e13a2f38ccbb2a61a0603292ba7fc976b`
- `claude-pr5808-combined-20261111/tmp/combined-head-20261111/canary.junit.xml` sha256 `ba0e8edc8213d36c36f5499ba538d8ce96867d43dd7657ac0123f8ccc607f404`
- `claude-pr5808-combined-20261111/tmp/combined-head-20261111/focused.junit.xml` sha256 `1d252df9df12eeb3c7890c8f9fe1703ae3c6f9d178cda21b8af0cd8777472fd0`
- `claude-pr5808-combined-20261111/tmp/combined-head-20261111/rerun.junit.xml` sha256 `89aae1f08032b29848b1cd669e1cb7cd40f7f709271b492e82bc136f8d707a8e`
- `claude-pr5808-combined-20261111/tmp/combined-head-20261111/rerun2.junit.xml` sha256 `45a0c2cd565c6ebd229742900f9bf9791166862c10b4d515b1307f536d196f37`
- `claude-pr5808-combined-20261111/tmp/combined-head-20261111/collect2.log` sha256 `d802ad1a90138b8628277be29857a06decae9aabe93dff091bbeb354e2221a5d`
- `claude-pr5808-combined-20261111/tmp/a21-builder-rehearsal-20261111/rehearsal.log` sha256 `335d8a04eea6528b8c8b693231ead6108409c0514f82a31e68fae4203367b3ed`

Written 2026-11-11T08:44:04Z.
