# Helper 2: run-limit and power review fixes

Local implementation is committed, but the power branch is not ready to integrate: exact controller pins remain unchanged and block integrated deadline/timing validation. Automatic approval review rejected their update. No publication or native run occurred.

The read-only 6094 timing assignment was completed first: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-6094-timing-20261113.md`, SHA-256 `a422e9d18fb8653d3b6fed584dde674a7b6da019c9bd957cdd37a0c45d956a3b`.

## Branches and integration

Fetched origin once as explicitly requested, then merged candidate `f7f8e8bff6ea14006957d8631f66346d91bcddcd` with `git merge --no-ff` into each assigned branch. No rebase, push or GitHub write. All three branches are clean. The four protected files and guard v1 remain byte-identical to that candidate.

| Branch | Head |
| --- | --- |
| `codex/native-helper-cache-home-20261112` | `9d743c87755030ddf687e3a5dd8a7a2b3b762437` |
| `codex/native-production-run-limits-20261112` | `0df39c077fb8125dc381302046f4cf7f92a60592` |
| `codex/native-host-power-20261113` | `916ad3af0adf278ab3bbde78be7c9fb3c4cc92f0` |

## Issue commits and proof

| Issue | Commit | Change and proving test |
| --- | --- | --- |
| 6167 | `2c158ddfce23285546b248a0b200437ad1feb2a7` | Supplemental start/stage/end persistence errors retain diagnostics and cannot replace launch errors or interrupt final publication. test_native_failure_publication.py (start/end injected disk errors); test_native_shared_live_capture.py (committed stage with failed clock); test_native_host_power.py (active cleanup exception) |
| 6168 | `f377dba1d94fbd84a146de729d0f6cfdd7b22087` | No-sleep requires recognized, ordered, matched events bracketing the interval. Unknown formats, gaps and unmatched events remain unknown; clock divergence stays separate. test_native_host_power.py: timestamped unrecognized, incomplete coverage, DarkWake, unmatched events, covered no-sleep |
| 6169 | `94378cd6240df3c2996ab3b370db5a862f8ead04` | Provisional rejection begins with a valid accepted document, mutates only the pair, checks generic acceptance and pair-specific refusal. Removing the pair check in the test admits the five invalid pairs. test_native_run_limits.py::test_provisional_refusal_depends_on_registered_pair_check (five cases; whole file also run) |
| 6170 | `feb1de3250bdefd6fd05bcc57ef513f63de0e9a7` | Declared child deadline begins immediately before Popen after admission, uses suspension-inclusive elapsed time, and checks expiry even if the child exited while suspended. AC is checked last before dispatch. test_native_attempt_deadline.py: six simulated-sleep cases, admission exclusion, macOS integer conversion, AC-to-battery/unknown public refusal. Integrated cases currently stop at controller pin verification. |
| 6171 | `0df39c077fb8125dc381302046f4cf7f92a60592` | Generated documentation preserves 300-second reservation margin and recorder --render-spec-env D4D_RENDER_SPEC plus --render-spec-sha256. Pair selection changes the visible digest; runtime stays readable. audit_run_limits_20261113.py source inventory regenerated to a new evidence directory; generator and document inspected |
| 6172 | `916ad3af0adf278ab3bbde78be7c9fb3c4cc92f0` | Both reviewed runners derive local installation paths at runtime; reconciliation helper derives its home path. Sleep fixture is entirely synthetic with 1252-second and 7034-second intervals. test_native_host_power.py synthetic fixture; hidden/ignored-inclusive personal-path search over edited helpers; AST parsing |
| 6172 cache follow-up | `9d743c87755030ddf687e3a5dd8a7a2b3b762437` | Required separate cache-branch follow-up fixes the published cache runner and reconciliation helper. Hidden/ignored-inclusive personal-path search and AST parsing; no behavioral cache changes |
| 6094 / assignment item 7 | `a4f45bb93eeb843ae85bb5b5bc283a50ac0329c7` | Bounded supplemental host-controller-timing.jsonl records execute_child entry, dispatch origin/deadline, callback delivery, tool-result intake and model turn frames, joined by tool ID and command digest. test_native_attempt_timing.py: partial-response and persistence-failure units pass; inert controller integration currently stops at exact-source verification |

The two 6172 commits are the explicitly requested follow-ups on different branches; their shared edits are identical.

## Saved tests

Every touched test file ran whole in a network-denied export outside all d4d-executions paths. At most two xdist workers. No real native binary, provider, model call, host probe or public completion run. Test probes use invented local interface bytes. The failure-publication canary stops before peer dispatch; it is not a public completion attempt.

| Cohort | Counts | Exit | Seconds | Source commit |
| --- | --- | ---: | ---: | --- |
| canary | 1 failure | 1 | 2.487635416997364 | `e351bb4e199573a528e901dc0d46695b3ef937bb` |
| power-canary | 1 passed | 0 | 0.5559391670030891 | `229a3d3e7f72cbe72601344bceed465ddecee2a4` |
| scanner | scanner (see retained report) | 1 | 109.57777545799763 | `229a3d3e7f72cbe72601344bceed465ddecee2a4` |
| scanner-unaffected | scanner (see retained report) | 1 | 195.27051600000414 | `991c9b7f43d6daad93af11a20fc4d8a3c2a1f0e8` |
| touched-files | 40 error, 16 failure, 80 passed | 1 | 44.40671962500346 | `229a3d3e7f72cbe72601344bceed465ddecee2a4` |
| unaffected-canary | 1 passed | 0 | 488.07623504200455 | `991c9b7f43d6daad93af11a20fc4d8a3c2a1f0e8` |

The `fixed` export is the current power/run-limit composition. Every current whole-file failure/error is an unchanged controller hash refusing changed source. The `unaffected` export retains the original controller sources and checks the earlier observation and pair/privacy fixes independently; its passes do not validate the clock/timing changes. All completed cohorts retain origin/network checks and verified owned-process cleanup.

The independent end-failure canary passed: after the launch error was already caught, an injected end-sidecar write error preserved that first error, allowed failed-result publication, and retained exact readback. It completed before the optional ten-minute cancellation check; no cancellation signal was sent. Start/stage integration remains to be rerun after source admission is repaired.

## Deadline clock and diagnostics

macOS uses `mach_continuous_time`, scaled by integer `mach_timebase_info`. Apple SDK header `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/mach/mach_time.h` lines 58–62 explicitly states that it advances during sleep; retained header SHA-256 `d690e304ea595ca216ed51e20aa9747e0b3bcb07446d996abe0080a231c7065f`. Linux implementation uses `clock_gettime_ns(CLOCK_BOOTTIME)`. No adjustable time-of-day or suspension-excluding fallback is accepted.

The origin is immediately before `Popen`, after launch verification and the final AC check. Declared durations remain 900, 21600 and 43200 seconds. Helper endpoints measure controller response delivery to result intake, including transport/scheduling; they are not actual subprocess start/exit or CPU time. Model boundaries are received CLI assistant/user/result frames, with message start/stop when supplied, not provider-internal token timing.

9 pure-function simulations passed using the exact execute_child AST, fake clocks and fake process objects: long admission, suspension while running, and suspension with an exited child, for each registered duration. This checks the deadline function without changing or replacing any authority loader/check. It is not source-admitted controller integration. Evidence: `/Users/marcin/agent-work/data-sheets-schema/helper2-review-fixes-20261113/deadline-function/results.json`, SHA-256 `cf4eeb58da6714cc294489879215abc9433825f963b52da6cb2f0e911699085a`.

## Approval boundary and remaining work

Controller manifest and authority digest updates were rejected as security-sensitive trust-pin changes reserved for the lead. No authority/scanner/prompt pin was edited, including in the private exports.

Reviewable proposal: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-controller-pin-proposal-20261113.diff`, SHA-256 `921eb9b024f7ab1a491b6d910aac4c1a880fed3477a9fba7330d2fc21d9695d7`. It changes only the two controller manifests and their three exact digest constants; the corresponding JSON lists all old and proposed hashes. The proposal is not applied.

1. Approve or have the lead apply the five-file pin proposal after source review.
2. Repeat the whole touched-file cohort against the admitted composition; start/stage publication failures, simulated deadline, AC-transition and controller timing integration have not yet reached their assertions there. The independent pre-clock end-failure canary passed.
3. Any quiet-host public completion run remains for the lead; the existing 900-second declaration is unchanged.

The whole-source specificity scanner ran without restamping its contracts. Both the current and pre-clock compositions exit 1 with the same nine legacy-controller project-default findings; the native-agentic surface has zero specificity violations. The exact rows and reports are retained in the audit JSON. This task does not authorize a launch or claim the integrated candidate passes.

## Review and provenance

Read-only diff review performed separately. No further implementation finding beyond the unapplied controller pins. Integrated behavior remains unverified where source admission stopped. One pre-existing blank EOF line remains in the power proof runner (reported by full-branch diff --check). No GitHub issue or review was written.

Detailed source, privacy, protected-byte, SDK and per-test evidence: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h2-review-fixes-audit-20261113.json`, SHA-256 `b0933561ce08fd8f8b729b9ca412865645f56b6d0d3b890ee22d15d50a0c70e9`.

Provenance helpers retained in R:

- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/audit_h2_review_fixes_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/prepare_h2_review_fixes_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/refresh_h2_review_fixes_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/report_h2_review_fixes_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/run_h2_review_fixes_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/prepare_h2_unaffected_fixes_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/propose_h2_controller_pins_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/simulate_h2_deadline_function_20261113.py`
- `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/bound_h2_failure_canary_20261113.py`
