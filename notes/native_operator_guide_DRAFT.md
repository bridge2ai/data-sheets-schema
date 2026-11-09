# DRAFT: CHORUS n=1 native canary operator guide

Prepared 2026-11-08 for U5 preparation. **This is not a launch packet, an approval, a real registration or a claim of acceptance.** It contains no executable launch command or launch word. Native execution, probing, account access and provider calls are outside this task.

Code references describe immutable U4 preparation head `d258611c5381bd7cf973817ebd2b6a04f65818b3`; bare Python filenames are relative to `src/data_sheets_schema/`. External schema input is pinned separately to `5e382f0c423fa8b0a331340adcdfac5a328bd6b3`. The accepted U1+U3/schema/packet integration head does not exist in this guide's evidence and must replace these preparation references before use.

Basis labels: **OWNER DECISION** states an explicit recorded choice; **CODE FACT** identifies an inspected source; **PENDING N1** means that the native amendment must supply and ratify the term. Proposals in the first N1 draft are not defaults that this guide silently applies.

## 1. Choices already recorded, and terms still open

| Item | Value or disposition | Basis |
|---|---|---|
| Scope | CHORUS, one descriptive feasibility attempt; not a native replicate or a matched runtime-only experiment. Retain D91 shared-v1 differences. | **OWNER DECISION:** D91/D107/D25. |
| Receipt instrument | v4 primary; full v5 not activated. Tool-receipt origin and full-to-core transformation measures are secondary, non-gating and separately identified. | **OWNER DECISION:** D105. |
| Effort/account | Explicit literal `high`; LBL work Claude Max first-party account; no API key. The public label contains no private account identifier. The account-choice sidecar records intent only. | **OWNER DECISION:** D106. **CODE FACT:** `native_generation.py:39`, `native_permission_probe.py:35`. |
| Native receipt floor | `{state: pending, mode: diagnostic_pilot}`. Report the floor; owner-defined canary acceptance requires every other row. A registered native floor is needed before any native replicate. | **OWNER DECISION:** D109 (2026-11-08T07:20Z). **CODE FACT:** `native_shared_receipts.py:296` returns pending with `passed: False`. **PENDING N1 / INTEGRATION:** implement the reviewed acceptance/readback mapping without relabelling a pending floor as strict success. |
| Dollar backstop | `budget_guard_usd` is the exact decimal string `90`; the launch word must state the guard and its stop role. It is not the subscription's cash value or a token conversion. | **OWNER DECISION:** D110. **CODE FACT:** argv always includes this field, `native_shared_registration.py:48`. |
| Overage | Disabled for the entire canary; the owner confirms this in the separate launch word. | **OWNER DECISION:** D111. |
| Starting seven-day utilization threshold | **PENDING N1**. The historical proposed 0.50 is not selected here. | **CODE FACT:** `native_subscription_guard.py:163` uses the explicitly supplied threshold. It is an admission ceiling, not a mid-run slice allowance. |
| Freshness interval | **PENDING N1**, chosen within the implemented 1–300-second bound. Do not substitute the maximum as the registered value. | **CODE FACT:** `native_subscription_guard.py:164`. |
| Captured quota event and provenance | **PENDING N1:** how the owner obtains the supported saved event, its capture time, provenance and exact evidence location. A usage-page reading is not automatically a native `rate_limit_event`; do not fabricate one. | **OWNER DECISION:** D106 assigns the owner the headroom check. **CODE FACT:** `native_subscription_guard.py:170` consumes the saved event shape. |
| Five-hour window | **PENDING N1:** record/disposition before dispatch. Current admission is seven-day based; recording a five-hour value does not create a new software gate. | **CODE FACT:** `native_subscription_guard.py:170` and `:207`; review #5542 P2-4. |
| Deadline | **PENDING N1**. The proposed six-hour value and offline 180/900-second fixture limits are not selected as the live deadline. | **CODE FACT:** explicit bounded runtime field in `native_shared_runtime_values.py:144`. |
| Exact binary/model/thinking identities | **PENDING N1 / REGISTRATION:** durable binary path, version/hash, primary and auxiliary models, requested/returned identity recording, thinking setting and context-mode environment. No model or fallback value is invented here. | **OWNER DECISION:** D106 requires recording. **CODE FACT:** `native_shared_runtime_values.py:24`, `native_shared_registration.py:46`. |
| Fallback and toolchain exposure | **PENDING N1:** exact model-fallback disposition, agent-definition exposure, tool allow-list and launch flags. These are separate choices; an allow-list does not describe all exposed agent definitions. | Review #5542 P2-5/P2-7; **CODE FACT:** current literal native flags in `native_shared_runtime_values.py:33`. |
| Keep-awake | **PENDING N1:** selected policy and failure handling. On macOS the implementation offers `macos_iokit_ims_v1`; the runtime also admits an explicitly justified `not_applicable`. Do not replace the registered policy with an informal `caffeinate -i` wrapper. | **CODE FACT:** `native_shared_runtime_values.py:150`; review #5542 P2-2. |
| Registration lifetime | D107 requests a two-week default. Exact start event, expiry semantics and ratification are **PENDING N1**; do not silently repurpose an older offline-acceptance time box. | **OWNER DECISION:** D107 drafting scope; review #5542 P3-7. |
| Stop authority, classification and acceptance | Owner is operator. Detailed automated/manual stop mapping, native failure classifications, independent acceptance procedure and any rating-route adoption remain **PENDING N1**. | D107 drafting scope; review #5542 P1-4/P2-1/P2-6. No A21-specific delegated stop authority is inherited. |

The complete [#5542 independent review](../../../d4d-executions/plans/reviews/pr5542_claude_review_2026-11-08.md) was considered. Its reviewed head was `b187e7160a7bce34816d70d5e9e8aa416c7c5644`; it reported five P1, eight P2 and ten P3 findings. D109–D111 subsequently settle the floor, dollar guard and overage choices, but do not prove that the revised amendment, runtime or acceptance mapping has been implemented or ratified. Re-check the revised amendment by immutable SHA; do not infer fixes from a moving PR label.

## 2. Preconditions before making a registration

These are software/delivery prerequisites, separate from acceptance of the eventual saved canary record. All remain open until their exact-source evidence is named:

1. Accepted U1+U3 integration, including the completed D10 composition and reviewed A6/C7 behavior, on the accepted released schema; all four owner-approved protected packets installed atomically with verified pre/postimages.
2. Explicit additive selection with captured prompt/playbook/schema/profile/source/context identities and runtime/receipt/audit limits; conflicting selections refuse before an attempt. Historical selectors, renderer captures, policies and artifacts remain intact.
3. Correct neutral role/status/date/granularity rules; each long shared contract once; actual typed-helper phases and applicable checks on every selected surface. No common-label parity claim.
4. Complete supervisor path: immutable original full/core/effective receipt, mandatory workers and every source chunk including negative/redundant chunks, source-first omissions, checked integration/assembly, available accounting, and candidate merge/drop lineage.
5. Exact derived audit through reconciliation; complete role-bearing owner context in report/recheck; rederived core; schema/pair/removal/attribution-correction/final-evidence/recorder gates and independent saved reconstruction. Saved success flags alone are insufficient.
6. Permission, authority, one-use, timeout/signal/first-error/cleanup/readback proofs; explicit limits and honest unavailable metrics. Pending receipt floors remain pending.
7. Actual public adapter plus ordinary Python protocol peer and genuine offline helpers: successful correction and exact failed readback; missing/stale workers, omitted chunks, changed authority, unrelated assembly, corrupt lineage, interruptions and terminal/cleanup faults without repeating consumed work.
8. Descriptor, guide and specificity scanner reconciled only after complete-path proof; independent adversarial review, exact-head full CI and merged-byte verification before delivery. All seven #4354 engineering criteria must be covered; the receipt floor is an additional record-level policy decision, not a replacement for criterion 7.

**Schema blocker:** preparation source declares 3.1.0 (`d258611c5:src/data_sheets_schema/schema/data_sheets_schema.yaml:17`). The pinned external 3.2.0 input still declares the five prefixes that D108 orders removed (`5e382f0c4:src/data_sheets_schema/schema/D4D_Base_import.yaml:13`). Use an accepted D108-compliant release and regenerate affected captures; do not copy historical postimages over newer source. Preserve 3.1.0 release bytes and old registrations.

**Amendment blocker:** N1 must be a separate dated amendment beside the unchanged D65 binding analysis plan, independently reviewed and ratified by its own file/commit/SHA-256. Record an explicit disposition for each proposal and review finding. This draft guide is not that ratification. N1's native registration gate does not itself block A21; D93 separately governs A21's rebuild and freeze.

## 3. Pin preparation and obtain the separately authorized real-binary probe

After §2 and the applicable N1 decisions are complete, freeze source/dependency/schema/input/context/scientific-asset identities, the actual registered runtime and exact argv. Pin the binary version/hash and account-choice document without publishing private account identifiers or credentials. Check the actual selected account under a separately authorized observation procedure; the literal label and subscription-kind expectation do not establish which account is logged in.

The real-binary permission probe is a separate authorized action. It uses the exact retained executable and a scripted local provider, an explicit probe deadline and a fresh evidence root. It must not use external provider credentials or fall back to generation. Its synthetic local transport token is not a live API key. No completed probe or final generation launch word is required to request this probe; those would be circular prerequisites.

Inspect its persisted manifest, version/binary/source/runtime pins, permission traces, outcomes and cleanup. Validate saved observations through the current saved-probe consumer. A saved-verifier pass does not establish account authenticity, production helper execution, receipt-policy bytes or scientific acceptance. A real local-provider probe does not establish live subscription-generation success. **CODE FACT:** `native_generation.py:63` and `:116`; the probe is explicit, while `validate-probe` does not run a producer.

Any change to selected code/assets/runtime/binary after the probe invalidates affected pins. Repeat affected review/probe evidence under new identities; do not reuse its success hash for another package.

## 4. Build and review the one-attempt packet

Only after the real-probe evidence is available, prepare the exact execution registration and independent review/CI evidence. Preserve one-use attempt and output identities; no reservation is consumed by drafting. The packet includes:

- registration, independent review, CI and real-probe SHA-256s;
- accepted merged source and dependency manifest; full/core schema closures; bundle/chunk/context/profile/scientific-asset identities; native/API declared differences;
- literal high effort, selected LBL work Max account intent, exact binary/model/auxiliary-model/thinking/argv/toolchain/permission identities;
- receipt checker v4 and the D109 pending diagnostic floor; separately named D105 secondary measurements;
- the D110 $90 backstop and D111 disabled-overage confirmation, plus every ratified threshold, deadline, freshness, keep-awake, lifetime and stop term;
- new label/attempt/output paths, capture/readback locations, input and output inventories, and the amendment's independent acceptance and classification procedure.

N1 must resolve the relation between D109's reported floor exception and current strict completion/readback before this packet is ready. Do not turn the code's pending `passed: False` into `True`, copy an API floor or accept an incomplete terminal record merely because D109 makes the measurement non-gating.

The four evidence hashes above are not the four protected source packets. The source-packet approval, permission to probe, one-attempt launch word and acceptance signature are separate acts.

## 5. Owner word first, then fresh guard capture and dispatch

This guide supplies **no launch word**. The owner reviews the immutable packet and separately supplies its exact one-attempt authorization, stating all ratified stop terms and disabled overage. The final subscription guard cannot be built before that word because it hashes the actual word bytes (`native_subscription_guard.py:150`).

After the word, the owner obtains the supported fresh saved quota event by the **PENDING N1** procedure. Record capture time, provenance, seven-day utilization before launch, reset time and the five-hour-window disposition. Do not manufacture a native event from a web-page percentage. The event is caller-supplied evidence, not authenticated account state.

Use offline guard preparation to bind the exact registration/runtime/word/event bytes and the ratified threshold and freshness. The front door requires its closed D105/D106 account-choice sidecar bound to the subject/runtime hashes; the expectation-side choice used for the probe is not interchangeable with the registration-side choice. Each sidecar records intent only.

Immediately before the separately authorized dispatch, re-read and verify the selected files, ensure the observation is within its chosen age and reset window, and confirm the attempt is unspent. Delay until after expiry means refuse and follow the ratified recapture procedure; do not alter timestamps or let an old guard age while waiting for permission. The current maximum is 300 seconds, not a selected default. **CODE FACT:** `native_generation.py:138`; `native_subscription_guard.py:191`.

## 6. Keep-awake, observations and stops

Run only under the registered keep-awake policy. The supported macOS policy is `macos_iokit_ims_v1`, with its acquisition/failure/release evidence; its selection and failure consequences remain **PENDING N1**. An external `caffeinate -i` command does not substitute for the registered IOKit contract. Do not turn the U6 quiet-host measurement lock into a live-canary requirement unless the amendment explicitly adopts it.

| Event | Actor and evidence | Disposition |
|---|---|---|
| Unsafe/unknown quota status, overage or exhausted observed window | Current controller guard observes the native event and records the observed stop reason and snapshot. | **CODE FACT:** `native_subscription_guard.py:207`. Record actual evidence and unavailable readings; preserve the controller's first terminal reason separately. D111 requires overage remain disabled. |
| $90 backstop, registered deadline or keep-awake failure | Registered runtime/supervisor; record the exact observed trigger, terminal state and cleanup. | Dollar backstop is **OWNER DECISION D110**. Exact deadline and keep-awake terms/classification are **PENDING N1**; no invented enforcement claim. |
| A software admission refusal | The relevant verifier refuses before dispatch; preserve refusal evidence and whether any reservation was consumed. | No attempt is credited as run or accepted; use the ratified failure classification. |
| A per-record acceptance failure discovered after completion | Independent review/readback identifies the failed row; retain all original outputs and the review. | **PENDING N1** final classification and continuation decision. Do not describe this as a mid-run event already monitored by the controller. |
| Manual intervention | The owner, as operator, uses the reviewed stop procedure; preserve reason, timestamps, output inventory and cleanup. | **PENDING N1** exact native stop procedure. No A21-specific delegated authority transfers automatically. |

The starting utilization ceiling is not a continuously measured quota allowance; no API-token-to-subscription conversion is implied. Preserve before/after seven-day observations and the guard snapshot; if a value cannot be observed, record it unavailable. A stopped attempt is retained and never resumed or re-run under the same identity. Any later proposed attempt requires a new label, registration, reviewed evidence and separate owner word; N1 must state the applicable classification and retry policy.

## 7. Readback and acceptance after the attempt

Use the offline saved readback route, not a launch command. It independently reconstructs captured evidence and must detect changed bytes, incomplete lifecycle states, incorrect receipts/audit/assembly or consumed-attempt inconsistencies. Preserve the original record, effective receipts, full/core pair, report, requests/replies, workers/chunks, journals, tool/permission history, runtime/account observations, quota snapshots, terminal/stop record and cleanup evidence. `read-final` is not permission to resume. **CODE FACT:** `native_generation.py:167`; `native_shared_results_orchestration.py:31`.

Keep three conclusions distinct:

1. **Software prerequisites:** #4354 criteria proved on the accepted implementation, including fault cases that cannot be proved from this one live output.
2. **Per-attempt evidence:** actual full/core schema and pair validity, duplicate-key count, report totals versus `audit_counts`, structural receipt checks, chunk completion, permission-denial counts, accounting and declared limits. D109 reports the pending final-record floor; it is not strict success. Clean/assisted status and any interventions remain explicit. Final native applicability of record-level rows is **PENDING N1**.
3. **Scientific acceptance:** independent blind source review under the ratified acceptance procedure and the owner's signed acceptance record. Neither checker success nor a completed terminal substitutes for this review. The native rating route and descriptive rating authorization remain **PENDING N1**; do not insert this canary into API/v8 evaluation aggregates or replicate means.

Retain the attempt regardless of outcome. A subsequent reviewed data/publication change must preserve historical originals. Quoted source text, valid receipts and verbatim copies do not independently prove entailment or justify `exactMatch`/`none`; retiring rows cannot improve measured source coverage.

## 8. Final handoff boundary

Before replacing DRAFT with an operator-ready guide, name the accepted merged source and schema commit, four installed packet hashes, final scanner/render/acceptance artifacts, ratified amendment SHA, exact registration/review/CI/probe identities and all filled N1 terms. Re-review this guide against those actual bytes. D93 puts the A21 rebuild/review after native integration; D35's freeze starts at that rebuilt registration. This guide neither reinstates an old A21 word nor grants a new native word.

This file was prepared by read-only source/decision inspection and bounded documentation edits. No native executable, probe, launch, account access, network/provider call, GitHub action, scoring or acceptance review was performed.
