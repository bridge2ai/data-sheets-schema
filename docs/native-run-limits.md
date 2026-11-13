# Two registered native run-limit sets

D143 retains the canary shakedown pair and the production pair, defined only in `native_run_limits.py`. A caller supplies both fields explicitly. No project, label or bundle selects a pair. Mixed pairs, alternate decimal spellings, third values, missing values and boolean/float deadlines refuse. The separately declared synthetic profile is unchanged.

No registered document kind or version changes. Runtime, registration, owner terms, review bundle and coded word already carry or pin the complete runtime and exact registration bytes. A production run needs newly prepared and reviewed evidence under its selected pair. Historical canary bytes are not rewritten.

| Source | Treatment |
| --- | --- |
| `src/data_sheets_schema/native_run_limits.py:6` | Changed: sole pair definitions and strict whole-pair validator. |
| `src/data_sheets_schema/native_u4b_runtime.py:174` | Changed: final runtime profile admits only the declared pair. |
| `src/data_sheets_schema/native_u4b_probe_sequence.py:96` | Changed: provisional runtime has the same pair restriction. |
| `src/data_sheets_schema/native_u4b_policy.py:61` | Changed: registered admission validates the pair, without extending freshness. |
| `src/data_sheets_schema/native_launch_review.py:182` | Changed: owner terms match the declared pair exactly; bundle and word retain their exact-byte joins. |
| `src/data_sheets_schema/native_shared_runtime_values.py:151` | Unchanged: generic one-day ceiling admits both values; production validators impose the narrower pairs. |
| `src/data_sheets_schema/native_shared_registration.py:51` | Unchanged: argv uses the declared budget verbatim. |
| `src/data_sheets_schema/native_shared_registration.py:175,278` | Unchanged: registration serializes the complete declared runtime. |
| `src/data_sheets_schema/native_execution_orchestration.py:485` | Unchanged: dispatch receives the declared deadline. |
| `src/data_sheets_schema/native_execution_orchestration.py:462` | Unchanged: IOKit lifetime wraps the same dispatch and cleanup for either duration. |
| `src/data_sheets_schema/native_attempt_supervisor.py:142` | Unchanged: separate synthetic fixture supervisor local bound, not the native execution deadline. |
| `src/data_sheets_schema/native_runtime_profiles.py:20` | Unchanged: separately declared synthetic profile remains fixed. |
| `src/data_sheets_schema/native_shared_runtime_constants.py:9` | Unchanged: both values are already explicit wire keys; no new discriminant. |
| `src/data_sheets_schema/native_shared_render.py:211` | Runtime identity is carried in render metadata; the environment specification transports the complete metadata. |
| `src/data_sheets_schema/native_shared_render.py:296` | Candidate recorder reads D4D_RENDER_SPEC and binds it with --render-spec-sha256; selecting another pair changes the visible digest, not embedded budget/deadline literals. |
| `src/data_sheets_schema/native_subscription_guard_v2.py:442` | Unchanged: age/reset checks repeat at dispatch; they do not certify quota throughout the longer run. |
| `src/data_sheets_schema/native_subscription_guard_v2.py:462` | Unchanged: the same registered reservation margin applies. |
| `notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:649` | Child runtime starts immediately before process creation on the continuous clock; admission is excluded. |
| `notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:651` | The declared 900, 21600 or 43200 seconds are measured from dispatch, including host suspension. |
| `notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:612` | Separate 900-second admission bound begins at execute_child entry, before setup and verification. |

## Operational differences

A twelve-hour attempt spans more five-hour usage-window boundaries than a six-hour attempt: for fixed aligned five-hour windows, two or three rather than one or two, depending on dispatch phase. This is arithmetic, not a claim about provider reset scheduling. A weekly boundary may occur during either; the longer run has more exposure to one. Starting utilization is not a guarantee of twelve hours of available quota. Overage remains disabled and observed rate/quota stops remain sticky.

The candidate retains a 1200-second maximum observation age and a 300-second pre-reservation margin (57bcc018b): reservation is allowed through age 900 seconds and dispatch through age 1200 seconds. They bound evidence age at launch, not evidence freshness throughout the attempt; a twelve-hour deadline does not turn them into twelve-hour authority or refresh a consumed capture. The fourteen-day registered validity interval and exact owner-word joins remain unchanged.

The three IOKit assertions remain acquired through the attempt and released through the same cleanup. Idle-sleep assertions do not prevent lid sleep, power exhaustion or host interruption. The combined implementation checks AC power immediately before dispatch and records supplemental host-power observations. The child deadline begins immediately before process creation on mach_continuous_time on macOS or CLOCK_BOOTTIME on Linux; both include suspension. There is no adjustable-wall-clock fallback. The separate synthetic fixture supervisor retains its one-hour bound.

Admission has its own 900-second continuous-clock bound from execute_child entry through the dispatch origin. It includes controller setup and launch verification, consumes none of the declared child runtime, and does not extend subscription freshness. A periodic POSIX alarm raises through interruptible Python system calls; expiry refuses dispatch and takes the existing failure-publication and keep-awake cleanup path. It cannot preempt uninterruptible kernel calls or C extensions that do not service signals. Earlier capture-to-reservation verification lies outside this admission bound.

Canary and production instructions differ through runtime-dependent render metadata and its digest. On the candidate (c577c0eff), the recorder uses --render-spec-env D4D_RENDER_SPEC plus --render-spec-sha256. The command contains the digest instead of embedded runtime JSON; changing the pair changes that model-visible digest and exact-command policy. The runtime declaration remains a registered readable input. The canary is therefore a shakedown, not the frozen production reference. The later reference pilot must use production terms.

Same-input compatibility is checked against exact source from the published base: prepared canary runtime bytes remain identical, and the unchanged saved canary registration/review/word bytes validate with equal derived terms. That saved-registration fixture is deliberately parser-scoped. A newly built complete registration binds package-source identities, so its bytes necessarily change when code changes; this test does not claim fresh full-registration byte identity across source revisions. No source pins are restamped to manufacture that identity.

## Frozen draft v12 references requiring production qualification

The historical draft is retained unchanged. The lead must qualify its universal six-hour statements for production; historical D14 source recommendations remain historical. The matching lines below are derived from the local frozen draft, not edited here.

- Line 228: | **D14** | The budget is subscription usage, plus a dollar backstop.<br>• **Re-validation, done by this amendment.** The 2026-10-25 packet's sources recommended a starting seven-day utilisation ≤ 0.80, an overage stop or overage disabled, a $90 guard and a 21,600 s deadline. Since then:<br>&nbsp;&nbsp;– the seven-day window was exhausted on 2026-10-24;<br>&nbsp;&nbsp;– D106 named the account;<br>&nbsp;&nbsp;– D110 set the guard;<br>&nbsp;&nbsp;– D111 disabled overage;<br>&nbsp;&nbsp;– D112 chose the 1M context, which spends headroom faster.<br>• **The result is N1.5's terms.** Any later change to them is a revision of this amendment, which the owner approves. |
- Line 339:        - **Why 1200.** With the 300 s margin proposed below it allows the reservation up to 900 s after the capture event, against roughly 6 to 10 minutes on that estimate. The reading guards a run of up to 21,600 s against starting above the admission bounds; its greatest age at dispatch moves from 5 minutes to 20. **That reasoning assumes no other session uses the registered account between the capture and the dispatch;** the host terms below require it (N1.8(ad)).
- Line 372: - **Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch. That's the sources' value, re-validated in D14.
- Line 379:   - **A mid-run five-hour exhaustion** is a usage stop, and it counts as an attempt (D118, D113). The 6 h deadline crosses at least one five-hour reset, and the 1M context spends faster, so this is possible whatever the admission reading.
- Line 469: - **(p)** Deadline: 21,600 s.
