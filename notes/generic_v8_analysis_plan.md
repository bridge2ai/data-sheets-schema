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
   are references — it now does, on all eight.
3. **The class the reviews found most often — a true statement in the
   wrong tense or scope** — has no rule at all: prospective stated as
   current (plan-as-done, CHORUS rep1/CM4AI rep3), historical stated as
   current (CM4AI rep3 archives), a related dataset's clause in the
   referent's slot (VOICE rep2, #913), a derived figure stated as the
   source's (#914). These are not inference from stated lines (rule-01
   covers that); they are attested passages attached to the wrong
   claim.

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
`committee_members`) and one more — under the same "required / optional
/ ranges / enums" shape; and mark the eight class-ranged attributes that
are references (`principal_investigator: Person (reference — a string,
not an object)`) in the one function both the digest and the judge's
view read (#486), so the "takes an object" header cannot reach them.
Measured: 67 → 71 nested classes, 40,922 → 43,817 chars against the
44,000 budget — **183 chars of headroom**, so any further digest
addition (D1's option (a) included) must first raise the budget
deliberately. The Dataset digest fingerprint moves `580992ed` →
`e3e060fe` (recorded in `digest_inventory.yaml` and the schema-sync
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

C. **Schema wording** (#805; a schema edit, so the digest moves): keep
`range: Person` on `principal_investigator` and `committee_contact`;
rewrite the descriptions to say a Person object — `name`, and where the
bundle states them `orcid`/`email`/`affiliations` — never a bare name
string. Decision D1 below; the recommendation is to keep the range
because the bundles do carry ORCIDs and emails the reviewers located.

D. **`ADDED IN v8`** — four rules, each naming a mechanism rather than
restating a prohibition:

1. *Inlined vs reference ranges, by the digest's marking.* A class-ranged
   attribute the digest marks `(reference — a string, not an object)`
   takes exactly that; every other class-ranged attribute takes an
   object with the keys the digest lists for that class — `Grant` under
   `grants`, `Organization` under `affiliations` — and a reconcile or
   repair phase must never reduce such an object to a string, nor
   inflate a reference to an object. (#900's Grant half; the Person
   slots follow D1 — if D1 chooses `inlined: true`, they move from the
   first sentence to the second and the digest marking moves with them.)
2. *Tense and scope.* Before writing a value from a passage, name to
   yourself what the passage is about and when: a plan, a proposal or
   a future release is stated as such or omitted, never as the current
   state; a description of an earlier release or an archived version is
   not a fact about the referent's current release; a passage under a
   source the manifest declares related-but-distinct describes that
   dataset, not this one, and belongs only in `related_datasets`. The
   coverage receipt's snippet must come from a passage about the
   referent in the present. (#830 comment, #913)
3. *Derived figures.* A number the record computes from attested
   figures — a sum, a difference, a fraction, a count — is stated as
   the record's computation with its inputs named, never as a figure a
   source reported; a passage cannot receipt an arithmetic result it
   does not contain. (#914)
4. *Receipts per entry for rosters.* Where a slot is a list of objects
   the bundle states one by one — creators, funders, variables,
   files — each entry carries its own receipt naming the passage that
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
| 2 | `grant_number`/`grant_title` populated where the bundle states an award number | A | every funder with an award number in the bundle; v7 had none |
| 3 | rule-06/07 violated (absence statements, access routes) | D2 | ≤ 2 of 12, from 7 of 12; a fall that does not reach this says restatement, not mechanism, was tried |
| 4 | misread verdicts of the tense/scope class (plan-as-done, historical-as-current, related-dataset clause) | D2 | 0 in the sampled receipted slots, from 5 instances on v7 |
| 5 | `value_changed_after_receipt` | A (work moved out of reconcile) | falls from 13.0% of receipt paths toward the v6 agentic arm's re-receipted 0; the measure is the fraction, not a floor |
| 6 | receipts `with_receipt / receiptable` | D4 | rises from 35.5% arm-wide toward the agentic arm's 48.2%; rule-15 violated < 8 of 12 |
| 7 | unforced mints (rule-11/14) | D1, watched | unchanged — v8 adds no minting rule; a fall would be the digest's labels displacing invented ids |
| 8 | populated leaves, rubric10/20 | A + B, watched | not below v7 within replicate spread; a fall means the larger digest displaced reading (the v7 markers confound, in a new form) |
| 9 | spend | A + B | prompt tokens rise by the digest growth; `full` output unchanged |

### Falsification tests

- **Rules restated, mechanism absent.** If prediction 1 holds but 3 and
  4 do not, the digest fixed what it can see and the v8 rules did what
  v2's did — nothing. Then D2 is text and should be cut, not extended.
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
CHORUS), gated against the **v7 production worst-of-arm** on every
existing metric (not the v5 baseline v7 used — v7 is now the better
instrument-matched baseline), the receipt floors at 0 with the #891
exposure-adjusted tolerances, and instrument-v3 British counts on both
sides (#906 settles whether the v7 side is re-derived). A canary that
fails on a prediction-1/2 metric is a v8 defect; one that fails only on
bookkeeping classes follows the v7 retained-with-basis pattern. Fill to
4×3 only after all four pass; the five Aug-28 exploratory records stay
excluded from every v8 comparison as they were from v7's.

## Sequencing (PRs, in order)

1. **F** — bundle fixes (#886, #875), rebuilt bundles and manifests,
   `audit-bundles --strict` clean. Moves `bundle_md5` for every project
   touched; existing records drift (reported, not fatal, #452).
2. **A + B + #912-pack** — digest depth two and registry labels, with the
   digest-size measurement and a test that every class reachable from a
   rendered class is rendered. `d4d api prompts check` unaffected
   (digest is assembly, not prompt); the assembly digest moves.
3. **C** — #805 wording, `make gen-project`, schema tests.
4. **D** — `d4d_generic_arm_prompt_v8.md` = v7 + `ADDED IN v8`, the
   version-diff test, `CONDITION_PROMPTS`/`CONDITION_AXES`/
   `RECEIPT_CONDITIONS` gain `generic_v8`, commit, then pin
   (`d4d api prompts pin --reason`). Playbook parity (#648's guard,
   `tests/test_playbook_reach.py`) — the agentic playbook must carry
   the same four rules even if no agentic v8 arm runs, or the parity
   test says which rules reach only one runtime.
5. **E** — report gate in the runner.
6. Register the production matrix here (as v7's plan did), then the
   four canaries, then the fill.

Each of 2–5 is a generation-path change; per the production rule none
of them may land between a v8 canary and its fill.

## Decisions needed before step 3

- **D1 (#805)**, three-way: (a) `inlined: true` on the five Person-ranged
  slots and descriptions rewritten to ask for the object (recommended:
  the bundles state ORCIDs and emails the reviewers located; the v3
  rule and the depth-two digest then apply; costs digest budget — the
  headroom is 183 chars, so the budget moves with it); (b) `range:
  string` with the descriptions as they stand (the rule-08 class is
  void for these slots by design); (c) keep reference semantics and
  require an identifier string (a name is then wrong, and `Dataset` has
  no Person list for a reference to resolve to — the incoherent
  option). Any of the three moves the digest; (a) is the only one that
  captures what the bundles state.
- **D2 (#902)**: receipts per roster entry as a v8 rule (recommended —
  it is the only route that raises coverage rather than reporting it),
  or reporting only.
- **D3 (#912)**: digest labels and pack labels (recommended: both — the
  digest half is the generation fix, the pack half lets a reviewer
  judge v7's existing values without regeneration).
- **D4 (#906)**: whether the v7 rep1 AI_READI canary carries an offline
  re-verdict under instrument v3 — it sets the British baseline v8's
  canaries are gated against.
- **D5**: API-only v8 first (recommended — the agentic arm needs #688's
  launcher and the parity update before a v8 playbook run is cheap
  enough to repeat), or both arms.
- **D6 (#690)**: whether to split the method directory before v8 writes
  another twelve records into `claudecode_agent/`.
