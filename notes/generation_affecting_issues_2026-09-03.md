# Open issues that affect generation (2026-09-03)

The open issues whose fix lands in the generation path — the prompt, the
reconcile/audit code, the bundle bytes, the runtime, or the schema the
prompt embeds. Under the adopted production rule (#849, registered in
`notes/generic_v7_analysis_plan.md`) any change to those invalidates the
frozen configuration: the fix reaches records only through a new label and
a fresh arm, never by editing records in place. Issues that affect the
records or their evaluation *without* regeneration (checkers, packs,
selection, dispositions, rubric agents, provenance backfills) are the
complement and are not listed here.

Evidence this table was drawn from: the completed 2026-09-01 v7 API
production arm and its evaluation — `notes/arm_2026-09-01_v7_production_comparison.md`
(receipts 12-vs-12, rubrics, the 12/12 review pass, dispositions, the
instrument changes of #907), `notes/cross_read_rubrics_vs_reviews_2026-08-30.md`
(what the rubrics and reviews each measure), the twelve
`{PROJECT}_review.yaml` files under
`data/d4d_concatenated/claudecode_agent_core/2026-09-01_claude-opus-5-api-generic-v7_rep*/`,
and `gh issue list --state open`.

| # | Issue | Path it changes | Why it needs a run | Fix reaches records only by |
|---|---|---|---|---|
| **Prompt / rules — re-baselines the condition (new pin, new label)** | | | | |
| 830 | v6→v8: recurring adverse-slot patterns to encode as rules or slot guidance | prompt rules | The patterns (plan-as-done, absence statements, Person-as-string, pointer entries) are model behaviour the reviews keep finding | v8 arm |
| 803 | Fragment rule (rule-14) conflicts with identifier slots and the id projector — v8 half | prompt rule + `derive_core` | Pack side is done; the rule text itself still contradicts the projector | v8 arm |
| 901 | Unforced mints on real-world referents — generation half | prompt rule | Twelve `#creator-*`/`#grant-*` fragments in CM4AI rep3 are the model inventing ids | v8 arm |
| 902 | Receipt coverage degree-limited (48–208 of 142–508) — if fixed by prompt | prompt (receipt-per-roster-entry) | Alternative is reporting-only, which is the no-regen route | v8 arm, or none |
| 647 | No guard against a real registry id / DOI prefix entering the generic prompts as an example | prompt hygiene | A guard is a test, but any prompt it forces a change in rotates the pin | v8 arm if a prompt changes |
| 648 | Parity guard blocks the historical sentence, not the concept | prompt hygiene | Same: a guard; regen only if it forces a prompt edit | v8 arm if a prompt changes |
| **Reconcile / audit code — same configuration digest as the prompt** | | | | |
| 900 | Reconcile over-flattens class-ranged slots; no key list for Grant | reconcile §2.3/§2.4 | Emails and ORCIDs were discarded at reconcile time; a repair script could move award numbers from notes into `grant_number`, but the Person fields need a re-read of the bundle | v8 arm (partial repair possible) |
| **Bundle bytes — moves `bundle_md5`, the chunk manifest, and every receipt anchored to them** | | | | |
| 886 | AI_READI bundle drops a character mid-sentence ("tudy visit") | preprocess | Honest verbatim quotes fail receipts; fixing the bundle orphans existing receipts | fresh AI_READI runs |
| 875 | `fix_mojibake` repairs only the em-dash signature class; accented-only mojibake stays broken | preprocess | Same drift mechanics as #872/#874, which already forced the 2026-09-01 restart | fresh runs on affected projects |
| **Runtime / provider — future runs' reliability and cost, not existing records** | | | | |
| 777 | Three consecutive full-phase stalls after the cap rose to 128k | CBORG + watchdog | Stall rate correlates with request size; bounded by watchdog+resume but unfixed | future runs |
| 832 | AI_READI at 74–100% of cap with ~70–75% of output spent on reasoning | `full.max_tokens` | Thin headroom; raising the cap is itself a configuration change (#771) | future runs |
| 771 | Raising `max_tokens` within v7 is a silent instrument change no check flags | provenance check | A checker, but its subject is generation config drift | future runs |
| 656 | A killed invocation's `api_usage` is lost | runner | Provenance written only at run end | future runs |
| **Launchers and pipeline shape for the next arms** | | | | |
| 688 | No agentic batch launcher: waves, resume, `run_observed` hand-orchestrated | agentic path | The v6 arm was hand-driven; a v8 agentic arm would be too | next agentic arm |
| 690 | API and agentic arms share the `claudecode_agent` directory; arm identity lives only in the label | layout | Changing it moves every run directory; do it before the next arm, not after | next arm |
| 623/624/637 | Manifest as project registry; per-project bundle mapping in batch; generalized preprocessing/concat/batch | batch generation | Needed before any dataset outside Bridge2AI can be run | external datasets |
| 621 | Provenance falsely attests the Bridge2AI manifest for an external bundle | recorder | Any external-bundle run is misattributed until fixed | external datasets |
| 629 | Legacy extraction paths broken and GC-shaped | legacy generators | Fix-or-delete decision | — |
| 116 | Redo D4D generation with latest RO-Crate and full mappings | RO-Crate arm | An explicit regeneration request | RO-Crate arm |
| 152 | Linked process: generate → validate → eval → semantic feedback | pipeline | A new generation mode | — |
| **Schema changes that alter what the prompt embeds** | | | | |
| 805 | `principal_investigator` / `committee_contact` range Person but ask for a name | schema | Schema digest is in the prompt; changing the range re-baselines | v8 arm |
| 457 | Constrain `uriorcurie` with a pattern (7,415 existing values would fail) | schema | Same; plus a migration of committed values | v8 arm + migration |
| 297 | LinkML cannot express string-or-object range; `target_dataset` stays a reference | schema | Whatever resolution is chosen changes the target | v8 arm |
| **Closable** | | | | |
| 834 | Define the v7 production cohort | — | Resolved by the #849 production decision and the completed 2026-09-01 arm | close |

## Reading it as a plan

The first two groups (#830, #803, #901, #902-prompt, #900, #805) are one
coherent **v8 configuration** — they should land together as a single pin
rotation and schema regeneration, then one fresh 4×3 arm, rather than each
forcing its own restart. The bundle fixes (#886, #875) should go in
*before* that arm's manifests are cut, because they move the bytes
everything else anchors to. The runtime and launcher items decide how
cheaply that arm runs, and the generalization group is a separate track for
datasets beyond Bridge2AI.

## Findings from the v7 review pass that bear on v8 (for cross-check)

From the twelve reviews (`notes/arm_2026-09-01_v7_production_comparison.md`,
"Recurring findings with structure"): rule-15 coverage degree violated in
8/12 (#902); reconcile over-flattening Person/Grant (#900); unforced mints
(#901); scope leaks surviving reconciliation (VOICE rep2 pediatric clause,
CM4AI rep3 historical-as-current — #441 class, no dedicated issue);
rule-12 British spellings in generated prose (139 hits on the arm under
instrument v3 — #836/#859 fixed the *detector*; the generation-side rule
is part of #830); rule-01 inferences (deductions from stated lines);
rule-06/07 absence statements and access routes in guarantee/format
fields (#830); the AI_READI rep3 byte-sum miscomputation (arithmetic
presented as sourced fact — no generation-side issue filed); the
report/record contradiction on `extension_mechanism` (reconcile report
claims a retention the record lacks — no issue filed).
