# generic v8 — preparation plan (2026-09-03, before any v8 generation)

Same purpose as the v5–v7 plans: what v8 changes, why the evidence says
so, the predictions the change is held to, the canary rule, and what a
v7-against-v8 comparison can and cannot attribute. Written from the
completed 2026-09-01 v7 production arm (12/12, reviewed 12/12), the
Codex-reviewed generation-issue table
(`notes/generation_affecting_issues_2026-09-03.md`) and a read of the
v7 prompt, the phase instructions and the schema digest.

## What the evidence actually says

**The rules already exist; the model violates them.** Every recurring
adverse pattern in the twelve v7 reviews is already forbidden by a rule
in `d4d_generic_arm_prompt_v7.md`:

| review finding (records) | rule that already forbids it |
|---|---|
| entity collapsing (#911; AI_READI rep2 ×2, rep3) | v2: "emit one object per distinct entity" |
| pointer entries, absence statements (#830 comment; 7 records on rule-06/07) | v2: "not with a pointer … not with a statement that it is pending or absent" |
| access routes in `future_guarantees`/`format` (rule-07) | v2: "put it in the field it answers, or omit it" |
| unforced mints (#901; CM4AI rep3 ×12, VOICE rep3 ×22) | v5 + v6: mint only a part another value points at |
| Grant/Person fields empty, content in prose (#900; rule-08 in 6 records) | v3: "populate the fields that class declares" |

So a v8 that adds more rule text of the same kind is the change the
evidence predicts will not work. Three things in the evidence are *not*
rule violations, and those are where v8 has leverage:

1. **The digest never shows the keys of the objects it asks for.**
   `schema_digest` rendered one level of nesting: `FundingMechanism`
   (with `grants: Grant[]`) is rendered; `Grant` is not — the model is
   told the range and never the keys, and the v3 rule asks it to
   populate fields it cannot see. This is the concrete root of #900's
   Grant half: `grant_number` is populated in none of the twelve records
   while the award numbers sit in prose.
2. **The Person "flattening" was the schema, not the model** (found by
   the #916 review and verified with `linkml-validate`): none of the five
   Person-ranged slots (`principal_investigator`, the two
   `contact_person`s, `committee_contact`, the deprecated
   `governance_committee_contact`) is `inlined`, so LinkML treats them as
   *references* — an inline Person object is rejected and the bare string
   is the only form that validates. All twelve v7 records carry strings
   and all twelve validate. The reconcile phase produced the only valid
   shape; the reviews' rule-08 verdicts on those slots (six records)
   charge the records with a schema constraint and are void; and #805's
   description ("a person's name such as 'Aaron Lee'") is, as things
   stand, the string form's only meaning. `Dataset` carries no list of
   Person entries for a reference to resolve to, so the decision (D1) is
   three-way, and until it is made the digest must say which attributes
   are references — it did, on the five Person slots, until D1 was
   adopted (below) and they became inlined objects. The #927 review then
   found that the marking's test (the slot's own `inlined` flags) was
   wrong: LinkML inlines a class range with no identifier implicitly, so
   `Person.affiliation: Organization[]` and Instance's
   `sampling_strategies` / `missing_information` take objects too. The
   marking now follows `SchemaView.is_inlined`; no attribute of the current
   schema is a reference.
3. **The class the reviews found most often — a true statement in the
   wrong tense or scope** — has no rule at all: prospective stated as
   current (plan-as-done: CHORUS rep2 slot-008/024, CM4AI rep2
   slot-019), historical stated as current (CM4AI rep3 slot-030), a
   related dataset's clause in the referent's slot (VOICE rep2 slot-009,
   #913), a derived figure stated as the source's (#914). Five
   instances, hand-classified from free-text evidence — prediction 4
   below names the classifier. These are not inference from stated
   lines (rule-01 covers that); they are attested passages attached to
   the wrong claim.
4. **Absence statements and access routes in the wrong field** (rule-06
   and rule-07, violated in seven records) have a rule (v2) and no
   mechanism: nothing in the phase chain looks for them. The audit phase
   lists what it flags (unsupported values, omissions, inconsistencies,
   shape) and does not list these; adding them to the audit instruction
   (step E2) is a mechanism, restating the v2 rule is not.

Two more facts shape the sequencing. Reconciliation rewrites 13% of
receipted values in place with no re-receipt route (#742, measured by
#907) — a v8 that moves work *out* of reconcile and into `full` (by
showing keys up front) also shrinks the unreceipted rewrite class. And
`british_spellings` at 139 on the arm under instrument v3 says the v5
American-English rule is not holding on AI_READI; that is #830's
generation half of #836/#859 and needs the same treatment as the others
— a mechanism, not a restatement.

## What v8 changes

A. **Digest depth two, through inlined attributes, with references
marked** (code, `schema_digest.py`, PR #916): render the keys of every
class reachable from a rendered nested class through an `inlined` /
`inlined_as_list` attribute — `Grant`, `Organization`, `Person` (via
`committee_members`) and `File` (via `FileCollection.resources`) —
under the same "required / optional / ranges / enums" shape; and mark
the class-ranged attributes that are references (eight at the time, the five Person slots among them)
(`principal_investigator: Person (reference — a string, not an
object)`, as it read before D1) in the one function both the digest and
the judge's view read (#486), so the "takes an object" header cannot
reach them — by LinkML's own rule (`SchemaView.is_inlined`), after the
#927 review showed the slot-flag test marked three implicitly inlined
attributes falsely. The
"mirrors the top-level listing" shortcut is now limited to classes
large enough to be truncated — it had fired on `Organization` and told
the model an Organization accepts every Dataset slot. Measured: 67 → 71
nested classes, 40,922 → 43,779 chars against the 44,000 budget —
**221 chars of headroom**, so any further digest addition (D1's option
(a) included) must first raise the budget deliberately. `File` is most
of the growth (six enum lists, 43 encodings among them) for a class no
v7 record populates under `resources`; kept because it is a legitimate
inline range and the budget holds, but it is the first thing to cut if
D1 needs the room. The Dataset digest fingerprint moves `580992ed` →
`163c7e4d` (recorded in `digest_inventory.yaml` and the schema-sync
test); the fitness cache keys on it, so this moves every condition's
assembly digest and is itself a re-baseline. Closes the digest half of
#900; the Person half is D1.

B. **Registry term labels — pack side only** (#912). The digest already
renders `id=name` pairs for `data_topic`/`data_substrate`
(`render_values_from`, #538), so the model sees the labels; the
reviewer does not. `build_pack` resolves `values_from` CURIEs through
`schema_digest.vocabularies()` and shows `CURIE — label` on the item.
No regeneration; not part of the v8 configuration, listed here only
because the plan's first draft put it in the digest.

C. **Schema: the five Person-ranged slots inlined** (#805, decision D1
option (a), adopted 2026-09-03): `principal_investigator`, both
`contact_person`s, `committee_contact` and the deprecated
`governance_committee_contact` carry `inlined: true` and descriptions
that ask for the object — `name`, and where the evidence states them
`orcid`, `email`, `affiliation`. Verified with `linkml-validate` on the
regenerated schema: a bare name string now fails, an object with an `id`
validates, an object without one fails (`Person.id` is the class
identifier, so a PI without an ORCID gets a forced fragment mint — exempt
from rule-14 by #803's `id_slots` logic). Consequence stated: every
existing record holding a string there is invalid under this schema;
verdicts stay pinned to the schema they were reached against (#426), as
after the #646 doi move, and commands that re-validate live (`d4d runs
select`) report them invalid — a re-selection across pre-v8 arms must use
the recorded verdicts. The digest moves `163c7e4d` → `ffe03dd4` (43,582 chars; 418
headroom; no reference marker remains, and SamplingStrategy and
MissingInfo now render — 72 nested classes), the Core digest with it.

D. **`ADDED IN v8`** — four rules (R1–R4; the decisions below are
D1–D6, a different series), each naming a mechanism rather than
restating a prohibition:

1. (R1) *Inlined vs reference ranges, by the digest's marking.* A class-ranged
   attribute the digest marks `(reference — a string, not an object)`
   takes exactly that; every other class-ranged attribute takes an
   object with the keys the digest lists for that class — `Grant` under
   `grants`, `Organization` under `affiliations` — and a reconcile or
   repair phase must never reduce such an object to a string, nor
   inflate a reference to an object. (#900's Grant half; with D1 adopted
   the Person slots are objects and the current schema marks no
   reference — the first sentence is there for the next one.)
2. (R2) *Tense and scope.* Before writing a value from a passage, name to
   yourself what the passage is about and when: a plan, a proposal or
   a future release is stated as such or omitted, never as the current
   state; a description of an earlier release or an archived version is
   not a fact about the referent's current release; a passage under a
   source the manifest declares related-but-distinct describes that
   dataset, not this one, and belongs only in `related_datasets`. The
   coverage receipt's snippet must come from a passage about the
   referent in the present. (#830 comment, #913)
3. (R3) *Derived figures.* A number the record computes from attested
   figures — a sum, a difference, a fraction, a count — is stated as
   the record's computation with its inputs named, never as a figure a
   source reported; a passage cannot receipt an arithmetic result it
   does not contain. (#914)
4. (R4) *Receipts per entry for rosters.* Where a slot is a list of objects
   the bundle states one by one — creators, funders, variables, file
   collections, files — each entry carries its own receipt naming the passage that
   states it; a roster receipted by one passage for one entry has
   receipted one entry. (#902 — decision D2)

The American-English rule (v5) stays as text; the mechanism for it is
instrument v3 in the canary gate (#906 decides the baseline), which is
where a rule the model does not hold is enforced.

E. **Reconcile report gate** (code, `report_claims` + `api_runner`): the
`report` phase's claims are checked against the record before the run
completes, and a report that claims a retention or removal the record
does not show is regenerated once with the contradiction named (#684,
#914's checker half). No prompt change; a runner change, so part of the
v8 configuration.

E2. **Audit phase looks for the four classes the rules forbid and the
reviews keep finding** (code, `PHASE_INSTRUCTIONS["audit"]`, PR #928):
a value stating documentation is absent, pending or held elsewhere; a
value answering a neighbouring field (an access route in
`future_guarantees` or `format`, a prohibition in `prohibition_reason`);
a plan, proposal or earlier release stated as the current state; a
figure computed from other figures presented as one a source reported.
The mechanism for the v2 rule and for prediction 3; a runner change like
E. The audit instruction is shared by every condition, so this moves
every condition's assembly digest — one re-baseline, stated here.

F. **Bundle fixes before manifests are cut**: #886 (the dropped
sentence-initial character), #875 (accent-only mojibake). Both move
`bundle_md5`; they land first so v8's manifests and receipts anchor to
the final bytes. #625 only if a new source kind is in scope.

Not in v8: #647/#648 (guards — added as tests without a prompt edit),
#831/#873 (measurements), the agentic-arm items (#688, #775, #776 —
decision D5), the generalization track (#621–#637), #457/#297 (schema
work with a migration of committed values; separate).

## Predictions, registered

| # | metric | attributed to | prediction |
|---|---|---|---|
| 1 | rule-08 violated in the review pass, on inlined class ranges only (Grant; Person too if D1 inlines it) — reviewers told which attributes are references | A + C + D1 | 0 of 12; on v7 the 6 of 12 were Person slots the schema forced to strings, which the corrected pack no longer charges |
| 2 | `grant_number` populated where the bundle states an NIH award number — denominator registered now: AI_READI 2, CHORUS 1, CM4AI 3, VOICE 3 distinct award numbers per bundle (pattern `\b[A-Z]\d{2}[A-Z]{2}\d{6}\b` and kin, e.g. OT2OD032644). **Recounted 2026-09-09 (#1028)** with the pattern actually used (`awards.NIH_AWARD`: a leading type digit, one-letter-two-digit or two-letter-one-digit activity codes, an optional space or hyphen before the institute code as the flagship papers write it, a `-NN` suffix — the narrow form matches only 1/0/2/2 of them), pinned to each bundle's md5 and reproduced by `tests/test_awards.py`: award-shaped tokens AI_READI **4** (d22b61a9…), CHORUS **1** (9b2ef4b6…), CM4AI **8** (50037fc6…), VOICE **3** (9193c3cb…). That is the ceiling as registered ("where the bundle states an NIH award number"; the registration itself anticipated that some are cited, not funding). A second, *post-hoc* reading — stated as funding this dataset: an award the dataset paper's funding statement attributes to this research or this work; not one it attributes to named investigators, to another named project, or to the platform hosting the release — gives AI_READI **3** (OT2OD032644, P30DK035816, UL1TR003096, the BMJ Open protocol paper's "This research is supported by"; the Nature Metabolism paper corroborates P30 DK035816; UL1TR001442 is an author's competing-interest grant), CHORUS **1**, CM4AI **2** (OT2OD032742 and U54HG012513: the CM4AI dataset paper's "This work was funded by"; the CM4AI Nature resource paper's acknowledgement names U54CA274502, U24HG012107, U24CA269436, U24HG006673, R01GM083960 and P41GM109824 against named investigators and the Cancer Cell Map, Cytoscape, NDEx and BioPlex projects), VOICE **1** (OT2OD032720; R01EB030362 and U24EB037545 are PhysioNet's platform grants in every release page's footer). `d4d runs award-numbers --contexts` prints the passages both readings rest on. | A | ≥ 1 per project in every replicate, from 0 of 12 on v7; the denominator is the ceiling, not the target (some are cited, not funding) |
| 3 | rule-06/07 violated (absence statements, access routes) | E2 | ≤ 2 of 12, from 7 of 12; a fall that does not reach this says the audit did not catch them |
| 4 | misread verdicts of the tense/scope class — classifier: a `misread` whose evidence names a plan/proposal/future release, an earlier version or archive, or a related-but-distinct source as the passage's subject | R2 | 0 in the sampled receipted slots, from 5 on v7 (CHORUS rep2 ×2, CM4AI rep2, VOICE rep2, CM4AI rep3) |
| 5 | `value_changed_after_receipt` | A (work moved out of reconcile), halved by the Person finding | below 10% of receipt paths, from 13.0%; the v6 agentic arm re-receipts and sits at 0 |
| 6 | receipts `with_receipt / receiptable` | R4 (D2) | above 40% arm-wide, from 35.5% (agentic 48.2%); rule-15 violated ≤ 6 of 12, from 8 |
| 7 | unforced mints (rule-11/14) | none, watched | no record above v7's worst (VOICE rep3, 22) and the arm median stays 0; v8 adds no minting rule, so a fall would be the digest's labels displacing invented ids |
| 8 | populated leaves, rubric10/20 | A, watched | not below the v7 per-project replicate minimum; a fall means the larger digest displaced reading (the v7 markers confound, in a new form) |
| 9 | spend | A | prompt tokens rise by ~2,900 chars of digest per call; `full` output tokens within ±10% of v7's per-project mean |

**Prediction 9's baseline rule, registered (#1026, 2026-09-09).** The v7
per-project mean is `run_telemetry.full_output_baseline` under
`PREDICTION_9_RULE` — the accepted attempt per phase (the last `end_turn`
`full` attempt with no abandoned-transport marker and no
`unusable_reason`; a retried attempt excluded; `full_readdress` and
`repair_full` are their own phases and not counted), a row the provenance
lost — a resume past the phase, or an abandoned attempt whose completed
retry was lost with the unseeded prior usage while the abandoned row
survived through the ledger (a shape no corpus record has today; VOICE
2026-09-04f rep2 keeps both rows) — recovered from the reasoning log, whose
entries are matched by (attempt, output_tokens) against the rows the
provenance refused, never by attempt number alone; the mean over the
replicates that yield a row with the replicate range beside it, and the
others named — printed by `d4d runs full-output-baseline`. The AI_READI 2026-09-04f row was read
three ways before the rule was code: by hand from rep2's retried attempt
(86,707, +3.2%), then over the two replicates with a provenance row alone,
rep3 dropped (78,646, +13.8%); the rule reads +4.4% (v7 production: 79,078
/ 78,215 / 99,870 → 85,721, rep3 recovered from its reasoning log). Under
the same rule VOICE is 76,159 (73,375 / 74,126 / 80,976), CHORUS 41,068
(35,025 / 40,186 / 47,994) and CM4AI 41,370 (26,766 with rep1's accepted
attempt 2 / 31,044 / 66,300 — a 2.5× range, so a ±10% band on that mean is
a weaker instrument than the mean suggests). The telemetry comparison
(`d4d runs telemetry`) read the *first* `end_turn` attempt until this
change — the one a retried phase threw away, wrong on all nine records
whose provenance carries more than one accepted-eligible `full` attempt
(ten phases with AI_READI 2026-09-01 rep3, whose two live only in its
log); on the five that kept a phase-1 snapshot the accepted attempt is
the one whose `visible_text_chars` matches the artifact — and now reads
the accepted one.

### Falsification tests

- **Rules restated, mechanism absent.** If prediction 1 holds but 4 does
  not, the digest fixed what it can see and R2 did what v2's rules did —
  nothing. Then R2 is text and should be cut, not extended. If 3 does
  not hold, E2's audit addition did not catch what the reviews catch.
- **The digest displaced reading.** If populated leaves fall on
  prose-heavy slots while object slots rise, the model spent its
  attention on keys. Measure per slot family before averaging.
- **Receipts per entry filled, not written.** The v7 falsification test
  for generic snippets applies per roster entry: distinct snippets per
  roster / entries; a ratio near 1/N is the signature.

## What v8 can and cannot be compared against

- Against **v7 production (2026-09-01)**: same bundle kind, same
  manifest rule, same validator and review instrument (receipts,
  identity join, dispositions all landed after v7 ran and apply to
  both arms retroactively) — but the digest, the schema, the prompt and
  the bundle bytes (F) all move, so v7-vs-v8 measures the *package*.
  The per-prediction attribution above is the plan's claim about which
  part moved which metric; only an ablation (A alone, then A+C, …) would
  separate them, and none is planned unless prediction 8 fails.
- Against **v6 agentic**: unchanged in kind from the v7 plan's caveats;
  the agentic arm would need its own v8 (D5).
- `comparable_conditions("generic_v7", "generic_v8")` is true **by name**
  — one base step — and false once the arms' own records are passed to it
  (#1073): their assembly digests differ (`d2f01480…` against `f7006dc1…`),
  so `condition_delta` reports `["base", "assembly"]`. The prose above
  already said v7-vs-v8 measures the package; the function's `True` said
  otherwise to anyone who quoted it without the prose, which is the whole
  of #1073. `CONDITION_AXES` gains `generic_v8: {base: v8, tuned: False}`.

## Canary rule

Four per-project rep1 canaries in the v7 order (CM4AI, VOICE, AI_READI,
CHORUS), gated against the **v7 production per-project worst across
replicates** (`canary.baseline_for` semantics) on every existing metric
(not the v5 baseline v7 used — v7 is now the better instrument-matched
baseline), the receipt floors at 0 with the #891 exposure-adjusted
tolerances, and British counts under instrument v3 on both sides (the
v7 form blocks already carry v3 counts; #906 governs only whether the
AI_READI rep1 *verdict* is re-derived). A canary that
fails on a prediction-1/2 metric is a v8 defect; one that fails only on
bookkeeping classes follows the v7 retained-with-basis pattern. Fill to
4×3 only after all four pass; the five Aug-28 exploratory records stay
excluded from every v8 comparison as they were from v7's.

### Canary results

| project | label | verdict | basis |
|---|---|---|---|
| CM4AI | `2026-09-04c_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric under instrument v2: undeclared prefixes 6 vs 0, all `mailto:` person ids (D1 forces `Person.id`). Everything else passed: receipts clean with no re-addressing needed, resolver URLs 0 with 0 rewrites, report gate 1 → 0 among 9 claims, British 0. **Prediction 5: 1.3%** (from 28.3% and 36.0%); 6: 70.4%; 9: +94% (full output 80,319); 2: 0. | Step I (#981/#982): `mailto:` ids get a mechanism and the counter its v3. **Re-verdicted OK under v3** (6 → 0, prior verdict kept in the block) — and **not retained for the fill** (#984): the mechanism and R5 landed after it, so CM4AI runs a fourth time under the final package after VOICE, AI_READI and CHORUS. |
| VOICE | `2026-09-04d_claude-opus-5-api-generic-v8_rep1` | **regressed** on two metrics: report findings 5 vs 0 (18 → 5 among 94 claims after the regate; all five `retained | both` rows on slots CoreDataset does not declare — `citation`, `consent_revocations`, `participant_compensation`, `third_party_sharing`, `collection_consents` — which the regate could not fix because its detail named no cause) and British spellings 8 vs 2 (one word, `programme`, four times in the full record's prose, counted again in the core). Everything else passed: receipts 22/22 chunks, 242/260 snippets verified, 1 entry re-addressed and none unresolved; resolver URLs 0; undeclared prefixes 0 under v3; pair errors 0. Prediction 5: 27.7% (54/195 changed after receipt, against < 10%); 6: 54.5%; 9: 79,582 (+4.5% against the v7 VOICE mean of 76,159); 2: 0. | The report findings were a defect on both sides (#990/#992): the report instruction now says `both` only where the core carries the slot, the finding names the cause, and the checker is instrument v2 (#996) — the strict reading stays, so the block stays at 5 and the verdict stands. Generation-path change: **VOICE runs again under the final package**. British spellings: **normaliser adopted** (step J, #1002), lands before the re-run. |
| VOICE | `2026-09-04e_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric for a runner reason: chunks unreviewed 15 of 22 vs 0. The full phase's stream ended before `message_stop` (`output_tokens: 5, stop_reason: null` for 68,183 characters; 04d: 79,582 / `end_turn`), the SDK returned the partial snapshot, the runner accepted it because it parsed and carried the receipt marker, and the receipt — what was being streamed — stopped at c007. Everything else clean under the final package: report findings 1 → 0 after the regate among 34 claims, British 0 (the normaliser rewrote one `colour`), resolver URLs 0, prefixes 0, pair errors 0, snippets 17/17. | Runner defect (#1013, item 13): a stream without `message_stop` is retried as a transient failure. Not retained; VOICE runs again under the guard. Not a generation-path change: a complete stream's output is untouched. |
| VOICE | `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | **passed the gate** — the first complete run under the final package (04e ran under it and lost its stream), with the incomplete-stream guard (#1013) in place and no retry needed. Receipts 22/22 chunks, 238/243 snippets verified in the chunk cited (5 verbatim in another chunk, 0 mismatched or unchecked; 2 bearing on no token), 223/343 slots with a receipt; report gate 2 → 0 among 46 claims (the v7 floor of 0 is a derived floor: 3 vacuous, 0 measured, #684); British 2 = the baseline worst, both the `Temerty Centre` title-case skip in `source_caveats` (full + core; the normaliser rewrote nothing else); resolver URLs 0, prefixes 0, ungrounded 0, pair errors 0. Prediction 5: **6.3%** (12/189, under the registered < 10%); 6: 65.0%; 9: **unfavourable**, +24.7% against a registered ±10% (full output 94,936 vs the v7 VOICE mean 76,159; the full phase took 2,257 s); 2: `grant_number` populated 2. First record with the endpoint's own thinking count (#999): full phase 59,495 observed, the estimate 69,825 ran 17% high; thinking was 63% of the phase's output. | **Retained.** VOICE done; the order is now AI_READI, CHORUS, CM4AI (fourth). |
| AI_READI | `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | **passed the gate as instrumented — not retained**: the full record carries a top-level `source_caveats` key three times (the model's own phase-1 output had two), which no instrument counted and a standard loader silently reduces to the last, losing two caveats from the parsed record and the core (#1029; 0 of the 270 records on main have a duplicate key, so the floor is 0 and this is a regression). No regate, no recorded retry; one repair round (13 findings). Receipts 28/28 chunks, 254/265 snippets verified in the chunk cited (8 adjacent, 1 elsewhere, 0 mismatched or unchecked; 18 bearing on no token, 2 unattesting below the floors — reported, not gated), 151/431 slots with a receipt; report gate 0 among 43 claims (the v7 floor: 1 measured, 2 vacuous); British **0 vs a v7 worst of 52** — the normaliser rewrote 15 (`programme`, `enrolment`, `colour`, `licence`, `metres`, `centimetre`, `minimise`, `personalised`, `generalisability`), the model's own count; resolver URLs 0, prefixes 0, ungrounded 0, pair errors 0. Prediction 5: **8.9%** (17/192, under < 10%); 6: **unfavourable**, 35.0% against the registered > 40% (inside v7 AI_READI's own 31.7–47.4%; 148 short scalars and enums carry no receipt and 64 prose values are the thin part); 9: +4.4% (full output 89,500 vs the v7 production mean 85,721 over the accepted full attempts of all three replicates — rep2's attempt 2, 78,215, not the retried 94,336; rep3's 99,870 recovered from its reasoning log, its provenance having no full row after a resume — within ±10%; the rule is registered in #1026); 2: `grant_number` populated 3 (the registered ceiling of 2 undercounts the bundle's three awards, #1028). Thinking count: full phase 46,248 observed of 89,500 output (52%); the full phase took 977 s. The record header says `Temperature: 0.0` while the request sent none (#1027). | **Not retained** (#1029). Re-verdicted 2026-09-06 under the instrument (#1030): validation `passed: false` (`source_caveats` at lines 812, 1019, 1565), canary **regressed** on `duplicate keys` 1 against a floor of 0, the prior `ok` kept under `prior_verdict`. AI_READI runs again; CHORUS and CM4AI (fourth) follow. |
| CHORUS | `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | **passed the gate** on every row, the first run to complete under the recorder of #1037 — AI_READI 04g started six minutes earlier in a parallel batch and finished after it (verdict written by the batch to the record; sizes match the files; no retry). Receipts 8/8 chunks, 79/79 snippets verified in the chunk cited (0 adjacent, 0 elsewhere, 0 mismatched or unchecked; 0 bearing on no token), 54/186 slots with a receipt (53 before receipts v3, #1053); report gate 2 → 0 among 46 claims (the v7 floor of 0 is derived: 3 vacuous, 0 measured, #684); one repair round (3 findings); British 0 (the normaliser rewrote nothing; v7 worst 0); resolver URLs 0, prefixes 0, ungrounded 0, pair errors 0, duplicate keys 0. Prediction 5: **14.5%** (9/62 changed after receipt, 8/62 before receipts v3; against < 10%; v7 CHORUS 33.8 / 6.8 / 4.4%); 6: **unfavourable**, 29.0% against > 40% (28.5% before v3; below v7 CHORUS's own 33.8–37.4%; 132 of 186 receiptable slots carry none, most of them enums and short scalars); 9: **unfavourable**, +26.8% (full output 52,066 vs the v7 CHORUS mean 41,068; the full phase took 591 s); 2: `grant_number` populated **1** (v7: 0 on all three; the row first said 0, read off the wrong path — #1049). Thinking count: full phase 34,907 observed of 52,066 output (67%). The record's `repo.dirty_paths` names `urelian` for `aurelian` (#1039, recorder-only). | **Retained.** CHORUS done; AI_READI (again) ran alongside it, CM4AI (fourth) follows. |
| AI_READI | `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | **passed the gate** on every row, duplicate keys 0 (the 04f defect, #1029, did not recur). First live capture of the transport-error path (#1017/#1037): the `reconcile_full` stream lost its connection to an `httpx.ReadError` after 84 s and 23,672 characters, the runner recorded the snapshot and the ledger row and the retry completed (335 s); no regate. Receipts 28/28 chunks, 346/351 snippets verified in the chunk cited (4 adjacent, 1 elsewhere, 0 mismatched or unchecked; 27 bearing on no token, 0 unattesting), 280/480 slots with a receipt; report gate 0 among 42 claims; one repair round (5 findings); British **0 vs a v7 worst of 52**, the normaliser having rewritten 16; resolver URLs 0, prefixes 0, ungrounded 0, pair errors 0. Prediction 5: **3.3%** (8/246, under < 10%); 6: **58.3%** (above > 40%, and above v7 AI_READI's 31.7–47.4% — 04f measured 35.0% on the same bundle); 9: **unfavourable**, +34.3% (full output 115,100 vs the v7 production mean 85,721; the full phase took 1,245 s); 2: `grant_number` populated **3** (as 04f did; the row first said 0, read off the wrong path — #1049). Thinking count: full phase 72,735 observed of 115,100 output (63%). The header still says `Temperature: 0.0` (#1027); `repo.dirty_paths` carries `urelian` (#1039). | **Retained.** Three of four canaries retained (VOICE 04f, CHORUS 04f, AI_READI 04g); CM4AI (fourth) runs under `2026-09-04g`, then the fill. |
| CM4AI | `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | **passed the gate** on every row — the fourth CM4AI canary and the first under the final package (04c ran before steps I and J). The first `full` stream dropped to a `RemoteProtocolError` after 386 s and 19,748 characters (snapshot and ledger row recorded, #1017); the retry completed (1,274 s). Receipts 28/28 chunks, 156/174 snippets verified in the chunk cited (12 adjacent, 6 elsewhere, 0 mismatched or unchecked; 0 bearing on no token; 10 entry receipts over one leaf, reported), 279/374 slots with a receipt; report gate 0 among 10 claims; one repair round (2 findings); British 0 (v7 worst 2; nothing rewritten); undeclared prefixes 0 under v3 with no `mailto:` id written (the 04c defect, #981, did not recur); resolver URLs 0, ungrounded 0, pair errors 0, duplicate keys 0; minted fragments 16 distinct (v7 CM4AI 17 / 10 / 17; reported, never gated). Prediction 5: **1.2%** (2/161, under < 10%; v7 CM4AI 17.0 / 17.4 / 7.9%); 6: **74.6%** (above > 40% and v7 CM4AI's 21.9–37.0%); 9: **unfavourable**, +93.7% (full output 80,122 vs the v7 CM4AI mean 41,370 over accepted attempts — rep1's attempt 2, 26,766; 04c measured 80,319); 2: `grant_number` populated **3** (v7: 0 on all three; registered 3; the row first said 0, read off the wrong path — #1049). Thinking count: full phase 50,081 observed of 80,122 output (62.5%). `repo.dirty_paths` carries `urelian` and the snapshot `events: -1` (#1039/#1040, addressed in #1041, open when this row was written); the header still says `Temperature: 0.0` (#1027). | **Retained.** All four canaries retained (VOICE 04f, CHORUS 04f, AI_READI 04g, CM4AI 04g); the fill (8 runs) is next, on the maintainer's word. |
| CM4AI | `2026-09-04b_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric: resolver URLs in identifier slots 16 vs 0 (the dataset DOI as a URL under `id` plus 15 minted fragments); every receipt metric passed — the re-addressing turn dropped the one mis-addressed entry and the report gate regenerated 1 contradiction among 40 claims to 0, both firing on a live run for the first time. Coverage 288/407 (70.8%). British 2 (= v7 worst). One repair round (14). | **Deferred fix, step H (#974)**: identifier form is a rule with no mechanism; the normaliser lands before the third canary. Predictions: 2 unfavourable (0), 5 unfavourable (36.0%), 6 favourable (70.8%), 9 unfavourable (−26.7%). |
| CM4AI | `2026-09-04_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric: receipt findings 1 against a floor of 0; every other gated metric equal to or better than the v7 per-project worst (British spellings 0 vs 2). Full-phase output 31,207 of 128,000 (24%). One repair round (11 findings). Receipts: 28/28 chunks, 117/168 snippets verified (45 adjacent, 6 elsewhere), 206/342 slots with a receipt (60.2%). | **v8 defect (#952)**, the plan owner's decision on 2026-09-04: the finding is one receipt entry addressed to `subject`, a name the schema has no slot for, for a value the record holds under `keywords` — the v8 receipt rule names the record path the value fills, so the model broke a rule it was given. Not the v7 retained-with-basis pattern. No fill and no further canary until fixed and re-canaried; fix chosen: the runner re-addressing turn (step G, #953); the re-canary runs under a new prefix, `2026-09-04b_claude-opus-5-api-generic-v8`. Recorded in the record's `canary` block (with the withdrawn retained-with-basis reading as `prior_disposition`). **Predictions this record measures (n=1):** 2 favourable (`grant_number` populated 2 of 3); 6 favourable (60.2%); **5 unfavourable** (`value_changed_after_receipt` 41/145 = 28.3% against <10%; v7 CM4AI replicates 17.0/17.4/7.9%); **9 unfavourable** (`full` output 31,207 against the v7 CM4AI mean 41,370, −24.6%, outside ±10%). First launch stopped on a CBORG 403 (off-VPN) before any phase; resumed on the VPN. |

### Fill results (12 records, 2026-09-07)

The fill ran as two batches on 2026-09-07 03:44–06:07 UTC under the
#1037/#1041 recorder: `2026-09-04f` rep2–3 for VOICE and CHORUS,
`2026-09-04g` rep2–3 for AI_READI and CM4AI; each batch re-gated its
rep1 canary first (VOICE's offline verdict was superseded by the batch's,
prior kept, the `duplicate keys` row added). All 12 records validate and
pass `d4d runs check --strict`. Deterministic numbers below are read from
the records by a script (`grant_number` at `funders[].grants[]`, #1049);
the arm table `notes/arm_comparison.md` carries the v8 column.

| project | rep | receipts `with/receiptable` (6) | changed after receipt (5) | minted (7) | `grant_number` (2) | report findings stored (after regate) | British form / rewritten | `full` output (Δ v7 mean) (9) | thinking on `full` | `full` s | `full` attempts / abandoned (any phase) | repair findings |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VOICE | 1 | 65.0% 223/343 | 6.3% 12/189 | 15 | 2 | 0 (0) | 2 / 0 | 94,936 (+24.7%) | 59,495 | 2,257 | 1 / 0 | 10 |
| VOICE | 2 | 54.0% 141/261 | 12.5% 19/152 | 0 | 2 | 2 (2)ᶠ | 0 / 0 | 83,711 (+9.9%) | 47,827 | 2,091 | 2 / 1 | 9 |
| VOICE | 3 | 57.6% 220/382 | 8.1% 14/173 | 21 | 3 | 1 (1)ᶠ | 2 / 1 | 86,279 (+13.3%) | 47,302 | 928 | 1 / 1 | 8 |
| CHORUS | 1 | 29.0% 54/186 | 14.5% 9/62 | 0 | 1 | 0 (0) | 0 / 0 | 52,066 (+26.8%) | 34,907 | 591 | 1 / 0 | 3 |
| CHORUS | 2 | 33.5% 83/248 | 22.8% 18/79 | 0 | 1 | 0 | 0 / 0 | 43,814 (+6.7%) | 26,716 | 485 | 3ᵘ / 0 | 2 |
| CHORUS | 3 | 39.4% 78/198 | 13.7% 14/102 | 0 | 1 | 0 (0) | 0 / 0 | 42,656 (+3.9%) | 22,902 | 474 | 1 / 0 | 11 |
| AI_READI | 1 | 58.3% 280/480 | 3.3% 8/246 | 19 | 3 | 0 | 0 / 16 | 115,100 (+34.3%) | 72,735 | 1,245 | 1 / 1 | 5 |
| AI_READI | 2 | 38.8% 163/420 | 6.9% 16/233 | 22 | 3 | 0 | 0 / 47 | 115,616 (+34.9%) | 66,469 | 1,280 | 1 / 0 | 7 |
| AI_READI | 3 | 64.5% 251/389 | 3.8% 9/237 | 13 | 3 | 0 | 0 / 38 | 112,321 (+31.0%) | 68,669 | 1,212 | 1 / 1 | 8 |
| CM4AI | 1 | 74.6% 279/374 | 1.2% 2/161 | 16 | 3 | 0 | 0 / 0 | 80,122 (+93.7%) | 50,081 | 1,274 | 2 / 1 | 2 |
| CM4AI | 2 | 73.6% 312/424 | 16.7% 28/168 | 26 | 2 | 0 | 0 / 1 | 28,124 (−32.0%) | **0**ᵗ | 273 | 1 / 0 | 12 |
| CM4AI | 3 | 58.1% 226/389 | 43.8% 70/160 | 28 | 1 | 0 (0) | 0 / 2 | 31,614 (−23.6%) | **0**ᵗ | 298 | 1 / 0 | 12 |

ᶠ every stored finding is a `false_schema_claim` on a claim scoped to
the core schema, which the checker resolved against `Dataset` (#1046);
the true count is 0 and both runs were regated on it. ᵘ two `full`
responses judged unusable (no parseable object) and discarded without a
snapshot (#1048). ᵗ the endpoint returned no thinking block on `full`,
`reconcile_full`, `report` and the report re-checks (#1047). The runner
sent no `thinking` parameter, but on this model family omitting it runs
adaptive thinking, so these two are a **different generation regime, not a
run that was not asked**, and their rows on predictions 8 and 9 are marked
rather than averaged in. "The other ten got it on identical requests" is
true of the parameters, not the inputs: a `full` phase with no thinking
block is on 11 of the corpus's 152 reasoning logs — 8 of CM4AI's 33 logs
(9 of its 35 full-phase entries), across four CM4AI labels and two prompt
versions, plus VOICE twice and AI_READI once — so it is an
input-correlated adaptive outcome, not a proxy fault. From this change the
request states adaptive thinking explicitly and the record carries it as
`model.thinking_requested`; that puts the request on record and does not
make a recurrence a deviation — under adaptive the model decides per
request, and no block is a legal answer. `d4d provenance reasoning` names
the `full` phase without a block (`full_phase_without_reasoning`) rather
than any phase, since audit, report and core skip it routinely. The same two runs wrote 27 and 35 resolver URLs under
`id` (`normalisation.identifier_form`; 0 on the other ten), rewritten
to CURIEs at write time — the model-written count, not the arm's 0.
Abandoned attempts (transport drops, all retried to completion): 5 across
the arm, each with a snapshot and ledger row (#1017).

**Predictions, as measured on 12 of 12** (1, 3, 4 need the review pass;
8 the rubric evaluations — both pending):

| # | result | reading |
|---|---|---|
| 2 | **favourable** — `grant_number` populated in 12 of 12 (1–3 entries per record; VOICE's are one award under two or three application numbers), from 0 of 12 on v7 | A did what it was for; the registered target is ≥ 1 per record and is met on 12 of 12. Whether a record reaches the *ceiling* depends on which ceiling and which unit (#1028): under the ceiling as registered — every award-shaped token the bundle states, recounted AI_READI 4, CHORUS 1, CM4AI 8, VOICE 3, counting distinct awards — it is met on **3 of 12** (CHORUS only); under the post-hoc funding reading (3/1/2/1) on **11 of 12**, CM4AI rep3 alone one short (OT2OD032742 without U54HG012513). The row first said 8 of 12 against ceilings of 2/1/3/3 counting `grant_number` *entries*, under which VOICE rep3's three application numbers of one award "met" a ceiling of 3 and AI_READI's three awards read as an excess over 2; the ceilings undercounted the bundle and the unit was entries, not awards. No record populates an award its bundle does not state |
| 5 | **unfavourable** — 11.1% of receipt paths pooled (218/1,962) against < 10%, from 13.0%; 6 of 12 records under 10%; CM4AI rep3 alone 43.8% (70/160) | reconcile still rewrites receipted values; the fall is 2 points, not the halving predicted, and one record without thinking carries a third of the arm's rewrites |
| 6 | **favourable** — 56.4% pooled (2,309/4,094) against > 40%, from 35.4% (1,387/3,917); 8 of 12 records above 40%, CHORUS all three below (28.5–39.4%, its v7 33.8–37.4%) | R4/D2 moved coverage everywhere but CHORUS, whose bundle is the smallest (8 chunks) |
| 7 | **unfavourable** on the median — 15.5 against "stays 0" (v7 median 0), 8 of 12 records mint; the max, 28 (CM4AI rep3), is below v7's worst, which the records put at **31** (VOICE rep3; the registered text's 22 was wrong) | the digest's labels did not displace invented ids: minting rose arm-wide, reported and never gated |
| 9 | **unfavourable** — `full` output within ±10% in 3 of 12; per-project means +16.0% VOICE, +12.4% CHORUS, +33.4% AI_READI, +12.7% CM4AI (whose rep2/3 ran without thinking at −32/−24%; rep1 alone +93.7%) | the larger digest and the receipt cost more output than the ±10% registered; AI_READI is the outlier in every replicate |

Bookkeeping rows arm-wide: British form count 4 (two `Temerty Centre`
title-case skips counted twice) against v7's 139, the normaliser having
rewritten 105; resolver URLs, undeclared prefixes, organisational
fragments, GC label variants, pair errors and duplicate keys 0 on all 12;
receipts 100% of chunks reviewed on all 12, snippets mismatched 5 across
the arm (CHORUS rep2 2, rep3 1, AI_READI rep2 1, CM4AI rep3 1), 6 of 12
reports regated.

### Review pass (12 of 12, 2026-09-07)

**Reviewer basis (#1058).** The v8 reviews were made by `claude-fable-5-1`
and the v7 reviews by `claude-fable-5`; the agent definition pinned
`claude-fable-5` and the reviewers write their own runtime identity, which
**changed between 2026-09-03 and 2026-09-07** — the twelve v7 reviews ran
2026-09-01 to 09-03 and all report Fable 5, the twelve v8 reviews ran
2026-09-07 and all report 5.1. So the v7-versus-v8 review numbers below —
and the ones merged in #1055 — compare a Fable-5-reviewed arm against a
Fable-5.1-reviewed arm, and the difference between them is the package
**plus the reviewer version**. Since #1097 that difference is also machine-
visible: `reviewer` is one of `ARM_PROCEDURE_FIELDS`, so `d4d runs
compare-arms --a <v7> --b <v8>` lists it beside the schema and assembly
digests instead of leaving it to this paragraph.

**The reviewer's identity is self-reported.** The agent is told to write "the
model you are"; nothing verifies it, and the review block records
`model_basis: self-reported by the reviewing agent` to say so. The rubric
records do better — they carry a `model.note` stating the identity comes from
the session environment — and until the review agent does the same, "the v8
reviews were made by `claude-fable-5-1`" and "the reviewer changed its
self-reporting convention" are not distinguishable from the artifacts. This
is CLAUDE.md's observed-versus-asserted rule for reasoning effort, applied to
the judge. A point release of the judge is a smaller
change than a different model family, but it is not nothing, and this
repository's rule is that an instrument change is declared. It is declared
here. The reviewer is recorded per record in `review.reviewer.model`, and
the 17 earlier reviews (the 2026-08-28 arms) are `claude-fable-5`.

How large that effect is has **not** been measured, and the honest place to
say so is next to the numbers rather than in an issue. The instrument for
measuring it exists: `{P}_review_b.yaml` plus `d4d review agree`, which
reports percent agreement and Cohen's kappa against **the same pack the
reviews pin** — enforced on bytes: `review_pack.agree` raises when either
review's `pack_sha256` differs from the pack on disk, which is why #1095's
regenerated pack breaks pairing loudly rather than silently. Nothing consults
git, so "committed" would be the wrong word (#1097).
Six such pairs exist, all from the 2026-08-28 arms and all same-model
retests. Their class agreement is **82.4, 84.8, 87.9, 91.2, 92.4, 95.6**
(exact 80.9 to 89.7) — but the chance-corrected figure is the one to read,
and `kappa_class` on those same six is **0.357, 0.494, 0.502, 0.549, 0.629,
0.654**. Fair to substantial, not good: on the trichotomy the reviewer
agrees with itself about as often as two people asked to sort borderline
cases would. That is the band for ordinary reviewer noise, and it is wide
enough that a modest v7-to-v8 difference in adverse counts is not
separable from it without a paired pass. A second pass under a different
model, compared against that band, would settle whether the version
difference is distinguishable from noise. That is the outstanding
work on #1058; it was set up and deliberately not run.

The agent is now pinned to `claude-opus-5` on the plan owner's instruction
that Opus 5 is the evaluator for all evaluations, which the two rubric agents
already follow. **That gives up judge independence, and the loss should be
stated rather than folded into "a third instrument" (#1097).** Every record
in both arms was *generated* by `claude-opus-5`; they were reviewed by a
different family, so the review was an outside reading. A future review under
`claude-opus-5` is a same-model self-review — a larger instrument change than
the point release this paragraph exists to declare, and one whose direction
of bias is unknown rather than merely unmeasured. Two defensible positions:
keep the pin for consistency with the rubric agents, since the corpus already
scores Opus-5 output with an Opus-5 judge; or return the reviewer to
`claude-fable-5-1`, which continues the v8 instrument and keeps the judge off
the generator's family. The first is what is pinned; the second is the
stronger instrument. It is a decision for the plan owner, recorded here
rather than made silently, and two facts belong with it. First, **after this
change no non-Opus judge remains in the corpus**: the reviews were the only
judgement instrument off the generator's family, since all 24 v7 and all 24
v8 rubric evaluations already record `evaluator_model: claude-opus-5[1m]`.
That is a corpus-level property, and the review's questions — were the rules
followed, is this snippet real support — sit closer to self-assessment than a
rubric score does. Second, measuring the Fable-5-to-5.1 confound with an
*Opus* paired pass is one-sided: inside the 0.357–0.654 kappa band the
point-release effect is bounded a fortiori, but outside it the pass says
nothing about the point release and the confound stays unbounded.

The same directive is now applied to the two non-semantic rubric agents,
which still pinned `claude-fable-5` (#1097). Nothing recorded is affected —
every arm evaluation came from the `-semantic` pair — but leaving them was
undeclared drift against the directive, of exactly the kind #1058 is about.

Nothing recorded was re-reviewed: the 24 review files stand as made, and the
canonical selection below rests on them.

One `d4d-review-record` agent per record (the CHORUS rep1 review run
first as the canary, then eleven in parallel), every check passed
`--write --strict`, review blocks in all 12 provenance records. Same
construction as the v7 table: `slot adv` is the non-affirmative
verdicts (weak, misread, unsupported, inferred, not_in_bundle) on the 50
sampled receipted + receiptless slots, `cannot_tell` listed apart;
`rules` is violated / rules asked — **21** under v8 (rules 1–16 as v7,
plus R1–R4 and the Person-id rule as 17–21), so the like-for-like column
is violations among rules 1–16. The v7 rows below were recounted from
the v7 review files with the same script and reproduce the v7 note's
65/600 and 44/192.

| record | items | slot adv | rules violated (of 21) | among 1–16 | total adverse | cannot_tell |
|---|---|---|---|---|---|---|
| VOICE rep1 | 83/83 | 1/50 (2%) | 1 (19) | 0 | 2 | 0 |
| VOICE rep2 | 83/83 | 1/50 (2%) | 1 (19) | 0 | 8 | 3 |
| VOICE rep3 | 81/81 | 2/50 (4%) | 2 (02, 19) | 1 | 5 | 0 |
| CHORUS rep1 | 78/78 | 5/50 (10%) | 3 (01, 08, 19) | 2 | 8 | 2 |
| CHORUS rep2 | 76/76 | 1/50 (2%) | 2 (07, 19) | 1 | 4 | 0 |
| CHORUS rep3 | 79/79 | 5/50 (10%) | 8 (01, 03, 05, 07, 08, 15, 17, 19) | 6 | 13 | 0 |
| AI_READI rep1 | 82/82 | 2/50 (4%) | 1 (01) | 1 | 3 | 0 |
| AI_READI rep2 | 96/96 | 0/50 (0%) | 1 (03) | 1 | 1 | 0 |
| AI_READI rep3 | 78/78 | 4/50 (8%) | 0 | 0 | 5 | 0 |
| CM4AI rep1 | 88/88 | 5/50 (10%) | 3 (01, 03, 06) | 3 | 8 | 0 |
| CM4AI rep2ᵗ | 81/81 | 10/50 (20%) | 4 (05, 07, 15, 17) | 3 | 14 | 0 |
| CM4AI rep3ᵗ | 97/97 | 2/50 (4%) | 2 (01, 13) | 2 | 4 | 0 |

ᵗ the two runs without thinking on `full` (#1047); rep2 is the arm's
most adverse record on the slot and total columns (CHORUS rep3 leads on
rules). VOICE rep1's and AI_READI rep3's reviews carry a placeholder
`reviewed_at` (#1056).

**v7 → v8, 12 vs 12.** Slot adverse **65/600 (10.8%) → 38/600 (6.3%)**;
rule violations among rules 1–16 **44 (mean 3.7) → 20 (mean 1.7)**, all
21 rules 28 (mean 2.3); total adverse 110 → 75; `unsupported` 6 → 1;
`not_in_bundle` 0 → 0 on both (no fabrication in either arm);
`cannot_tell` 6 → 5. Two counts rose: `changed_meaning` 1 → 8 (VOICE
rep2's six: three are one silent removal of the whole `data_governance`
object, #1054, three are documented removals with Dispositions rows) and `missed_content` 0 → 1 (VOICE rep3: a paper's
affiliations for two creators contradicting the record, uncaveated).
The new rules: rule-19 (R4, per-entry receipts for rosters) is the
arm's most-violated rule, 6 of 12 (VOICE and CHORUS, every replicate); rule-17 (R2, tense and scope) 2 of
12; rules 18, 20 and 21 violated nowhere.

**Predictions 1, 3, 4 and the rule-15 clause of 6, as measured:**

| # | result | reading |
|---|---|---|
| 1 | **unfavourable** — rule-08 violated in 2 of 12 (predicted 0), from 6 of 12 (the v7 six being the Person-as-string charges the v7 note's 2026-09-03 correction voided on validity) | both are CHORUS (rep1, rep3) and the same defect: `maintainers[0]` leaves the declared `name` empty with the person's name in `maintainer_details` prose; the v7 Person-as-string class is gone, as predicted, so the residual is one slot on one bundle |
| 3 | **unfavourable** — rule-06/07 violated in 4 of 12 (predicted ≤ 2), from 7 of 12 | CHORUS rep2/rep3 (rule-07: standards in `distribution_formats`, ethics prose in `regulatory_compliance`), CM4AI rep1 (rule-06: pointers in `review_details`), CM4AI rep2 (rule-07: a URL under `publisher`); E2's audit caught some and not these |
| 4 | **unfavourable, narrowly** — 1 tense/scope misread in the sampled receipted slots (CHORUS rep3 `acquisition_methods[0]`, a plan written as the current pipeline), from 5 on v7 (the hand classification of the prediction's own text, reproducible from the nine v7 misreads) | R2 did not reach 0; the fall from 5 to 1 is the falsification test's answer that R2 was not text alone. The arm's other misread (CM4AI rep2 `publisher`) is a wrong-entity read, not this class |
| 6 (rule-15) | **favourable** — rule-15 violated in 2 of 12 (predicted ≤ 6), from 8 of 12 | CHORUS rep3 and CM4AI rep2 (the c019 boilerplate chunk marked `extracted` with pairs that sit in c018/c020) |

**Falsification tests.** "Rules restated, mechanism absent" asked
whether 1 would hold and 4 not; neither held strictly, and both moved in
the predicted direction by more than sampling noise on the slot column
(the ±2–3pp the cross-read states) — the digest and R2 each did part of
what they were for, and the residuals are project-specific (CHORUS's
maintainer, CHORUS/CM4AI's format-versus-standard slots). The
per-roster receipt ratio (R4's own falsification test) was not computed
here; rule-19's 6 of 12 says the rule is the one most often broken.

**Instrument findings from the reviewers**, each verified and filed:
#1053 (a receipt path whose entry lost its minted `id` at reconcile is
reported `entry_dropped` though it survives at the same index — CHORUS
rep1), #1054 (an unrecorded removal escapes the report gate: CHORUS rep2
`regulatory_restrictions`, AI_READI rep3 `content_warnings`, VOICE rep2
`data_governance` — a snapshot-diff check is the fix). Wrong-chunk
attributions of the #763 class were confirmed by nine reviewers with
support holding in every case. One factual error for a curator
disposition: CM4AI rep3 `creators[1].notes` names "Jillian Parker" as a
preprint author where the preprint gives "Jillian Mohan" (bundle line
2927).

Remaining for the arm: prediction 8 (rubric10/20-semantic evaluations)
and the v8 canonical selection under the review criterion (#660).

### Rubric evaluations, prediction 8 (48 evaluations, 2026-09-08)

**The evaluator changed, and both arms were rescored.** Every rubric
evaluation under `label_aware/` through 2026-09-07 was made by
`claude-fable-5`, pinned in the two agent definitions; generation has
always been Opus 5. (Older evaluations elsewhere in
`data/evaluation_llm/`, the `concatenated/` sets and the 2026-07
archives, were made by Sonnet and Opus 4.8 — the Fable claim is about
the label-aware sets the arm table reads.) On the plan owner's decision the evaluator is now
Opus 5 for all evaluations, so v8 was scored (24) and v7 rescored (24)
under `claude-opus-5[1m]`, one evaluator across all 48. The 24 Fable 5
scores are kept as evidence under
`label_aware/superseded_fable5/`, outside the comparison glob: an
evaluator is an instrument, and a score is comparable only to another
score from the same one. Nothing is retracted. The agents are now pinned
to `claude-opus-5`.

Both arms carry three replicates per project. Prediction 8 asks whether
v8 falls **below the v7 per-project replicate minimum**, and it registers
**three** measures: rubric10, rubric20 and populated leaves. The leaves
measure was dropped from an earlier draft of this section (#1083); it is
restored below, and the three are reported together because the registered
text names all three and admits no partial credit.

| project | rubric10 v7 reps | v8 reps | v7 min | v8 min | verdict |
|---|---|---|---|---|---|
| AI_READI | 98.0, 98.0, 98.0 | 98.0, 98.0, 98.0 | 98.0 | 98.0 | favourable |
| CHORUS | 65.3, 59.2, 63.3 | 72.0, 63.3, 63.3 | 59.2 | 63.3 | favourable |
| CM4AI | 91.5, 91.5, 89.4 | 85.1, 91.5, 87.2 | 89.4 | 85.1 | **unfavourable**ᵍ |
| VOICE | 96.0, 98.0, 94.0 | 94.0, 98.0, 98.0 | 94.0 | 94.0 | favourable |

| project | rubric20 v7 reps | v8 reps | v7 min | v8 min | verdict |
|---|---|---|---|---|---|
| AI_READI | 96.6, 96.0ᶠ, 96.6 | 89.8, 95.5, 90.9 | 96.0 | 89.8 | **unfavourable** |
| CHORUS | 79.5, 69.3, 76.1 | 73.9, 73.9, 75.0 | 69.3 | 73.9 | favourable |
| CM4AI | 86.4, 85.2, 86.4 | 76.1, 79.5, 78.4 | 85.2 | 76.1 | **unfavourable** |
| VOICE | 90.9, 90.9, 94.9ᶠ | 89.8, 86.4, 90.9 | 90.9 | 86.4 | **unfavourable** |

ᵍ CM4AI's rubric10 row was rescored twice on 2026-09-08: under the
corrected Element 4 gate (#1060), which **changed the verdict**, and again
under the software sub-element's role rule (#1081, #1082), which took a
point off each v7 replicate and left the verdict standing on a narrower
gap. Replicates are listed rep1, rep2, rep3 throughout; an earlier draft
listed CM4AI's v8 row in descending order, which read as a different
trajectory (#1083). See below.

ᶠ a half-point score on an integer-anchored rubric (#1062). AI_READI's
96.0 **is** its v7 minimum, so that verdict is quoted off a fractional
score — it does not change the reading (the v8 minimum 89.8 is below
96.6 either way), but the fraction is load-bearing. VOICE's 94.9 is not
its minimum.

### Populated leaves, the third registered measure

Per-project replicate minima, read from the comparison table's
`populated leaves (full record)` rows:

| project | v7 reps | v8 reps | v7 min | v8 min | verdict |
|---|---|---|---|---|---|
| AI_READI | 562, 478, 440 | 525, 525, 449 | 440 | 449 | favourable |
| CHORUS | 199, 168, 210 | 235, 278, 251 | 168 | 235 | favourable |
| CM4AI | 458, 480, 358 | 422, 473, 479 | 358 | 422 | favourable |
| VOICE | 306, 375, 440 | 386, 297, 432 | 306 | 297 | **unfavourable** |

Leaves are 3 of 4, and the project that fails is VOICE — not the one that
fails on rubric10. This measure was registered and then omitted from an
earlier draft of this section (#1083); reporting the rubrics alone made the
result look more consistent across measures than it is.

**Prediction 8: 3 of 4 on rubric10, 1 of 4 on rubric20, 3 of 4 on leaves —
unfavourable on all three.** The registered text — "not below the v7
per-project replicate minimum" — names no measure and admits no partial
credit, so a prediction that fails on one project fails. Read
conjunctively, which is how it is written, **only CHORUS passes all three
measures**: AI_READI fails on rubric20, CM4AI on rubric10 and rubric20,
VOICE on rubric20 and leaves. It was read as holding on rubric10 until the
Element 4 gate was fixed (#1060) and CM4AI moved; the measures now differ
in how much v8 fell and where, not in whether it did.

**The rubric10 half of this is provisional (#1080).** The instrument's own
test-retest movement on an unchanged record is up to 8.7 points, which is
larger than three of the four rubric10 margins the verdicts rest on. The
per-record observations stand; the project-level rubric10 verdicts and the
causal reading below should be treated as indeterminate until the spread is
established by repeats. #1080 calibrates rubric10 only — rubric20 has no
repeatability measurement at all, so its 1 of 4 carries an unknown, not a
small, error bar.

The two rubrics disagree because they ask different questions, and the
reasons the three rubric20 projects fell are consistent across them, in
the reviewers' own words: processing documentation that describes a
pipeline whose outputs the release excludes (CM4AI, all three
replicates), empty derivation slots where lineage is documented in prose
instead, absent variable metadata, and unpinned tool versions. Rubric10
scores none of those as deeply — its Element 8 has one software
sub-element where rubric20 has a whole technical-documentation category
of five questions. So rubric20 registers the thinning across three
projects and rubric10 registers it on one, CM4AI, where it costs 4.3
points; the difference between the instruments is sensitivity, not
direction. Read against #1080's 8.7-point test-retest movement, that 4.3
is inside the instrument's own noise, so the sensitivity claim is a
reading of the reviewers' reasons rather than a result the numbers
establish on their own.
That is the falsification test of prediction 8 answering in the
direction the plan warned of — "a fall means the larger digest displaced
reading" — on the instrument sensitive enough to see it, and it is a
finding for v9 rather than a defect in the arm.

**The Element 4 gate changed a verdict (#1060, 2026-09-08).** When this
section was written, CM4AI's rubric10 row read 84.0/88.0/88.9 against
86.7/91.1/86.7 and was favourable. Those six evaluations disagreed about
whether Element 4 applied to a dataset with no human participants: two
scored it out of 50, four excluded it out of 45. The gate is now stated
per sub-element — oversight and deidentification apply, participant
privacy, consent and compensation do not — and all six rescores land on
one denominator, 47. Under it CM4AI read 93.6/93.6/91.5 against
85.1/91.5/87.2, a v7 minimum of 91.5 against a v8 minimum of 85.1, and
the verdict became **unfavourable**. Prediction 8 on rubric10 is therefore
3 of 4, not 4 of 4. The software rule (#1082) later took a point off each
v7 replicate, leaving 91.5/91.5/89.4 and a v7 minimum of 89.4; the verdict
is unchanged and the gap is 4.3 points rather than 6.4.

The number moved because the instrument was underspecified, not because
the records changed: the same six records scored under three different
readings of one rule produced denominators of 45, 47 and 50. The
superseded scores are kept beside the current ones with a README, and
both rounds of the fix are recorded there — the first edited the
per-sub-element prose and did not hold, because an authoritative
conditions table above it still mapped both conditions to all five.

**The instrument's own variance is larger than most of these gaps
(#1080).** Rescoring eight records under a rule that touched one
sub-element of fifty moved their totals by up to 8.7 points. The clearest
case is a control: CHORUS v8 rep1 scored the sub-element under test
identically both times and still moved 63.3 → 72.0, gaining a point each
on four unrelated elements and losing an exclusion, so its denominator
went 49 → 50 while its two siblings stayed at 49.

That bears on every rubric10 verdict above. AI_READI and VOICE are exact
ties; CHORUS's favourable reading rests on 4.1 points and CM4AI's
unfavourable one on 4.3, both inside the observed spread. The ordering
has been stable across every rescore and the densest record, AI_READI,
reproduced exactly — so this is not a reason to discard the scores. It is
a reason to stop quoting a single evaluation as a project's score, and to
establish the spread before any of these verdicts is cited outward. The
proposal is on #1080.

**Four instrument findings, all filed, none changing a verdict today:**
#1059 (rubric10 Element 8's software sub-element scored 0, 0, 1 on
identical AI_READI evidence — one point, the whole gap between 98% and
100%); #1060 (rubric10 Element 4's applicability gate resolved both ways
on CM4AI, 2 scored and 4 excluded, moving the denominator between 50 and
45; it set CM4AI's v7 rubric10 minimum at 84.0% until the gate was
fixed and the six rescored — see above); #1061 (one v7
rescore read its v8 counterpart to calibrate; re-run independently to an
identical 98.0%, so the anchoring cost nothing, and the agents now
forbid opening any evaluation file); #1062 (the two half-point scores
above). #1059 and #1060 were undecided thresholds in the rubric text, not
evaluator error: both readings were defensible on what the rubric
said, which is the defect. #1060 is now fixed and its verdict change is
above. **#1059 took four rounds and an external review to fix, and
changed no verdict** (2026-09-08).

The first three rounds each stated a threshold and each was wrong in a way
the next round found: naming the qualifying slots let a GitHub organisation
root earn the point; barring publisher pointers would have flipped three
CHORUS records; writing the applicability rule as a new paragraph left two
older gate texts standing that said the opposite, and several rescores
recorded `match: false` and applied the launcher's quoted rule instead of
the checked-in one. A Codex review of the pull request then found the
deeper problem: the sub-element's only declared field, `software_and_tools`,
**is not a slot in the D4D schema** and appears in no record, so the rule
could never be satisfied as written and every evaluator had been
improvising a substitute (#1081). A rubric20 test has been asserting that
same name does not resolve for as long as rubric10 has been declaring it.
The review also showed the threshold was not total: packaging, metadata
production and quality-assessment software fell outside its three failure
cases, leaving 8 of the 24 records undecidable and producing opposite
scores on identical packaging evidence (#1082).

The rule now asks one question — can a reader tell what software produced
or transformed the data being distributed — and names five roles that do
not answer it: capture and instrumentation, hosting and serving, packaging
and metadata production, validation and quality assessment, and a pipeline
the record itself says produced outputs the release excludes. All 24
production replicates were re-adjudicated on this one sub-element, from the
records alone, with the rule quoted verbatim to the adjudicator rather than
read from the agent definition (#1077).

**Every project is now uniform across its six replicates**: AI_READI 0,
CM4AI 0, CHORUS 1, VOICE 1. Three v7 CM4AI evaluations moved 1 → 0 and
were archived under `superseded_software_role/`; the other 21 were
unchanged, and all 24 adjudications are recorded in
`readjudication_software_role.json` whether they moved or not. CM4AI's v7
minimum falls 91.5 → 89.4 and its verdict stays unfavourable; no other
project's numbers move. The issue's second example was wrong for a
different reason than the earlier draft gave: CM4AI's replicates do not
differ on this sub-element at all.

### Canonical selection (2026-09-08)

Executed under the review criterion (#660) — validity, then fewest review
adverse verdicts (a difference of at most 2 a tie), then most slots, then
lowest label — with each project's own label prefix as the config:

| project | canonical | slots | review adverse | next-lowest adverse |
|---|---|---|---|---|
| VOICE | `2026-09-04f…v8_rep1` | 80 | 2 | rep3 (5) |
| CHORUS | `2026-09-04f…v8_rep2` | 55 | 4 | rep1 (8) |
| AI_READI | `2026-09-04g…v8_rep2` | 80 | 1 | rep1 (3, a tie on adverse) |
| CM4AI | `2026-09-04g…v8_rep3` | 59 | 4 | rep1 (8) |

The last column is the second-lowest-adverse *replicate*, not the tool's
`margin_over_runner_up`, which is null wherever only one replicate
survived the adverse filter — three of the four.

The adverse count decided every project, with two replicates out of
contention on it in three of the four; only AI_READI came down to slots
as well, and there by a single slot on ~80 — "no reason to prefer
another", not "clearly best". The marks are **runtime-scoped** (#690):
each supersedes the prior *api* canonical (the v7 production records)
and leaves the v6 agentic canonicals standing. Nothing is moved or
deleted; each superseded record keeps its old block under
`canonical_history` with a `superseded_by` stamp naming its replacement.

Note what the criterion does **not** use: the rubric scores. On rubric10
the criterion picks a project's top-scoring replicate in none of the
four: the chosen VOICE record is its project's lowest (94.0 against 98.0
twice), CM4AI's is its lowest (85.1 against 91.5 and 87.2, under the
corrected Element 4 gate — it was tied-lowest at 86.7 before it), AI_READI's scores 98.0 against
rep3's 100.0, and CHORUS is a three-way tie at 63.3. The review's
adverse count and the rubrics disagree about which replicate is best,
which is the honest state of two instruments that measure different
things — the criterion was registered before these scores existed and is
not re-opened on them. **Those scores land in a separate change** (the
prediction-8 section above and
`data/evaluation_llm/rubric10_semantic/label_aware/`); this selection
neither reads nor depends on them.

### After the arm: the first v9 boundary change (#932)

The v8 arm is complete and retained, so the condition is closed and the
next generation-path change belongs to v9. The first one landed
2026-09-08: **the manifest's scope declaration is now rendered to the
model** (`api_runner.scope_block`), beside the source ranking (#603) and
the declared naming (#668), under the same manifest-not-used exemption.

Why it is the first: v8's R2 already tells the model that a passage whose
subject is another dataset belongs in `related_datasets` and never in the
referent's own slots, and the uniform rules already say `Dataset` admits
one referent. Both refer to a distinction the model was never given — the
`scope:` block was read only by `scope.py` and `d4d download scope
--check`. So the rule could be broken by a model with no way to know
which dataset in its bundle was which, and only the checker could see it.
That is the #913 class — a related-but-distinct dataset's material
absorbed into the referent's own slots. Its evidenced instance is VOICE
on the v7 arm (rep2 carried a pediatric-protocol clause into an adult
slot), and `d4d download scope --check` reports 32 records placing the
pediatric release inside VOICE's own `resources`, `access_urls` and
`download_url`.

**What it does not fix, stated so a v9 canary is not read wrongly.** The
v8 review pass's CM4AI rep2 rule-17 finding — earlier releases' dates in
`distribution_dates`, a June 2025 erratum under this referent — is *not*
of this class. CM4AI declares `related_but_distinct: []` and its referent
note says the four Dataverse releases **are** this dataset, so the block
gives the model no basis for excluding their dates and arguably licenses
what rep2 did. Release-versus-referent scope is the other half of R2 and
a separate question; scoring a CM4AI canary on rule-17 as evidence for
this block would be measuring the wrong thing.

The block carries facts, not behaviour: the referent and its identifier,
the referent note (which is where the earlier-release half of R2 lives
for AI_READI and CM4AI), and for each declared related-but-distinct
dataset its name, every identifier it answers to, why it is distinct, the
slot its facts belong in, and the bundle source that legitimately carries
its documentation. It ends by saying it names the datasets and does not
say what any passage means, so the rules remain the only text governing
the decision.

**The two rules that pair with it landed the same day** as
`generic_v9` (#913, #911): R6, that a value in one of the referent's own
slots is supported by a passage whose subject is the referent — binding
the reconcile phase, which is where the v7 arm's leaks survived, since
reconciling the two records against each other does not test what a value
is about; and R7, that a list entry names exactly one entity, with the
signature of a merged one. R6 is the obligation this block's declaration
exists to make checkable by the model rather than only by `d4d download
scope --check`.

**#932 re-baselines the condition.** `ASSEMBLY_LAYOUT` names the new block,
so `assembly_digest` moves and a record made under it is distinguishable
from the v8 arm's — which is the point of that digest (#353). No run
carrying a v8 label may be made under this runner: the twelve retained
records were generated without the block, and a thirteenth with it would
be a different condition wearing the same name. The prompt files are
unchanged, so no pin rotates (`d4d api prompts check --strict` passes).

### report_claims instrument v3 (#1022, #1046, #1087, 2026-09-08)

A schema claim that names its own inventory is now resolved against that
inventory only. The v8 report instruction (step E) asks for exactly the
sentence this broke on — "`splits` and `participant_privacy` are not
declared by the core schema and appear only in the full record" — and the
checker resolved the slot against every class, so a true sentence read as
a `false_schema_claim`.

**Two regates were fed false schema claims**, and one of them was driven
entirely by them: VOICE `2026-09-04f_rep1`, whose two findings before the
regate were both false, and CM4AI `2026-09-04g_rep3`, where two of four
were. Those two reports were regenerated over contradictions the model had
not made.

Counted on the **model-written report** (`intermediate/{P}_report.md`), the
false findings across the two production arms were **19 before and 0
after**: VOICE 04f rep1 alone carried 12, with the rest on VOICE 04f rep3,
VOICE v7 rep3, AI_READI 04g rep1, CM4AI 04g rep2 and CM4AI 04g rep3.
Counted on the **artifact the block records** (`{P}_reconciliation.md`, the
path in `report_claims.artifacts.report`), the same arms go **3 before and 0
after** — VOICE 04f rep2 twice and 04f rep3 once. The two artifacts are
different documents and the numbers are not interchangeable; the recorded
blocks moved by the second figure.

Corpus-wide, recomputed uniformly over the same artifacts, the count goes
**38 under v2 to 25 under v3**. The blocks as they stood before this showed
47, but that figure spans instrument versions — some blocks were written by
the runner, others by earlier backfills — which is why the comparable pair
is the two recomputes rather than the recorded total.

Of the 25 that remain, **23 are true and 2 are false positives of a
different, pre-existing defect** (#1089). The 23 are mostly the
`distributions` claims that #546 exists for — 20 of them — spread over the
2026-07-28, 2026-07-31, v3, v4 and v5 arms rather than v4 and v5 alone, plus
one each on `conforms_to`, `md5` and `path`, all false against the class the
claim names. The 2 are from one v5 VOICE reconciliation whose section 3.4
reports that *the record* asserted the core schema lacked a slot and says
the digest does not support it: the report is rejecting a claim, and the
checker reads the quoted claim as one the report makes. Filed rather than
fixed here, because a rule that suppresses findings on a sentence's stance
needs its own evidence base and two instances is not one — #1087 is what
that failure looks like when it goes wrong.

The scope is read from the **clause** carrying the "not declared" phrase,
splitting on `[;,]` — not from the sentence, and only from the words "core"
and "full" qualifying a schema, record, class, inventory, digest, projection
or view. Both bounds were put there by a defect the first version had, and
the second is the sharper lesson (#1087). Read over the whole sentence, a
v5 VOICE report's trailing clause — "and stated content in five slots that
**the full record** did not state" — scoped a `distributions` claim in the
first clause to `Dataset`, where `distributions` is not declared, and
silenced it. `full` resolves to `Dataset` alone, so every subject of #546 —
`distributions`, `path`, `md5`, `format`, `media_type` — was one line of
boilerplate away from being unreportable, and the whole-sentence reading was
wrong on 100% of the corpus sentences it fired on (55 core, 1 full, 32
unscoped; the one `full` was that sentence). A qualifier qualifies what it
is adjacent to.

Two further non-signals, each with a test: a bare class name is not a scope
— "no such slot appears in the inventory for `Dataset`, and `md5` and `path`
are not attested keys on any listed range class" names a class in its first
half and ranges over all of them in its second — and a clause saying "any
class" is unscoped whatever it names.

The block was recomputed for every record the backfill covers — 282, of
which 277 have a reconciliation report and so carry a checked block — under
one instrument, so no comparison spans v2 and v3. Recomputing exposed a second defect (#1085):
`backfill-checks --blocks report_claims` replaced the block's `artifacts`
with the report alone, dropping the full and core record md5s and never
writing the schema digests the runner records, so a recomputed verdict could
not be told apart from one reached against records or a schema that had
since moved. Fixed first; the recompute was redone under the fix. The
datasheets are untouched, and the two regenerated reports stand as written
with the cause on record here.

### v9 R8–R14, added before the first v9 run (#803, #901, #830; 2026-09-09)

Seven rules joined the v9 block while no v9 record existed, so the
condition has one boundary, not two, and the pin rotated with the reason
naming them (twice: once for R8–R14, once for the review's corrections,
#1109). Nothing here changes the runner: the assembly digest hashes the
layout and the phase instructions and does not move on a prompt edit; the
prompt-file hash and `resolved_prompt_digest` do.

- **R8** closes the prompt half of #803 and point 1 of #901. The v6
  fragment rule ("mint only where a value points at the part") was read
  against `File`, `FileCollection`, `DataSubset`, `Person` and `Software`
  ids that the schema forces (`identifier` or `required` — the v9 prompt
  test enumerates every forced-id class reachable from `Dataset` against
  `SchemaView` and holds R8 to naming each; `Software` is reachable from
  every object through `used_software` and was the hole the review found)
  and against the ids `derive_core` consumes — collection and file ids
  copied into the core's distributions, top-level `resources` matched by
  id; the pack-side half (#821 `forced`, #1108 `origin`) let the reviewer
  excuse those, and R8 tells the model the same. Five of the six v6
  rule-14 charges were of this kind; of CHORUS rep2's 68 fragments, the 57
  on splits, purposes and limitations (none forced) were a correct charge
  R8 leaves standing and the 11 on `used_software` are the Software case
  it excuses. A nested `Dataset` (under `resources`, `parent_datasets`) is
  forced too, and R8 names it. R8 prefers the record's own id as the base:
  a label on the dataset's landing page is licensed by the v5 rule and
  #1108's reading, but `receipts._minted` exempts only own-id fragments
  and urns from needing a receipt, so a landing-page label costs receipt
  coverage a own-id label does not — stated in the rule, and filed for the
  receipt instrument to consider at its next revision. Its second
  half is the referent test for every other mint: an organisation, grant,
  award or program has a referent outside the record, so a fragment for it
  on the dataset's DOI is a claim about that DOI (CM4AI rep3's twelve and
  VOICE rep3's twenty-two on the 2026-09-01 arm), and a fragment on another
  thing's identifier labels that thing (AI_READI rep1's ten
  `file_collections[*].id` on the fairhub page). `Organization`, `Grant` and
  `Creator` ids are neither identifier nor required, so "leave `id` empty
  and carry the name" validates; R8 says a creator or maintainer entry is a
  role whose id is the person's or organisation's own, which is where 9 of
  CM4AI rep3's 12 unforced mints sat (`creators[*].id`). R8 defers to the
  ORCID-first person rule and states that it refines the v5 minting base
  ("an identifier the evidence supplies" → one the evidence supplies *for
  this dataset*) rather than replacing it.
- **R9–R14** are #830's candidates, each present in three or more
  independent reviews: enumeration slots inferred from names (`data_type`,
  `collection_type`: six verdicts on those two leaves — with the review's
  two exemptions: a required enum such as `relationship_type`, where the
  entry itself is what the evidence must support, and the file enums
  `format`, `media_type`, `encoding`, `compression`, which the schema reads
  from the file's name); `raw_data_format`
  naming the released standard (five, recurring on the production pass);
  `principal_investigator` inflation (seven adjudicated items, with the
  VOICE bundle's own "co-principal investigators" versus "lead
  investigators" as the anchor — R11 asks for the source's designation
  rather than quoting it); `scope_impact` composed beyond the stated fact
  and the keyword-line substitution the adjudication ruled closer to
  fabrication (R12 carves out `keywords` itself — 30 of 30 recent records
  fill it from keyword lines, 90 receipt entries — as the one slot whose
  subject is that a term appears); a pointer entry sitting in `variables`; absence statements
  and access routes under `errata`, `future_guarantees`, `format`,
  `prohibition_reason` (seven records on the production pass).
- **Not added**: plan-as-done (the v8 tense rule already says it) and
  entity merging (R7). Person-as-string was struck from #830 as reconcile's
  own flattening (#900, #805), not model behaviour.

**What a v9 canary can measure.** R8's first half predicts fewer rule-14
verdicts on `forced: true` mints and no change in the mints themselves;
its second half predicts fewer `origin: minted, forced: false` entries on
`creators[*].id` (9 of CM4AI rep3's 12), `affiliations` (17 of VOICE
rep3's 22), `funders[*].grants` and `accountable_organization`, and no
`origin: constructed` entries on another entity's identifier (one on the
dataset's own landing page is R8's licensed form, as #1108 reads it). R9–R14 predict fewer adverse verdicts on the
named slots; each has a small base (three to seven verdicts across
seventeen to twenty-nine reviews), so a null on twelve records says little,
as #1072 said of R7. The prompt-side lifted-string guard (`test_the_rules_
name_no_value_from_a_record_they_will_be_scored_against`) keeps the
verdict strings the rules were drafted from out of the text.
### The report phase sees the core inventory (#998, 2026-09-09)

The report instruction's `both` rule referred to "the core schema" while
the phase was assembled with the `Dataset` digest; the model's only view
of the core inventory was the carried core record, where a slot the
derivation left empty and one the core class cannot declare look the
same. The phase now carries `CoreDataset`'s top-level slot names before
its instruction (`core_inventory_block`, names only, ~1.3 KB). Runner-side,
so `ASSEMBLY_LAYOUT` names it and the assembly digest moves; no v9 record
exists, so the condition still has one boundary. On the v8 fill
`claims_core_cannot_hold` was 0 on seventeen of eighteen records and 5 on
one — and every report finding on the v8 fill is of that class: five
`retention_not_shown` on `both` rows over full-only slots (`citation`,
`consent_revocations`, `collection_consents[0].consent_details`,
`participant_compensation[0].compensation_amount`,
`third_party_sharing[0].is_shared`), on that one record, and no `both` row
on a core-declared slot has ever failed presence. So the prediction for
the canary is narrow: that count at 0 with no `both` row on an undeclared
slot, and no change anywhere else — read with one caveat the review
named: the gate resolves a `full` row against the full record only, so a
row wrongly flipped from `both` to `full` produces no finding; the block
therefore says the test is on the *root* of the slot path and applies to
retained/changed/added rows, and a canary reader should compare the rate
of `both` rows with the v8 fill's rather than trust the zero alone — read
off `report_claims.rows_by_record` (instrument v4, #1122). The fill as
defined above (12 records) reads 419 `both` of 461 (90.9%); all 18
v8-labelled API records, the fill plus the six canaries, read 617 of 682
(90.5%), with the five rows on slots the core cannot hold all on the VOICE
2026-09-04d canary and none in the fill. (The "612 of 682" this paragraph
first gave was the 18-record count less those five, computed by hand from
the reports, and called the fill; it was neither.) The recorded tally is
the post-regate reading: the tally moved on nine of the ten v8 records
with a pre-regate snapshot (only 04b rep1 CM4AI is unchanged); on five
the `both` count fell while `full` rose, three of them with the row
total unchanged — the unambiguous flip of `both` to `full` (04e rep1
VOICE ×1, 04f rep1 CHORUS ×2, 04g rep3 CM4AI ×2); 04f rep3 VOICE gained
four `full` and lost three `both` while a row was added. So `report_gate` now carries
the tally before and after, and the comparison is post-regate against
post-regate. The v8 labels already carry three assembly digests (2026-09-04
rep1; b/c/d; e/f/g), so "one boundary" is a statement about v9, not a
claim that v8 was one arm; and the block is unconditional, as step E was,
so a re-run of an earlier condition would receive it too.

### The agentic playbook carries R6–R14 (#1119, 2026-09-09)

`.claude/commands/d4d-uniform-rules.md` — the one copy of the decision
rules the agentic runtime reads (#563) — stopped at v8 R5, so an agentic
run under the v9 condition would have received none of R6–R14 (#1119,
from the #1109 review). The nine are mirrored in the playbook's own
style, `test_playbook_reach` points at the v9 prompt with a row per rule,
and the playbook hash every agentic record carries moves with it: an
agentic boundary at the same point as the API one, with no agentic v9
record on either side of it.

The nine are the prompt's text with the playbook's tags — clause for
clause, held by a per-clause probe table, after the first mirror kept
each rule's statement and dropped its procedure (#1131). The same change
edits `d4d-full-core.md`'s stale condition list, a second hashed
playbook: 47 records pinned its previous hash and read as drifted (12
agentic v6 records among them, the re-marked v6 canonicals included);
the edited line is a conditions catalogue, not a decision rule, so no
rule those records ran under moved — reported, never fatal, and named
here so the drift is attributable.

### The v9 body writes American English (#1134, 2026-09-09)

The fourth v9 pin in two days, and the first that changes no rule. Under
the declared instrument the whole file carried twelve British forms: the
body eight "organisation" (inherited from v8's v5 block, and one in R7),
one "recognise" (v5 block) and one "neighbouring" (v2 block), and the
rationale two more, one of them the plural — while the body's own v5 rule
says "Write American English throughout" and the runner rewrites British
forms out of every record (#1002). All twelve are American now. v8 and earlier keep theirs:
their records were generated under those bytes. No v9 record existed, so
nothing is re-baselined; the assembly digest does not move (the prompt
file is covered by its pin, not the assembly); `condition_delta` stays
`["base"]`. The guard is the declared instrument, `grounding.BRITISH_PATTERNS`
(v3), swept over the whole file — the first version was a hand-written
list that passed on "neighbouring" (#1143). The audit-phase instruction the
runner sends says "neighbouring" too and is filed as #1138, because
`PHASE_INSTRUCTIONS` is in the assembly digest and moving it is a
condition-boundary change.

### The schema modules are a scanned surface of the real-identifier guard (#1146, 2026-09-09)

The #647 guard scanned the prompts, the two playbooks and the rendered
digests; the two docExamples the #1126 review found by hand (a registered
trial number, a DOI that does not exist) sat in schema modules it never
read. The modules are a surface now — the docExamples reach the agentic
runtime through the merged schema file and the descriptions reach every
API request through the digest — and two shapes were made form-aware so
the surface is scannable without an allowlist: a ROR id is `0` + six
Crockford base32 characters + two check digits (`01an7q238`; the
placeholder `0xxxxxxxx` is not one, where the first shape matched any nine
lowercase alphanumerics), and an ORCID-shaped token counts only when its
ISO 7064 MOD 11-2 check digit holds — the property #1126 used to make the
schema's four ORCID-shaped tokens form-only (three docExamples and the
`orcid` slot's description) is the property the scanner now reads; the
prompt body keeps the un-narrowed reading, since an identifier-shaped
token there is a copy-through candidate whether or not it is anyone's.
The surface's first pass reported green; the review of that pass found
one real identifier the shape could not read — the `publisher` docExample
`ror:04t3en479`, Karlsruhe Institute of Technology's ROR, written with a
lower-case prefix the CURIE shape matched in upper case only (#1178) —
the #647 defect verbatim, in the merged schema file the agentic playbook
reads, reported as a pass. The shape reads either case now, the
docExample is `ROR:0xxxxxxxx`, and the derived artifacts are regenerated.
The guard is green on all 22 modules; the generated merged files and the
datamodel are derived from them and are not scanned twice.

### The schema digest moved with #1114 (2026-09-09)

The `doi` slot's description carried a real Nature DOI as its example,
and the schema digest — sent ahead of the arm prompt on every request —
renders slot descriptions, so a real identifier sat in model-facing text
on every run (#1114, found by the #647 guard once it scanned the digest).
The example is now a form (the docExample
`10.xxxxx/example.1234`; the description states the shape without an
instance). `schema_digest`'s
`Dataset` fingerprint moved from `ffe03dd469feb388e0a4149e4f5ccb6f` to
`a91bad8b8eaf7c34b147ff5970474342` (CoreDataset `386a470d…` → `dfb9f93c…`) and
`schema.core_sha256` with it (the inventory ledger gained the new digest; no
slot was added or removed). The operative sentence of the `doi`
description — the bare DOI only — stays inside the digest's 300-character
window; the first draft pushed it out, which would have been a rule
removal presented as an identifier removal (#1126 review). The docExample
annotations and `latest_version_doi`'s description lost their real and
corpus identifiers too: they reach the agentic runtime through the merged
schema file, not the digest.
No v9 record exists, so the condition still has one boundary; a v9 run
differs from the v8 fill by the scope block, R6–R14, the report-phase
inventory (#998) and this digest together, and no comparison against the
fill can attribute a difference to any one of them. The organization
docExample pair is form-only (`https://ror.org/0xxxxxxxx`, "Example
University", #1115), because docExample is model-facing on the agentic
path. The review of round 2 found two more real-identifier docExamples
(a registered trial in `D4D_Human.yaml`, a DOI that does not exist in
`D4D_Uses.yaml`) and the review of round 3 an ORCID placeholder whose
ISO 7064 check digit was valid (`0000-0001-2345-6789`, assignable to a
person); all three are form-only now — the ORCID ends in a digit its
checksum forbids — and none moved the digest.

### The audit-phase instruction writes American English (#1138, 2026-09-09)

The audit phase's instruction — sent on every API run, under every
condition — said "a value answering a neighbouring field" while the
same runner rewrites that word out of every record it writes (#1002, v8
step J). It says "neighboring" now. `PHASE_INSTRUCTIONS` is hashed into
the assembly digest, so the digest moves for every condition from here:
`a0c34202…` → `a78228e9…`, one re-baseline registered here as #352's,
E2's (#928), G's (#952), E's (#929), #932's and #998's were. No v9 record
exists, so v9 still has one boundary; the v8 fill's records carry the
digests they ran under and are compared among themselves as before. The
prompt pins do not move. The instruction's spelling had propagated into
model output — "neighbouring" in 17 audit JSONs and 24 reconciliation
reports — and stopped short of the records, so the form block and the
canary's British row do not move. A test sweeps every piece of prose the
runner writes into a request (`api_runner.sent_text_surfaces`: the phase
instructions and layout the digest hashes, and the system prompt, repair
prompts, core inventory block and headers it does not) with the declared
instrument as the instrument applies it — lower-cased, no quotation
exemption — so the runner's sent text is guarded with the same wrapper
as the v9 prompt file (#1134), which exempts quotations because a prompt
quotes sources; the manifest-derived blocks (scope, naming, source
ranking) are left out on purpose, their content being a source's.

### What a v9 arm can and cannot be compared against (#1072)

`condition_delta("generic_v8", "generic_v9")` returns `["base"]`, and that
is **not** a statement that a v9 arm differs from the retained v8 records by
the prompt's rules alone. `CONDITION_AXES` tracks which generic base a condition
is built on and whether it is tuned; neither axis can see a runner-side
assembly change. Since #1073 the function takes each side's records — or
`runs.arm_assembly_digests(label_prefix)` — and adds an `assembly` axis read
from `prompts.assembly.sha256`, so once a v9 arm exists this delta will
report `["base", "assembly"]` from evidence rather than needing this
paragraph. It stays prompt-only when given nothing, because the assembly of
a run that has not happened yet is not knowable from a condition name; when
records **are** passed and cannot be read, the axis comes back as
`assembly unmeasured` rather than silently vanishing (#1092). The declared-scope block (#932) landed on 2026-09-08, after all
twelve v8 records were generated on 2026-09-04, so a v9 run differs from
them by **the scope block, R6 and R7 together**.

Three consequences, stated before any v9 canary rather than after:

- **R6 is not measurable against the v8 arm.** Its premise is a declaration
  those records never received. A v9-versus-v8 delta on the #913 class
  measures #932 and R6 as one package, which is a fair thing to measure and
  a different thing from what the prompt block does.
- **R7 is the one rule a v8 comparison can isolate**, since it depends on
  nothing the runner changed. Its evidence base is thin — three instances
  across two v7 records — so a null result on twelve records says little in
  either direction.
- **A clean v8 baseline under the current runner cannot be made**, because
  no run carrying a v8 label may be made under it (above). Producing one
  would mean a new label for a v8-prompt-plus-scope-block configuration, a
  thirteenth-through-twenty-fourth record and its own canary. Whether that
  is worth the spend is a decision for the plan owner; it is not assumed
  here.

The axes model's blindness to runner-side changes was filed as #1073 and is
now fixed: the assembly digest already recorded them, and the join is the
optional records argument described above. Applied to the arms that already
exist it says something the condition names never did — v7 and v8 production
also differ on assembly (`d2f01480…` against `f7006dc1…`), so
`comparable_conditions("generic_v7", "generic_v8")` is true by name and
false on the evidence.

## Sequencing (PRs, in order)

The first PR (#916) landed A and the #912 pack half ahead of this
order; that is safe because A is decision-independent as merged — the
reference marking adapts to whatever D1 chooses — and no v8 canary
exists for the production rule to protect. The order the remaining
steps need:

1. **F** — bundle fixes (#886, #875), rebuilt bundles and manifests,
   `audit-bundles --strict` clean. Moves `bundle_md5` for every project
   touched; existing records drift (reported, not fatal, #452).
2. **C (D1)** — done: #805 applied (`inlined: true` and the
   descriptions), `make gen-project` + `gen-core-schema`, schema tests;
   the digest moved to `ffe03dd4`.
3. **A** (done in #916) re-measured after C: 72 nested classes, 43,582
   chars, no reference marker (the marking follows LinkML's rule since
   the #927 review).
4. **D** — `d4d_generic_arm_prompt_v8.md` = v7 + `ADDED IN v8`, the
   version-diff test, `CONDITION_PROMPTS`/`CONDITION_AXES`/
   `RECEIPT_CONDITIONS` gain `generic_v8`, commit, then pin
   (`d4d api prompts pin --reason`). Playbook parity (#648's guard,
   `tests/test_playbook_reach.py`) — the agentic playbook must carry
   the same four rules even if no agentic v8 arm runs, or the parity
   test says which rules reach only one runtime.
5. **E2** landed with D (PR #928); **E** (the report gate) is #929 and
   lands before the canaries or after the arm, never between. D's R1
   example (a Person object under `principal_investigator`) is true only
   once C (PR #927) has merged — #928 asserts that order in a test.
6. Register the production matrix here (as v7's plan did), then the
   four canaries, then the fill.

7. **G (#952)** — after the CM4AI canary (`2026-09-04_claude-opus-5-api-generic-v8_rep1`,
   PR #951) stopped on one `slot_not_in_record` receipt entry, decided a v8
   defect: the API runner asks the model once, inside the `full` phase, to
   re-address receipt entries whose slot is not a path in the record it just
   wrote (`full_readdress`; the receipt as written is snapshotted, the usage
   entry records before/after). The instruction joins `PHASE_INSTRUCTIONS`,
   so the **assembly digest moves** for every condition from here — one
   re-baseline, registered here as #352's was; the prompt pin does not move.
   The CM4AI canary is re-run under a new label; the 2026-09-04 rep1 stays on
   disk as the defect's evidence and is excluded from the v8 comparison like
   the Aug-28 exploratory records.

8. **E (#929)** — landed before the re-canary, in the same re-baseline
   window as G: the report phase ends with a dispositions table the
   checker reads (#684's two-form limit lifted for the form v8 writes), the
   runner checks it in-process and regenerates once with the contradictions
   named (`report_regate`), and the gate reads a report with no finding and
   no readable claim as unmeasured — blind for a run that was asked for the
   table, tolerated on earlier records so their arm still satisfies its own
   gate. **Instrument revision, registered here**: `report_claims`
   now also checks `retained`/`changed`/`added` rows (`retention_not_shown`,
   `change_not_shown`); the 2026-09-01 v7 arm writes no such table, so
   recomputing its blocks changes nothing there (`claims_checked` stays 0 on
   11 of 12) and the v7 baseline for `report findings` is a floor of 0 with
   its basis on the row for CHORUS, CM4AI and VOICE, and a measured 0 for
   AI_READI (rep3 read 4 claims). **Fifteen older records** (v2–v5 API and crate
   arms) do carry disposition-column tables and would recompute differently
   under this instrument (e.g. 2026-08-13 v4 rep1 CM4AI 6/3 → 16/12); no
   backfill is scheduled, and `baseline_for` reads recorded blocks, so
   nothing moves until one is run and registered. The v7-vs-v8 report metric is therefore one-sided: measured
   on v8, unmeasured on v7 — say so wherever it is tabled. `companions` is
   hashed after the last phase (#652).

9. **H (#974)** — after the CM4AI re-canary (`2026-09-04b_…_rep1`, PR #975)
   passed every receipt metric and the report gate but wrote the dataset's
   own DOI as a resolver URL under `id` (16 resolver URLs vs 0 on every
   12-record fill since v5 — five arms, 60 records; the v5 2026-08-19 and
   v7 2026-08-28b exploratory canaries were not 0): a write-time normaliser rewrites a resolver URL in a
   `uriorcurie` slot to the CURIE it names (`normalise_identifier_form`, in
   the same chain as the enum, temporal and multivalued normalisers). A
   runner change with no prompt or digest movement; registered here as a
   generation-path change that lands before the third CM4AI canary
   (`2026-09-04c`), never between a canary and its fill. The 2026-09-04b
   record stays as evidence, excluded from the v8 comparison by prefix.

10. **I (#981, #982)** — after the third CM4AI canary (`2026-09-04c_…_rep1`)
    passed every receipt metric, resolver URLs and the report gate and
    stopped on six `mailto:` person ids: (a) a write-time normaliser mints a
    fragment on the record's id for a `mailto:` identifier and keeps the
    address in `email` (`normalise_mailto_ids`, logged under
    `normalisation.mailto_ids`); (b) the undeclared-prefix counter is
    instrument v3 — `mailto:` excluded on a Person's id (the normaliser's
    case) and counted anywhere else, as its v2 docstring judged; the two
    affected form blocks (v6 agentic CM4AI rep1: 2 → 0; 2026-09-04c: 6 → 0)
    are recomputed and the 2026-09-04c canary re-verdicted offline under v3
    — which settles the instrument question only. (a) and the R5 clause that
    goes with it (the v8 prompt's identity rule now says what the D1 slot
    descriptions already said: a Person's id is an ORCID or a fragment on the
    record's id, never `mailto:`; pin rotated) are generation-path changes,
    and the production rule invalidates every earlier record of the
    condition: **CM4AI runs a fourth time under the final package before the
    fill** (#984). VOICE runs next; the canary order becomes VOICE,
    AI_READI, CHORUS, CM4AI. (b) is an instrument revision registered here
    with both sides recomputed.
11. **`both` rows on slots the core cannot hold (#990/#992, 2026-09-04).**
    The VOICE canary's five remaining report findings were `retained |
    both` rows on slots CoreDataset does not declare. The first reading
    (PR #991 as opened) read such a row against the full record alone;
    both reviews found that the instruction defines `both` as present
    in both, so the instrument would have accepted a false claim about
    the core that the CM4AI 2026-09-04c regate had correctly rewritten.
    Adopted: the strict reading stays; the finding names the cause and
    the report instruction says up front that a slot the core schema
    does not declare is `full`. The checker carries `instrument: v2`
    from here (#996); no recorded block moves. The instruction text is a
    generation-path change, so the VOICE canary is not retained and
    runs again under the final package; the order becomes VOICE
    (again), AI_READI, CHORUS, CM4AI.
12. **British spellings get a mechanism (#1002, 2026-09-04, step J).**
    The VOICE canary counted 8 (`programme` ×4 in the full record's
    prose, again in the core) against a v7 worst of 2, under a prompt
    that has asked for American English since v5 on this path. Adopted: a write-time
    normaliser, one rewrite rule per pattern of the form instrument
    (v3, 38 patterns), the instrument's own double-quoted exemption plus
    identifier-shaped tokens, keys and the header untouched, every
    rewrite logged under `normalisation.british_spellings`. The form
    block's British count is unchanged as an instrument and becomes,
    like the resolver-URL row after #974, an invariant for the forms the
    normaliser does not cover; the model's own count is read from the
    normalisation block. Retain-with-basis was the alternative (one
    word, four occurrences); rejected because the metric would then
    depend on variance the v6/v7 arms only happened to sit under.
    Generation-path change; folded into the VOICE re-run item 11 already
    requires.
13. **Incomplete streams are retried (#1013, 2026-09-05).** The VOICE
    re-run's full phase lost its connection mid-receipt; the SDK hands
    back the partial snapshot without raising on a clean close, and
    the runner accepted a body that parsed. `_call_with_retry` now
    raises `IncompleteStreamError` when an iterable stream ends without
    a `message_stop` event, or when the final message carries no
    `stop_reason` (a proxy that framed the close itself), and retries it
    like a dropped connection at most twice per call (#1016), printing
    each attempt. Runner robustness, not a generation-path change: a
    complete stream's output is untouched, so no earlier canary is
    invalidated by it; the 04e run itself is not a measurement of the
    package and VOICE runs again.
    VOICE passed as `2026-09-04f` on 2026-09-05 and is retained.
    AI_READI passed the gate as `2026-09-04f` on 2026-09-06 but is not
    retained: a duplicate top-level key no instrument saw (#1029).
    CHORUS passed as `2026-09-04f` and AI_READI as `2026-09-04g` on
    2026-09-07, both retained; the AI_READI run is the first live
    capture of a transport error mid-stream by the #1037 recorder.
    CM4AI passed as `2026-09-04g` the same day, retained: all four
    canaries are in, and the fill may start.
14. **Duplicate mapping keys are validated and gated (#1029, 2026-09-06).**
    The AI_READI canary's full record carried `source_caveats` at the
    top level three times; every loader keeps the last, so the parsed
    record and the core lost two caveats while validation read the
    last-wins parse and passed. Detection off the record's text is now
    a validation failure (`validation.duplicate_keys`, per artifact) and
    a gated floor of 0, which 270 of 270 records on main support. On the
    generation side nothing bespoke: a failing validation already drives
    the repair round, which is told what to merge. A clean run's output
    is untouched, so VOICE 04f stays retained; the AI_READI 04f record is
    re-verdicted under the instrument (regressed) and AI_READI runs again.

15. **A label minted on an identifier the record carries is exempt from the
    receipt denominator (#1123, 2026-09-09, receipts instrument v2).** v1
    exempted only a fragment on the record's own id byte for byte; the v5
    rule licenses one on any identifier the evidence supplies, so a record
    that labelled its file collections on the landing page (AI_READI
    2026-09-01 rep1, withheld below) or wrote its own id as a fragment on
    its page (CHORUS) was counted as uncovered for them. v2 exempts a
    fragment on the record's `id` in either form, its `doi` or its `page`,
    names its instrument in the block, and counts the difference
    (`slots.exempt_on_carried_identifier`: 4 leaves, all CHORUS API v7, all
    the record's own top-level `id`; one had a receipt, three had none).
    Recomputed with `backfill-checks --blocks receipts --overwrite`: 29
    records; no *gated* number moved (findings, snippet verdicts and chunk
    counts identical). Reported-only values that had never been recomputed
    under later revisions did: three 2026-08-28 CHORUS agentic blocks gained
    the #840/#891/#899 keys and their `recorded_by` moved from `d4d receipts
    check` to `backfill_checks`; `entry_single_leaf_sample[*].leaves` fell
    by one on two CM4AI records (6→5, 7→6: the #842 minted-id filter, own-id
    fragments, not v2); `remapped_by_identity[*].basis` read `by_id` for
    `by_overlap` on CM4AI 2026-09-04b (the #899 remap, not v2); 18 v8 blocks
    gained `recorded_by`. The 18 receipted records whose bundle drifted are
    withheld by the #907 guard and stay under v1 — #1140 is the recompute
    from the git blob. v9 R8's "needs a receipt like any other value" clause
    states the cost v2 removes; #1147 rotates it (no v9 record exists).

16. **The dispositions rows are tallied by record column (#1122, 2026-09-09,
    report_claims instrument v4).** The v9 canary reader was told to compare
    the count of `both` rows with the v8 fill's, and the block carried only
    the total. `rows_by_record` (`full`/`core`/`both`/`either`/
    `no_record_column`/`invalid`, fixed keys, summing to `disposition_rows`)
    is now on every record: recomputed over the corpus with
    `backfill-checks --blocks report_claims --overwrite`, which moved no
    finding and no count into or out of the block — only the new key and
    the instrument string, and 12 rows on two pre-v8 records from `either`
    to `no_record_column` when the two were split. The 12-record fill reads 419 `both` of 461;
    all 18 v8-labelled API records, 617 of 682. Not a generation-path
    change: a derived key in the provenance record, no prompt, assembly or
    datasheet touched.

17. **An entry whose stripped identity key matched nobody is not dropped
    (#1053, 2026-09-09, receipts instrument v3).** The identity join (#899)
    keyed on `id` first; when reconciliation removed a minted id and
    rewrote the entry in place, the id matched no final entry and the
    entry read as `entry_dropped` / `index_reused_by_another_entry`, so
    the pack showed `<path does not resolve>` and the receipt lost its
    credit for a value sitting at the receipted path (CHORUS 2026-09-04f
    rep1, `labeling_strategies[0]`). v3 locates an entry whose key the
    final list carries nowhere as a keyless one — by overlap, else by
    position for the same shape **when the list kept its length**, basis
    `same_key_stripped`, listed under `slots.located_after_key_stripped`;
    a keyed entry whose key other final entries still carry is gone as
    before, and so is a stripped entry in a list that shrank: the strip
    test cannot tell every entry losing its key from this entry being
    deleted and the survivors losing theirs, and the first v3 credited
    the CHORUS 2026-09-01 rep3 receipt for Azra Bihorac / University of
    Florida (`creators[1]`, snapshot 7 creators) to the CHoRUS Consortium
    entry the final record's 2 creators put at that index — the #907
    misjoin again (#1162 review). Recomputed with `backfill-checks
    --blocks receipts --overwrite`: 29 records under v3 (the 18 drifted
    are withheld by the #907 guard and carry no `instrument` key at all,
    #1140); one record moved — CHORUS v8 2026-09-04f rep1, two
    index-reused paths (`existing_uses[0].examples[0]`,
    `labeling_strategies[0].labeling_details`) to none and 53 → 54 slots
    with a receipt, 8 → 9 values changed after the receipt; rep3 reads as
    on main; no finding, snippet verdict or chunk count moved anywhere.
    52 paths corpus-wide carry the basis, 50 of them resolved by overlap
    before and after — so `claim_receipts` puts a new `resolution` on those
    items and a regenerated review pack differs from its committed copy
    (its sha moves and the attestation reads stale, #969); the committed
    04f rep1 pack still shows the two paths as `entry_dropped` until it is
    rebuilt. 15 and 17 are recomputes of a check block with no prompt,
    assembly or datasheet touched — not generation-path changes; #1147's
    rotation of v9 R8 is its own item when it lands.

18. **British spellings instrument v4 (#1006, 2026-09-09).** The Codex
    review of #1003 found eight forms v3 could not see — `labourers`,
    `honourably`, `millilitres`, `micrometres`, `paediatricians`,
    `haematopoietic`, `sulphide`, `grey` — which the normaliser, mirroring
    the instrument rule for rule, let through while `residual_count` read
    0. v4 widens seven patterns (the `-our` family takes `ers`, `honour`
    takes `ably`, `metre` and `litre` take the `micro`/`nano`/`milli`/
    `deci` prefixes, `paediatric` takes `ians`, `haem` takes any `ato…`
    stem, `sulph` any suffix) and adds `grey`; the normaliser is v2, one
    rule per v4 pattern, and its coverage test holds the mirror. The form
    block now names `british_instrument`. Recomputed with
    `backfill-checks --blocks form --overwrite` over all 282 records: 18
    moved, all in the 2026-07 and early-2026-08 arms except the v5 rep1
    AI_READI record (9 → 10, `haematocrit`), the v6 rep3 CM4AI record
    (0 → 2, `nanometres`) and the 2026-08-28d v7 AI_READI canary (44 →
    45), none of which carries a canary block; the v7 production arm (139)
    and the 2026-08-22c baseline (88) are unchanged, so no gate row and no
    canary verdict moves; none of the eight forms occurs in any record, and
    the 52 new occurrences are the widened patterns' (`haematocrit` 19,
    `microlitre` 15, `micrometres` 12, `nanometres` 6). A surname `Grey`
    would be counted, as the Temerty Centre is, and the normaliser leaves it
    as written only inside a title-case run — a bare `family_name: Grey` is
    rewritten and logged, and the disposition command restores it. An
    instrument change lands at a condition boundary: the v8 fill is
    complete and no v9 record exists. Not a generation-path change on its
    own — but the normaliser is on the generation path, and its v2 rule
    table rewrites eight more forms in any run made after it, so a v9 arm
    is compared with v8 across this line as it is across step J.
<<<<<<< HEAD

20. **A receipts recompute reads the bytes a drifted record read (#1140,
    2026-09-10).** `backfill-checks --blocks receipts` refused a record
    whose bundle had drifted since the run and the #907 guard withheld the
    write, so 18 receipted records stayed under receipts instrument v1
    after the v2 and v3 recomputes — among them AI_READI 2026-09-01 rep1,
    the record #1123 was filed about. #1121 already resolves a record's
    bundle to the committed version whose hash it recorded; the recompute
    now does the same (`provenance.bundle_bytes_for`, by the record's md5
    and sha256 where both are recorded — a version matching one and not
    the other is not the version the run read — naming which matched),
    chunks the recovered bytes in memory under the record's own
    `inputs.chunks.rule` (`chunking.manifest_from_bytes`: same bytes + same
    rule = the manifest the run would have chunked; the on-disk manifest's
    rule only where the record carries none, and a recovered manifest
    whose chunk count is not the one the record cites is refused, chunk
    ids being positional), and writes a block whose `bundle_md5` is the
    record's own, with `bundle_basis` naming the commit, hashes and rule
    basis and `artifacts.manifest` carrying the rule and hashes instead of
    a path. Where the record declares no path, no committed version
    matches, git cannot supply the blob, or the blob is not UTF-8, the
    block stays `checked: false` with that reason. `d4d receipts check`
    and the runner's own receipts block make the same recovery, so the
    gate on attestation cannot say "unchecked" of a record the backfill
    checked. Recomputed over the corpus after a one-record canary: 47
    receipted records, all v3, 29 on the bundle on disk and 18 from a git
    blob (every one matched on md5, the only hash those records carry, and
    every one chunked under its own recorded rule, which equals today's);
    on the 18 the chunk count, the snippet verdicts and the findings are
    identical to the blocks written at run time, and coverage moves on
    one — AI_READI 2026-09-01 rep1, 161/508 → 160/498,
    `exempt_on_carried_identifier` 10, the file-collection labels on the
    landing page the v5 rule licenses. The twelve blocks written before
    #840/#891/#899 gain those revisions' keys — about thirty each,
    among them measured, non-zero values that were unmeasured before
    (`snippets.no_value_overlap` up to 63 on v6 rep1 AI_READI,
    `entry_single_leaf`, `slots.never_receipted`, `added_after_receipt`,
    `value_changed_after_receipt_count`), so their `summary` strings move,
    and two of those keys are canary display rows ("snippets bearing on
    no token of their value", "entry receipts overlapping one leaf") for
    which these records supplied no baseline before and supply a measured
    one now — the intended consequence of one instrument, stated here.
    No canary block's receipt row disagrees with its record. `d4d runs
    check` reports receipts blocks by instrument, counts a record it
    cannot read, and names those behind the current one (0 today). Not a
    generation-path change.

22. **The agentic arms carry the transcript's reasoning measure (#1010,
    2026-09-10).** `d4d provenance extend-observed` recomputed every one
    of the 24 agentic records' `run_observed` from its transcript on the
    bundle bytes the record hashed (18 recovered from git, 6 on disk),
    with the record's own `run_observed_until` cut, and extended it only
    where every prior key reproduced exactly — 24 of 24, 21 from one
    transcript and 3 (the v5 rep3 AI_READI, CM4AI and VOICE runs, killed
    and resumed) from the pair of files their name covers, whose sums are
    the recorded token, tool and duration totals and whose union of read
    windows is the recorded `bundle_lines_read`. "Every prior key" is 4–5
    discriminating integers per record (`total_tokens`, eight digits, and
    `duration_ms`, seven, carry the identification; `bundle_lines_total`
    and `receipt_chunks_total` are the bundle's and the manifest's, the
    same for every candidate) — the best non-matching candidate
    reproduces at most 2 of them, and 0 on 16 of the 24. Added: `assistant_turns`, `output_tokens`,
    `thinking_blocks`, `thinking_text_chars` (0 throughout), `visible_text_chars`,
    `tool_input_chars`, `reasoning_tokens_estimate`, and where any turn
    carries it `thinking_tokens` / `turns_with_thinking_tokens` (the
    twelve v6 records and the three resumed v5 rep3 runs). That count is
    partial on all fifteen — `turns_with_thinking_tokens` is short of
    `assistant_turns` by 1 to 6 turns on the v6 records and by 36 to 62
    on the resumed ones, whose first transcript carries the detail on no
    turn — so it is a floor, not the run's thinking, and only
    `reasoning_tokens_estimate` spans both arms. `output_tokens` median 116,774 (v5) and 153,026.5 (v6);
    `reasoning_tokens_estimate` median 68,315.5 and 88,556 — an upper
    bound on a runtime whose output is mostly tool payloads, never
    averaged with `api_usage`. `d4d provenance reasoning` reports all 24
    as `recovered_from_transcript`. Each record's `run_observed_basis`
    describes the keys it carries and no others, and
    `run_observed_extended` is a list
    of extensions naming the keys, the transcripts, the bundle basis and
    the observer script's sha256 (#1191 review). A `VOICE_PEDIATRIC` run
    is looked for as `voicepediatric` or `voicepeds` and never offered as
    VOICE's. Numbered with 19, 20 and 21 open. Not a generation-path
    change; no verdict reads these keys. Each record's
    `run_observed_basis` describes the keys it carries and no others: a
    sentence for the estimate keys present, one for
    `reasoning_tokens_estimate`'s subtraction, one for the runtime's
    count and what its turn coverage means (or, on the nine without it,
    that the observation carries none), and one naming which of them an
    extension added — the record's only in-text statement that those
    numbers are not the orchestrator's own run-time observation.

Each of 2–5, 7–10, 11 and 12 is a generation-path change (13, 14, 15, 16,
17, 20 and 22 are not; 15 and 17 are the receipts instrument's revisions and
=======

20. **A receipts recompute reads the bytes a drifted record read (#1140,
    2026-09-10).** `backfill-checks --blocks receipts` refused a record
    whose bundle had drifted since the run and the #907 guard withheld the
    write, so 18 receipted records stayed under receipts instrument v1
    after the v2 and v3 recomputes — among them AI_READI 2026-09-01 rep1,
    the record #1123 was filed about. #1121 already resolves a record's
    bundle to the committed version whose hash it recorded; the recompute
    now does the same (`provenance.bundle_bytes_for`, by the record's md5
    and sha256 where both are recorded — a version matching one and not
    the other is not the version the run read — naming which matched),
    chunks the recovered bytes in memory under the record's own
    `inputs.chunks.rule` (`chunking.manifest_from_bytes`: same bytes + same
    rule = the manifest the run would have chunked; the on-disk manifest's
    rule only where the record carries none, and a recovered manifest
    whose chunk count is not the one the record cites is refused, chunk
    ids being positional), and writes a block whose `bundle_md5` is the
    record's own, with `bundle_basis` naming the commit, hashes and rule
    basis and `artifacts.manifest` carrying the rule and hashes instead of
    a path. Nothing on disk gates the recovery (#1187 round 3): an absent
    bundle, a missing, stale or unreadable manifest, and a drift are one
    case, checkable from the record's path, hash and rule alone — and
    where the bytes on disk are the record's and only the manifest is not,
    those bytes are chunked in memory rather than asked of git (round 4).
    A record carrying only a sha256 is recovered by it. Where the record
    declares no path, no committed version matches, git cannot supply the
    blob, the bytes are not UTF-8, or neither the record nor a usable
    manifest on disk says which rule to chunk under, the block stays
    `checked: false` — where a recovery produced bytes, the refusal names
    that outcome first and the disk state as context. `d4d receipts check`
    and the runner's own receipts block make the same recovery, so the
    gate on attestation cannot say "unchecked" of a record the backfill
    checked. Recomputed over the corpus after a one-record canary: 47
    receipted records, all v3, 29 on the bundle on disk and 18 from a git
    blob (every one matched on md5, the only hash those records carry, and
    every one chunked under its own recorded rule, which equals today's);
    on the 18 the chunk count, the snippet verdicts and the findings are
    identical to the blocks written at run time, and coverage moves on
    one — AI_READI 2026-09-01 rep1, 161/508 → 160/498,
    `exempt_on_carried_identifier` 10, the file-collection labels on the
    landing page the v5 rule licenses. The twelve blocks written before
    #840/#891/#899 gain those revisions' keys — about thirty each,
    among them measured, non-zero values that were unmeasured before
    (`snippets.no_value_overlap` up to 63 on v6 rep1 AI_READI,
    `entry_single_leaf`, `slots.never_receipted`, `added_after_receipt`,
    `value_changed_after_receipt_count`), so their `summary` strings move,
    and two of those keys are canary display rows ("snippets bearing on
    no token of their value", "entry receipts overlapping one leaf") for
    which these records supplied no baseline before and supply a measured
    one now — the intended consequence of one instrument, stated here.
    No canary block's receipt row disagrees with its record. `d4d runs
    check` reports receipts blocks by instrument, counts a record it
    cannot read, and names those behind the current one (0 today). Not a
    generation-path change.

Each of 2–5, 7–10, 11 and 12 is a generation-path change (13, 14, 15, 16,
17 and 20 are not; 15 and 17 are the receipts instrument's revisions and
>>>>>>> origin/main
17 classifies both; 18 changes the normaliser's rule table and is a
generation-path change by that half); per the production rule none of them may land
between a v8 canary and its fill.

## Decisions needed before step 3

- **D1 (#805)** — adopted 2026-09-03, option (a), applied in step C:
  `inlined: true` on the five Person-ranged slots with descriptions that
  ask for the object. The rejected options: (b) `range: string` (the
  rule-08 class void by design); (c) reference semantics with an
  identifier string (incoherent — `Dataset` has no Person list for a
  reference to resolve to). (a) is the only one that captures what the
  bundles state; the budget cost turned out negative (the markers left).
- **D2 (#902)** — adopted 2026-09-03: receipts per roster entry as a v8
  rule (R4), the only route that raises coverage rather than reporting
  it.
- **D3** — withdrawn: #912's digest half already existed (#538); the
  pack half landed in #916. Nothing to decide.
- **D4 (#906)** — adopted 2026-09-03, option (a), PR #920: the v7 rep1
  AI_READI canary carries an offline re-verdict under instrument v3
  (regressed on the British row, prior verdict under `prior_verdict`). The
  v7 form blocks already hold v3 counts, so the baseline v8's canaries
  are gated against is v3 either way; this decided only that one
  recorded verdict. CM4AI rep1's block (v2 baseline numbers, pre-#891
  rows) was the same shape and was re-derived the same way on 2026-09-09
  (#922): `ok` before and after, British 0 vs 4, the slips row present,
  the report row unmeasured under #684 (the record read no claim) against
  a baseline worst of 1 (2 before `report_claims` v3, #1022/#1046). The
  AI_READI block was re-derived the same way on 2026-09-10 UTC (#1170):
  status `regressed` before and after (British 45 vs 43, the same under
  v4 as proposed in #1173, open at the time of writing), the report row unmeasured, the D4 block (#906) under
  `prior_verdict` and #891's beneath it.
- **D5** — adopted 2026-09-03: API-only v8 first; the agentic arm needs
  #688's launcher and the parity update before a v8 playbook run is
  cheap enough to repeat.
- **D6 (#690)** — adopted 2026-09-03: split the method directory before
  v8 writes records. Design: a runtime-qualified method directory
  (`claudecode_api`, with `_core`) for API-runtime runs from v8 on, plus
  runtime-aware canonical selection (one canonical per project per
  runtime, read from `model.agent_runtime`) so the 104 historical
  API-runtime records and the 90 agentic ones under `claudecode_agent`
  keep separate canonicals; migrating the historical labels is a filed
  follow-up, not a corpus rewrite inside this chain.
