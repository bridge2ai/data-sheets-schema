# Native capture timing question — 2026-11-11

**Answer: possible in principle, but not available in the current launch flow.** A genuinely new observation under the same registration, review bundle and unchanged current launch word is explicitly supported before generation reservation, up to three durable capture claims. The examined records do **not** reject taking such an observation later. They reject retimestamping an existing observation and replacing genuine verification with a supplied verdict. Moving acquisition after the launch's heavy work would require a reviewed change to ordering and selection, with fresh authority checks and timing evidence. It is not a way to refresh the already selected guard in place.

On the existing evidence there is **no demonstrated successful route on this host with the present implementation**. That is narrower than saying the unchanged 300-second age / 90-second margin makes every possible design impossible. Draft PR5871 removes a baseline cascade costing **11.370907 seconds of thread CPU**, not enough by itself to close the **44.200434-second** optimistic self-CPU deficit. A later genuine acquisition is a distinct, unproved route; the records already recognized that distinction.

This is a read-only source/record audit. The native reference is **382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b**, inspected through Git objects in `d4d-executions/codex-native-u1u3`; PR5871 is compared at **1a137b58860416a31618de44173180d021dfcc61**. Issue material was read from retained local bodies and their issue-number mappings; no current GitHub state was fetched. No tests, diagnostic reruns, production imports, native/provider calls, compositions, configuration changes, commits, network operations or STATUS edits occurred. `launch-a21` and its run directories were not accessed. The only writes are this report and the read-only helper listed at the end.

**What the records have already decided**

For local record citations below:

- `DEV` means `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111`.
- `PRIMARY` means `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`.
- `REVIEWS` means `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews`.

| Record and passage | Decision relevant to this question |
|---|---|
| #5836: `DEV/tmp/review-postaccept-supplied-value.md:3–7`; number mapped by `DEV/notes/development_efficiency_20261111/review-post-acceptance-design.md:7` | Rejects a caller-supplied `verified_value` replacing full preparation/execution reconstruction. Public entry points retain genuine verification; any reduced check must belong to the same live invocation and preserve capture/clock/journal/one-use/source checks. It does not reject genuine new acquisition. |
| #5837: `DEV/tmp/review-postaccept-test-fallback.md:3–5`; number mapped by the same rejection record at line 8 | Rejects production detection of monkeypatched verifiers that sends tests down an older path. Requires witnesses of the actual changed path. It makes no acquisition-timing decision. |
| #5722: `PRIMARY/notes/coordination/issue-bodies/native-latency-plan-review/nl-10.md:9–13`; mapping in `PRIMARY/notes/coordination/STATUS.md:6543` | A freshness timing pass does not close structural U3K-F1. The required cheap postacceptance contract and measured margin are separate gates. No particular snapshot architecture is mandated; live identity, clock, journal, one-use and refusal guarantees remain required. |
| `DEV/notes/development_efficiency_20261111/handoffs/private-postaccept-design.md`, “Checks that must remain live” and “Exact unresolved implementation boundary” | Pins and schema guards do not establish preservation of all mutable preparation/composition interpretation state. Original capture time must remain unchanged. This evaluates replacing verification, not taking a new observation. |
| `DEV/notes/development_efficiency_20261111/reviews/remaining_postaccept_feasibility.md`, “Exact gap in the cheaper alternatives” | No complete cheaper verifier is established. Fresh preparation and full execution reconstruction are still needed. A new quota observation does not solve that producer-state obligation. |
| `DEV/notes/development_efficiency_20261111/handoffs/postaccept-fusion-implementation.md:49–52` | The PR5871 slice must preserve the lock and original clock, and must not nest locks, retimestamp a capture, change age300/margin90 or change later launch/dispatch. This excludes adding recapture to that existing slice; it is not a universal finding against a new genuine observation before the final lease. |

The earlier timing discussion is explicit. `REVIEWS/native_u3k_2026-11-09.md:217–222` says:

> Deferring acceptance does not restart an already saved observation's age.

It then says heavy preparation must precede the **actual capture**, or a validated handoff must fit the unchanged window and margin, and states that its patch neither creates a new capture nor silently refreshes the timestamp. The preceding task, `PRIMARY/notes/coordination/2026-11-09-codex-native-u3k.md:20`, contemplated heavy verification before the capture is “taken or accepted” and required a changed N1.5 event order to be described for the lead's amendment work. Those passages establish prior consideration, not a completed or approved new acquisition protocol.

A superficially similar proposal was rejected in #5721/NL-9: `PRIMARY/notes/coordination/issue-bodies/native-latency-plan-review/nl-9.md:9–13` explains that registration/bundle validation, activation and claim construction were **already before** the synthetic fixture's `capture_now`; moving them there again could save nothing. It does not reject moving real observation acquisition after launch verification. The later snapshot proposal in `REVIEWS/native_u3k_2026-11-09.md:589–600` was expressly unimplemented and unauthorized; it cannot override #5836 or the subsequent producer-state finding.

Thus **“already rejected in the records” is not the answer for a genuine later observation**. It is the answer for age resetting, supplied verification verdicts, test-dependent bypasses and the no-op fixture reordering. Searches for these records included hidden and ignored files in the lead notes/tmp records and relevant primary coordination/native review records, without inspecting the live A21 checkout.

**1. What the capture is, and why it currently comes first**

All source references in this section and the next two sections are under `src/data_sheets_schema/` at 382f.

The production capture is a separate, explicitly selected command, `native_generation.py:117–120,218–235`: `capture-subscription-event`. It validates the exact registration, account-choice document, review bundle and launch word, then invokes `native_subscription_capture.capture_subscription`. It is not a screenshot, manually typed utilization percentage or read-only query of a local counter.

`native_subscription_capture.py:161–169` constructs one pinned executable invocation with the fixed prompt **“Reply with OK.”**, the registered model/effort/budget and an isolated environment/cwd/config. The flags prohibit tools, MCP servers, hooks and session persistence (`:44–48`); caller argv and environment are not inherited. `_supervise` launches that process and reads its JSON stdout/stderr (`:202–245`). When a `rate_limit_event` line arrives, it records the local UTC observation time, line number, exact event JSON and its digest (`:241–245`). The selected observation is the last rate-limit event in the validated ordered stream (`:272–295`). It also requires a successful final result and registered model limits (`:486–498,554–567`).

In production this depends on the registered native executable and its selected first-party subscription session/provider behavior. It can wait on process startup, authentication/provider response and terminal completion; it is not a pure in-process reconstruction. The capture supervisor allows at most **60 seconds** for its subprocess/stream loop (`:38,113–115,202–220`), but that is **not** a 60-second bound on all surrounding verification and evidence work. Full authority verification runs at entry (`:413`), again after the durable claim before spawn (`:538–546`), and again **after the event has been received** (`:547–549`); terminal checking, cleanup and durable evidence writes also remain. No production capture duration or provider request rate is established by the diagnostic.

The module's own scope is precise (`:1–7,42–43`): one process is not proof of one provider request, and an emitted quota event is not authenticated account/quota state. The owner action supplies the exact authorized word and bounded request; the code performs acquisition when that command is explicitly invoked. Reading the guard or accepting it does not make a new observation.

The current workflow requires the capture first because guard preparation is a separate saved-evidence step. `native_generation.py:237–246` reads the retained capture, uses its exact `event_json` and original `captured_at`, and creates a new guard file. Launch requires that file and its expected SHA (`:129–133,259–264`). `native_shared_execution_orchestration.py:87–94` selects it and performs preflight before engine entry. Preflight verifies the selected SHA, word/bundle, current journal and actual-clock freshness (`native_subscription_admission.py:38–65`). Static inspection also reconstructs the selected event before the heavy work has finished (`:84–105`). There is no “no observation yet” launch entry or acquisition callback in the current sequence.

The later `accept_current_selection` expressly **accepts the original timestamp after heavy reconstruction** (`native_subscription_admission.py:108–120`). It does not capture again. In the engine, composition/admission/controller prewarm finish at `native_execution_orchestration.py:344–364`; acceptance follows at `:365–368`; join, `_unchanged`, lease and reservation follow at `:369–388`.

The 382f measurement is a **synthetic-software-test**, not a production subscription observation. Its saved diagnostic labels the measurement an unqualified contended CPU diagnostic. `tests/test_native_u3k_profile.py:208–240` obtains the retained timestamp from the neutral fixture and `:244–257` calls the genuine synthetic launch while stopping before any attempt reservation effect. The 10.802291-second capture-to-launch interval measures that fixture-to-launch boundary; it does not establish production CLI/account acquisition cost. Production capture explicitly requires the production profile (`native_subscription_capture.py:410–416`), while the synthetic front door says actual capture refuses its synthetic authority (`native_shared_execution_orchestration.py:97–103`).

**2. What 300 seconds and 90 seconds protect**

`native_u4b_policy.py:14–17` declares `max_age_seconds = 300` and `pre_reservation_margin_seconds = 90`. Validation requires these exact registered A3 terms (`:33–39`); later owner statements or guards cannot independently select different values. `native_subscription_guard_v2.py:24,341–351` separately enforces an age at most 300 and equality of age/margin/headroom terms with the owner/runtime statement.

| Rule | Interval and purpose |
|---|---|
| Age 300 | `_fresh`, `native_subscription_guard_v2.py:419–437`, requires actual current time minus the **recorded event observation time** to be between 0 and 300 seconds. It also refuses changed guard bytes, reset windows, a consumed dispatch or a stop state. It does not measure time since guard construction or acceptance. |
| Margin 90 | `before_reservation`, `:439–447`, requires at least 90 seconds of that same 300-second lifetime still available before the attempt identity is consumed. Thus observation-to-reservation age must be **at most 210 seconds**. This reserves preparation headroom after reservation; it neither creates a new 90-second clock nor promises later work will finish in time. |
| Actual dispatch | `before_dispatch`, `:449–455`, again checks the original event's freshness and consumes the guard unless `check_only=True`. Passing pre-reservation does not waive this later check. |

The engine holds the current-word lease, checks controls and calls `before_reservation` **after slow reconstruction and immediately before mkdir** (`native_execution_orchestration.py:379–388`). Its later launch check again joins current authority and admits the one-use guard before actual execution (`:430–442`).

In the retained measurement the pre-reservation entry occurs at capture age **306.533703 seconds**. It already exceeds the 300-second age, so `_fresh` raises the recorded “stale or future-dated” error before the additional margin test. It also exceeds the effective 210-second reservation limit by about 96.53 seconds. The three earlier check-only dispatch freshness calls pass the 300-second check; that does not mean reservation is allowed at those ages.

**3. Genuine re-capture immediately before reservation**

Classification: **possible in principle**, subject to the obligations below; not an implemented or timing-proven route in 382f.

“Same authority” must distinguish four things:

| Identity | What the current source permits or refuses |
|---|---|
| Same registration, runtime, review and current launch word | A new genuine capture is permitted while the v3 request is valid and generation remains unspent. Capture binds hashes of all these, the request and attempt (`native_subscription_capture.py:98–138,400–427`). `Journal.activate` returns the existing current word event when its hash is unchanged (`native_capture_words.py:209–224`). |
| Same selected event/guard | It cannot be silently refreshed. The guard names exact `event_json`, digest and **original captured_at**, and readback must find exactly one retained matching capture (`native_subscription_capture.py:704–744`). The source explicitly says a later re-capture does not rewrite an earlier guard's event (`:706–710`). |
| New occurrence under that word | It consumes a new numbered immutable claim, even if the emitted quota JSON happens to be identical. The new timestamp belongs to the newly received line and retained claim/streams/manifest. Up to three claims are allowed; failed, stale or incomplete attempts stay spent (`native_subscription_capture.py:359–395`). |
| New word | This is a distinct authorization, not the same word. A newer recorded authorization supersedes the old one and must have a strictly later authorization time (`native_capture_words.py:209–236`). It cannot be invented to bypass exhausted allowance or refusal. |

There is even an existing source-level test of the intended same-word behavior: `tests/test_native_u4b_capture_retries.py:71–91`, `test_expired_capture_is_retained_while_same_word_recaptures`, creates a second slot after the first is stale and verifies the first event/evidence is unchanged. This audit only read that test; it did not run it or claim new validation.

The current launch cannot use an out-of-band new capture automatically. `CurrentSelection` freezes the guard path, expected digest and registration/runtime/word/review bindings (`native_subscription_admission.py:14–35`). Acceptance rereads the files and reconstructs the chosen occurrence (`:68–81,108–173`). Changing the existing guard file fails its digest or live-file equality checks (`native_subscription_guard_v2.py:305–329,419–423`). An unchanged earlier guard continues to age even if another capture has appeared in the journal.

A later-acquisition route would have to establish all of the following. These are acceptance obligations, **not a proposed design or patch**:

1. **Authority and selection:** the newly selected observation must come from a genuine retained capture under the exact independently checked registration/review/CI/word and account intent. Preserve the initial/pre-admission checks and all required live preparation/execution reconstruction across the elapsed time and effects of the capture. A new observation is not a reusable verification verdict; #5836 and the producer-state gap still apply. Starting without any earlier guard also changes the present preflight/inspection ordering.
2. **Allowance, chronology and refusal:** an unused capture slot, current valid word, valid registration window and unspent generation identity must still exist. Existing attempt **or evidence** directories prevent capture renewal (`native_capture_words.py:91–93`). Limits mismatch permanently refuses that registration, including attempts with another word (`:209–236`; `native_subscription_capture.py:554–565`). No old slot is overwritten, no prior timestamp is reset, and no discarded failed attempt is retried in place.
3. **Locking and races:** capture holds the registration journal lock through its own acquisition (`native_subscription_capture.py:422–427`). The final admission lease uses the same registration-wide lock (`:457–469`). `native_capture_words.py:250–256,282–294` specifies nonblocking exclusivity and forbids nesting that lock during reservation. Inserting a capture *inside the current held lease* would fail the lock contract; releasing a lease without re-establishing current authority would reintroduce a renewal/refusal race. The final lock must still span the control/freshness/profile checks and attempt mkdir/fsync.
4. **Exact new evidence and one use:** newly received event bytes, timestamp, claim chain, stream digests, terminal success/limits and observed cleanup must all reconstruct (`native_subscription_capture.py:618–670`). Later acceptance must use that occurrence, not an updated timestamp on the earlier guard. Original-time, reset-window and actual-clock checks must still run after all slow work; the later dispatch check remains one-use. Even partial attempt reservation consumes the generation identity (`native_execution_orchestration.py:385–388`).
5. **Remaining time and structural acceptance:** show that work **after the actual event arrives** fits 210 seconds to reservation and 300 to dispatch on the relevant host, with the 90-second margin intact. The capture producer itself does a full authority verification after observation (`native_subscription_capture.py:547–549`), and saved readback/acceptance/final lease also perform genuine work. A late event cannot be assumed adjacent to mkdir in elapsed time. Independently close, or explicitly retain, the structural postacceptance requirement of #5722; a timing pass alone does not close it. Any changed N1.5 event order remains subject to the recorded amendment/review requirement.

None of these observations authorizes a new capture or a rerun here. The existing evidence proves that same-word re-observation is part of the capture contract; it does not prove a safe in-launch handoff, a remaining freshness budget, or successful native reservation. A new capture followed by an ordinary launch from its beginning retains the expensive full launch path; merely reducing the 10.8-second gap before launch cannot remove the launch's measured CPU deficit.

**4. What draft PR5871 can contribute**

The exact diff from 382f to `1a137b58860416a31618de44173180d021dfcc61` retains actual acceptance and its subsequent current-authority join. On the accepted shared `CurrentSelection` route only, it combines the second `_unchanged` reconstruction with the adjacent lease's **remaining full reconstruction**, compares both the fresh and current engine values with original invocation-local canonical bytes, then acquires the lease. Public/direct routes and the actual input/source/platform tail remain. It does not move capture or change age/margin.

Base call sites are `native_execution_orchestration.py:369–381` and `native_shared_execution_orchestration.py:37–45`. Candidate sites are `native_execution_orchestration.py:367–405,409–416` and `native_shared_execution_orchestration.py:40–55` at the draft commit.

| Baseline launch row (zero-based) | Reconstruction | Inclusive thread CPU | Inclusive wall | Draft |
|---:|---|---:|---:|---|
| 972 | Postacceptance join | 11.519216 s | 14.387324 s | Retained |
| **1046** | Second `_unchanged` → shared `registration.verified` | **11.370907 s** | **13.312553 s** | Removed; input/source/platform tail retained |
| 1080 | Lease → `_current_authority` → shared `registration.verified` | 9.980186 s | 11.972933 s | Retained |

The lead's **“about 10 seconds” is a reasonable order-of-magnitude estimate**; the precise attributable baseline cascade is 11.37 seconds. The 9.98-second row belongs to the retained lease. Row 1046 already contains its execution/preparer children, so those times must not be added again.

These are baseline costs, **not measured net candidate savings**. Extra comparisons/canonicalization remain, and removing an earlier reconstruction can change later costs. The retained component report isolates registration/source/controller prerequisites and does not demonstrate genuine producer performance. Removing an intermediate sample also changes detection of transient drift restored before the remaining sample; the implementation brief explicitly records this limitation.

The baseline launch uses **243.398143 process CPU seconds** and starts **10.802291 seconds** after capture. Its optimistic self-CPU deficit is `243.398143 − (210 − 10.802291) = 44.200434 seconds`. Even granting the full 11.370907-second baseline cascade as a saving leaves **32.829527 seconds**. Even granting both that saving **and zero delay between capture and launch** leaves **22.027236 seconds** above 210 on the same arithmetic. These are conditional subtractions, not a forecast; the run was contended, instrumented and synthetic, and reaped-child CPU is separate. They do show why PR5871 alone, or simply initiating the same launch a little sooner after capture, is not an evidence-backed solution.

**5. Paragraph for the owner**

The native arm has not demonstrated reservation within its current freshness rule on this host. The retained 382f diagnostic reaches the pre-reservation check with its observation already 306.5 seconds old; reservation requires age at most 210 seconds, leaving 90 seconds before the 300-second dispatch limit. Draft PR5871 removes work that cost about 11.4 CPU seconds in that baseline, versus roughly 44.2 seconds needed even on an optimistic CPU-only calculation, so it is insufficient by itself. Taking a genuinely new observation later under the same valid word is allowed within the existing three-capture allowance and was contemplated in earlier records; it was not categorically rejected. However, the current launch remains bound to its original guard and has no validated later-capture handoff. There is therefore no demonstrated route without further implementation/design work; it is premature to say the numerical freshness rule itself must change. Any later-capture route must preserve authority, journal locks, immutable evidence and one-use checks, prove the remaining timing, and keep the separate structural acceptance obligation visible.

**Evidence identity and reproduction**

The only runtime evidence used is the already completed native diagnostic under:

`d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111/phase-metrics/`

| File | SHA-256 |
|---|---|
| `67941-measurement.json` | `12cba82d359f98d39220db521d8920130da94f863b554d265c0116736738a31d` |
| `67941-diagnostic.json` | `33b032291d891f06249596da823d2a6f26d87d59317388f078b3a399ffc21cba` |

The new read-only helper is `DEV/scripts/adhoc/audit_native_capture_timing_20261111.py`, SHA-256 **273527823ebdfce3f86875733e3d4d5e37a6fdaf8c6880c9bae10f9d5384e4fb**. It reads those JSON files, asserts the three source-mapped baseline rows, and prints the timing arithmetic and digests. It writes no artifacts and imports no production code. It was run from DEV with:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \
  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \
  scripts/adhoc/audit_native_capture_timing_20261111.py
```

Source was read with `git show`, `git grep` and an object-to-object diff only. Independent read-only passes checked the prior decisions, capture invariants and PR5871 cost mapping. No design, patch or runtime is released by this report. Assignment complete; stop here.
