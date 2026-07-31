# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep2`
**Arm:** BASELINE (input documents only)
**Phase:** 4 — strict reconciliation
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`

---

## 1. Referent declaration

`Dataset` admits one referent. The referent for both records is:

> **Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, published 2025-11-17, 2,280 participants, 356,343 files, 3.82 TB.

This choice is stated here explicitly because the declared bundle is internally split on it. The input manifest selects the v2.0.0 sources (`fairhub_dataset`, `dataset_documentation`), but both carry curation notes stating they are superseded and that the v3 captures should be preferred where the two disagree; the v2.0.0 FAIRhub page itself states "This version of the dataset is no longer accessible." The v3 sources — `fairhub_dataset_v3`, `fairhub_dataset_v3_api`, `dataset_documentation_v3` — are the current release and carry essentially all of the substantive structured metadata in the bundle. Both records resolve to v3.0.0 and hold to it consistently.

The v1.0.0 and v2.0.0 releases are represented as *history* (via `distribution_dates`, `version_access`) rather than as the referent. The "Mini Version" (DOI `10.60775/fairhub.4`, 100 participants) is a distinct dataset per its curation note, not a version of this one.

---

## 2. Core record — blocking defect and regeneration

The audit's two high-severity core findings are correct and are blocking.

The core artifact as it stood contained two entries: `_annotation_analyses: []` and a `conditions_of_access` value. This is not a `CoreDataset`:

- **`id` is required and was absent.** The record cannot validate.
- **`_annotation_analyses` is not a slot.** The declared inventory lists `annotation_analyses` without a leading underscore. An underscore-prefixed key is not in the schema, and an empty list asserts nothing in any case — under the stated preference for omission over vacuous population it should not be present even under its correct name.
- **No referent-establishing content.** With no `id`, `title`, `description`, or `doi`, the core record shared nothing with the full record against which reconciliation could operate.

**Action:** the core record was regenerated against `CoreDataset` from the declared bundle, not repaired in place. It now carries `id` (the v3 DOI URI), `title`, `description`, `doi`, `version`, `license`, `publisher`, `issued`, `keywords`, and the access-condition content described in §3 below, all consistent with the full record.

This is reported as a regeneration rather than an edit because the prior artifact had no recoverable content beyond the single `conditions_of_access` value, which was retained.

---

## 3. `conditions_of_access` — cross-record placement

`conditions_of_access` is not among the 94 slots of the full `Dataset` class. The consequence was that the core record asserted the dataset has substantial access controls while the full record was silent on the question — a direct disagreement between paired records about a well-evidenced property.

The bundle supports this material clearly: `fairhub_dataset_v3_api` gives `accessType: PublicDownloadSelfAttestationRequired` and an `accessDetails.description` enumerating verified-ID login, agreement to use the data only for T2DM-related research, and agreement to the licence terms; the BMJ Open protocol describes the two-tier public/controlled split and states that controlled-access requirements "are being currently developed by the Data Access Committee."

**Action:** this content was folded into `license_and_use_terms` in the full record, which is the field it answers (the slot description asks for the applicable licence, permitted uses, and restrictions). It was retained in the core record under its own slot. Both records now assert the same access posture.

---

## 4. Changes made to the full record

### 4.1 Claims downgraded to match the strength of the evidence

| Slot | Change |
|---|---|
| `is_deidentified`, `participant_privacy`, `future_use_impacts` | Data watermarking was stated as applied. The Nature Metabolism comment says the project "*are implementing* … data watermarking for both public and controlled sets" — a 2024 statement of work in progress. Reworded to reflect stated intent rather than accomplished fact. |
| `license_and_use_terms` | The narrated clauses (one-dollar aggregate liability cap, indemnification, NIH GDS security compliance, no clinical treatment decisions, no re-identification, Other Licensee sharing constraint) are from **licence v1.0**, the University of Washington document actually captured in the bundle. The operative licence for v3.0.0 is **v2.0** (`10.5281/zenodo.17555036`), whose text is *not* in the bundle — only its DOI. The v1.0 attribution was moved from a mid-paragraph aside to the leading clause, so the reader is not invited to treat v1.0 terms as the current ones. |
| `acquisition_methods`, `raw_data_sources`, `direct_collection` | Retrieval of driving and accident records "from the state Department of Licensing" was stated as executed. The only support is the IRB protocol's future-tense "will be obtained from the Department of Licensing." Reworded as protocol-specified. The *existence* of traffic and accident reports in the controlled tier is separately supported by the healthsheet and was retained. |
| `distribution_dates` | The v2.0.0 entry's "data collected through 31 July 2024" derives from the BMJ protocol's description of a release then still *planned*. The v3 healthsheet describes v2 as covering "the first full year of the study" (1,067 participants). Cutoff reworded as the pre-release plan, not a confirmed property. |

### 4.2 Unstated identifier removed

**`publisher`** held `https://fairhub.io`. The bundle gives `publisher.publisherName: "FAIRhub"` with no URI attached. A bare domain is not an identifier the bundle supplies; constructing one is inference. The slot range is `uriorcurie`, and no CURIE or URI for FAIRhub-as-publisher exists in the evidence, so the slot was **omitted**. Publisher identity is preserved in `distribution_formats` and `version_access`, which name FAIRhub in prose.

### 4.3 Funders narrowed

`funders` carried four `FundingMechanism` objects. The healthsheet is unambiguous on attribution:

> "The creation of the dataset was funded by the National Institutes of Health (NIH) through their Bridge2AI Program… The grant number is OT2ODO32644."

P30DK035816, UL1TR003096 and Research to Prevent Blindness appear only in publication acknowledgement sections ("This research is supported by…"), which credit the *research*, not the dataset's creation. Three objects were **removed**; OT2OD032644 retained, with ROR and award URI from the API `fundingReference`. The acknowledged grants are noted in `external_resources` against the publications that acknowledge them.

### 4.4 Absence-statements removed from object slots

Per the v2 rule that a slot must not be populated with a statement that the thing is absent:

- **`confidential_elements`** — the first object was a meta-statement that the dataset contains no confidential data. Removed; the six substantive controlled-tier entries carry the content.
- **`cleaning_strategies`** — the final object recorded that *no* instances were excluded at preprocessing. Removed. (The eligibility criteria that did operate are held in `sampling_strategies`.)
- **`at_risk_populations`** — trimmed to the two genuine safeguards evidenced (rideshare transport assistance for participants reporting transport barriers; consent read aloud with witnessed signature for functionally illiterate participants) plus the Native Biodata Consortium engagement. The catalogue of populations excluded by eligibility criteria was removed to `known_limitations`, where exclusion is what the field asks about.

### 4.5 Typed relationship added

**`related_datasets`** was omitted while the mini-subset was described in `version_access` prose. The API records `data.child: 4`, and the curation note identifies DOI `10.60775/fairhub.4` as a distinct 100-participant dataset for pipeline development. A `DatasetRelationship` was added with both required keys (`relationship_type`, `target_dataset`). The prose mention in `version_access` was left, since it answers a different question (what a user encounters on the landing page).

---

## 5. Conflicts now represented rather than resolved

The instruction is to represent disagreement rather than silently select. Two conflicts were previously stated as settled and are now surfaced in the records themselves.

### 5.1 Lead institution — Washington University in St. Louis vs University of Washington

`fairhub_dataset_v3_api` names Washington University in St. Louis (ROR `01yc7t268`) in four places: `managingOrganization`, `leadSponsor`, and the affiliations attached to Aaron Lee and Cecilia Lee. Every other source in the bundle says University of Washington:

- NIH RePORTER — `Organization: UNIVERSITY OF WASHINGTON`
- The licence — "UNIVERSITY OF WASHINGTON ('Licensor')"
- The IRB protocol — UW Human Subjects Division, approval `STUDY00016228`
- BMJ Open — UW IRB with reliance agreements from UAB and UCSD
- Nature Metabolism — Aaron Y. Lee and Cecilia S. Lee affiliated to University of Washington, Seattle; corresponding address `leeay@uw.edu`
- The API's own `locationList` — "University of Washington", Seattle, ROR `00cvxb145`

This is very likely an upstream metadata error in the FAIRhub record, which is a reason to surface it rather than suppress it. `human_subject_research` now records the UW IRB approval as the governing oversight (with the December 2022 approval date and study number) and notes that the FAIRhub structured metadata names Washington University in St. Louis as lead sponsor, in conflict with the balance of the evidence. The full record no longer reproduces the WashU claim unqualified.

### 5.2 Age eligibility — 40+ vs 40–85

The healthsheet states the eligibility criteria **twice** (preprocessing Q4, inclusion Q3) and both times gives "≥ 40 years old" with no upper bound. The 85-year ceiling appears only in `studyDescription.eligibilityModule` (`maximumAge: "85 Years"`, exclusion "Adults older than 85 years of age") and in the IRB protocol.

`subpopulations` and `known_limitations` previously asserted the 85-year maximum as an operative criterion. Both now state the lower bound as firm and record the upper bound as present in the study metadata and IRB protocol but absent from the healthsheet's eligibility statements. The duplicate eligibility content in `sampling_strategies` was reduced to a cross-reference to avoid a third divergent copy.

---

## 6. Left as-is, with rationale

### 6.1 Omissions verified as evidence-driven

The audit checked a set of unpopulated slots against the bundle and found each omission correct rather than an oversight. No change made to any of these:

| Slot | Why omitted |
|---|---|
| `existing_uses` | Healthsheet uses Q1: "No." A negative answer supports omission, not an object recording absence. |
| `labeling_strategies` | Healthsheet labeling section answers N/A throughout — no labels provided, no labelling performed. |
| `machine_annotation_tools` | Follows from the above: no annotation, so no tooling. |
| `errata` | Healthsheet maintenance Q3 has an **empty** response. An empty upstream answer supports omission over invention. |
| `data_protection_impacts` | Healthsheet collection Q12: "No, a data protection impact analysis has not been conducted." |
| `extension_mechanism` | Healthsheet maintenance Q7: no mechanism currently exists. |
| `use_repository` | Healthsheet uses Q3: "No." |
| `content_warnings` | Healthsheet composition Q12: nothing offensive, insulting, threatening, or posing safety risk. |
| `imputation_protocols` | No statistical imputation described. Filling missing values from elsewhere in a respondent's record is a *cleaning* step and is held in `cleaning_strategies` — placed in the field it answers. |
| `parent_datasets` | API `data.parent: null`. |
| `compression` | No compression format stated anywhere; the enum admits no "none" value. |
| `was_derived_from` | Primary-collected data, not derived from a prior resource. |
| `download_url` | The bundle gives a landing page and a gated "Access this dataset" affordance, no direct data URL. |
| `created_on`, `last_updated_on`, `modified_by` | The only available "last updated" is the *documentation page's* edit metadata ("Jun 4, 2026 by Eamon Dysinger"), which is a property of the docs site, not the dataset. Correctly not transposed. The FAIRhub `created_at` epoch is already carried as `issued`. |
| `discouraged_uses` | Healthsheet motivation Q3 and uses Q5 both point to the licence. Licence terms are prohibitions, not discouragements, so they sit in `prohibited_uses`. Routing confirmed correct. |

### 6.2 Findings not acted on

**`creators` — single object.** Left as one `Creator` for "AI-READI Consortium". The DataCite record declares exactly one creator with `nameType: Organizational`, and that is the dataset's authorship as the metadata states it. The individual consortium members in the Nature Metabolism author list are authors of *that comment piece* under a group byline, not separately declared dataset creators. The description enumerating seven institutions was trimmed so the object does not read as a collapsed multi-entity list.

**`external_resources` — Bridge2AI and project website.** Retained. Both appear in the API `relatedIdentifier` block and the README resource list; the slot description admits documentation and related repositories, and these are the project's canonical documentation entry points.

**`subpopulations` — counts from the split table.** Retained with counts. The README's training/validation/test table is internally consistent and is the dataset's own account of its composition. Each entry already carries the caveat that race/ethnicity and sex are withheld from the public release; that caveat was kept and made uniform. Only the age entry was amended (§5.2).

**`total_file_count` / `total_size_bytes` arithmetic.** Retained as the API's declared totals. The nine `file_collections` sum to 356,334 files — nine short of 356,343 — because nine root-level metadata files (`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`, `healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`, `study_description.json`) sit outside any datatype directory. The byte totals differ by four bytes against the per-directory sum. Both are reconcilable and the declared totals are authoritative; recorded here so the discrepancy is not later read as an arithmetic error.

---

## 7. Provenance note

One structural caveat about this record's evidence base, disclosed because it bears on how the output should be read.

The densest single source in the bundle, `fairhub_dataset_v3_api`, contains an 84-question **healthsheet** — itself a datasheet-style artifact, structured around motivation, composition, collection, preprocessing, labeling, uses, distribution, and maintenance. Material drawn from it is closer to transcription than to extraction. The bundle's own curation note flags this. A substantial fraction of the populated slots in both records — most of `purposes`, `addressing_gaps`, `instances`, `anomalies`, `collection_consents`, `ethical_reviews`, `updates`, `retention_limit` — trace to healthsheet answers rather than to independent synthesis across sources.

No prior D4D record was consulted, in this arm or any other. Facts derive solely from the declared bundle and the schema files.

---

## 8. Outcome

| | |
|---|---|
| **Full record slots populated** | 62 (from 63; `publisher` removed, `related_datasets` added, `funders` narrowed within-slot) |
| **Core record slots populated** | 10 (regenerated from 2, of which 1 was non-schema) |
| **Referent** | Consistent across both records — v3.0.0, DOI `10.60775/fairhub.3` |
| **Cross-record contradictions** | None remaining; the `conditions_of_access` asymmetry is resolved via `license_and_use_terms` in the full record |
| **Source conflicts** | Two, both now represented in-record rather than silently resolved (lead institution; age ceiling) |
| **High-severity findings** | 4 — all addressed (core `id`, core scope, `conditions_of_access` asymmetry, constructed `publisher` URI) |
| **Medium-severity findings** | 7 — all addressed |
| **Low-severity findings** | 22 — 6 acted on, 16 verified as correct and left unchanged |

**Validation must be re-run against both files after these edits.** The core record was regenerated rather than patched and has not previously validated; the prior artifact would have failed on the missing required `id` and on the non-schema `_annotation_analyses` key. No validation result is asserted in this report.