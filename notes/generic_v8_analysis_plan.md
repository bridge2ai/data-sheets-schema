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
| 2 | `grant_number` populated where the bundle states an NIH award number — denominator registered now: AI_READI 2, CHORUS 1, CM4AI 3, VOICE 3 distinct award numbers per bundle (pattern `\b[A-Z]\d{2}[A-Z]{2}\d{6}\b` and kin, e.g. OT2OD032644) | A | ≥ 1 per project in every replicate, from 0 of 12 on v7; the denominator is the ceiling, not the target (some are cited, not funding) |
| 3 | rule-06/07 violated (absence statements, access routes) | E2 | ≤ 2 of 12, from 7 of 12; a fall that does not reach this says the audit did not catch them |
| 4 | misread verdicts of the tense/scope class — classifier: a `misread` whose evidence names a plan/proposal/future release, an earlier version or archive, or a related-but-distinct source as the passage's subject | R2 | 0 in the sampled receipted slots, from 5 on v7 (CHORUS rep2 ×2, CM4AI rep2, VOICE rep2, CM4AI rep3) |
| 5 | `value_changed_after_receipt` | A (work moved out of reconcile), halved by the Person finding | below 10% of receipt paths, from 13.0%; the v6 agentic arm re-receipts and sits at 0 |
| 6 | receipts `with_receipt / receiptable` | R4 (D2) | above 40% arm-wide, from 35.5% (agentic 48.2%); rule-15 violated ≤ 6 of 12, from 8 |
| 7 | unforced mints (rule-11/14) | none, watched | no record above v7's worst (VOICE rep3, 22) and the arm median stays 0; v8 adds no minting rule, so a fall would be the digest's labels displacing invented ids |
| 8 | populated leaves, rubric10/20 | A, watched | not below the v7 per-project replicate minimum; a fall means the larger digest displaced reading (the v7 markers confound, in a new form) |
| 9 | spend | A | prompt tokens rise by ~2,900 chars of digest per call; `full` output tokens within ±10% of v7's per-project mean |

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
- `comparable_conditions("generic_v7", "generic_v8")` is true by base
  step; `CONDITION_AXES` gains `generic_v8: {base: v8, tuned: False}`.

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
| CM4AI | `2026-09-04c_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric under instrument v2: undeclared prefixes 6 vs 0, all `mailto:` person ids (D1 forces `Person.id`). Everything else passed: receipts clean with no re-addressing needed, resolver URLs 0 with 0 rewrites, report gate 1 → 0 among 9 claims, British 0. **Prediction 5: 1.3%** (from 28.3% and 36.0%); 6: 70.4%; 9: +94% (full output 80,319); 2: 0. | Step I (#981/#982): `mailto:` ids get a mechanism and the counter its v3; re-verdicted offline under v3 before the VOICE canary. |
| CM4AI | `2026-09-04b_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric: resolver URLs in identifier slots 16 vs 0 (the dataset DOI as a URL under `id` plus 15 minted fragments); every receipt metric passed — the re-addressing turn dropped the one mis-addressed entry and the report gate regenerated 1 contradiction among 40 claims to 0, both firing on a live run for the first time. Coverage 288/407 (70.8%). British 2 (= v7 worst). One repair round (14). | **Deferred fix, step H (#974)**: identifier form is a rule with no mechanism; the normaliser lands before the third canary. Predictions: 2 unfavourable (0), 5 unfavourable (36.0%), 6 favourable (70.8%), 9 unfavourable (−26.7%). |
| CM4AI | `2026-09-04_claude-opus-5-api-generic-v8_rep1` | **regressed** on one metric: receipt findings 1 against a floor of 0; every other gated metric equal to or better than the v7 per-project worst (British spellings 0 vs 2). Full-phase output 31,207 of 128,000 (24%). One repair round (11 findings). Receipts: 28/28 chunks, 117/168 snippets verified (45 adjacent, 6 elsewhere), 206/342 slots with a receipt (60.2%). | **v8 defect (#952)**, the plan owner's decision on 2026-09-04: the finding is one receipt entry addressed to `subject`, a name the schema has no slot for, for a value the record holds under `keywords` — the v8 receipt rule names the record path the value fills, so the model broke a rule it was given. Not the v7 retained-with-basis pattern. No fill and no further canary until fixed and re-canaried; fix chosen: the runner re-addressing turn (step G, #953); the re-canary runs under a new prefix, `2026-09-04b_claude-opus-5-api-generic-v8`. Recorded in the record's `canary` block (with the withdrawn retained-with-basis reading as `prior_disposition`). **Predictions this record measures (n=1):** 2 favourable (`grant_number` populated 2 of 3); 6 favourable (60.2%); **5 unfavourable** (`value_changed_after_receipt` 41/145 = 28.3% against <10%; v7 CM4AI replicates 17.0/17.4/7.9%); **9 unfavourable** (`full` output 31,207 against the v7 CM4AI mean 41,370, −24.6%, outside ±10%). First launch stopped on a CBORG 403 (off-VPN) before any phase; resumed on the VPN. |

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
    instrument v3 — `mailto:` excluded, as its v2 docstring judged; the two
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

Each of 2–5 and 7–10 is a generation-path change; per the production rule
none of them may land between a v8 canary and its fill.

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
  rows) is the same shape and is #922.
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
