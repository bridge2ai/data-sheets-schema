#!/usr/bin/env python3
"""Purpose: build draft v4 of analysis plan amendment NP1 from draft v3 by
replacing named line ranges and exact single-line substrings, so that every
change from v3 is one stated replacement and nothing else moves.

Inputs: draft v3 read with `git show` from commit
27429678f37d5df92e2055fe5fa8e13e7717f871 of the NP1 worktree (its sha256 is
asserted), and the replacement texts below, which answer the two reviews of
v3 (issues 5969 to 5988) under the lead's rulings of 2026-11-12.
Outputs: the amendment file in the NP1 worktree, overwritten with v4. The
script commits nothing.
Serves: owner direction D134/D135; amendment NP1. Date: 2026-11-12.

Line numbers are those of v3. Ranges are applied from the bottom up.
"""
import hashlib
import subprocess
import sys

WORKTREE = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-native-production-amendment-np1-20261112"
PATH = "notes/generic_v10_analysis_plan_amendment_np1_2026-11-12.md"
V3_COMMIT = "27429678f37d5df92e2055fe5fa8e13e7717f871"
V3_SHA256 = "2160b96c6a98bd13636547b7395f41bcac7b016ba17d6f93614af4526f07c9c8"

SUBS = [
    ("**Status: draft v3, written by claude (lead) on 2026-11-12.**",
     "**Status: draft v4, written by claude (lead) on 2026-11-12.**"),
    ("Every other source reference was read by the lead at that commit.",
     "Every other source reference was read by the lead at that commit. For v4 the lead also read, at that commit, the capture and recorder lines the Claude review of v3 cited (NP1.4), the receipt-completion lines (NP1.5) and the lines that fix the runtime terms (NP1.7)."),
    ("NP1.10(b) and (c) propose the rest for the native arm, and NP1.10(ab) proposes that both projects are out of the API arm's scope. Items (c) and (ab) together answer item 38's route for both arms: native, and not API.",
     "NP1.10(b) and (c) propose the rest for the native arm, and NP1.10(ag) proposes that both projects are out of the API arm's scope. Items (c) and (ag) together answer item 38's route for both arms: native, and not API."),
    ("| CHORUS | The N1 canary: n=1, descriptive, never a replicate. Then 3 production cells |",
     "| CHORUS | The N1 canary: n=1, descriptive, never a replicate. [proposed, NP1.10(ak)] One replacement pilot, not a replicate, only in that item's case. Then 3 production cells |"),
    ("| AI_READI | [proposed] 1 pilot, not a replicate; then 3 production cells |",
     "| AI_READI | [proposed, NP1.10(e)] 1 pilot, not a replicate; then 3 production cells |"),
    ("Restated as the package-and-runtime contrast above [proposed] |",
     "Restated as the package-and-runtime contrast above [proposed, NP1.10(j)] |"),
    ("**Not measured for this cohort** [proposed] (NP1.9) |",
     "**Not measured for this cohort** [proposed, NP1.10(p)] (NP1.9) |"),
    ("Not measured for this cohort [proposed] (NP1.9) |",
     "Not measured for this cohort [proposed, NP1.10(q)] (NP1.9) |"),
    ("- **A production cell** [proposed] is", "- **A production cell** [proposed, NP1.10(d)] is"),
    ("- **The N1 canary is never one of these cells** (D25, D107; N1.5).",
     "- **The N1 canary is never one of these cells** (D25, D107; N1.5), and neither is a pilot."),
    ("- **An AI_READI pilot** [proposed]:", "- **An AI_READI pilot** [proposed, NP1.10(e)]:"),
    ("the floor comes from the canary alone, and AI_READI's first run is its first replicate.",
     "the floor comes from CHORUS's pilot alone (the canary, or the replacement pilot of NP1.5), and AI_READI's first run is its first replicate."),
    ("- **Role** [proposed]:", "- **Role** [proposed, NP1.10(i)]:"),
    ("- **Comparison rules** [proposed]:", "- **Comparison rules** [proposed, NP1.10(j)]:"),
    ("- **The AI_READI comparator** [proposed]:", "- **The AI_READI comparator** [proposed, NP1.10(l)]:"),
    ("The owner may choose it instead by answering no to NP1.10(k) and naming it.",
     "The owner may choose it instead by answering no to NP1.10(l) and naming it."),
    ("- **The native pre-completion reading** [proposed]:", "- **The native pre-completion reading** [proposed, NP1.10(o)]:"),
    ("n=1 cells (the canary, the pilot, VOICE_PEDIATRIC and Kids First) are descriptive only.",
     "n=1 cells (the canary, the pilots, VOICE_PEDIATRIC and Kids First) are descriptive only."),
    ("beyond inputs and runtime terms (NP1.7)", "beyond its inputs (NP1.7)"),
    ("- **The basis** [proposed, NP1.10(p)]:", "- **The basis** [proposed, NP1.10(r)]:"),
    ("- **The rule** [proposed, NP1.10(q)].", "- **The rule** [proposed, NP1.10(s)]."),
    ("- **How the value is registered** [proposed, NP1.7]:", "- **How the value is registered** [proposed, NP1.10(z)]:"),
    ("2. **The native measured-usage packet** [proposed],", "2. **The native measured-usage packet** [proposed, NP1.10(z)],"),
    ("- **Reviews** [proposed]:", "- **Reviews** [proposed, NP1.10(aa)]:"),
    ("- **The comparison set** [proposed]: CHORUS only.", "- **The comparison set** [proposed, NP1.10(ag)]: CHORUS only."),
    ("**Deferred** [proposed]:", "**Deferred** [proposed, NP1.10(aj)]:"),
    ("- **BC1 parity for the native arm** [proposed, NP1.10(aa)].", "- **BC1 parity for the native arm** [proposed, NP1.10(af)]."),
]

RANGES = []


def put(start, end, text):
    RANGES.append((start, end, text))


# ---- header: lines 10-20 --------------------------------------------------
put(10, 20, r'''- **v3** (commit `27429678f37d5df92e2055fe5fa8e13e7717f871`, file sha256 `2160b96c6a98bd13636547b7395f41bcac7b016ba17d6f93614af4526f07c9c8`) responded to every v2 finding; its response table is in that commit. It was reviewed twice, and both reviews said "ratifiable after listed fixes".
  - A Codex CLI pass (review sha256 `e544ddb789499818bd1670f56a83cf22be9262343f73170958ded7e6b3169f62`): 2 P1, 4 P2, 1 P3.
  - A Claude reviewer, a fresh session run on another model (review sha256 `e5ae36455c553e5b500298a5b95c1ea483df777f134fe30c2157a3d27f8ccbe0`): 2 P1, 6 P2, 10 P3.
  - The 25 findings are filed as 20 issues, #5969 to #5988; five overlap.
- **v3 → v4** responds to every finding; the table below maps each one. Besides wording, it:
  - corrects the account of which native records are eligible. As the code stands, a full record is kept only when the recorder ran. A small retention change is proposed as a prerequisite of any pilot, as its own item (NP1.4);
  - replaces the remedy for a canary launched before ratification. The canary's reading sets the floor only if the owner's answers to the items that determine the floor were recorded before its dispatch. Otherwise one further CHORUS pilot, now written into the sequence, supplies it (NP1.5, NP1.6, NP1.7);
  - fixes the stage at which the floor is enforced: the final stage only (NP1.5);
  - drops v3's per-project runtime formula. The source fixes every native run's deadline and dollar guard, so every pilot and production attempt runs under the canary's registered terms, and an end on a backstop has a fixed consequence (NP1.7);
  - removes the owner choices that had no stated criterion (NP1.2, NP1.5);
  - says when the basis has to be answered, and what the basis change and the #5939 repair change for the canary itself (NP1.5, NP1.9);
  - gives a lettered item to every rule marked [proposed] (NP1.6, NP1.10);
  - lists every engineering prerequisite of a pilot in one place, with its issue (NP1.7).
- **v4 has not been reviewed.**''')

# ---- response table: lines 37-68 ------------------------------------------
put(37, 68, r'''## Responses to the reviews of v3
Each issue stays open until a re-check of v4 confirms the answer. "Claude" and "Codex" name the two v3 reviews; both used the keys P1-1, P2-1 and so on, so each key is given with its review. The responses to the reviews of v2 are in v3's own table, at the commit named above.

| v3 finding | Issue | Answer in v4 | Where |
|---|---|---|---|
| Claude P1-1: the eligibility rule keeps a native record only when the recorder ran, and the draft said otherwise | #5969 | Confirmed by the lead in source. The wrong sentences are removed. The retention change is proposed as a prerequisite, with its own item; the "no" branch states the departure from the plan | NP1.4, (m), (n) |
| Claude P1-2 and Codex P1-1: the canary-first remedy lets the basis and the pilot be chosen after the outcome | #5970 | The canary's reading counts only if the owner's answers to the eight items that determine the floor were recorded before its dispatch; otherwise a replacement pilot supplies CHORUS's fraction | NP1.5, (ak) |
| Claude P2-1: two owner choices made after outcomes have no stated criterion | #5971 | At NP1b a project leaves scope only if its inputs fail the registered limits, or as part of a suffix of the order outside a stated number of weeks. The pilot's second attempt runs unless its class bars it; declining it needs a recorded reason of usage or calendar | NP1.2, NP1.5, (a), (f) |
| Claude P2-2: the "second reading" clause lets the registration choose between two ratios | #5972 | The final-stage reading governs. A difference is an instrument finding, and the rule yields no value while it is open | NP1.5, (s) |
| Claude P2-3: the basis may be answered after the canary's registration; N1 is not "unchanged" | #5973 | The basis is answered before the canary's registration is built, with a stated default. What changes for the canary is listed under "Changed" | NP1.5, NP1.9, (r) |
| Claude P2-4 and Codex P1-2: the stopping stage is left to the implementation | #5974 | Fixed here: the floor is enforced at the final stage only; the reading at receipt completion is diagnostic and stops nothing | NP1.5, (t) |
| Claude P2-5 and Codex P2-1: the per-project runtime terms | #5975 | The formula, the factor and the flag are dropped. The source fixes the deadline and the dollar guard. Every pilot and production attempt runs under the canary's registered terms, and a backstop end has a fixed consequence | NP1.7, (ab) |
| Claude P2-6: [proposed] acceptance rules with no letter | #5976 | Two new items | NP1.6, (u), (v) |
| Claude P3-1: the plan's pilot rule is quoted in part | #5977 | Quoted whole, with what (g) does not take from it | NP1.6 |
| Claude P3-2: "no lower bound" describes a bound of 1/20 | #5978 | "The lowest value that can be registered is 1/20" | NP1.5, (s) |
| Claude P3-3: "after the seal" | #5979 | "After receipt completion" | NP1.5 |
| Claude P3-4: the receipts gate is not inside the run; row B0 needs a production reading | #5980 | Both corrected | NP1.6, (u) |
| Claude P3-5: the #5939 repair against N1.4(A) item 5 and the API path | #5981 | The repair separates the structural floors from the coverage floor and is confined to the native route | NP1.5 |
| Claude P3-6: D113's reading is applied to the canary without a letter | #5982 | Marked [proposed], with its own item | NP1.6, (h) |
| Claude P3-7: several items do not say what a "no" means | #5983 | One clause each. v3's item (ae) is no longer a lettered item | NP1.10 |
| Claude P3-8: a manual stop is classed whatever its reason | #5984 | A manual stop takes the class of its recorded reason | NP1.6, (x) |
| Claude P3-9 and Codex P2-2: the further CHORUS pilot is underspecified and outside the sequence | #5985 | Its identity, floor state, acceptance rows, attempts, ends and place in the sequence are stated; the count is up to 17 first attempts | NP1.5, NP1.6, NP1.7, (ak) |
| Claude P3-10 and Codex P2-4: two items still hold two decisions | #5986 | Each is split in two | NP1.10 (ac), (ad), (ah), (ai) |
| Codex P2-3: exhausted attempts are equated with no verdict | #5987 | K_native stays fixed. The plan's three kinds of missing are used, and a verdict is unavailable only when a required eligible record or measurement is missing | NP1.2, NP1.3, NP1.6, (k) |
| Codex P3-1: reconciliation does not necessarily lower final-record coverage | #5988 | Reworded as the review proposed | NP1.5 |''')

# ---- NP1.2 scope rule: lines 110-120 --------------------------------------
put(110, 120, r'''- **Scope rule** [proposed, NP1.10(a)]: the plan's rule (lines 333–355), read for the native arm.
  - **Whole projects only.** A project is in or out with all its cells. Replicates are never trimmed inside a project.
  - **The evidence is fit, usage and stop outcomes.** It is never a quality metric of the canary, or of any v10 record, against v8 (lines 337–339).
  - **The order** is the plan's (lines 340–344): CHORUS ×3 → CM4AI ×3 → VOICE ×3 → AI_READI (pilot + ×3) → VOICE_PEDIATRIC ×1 → Kids First ×1. Under NP1.7 every pilot runs before the floor is registered and so before any production cell, as the plan's own pilot does (lines 307–312).
  - **Fit is settled at NP1b, by one test.** NP1b checks every project's frozen inputs offline against the registered limits. A project whose inputs fail them cannot run, and it leaves scope. No project leaves scope for fit after NP1b.
  - **Usage can shorten the scope only to a prefix of the order.** NP1b states, from the usage packet, how many attempts the usage windows allow in a week (NP1.7). The owner may state in NP1b a number of weeks for the batch. The scope is then the longest prefix of the order whose first attempts fit in those weeks at that figure. The arithmetic is NP1b's, and both reviewers check it. With no number stated, every project whose inputs pass stays in scope. This is the plan's "longest prefix of the order that the budget covers" (line 345), with weeks of usage in place of dollars.
  - **Those are the only two ways a project leaves scope at NP1b.** AI_READI can also leave at its pilot (NP1.5). D135 names the scope this amendment plans. The owner has no other descoping choice, and none that rests on anything read from the canary's record.
  - **A descoped project is "out of scope", not missing,** with the event that removed it named: "(NP1b: inputs)", "(NP1b: weeks)" or "(pilot)". It is not counted in K_native (NP1.3), and plan §7's missing-cell rules apply only to in-scope cells (lines 347–349).
  - **After K_native is fixed (NP1.3), nothing removes a project from scope.** What happens to its cells afterwards is described with the plan's three kinds of missing (lines 777–781), not as a change of scope:
    - a cell whose attempts end without acceptance is acceptance-missing, and its attempts' eligible records still enter Set A (lines 1094–1104);
    - a cell with no eligible full record is artifact-missing;
    - a project has no primary verdict only when its three cells do not each have an eligible record, or when a reading the metric requires is missing (lines 844–853).
  - **With CHORUS alone in scope,** every native verdict is a single-project result, written "holds for CHORUS" (lines 352–353).
- **VOICE_PEDIATRIC** [proposed, NP1.10(b)]: in scope unless NP1b removes it under the scope rule above. One cell under its own label. It is reported in VOICE's section of every table as its own row, never as a VOICE replicate and never in a VOICE verdict (lines 640–646).
- **Kids First** [proposed, NP1.10(c)]: in scope unless NP1b removes it under the scope rule above. One cell, last in the order, with the neutral profile and `vocabulary: {}`, under its own curator-written omission context, with its frozen chunk manifest re-validated first (lines 647–656). Those conditions are the plan's, not a choice made here.''')

# ---- NP1.3 K_native: lines 139-141 ----------------------------------------
put(139, 141, r'''- **K_native** [proposed, NP1.10(k)] counts the in-scope projects among CHORUS, CM4AI and VOICE, and AI_READI only when its comparator's record hashes were pinned at NP1b (below). The n=1 cells and a descriptive project are never in it.
  - **It is fixed once,** in the document that registers the floor's value (NP1.7 step 6): in NP1b when no pilot is pending, otherwise in the floor's own amendment, after every pending pilot has concluded. That is after every event that can remove a project from scope and before any production cell registers.
  - **It never moves afterwards.** A project in K_native stays in the denominator whatever happens to its cells. Its verdict is read by the plan's missing-data rule (lines 844–853): a project whose three cells each have an eligible full record gets its verdict, whether those records were accepted or not, and a project without that counts as "not measured" in "k of K_native". Using both attempts of a cell does not by itself make a project "not measured".''')

# ---- NP1.4 eligibility: lines 168-192 -------------------------------------
put(168, 192, r'''- **Set A** keeps the plan's two definitions, with definition (2) primary and (1) reported beside it (lines 681–712).
- **An eligible native full record** [proposed, NP1.10(m)]. **This item amends the plan's eligibility rule for the native arm. It does not apply an existing allowance.**
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
  - **What is never the test:** the phase report's own `passed`, `runtime_gates_passed`, and the saved result's completion state.
  - **What the code does today: condition 2 holds only when the recorder ran.** v3 said that a later failed check, a rejection and a stop all leave the record eligible. That was wrong. The Claude review of v3 found it, and the lead then read the lines.
    - The complete end capture reads the full record, the core, the report and the original receipt output, and then the recorder's provenance file (`native_shared_results_orchestration.py:68–74`). It later parses that provenance (`:208`).
    - If any of that fails, the controller falls back to the incomplete capture (`native_execution_orchestration.py:500–508`). That keeps the transcript, the control stream, the error stream, the runtime observation and the composition, and no record (`native_shared_results_orchestration.py:274–294`).
    - The phase rules admit the recorder only when every final check, the draft and the final evidence are current (`native_shared_phase.py:212–214`). The final checks are `derive_final_core`, `full_schema`, `full_terms`, `core_schema`, `pair`, `final_receipts` and `final_scope` (`:111–113`). The report can be rewritten only after them (`:155–161`).
    - So today an attempt that fails any final check, or stops before the recorder, has no pinned full record. In production that includes an attempt that fails the registered floor at the final receipt check, a full record that fails its own schema, a failed draft or final-evidence check, and every deadline, dollar-guard, usage or manual stop after reconciliation.
    - In a complete capture condition 1 holds by construction: the recorder needs it, and no tool is admitted after the recorder (`:134`). Condition 1 decides something only where the capture was incomplete.
  - **The retention change** [proposed, NP1.10(n)]: **an engineering prerequisite of any pilot, not yet written.** The incomplete capture also retains the current full record and core record, each with its sha256, when they exist, and records their absence when they do not. The attempt's live phase report is saved with them, if it is not saved already (audit, for where the live report is saved). A helper sizes the change on a separate local branch. Nothing of it exists today.
    - **What a yes gives.** Condition 2 then holds for a stopped or rejected attempt whose record exists. The eligible set is not gated on acceptance, on the recorder or on the floor. That is what the plan requires:
      - "A record that fails schema validation is eligible for Set A; Set B removes it." (line 758);
      - "A floor failure stops the roster without discarding records." (line 1163);
      - "The coverage floor is applied to neither arm, because v8 never had one and applying v10's floor would select on the measured outcome." (lines 799–800, on Set B).
    - **If the answer is no:** the native eligible set is limited to attempts whose recorder ran. That departs from the plan, and the owner accepts these consequences:
      1. native Set A is selected on every in-run final check: the registered coverage floor, full-record validation, the draft and the final-evidence check. The v8 side is selected on none of them;
      2. prediction 2's coverage is correlated with the floor's ratio, so the cells that fail the floor are removed from the measure the floor is closest to;
      3. a project whose cells fail the floor or a final check has no eligible records and gets no verdict, where the plan would report the failure;
      4. every stop after reconciliation is artifact-missing, whatever the record on disk held.

      Every report of a native result then says that Set A holds completed attempts only.
  - **What the rule cannot see, with the retention change in place.** It reads the end of the attempt, not an event inside it. Compared with the plan's rule it loses:
    - **(i) a record whose derived core failed validation.** The helper then exits nonzero and is not a current check. The plan keeps a schema-invalid record in Set A (line 758). With the retention change, a full record that fails its own schema but derives a valid core is kept;
    - **(ii) a completed record that a later write disturbed.** Any attempted write to the full record or the core after the check removes it from `current_checks`, even a write that was interrupted, and the earlier bytes are not kept. The plan's "A repair interrupted before writing its snapshot leaves the previous one eligible" (lines 751–752) cannot be met;
    - **(iii) an attempt with no saved phase report or no capture at all:** an uncatchable termination, a host loss or a publication failure. That is no evidence that reconciliation did not happen;
    - **(iv) a write the phase tracker did not observe,** for example one made by a shell command. The rule takes the tracker's word that nothing wrote the record after the check. Here the rule could keep bytes the check never covered. The guard against that is the registered command permissions, which allow the shell only for the typed helpers and read-only lookups (N1.4(B) row 3, N1.6); this rule adds none.
  - **What that does to the analysis.** In cases (i) to (iii) the attempt is artifact-missing for Set A where the plan's rule would have kept a record. In those cases the rule can lose a record; it never adds one. The losses fall on attempts that ended badly after reconciliation, so Set A understates such failures to that extent.
    - Every artifact-missing attempt is listed in the analysis manifest, with the case that applies as far as its retained evidence shows.
    - Where such an attempt's saved gates carry a validation result, it is still counted in row 6 and in the feasibility proportions.
    - A cell with no eligible record is artifact-missing under plan §7, and its project has no primary verdict.
  - **If the answer to NP1.10(m) is no:** the plan's own rule is built for the native arm before any pilot. The audit describes what that takes: an unchangeable copy of the full record at each completed reconciliation; a journal that binds each copy to the attempt and the event; and a reader that returns the last completed copy from a stopped or rejected attempt. That is new production code, with its own pins, tests and reviews, and the canary waits for it. Item (n) is then not needed.
  - **Conformance, not choice.** NP1b names the exact saved fields from the merged source. If the merged source no longer saves them, this item is restated by a prospective amendment before any production registration.''')

# ---- insert after line 194: the "no" clause of the pre-completion reading --
put(195, 194, r'''  - **If the answer is no,** prediction 2 is not measured for the native arm. No other reading takes its place.''')

# ---- NP1.5 #5939: lines 204-205 -------------------------------------------
put(204, 205, r'''  - **Its repair is a prerequisite of any pilot** (NP1.7). The rule the code has to match is amendment N1's: N1.4(B) rows 0 and 5. This amendment does not restate them.
  - **What the repair is, and is not.** N1.4(A) item 5 quotes "A pending scientific receipt floor cannot become strict success." The repair keeps that. It separates the structural receipt floors, which still gate the final strict check and the receipts gate, from the coverage floor, which under a pending registration is reported as UNMEASURABLE and never as a pass. A pilot then completes on the structural floors, with its coverage floor unmeasured. The command that fails today, `cli/receipts.py:303–322`, also serves the API arm, where the plan's rule for a pending floor stays as it is (lines 977–980). The repair is confined to the native route, and a test shows that the API arm's use is unchanged.
  - The policy asset says what the code does: "A pending floor remains a diagnostic pilot and cannot satisfy strict completion." That sentence is model-facing, and the asset's pin sits in a protected file. Its change goes to the owner as a changed packet.''')

# ---- NP1.5 basis: lines 219-226 -------------------------------------------
put(219, 226, r'''  - **What a yes needs: an engineering prerequisite, not yet written.** The receipt-policy registration declares the basis; `floor()` and the receipts gate read the at-receipt counters; a pending registration's reading carries the same counters; and the policy asset's sentence quoted above is changed to name that basis. A helper is preparing the change on a separate local branch. It lands with the repair of #5939, before the canary's registration is built, so that the canary, every pilot and every production cell run one source and one asset. Both asset sentences go to the owner in one changed packet.
  - **When this item is answered.** Before the canary's registration is built. The owner can answer it ahead of the rest of this amendment, in the coordination record, naming this file's commit and sha256. **If it has not been answered by then, the basis is the final-record one the code has,** recorded as such when the registration is built, with the consequences listed below. It does not change afterwards in this condition: a later change of basis changes a model-facing asset, and the cells run after it would be a new stratum (NP1.7). A registration is never rebuilt around a later answer.
  - **What a yes changes for the canary itself.** Amendment N1's text is not amended. Its row 0 is implemented by the #5939 repair, and its row 5 keeps the canary's reading reported and UNMEASURABLE. But the canary's model then reads two changed sentences of the policy asset, and a receipt-policy registration that declares the basis; both are shown to it at the initial check (`native_shared_receipts.py:369–374`). The canary's pending reading carries the at-receipt counters. NP1.9 lists this under "Changed".
  - **What a yes gives.** After receipt completion the model can change neither the sealed original record nor the completed receipt, so nothing it does later moves the gated ratio. The ratio is settled when receipt completion ends.
  - **Where the floor is enforced** [proposed, NP1.10(t)]: **at the final stage only.** The reading at receipt completion is saved and reported as a diagnostic, and it stops nothing. A production run whose ratio already fails there continues through the audit and reconciliation to its final receipt check, and fails there.
    - **That is what the code does today,** on either basis. The completion stage computes the reading and saves it; its own state depends on whether the model's answers are complete, not on the floor (`native_shared_receipts.py:433–463`).
    - **It is fixed here and not left to the implementation,** because it decides what a floor failure leaves behind. The attempt has a reconciled full record and a derived core. Under NP1.4 they stay eligible for Set A, so a floor failure is reported with its record and not as a missing one.
    - **What it costs:** the rest of that run, which is its time, up to the deadline, and its usage.
    - **Stopping at receipt completion instead** would change how attempts are stopped. That is a change of scientific procedure and a new stratum, under its own prospective amendment (NP1.7).
  - **If the answer to the basis is no:** the floor is measured on the final record, as the code has it today. Only the #5939 sentence of the asset changes. The owner then accepts these consequences:
    1. **It departs from D37 and from plan §8.** Removing unreceipted leaves from the full record after the seal raises the gated ratio. That is the behaviour D37 was chosen to neutralise, and prediction 1 then reads the reduced record. This is a reading of the code; no run has shown it.
    2. **Reconciliation moves the ratio, in either direction.** Adding receiptable leaves that have no receipt lowers it; removing unreceipted leaves raises it. So a floor taken from a CHORUS pilot would gate projects differently according to what their reconciliation did.
    3. **The stop-loss is exposed.** Two floor failures with one root cause, "reconciliation added leaves that cannot be receipted", would end native re-running (NP1.6).
    4. **The cap's reason does not apply.** The plan's reason is that receipt completion drives the D37 ratio towards 1 (lines 1134–1135). On the final record the plan's two assisted API canaries read 58/63 and 64/75.
  - **What the lead knew.** The plan's values for those two API canaries predict a floor near 17/20 on the final-record basis and 19/20, capped, on D37's (lines 200–201). The lead had them in view. They are API values from assisted runs, not native readings, and v2's choice followed the policy asset's sentence, which predates this amendment. They are stated here so that the owner chooses the basis knowing them.''')

# ---- NP1.5 canary first: lines 228-232 ------------------------------------
put(228, 232, r'''  - **If the canary's word is given first** [proposed, NP1.10(ak)]. This is the case in which the owner answers no to amendment N1's item (ah).
    - Before its own ratification this amendment's header records when the canary's outcome became available, and what of it the lead, each reviewer and the owner had seen. N1.5 requires that record.
    - **The canary's reading is a floor input only if the owner's answers that determine the floor were recorded before the canary's dispatch.** Those are the answers to NP1.10(a), (e), (f), (r), (s), (t), (u) and (ab): the scope and order; the AI_READI pilot and how it concludes; the basis; the floor rule; where the floor gates; the acceptance rows, which decide which pilot attempt is accepted; and the runtime terms, which can remove AI_READI at its pilot. Each answer has to be in the coordination record with a time before the dispatch, naming this file's commit and sha256 at that time.
    - **An earlier draft with the same words is not enough.** v3 asked only that the text had been pushed first. Both reviews of v3 found that this fixes the words and not the answers: the basis and the pilot could still be chosen with the canary's two ratios in view.
    - **Otherwise the canary's reading is excluded,** and one further native CHORUS pilot, the **replacement pilot,** supplies CHORUS's fraction (NP1.6, NP1.7). The canary stays what N1 made it: the n=1 feasibility result, reported with both of its coverage readings, and never a floor input.
    - Any other rule of this amendment that was answered after the outcome was available is listed in the header, with the outcome values that were in view.
    - **If the answer is no,** this amendment cannot register a floor in that case, and no production cell registers until a revised amendment says where the floor comes from.''')

# ---- NP1.5 rule details: lines 237-248 ------------------------------------
put(237, 248, r'''  - **If NP1.10(r) is answered no,** the rule reads `with_receipt / receiptable` on the final record in place of the at-receipt counters, and is otherwise the same.
  - **Eligible pilots:** CHORUS's pilot and, if NP1.10(e) is yes and AI_READI is in scope, the AI_READI native pilot. **CHORUS's pilot** is the N1 canary, or the replacement pilot where NP1.10(ak) excludes the canary's reading. Only an accepted attempt's saved result supplies a fraction; a rejected, stopped or assisted attempt never does (lines 1129–1133).
  - **Which reading: one.** Each pilot contributes one fraction, from the `slots` of its final-stage receipt check: the block the controller writes with `native_receipt_stage: final` (`native_shared_receipts.py:484–498`), read from the accepted attempt's saved result.
  - **The second reading is a check, never an input.** On the at-receipt basis the receipt-completion stage's `after` block is the checker run on the sealed original with the completed receipt (`:433–437`), so it should equal the final-stage pair. It is reported beside it. If the two differ, that is an instrument defect: it is filed as a finding, and the rule yields no value while it is unresolved. The floor's registration never chooses between two observed ratios.
  - **Readings that are not used.** The controller also evaluates the floor at the initial receipt check, where it forces the state to pending (`:363–364`). That is reported. It does not enter the rule and does not gate a production record. Final-record coverage is reported for every record as the plan's descriptive quantity.
  - **What gates in production:** the final-stage check's reading on the chosen basis, against the registered fraction (above, and NP1.6).
  - **A pilot whose saved result has no such reading** supplies no fraction, and the "no value" case below applies.
  - **Arithmetic:** exact integers, `floor(20 × with_receipt_at_receipt / receiptable_at_receipt) / 20`, then the minimum with 19/20, registered as a numerator over the denominator 20.
  - **Why the cap:** the plan's reason (lines 1134–1140). Receipt completion drives the at-receipt ratio towards 1, and a floor of 1 would stop a replicate on one unreceipted leaf.
  - **The lowest value that can be registered is 1/20.** The plan's rule rests on a re-canary that has passed its own 19/20 gate (lines 1147–1149). The native canary is ungated (D109), so the native floor is wholly the pilots' own reading. A low reading registers a low floor, which gates little. The value is reported with that said, and every production record's coverage is reported whatever the floor. A reading under 1/20 yields no value.
  - **The AI_READI branch.** The pilot's second attempt is registered and run unless the first attempt's cause class bars it (NP1.6). The pilot concludes without acceptance in three cases only:
    - its second attempt ends without acceptance;
    - an attempt of it ends on a backstop, after which no further attempt follows (NP1.7);
    - the owner declines the word for the second attempt and records a reason of usage or calendar. The record says that the reason is not a coverage or quality reading of the first attempt.

    If the cause is not rule-level, AI_READI then leaves scope as infeasible, reported as a feasibility result, and CHORUS's pilot alone sets the value (plan step 8, lines 307–312). A rule-level rejection is NP1.6's case.
  - **No value:** if a pilot the branch still requires has no accepted attempt or a zero denominator, if the value comes to 0/20, or while an instrument finding on the two readings is open, the rule yields no value. No production cell registers until a prospective amendment, reviewed as this one, supplies one. No other observed ratio is substituted (lines 1150–1152).''')

# ---- NP1.6: lines 253-285 -------------------------------------------------
put(253, 285, r'''- **Each attempt is judged by N1.4(B)'s rows B0–B7** [proposed, NP1.10(u)], as ratified, on the saved result after the attempt ends. N1 wrote those rows for the canary. Applying them to the AI_READI pilot, to the replacement pilot and to every production cell is this amendment's proposal.
  - **Row B0 for production.** N1 wrote B0 for a pending floor: "The receipts gate uses the structural floors only, so D109's pending floor doesn't block it." For a production cell B0 reads the receipts gate with the structural floors and the registered coverage floor.
  - **If the answer is no,** those attempts have no acceptance rule, and none registers until a revised amendment supplies one.
- **For production cells, row B5 gates** [proposed, NP1.10(t)]: the final-stage floor reading (NP1.5) must read `state: passed` under the registered floor. Pilots keep B5 reported and labelled UNMEASURABLE (D109). "Accepted" for a production cell then means B0–B7 all hold.
  - **Where a registered floor is enforced.** Inside the run, by the final strict receipt check. After the run, at finalization, by the receipts gate (audit). So a production attempt that fails the floor does not reach the recorder, and row B0 fails with it. It is classified by its cause, a content slip, not as a controller fault.
  - **A no cannot leave production ungated,** because the in-run strict check enforces any registered floor. A no means that no floor is registered under this amendment. D109 then allows no native replicate until the amendment is revised.
- **Blind source review (B6) is per record** (D36): a fresh Claude session and a Codex CLI pass, neither of which generated or operated the run, with the second blind reviewer's recall seed pinned to `original_full` before anyone reads the audit.
- **The owner signs each acceptance record** (D36). Its format is plan §6's (lines 1026–1048). [proposed, NP1.10(v)] The native identities N1.6 lists stand in place of the API-only fields. If the answer is no, the owner names the format before the first acceptance record under this amendment.
- **Attempts** [proposed, NP1.10(w)]:
  - **At most two attempts per native production cell,** counted across every label and registration, then the owner reviews. This is the plan's bound (§7, lines 1066–1069; D07), which D113 already applies to the canary.
  - **No attempt follows a backstop end of the same cell** (NP1.7).
  - **An attempt** is one launch that consumed its reservation. A capture is not an attempt, and a refusal before the reservation consumes none. A capture that is fresh at the reservation but stale at dispatch stops the attempt, and it counts (N1.5).
  - **Every attempt is retained,** stopped and rejected ones included (lines 1052–1056). A stopped or rejected attempt is never resumed or re-run under its label; any new attempt needs a new label, registration and word (N1.5; D56).
- **Classification** [proposed, NP1.10(x)]: every stop or rejection gets the plan's two records, its evidence status and exactly one primary cause class by the precedence of the plan's table (lines 1337–1377), with these native readings.

| Class | Native reading |
|---|---|
| instrument | As the plan writes it |
| rule-level | A B6 rejecting-class finding is sustained on anything the run wrote, or the final records fail validation or carry duplicate keys. In production it counts toward the stop-loss, and the cell may use its second attempt only while the stop-loss is not reached |
| content slip | A structural receipt floor, the registered coverage floor or the report-totals equality row fails, and rule-level does not match. One contingency within the cell's two attempts; counts toward the stop-loss by root cause |
| registration or environment | A fault of the registration or the launch environment and not of generated content: the host, the keep-awake, the account, a usage stop, or an admission failure at dispatch. One contingency under a new registration, corrected where there is something to correct. A usage stop has nothing to correct; it needs only the new registration and word. No test predicts one: N1.5 says a mid-run five-hour exhaustion is possible whatever the admission reading |
| impossible limit | As the plan writes it |
| record shape | The attempt ends on a native helper's refusal of the record for a value of the wrong cardinality or type. A refusal before the phase-1 seal that the model corrects and re-checks is not a stop; the instruction allows it. The native arm has no write-time normaliser (N1.1). One contingency |
| transport | The runtime's terminal result or a supervisor boundary records a transport fault. One contingency |
| budget or clock | The registered deadline or the registered dollar guard ended the attempt: a backstop end. No contingency under this amendment; NP1.7's backstop rule applies. For the canary, N1.5 and D113 govern |
| unknown | Held for the owner's adjudication before any retry |

  - **A manual stop takes the class of its recorded reason.** It is a backstop end only when the reason is the clock or the guard. A stop made because the operator saw a problem in the content is classed by that problem.
  - The plan's rules beside its table stand (lines 1360–1377): a content defect outranks every operational class; unmeasurable is not failed; an assisted attempt is evidence only.
- **Stop-loss** [proposed, NP1.10(y)]: the plan's production rule (lines 1322–1329) for the native shared-v1 condition. Two rejections with the same root cause end re-running in that condition. The count covers every native production cell, the two descriptive cells included, across every label and registration, and it never resets. Rule-level causes and content slips count; other stops, backstop ends among them, are counted and reported separately. If the answer is no, the owner names the stop-loss before the first production registration.
- **Pilots:**
  - **The canary** is governed by D113 and N1.5.
    - **How D113 is read** [proposed, NP1.10(h)]. D113 says a rule-level rejection of the canary "ends the **native shared-v1 cell only,** not the API arm's generic_v10." It was decided when the canary was the only native cell, and its contrast is with the API arm. This amendment reads it as ending the whole native shared-v1 condition: after a rule-level rejection of the canary, this amendment has nothing to apply to. That is the lead's reading, not the decision's words.
    - **If the answer is no,** the narrow reading holds: the rejection ends the canary's cell, and a later prospective amendment could add a native CHORUS pilot in this condition.
  - **The replacement pilot** [proposed, NP1.10(ak)] exists only where NP1.5 excludes the canary's reading.
    - **What it is:** one native CHORUS run, n=1, never a replicate and never one of this amendment's cells, with its own label, registration, two reviews and word. It runs the merged source and assets the production cells will run, with the floor pending as the canary's was. D109 set that state for the canary; applying it here is part of this item.
    - **When:** after this amendment's ratification and after NP1b, and before the AI_READI pilot (NP1.7). CHORUS is first in the order and the cheapest run, and a rule-level end here stops everything before AI_READI is spent on.
    - **How it is judged:** rows B0–B7, with B5 reported and UNMEASURABLE.
    - **Attempts:** at most two. They are its own and are not the canary's two. No attempt follows a backstop end.
    - **A rule-level rejection** ends the native shared-v1 condition, as NP1.10(g) has it for the AI_READI pilot.
    - **If it concludes without acceptance for any other cause,** CHORUS has no fraction, the rule yields no value, and no production cell registers until a prospective amendment (NP1.5).
    - **If the source changed between the canary and it,** the canary is outside the production stratum and is reported so. The replacement pilot and every later cell run one source.
  - **The AI_READI pilot has at most two attempts** [proposed, NP1.10(f)], concluded as NP1.5 says.
  - **A rule-level rejection of the AI_READI pilot ends the native shared-v1 condition** [proposed, NP1.10(g)]: no further native pilot or production attempt, for any project, in this condition. The API arm is not affected.
    - The plan's rule for its own pilots is: "The first rule-level rejection of a pilot, the re-canary included, ends this condition and schedules the next shared-generation version for both arms." (lines 1318–1320). This item takes the first half, for the native arm only. It schedules nothing for the API arm, and D113 does not either.
    - **If the answer is no:** a rule-level rejection of the AI_READI pilot ends AI_READI's cells only. AI_READI leaves scope, CHORUS's pilot alone sets the floor, and the rejection counts once toward the production stop-loss.
- **Missing cells** follow plan §7 unchanged (lines 1094–1108). A cell with no accepted replicate after its attempts is acceptance-missing, and "Its attempts' eligible records still enter Set A where they exist." A project has a primary verdict when its three cells each have an eligible full record, "accepted or not".''')

# ---- NP1.7 prerequisites and step 1: lines 288-293 ------------------------
put(288, 293, r'''- **Before any pilot: code that has to exist.** These are engineering prerequisites, not choices. All of them land before the canary's registration is built, so that every pilot and production cell runs one source and one set of assets. **None of the five that carry a label below is repaired or written today.**
  - N1.9's list.
  - **#5939, the pending floor:** a pending floor is reported and does not block a pilot (NP1.5).
  - **#5966, the helper cache:** a helper's dependency writes a cache under HOME, and the empty-HOME guard then stops the public completion path. Two offline runs on synthetic inputs found it after v3 was written.
  - **#5967, the failure record:** when the runtime validation itself fails, no failure record is published, so there is no exact failed readback, which N1.4(A) item 6 requires.
  - **The basis change, if NP1.10(r) is yes:** the at-receipt basis in the registration, in `floor()` and in the receipts gate (NP1.5). No issue yet; a helper is sizing it.
  - **The retention change, if NP1.10(n) is yes:** the incomplete capture retains the current full and core records (NP1.4). No issue yet; a helper is to size it.
  - The changed policy asset, approved by the owner as a changed packet: one sentence for #5939, and a second if NP1.10(r) is yes.
1. **The canary is accepted under N1.** Amendment N1 is ratified, the native code is accepted and merged (N1.9), and the CHORUS canary is registered, run and accepted on N1.4(B)'s rows. **No pilot or production registration under NP1 is made before the canary's acceptance record is signed.** That governs when the production sequence runs. It does not govern when NP1 is reviewed and ratified: NP1 is ratified before the canary's word (NP1.5). If the canary is rejected at rule level, D113 ends the native shared-v1 cell, which this amendment reads as the whole condition (NP1.6, NP1.10(h)), and this amendment has nothing to apply to.''')

# ---- NP1.7 steps 3 onwards: lines 303-320 ---------------------------------
put(303, 320, r'''3. **NP1b** [proposed, NP1.10(z)]: a dated amendment, reviewed as this one is and ratified by the owner by sha256 before any native pilot or production registration. "It applies rules; it does not invent them" (the plan on P4b, lines 304–305). It:
   - applies NP1.2's scope rule: the inputs test for every project, and the prefix arithmetic if the owner states a number of weeks;
   - confirms from the merged source that the registered runtime terms are still the canary's for every attempt (below);
   - names, as a conformance check on the merged source, the exact saved fields of the eligible record and of the pre-completion reading (NP1.4);
   - pins the comparator manifest's record hashes, which include AI_READI's only if that comparator exists by then (NP1.3);
   - pins the recall adapter, the common checker's source hash and the schema closures;
   - states, from the usage packet, how many attempts the usage windows allow in a week;
   - when no pilot is pending, registers the floor's value under NP1.5 and fixes K_native.

   It may change which whole projects are in scope, and only by NP1.2's two tests. It may not change a metric, an instrument, a decision rule, a tolerance, an analysis-set definition, an eligibility rule or a missingness rule. It may not use any v10 quality value to choose a project, a rule or a threshold (lines 316–325). **Computing the floor's value by NP1.5's fixed rule is not such a choice:** it applies the rule to the accepted pilots' coverage readings, as the plan's A15 does (lines 1159–1162).
4. **The replacement pilot,** only where NP1.10(ak) excludes the canary's reading: registered, run, and accepted or concluded under NP1.6.
5. **The AI_READI pilot,** if NP1.10(e) is yes and AI_READI is in scope: registered, run, and accepted or concluded before the floor's value is computed.
6. **The floor's registration** (NP1.5), in NP1b or, when a pilot was pending, in its own dated amendment reviewed and ratified the same way. **It fixes K_native** (NP1.3). **No production cell registers before it.**
7. **Production cells, in NP1.2's order, one attempt at a time.** A project's first cell runs first: its other cells register only after the first cell's attempts have ended (below). For each attempt:
   - a registration on merged main that pins the source commit, the full and core schema closures, the bundle, the chunk manifest and the source manifest (plan §11, lines 1404–1405), the runtime and its probes (N1.2, N1.9), the registered runtime terms, and the receipt policy that carries the registered floor;
   - two independent reviews of the registration and its packet (N1.3);
   - the owner's statement of launch terms and the coded word, which binds one attempt by construction (N1.5);
   - capture, guard and launch as N1.5 orders them;
   - acceptance under NP1.6.''')

# ---- NP1.7 runtime terms, pacing, one procedure: lines 323-347 ------------
put(323, 347, r'''- **Runtime terms: the canary's, for every attempt** [proposed, NP1.10(ab)].
  - **What the source fixes.** Every runtime that is not the synthetic test profile has to declare a deadline of exactly 21,600 seconds (`native_u4b_policy.py`, `N1_DEADLINE_SECONDS`, checked by `validate_runtime_terms`) and the dollar guard D110 decided (`native_u4b_runtime.py:171`). Those are N1.5's terms, and a registration with other values is refused. v3 proposed per-project deadlines and guards computed at NP1b. Both reviews found that the source does not admit them.
  - **The rule.** Every pilot and production attempt under this amendment runs under the canary's registered runtime terms. There are no per-project terms, and this amendment asks for no code change to allow them.
  - **Why longer terms are not built now.** They would be a source change before the canary, with design questions of their own: a run of more than six hours crosses more usage windows, and every session on the account stands down for as long. The canary would wait for it. Nothing here forecloses it later.
  - **A backstop end** is an attempt ended by the registered deadline or the registered dollar guard, or by a manual stop whose recorded reason is one of them (NP1.6). The canary's terms were sized for CHORUS, the plan's cheapest run (lines 371–375), so a larger project may end this way for its size alone. Its consequence is fixed here, and nobody chooses it after the fact:
    - **No further attempt of that cell or pilot.** A second attempt would run under the same terms. A longer run needs a longer deadline, which needs source support and its own later amendment, as a new stratum.
    - **The AI_READI pilot:** the pilot concludes without acceptance, and AI_READI leaves scope before K_native is fixed, reported "out of scope (pilot)" with the backstop named (NP1.5).
    - **The replacement pilot:** it concludes without acceptance, and the floor rule yields no value (NP1.6).
    - **A production project's first cell:** the project's other cells are not started. The project stays in K_native, and its cells are reported "not measured (runtime)": the first as acceptance-missing, with whatever eligible record it left, and the others as never run.
    - **A later cell of a project:** that cell is acceptance-missing, its eligible record, if it left one, enters Set A, and the project's remaining cells proceed.
  - **A project's first cell runs first.** Its other cells register only after the first cell's attempts have ended. One attempt runs at a time in any case; this adds that a project's size is tested once before its other cells are spent.
  - **A backstop end is not a rejection.** It is reported under estimand 1 as a stop. It does not count toward the stop-loss, and it says nothing about the content.
  - **For the canary itself,** N1.5 and D113 govern, unchanged.
  - **If the answer is no:** per-project terms are built in source before the canary, under a revised amendment that states the rule for them, and the canary waits for it.
- **Admission and capture terms** [proposed, NP1.10(ac)]: the admission bounds (D118 and N1.5), overage disabled, the freshness age (D136) and margin, the keep-awake policy, the capture rules and the context mode apply unchanged to every pilot and production attempt. D110, D111, D118 and D136 were decided for the canary; applying them here is this amendment's proposal. If the answer is no, the owner names the terms that differ, and the source has to admit them before the canary.
- **Pacing** [proposed, NP1.10(ad)]: one native attempt runs at a time on the account. No term is relaxed to shorten the batch.
  - **The count:** up to 16 first attempts with the canary (1 canary, 1 AI_READI pilot, 12 replicates and 2 descriptive cells), a seventeenth if the replacement pilot is needed, and at most one further attempt per pilot or cell.
  - **What each attempt asks of the owner's sessions.** Every session that draws on the registered account stands down from before the capture until the attempt ends, and none of them monitors it (amendment N1's item (ad)). That is up to six hours each time, 16 times or more.
  - **Each registration is valid for two weeks** (amendment N1's item (g)).
  - **The usage windows pace the batch.** How many attempts fit in a week is not known. It follows from the usage packet and is stated in NP1b.
  - **If the answer is no,** the owner names the concurrency, and a revised amendment says how two attempts share one account's usage windows.
- **One procedure** [proposed, NP1.10(ae)]: every native pilot and production cell runs the same merged source, the same selected assets and the same runtime terms. Two things differ, and each is declared: a project's inputs; and the floor value in the receipt-policy registration, which also changes what the model is shown (NP1.5).''')

# ---- NP1.8 contrast and schema: lines 360-362 -----------------------------
put(360, 362, r'''  - **What it supports** [proposed, NP1.10(ah)]: a descriptive native/API contrast for CHORUS: the two arms' values side by side on the plan's metrics, with N1.6's declared differences. No directional rule is added for it. Each arm's own comparison with v8 keeps its own label. If the answer is no, the owner names the rule, and a directional rule needs its own prospective amendment before either side's CHORUS production record exists.
  - **What a matched contrast requires,** from the plan (lines 583–592): the same frozen source bundle, manifest, source policy, schema closures, profile, omission context and scientific assets wherever the contrast claims they match; hashes of the complete effective instructions and of each stage request; and every remaining difference declared, not normalised away.
  - **The schema release may differ, declared** [proposed, NP1.10(ai)]. The plan requires identical closures only where the contrast claims they match. N1.6 declares the native arm's 3.2.1 against the API arm's ratified 3.1.0 "unless the comparison registration moves by its own amendment". Which release the rebuilt comparison registration uses is decided with that registration. This amendment requires neither; the contrast reports each side's schema closure. If the answer is no, both sides run one release: the comparison registration is rebuilt on the native arm's, or the native arm's release is changed by its own amendment before the cells it governs.''')

# ---- NP1.9 unchanged / changed: lines 386-397 -----------------------------
put(386, 397, r'''**Unchanged:**
- the plan file and its sha256;
- P4a amendment 1;
- the text of amendment N1, including N1.5's terms for the canary and N1.4(B)'s rows;
- D22, D25, D109's pending floor for the canary, and D113;
- any API-arm registration, and the rules the plan fixes for any API cell that runs, except the API arm's scope rule if NP1.10(ag) is adopted;
- any historical decision or record.

**Changed, for readers of the amendment:**
- the native column of the plan's matrix (NP1.1);
- plan §1 item 5's statement that native production cells are unregistered: they are planned here, and each still needs its registration;
- the plan's eligibility rule, for the native arm only (NP1.4);
- the API arm's scope rule, superseded by a fixed CHORUS-only set if NP1.10(ag) is adopted (NP1.8);
- **what the N1 canary runs, though not N1's text:**
  - the repairs of #5939, #5966 and #5967 are prerequisites of the canary that N1.9's list does not name;
  - if NP1.10(r) is yes, the canary's model reads two changed sentences of the policy asset and a registration that declares the basis, and the canary's pending reading carries the at-receipt counters. If it is no, one sentence changes;
  - if NP1.10(n) is yes, a stopped or rejected canary attempt retains its full and core records.''')

# ---- NP1.10: lines 399-448 ------------------------------------------------
put(399, 448, r'''## NP1.10 Ratification: the owner names this file's sha256 at a commit, and answers each lettered item
Each letter is one decision, and a "yes" adopts exactly the value given. The cells themselves are D135's scope and are not a lettered item. An item answered no is revised and re-submitted before any registration that depends on it; where a no has a consequence beyond that, the item says so. Letters differ from v3's; the note after each item says how. "Amendment N1's item" always means a letter of N1, never one of these.

**Scope**
- **(a)** Scope and order for the native arm: whole projects only; the evidence is fit, usage and stop outcomes, never a quality value; the plan's order. At NP1b a project leaves scope only if its frozen inputs fail the registered limits, or as part of a suffix of the order that falls outside a number of weeks the owner states. AI_READI can also leave at its pilot. There is no other descoping choice (NP1.2). *Changed.*
- **(b)** VOICE_PEDIATRIC is in scope, one descriptive cell, unless NP1b removes it under (a) (NP1.2). *Reworded.*
- **(c)** Kids First is in scope, one descriptive cell, run last under the plan's conditions, unless NP1b removes it under (a) (NP1.2). *Reworded.*
- **(d)** The two descriptive cells are production cells: they run under the registered floor and under NP1.6's acceptance rows, attempt bound, classification and stop-loss, and they never enter K_native or a verdict. A no means the owner names their rules before their registrations; they are last in the order, and nothing else waits (NP1.2). *A "no" clause is added.*
- **(e)** One native AI_READI pilot, not a replicate, with the floor pending, accepted before the floor's value is computed. A no means the floor comes from CHORUS's pilot alone (NP1.2). *Unchanged.*
- **(f)** That pilot has at most two attempts, and the second runs unless the first's cause class bars it. The pilot concludes without acceptance when the second ends without acceptance, when an attempt ends on a backstop, or when the owner declines the second word for a recorded reason of usage or calendar. If the cause is not rule-level, AI_READI leaves scope and CHORUS's pilot alone sets the floor (NP1.5, NP1.6). *Changed.*
- **(g)** A rule-level rejection of the AI_READI pilot ends the native shared-v1 condition, for every project. A no ends AI_READI's cells only (NP1.6). *Unchanged.*
- **(h)** D113's "native shared-v1 cell only" is read as the whole native shared-v1 condition: after a rule-level rejection of the canary this amendment has nothing to apply to. A no keeps the narrow reading, under which a later prospective amendment could add a native CHORUS pilot in this condition (NP1.6). *New.*

**Role and comparison**
- **(i)** Role: native production cells are the study's primary generic_v10 cells; a native result is never pooled with an API cell or reported as the plan's package effect (NP1.3). *Was (h).*
- **(j)** Comparison rules: the plan's v10-against-v8 rules apply to the native replicate cells unchanged, under the label "native v10 against v8 API: package and runtime". A no makes native production descriptive only (NP1.3). *Was (i).*
- **(k)** K_native counts the in-scope projects among CHORUS, CM4AI and VOICE, and AI_READI only when its comparator was pinned at NP1b. It is fixed once, at the floor's registration, and never moves. A project in it gets its verdict by the plan's missing-data rule, and using both attempts of a cell does not by itself make it "not measured" (NP1.3). *Was (j); changed.*
- **(l)** The AI_READI comparator follows D64, item 14; its branch is fixed at NP1b on whether the no-crate v8 API run exists then; native AI_READI cells do not wait for that run (NP1.3). *Was (k).*

**Analysis sets**
- **(m)** An eligible native full record is the one the end capture pinned, in an attempt whose saved phase report lists `derive_final_core` as a current check. This amends the plan's eligibility rule for the native arm, with the limits NP1.4 names. A no means the plan's own event-bound rule is built before any pilot (NP1.4). *Was (l); its account of the code is corrected.*
- **(n)** The incomplete capture retains the current full and core records with their sha256, as an engineering prerequisite of any pilot, so that a stopped or rejected attempt can have an eligible record. A no limits the native eligible set to attempts whose recorder ran, with the four consequences NP1.4 lists (NP1.4). *New.*
- **(o)** Prediction 2 reads the receipt-completion stage's `before` block, reported as taken after pre-seal self-correction; a run without one is metric-missing. A no means prediction 2 is not measured for the native arm (NP1.4). *Was (m); a "no" clause is added.*
- **(p)** Prediction 4 (E2) is not measured for this cohort, and is measured on native cells only under a separate prospective amendment ratified before the first production registration (NP1.3, NP1.9). *Was (n).*
- **(q)** Prediction 5 (E5) is not measured for this cohort, on the same condition (NP1.3, NP1.9). *Was (o).*

**The floor**
- **(r)** The floor's basis is D37's at-receipt coverage, with the code change NP1.5 names landing before the canary's registration is built. This item is answered before that registration is built. Unanswered by then, or answered no, the basis is the final-record one the code has today, with the four consequences NP1.5 lists, and it does not change afterwards in this condition (NP1.5). *Was (p); changed.*
- **(s)** The floor rule: the lowest of the eligible native pilots' fractions on (r)'s basis, each read once from the final-stage check, rounded down to a multiple of 1/20 and capped at 19/20. The lowest value that can be registered is 1/20. No value, or an open instrument finding on the two readings, means no production registration (NP1.5). *Was (q); changed.*
- **(t)** The registered floor gates production cells at the final stage only: N1.4(B)'s row B5 reads the final-stage check on (r)'s basis, and the reading at receipt completion is diagnostic and stops nothing. Pilots keep B5 reported. A no means no floor is registered under this amendment, and no native replicate runs until it is revised (NP1.5, NP1.6). *Was (r); changed.*

**Acceptance**
- **(u)** N1.4(B)'s rows B0–B7 judge the AI_READI pilot, the replacement pilot and every production cell, with B0 read for production as the receipts gate under the structural floors and the registered floor (NP1.6). *New.*
- **(v)** The acceptance record has plan §6's format, with the native identities N1.6 lists in place of the API-only fields (NP1.6). *New.*
- **(w)** At most two attempts per native production cell, counted across every label and registration, and none after a backstop end (NP1.6, NP1.7). *Was (s); changed.*
- **(x)** The plan's cause classes with NP1.6's native readings; a manual stop takes the class of its recorded reason (NP1.6). *Was (t); two rows reworded.*
- **(y)** Stop-loss: two rejections with the same root cause end re-running in the native shared-v1 condition; the count covers every native production cell and never resets. A no means the owner names the stop-loss before the first production registration (NP1.6). *Was (u); a "no" clause is added.*

**Procedure**
- **(z)** The staged procedure: the measured-usage packet, then NP1b, then any pending pilot, then the floor's registration, each reviewed and ratified before the registrations that depend on it. NP1b applies rules and changes none; computing the floor by (s) is an application (NP1.5, NP1.7). *Was (v).*
- **(aa)** Reviews: both reviewers review every registration, each registration with its own two review documents (NP1.7). *Was (w).*
- **(ab)** Runtime terms: every pilot and production attempt runs under the canary's registered deadline and dollar guard, which the source fixes. After a backstop end no further attempt of that cell or pilot follows. The AI_READI pilot's backstop end takes AI_READI out of scope. A production project's first cell runs first, and its backstop end leaves the project's other cells unstarted and the project "not measured (runtime)". A no means per-project terms are built before the canary under a revised amendment (NP1.7). *Was (x); replaced.*
- **(ac)** The admission bounds, overage disabled, the freshness terms, the keep-awake policy, the capture rules and the context mode, each decided for the canary, apply unchanged to every pilot and production attempt (NP1.7). *Split from (y).*
- **(ad)** One native attempt at a time on the account, and no term relaxed to shorten the batch (NP1.7). *Split from (y).*
- **(ae)** One procedure: a later change to the native runner or a model-facing asset is a new stratum; a change to admission, retry, stopping, selection or retention always is, and needs a prospective amendment; byte parity with an authorized diagnostic canary keeps the stratum only for a change that both reviewers confirm, and the owner accepts by sha256, as leaving those untouched (NP1.7). *Was (z).*
- **(af)** Production cells run the declared shared-v1 differences, as the canary does; BC1 parity, if adopted later, is a new stratum. A no means BC1 parity before the first production registration, with a further pilot (NP1.9). *Was (aa).*

**The API arm**
- **(ag)** The API comparison set is CHORUS only, the clean re-canary and the three replicate-gate cells, with every other API cell out of scope. This supersedes the API arm's longest-affordable-prefix scope rule (NP1.8). *Was (ab).*
- **(ah)** The native/API contrast for CHORUS is descriptive, with no directional rule (NP1.8). *Split from (ac).*
- **(ai)** The two arms' schema releases may differ, declared. A no means both sides run one release, fixed before the cells it governs (NP1.8). *Split from (ac).*
- **(aj)** No cell of the API comparison set and nothing on NP1.9's deferred list is a prerequisite for a native pilot or production cell. This holds only with a yes to amendment N1's item (y); with a no, D35's diagnostic canary on the API route precedes native integration (NP1.8, NP1.9). *Was (ad).*

**Timing**
- **(ak)** If the canary's word is given before this amendment is ratified: the canary's reading is a floor input only if the owner's answers to (a), (e), (f), (r), (s), (t), (u) and (ab) were recorded in the coordination record before the canary's dispatch. Otherwise it is excluded, and one replacement CHORUS pilot supplies CHORUS's fraction: n=1, floor pending, judged by B0–B7, at most two attempts, run after NP1b and before the AI_READI pilot, with a rule-level rejection ending the condition. A no means that in that case no production cell registers until a revised amendment (NP1.5, NP1.6, NP1.7). *Was (af); replaced.*

v3's item (ae), that this amendment is ratified before the canary's word, is no longer a lettered item. It is the header's condition, and the decision that makes it operative is amendment N1's item (ah).''')


def main() -> int:
    raw = subprocess.run(["git", "-C", WORKTREE, "show", f"{V3_COMMIT}:{PATH}"],
                         check=True, capture_output=True).stdout
    if hashlib.sha256(raw).hexdigest() != V3_SHA256:
        print("refusing: v3 bytes differ from the recorded sha256", file=sys.stderr)
        return 2
    text = raw.decode("utf-8")
    for old, new in SUBS:
        if text.count(old) != 1:
            print(f"refusing: {text.count(old)} occurrences of {old[:70]!r}", file=sys.stderr)
            return 3
        text = text.replace(old, new)
    lines = text.split("\n")
    spans = sorted(RANGES, key=lambda r: r[0], reverse=True)
    low = len(lines) + 1
    for start, end, new in spans:
        if end >= low or start > end + 1 or start < 1:
            print(f"refusing: range {start}-{end} overlaps or is malformed", file=sys.stderr)
            return 4
        lines[start - 1:end] = new.split("\n")
        low = start
    out = "\n".join(lines)
    if "@" in out:
        print("refusing: at-sign in the output", file=sys.stderr)
        return 5
    with open(f"{WORKTREE}/{PATH}", "w", encoding="utf-8") as handle:
        handle.write(out)
    print(len(out.split("\n")) - 1, "lines;", "sha256", hashlib.sha256(out.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
