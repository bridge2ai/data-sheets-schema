# Third-adjudicator rulings — 44 rater disagreements (2026-08-29/31)

Adjudicated against direct verification of the bundle files (`sed`/`grep` on the
concatenated bundles) and the LinkML schema (source YAML + compiled JSON Schema),
not just the raters' quoted excerpts.

## Ruling table

| # | Verdict | Reason |
|---|---|---|
| 1 | **weak** (neither) | The CHORUS table at lines 295–395 is genuinely PDF-column-scrambled; A's confident "backwards" read and B's confident "supported" both overclaim precision from an unrecoverable row/column alignment. |
| 2 | **weak** — agree A | `update_details` asks for planned update types/responsible parties/communication method; only the GitHub/Google-Form clause answers that — the rest restates growth/status facts belonging elsewhere. |
| 3 | **weak** — agree A | Both cited lines (45, 1220) are stated future-tense aims; neither names an actual sampling technique (stratified, cluster, etc.), which `strategies` asks for. |
| 4 | **supported** — agree B | The bundle names only one CHoRUS cloud environment throughout (Collaborative Cloud, lines 465–493, 768); identifying it as "the enclave" from context, with no competing entity named, is legitimate synthesis, not weak. |
| 5 | **bundle_supports** — agree A | "PACS" (line 346) is an unambiguous standard acronym; expanding it to "imaging archive" is definitional decoding, not inference. |
| 6 | **inferred** — agree A | Line 42 is the NIH award's project end date, not a stated data-collection end date; grant period ≠ collection period. |
| 7 | **followed** — agree B | The cited descriptions name the actual repo/tool as the answer to "what tooling exists," not a "see elsewhere" deferral — rule-06 targets deferral, not naming a tool. |
| 8 | **violated** — agree A | Verified: "under review… Administration directives" (lines 1044/1057) is a website compliance banner, not the dataset's draft/published/deprecated status — answers nothing the `status` slot asks. |
| 9 | **weak** — agree B | Verified: Leadership Team slide (line 171ff) states name+institution only; NIH RePORTER (line 37) names only Rosenthal as PI. Listing ≠ PI status. |
| 10 | **weak** — agree B | Same reasoning (Kwong). |
| 11 | **weak** — agree B | Same reasoning (Bihorac). |
| 12 | **bundle_supports** — agree A | "Controlled access" (240) + the eligible-outside-org trainee program (215–217, 861–879) is a fair synthesis, not a distinctive unstated claim. |
| 13 | **bundle_supports** — agree A | Same synthesis; all clauses trace to stated lines. |
| 14 | **followed** — agree B | `known_limitations[0]/[2].scope_impact` are near-tautological corollaries of their own stated limitation, not invented facts; PICU/NICU→pediatric/neonatal is safe, self-caveated decoding. |
| 15 | **followed** — agree B | `recommended_mitigation`'s schema description literally asks for a recommended approach — "check the current snapshot" is exactly that, not a rule-06 pointer-dodge. |
| 16 | **violated** — agree A | Verified: `distribution_formats[5]` "Cloud enclave" has no `format` value (unlike its siblings) and its description is pure access-route content — rule-07's own worked example. |
| 17 | **followed** — agree B, on different grounds than either rater argued | Verified schema: `Creator.name` is a generic "human-readable name for this property" (inherited base-class label), while `principal_investigator`'s description explicitly says "a person's name such as 'Aaron Lee'... the slot name reads like a boolean; the value is not one (#360)." A's premise that `name` must hold the person's name is not what the schema asks; the record correctly used `principal_investigator`. |
| 18 | **violated** — agree A | Rule-11's own test (does the thing named have a referent outside this record?) fails: these are real people; a fragment on the project's own website is exactly the "false claim about the organisation" the rule warns against. |
| 19 | **violated** — agree B | Verified schema: `impact_details`/`extension_details` are built to hold a completed analysis/mechanism; "has not been conducted"/"no mechanism currently" are statements of absence, not the substantive content asked for — and the record's own correct omissions elsewhere show it knows the convention. |
| 20 | **violated** — agree A | Verified: `compensation_rationale` asks "why this amount," value gives only payment timing; `anonymization_method` asks for a de-identification technique, value gives storage/access security controls. Clean rule-07 misplacements. |
| 21 | **not_applicable** — agree B | Verified via compiled JSON Schema: `DataSubset.id` is `required`. Minting is forced by representing subsets as structured objects at all — rule-14 governs discretionary minting, not a schema-mandated key. |
| 22 | **supported** — agree B | Verified: line ~2985 (inside the cited chunk range) states the login/T2D-use/self-attestation language near-verbatim; imprecise snippet anchors don't demote an otherwise-supported chunk to weak. |
| 23 | **weak** — agree A | Verified: lines 7366–7369 are an IRB staff-role list (who is responsible), not a described preprocessing step/tool/parameter. |
| 24 | **weak** — agree A, with a correction | Verified a complete standards table (README, ~line 4599) naming CDS/WFDB/OMOP/ESDS/DICOM/Open-mHealth per datatype directory — so the enum's content is true. But the three cited receipts support only OMOP_CDM/DICOM/RO_CRATE; four of seven enum members have no citation among the offered evidence — a genuine partial-receipt defect distinct from correctness. |
| 25 | **bundle_supports** — agree B | Verified line ~4327: "Heart rate can be read from EKG or blood pressure measurement devices" verbatim, plus a Garmin `heart_rate` directory. |
| 26 | **violated** — agree A | `notification_details` is scoped to notice of data collection itself; the cited entry is entirely about returning results to participants — a distinct, misplaced topic. |
| 27 | **not_applicable** — agree B | Verified via compiled JSON Schema: `FileCollection.id` is also `required`; same reasoning as #21, and no other reference to any of the 9 fragments exists in either record. |
| 28 | **supported** — agree B | The pull-quote anchor is an odd choice, but "Yael Bensoussan" appears twice in the same cited chunk, including as corresponding author. |
| 29 | **inferred** — agree A | Verified: the bundle explicitly distinguishes "co-principal investigators" (Bensoussan, Elemento only) from "lead investigators" (the other 10, including Bahr as "Lead Voice Disorders"). Calling Bahr a PI conflates two terms the source deliberately separates. |
| 30 | **violated** — agree A | Same distinction applied at scale: creators[5..11] all get `principal_investigator` from "lead investigator" roles the bundle explicitly reserves for a narrower designation. |
| 31 | **followed** — agree B | Verified line ~2019: "no predefined recommended data splits… researchers encouraged to create their own" is the source's own deliberate answer, not a pending/pointer dodge. |
| 32 | **violated** — agree A | The systemic PI/lead-investigator conflation (#29/30) is exactly a rule-07 pattern: "who leads this cohort" content placed in the field asking "who is the overseeing PI." |
| 33 | **weak** — agree A | The class wants a formal review process with documented outcomes; the passage describes ethics research activities (focus groups) — on-topic but a different concept, as B's own caveat concedes. |
| 34 | **weak** — agree A | Line 1538 is a GitHub repo blurb (capability exists); nothing states geocoding was applied to this dataset's data. |
| 35 | **supported** — agree B | Registration/licensing/compute-provisioning (444–493) squarely answers the access-review question; the trailing sampling sentence is a genuine stray but doesn't overturn an otherwise well-supported value. |
| 36 | **misread** — agree A | Verified: the bundle's own most recent snapshot is dated 2025-11-14 — three days *before* the claimed "Program Start Date: November 17, 2025," which itself sits in a forward-looking "Key Program Dates" schedule in a Sept-9 webinar. Nothing in the bundle can attest Cohort 2 actually began; the value states a scheduled future date as a completed existing use. |
| 37 | **weak** — agree A | Same tool-exists-vs-tool-applied pattern as #23/#34: repo names in a GitHub listing, not evidence they processed this dataset. |
| 38 | **weak** — agree A | Schema wants annotation guidelines/procedures; the passage is a stated future-tense capability ("will label data"), not a described procedure. |
| 39 | **supported** — agree B | `stewardship_roles` asks for a continuing-custodianship role; "Data site managers… follow validated SOPs… report status" is exactly that, directly attested at lines 1254–1334. |
| 40 | **inferred** — agree A | Same PI/leadership-team conflation as #9–11, receiptless form. |
| 41 | **inferred** — agree B, flagging severity | Line 45 states "predicting complications, and measuring treatment response," not deterioration; "Deterioration" appears only as a decontextualized keyword (line 50). Substituting a keyword-list term for the sentence's actual content is closer to fabrication-from-keyword-dump than ordinary inference, but "inferred" is the closest available label. |
| 42 | **exempt_by_nature** — agree B | `use_category`'s schema example is itself a coined category word ("academic research"); it's the record's own classification label, not a bundle-quotable fact. |
| 43 | **inferred** — agree A | "Various source formats" (1234–1236) is generic; "CHoRUS-specific clinical data extract" (1323–1325) is already a transformed deliverable, not the pre-OMOP raw format. Conflates two pipeline stages. |
| 44 | **violated** — agree A | `maintainers[3].maintainer_details` = "a package status page lists versions, maintainers…" is a textbook rule-06 pointer-instead-of-answer. |

## Counts

- **Rater A right: 24** (items 2, 3, 5, 6, 8, 12, 13, 16, 18, 20, 23, 24, 26, 29, 30, 32, 33, 34, 36, 37, 38, 40, 43, 44)
- **Rater B right: 19** (items 4, 7, 9, 10, 11, 14, 15, 17, 19, 21, 22, 25, 27, 28, 31, 35, 39, 41, 42)
- **Neither (my own call): 1** (item 1)

## Policy syntheses

**(a) Weak vs. supported.** Judge against the *chunk* the receipt cites, not the
literal pull-quote anchor — an imprecise anchor inside an otherwise-correct chunk
(items 4, 22, 28, 35, 39) is **supported**, not weak. Rule **weak** when the cited
passage is genuinely on-topic but answers a different question than the slot's own
schema description asks: a stated future aim in place of a completed action (3, 38),
"this tool/documentation exists in our repo" in place of "this tool was applied to
this dataset's data" (23, 34, 37 — a recurring pattern distinct enough to name on
its own), staff-role lists in place of process description (23), or a receipt that
verbatim-covers only part of a multi-member enum while the rest, though true
elsewhere in the bundle, goes uncited (24). Genuine PDF-extraction garbling that
makes row/column attribution truly unrecoverable (1) also belongs here — neither
"misread" (implies confident wrongness) nor "supported" (implies confident
rightness) fits.

**(b) Rule-06 / rule-07 boundary.** Rule-06 is violated only when a field meant to
hold substantive content instead gets "go look elsewhere" (44's pointer to a status
page) — not when the absence *is* the source's own deliberate, stated answer to
the class's defining question (31's "no predefined splits… make your own" is the
bundle's real answer, not a dodge), when the value *names an actual tool/repo* as
the answer to "what was used" (7), or when it's a genuinely actionable
recommendation exactly matching its field (15). Rule-07 is violated when a
class-shaped object is missing its own core structural field entirely and its
prose answers a different class's question outright — access route in a formats
slot with no format value at all (16), payment timing in a compensation-*rationale*
slot (20), storage security in an anonymization-*method* slot (20),
return-of-results in a data-collection-*notification* slot (26) — and, as the
single most repeated pattern across two different records, "cohort/site lead"
content poured into `principal_investigator` wherever the bundle explicitly names
only one or two people with that specific title (9–11, 29, 30, 32, 40). A value
that is mostly on-topic with one stray sentence (35) is a minor defect, not a full
violation.

## What both raters missed

Two things, both independently verified:

1. The VOICE bundle states outright that Bensoussan and Elemento "are
   co-principal investigators" while separately naming ten others, including
   Bahr, as "lead investigators." That one sentence — not the "Lead X
   Disorders" table entries both raters leaned on — settles the entire
   PI-conflation family (items 9–11, 29, 30, 32, 40) across both CHORUS and
   VOICE: the source itself draws the exact line the records blur, and
   neither rater quoted it.
2. Item 36's evidentiary problem is stronger than either rater stated: the
   CHORUS bundle's own newest document is dated three days *before* the
   "Program Start Date" the record treats as a completed existing use —
   nothing in the bundle could attest the event happened, since no document
   postdates it.

Separately (not a raters-missed item but worth flagging): item 17's rule-08
dispute was resolvable by reading the schema itself (`Creator.name` is a
generic label; `principal_investigator` carries an explicit historical
annotation, #360, distinguishing exactly this ambiguity) — neither rater
checked the schema before arguing from assumption.

## Files referenced for verification

- `data/preprocessed/concatenated/{CHORUS,AI_READI,VOICE}_preprocessed.txt`
- `src/data_sheets_schema/schema/D4D_Motivation.yaml` (Creator / principal_investigator)
- `project/jsonschema/data_sheets_schema.schema.json` (DataSubset / FileCollection required fields)
- Full/core record YAMLs named in the case file's per-record section headers
