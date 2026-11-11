# Prompt for the incoming Claude lead

Handoff prepared 2026-11-11, approximately 07:21 UTC (2026-11-10 evening America/Los_Angeles). Refresh live state before acting.

You are the new lead for the D4D repository and its local coding workers. The user explicitly requested this transfer. The outgoing lead Codex session becomes an additional worker helper. Take ownership of monitoring, delegation, integration, review and concise user updates. Do not restart the project or repeat completed checks.

## Objective and priorities

The user wants final D4D generation unblocked, and the D4D development/test/CI loop made faster. Keep these two tracks separate:

1. Finish only the work needed for the selected API-only final generation route. Broader native acceptance, schema/Core expansion, historical migration, AI-readiness scoring and semantic exchange/RO-Crate repair **must not become prerequisites for this run**.
2. Continue justified native-development and CI efficiency work separately. Improvements have shipped, but native freshness is still unproved. Do not fill idle slots with speculative optimizations or repeated expensive failures.

The user is frustrated by workers waiting without review or reassignment. Poll live worker tabs during active work, collect completed handoffs promptly, review them, and assign useful independent tasks. A stale STATUS entry or terminal viewport alone is not proof of a process's current state. Do not claim unattended monitoring between inactive turns. The outgoing lead acknowledged a monitoring gap and restarted the assignments below.

## First actions

1. Read this file and the current consolidated report linked below; refresh the five worker terminals and GitHub heads.
2. Collect AGY2's completed PR5808 review and AGY3's API-only blocker reconciliation. These are new worker assessments awaiting lead review, not automatically accepted decisions. AGY2's visible verdict is ready for merge decision; verify its full report, retained/deferred findings and exact head before presenting approval.
3. Review AGY1's next CI bottleneck recommendation and AGY4's diagnostic-evidence assessment when they finish. Both were read-only tasks; no new runtime or implementation is released by their reports.
4. If PR5808 is ready, present the exact PR/head for the user's separate merge approval. Approval for earlier PRs does not carry over. Then make the selected route's next action concrete and reviewable; do not request vague blanket approval.
5. Use the outgoing lead Codex helper for a bounded review, implementation slice, evidence reconciliation or provenance question. Avoid two agents editing the same branch/worktree.

## Session directory and coordination

Repository: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`

Execution/worktree root: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions`

GitHub: https://github.com/bridge2ai/data-sheets-schema

The primary checkout is stale local main at `384993879fba3b6f4e83b1c5b25bf405030976b1`, with a dirty `aurelian` submodule and substantial untracked work. Do not switch, reset, clean, or pull this shared checkout. Remote main was independently verified at `925d726d67cdd03fe28fdeafdde60fa27df57205`; refresh it read-only before decisions. A PR's `baseRefOid` may still show its older base snapshot.

| Worker | Verified Terminal window / TTY | Current assignment and snapshot |
| --- | --- | --- |
| AGY1 | 3155 / `/dev/ttys034` | Active: identify one next CI critical-path improvement from saved successful runs and workflow/source, preserving coverage and shard counts. Separate queue delay from execution. Read-only; no tests, edits, CI triggers, push or merge. Latest viewport was investigating repeated catalog derivation. |
| AGY2 | 6245 / `/dev/ttys048` | Finishing/finished read-only adversarial PR5808 readiness review. Visible verdict: ready for merge decision, zero remaining defects found. Root supplied live CI/head/main identities. Review its full conclusion, including distinction between fixes in this PR and deferred historical findings. |
| AGY3 | 341 / `/dev/ttys002` | Completed read-only API-only critical-path reconciliation. Proposed PR5808 approval followed by exact post-merge route/registration/preflight preparation and a separately authorized A21 canary. Its route-specific owner-decision interpretation still needs lead review. |
| AGY4 | 6921 / `/dev/ttys010` | Active: inspect preserved integrated diagnostic deadline evidence, identify last proved boundary and unknowns, and recommend the cheapest useful next witness. No imports, reruns, new helper, evidence rewrite or timing claim. |
| Native Codex | 339 / `/dev/ttys001` | Idle after completed source assessment: no evidence-backed material optimization supported now; defer repeated-tokenization microchange. Clean PR5871 source/evidence preserved. |
| Outgoing lead Codex, now helper | Codex thread `01a1c340-fad4-7642-8484-a0b02c04c143`; terminal not identified | This session. Available for a bounded assignment from you. Holds detailed knowledge of recent reviews, report publication and evidence. |

Native Codex thread: `01a0f037-6988-7731-a35d-63532027e07a`.

If available, use `codex_tui` list/read/send tools for Codex threads. Message limit is 1,000 UTF-8 bytes. Local AGY terminals are running the `agy` executable; a restart as `agy-work` is not currently needed. If a session later needs restart, preserve its state and verify the actual shell/session first.

Existing provenance helpers (read them before use):

- Fleet reader: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-schema-alignment-review-20261110/scripts/adhoc/monitor_worker_terminals_20261110.applescript`. Reads five exact windows/TTYs, approximately 1,500 visible characters each. Successful in the latest checks.
- Single-tab reader for AGY3/4: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/read_native_worker_tab_20261111.applescript`, role argument, up to 3,500 visible characters.
- Task relay: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110/scripts/adhoc/message_readiness_worker_20261110.applescript`, role and quoted message arguments. Verify foreground worker and TTY first so instructions cannot land in an ordinary shell.
- Queued guidance: same directory, `flush_readiness_worker_queue_20261110.applescript`, role argument. It verifies the visible queued-message shortcut before sending Alt-M. A successful relay may merely queue guidance until this shortcut is used. If it refuses because the shortcut is absent, no key was sent; refresh before retrying.

Shared historical coordination: `data-sheets-schema/notes/coordination/STATUS.md`. Its chronology is not strictly sorted. Include ignored/untracked files in any search used to establish absence; scope searches to relevant notes/packets rather than scanning every execution tree.

## Authorization and operating constraints

- The user explicitly approved **local AI-worker coordination without per-message approval**. This covers tasks/status/review messages among these local workers. Human messages remain governed by per-action permission. Never use notifying mentions without specific permission.
- Branch before edits; PR required; separate adversarial read-only review; every concrete finding becomes a GitHub issue before repair/disposition. Issues/PRs in this user-owned repository have the standing communication exception. No force push or rebase of shared work.
- **Each merge needs explicit approval for that PR in the conversation.** Only #5814 and #5835 have the relevant recent specific approvals; both are already merged. There is no current merge approval for #5808, #5858, #5871 or the other native drafts.
- No real native executable/provider/model call or final generation has been run in this efficiency work. Current worker tasks do not authorize such a launch, another genuine diagnostic, a broad cohort, private-config rearming, or automatic retries.
- Preserve protected API/prompts/schema/canonical-hash/scanner boundaries. Any previously approved private composition is distinct from production protected-file installation and scanner decisions. Determine applicability to the selected route rather than importing native gates into API-only generation.
- Canary first, same path as intended batch; verify persisted outputs, not exit codes. Free preflight before paid execution. Historical budgets/approvals must be checked against the exact current route/packet before use.
- Save helper scripts in repository `scripts/adhoc/` and retain provenance. Do not create working state in `/tmp`. Existing temporary PR body files are convenience copies; authoritative work is committed or durable in the worktrees.
- Preserve all source worktrees, raw evidence, failed attempts, manifests and untracked handoffs. Do not perform branch/worktree cleanup while those remain active or needed as evidence. Never stage all existing untracked files.
- Earlier PFAS/CultureBotAI temporary pauses were fully resumed. No outstanding resumption action remains. Do not signal unrelated jobs.

## Current authoritative report and publication

Report worktree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111`

Branch: `codex/native-efficiency-results-20261111`

Published head before this handoff: `e2ebdf01f39c0b1d6c97ddceddc72b2ac9d68f31`

Draft PR5858: https://github.com/bridge2ai/data-sheets-schema/pull/5858

Current report:
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/lead-results.md`

Report SHA256: `84d2e6cefb1a88a5b955ca6cf8d203d5d4a7980eda3b955cbede3b949c408ccd`.

The latest report delta was independently reviewed, committed and pushed. PR description and separate exact-head COMMENT review were published and read back successfully. Full duplicate CI42977148945 is confirmed cancelled; cheap large-file CI42977148944 succeeded. No green full-CI claim for this head. Older cancelled runs and historical snapshots retain their original meaning.

This handoff file is a new local coordination artifact in the existing non-main report worktree. Check its git status before deciding whether to include it in the existing report PR; do not assume it was part of e2ebdf01.

## Final-generation PR5808

URL: https://github.com/bridge2ai/data-sheets-schema/pull/5808

Head: `6792947ea6558d10c85106065b023cb57838835a`; original base `7233f193ad102a8488b31ec7333662c8fefaa996`. Last live GitHub state: open, non-draft, CLEAN/MERGEABLE; all applicable checks succeeded. Those checks did not rerun against newer main925d.

Worktree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110`

Read `notes/final_generation_readiness_20261110/RESULTS.md`, `REVIEW_LEDGER.md`, and `docs/final-generation-acceptance.md` there.

Scope: scalar collection-type prose correction, schema3.2.1 product/release synchronization, focused full/Core/HTML and receipt/source-review regressions, and operator acceptance guidance. Full YAML remains authoritative; Core omissions and broader exchange defects are not hidden by schema validity.

Evidence: 24 schema/release checks, 6 integrated focused cases, positive persisted-output canary, generated-product equivalence. Global specificity scanner still exits1 for nine existing findings #5582–#5590 in historical controllers unchanged from base. Their disposition is retained/deferred; do not call the global audit clean or say every ledger issue was fixed inside this PR.

Main925d's intervening file changes do not overlap PR5808's changed files; root checked the two main test diffs. AGY2 is checking behavioral compatibility. No new combined-head full suite has run.

AGY3's proposed next step is to freeze A21 CHORUS generic_v10/BC1 registration and `shared_generation_batch_roster_v1` at exact post-merge main, complete offline check/dry-run, and present concrete canary command plus registration hash for explicit launch approval. It cited a $60 slice/$51 stop/3h cap and no `--canary-baseline`; **these are worker-reported historical constraints, not fresh launch permission**. Review the underlying owner packet and whether D129/protected postimage/D128 decisions apply to the chosen API-only route. The proposed 15-run batch cannot bypass the real canary or its own authorization.

## Efficiency work already completed

- PR5814 merged with explicit approval at `95969b5d508577c6e740a16e7acc364379bb40b6`: CI timing weights refreshed from eight artifacts, retaining coverage and shard counts. PR CI33m17 versus reference36m37; one observed comparison is not causal proof. Main CI46m28. PR has eight ordinary shards; main six.
- PR5835 merged with explicit approval at `925d726d67cdd03fe28fdeafdde60fa27df57205`: explicit-profile vocabulary test fix and CI evidence corrections; full CI passed, approximately33 minutes. Its old branch was deleted; active evidence worktree retained.
- Matched observer diagnostic: fixture CPU149.665813→149.126013s; launch CPU581.237720→275.663033s, 52.6% lower; combined41.9% lower. Same frozen source/rosters. Both refused stale evidence. No comparable live-generation or quiet-host wall-time claim. Do not repeat this measurement.
- Import-fact reuse: 45 targeted cases passed; retained exact-byte facts reduce repeated eligible graph CPU in a component comparison. No integrated freshness benefit established.
- Integrated genuine software capture/readback check passed at source382f: one test,286.671s; suite300.431s; outer318.631411s. Positive readback/order and real stage-root mutation refusal; not reservation/native generation.

## Latest native candidate: draft PR5871

URL: https://github.com/bridge2ai/data-sheets-schema/pull/5871

Worktree: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-postaccept-fusion-20261111`

Branch: `codex/native-postaccept-fusion-20261111`; clean published head `1a137b58860416a31618de44173180d021dfcc61`, base `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b` on `codex/native-capture-ast-integration-20261111` (draft5857).

Implementation combines adjacent accepted-route verification with the lease's full reconstruction. It reduces full post-acceptance reconstructions before first reservation from three to two on that selected route, retaining fresh full production, immutable original comparison, authorization/source/platform checks and lock through reservation. Public/direct routes stay cold. One intermediate sample is removed; do not claim detection of transient drift restored before remaining samples or strict complete observational equivalence.

All19 fixed component singletons passed on clean `64c612133b5b8fa0972ec2b10dc821f4d81e65c6`; publication adds reports only, executable bytes unchanged. Each helper took3.185–6.722s with10s work/20s cleanup allowance, a30s acceptance budget rather than a new independent hard alarm. Registration/source/controller prerequisites are isolated. No actual native executable/provider/model calls.

Evidence report:
`notes/reviews/native_postaccept_fusion_results_20261111.md` in the worktree; SHA256 `4571b1c41dc478dfd90fc1456deaf083b65d05242c972537903848c196d0bd5e`.

Raw evidence: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-postaccept-fusion-v4-20261111/`.

Manifest `notes/reviews/native_postaccept_fusion_v4_evidence_20261111.sha256`, SHA256 `46ce69b33ea44da93eac41a38ae5373a638d56357a263a3c4f40094079b43c88`; all415 entries independently verified. This is not415 tests. Twenty scripted captures include two intentional limit refusals. Normal deadline completion, peer cleanup and selected source stability verified.

Issues5867–5870 record fixture, portability and runner repairs, addressed in this draft. Earlier setup failures and v1/v2/v3 evidence remain preserved. Source review and separate PR review completed. Full CI42976790438 confirmed cancelled; cheap file check42976790492 succeeded. No merge approval or full green CI.

## Native uncertainty and stop boundary

The subsequent integrated diagnostic on382f hit its900s budget with forced cleanup and no final freshness result. Inner returned124/worker-15; outer125 at894.469324s; supervisor125 at894.533025s. Cleanup certification false; no observed survivors does not prove every possible orphan absent. Final diagnostic/measurement/JUnit were not produced, and phase metrics are empty. This is **not** a genuine stale refusal, speedup/regression measurement, or reached-reservation result. Issue5865 remains open. AGY4 is examining retained evidence, not rerunning it.

Raw interrupted diagnostic:
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`

Private configuration was restored on2026-11-11T06:08:07Z and independently checked. Both files below are173 bytes, mode0644, SHA256 `95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1`:

- `scratch-native-u1u3/u3m/composition-382f0dfd1ce8/tree/.git/config`
- sibling `config.bak-u3m-20261109`

Do not rearm/retry or mint another identity just to repeat failed setup. Restoration does not retroactively certify diagnostic cleanup.

U3K-F1 / issues5722 and5836 remain open. No cheaper complete verifier preserving fresh preparation, policy, permission, effective system, command and environment has been established. Latest source-only review found only a small duplicate-tokenization possibility in `native_shared_policy.py`, with no measured material benefit; defer it. Prewarm checks protect distinct mutation/lifetime intervals and cannot simply be removed.

The native target remains genuine freshness and `reached_reservation_without_effect` within210 seconds at unchanged300-second age/90-second margin. Even that is a boundary proof, not actual generation. Completion/failure cohorts and wider native acceptance remain stopped. These are not API-only final-generation prerequisites.

## Other preserved native PRs and source references

Consult PR5858's report for full dispositions rather than re-reviewing the entire stack by default: drafts5839,5840,5841,5851,5852,5853,5855,5857,5866. All remain separate from approved merged CI work; many full CI runs were intentionally cancelled. No inferred green status.

Core preserved paths:

- `codex-native-u1u3`: frozen integrated source382f.
- `codex-native-wp1-preparation-20261111`: tools7043f0be145d5a0922cdbd3a73f099e6e9a12a3c.
- `codex-native-capture-cleanup-20261111`: draft5866 at8bb1e949ccf3ee6ce5698af301238a01935676b5.
- Report reviews: `notes/development_efficiency_20261111/reviews/capture_runtime_382f.md`, `diagnostic_runtime_382f.md`, and `remaining_postaccept_feasibility.md` in the report worktree.

## How to use the outgoing lead as your helper

Assign one concrete bounded task with target branch/worktree, expected artifact and validation scope. This Codex helper should report evidence and findings back to you, not independently direct the other workers, merge, alter protected files, launch generation, or expand the test campaign. It can clarify the recent report/PR/evidence history without repeating the research. You own the next coordination and approval decisions.
