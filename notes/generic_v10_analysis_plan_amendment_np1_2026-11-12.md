# generic_v10 analysis plan, amendment NP1: native production cells

**Status: draft v3, written by claude (lead) on 2026-11-12.**
- **v1** (commit `b98b285d0fb75e5a86340980db377ac89aa93b9b`, file sha256 `79948599629f0ef5ee93ca5530b7bbbba03caa41448b22b054dd3d12c1759297`): reviewed by a Codex CLI pass (review sha256 `29efb19f481ab37064f4d8b4ddfe365f97c2c4f012d4a00bfdf8a0e1eddce296`), filed as #5914 to #5925.
- **v2** (commit `c515160aee3330429a46e4819b885e2d974adee5`, file sha256 `db5f23f759b95b0adc2a85e895b510b5398dc50891ab3c1b2cf06ba5537bc7ee`): reviewed twice, and both reviews said "ratifiable after listed fixes".
  - A Codex CLI pass (review sha256 `87b9568e16747d2f0ed0f12a6d24bbeb9e0993d016ff14feaf9dc9357727e513`): 2 P1, 4 P2, 1 P3.
  - A Claude reviewer, a fresh session run on another model (review sha256 `1dfc86776cc1a49e80a6e0a106649420e4f335b541fed269a437f0f274fdfcd9`): 2 P1, 8 P2, 12 P3.
  - The 29 findings are filed as 25 issues, #5940 to #5964; four overlap.
  - Two read-only source audits followed, both of commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e`: a Codex CLI audit of the receipt floor (sha256 `4a6a95f65ca3cf96c1cc56b6c624b693fc432559d7cf3711c3076c7370abb35b`) and a Codex helper's audit of native eligibility (sha256 `4b42694ab342dbdcf2d9f0db0faf3bffe5a015bf87968cb669aee19d25b0c3db`). The review and audit files are kept outside the repository and are cited by sha256.
- **v2 → v3** responds to every finding; the table below maps each one. Besides wording, it:
  - restates the eligible native full record in terms of what the source saves, and names what that misses (NP1.4);
  - puts the floor's basis to the owner as its own item, proposes D37's at-receipt basis, and names the code change that needs (NP1.5);
  - names a defect that stops every pilot (#5939) as a prerequisite of any pilot (NP1.5, NP1.7);
  - fixes K_native once, at the floor's registration, after the pilot branch (NP1.3);
  - says what a rule-level rejection of the AI_READI pilot ends (NP1.6);
  - sets each project's runtime terms by a rule, in place of applying the canary's terms to every project (NP1.7);
  - makes "no API prerequisite" depend on the owner's answer to amendment N1's item (y) (NP1.8);
  - says what holds if the canary's word is given before this amendment is ratified (NP1.5);
  - splits the lettered items that still held two decisions (NP1.10).
- **v3 has not been reviewed.**
- **It is not binding until:**
  - a Claude reviewer and a Codex CLI pass review it, with each finding filed;
  - amendment N1 has been ratified, because NP1 builds on N1's ratified text and names that file's sha256 at its own ratification. NP1 is reconciled against the answers the owner actually gave to N1's lettered items before its own ratification;
  - the owner ratifies it by naming this file's sha256 at a commit and answering each lettered item of NP1.10, **before the N1 canary's word is given** (NP1.5 says why, and what holds otherwise; amendment N1 proposes the same as its item (ah));
  - and it merges only after that word.
- **Values marked [proposed]** are the lead's choices. They take effect only through NP1.10. Unmarked rules are the owner's decisions, the plan's own text or amendment N1's text, each cited.
- **It is prospective.** No native record exists under this condition: the native canary has not run and amendment N1 is not ratified. Every rule here is fixed before any native outcome it governs, as the plan requires of its own stages ("No rule is chosen after an outcome it governs", staged sequence step 2, lines 271–272).
- **What the lead had in view when writing it:**
  - the plan's "Known v10 values on the predicted metrics" (lines 178–252), which are the two assisted API canaries'. They include those records' coverage on both bases the floor could use: 58/58 and 64/64 at receipt, and 58/63 and 64/75 on the final record (lines 200–201). NP1.5 says how those values bear on the choice of basis;
  - the API run A21 of 2026-11-11, which ended at its first typed-audit call and left a phase-1 full record and core record. The lead read their validation result (0 errors; two warnings: no `title`, and an empty `Distribution`) and their file sizes. Validation is row 6's invariant, so that is outcome information of a kind this amendment reports. The lead did not compute or inspect a populated-leaf count, a coverage fraction, a recall counter or a rating for those records;
  - results of offline tests of the native code on synthetic inputs. They produce no native record;
  - no value from any native run under this condition.
- **Line numbers** are those of `notes/generic_v10_analysis_plan.md` at main `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`, where the file's sha256 is the ratified `b4a4f9a596173d3bdeb817b01ea53fb1a1d77574e121c7cecaf6f63b67fd4b4b`.
- **Section numbers and letters of amendment N1** are those of its draft v12 (commit `c289eed19e37e227e04dd5e0c4fc077da54184aa`, file sha256 `de1f4a1386d2a5b05feba13f4bd6f7518c9768e73fb1f0e4d16c5a79a2f11c18`), which is unratified. Where N1's ratified text differs, N1's ratified text governs.
- **Source references** are to commit `5d63d0a77dc43c064cfc2b376355f98009dd5b6e` of the native integration branch, read with `git show`. That source is unmerged and unpublished. A reference followed by "(audit)" is a line the lead did not read; it is taken from one of the two audits above. Every other source reference was read by the lead at that commit.

## Responses to the reviews of v2
Each issue stays open until a re-check of v3 confirms the answer. "Claude" and "Codex" name the two v2 reviews.

| v2 finding | Issue | Answer in v3 | Where |
|---|---|---|---|
| Claude P1-1: the floor rule departs from D37's basis without saying so | #5940 | The basis is its own lettered item. D37's at-receipt basis is proposed; the departure the code makes today, its consequences and the values the lead knew are stated | NP1.5, (p) |
| Claude P1-2 and Codex 1: the eligibility witness is not what the source saves | #5941 | Restated as an end-state rule on what the source saves. What it cannot see is named. The cost of the plan's own rule is stated as the "no" branch | NP1.4, (l) |
| Claude P2-1 and Codex 2: K_native fixed at NP1b, yet projects leave scope later | #5942 | Fit is settled at NP1b. K_native is fixed once, at the floor's registration, after the pilot branch. A later failure is "not measured" | NP1.2, NP1.3, NP1.7, (j) |
| Claude P2-2: "cell" in two senses for a rule-level pilot rejection | #5943 | "Cell" keeps the plan's meaning; the whole native arm is "the native shared-v1 condition". The consequence is its own item | NP1.6, (g) |
| Claude P2-3 and Codex 4: "no API prerequisite" ignores N1 item (y) = no | #5944 | The statement is limited to the comparison set and made conditional on (y) | NP1.8, (ad) |
| Claude P2-4: D91 cited for production; BC1 parity foreclosed without a letter | #5945 | D91 is quoted in full. Its extension to production is marked as this amendment's proposal and has its own item | NP1.9, (aa) |
| Claude P2-5: the D135 quotation omits its premise | #5946 | Quoted whole, with what this amendment can and cannot support of the premise | Authority |
| Claude P2-6: no provision if the canary launches first | #5947 | A stated remedy, as its own item | NP1.5, (af) |
| Claude P2-7: the canary's terms applied to the largest projects | #5948 | Each project's deadline and dollar guard are set by a rule, at NP1b, from the usage packet | NP1.7, (x) |
| Claude P2-8: under a pending floor the final strict check appears to fail | #5949 | Confirmed from source by a second reading and filed as defect #5939. Its repair is a prerequisite of any pilot | NP1.5, NP1.7 |
| Claude P3-1: confound lists incomplete or misattributed | #5950 | The list is completed and the v8 schema comparison is attributed to this amendment | NP1.3 |
| Claude P3-2: the quoted plan sentence is about another run | #5951 | The item says it amends the eligibility rule for this arm | NP1.4 |
| Claude P3-3: item 38 is not only an API-matrix question | #5952 | The two items that together answer its route are named | Authority, NP1.8 |
| Claude P3-4: the floor has no lower bound | #5953 | Stated. A value of 0/20 yields no value | NP1.5, (q) |
| Claude P3-5: "production cell" undefined; N1.4(B)'s application unmarked | #5954 | Defined, with its own item. The applications are marked [proposed] | NP1.2, NP1.6, (d) |
| Claude P3-6: two classification readings | #5955 | Both rows reworded | NP1.6 |
| Claude P3-7: prediction 2's native reading includes pre-seal self-correction | #5956 | Said in the row and in the reading's definition | NP1.3, NP1.4 |
| Claude P3-8: the deadlines the owner faces are not named | #5957 | Both are named. The account figure the review quoted is not repeated here | NP1.3, NP1.9 |
| Claude P3-9: pacing disclosures | #5958 | Stated together | NP1.7 |
| Claude P3-10: one review document for three registrations | #5959 | The allowance is dropped | NP1.7, (w) |
| Claude P3-11: the stratum exception does not say who decides | #5960 | The reviewers and the owner are named | NP1.7, (z) |
| Claude P3-12 and Codex 6: lettered items still bundle | #5961 | v2's (b), (c) and (d) are split into (b)–(c), (e)–(g) and (h)–(i) | NP1.10 |
| Codex 3: registering the floor changes what the model is shown | #5962 | Stated, declared as the planned pilot-to-production difference, with what it means for comparison | NP1.5, NP1.7 |
| Codex 5: same-release schema matching presented as an existing requirement | #5963 | The schema difference may stay declared; neither release is required here | NP1.8, (ac) |
| Codex 7: NP1b's ban on "any v10 quality value" contradicts computing the floor | #5964 | The ban is on choosing by a quality value; applying NP1.5's fixed rule is permitted | NP1.7 |

The Claude review's closing note on the API arm (an unaccepted re-canary) is answered in NP1.8. It was not a numbered finding and has no issue.

## Authority
- **The plan being amended:** `notes/generic_v10_analysis_plan.md`, ratified at commit `5b17ae079c8eb1fa4abdda3261054bfd22e4c2f1` with the sha256 above (D65). That file is not edited; this amendment stands beside it, as P4a amendment 1 (sha256 `7b1a3e79ee12c33193b0e8c58de8bbfae02a57944aee19830f9a923ec55eccb7`, ratified by D71) and amendment N1 do.
- **What the plan says today about native production.** §1 item 5 (lines 465–470): the first native CHORUS canary is "**n=1 descriptive feasibility only**", and "Native production cells are unregistered. No six-project native/API effect is estimable from one canary." The matrix (lines 574–581) gives the native arm one cell, the CHORUS canary, and marks AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC and KIDS_FIRST "Unplanned/unregistered" on it.
- **The owner's decisions.** These are excerpts from the coordination record, which is not in the repository. Text in quotation marks is exact; everything else is a summary.
  - **D134 (2026-11-12):** "we dont even need the API route except for comparison, the native agentic is the main result".
  - **D135 (2026-11-12).** The lead asked: "Native production scope: mirror the API arm's planned matrix? That is three replicates each for CHORUS, CM4AI, VOICE and AI_READI, plus one each for VOICE_PEDIATRIC and Kids First if in scope. I recommend yes." with "If yes: the result is comparable with the v8 records the plan already uses, and I start drafting the amendment now." The owner answered "1 yes 2 yes 3 yes"; this was the first of the three questions. It authorizes this draft. It is not a ratification, a registration or a generation word.
    - **What this amendment can support of that premise is narrower than the question said.** The comparison with the v8 records is a package-and-runtime contrast, not the plan's package effect, and predictions 4 and 5 are not measured for this cohort (NP1.3). The owner answered before that analysis existed.
  - **D109:** "The native receipt floor for the CHORUS n=1 canary stays `{state: pending, mode: diagnostic_pilot}`." "The canary counts as "accepted" when every other acceptance row holds. Its policy-v1 floor reading is reported, not gated." "The measured value informs a registered native floor before any native replicate. No API threshold is copied (D25: the canary is not a replicate)."
  - **D37,** on the API arm's receipt floor: "The receipted-part floor gates `with_receipt / receiptable`, computed on the phase-1 snapshot: the record as it stood when the receipts were written." "A phase-1 value with no receipt that the audit later removed still counts against the floor." The plan says of it: "D37 fixes the snapshot basis" (line 1117).
  - **D113 (A13 and D07 for the native cell):** "A rule-level rejection of the native canary ends the **native shared-v1 cell only,** not the API arm's generic_v10." "At most **two** native canary attempts (D07), each with its own label, registration and word." "Transport or budget stops are distinct from a scientific rejection."
  - **D91:** "The first native canary uses N2's declared shared-v1 differences, not BC1 parity." "BC1 parity is a follow-up." The owner chose "Declared v1 differences (Recommended)". The decision is about the first canary. It does not say when the follow-up comes.
  - **D105:** "Receipts v5 is not activated for final generation." v4 stays the registered instrument.
  - **D107:** the native amendment's defaults, among them: the owner is operator, a Claude-plus-codex pair reviews (D12); no native canary counts as a replicate (D25); the first canary is CHORUS with one replicate.
  - **D36:** "Models review; you sign; seed (Recommended)". A fresh Claude session does the blind source review, with a Codex CLI pass; neither generated nor operated the run. The owner signs each acceptance record.
  - **D22:** "Withdraw them all": no standing authorizations. Every generic_v10 generation and evaluation needs its own owner word.
  - **D07,** as the plan's decision table records it: "At most 2 billed attempts per registered cell, then an owner review."
  - **D56,** as the plan's decision table records it: an override never continues a run past a terminal or control-state discrepancy; a retry needs a new registration.
  - **D64:** the owner's answers to the 37 P4a questions. Those used here: the scope rule (item 2), the AI_READI comparator (item 14), the analysis sets (items 15–16, 24), K (item 17), the tolerances (items 18–23), the floor rule (item 28), the cell roles (item 29), the stop classification (items 31–34), and gating with continuation (item 35).
  - **Also applied:** D25 and D27 (the arm, its directories, and no canary as a replicate); D118, D110, D111 and D136 (admission, the dollar guard, overage and the freshness age: each decided for the canary and applied here through N1.5 as NP1.7 says); D126 (declared paths, through N1.6); D35 (the freeze).
- **Open in the plan and touched here:** P4 agenda items 38 (Kids First's "route, order and floor") and 39 (VOICE_PEDIATRIC ×1 or ×3), both "latest P4b" (lines 2377–2391). The plan's own text on Kids First recommends "API first" (line 647). D135 answers both projects' count for the native arm. NP1.10(b) and (c) propose the rest for the native arm, and NP1.10(ab) proposes that both projects are out of the API arm's scope. Items (c) and (ab) together answer item 38's route for both arms: native, and not API.

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
| VOICE_PEDIATRIC | 1 production cell, descriptive, if in scope |
| KIDS_FIRST | 1 production cell, descriptive, if in scope |

## NP1.2 Cells, scope and order
- **The cells (D135):** three replicates each for CHORUS, CM4AI, VOICE and AI_READI, and one each for VOICE_PEDIATRIC and Kids First if in scope. Records go under `claudecode_direct{,_core}/<label>/` (D27; N1.1).
- **A cell** is (arm, project, replicate position), as plan §3 defines it (lines 715–718). Each registration declares the position it fills. This amendment uses "cell" only in that sense. The whole native arm under the shared-v1 protocol is called **the native shared-v1 condition**.
- **A production cell** [proposed] is any cell of this amendment that is not a pilot: the twelve replicate cells and the two descriptive cells. All fourteen run under the registered floor and under NP1.6's acceptance rows, attempt bound, classification and stop-loss. Only the twelve replicate cells can enter a verdict.
- **The N1 canary is never one of these cells** (D25, D107; N1.5).
- **Scope rule** [proposed]: the plan's rule (lines 333–355), read for the native arm.
  - **Whole projects only.** A project is in or out with all its cells. Replicates are never trimmed inside a project.
  - **The evidence is usage, fit and stop outcomes:** the accepted canary's measured-usage packet (NP1.7) and each project's fit (below). It is never a quality metric of the canary, or of any v10 record, against v8 (lines 337–339).
  - **The order** is the plan's (lines 340–344): CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI (pilot + ×3) → VOICE_PEDIATRIC ×1 → Kids First ×1. Under NP1.7 the AI_READI pilot, if there is one, runs before the floor is registered and so before any production cell, as the plan's own pilot does (lines 307–312).
  - **Fit is settled at NP1b.** NP1b checks every in-scope project offline: its frozen inputs against the registered limits, and its expected usage against the rule of NP1.7. No project leaves scope for fit after NP1b.
  - **D135 names the four three-replicate projects as the scope this amendment plans.** One of them leaves scope in only three ways: NP1b finds that it does not fit; the owner descopes it at NP1b on the usage packet; or, for AI_READI, its pilot concludes without acceptance (NP1.5).
  - **A descoped project is "out of scope", not missing,** with the event that removed it named: "(NP1b)" or "(pilot)". It is not counted in K_native (NP1.3), and plan §7's missing-cell rules apply only to in-scope cells (lines 347–349).
  - **After K_native is fixed (NP1.3), nothing removes a project from scope.** A registration that is refused, a cell that uses both attempts, or a cell that is never run leaves in-scope cells missing under plan §7, and the project reads "not measured".
  - **With CHORUS alone in scope,** every native verdict is a single-project result, written "holds for CHORUS" (lines 352–353).
- **VOICE_PEDIATRIC** [proposed]: in scope unless NP1b descopes it on usage or fit. One cell under its own label. It is reported in VOICE's section of every table as its own row, never as a VOICE replicate and never in a VOICE verdict (lines 640–646).
- **Kids First** [proposed]: in scope unless NP1b descopes it on usage or fit. One cell, last in the order, with the neutral profile and `vocabulary: {}`, under its own curator-written omission context, with its frozen chunk manifest re-validated first (lines 647–656). Those conditions are the plan's, not a choice made here.
- **An AI_READI pilot** [proposed]: one native AI_READI attempt in the role of the plan's A14 (line 555): not a replicate, run with the coverage floor pending as the canary is (D109), and accepted before the floor's value is computed.
  - **Why:** AI_READI is the largest of the four three-replicate bundles, and under the plan's floor rule it is the only pilot that can lower the floor (lines 1143–1149). Without it, AI_READI's replicates meet a floor set from CHORUS alone.
  - **What it costs:** one more native run before any production cell.
  - **If the answer is no:** the floor comes from the canary alone, and AI_READI's first run is its first replicate.

## NP1.3 Roles, comparator and what can be claimed
- **The comparator is the plan's** (lines 474–488): the v8 API package. For CHORUS, CM4AI and VOICE it is the nine v8 API records the plan lists; for AI_READI it follows D64, item 14 (below).
- **What a native-against-v8 comparison is.** The plan's package effect (estimand 2, lines 453–460) compares generic_v10 API cells with v8 API records. Both sides ran through the provider route without tools. A native production cell differs from a v8 record in two sets of things at once:
  - **what plan §4 lists** between v8 and v10 (lines 908–973), including: the prompt, the harness, coverage timing, the schema, the caps, the thinking display, gating and selection, and the check instruments; the recall rule and the newly exposed Software keys (lines 955–958), which prediction 3 is read with; provider-side model drift (lines 959–961); effort (lines 962–964); and repository state (lines 965–968);
  - **what N1.6 declares between the arms:** effort (explicit high, against the provider default); runtime and transport (a subscription CLI, not a provider route), and with them the account; tools (Read, Write and Bash plus the permitted lookups, against none); staged exposure (the typed-helper phases); context (1M); no write-time normaliser; absolute local paths in the instruction (D126); and the D91 shared-v1 protocol differences in place of BC1;
  - **the schema release.** The native arm runs 3.2.1 under N1.8(h). N1.6 declares that against the API arm's ratified 3.1.0. Against the v8 records the difference is 3.2.1 against 2.0.0 (the plan's own row is "2.0.0 against 3.0.0", line 922); that statement is this amendment's.
- **So a difference between native v10 cells and v8 records is a package-and-runtime difference.** Nothing in it attributes an effect to the prompt package, to the runtime or to any one component. The plan counts in K the projects "whose contrast is like-for-like" (lines 836–837); this contrast is like-for-like in the source bundle only, and each registration verifies that identity (lines 936–938).
- **Role** [proposed]: native production cells are the study's primary generic_v10 cells (D134). A native result is never pooled with an API v10 cell and never reported as the plan's package effect.
  - **If the answer is no,** the owner names the role, and this amendment is revised to it.
- **Comparison rules** [proposed]: each rule the plan fixed for a v10-against-v8 comparison is applied to the native replicate cells unchanged: metric, instrument, analysis set, tolerance, missingness rule and per-project verdict.
  - Every result is reported under the label **"native v10 against v8 API: package and runtime"**. A prediction's overall statement reads "holds in k of K_native projects (package and runtime)".
  - D134 makes the native arm the main result. It does not say that the plan's tolerances and verdict rules transfer to it; that is this item.
  - **If the answer is no:** native production is descriptive only: per project, native values beside v8's with mean, SD and range, and no verdict (the default the plan describes at lines 822–824). The role above can stand with either answer.
- **K_native** [proposed] counts the in-scope projects among CHORUS, CM4AI and VOICE, and AI_READI only when its comparator's record hashes were pinned at NP1b (below). The n=1 cells and a descriptive project are never in it.
  - **It is fixed once,** in the document that registers the floor's value (NP1.7 step 5): in NP1b when no pilot is pending, otherwise in the floor's own amendment, after the AI_READI pilot branch has concluded. That is after every event that can remove a project from scope and before any production cell registers.
  - **It never moves afterwards.** A project in K_native whose cells are later missing counts as "not measured" in "k of K_native", as the plan's missing-data rule has it (lines 844–853). It is not removed.
  - The comparator manifest pinned at NP1b is not edited afterwards. If AI_READI leaves scope at its pilot, its rows stay in the manifest and are unused.
- **What carries over, what is restated and what cannot be claimed:**

| Plan item | For native production cells |
|---|---|
| Estimand 1, feasibility and acceptance (lines 438–452) | Unchanged. Reported for the native arm on its own, per project. The two success proportions use native attempts (NP1.6). A refusal before the reservation is a preflight refusal and is in neither denominator |
| Estimand 2, package effect (lines 453–460) | **Cannot be claimed.** Restated as the package-and-runtime contrast above [proposed] |
| Estimand 3, replicate structure (lines 461–462) | Unchanged in rule: three native replicates against v8's three, n=3 primary. It is descriptive (prediction 8) |
| Estimand 4, external feasibility (lines 463–464) | Unchanged, for VOICE_PEDIATRIC and Kids First |
| Estimand 5, cross-arm contrast (lines 465–470) | Restated: estimable only for a project that has both native production cells and API comparison cells (NP1.8), and descriptive there |
| Prediction 1, populated leaves | Rule unchanged, under the label above. Read with NP1.5's note on a floor the model can see |
| Prediction 2, pre-completion coverage | Rule unchanged. It needs the native pre-completion reading (NP1.4); a run without one is metric-missing. On the native arm that reading is taken after the model may have corrected its receipt before the seal, and in production with the registered fraction in view (NP1.4) |
| Predictions 3 and 3a, recall targets | Rules unchanged. The adapter that applies the counters is pinned by sha256 in NP1b, before any production record exists, as the plan requires of P4b |
| Prediction 4, review-pass rates (E2) | **Not measured for this cohort** [proposed] (NP1.9) |
| Prediction 5, rubric20 Q11 and Q19 (E5) | **Cannot be claimed.** The plan's rule excludes native records from these means (line 1876: "No pilot, re-canary, with-crate, native or calibration record enters these means"), and N1.6 defers native ratings. Not measured for this cohort [proposed] (NP1.9) |
| Row 6, the validation and duplicate-key invariant | Unchanged, read on native acceptance |
| Rows 7 and 8, report findings and structure | Unchanged: descriptive, no direction |

- **The AI_READI comparator** [proposed]: D64, item 14 stands unchanged for native cells (lines 495–523).
  - Under option (d), the comparator is the new no-crate v8 API run, used only if its render diff passes. Otherwise AI_READI is descriptive, option (b), and outside K_native.
  - That run is API work with its own registration, allocation and owner word. It is not a cell of this amendment, and native AI_READI cells do not wait for it.
  - **The branch is fixed at NP1b,** before any native AI_READI registration. If the no-crate v8 API run exists by then and its render diff has passed, NP1b pins its record hashes in the comparator manifest and AI_READI can be in K_native. If it does not, AI_READI is descriptive for this analysis, whatever is produced later, and the comparator manifest has no AI_READI rows. Nothing about a native AI_READI outcome can move the branch.
  - **The deadline this sets for the owner.** NP1b follows the canary's acceptance. For AI_READI to count in K_native, the no-crate v8 API run has to be registered, authorized, run and diffed by then. It runs on the provider account, whose remaining budget is read before any launch and has to cover it. If the owner wants AI_READI in K_native, that run is started about when the canary is.
  - The plan's option (c), the 2026-10-14b no-crate agentic rerun (line 522), is not adopted here. It shares the Claude Code runtime with the native arm, but it ran a different harness and its records are not on main. The owner may choose it instead by answering no to NP1.10(k) and naming it.

## NP1.4 Analysis sets for native records
- **Set A** keeps the plan's two definitions, with definition (2) primary and (1) reported beside it (lines 681–712).
- **An eligible native full record** [proposed]. **This item amends the plan's eligibility rule for the native arm. It does not apply an existing allowance.**
  - **The plan's rule.** Eligibility is fixed by a completion event of the API runner, `reconcile_full` in the run's snapshot index, and the runner keeps a copy of the record at each such event (lines 721–757). The plan's sentence about "the completion evidence that run's runner writes" (lines 766–768) is about v10's API records and the new no-crate v8 run, not about this arm.
  - **Why v2's rule could not stand.** v2 bound the eligible record "by sha256" to a "settled" `derive_final_core` check in the phase history. Both reviews found, and the eligibility audit confirmed, that:
    - the phase history records, per helper call, a tool identity, the helper's name, its exit code and two event positions, and no file hash (`native_shared_phase.py:358–359`; its report says "actual hashes and all other gates are external", `:422–442`);
    - the helper prints an md5 of the full record, not a sha256, and validates the derived core only after writing it, so a nonzero exit does not say whether derivation completed (audit);
    - the native arm writes the full record in place and keeps no copy of it at that event (audit).
  - **The rule, on what the source saves.** A native attempt has an eligible full record when both of these hold:
    1. **the attempt's saved phase report lists `derive_final_core` among its `current_checks`.** That list holds a helper only if its last call succeeded and the tracker saw no later write, by a file tool or a derive helper, to the files it covers (`native_shared_phase.py:100–101`, `:229–240`, `:365–366`, `:439`; the helper covers the full record and the core, `:92`). The phase rules admit that helper only after the checked audit and the observed stage assembly (`:195–206`);
    2. **the attempt's end capture pinned the full record:** the saved result's captured-file identities carry its sha256 (`native_shared_results.py:58–60`).

    The eligible record is the full record with that sha256, read from the retained capture.
  - **Which phase report.** The replay report saved under the saved result's phase-history gate. Where the saved result has none, the live report saved under its live attribution (audit, for both locations). The analysis manifest says which was read.
  - **What is never the test:** the phase report's own `passed`, `runtime_gates_passed`, and the saved result's completion state. They would drop the rejected attempts the plan keeps. A later failed final check, report, recorder or runtime gate, a rejection and a stop all leave the record eligible while the two conditions hold.
  - **What this rule cannot see.** It reads the end of the attempt, not an event inside it. Compared with the plan's rule it loses:
    - **(i) a record whose derived core failed validation.** The helper then exits nonzero and is not a current check. The plan keeps a schema-invalid record in Set A (line 758). A full record that fails its own schema but derives a valid core is still kept here;
    - **(ii) a completed record that a later write disturbed.** Any attempted write to the full record or the core after the check removes it from `current_checks`, even a write that was interrupted, and the earlier bytes are not kept. The plan's "A repair interrupted before writing its snapshot leaves the previous one eligible" (lines 751–752) cannot be met;
    - **(iii) an attempt with no saved phase report or no end capture:** an uncatchable termination, a host loss, a publication failure, or an incomplete capture, which retains the streams and not the full record (audit). That is no evidence that reconciliation did not happen;
    - **(iv) a write the phase tracker did not observe,** for example one made by a shell command. The rule takes the tracker's word that nothing wrote the record after the check. Here the rule could keep bytes the check never covered. The guard against that is the registered command permissions, which allow the shell only for the typed helpers and read-only lookups (N1.4(B) row 3, N1.6); this rule adds none.
  - **What that does to the analysis.** In cases (i) to (iii) the attempt is artifact-missing for Set A where the plan's rule would have kept a record. In those cases the rule can lose a record; it never adds one. The losses fall on attempts that ended badly after reconciliation, so Set A can understate the failures Set B removes.
    - Every artifact-missing attempt is listed in the analysis manifest, with the case that applies as far as its retained evidence shows.
    - Where such an attempt's saved gates carry a validation result, it is still counted in row 6 and in the feasibility proportions.
    - A cell with no eligible record is missing under plan §7, and its project has no primary verdict.
  - **If the answer is no:** the plan's rule is built for the native arm before any pilot. The audit describes what that takes: an unchangeable copy of the full record at each completed reconciliation; a journal that binds each copy to the attempt and the event; and a reader that returns the last completed copy from a stopped or rejected attempt. That is new production code, with its own pins, tests and reviews, and the canary waits for it.
  - **Conformance, not choice.** NP1b names the exact saved fields from the merged source. If the merged source no longer saves them, this item is restated by a prospective amendment before any production registration.
- **The native pre-completion reading** [proposed]: prediction 2 reads the plan's `O,R0` pair (§3a, lines 871–889). On the native arm that is the receipt-completion stage's `before` block, which the completion result saves beside its `after` block (`native_shared_receipts.py:433–437`, `:462`). A run that saves no `before` reading is metric-missing for prediction 2; the `after` value never replaces it.
  - **What "pre-completion" means on this arm.** The native model can rerun the structural receipt check and correct its receipt before the seal (the plan's declared difference H6, line 600). So `R0` is the receipt after that self-correction. In production the initial check's output also shows the registered fraction (NP1.5). The reading is reported under that description beside the API values, which had neither.
- **Set B** is unchanged (lines 783–807): validation passed under the native arm's registered schema closure; duplicate keys 0; the five receipt floors at 0; one common checker, the v4 receipts checker at a pinned source hash, run on copies of both sides' records. The coverage floor is applied to neither side. The checker's source hash, the schema closures and the snapshot identities are bound in NP1b, where the plan binds them in P4b.
- **Missing data, n=3 and n=1** are unchanged (lines 844–855): a primary verdict for a project needs complete n=3 on each side under definition (2); the three kinds of missing are kept apart; n=1 cells (the canary, the pilot, VOICE_PEDIATRIC and Kids First) are descriptive only.

## NP1.5 The native receipt floor for replicates
- **What D109 requires:** the canary's floor stays pending and its reading is reported; "The measured value informs a registered native floor before any native replicate. No API threshold is copied".
- **A defect in the code as it stands (#5939).** At the cited commit a run whose floor is pending cannot complete.
  - The final receipt command is `receipts check … --strict` (`native_shared_render.py:288`). Under `--strict` the command exits 1 when the block's floor state is `pending` (`cli/receipts.py:303–322`). That check has to pass before the draft, the final evidence and the recorder, and the independent receipts gate applies the same floors (audit).
  - Two independent readings agree: the Claude review's P2-8 and the Codex CLI floor audit. No run has reproduced it, because no native run has reached that check.
  - The canary and the AI_READI pilot both run with a pending floor. As the code stands neither could be accepted, and the rule below would have no input.
  - **Its repair is a prerequisite of any pilot** (NP1.7). The rule the code has to match is amendment N1's: N1.4(B) rows 0 and 5. This amendment does not restate them.
  - The policy asset says what the code does: "A pending floor remains a diagnostic pilot and cannot satisfy strict completion." That sentence is model-facing, and the asset's pin sits in a protected file. Its change goes to the owner as a changed packet.
- **What a registered native floor is in the code.** Two identities are involved:
  - **the policy asset,** `native_shared_receipt_policy_v1.md`, a model-facing file selected and pinned by sha256;
  - **the receipt-policy registration,** a separate JSON document that names the asset by `runtime_policy_sha256` and carries `coverage_floor`, which is either `{state: pending, mode: diagnostic_pilot}` or `{state: registered, numerator, denominator}` (`native_shared_contract.py:785–810`).

  Registering a value makes new registration bytes with a new sha256, which each production registration selects. The policy asset does not change at that step.
- **What the model is shown does change.** The initial receipt check's output carries the registration's JSON (`native_shared_receipts.py:369–374`), and the receipt-stage request carries the parsed policy (`:389–391`). So a production run's model sees the registered fraction from phase 1 on, where a pilot's model sees `pending`.
  - **This is the planned difference between a pilot and a production cell,** beyond inputs and runtime terms (NP1.7). The stage-request hashes on both sides are retained, so the difference is shown and not inferred.
  - **What it means for comparing a pilot with production.** A pilot's coverage is produced with no target in view. Production coverage is produced with one. The floor is a threshold taken from the first kind of reading and applied to the second. Whether a visible target raises coverage, or leads a model to leave out, before the seal, values it cannot receipt, is not known. Production's populated-leaf counts (prediction 1) and coverage (prediction 2) are read with that. Pilot readings are never pooled with production readings and never set beside them as like for like.
- **The basis** [proposed, NP1.10(p)]: **the native floor is measured on D37's at-receipt basis,** as the plan's floor is and as the API arm's registration is (`basis: receipted_part`).
  - **What the plan and D37 say.** "D37 fixes the snapshot basis" (line 1117). The plan's rule reads "D37 at-receipt coverage fractions, `with_receipt_at_receipt / receiptable_at_receipt`" (lines 1125–1127) from the accepted attempt's frozen `O,R1` snapshot (line 1131). The plan calls final-record coverage descriptive (§3a, lines 880–881), and says "deleting unreceipted leaves **does not improve source coverage**" (lines 893–894).
  - **What v2 did.** v2's rule read final-record coverage and did not say that this departs from D37. That was the Claude review's first P1.
  - **What the code does today.** The native `floor()` reads only the final-record counters, `with_receipt` and `receiptable` (`native_shared_receipts.py:250–259`, `:296–307`), and the native registration has no basis field (`native_shared_contract.py:803–808`). The policy asset says the same: "The registered production floor is the exact integer fraction with_receipt / receiptable on the final record, using the unchanged receipt counters."
  - **The D37 counters are already measured on the native arm.** The final-stage check passes the sealed original record to the checker (`native_shared_receipts.py:484–498`), which then fills `slots.with_receipt_at_receipt` and `slots.receiptable_at_receipt` (`receipts.py:2497–2513`). The final receipt has to equal the receipt-completion stage's effective receipt (`native_shared_receipts.py:485–489`), so those counters are the plan's `O,R1` pair. The native gate does not read them.
  - **What a yes needs: an engineering prerequisite, not yet written.** The receipt-policy registration declares the basis; `floor()` and the receipts gate read the at-receipt counters; and the policy asset's sentence quoted above is changed to name that basis. A helper is preparing the change on a separate local branch. It lands before the canary's registration, together with the repair of #5939, so that the canary, the pilot and every production cell run one asset. Both asset sentences go to the owner in one changed packet.
  - **What a yes gives.** After the seal the model can change neither the original record nor the completed receipt, so nothing it does later moves the gated ratio. The ratio is settled when receipt completion ends. Whether a production run whose ratio already fails stops there or at its final check is settled by the implementation before the canary; the attempt is not accepted either way.
  - **If the answer is no:** the floor is measured on the final record, as the code has it today. Only the #5939 sentence of the asset changes. The owner then accepts these consequences:
    1. **It departs from D37 and from plan §8.** Removing unreceipted leaves from the full record after the seal raises the gated ratio. That is the behaviour D37 was chosen to neutralise, and prediction 1 then reads the reduced record. This is a reading of the code; no run has shown it.
    2. **The ratio falls with reconciliation,** which adds leaves that have no receipt route. A floor taken from a CHORUS canary would gate projects whose reconciliation volumes differ.
    3. **The stop-loss is exposed.** Two floor failures with one root cause, "reconciliation added leaves that cannot be receipted", would end native re-running (NP1.6).
    4. **The cap's reason does not apply.** The plan's reason is that receipt completion drives the D37 ratio towards 1 (lines 1134–1135). On the final record the plan's two assisted API canaries read 58/63 and 64/75.
  - **What the lead knew.** The plan's values for those two API canaries predict a floor near 17/20 on the final-record basis and 19/20, capped, on D37's (lines 200–201). The lead had them in view. They are API values from assisted runs, not native readings, and v2's choice followed the policy asset's sentence, which predates this amendment. They are stated here so that the owner chooses the basis knowing them.
- **When the rule is fixed.** The plan fixes its floor rule "before any pilot runs", and the later amendment "only computes its value" (§8, lines 1117–1121 and 1159–1162). The N1 canary is the first pilot here: it supplies a reading this rule uses. So this amendment, with the rule and the reading it names, is ratified **before the canary's word is given.** That is why the header says so.
  - **If the canary's word is given first** [proposed, NP1.10(af)]. This is the case in which the owner answers no to amendment N1's item (ah).
    - Before its own ratification this amendment's header records when the canary's outcome became available, and what of it the lead, each reviewer and the owner had seen. N1.5 requires that record.
    - **The floor rule stands only if it was written first.** The rule block below and items (p), (q) and (r) have to be byte-identical to a draft of this file that was committed and pushed before the canary's dispatch. A GitHub record that names that commit and carries a server time before the dispatch is the evidence. The ratification names that commit, and every report of the floor says that the rule was written before the outcome and ratified after it.
    - **If that text changed after the outcome was available,** the canary's reading supplies no fraction. One further native CHORUS pilot, registered after this amendment's ratification, supplies it. It is not a replicate, and NP1.6's pilot rules apply to it.
    - Any other rule of this amendment that changed after the outcome was available is listed in the header in the same way.
- **The rule** [proposed, NP1.10(q)]. It is the plan's floor rule (§8, lines 1125–1127) read for native pilots, and it takes no value from the API arm:

> The registered native coverage floor is the lowest of the eligible native pilots' D37 at-receipt coverage fractions, `with_receipt_at_receipt / receiptable_at_receipt`, rounded down to a multiple of 1/20 and capped at 19/20.

  - **If NP1.10(p) is answered no,** the rule reads `with_receipt / receiptable` on the final record in place of the at-receipt counters, and is otherwise the same.
  - **Eligible pilots:** the N1 canary and, if NP1.10(e) is yes and AI_READI is in scope, the AI_READI native pilot. Only an accepted attempt's saved result supplies a fraction; a rejected, stopped or assisted attempt never does (lines 1129–1133).
  - **Which reading.** Each pilot contributes one fraction, from the `slots` of its final-stage receipt check: the block the controller writes with `native_receipt_stage: final` (`native_shared_receipts.py:484–498`), read from the accepted attempt's saved result.
  - **On the at-receipt basis, a second reading of the same pair exists.** The receipt-completion stage's `after` block is the checker run on the sealed original with the completed receipt (`:433–437`). It is reported beside the first. If the two differ, the floor's registration resolves the difference in a filed finding before it registers a value.
  - **Readings that are not used.** The controller also evaluates the floor at the initial receipt check, where it forces the state to pending (`:363–364`). That is reported. It does not enter the rule and does not gate a production record. Final-record coverage is reported for every record as the plan's descriptive quantity.
  - **What gates in production:** the final-stage check's reading on the chosen basis, against the registered fraction (NP1.6).
  - **A pilot whose saved result has no such reading** supplies no fraction, and the "no value" case below applies.
  - **Arithmetic:** exact integers, `floor(20 × with_receipt_at_receipt / receiptable_at_receipt) / 20`, then the minimum with 19/20, registered as a numerator over the denominator 20.
  - **Why the cap:** the plan's reason (lines 1134–1140). Receipt completion drives the at-receipt ratio towards 1, and a floor of 1 would stop a replicate on one unreceipted leaf.
  - **No lower bound.** The plan's rule rests on a re-canary that has passed its own 19/20 gate (lines 1147–1149). The native canary is ungated (D109), so the native floor is wholly the pilots' own reading. A low reading registers a low floor, which gates little. The value is reported with that said, and every production record's coverage is reported whatever the floor. **A value of 0/20 is no floor:** a reading under 1/20 yields no value.
  - **The AI_READI branch:** the pilot is concluded without acceptance when its second attempt ends without acceptance, or when the owner records a decision to forgo the second attempt (NP1.6 gives it two). At that point, and not after a first stop, if the cause is not rule-level, AI_READI leaves scope as infeasible, reported as a feasibility result, and the canary alone sets the value (plan step 8, lines 307–312). A rule-level rejection is NP1.6's case.
  - **No value:** if a pilot the branch still requires has no accepted attempt or a zero denominator, or if the value comes to 0/20, the rule yields no value. No production cell registers until a prospective amendment, reviewed as this one, supplies one. No other observed ratio is substituted (lines 1150–1152).
  - **Conformance, not choice.** The floor's registration confirms from the merged source that these are still the fields. If the merged source differs, the rule yields no value until a prospective amendment restates it.
- **How the value is registered** [proposed, NP1.7]: in a dated amendment that gets this amendment's review and the owner's ratification. It checks the arithmetic and the inputs and does not revisit the rule (lines 1159–1163).

## NP1.6 Acceptance, attempts and stops
- **Each attempt is judged by N1.4(B)'s rows B0–B7** [proposed], as ratified, on the saved result after the attempt ends. N1 wrote those rows for the canary. Applying them to the AI_READI pilot and to production cells is this amendment's proposal.
- **For production cells, row B5 gates** [proposed]: the final-stage floor reading (NP1.5) must read `state: passed` under the registered floor. Pilots keep B5 reported and labelled UNMEASURABLE (D109). "Accepted" for a production cell then means B0–B7 all hold.
  - A registered floor is also enforced inside the run, by the final strict check and by the receipts gate (audit). So a production attempt that fails the floor does not complete, and row B0 fails with it. It is classified by its cause, a content slip, not as a controller fault.
- **Blind source review (B6) is per record** (D36): a fresh Claude session and a Codex CLI pass, neither of which generated or operated the run, with the second blind reviewer's recall seed pinned to `original_full` before anyone reads the audit.
- **The owner signs each acceptance record** (D36). Its format is plan §6's (lines 1026–1048). [proposed] The native identities N1.6 lists stand in place of the API-only fields.
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
| registration or environment | A fault of the registration or the launch environment and not of generated content: the host, the keep-awake, the account, a usage stop, or an admission failure at dispatch. One contingency under a new registration, corrected where there is something to correct. A usage stop has nothing to correct; it needs only the new registration and word |
| impossible limit | As the plan writes it |
| record shape | The attempt ends on a native helper's refusal of the record for a value of the wrong cardinality or type. A refusal before the phase-1 seal that the model corrects and re-checks is not a stop; the instruction allows it. The native arm has no write-time normaliser (N1.1). One contingency |
| transport | The runtime's terminal result or a supervisor boundary records a transport fault. One contingency |
| budget or clock | The dollar guard, the deadline or the owner's manual stop ended the attempt. One contingency, with a new word |
| unknown | Held for the owner's adjudication before any retry |

  - The plan's rules beside its table stand (lines 1360–1377): a content defect outranks every operational class; unmeasurable is not failed; an assisted attempt is evidence only.
- **Stop-loss** [proposed]: the plan's production rule (lines 1322–1329) for the native shared-v1 condition. Two rejections with the same root cause end re-running in that condition. The count covers every native production cell, the two descriptive cells included, across every label and registration, and it never resets. Rule-level causes and content slips count; other stops are counted and reported separately.
- **Pilots:**
  - **The canary** is governed by D113 and N1.5.
  - **The AI_READI pilot has at most two attempts** [proposed], concluded as NP1.5 says.
  - **A rule-level rejection of the AI_READI pilot ends the native shared-v1 condition** [proposed]: no further native pilot or production attempt, for any project, in this condition. The API arm is not affected.
    - This is what the plan does for its own pilots: "The first rule-level rejection of a pilot, the re-canary included, ends this condition" (lines 1318–1321).
    - It is also how the lead reads D113's "native shared-v1 cell only" for the canary. D113 was decided when the canary was the only native cell, and its contrast is with the API arm. That is the lead's reading, not the decision's words.
    - **If the answer is no:** a rule-level rejection of the AI_READI pilot ends AI_READI's cells only. AI_READI leaves scope, the canary alone sets the floor, and the rejection counts once toward the production stop-loss.
- **Missing cells** follow plan §7 unchanged (lines 1094–1108).

## NP1.7 Order of events and pacing
- **Before any pilot: code that has to exist.** These are engineering prerequisites, not choices. All of them land before the canary's registration, so that every pilot and production cell runs one source and one set of assets.
  - N1.9's list.
  - The repair of #5939: a pending floor is reported and does not block a pilot (NP1.5).
  - If NP1.10(p) is yes: the at-receipt basis in the registration, in `floor()` and in the receipts gate (NP1.5).
  - The changed policy asset, approved by the owner as a changed packet: one sentence for #5939, and a second if (p) is yes.
1. **The canary is accepted under N1.** Amendment N1 is ratified, the native code is accepted and merged (N1.9), and the CHORUS canary is registered, run and accepted on N1.4(B)'s rows. **No pilot or production registration under NP1 is made before the canary's acceptance record is signed.** That governs when the production sequence runs. It does not govern when NP1 is reviewed and ratified: NP1 is ratified before the canary's word (NP1.5). If the canary is rejected at rule level, D113 ends the native shared-v1 cell, which this amendment reads as the whole condition (NP1.6), and this amendment has nothing to apply to.
2. **The native measured-usage packet** [proposed], in the role of the plan's measured-cost packet (lines 290–299). From the accepted canary's saved result it reports:
   - the admission readings of each usage window, and the first, last and highest reading of each window during the run (N1.6);
   - the wall clock from dispatch to the end, against the deadline;
   - the runtime's own cost estimate, against the dollar guard;
   - context use against the registered limits;
   - each stage's outcome;
   - the capture-to-reservation and capture-to-dispatch ages (N1.5).

   It carries no quality comparison against v8.
3. **NP1b** [proposed]: a dated amendment, reviewed as this one is and ratified by the owner by sha256 before any native pilot or production registration. "It applies rules; it does not invent them" (the plan on P4b, lines 304–305). It:
   - applies NP1.2's scope rule to the usage packet, and settles every in-scope project's fit;
   - computes each project's runtime terms by the rule below;
   - names, as a conformance check on the merged source, the exact saved fields of the eligible record and of the pre-completion reading (NP1.4);
   - pins the comparator manifest's record hashes, which include AI_READI's only if that comparator exists by then (NP1.3);
   - pins the recall adapter, the common checker's source hash and the schema closures;
   - states, from the usage packet, how many attempts the usage windows allow in a week;
   - when no pilot is pending, registers the floor's value under NP1.5 and fixes K_native.

   It may change which whole projects are in scope. It may not change a metric, an instrument, a decision rule, a tolerance, an analysis-set definition, an eligibility rule or a missingness rule. It may not use any v10 quality value to choose a project, a rule or a threshold (lines 316–325). **Computing the floor's value by NP1.5's fixed rule is not such a choice:** it applies the rule to the accepted pilots' coverage readings, as the plan's A15 does (lines 1159–1162).
4. **The AI_READI pilot,** if NP1.10(e) is yes and AI_READI is in scope: registered, run and accepted before the floor's value is computed.
5. **The floor's registration** (NP1.5), in NP1b or, when a pilot was pending, in its own dated amendment reviewed and ratified the same way. **It fixes K_native** (NP1.3). **No production cell registers before it.**
6. **Production cells, in NP1.2's order, one attempt at a time.** For each attempt:
   - a registration on merged main that pins the source commit, the full and core schema closures, the bundle, the chunk manifest and the source manifest (plan §11, lines 1404–1405), the runtime and its probes (N1.2, N1.9), the project's runtime terms, and the receipt policy that carries the registered floor;
   - two independent reviews of the registration and its packet (N1.3);
   - the owner's statement of launch terms and the coded word, which binds one attempt by construction (N1.5);
   - capture, guard and launch as N1.5 orders them;
   - acceptance under NP1.6.
- **Words and registrations.** Each attempt has its own registration and its own word (D22; N1.5). Each retry is a new registration (D56).
- **Reviews** [proposed]: both reviewers review every registration, and each registration has its own two review documents. N1.9 item 4 builds one review bundle per registration, and its reader checks each review. v2's allowance of one document for a project's three registrations is dropped: nothing shows that the reader accepts it.
- **Runtime terms are per project** [proposed, NP1.10(x)].
  - **Why.** N1.5's deadline and dollar guard (D110) were set for one CHORUS canary, and D111 is scoped to "the canary's whole duration". CHORUS is the plan's cheapest run by a wide margin (lines 371–375), and Kids First's bundle is the largest of the six (lines 658–659). Applied unchanged, the canary's backstops could stop the larger projects for their size alone.
  - **CHORUS's production cells keep the canary's terms.**
  - **For every other project, NP1b computes two terms from the usage packet,** by this rule, fixed now:
    - the **size ratio** is the plan's expected cost of one run of the project over that of one CHORUS run, from the "Expected" column of the plan's table (lines 371–375). Kids First, which the plan does not price (line 376), takes the largest ratio in that table;
    - the **deadline** is the larger of the canary's deadline and twice the canary's measured wall clock times the size ratio, rounded up to a whole hour;
    - the **dollar guard** is the larger of the canary's guard and twice the runtime's cost estimate for the canary times the size ratio, rounded up to a whole ten dollars.
  - **The ratio is a proxy.** It comes from the API arm's sizing of each project's run, not from a native measurement. It is used because the ratified plan fixed it before any native outcome, and because it counts each run's fixed overhead, which a bundle's byte size alone does not.
  - **Fit, settled at NP1b.** NP1b reports a project when any of these holds:
    - its frozen inputs fail the registered limits. Such a project cannot run: it is descoped, or a prospective amendment changes the procedure for it before its cells, which then form a new stratum;
    - its computed deadline exceeds twice the canary's;
    - the rise in the seven-day reading over the canary's run, times the size ratio, exceeds the room the seven-day admission bound leaves. If the canary's run crossed a seven-day reset, this test cannot be made, and NP1b says so.

    In the last two cases the owner decides at NP1b, on that evidence alone: the project runs under its computed terms, or it is descoped.
  - **Unchanged for every pilot and production attempt:** the admission bounds (D118 and N1.5), overage disabled, the freshness age (D136) and margin, the keep-awake policy, the capture rules and the context mode. D110, D111, D118 and D136 were decided for the canary; applying them here is this amendment's proposal.
  - **Who sets the terms, and when.** NP1b computes them, both reviewers check the arithmetic, and the owner ratifies NP1b by sha256, before any pilot or production registration under this amendment. The AI_READI pilot runs under AI_READI's terms. Each registration carries its project's terms, and the owner's statement of launch terms restates them before each word (N1.5).
  - **One project, one set of terms.** They do not change between a project's cells or attempts, and they are not recomputed from a pilot or an earlier cell. A later change is made before the cells it governs, and those cells form a new stratum (lines 321–325).
  - **What the rule is.** It sizes backstops; it predicts nothing. A stop by a backstop is a budget-or-clock stop (NP1.6). It does not change amendment N1: N1.5's terms remain the canary's.
  - **If the answer is no:** the canary's terms apply unchanged to every project, and a project that cannot finish inside them is descoped at NP1b or stopped.
- **Pacing** [proposed]: one native attempt runs at a time on the account. No term is relaxed to shorten the batch.
  - **The count:** up to 16 first attempts with the canary (1 canary, 1 pilot, 12 replicates and 2 descriptive cells), and at most one further attempt per cell.
  - **What each attempt asks of the owner's sessions.** Every session that draws on the registered account stands down from before the capture until the attempt ends, and none of them monitors it (N1.8(ad)). That is up to the attempt's deadline each time, 16 times or more.
  - **Each registration is valid for two weeks** (N1.8(g)).
  - **The usage windows pace the batch.** How many attempts fit in a week is not known. It follows from the usage packet and is stated in NP1b.
- **One procedure** [proposed]: every native pilot and production cell runs the same merged source and the same selected assets. Three things differ, and each is declared: a project's inputs; a project's runtime terms; and the floor value in the receipt-policy registration, which also changes what the model is shown (NP1.5).
  - **A later change to the native runner or to a model-facing asset makes the cells run after it a new stratum.**
  - **A change to how attempts are admitted, retried, stopped, selected or retained** is a change of scientific procedure. It is a new stratum and needs its own prospective amendment, whatever the bytes show. The plan says why: D35's parity test and diagnostic canary "show that the engineering is sound, not that a changed selection process has the same estimand" (lines 1221–1236).
  - **The one exception** is a change shown to leave all of that untouched. Then byte parity of the complete effective instruction and of each stage request on an already-run project, with a diagnostic canary the owner separately authorizes, keeps the later cells in the same stratum. That is D35's rule (plan §11, lines 1399–1405) read for the native arm.
  - **Who decides that the exception applies.** A written comparison says what changed and why admission, retry, stopping, selection and retention are untouched. A Claude reviewer and a Codex CLI pass, independent as N1.3 defines it, each confirm it, with findings filed. The owner accepts it by naming its sha256, before authorizing the diagnostic canary.

## NP1.8 The API arm under D134
- **What D134 says:** the API route is needed only for comparison. The plan's API matrix (lines 552–560) stays in the plan's text, and its scope is P4b's to fix (lines 300–306).
- **The comparison set** [proposed]: CHORUS only.
  - **The cells:** the clean CHORUS re-canary in plan A10's role (n=1, descriptive for good) and the three CHORUS replicate-gate cells (A16).
  - **Everything else on the API arm is "out of scope":** CM4AI, VOICE, AI_READI, VOICE_PEDIATRIC and Kids First. For Kids First this, with NP1.10(c), answers plan item 38's route.
  - **This supersedes the API arm's scope rule; it does not follow from it.** The plan funds the longest affordable prefix of its order from measured costs (lines 335–346), so with a larger budget the plan's rule would add CM4AI and the rest. D134 says the API route is for comparison; it sets no budget and names no project. Fixing the set at CHORUS is the lead's proposal, and P4b records it if the owner adopts it.
  - **Why this set and not less:** one API record supports no contrast beyond one record beside another. Three cells on one project allow the plan's n=3 structure rule and per-project means on a matched project. CHORUS is first in the plan's order and its cheapest run (lines 369–377).
  - **What it supports** [proposed]: a descriptive native/API contrast for CHORUS: the two arms' values side by side on the plan's metrics, with N1.6's declared differences. No directional rule is added for it. Each arm's own comparison with v8 keeps its own label.
  - **What a matched contrast requires,** from the plan (lines 583–592): the same frozen source bundle, manifest, source policy, schema closures, profile, omission context and scientific assets wherever the contrast claims they match; hashes of the complete effective instructions and of each stage request; and every remaining difference declared, not normalised away.
  - **The schema release may differ, declared.** The plan requires identical closures only where the contrast claims they match. N1.6 declares the native arm's 3.2.1 against the API arm's ratified 3.1.0 "unless the comparison registration moves by its own amendment". Which release the rebuilt comparison registration uses is decided with that registration. This amendment requires neither; the contrast reports each side's schema closure.
  - **If the re-canary is not accepted within its attempts,** the three replicate-gate cells do not run, and estimand 5 is not estimable. Native results are not affected.
  - **If the answer is no:** the owner names the set. With the re-canary alone, the contrast is one API record beside the native cells. With the plan's full matrix, P4b fixes its scope as the plan says.
- **No cell of the comparison set is a prerequisite for native production, if amendment N1's item (y) is answered yes.** Native pilots and production cells then proceed under NP1.7 whether or not any API cell has run.
  - **If (y) is answered no,** D131's freeze at the roster of 2026-11-11 stands. Native integration then needs D35's byte-parity test and one diagnostic CHORUS canary on the API route before it lands (N1.6). That paid API run is then a prerequisite of the native canary, and so of every cell here. It is not a cell of the comparison set.
- **The API arm's own open items,** recorded here and decided elsewhere:
  - the A21 run of 2026-11-11 ended at its first typed-audit call on a provider refusal (#5874). Its classification under plan §10 has not been recorded. By the lead's reading it used one of the re-canary cell's two attempts (plan §7);
  - the schema release of the comparison registration (above). The API arm's ratified schema is 3.1.0 (D71(a), P4a amendment 1), and the A21 registration was built on main at 3.2.1 with no API-arm schema amendment on record (N1.6);
  - the provider account's budget has to cover the set, and it is read before any launch;
  - the order of the rebuild and where D35's freeze starts depend on the owner's answer to amendment N1's item (y), as above.

## NP1.9 What is deferred, what this amendment does not change, and what it does
**Deferred** [proposed]: none of these is a prerequisite for a native pilot or production cell.
- **Native E2 and E5.** Prediction 4's review-pass instrument is P4b's open item 40, and N1.6 leaves native ratings to a separately ratified rating registration. Predictions 4 and 5 are "not measured" for this production cohort.
  - **They are not revived later by a registration alone.** The plan freezes E2's protocol before confirmatory outcomes (lines 1455–1456) and requires E5's scientific instrument choice before confirmatory generation (lines 1469–1474 and 2402–2413). A prediction of this kind can be measured on native cells only if a separate prospective amendment fixes its scientific rules before the first outcome it governs.
  - **The deadline this sets for the owner.** For prediction 4 or 5 to be measured on the main result, that amendment has to be ratified before the first production registration. After that the chance is gone for this cohort.
  - **Otherwise** a later native evaluation of these records is labelled descriptive or exploratory. It is not a registered prediction.
- **BC1 parity for the native arm** [proposed, NP1.10(aa)]. D91 decided that the first canary uses the declared shared-v1 differences and that "BC1 parity is a follow-up". It did not say whether the follow-up comes before production. **This amendment proposes that production cells run the declared shared-v1 differences, as the canary does,** and that adopting BC1 parity later is a change of procedure and a new stratum. That is the lead's extension of D91, not the decision's text.
  - **What a yes means:** the main result is produced under shared-v1. BC1 parity, if it is ever built for the native arm, starts a separate stratum.
  - **If the answer is no:** BC1 parity is built and accepted before the first production registration. The pilots then ran a different procedure, so a further pilot under BC1 parity supplies the floor, and this amendment is revised first.
- **Receipts v5.** v4 stays the registered, gating instrument (D105; plan §3a). The two D105 secondary measures are recorded under their own identities, as N1.1 says.
- **Canonical marks for native cells** (plan item 42, lines 2417–2423). A mark never changes an estimate.
- **Any with-crate native arm.** It is not in this matrix.

**Unchanged:**
- the plan file and its sha256;
- P4a amendment 1, and amendment N1, including N1.5's terms for the canary;
- D22, D25, D109's pending floor for the canary, and D113;
- any API-arm registration, and the rules the plan fixes for any API cell that runs, except the API arm's scope rule if NP1.10(ab) is adopted;
- any historical decision or record.

**Changed, for readers of the amendment:**
- the native column of the plan's matrix (NP1.1);
- plan §1 item 5's statement that native production cells are unregistered: they are planned here, and each still needs its registration;
- the plan's eligibility rule, for the native arm only (NP1.4);
- the API arm's scope rule, superseded by a fixed CHORUS-only set if NP1.10(ab) is adopted (NP1.8).

## NP1.10 Ratification: the owner names this file's sha256 at a commit, and answers each lettered item
Each letter is one decision, and a "yes" adopts exactly the value given. The cells themselves are D135's scope and are not a lettered item. An item answered no is revised and re-submitted before any registration that depends on it. Letters differ from v2's; the note after each item says how.

**Scope**
- **(a)** Scope and order for the native arm: whole projects only; the evidence is usage, fit and stop outcomes, never a quality value; the plan's order; fit is settled at NP1b; a D135 project leaves scope only at NP1b or, for AI_READI, at its pilot (NP1.2). *Changed.*
- **(b)** VOICE_PEDIATRIC is in scope, one descriptive cell, unless NP1b descopes it on usage or fit (NP1.2). *Split from v2 (b).*
- **(c)** Kids First is in scope, one descriptive cell, run last under the plan's conditions, unless NP1b descopes it on usage or fit (NP1.2). *Split from v2 (b).*
- **(d)** The two descriptive cells are production cells: they run under the registered floor and under NP1.6's acceptance rows, attempt bound, classification and stop-loss, and they never enter K_native or a verdict (NP1.2). *New.*
- **(e)** One native AI_READI pilot, not a replicate, with the floor pending, accepted before the floor's value is computed (NP1.2). *Split from v2 (c).*
- **(f)** That pilot has at most two attempts. It is concluded without acceptance at the end of the second, or when the owner forgoes the second. If the cause is not rule-level, AI_READI leaves scope and the canary alone sets the floor (NP1.5, NP1.6). *Split from v2 (c).*
- **(g)** A rule-level rejection of the AI_READI pilot ends the native shared-v1 condition, for every project. A no ends AI_READI's cells only (NP1.6). *New.*

**Role and comparison**
- **(h)** Role: native production cells are the study's primary generic_v10 cells; a native result is never pooled with an API cell or reported as the plan's package effect (NP1.3). *Split from v2 (d).*
- **(i)** Comparison rules: the plan's v10-against-v8 rules apply to the native replicate cells unchanged, under the label "native v10 against v8 API: package and runtime". A no makes native production descriptive only (NP1.3). *Split from v2 (d).*
- **(j)** K_native counts the in-scope projects among CHORUS, CM4AI and VOICE, and AI_READI only when its comparator was pinned at NP1b. It is fixed once, at the floor's registration, and never moves; a later failure is "not measured" (NP1.3). *Changed.*
- **(k)** The AI_READI comparator follows D64, item 14; its branch is fixed at NP1b on whether the no-crate v8 API run exists then; native AI_READI cells do not wait for that run (NP1.3). *Was (f).*

**Analysis sets**
- **(l)** An eligible native full record is the one the end capture pinned, in an attempt whose saved phase report lists `derive_final_core` as a current check. This amends the plan's eligibility rule for the native arm, with the four limits NP1.4 names. A no means the plan's rule is built before any pilot (NP1.4). *Restated.*
- **(m)** Prediction 2 reads the receipt-completion stage's `before` block, reported as taken after pre-seal self-correction; a run without one is metric-missing (NP1.4). *Was (h); wording added.*
- **(n)** Prediction 4 (E2) is not measured for this cohort, and is measured on native cells only under a separate prospective amendment ratified before the first production registration (NP1.3, NP1.9). *Was (i).*
- **(o)** Prediction 5 (E5) is not measured for this cohort, on the same condition (NP1.3, NP1.9). *Was (j).*

**The floor**
- **(p)** The floor's basis is D37's at-receipt coverage, with the code change NP1.5 names landing before the canary's registration. A no keeps the final-record basis the code has today, with the four consequences NP1.5 lists (NP1.5). *New.*
- **(q)** The floor rule: the lowest of the eligible native pilots' fractions on (p)'s basis, rounded down to a multiple of 1/20 and capped at 19/20; no lower bound, except that a value of 0/20 yields no value; no value means no production registration (NP1.5). *Changed.*
- **(r)** For production cells, N1.4(B)'s row B5 gates on the final-stage check's reading, on (p)'s basis, against the registered floor; pilots keep it reported (NP1.6). *Changed.*

**Acceptance**
- **(s)** At most two attempts per native production cell, counted across every label and registration (NP1.6). *Was (m).*
- **(t)** The plan's cause classes with NP1.6's native readings (NP1.6). *Was (n); two rows reworded.*
- **(u)** Stop-loss: two rejections with the same root cause end re-running in the native shared-v1 condition; the count covers every native production cell and never resets (NP1.6). *Was (o).*

**Procedure**
- **(v)** The staged procedure: the measured-usage packet, then NP1b, then the floor's registration, each reviewed and ratified before the registrations that depend on it. NP1b applies rules and changes none; computing the floor by (q) is an application (NP1.5, NP1.7). *Was (p); wording added.*
- **(w)** Reviews: both reviewers review every registration, each registration with its own two review documents (NP1.7). *Was (q); the allowance is dropped.*
- **(x)** Runtime terms are per project: CHORUS keeps the canary's; every other project's deadline and dollar guard are computed at NP1b by NP1.7's rule; NP1.7's fit tests apply. A no applies the canary's terms to every project (NP1.7). *New.*
- **(y)** Pacing: the admission bounds, overage disabled, the freshness terms, the keep-awake policy and the capture rules apply unchanged to every pilot and production attempt; one native attempt at a time; no term relaxed to shorten the batch (NP1.7). *Was (r); narrowed by (x).*
- **(z)** One procedure: a later change to the native runner or a model-facing asset is a new stratum; a change to admission, retry, stopping, selection or retention always is, and needs a prospective amendment; byte parity with an authorized diagnostic canary keeps the stratum only for a change that both reviewers confirm, and the owner accepts by sha256, as leaving those untouched (NP1.7). *Was (s); who decides is added.*
- **(aa)** Production cells run the declared shared-v1 differences, as the canary does; BC1 parity, if adopted later, is a new stratum. A no means BC1 parity before the first production registration, with a further pilot (NP1.9). *New.*

**The API arm**
- **(ab)** The API comparison set is CHORUS only, the clean re-canary and the three replicate-gate cells, with every other API cell out of scope. This supersedes the API arm's longest-affordable-prefix scope rule (NP1.8). *Was (t).*
- **(ac)** The native/API contrast for CHORUS is descriptive, with no directional rule; the two arms' schema releases may differ, declared (NP1.8). *Was (u); the schema clause is added.*
- **(ad)** No cell of the API comparison set and nothing on NP1.9's deferred list is a prerequisite for a native pilot or production cell. This holds only with a yes to amendment N1's item (y); with a no, D35's diagnostic canary on the API route precedes native integration (NP1.8, NP1.9). *Was (v); made conditional.*

**Timing**
- **(ae)** This amendment is ratified before the N1 canary's word is given, so that its floor rule and the reading it names are fixed before the canary's outcome exists (NP1.5). Amendment N1 proposes the same as its item (ah). *Was (w).*
- **(af)** If the canary's word is given first: the floor rule stands only if its text was committed and pushed, unchanged, before the canary's dispatch, and is reported as written before the outcome and ratified after it; otherwise one further native CHORUS pilot supplies the floor (NP1.5). *New.*
