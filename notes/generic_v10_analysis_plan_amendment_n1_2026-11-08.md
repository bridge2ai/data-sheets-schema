# generic_v10 analysis plan, amendment N1: the native agentic (direct) arm

**Status: draft v6.1, written by claude (lead) on 2026-11-08.**
- **v1:** an in-place edit of the plan file (PR #5542 head `b187e7160`), reviewed by Claude (review sha256 `6f09cc8e…`).
- **v2:** a separate file (`bc53c1ce…`), re-reviewed by Claude (`37309f2d…`) and Codex CLI (`d49ed159…`).
- **v3:** `e8b475c4…`.
  - Claude re-review: 3 P1, 6 P2, 13 P3, with 33 prior findings resolved and 7 partly.
  - Codex re-review: 1 P1, 3 P2, 1 P3.
- **v3 → v4:** responded to every v3 finding and took in D115 and D116. Codex's R5 was checked and withdrawn.
- **v4:** `9edff5b9…`.
  - Claude re-review: 1 P1, 3 P2, 9 P3; all 27 prior findings resolved.
  - Codex re-review: 1 P2, 1 P3; its v3 findings resolved, and R5 withdrawn as its own error.
- **v4 → v5:** responded to every v4 finding, and took in D117 and D118.
- **v5:** `ece2c8b3…`.
  - Codex re-review: ratifiable as is.
  - Claude re-review: 0 P1, 1 P2, 7 P3; all 15 prior findings resolved.
- **v5 → v6:** fixes that P2 and the seven P3s, and nothing else.
- **v6:** `18f29f83…`. Both narrow re-checks found it ratifiable as is: Claude with three optional wording nits, Codex with none.
- **v6.1:** applies those three wording nits only.
- **It is not binding until:**
  - a Claude reviewer and a Codex CLI pass re-review it, with each finding filed;
  - the owner ratifies it by naming this file's sha256 at a commit and answering each lettered item of N1.8;
  - and it merges only after that word, and before the native registration.
- **Values marked [proposed]** are the lead's choices. They take effect only through N1.8. Unmarked rules are the owner's decisions or the plan's own text, each cited.
- **Review files** live outside the repository, under `d4d-executions/plans/reviews/`. They're cited by sha256:
  - v1 review: `6f09cc8e5f71d052024f0c0046f946a2d071162c3cde6cb377d596f7415e4fa6`;
  - v2 re-reviews: `37309f2dd70a45c8089947fe3256881d0a475fac6920c342a748bac537921e54` and `d49ed15954e5354275668b3dce5863c395a7365ea407d787fff8c43b379b004e`;
  - v3 re-reviews: `1e0bb1cdef678f7464813ac0468f0798c987545b63552158c86c5a6012eca8cb` (Claude) and `5f66e4bea9117d9e2bac0484c5fc41cef65ee0f19cb3d22b4af7b3ab88d67d7b` (Codex);
  - v4 re-reviews: `07311a51cae2a60c11c8f371250792e3176a9a1ba759e353d90cb3e271bae80d` (Claude) and `0408c6f670b880137092ac2a782bbc73ccb973f38d86153fc2b53cdf2d858ac3` (Codex);
  - v5 re-reviews: `a88cf25364db8d80b9b9fac95582c9c73edcf38166e5a4f57e2018f71823b0a9` (Claude) and `73df58bf3fac3b707ce140abb5432c160e34e3df21813361431bf67fb13179e6` (Codex);
  - the U4–U7 readiness plan: `07ebb68661512e6f0d4bd04b42523b3930a8ce952f9b89148babf061195d9a6f`.
- **The saved #4354 issue** was fetched 2026-11-08; the issue was last updated 2026-11-07T02:53:46Z. Its body sha256 is `7f6a07a063796414866f282afdd3008a6e9723e2cce816c60eacf5bff21d687c`, computed over the UTF-8 bytes of the API's `body` field with no trailing newline.

## Authority
- **The plan being amended:** `notes/generic_v10_analysis_plan.md`, ratified at commit `5b17ae079c8eb1fa4abdda3261054bfd22e4c2f1` with sha256 `b4a4f9a596173d3bdeb817b01ea53fb1a1d77574e121c7cecaf6f63b67fd4b4b` (D65). That file is not edited; this amendment stands beside it, as P4a amendment 1 does (sha256 `7b1a3e79ee12c33193b0e8c58de8bbfae02a57944aee19830f9a923ec55eccb7`, ratified by D71).
- **Plan item 43** asks for a dated amendment that settles the native decisions before the native registration, without blocking A21.
- **The owner's decisions.** These are excerpts from the coordination record, which is not in the repository. Text in quotation marks is exact; everything else is a summary.
  - **D105:** "Receipts v5 is not activated for final generation." v4 stays the registered instrument. v5's tool-receipt origin and the full→core transformation receipts are "secondary, non-gating measurements".
  - **D106 (resolves D29's effort and account):** "Native effort: explicit `high`" (`--effort high`).
    - The account is the LBL work Claude Max account, first party, the same as the v6 agentic arm, with no API key.
    - "The owner checks the seven-day usage headroom before launch."
    - "The registration records the Claude Code version and binary sha256 and the thinking setting."
  - **D107:** a dated native amendment, drafted by claude with the plan's proposals as defaults, independently reviewed, then ratified by the owner before the native registration. "None of it blocks A21." Its defaults:
    - D09: the pause applies only to the old generic_v9 arm;
    - D11: the binary and hash are pinned at registration;
    - D12: the owner is operator, claude orchestrates, and a Claude-plus-codex review pair reviews;
    - D13: the toolchain exposure, launch flags, runtime-closure fix and receipt origin are pinned;
    - D14: the old spend package is re-validated against subscription usage;
    - D18: a two-week time box from registration;
    - D25: no native canary counts as a replicate;
    - D91 scope and receipt v4;
    - the first canary is CHORUS with one replicate;
    - "the stop rule is any acceptance-row failure or the usage limit".
  - **D109:** the native receipt floor for the CHORUS n=1 canary stays `{state: pending, mode: diagnostic_pilot}`. "The canary counts as "accepted" when every other acceptance row holds. Its policy-v1 floor reading is reported, not gated." "The measured value informs a registered native floor before any native replicate."
  - **D110:** `budget_guard_usd` = 90 (`--max-budget-usd 90`). "It's a backstop, and it's a stop trigger the launch word states."
  - **D111:** "Extra usage (overage) stays disabled on the account for the canary's whole duration." The owner confirms that state in the launch word.
  - **D112 (completes D29's runtime-limit basis, plan §2):** the native canary runs with the 1M context, `CLAUDE_CODE_DISABLE_1M_CONTEXT=0`, pinned from the real-binary probe.
  - **D113 (A13 and D07 for the native cell):**
    - a rule-level rejection of the native canary ends the native shared-v1 cell only, not the API arm's generic_v10;
    - at most two native canary attempts, each with its own label, registration and word;
    - transport or budget stops are distinct from a scientific rejection.
  - **D114 (#4019):** narrow `toolchain()` to the generation agents, so the native run sees no study-specific agent files. This is a code change before the registration.
  - **D115:** `AUTHORIZE_ONE_NATIVE_ATTEMPT` also authorizes up to three admission-capture calls for that attempt.
    - **A capture** is a tiny live Claude Code call on the same account, with the same binary, model, effort and context, a fixed trivial prompt, no repository content, and a capture-only config directory outside every attempt path.
    - A stale or failed capture may be retried under the same word, up to the three.
    - Captures never count against D113's two attempts, and every capture is recorded.
  - **D116 (corrects D112's mechanics; the intent is unchanged):**
    - `limits {contextWindow, maxOutputTokens}` come from the probe's terminal `modelUsage` entry, and the thinking setting from its captured request body. The init line carries neither.
    - The model is requested as `--model claude-opus-5[1m]`, with a declared alias pair that the gates check exactly: requested, init and `modelUsage` are `claude-opus-5[1m]`; returned messages are `claude-opus-5`.
  - **D117:** one separate real-binary probe authorization covers two probe runs, both against the scripted local provider, with no account usage.
    - **The observation probe,** under a provisional runtime, reads the limits from terminal `modelUsage` and the thinking setting from the captured request body.
    - **The bound permission probe,** under the final runtime, has a `limits_basis` that names the observation probe's saved bytes.
    - The first live capture's terminal `modelUsage` limits must equal the registered limits, or the attempt is refused before its reservation.
  - **D118:** admission also requires five-hour utilisation ≤ 0.25, alongside seven-day ≤ 0.50. A mid-run five-hour exhaustion is still possible; it is a usage stop that counts as an attempt.
  - **D36:** "Models review; you sign; seed (Recommended)".
    - A fresh Claude session does the blind source review, with a Codex CLI pass. Neither generated nor operated the run.
    - The owner signs each acceptance record.
    - "a second blind model reviewer writes audit-recall observations, pinned to `original_full`'s sha256, before anyone reads the audit".
  - **D43:** "You launch it (Recommended)". The owner runs the exact launch command after giving the word on the sha256. "The guard and the rule that any assisted run is evidence-only both still apply."
  - **Also applied:**
    - D26 and D27 (the arm and its directories);
    - D53 (nothing is edited inside a run directory);
    - D56 (every retry is a new registration);
    - D65 and D71;
    - D89 (native first);
    - D91 (the declared shared-v1 differences);
    - D93 and D35 (sequencing);
    - D98, D99 and D108 (schema 3.2.0's content).

## Decision status (moved here from the plan's decision table)
| Item | Status after ratification |
|---|---|
| D29 | Effort and account resolved by D106; runtime-limit basis resolved by D112 and D116 (N1.2) |
| D09 remainder, D11, D12, D13, D14, D18 | Settled in N1.3 |
| D25 | Settled by D107's default (N1.3) |
| Plan item 43 | Settled by this amendment |

The plan's own rows (D29 "Pending owner"; D25 and item 43 "Pending: the native amendment") stay as ratified. For readers of the amendment, this table supersedes them.

## N1.1 Scope and condition
- **The arm:** native agentic, also called direct (Track N, D26). Records go under `claudecode_direct{,_core}/<label>/` (D27).
- **Protocol axes, kept separate:**
  - native shared generation v1 (`native_shared_generation_v1`);
  - native renderer 26;
  - native receipt policy v1;
  - execution authority v2;
  - receipt checker instrument 4.

  The first four exist today on native branches only. Their binding bytes are those of **the accepted U1+U3 merge commit on main** (the readiness plan's gate G0), which the registration names. The first native canary uses the declared shared-v1 differences (D91), not BC1 parity.
- **Schema** [proposed]: the released 3.2.0 (content: D98, D99, D108), once it has merged and the native integration has been re-validated on it.
  - For the native arm, this **supersedes D71(a)** ("Schema 3.1.0 as the v10 condition's schema"). The API arm's schema is unchanged by this amendment; A21's rebuild needs its own amendment if it moves to 3.2.0.
  - **P4a amendment 1's native hand-offs are taken up here:**
    - the native arm reads the schema files directly;
    - it has **no write-time normaliser**, so a resolver URL or an EDAM URL written where a CURIE is required stays in the record and is counted as a finding, not rewritten.

    This is a declared difference (N1.6).
- **Receipt instrument:** checker v4 is the registered, gating instrument (D105).
  - The two D105 secondary measures are recorded under their own identities, never pooled with v4 (plan §3a):
    - the **transcript-based receipt origin** (`receipt_origin.py`, `native_receipt_origin.py`; #2933, #4445, #4447). These are not v5's model-written `tool_receipts`.
    - the offline **full→core transformation receipts**.
  - [proposed] The transcript-based receipt origin is the "receipt origin" that D107's D13 default pins: one measurement, named twice.

## N1.2 Runtime and account
- **Runtime:** the Claude Code CLI, with `--effort high` (D106).
- **Runtime limits and model (D112, D116):**
  - `CLAUDE_CODE_DISABLE_1M_CONTEXT` is `"0"`;
  - `--model claude-opus-5[1m]`;
  - the declared alias pair, which the gates check exactly: requested, init and `modelUsage` are `claude-opus-5[1m]`; returned assistant messages are `claude-opus-5`. Any other model string refuses;
  - `limits {contextWindow, maxOutputTokens}` come from the **observation probe's** terminal `modelUsage` entry (D117). The final runtime's `limits_basis` names that probe's saved bytes by sha256, and the bound permission probe then runs under the final runtime. One probe can't supply the limits of the runtime it ran under. The observation probe's provisional runtime must equal the final runtime in every field except `limits`, `limits_basis` and the thinking field;
  - [proposed] **every** live capture's terminal `modelUsage` limits must equal the registered limits. D117 names the first, and checking each one is the stricter reading.
    - A mismatch means the registered limits are wrong, so a re-capture can't cure it. It refuses this registration before any reservation, so no attempt is consumed. A new registration with a new observation probe is needed, and with it a **new probe authorization**, because D117's covers only its two runs.
    - This is also where an account that doesn't serve the 1M build would first show;
  - the live accounting gate refuses any difference from them.
- **The thinking setting** comes from the observation probe's captured request body (D116, D117). It's recorded in a field of the runtime declaration, so it follows the same two-step sequence as the limits (D106). A missing value refuses the registration (N1.9 item 6). The attempt runs with a fresh `CLAUDE_CONFIG_DIR`, so the account's own settings don't carry over.
- **1M entitlement is not yet proven.** The real-binary probe runs against a scripted local provider, so it can't show that the Max account serves the 1M build. The first live evidence is the first capture (N1.5).
- **Auxiliary models** [proposed]: none.
  - **Disclosed risk:** with an empty auxiliary list, any call to another model stops the attempt. The first subscription canary showed none.
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` is fixed in the policy environment (`native_shared_runtime_values.py`, `POLICY_ENV`); it's not a choice made here.
  - **A fallback model can't be passed,** by construction: the runtime key set is closed, the flag list is fixed, and `model` cannot be a CLI option.
- **Recorded identities, three observations kept apart:**
  - the **requested and init** identity (`claude-opus-5[1m]`);
  - the **returned** identity, per assistant message (`claude-opus-5`);
  - the **terminal accounting key** in `modelUsage` (`claude-opus-5[1m]`).

  Their relationship is the declared pair. The native transport has no per-call request record (criterion 5).
- **Account:** the owner's LBL work Claude Max first-party account. No API key, no CBORG route, no provider fallback.
  - The label "LBL work Claude Max" is public by design: the native outputs emit it as `ACCOUNT_LABEL`.
  - No account identifier or email address appears in any public record.
- **D11:** the registration pins the Claude Code version and binary sha256 (D107).
  - [proposed] The pinned executable is a **durable copy** outside the auto-updater's path, so that an update inside the validity window can't change the pinned sha. This was the 2026-10-25 packet's source recommendation, §4.3.
  - A different binary is a different registration.
- **Declared confound:** effort differs from the API arm, which runs at the provider default (D09, plan §4). It is recorded, not corrected.

## N1.3 The remaining owner items
| Item | Ruling |
|---|---|
| **D09 remainder** | The direct-arm pause applies only to the old generic_v9 arm. It does not apply to this arm (D107). |
| **D12** | The owner is the operator: the owner holds the account, gives the launch word and launches (D43). claude orchestrates. The registration and its packet get an independent Claude review plus an independent Codex CLI review, by neither its author nor its operator (D107). This supersedes generation plan N9's "codex-operator". |
| **D13** | The registration pins:<br>• the **toolchain exposure**, narrowed to the generation agents under D114 (#4019);<br>• the **tool allow-list**;<br>• [proposed] the **literal launch argv, recorded verbatim** (#4162's recorded-argv option), including `--safe-mode`;<br>• the **runtime-closure fix**, PR #2922 (#2714), merged 2026-10-17;<br>• the **transcript-based receipt origin** (#4445).<br>[proposed] Any change to these is a new registration. |
| **D14** | The budget is subscription usage, plus a dollar backstop.<br>• **Re-validation, done by this amendment.** The 2026-10-25 packet's sources recommended a starting seven-day utilisation ≤ 0.80, an overage stop or overage disabled, a $90 guard and a 21,600 s deadline. Since then:<br>&nbsp;&nbsp;– the seven-day window was exhausted on 2026-10-24;<br>&nbsp;&nbsp;– D106 named the account;<br>&nbsp;&nbsp;– D110 set the guard;<br>&nbsp;&nbsp;– D111 disabled overage;<br>&nbsp;&nbsp;– D112 chose the 1M context, which spends headroom faster.<br>• **The result is N1.5's terms.** Any later change to them is a revision of this amendment, which the owner approves. |
| **D18** | [proposed] D18's original subject, a time box for #4354's offline acceptance, is closed by this amendment.<br>[proposed] D18 now means a **two-week validity window** for the native registration, counted from the **author date** of the commit that adds the reviewed registration file. A rebase or cherry-pick keeps the author date. After the window, the registration expires and a new one is needed. |
| **D25** | No native canary counts as a replicate (D107). A canary is descriptive feasibility evidence only. |

## N1.4 Acceptance
### (A) Software prerequisites: #4354's criteria 1–7, proved offline before registration
These are quoted verbatim from #4354; the body sha256 is above. They are software proofs, made at U3–U7, and they are not themselves rows on a live attempt.
1. "Bind an explicit native shared-protocol selector, captured prompt/playbook/schema/profile/source/context identities, caller-supplied runtime/receipt/audit limits and supported arm. Missing or conflicting declarations refuse before consuming an attempt. Preserve old default selectors, renderer captures, policy identities, historical registrations and artifacts."
2. "Generate the same selected neutral role/status/date/granularity rules, with each long shared contract paragraph occurring once in the complete native instruction. The native instruction must describe the actual typed-helper protocol and its phases. Preserve applicable checks in every selected request/helper surface; do not claim cross-arm parity solely from a common label."
3. "At the real native supervisor boundary, enforce immutable original full/core/effective receipt and complete typed worker, source-first omission, integration and independently checked assembly. Capture exact requests/replies, phase transitions and available accounting evidence. All registered chunks and workers are mandatory, including negative/redundant receipt chunks. Preserve model-declared candidate merging/drop decisions and their checked lineage."
4. "Carry the exact derived audit into reconciliation, retain complete role-bearing owner context for report/recheck, rederive core and preserve existing schema, pair, removal, attribution correction, final evidence and recorder gates. The final saved result must reconstruct the selected assembly and bind it to this attempt and downstream audit; saved success flags are insufficient."
5. "Retain the reviewed native permission, authority, one-use reservation, timeout/signal, first-error, cleanup and saved-readback contracts. Do not copy API token-count/accounting claims onto a native transport that cannot provide them. Caller limits, unavailable measurements and unsupported combinations must remain explicit. A pending scientific receipt floor cannot become strict success."
6. "Exercise the actual public native adapter with an ordinary Python protocol peer plus genuine offline helpers, including a successful correction path and exact failed readback. Test missing/stale workers, omitted chunks, changed authority, unrelated assembly, corrupt lineage, interruption and terminal/cleanup faults without repeated consumed work. These are synthetic software proofs; no real native executable, auth probe, provider request, permission probe, model, scoring or paid canary is authorized."

   The live canary is authorized only by its own word (N1.5).
7. "Update the public descriptor, guide and specificity scanner to disclose the new supported arm and actual optional/dynamic phases only after complete-path validation. Retain historical bytes and capture source identities before edits. Final independent adversarial review, exact-head full CI and merged-byte verification precede delivery."

### (B) Per-attempt acceptance, judged on the saved result after the attempt ends
[proposed] **The row set.** Plan §5 defers the native rows to this amendment. These are taken from the plan and generation plan N10, not from #4354.
0. **Controller completion.** The saved result reads `state: completed_pending_independent_review` with `runtime_gates_passed: true` over all 15 runtime gates (`native_execution_engine.py`). N1.9 item 9's `audit_counts` row sits inside the `evidence` gate, so the count stays 15. The gates:
   - terminal, shutdown, first_stop;
   - live_attribution, saved_attribution;
   - phase_history, tool_history;
   - schema, pair, receipts, evidence;
   - observation, accounting;
   - runtime_authority, keep_awake.

   The receipts gate uses the structural floors only, so D109's pending floor doesn't block it.
1. **Readback.** An independent `read_final` reconstructs the selected assembly and binds it to this attempt and its downstream audit. This is criterion 4's saved-result property, read on the live attempt's bytes.
2. **Record rows** (the A11 equivalents):
   - the full and core records validate;
   - duplicate keys are 0;
   - the report totals equal `audit_counts` (#4766), through the explicit equality row inside the `evidence` gate (N1.9 item 9);
   - the five phase-1 structural receipt floors that `check_initial` computes (`native_shared_receipts.py`) are each 0:
     - chunks unreviewed;
     - snippets unverified;
     - addressing slips over #891's tolerance of ceil(verified/200);
     - receipts vacuous;
     - receipt findings.
3. **Tool history**, generation plan N10 mapped to the typed protocol [proposed]:
   - **Permission denials:** zero prescribed or unclassifiable denials.
   - **Ordering.** N10's per-chunk file-tool ordering doesn't apply: the typed protocol's phase 1 writes the full record and the whole original receipt in one stage (`native_shared_generation_v1.md`), and chunks are never dispatched one by one. What applies instead, both shown from the saved `phase_history`:
     - the phase-1 receipt is checked before the seal and `derive_core`;
     - the strict receipt check passes before any typed-audit dispatch.
   - **`receipt_chunks_unopened` is reported only.** The instrument counts permitted read-only shell lookups (`sed -n`, `cat`) as unopened, and the native instruction doesn't impose #709's file-tool duty. A missing measurement is reported as unavailable, not zero.
4. **Clean.** The attempt is clean: an assisted attempt is evidence only and never accepted (D43; plan §1 item 1, §5 row 7, §10). [proposed] The native clean checks, with how each is evidenced:
   - **nothing edited inside the run directory (D53):** the saved-readback byte comparison;
   - **no interrupted write:** the saved-readback and stage journal;
   - **the one-use reservation intact:** shown by the orchestration's reservation record;
   - **no manual intervention** between dispatch and the end of the attempt, other than a stop: an operator attestation in the acceptance record;
   - **no override (D56):** there is no override mechanism natively, so this check is satisfied by construction and recorded as such.
5. **The native policy-v1 receipt floor** is `{state: pending, mode: diagnostic_pilot}` (D109).
   - `native_shared_receipts.floor()` returns `state: pending`, `passed: False` with its counters. The acceptance record keeps that raw result and labels the row UNMEASURABLE.
   - It doesn't block acceptance, and it is never reported as a strict success.
   - The measured counters inform a registered native floor before any native replicate (D109).
6. **Blind source review (A12, D36).**
   - **Who:** a fresh Claude blind source-review session plus a Codex CLI pass, neither of which generated or operated the run.
   - **What:** they review the unchanged originals against the frozen bundle. The plan's A12 scope covers "#1782, #1801/#2924, #1815, #1816 and #2924 dates".
   - **The seed (D36):** a second blind model reviewer writes audit-recall observations, pinned to `original_full`'s sha256, before anyone reads the audit.
   - **The row holds** when the review is complete on that scope, no rejecting-class finding is sustained by the owner, and no evidence stays unresolved (plan §6).
7. **The owner signs the acceptance record** (D36), having adjudicated any disagreement (plan §6).

**"Accepted"** means B0–B4, B6 and B7 hold, with B5 reported (D109). The API-only rows don't apply: the full-phase output cap and the CBORG provider route.

**How N1.8 splits these rows:** (i) decides which rows exist; (j) and (k) decide B3's and B4's content. If (j) or (k) is answered no, that row is revised and re-submitted before registration; the other rows stand.

## N1.5 The first canary, its slice and its stop rule
- **What:** CHORUS, n = 1, descriptive feasibility. Not a replicate (D107, D25).
- **Order of events.** Each step needs the code in N1.9 to be accepted first.
  1. **The registration is reviewed, with its inputs complete.**
     - The two independent reviews of the registration and its packet are complete.
     - The exact-head CI evidence (`ci_sha256`) exists.
     - The bound permission probe (`permission_probe_sha256`) exists.
  2. **The owner writes the statement of launch terms.** [proposed] This statement is what D110 and D111 mean by "the launch word states" and "confirms … in the launch word": the coded word's closed fields can't carry those terms, so the word binds them through the bundle. It states:
     - `budget_guard_usd` "90";
     - the deadline;
     - the maximum starting seven-day utilisation (0.50) and five-hour utilisation (0.25, D118);
     - `max_age_seconds` and the 90 s margin;
     - the overage state (disabled);
     - the keep-awake policy;
     - the context mode;
     - the capture limit (three, D115).
  3. **The bundle is frozen.** The two reviews and the statement are assembled into the review bundle, and its sha256 is taken.
  4. **The owner gives the coded word** `AUTHORIZE_ONE_NATIVE_ATTEMPT`. Its `review_sha256` names that bundle, and its `authorized_at` is a strict UTC timestamp (N1.9 item 4).
  5. **The owner runs the registered capture command** (D115; N1.9 item 3).
     - It runs a tiny live call on the same account, binary, model, effort and context, with a fixed trivial prompt, no repository content, and a capture-only config directory outside every attempt path.
     - It saves the runtime's `rate_limit_event` and its terminal result's `modelUsage`, with the sha256 of the word it ran under.
     - A capture reservation allows at most three captures under this word, and records each one, including stale and failed ones.
     - Captures are not attempts.
  6. **The owner prepares the guard on the latest capture and dispatches.** Subscription guard v2 (N1.9 item 2) admits the attempt only if all of these hold:
     - **[proposed] the seven-day utilisation is ≤ 0.50.** It's stricter than the sources' 0.80 because the window was exhausted on 2026-10-24, the 1M context spends faster, and a canary stopped by the usage limit is lost;
     - **the five-hour utilisation is ≤ 0.25** (D118). Both windows must be present, which is implied by D118's bound under fail-closed admission;
     - **[proposed] both windows are allowed.** A nested window is allowed when its `utilization` is a finite JSON number, not a boolean, with 0 ≤ utilisation < 1, and its `resetsAt` is after both capture and dispatch. Saved nested windows carry no per-window status;
     - **[proposed] a further window type is judged by the same rule when it carries `utilization`, and is recorded but not refused when it doesn't;**
     - the top-level status is allowed or allowed_warning, and overage is explicitly false;
     - **[proposed] One freshness rule with two values:** `captured_at` is no earlier than the word's `authorized_at`, and dispatch occurs within `max_age_seconds` = 300 of `captured_at`. 300 is the code's maximum. The launch path re-verifies the registration several times before the freshness check, and no launch-path timing has been measured yet; U6 may measure one and propose a smaller value as a revision;
     - **[proposed] a margin at the reservation:** at the pre-reservation check, `captured_at + max_age_seconds − now` is at least 90 s. That covers what runs after the reservation and before dispatch: keep-awake acquisition, the runtime probe (`--version` and `auth status`, each with a 30 s timeout) and the binary hash;
     - the capture's terminal `modelUsage` limits equal the registered limits (D117; every capture is checked, as in N1.2);
     - the capture was made under the word the guard binds;
     - **every launch value equals the statement's** (N1.9 item 4). All of these are registration values, and the guard is prepared from them:
       - the guard's seven-day maximum, five-hour maximum, `max_age_seconds` and 90 s margin;
       - the runtime's budget, deadline, keep-awake and context mode.
  - **A capture that fails the margin** is refused before the attempt's reservation, so it doesn't spend the attempt, and the owner re-captures within D115's three.
    - The margin makes a stale-at-dispatch capture unlikely, not impossible.
    - A capture that is fresh at the reservation but stale at dispatch stops the attempt after its reservation. That is an environment stop, an admission failure at the guard's one-use dispatch check, and it counts as an attempt (D113).
  - [proposed] **After three failed captures,** the capture reservation refuses a fourth. The path is a new word for the same registration, if it's still within its validity window. A new word gets three new captures, and no attempt is consumed.
    - This **extends D115**, which says "up to three admission-capture calls for that attempt".
    - A newer word supersedes an earlier one for the same `attempt_id`, so only one word is valid at a time.

  The observation is caller-supplied evidence, not authenticated account state. The threshold is a start-admission rule, not a mid-run allowance.
- **Overage:** disabled for the attempt's whole duration (D111). It's an owner account setting that the statement confirms. `isUsingOverage: false` shows only that no overage was used.
- **Dollar guard:** `runtime.budget_guard_usd: "90"`, a decimal string producing `--max-budget-usd 90` (D110).
  - The runtime enforces it on its own cost estimate.
  - Afterwards, the controller's accounting gate fails the attempt if the reported cost exceeds it.
  - It isn't independently metered billing.
- **Host:**
  - [proposed] the registered keep-awake policy `macos_iokit_ims_v1` (idle, disk and system sleep), on AC power;
  - [proposed] the operator holds the quiet-window lock for the attempt. That's a coordination protocol, not a controller gate, and not proof of a quiet host.
- **What the keep-awake enforces:** a failure to acquire it refuses before dispatch, and a failed release fails the `keep_awake` cleanup gate. A mid-run sleep or loss of the assertion is not detected. Forced sleep, lid closure, thermal or battery policy and power loss aren't prevented.
- **Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch. That's the sources' value, re-validated in D14.
- **Stops, and who enforces them:**
  - **The controller** stops at the first of:
    - the deadline;
    - subscription guard v2's `observe` stop on any window that is no longer allowed by the rule above, or on overage;
    - any refusal or first error at a supervisor boundary.
  - **The runtime** stops itself at its `--max-budget-usd` estimate.
  - **A mid-run five-hour exhaustion** is a usage stop, and it counts as an attempt (D118, D113). The 6 h deadline crosses at least one five-hour reset, and the 1M context spends faster, so this is possible whatever the admission reading.
  - [proposed] **The owner, as operator (D12),** may stop the attempt manually at any time, by the signal and cleanup procedure the launch packet names.
  - [proposed] **D107's stop rule is read as follows.** The usage limit is the live stop above. "any acceptance-row failure" is judged after the attempt on the saved result, because the rows are properties of that result: a failure rejects the attempt, and it is not a mid-run stop.
- **After a stop or a rejection:**
  - outputs, the stop reason and the guard snapshot are preserved. Every attempt is retained, stopped and rejected ones included (plan §7). For a stopped attempt, the after-run readings are reported as unverified, because saved-observation validation applies only to a completed attempt;
  - **classification (D113):**
    - a **transport, budget or environment stop** (deadline, usage, dollar guard, host) is not a scientific rejection;
    - a **rule-level rejection** under N1.4(B) ends the native shared-v1 cell only, not the API arm's generic_v10;
    - plan §10's API-specific rows (the full-phase cap, `api_usage`, the item 5 rows 5–6) don't apply;
  - **at most two native canary attempts** (D113, D07);
  - a stopped attempt is never resumed or re-run under its label (plan §13, D56, generation plan N9). Any new attempt needs a new label, registration and word, and it counts against the two.
- **What the coded word binds.** Its fields are closed (`native_execution_registration_v2.py`):
  - the binding keys: `registration_sha256`, `attempt_id`, `source_commit` and `dependencies_sha256`;
  - `kind`, `version`, `owner`, `authorized_at` and `word`;
  - `review_sha256`, `ci_sha256` and `permission_probe_sha256`.

  The budget, deadline and keep-awake reach the word through the registration hash. Every other launch term reaches it through `review_sha256`'s bundle. The real-binary probe is authorized separately, and that authorization is not a generation word.
- **Supersessions:** this procedure supersedes generation plan N9's `caffeinate -ims` (now the registered keep-awake policy) and its codex operator (now the owner, D12).

## N1.6 Recording and comparison
**Recorded:**
- the arm, `claudecode_direct`;
- the receipt checker v4 instrument string, and separately the identities of the two D105 secondary measures;
- the effort literal and its basis;
- the thinking setting and its source;
- the runtime limits and their basis (D112, D116);
- the three model observations: requested and init, returned per assistant message, and the terminal accounting key (N1.2);
- the binary version and the sha256 of its pinned copy;
- the account kind and label;
- every capture;
- the guard's admission readings (seven-day, five-hour and any further window), its after-run readings (first, last and highest per window; unverified for a stopped attempt), and the guard snapshot.

**The cross-arm contrast** follows plan §1 item 5, with the effort confound of plan §4. Under plan §2 these differences are declared, and the N2 declaration (`be0bd05821256212e89e4d011ba6b30a780e299b`), or the U5 successor that names it by hash, carries them:
- **effort:** explicit high, against the provider default;
- **runtime and transport:** a subscription CLI, not a provider route;
- **tools:** Read, Write and Bash plus the permitted read-only lookups, against the API arm's no-tool boundary;
- **staged exposure:** the typed-helper phases, against the API arm's phase requests;
- **context:** 1M (D112), against the API arm's room;
- **schema:** 3.2.0, against the API arm's ratified 3.1.0, unless A21 moves by its own amendment;
- **normalisation:** none at write time on the native arm, against the API arm's write-time normaliser;
- **protocol:** the D91 shared-v1 differences.

**Native ratings** stay deferred until a native canary is accepted under N1.4(B). Their route is chosen by a separately ratified rating registration, not here.

**Sequencing (D93, D35):** native integration lands first, then A21 is rebuilt on native-integrated main. D35's freeze starts at that rebuilt registration.

## N1.7 What this amendment does not change, and what it does
**Unchanged:**
- the plan file and its sha256 `b4a4f9a5…`;
- the A21 registration and its packet, which bind that sha256;
- any API-arm registration;
- P4a amendment 1 for the API arm;
- any historical decision or record.

**Changed, for the native arm only:**
- D71(a)'s schema, under N1.1 [proposed];
- generation plan N9's keep-awake form and operator, under N1.5.

## N1.8 Ratification: the owner names this file's sha256 at a commit, and answers each lettered item
Each letter is one decision, and a "yes" adopts exactly the value given.
- **(a)** No auxiliary models, accepting that an auxiliary call stops the attempt (N1.2).
- **(b)** The pinned executable is a durable copy outside the auto-updater's path (N1.2, D11).
- **(c)** D13: the literal launch argv recorded verbatim (#4162).
- **(d)** D13: any change to a pinned item is a new registration.
- **(e)** D13: the transcript-based receipt origin is the "receipt origin" D107 names (N1.1).
- **(f)** D18: its old meaning (the #4354 offline time box) is closed.
- **(g)** D18: the registration is valid for two weeks from its registration commit's author date.
- **(h)** Schema 3.2.0 for the native arm, superseding D71(a) for that arm only (N1.1).
- **(i)** The N1.4(B) row set, B0–B7.
- **(j)** B3: the typed-protocol ordering mapping, with `receipt_chunks_unopened` reported only.
- **(k)** B4: the native clean checks and their evidence.
- **(l)** Admission: starting seven-day utilisation ≤ 0.50. D118's record restates this value; a "no" here supersedes D118's restated 0.50 for this amendment.
- **(m)** Admission: a window is allowed when its utilisation is a finite non-boolean number with 0 ≤ u < 1 and its reset is after capture and dispatch. D118 sets the five-hour bound, and presence of both windows is implied by it.
- **(n)** Admission: a further window judged by the same rule when it carries `utilization`, and recorded but not refused otherwise.
- **(o)** Freshness, one rule with two values: `captured_at` ≥ the word's `authorized_at`, and `max_age_seconds` = 300.
- **(p)** Deadline: 21,600 s.
- **(q)** Host: keep-awake `macos_iokit_ims_v1` on AC power, accepting that mid-run loss is undetected.
- **(r)** Host: the quiet-window lock held by the operator for the attempt.
- **(s)** The owner may stop the attempt manually, as operator.
- **(t)** D107's stop rule read as in N1.5: usage is a live stop, and acceptance-row failures are judged after the attempt.
- **(u)** Freshness margin: at least 90 s left at the pre-reservation check.
- **(v)** After three failed captures: a new word for the same registration within its validity window, with no attempt consumed. This extends D115, and the newer word supersedes the earlier one.
- **(w)** The owner statement is how the word states D110's and D111's terms, bound through the review bundle.
- **(x)** Every capture's limits are cross-checked, not only the first (stricter than D117).

## N1.9 Code that must exist and be accepted before registration
These are engineering prerequisites, not choices. They are **to be built** as native unit U4b on the U5 preparation line; at the time of writing, none is delivered. The registration cites each one's merged commit.

**The U4b work files** are in `notes/coordination/`. They're not in the repository's tracked tree, so they're cited by sha256:
- the brief `2026-11-08-codex-native-u4b.md`: `af5cb901c0a77f75926d0c6f0e14c6d198ce3415a5cbe87fbce57f567818037e`;
- addendum 1: `ba25e02d942c72baab1c25dc658fc6e4ed431439532083f89f69bc0a2195e90c`;
- addendum 2: `9c8783fa8c108ed190bd498ce5808afa2601efb5ba601dfc4d7176b556f07aee`;
- addendum 3: `4472fde84eb588fde15217294b21c8c48ee2f3f3b40cd88129d83b1157aa0240` (including its item 8, from the v5 review).

Addenda 2 and 3 and D115–D117 supersede the brief's items 3, 5 and 6 and addendum 1's single capture. Where they differ, this list governs.
1. **D114:** `toolchain()` narrowed to the generation agents for the native shared route; the specificity scanner run over the exposed set.
2. **Subscription guard v2** (v1 kept byte-identical):
   - admission requires the seven-day (≤ 0.50) and five-hour (≤ 0.25) windows and applies N1.5's window rule and domain;
   - the 90 s margin at the pre-reservation check;
   - the capture-limits cross-check on every capture (D117), whose mismatch refuses the registration before any reservation;
   - refusal of a capture made under a word other than the one the guard binds;
   - the chronology check against a parsed `authorized_at`;
   - `observe` stops on any nested window that is no longer allowed;
   - the snapshot keeps the admission and after-run readings, with saved-readback validation; stopped-attempt readings are labelled unverified.
3. **The registered capture command** (D115):
   - a capture-only config directory outside every attempt path;
   - a capture reservation with a maximum of three per word, refusing a fourth;
   - each capture saves its `rate_limit_event`, its terminal `modelUsage` and the sha256 of its word;
   - a newer word supersedes an earlier one for the same `attempt_id`;
   - every capture recorded;
   - captures never consume the attempt's reservation.
4. **The review bundle and owner statement.** `review_sha256` names a bundle of the two independent reviews and the owner statement.
   - The v2 review reader is replaced or extended to accept it. It checks each review's independence from both author and operator, with replay and readback validation.
   - `authorized_at` is a strict ISO-8601 UTC timestamp.
   - An equality check refuses the attempt if any launch value differs from the statement:
     - the guard's seven-day maximum, five-hour maximum, `max_age_seconds` or 90 s margin;
     - the runtime's budget, deadline, keep-awake or context mode.
5. **The runtime declaration under D112, D116 and D117:**
   - the two-probe sequence: the observation probe's `limits`, then the bound permission probe under the final runtime, whose `limits_basis` names the observation probe by sha256.
     - A `limits_basis` naming the bound probe itself refuses.
     - So does a provisional runtime that differs from the final one in any field other than `limits`, `limits_basis` and the thinking field;
   - the declared 1M alias pair, gated exactly in the runtime gates **and in the saved-probe verifier** (`native_shared_permissions.py`), with the scripted provider returning `claude-opus-5` in messages;
   - tested on a saved 1M transcript.
6. **The thinking setting:** a required field of the runtime declaration, taken from the observation probe's captured request body. A missing value refuses.
7. **D11's pinned executable:** the durable copy, if N1.8(b) is ratified.
8. **`receipt_chunks_unopened`** wired with its receipt and manifest inputs, reported only.
9. **An explicit `audit_counts` equality row** inside the `evidence` gate: report totals against the derived audit, with the compared artifacts recorded. Missing or mismatched data refuses.
