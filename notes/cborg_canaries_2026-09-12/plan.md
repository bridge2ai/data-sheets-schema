# CBORG rescore and v9 generation canary — 2026-09-12

**Current evaluation condition:** [CBORG with execution-metadata provenance](../reference_rescore_2026-09-12_cborg_runtime/plan.md). The preliminary condition below was superseded before fill after four CLI sessions; all original evidence remains on disk. The separate v9 generation canary is complete.

The user requested “rescore with CBORG API” and separately approved adding a v9 generation canary using existing source bundles. This is a new provider condition beside the completed September 11 reference run. Earlier evaluations, failed attempts and semantic errata remain unchanged.

## Evaluation registration

- Cohort: the same 24 public v7/v8 full D4Ds, both semantic rubrics; 48 primary ratings plus eight rubric10 repeat ratings (56 planned).
- Manifest: `notes/reference_rescore_2026-09-12_cborg/manifest.json`; SHA256 `e71b8805b7fde90b5e64e23ba1c1f346f2f17e33fe49df7c98c9e885aeec1501`.
- Definitions, rubric text, schemas, complete scoring prompts and 24 input byte hashes match the prior registered instrument. The new manifest preserves 258 prior evaluation files.
- Model selector: `claude-opus-5[1m]`, effort high, temperature unspecified. The accepted runtime must identify `claude-opus-5` with the same existing alias-evidence checks.
- Transport: Claude Code 2.1.269 with the existing isolated runner through `https://api.cborg.lbl.gov`. The adapter uses `CBORG_API_KEY` in memory, selects the CBORG base URL explicitly, and clears inherited Anthropic model/auth overrides and alternate cloud-provider switches. A fresh CLI configuration directory lives inside each isolated workspace; safe/restricted modes and exact-validator tool permissions remain. Runtime acceptance requires the explicit API-key source and all required tools.
- Budget: the registered CLI maximum remains $5 per attempt. Original usage and excluded attempts will be retained; CLI-reported cost is not an independently reconciled CBORG invoice.
- Canary: CHORUS v7 rep1, rubric10, rating1. It uses the same adapter, foreground shell environment, sequential launch mode and output locations as the fill. No remaining rating starts until exact output, schema, arithmetic, source-aligned item identities, runtime identity, quoted definition, final Write binding and an inspected review pass.
- No automatic retries. A failed attempt stops new launches and is retained. A diagnosed retry is a fresh original measurement under its registered condition.
- The initial fill plan was sequential. The dated scheduler amendment below supersedes that launch mode after a separate scheduler canary. The planned output paths are separate from every prior condition.
- Rubric20 Q19 still allows complete textual provenance or a graph. The old semantic errata are preserved and do not prejudge the new measurements. Mechanical acceptance alone cannot make a score rubric-conformant; inspect new Q19 rationales before final manuscript interpretation.

## Generation registration

- One CHORUS record only, condition `generic_v9`, baseline arm, label `2026-09-12_claude-opus-5-api-generic-v9_rep1`.
- Use the existing `data/preprocessed/concatenated/CHORUS_preprocessed.txt` bundle and recorded chunk/source metadata. No downloads or factual reuse from an earlier D4D.
- Use the generic v9 prompt already on main, current schemas and current check instruments. Do not change prompt/schema/checker content during this canary.
- Use CBORG's unprefixed `claude-opus-5` route and the generation runner's recorded adaptive-thinking/default-effort configuration. This differs from the evaluation CLI's requested high effort and will not be conflated with it.
- Run through `d4d api batch` restricted to one project and one replicate, with the current v7 baseline `2026-09-01_claude-opus-5-api-generic-v7`. Retain artifacts and the actual gate verdict even if the canary fails.
- The current offline plan and model catalogue observation are in [v9_generation_plan.json](v9_generation_plan.json). Listed input-token counts are estimates; conditional repair/re-address/report calls and returned usage will be recorded by the existing runner.
- The user approved a canary only. Do not expand to a v9 production cohort without further scope authorization. A generated canary record is not a released manuscript cohort.

## Commands

Run in the project Poetry environment, from the repository root. The CBORG key must be inherited as an environment variable, never written to a command, manifest or log.

```bash
python scripts/reference_rescore_cborg.py canary
# Inspect the original output and trace; write the canary review before acceptance.
python scripts/reference_rescore_cborg.py accept-canary
python scripts/reference_rescore_cborg_batch.py pilot
# Review its original output and scheduler evidence, then accept it.
python scripts/reference_rescore_cborg_batch.py accept-pilot
python scripts/reference_rescore_cborg_batch.py remaining
python scripts/reference_rescore_cborg.py report
python scripts/reference_rescore_cborg.py audit
```

The generation launch clears a potentially inherited direct Anthropic key so the existing API client's credential precedence selects CBORG:

```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN d4d api batch --projects CHORUS --replicates 1 --condition generic_v9 --label-prefix 2026-09-12_claude-opus-5-api-generic-v9 --canary-baseline 2026-09-01_claude-opus-5-api-generic-v7 --yes
```

## Pre-spend checks

The CBORG model catalogue lists `claude-opus-5`; its observed route is `vertex_ai/claude-opus-5`, with 1,000,000 input and 128,000 output token limits. These are pre-run catalogue observations, not a guarantee about the identity returned by a later request. Endpoint/auth setup follows [CBORG's Claude Code documentation](https://cborg.lbl.gov/tools_claudecode/).

The new evaluation registration exactly matches both prior instrument definitions and all 24 input hashes. The generation batch dry-run resolves exactly one CHORUS job and makes no model calls. Offline provider-selection and inherited-runner tests are required before the paid canaries.


## Pre-spend review passed

Codex adversarial review approved published commit `0c9592373` with no supported P1/P2 findings. It independently verified all 36 pinned-file hashes, 258 preserved evaluations and 56 complete prompts. Offline tests: 161 passed. Canonical prompt check: all 15 pins passed. Live-provenance check: 277 records checked, 195 subject to the requirement, zero failing. The bundle audit passed for all rebuildable bundles and chunk manifests; unrelated bundle types without a reconstruction route remain explicitly unchecked.

The separate v9 input pins and pre-run CHORUS baseline are recorded in `v9_input_pins.json` and `v9_baseline_before_run.json`. The seven gated baseline defect counts are zero; the baseline report basis is one measured replicate and two vacuous replicates. This review authorizes execution of the already user-approved canaries; it does not assert their live results.


## Write-tool correction before a fresh canary (#1340)

The first CBORG canary ended without an output file after $2.433457 of CLI-reported usage. Its init advertised only Bash and Read: adding `--bare` removed Write from the available tool set. The evaluator's attempted shell writes were denied as intended. The failed attempt and original registration remain preserved, with no accepted rating.

A real installed-CLI probe against a local rejecting HTTP server reproduced the missing Write tool with bare mode and verified Read/Write/Bash without it, using fake credentials and no model inference. The adapter now uses safe/restricted mode with a fresh CLI configuration directory, explicit CBORG credentials and startup identity/tool checks. The seven adapter tests pass. The scoring definitions, all 56 complete prompts, input bytes, schemas and five-dollar attempt control are unchanged. A fresh canary must pass before any fill; the denied shell payload will never be treated as an accepted evaluation. The original pre-spend review remains as the historical review of the earlier launch configuration.


## Four-worker scheduler amendment — 2026-09-12

The first successful evaluation canary is accepted at 35/50 (70.0% on both
bases), with all 50 source item names and original Write bytes verified.
Its CLI-reported cost is $2.80151575. The failed bare-mode attempt remains
excluded. See the separately retained canary review and acceptance.

The successful session took 9.7 minutes. To complete the authorized cohort
with less elapsed time, `batch_registration.json` registers a four-worker
controller without editing the frozen scoring manifest or executable.
This supersedes the initial sequential fill plan, whose exact bytes are
archived with their hash. It is an execution-condition amendment, not a
new rubric or an added rating.

Before fan-out, CHORUS v7 rep1 rubric10 rating2, already among the planned
eight repeats, must run alone through this same controller with its worker
limit still set to four. Review must verify the persisted original Write,
explicit CBORG initialization, schema/echo/model gates and controller logs.
Only matching reviewed acceptance opens the rest of the queue.

The controller waits for each frozen runner's startup message before
launching the next worker, so the shared canary gate is not contended. It
retains each process's own workspace, stops new launches on an observed
failure, drains in-flight sessions and refuses automatic retries. One pilot
cannot establish provider rate-limit behavior under load, cross-item
contention, repeatability or long-tail success. No additional v9 generation
or download is part of this amendment.


The first scheduler review found #1341: shared foreground process groups
could interrupt workers before their original runner wrote receipts. The
corrected scheduler gives each worker a separate session and handles
controller SIGINT/SIGTERM as a request to stop new launches and drain. The
stopped controller result is retained. The initial scheduler and its
registration are archived unchanged; no model calls occurred under them.
Offline process-group interruption tests cover candidate and receipt
retention for all four active workers and non-launch of the fifth job.
A forced kill or host loss is outside this graceful-drain guarantee.


The second scheduler review verified graceful draining and found #1342:
a stop observed while preparing launch arguments could still reach `Popen`.
The corrected launch prepares arguments first and serializes stop handling
with the short dequeue/spawn decision. A stopped job remains queued. Worker
startup restores SIGINT/SIGTERM handling before any evaluator preflight.
Deterministic preparation-boundary tests cover both signals, in addition to
the four-worker evidence-retention tests. No scheduler model calls have
occurred; the scoring manifest and all earlier artifacts remain unchanged.


## Scheduler pilot identity rejection and one reviewed retry (#1343)

The first scheduler pilot completed a CLI session but its JSON named Opus
4.5 while its runtime trace and CLI canonical identity named Opus 5. The
unchanged identity gate rejected it; its attempted 34/50 and $2.4216595 of
CLI usage are retained and excluded. No other rating launched. The prior
scheduler registration, code, launch record and approval are archived or
retained unchanged. A separate registration allows exactly one fresh
original retry against the precise hashed failed-attempt history. An
additional attempt, changed evidence, missing terminal usage or a successful
prior receipt invalidates the retry gate. This does not change prompts,
definitions, inputs, model identity criteria or the 56-rating scope.
