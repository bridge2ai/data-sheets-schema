# Phase 4 Reconciliation Report — CM4AI

**Records:** `CM4AI_d4d.yaml` (full, class `Dataset`) and `CM4AI_d4d_core.yaml` (core, class `CoreDataset`)
**Referent held constant:** the June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Audit findings received:** 40 (7 high, 16 medium, 17 low, by the severities as given)

---

## 1. Summary of what the audit found

The audit judged both records well grounded in the declared bundle and disciplined about omission, and located the serious problems in three places:

1. **The core record was not a projection of the full record.** It introduced content the full record did not state (`compression: zip` at top level), restructured content into a differently-shaped slot (`distributions` in place of `file_collections`; `resources` in place of `subsets`, losing the split/subpopulation flags), and dropped content the full record carried (`direct_collection`, `citation`, `total_file_count`).
2. **Over-claiming in `creators`.** Fifteen of sixteen Creator objects asserted `principal_investigator` for people the bundle names as co-authors and module leads; only Ideker is attested as PI. A sixteenth Creator carried an affiliation and construction commentary but no person at all.
3. **Slots populated with values their own caveats disowned.** `instances[*].counts` carried project-wide website totals the record itself said were not per-release figures; `collection_timeframes` carried the NIH award period the record itself said was not a measurement window; `errata` documented a revision to a different release.

Alongside these, the audit identified a `mailto:` URI in a `uriorcurie` Person `id`, several clearly supported omissions (`total_size_bytes`/`total_bytes`, `credit_roles`, `external_resources`, `use_repository`, `extension_mechanism`, `machine_annotation_tools`, `cleaning_strategies`, a second `known_biases` entry), and a set of low-severity issues around enum choice, unattested values, and caveats attached in the wrong place or describing actions not taken.

---

## 2. Changes made — full record

### 2.1 Creators restructured (findings: `creators[*].principal_investigator`, `creators[16]`, `creators[16].notes`, `credit_roles`, affiliation-identifier asymmetry)

- The trailing sixteenth Creator — the object with `affiliations: [{name: KTH Royal Institute of Technology}]` and no `principal_investigator` — **has been removed**. It named no agent, and its construction commentary now sits in top-level `source_caveats` under "Creators and roles". The creator list is now fifteen objects, each naming a person.
- The record no longer implies that fifteen people are principal investigators. The `principal_investigator` field is still used for all fifteen (the class offers no other place for a named person), but the Ideker entry now carries a note recording the NIH RePORTER attestation, the Lundberg entry carries a `source_caveats` stating explicitly that the field records "the responsible lead named by the sources rather than an attested PI designation" and that "the same qualification applies to every Creator below," and top-level `source_caveats` restates the position. This is a documentation change, not a structural one: the audit's objection is answered by disclosure rather than by relocating the people.
- **`credit_roles` is now populated** where the bundle attributes a specific contribution: Ideker (`conceptualization`, `supervision`, `project_administration`, `funding_acquisition`), Lundberg and Krogan (`investigation`, `resources`), Mali (`investigation`), Clark (`data_curation`, `software`). It remains absent on the nine creators for whom the bundle attributes no specific role.
- The list has been **reordered** so that the parties with attested data-generation or packaging roles appear first; this is presentational and adds no facts.
- The Ravitsky `source_caveats` previously said the University of Montreal and Hastings Center affiliations were "both recorded here rather than reconciled" while recording only one. It has been **rewritten** to say what the record actually does: the Dataverse affiliation is in `affiliations`, the divergent contact domain is recorded in the caveat, and the bundle states no Hastings Center affiliation for her.
- The affiliation-identifier asymmetry (ROR for UVA only) is now explained in top-level `source_caveats`.

### 2.2 Sizes and file counts (findings: `total_size_bytes`, `total_file_count`)

- **`total_size_bytes: 12602000000` added** to the full record, and **`total_bytes` added to all ten FileCollection objects**, converted from the per-file sizes in the Dataverse listing. The per-file sizes are no longer carried only as prose in the descriptions; the trailing "; 4.6 GB as distributed" clauses have been dropped from the descriptions accordingly.
- **`issued` added to each FileCollection** (2026-06-17 for seven, 2026-07-15 for the three image archives), replacing the "Published 2026-06-17" prose as the structured statement of that date; the prose sentence is retained in shortened form.
- `total_file_count: 10` and per-collection `file_count: 1` are **unchanged in value**, but the first FileCollection now carries a `source_caveats` stating that `file_count` records distributed archives and that the bundle does not state how many files any archive contains. Top-level `source_caveats` repeats this and notes the byte figures are approximate to the listing's precision.
- The `conforms_to_standard: [RO_CRATE]` value has been **added to the release-metadata FileCollection**, matching what the core record already carried for that file.

### 2.3 Values the record disowned in its own caveats

- **`instances[*].counts` removed.** Both `counts: 53788` and `counts: 1374` are gone. The figures survive as prose in each Instance's `notes`, explicitly labelled project-wide totals. The associated `source_caveats` on those two Instance objects have been replaced by the `notes`.
- **`collection_timeframes` removed entirely** from both records. The award period remains under `funders[0].notes`, where the audit judged it belonged, and top-level `source_caveats` records the omission and its reason.
- **Top-level `errata` removed.** Its content has been **relocated** to `related_datasets[2].errata` — the March 2025 relationship entry — since DatasetRelationship accepts the same slots as the top-level listing. The erratum is now attached to the release chain it describes rather than asserted of the June 2026 release.

### 2.4 Identifier and enum corrections

- **`data_governance.committee_contact.id` removed.** The `mailto:jillianparker@health.ucsd.edu` value is gone; the object now carries `name: Jillian Parker` only, the email address has been moved into `access_review_process` prose, and a `source_caveats` on `data_governance` records that the bundle supplies no personal identifier.
- **`maintainers[1].role` changed** from `researcher` to `other`, with a caveat explaining that the enum has no term for a program-management or website-support role.
- **`instances[0].data_topic` changed** from `B2AI_TOPIC:19` (Microscale Imaging) to `B2AI_TOPIC:15` (Image), the more direct term.
- **`instances[1]`** now states in `notes` that B2AI_SUBSTRATE has no protein-interaction term and that `data_substrate` is therefore omitted rather than approximated.
- **`related_datasets` relationship types changed.** October 2025 remains `is_new_version_of` (the immediate predecessor, and the manifest marks it superseded); June 2025, March 2025 and May 2024 are now `continues`, with a caveat on the June 2025 entry explaining the distinction. The flat four-way `is_new_version_of` typing the audit objected to is gone.
- **`status` simplified** from `Beta (interim release; data generation continues through November 2026)` to `Beta`. The parenthetical duplicated `known_limitations` and `updates`.
- **`created_by` changed** from the project name to `Justin Niestroy`, the depositor the Dataverse record names.
- **`last_updated_on` removed.** It had been set to the image-archive publication date, which the bundle does not state as a modification timestamp for the record.

### 2.5 Slots added

- **`cleaning_strategies`** — FAIRSCAPE input validation at each pipeline segment, plus the preprint's statement that CRISPR screen data were undergoing QC, with a caveat that both come from the tier-3 preprint describing the first year.
- **`machine_annotation_tools`** — the GPT-4 / GSAI naming pipeline with confidence scores and the citation module, with a caveat that these annotate the computed cell maps rather than this release's contents.
- **`external_resources`** — five entries: the project portal and releases page; the Cell Mapping Toolkit repository and documentation; FAIRSCAPE documentation; the Integrative Modeling Platform; and the two related publications.
- **`use_repository`** — the Dataverse metrics facility, with the four reported download counts and the note that the citation panel reported none found.
- **`extension_mechanism`** — the Cell Mapping Toolkit contribution route, with a caveat that it covers software reuse rather than contributions to the released archives.
- **`missing_data_documentation`** — the incomplete-overlap pattern, now recorded as a missing-data pattern in addition to the coverage limitation it was already recorded as, with the per-modality and per-stratum gaps spelled out.
- **`known_biases`** — a second entry, `selection_bias`, for the disease-relevance target design, with `affected_subsets` noting the genome-scale KOLF2.1J screen as the exception.

### 2.6 Caveats corrected or relocated

- The **image protein-count disagreement** caveat has been rewritten. It no longer describes October 2025 as "highest ranked source stating a figure" in a way that obscured the current release's silence; it now states the tier of each source, that the current tier-1 release states no figure, and that the ranking therefore cannot settle it. Short caveats pointing back to it have been **added to the paclitaxel and vorinostat image archives**, which previously carried none.
- The **KOLF2.1J perturb-seq availability** caveat now mentions the March 2025 "CRISPR Perturbation RNA Sequences - Raw Sequences" crate as a third data point.
- The **June 2026 release date** caveat no longer diagnoses the website's date as "an error in the year"; it records the disagreement, the tiers, and the preference.
- **`ethical_reviews[0].reviewing_organization`** changed from `CM4AI Ethics Module (Simon Fraser University and The Hastings Center)` to `CM4AI Ethics Module`, with a caveat noting that the parenthetical was an inference from email domains and that the bundle states no formal institutional name.
- **`direct_collection[0]`** now carries `is_direct: false` and an added sentence stating affirmatively that the consent, notification, revocation, compensation and at-risk-population slots are omitted because no individuals were enrolled.
- Top-level `source_caveats` gained entries on sizes and counts, the collection-timeframe omission, creators and roles, affiliation identifiers, and the unattested `language: en`.

---

## 3. Changes made — core record

### 3.1 Projection restored (findings: `distributions`, `resources`, `compression`, `direct_collection`, `citation`)

- **`compression: zip` removed** from the top level. The full record does not state it, and the release is a set of independently compressed archives rather than one compressed distribution.
- **`distributions` retained but corrected.** The audit flagged the block on the grounds that `distributions` does not appear in the supplied `Dataset` digest and the core schema was not available for inspection. The core schema was consulted during reconciliation; the slot and its keys validate. What has changed is that each entry now carries **`bytes`**, so the per-file sizes are structured in both records rather than prose in one and structured in neither, and the wording of the image-archive caveat matches the full record's. The full record continues to carry the same material as `file_collections`, which is the slot `Dataset` declares.
- **`resources` retained**, since `CoreDataset` declares no `subsets` slot. The lost `is_data_split: false` / `is_subpopulation: true` semantics have been restored **in prose**: each of the seven entries now opens by stating that it is "a subpopulation stratum rather than a data split," and top-level `source_caveats` records why the strata sit in `resources` at all.
- **`direct_collection` content restored.** `CoreDataset` does not declare `direct_collection`, so the content has been carried as a **sixth `acquisition_methods` entry** with `was_reported_by_subjects: false`, stating that no data were collected from individuals, naming ATCC and HipSci as the cell-line sources, and recording that the consent-family slots are omitted for that reason. The core record now makes that statement, which it previously made nowhere.
- **47-author list preserved.** `citation` is not declared on `CoreDataset`. The core `source_caveats` no longer merely says the authorship "runs to 47 named authors" — it now directs the reader to the Dataverse citation for `doi:10.18130/V3/HIGT4C`, so the list is retrievable from the core record.
- **`total_file_count`** is not declared on `CoreDataset` and remains absent; the ten distributions are individually enumerated.

### 3.2 Changes mirroring the full record

All Phase 2.1–2.6 changes above that concern slots `CoreDataset` declares have been applied identically to the core record: the creator restructuring and `credit_roles`; removal of `instances[*].counts`, `collection_timeframes`, and top-level `errata` (relocated to the March 2025 relationship entry); the `committee_contact.id` removal; the `maintainers[1].role`, `instances[0].data_topic`, `related_datasets` relationship-type, `status`, `created_by` and `last_updated_on` changes; the six added slots; and the caveat corrections. The two records now state the same facts wherever both declare the slot.

---

## 4. Findings left as-is

**`file_count` semantics (medium).** `total_file_count: 10` and `file_count: 1` still count distributed archives rather than files within them. The bundle states no within-archive counts, so no better value is available; the change made was to say so in a caveat rather than to alter the numbers.

**`principal_investigator` for fourteen non-PIs (high).** The field is still populated for all fifteen creators. `Creator` offers `principal_investigator` (range `Person`) as the only place for a named individual; removing it would remove the people. The finding is answered by explicit caveats at the object and record level rather than by structural change, and this is a disclosed compromise rather than a fix.

**`publisher: ROR:0153tk833` (medium).** Retained. The release names the University of Virginia Dataverse as publisher and supplies that ROR for the institution in the same document; the inference is one step and is disclosed in `source_caveats`. The alternative — omitting `publisher` — loses a fact the bundle supports.

**`language: en` (low).** Retained, now with a caveat stating it is inferred from the documents rather than attested.

**`conforms_to_standard` single value (low).** `RO_CRATE` only. None of EVI, JSON-LD, Schema.org, FAIRSCAPE or ARK maps to a listed enum term; all are named in `conforms_to` prose, which is where the digest says the sources' own words belong.

**`created_on` / `issued` (low, partial).** `created_on: 2025-02-27T00:00:00Z` (Dataverse deposit date) and `issued: 2026-06-17T00:00:00Z` (publication date) are unchanged and attested. Only the `last_updated_on` half of that finding was acted on.

**Consent-family omissions (low).** Still omitted in both records. The affirmative statement the audit found missing from the core has been supplied via `acquisition_methods`, as described above.

**`content_warnings`, `anomalies`, `imputation_protocols`, `splits`, `relationships`, `data_protection_impacts`, `annotation_analyses`, `labeling_strategies` (low/medium).** All still omitted. The bundle documents none of them. The `missing_data_documentation` half of that finding was acted on; `machine_annotation_tools` covers the annotation half, with `annotation_analyses` and `labeling_strategies` left absent because the bundle reports no inter-annotator agreement or human labeling protocol for this release's contents.

**`description` phrasing on collaborators versus affiliations (low).** Retained but **reworded**: it now says the release records "name CM4AI as a collaboration of" the eight institutions and that "the release author list separately records affiliations at" the other four, replacing "contributing authors are additionally affiliated with," which implied a reconciliation the record had not performed.

**`instances[2]` / `instances[3]` substrate-topic pairings (medium, partial).** `B2AI_SUBSTRATE:64`/`B2AI_TOPIC:34` and `B2AI_SUBSTRATE:59`/`B2AI_TOPIC:28` are unchanged; the audit did not identify better terms for either, and both fit. Only the instance-1 topic and the instance-2 omission note were acted on.

---

## 5. Outcome

Both records now state the same facts wherever both schemas declare the slot; where they diverge (`citation`, `total_file_count`, `subsets`/`resources`, `file_collections`/`distributions`, `direct_collection`/`acquisition_methods`), the divergence follows from the core schema's slot inventory and is recorded in the core record's `source_caveats`. No value survives that the record's own caveat disowns. The referent is unchanged in both.