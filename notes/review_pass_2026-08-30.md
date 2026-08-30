# Arm-wide d4d-review-record pass and v6 canonical selection (2026-08-30)

Seventeen records reviewed under the `d4d-review-record` agent (#787): the
twelve 2026-08-28 agentic v6 replicates and the five 2026-08-28 API v7
canaries. One reviewer per record, against a `d4d review pack` (v2: 25
receipted slots sampled, 25 receiptless, every `nothing_relevant` chunk,
every rule of the instruction), each review bound to its pack's sha256 and
checked with `d4d review check --write --strict`. Every review passed strict
on the first check. The `review` block of each provenance record carries the
counts; the review files sit beside the packs.

**What the numbers are.** `adverse` counts verdicts that are not affirmative
over the *sampled* items — it is a rate on a sample of ~50 slots plus the
rules, not a defect count for the record. Each record had a single reviewer
(a Claude agent); there is no inter-rater figure, and the reviewer is not a
gold standard. The two arms are not matched: the v7 side is five canaries,
three of them AI_READI under successive instrument fixes, and v7 carries one
more rule (rule-15, the receipt) than v6.

## Per record

| arm | project | label | items | adverse | cannot_tell | receipted ok | receiptless ok | rules ok | rules violated | canonical |
|---|---|---|---|---|---|---|---|---|---|---|
| agentic v6 | AI_READI | 2026-08-28_rep1 | 68 | 4 | 0 | 23/25 | 25/25 | 13/15 | 07,14 | ✓ |
| agentic v6 | AI_READI | 2026-08-28_rep2 | 68 | 4 | 0 | 24/25 | 25/25 | 12/15 | 05,07,14 |  |
| agentic v6 | AI_READI | 2026-08-28_rep3 | 68 | 13 | 0 | 22/25 | 19/25 | 11/15 | 01,07,12,14 |  |
| agentic v6 | CHORUS | 2026-08-28_rep1 | 66 | 12 | 0 | 18/25 | 23/25 | 12/15 | 01,06,07 |  |
| agentic v6 | CHORUS | 2026-08-28_rep2 | 66 | 9 | 0 | 24/25 | 23/25 | 9/15 | 01,06,07,08,11,14 |  |
| agentic v6 | CHORUS | 2026-08-28_rep3 | 66 | 9 | 0 | 19/25 | 25/25 | 12/15 | 01,06,07 | ✓ |
| agentic v6 | CM4AI | 2026-08-28_rep1 | 72 | 4 | 0 | 24/25 | 22/25 | 15/15 |  |  |
| agentic v6 | CM4AI | 2026-08-28_rep2 | 71 | 9 | 0 | 24/25 | 22/25 | 10/15 | 01,05,06,12,13 |  |
| agentic v6 | CM4AI | 2026-08-28_rep3 | 72 | 4 | 0 | 22/25 | 24/25 | 15/15 |  | ✓ |
| agentic v6 | VOICE | 2026-08-28_rep1 | 67 | 9 | 0 | 21/25 | 23/25 | 12/15 | 01,06,14 |  |
| agentic v6 | VOICE | 2026-08-28_rep2 | 66 | 10 | 0 | 22/25 | 23/25 | 10/15 | 01,06,07,12,13 |  |
| agentic v6 | VOICE | 2026-08-28_rep3 | 67 | 5 | 0 | 24/25 | 24/25 | 12/15 | 01,06,14 | ✓ |
| API v7 | CHORUS | 2026-08-28_rep1 | 68 | 20 | 0 | 16/25 | 19/25 | 11/16 | 01,06,07,08,15 |  |
| API v7 | CHORUS | 2026-08-28b_rep1 | 83 | 13 | 2 | 22/25 | 21/25 | 10/16 | 01,05,06,07,08,15 |  |
| API v7 | AI_READI | 2026-08-28b_rep1 | 70 | 10 | 0 | 24/25 | 24/25 | 8/16 | 01,03,06,09,10,11,12,14 |  |
| API v7 | AI_READI | 2026-08-28c_rep1 | 72 | 14 | 0 | 21/25 | 22/25 | 9/16 | 01,05,06,07,08,12,14 |  |
| API v7 | AI_READI | 2026-08-28d_rep1 | 71 | 14 | 0 | 22/25 | 24/25 | 7/16 | 01,03,06,07,08,10,11,12,14 |  |

Totals: agentic v6 92 adverse over 817 items (11.3%), 0 cannot_tell; API v7
71 over 364 (19.5%), 2 cannot_tell (CHORUS 28b: two slots whose receipted
value phase 4 removed entirely, so there was nothing to judge).

"receipted ok" is `supported` over the 25 sampled receipted slots; "receiptless
ok" is `bundle_supports + exempt_by_nature` over the 25 sampled receiptless
slots. The `nothing_relevant` chunk verdicts are omitted from the table: 51 of
the 52 across the 17 records were `confirmed`; the one `missed_content` is
AI_READI v7 28d chunk c008, marked nothing_relevant while its lines 2144–2150
(consortium affiliations, the PI e-mail) supplied content to
`creators[0].description` — a chunk the record used and the receipt says it
did not.

## What the reviews found that the validator cannot

None of the 17 reviews found a fabricated identifier: every ROR, ORCID, DOI,
RRID and trial id sampled traces to a bundle line. The adverse verdicts are
almost all of four kinds, and each is invisible to a verbatim check:

1. **A real snippet that does not answer the slot.** A repository name
   (`CTP-deid Public`, `privacy_scan_tool`) receipting a de-identification
   *method*; a "Contact Us" line receipting a *maintainer*; an IRB
   recruitment passage receipting *clinical validation*; `"project_name":
   "AI READI"` receipting a licence description. The snippet is verbatim,
   over the length floor, in the cited chunk — and bears on nothing in the
   value. (CHORUS v6 rep1/rep3, VOICE v6 rep1, AI_READI v6 rep3, CHORUS v7
   28, AI_READI v7 28c.)
2. **Plan-as-done.** Future-tense aims in the CHORUS bundle ("will transform",
   "will harmonize", "Program Start Date") rendered as present or past
   fact. Every CHORUS record, both arms.
3. **Composed values whose main claim lives in an unreceipted chunk.** The
   receipt attests one clause; the load-bearing sentence is elsewhere in the
   bundle and receipted nowhere for that slot (AI_READI v6 rep1 slot-004/011,
   CM4AI v6 rep1 slot-011). The value is supported, the attribution is not.
4. **Inferred enums.** `variables[*].data_type`, `file_collections[*].collection_type`,
   `relationship_type`, `raw_data_format` from a file extension — categorisations
   no passage states. AI_READI v6 rep3 names this as likely a large share of
   its 331 receiptless slots.

Rule violations cluster: rule-01 (no inference) and rule-06 (omit rather
than record absence) in nearly every record on both arms; rule-07 (a
neighbouring slot's content — the access route filed under
`distribution_formats`, return-of-results under `collection_notifications`)
in 7/12 v6 and 4/5 v7; rule-08 (the person's name in a role phrase, or a
bare string where the range is `Person`) in 4/5 v7 and 1/12 v6; rule-12
(British spellings) in 3/12 v6 and 3/5 v7. Two reviewers (VOICE v6 rep2,
CHORUS v7 28) independently name the same semantic pattern: every cohort or
leadership member recorded as their own `principal_investigator`.

The v7 records additionally violate rule-15 (CHORUS 28, 28b): the receipt is
well-formed but 112–113 of ~190 slots carry none, *including phase-1 values*
— so `slots.without_receipt` on the API arm cannot be read as "rewritten by
reconcile" alone (#742 from the other side), and verified snippets can point
at values reconcile later removed.

## Findings against the instruments (issues filed from this pass)

- **rule-14 (fragment ids) conflicts with the schema and the projector.**
  `File.id` and `FileCollection.id` are LinkML identifiers (the latter
  required), and `derive_core.py` matches `resources` to the full record *by
  id*. Six v6 verdicts of `rule-14 violated` are on exactly those ids, which
  the record could not omit; CHORUS v6 rep2's 68 fragments on persons and
  the dataset (ids the schema leaves optional) are the genuine case. The v6
  fragment rule needs a carve-out for identifier slots, and the reviewer
  should consult `induced_slot(...).identifier` before ruling.
- **Two writers emitted YAML aliases.** `runs select` wrote the demotion
  pointer as one object referenced twice (`canonical_superseded_by: &id001`
  … `superseded_by: *id001`) in the four v5 records it demoted today, and
  `write_pack` wrote every pack's chunk spans the same way (`lines: &id001`).
  Fixed at the writer (a no-alias dumper on `ProvenanceRecord.write` and
  `write_pack`, regression tests). The four provenance records were
  rewritten; **the 17 packs were not**, because each review is bound to its
  pack's sha256 — the aliases in them are valid YAML and resolve on load.
- **`_value_at` indexed into a string.** A receipt path
  `missing_data_patterns[3]` into a value phase 4 had collapsed to one
  string rendered the pack item's value as `'g'` (CHORUS v7 28b). Fixed:
  an `[n]` step resolves only against a list.
- **Entry-level receipts attest one leaf.** An entry receipt on
  `file_collections[4]` whose snippet matches only `description` covers the
  entry's counts and ids by construction (#721); the reviewer for AI_READI
  v7 28c asks for a validator flag when the snippet matches exactly one leaf.
- **Schema.** `Creator.principal_investigator` and
  `DataGovernance.committee_contact` declare `range: Person` while their
  descriptions ask for a name; both bare strings and ORCID CURIEs validate
  (CM4AI v6 rep3, AI_READI v6 rep3).

## Canonical selection for the v6 arm

`d4d runs select --config 2026-08-28_claude-opus-5-claudecode-generic-v6
--execute`, criterion unchanged (validates → most slots → lowest label):

| project | selected | slots | margin | review adverse (selected / others) | displaced |
|---|---|---|---|---|---|
| AI_READI | rep1 | 82 | 2 | 4 / 4, 13 | 2026-08-22c v5 rep2 |
| CHORUS | rep3 | 50 | 3 | 9 / 12, 9 | 2026-08-22c v5 rep3 |
| CM4AI | rep3 | 59 | 2 | 4 / 4, 9 | 2026-08-22c v5 rep1 |
| VOICE | rep3 | 79 | 1 | 5 / 9, 10 | 2026-08-22c v5 rep2 |

Every margin is thin (the command says so), and the review was not an input
to the criterion (#660). It is recorded here as a cross-check: in each
project the selected replicate is at or tied for the fewest adverse review
items, so the selection and the review do not disagree. The displaced v5
marks are demoted to `canonical_history` with a pointer to what replaced
them; nothing was moved or deleted.
