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
| `src/data_sheets_schema/native_shared_registration.py:50` | Unchanged: argv uses the declared budget verbatim. |
| `src/data_sheets_schema/native_shared_registration.py:174,277` | Unchanged: registration serializes the complete declared runtime. |
| `src/data_sheets_schema/native_execution_orchestration.py:485` | Unchanged: dispatch receives the declared deadline. |
| `src/data_sheets_schema/native_execution_orchestration.py:462` | Unchanged: IOKit lifetime wraps the same dispatch and cleanup for either duration. |
| `src/data_sheets_schema/native_attempt_supervisor.py:142` | Unchanged: separate synthetic fixture supervisor local bound, not the native execution deadline. |
| `src/data_sheets_schema/native_runtime_profiles.py:20` | Unchanged: separately declared synthetic profile remains fixed. |
| `src/data_sheets_schema/native_shared_runtime_constants.py:9` | Unchanged: both values are already explicit wire keys; no new discriminant. |
| `src/data_sheets_schema/native_shared_render.py:211` | Unchanged: raw runtime reaches model-visible rendered input; the two sets intentionally produce different instructions. |
| `src/data_sheets_schema/native_subscription_guard_v2.py:442` | Unchanged: age/reset checks repeat at dispatch; they do not certify quota throughout the longer run. |
| `src/data_sheets_schema/native_subscription_guard_v2.py:462` | Unchanged: the same registered reservation margin applies. |
| `notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py:605` | Unchanged: actual native child timer uses the declared seconds with monotonic time, not the synthetic supervisor. |

## Operational differences

A twelve-hour attempt spans more five-hour usage-window boundaries than a six-hour attempt: for fixed aligned five-hour windows, two or three rather than one or two, depending on dispatch phase. This is arithmetic, not a claim about provider reset scheduling. A weekly boundary may occur during either; the longer run has more exposure to one. Starting utilization is not a guarantee of twelve hours of available quota. Overage remains disabled and observed rate/quota stops remain sticky.

The same 1200-second observation age and 90-second reservation margin apply at admission/dispatch. They bound evidence age at launch, not evidence freshness throughout the attempt; a twelve-hour deadline does not turn them into twelve-hour authority or refresh a consumed capture. The fourteen-day registered validity interval and exact owner-word joins remain unchanged.

The three IOKit assertions must remain acquired through the longer attempt and released through the same cleanup. Idle-sleep assertions do not guarantee protection from lid sleep, power exhaustion or host interruption. Issue 6046 adds separately reviewed host-power evidence; this branch does not merge that change. The production dispatch passes the registered deadline into the existing monotonic timer; the separate local synthetic supervisor keeps its own one-hour bound. On hosts whose monotonic clock pauses in sleep, the existing timer can allow more wall time than the declaration describes. This pre-existing timer/wording discrepancy is retained for lead review, not silently changed by this pair-policy patch.

Canary and production instructions differ because the raw runtime appears in rendered recorder commands and metadata. The canary is therefore a shakedown, not the frozen production reference. The later reference pilot must use production terms.

Same-input compatibility is checked against exact source from the published base: prepared canary runtime bytes remain identical, and the unchanged saved canary registration/review/word bytes validate with equal derived terms. That saved-registration fixture is deliberately parser-scoped. A newly built complete registration binds package-source identities, so its bytes necessarily change when code changes; this test does not claim fresh full-registration byte identity across source revisions. No source pins are restamped to manufacture that identity.

## Frozen draft v12 references requiring production qualification

The historical draft is retained unchanged. The lead must qualify its universal six-hour statements for production; historical D14 source recommendations remain historical. The matching lines below are derived from the local frozen draft, not edited here.

- Line 228: | **D14** | The budget is subscription usage, plus a dollar backstop.<br>• **Re-validation, done by this amendment.** The 2026-10-25 packet's sources recommended a starting seven-day utilisation ≤ 0.80, an overage stop or overage disabled, a $90 guard and a 21,600 s deadline. Since then:<br>&nbsp;&nbsp;– the seven-day window was exhausted on 2026-10-24;<br>&nbsp;&nbsp;– D106 named the account;<br>&nbsp;&nbsp;– D110 set the guard;<br>&nbsp;&nbsp;– D111 disabled overage;<br>&nbsp;&nbsp;– D112 chose the 1M context, which spends headroom faster.<br>• **The result is N1.5's terms.** Any later change to them is a revision of this amendment, which the owner approves. |
- Line 339:        - **Why 1200.** With the 300 s margin proposed below it allows the reservation up to 900 s after the capture event, against roughly 6 to 10 minutes on that estimate. The reading guards a run of up to 21,600 s against starting above the admission bounds; its greatest age at dispatch moves from 5 minutes to 20. **That reasoning assumes no other session uses the registered account between the capture and the dispatch;** the host terms below require it (N1.8(ad)).
- Line 372: - **Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch. That's the sources' value, re-validated in D14.
- Line 379:   - **A mid-run five-hour exhaustion** is a usage stop, and it counts as an attempt (D118, D113). The 6 h deadline crosses at least one five-hour reset, and the 1M context spends faster, so this is possible whatever the admission reading.
- Line 469: - **(p)** Deadline: 21,600 s.
