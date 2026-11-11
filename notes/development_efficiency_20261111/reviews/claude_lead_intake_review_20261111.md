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

## Fifth round: the owner's answers, the merge, the A21 rebuild and the one native diagnostic

**The owner's words (2026-11-11).** At 16:11:12Z, to the line about AGY4's proposed diagnostic: "yes". At 16:12:28Z, to the three numbered questions (merge PR 5808 at the named head; release the "native first" hold; the budget as an either/or): "yes yes yes", then "give decisions and recommendations". Recorded as D130 to D132 in `data-sheets-schema/notes/coordination/STATUS.md`. The budget answer does not pick a figure; the lead recommends $60 with a $51 stop and leaves it to the launch word.

**PR 5808.** Merged 16:14:19Z as `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` (merge commit, `--match-head-commit 6792947e…`). Its tree `3bb94f5c2abc5e7ac9f7f333949597f1a7e43c9d` equals the tested preview's. Main CI run 43056320723 on it is green on all 18 jobs (16:14Z to 16:57Z), including the push-only `schema-examples` at 3.2.1.

**A21 rebuild** (`scripts/adhoc/a21_rebuild_on_merged_main_20261111.sh`; logs beside the packet in `d4d-executions/plans/`).
- `launch-a21` moved from M4 to the merge commit; status `?? poetry.toml` only. `poetry install` was not run: the only lock change is the content hash, for a dependency restricted to Python below 3.11, and the launch base runs 3.13.
- Label `2026-11-11a_claude-opus-5-api-bc1-a21_rep1`: roster `d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63`, registration `55691023e1d75c3bf5f9df09dcb524b4536870b93a4a3dde67306276f082aa1a`, sizing `0ae32356404e52d28acf0ff9ae8e39707947664df7506104a52fbab438465c87`.
- Offline `--check` passed; the launcher dry-run of the exact batch command exited 0 and wrote nothing.
- The lead's leaf comparison against M4 (`scripts/adhoc/a21_registration_leaf_diff_20261111.py`, output `tmp/a21-rebuild-review-20261111/leaf_diff_m4_vs_rebuild.json`): registration 367 to 351 leaves, 14 changed, 2 added, 18 removed; every one is a hash of one of six files, a schema byte count, the label, or the term-policy context moving from v1 to v2.
- AGY2's independent identity review: 0 unexplained differences; its 173 leaf differences equal the lead's value for value; the lead checked the line numbers it cites.
- The Codex helper's payload review (`plans/reviews/a21_registration_review_2026-11-11/codex_payload_review.md`): 0 unexplained payload bytes over 20 requests; re-priced expected $31.71, at caps $43.23 and $44.31, worst call $8.65.
- Its tree-preservation gate failed on one ignored cache file born 16:45:05Z in the launch base. The lead had AGY3 running `--help` commands there at that time, and `python -m <package>` writes exactly such a file (checked on a scratch package). The lead's scheduling error.
- Launch packet: `d4d-executions/plans/a21_launch_packet_2026-11-11.md`.

**Three errors in AGY3's runbook, found by executing it.** The monitoring command exits 1 (issue 5873; the 2026-11-05 packet had the same line); the post-run list names files the code does not write; and the import proof expects a `__file__` that a namespace package does not have.

**The one native diagnostic (D132).** Run by `scripts/adhoc/run_native_cpu_monitoring_once_20261111.sh` with `native_private_config_rearm_restore_20261111.py`.
- The run needs `d4d.ciRepositoryUrl` in the private composition's Git config, which the composer's write-once cleanup had removed. The helper set it and restored it, as the previous lead's `native_wp1_private_config_20261111.py` did for 3cc113. Armed 16:38:01Z to 16:45:46Z; the config is back at `95a1f7d1…`.
- A 12-second `canary` kind passed through the lead's shell first. The diagnostic started at 16:38:13Z at 1.44 load per CPU; the maximum during the run was 2.74.
- It completed normally: 452.4 s, return code 0, cleanup verified, one test passed, both phase-metric files written.
- Outcome `genuine_refusal` ("subscription observation is stale or future-dated"), no reservation boundary. Launch-phase process CPU 243.40 s (458887: 237.96 s; 3cc113: 275.66 s); fixture 110.88 s (119.92 s; 149.13 s).
- Reading: the earlier 382f cutoff was contention, not a regression; and in this instrumented run the launch phase's CPU alone exceeds the 210-second target, so lower host load would not have produced a reservation here. The figure includes the observer's own overhead (13.3 million audit events), so it does not bound an uninstrumented launch. One contended sample; no quiet-host or speedup claim.
- AGY4's packet agreed on the invocation but cited defaults and variable names that are not in the code; nothing was run from it.

Written 2026-11-11T16:58:25Z.

## Sixth round: the last two worker notes, and a correction to the lead's first reading

- **Main CI on the merge commit is green** (run 43056320723, 18 jobs).
- **AGY3's post-run checklist** (`handoffs/agy3-a21-post-run-checklist.md`): its tables of output directories and file names agree with the code, the archived 10-22a listing and the ledger-name formula (the formula reproduces `90e59e50c9d423fe` for 10-22a and gives `e4c1f42d7aa2a317` for the new label). Its after-run command lines do not all exist as written: `d4d api verdict` has no `--registration` or `--json` and requires `--canary-baseline`; `d4d runs check` has no `--require-complete`; `d4d provenance validate-records` takes only `--strict` and `--label`; and `check_final_generation_products_20261110.py` is a schema-product comparison with no record arguments. The launch packet carries only lines the lead checked against `--help`, which are those of `docs/final-generation-acceptance.md` sections 3 to 5.
- **AGY4's analysis of the diagnostic** (`handoffs/agy4-diagnostic-result-analysis.md`) corrects the lead's first reading. Equal launch CPU on 382f and 458887 does not mean no change: 382f does more in that time. The lead re-derived the key rows with `scripts/adhoc/lead_check_freshness_rows_20261111.py`:

  | Source | Refused at | Capture age at the refusal | Limit there |
  |---|---|---:|---:|
  | `3cc113e2606c` | dispatch check | 318.89 s | 300 s |
  | `458887766eff` | second dispatch check | 334.86 s | 300 s |
  | `382f0dfd1ce8` | pre-reservation check, after three passed dispatch checks (38.53 s, 259.40 s, 279.56 s) | 306.53 s | 210 s |

  382f is the first source to reach the pre-reservation check; it arrives 96.5 s late. Its launch starts 10.8 s after capture, so with wall time equal to CPU time this instrumented launch would still need about 44 s less CPU.
- AGY4 attributes the launch CPU mostly to repeated full registration and preparer verification (nine `shared_registration_verified` calls, 108 s inclusive) and one controller prewarm (64 s inclusive), and proposes a static audit of those call sites as a next step that needs no run. Those attributions are AGY4's, from its script's JSON; the lead has not re-derived them. Its text names PR 5835 as the source of 382f's change, which is wrong (5835 is the vocabulary-test fix); the change is the capture work in draft 5857.
- AGY3 and AGY4 were both interrupted by a network error for about 2.5 hours and resumed on a relayed message.

**Evidence kept outside git, hashed when this section was written:**

- `plans/a21_launch_packet_2026-11-11.md` sha256 `5d63c4a4817bc29c9d55d888c97132f04141bc97a0f96f77eb20c39ef9e0a1f1`
- `plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.preflight.log` sha256 `1523bc1fd80155bdeb8fc1e5a2da7a7136c485fc9f02d7bfc60f177e6d85410e`
- `…builder.log` sha256 `16aa43656587f3551d4b95740607576f058673d039dbd69d6202b4d10ee3d125`
- `…check.log` sha256 `e1c7c0f8262f016743752c9ff7ddc85f0447450d334a3f7735181b1d9fe53994`
- `…dryrun.log` sha256 `3b24c2a31f3b576212df3d99c4edb4af9daacfc6625ba5e7b5b682cbad8a237b`
- `tmp/a21-rebuild-review-20261111/leaf_diff_m4_vs_rebuild.json` sha256 `c6f4ecee267cfc686acd0fce4825bd39876193cfd9fb07f7ab6b95ae6d7e7c7f`
- `tmp/a21-rebuild-review-20261111/agy2/a21_rebuild_identity_review.json` sha256 `23f96bb28e2c4b186239180217f67349b50e11947f5e5c453d5b44ec94ba4119`
- `plans/reviews/a21_registration_review_2026-11-11/codex_payload_review.md` sha256 `366b79edc1f3faaec3256dbffa4b659677007ff1974d275f5372fa31f72d9b8c`
- `plans/reviews/a21_registration_review_2026-11-11/evidence-manifest.json` sha256 `d56c652c697e8e591e2d85ab2cc149b6b2c81f4713a962351d0479713fb9cc12`
- `scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111.supervisor.json` sha256 `32404f066fcbc25341f3f25e5d7da0dc59ea2588c66afd93c47116114e1743ac`
- `…/phase-metrics/67941-diagnostic.json` sha256 `33b032291d891f06249596da823d2a6f26d87d59317388f078b3a399ffc21cba`
- `…/phase-metrics/67941-measurement.json` sha256 `12cba82d359f98d39220db521d8920130da94f863b554d265c0116736738a31d`
- `scratch-native-u1u3/u3m/lead-cpu-monitoring-rerun-382f0dfd1ce8-20261111.log` sha256 `ca316e23d3b543a4f121af3a3f3892fe87c05a1aba33666beafb7eff2e45389a`
- `tmp/diagnostic-result-20261111/result-analysis.json` sha256 `4b104257ec4a752c71adddc1ddf739893dafdd7a83e3f67fbb18de27e5875c6f`

Written 2026-11-11T19:51:51Z.

## Seventh round: the stop rule rehearsed offline

The launch packet's stop command and the lead's watcher had never been exercised. `scripts/adhoc/a21_stop_rehearsal_20261111.sh` rehearses them in a sparse scratch checkout of the merge commit (`d4d-executions/claude-a21-stop-rehearsal-20261111`, `src` and `scripts` only), against `a21_stop_rehearsal_fake_sweep_20261111.py`, a stand-in that claims a label prefix with the production `run_lock.acquire` and then sleeps. No provider call; the launch base's status and lock directory were unchanged.

- **First attempt, two failures, both the lead's.** The rehearsal script waited on its own background process (a command substitution held open), and after that was fixed the launcher refused the scratch checkout because the borrowed environment's packages resolve to `launch-a21`. In that attempt the watcher also reported a sweep still running after the stand-in had been killed by hand: it treated any status output other than "No sweep is running." as a live sweep, and a stopped sweep leaves a stale lock. On launch day that would have kept the watcher from ever reporting the run as ended after a stop or a crash.
- **Fixes.** The watcher now counts only the status lines that list a live sweep for its own prefix and reports a stale lock separately. For the rehearsal only, it runs `d4d api stop` without the launcher.
- **Second attempt, three cases pass.** Dollar trigger: the readout exits 1, the stop command signals the stand-in, the watcher confirms no live sweep and exits 21. Clock: the same after 13 s, exit 22. Launcher: the packet's exact stop command, through the launcher, in the real launch base with nothing running: exit 0, "No running sweep holds", no signal sent.
- **Not exercised:** the launcher form of the stop command against a live process, and stopping a real generation run in the middle of a provider call.
- The readout priced the copied 10-22a ledger at $15.17 in the scratch checkout and $17.95 in place: the difference is the abandoned-attempts journal beside the original, which was not copied.

Evidence: `claude-a21-stop-rehearsal-20261111/rehearsal-logs/result.txt` sha256 `03da095fcfce34637d656911387fda684cc398fba7e5495d8b4be7b385645fee`. Launch packet after this round: sha256 `8f365c8db05512b85697661d45ae874ff052019a01b8aacf5cd0d4183b2f7447`.

Written 2026-11-11T20:09:19Z.

## Eighth round: the native launch verification audit (Codex helper)

Asked, after the diagnostic, whether any of the repeated verifications in one launch on 382f could safely be replaced by the narrowed recheck the capture work introduced (`assignments/claude-lead-codex-native-launch-verification-audit.md`). Source reading only; no run.

- `handoffs/codex-native-launch-verification-audit.md` (sha256 `cda53553a43331051c684231a3f27ebb4625043283d9ef0ba0ed7b87a44f920f`) confirms AGY4's counts and totals from the measurement rows (nine shared-registration, fourteen execution and twenty-one preparation verifications, one prewarm) and corrects several of AGY4's details, including its estimate of 40 to 50 s saved, which the rows do not establish.
- **Finding: no additional call site for which the narrowed recheck is demonstrably sufficient. Proven savings 0 s against about 44.2 s needed.** On the available evidence this route cannot reach the 210-second target on its own. It is not a proof that every repeat is irreducible: some intervals remain unproved and the prewarm's 57 s outside monitored children has no applicable retained profile.
- It also names a source-level counterexample to treating the narrowed recheck as equivalent in general (the environment's `VIRTUAL_ENV` is derived from `sys.prefix`, which the narrowed path does not re-derive); unexecuted, and not evidence that the diagnostic changed it.
- The lead's reading: the measurement confirms where the launch time goes and does not change the earlier conclusion that no material, safely established reduction is available by this route. The native target stays unmet; nothing on the API route depends on it.

Written 2026-11-11T20:19:53Z.
