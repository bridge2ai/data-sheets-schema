# Development efficiency: implementation and measured results

Updated 2026-11-11 05:43 UTC. CI improvements have shipped. Native optimization has a reviewed integrated source and one authorized capture-readback check; successful fresh reservation and final native acceptance remain unproved.

## Shipped CI work

[PR5814](https://github.com/bridge2ai/data-sheets-schema/pull/5814) merged with explicit approval at `95969b5d508577c6e740a16e7acc364379bb40b6` on 2026-11-11T03:31:17Z. It refreshes ordinary-shard scheduling weights from all eight artifacts of successful run42916359440, retaining coverage, shard counts, historical weights and dedicated jobs. Required review findings were filed and addressed.

| Completed run | Observed duration | Interpretation |
|---|---:|---|
| Reference PR run | 36m37s | Comparison baseline |
| [PR run42947560899](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42947560899) | 33m17s | 3m20s shorter; one comparison does not isolate causality |
| [Automatic main run42953302794](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42953302794) | 46m28s | All applicable jobs passed; main has six ordinary shards, PR eight |

Issues5831/5832 corrected execution-step selection and reported shard counts. Independent review verified 674 files/23,265 cases; original analysis remains preserved. No extra timing run was made. Analysis helper `scripts/adhoc/analyze_ci_run_42947560899_20261111.py` has SHA256 `19496cb58eb99aa744e1cfe834fea12831475811ab0896b8d74527c180ea5a6d`. Main raw response `tmp/ci-main-42953302794/run-raw.json` has SHA256 `d206c343d003338300e2b550515f8fdbba8141c741202eb22cd7b865d5678d9d`.

[PR5835](https://github.com/bridge2ai/data-sheets-schema/pull/5835), containing those report corrections and the explicit-profile vocabulary fixture, **merged 2026-11-11T05:28:50Z**, squash `925d726d67cdd03fe28fdeafdde60fa27df57205`. Reviewed head was `fa4f3a7f01ee9531555899ffdc7838b64a2992ab`; automatic CI42958252720 passed in about 33 minutes. Its raw response remains `tmp/ci-evidence-42958252720/run-raw.json`, SHA256 `a87dd687d0fe8dc3701405823c5d2a6ac3629b26741bd7bf5c8f73ae9686e1f3`. The old `codex/development-efficiency-evidence-20261111` branch was deleted locally and remotely. The worktree and evidence are retained. This report uses the separate main-based `codex/native-efficiency-results-20261111` branch; the analysis PR branch remains preserved.

## Matched observer measurement

Frozen source `3cc113e2606c563236d9c06098c5329ddd027a38` supplied both arms with the same private composition, manifest, genuine equivalence canary, interpreter, fixed synthetic diagnostic, one worker and observer-stability guard. Both completed within 900 seconds with normal cleanup and stable source/dependency/origin identities. The comparator matched ordered call rosters/outcomes:478 fixture and 535 launch calls per arm. Independent review verified all twelve input hashes.

| Nonoverlapping phase | Legacy process CPU | Monitoring process CPU | Ratio |
|---|---:|---:|---:|
| Fixture | 149.665813 s | 149.126013 s | 0.996393 |
| Launch | 581.237720 s | 275.663033 s | 0.474269 |
| Fixture + launch | 730.903533 s | 424.789046 s | 0.581183 |

Launch CPU was 52.6% lower in this guarded diagnostic; owner elapsed times were approximately 779.995s and 478.335s. These are unqualified observations, including guard cost, not quiet-host acceptance or model-speed comparisons. Both arms refused stale evidence before reservation. Comparison artifact: `scratch-native-u1u3/u3m/wp1-cpu-comparison-3cc113e2606c-20261111.json`, SHA256 `d6c3a077889039e81a62fde5e202e94786a1d4dd74f6d53e5fec8fba682d53b4` under `d4d-executions`.

## Native baseline and remaining failure

Earlier slices integrated at 7ee4cd8 comprised fixture derivation reuse (23 affected passes), path-alias invalidation (24 passes), early capture refusal (18 unchanged passes plus two repaired renewal cases) and guarded monitoring routing. Two fixed refusal checks passed in 13.11s under their combined 180s cap. Private configuration was restored; all four protected preimages remained unchanged. The retained refusal outcome has SHA256 `d31d318df45cdda03ccdced1d0f0beece5312dc41820c411ad12d167c1333db5` at `scratch-native-u1u3/u3m/refusals-7ee4cd8ba4fa-20261111/outcome.json`.

Schema-import-metadata reuse 5826 integrated at 89c28 after findings 5827–5830 were corrected. Its positive transfer canary and 36 module cases passed. A subsequent genuine diagnostic exposed loader-binding defect 5834 before reservation; its 131.504s outcome was not freshness or speedup evidence. Correction `d6f51f8ed3da7928e66e81fa48f47722a77bbdf5` verifies authentic snapshot source-ledger identity, canonical path, pin and fresh bytes while retaining the original donor. Its genuine nested-loader regression passed in 3.777s; the affected module passed 37 tests in 59.012s. Probe/provenance follow-up `d398f7bee0a141c516ebcad223030f07ce20fa0c` and exact four-file integration were reviewed at the last frozen baseline `458887766effe38207a77fea2d8033f1f3e1c7f3`.

The separate vocabulary failure 5833 reproduced before WP3 and was an ambient-profile fixture assumption. Its two-line main-based fix shipped in 5835 after both parametrizations passed under a deliberately neutral incoming environment. No corpus copy or native-source change was required.

The post5834 diagnostic on 458887 passed the old loader boundary but still refused stale evidence before reservation: one pytest pass in 501.380s records that refusal, not the 210-second gate. Capture age was 71.055s at preflight, 218.553s at controller prewarm and 302.649s when acceptance began; final refusal was 334.858s. Prewarm consumed 71.005 process-CPU/84.097 wall seconds. Normal cleanup and exact private-config restoration completed. See `post5834-diagnostic-analysis.md` for input identities and limits. Four later full verification cascades remain; removing them alone cannot fix this earlier failure. Dependent completion/failure cohorts remain stopped.

## Reviewed candidates and publication

| PR / commit | Current disposition |
|---|---|
| [Draft5839](https://github.com/bridge2ai/data-sheets-schema/pull/5839), `458887766effe38207a77fea2d8033f1f3e1c7f3` | Reviewed 16-file native delta against immutable 5f4a8e2 base; full CI42961942947 cancelled with outstanding gates recorded. |
| [Draft5840](https://github.com/bridge2ai/data-sheets-schema/pull/5840), `7043f0be145d5a0922cdbd3a73f099e6e9a12a3c` | Reviewed private preparation/refusal/cleanup tools; native full CI cancelled, cheap file checks passed. |
| [Draft5841](https://github.com/bridge2ai/data-sheets-schema/pull/5841), `a36c7174fb35c62a2499ee52918354e57a877d6a` | Reviewed matched-CPU helper;5842 bounded its input read. Saved-input recomparison changed only helper identity. Full run42964017924 is cancelled; no green-CI claim. |
| [Draft5853](https://github.com/bridge2ai/data-sheets-schema/pull/5853), `76a443ee34103ed18f30041c111f9f2aae1af40e` | Main-based replacement for5843, which auto-closed when its base branch was deleted. Its tree is identical to reviewedaa86cf0039293a042666751d69dd703a20bfabf5: `d5104e82d26fabfe0af981a3c8168b5e03abfdb0`. Both head and GitHub merge-tree identities match. Older analysis CI42963052291 passed in37m10s. Duplicate CI42966522505 is confirmed cancelled after6m34s; the current head has no green full-CI result. |
| [Draft5851](https://github.com/bridge2ai/data-sheets-schema/pull/5851), `459e56bf896a29d854c5d250ce8632d7e2564427` | Published and independently reviewed capture A; full CI42965552735 confirmed cancelled. A later standalone genuine-node pass is recorded below; combined-source/fixed-supervisor validation remains outstanding. |
| [Draft5852](https://github.com/bridge2ai/data-sheets-schema/pull/5852), `89975411d65e42aae5baa2bb92276ad5f9fabf1a` | Published and independently reviewed import-fact reuse; full CI42965805390 confirmed cancelled. Component evidence does not establish integrated freshness. |

Capture A implements the narrow duplicate-capture reduction and fresh selection recheck, including the stage-root/cohort checks required by findings 5838/5847. Broader bypass designs 5836/5837 were rejected. Final source review found no remaining blocker. Earlier genuine attempts failed on an existing fixture directory and then inherited user Git configuration denial at 22.40s; both remain preserved and neither is a passing genuine test. A later direct terminal and artifact check corrected the earlier stale lead snapshot: the standalone genuine node passed 1 test with 31 deselected in 188.04s at 2026-11-11T05:24:20Z, before the approved stop at 05:29 UTC. Failed attempts 1/2 remain in distinct paths. Current `canary-pass.log` SHA256 is `cdb2ceea4b56f572b16c9a89342822686be43a5972ce576f443f9def0557d393`; JUnit SHA256 is `9191266e3ec67bd9f9c1cb23d67a84fe998f807058bfdec67a962b829133b791`. This is a standalone software-boundary pass, not combined-source or fixed-supervisor proof, and no 30-second-cap claim is made.

Import-fact findings 5844–5846/5848–5850 are addressed. A failed positive canary exposed a private AST alias; the first CPU comparison then exposed a tiny-input regression. Sources below 4096 bytes now take the original AST path before optional guards. Final validation passed 45 targeted cases in 0.59s. Three repeated real-registration graph checks reused 57 eligible sources and used 0.522727s process CPU versus 1.392191s cold (ratio 0.3755); first fills cost 1.731362s. Tiny inputs retained nothing, with no speedup claim. Helpers, source snapshots and failures remain preserved; Python 3.9 stays cold-only and was not locally executed.

The fixed capture adapter is committed at `f82e451743086fc4ec45cda044577e7b587c57c1` and has clean independent source/evidence review. Its synthetic evidence covers 33 distinct passing cases across invocations: canary 1 pass, affected 29 pass/3 fixture failures, then all 6 repaired entry cases passed. This is not a final 33-pass run. CAP-UNIT-1 is recorded as [issue5854](https://github.com/bridge2ai/data-sheets-schema/issues/5854): the unit helper now reserves 20 seconds for cleanup with at most 10 seconds child work. That correction was source-reviewed, not rerun, and claims a 30-second acceptance budget rather than a new independent hard alarm. Final review is `../reviews/capture_adapter_final_review.md` beside these handoffs. [Draft5855](https://github.com/bridge2ai/data-sheets-schema/pull/5855) is published and reviewed at that exact head; CI42967083141 cancellation was requested.

## Current runtime ownership and next check

The user approved the exact AGY3 stop message; it was delivered. The user also explicitly authorized local AI-worker coordination. The earlier administrative messaging hold is lifted; its rejected attempts remain chronology, not a current blocker.

The native worker is the **sole runtime owner**. Integrated source `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b` combines the reviewed 459e56bf/89975411/f82e451 work. Independent review verified all donor patches, unchanged protected preimages and the narrow exact-branch correction for [5856](https://github.com/bridge2ai/data-sheets-schema/issues/5856). The original branch remains frozen at458887. [Draft5857](https://github.com/bridge2ai/data-sheets-schema/pull/5857) preserves this source and its review. The worker is released for sparse preparation180s, same-manifest equivalence60s and one fixed capture-readback check900s. No combined-source runtime pass is yet claimed.

On a certified capture pass, owned processes must retire before lead artifact review. The exact private configuration may remain configured for that review and a separately released single existing monitoring diagnostic; on failure, restore once and stop. This avoids restoring and rearming the same composition or creating a new source identity only to repeat setup. A diagnostic's pytest pass may still represent refusal: the target is genuine freshness returning and `reached_reservation_without_effect` within210seconds, with the existing300-second age limit and90-second margin. This would establish a functional boundary, not actual reservation, quiet-host acceptance or generation. Restore private configuration once after the final released check. No broad cohorts or automatic retry is included.

The adapter fixes the singleton node, one worker, total cap, source/manifest keyed once marker and outer/supervised canary gates. It requires no quiet lease and keeps timing/freshness acceptance false. The child uses a fresh HOME and null global/system Git config, addressing the observed setup denial without relaxing source-origin checks. Original private-packet permission persists; production protected-source installation and D128 scanner approval remain separate. The unmeasured prewarm candidate is deferred.

Deferred schema/Core/RO-Crate changes and the wider native PR stack remain outside final-D4D prerequisites. No real native executable, provider/model call or D4D generation has been launched in this efficiency work. The recorded standalone capture-readback pass establishes its software boundary; it does not establish fresh reservation or final generation.
