# Open issues that affect generation (2026-09-03)

The open issues whose fix lands in the generation path — the prompt, the
reconcile/audit code, the bundle bytes, the runtime (API or agentic), or
the schema the prompt embeds. Under the adopted production rule (#849,
registered in `notes/generic_v7_analysis_plan.md`) any change to those
invalidates the frozen configuration: the fix reaches records only through
a new label and a fresh arm, never by editing records in place. Issues that
affect the records or their evaluation *without* regeneration (checkers,
packs, selection, dispositions, rubric agents, provenance backfills —
#906, #908, #909, #910 among the recent ones) are the complement and are
not listed here.

Evidence this table was drawn from: the completed 2026-09-01 v7 API
production arm and its evaluation — `notes/arm_2026-09-01_v7_production_comparison.md`
(receipts 12-vs-12, rubrics, the 12/12 review pass, dispositions, the
instrument changes of #907), `notes/cross_read_rubrics_vs_reviews_2026-08-30.md`
(what the rubrics and reviews each measure), the twelve
`{PROJECT}_review.yaml` files under
`data/d4d_concatenated/claudecode_agent_core/2026-09-01_claude-opus-5-api-generic-v7_rep*/`,
and `gh issue list --state open`. Reviewed for completeness and accuracy by
Codex (gpt-5.6-sol, 2026-09-03; the corrections it produced are folded in
and listed at the end).

| # | Issue | Path it changes | Why it needs a run | Fix reaches records only by |
|---|---|---|---|---|
| **Prompt / rules — re-baselines the condition (new pin, new label)** | | | | |
| 830 | v6→v8: recurring adverse-slot patterns to encode as rules or slot guidance | prompt rules | The issue's five patterns (enum slots inferred without a passage, `raw_data_format` naming a released standard, PI role inflation, `scope_impact` composed beyond the fact, award period as collection period): three recur on the v7 arm, the timeframe one reads as fixed. The 2026-09-01 pass adds plan-as-done (CHORUS rep1 slot-008/024, CM4AI rep3 slot-060), absence statements and access routes in the wrong fields (rule-06/07 in seven records), and pointer entries (AI_READI rep3 `variables[8]`) — recorded in the issue's 2026-09-03 comment. "Person-as-string" is **not** here: it is the reconcile script's own §2.4 flattening (#900/#805). | v8 arm |
| 911 | One object per distinct entity — separately-stated entities collapsed into one (rule-05) | prompt rules | AI_READI rep2 `data_collectors[4]`, `raw_data_sources`; rep3 `funders[3]` merges seven manufacturers | v8 arm |
| 803 | Fragment rule (rule-14) conflicts with identifier slots and the id projector — v8 half | prompt rule + `derive_core` | Pack side is done; the rule text itself still contradicts the projector | v8 arm |
| 901 | Unforced mints on real-world referents — generation half | prompt rule | Twelve `#creator-*`/`#grant-*` fragments in CM4AI rep3 and **22** `#org-*`/`#grant-*` in VOICE rep3 are the model inventing ids | v8 arm |
| 902 | Receipt coverage degree-limited (48–208 of 142–508; rule-15 violated 8/12) — if fixed by prompt | prompt (receipt-per-roster-entry) | Alternative is reporting-only, which is the no-regen route | v8 arm, or none |
| 914 | Arithmetic and retention claims presented as sourced fact (byte sum miscomputed; report claims a slot the record lacks) | prompt rule + reconcile report check | AI_READI rep3 rule-01 and slot-058; the checker half is #684 | v8 arm |
| 913 | Scope leaks surviving reconciliation — related-but-distinct or historical material stated as the referent's own (#441 class) | prompt rule + reconcile check | VOICE rep2 slot-009 (amended), CM4AI rep3 slot-030 (retained) | v8 arm (reconcile half could also run offline) |
| 647 | No guard against a real registry id / DOI prefix entering the generic prompts as an example | prompt hygiene | A guard is a test, but any prompt it forces a change in rotates the pin | v8 arm if a prompt changes |
| 648 | Parity guard blocks the historical sentence, not the concept | prompt hygiene | Same: a guard; regen only if it forces a prompt edit | v8 arm if a prompt changes |
| **Reconcile / audit code — same configuration digest as the prompt** | | | | |
| 900 | Reconcile over-flattens class-ranged slots; no key list for Grant | reconcile §2.3/§2.4 | Emails and ORCIDs were discarded at reconcile time (rule-08 in six records); a repair script could move award numbers from notes into `grant_number`, but the Person fields need a re-read of the bundle. **Decide #805 first** — whether these slots stay Person-ranged determines what the reconcile fix restores | v8 arm (partial repair possible) |
| **Bundle bytes — moves `bundle_md5`, the chunk manifest, and every receipt anchored to them** | | | | |
| 886 | AI_READI bundle drops a character mid-sentence ("tudy visit") | preprocess | Honest verbatim quotes fail receipts; fixing the bundle orphans existing receipts | fresh AI_READI runs |
| 875 | `fix_mojibake` repairs only the em-dash signature class; accented-only mojibake stays broken | preprocess | Same drift mechanics as #872/#874, which already forced the 2026-09-01 restart | fresh runs on affected projects |
| 625 | Source ingestion assumes a Google Sheet of URLs, six formats and eight hosts | preprocess | Any new source kind changes the bundle bytes | fresh runs on affected projects |
| **Runtime — future runs' reliability and cost, not existing records** | | | | |
| 777 | Three consecutive full-phase stalls after the cap rose to 128k | API: CBORG + watchdog | Stall rate correlates with request size; bounded by watchdog+resume but unfixed | future API runs |
| 832 | AI_READI at 74–100% of cap with ~70–75% of output spent on reasoning | API: `full.max_tokens` | Thin headroom; raising the cap is itself a configuration change (#771) | future API runs |
| 771 | Raising `max_tokens` within v7 is a silent instrument change no check flags | provenance check | A checker, but its subject is generation config drift | future API runs |
| 656 | A killed invocation's `api_usage` is lost | API runner | Provenance written only at run end | future API runs |
| 775 | A chunk opened partially can be receipted as fully reviewed | agentic receipt protocol | The receipt is the agent's claim; the read windows are the observation | next agentic arm |
| 776 | Receipt entries edited by script after the check, not written before the next chunk | agentic receipt protocol | Same protocol gap, on the writing side | next agentic arm |
| **Launchers and pipeline shape for the next arms** | | | | |
| 688 | No agentic batch launcher: waves, resume, `run_observed` hand-orchestrated | agentic path | The v6 arm was hand-driven; a v8 agentic arm would be too | next agentic arm |
| 690 | API and agentic arms share the `claudecode_agent` directory; arm identity lives only in the label | layout | Changing it moves every run directory; do it before the next arm, not after | next arm |
| 623/624/637 | Manifest as project registry; per-project bundle mapping in batch; generalized preprocessing/concat/batch | batch generation | Needed before any dataset outside Bridge2AI can be run | external datasets |
| 626 | `VOICE_PEDIATRIC_source_dir` sits inside `projects` and is iterated as if it were a project | batch generation | A concrete crash path in the batch loop | next arm / external datasets |
| 621 | Provenance falsely attests the Bridge2AI manifest for an external bundle | recorder | Any external-bundle run is misattributed until fixed | external datasets |
| 629 | Legacy extraction paths broken and GC-shaped | legacy generators | Fix-or-delete decision | — |
| 116 | Redo D4D generation with latest RO-Crate and full mappings | RO-Crate arm | An explicit regeneration request | RO-Crate arm |
| 152 | Linked process: generate → validate → eval → semantic feedback | pipeline | A new generation mode | — |
| **Schema changes that alter what the prompt embeds** | | | | |
| 805 | `principal_investigator` / `committee_contact` range Person but ask for a name | schema | Schema digest is in the prompt; changing the range re-baselines. The decision gates #900 | v8 arm |
| 912 | B2AI_TOPIC / B2AI_SUBSTRATE local parts unverifiable by reviewers — embed the registry's labels in the digest (or the pack) | schema digest (or pack) | Three reviews could score `B2AI_TOPIC:43` only as well-formed | v8 arm (digest) or none (pack) |
| 457 | Constrain `uriorcurie` with a pattern (7,415 existing values would fail) | schema | Same; plus a migration of committed values | v8 arm + migration |
| 297 | LinkML cannot express string-or-object range; `target_dataset` stays a reference | schema | Whatever resolution is chosen changes the target | v8 arm |
| **Closable** | | | | |
| 834 | Define the v7 production cohort | — | Resolved by the #849 production decision and the completed 2026-09-01 arm | close |

Not listed, deliberately: #831 (a measurement of v7 coverage and attribution,
now superseded by the production numbers — it informs #902/#830, it has no
landing spot of its own); #873 (defers its own fix to #803/#830, and asks
that the fix include a marker-placement/runtime check, not only a rule);
#378 (a deterministic post-generation enrichment, never model-invented);
#627/#628 (evaluation-side and architectural); #630 (the tracker).

## Reading it as a plan

The prompt-rule and reconcile groups (#830 with its 2026-09-03 comment,
#911, #803, #901, #902-prompt, #914, #913, #900, #805, #912-digest) are one
coherent **v8 configuration** — they should land together as a single pin
rotation and schema regeneration, then one fresh 4×3 arm, rather than each
forcing its own restart. Two orderings inside it matter: draft the v8 rules
from #830's *comment* as well as its body (the body alone targets the
earlier arm's patterns and misses plan-as-done, absence statements and
pointer entries), and settle **#805 before #900** — what the reconcile fix
restores depends on whether those slots stay Person-ranged. The bundle
fixes (#886, #875, #625) go in *before* that arm's manifests are cut,
because they move the bytes everything else anchors to. The runtime items
(API and agentic) decide how cheaply that arm runs, and the generalization
group is a separate track for datasets beyond Bridge2AI.

One caveat over the whole table: every "why it needs a run" that cites an
adverse count rests on a single reviewer per record (Claude judging
Claude); the reliability program measured pooled κ = 0.53 and #835 (a
second judge before adverse rates gate or select) is still open.

## Findings from the v7 review pass that bear on v8

From the twelve reviews (`notes/arm_2026-09-01_v7_production_comparison.md`,
"Recurring findings with structure"): rule-15 coverage degree violated in
8/12 (#902); reconcile over-flattening Person/Grant (#900); unforced mints
(#901); scope leaks surviving reconciliation (#913); entity collapsing
(#911); arithmetic and retention claims as sourced fact (#914);
rule-12 British spellings in generated prose (139 hits on the arm under
instrument v3 — #836/#859 fixed the *detector*; the generation-side rule
is part of #830); rule-01 inferences (deductions from stated lines);
rule-06/07 absence statements and access routes in the wrong fields
(#830's comment); B2AI_TOPIC/SUBSTRATE terms unverifiable (#912).

## Codex review (2026-09-03) — what it changed here

Accuracy: every issue-to-fix-path mapping held except #830, whose row cited
patterns the issue body does not contain and attributed "Person-as-string"
to the model when every instance is the reconcile script's own flattening
(#900/#805) — the row and the issue are corrected. Completeness against the
backlog: #775/#776 were a whole missing category (the agentic receipt
runtime), #625/#626 belonged beside #623/#624/#637. Completeness against
the evidence: four generation-side patterns had no issue — now #911, #912,
#913, #914. Sequencing: #805 before #900; #830's comment before drafting.
Verdict after corrections: fit to plan the v8 arm from.
