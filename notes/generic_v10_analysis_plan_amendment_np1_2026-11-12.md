# generic_v10 analysis plan, amendment NP1: native production cells

**Status: draft v1, written by claude (lead) on 2026-11-12.**
- **It is not binding until:**
  - a Claude reviewer and a Codex CLI pass review it, with each finding filed;
  - amendment N1 has been ratified, because NP1 builds on N1's ratified text and names that file's sha256 at its own ratification;
  - the owner ratifies it by naming this file's sha256 at a commit and answering each lettered item of NP1.10;
  - and it merges only after that word, and before any native pilot or production registration.
- **Values marked [proposed]** are the lead's choices. They take effect only through NP1.10. Unmarked rules are the owner's decisions, the plan's own text or amendment N1's text, each cited.
- **It is prospective.** No native record exists under this condition: the native canary has not run and amendment N1 is not ratified. Every rule here is fixed before any native outcome it governs, as the plan requires of its own stages ("No rule is chosen after an outcome it governs", staged sequence step 2, lines 271–272).
- **What the lead had in view when writing it:**
  - the plan's "Known v10 values on the predicted metrics" (lines 178–252), which are the two assisted API canaries';
  - the API run A21 of 2026-11-11, which ended at its first typed-audit call and left a phase-1 full record and core record. The lead read their validation result (0 errors; two warnings: no `title`, and an empty `Distribution`) and their file sizes, and no metric of this amendment;
  - no value from any native run under this condition.
- **Line numbers** are those of `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`, where the file's sha256 is the ratified `b4a4f9a596173d3bdeb817b01ea53fb1a1d77574e121c7cecaf6f63b67fd4b4b`.
- **Section numbers of amendment N1** are those of its draft v7 (commit `2fb0503757db041e009f21dd02a1d57a45a75a88`, file sha256 `8a644c0efb968da23f45c533e757fcd06af495c3d15c73c442c9d4a8c5566a60`), which is unratified and under revision after its re-review. Where N1's ratified text differs, N1's ratified text governs.
- **Source references** are to commit `1a137b58860416a31618de44173180d021dfcc61` of the native branches, read with `git show`. That source is unmerged.

## Authority
- **The plan being amended:** `notes/generic_v10_analysis_plan.md`, ratified at commit `5b17ae079c8eb1fa4abdda3261054bfd22e4c2f1` with the sha256 above (D65). That file is not edited; this amendment stands beside it, as P4a amendment 1 (sha256 `7b1a3e79ee12c33193b0e8c58de8bbfae02a57944aee19830f9a923ec55eccb7`, ratified by D71) and amendment N1 do.
- **What the plan says today about native production.** §1 item 5 (lines 465–470): the first native CHORUS canary is "**n=1 descriptive feasibility only**", and "Native production cells are unregistered. No six-project native/API effect is estimable from one canary." The matrix (lines 574–581) gives the native arm one cell, the CHORUS canary, and marks AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC and KIDS_FIRST "Unplanned/unregistered" on it.
- **The owner's decisions.** These are excerpts from the coordination record, which is not in the repository. Text in quotation marks is exact; everything else is a summary.
  - **D134 (2026-11-12):** "we dont even need the API route except for comparison, the native agentic is the main result".
  - **D135 (2026-11-12).** The lead asked: "Native production scope: mirror the API arm's planned matrix? That is three replicates each for CHORUS, CM4AI, VOICE and AI_READI, plus one each for VOICE_PEDIATRIC and Kids First if in scope. I recommend yes." The owner answered "1 yes 2 yes 3 yes"; this was the first of the three questions. It authorizes this draft. It is not a ratification, a registration or a generation word.
  - **D109:** the native receipt floor for the CHORUS n=1 canary stays `{state: pending, mode: diagnostic_pilot}`. "The measured value informs a registered native floor before any native replicate. No API threshold is copied (D25: the canary is not a replicate)."
  - **D113 (A13 and D07 for the native cell):** "A rule-level rejection of the native canary ends the **native shared-v1 cell only,** not the API arm's generic_v10." "At most **two** native canary attempts (D07), each with its own label, registration and word." "Transport or budget stops are distinct from a scientific rejection."
  - **D91:** "The first native canary uses N2's declared shared-v1 differences, not BC1 parity." BC1 parity is a follow-up.
  - **D105:** "Receipts v5 is not activated for final generation." v4 stays the registered instrument.
  - **D107:** the native amendment's defaults, among them: the owner is operator, a Claude-plus-codex pair reviews (D12); no native canary counts as a replicate (D25); the first canary is CHORUS with one replicate.
  - **D36:** "Models review; you sign; seed (Recommended)". A fresh Claude session does the blind source review, with a Codex CLI pass; neither generated nor operated the run. The owner signs each acceptance record.
  - **D22:** "Withdraw them all": no standing authorizations. Every generic_v10 generation and evaluation needs its own owner word.
  - **D07,** as the plan's decision table records it: "At most 2 billed attempts per registered cell, then an owner review."
  - **D56,** as the plan's decision table records it: an override never continues a run past a terminal or control-state discrepancy; a retry needs a new registration.
  - **D64:** the owner's answers to the 37 P4a questions. Those used here: the scope rule (item 2), the AI_READI comparator (item 14), the analysis sets (items 15–16, 24), K (item 17), the tolerances (items 18–23), the floor rule (item 28), the cell roles (item 29), the stop classification (items 31–34), and gating with continuation (item 35).
  - **Also applied:** D25 and D27 (the arm, its directories, and no canary as a replicate); D118, D110 and D111 (admission, the dollar guard and overage, through N1.5); D126 (declared paths, through N1.6); D35 (the freeze).
- **Open in the plan and touched here:** P4 agenda items 38 (Kids First's route, order and floor) and 39 (VOICE_PEDIATRIC ×1 or ×3), both "latest P4b" (lines 2377–2391). They are questions about the API matrix. D135 answers their count for the native arm; NP1.2 proposes the rest for the native arm; NP1.8 says what becomes of them on the API arm.

## NP1.1 What this amendment does
- **It plans the native arm's production cells,** which the plan leaves unplanned, and says how they are analysed, accepted and sequenced.
- **It does not register or authorize any run.** Each native pilot and production attempt still needs its own registration, two independent reviews and the owner's word (D22, D56; N1.5).
- **For readers of the amendment, this table supersedes the native column of the plan's matrix** (lines 574–581). The plan's own rows stay as ratified.

| Project | Native agentic (direct arm), under NP1 |
|---|---|
| CHORUS | The N1 canary: n=1, descriptive, never a replicate. Then 3 production cells |
| CM4AI | 3 production cells |
| VOICE | 3 production cells, adult scope; pediatric records never substitute |
| AI_READI | [proposed] 1 pilot, not a replicate; then 3 production cells |
| VOICE_PEDIATRIC | 1 cell, descriptive, if in scope |
| KIDS_FIRST | 1 cell, descriptive, if in scope |

## NP1.2 Cells, scope and order
- **The cells (D135):** three replicates each for CHORUS, CM4AI, VOICE and AI_READI, and one each for VOICE_PEDIATRIC and Kids First if in scope. Records go under `claudecode_direct{,_core}/<label>/` (D27; N1.1).
- **A cell** is (arm, project, replicate position), as plan §3 defines it (lines 715–718). Each registration declares the position it fills.
- **The N1 canary is never one of these cells** (D25, D107; N1.5).
- **Scope rule** [proposed]: the plan's rule (lines 333–355), read for the native arm.
  - **Whole projects only.** A project is in or out with all its cells. Replicates are never trimmed inside a project.
  - **The evidence is usage, fit and stop outcomes:** the accepted canary's measured-usage packet (NP1.7) and each project's fit against the registered runtime limits at its registration. It is never a quality metric of the canary, or of any v10 record, against v8 (lines 337–339).
  - **The order** is the plan's (lines 340–344): CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI (pilot + ×3) → VOICE_PEDIATRIC ×1 → Kids First ×1. Under NP1.7 the AI_READI pilot, if there is one, runs before the floor is registered and so before any production cell, as the plan's own pilot does (lines 307–312).
  - **D135 puts the four three-replicate projects in scope.** One of them leaves scope only as infeasible: its inputs are refused by the registered limits at its registration, or the owner descopes it at NP1b on the usage packet.
  - **A descoped project is "out of scope (NP1b)", not missing.** It is not counted in K_native (NP1.3), and plan §7's missing-cell rules apply only to in-scope cells (lines 347–349).
  - **With CHORUS alone in scope,** every native verdict is a single-project result, written "holds for CHORUS" (lines 352–353).
- **VOICE_PEDIATRIC and Kids First** [proposed]: each is in scope unless NP1b descopes it on usage or fit.
  - **VOICE_PEDIATRIC:** one cell under its own label. It is reported in VOICE's section of every table as its own row, never as a VOICE replicate and never in a VOICE verdict (lines 640–646).
  - **Kids First:** one cell, last in the order, with the neutral profile and `vocabulary: {}`, under its own curator-written omission context, with its frozen chunk manifest re-validated first (lines 647–656), and under the registered native floor.
  - The plan's items 38 and 39 stay open for the API arm; NP1.8 proposes that both projects are out of the API arm's scope.
- **An AI_READI pilot** [proposed]: one native AI_READI attempt in the role of the plan's A14 (line 555): not a replicate, run with the coverage floor pending as the canary is (D109), and accepted before the floor's value is computed.
  - **Why:** AI_READI is the largest of the four three-replicate bundles, and under the plan's floor rule it is the only pilot that can lower the floor (lines 1143–1149). Without it, AI_READI's replicates meet a floor set from CHORUS alone.
  - **What it costs:** one more native run before any production cell.
  - **If the answer is no:** the floor comes from the canary alone, and AI_READI's first run is its first replicate.

## NP1.3 Roles, comparator and what can be claimed
- **The comparator is the plan's** (lines 474–488): the v8 API package. For CHORUS, CM4AI and VOICE it is the nine v8 API records the plan lists; for AI_READI it follows D64, item 14 (below).
- **What a native-against-v8 comparison is.** The plan's package effect (estimand 2, lines 453–460) compares generic_v10 API cells with v8 API records. Both sides ran through the provider route without tools. A native production cell differs from a v8 record in two sets of things at once:
  - **everything plan §4 lists** between v8 and v10 (lines 908–973): the prompt, the harness, coverage timing, the schema, the caps, the thinking display, gating and selection, and the check instruments;
  - **everything N1.6 declares between the arms:** effort (explicit high, against the provider default); runtime and transport (a subscription CLI, not a provider route), and with them the account; tools (Read, Write and Bash plus the permitted lookups, against none); staged exposure (the typed-helper phases); context (1M); the schema release (3.2.1 under N1.8(h), against v8's 2.0.0); no write-time normaliser; absolute local paths in the instruction (D126); and the D91 shared-v1 protocol differences in place of BC1.
- **So a difference between native v10 cells and v8 records is a package-and-runtime difference.** Nothing in it attributes an effect to the prompt package, to the runtime or to any one component. The plan counts in K the projects "whose contrast is like-for-like" (lines 836–837); this contrast is like-for-like in the source bundle only, and each registration verifies that identity (lines 936–938).
- **Role** [proposed]: native production cells are the study's primary generic_v10 cells (D134).
  - Each rule the plan fixed for a v10-against-v8 comparison is applied to them unchanged: metric, instrument, analysis set, tolerance and missingness rule.
  - Every result is reported under the label **"native v10 against v8 API: package and runtime"**. A prediction's overall statement reads "holds in k of K_native projects (package and runtime)".
  - **K_native** counts the in-scope native projects among CHORUS, CM4AI and VOICE, and AI_READI only under option (d) of D64, item 14.
  - A native result is never pooled with an API v10 cell and never reported as the plan's package effect.
  - **If the answer is no:** native production is descriptive only: per project, native values beside v8's with mean, SD and range, and no verdict (the default the plan describes at lines 822–824).
- **What carries over, what is restated and what cannot be claimed:**

| Plan item | For native production cells |
|---|---|
| Estimand 1, feasibility and acceptance (lines 438–452) | Unchanged. Reported for the native arm on its own. The two success proportions use native attempts (NP1.6). A refusal before the reservation is a preflight refusal and is in neither denominator |
| Estimand 2, package effect (lines 453–460) | **Cannot be claimed.** Restated as the package-and-runtime contrast above [proposed] |
| Estimand 3, replicate structure (lines 461–462) | Unchanged in rule: three native replicates against v8's three, n=3 primary. It is descriptive (prediction 8) |
| Estimand 4, external feasibility (lines 463–464) | Unchanged, for VOICE_PEDIATRIC and Kids First |
| Estimand 5, cross-arm contrast (lines 465–470) | Restated: estimable only for a project that has both native production cells and API comparison cells (NP1.8), and descriptive there |
| Prediction 1, populated leaves | Rule unchanged, under the label above |
| Prediction 2, pre-completion coverage | Rule unchanged. It needs the native pre-completion reading (NP1.4); a run without one is metric-missing |
| Predictions 3 and 3a, recall targets | Rules unchanged. The adapter that applies the counters is pinned by sha256 in NP1b, before any production record exists, as the plan requires of P4b |
| Prediction 4, review-pass rates (E2) | **Not measured under NP1** [proposed]: deferred (NP1.9) |
| Prediction 5, rubric20 Q11 and Q19 (E5) | **Cannot be claimed.** The plan's rule excludes native records from these means (line 1876: "No pilot, re-canary, with-crate, native or calibration record enters these means"), and N1.6 defers native ratings. Not measured under NP1 [proposed] |
| Row 6, the validation and duplicate-key invariant | Unchanged, read on native acceptance |
| Rows 7 and 8, report findings and structure | Unchanged: descriptive, no direction |

- **The AI_READI comparator** [proposed]: D64, item 14 stands unchanged for native cells (lines 495–523).
  - Under option (d), the comparator is the new no-crate v8 API run, used only if its render diff passes. Otherwise AI_READI is descriptive, option (b), and outside K_native.
  - That run is API work with its own registration, allocation and owner word. **It is not a prerequisite for native AI_READI cells.** If it does not exist when the analysis is made, AI_READI is descriptive.
  - The plan's option (c), the 2026-10-14b no-crate agentic rerun (line 522), is not adopted here. It shares the Claude Code runtime with the native arm, but it ran a different harness and its records are not on main. The owner may choose it instead by answering no to NP1.10(e) and naming it.

## NP1.4 Analysis sets for native records
- **Set A** keeps the plan's two definitions, with definition (2) primary and (1) reported beside it (lines 681–712).
- **An eligible native full record** [proposed]. The plan fixes eligibility by a completion event of the API runner, `reconcile_full` in the run's snapshot index (lines 721–757). The native arm writes no such index. The plan already lets a run's own completion evidence be the one "that run's runner writes, which its registration review identifies" (lines 766–768). For the native arm:
  - an attempt's full record is eligible when its saved result shows that the native protocol's final reconciliation and its final core derivation completed, and an independent `read_final` reconstructs that full record by sha256;
  - it is eligible whether or not the attempt is later accepted, as in the plan;
  - an attempt without that evidence has no eligible full record and is artifact-missing for Set A;
  - **the exact saved field and event are named in NP1b,** from the merged source, before any production record exists.
  - **What the lead read and did not read.** The native recipe is named `source_receipt_derive_audit_reconcile_attribution_record_v1` (`native_attempt_supervisor.py:29`). The phase rules name a final reconciliation in which the core is derived by `derive_final_core`, and the final core checks require that derivation (`native_shared_phase.py:198–206`). The lead did not verify the saved field names.
- **The native pre-completion reading** [proposed, with the item above]: prediction 2 reads the plan's `O,R0` pair (§3a, lines 871–889). On the native arm that is the receipt-completion stage's `before` block, which the completion result saves beside its `after` block (`native_shared_receipts.py`). A run that saves no `before` reading is metric-missing for prediction 2; the `after` value never replaces it.
- **Set B** is unchanged (lines 783–807): validation passed under the native arm's registered schema closure; duplicate keys 0; the five receipt floors at 0; one common checker, the v4 receipts checker at a pinned source hash, run on copies of both sides' records. The coverage floor is applied to neither side. The checker's source hash, the schema closures and the snapshot identities are bound in NP1b, where the plan binds them in P4b.
- **Missing data, n=3 and n=1** are unchanged (lines 844–855): a primary verdict for a project needs complete n=3 on each side under definition (2); the three kinds of missing are kept apart; n=1 cells (the canary, the pilot, VOICE_PEDIATRIC and Kids First) are descriptive only.

## NP1.5 The native receipt floor for replicates
- **What D109 requires:** the canary's floor stays pending and its reading is reported; "The measured value informs a registered native floor before any native replicate. No API threshold is copied".
- **What a registered native floor is in the code.** The native receipt policy is a selected asset pinned by sha256. Its `coverage_floor` is either `{state: pending, mode: diagnostic_pilot}` or `{state: registered, numerator, denominator}` (`native_shared_contract.py`, `parse_receipt_policy`). A registered floor passes when `with_receipt × denominator ≥ receiptable × numerator` (`native_shared_receipts.py:296–307`). Registering a value therefore makes a new receipt policy asset with a new sha256, which each production registration selects.
- **The rule** [proposed]. It takes the form of the plan's floor rule (§8, lines 1125–1127) and no value from the API arm:

> The registered native coverage floor is the lowest of the eligible native pilots' coverage fractions, `with_receipt / receiptable`, rounded down to a multiple of 1/20 and capped at 19/20.

  - **Eligible pilots:** the N1 canary and, if NP1.10(c) is yes and AI_READI is in scope, the AI_READI native pilot. Only an accepted attempt's saved result supplies a fraction; a rejected, stopped or assisted attempt never does (lines 1129–1133).
  - **Which reading.** Each pilot contributes the lowest of the readings at which the native controller evaluates the floor for that attempt. In the source the lead read, the floor is evaluated at the receipt-completion stage and again at the final stage (`native_shared_receipts.py:463` and `:498`). Taking the lowest means a registered floor never asks more of a production record at a stage than the pilots met at that stage. Which readings gate under a registered floor is confirmed from the merged source in the floor's registration; the lead did not verify it.
  - **Arithmetic:** exact integers, `floor(20 × with_receipt / receiptable) / 20`, then the minimum with 19/20, registered as a numerator over the denominator 20.
  - **Why the cap:** the plan's reason (lines 1134–1140). Receipt completion drives the ratio towards 1, and a floor of 1 would stop a replicate on one unreceipted leaf.
  - **The AI_READI branch:** if the AI_READI pilot ends without acceptance for a cause that is not rule-level, AI_READI leaves scope as infeasible, reported as a feasibility result, and the canary alone sets the value (plan step 8, lines 307–312).
  - **No value:** if a pilot the branch still requires has no accepted attempt, or a zero denominator, the rule yields no value. No production cell registers until a prospective amendment, reviewed as this one, supplies one. No other observed ratio is substituted (lines 1150–1152).
- **How the value is registered** [proposed, NP1.7]: in a dated amendment that gets this amendment's review and the owner's ratification. It checks the arithmetic and the inputs and does not revisit the rule (lines 1159–1163).

## NP1.6 Acceptance, attempts and stops
- **Each attempt is judged by N1.4(B)'s rows B0–B7,** as ratified, on the saved result after the attempt ends.
- **For production cells, row B5 gates** [proposed]: the native policy floor must read `state: passed` under the registered floor. Pilots keep B5 reported and labelled UNMEASURABLE (D109). "Accepted" for a production cell then means B0–B7 all hold.
- **Blind source review (B6) is per record** (D36): a fresh Claude session and a Codex CLI pass, neither of which generated or operated the run, with the second blind reviewer's recall seed pinned to `original_full` before anyone reads the audit.
- **The owner signs each acceptance record** (D36). Its format is plan §6's (lines 1026–1048), with the native identities N1.6 lists in place of the API-only fields.
- **Attempts** [proposed]:
  - **At most two attempts per native production cell,** counted across every label and registration, then the owner reviews. This is the plan's bound (§7, lines 1066–1069; D07), which D113 already applies to the canary.
  - **An attempt** is one launch that consumed its reservation. A capture is not an attempt, and a refusal before the reservation consumes none. A capture that is fresh at the reservation but stale at dispatch stops the attempt, and it counts (N1.5).
  - **Every attempt is retained,** stopped and rejected ones included (lines 1052–1056). A stopped or rejected attempt is never resumed or re-run under its label; any new attempt needs a new label, registration and word (N1.5; D56).
- **Classification** [proposed]: every stop or rejection gets the plan's two records, its evidence status and exactly one primary cause class by the precedence of the plan's table (lines 1337–1377), with these native readings.

| Class | Native reading |
|---|---|
| instrument | As the plan writes it |
| rule-level | A B6 rejecting-class finding is sustained on anything the run wrote, or the final records fail validation or carry duplicate keys. In production it counts toward the stop-loss, and the cell may use its second attempt only while the stop-loss is not reached |
| content slip | A structural receipt floor, the registered coverage floor or the report-totals equality row fails, and rule-level does not match. One contingency within the cell's two attempts; counts toward the stop-loss by root cause |
| registration or environment | A fault of the registration or the launch environment and not of generated content: the host, the keep-awake, the account, a usage stop, or an admission failure at dispatch. One contingency under a corrected registration |
| impossible limit | As the plan writes it |
| record shape | A native helper refuses the phase-1 record for a value of the wrong cardinality or type. The native arm has no write-time normaliser (N1.1). One contingency |
| transport | The runtime's terminal result or a supervisor boundary records a transport fault. One contingency |
| budget or clock | The dollar guard, the deadline or the owner's manual stop ended the attempt. One contingency, with a new word |
| unknown | Held for the owner's adjudication before any retry |

  - The plan's rules beside its table stand (lines 1360–1377): a content defect outranks every operational class; unmeasurable is not failed; an assisted attempt is evidence only.
- **Stop-loss** [proposed]: the plan's production rule (lines 1322–1329) for the native condition. Two rejections with the same root cause end re-running in the native shared-v1 condition. The count covers every native production cell, label and registration, and it never resets. Rule-level causes and content slips count; other stops are counted and reported separately.
- **Pilots:** the canary is governed by D113. [proposed] D113's rule applies to the AI_READI native pilot in the same way: a rule-level rejection ends the native shared-v1 cell, and the pilot has at most two attempts.
- **Missing cells** follow plan §7 unchanged (lines 1094–1108).

## NP1.7 Order of events and pacing
1. **The canary is accepted under N1.** Amendment N1 is ratified, the native code is accepted and merged (N1.9), and the CHORUS canary is registered, run and accepted on N1.4(B)'s rows. **Nothing in NP1 starts before the canary's acceptance record is signed.** If the canary is rejected at rule level, D113 ends the native shared-v1 cell, and this amendment has nothing to apply to in this condition.
2. **The native measured-usage packet** [proposed], in the role of the plan's measured-cost packet (lines 290–299). From the accepted canary's saved result it reports:
   - the admission readings of each usage window, and the first, last and highest reading of each window during the run (N1.6);
   - the wall clock from dispatch to the end, against the deadline;
   - the runtime's own cost estimate, against the dollar guard;
   - context use against the registered limits;
   - each stage's outcome;
   - the capture-to-reservation and capture-to-dispatch ages (N1.5).

   It carries no quality comparison against v8.
3. **NP1b** [proposed]: a dated amendment, reviewed as this one is and ratified by the owner by sha256 before any native pilot or production registration. "It applies rules; it does not invent them" (the plan on P4b, lines 304–305). It:
   - applies NP1.2's scope rule to the usage packet and to each project's fit;
   - names the eligibility event and the pre-completion reading (NP1.4);
   - pins the comparator manifest's record hashes, the recall adapter, the common checker's source hash and the schema closures;
   - states, from the usage packet, how many attempts the usage windows allow in a week;
   - registers the floor's value under NP1.5 when no pilot is pending.

   It may change which whole projects are in scope. It may not change a metric, an instrument, a decision rule, a tolerance, an analysis-set definition, an eligibility rule or a missingness rule, and it may not use any v10 quality value (lines 316–325).
4. **The AI_READI pilot,** if NP1.10(c) is yes and AI_READI is in scope: registered, run and accepted before the floor's value is computed.
5. **The floor's registration** (NP1.5), in NP1b or, when a pilot was pending, in its own dated amendment reviewed and ratified the same way. **No production cell registers before it.**
6. **Production cells, in NP1.2's order, one attempt at a time.** For each attempt:
   - a registration on merged main that pins the source commit, the full and core schema closures, the bundle, the chunk manifest and the source manifest (plan §11, lines 1404–1405), the runtime and its probes (N1.2, N1.9), and the receipt policy that carries the registered floor;
   - two independent reviews of the registration and its packet (N1.3);
   - the owner's statement of launch terms and the coded word, which binds one attempt by construction (N1.5);
   - capture, guard and launch as N1.5 orders them;
   - acceptance under NP1.6.
- **Words and registrations.** Each attempt has its own registration and its own word (D22; N1.5). Each retry is a new registration (D56).
- **Reviews** [proposed]: both reviewers review every registration. The registrations of one project's three replicate cells differ only in replicate position, label, attempt identity and the paths derived from them; each reviewer may cover the three in one review document that names each registration's sha256 and states the differences it checked.
- **Pacing** [proposed]: N1.5's terms apply unchanged to every pilot and production attempt: the admission bounds, the deadline, the dollar guard, overage disabled, the keep-awake policy and the capture rules. One native attempt runs at a time on the account. No term is relaxed to shorten the batch; a change to any of them is a revision of N1, made before the cells it governs, and those cells form a new stratum (lines 321–325).
  - **The count:** up to 16 first attempts with the canary (1 canary, 1 pilot, 12 replicates and 2 descriptive cells), and at most one further attempt per cell.
  - **How many fit in a week is not known.** It follows from the usage packet and is stated in NP1b.
- **One procedure** [proposed]: every native pilot and production cell runs the same merged source and the same selected assets, apart from the receipt policy's registered floor and each project's inputs. A later change to the native runner or to a model-facing asset makes the cells run after it a new stratum, unless byte parity of the complete effective instruction and of each stage request is shown on an already-run project and the owner separately authorizes a diagnostic canary. That is D35's rule (plan §11, lines 1399–1405) read for the native arm.

## NP1.8 The API arm under D134
- **What D134 says:** the API route is needed only for comparison. The plan's API matrix (lines 552–560) stays in the plan's text, and its scope is P4b's to fix (lines 300–306).
- **The comparison set** [proposed]: CHORUS only.
  - **The cells:** the clean CHORUS re-canary in plan A10's role (n=1, descriptive for good) and the three CHORUS replicate-gate cells (A16).
  - **Everything else on the API arm is "out of scope":** CM4AI, VOICE, AI_READI, VOICE_PEDIATRIC and Kids First. This is the scope the plan's own rule yields for a budget that covers CHORUS alone (lines 335–353), and P4b records it.
  - **Why this set and not less:** one API record supports no contrast beyond one record beside another. Three cells on one project allow the plan's n=3 structure rule and per-project means on a matched project. CHORUS is first in the plan's order and its cheapest run (lines 369–377).
  - **What it supports:** a descriptive native/API contrast for CHORUS: the two arms' values side by side on the plan's metrics, with N1.6's declared differences. No directional rule is added for it. Each arm's own comparison with v8 keeps its own label.
  - **What a matched contrast requires,** from the plan (lines 583–592): the same frozen source bundle, manifest, source policy, schema closures, profile, omission context and scientific assets wherever the contrast claims they match; hashes of the complete effective instructions and of each stage request; and every remaining difference declared, not normalised away.
  - **If the answer is no:** the owner names the set. With the re-canary alone, the contrast is one API record beside the native cells. With the plan's full matrix, P4b fixes its scope as the plan says.
- **None of this is a prerequisite for native production.** Native pilots and production cells proceed under NP1.7 whether or not any API cell has run.
- **The API arm's own open items,** recorded here and decided elsewhere:
  - the A21 run of 2026-11-11 ended at its first typed-audit call on a provider refusal (#5874). Its classification under plan §10 has not been recorded. By the lead's reading it used one of the re-canary cell's two attempts (plan §7);
  - a schema amendment. The API arm's ratified schema is 3.1.0 (D71(a), P4a amendment 1), and that registration was built on main at 3.2.1. A matched contrast needs the comparison registration on the native arm's release, by its own amendment (N1.1);
  - the provider account's budget has to cover the set, and it is read before any launch;
  - the rebuild comes after native integration, and D35's freeze starts at that rebuilt registration (N1.6).

## NP1.9 What is deferred, what this amendment does not change, and what it does
**Deferred** [proposed]: none of these is a prerequisite for a native pilot or production cell.
- **Native E2 and E5.** Prediction 4's review-pass instrument is P4b's open item 40, and N1.6 leaves native ratings to a separately ratified rating registration. Until a native evaluation registration is ratified, predictions 4 and 5 are "not measured" for the native arm.
- **BC1 parity for the native arm.** Production cells use the declared shared-v1 differences, as the canary does (D91). Adopting BC1 parity later is a change of procedure and a new stratum.
- **Receipts v5.** v4 stays the registered, gating instrument (D105; plan §3a). The two D105 secondary measures are recorded under their own identities, as N1.1 says.
- **Canonical marks for native cells** (plan item 42, lines 2417–2423). A mark never changes an estimate.
- **Any with-crate native arm.** It is not in this matrix.

**Unchanged:**
- the plan file and its sha256;
- P4a amendment 1, and amendment N1;
- D22, D25, D109's pending floor for the canary, and D113;
- any API-arm registration, and the rules the plan fixes for any API cell that runs;
- any historical decision or record.

**Changed, for readers of the amendment:**
- the native column of the plan's matrix (NP1.1);
- plan §1 item 5's statement that native production cells are unregistered: they are planned here, and each still needs its registration;
- the API arm's scope, as a proposal for P4b (NP1.8).

## NP1.10 Ratification: the owner names this file's sha256 at a commit, and answers each lettered item
Each letter is one decision, and a "yes" adopts exactly the value given. The cells themselves are D135's and are not a lettered item.
- **(a)** Scope and order for the native arm: whole projects only; the evidence is usage, fit and stop outcomes, never a quality value; the plan's order; a D135 project leaves scope only as infeasible or by the owner's descoping at NP1b (NP1.2).
- **(b)** VOICE_PEDIATRIC and Kids First are each in scope, one descriptive cell, unless NP1b descopes them on usage or fit; Kids First runs last, with the neutral profile and its own omission context, under the registered native floor (NP1.2).
- **(c)** One native AI_READI pilot, not a replicate, with the floor pending, accepted before the floor's value is computed; D113's rule applies to it (NP1.2, NP1.6).
- **(d)** Role: native production cells are the primary generic_v10 cells; the plan's rules apply to them unchanged; every result carries the label "native v10 against v8 API: package and runtime" and counts in K_native; it is never pooled with an API cell or reported as the plan's package effect (NP1.3).
- **(e)** The AI_READI comparator follows D64, item 14 unchanged; the no-crate v8 API run is not a prerequisite for native AI_READI cells, and without it AI_READI is descriptive (NP1.3).
- **(f)** An eligible native full record is one whose saved result shows the final reconciliation and final core derivation completed and which `read_final` reconstructs; prediction 2 reads the completion stage's `before` block; NP1b names the exact fields from the merged source (NP1.4).
- **(g)** Predictions 4 and 5 are not measured for the native arm under NP1; they wait for a separately ratified native evaluation registration (NP1.3, NP1.9).
- **(h)** The floor rule: the lowest of the eligible native pilots' coverage fractions, each pilot's lowest evaluated reading, rounded down to a multiple of 1/20 and capped at 19/20; no value means no production registration (NP1.5).
- **(i)** For production cells, N1.4(B)'s row B5 gates on the registered floor; pilots keep it reported (NP1.6).
- **(j)** Attempts, classes and stop-loss: at most two attempts per native production cell; the plan's cause classes with NP1.6's native readings; two rejections with the same root cause end re-running in the native shared-v1 condition (NP1.6).
- **(k)** The staged procedure: the measured-usage packet, then NP1b, then the floor's registration, each reviewed and ratified before the registrations that depend on it; NP1b applies rules and changes none (NP1.5, NP1.7).
- **(l)** Reviews: both reviewers review every registration; one review document per reviewer may cover one project's three replicate registrations (NP1.7).
- **(m)** Pacing: N1.5's terms unchanged for every pilot and production attempt, one native attempt at a time, and no term relaxed to shorten the batch (NP1.7).
- **(n)** One procedure: a later change to the native runner or a model-facing asset is a new stratum, unless byte parity is shown and the owner authorizes a diagnostic canary (NP1.7).
- **(o)** The API comparison set is CHORUS only: the clean re-canary and the three replicate-gate cells; every other API cell is out of scope; the contrast is descriptive; none of it is a prerequisite for native production (NP1.8).
- **(p)** Nothing on NP1.9's deferred list is a prerequisite for a native pilot or production cell.
