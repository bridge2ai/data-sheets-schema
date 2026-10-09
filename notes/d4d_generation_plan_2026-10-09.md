# D4D generation plan — 2026-10-09

Written in America/Los_Angeles on 2026-10-09, after the open-issue triage of 2026-10-08 (its working files are not in the repository; it filed #4758–#4763, #4765 and #4766), read against main `15d053d1a8ec8d306deed6650751cb57b6a4fddc`. It continues [the 2026-09-12 completion plan](d4d_generation_evaluation_completion_plan_2026-09-12.md) for the remaining API and Claude Code / native generations.

**Status: a proposal.** Nothing here is authorized until the owner decides the items under [Owner decisions](#owner-decisions). Every billed step needs a reviewed registration and an owner word naming the registration's sha256 and a cap; for a roster, the word names the roster's sha256 and every registration sha256 it lists, because a roster row pins only a path (`cli/api.py:155`). No fan-out before a reviewed canary; the canary takes the same launch path as the batch.

**How it was made.** Four research passes (inventory against the study design, the API route, the native routes, acceptance requirements) fed three independent plans (critical path, cost and risk, scientific validity). A synthesizer merged them; an adversarial critique found 21 problems and 11 missing items; a revision addressed all 32 and a second check found 12 new inconsistencies, which a repair pass fixed. None of these drafts is published; where a figure rests on one, the note says so. An adversarial review of PR #4787 then confirmed 49 findings, filed as #4789–#4800; the revision that followed applied them and refreshed the time-sensitive facts as of 2026-10-09 17:08Z. A second review round confirmed 24 more, filed as #4804–#4812, and a third confirmed 18, filed as #4817–#4819; both are applied here. Facts were checked at `15d053d1a`, in local ledgers and records, and on GitHub. Nothing was launched or spent in making this plan. Its only GitHub writes were this PR (opened, force-pushed and its body edited) and the review issues #4789–#4800, #4804–#4812 and #4817–#4819, including an edit to #4800's body and the deletion of that issue's first revision from its edit history (G3).

Files under `notes/matched_cborg_2026-09-14_v10d/.local_drafts/` are gitignored local evidence in the primary checkout, and `d4d-executions/` is an unversioned local directory; neither is published. The CBORG chain amounts (the shared ledger's total and its split, the chain's cap and remaining headroom, the lineage totals and the per-audit costs) are not given here. The v10z public records do not give them (`notes/matched_cborg_2026-09-18_v10z/workload.public.json`: 'exact amounts and reconciled headroom remain private'), and on 2026-10-09 the owner decided that this note keeps them out (G3). Withholding them keeps the note consistent with those records; it does not make the amounts private. Issue and pull-request text and files on main written before this plan already give most of them; G3 gives examples and says what this PR added.

**Changed on main since the plan's basis** (`15d053d1a` → `c34d9a638`, origin/main as of 2026-10-09 17:08Z: three PRs; none edits the runner, shared-generation, typed-audit, batch or render files):

- PR #4769 (`7ff16f9bf`): offline receipt readdressing, `d4d receipts readdress`; closes #4446, #4767, #4768. It also changes `receipts.resolve`, which the runner's full-readdress step (`unresolved_receipt_slots`, `apply_readdress`) and the receipt check call: an index spelled with more than 4,300 digits used to raise ValueError and now resolves by its value, or not at all (#4767). Every shorter spelling, leading zeros included, resolves as before.
- PR #4771 (`a6568b4cd`): documents the release inventory and receipt origin; closes #3284, #4447.
- PR #4772 (`c34d9a638`): records the actual merge selection rule in provenance; closes #4770 (the first merge-CLI defect in #4765).

Related issues filed by the triage: #4758 (direct-arm pause scope), #4759 (Claude Code 2.1.272 runtime), #4760 (saved permission-probe producer), #4761 (audit28: run or retire), #4762 (`arm_comparison.md` bundle-md5 sentence), #4763 (publish the `/private/tmp` lineages), #4765 and #4766 (follow-ups from #176 and #1802).

Native issues filed after the triage (all open as of 2026-10-09 17:08Z): #4773–#4786 and #4788, the Codex session's stopped-capture work, several of them cited by the terminal-source branch's commits (N1); and #4801, reuse of the #4764 span loader in JSON event preflight, filed against the 900 s selected-trial deadline (N2).

## Summary

Basis: main 15d053d1a. For what main gained after that commit, see "Changed on main since the plan's basis" above. Every fact relied on was checked on 2026-10-09 in code at 15d053d1a, in local ledgers and records, or on GitHub. As of 2026-10-09 no billed run is live; nothing was launched or spent in making this plan, and its GitHub writes are listed under How it was made.

**What the owner decides first (sitting 1, G3)**

1. **What 'native' means now** (D09 #4758, D10 #4761). The recommended options are: the #4354 adapter's first live run goes on the claude.ai subscription and is labelled the direct arm, and audit28 is retired. **Under those options this plan contains no CBORG-native (claudecode_agent) generation at all.** All of its CBORG generation goes through the Messages API: the claudecode_api arm, the with-crate runs under #2914 B (written under claudecode_agent_crate) and, if D16 adds them, the monolithic runs (claudecode_api_monolithic). E5's rating sessions, if run like the 2026-09-12 CBORG rescore, are Claude Code CLI sessions on CBORG: agentic evaluation, not generation. That departs from the owner's 2026-09-25 instruction 'focus is native until everything is validated and working', and the owner must confirm the departure. To keep CBORG native in scope instead, build a CBORG transport for the shared protocol (N12, new engineering) and/or run audit28 once (Z3–Z5).
2. **API first, and its money** (D01, D07, D22, D08).
   - A new generic_v10 API allocation of $100 for the pilot phase: the CHORUS pilot ($15 cap), one CHORUS contingency ($15), the AI_READI pilot ($35 ceiling) and one AI_READI contingency (at most $35). Both AI_READI lines are provisional until sizing.
   - At most 2 billed attempts per registered cell.
   - A ruling that the v10z standing authorizations ('until they succeed', 'all evaluations of the CHORUS d4d', full-reservation debits) do not extend to generic_v10, and their withdrawal at G3 whatever D10 decides (D22).
   - Yes or no on sending the prepared #1849 CBORG follow-up. Claude sends it only after the owner's explicit yes to a question naming the recipient, the channel and the exact text (G5).
3. **Today:** tell the Codex session to push its seven unpublished heads, as they stand at push time (G0, #4763).

The rest of sitting 1 settles the design: D02–D06, D12, D13 (#4162 only), D15, whether D16 is needed, D17–D21, D23 and D24.

**What can start this week at $0 (no provider call)**

- G1a: `git bundle` copies of the seven `/private/tmp` branches into a durable directory, changing no clone's refs or branch, inside a window outside the Codex session's CPU-timing windows, agreed through the owner alongside G0. G1b: Codex pushes them once told.
- G2 decision table; G4 gap issues.
- Drafts at 15d053d1a of the A3 registration builder and the A4b single launcher script, plus the A3b live dollar readout and the A5d root-only draft contexts (the full drafts follow G3). Then the A1 sizing harness at 15d053d1a, which builds the real runtime payloads with no model call. The builder's and launcher's final runs are part of A6 at the launch base, and A7 reviews them.
- P1 comparability audit; E7 (#4762).
- The Codex session continues N1 (#4741→#4738→#4740) on its own branches. The plan edits none of them; #4354 delivery (N3) uses a separately cut branch.

**Then the API route**

- Preregistration (P2–P4), the A2 runtime PR (summarized thinking display) and the A2c dollar stop, all merged before the launch base (A4).
- One CHORUS pilot under a pending floor: a one-row `d4d api batch` roster through the launcher, then blind source review and owner acceptance.
- Then the AI_READI pilot, the numeric floor, CHORUS ×3, CM4AI/VOICE/AI_READI ×3, VOICE_PEDIATRIC ×1 (or ×3), Kids First ×1.
- Under #2914 path B, also a with-crate CHORUS canary plus ×3.
- That is 16 API runs under the recommended options, 20 with path B, plus contingencies.
- Every generic_v10 API launch goes through `d4d api batch` with a roster, never `d4d api run` (D20).
- Every billed step has its own registration review and an owner word naming its registration's sha256 (for a roster, the roster's and every listed registration's) and its cap.

**Biggest new risk.**

Typed-audit stages and receipt completion get one delivery each, with no retry. In v8, 8 of 92 calls needed a retry: 5 transport errors and 3 answers that ended end_turn and were rejected. At that rate a run with 4–8 single-delivery calls ends terminally 30–52% of the time, and a 3-row roster under a registered floor finishes without a stop only 11–34% of the time. A stopped label can never be re-run: re-running re-derives its verdict and stops again. So D21 preregisters continuation under a new prefix, and the pilots measure the real rate first.

**Facts that shape this plan (checked on 2026-10-09)**

- The receipt registration, floor included, is in every ordinary phase's base instruction from the full phase onward (`api_runner.py:1470-1472, 978, 2784-2788`), so a `render-prompt` diff does show a pending floor against a registered one (D03, A6).
- `render-prompt` omits `generation_context`, whose source-manifest pin `{path, sha256, bytes}` reaches every shared-generation request, so even a comment-only manifest edit is model-facing (D04).
- A3 and A4b are drafted at 15d053d1a and A1 runs there; their final runs are A6's at the launch base, reviewed in A7, so none of them waits on G3 or the launch base.
- A2c lands before A4. The launch worktree never fast-forwards over a merged data PR except by D17's procedure: git refuses to overwrite the untracked run outputs even when they are identical.
- Each roster row needs its own top-level `registration_id` (`cli/api.py:163-167`); A7 checks each one for neutrality.
- A roster row pins only a registration's path (`cli/api.py:155`), and the batch reads each registration when it starts, so a word names the roster's sha256 and every registration sha256 it lists, and the operator re-hashes them before each launch (A10).
- `d4d api run` runs a single registration with no floor verdict, canary block, run lock or #795 guard, and `d4d api status` and `d4d api stop` cannot see it (`cli/api.py:589-672, 827, 1070, 1100`). Every generic_v10 launch therefore goes through `d4d api batch` with a roster (D20).
- `data_sheets_schema` has no `__init__.py`, so `data_sheets_schema.__file__` is `None`; the launcher checks `__path__` and five module files instead (A4b).
- The $100 pilot allocation funds the AI_READI contingency that A14-acc allows (D07).
- Direct-arm counts follow D02's VOICE_PEDIATRIC ×1, and a pending-floor N9 never counts as a replicate: 15 or 18 runs (D25). D23's review counts include the direct arm and the #2914 B records. E5's rating counts include the #2914 B records and a rubric20 repeat panel, but not the direct arm: E5b-reg waits on no N step, and no step yet rates direct-arm records (that would need its own registration, review and word after N11).
- A1 sizes the full runtime payload, not only what the offline prepare check sees.
- #2914 path B is about 4 billed with-crate runs.
- The typed-stage 'cap' risk is an end_turn with an empty answer, which larger caps do not prevent (risk 3).
- The A4b launcher pins the worktree's code (risk 10).
- Effort is a fixed confound between arms (D09).
- N3 delivers #4354 from a separately cut branch and edits no Codex branch.
- #4764's YAML fast path is applied locally at aa09dbbc6, but #4740's latest result (2026-10-09T07:41Z, still its newest comment as of 2026-10-09 17:08Z) is a failure: the receipt child exits 0, but no parent phase-1 seal is written before the 60 s deadline.
- #4751 is closed and leaves N1.
- #4766's report-totals check is an A11 acceptance check.
- #4765 does not gate generation.
- The triage closed all 383 of its close candidates (the last, #4751, at 2026-10-09T08:08:48Z); 575 issues were open afterwards.

## First actions

1. owner, today: tell the Codex session to push its seven unpublished branch heads to their existing names, as they stand at push time, with no PR and no merge (G0, #4763). The terminal-source branch was at aa09dbbc6 at the 2026-10-09T08:58Z re-check, past the 7a17202f7 the issue lists, and has moved since (f00bcb5df as of 2026-10-09 17:08Z, still unpublished).
2. maintainer-dev, today, $0: `git bundle` the same seven branches into a new durable directory under `d4d-executions` and verify each bundle (G1a). Run it outside the Codex session's CPU-timing windows for #4740, in a window agreed through the owner alongside G0, one clone at a time. No clone's refs, branch or Codex file is changed.
3. maintainer-dev, $0: the G2 decision table, and the G4 gap issues (11 items) plus the #4762 extension. Sanitize at-sign tokens; no at-mentions.
4. owner, sitting 1 (G3), once the G2 table exists, decide first:
   - D09 and D10: confirm or reject the departure from 'focus is native'. Under the recommended answers the plan has no CBORG-native generation.
   - D01, D07 and D22: API first; a $100 pilot allocation with at most 2 billed attempts per registered cell; and the v10z standing authorizations not extending to generic_v10 and withdrawn now, whatever D10 decides.
   - D08: yes or no on sending the #1849 follow-up. Claude sends it only after the owner's explicit yes to a question naming the recipient, the channel and the exact text (G5).

   Then work through the rest of the decision table.
5. maintainer-dev and curator, $0, this week:
   - A3 registration builder, drafted at 15d053d1a with provisional limits;
   - A3b dollar readout (gate: it reproduces $3.30811950 from the v9 ledger);
   - A4b launcher, drafted at 15d053d1a;
   - A5d draft contexts (root-only now; the full drafts after G3);
   - then the A1 runtime-composition sizing harness at 15d053d1a;
   - P1 comparability audit;
   - E7 (#4762).

   Run them outside the Codex session's CPU-timing windows.
6. Codex session: continue N1 on its own branches; the next #4740 target is parent receipt settlement and phase-1 sealing, last measured at aa09dbbc6. The plan edits none of its branches; #4354 delivery (N3) uses a separately cut branch.
7. After G3:
   - codex-operator runs A1b's unbilled count calibration, with the owner's consent, and acknowledges D22 (with the G3 withdrawal) and D12 (G6);
   - maintainer-dev opens P2, A2 and A2c, and Z1 if D10 is 'retire'.
8. After P4, A2 and A2c merge: codex-operator runs A4, A6 and A8 through the launcher; the curator finalizes A5; an independent reviewer who is neither the author nor the operator does A7. A6 includes the builder's final run and the launcher's dry-run at the launch base. Then the owner gets the A9 question naming the registration and roster sha256s, the $15 cap with its trigger near $11.50, and the 2 h stop.

## Owner decisions

| ID | Issue | Question | Needed by |
|---|---|---|---|
| [D01](#d01) | #2930 | Run an API-only generic_v10 CHORUS pilot before any Claude Code shared-protocol run, although the owner's stated focus is native? | G3, decided first with D09, D10, D07 and D22 |
| [D02](#d02) | #3287 | Which comparator, metrics, cell roles and decision rules does the dated generic_v10 analysis plan preregister? | Before P2 is finalized, so before any spend |
| [D03](#d03) | #3336 | Which canary and pilot design reconciles #2930 (one reviewed canary), #2926 (CHORUS and AI_READI pilots, a floor before fan-out) and #3336/#2932 (1 project × 3 replicates against v8)? Do pilots count as replicates? | G3; final before P4 |
| [D04](#d04) | #2914 | Which CHORUS corpus path applies under generic_v10: A (add the DUA sources), B (keep the corpus and re-run the with-crate arm), or defer? | G3; before A4 if `source_manifest.yaml` is edited in this condition |
| [D05](#d05) | #2919 | Do the #2918 person-name grounding rule and the #2919 source_caveats absence/self-narration rule enter generic_v10? | Before A6 |
| [D06](#d06) | #1849 | Does every generic_v10 API registration add `display: summarized` to adaptive thinking, and do typed stages get a cache breakpoint? Neither can change after the first run. | G3 (display, and consent to unbilled count calls); breakpoint after A1b |
| [D07](#d07) | #1763 | Which allocation funds generic_v10 API runs, what stops each run, and how are attempts bounded, given that the code has no dollar cap? | G3 (before A9) |
| [D08](#d08) | #1849 | Should the prepared CBORG timeout and keepalive follow-up be sent? It has been unsent since 2026-09-16, and as an outbound message Claude never sends it without the owner's explicit yes. What gates multi-row rosters? | Yes or no this week; resolved before A16 |
| [D09](#d09) | #4758 | Which transport carries the first Claude Code shared-protocol run, and does the 2026-09-25 direct-arm pause cover #4354 runs? | G3 (this week), decided first with D10 |
| [D10](#d10) | #4761 | audit28: run it from a compatible checkout, or retire the v10z/audit_controls lineage (#2114)? | G3 (this week), decided first with D09 |
| [D11](#d11) | #4759 | Which runtime path do new native and direct registrations pin, now that the updater has pruned 2.1.272? As of 2026-10-09 17:08Z only 2.1.291 to 2.1.295 were installed in `~/.local/share/claude/versions`; the updater adds and prunes versions (2.1.296 arrived at 18:38Z). | N6 (second sitting); under D10 'run', its restore option at G3, for Z3 |
| [D12](#d12) | #4354 | Who develops, operates and reviews, now that the Codex session is developing #4354? | G3 |
| [D13](#d13) | #4019 | Which native registration choices apply before the first #4354 registration: #4019 (toolchain exposure), #4162 (launch form), #2714 (PR #2922 as a closure version) and #4445 (receipt origin)? | #4162 at G3, before N3 is finalized; the rest at N6 |
| [D14](#d14) | #2370 | Which launch parameters apply to subscription (direct-transport) runs: maximum starting seven-day utilization, overage handling, budget_guard_usd, deadline and effort? | N6 |
| [D15](#d15) | #1763 | Kids First under generic_v10: which protocol and order, and which floor? | G3; before A19-reg |
| [D16](#d16) | #4013 | Does the paper need a monolithic API baseline (prompt, full LinkML schema and documents in one call)? If so, how is it defined? | The need at G3; the definition before M2 |
| [D17](#d17) | #3972 | What is frozen from the first generic_v10 registration until each arm completes? | Before A4 |
| [D18](#d18) | #4354 | How long does #4354 offline acceptance continue under the unchanged 60 s owner budget and 900 s test deadline? | G3 |
| [D19](#d19) | #2921 | Does the CHORUS pilot's source review also seed audit-recall ground truth? | Before A12 starts |
| [D20](#d20) | #2926 | What rule sets the numeric receipt-coverage floor registered after the pilots? | The rule in P2; the value at A15 |
| [D21](#d21) | #2926 | How do production rosters gate and continue, given that one stop closes a label prefix for good? | G3; the rule merged in P2 before any spend |
| [D22](#d22) | #1763 | Do the v10z standing authorizations ('all evaluations of the CHORUS d4d', full-reservation debits) extend to generic_v10? | G3, before A6 |
| [D23](#d23) | #2930 | Who reviews and curates, and is there capacity? The repository binds reviews by hash, not by name, and does not say whether source reviewers must be human. | G3 |
| [D24](#d24) | #3343 | Which instrument defines the unsupported-claim and adverse-slot rates #2930 predicts, given that neither review instrument is calibrated? | G3; before P2 is final |
| [D25](#d25) | #3336 | On the direct vehicle, do per-project canaries count as replicates, and how are runs scheduled across weekly windows? | N6 |

### D01

**Issue:** #2930 · **Needed by:** G3, decided first with D09, D10, D07 and D22

**Question.** Run an API-only generic_v10 CHORUS pilot before any Claude Code shared-protocol run? The owner's stated focus since 2026-09-25 is native, and `docs/shared-generation-api-v1.md` ('Remaining scope') says no API-only result satisfies the cross-arm requirement.

**Options.**

- Yes, API first. The Claude Code cell follows when #4354 can run. The API record is the protocol's first empirical result, not the cross-arm comparison
- No: launch both arms together. That means no generic_v10 evidence until #4354 passes offline acceptance, which still fails at aa09dbbc6 (#4740, 2026-10-09T07:41Z)
- Yes, but only after D09 settles the Claude Code transport

**Recommendation.** Yes, API first. It is the only route with no engineering blocker at 15d053d1a, and it touches neither native lineage. A rule-level rejection found here becomes the next shared-generation version for both arms before any subscription or native spend. (This plan calls it "the next shared-generation version" because draft PR #4508 already uses the name `shared_generation_v2` for its opt-in routing evidence.)

Decide it together with D09 and D10. Under their recommended answers all of the plan's CBORG generation goes through the Messages-API runtime (claudecode_api, plus claudecode_agent_crate under #2914 B and the monolithic arm if D16 adds it), so 'API first' also means 'API only on CBORG' until the owner chooses otherwise.

**Unblocks.** P2–P4, A1–A22, M5 timing, and evidence that de-risks N9

### D02

**Issue:** #3287 · **Needed by:** Before P2 is finalized, so before any spend

**Question.** Which comparator, metrics, cell roles and decision rules does the dated generic_v10 analysis plan preregister?

**Options.**

- Comparator: the v8 API production fill 2026-09-04f/g (12 records, 3 per project; bundles byte-identical to today's for all four projects: CHORUS 9b2ef4b6, AI_READI d22b61a9, CM4AI 50037fc6, VOICE 9193c3cb), or the single v9 CHORUS canary (2026-09-12, no rubric score)
- Rubric: compare with the stored v8 ratings (older instruments, e.g. rubric10-semantic 1.1 and rubric20-semantic 1.0 on CHORUS 04f rep1), or re-rate v8 and v10 together under one current instrument (3.0, or 4.0 for rubric20)
- VOICE_PEDIATRIC ×1 or ×3, descriptive either way: no comparator on any arm, and its six source ids are a subset of VOICE's eleven
- n=3 decision rules: descriptive only, or a numeric tolerance preregistered per metric

**Recommendation.** Use the v8 fill as the primary comparator: prefix 04f for CHORUS and VOICE, 04g for AI_READI and CM4AI. Exclude the 04 and 04b–04e canaries and the invalid 04f AI_READI rep1. Keep v9 as a secondary single-point CHORUS reference. Claims are package-level only.

Primary metrics are deterministic:

- populated leaves;
- recall-target counts under cue sha256 768a26a3…;
- receipt coverage, with its denominator;
- #2932 structure;
- validation, duplicate keys and report findings.

Recall predictions are tested wherever v8 has targets (`notes/recall_target_baseline.md`):

- AI_READI: variables 20/13/20.
- CM4AI: lexical candidates 9/5/3.
- VOICE: variables 4/4/4, lineage entries 1/1/1, lexical candidates 3/0/1, tools with a version token 0/0/0 (9/8/8 is the plain tools column).
- CHORUS: cannot test variables or lexical candidates (0/0/0 each); its lineage is 1/1/0.

The unsupported-claim and adverse-slot predictions use the D24 instrument. They are measured in one shuffled, label-stripped comparison batch over v8 and v10 records (E2, #3280), separate from acceptance reviews. Rubric predictions stay secondary, from one joint re-rating (E5).

The n=3 rules are descriptive, with no 'v10 mean at or above the v8 minimum' test, unless the owner preregisters a tolerance per metric in P2.

VOICE_PEDIATRIC: ×1, descriptive, pooled with VOICE as one cluster. Choose ×3 only if the paper needs replicate variance on a near-duplicate corpus (2 more runs, no measured basis). Kids First: ×1, descriptive.

**Unblocks.** P1, P2, A18, E2, E5, E6

### D03

**Issue:** #3336 · **Needed by:** G3; final before P4

**Question.** Which canary and pilot design reconciles #2930 (one reviewed canary), #2926 (CHORUS and AI_READI pilots, a floor before fan-out) and #3336/#2932 (1 project × 3 replicates against v8)? Do pilots count as replicates?

**Options.**

- (a) CHORUS pilot accepted, then the AI_READI pilot, then a numeric floor, then CHORUS ×3 (the #3336/#2932 measurement and the CHORUS production cells), then the remaining projects
- (b) CHORUS 1×3 first, as three single pending-floor runs designated as pilots
- (c) Launch both pilots together
- (d) Count a pilot as replicate 1, registered before launch

**Recommendation.** Choose (a): it is the only option that puts one reviewed canary before any other spend (#2930), runs both of #2926's pilots before a floor and fan-out, and then gives #3336/#2932 their 1 × 3 measurement. Start the AI_READI pilot only after CHORUS passes blind source review: a rejection usually means a rule change, which would strand the AI_READI spend.

Pilots never count as replicates. `resolve_prompt` appends the raw receipt registration as `'Registration: {sha256, raw_json}'`, its floor, `registration_id`, limits and `context_limit_basis` included (`api_runner.py:1470-1472`; `receipt_completion.py:65-68`; `receipt_completion_policy.py:85-87`). That text is the base instruction of every ordinary phase from the full phase onward (`api_runner.py:978, 2784-2788`), and the completion turn carries the registration again (`receipt_completion.py:202, 246`). So a pending-floor pilot and a registered-floor replicate differ in model-facing content from their first call, and the pilots also train the floor. A `render-prompt` byte diff shows the difference: pending against registered.

How rosters gate and continue after the pilots is D21. Keep #3336 open as the record; #4345 (closed) and #4354 cite it.

**Unblocks.** P2, A6, A14–A18

### D04

**Issue:** #2914 · **Needed by:** G3; before A4 if `source_manifest.yaml` is edited in this condition

**Question.** Which CHORUS corpus path applies under generic_v10? #2914's path B keeps the corpus and re-runs the CHORUS with-crate (de_novo) arm under the current prompt (one canary, then 3 replicates); it is more than keeping bundle 9b2ef4b6.

**Options.**

- A: add the CHoRUS DUA page and the Data-Agreement docx as tier-2 sources, add a `bundle_hash_history` event and rebuild the chunks. This breaks bundle identity with every CHORUS comparator (9b2ef4b6) and needs its own canary
- B: keep the corpus (9b2ef4b6 stays comparable) and run a with-crate CHORUS canary plus 3 replicates under generic_v10 (A21–A22), about 4 billed runs. The inputs are on main: `CHORUS_preprocessed_with_crate.txt` (65,749 bytes) and its chunk manifest. `_shared_spec` admits the de_novo arm (method claudecode_agent_crate; `cli/api.py:24-26, 85-89`)
- Defer: keep the corpus, leave #2914 open and record the deferral on it. v10 CHORUS records then still leave doi, license, version, issued and citation empty, which is a corpus fact, not a generation defect

**Recommendation.** Never A in this condition. Choose B, scheduled after the CHORUS replicate gate is accepted (A16-acc). Choose Defer instead if the paper does not need a crate-versus-no-crate delta at the same prompt version. #2914's own argument is that the corpus exclusion pays off only if the with-crate arm is current.

Under B:

- The with-crate context is the CHORUS context unchanged (release null), so the two arms differ only in their bundles.
- The runs pass no `--canary-baseline`. `canary.baseline_for` searches only claudecode_agent, claudecode_api and claudecode_direct (`runs.py:77`), so a named baseline would match no crate record and read UNMEASURABLE.
- crate_only ('preferably' in #2914) is not planned.

Record the choice on #2914 now, and leave `source_manifest.yaml` unedited until the matrix ends (D17). No edit to it is invisible to the model, not even a YAML comment. Every shared-generation request (full phase onward, repair and typed stages) carries `generation_context`, whose source_manifest entry is a file pin `{path, sha256, bytes}` (`shared_generation.py:244-248, 455-457`; `api_runner.py:2835-2840, 5311-5313`; `typed_audit_runtime.py:139`). So any edit changes the pin's hash and size in model-facing text. `render-prompt` renders only `resolve_prompt` (`cli/api.py:495`), which omits that block, so its byte diff would wrongly report no change.

If the owner wants the choice in the manifest during this condition, the edit must be in the launch base (before A4, so before the first generic_v10 registration). The plan then states that the source-manifest pin's sha256 and size differ from the unedited file's, and `d4d download audit-bundles` and `d4d bundle chunk --check` show the bundles unchanged. `crate_manifest.yaml` is not pinned in a shared registration; an edit to it reaches the model only through a bundle, which `audit-bundles` would show.

**Unblocks.** A5 (the CHORUS context, release null), A6, A21–A22

### D05

**Issue:** #2919 · **Needed by:** Before A6

**Question.** Do the #2918 person-name grounding rule and the #2919 source_caveats absence/self-narration rule enter generic_v10?

**Options.**

- Defer both to the next shared-generation version. The eight v10 assets are hash-frozen (`shared_generation.py:29-36`, `ASSET_HASHES`)
- Add them now. That means a new shared-generation version, a pin rotation and a descriptor change before any run

**Recommendation.** Defer both: adding them now is a new shared-generation version, a pin rotation and a descriptor change before any run, and the source review counts these two classes separately and does not reject on them alone; the #1782, #1801, #1815, #1816 and #2924 classes do reject. An optional evaluation-only name-grounding check could measure #2918 without touching v10 inputs. If both pilots are rejected for the same rule-level cause, take both rules in at that next-version boundary.

**Unblocks.** A6 (assets frozen) and the A12 review protocol

### D06

**Issue:** #1849 · **Needed by:** G3 (display, and consent to unbilled count calls); breakpoint after A1b

**Question.** What does every generic_v10 API registration declare? (1) Thinking: keep `{type: adaptive}` with no display (`api_runner.py:1614`), or add `display: summarized`. (2) Whether typed stages get a cache breakpoint. Neither can change after the first generic_v10 run.

**Options.**

- Keep adaptive thinking without a display, as v8 and v9 did
- Add `display: summarized` before the first registration, scoped to generic_v10 so earlier conditions' declarations do not change
- Add a typed-stage cache breakpoint after the shared context, or leave it out of this condition; `typed_audit_runtime.py` sets no `cache_control`

**Recommendation.** Add the summarized display before the first registration. Reasons:

- Typed stages and receipt completion admit one delivery.
- The display is the only recorded mitigation for CBORG's 270 s `stream_timeout`. The 2026-09-26 probe streamed thinking from 7.4 s to 562.7 s, with a largest gap of 15.0 s, and ended at 605.1 s (`notes/matched_cborg_2026-09-14_v10d/.local_drafts/v10z_registration/transport_probe_2463/result.json`, gitignored local evidence, re-read on 2026-10-09).
- Each AI_READI typed worker carries at least 761,799 bytes of inputs.

Limits of the display:

- It is a transport mitigation only. It does not address an end_turn with an empty answer (risk 3); P2 records whether it changes that rate.
- The probe went through the native proxy, so passthrough on `api.cborg.lbl.gov` is unverified.
- The first `count_tokens` call carries the thinking dict and happens at receipt completion, after the full phase is billed (`receipt_completion.py:334-352`; `api_runner.py` makes no count call). So A1b checks, with the owner's consent and unbilled on the v10e precedent, that the route accepts display on `count_tokens` before A2 merges. A8 repeats the check.

Decide the cache breakpoint from A1/A1b: add it only if AI_READI's worst case exceeds D07's ceiling without it. Each change lands before A4 or not at all in this condition.

**Unblocks.** A1b, A2, A4, A6

### D07

**Issue:** #1763 · **Needed by:** G3 (before A9)

**Question.** Which allocation funds generic_v10 API runs, what stops each run, and how are attempts bounded? Neither `d4d api run` nor `d4d api batch` has a dollar cap, registrations carry token allowances only, and the batch prints tokens, not dollars.

**Options.**

- A new named generic_v10 API allocation of $100 for the pilot phase: CHORUS pilot $15 cap, one CHORUS contingency at its own $15 cap, AI_READI pilot $35 planning ceiling, one AI_READI contingency at no more than the AI_READI pilot's cap ($35). Production envelopes are set per roster from actuals
- $65 ($15 + $15 + $35). It has no line for the AI_READI contingency that A14-acc allows, so that contingency would need an allocation amendment, an owner word naming its amount, before its registration
- $60. It leaves $10 after the two pilots, which cannot fund a contingency at its $15 cap
- Re-point the remaining headroom of the matched-sequence ledger, the v10z chain (amounts withheld here; G3). The September additional $200 allocation is not a separate source: it bounded that sequence's API and native attempts and its evaluation attempts alike, and the chain later raised its cap on the same ledger
- Per-run approvals with no allocation

**Recommendation.** Option 1. Each run still needs its own word naming its registration's sha256 (for a roster, the roster's sha256 and every registration sha256 it lists) and its cap, the contingencies included.

Attempt bound: at most 2 billed attempts per registered cell (a pilot and one contingency; a replicate and one re-run under D21), then an owner review. This replaces 'per project per condition', which the plan's own CHORUS runs exceeded.

The AI_READI ceiling is provisional, and the AI_READI contingency line with it. If A1/A1b's worst case exceeds $35, re-plan before A14: fewer, larger workers, or the D06 breakpoint. A raised ceiling raises both AI_READI lines and needs an allocation amendment before A14-word.

Enforcement:

- The operator watches the A3b readout (settled dollars plus the pending call's worst case) and runs `d4d api stop`.
- The trigger is the cap minus the worst-case in-flight call, because a stop cannot recall a sent request and an interrupted stream may still bill (#1849). For CHORUS that call is about $3.45 (v9's full-phase input of 41,339 tokens plus a full 128k output), so the trigger is about $11.50 against a $15 cap.
- A2c (a between-run cumulative stop) lands before A4 (D17), so it is in place for every billed run.
- The matched-sequence ledger's remaining headroom (the v10z chain) is not assumed available (D22).

**Unblocks.** A9, A10c, A14–A22, Z4

### D08

**Issue:** #1849 · **Needed by:** Yes or no this week; resolved before A16

**Question.** Should the prepared CBORG timeout and keepalive follow-up be sent? It has been unsent since 2026-09-16, and as an outbound message Claude never sends it without the owner's explicit yes. What gates multi-row rosters?

**Options.**

- Send it now. Single-row runs go under a written risk acceptance. The first multi-row roster needs CBORG's answer or a written risk acceptance
- Hold it, and accept the risk in writing for everything
- Hold it, and block every roster until CBORG answers

**Recommendation.** Option 1. Sending early gives CBORG the most time to answer. #777's later comments tie stalls to request size and stream length, not time of day. The written risk acceptance must state the single-delivery estimate: at v8's per-call rate, 30–52% of runs with 4–8 single-delivery calls end terminally.

**Unblocks.** G5, A9 (the risk acceptance), A15, A16

### D09

**Issue:** #4758 · **Needed by:** G3 (this week), decided first with D10

**Question.** Which transport carries the first Claude Code shared-protocol run, and does the 2026-09-25 direct-arm pause cover #4354 runs?

**Options.**

- (a) Lift or scope the pause for #4354 runs. The cells are claudecode_direct on the claude.ai subscription
- (b) Build a CBORG claudecode_agent transport for the shared protocol: route and auth admission, proxy ledger admission, reservation and settlement, display substitution, a probe variant and a budget source. Only this gives a same-provider API-versus-native contrast
- (c) Defer. generic_v10 is API-only, and the v6 agentic arm stays the latest CBORG-native baseline

**Recommendation.** Choose (a) for the first Claude Code canary, and label every such cell the direct arm, not native. In the owner's 2026-09-25 vocabulary, native means the CBORG claudecode_agent arm, and the direct arm is 'never called native'.

Preregister the contrast as runtime, provider, transport and effort together. Effort cannot be matched:

- native and direct registrations require an explicit literal and always pass `--effort` (`native_execution_registration.py:92-94, 153`);
- the API route's effort is the provider default with no ladder (`.github/workflows/d4d_assistant_deterministic.config:19-20`; `shared_generation.py:409`).

So effort is a fixed confound. N6 chooses the level and justifies it.

Stated plainly: with (a) and D10 'retire', this plan runs no CBORG-native generation. That departs from 'focus is native until everything is validated and working' (2026-09-25), and the owner must confirm the departure. To keep CBORG native in scope, choose (b) (N12, built on the same adapter) and/or D10 'run'. Under (c), native engineering stops after G1a and G1b.

Keep the generic_v9 direct arm paused and superseded (R1).

**Unblocks.** N3–N12 scope, N4a's probe environment, N5, R1

### D10

**Issue:** #4761 · **Needed by:** G3 (this week), decided first with D09

**Question.** audit28: run it from a compatible checkout, or retire the v10z/audit_controls lineage (#2114)?

**Options.**

- Retire now. It is free and releases PRs #2910, #2922 and #4387 and issues #2909, #3879, #3785 and #3856
- Run audit28 once, from compatible checkout 3de6cd7d9, with 2.1.272 at its registered path, the LBL network, the pinned CA and a $60 per-job cap. Retirement is pre-committed on a stop or rejection, and Phase 4 (#2114) is still unbuilt
- Keep holding. The hold has no end date: the registered runtime is gone and main fails the identity check

**Recommendation.** Retire: an accepted audit28 would yield one composite generic_v9 CHORUS record that still needs Phase 4 and cannot be compared with any generic_v10 cell, and 0 of 26 billed audits were accepted.

Costs, grouped on 2026-10-09 from the local ledger files (amounts withheld here; G3):

- the v10z lineage: generation d4810ca2 plus 26 billed audits;
- the matched native sequence: 9 generations plus 26 audits;
- the shared ledger, which also holds the 15 CHORUS API attempts and the transport probe.

Retiring together with D09(a) removes all CBORG-native generation from the plan (see D09).

**Unblocks.** Z1, Z2, N6b (#2714), the D07 budget question; Z3–Z7 only if 'run'

### D11

**Issue:** #4759 · **Needed by:** N6 (second sitting); under D10 'run', its restore option at G3, for Z3

**Question.** Which runtime path do new native and direct registrations pin, now that the updater has pruned 2.1.272? As of 2026-10-09 17:08Z only 2.1.291 to 2.1.295 were installed in `~/.local/share/claude/versions`; the updater adds and prunes versions (2.1.296 arrived at 18:38Z).

**Options.**

- Copy (never move) the retained 2.1.272 bytes to a durable path outside the updater's directory and pin that path
- Re-register on a current runtime as a recorded instrument boundary, re-validating the command policy, the permission probe and the display
- Restore 2.1.272 at its registered updater path; needed only if D10 is 'run'

**Recommendation.** Use a durable copy of 2.1.272 for new registrations:

1. `cp` (never `mv`) the retained file.
2. `chmod u+x` on the copy only. The retained file is mode 0600, 210,702,192 bytes.
3. Verify sha256 195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75 (re-hashed on 2026-10-09) and the code signature.
4. Only then run `--version`.

The command policy, the recorder probe and the display were validated on this version. Restore it at the updater path only if D10 is 'run', and verify the hash at launch.

**Unblocks.** N4b, N7, Z3

### D12

**Issue:** #4354 · **Needed by:** G3

**Question.** Who develops, operates and reviews? The 2026-09-25 split was 'Claude develops, Codex operates'. The Codex session has been developing #4354 since 2026-10-03 and, per the maintainer (a private report, not in the repository), is actively working #4740 and #4354 now.

**Options.**

- Restore the split for new work: Codex finishes its in-flight offline loop (N1–N2) on its own branches; maintainer-dev delivers #4354 from a separately cut branch and builds launch inputs; Codex operates every registration, ledger and launch; an independent reviewer reviews each registration
- Codex develops #4354 through delivery and also operates native runs, with an independent reviewer bound to each registration
- Move all #4354 work to maintainer-dev now

**Recommendation.** Option 1, with one constraint from the maintainer's private report: the plan edits none of the Codex session's branches. That covers `review/4354-offline-acceptance`, `fix/4537-trace-single-decode` (PR #4659's head, 38fb11d5d) and every `/private/tmp` branch.

For each registration, the reviewer is neither its author nor its operator: a Claude reviewer plus a Codex CLI pass run directly, per the maintainer's private session notes.

One overlap remains: Codex will operate an adapter it largely wrote. That review covers it. The owner confirms the split or reassigns it, and G6 records Codex's acknowledgment.

**Unblocks.** An owner for every step; N3's branch rule

### D13

**Issue:** #4019 · **Needed by:** #4162 at G3, before N3 is finalized; the rest at N6

**Question.** Which native registration choices apply before the first #4354 registration: #4019 (toolchain exposure), #4162 (launch form), #2714 (PR #2922 as a closure version) and #4445 (receipt origin)?

**Options.**

- #4019: narrow `toolchain()` to the generation agents, or neutralize the exposed evaluation agents
- #4162: literal flags, a recorded argv, or accept 'not shown' for `--safe-mode`
- #2714: merge PR #2922 as a closure version, or decline it and accept the latent pid-reuse SIGKILL
- #4445: measure receipt origin on the final transcript, or not

**Recommendation.**

- #4019: narrow the toolchain. Study-named evaluation agents are study content, which is kept out of generation inputs.
- #4162: use literal flags with a recorded argv (decided at G3, because N3 sets the launch form).
- #2714: decide PR #2922 at N6b. N7 waits only on that answer, never on Z2, which runs only if D10 is 'retire'. Under 'run', N7 waits through N6b for audit28 to close (Z5).
- #4445: measure receipt origin, because native acceptance relies on it.

**Unblocks.** N3 (launch form), N6b, N7

### D14

**Issue:** #2370 · **Needed by:** N6

**Question.** Which launch parameters apply to subscription (direct-transport) runs: maximum starting seven-day utilization, overage handling, `budget_guard_usd`, deadline and effort?

**Options.**

- Maximum starting utilization of 0.80 or below. The v2 retry used about 0.02 of the window (0.94 to 0.96); v3 used at least 0.04 before blocking_limit at 1.0
- Overage: the owner states whether extra usage is enabled. Either keep it disabled during canaries, or implement #2370's stop on `isUsingOverage` before N7 (#2370: 'a run that enters overage is not stopped')
- A $90 guard and a 21,600 s deadline, following the v2-retry and v3 precedent
- Effort: an explicit Claude Code level (max on prior direct canaries), recorded as a fixed confound against the API arm's provider default

**Recommendation.**

- Utilization: set a 0.80 threshold, checked on claude.ai before each word, and launch soon after a weekly reset.
- Overage: implement the `isUsingOverage` stop in N4b, or keep extra usage disabled. Until one holds, a subscription run can bill real dollars up to the $90 guard.
- Guard and deadline: $90 and 21,600 s.
- Effort: chosen and justified at N6 as a fixed, preregistered confound. 'Match the API arm' cannot be implemented (D09).

**Unblocks.** N4b, N5, N7, N8

### D15

**Issue:** #1763 · **Needed by:** G3; before A19-reg

**Question.** Kids First under generic_v10: which protocol and order, and which floor?

**Options.**

- API first, after the CHORUS pilot is accepted and the AI_READI pilot has sized the allowances. This departs from the v10z native-first order
- Native first: wait for an accepted Claude Code shared-protocol CHORUS canary
- Wait for accepted CHORUS pairs on both arms
- Floor: the registered numeric floor, or a pending floor

**Recommendation.** API first, after A14-acc and once A15 exists.

The floor matters for verdicts:

- Under a registered floor, `d4d api batch` gates every run against absolute floors.
- Under a pending floor with no baseline it computes no verdict at all (`cli/api.py:833-841, 914-927`), and no arm has a Kids First baseline.

Record the order change on #1763. Keep one record per arm, descriptive only. Size the cap from AI_READI actuals: the Kids First bundle is 541,184 bytes, about AI_READI's 542,513, and v10r's $15 cap predates the typed audit. A19-reg re-validates the frozen chunk manifest, because A4's study-bundle gates do not cover it.

**Unblocks.** A19 and the Kids First part of N11

### D16

**Issue:** #4013 · **Needed by:** The need at G3; the definition before M2

**Question.** Does the paper need a monolithic API baseline (prompt, full LinkML schema and documents in one call)? If so, how is it defined?

**Options.**

- Not needed
- Register monolithic_v1 with its own method directory: one call, pinned prompts, the merged 3.0.0 schema (1,442,513 bytes), opus-5 via CBORG, adaptive thinking, a 128k cap, no repair turn
- Prompt: the legacy concatenated prompts as written (fidelity), or a prompt derived from the v10 rules (isolation)
- Route: CBORG, or the Anthropic API directly
- Rename the current API arm instead

**Recommendation.** Decide the need first. The 2026-09-30 statement that results are needed is in a private message (not in the repository).

If it is needed:

- Register it as its own condition; do not rename the existing arm.
- Use the fidelity prompt, recording the mechanical changes: model, temperature omitted, 128k cap.
- Run on CBORG opus-5 for comparability, with no repair turn.
- Schedule its canary after A10 has exercised the D06 runtime on the same route.

M5 (CHORUS) and M6 (AI_READI) each get a registration review and an owner word naming the hash and cap. M6 runs only after the CHORUS monolithic record is accepted and the route's input window is confirmed (M3).

**Unblocks.** M1–M6

### D17

**Issue:** #3972 · **Needed by:** Before A4

**Question.** What is frozen from the first generic_v10 registration until each arm completes?

**Options.**

- Freeze, unless v1 byte parity is shown and the remaining runs re-register: no schema release (#3972, #3124), no merge of draft PR #4508 (#4489), no #2914 path A, no source-manifest edit (#3414), no preprocessing change (#2934), no API runtime change, no #4354 merge that touches the API path
- Land the schema releases before the CHORUS pilot
- No freeze

**Recommendation.** Freeze: every registration pins the full and core schema closures, the bundle, the chunk manifest and the source manifest, so a change mid-matrix splits replicates across inputs. Decide #3414 before A4 or hold it, because its fix edits the manifest that every registration pins.

Also inside the freeze:

- #4766's report-totals checker may land only report-only, in the A2 runtime PR before A4, or after the matrix. Until then A11 checks totals offline.
- A2c lands before A4. A D21(c) batch change lands before A4, or, if the owner chooses it at A15, by the advance procedure below.
- M2's monolithic runner path lands in the launch base (before A4) or after the API matrix completes (M2).
- #4765's merge and fitness work do not touch generic_v10 inputs.

The launch worktree stays at the launch base for the whole matrix. Merged data PRs make that a requirement: run outputs under `data/d4d_concatenated/claudecode_api*/` are untracked in the launch worktree and not gitignored (apart from `*_api_progress.json` and `*.log`), and git refuses to fast-forward over untracked files even when they are byte-identical ('untracked working tree files would be overwritten by merge'; reproduced on git 2.50.1 in a scratch repository).

If a post-A4 change is unavoidable, the operator advances only between stages, with no run live: `d4d api status` shows no live sweep, and `pgrep -fl "d4d api run|'api', 'run'|data_sheets_schema[.]cli api run"` prints nothing (exit status 1), because `d4d api status` sees only batch locks (`cli/api.py:1070`) and `d4d api run` takes none. The pattern covers the venv script (`…/bin/d4d api run`), a `poetry run` launch, which carries its arguments inside `python -c … sys.argv = ['…/bin/d4d', 'api', 'run', …]`, and `python -m data_sheets_schema.cli api run`. A name match such as `pgrep -f "d4d api run"` misses the last two (`cli/api.py:1061-1066`, #513). On macOS pgrep never matches itself or the shell that runs it, where a `ps | grep` pipeline matches its own grep (checked on 2026-10-09 with three harmless stand-in processes).

1. For every untracked output the target commit tracks, confirm that `git hash-object` equals the tracked blob; stop on any mismatch.
2. Move those files, never delete them, to a dated holding directory outside the worktree.
3. `git merge --ff-only` to the target.
4. Confirm the checked-out files hash identically to the held copies.
5. Re-run A4's gates, reading 'HEAD equals the base' as HEAD equal to the target commit, and run the #795 check directly: `run_guard.runs_on_other_refs` over every label the matrix has written must return nothing. The batch's `--dry-run` returns before that guard (`cli/api.py:804, 818-819`), so it cannot stand in for it.
6. Write a parity statement naming the target commit: the rendered requests are unchanged apart from label and date, or the remaining cells re-register. From then on, A4's 'HEAD equals the base' and A8's 'HEAD equal to the launch base' mean HEAD equal to that target commit.
7. If the advance changed any code the runner or `d4d api batch` executes, run one diagnostic single-row CHORUS roster at the advanced base through the launcher before the next multi-row roster. It gets its own prefix, registration, review and word, and is funded by an allocation line or amendment named in that word (D07). Accept it by A11–A13. It is not a replicate (D03).

Keep the held copies until step 5 passes.

**Unblocks.** A4 onward

### D18

**Issue:** #4354 · **Needed by:** G3

**Question.** How long does #4354 offline acceptance continue under the unchanged 60 s owner budget and 900 s test deadline?

**Options.**

- Continue with no end date
- Set a time-box with an owner review date; at its end, continue, re-register the budgets with a stated runtime rationale, or defer
- Re-register the budgets now

**Recommendation.** Set a time-box with a date the owner chooses; two weeks is proposed.

Latest state, from #4740 at 2026-10-09T07:18Z and 07:41Z (still its newest comments as of 2026-10-09 17:08Z):

- At local aa09dbbc6, with #4764's YAML fast path applied, the plain receipt-process test still fails with 'native owner coordination deadline elapsed'.
- The registered receipt child now exits 0 and its output is captured, but the parent journal has no phase-1 seal before the unchanged 60 s deadline.
- A warm-JSON duplicate-key candidate missed its preregistered thresholds (4/6 wall pairs and a 0.787% CPU saving, against 5/6 and 3%) and was deferred.

Next target: parent result settlement and phase-1 sealing, then end-to-end acceptance with #4764 applied. The API route does not wait on this.

**Unblocks.** A stop-loss for N1–N2

### D19

**Issue:** #2921 · **Needed by:** Before A12 starts

**Question.** Does the CHORUS pilot's source review also seed audit-recall ground truth?

**Options.**

- Yes. A second, blind reviewer writes observations pinned to the original_full sha256 before anyone reads the audit, and the owner signs off HIT_RULE
- No. Audit recall stays unmeasured for the pilots

**Recommendation.** Yes, if D23 names a second blind reviewer before A12; otherwise no. It must not delay A12. Once anyone has read the audit, the blind order cannot be recovered.

**Unblocks.** The #2921 measurement

### D20

**Issue:** #2926 · **Needed by:** The rule in P2; the value at A15

**Question.** What rule sets the numeric receipt-coverage floor registered after the pilots?

**Options.**

- The lower pilot's post-turn coverage fraction, rounded down to the nearest 0.05
- The lower fraction minus a margin stated in advance
- A fixed fraction chosen now. #2926 rejects this: the floor should come 'from the canary's post-turn distribution, not a guess'

**Recommendation.** Commit the rule in P2 before the pilots run, and register the value at A15. Rounding down to the nearest 0.05 is the proposed default. Two pilots are a thin basis, and #2926 notes that a 0.6 floor would fail 8 of the 12 v8 records.

A floor failure stops the roster without discarding records. Within `d4d api batch` nothing continues a stopped roster (`cli/api.py:784-785, 835-841`). `d4d api run` is not a continuation route: it runs any single row's registration with no floor verdict, canary block, run lock or #795 guard, and `d4d api status` and `d4d api stop` cannot see it (`cli/api.py:589-672, 827, 1070, 1100`). Every generic_v10 launch, continuations included, goes through `d4d api batch` with a roster, so continuation follows D21.

**Unblocks.** A15–A22

### D21

**Issue:** #2926 · **Needed by:** G3; the rule merged in P2 before any spend

**Question.** How do production rosters gate and continue? Under a registered floor every `d4d api batch` run is gated with no bypass (`cli/api.py:784-785, 835-841`; `d4d api run` is excluded by D20), and `--canary-baseline` adds v8's per-project worst on seven defect metrics. Rosters always start at rep1, and a re-run re-derives a finished run's verdict (`cli/api.py:760, 386-392, 917-955`), so one stop closes the prefix for good.

**Options.**

- (a) `--canary-baseline` on every production roster: each run must match v8's per-project worst on all seven metrics. Recomputed on 2026-10-09 from the v8 04f/04g records: report findings CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0; British spellings VOICE 2; pair errors, ungrounded identifiers, resolver URLs, organisational fragments and undeclared prefixes 0 everywhere
- (b) Absolute floors only, with no `--canary-baseline`: the registered coverage floor, the receipt defect floors and duplicate keys gate every run, and a blind check stops the roster as UNMEASURABLE. The seven metrics are reported but never regress without a bar (`canary.py` verdict); v8 is compared offline with a report-only `d4d api verdict`, and in E6
- (c) Build a reviewed adjudicated-continue path in `d4d api batch` before A16. It lands before A4, or after A15 by D17's advance procedure (untracked outputs moved aside, fast-forward, #795 re-check, parity statement, step-7 canary)
- Continuation after any stop: (i) re-run the roster, which stops again and is not viable; or (ii) close the roster and run the remaining cells under a new prefix with new registrations, a new roster and an owner word

**Recommendation.** (b) for production rosters, plus continuation (ii), preregistered in P2:

- a stopped label is never re-run;
- the owner classifies the stop as transport, rule-level or instrument;
- remaining cells run under a new date-letter prefix with new registrations, a new roster, a review and an owner word naming the new roster's sha256, every registration sha256 it lists, and the cap;
- every attempt is counted, within D07's per-cell bound;
- a cell split across prefixes cannot be grouped by `d4d runs select --config` (A20, G4 gap).

Pilots keep `--canary-baseline`: they stop anyway, and the canary block records the comparison.

Trigger: if the pilots show any terminal single-delivery failure, the owner decides at A15 between (b), building (c) before A16 (landed by D17's advance procedure, including its step-7 canary), and moving to the next shared-generation version with one recorded retry, which is a condition boundary for both arms. Choosing the next shared-generation version ends this generic_v10 API matrix: that version needs its own analysis-plan amendment, its code and pin PR, and new pilots in the A6–A15 pattern before any roster, and A16-reg follows only (b) or (c).

(a) is not recommended. It turns a measured outcome into a stopping rule, against bars that are mostly zero for a different package.

**Unblocks.** P2 item 9, A15–A22, A20

### D22

**Issue:** #1763 · **Needed by:** G3, before A6

**Question.** Do the v10z standing authorizations extend to generic_v10? The standing authorization in `notes/matched_cborg_2026-09-18_v10z/workload.public.json` reads 'you are approved to run CHORUS canaries until they suceed. then you are approved to run all evaluations of the CHORUS d4d', funded with 'no further approval' within the amended budget. On 2026-09-25 the owner also granted standing authority to debit an unconfirmed charge at its full reservation. The Codex operator acts on these.

**Options.**

- They do not extend. They cover only the v10z/audit_controls lineage: not generic_v10 records, not their evaluation, and not any generic_v10 allocation, whatever D10 decides
- They extend to generic_v10 CHORUS records, so an accepted A13 record would trigger paid evaluations without a word
- Leave it unstated

**Recommendation.** Option 1, and whatever D10 decides, the owner withdraws the v10z standing generation, evaluation and full-reservation-debit authorizations at G3. maintainer-dev records the ruling and the withdrawal on #1763 and #4761, quoting the owner, with no at-mentions. The Codex operator acknowledges both in writing before any generic_v10 registration, on either arm (G6). Every generic_v10 generation and evaluation then needs its own word. Under D10 'run', Z4's word is the only authority for one audit28 attempt, and every later Phase 4 run, evaluation or Kids First run needs its own registration, review and word. Under 'retire', Z1 records the G3 withdrawal; the withdrawal itself does not wait for Z1.

**Unblocks.** G6, A6, E5

### D23

**Issue:** #2930 · **Needed by:** G3

**Question.** Who reviews and curates, and is there capacity? The repository binds reviews by hash, not by name, and does not say whether source reviewers must be human.

**Options.**

- Named humans for curation and source review
- Model reviewers: a fresh session that neither generated nor operated, or a cross-family rater (#3328)
- Mixed: a human curator; a Claude reviewer plus a Codex CLI pass for registrations and code; named source reviewers for acceptance and for the comparison batch

**Recommendation.** Mixed (option 3). The owner gives names at G3 for:

- a curator for the A5, A19 and A21 contexts;
- the registration and code reviewer pair;
- acceptance source reviewers, never the generating session;
- comparison-batch reviewers for E2, blind and label-stripped (#3280);
- a second blind reviewer if D19 is yes.

Capacity: about 16 API acceptance reviews under the recommended options (2 pilots, 3 CHORUS gate, 9 production, 1 VOICE_PEDIATRIC, 1 Kids First). Add 2 more if VOICE_PEDIATRIC is ×3, 4 under #2914 B, and one per contingency or D21 re-run. With 24 comparison-batch reviews (12 v8 plus 12 v10 confirmatory) that is about 40–46. The direct arm adds one acceptance review per run, 15–21 (D25), and the monolithic arm 2 (M5, M6): about 57–69 in all, plus contingencies and re-runs.

Schedule: each stage's acceptance review finishes before the next stage's word; E2 starts after A17-acc.

**Unblocks.** A5, A7, A12, E2, D19

### D24

**Issue:** #3343 · **Needed by:** G3; before P2 is final

**Question.** Which instrument defines the 'unsupported-claim rate' and 'adverse-slot rate' that #2930 predicts 'in the review pass'? The d4d-review-record pass did not meet its calibration criterion (#835, closed). Support judge v2 is uncalibrated (#3342 and #3343 open); its calibration is paid and needs owner decisions on controls, model, route, limits, prices and acceptance.

**Options.**

- The blind comparison-batch source review (E2): per record, counts of the rejecting classes (#1782 plans-as-current and scope, #1801/#2924 roster roles, #1815 attribution, #1816 qualifiers and headers) over a stated denominator; the support judge is excluded from preregistered predictions
- Calibrate the support judge first (#3343) and use it as the instrument
- Option 1 as primary, with the support judge as a secondary analysis after calibration

**Recommendation.** Option 1 now. Move to option 3 only if the owner later funds #3343's calibration under its own registration and word. P2 records the deviation from #2930's wording ('in the review pass') and the reason (#835).

**Unblocks.** P2, E2, E6

### D25

**Issue:** #3336 · **Needed by:** N6

**Question.** On the Claude Code (direct) vehicle, do per-project canaries count as replicates, and how are runs scheduled across weekly windows?

**Options.**

- No: N9, CHORUS ×3, a canary plus 3 replicates for each of AI_READI, CM4AI and VOICE, and one run each for VOICE_PEDIATRIC (D02's ×1) and Kids First: 18 runs, or 21 with VOICE_PEDIATRIC ×3 (a canary plus 3)
- Yes, for canaries registered under the A15 floor before launch (the 2026-09-13 cohort note allows this for a CHORUS canary; extending it to the other projects is part of this decision), when the N7 review shows by byte diff that the canary's model-facing inputs equal its replicates', apart from label and opaque ids. That includes the adapter's native receipt floor (`native_shared_contract.py:776-789` at 0125eebbc). A pending-floor N9 fails that test and never counts: 15 runs, or 17 with VOICE_PEDIATRIC ×3

**Recommendation.** Decide at N6 using D03's model-facing test: option 2 only when the diff holds, otherwise option 1. Use D02's VOICE_PEDIATRIC count on both arms (×1 recommended).

N9 counts as CHORUS replicate 1 only if N7 registered the A15 floor and the diff holds. N7 does not wait for A15, so the counts above assume it does not count (D03). When N7 does register the A15 floor, it also builds an unlaunched draft CHORUS replicate registration, which N7-rev diffs against the canary; N11-rev repeats the diff against the real replicate registrations before N9 is counted.

Size the weekly schedule from N9's measured seven-day utilization per run before committing to N11. Prior direct runs moved it about 0.02 (v2 retry) and at least 0.04 (v3).

**Unblocks.** N5, N11

## Tracks

Who: **owner** (decisions and launch words), **maintainer-dev** (development in the maintainer's Claude sessions), **codex-operator** (the Codex session that operates registrations, ledgers and launches), **independent-reviewer**, **curator**. "The maintainer" is the person who requested this plan and runs the maintainer-dev sessions; in this plan that person is also the owner. "The maintainer's report" and "the maintainer's notes" are that person's private messages and session notes, not in the repository.

### G. This week, $0: protect unpublished work, file gaps, decide

Protect the unpublished native work today, file the untracked gaps, and settle in one owner sitting the decisions every route shares, before any spend. Every other track depends on G3.

#### G0 · owner · owner decision

Tell the Codex session to publish now (#4763). Each of the seven branches is pushed to its existing name on GitHub, at its head as it stands at push time, with no PR and no merge. Its #4740 comments record a no-partial-chain-push practice; this instruction overrides that for durability only. Alongside it, the owner agrees with the Codex session a window, outside its CPU-timing windows, for G1a's bundling.

The branches (heads re-checked at 2026-10-09 17:08Z; none published):

- `fix/4728-native-owner-helper-integration`: f00bcb5df, and still moving. It was at aa09dbbc6 at the 2026-10-09T08:58Z re-check (aa09dbbc6's parent is the 7a17202f7 that #4763 lists) and is now 12 commits past it, so G1a and G1b take the head as it stands;
- `fix/4687-native-owner-snapshot`: 6ce623c06;
- `work/4385-figure-consumer-integration`: 49477bab9;
- `review/three-feature-integration`: 6134acdc9;
- `fix/4728-native-owner-public-integration`: a0d57338e;
- `fix/4728-native-owner-adapter-capture`: 7e7e155f0;
- `fix/4687-native-clock-domain`: 6fa966ba7.

* **Depends on:** none
* **Cost:** Owner time; $0
* **Gate:** Instruction recorded on #4763 in this repository, with no at-mentions
* **Issues:** #4763, #4740

#### G1a · maintainer-dev · publish only

Today, in the window agreed at G0 outside the Codex session's CPU-timing windows, and changing no clone's refs, no branch and none of the Codex session's files: `git bundle` each of the seven branches, at its head when bundled, into a new durable directory under `d4d-executions` (never `/private/tmp`).

`git bundle` runs `pack-objects` inside each clone, and the Codex session is taking preregistered wall and CPU benchmark pairs for #4740. So agree the window with the Codex session through the owner (alongside G0), bundle one clone at a time under `nice`, stop if a timing pair starts, and skip any branch G1b has already pushed.

Re-checked at 2026-10-09T08:58Z and again at 2026-10-09T17:08Z (38 counted at about 2026-10-09T07:50Z): exactly these seven of the 40 top-level git checkouts under `/private/tmp/d4d-goal-resume-5sVO4ntI` have heads absent from the primary checkout's object store, and none of the seven resolves through the GitHub commits API. (Git repositories in the pytest temporary directories beside them, such as `support-rubric-tests-01-tmp/` and `pytest-evaluation-final/`, are test fixtures, not branches, and are excluded, as is the `native-recovery/source` repository, whose head 0125eebbc is on origin.) 4366dc20 is already lost.

* **Depends on:** G0 (the agreed window)
* **Cost:** $0 (local copy; no provider call)
* **Gate:** `git bundle verify` passes for each file, each bundle contains the head SHA recorded when it was made, and the recorded start and end times fall inside the window agreed at G0, outside the Codex session's timing windows
* **Issues:** #4763, #4740

#### G1b · codex-operator · publish only

Push each branch's head as it stands at push time, not a fixed SHA. Cite the branches on #4728, #4687 and #4385. No code changes. Recheck reachability at push time.

* **Depends on:** G0
* **Cost:** $0
* **Gate:** Each head in #4763's table, and each head as pushed, resolves through the GitHub commits API and is reachable from its pushed branch, as #4763's acceptance requires (the terminal-source head descends from aa09dbbc6, whose parent is the table's 7a17202f7). 4366dc20, which #4763 records as unrecoverable, is not part of the gate. A zero exit from push is not enough. A re-sweep of every top-level git checkout under `/private/tmp/d4d-goal-resume-5sVO4ntI` finds no head absent from origin
* **Issues:** #4763, #4728, #4687, #4385

#### G2 · maintainer-dev · read only audit

From this plan, write a one-page table for sitting 1: each decision's question, options, recommendation and what it unblocks. Mark the three to take first:

- D09 with D10 (the departure from 'focus is native');
- D01 with D07 and D22;
- D08.

Read-only.

* **Depends on:** none
* **Cost:** $0
* **Gate:** Every figure names its source file, record or issue
* **Issues:** #2930, #3287, #3336, #4758, #4761, #1763

#### G3 · owner · owner decision

Owner sitting 1, once the G2 table exists. Decide in this order:

1. D09 and D10.
2. D01, D07, D22 (including the withdrawal of the v10z standing authorizations, whatever D10 decides) and D08.
3. D02–D06, D12, D13 (#4162 only), D15, whether D16 is needed, D17–D21, D23 and D24. D06's cache-breakpoint half may wait for A1b. If D10 is 'run', also D11's restore option, for Z3.

Also give consent for the unbilled `count_tokens` calls in A1b and A8.

On 2026-10-09 the owner decided to keep the CBORG chain amounts (How it was made) out of this note, and Z1's note gives none either. That keeps the note consistent with the v10z public records; it does not make the amounts private. Before this plan, issue and pull-request text and files on main had already given most of them, directly or by subtraction: for example the #1763 comment of 2026-09-16, the #2463 comment of 2026-09-26, #2278 (one audit's cost), #2468 (the cap's history) and three notes on main (`notes/native_audit_continuation_plan_2026-09-18.md`, `notes/native_audit_retry_2026-09-21.md`, `notes/chorus_audit26_controller_review_2026-09-24.md`). These are examples, not an inventory. This PR's first pushed commit added some figures that no earlier source gives, and its round-1 commit, the parent of the current head, still carries the audits' share of the matched native sequence that round 2 removed (#4804). The branch was rewritten on 2026-10-09 at 18:25Z, but as of 2026-10-09 21:02Z GitHub still served both commits by SHA, under this repository and each of its four public forks. Rewriting the branch again or opening a fresh PR withdraws nothing, and the round-1 commit stays reachable through this PR whatever the merge method; a merge commit or a rebase merge would also put it into main's history, and a squash merge would not. #4800 carries none of the amounts: its body was edited at 18:25Z, and its first revision was deleted from the edit history at 18:47Z.

Retracting the earlier copies is a separate owner decision, not part of this plan. Editing a comment or body withdraws nothing by itself: anyone who can read the repository can open its edit history, so each earlier revision must then be deleted from it, as was done for #4800, and a renamed title stays in the issue's timeline. A retraction would therefore start from a full search of issue and pull-request titles, bodies, comments and edit histories, and of files on main. The three notes on main cannot be withdrawn: as of 2026-10-09 a public fork made on 2026-09-29 carries identical copies on its own main branch, so even rewriting main would not remove them. GitHub's documentation says Support does not remove non-sensitive data and that a purge dereferences or deletes the affected pull requests, so a purge request may be refused or may remove this PR. Copies already fetched cannot be recalled.

maintainer-dev records each answer on its issue, quoting the owner, as comments on those issues in this repository, with no at-mentions. No launch word is given here: each billed run later gets its own word, in answer to a question naming its registration's sha256 (for a roster, the roster's sha256 and every registration sha256 it lists) and its cap.

* **Depends on:** G2
* **Cost:** Owner time; $0
* **Gate:** Each decision answered, or deferred to a stated date, and visible on its issue
* **Issues:** #4758, #4761, #2930, #1763, #1849, #3287, #3336, #2914, #2919, #4354, #3972, #2921, #2926, #4013, #3343, #4162, #4759

#### G4 · maintainer-dev · issue filing

File the gaps no open issue tracks (searched 2026-10-09):

1. The API-path thinking display (D06).
2. A typed-stage cache breakpoint.
3. A between-run dollar stop in `d4d api batch`, and dollar output (the batch prints only token totals).
4. The pilot acceptance rows and the acceptance-record format.
5. An evaluation route that reads `shared_generation_registration_v1`, which the matched evaluation controller cannot.
6. Recording the returned model identity per call (CBORG sends `x-litellm-model-id`).
7. Model-facing absolute caller paths (`shared_generation.py:244-248, 440-459`), as a design question for the next shared-generation version.
8. For the next shared-generation version: one recorded malformed-response retry and one transport retry for single-delivery stages (today exactly `{1, 0, 0}`; `shared_generation.py:226-228`).
9. `d4d runs select` cannot group a cell split across prefixes (D21).
10. An offline typed-sizing mode, if A1 needs one.
11. `d4d runs select` does not read acceptance, so canonical marks are kept to accepted replicates only by procedure (A20; risk 23).

Also extend #4762 with the v6 drift for CM4AI and VOICE: rep1 bundles 1dfd34e5 and dcd71717 against today's 50037fc6 and 9193c3cb. Sanitize at-sign tokens before posting.

* **Depends on:** none
* **Cost:** $0
* **Gate:** Each issue cites file:line evidence; no at-mentions
* **Issues:** #4762, #1849, #2930, #4345 (closed 2026-10-05; context), #931, #2926

#### G5 · owner · outbound message

#1849: if D08 is yes, the owner sends the prepared CBORG timeout and keepalive follow-up, or Claude sends it after the owner's explicit yes to a question naming the recipient, the channel and the exact text. Claude never sends it unasked.

Whatever D08 decides, the owner also records in writing that the transport risk is accepted for single-row runs, stating the single-delivery estimate: at v8's per-call rate, 30–52% of runs with 4–8 single-delivery calls end terminally.

* **Depends on:** G3
* **Cost:** $0
* **Gate:** The written single-row risk acceptance, stating the 30–52% estimate, is recorded on #1849; and, if D08 is yes, the follow-up is sent by the owner, or by Claude after the owner's yes to a question naming the recipient, the channel and the exact text
* **Issues:** #1849

#### G6 · codex-operator · acknowledgment

The Codex session acknowledges in writing, on #1763 and #4761, before preparing any generic_v10 registration on either arm (A6 for the API, N7 for the direct arm):

- the D22 ruling: the v10z standing authorizations, including 'all evaluations of the CHORUS d4d' and full-reservation debits, do not extend to generic_v10;
- their withdrawal at G3, whatever D10 decides (D22);
- the D12 role split.

* **Depends on:** G3
* **Cost:** $0
* **Gate:** Acknowledgment visible on both issues
* **Issues:** #1763, #4761, #4354

### P. Preregistration (shared by every route, $0)

Before any spend, commit what each generic_v10 run is for and how it is judged, as #2930's acceptance requires ('committed before any paid canary'). Every billed generic_v10 step depends on P4.

#### P1 · maintainer-dev · local deterministic recompute

A free comparability audit at 15d053d1a, run outside the Codex session's CPU-timing windows. It covers:

- each v8 baseline record's sha256 and bundle md5 (all four match today's files);
- the v6 drift: AI_READI 0f3abb51, CM4AI 1dfd34e5 and VOICE dcd71717, against today's d22b61a9, 50037fc6 and 9193c3cb;
- VOICE_PEDIATRIC's bundle 03502237, which has no record;
- recall-target counts per record (cue sha256 768a26a3…, tools pattern 4726c005…), VOICE's targets included;
- receipt coverage with denominators, #2932 structure and report findings;
- the v8 per-project worst values D21 refers to: report findings CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0; British spellings VOICE 2; all other gated metrics 0;
- the v8 per-call retry tally: 92 calls, 5 transport errors, 3 answer-level retries after end_turn.

The last two items were recomputed on 2026-10-09.

* **Depends on:** none
* **Cost:** $0
* **Gate:** Every number is reproducible by a named command and cited by hash
* **Issues:** #3287, #2932, #4762, #3288, #2930

#### P2 · maintainer-dev · docs preregistration

Write `notes/generic_v10_analysis_plan.md` on a branch, in a durable worktree under `d4d-executions`. Items:

1. Estimands: feasibility and acceptance; the package effect against v8; replicate structure; external feasibility; the cross-arm contrast only as D09 permits.
2. D02's comparator, metrics and cell roles, VOICE included in the recall predictions, and the VOICE_PEDIATRIC count.
3. Rules for n=1 and n=3: descriptive, or a tolerance preregistered per metric.
4. Confounds, including effort as a fixed confound (API provider default against an explicit Claude Code level). Also state that `repo.dirty` will read true, because run outputs and inputs are untracked; launch cleanliness is `git status --porcelain --untracked-files=no` plus an allowlist of output paths.
5. Pilot acceptance rows: the canary rows that must be 0 under a pending floor, which is UNMEASURABLE by design; coverage as a fraction with its denominator; #2926's report items; the report-totals check (#4766).
6. The acceptance-record format.
7. Attempt accounting: every attempt counted; at most 2 billed attempts per registered cell; pilots analysed separately; no replicate chosen by score; canonical marks never used as the estimate.
8. The D20 floor rule.
9. D21: absolute floors on production rosters, the continuation rule, and cells split across prefixes.
10. D07's caps and operator triggers (the cap minus the pending phase's worst case), the stop-loss, and the single-delivery terminal-failure estimate with how the pilots measure it.
11. The D17 freeze.
12. Blinding and reviewers (D23): acceptance reviews kept separate from the shuffled, label-stripped comparison batch (#3280).
13. Labels and launches: a distinct date-letter prefix per roster; generic-v10 as a delimited token; no pilot or canary word; outputs copied, never moved, into data PRs so the #795 guard keeps passing; the launch worktree never fast-forwarded over those data PRs except by D17's procedure; a stopped label never re-run; every generic_v10 launch, continuations included, through `d4d api batch` with a roster, never `d4d api run` (D20).
14. Fixed model-facing values: one receipt registration body for all projects and roles, in which only the floor changes at A15, with a neutral `registration_id` and `context_limit_basis`; and the model-facing audit limits A1 lists, sized for the largest bundle. Each registration's top-level `registration_id` differs, because a roster refuses a reused one (`cli/api.py:163-167`); it is neutral and sits outside the fixed receipt body.
15. Stage caps and non-model-facing allowances from A1 and A1b.
16. The D24 instrument, and the recorded deviation from #2930's wording.
17. The D04 path and, under B, the with-crate stage.
18. Per-stage transport and empty-answer rates, and whether D06's display changed them.

* **Depends on:** G3, P1, A1, A1b
* **Cost:** $0
* **Gate:** PR open with CI green
* **Issues:** #2930, #3287, #2926, #3336, #2932, #2914, #4766, #3280

#### P3 · independent-reviewer · review offline

Adversarial review of the P2 PR by a Claude reviewer plus a Codex CLI pass (`codex exec` run directly, per the maintainer's private session notes). Every prediction needs a metric, a comparator, a decision rule and an instrument, and nothing may be chosen after seeing data. Each finding becomes an issue and is fixed in the PR.

* **Depends on:** P2
* **Cost:** $0 provider; reviewer time
* **Gate:** No open blocking finding
* **Issues:** #2930, #3287

#### P4 · owner · owner decision

The owner merges P2 with an explicit word. Together with the A2 and A2c merges, this fixes the launch base for every generic_v10 API registration.

* **Depends on:** P3
* **Cost:** Owner time
* **Gate:** Merged on main before any registration hash is put to the owner
* **Issues:** #2930, #3287

### A. API generic_v10 (claudecode_api; Messages SDK via CBORG claude-opus-5)

Produce the first accepted generic_v10 record (the CHORUS pilot), then the API matrix:

- 2 diagnostic pilots;
- 13 production runs (15 with VOICE_PEDIATRIC ×3);
- Kids First ×1;
- under #2914 path B, a with-crate CHORUS canary and ×3.

Every billed step has its own registration (-reg), independent review (-rev) and owner word (-word) naming its registration's sha256 and a cap; for a roster, the word names the roster's sha256 and every registration sha256 it lists. Every API generic_v10 launch goes through `d4d api batch` with a roster, never `d4d api run` (D20). Every later word re-runs A8's checks first (A8).

Critical path:

1. Drafts at 15d053d1a, none needing G3: A3, A4b and the A5d root drafts, then A1.
2. G3, then A1b.
3. P2, P3 and P4, with A2 and A2c in parallel.
4. A4.
5. A5, then A6 (the builder's final run and the launcher's dry-run at the launch base).
6. A7, A8, A9.
7. A10.
8. A11, A12, A13.

#### A1 · maintainer-dev · local deterministic recompute

Model-free runtime-composition sizing.

Preferred: a reviewed offline sizing script under `scripts/` (or the sibling inputs directory). It stages a historical record as a scratch run's phase-1 originals, then calls the runtime unchanged:

- `typed_audit_runtime.prepare_packet` and `build_request` for every worker and the omission stage;
- `receipt_completion.build_request` and `request_payload`.

Integration needs worker and omission responses, so it is sized as an upper bound from the output caps.

Fallback: a harness composing the same parts, checked line by line against `typed_audit_runtime.py:122-148`. That code wraps the inner request in policy text, evidence contract, audit carry, schema context, generation context and a binding, then bounds `len(sg.canonical(payload))` by `max_request_bytes`. The offline prepare check (`typed_audit.py:252-254`) sees only shared plus worker tail.

Run it in a scratch worktree at 15d053d1a with its own venv (the launch base does not exist until A4), with `PYTHONPATH=<worktree>/src`, the A3 draft registration and the A5d draft contexts. `prepare` requires `--context` and `--schema` (`typed_audit.py:534-537`). A6 re-runs it at the launch base.

Inputs:

- v9 CHORUS 2026-09-12 rep1 originals (bundle 9b2ef4b6);
- v8 2026-09-04g rep2 AI_READI originals (bundle d22b61a9).

For 2–3 `max_paths`/`max_workers` settings, record:

- payload bytes per stage;
- worker counts;
- which `audit_limits` values reach request text, found by rendering twice with one limit changed. At 15d053d1a at least `max_request_bytes` and `omission_output_tokens` do (`audit_omissions.py:376-378`, sent via `typed_audit_runtime.py:115-116`). `max_paths`, `max_workers` and `max_inventory_bytes` shape each worker's assignment.

Floors the harness must exceed: each worker carries at least 761,799 bytes of raw inputs for AI_READI (bundle 542,513, full 94,536, core 79,062, receipt 40,009, manifest 5,679) and 93,654 for CHORUS, before escaping, schema context and wrappers.

Run outside Codex's CPU-timing windows.

* **Depends on:** A3, A5d
* **Cost:** $0 (no model or token-count call)
* **Gate:** A sizing table in a local draft: payload bytes per stage and project, worker counts, the model-facing limits list, and proposed limits with margin. If the harness and `build_request` disagree on the CHORUS case, `build_request` wins and the harness is fixed
* **Issues:** #4345 (closed 2026-10-05; context), #2926

#### A1b · codex-operator · unbilled provider call

Unbilled token calibration, with the owner's consent from G3. Through the A4b draft launcher's environment (`ANTHROPIC_API_KEY` unset, `CBORG_API_KEY` exported), call `messages.count_tokens` on `api.cborg.lbl.gov` for:

- A1's largest CHORUS and AI_READI worker payloads;
- the omission payload;
- the receipt-completion payload.

Each call carries the D06 thinking dict (`{type: adaptive, display: summarized}`).

This answers two questions before any registration:

1. Exact token counts for `max_input_tokens_per_call`, `aggregate_input_tokens` and the dollar stops.
2. Whether the route accepts display on `count_tokens`. This matters because the first count call comes at receipt completion, after the full phase is billed (`receipt_completion.py:334-352`).

* **Depends on:** A1, A4b, G3
* **Cost:** $0 expected: v10e did a count-only admission with no generation request (`notes/matched_cborg_2026-09-14_v10e/api_initial_admission.json`). Verify no charge appears
* **Gate:** Counts recorded beside A1's table. A refusal of display sends D06 back to the owner before A2 merges
* **Issues:** #1849, #4345 (closed 2026-10-05; context), #777

#### A2 · maintainer-dev · code fix offline

The API runtime PR, with its G4 issue filed first:

- add `display: summarized` to adaptive thinking for generic_v10 runs only (`api_runner.py:1614`), so earlier conditions' declarations do not change;
- add the typed-stage cache breakpoint only if D06 chooses it;
- if #4766's checker is wanted inside generic_v10, add it here, report-only (D17).

Then tests, adversarial review (Claude reviewer plus Codex CLI pass), CI and the owner's merge word.

* **Depends on:** G3, G4, A1b
* **Cost:** $0
* **Gate:** Merged before A4
* **Issues:** #1849, #4345 (closed 2026-10-05; context), #4766

#### A2c · maintainer-dev · code fix offline

A between-run cumulative dollar stop in `d4d api batch`, at the `run_telemetry` rates, printing dollars as well as tokens; the batch prints only token totals today. Its issue is filed first (G4). Then tests, adversarial review, CI and the owner's merge word.

It lands before A4, so the launch worktree never has to advance for it (D17).

* **Depends on:** G3, G4
* **Cost:** $0
* **Gate:** Merged before A4
* **Issues:** #1763, #4345 (closed 2026-10-05; context)

#### A3 · maintainer-dev · code fix offline

A registration builder, drafted at 15d053d1a and kept in the sibling inputs directory, outside `src/`. Model it on `tests/test_shared_generation_selection.py:17-52`. It uses `descriptor()`, `file_pin`, `schema_pin(capture_schema(strict=True))` and `_model_settings()`.

It declares:

- runtime: provider exactly 'LBL CBORG (proxy to Anthropic)', `base_url` `https://api.cborg.lbl.gov`, claude-opus-5, temperature null, thinking per D06, effort null. The draft records the thinking that `_model_settings()` resolves at 15d053d1a, because preflight compares the two (`shared_generation.py:402-412`);
- a config pin on `.github/workflows/d4d_assistant_deterministic.config`;
- `audit_transport` `{1, 0, 0}`;
- one `receipt_completion_registration_v2` body for every project and role, identical apart from the floor (pending until A15), with a neutral `registration_id` and `context_limit_basis` and limits sized for the largest bundle;
- a distinct, neutral top-level `registration_id` for each registration, because a roster refuses a reused one (`cli/api.py:163-167`);
- model-facing audit limits (A1's list) fixed across projects; only non-model-facing allowances vary.

It also writes the `shared_generation_batch_roster_v1`. Its output is checked with `shared_generation.parse_registration`.

The draft carries provisional limits, marked as such, so that A1 can build real requests; no draft output is ever launched. The final run, with limits from A1/A1b and P2 item 14, is part of A6 at the launch base, and A7 reviews it.

* **Depends on:** none
* **Cost:** $0
* **Gate:** The draft's output parses with `shared_generation.parse_registration` at 15d053d1a
* **Issues:** #4345 (closed 2026-10-05; context), #2926

#### A3b · maintainer-dev · code fix offline

A read-only live dollar readout for the operator. It reads:

- the run's usage ledger, `{metadata_dir}/{P}_api_usage_{key}.json`, written as calls settle (`usage_ledger.py:112-116`);
- its `pending_call`, written before each request (`usage_ledger.py:306-341`).

It prices settled rows at `run_telemetry.py`'s rates and adds the pending phase's worst case: its output cap at $25/M plus its input. `pending_call` records only the usage id, phase, attempt and start time (`usage_ledger.py:338-339`), so the readout takes the cap and the input from elsewhere. For typed stages and receipt completion, it reads the saved request's `max_tokens` and the counted `input_tokens` saved before the call (`typed_audit_runtime.py:464-472`, `receipt_completion.py:511`). Ordinary phases (full, reconcile, report, repair) save neither, so for them it takes the phase cap, clamped to 128000, and a stated per-project input bound per phase. Both are stated at generic_v10's values. Renderer 25 sends the report, its regate and its after-repair call at 96,000 output tokens (`api_runner.py:402-403`), where v8 and v9 sent 24,000, and the report also carries a source-review inventory of the final full record (`api_runner.py:2819-2829`) besides the typed audit's findings. So the full phase's worst case is no stand-in for a pending report: later phases carry more input than full (v9 CHORUS report 76,237 tokens against full's 41,339), and v8's AI_READI report input of 338,608 tokens at the 96k cap already comes within about $0.25 of the full phase's $4.50 at its recorded cache split, and exceeds it if all input is priced at the cache-write rate. It is kept with the caller inputs and changes no runtime code.

* **Depends on:** none
* **Cost:** $0
* **Gate:** Reproduces $3.30811950 from the v9 CHORUS ledger file `data/d4d_concatenated/claudecode_api_core/2026-09-12_claude-opus-5-api-generic-v9_rep1/CHORUS_api_usage_46d8033e251b3c6e.json` at 15d053d1a (re-checked on 2026-10-09), and reproduces the about $3.45 CHORUS and about $4.50 AI_READI full-phase worst cases from synthetic `pending_call` rows, and a pending AI_READI report row at the 96k cap with the stated report input bound
* **Issues:** #1763, #4345 (closed 2026-10-05; context)

#### A4 · codex-operator · read only audit

Launch base and directories:

- One durable worktree under `d4d-executions` with a neutral name (no pilot, canary, date, replicate or arm token), at the main commit after P4, A2 and A2c, with its own environment: a venv dedicated to the worktree, never a `.venv` symlinked to the primary checkout's, whose editable `.pth` would add the primary checkout's `src` to the package path.
- One sibling durable directory, also neutrally named, for caller inputs (contexts, registrations, rosters) and logs.

Both paths reach the model: `file_pin` is absolute (`shared_generation.py:244-248`), and `generation_context` sends the context and source-manifest pins (`shared_generation.py:440-459`). Every API generic_v10 run uses these two directories, and the worktree stays at this commit for the whole matrix (D17).

Through the A4b launcher, with `CBORG_API_KEY` set, run the import check, then:

- `d4d api prompts check --strict`
- `d4d bundle chunk --check --strict`
- `d4d download audit-bundles --strict`
- `d4d download scope --check --strict`
- `d4d runs check --strict`

Never commit run data here (#795). Data PRs copy outputs into a separate worktree.

* **Depends on:** P4, A2, A2c, A4b
* **Cost:** $0
* **Gate:** All gates exit 0 through the launcher. The import check passes: every entry of `list(data_sheets_schema.__path__)` resolves to `<worktree>/src/data_sheets_schema`, and `data_sheets_schema.api_runner`, `.shared_generation`, `.typed_audit_runtime`, `.receipt_completion` and `.cli.api` each have `__file__` under `<worktree>/src` (the package has no `__init__.py`, so `data_sheets_schema.__file__` is `None`). HEAD equals the base. `git status --porcelain --untracked-files=no` is empty. The CHORUS and AI_READI bundle md5s equal the comparators' (9b2ef4b6, d22b61a9)
* **Issues:** #2930, #3414

#### A4b · maintainer-dev · code fix offline

One launcher script, drafted at 15d053d1a and kept in the sibling inputs directory. Every later API step uses it: A1b's environment, A4's gates, A6's plan, render and dry-run, A8's checks, and every billed launch. It:

- changes to the worktree root, which the batch requires;
- runs the worktree venv's `d4d` under `env -u ANTHROPIC_API_KEY -u D4D_RECEIPT_FULL_MAX_TOKENS -u D4D_PHASE_WALL_CLOCK_SECONDS`, with `PYTHONUNBUFFERED=1` and `PYTHONPATH=<worktree>/src`. `ANTHROPIC_API_KEY` otherwise wins (`api_runner.py:3068-3076`). The other two are read from the process environment, and neither is pinned by the registration or compared by preflight: a leftover value would lower the full-phase output cap below 128,000, or change the 3,600 s per-call watchdog (`api_runner.py:404-414, 5767-5791`);
- refuses unless `CBORG_API_KEY` is set. The runner reads only the process environment, with no `.env` loading, and the primary checkout has no `.env`;
- refuses the `d4d api run` subcommand (D20);
- refuses unless the import check passes: every entry of `list(data_sheets_schema.__path__)` resolves (`os.path.realpath`) to `<worktree>/src/data_sheets_schema`, and `data_sheets_schema.api_runner`, `.shared_generation`, `.typed_audit_runtime`, `.receipt_completion` and `.cli.api` each have `__file__` under `<worktree>/src`. The package has no `__init__.py`, so `data_sheets_schema.__file__` is `None`. A `.venv` symlinked to the primary checkout's carries that checkout's editable `.pth`, which adds a second `__path__` entry, and the launcher refuses it ('resolves to', not 'equals', so a symlinked spelling of the same directory passes);
- for a launch, runs under `caffeinate -ims` with `nohup`, logging outside the worktree.

Without it, a launch could import the primary checkout's code while provenance names the worktree's commit. That checkout's editable `.pth` points at a branch 1,185 commits behind 15d053d1a with no `shared_generation.py`.

Its final check is part of A6 (the dry-run at the launch base, with its sha256 recorded), and A7 reviews it.

* **Depends on:** none
* **Cost:** $0
* **Gate:** Its dry-run mode exits 0 at 15d053d1a in a scratch worktree with its own venv, with the import check passing for that worktree's `src`
* **Issues:** #4345 (closed 2026-10-05; context), #777

#### A5d · curator · curator or human rating

Draft scope contexts (`omission_context_v1`) from the `source_manifest.yaml` scope blocks:

- root-only drafts for CHORUS and AI_READI now, for A1's sizing;
- full drafts for CM4AI, VOICE, VOICE_PEDIATRIC and Kids First after G3.

No labels, diagnoses or prior-arm content (#422).

* **Depends on:** none for the root drafts; G3 for the full drafts
* **Cost:** $0; curator time
* **Gate:** Each draft validates against `omission_inventory_v1/context.schema.json`
* **Issues:** #1763, #2914

#### A5 · curator · curator or human rating

Final contexts in the sibling inputs directory: one neutrally named file per project, shared by pilot and production runs. Each has:

- a root scope;
- a release, named or null (CHORUS is null under D04);
- a `source_policy`.

VOICE declares VOICE_PEDIATRIC as related but distinct, as its manifest scope block does. Nested owner scopes only where a mapping exists.

* **Depends on:** G3, A4, A5d
* **Cost:** $0; curator time
* **Gate:** Independent review (D23) against #422 and the context schema
* **Issues:** #1763, #2914

#### A6 · codex-operator · registration offline

At the launch base, through the A4b launcher with `CBORG_API_KEY` set so that preflight checks the endpoint (`shared_generation.py:418`; `plan` reaches preflight via `api_runner.py:828-843`):

1. Re-run A1's harness and confirm its sizes still hold with A2's changes.
2. Run the A3 builder with the final limits (A1/A1b and P2 item 14) to write the CHORUS pilot registration and a one-row roster in the sibling inputs directory:
   - `registration_path` is the file's absolute path, and the top-level `registration_id` is neutral;
   - the label is `2026-10-DDa_claude-opus-5-api-generic-v10_rep1`: a date letter reserved for this roster, generic-v10 as a delimited token (#1094), no pilot or canary word;
   - `run.arm` is 'BASELINE (input documents only)' and the method claudecode_api;
   - the floor is `{state: pending, mode: diagnostic_pilot}`.
3. Run the launcher's dry-run mode.

Offline checks:

- `d4d api plan` and `d4d api render-prompt`, each with `--shared-generation-version 1 --shared-generation-registration <registration>`;
- the batch dry-run below: exactly A10's flags, with `--dry-run` in place of `--yes`.

```bash
d4d api batch --dry-run --projects CHORUS --replicates 1 --label-prefix <prefix> --shared-generation-version 1 --shared-generation-registration <roster> --canary-baseline 2026-09-04f_claude-opus-5-api-generic-v8
```

The dry-run returns before the confirm and the lock (`cli/api.py:804-805`), after `_shared_current` has folded the baseline's records into the authority and disjoint-output checks (`cli/api.py:779, 187-211`). It does not refuse a baseline prefix that matches nothing, so also confirm that the three 2026-09-04f CHORUS provenance records exist under `data/d4d_concatenated/claudecode_api_core/`.

`render-prompt` renders the base instruction, which carries the receipt registration, floor included (`api_runner.py:1470-1472`). It renders only `resolve_prompt` (`cli/api.py:495`), so it omits `generation_context` (the context and source-manifest pins), the schema context (the schema pins) and the typed-stage requests. List the model-facing strings from the `render-prompt` output and from the registration and context files:

- the label and the bundle path;
- the context, source-manifest and schema pins: paths, hashes and sizes;
- the raw receipt registration: `registration_id`, limits, `context_limit_basis` and floor;
- the omission request's limits;
- the binding hashes.

Record the sha256s of the registration, the roster, the builder and the launcher.

* **Depends on:** A1, A1b, A3, A4, A4b, A5, G6
* **Cost:** $0
* **Gate:** No refusal. The bundle md5 is 9b2ef4b6. The three 2026-09-04f CHORUS baseline records exist. The allowances' worst case fits the $15 cap. The launcher's dry-run exits 0 at the launch base
* **Issues:** #4345 (closed 2026-10-05; context), #2926, #2914

#### A7 · independent-reviewer · review offline

Registration review. Check:

- the byte pins, and that selection equals `descriptor()`;
- the runtime against D06, and that the provider reads exactly 'LBL CBORG (proxy to Anthropic)';
- the limits and stage caps against A1/A1b, with margin;
- that model-facing limits and the receipt registration body equal P2 item 14's fixed values;
- the scope context against #422;
- the label form;
- that no pilot or canary token appears in the label, paths, either `registration_id` (each registration's top-level id, unique per roster row, and the receipt body's) or `context_limit_basis` (the mandated floor literal is exempt);
- that the roster is outside every output directory and no input aliases an output;
- the A3 builder and the A4b launcher at the sha256s A6 recorded, and the A3b readout.

The approval is written and bound to those sha256s. Every finding becomes an issue, and any fix means a new registration.

* **Depends on:** A6
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the registration, roster, builder and launcher sha256s, from a reviewer who is neither the author nor the operator
* **Issues:** #4345 (closed 2026-10-05; context), #2930

#### A8 · codex-operator · read only audit

Pre-launch checks, all through the A4b launcher:

- re-observe the CBORG catalogue: the route, 1M in / 128k out, and prices against `run_telemetry.py:41-46` (posted 2026-08-05);
- `d4d api status` shows no live sweep, and D17's `pgrep` check for a live `d4d api run` prints nothing, because `d4d api status` sees only batch locks;
- the import check (A4b) and HEAD;
- `git status --porcelain --untracked-files=no` is empty, with run outputs on the allowlist;
- `CBORG_API_KEY` present, and `ANTHROPIC_API_KEY`, `D4D_RECEIPT_FULL_MAX_TOKENS` and `D4D_PHASE_WALL_CLOCK_SECONDS` absent, in the child;
- with the G3 consent, one unbilled `count_tokens` call on the registered payload with the registered thinking dict;
- the A3b readout run against a historical ledger;
- AC power, and the `caffeinate` form ready.

Before every later API word (A10c-word, A14-word, A16-word to A22-word, the word for a D17 step-7 canary, M5-word, M6-word), the operator re-runs A8 and records it beside that word's registration: the catalogue and price re-observation, `d4d api status` and the `pgrep` check, HEAD equal to the launch base or, after a D17 advance, to the target commit named in the most recent advance's step-6 parity statement (for M5-word and M6-word, equal to the base that M5-reg or M6-reg registered, which is later than the launch base if M2 landed after the API matrix), and `git status --porcelain --untracked-files=no` with the output allowlist. The launcher enforces the key, environment and import checks at every launch, so they need no separate step.

* **Depends on:** A7
* **Cost:** $0 (one unbilled count call)
* **Gate:** Checklist recorded beside the registration. A changed price or limit, or a refused count, stops the launch
* **Issues:** #777, #1849

#### A9 · owner · owner decision

The owner's launch word. It answers a question that names:

- the registration and roster sha256s;
- the $15 cap and its operator trigger (about $11.50);
- the 2 h wall-clock stop;
- the allocation (D07);
- the written transport-risk acceptance (G5).

'try again' or 'continue' after an outage is not a word.

* **Depends on:** A8, G5
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim beside the registration
* **Issues:** #2930, #1849

#### A10 · codex-operator · one canary run

BILLED. Through the A4b launcher, from the worktree root, under `caffeinate -ims` and `nohup`:

```bash
d4d api batch --projects CHORUS --replicates 1 --label-prefix <prefix> --shared-generation-version 1 --shared-generation-registration <roster> --canary-baseline 2026-09-04f_claude-opus-5-api-generic-v8 --yes
```

Immediately before launch, the operator hashes (`shasum -a 256`, before invoking the launcher) the roster, every registration it lists and the launcher script, and stops on any difference from the sha256s named in the word and the review. Every later billed API launch repeats this pre-launch hash check.

This is the fan-out path: it takes the run lock, runs the branch guard and writes the canary block (`cli/api.py:817-841, 917-955`). Expect exit 1 with 'registered receipt gate unmeasurable': a pending floor is blind by design.

The operator watches A3b and runs `d4d api stop --label-prefix <prefix>` at the trigger or at 2 h. No branch switch while the run is live (#795). A stopped label is never resumed.

* **Depends on:** A7, A9
* **Cost:** Unmeasured; cap $15, trigger about $11.50. References: v9 CHORUS cost $3.30811950 for 6 calls; v8 CHORUS runs $4.37–$6.12. v10 adds one receipt-completion call and W+2 uncached typed calls, bounded by the registered allowances
* **Gate:** The run completes, or stops with outputs and reason preserved
* **Issues:** #2930, #2926, #1849, #777

#### A11 · codex-operator · local deterministic recompute

Mechanical acceptance (free).

Confirm on disk and non-empty:

- the full record;
- the effective receipt and its completion snapshots;
- the derived core;
- the typed-audit packet, every stage response and the integration snapshot (`intermediate/CHORUS_audit.json`);
- the report, with its dispositions table;
- the provenance `shared_generation` block;
- the `api_usage` rows;
- the canary block.

Then:

- `d4d receipts check --method claudecode_api --label <label> --project CHORUS`: 0 unreviewed chunks, 0 unverified snippets, 0 gated findings, not vacuous, and coverage with its denominator;
- `python -m data_sheets_schema.typed_audit_report --assembly data/d4d_concatenated/claudecode_api_core/<label>/intermediate/CHORUS_typed_audit_assembly.json --output <a path that does not exist yet, beside the A13 acceptance record>`. The runtime saves the assembly under that name, or with a numeric suffix, and the usage ledger's `typed_audit.assembly.path` pins it; the report refuses an existing destination (`typed_audit_report.py:175-176`);
- duplicate keys: 0 in full and in core;
- the report-totals check (#4766): compare the report's stated finding total and severity subtotals with `audit_counts` of `intermediate/CHORUS_audit.json`, the counts the report request carried, by hand or with a read-only script. Record the stated values, the computed values and any mismatch;
- every `full` row in `api_usage`, and `model.max_tokens_by_phase.full`, read 128000;
- the provenance `model.provider` reads 'LBL CBORG (proxy to Anthropic)' and `model.base_url` reads `https://api.cborg.lbl.gov`. `api_usage` rows record no route; these two fields describe the record-writing process's environment, and `shared_generation.require_client` enforces the registered base_url for the run's client (`shared_generation.py:535`);
- record per-call transport and empty-answer outcomes, and the cost at that day's prices.

Record #2926's items.

* **Depends on:** A10
* **Cost:** $0
* **Gate:** Every row P2 names is 0, the report totals match, the full-phase cap reads 128000, and the provenance `model.provider` and `model.base_url` read 'LBL CBORG (proxy to Anthropic)' and `https://api.cborg.lbl.gov`; otherwise the record goes to A13 as a rejection candidate
* **Issues:** #2926, #4345 (closed 2026-10-05; context), #4766

#### A12 · independent-reviewer · curator or human rating

Blind source review, for acceptance only, of the unchanged originals against the frozen bundle. The reviewer is named under D23 and is not the generating session. It checks:

- plans stated as current, and scope (#1782);
- roster roles (#1801, #2924);
- attribution to the named document (#1815);
- qualifiers and header history (#1816);
- that each date covers only its own clause, and ongoing work is stated as ongoing (#2924).

The #2918 and #2919 classes are counted separately (D05). If D19 is yes, a second blind reviewer writes the #2921 observations first. The comparison against v8 comes later, from E2's blinded batch, not from this review.

* **Depends on:** A11
* **Cost:** Reviewer time
* **Gate:** A dated accept or reject, bound to the artifact sha256s
* **Issues:** #1782, #1801, #1815, #1816, #2924, #2921

#### A13 · owner · owner decision

The owner accepts or rejects.

The acceptance record follows P2's format: verdict, registration and roster sha256s, artifact sha256s, check rows, coverage and its denominator, cost and reviewer references. It also states what the run did not establish: one project, n=1, no load test and no recall test.

maintainer-dev commits the record with the run's outputs in a data PR from a separate worktree. The outputs are copied, never moved, so the launch worktree keeps them and the #795 guard keeps passing. The data PR is reviewed (artifact sha256s checked against the acceptance record) before the owner merges. The launch worktree is never fast-forwarded over that merge except by D17's procedure.

On a rejection, preserve the outputs, diagnose and file the findings:

- a transport or operational cause allows one contingency (A10c-reg onward);
- a rule-level cause schedules the next shared-generation version for both arms.

* **Depends on:** A12
* **Cost:** Owner time; $0
* **Gate:** Acceptance record merged: the first accepted generic_v10 record
* **Issues:** #2930, #1763

#### A10c-reg · codex-operator · registration offline

Only if A13 rejects for a transport or operational cause: a new CHORUS registration and one-row roster under a new date-letter prefix, otherwise identical to A6, with A6's offline checks run through the launcher. The stopped label is never resumed.

* **Depends on:** A13
* **Cost:** $0
* **Gate:** No refusal; model-facing values equal A6's apart from label and paths
* **Issues:** #2930, #1849

#### A10c-rev · independent-reviewer · review offline

A7's review, applied to the contingency registration and roster.

* **Depends on:** A10c-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to both sha256s
* **Issues:** #4345 (closed 2026-10-05; context)

#### A10c-word · owner · owner decision

The owner's word for the contingency. It names both sha256s, the $15 cap with its trigger, and the D07 allocation, and states that this is the cell's second and last billed attempt.

* **Depends on:** A10c-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim beside the registration
* **Issues:** #2930

#### A10c · codex-operator · one canary run

BILLED. The contingency CHORUS pilot through the A4b launcher, run as A10 (pre-launch hash check included), then A11, A12 and A13.

* **Depends on:** A10c-rev, A10c-word
* **Cost:** As A10: unmeasured, $15 cap, inside the $100 pilot allocation
* **Gate:** Accepted, or the cell closes after two attempts and the owner reviews (D07)
* **Issues:** #2930, #2926

#### A14-reg · codex-operator · registration offline

The AI_READI pilot: a registration and one-row roster under a new date letter, planned with `--canary-baseline 2026-09-04g_claude-opus-5-api-generic-v8`. Never 04f, whose AI_READI rep1 is declared invalid.

The receipt registration body and the model-facing audit limits stay identical to A6's. Only non-model-facing allowances are re-sized, from A1b and the A10 actuals. Run A6's offline checks through the launcher, with the batch dry-run carrying `--canary-baseline 2026-09-04g_claude-opus-5-api-generic-v8`, and confirm that the three 2026-09-04g AI_READI provenance records exist under `data/d4d_concatenated/claudecode_api_core/`.

* **Depends on:** A13
* **Cost:** $0
* **Gate:** No refusal; the bundle md5 is d22b61a9; the three 04g AI_READI baseline records exist; model-facing values equal A6's
* **Issues:** #2926, #2930

#### A14-rev · independent-reviewer · review offline

A7's review for this registration, including the model-facing equality with A6 and the allowances checked against A1/A1b.

* **Depends on:** A14-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to both sha256s
* **Issues:** #4345 (closed 2026-10-05; context), #2926

#### A14-word · owner · owner decision

The owner's word. It names:

- both sha256s;
- a cap set from the CHORUS actuals (planning ceiling $35);
- its operator trigger: the cap minus the pending phase's worst case (about $4.50 while an AI_READI full call is pending: v8 input of 6,361 uncached plus 203,662 cache-write tokens, and a full 128k output), so about $30.50 at the $35 planning ceiling;
- a 3 h wall-clock stop.

* **Depends on:** A14-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #2926

#### A14 · codex-operator · one canary run

BILLED. The AI_READI pilot through the A4b launcher, run as A10 (pre-launch hash check included).

* **Depends on:** A14-rev, A14-word
* **Cost:** Unmeasured. Scenario $17–33 (the cost-and-risk input plan, unpublished; not re-derived here); ceiling $35, provisional on A1/A1b. v8 AI_READI runs cost $9.97–$13.66, with full-phase outputs of 112,321–115,616 of 128,000 tokens. Each typed worker carries at least 761,799 bytes uncached
* **Gate:** The run completes, or stops with outputs and reason preserved
* **Issues:** #2926, #2930, #777

#### A14-acc · owner · owner decision

A11 (operator) and A12 (reviewer) on the AI_READI pilot, then the owner's acceptance record, committed by data PR as in A13 and reviewed (artifact sha256s checked against the acceptance record) before the owner merges. On a transport or operational rejection, one contingency follows A10c's pattern under its own registration, review and word, funded by D07's AI_READI contingency line (no more than the pilot's cap, at most $35).

* **Depends on:** A14
* **Cost:** Owner and reviewer time; $0
* **Gate:** Acceptance record merged
* **Issues:** #2926, #2930

#### A15 · owner · owner decision

Register the numeric floor by the D20 rule, in a dated analysis-plan amendment PR. The amendment PR gets P3's review (a Claude reviewer plus a Codex CLI pass), with each finding filed as an issue, before the owner merges. This creates a new registration identity and does not certify the pilots.

Also record CBORG's #1849 answer, or the written risk acceptance.

Then apply D21's trigger. If either pilot had a terminal single-delivery failure, decide between:

- continuing under D21 (b);
- building (c) before A16, landed by D17's advance procedure (its step-7 canary included);
- moving to the next shared-generation version with one recorded retry.

Choosing the next shared-generation version ends this generic_v10 API matrix. That version needs its own analysis-plan amendment, its code and pin PR, and new pilots in the A6–A15 pattern before any roster; A16-reg follows only (b) or (c).

* **Depends on:** A14-acc, G5
* **Cost:** Owner time; $0
* **Gate:** Amendment reviewed and merged before any multi-row roster; the #1849 state and the D21 trigger answer recorded
* **Issues:** #2926, #1849, #2932

#### A16-reg · codex-operator · registration offline

The CHORUS replicate gate: three registrations and a 3-row roster under a fresh date-letter production prefix, excluding the pilots. Prepared only if A15 continues this matrix (the trigger did not fire, or the owner chose (b) or (c)). They use the A15 floor and no `--canary-baseline` (D21 b), from the same worktree and inputs directory. Run A6's offline checks through the launcher.

* **Depends on:** A15, A2c, A5
* **Cost:** $0
* **Gate:** No refusal. The three registrations differ only in label, paths and each row's top-level `registration_id`, which the roster requires to be unique (`cli/api.py:163-167`) and A7 checks for neutrality; the receipt body, its own `registration_id` included, is identical
* **Issues:** #3336, #2932, #2926

#### A16-rev · independent-reviewer · review offline

A7's review of the three registrations and the roster.

* **Depends on:** A16-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the roster and registration sha256s
* **Issues:** #4345 (closed 2026-10-05; context), #3336

#### A16-word · owner · owner decision

The owner's word. It names the roster sha256 and each registration sha256, a cap of about three times the accepted CHORUS pilot's actual cost plus margin, the per-run triggers, and D21's continuation rule.

* **Depends on:** A16-rev, and an A8 re-run recorded beside its registrations
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #3336, #1849

#### A16 · codex-operator · replicate gate

BILLED. The 3-row roster through the launcher, after A10's pre-launch hash check. Under the registered floor every run is gated (`cli/api.py:835-841`), and a stop closes the roster (D21).

* **Depends on:** A16-rev, A16-word, A2c
* **Cost:** About three times the accepted CHORUS pilot. The three v8 CHORUS runs cost $14.92
* **Gate:** Each run completes, or stops with outputs preserved
* **Issues:** #3336, #2932, #2926, #1849

#### A16-acc · owner · owner decision

A11 and an A12 acceptance review on each replicate, and the #2932 instability report from deterministic metrics. The acceptance records go by data PR as in A13, reviewed (artifact sha256s checked against each acceptance record) before the owner merges. The owner accepts before A17. Stopped cells continue under D21.

* **Depends on:** A16
* **Cost:** Owner and reviewer time; $0
* **Gate:** Three acceptance records, or a recorded D21 continuation
* **Issues:** #3336, #2932

#### A17-reg · codex-operator · registration offline

Production stage 2: one roster per project, each under its own date-letter prefix, with the A15 floor and no `--canary-baseline`. Order: CM4AI, VOICE, AI_READI. These are the confirmatory cells, in ascending bundle size (320,799, 376,446 and 542,513 bytes). Prepare each roster after the previous one is accepted.

CM4AI and VOICE get no project-specific canary: each roster's first run is a gated replicate under the A15 floor, and a stop closes that roster (D21).

* **Depends on:** A16-acc
* **Cost:** $0
* **Gate:** No refusal for each roster. Within a roster the registrations differ only in label, paths and each row's top-level `registration_id` (`cli/api.py:163-167`), which A7 checks for neutrality
* **Issues:** #3336, #2926, #1763

#### A17-rev · independent-reviewer · review offline

A7's review for each roster, in turn.

* **Depends on:** A17-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to each roster's sha256 and every registration sha256 it lists
* **Issues:** #4345 (closed 2026-10-05; context)

#### A17-word · owner · owner decision

One owner word per roster. Each names that roster's sha256 and every registration sha256 it lists, a cap re-estimated from actuals, and the triggers.

* **Depends on:** A17-rev, and an A8 re-run before each roster's word, recorded beside its registrations
* **Cost:** Owner time
* **Gate:** Each word is recorded verbatim
* **Issues:** #1763

#### A17 · codex-operator · full arm

BILLED. Run the rosters one at a time through the launcher, each under its own word and after A10's pre-launch hash check.

* **Depends on:** A17-rev, A17-word
* **Cost:** $78.77 at v8-equivalent cost for these 9 runs ($17.29 + $27.31 + $34.17), plus the typed-audit and receipt increment and any D21 re-runs. Replace with actuals
* **Gate:** Each run completes, or stops with outputs preserved
* **Issues:** #3336, #2926, #1763

#### A17-acc · owner · owner decision

A11 and an A12 review on every record. Each record is accepted or recorded as failed, and stopped cells continue under D21. The acceptance records go by data PR as in A13, reviewed (artifact sha256s checked against each acceptance record) before the owner merges.

* **Depends on:** A17
* **Cost:** Owner and reviewer time; $0
* **Gate:** Every cell is accepted, failed, or in a recorded D21 continuation
* **Issues:** #3336, #2926

#### A18-reg · codex-operator · registration offline

VOICE_PEDIATRIC, descriptive: ×1, or ×3 if D02 chose it, under its own prefix with the A15 floor. No comparator exists on any arm, so it runs on absolute floors only (`cli/api.py:398-400`). It is analysed with VOICE as one cluster.

* **Depends on:** A17-acc
* **Cost:** $0
* **Gate:** No refusal; the bundle md5 is 03502237; with ×3, each row's top-level `registration_id` is distinct (`cli/api.py:163-167`) and neutral
* **Issues:** #1763, #3414

#### A18-rev · independent-reviewer · review offline

A7's review of the VOICE_PEDIATRIC registration and roster.

* **Depends on:** A18-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the roster and registration sha256s
* **Issues:** #1763

#### A18-word · owner · owner decision

The owner's word naming the roster sha256, each registration sha256 it lists and a cap.

* **Depends on:** A18-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #1763

#### A18 · codex-operator · full arm

BILLED. The VOICE_PEDIATRIC roster through the launcher, after A10's pre-launch hash check.

* **Depends on:** A18-rev, A18-word
* **Cost:** No measured basis. The bundle (206,008 bytes) sits between CHORUS's and CM4AI's
* **Gate:** Each run completes, or stops with outputs preserved
* **Issues:** #1763

#### A18-acc · owner · owner decision

A11 and an A12 review; each record accepted or recorded as failed. The acceptance records go by data PR as in A13, reviewed (artifact sha256s checked against each acceptance record) before the owner merges.

* **Depends on:** A18
* **Cost:** Owner and reviewer time; $0
* **Gate:** Recorded per record
* **Issues:** #1763

#### A19-reg · codex-operator · registration offline

Kids First (D15):

- Its own `omission_context_v1`, written by the curator. The root scope is the Kids First Data Resource; release is null or the catalogue snapshot, as the owner decides; per-study owner scopes only where a mapping exists.
- A registration built from `notes/matched_cborg_2026-09-13/kids_first/`, with the neutral profile and vocabulary null.
- A one-row roster under the registered floor.

First re-validate the frozen chunk manifest, which A4's study-bundle gates do not cover:

```bash
d4d bundle chunk --bundle notes/matched_cborg_2026-09-13/kids_first/KIDS_FIRST_preprocessed.txt --chunk-manifest notes/matched_cborg_2026-09-13/kids_first/chunks.yaml --check --strict
```

Its rule is version 2, which is main's `DEFAULT_RULE` (`chunking.py:34-35`).

* **Depends on:** A14-acc, A15, A5
* **Cost:** $0
* **Gate:** The chunk check exits 0; no refusal; the context is reviewed against #422
* **Issues:** #1763, #1541

#### A19-rev · independent-reviewer · review offline

A7's review under the neutral profile.

* **Depends on:** A19-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the roster and registration sha256s
* **Issues:** #1763

#### A19-word · owner · owner decision

The owner's word naming the roster sha256, the registration sha256 and a cap set from AI_READI actuals (the Kids First bundle, 541,184 bytes, is about the size of AI_READI's 542,513).

* **Depends on:** A19-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #1763

#### A19 · codex-operator · one canary run

BILLED. The Kids First canary through the launcher, after A10's pre-launch hash check.

* **Depends on:** A19-rev, A19-word
* **Cost:** Unmeasured, likely near the AI_READI pilot. v10r's $15 cap predates the typed audit; four pre-v10 phases reserved $13.84 (the full-generation, audit, reconciliation and report reservations, without carried outputs, in `notes/kids_first_budget_proposal_2026-09-14/README.md`); the initial request was 233,161 tokens
* **Gate:** Completes, or stops with outputs preserved
* **Issues:** #1763, #1541

#### A19-acc · owner · owner decision

A11 and an A12 review under the neutral profile, then the owner's acceptance, recorded by data PR as in A13 and reviewed (artifact sha256s checked against the acceptance record) before the owner merges. Evaluate only after acceptance, with `--profile neutral` (#1541). Fix #4104 before any outward HTML.

* **Depends on:** A19
* **Cost:** Owner and reviewer time; $0
* **Gate:** Accepted, with no Kids First expansion
* **Issues:** #1763, #1541, #4104

#### A20 · maintainer-dev · local deterministic recompute

Canonical marks among accepted replicates only:

```bash
d4d runs select --method claudecode_api --project P --config <prefix>
```

The command needs at least two replicates, validates candidates live against the current schema (#931), does not read acceptance (no issue yet; G4 files one) and groups one prefix only. So candidates are restricted by procedure, and a cell that D21 split across prefixes is either marked by a recorded procedure or left unmarked (G4 gap). Pilots are never candidates. Use `--execute` only on the owner's word.

* **Depends on:** A16-acc, A17-acc
* **Cost:** $0
* **Gate:** Canonical marks only on accepted replicates
* **Issues:** #931, #3336

#### A21-reg · codex-operator · registration offline

Only if D04 is B: a with-crate CHORUS canary. Its registration has:

- `run.arm` 'DE NOVO WITH CRATE (documents + RO-Crate evidence)' and method claudecode_agent_crate;
- the bundle `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt` (65,749 bytes) and its chunk manifest;
- the CHORUS context unchanged and the registered floor;
- a one-row roster under its own date-letter prefix, with no `--canary-baseline`.

* **Depends on:** A16-acc, A15
* **Cost:** $0
* **Gate:** No refusal; model-facing values differ from A16's only in label, method, bundle and paths
* **Issues:** #2914

#### A21-rev · independent-reviewer · review offline

A7's review of the with-crate registration.

* **Depends on:** A21-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the roster and registration sha256s
* **Issues:** #2914

#### A21-word · owner · owner decision

The owner's word naming the roster sha256, the registration sha256 and a cap scaled from the CHORUS replicate actuals.

* **Depends on:** A21-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #2914

#### A21 · codex-operator · one canary run

BILLED. The with-crate CHORUS canary through the launcher, after A10's pre-launch hash check.

* **Depends on:** A21-rev, A21-word
* **Cost:** Unmeasured; scale from A16's actuals (bundle 1.8× CHORUS's 35,920 bytes)
* **Gate:** Completes, or stops with outputs preserved
* **Issues:** #2914

#### A21-acc · owner · owner decision

A11 and an A12 review, then the owner's acceptance, recorded by data PR as in A13 and reviewed (artifact sha256s checked against the acceptance record) before the owner merges.

* **Depends on:** A21
* **Cost:** Owner and reviewer time; $0
* **Gate:** Accepted before A22
* **Issues:** #2914

#### A22-reg · codex-operator · registration offline

Under B: three with-crate CHORUS replicates in a 3-row roster under a new prefix, with the registered floor and no `--canary-baseline`.

* **Depends on:** A21-acc
* **Cost:** $0
* **Gate:** No refusal. The registrations differ only in label, paths and each row's top-level `registration_id` (`cli/api.py:163-167`), which A7 checks for neutrality
* **Issues:** #2914

#### A22-rev · independent-reviewer · review offline

A7's review of the roster.

* **Depends on:** A22-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the roster and registration sha256s
* **Issues:** #2914

#### A22-word · owner · owner decision

The owner's word naming the roster sha256, each registration sha256 it lists and a cap from A21's actuals.

* **Depends on:** A22-rev, and an A8 re-run recorded beside its registrations
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #2914

#### A22 · codex-operator · full arm

BILLED. The with-crate roster through the launcher, after A10's pre-launch hash check.

* **Depends on:** A22-rev, A22-word
* **Cost:** About three times A21's actual cost
* **Gate:** Each run completes, or stops with outputs preserved
* **Issues:** #2914

#### A22-acc · owner · owner decision

A11 and an A12 review on each record, recorded by data PR as in A13 and reviewed (artifact sha256s checked against each acceptance record) before the owner merges. Then report the with-crate minus without-crate delta at generic_v10, as #2914's B acceptance requires.

* **Depends on:** A22
* **Cost:** Owner and reviewer time; $0
* **Gate:** `d4d runs list --arm de_novo` shows the CHORUS canary plus 3 replicates under generic_v10
* **Issues:** #2914

### N. Claude Code shared protocol via the #4354 adapter (claudecode_direct, subscription)

Produce one accepted shared-protocol Claude Code CHORUS record at no CBORG cost. This vehicle is the direct arm unless D09 chooses (b). The Codex session's in-flight work stays on its own branches; delivery uses a separately cut branch. The first billed run is one bounded canary.

#### N1 · codex-operator · code fix offline

Codex's in-flight work, on its own branches only, inside the D18 time-box once G3 sets it, with every deadline unchanged and no provider call. Order: #4741, then #4738, then #4740. The next #4740 target is parent receipt settlement and phase-1 sealing, last measured at aa09dbbc6.

Fold in #4764 (applied locally at aa09dbbc6), #4737, #4739, #4742, #4748–#4750, #4752–#4757 and #4729, and the native stopped-capture issues filed after the triage, #4773–#4786 and #4788 (all open as of 2026-10-09 17:08Z; several are cited by the terminal-source branch's commits). #4751 is dropped: the triage closed it as observation-only at 2026-10-09T08:08:48Z. The plan edits none of these branches.

* **Depends on:** G1b, for the gate's published head; the work itself continues now
* **Cost:** $0
* **Gate:** At a head published on GitHub (G1b), the genuine helper fixture and the initial-receipt fixture reach phase-one seal, helper publication and receipt admission inside the unchanged 60 s budget
* **Issues:** #4741, #4738, #4740, #4764, #4737, #4739, #4742, #4748, #4749, #4750, #4752, #4753, #4754, #4755, #4756, #4757, #4729, #4773–#4786, #4788

#### N2 · codex-operator · code fix offline

Public #4728 integration, carrying #4687 together with #4733, #4735, #4718, #4720, #4721, #4723–#4726, #4697, #4700, #4703, #4707 and #4708, on Codex's branches. Fold in #4801 (filed 2026-10-09T16:47Z, open as of 2026-10-09 17:08Z): the selected native completion trial still reaches its 900 s deadline, and the issue proposes reusing the #4764 span loader in JSON event preflight.

PR #4659 (head 38fb11d5d, base `review/4354-offline-acceptance`), or its successor, must be green at the exact head. As of 2026-10-09 17:08Z it fails shard 1, shard 3 and test. Green means no #4680 live-stream refusal, and both selected native tests finish inside 900 s (#4400, #4550, #4575, #4576).

* **Depends on:** N1
* **Cost:** $0 (hosted CI)
* **Gate:** CI green at the exact head, including shards 1 and 3
* **Issues:** #4728, #4687, #4680, #4400, #4550, #4575, #4576, #4659, #4801

#### N3 · maintainer-dev · code fix offline

Deliver #4354 to main (item 7) without editing any Codex branch:

1. Cut a separate delivery branch (for example `deliver/4354-main`) from the published head that N2 names.
2. Merge `origin/main` into it there. Record the base SHA and the published-head SHA. The review branch is 95 ahead and 125 behind 15d053d1a (merge-base 286b88688), and main changed seven native files after that merge-base.
3. Never push to `review/4354-offline-acceptance`, `fix/4537-trace-single-decode` or any `/private/tmp` branch. If Codex publishes more commits, fetch and merge them into the delivery branch.
4. Keep the review-branch fixes, port #4603, reconcile with draft PR #4508 (#4521, #4505, #4502), update the descriptor, guide and scanner (#4136, #4402, #4403), and set the launch form per D13 (#4162) and the label design per #2223.
5. Then an independent adversarial review, full CI at the exact head, a merged-byte check and the owner's merge.

* **Depends on:** N2, G3
* **Cost:** $0
* **Gate:** Merged by the owner, with offline acceptance still green after the merge. While the API window is open the merge changes no API-path bytes; otherwise it waits for a stage boundary with a parity check (D17)
* **Issues:** #4354, #4603, #4508, #4521, #4505, #4502, #4136, #4402, #4403, #4162, #2223

#### N4a · maintainer-dev · code fix offline

The #4760 saved permission-probe producer. It runs the real binary against a scripted local provider, with no provider spend, in the environment D09 implies. It includes a round-trip test through `verify_saved_probe`.

* **Depends on:** G3
* **Cost:** $0
* **Gate:** Reviewed and merged before N7; native registrations hash all of `src/` (#4693)
* **Issues:** #4760, #4693

#### N4b · maintainer-dev · code fix offline

Runtime and quota guards, after N6:

- the #4759 durable runtime per D11: `cp` (never `mv`) the retained file `notes/matched_cborg_2026-09-14_v10d/.local_drafts/v10z_registration/reboot_recovery_2026-09-20/native_binary/claude-2.1.272-darwin-arm64` (in the primary checkout only: gitignored and absent from worktrees) to a path outside `~/.local/share/claude/versions`; `chmod u+x` on the copy only; verify sha256 195e24e8e1f9… and `codesign`; then run `--version`;
- a pre-launch weekly-headroom check (#2370);
- either a stop on `isUsingOverage` or a rejected status, or a recorded owner statement that extra usage stays disabled (D14).

* **Depends on:** N6
* **Cost:** $0
* **Gate:** Reviewed and merged before N7; the copy's hash and signature recorded
* **Issues:** #4759, #2370, #4693

#### N5 · maintainer-dev · docs preregistration

A native addendum to the analysis plan, written after N6's answers. It covers:

- the arm definition: adapter renderer 26 against the API's 25, transport, provider and thinking;
- effort as a fixed confound at N6's level;
- the cross-arm claims D09 permits;
- the native acceptance extras (N10);
- the label 'direct arm', unless D09 (b) is built;
- D25's canary rule and the weekly schedule;
- the overage policy.

* **Depends on:** P4, N6
* **Cost:** $0
* **Gate:** Reviewed, CI green, and merged by the owner before N7
* **Issues:** #4354, #3287, #4758, #3336

#### N6 · owner · owner decision

Owner sitting 2, at the #4354 merge: D11, the rest of D13, D14, D25, the native receipt parameters (#2926, #3336), and consent for the N7 saved-probe run.

* **Depends on:** N3
* **Cost:** Owner time
* **Gate:** Answers recorded on the issues
* **Issues:** #4759, #4019, #4162, #4445, #2370, #2926, #3336, #4760

#### N6b · owner · owner decision

Decide PR #2922 (#2714): merge it as a controller-closure version, or close it and accept the latent pid-reuse SIGKILL. If D10 is 'retire', it is released by Z1. If D10 is 'run', it is decided after audit28 closes (Z5). N6b does not depend on Z2.

* **Depends on:** G3; Z1 if D10 is 'retire'; Z5 if 'run'
* **Cost:** Owner time
* **Gate:** PR #2922 merged, or closed with a reason
* **Issues:** #2714, #2922, #4761

#### N7 · codex-operator · registration offline

A fresh CHORUS registration at the exact merged commit (#4693, #4703), from one neutrally named durable worktree and one neutrally named sibling inputs directory (A4's rule: no pilot, canary, date, replicate or arm token), used for every direct-arm run; its `PYTHONPATH` or venv resolves to that worktree. The adapter's `generation_context` sends the context and source-manifest file pins as absolute paths (`native_shared_contract.py:285-296, 619-633` at 0125eebbc), so these names reach the model as they do on the API arm. It uses claudecode_direct, generic_v10 through the adapter, the N4b runtime path, N6's effort level and the adapter's receipt floor: `{state: pending, mode: diagnostic_pilot}`, unless A15 has merged and N6 chooses the registered floor (`native_shared_contract.py:776-789` at 0125eebbc admits either). If N7 registers the A15 floor, it also builds an unlaunched draft CHORUS replicate registration (same floor, a replicate label, same worktree and inputs directory) for N7-rev's D25 diff. Then:

- the saved permission probe on the exact binary and instruction (owner-authorized at N6, unbilled, scripted local provider);
- exact CI evidence;
- the headroom check.

* **Depends on:** N3, N4a, N4b, N5, N6, N6b, G6
* **Cost:** $0
* **Gate:** `verify_saved_probe` reports checked and passed; the CI evidence is bound to the source
* **Issues:** #4354, #4693, #4703, #4760

#### N7-rev · independent-reviewer · review offline

Independent registration review, covering the byte pins, the effort level, the overage setting, the toolchain (#4019), the launch form (#4162), and no pilot or canary token in the label, paths or ids. For D25, when N7 registered the A15 floor, it diffs the model-facing inputs of the canary against those of N7's draft replicate registration.

* **Depends on:** N7
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the registration, CI and probe hashes
* **Issues:** #4354, #4019, #4162

#### N8 · owner · owner decision

The owner's `AUTHORIZE_ONE_NATIVE_ATTEMPT` word. It is bound to the registration, review, CI and probe hashes. It states `budget_guard_usd`, the deadline, the maximum starting seven-day utilization, the overage state and the keep-awake form. Check claude.ai usage before giving it.

* **Depends on:** N7-rev
* **Cost:** Owner time
* **Gate:** The word names all four hashes
* **Issues:** #4354, #2370, #4758

#### N9 · codex-operator · one canary run

BILLED (subscription). One CHORUS canary on the direct transport, under `caffeinate -ims`. Never resume a stopped attempt. Record the seven-day utilization before and after. Under a pending floor it is diagnostic and never counts as a CHORUS replicate (D03, D25).

* **Depends on:** N7-rev, N8
* **Cost:** No CBORG dollars; subscription quota, plus real dollars up to the $90 guard if extra usage is enabled and no overage stop exists (#2370). Prior direct CHORUS runtime estimates: $49.94 (v1, 2 h 35 m, completed and then disqualified, #2282) and $51.89 (v3, 3 h 21 m to blocking_limit, seven-day 0.96 to 1.0). The first v2 attempt's $7.76 covers 21 m 41 s of runtime (48 m 48 s wall) before ENOTFOUND, and the v2 retry (3 h 01 m) recorded none. The typed protocol adds stages
* **Gate:** Ends at completion, the deadline, `budget_guard_usd` or the utilization threshold, with outputs and stop reason preserved
* **Issues:** #4354, #2370

#### N10 · independent-reviewer · curator or human rating

Native acceptance:

- the A11 rows;
- tool-history checks: each chunk's receipt entry was written with the file tool before the next chunk was opened; the strict receipt check passed before any Phase 2 command; there were zero prescribed or unclassifiable permission denials; `scripts/agentic_observed.py --receipt R --manifest M` reports `receipt_chunks_unopened = 0`;
- an A12 blind source review.

maintainer-dev writes the acceptance record and the data PR (copies, not moves); the data PR is reviewed (artifact sha256s checked against the acceptance record) before the owner merges.

* **Depends on:** N9
* **Cost:** Reviewer time
* **Gate:** Accepted: the first accepted Claude Code shared-protocol record, in the direct arm unless D09 (b) is built
* **Issues:** #1782, #1801, #1815, #1816, #2924, #2079, #4445

#### N11-reg · codex-operator · registration offline

Production on this vehicle under the A15 floor, with the count set by D25: CHORUS ×3; AI_READI, CM4AI and VOICE ×3 each, plus a canary each unless D25 counts it as replicate 1; VOICE_PEDIATRIC as D02 sets it (×1 recommended); Kids First ×1. Each run has its own registration at N7's merged commit, from N7's worktree and inputs directory, through N9's launch form; if `src/` has moved, re-canary CHORUS first. Runs are scheduled across weekly windows from N9's measured utilization, within D07's per-cell bound.

* **Depends on:** N10, A15
* **Cost:** $0
* **Gate:** No refusal per registration
* **Issues:** #1763, #3336, #2926

#### N11-rev · independent-reviewer · review offline

N7-rev's review for each registration. Repeat the D25 diff against the real CHORUS replicate registrations before N9 is counted as replicate 1.

* **Depends on:** N11-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval per registration
* **Issues:** #1763

#### N11-word · owner · owner decision

One owner word per run, naming its hashes, guard, deadline, utilization threshold, overage state and the keep-awake form.

* **Depends on:** N11-rev
* **Cost:** Owner time
* **Gate:** Each word is recorded verbatim
* **Issues:** #1763, #2370

#### N11 · codex-operator · full arm

BILLED (subscription). The production runs, one per word. Each project's canary is accepted before its replicates run.

* **Depends on:** N11-rev, N11-word
* **Cost:** Subscription quota, plus up to the $90 guard per run if overage is enabled; unmeasured until N9
* **Gate:** Each run is accepted under N10, or recorded as failed
* **Issues:** #1763, #3336, #2926

#### N12 · maintainer-dev · code fix offline

Only if D09 chooses (b): build the CBORG claudecode_agent transport for the shared protocol. It needs:

- a second registered route and auth form;
- method admission in `native_execution_registration` and `native_shared_contract`;
- the proxy's ledger admission, reservation and settlement;
- the thinking-display substitution;
- stall controls;
- a probe variant;
- a budget source.

It is a new registered condition with new comparability claims. Its first run would follow N7–N10 under its own registration, review and word.

* **Depends on:** N3, G3
* **Cost:** $0 to build. Runs would bill CBORG; the generic_v9 native generation attempts' costs are withheld here (G3)
* **Gate:** Independent review and CI green at the exact head
* **Issues:** #4758, #4354

### Z. Frozen v10z CBORG native lineage (generic_v9, audit28)

Close the open-ended hold. Retiring (Z1, Z2) costs $0 and releases three PRs and four issues. Running audit28 (Z3–Z5) yields at most one composite generic_v9 record, so it is bounded to one attempt.

#### Z1 · maintainer-dev · docs pr offline

If D10 is 'retire', open a dated notes PR that:

- records the lineage's outcome, split three ways: the v10z lineage (generation d4810ca2 plus 26 billed audits); the matched native sequence (9 generations plus 26 audits); and the shared ledger total, which also holds the 15 CHORUS API attempts and the transport probe. Following G3, it gives no amounts, as the v10z records give none. No pair was accepted, and all artifacts are preserved;
- records in the new dated note that the 32-job generic_v9 v10z workload and the generic_v9/r17 direct registrations are superseded by generic_v10; it edits no existing file under `notes/matched_cborg_*`;
- adds the missing outcome note for the third direct canary (2026-09-25: blocking_limit, seven-day utilization 0.96 to 1.0, no overage; evidence untracked in `d4d-executions/direct-canary-3`);
- records the G3 withdrawal of the v10z standing authorizations (D22);
- points the held items at #4761.

* **Depends on:** G3
* **Cost:** $0
* **Gate:** Reviewed, CI green, merged by the owner
* **Issues:** #4761, #2114, #1763, #2370, #4758

#### Z2 · owner · owner decision

The owner decides each released item separately:

- PR #2910 (#2605);
- PR #4387 (#4009);
- issues #2909, #3879, #3785 and #3856.

PR #2922 (#2714) is decided at N6b.

* **Depends on:** Z1
* **Cost:** Owner time
* **Gate:** Each is merged, or closed with a reason
* **Issues:** #2910, #4387, #2605, #4009, #2909, #3879, #3785, #3856

#### Z3 · codex-operator · registration offline

Only if D10 is 'run':

- run `d4d-executions/lineage-durable/lineage_durable.py restore`, then verify; all 46 roots in its manifest are absent (re-checked 2026-10-09 17:08Z);
- copy 2.1.272 to its registered path, `~/.local/share/claude/versions/2.1.272`, and verify sha256 195e24e8…;
- prepare from compatible checkout 3de6cd7d9, whose `schema_digest.py` and `profiles.py` match the v10z pins. First write a review of how its versioned `api_runner.py` and `evidence_assertions.py` differ from audit27's compatible source;
- connect to the LBL network with the pinned CA for `api-local.cborg.lbl.gov`;
- prepare with `--native-thinking-display summarized`, stall controls, `--automatic-stop-reconciliation` and `--budget-amendment` set to the chain's budget-amendment file, which sits beside `budget_authorization_2026-09-26.json` in `notes/matched_cborg_2026-09-14_v10d/.local_drafts/v10z_registration/audit28_budget_authorization_2026-09-26/` (gitignored local evidence in the primary checkout);
- collect CI evidence.

* **Depends on:** G3
* **Cost:** $0
* **Gate:** Preflight passes
* **Issues:** #4761, #4759, #2114

#### Z3-rev · independent-reviewer · review offline

Independent review of the audit28 registration, including the versioned-file differences.

* **Depends on:** Z3
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the registration hash
* **Issues:** #4761, #2114

#### Z4 · owner · owner decision

The owner's word naming the audit28 registration hash, a $60 per-job cap (proposed here, the same as audit27's), and the pre-committed rule: one attempt, and a stop or rejection retires the lineage. The v10z standing authorizations are withdrawn at G3 (D22), so this word is the only authority for the attempt; if the registration keeps `--automatic-stop-reconciliation`, the word also states that it may debit an unconfirmed charge at its full reservation for this attempt.

* **Depends on:** Z3-rev
* **Cost:** Owner time
* **Gate:** The word names the hash
* **Issues:** #4761

#### Z5 · codex-operator · one canary run

BILLED. Run audit28 under `caffeinate`, then run `lineage_durable.py snapshot`. The exact Phase 3 audit then needs independent acceptance.

* **Depends on:** Z3-rev, Z4
* **Cost:** Cap $60. The per-audit costs of audits 11–27 and the chain's remaining headroom are withheld here (G3). 0 of 26 billed audits have been accepted
* **Gate:** Accepted; otherwise retire (Z1)
* **Issues:** #2114, #4761, #1849

#### Z6 · maintainer-dev · code fix offline

Only if Z5 is accepted: design and register the Phase 4 continuation (#2114): reconciliation, final core, report, composite provenance.

* **Depends on:** Z5
* **Cost:** $0 to build
* **Gate:** Reviewed, CI green, merged
* **Issues:** #2114

#### Z6-rev · independent-reviewer · review offline

Independent review of the Phase 4 registration.

* **Depends on:** Z6
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the hash
* **Issues:** #2114

#### Z6-word · owner · owner decision

The owner's word naming the Phase 4 registration hash and a cap.

* **Depends on:** Z6-rev
* **Cost:** Owner time
* **Gate:** The word names the hash
* **Issues:** #2114

#### Z7 · codex-operator · one canary run

BILLED. Run Phase 4, then final-pair acceptance. Evaluation, and a generic_v9 Kids First run, come only after that, each under its own registration, independent review and word naming its hash and cap.

* **Depends on:** Z6-rev, Z6-word
* **Cost:** No recorded basis
* **Gate:** An accepted composite generic_v9 pair
* **Issues:** #2114, #1763

### R. Direct arm under generic_v9 (claudecode_direct, renderer 17, effort max)

Give the 2026-09-25 pause an explicit, recorded scope, so it stops deciding silently whether the shared protocol can run. No spend unless the owner resumes the arm.

#### R1 · owner · owner decision

Under D09, record on #4758 that the generic_v9/r17 direct arm stays paused and is superseded. Its condition has no comparator, and the subscription transport's next use is N9.

* **Depends on:** G3
* **Cost:** Owner time
* **Gate:** Recorded on #4758
* **Issues:** #4758, #2370

#### R2-reg · codex-operator · registration offline

Only if the owner resumes this arm: a new generic_v9/r17 registration with the #4760 probe and the #4759 runtime (N4a, N4b), the #2370 headroom and overage guards, and exact CI.

* **Depends on:** R1, N4a, N4b
* **Cost:** $0
* **Gate:** The probe verifies; no refusal
* **Issues:** #2370, #4760, #4759

#### R2-rev · independent-reviewer · review offline

Independent registration review.

* **Depends on:** R2-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the hashes
* **Issues:** #2370

#### R2-word · owner · owner decision

The owner's word naming the hashes, guard, deadline, utilization threshold and overage state.

* **Depends on:** R2-rev
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #2370

#### R2 · codex-operator · one canary run

BILLED (subscription). One CHORUS canary. Kids First follows only after that canary is accepted, under its own registration, review and word; its first run on the project-neutral launcher (#4010) is treated as a canary.

* **Depends on:** R2-rev, R2-word
* **Cost:** Subscription quota, plus up to the $90 guard if overage is enabled. The three attempts not cut short by machine sleep ran 2 h 35 m to 3 h 21 m; the two with a runtime estimate came to $49.94 (v1) and $51.89 (v3)
* **Gate:** Accepted under N10's checks
* **Issues:** #2370, #4010

### M. Monolithic API condition (#4013)

Only if the paper needs it: one registered, provenance-bearing canary of the original 'api' approach (one call: prompt plus full schema plus documents), at a few dollars per attempt.

#### M1 · owner · owner decision

Decide D16: whether the arm is needed and, if so, its definition, prompt, route, model, thinking, cap and post-processing.

* **Depends on:** G3
* **Cost:** Owner time
* **Gate:** Recorded on #4013
* **Issues:** #4013

#### M2 · maintainer-dev · code fix offline

Engineering PR for monolithic_v1. A minimal `api_runner` path:

- one full phase;
- the merged 3.0.0 schema (1,442,513 bytes) in place of the digest;
- no receipt, audit or repair;
- at most one attempt;
- `api_usage` and provenance written by the existing record writer;
- method directory claudecode_api_monolithic, with `_core` produced by `d4d derive core`.

Commit the chosen prompt, then pin it with `d4d api prompts pin --file <the committed prompt path> --reason '<why this is the text>'`, adding a `CONDITION_PROMPTS` entry and a delimited label token.

M2 also defines what M5-reg and M6-reg write and how those runs launch. Today's API commands accept a registration only for shared generation and receipt completion (`cli/api.py:590-597, 676-683`), and the A4b-form launcher refuses `d4d api run`. M2 therefore defines:

- the monolithic run registration: the commit it is prepared at (the base that A8's later-word check compares HEAD with), the route (provider and base_url, as M1 decides), the prompt pin's sha256, the merged schema's sha256, the bundle md5, the model, the thinking setting, max_tokens, the label and the method directory;
- the exact `d4d api batch` line that takes it, with whatever condition flag and arm or method selector M2 adds so that outputs land under claudecode_api_monolithic (today `--arm baseline` writes under claudecode_api), plus `--projects`, `--replicates 1`, `--label-prefix` and `--yes`.

Then tests, adversarial review, CI and the owner's merge. Later, M5-rev and M6-rev review that registration, and M5-word and M6-word name its sha256 and the cap.

M2 lands before A4 (in the launch base) or after the API matrix completes. If it lands mid-matrix it is a D17 change: the launch worktree never advances over it except by D17's procedure, and the parity statement covers it.

* **Depends on:** M1
* **Cost:** $0
* **Gate:** Merged, with the prompts at their pins
* **Issues:** #4013

#### M3 · maintainer-dev · local deterministic recompute

Run `d4d api plan` offline for CHORUS (about 1.48 MB per request) and AI_READI (about 1.99 MB). Confirm the route's input window: `context_facts` returns no limit for bare claude-opus-5 (`api_runner.py:4187`), and a code comment says 1M in, 128k out.

* **Depends on:** M2
* **Cost:** $0
* **Gate:** Estimates recorded and inside the confirmed window
* **Issues:** #4013, #777

#### M4 · owner · owner decision

Merge a dated monolithic addendum to the analysis plan. It states the question being answered and uses the generic_v10 API arm as the comparator. Only validation, rubric and presence scores and blind source review are compared, because the arm has no receipts and no report gate. The addendum PR gets P3's review (a Claude reviewer plus a Codex CLI pass), with each finding filed as an issue, before the owner merges.

* **Depends on:** M3, P4
* **Cost:** Owner time
* **Gate:** Addendum reviewed and merged
* **Issues:** #4013

#### M5-reg · codex-operator · registration offline

The CHORUS monolithic registration M2 defines, from a durable worktree through a launcher of A4b's form.

* **Depends on:** M4, A10
* **Cost:** $0
* **Gate:** No refusal
* **Issues:** #4013

#### M5-rev · independent-reviewer · review offline

Independent registration review.

* **Depends on:** M5-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the hash
* **Issues:** #4013

#### M5-word · owner · owner decision

The owner's word naming the hash, a cap and a 1 h stall stop.

* **Depends on:** M5-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #4013

#### M5 · codex-operator · one canary run

BILLED. One CHORUS monolithic canary under `caffeinate`, run after A10 has exercised the D06 runtime on the same route, with A10's pre-launch hash check of the registration and the launcher. One attempt, with a 1 h stall stop: #777 records a VOICE full phase of about 523k tokens that stalled at 3,600 s.

* **Depends on:** M5-rev, M5-word, A10
* **Cost:** About $4.70–5.75 per attempt (see costs)
* **Gate:** Completes, or stops with outputs preserved
* **Issues:** #4013, #777, #1849

#### M5-acc · owner · owner decision

A11-style checks and an A12 review, then the owner's acceptance, recorded by data PR as in A13 and reviewed (artifact sha256s checked against the acceptance record) before the owner merges.

* **Depends on:** M5
* **Cost:** Owner and reviewer time; $0
* **Gate:** Accepted before M6
* **Issues:** #4013

#### M6-reg · codex-operator · registration offline

The AI_READI monolithic registration, prepared only after M5 is accepted and M3 has confirmed the window.

* **Depends on:** M5-acc, M3
* **Cost:** $0
* **Gate:** No refusal; the request fits the confirmed window
* **Issues:** #4013

#### M6-rev · independent-reviewer · review offline

Independent registration review.

* **Depends on:** M6-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the hash
* **Issues:** #4013

#### M6-word · owner · owner decision

The owner's word naming the hash and a cap.

* **Depends on:** M6-rev, and an A8 re-run recorded beside its registration
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #4013

#### M6 · codex-operator · one canary run

BILLED. One AI_READI monolithic attempt, with A10's pre-launch hash check of the registration and the launcher.

* **Depends on:** M6-rev, M6-word, M5-acc
* **Cost:** About $5.20–6.65 per attempt (see costs)
* **Gate:** Accepted, or recorded as failed
* **Issues:** #4013, #777

### E. Evaluation and comparator re-measurement (gates claims, not launches)

Measure the v10 records and the v8 comparator with the same blinded, current instruments, in a comparison batch kept separate from acceptance, and pay for rubric scoring once.

#### E1 · maintainer-dev · code fix offline

Build an evaluation route that reads `shared_generation_registration_v1`; the matched evaluation controller cannot. Also write a successor to `scripts/reference_rescore.py` that:

- pins contexts by hash on every job;
- runs a rubric20 repeat panel (#2912: at least 2 extra rubric20 ratings of one fixed record per project, CM4AI v7 rep2 among them);
- selects CBORG explicitly, as `scripts/reference_rescore_cborg.py`'s `cborg_environment()` does, and refuses a session whose init line does not read `apiKeySource: ANTHROPIC_API_KEY`. `scripts/reference_rescore.py` alone inherits the environment's login, which is how the 2026-09-11 pass ran on a claude.ai subscription;
- names the instrument version explicitly (3.0, or 4.0 for rubric20 per #2911);
- uses `d4d agents preamble` and `check-echo` (#1077);
- strips labels and provenance headers from rating copies where feasible (#3280).

* **Depends on:** P4
* **Cost:** $0
* **Gate:** Reviewed, CI green, merged
* **Issues:** #2912, #2911, #3280

#### E2 · independent-reviewer · curator or human rating

The comparison batch, separate from acceptance reviews. It covers the 12 v8 confirmatory records (04f/04g rep1–3) and the 12 v10 confirmatory records (the CHORUS gate plus production), shuffled and label-stripped where feasible (#3280). They are reviewed blind under the A12 protocol, with D24's counts and denominators. No v8 record has yet been reviewed under the #1782–#1816 protocol.

* **Depends on:** A17-acc
* **Cost:** Reviewer time (24 reviews)
* **Gate:** Dated reviews bound to the record sha256s, with reviewers blind to arm
* **Issues:** #1782, #1801, #1815, #3287, #3280

#### E3 · curator · curator or human rating

#2912: a named human reviews the five applicability contexts and settles their null predicates. A companion review pins the hashes.

* **Depends on:** none
* **Cost:** Curator time
* **Gate:** Companion review recorded
* **Issues:** #2912

#### E4 · owner · owner decision

#2911: the owner chooses rubric20 3.0 or 4.0. If 4.0, the owner reviews its normative examples and approves the 9-case Q19 calibration.

* **Depends on:** none
* **Cost:** Owner time
* **Gate:** Recorded on #2911
* **Issues:** #2911

#### E5-reg · codex-operator · registration offline

An evaluator canary registration under the E1 route: one accepted generic_v10 record, the instrument named explicitly, contexts pinned by hash, and preamble plus check-echo.

* **Depends on:** E1, E3, E4, G6, A13
* **Cost:** $0
* **Gate:** No refusal
* **Issues:** #2912, #2911

#### E5-rev · independent-reviewer · review offline

Independent review of the evaluator registration.

* **Depends on:** E5-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the hash
* **Issues:** #2912

#### E5-word · owner · owner decision

The owner's word naming the hash and a $5-per-attempt cap. The v10z evaluation authorization does not apply: it never extended to generic_v10 and is withdrawn at G3 (D22).

* **Depends on:** E5-rev
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #2912, #1763

#### E5c · codex-operator · one canary run

BILLED. One evaluator canary.

* **Depends on:** E5-rev, E5-word
* **Cost:** $5 cap per rating attempt
* **Gate:** Completes
* **Issues:** #2912

#### E5-acc · owner · owner decision

`validate_evaluation_schema.py --file` exits 0 and `check-echo` passes; then the owner accepts. A failed evaluator canary stops expansion.

* **Depends on:** E5c
* **Cost:** $0
* **Gate:** Accepted
* **Issues:** #2912, #2911

#### E5b-reg · codex-operator · registration offline

One joint registration that rates every accepted generic_v10 API-route record (claudecode_api, and claudecode_agent_crate under #2914 B), re-rates the 12 v8 comparator records under the same instrument, with label-stripped copies, and runs E1's rubric20 repeat panel. #2912 names CM4AI v7 rep2 among the panel's fixed records, and E5 rates no other v7 record, so the registration either adds it to its inputs or records on #2912 which CM4AI record replaces it. Under #2914 B every accepted record includes the 4 with-crate records, so it also waits for A22-acc; if D04 is Defer, A21–A22 never run and that dependency does not apply.

This joint pass does not rate direct-arm records: this plan excludes them so that the API ratings do not wait for N11 to finish. Rating the direct arm would need its own registration, review and word after N11, and no step yet schedules it.

* **Depends on:** E5-acc, A17-acc, A18-acc, A19-acc, A22-acc
* **Cost:** $0
* **Gate:** No refusal
* **Issues:** #2912, #3287, #2914

#### E5b-rev · independent-reviewer · review offline

Independent review of the joint registration.

* **Depends on:** E5b-reg
* **Cost:** $0; reviewer time
* **Gate:** Written approval bound to the hash
* **Issues:** #2912

#### E5b-word · owner · owner decision

The owner's word naming the hash and a cap.

* **Depends on:** E5b-rev
* **Cost:** Owner time
* **Gate:** The word is recorded verbatim
* **Issues:** #2912

#### E5 · codex-operator · full arm

BILLED. The joint rating pass. Each new output must pass `validate_evaluation_schema.py --file` with exit 0. If run like the 2026-09-12 CBORG rescore (`notes/reference_rescore_2026-09-12_cborg_runtime/`), these are Claude Code CLI sessions on CBORG: agentic evaluation calls, not generation. The 2026-09-11 rescore ran on a claude.ai subscription login, so it is not this route's precedent (E1).

* **Depends on:** E5b-rev, E5b-word
* **Cost:** About 66–70 ratings in all: 56–60 primary (24 v8 re-ratings plus 16–18 v10 API records under two rubrics) and a rubric20 repeat panel of at least 10 (two per Bridge2AI project, #2912; 12 if Kids First is included, which adds 2 ratings to every count here). Under #2914 B, the 4 with-crate records add 8 primary ratings, for 74–78 in all. At the 2026-09-12 CBORG rescore's rate of at least $2.88 per accepted rating ($161.3993945 known CLI subtotal for 56 accepted ratings from 63 sessions; 7 excluded, 2 of them interrupted and unpriced) that is about $190–202 ($213–225 under B). The $5 cap is per attempt: $330–350 ($370–390 under B) if every attempt is accepted, or about $371–394 ($416–439 under B) if that rescore's ratio of 63 sessions per 56 accepted ratings repeats. Direct-arm records are not included (E5b-reg)
* **Gate:** The exact-file validator exits 0 for every output
* **Issues:** #2912, #2911, #3287

#### E6 · maintainer-dev · local deterministic recompute

Run the confirmatory analysis exactly as preregistered:

- report effects at package level against v8;
- report VOICE_PEDIATRIC and Kids First descriptively;
- count every attempt, stopped and rejected ones included;
- name each metric's instrument and denominator.

Then update `arm_comparison` with denominators and explicit missing cells. The owner approves the outward wording: no gold standard; package-level effects; runtime claims only as D09 permits; costs given as estimates.

* **Depends on:** E2, E5, E7, A18-acc, A19-acc
* **Cost:** $0
* **Gate:** Analysis note reviewed, numbers reproducible, wording approved
* **Issues:** #2930, #3287, #2932, #1763

#### E7 · maintainer-dev · code fix offline

Fix #4762 so that `arm_comparison` computes each arm's bundle drift instead of asserting that every arm matches. On v6, AI_READI, CM4AI and VOICE drifted.

* **Depends on:** none
* **Cost:** $0
* **Gate:** Reviewed, CI green, merged by the owner
* **Issues:** #4762

#### E8 · maintainer-dev · local deterministic recompute

Optional. #4765 Part B, after #2929's paid fitness run (which needs its own registration, independent review and word naming its hash and cap): a per-arm fitness failure-class table. Any rule it adopts goes into the next shared-generation version, never into generic_v10 (D17). Part A (whether merged records ship) is not a generation step.

* **Depends on:** none
* **Cost:** $0 here
* **Gate:** Not scheduled before #2929's run; no effect on generic_v10 inputs
* **Issues:** #4765, #2929

## Remaining generations

| Arm | Projects | Replicates | Condition | Exists today | Status |
|---|---|---|---|---|---|
| API: claudecode_api (Messages SDK via CBORG, claude-opus-5) | CHORUS | 1 diagnostic pilot, never a replicate (D03); at most 1 contingency under a new prefix (D07) | generic_v10 / shared_generation_v1 (renderer 25, API playbook v2, receipt completion v2, typed worker/omission/integration audit), D06 thinking display, pending diagnostic_pilot floor | None: no generic_v10 record anywhere (gitignore-independent `find` over the primary checkout's `data/`, the `d4d-executions` worktrees and the `/private/tmp` clones, 2026-10-09). Comparators on the identical bundle 9b2ef4b6: v8 2026-09-04f rep1–3 ($4.37, $6.12, $4.42) and v9 2026-09-12 rep1 ($3.31), recomputed at `run_telemetry` rates on 2026-10-09 at 15d053d1a | Not started; no engineering blocker on main 15d053d1a. Waits on G3, P4, A2, A2c, A1/A1b sizing and A6–A9 (registration, review, word). |
| API: claudecode_api | AI_READI | 1 diagnostic pilot; at most 1 contingency under a new prefix (D07) | generic_v10, pending diagnostic_pilot floor | None. Comparator v8 2026-09-04g rep1–3 on the identical bundle d22b61a9 ($10.54, $13.66, $9.97); never 04f rep1, which its own validation block declares invalid | Runs after the CHORUS pilot is accepted (A13). Model-facing values stay as fixed at A6; only non-model-facing allowances are re-sized. v8 AI_READI full phases used 112,321–115,616 of the 128,000-token output cap. |
| API: claudecode_api | CHORUS | 3 fresh replicates: the #3336/#2932 gate, also the CHORUS production cells | generic_v10, registered numeric receipt floor (a new registration identity; same prompt condition) | None | Needs both pilots accepted, the A15 floor, CBORG's #1849 answer or a written risk acceptance, A2c, and its own review and word. Gated on absolute floors only; a stop closes the roster and remaining cells continue under a new prefix (D21). |
| API: claudecode_api | CM4AI, VOICE, AI_READI (in that order) | 3 each (9 runs) | generic_v10, registered floor | None. The v8 comparators read identical bundles (50037fc6, 9193c3cb, d22b61a9) | After A16 is accepted. One roster per project under its own date-letter prefix, each with its own review, word and cap re-estimated from actuals. |
| API: claudecode_api | VOICE_PEDIATRIC | 1 recommended, or 3 (D02) | generic_v10, registered floor | None in any API condition. Its agentic records (2026-08-07 v3, 2026-08-11 generic) read other bundles; nothing on today's bundle 03502237 | Descriptive. Its six source ids are a subset of VOICE's eleven (`source_manifest.yaml` at 15d053d1a), so it pools with VOICE. Runs after A17 on absolute floors (no comparator on any arm). |
| API: claudecode_api | KIDS_FIRST | 1 | generic_v10, neutral profile, its own scope context and registration, registered floor (D15) | None on any arm. Frozen inputs on main under `notes/matched_cborg_2026-09-13/kids_first/` (bundle 541,184 bytes, 58 chunks, chunk rule version 2) | After the AI_READI pilot is accepted and A15 exists (A19). External and descriptive; no expansion. |
| API via the de_novo arm: claudecode_agent_crate (shared protocol) | CHORUS (with-crate bundle) | 1 canary + 3 replicates, only if D04 is B | generic_v10, registered floor, CHORUS context unchanged | Stale only: claudecode_agent_crate 2026-07-31 api-generic rep1–3 under the unversioned generic prompt. Inputs on main: `CHORUS_preprocessed_with_crate.txt` (65,749 bytes) and its chunk manifest; `_shared_spec` admits the arm (`cli/api.py:24-26, 85-89`) | Scheduled after A16 is accepted (A21–A22). No `--canary-baseline`: `canary.baseline_for` searches only claudecode_agent, claudecode_api and claudecode_direct (`runs.py:77`). |
| Claude Code shared protocol via the #4354 adapter: claudecode_direct on the claude.ai subscription (the direct arm, not native) | CHORUS canary, then AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC and KIDS_FIRST | With VOICE_PEDIATRIC ×1 as D02 recommends: 15 runs if each later project's canary counts as replicate 1, otherwise 18; with ×3, 17 or 21 (D25). Each count includes N9 as a diagnostic CHORUS canary: under a pending floor it never counts as a replicate (D03) | generic_v10 shared contract (adapter renderer 26; the API side is renderer 25) | None. Adapter not on main: `review/4354-offline-acceptance` (0125eebbc) is 95 ahead and 125 behind 15d053d1a (merge-base 286b88688). PR #4659 (38fb11d5d) fails shard 1, shard 3 and test (as of 2026-10-09 17:08Z). Owner-lifetime fixes are local only: terminal-source was at aa09dbbc6 at the 2026-10-09T08:58Z re-check and has moved since (f00bcb5df as of 2026-10-09 17:08Z, unpublished); #4740's last recorded result (2026-10-09T07:41Z) is at aa09dbbc6 (#4763, #4764) | Blocked on engineering: #4740 still fails at aa09dbbc6 (2026-10-09T07:41Z). Also needs D09, N3 delivery from a separate branch, #4760, #4759, N6 decisions, a fresh registration, review and word. |
| Native on CBORG: a claudecode_agent transport for the shared protocol | Same cells | Same as above | generic_v10 | None, and no code path: `shared_generation.py:573` reads `'native_direct': 'unsupported; separate adapter required'`, and native_execution admits only claudecode_direct on a first-party login (`native_execution_registration.py:108-110, 167`) | Built only if D09 chooses (b) (N12). Under the recommended options the plan has no CBORG-native generation; the owner must confirm that departure from 2026-09-25. |
| Native frozen v10z controller: claudecode_agent via the CBORG proxy | CHORUS | rep1 | generic_v9 renderer 14; audit protocol 7 / renderer 23 | Frozen full record, core and receipt from 2026-09-18 (generation d4810ca2); 26 billed audits plus the unbilled audit10, their costs withheld here (G3); none accepted; audit28 unregistered | Cannot launch as registered: 2.1.272 pruned (#4759; as of 2026-10-09 17:08Z only 2.1.291–2.1.295 were installed, and 2.1.296 arrived at 18:38Z); main's `schema_digest.py` (2626779774de…) differs from the pinned 980ab77322fa… (#4761); Phase 4 (#2114) unbuilt. D10 recommends retiring it (Z1). |
| Rest of the v10z workload (API and agentic) | Both arms for AI_READI, CM4AI, VOICE, VOICE_PEDIATRIC and KIDS_FIRST; CHORUS API ×3; CHORUS agentic rep2–3 | 31 of the 32 registered jobs | generic_v9 renderer 14 | 0. `notes/matched_cborg_2026-09-18_v10z/workload.public.json` calls itself 'proposed_workload_inventory_not_a_launch_registration' | Superseded by generic_v10. Z1 records this in a new dated note, so no cell is filled under two conditions. |
| Direct: claudecode_direct (claude.ai subscription, effort max) | CHORUS, then KIDS_FIRST | 1 + 1 canaries; no production matrix registered | generic_v9 renderer 17 | 4 attempts across 4 registrations, none accepted (a $60 sibling of the first v2 registration, 3ece0fe5…, was prepared and retired unlaunched): v1 disqualified (#2282); v2 stopped on ENOTFOUND during machine sleep; the v2 retry stopped at the terminal evidence check (#2427, closed); v3 stopped at blocking_limit, seven-day utilization 0.96 to 1.0, no overage. The v3 outcome note is not on main | Paused since 2026-09-25. Keep paused and superseded (R1); the next use of the subscription transport is N9. |
| Monolithic API (prompt, full LinkML schema and documents in one call) | Owner to define. Proposal: a CHORUS canary, then AI_READI | Owner to define | Unregistered (#4013) | No current record. Legacy flat files `data/d4d_concatenated/claudecode/*_d4d.yaml` (2026-04-24) carry no provenance; the legacy prompts are not pinned in `canonical_hashes.yaml` | Depends on D16 (is it needed), then a small runner path (M2), and its own registration, review and word per run (M5, M6). |
| Other input arms: crate-only, healthsheet, merged (`claudecode_agent_crate_only`, `_healthsheet`, `_merged`) | CHORUS, CM4AI, VOICE (crate-only); AI_READI (healthsheet); four projects (merged) | 3 each recorded; merged records derive from three replicates | Unversioned 2026-07-31 api-generic (merged: 2026-07-29 derived records) | Yes, but stale; the merged records are derived, not generated | Outside the generic_v10 design. crate_only ('preferably' in #2914 B) is not planned. Whether merged records ship is #4765 Part A, not a generation. |

## Costs

| Item | Estimate | Basis |
|---|---|---|
| CBORG spend to date (shared matched-sequence ledger) | Withheld here (G3): 1,937 settled rows in 51 attempt groups. They are 15 CHORUS API attempts (the unsuffixed 2026-09-13 canary at $3.291465, then v10b, v10d, v10e, v10f_cap20 and v10g–v10p); 9 native generations, the v10z generation d4810ca2 among them; 26 billed native audits; and the transport probe | Grouped by attempt key on 2026-10-09 from `transport_probe_2463/billing.json`; its total equals `sequence_accounted_usd` in `budget_authorization_2026-09-26.json`. Both are gitignored local evidence under `notes/matched_cborg_2026-09-14_v10d/.local_drafts/v10z_registration/` (the second in `audit28_budget_authorization_2026-09-26/`) |
| Lineage splits (for Z1) | Withheld here (G3): the v10z lineage (generation d4810ca2 plus 26 billed audits) and the matched native sequence (9 generations plus 26 audits) | Same grouping |
| Money already authorized | The shared chain's cap and remaining headroom are withheld here (G3). The chain is the matched-sequence ledger: the September additional $200 allocation bounded that sequence's API and native attempts and its evaluation attempts alike, and was later raised on the same ledger, so it has no remainder apart from the chain's headroom. That headroom is not assumed for generic_v10 (D07, D22) | `budget_authorization_2026-09-26.json` (gitignored; chain origin d4810ca2). Scope: `notes/matched_cborg_2026-09-13/expansion_cost_draft.md:23`, the v10m and v10n cap tables (native agentic lines under the same allocation) and `notes/matched_cborg_2026-09-16_v10r/README.md:65-68`; the raise: `notes/native_audit_continuation_plan_2026-09-18.md` and #2468. The balances published while only API attempts had been charged ($196.708535 after the first canary in `notes/matched_cborg_2026-09-13_v10b/README.md`, $168.332762 after v10l in `notes/matched_cborg_2026-09-15_v10m/README.md`, $165.434368 after v10m in `notes/matched_cborg_2026-09-15_v10n/README.md`) equal $200 minus the cumulative API spend in the ledger; later balances are withheld here (G3) |
| Native audit pattern to avoid | The per-audit costs of audits 11–27 (median, range, audit27's) are withheld here (G3). 0 of 26 billed audits accepted | Same ledger, grouped by attempt key |
| v8 API production comparator (already paid; reused, not regenerated) | $93.69 for 12 records: CHORUS $14.92, VOICE $27.31, AI_READI $34.17, CM4AI $17.29; $4.37–$13.66 per run | `api_usage` rows in `claudecode_api_core/2026-09-04{f,g}_*/{P}_provenance.yaml` at the `run_telemetry.py` rates, recomputed on 2026-10-09 at 15d053d1a. Estimates, not invoices. Rows with transport errors carry partial usage (#1017) |
| Price basis for every estimate | $5/M input, $6.25/M cache write, $0.50/M cache read, $25/M output; no premium tier above 200k | `run_telemetry.py:41-46` ('CBORG-posted opus-5 rates (2026-08-05, `/model/info`)'). They reproduce the v8 and v9 figures exactly. Re-observe the catalogue before every word (A8) |
| v9 CHORUS API canary (reference) | $3.30811950 for 6 calls. Full phase: 501.7 s, input 41,339 tokens (9,636 uncached plus 31,703 cache write), output 46,182 | v9 provenance and its usage ledger `data/d4d_concatenated/claudecode_api_core/2026-09-12_claude-opus-5-api-generic-v9_rep1/CHORUS_api_usage_46d8033e251b3c6e.json`, both reproduced on 2026-10-09 at 15d053d1a |
| generic_v10 CHORUS pilot (A10) | Unmeasured. Scenario $5–12 (the cost-and-risk input plan's derivation, unpublished; not re-derived here). Cap $15, with an operator trigger near $11.50, because one in-flight CHORUS full call can cost about $3.45 | v9's ordinary phases without the legacy audit (about $2.9), plus one receipt-completion call that resends the full conversation, and W+2 uncached typed calls, each carrying at least 93,654 bytes of inputs plus the schema context. A1 and A1b replace the scenario |
| Pilot-phase allocation (D07) | $100: CHORUS pilot $15, one CHORUS contingency $15, AI_READI pilot $35 and one AI_READI contingency at most $35 (both AI_READI lines provisional) | D07. $65 has no line for the AI_READI contingency that A14-acc allows; $60 leaves $10 after the two pilots, less than a contingency's $15 cap |
| Terminal-failure exposure of single-delivery calls | At v8's rate (8 of 92 calls retried: 5 transport, 3 answer-level), runs end terminally 30% of the time with 4 single-delivery calls, 42% with 6 and 52% with 8. Transport alone: 20% (4 calls) and 36% (8 calls). A 3-row roster completes without a stop in 11–34% of cases, and both attempts of a cell fail in 9–27% | v8 04f/04g `api_usage`, recomputed on 2026-10-09. A run has W+3 single-delivery calls (W workers, omission, integration, receipt completion). Independence is assumed. Illustrative until the pilots measure typed-stage rates |
| Theoretical ceiling of one API run without an operator stop | About $100 for CHORUS (the cost-and-risk input plan's derivation, unpublished; not re-derived here) | Phase caps (full 128k; reconcile, report and repair 96k) × `MAX_ATTEMPTS` = 5 per ordinary phase (`api_runner.py:446`), plus the registered typed allowances. Neither `d4d api run` nor `d4d api batch` has a dollar cap |
| generic_v10 AI_READI pilot (A14) | Unmeasured. Scenario $17–33 (the cost-and-risk input plan, unpublished; not re-derived here). Planning ceiling $35, provisional until A1/A1b. One in-flight full call can cost about $4.50, so the operator trigger is about $30.50 at that ceiling | v8 AI_READI runs cost $9.97–$13.66, with full-phase cache writes of 203,662 tokens and outputs of 112,321–115,616 of 128,000. Each typed worker carries at least 761,799 bytes of inputs uncached |
| API production (A16–A18) | Not a forecast. 13 runs under the recommended options (CHORUS ×3; CM4AI, VOICE and AI_READI ×3; VOICE_PEDIATRIC ×1), or 15 with VOICE_PEDIATRIC ×3. The v8-equivalent cost of the 12 comparable cells is $93.69, plus the typed-audit and receipt increment and any D21 re-runs | v8 per-project totals. Bundle sizes: CM4AI 320,799, VOICE 376,446, AI_READI 542,513, VOICE_PEDIATRIC 206,008 bytes. Replace with pilot actuals before each roster word |
| Kids First API canary (A19) | Unmeasured; likely near the AI_READI pilot and above v10r's $15 cap | `notes/matched_cborg_2026-09-16_v10r/README.md` sets $10 (CHORUS) and $15 (Kids First) caps, both before the typed audit. Four pre-v10 phases reserved $13.84 (the full-generation, audit, reconciliation and report reservations, without carried outputs, in `notes/kids_first_budget_proposal_2026-09-14/README.md`). Initial request 233,161 tokens (`notes/matched_cborg_2026-09-13/api_initial_admission.json`). Bundle 541,184 bytes |
| #2914 path B with-crate runs (A21–A22, only if chosen) | 4 billed runs. Unmeasured; scale from the CHORUS replicate actuals | #2914 path B: one canary, then 3 replicates under the current prompt. The with-crate bundle is 65,749 bytes against CHORUS's 35,920 |
| Keeping the pilots diagnostic (D03) | Two extra runs; scenario $22–45 | One CHORUS and one AI_READI run at the input plan's scenarios above |
| Claude Code shared-protocol canary on the direct transport (N9) | No CBORG dollars; subscription quota. Real dollars up to the $90 guard if extra usage is enabled and no overage stop exists. Expect 2.5–3.5 h or longer | #2370. `notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md` ($49.94 estimate, about 2 h 35 m). `notes/claudecode_direct/CHORUS_direct_v2_2026-09-24_stopped.md` ($7.76 for the first attempt's 21 m 41 s; none for the retry). v3: the terminal result in `transcript.jsonl` (`total_cost_usd` 51.8889805, `duration_ms` 12,063,037) and `result.json` (blocking_limit, 0.96 to 1.0, `overage_used` false), both untracked under `d4d-executions/direct-canary-3/notes/claudecode_direct/.local_drafts/2026-09-25_CHORUS_v3/attempts/CHORUS_direct_rep1/` |
| audit28, only if D10 is 'run' (Z5) | $60 per-job cap, proposed here (the same as audit27's). The typical audit cost and the chain's remaining headroom are withheld here (G3). Phase 4 not costed | The ledger's audits 11–27 (withheld, G3); audit27's registered cap, `limits.attempt_cap_usd` in `notes/matched_cborg_2026-09-14_v10d/.local_drafts/v10z_registration/audit_continuation_27_fresh_responsive_r2/launch_review.json` (gitignored local evidence) |
| Retiring audit28 and the v10z lineage (Z1–Z2) | $0 | No provider calls. Releases three PRs and four issues |
| Monolithic canaries (M5, M6) | CHORUS about $4.70–5.75 per attempt; AI_READI about $5.20–6.65 | One call: the merged 3.0.0 schema (1,442,513 bytes), plus the bundle (35,920 or 542,513 bytes), plus 2,680 bytes of legacy prompts. At 2.9–5 bytes per token and $5/M, plus a full 128k output at $25/M |
| Evaluation (E5) | $5 cap per rating attempt. About 66–70 ratings: 56–60 primary (24 v8 re-ratings plus 16–18 v10 API records under two rubrics) and a rubric20 repeat panel of at least 10 (two per Bridge2AI project, #2912; 12 with Kids First). About $190–202 at $2.88 per accepted rating; at the cap, $330–350 if every attempt is accepted, or about $371–394 at the 2026-09-12 CBORG rescore's ratio of 63 sessions per 56 accepted ratings; plus the evaluator canary. Under #2914 B, 74–78 ratings (20–22 v10 records): about $213–225 at that rate, and $370–390 or about $416–439 at the cap. Direct-arm records are not included (E5b-reg) | `notes/reference_rescore_2026-09-12_cborg_runtime/completion_audit.json`, the CBORG rating condition: $161.3993945 known CLI subtotal (CLI-reported, not an invoice) for 56 accepted ratings from 63 sessions, 7 excluded, 2 of them interrupted and unpriced, so at least $2.88 per accepted rating, the allocation `notes/matched_cborg_2026-09-13/expansion_cost_draft.md:25` already uses. The 2026-09-11 rescore ($142.25036250 for 56 accepted ratings from 64 sessions) ran on a claude.ai subscription login (`apiKeySource: none` on every transcript's init line); its prompts name 'LBL CBORG (proxy to Anthropic)' only because they quote the rated records' provenance headers, so it is not a CBORG cost basis |
| Offline, review, decision and preregistration steps, and unbilled count calls | $0 provider spend | No generation calls. The v10e count-only admission recorded no settled cost. Owner, maintainer, curator and reviewer time only; Claude sessions draw on the subscription's weekly window |

## Risks

1. **Risk:** Rejection on the first pass is the norm. Nothing has been accepted from 15 executed CHORUS API canaries (the unsuffixed 2026-09-13 canary, v10b, v10d, v10e, v10f (run as its $20-cap amendment v10f_cap20) and v10g–v10p; v10c never ran), 9 native generations, 26 billed audits or 4 direct attempts. **Mitigation:** generic_v10 carries the #1782, #1801 and #1815 rules. One contingency per pilot cell (D07). P2 preregisters a stop-loss: two rejections in one defect class end re-running and schedule the next shared-generation version. Every retry gets a new label, registration and word.
2. **Risk:** Single-delivery terminal failure. Typed stages and receipt completion admit exactly one delivery (`{1, 0, 0}`; `shared_generation.py:226-228`). At v8's per-call rate (8 of 92 calls retried), 30–52% of runs with 4–8 such calls end terminally, and a 3-row roster under a registered floor completes without a stop in only 11–34%. **Mitigation:** The D06 display. CHORUS first. The pilots record per-stage failure rates (P2 item 18). D21's trigger at A15. One recorded retry on the next shared-generation version's list (G4). D08's risk acceptance states the estimate.
3. **Risk:** An end_turn with no usable answer is terminal on typed stages, and larger caps do not prevent it. Evidence: in v8 04g rep2 the first AI_READI audit ended end_turn after 18,487 thinking tokens, out of 18,488 output, under a 24,000 cap; CHORUS 04f rep2's first two full attempts ended end_turn (40,093 and 54,886 output tokens) and were retried; see also #777's header-only dud and #1849's empty successes. **Mitigation:** Record the empty-answer rate per stage in the pilots, and whether D06's display changes it. One recorded malformed-response retry goes on the next shared-generation version's list. Size the contingency from the measured rate.
4. **Risk:** AI_READI full phases ran close to the route's output cap: v8 used 112,321–115,616 of 128,000 tokens (thinking 66,469–72,735). v10's added rules could push AI_READI or Kids First to the cap (`output_limit` is 128k for bare claude-opus-5). Ordinary phases retry up to 5 times, each at full cost (about $4.50). **Mitigation:** Measured in the AI_READI pilot, with the operator trigger and A3b watching. If the pilot truncates, the owner re-plans before A16; nothing in this condition can raise the cap.
5. **Risk:** There is no dollar cap in code. An operator stop cannot recall a request already sent, and an interrupted stream may still bill (#1849). **Mitigation:** Trigger at the cap minus the pending phase's worst case, read live from A3b. A2c before A4, so before any billed run. The registered token allowances as the hard bound.
6. **Risk:** Typed-audit cost on large bundles. Every worker carries the bundle, both records, the receipt and the manifest (at least 761,799 bytes for AI_READI), plus a schema context that carries, for every occupied owner, that owner's complete value twice (YAML and a typed tree; the root owner is the whole record, so nested content recurs once per enclosing owner) and induced-slot JSON per class (`shared_generation.py:488-532`). There is no `cache_control`. **Mitigation:** A1 sizing and A1b exact counts before registration. Fewer, larger workers. D06's optional breakpoint. CHORUS first, with each cap set from actuals.
7. **Risk:** Run-specific strings reach the model: the full label (prompt v10 line 23); the absolute context and source-manifest pins in `generation_context` and the schema pins in the schema context, each a path with its sha256 and size (`shared_generation.py:244-248, 440-459, 530`); the raw receipt registration (`registration_id`, limits, `context_limit_basis` and floor) in every ordinary phase's base instruction (`api_runner.py:1470-1472`) and again in the completion turn (`receipt_completion.py:246`); the omission request's `max_request_bytes` and `max_output_tokens` (`audit_omissions.py:376-378`), so some `audit_limits` are model-facing; and binding hashes, the registration's sha256 among them (`typed_audit_runtime.py:131-132, 140`). **Mitigation:** One neutral worktree and one neutral inputs directory for the whole matrix, and the same rule for the direct arm (N7). Date-letter prefixes. Model-facing values fixed across projects (P2 item 14), listed by A6 from the `render-prompt` output and the registration and context files, and checked by A7 together with each row's top-level `registration_id`. G4 files the logical-path question for the next shared-generation version.
8. **Risk:** Pilot contamination: from the full phase onward, every ordinary phase's base instruction shows the model the receipt registration, floor included (`api_runner.py:1470-1472, 2784-2788`). **Mitigation:** Pilots stay diagnostic (D03). Within a roster, the receipt object is identical across rows, and a `render-prompt` diff shows any floor difference.
9. **Risk:** Drift inside the window would make registrations refuse, or split the matrix across inputs. Sources: schema releases (#3972, #3124), draft PR #4508, #2914 path A, a manifest edit (#3414), a preprocessing change (#2934), the #4354 merge, the monolithic runner path (M2), or the #4766 and A2c code. **Mitigation:** The D17 freeze: A2c lands before A4, M2 lands in the launch base or after the matrix, and the launch worktree advances only by D17's procedure, with a parity statement or re-registration and, for a code change, its step-7 canary. Native registrations only after the final merge, since they hash all of `src/` (#4693).
10. **Risk:** A launch could import the wrong code. The primary checkout's editable `.pth` points at its own `src`, on `feat/figure-set-2303-explore`: 1,185 commits behind 15d053d1a (as of 2026-10-09) and with no `shared_generation.py`. `data_sheets_schema` has no `__init__.py`, so a venv carrying that `.pth` merges both trees into the package's `__path__`, and a module the worktree lacked would import silently from the primary checkout. The record would still name the worktree's commit. **Mitigation:** The A4b launcher (the worktree's own venv, `PYTHONPATH`, and an import check that every `__path__` entry and five module files resolve inside the worktree's `src`), used for the dry-run, the checks and the launch alike.
11. **Risk:** Credentials and environment: the runner reads only the process environment, with no `.env` loading, and the primary checkout has no `.env`; `ANTHROPIC_API_KEY` takes precedence over `CBORG_API_KEY`; a `nohup` child can lack the key; a leftover `D4D_RECEIPT_FULL_MAX_TOKENS` or `D4D_PHASE_WALL_CLOCK_SECONDS` would lower the full-phase cap, or change the per-call watchdog, with nothing in the registration to show it. **Mitigation:** The launcher unsets `ANTHROPIC_API_KEY` and the two D4D overrides and refuses without `CBORG_API_KEY`. The A6 dry-run runs with the key set, so preflight checks the registered provider. A11 verifies the recorded route in the provenance `model` block (`api_usage` rows carry none) and the 128000 full-phase cap in every `full` row.
12. **Risk:** Rosters strand. There is no bypass under a registered floor, rosters start at rep1, and a re-run re-derives a stopped run's verdict, so one stop closes the prefix. A cell continued under a new prefix cannot be grouped by `d4d runs select`. **Mitigation:** D21: absolute floors, preregistered continuation under a new prefix, every attempt counted. The `d4d runs select` gap is filed (G4).
13. **Risk:** Gating against v8's per-project worst would stop rosters on bars that are mostly 0 (report findings: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0). **Mitigation:** D21 (b): absolute floors for production. The v8 comparison runs offline (report-only verdict, E6).
14. **Risk:** The v10z standing authorizations could be misread as covering generic_v10. They include 'all evaluations of the CHORUS d4d' and full-reservation debits, and an accepted A13 record could be taken as their trigger. **Mitigation:** The D22 ruling and the withdrawal of those authorizations at G3, whatever D10 decides, recorded on #1763 and #4761, and Codex's acknowledgment (G6) before any registration on either arm.
15. **Risk:** The #795 branch guard could refuse later runs. It keys on `{method}_core/{label}` (`run_guard.py:69-70`), a directory every project under one label shares, so outputs moved off disk onto a data branch block that label. **Mitigation:** Copy, never move, outputs into data-PR worktrees. Use a distinct prefix per roster. Never fast-forward the launch worktree over a merged data PR except by D17's procedure: git refuses to overwrite the untracked outputs even when they are identical.
16. **Risk:** Editing the Codex session's branches. PR #4659 targets `review/4354-offline-acceptance`, and the session is actively working #4740 and #4354. **Mitigation:** N3 uses a separately cut delivery branch. G1a takes bundle copies. G1b is the Codex session's own push.
17. **Risk:** Unpublished native work can be lost on reboot: seven branch heads exist only under `/private/tmp`, 4366dc20 is already lost, and all 46 lineage roots in the durable manifest are absent (re-checked 2026-10-09 17:08Z). **Mitigation:** G0, G1a and G1b today. Keep worktrees under `d4d-executions`. Run `lineage_durable.py snapshot` after any lineage write.
18. **Risk:** The updater prunes pinned runtimes; 2.1.272 has been removed at least twice. **Mitigation:** D11: a durable, executable copy, with its sha256 and signature verified at preflight and again at launch.
19. **Risk:** #4354 offline acceptance may not converge. #4740's latest result (2026-10-09T07:41Z) still fails at aa09dbbc6, and a warm-JSON candidate missed its preregistered thresholds. **Mitigation:** The D18 time-box. The API route proceeds independently.
20. **Risk:** Subscription runs can exhaust the weekly window (v3 started at 0.96 and stopped at 1.0), and a run that enters overage is not stopped (#2370). **Mitigation:** The D14 threshold. N4b's headroom check, plus an overage stop or extra usage kept disabled. Launch after a reset.
21. **Risk:** Comparability confounds: schema 2.0.0 against 3.0.0; the digest term-source change; renderer 25's typed audit and receipt completion; audit and report caps of 24k against 96k; the thinking display; transport and provider against the CBORG API arm; effort, the API provider default against an explicit Claude Code level, a fixed confound; renderer 26 against 25; and provider-side model drift under one model id. **Mitigation:** List every confound in P2. Make package-level claims only. Label direct cells as the direct arm. Record the returned model identity per call (G4).
22. **Risk:** Comparator measures do not transfer, and reviewers would know the arm. The v8 ratings use older instruments, and no v8 record was source-reviewed under the #1782–#1816 protocol. **Mitigation:** E2's shuffled, label-stripped comparison batch, separate from acceptance. One joint rating pass (E5). Rubric metrics stay secondary.
23. **Risk:** Pilot acceptance has no tool verdict. A pending floor is UNMEASURABLE by design, `d4d api verdict --execute` refuses to write it, and `d4d runs select` ignores acceptance. **Mitigation:** P2 names the rows that must be 0 and the acceptance-record format. The batch path writes the canary block. Canonical marks go only to accepted replicates, by procedure (A20).
24. **Risk:** Survivorship and small n: 15 API and 36 native attempts so far, n=1 pilots and n=3 cells. **Mitigation:** Count every attempt. Analyse pilots separately. Never choose a replicate by score. Use descriptive n=3 rules unless a tolerance is preregistered.
25. **Risk:** Open-ended authorizations: the v10z chain's cap was raised repeatedly while the audits kept failing (amounts withheld here; G3). **Mitigation:** D07's per-cell bound and allocation, D22's withdrawal at G3, and an owner review after two attempts in a cell.
26. **Risk:** Report totals are unchecked (#4766). The v10g report said 12 findings, 6 low, against 13 entries, 7 low. Five committed pairs show the same defect. **Mitigation:** A11's offline totals check. The code fix only under D17.
27. **Risk:** Overlapping roles: one session both develops and operates the same lineage. **Mitigation:** D12. For every registration, a reviewer who is neither its author nor its operator.
28. **Risk:** Scope contexts could import labels or diagnoses (#422), name the wrong release, or need nested scopes that cannot be declared yet. **Mitigation:** A curator writes them and an independent reviewer checks them (A5). Root scope only, unless a mapping exists. A null release means unknown.
29. **Risk:** Monolithic requests of about 300–690k tokens fall in the size class that stalled on CBORG (#777). **Mitigation:** Run only after A10. CHORUS first, one attempt, a 1 h stall stop. Consider the direct Anthropic route (D16).
30. **Risk:** Reviewer capacity: about 40–46 blind reviews (API acceptance plus the comparison batch), then one per direct-arm run (15–21) and 2 for the monolithic arm: about 57–69 in all, plus contingencies and re-runs. **Mitigation:** D23 names the reviewers and sets the schedule. Strip labels and provenance headers from review copies (#3280).
31. **Risk:** The Kids First chunk manifest lies outside the study-bundle gates, so A4 would not catch a stale one. **Mitigation:** A19-reg runs `d4d bundle chunk --bundle … --chunk-manifest … --check --strict` on the frozen files.

## Open questions

1. Does 'native' in the paper still mean the CBORG claudecode_agent arm, as on 2026-09-25? If so, how much engineering is N12 on top of the adapter? No estimate exists.
2. Which allocation funds generic_v10 (D07)? The candidates are a new allocation or part of the matched-sequence ledger's remaining headroom, the v10z chain, whose cap raised the September additional $200 allocation on the same ledger (amounts withheld here; G3). Whether that headroom may fund another lineage is unverified.
3. Does `api.cborg.lbl.gov` accept `display: summarized` on messages and on `count_tokens`, and is `count_tokens` unbilled there, as the v10e admission suggests (A1b)? Does CBORG honour a cache breakpoint on typed calls? Is its 270 s `stream_timeout` an idle limit or a total limit?
4. Is bare claude-opus-5 on CBORG really 1M input tokens? `context_facts` returns no limit for the bare name (`api_runner.py:4187`), while the config comment says 1M in, 128k out. The answer sets `context_limit_tokens` and decides whether AI_READI and Kids First typed workers fit.
5. Which `audit_limits` values reach request text, beyond `max_request_bytes`, `omission_output_tokens` and the worker-partition limits? A1's differential rendering answers this.
6. How large is the schema context that typed requests carry? A1 measures it, and it may dominate the AI_READI and Kids First costs.
7. What is the per-call failure rate of typed stages specifically, as opposed to v8's ordinary phases? The pilots measure it, and D21's trigger depends on it.
8. Will v10 AI_READI and Kids First full phases exceed the 128k output cap, given v8's 112–116k?
9. Does the #4354 adapter's native receipt floor reach the model? This decides D25.
10. Is extra usage (overage) enabled on the claude.ai account used for direct runs (#2370)?
11. Who are the named reviewers and curator (D23)? Is a second blind reviewer available for #2921 (D19)?
12. Is #4354's 60 s owner budget a runtime constraint, or a budget chosen for the fixtures? This decides whether re-registering it under D18 is legitimate.
13. Can `omission_context_v1` declare nested owner scopes (CM4AI's releases, VOICE's versions, Kids First's studies) before the record exists?
14. Should the next shared-generation version send logical rather than absolute caller paths, and allow one recorded retry per single-delivery stage? Both are condition boundaries for both arms.
15. Monolithic (D16): is it needed for the paper? Fidelity or isolation prompt? CBORG or the Anthropic API? Display or not? How many projects and replicates?
16. If #4354 is ready mid-matrix, should it merge between API stages with a parity check and re-registration, or wait until the API fan-out finishes?
17. Should the CHORUS v8 API canonical (`reviews_applied: true`, `review_margin` 2) be re-selected under the #835 reported-only policy before it is cited?
18. Should the GitHub D4D assistant (#2088) move to generic_v10 once the matrix completes, or keep its condition with the difference stated?
19. #4765: do merged records ship (Part A), and when does the fitness-feedback loop (Part B) run after #2929? Neither gates generic_v10.
20. Will the Codex session accept the D12 split while it is actively developing #4354? Will it publish on the owner's instruction, despite the no-partial-chain-push practice recorded in its #4740 comments?
