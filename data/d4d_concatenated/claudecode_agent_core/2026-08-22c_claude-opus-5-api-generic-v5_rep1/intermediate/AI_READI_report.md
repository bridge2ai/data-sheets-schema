# Reconciliation Report — AI_READI

**Label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep1`
**Records:** full (`AI_READI_d4d.yaml`, class `Dataset`) and core (`AI_READI_d4d_core.yaml`, class `CoreDataset`)
**Phase:** 4 (strict reconciliation following the Phase 3 source/provenance audit)

---

## 1. What the audit found

The Phase 3 audit returned 48 findings, of which two were withdrawn on re-checking the schema digest (`conforms_to_standard` enum membership; `Creator.source_caveats` admissibility). Neither withdrawn item required action.

The audit found **no fabricated dataset facts**. Participant counts, byte and file totals, the collection window, the DOI, the split arithmetic, the device inventory, the laboratory panel, the license clauses and the IRB details all trace to the declared bundle. Source-conflict handling was assessed as a strength: eleven disagreements were enumerated with tier reasoning, and the two tier-1 sensitivity accounts were represented side by side rather than silently resolved.

The substantive defects clustered into five groups:

| Group | Severity | Count |
|---|---|---|
| Identifier provenance — minted `uriorcurie` values, an unsupported affiliation, an organizational contact typed as a Person | high / medium | 6 findings across both records |
| List granularity — multivalued slots carrying semicolon-delimited or paragraph-length single elements | medium | 18 findings across both records |
| Object structure — Grant identity carried in sibling `notes`; missing available ARK identifiers | high / low | 4 findings |
| Source attribution embedded in content fields | low | 4 findings |
| Value-typing and residue — eligibility ceiling as observed maximum, DOI concatenated into date strings, platform telemetry in `notes` | low | 8 findings |

---

## 2. Changes made — full record

### 2.1 Identifier provenance

**`publisher` — removed.** The original carried `publisher: https://fairhub.io/`. The bundle supplies only the DataCite string `publisherName: "FAIRhub"` and no publisher identifier. The portal home URL was minted, not evidenced. The slot is now absent from the full record; the FAIRhub landing page remains in `page: https://fairhub.io/datasets/3`, which is where a landing page belongs.

**`creators[0].id` — removed.** The original carried `id: https://aireadi.org/`, the project marketing website, standing in as an identifier for the organizational creator "AI-READI Consortium". `Creator.id` is `uriorcurie` and the consortium has no registry entry anywhere in the bundle. The Creator object now has no `id` and the `notes` field records explicitly that no registry identifier for the consortium appears in the bundle.

**`creators[0].affiliations` — one entry removed.** `ROR:00cvxb145` (University of Washington) was dropped, reducing the list from eight ROR CURIEs to seven. The audit found that value attested in the bundle only inside the FAIRhub `locationList` as a study-site location, never as a collaborator or affiliation. The `notes` now states which seven organizations the FAIRhub study description names as lead sponsor or collaborator, and records separately that the University of Washington appears only as a study-site location although the publications place several investigators there.

**`ethical_reviews[0].contact_person` — removed.** The original instantiated a `Person` with `id: mailto:hsdrely@uw.edu`. The RO-Crate gives this as a `ContactPoint` with `contactType: "IRB Reliance Team"` — an organizational mailbox, not an individual. The mailbox and postal address are now stated in `review_details`, and a new `notes` field on that object records that no named individual is given as the review contact in any source.

### 2.2 Object structure

**`funders` — restructured from three entries to five, with Grant objects populated.** The original carried one NIH entry whose two Grant objects had only `id` values (RePORTER page URLs), with the award number `OT2OD032644` and the secondary grants `P30DK035816` and `UL1TR003096` stated only inside `notes` prose. The reconciled record populates `name` and, where the bundle supplies it, `title` on each Grant object, and splits the two BMJ-Open-attested NIH grants into their own `funders` entries so each has a Grant object of its own:

- NIH Bridge2AI entry: two Grants, now carrying `name: OT2OD032644` / `title: "Bridge2AI: Salutogenesis Data Generation Project"` and `name: 1OT2OD032644`.
- New entry, grantor "National Institutes of Health", one Grant `name: P30DK035816`.
- New entry, grantor "National Institutes of Health", one Grant `name: UL1TR003096`.
- Research to Prevent Blindness and Microsoft AI for Good Lab entries unchanged.

**`file_collections[*].id` — all nine replaced with attested ARKs.** The originals were fragments minted on the FAIRhub dataset URL (`https://fairhub.io/datasets/3#cardiac_ecg` and so on). The audit noted that the RO-Crate supplies real ARK identifiers for nine sub-crates mapping one-to-one onto these directories. Each collection now carries its ARK — `ark:59853/rocrate-b2ai-ai-readi-ecg`, `ark:59853/rocrate-b2ai-ai-readi-omop`, `ark:59853/rocrate-b2ai-ai-readi-environmental-sensor`, `ark:59853/rocrate-b2ai-ai-readi-flio`, `ark:59853/rocrate-b2ai-ai-readi-retinal-oct`, `ark:59853/rocrate-b2ai-ai-readi-retinal-octa`, `ark:59853/rocrate-b2ai-ai-readi-retinal-photography`, `ark:59853/rocrate-b2ai-ai-readi-wearable-activity-monitor`, `ark:59853/rocrate-b2ai-ai-readi-wearable-blood-glucose` — with a `notes` field on each naming the corresponding sub-crate title. Minting was correct in principle for labels internal to the record, but attested identifiers existed and are preferable.

### 2.3 List granularity

Nine multivalued slots were split into one element per distinct entity:

| Slot | Before | After |
|---|---|---|
| `known_biases[1].affected_subsets` | 1 semicolon-delimited string | 5 elements |
| `known_biases[2].affected_subsets` | 1 semicolon-delimited string | 3 elements |
| `human_subject_research.irb_approval` | 1 prose block | 4 elements |
| `human_subject_research.regulatory_compliance` | 1 prose block | 5 elements |
| `data_governance.stewardship_roles` | 1 paragraph | 7 elements |
| `at_risk_populations.special_protections` | 1 paragraph | 5 elements |
| `ip_restrictions.restrictions` | 1 paragraph | 5 elements |
| `regulatory_restrictions.regulatory_restrictions` | 1 paragraph | 4 elements |
| `external_resources` | 10 entries, last bundling 3 documents | 12 entries, one per document |
| `intended_uses[0].examples` | 1 semicolon-delimited string | 3 elements |
| `variables[2].categories` (Biological sex) | 1 string `"male; female"` | 2 elements |
| `variables[3].categories` (Race and ethnicity) | 1 string | 4 elements |
| `variables[4].categories` (Diabetes study group) | 1 string | 4 elements |
| `variables[5].categories` (Split assignment) | 1 string `"train; val; test"` | 3 elements |

The `external_resources` split produced three separate entries for the REDCap surveys PDF, the IRB approval letter and the participant consent form, replacing the single bundled entry.

**`sampling_strategies[0].representative_verification` — removed; content relocated.** The original carried one element opening "No representativeness verification was performed", which is a negation occupying a slot that asks what verification *was* done. The statement, together with the mitigating context about site selection and uniform protocols, now appears at the end of `why_not_representative`, where an absence of verification belongs.

### 2.4 Source attribution moved out of content fields

**`is_deidentified.identifiers_removed`** — the clause "stated in the Nature Metabolism comment to be in order to prevent stigmatization of findings" is now "in order to prevent stigmatization of findings", and a new `is_deidentified.source_caveats` records that the rationale is stated in the Nature Metabolism comment while the fact of removal is stated in the FAIRhub description, README and documentation.

**`known_biases[0].bias_description`** — "The BMJ Open protocol states explicitly that this selection bias may limit..." is now "This selection bias may limit...", and a new `known_biases[0].source_caveats` attributes the characterization to the BMJ Open protocol.

### 2.5 Value typing and residue

**`variables[1].maximum_value` (Age) — removed.** The original asserted `maximum_value: 85.0`. The bundle gives 85 only as an eligibility ceiling ("Adults older than 85 years of age" as an exclusion criterion); no observed maximum age is reported anywhere. The eligibility ceiling is now stated in `notes` and the existing `source_caveats` was extended to explain that the figure is a criterion rather than an observed bound. `minimum_value: 40.0` is retained — 40 is both the eligibility floor and, given the exclusion, a genuine lower bound on observed values.

**`distribution_dates[*].release_dates` — DOIs and versions unconcatenated.** All three entries changed from e.g. `"2024-05-03 (version 1.0.0, DOI 10.60775/fairhub.1)"` to `'2024-05-03'`, with the version number and DOI moved into the accompanying `notes`. The version 2.0.0 entry's `notes` additionally absorbed the size and file-count figures.

**`license` — value changed.** From `AI-READI Data License Agreement, Version 2.0` (a wording composed from the license document's title block) to `AI-READI custom license v2.0`, the DataCite `rightsName`. All three tier-1 renderings share a rank, so the ranking cannot decide; the DataCite value was chosen because it is the one attached to the dataset record itself rather than to the document. A new `license_and_use_terms.source_caveats` enumerates all three renderings — DataCite, the FAIRhub pages' "Health Data License", and the document's own title — and states that all three refer to the single Zenodo document. The `license_terms` prose was also amended to drop the composed name in favor of "a custom license, published at https://doi.org/10.5281/zenodo.17555036".

**`notes` — telemetry removed.** The sentence "The FAIRhub API records 24,636 views and zero citations for this version at the time of capture" was deleted. View and citation counts are point-in-time platform statistics that are stale on arrival. The two repository notices are retained.

**`instances[0].data_substrate` — added.** The audit noted the slot was omitted despite bundle support. `B2AI_SUBSTRATE:11` (DICOM) is now recorded, DICOM being the release's largest holding by volume. The `notes` on that object explains that both `data_topic` and `data_substrate` are single-valued and cannot express the full modality range, and directs the reader to `file_collections`.

**`regulatory_restrictions.notes` — expanded.** The mapping of HL7 2N to the `restricted` enum value is now stated as an interpretive decision, with the note recording explicitly that 2N denotes *normal* confidentiality and that the enum value derives from the access controls rather than from the code. The value itself was left as `restricted`; see §4.

**`source_caveats` (top level) — renumbered and extended** from 11 items to 14. New items cover the license-name disagreement (item 10), the identifiers not supplied by the bundle and the reasons for omitting `publisher`, `creators[0].id` and `ethical_reviews[0].contact_person` (item 11), and the single-valued limitation on `Instance.data_topic` and `Instance.data_substrate` (item 14). Item 7 (age ceiling) was rewritten to reflect the `maximum_value` removal.

---

## 3. Changes made — core record

Every change above that touches a slot present in the core record was applied there identically. Specifically:

- `publisher` removed; `creators[0].id` removed; `ROR:00cvxb145` removed from affiliations; `ethical_reviews[0].contact_person` removed with the mailbox moved to `review_details` and a `notes` field added.
- `funders` restructured to five entries with populated Grant `name` and `title`.
- `known_biases[1].affected_subsets` (5 elements), `known_biases[2].affected_subsets` (3), `human_subject_research.irb_approval` (4), `human_subject_research.regulatory_compliance` (5), `data_governance.stewardship_roles` (7), `at_risk_populations.special_protections` (5), `ip_restrictions.restrictions` (5), `regulatory_restrictions.regulatory_restrictions` (4), `intended_uses[0].examples` (3), `external_resources` (12 entries) all split.
- `sampling_strategies[0].representative_verification` removed, content folded into `why_not_representative`.
- Source attribution removed from `is_deidentified.identifiers_removed` and `known_biases[0].bias_description`, with `source_caveats` added to both.
- `license` changed to `AI-READI custom license v2.0`; `license_and_use_terms.source_caveats` added.
- `distribution_dates[*].release_dates` reduced to bare dates.
- Telemetry sentence removed from `notes`.
- `instances[0].data_substrate: B2AI_SUBSTRATE:11` added.
- `regulatory_restrictions.notes` expanded with the interpretive-mapping disclosure.

**Core-specific change: `distributions[*].notes` now carry the sub-crate ARKs.** `CoreDistribution` declares no identifier field, so the ARKs recovered for the full record's `file_collections[].id` could not be carried structurally. Each of the nine `distributions` entries now closes its `notes` with "The RO-Crate assigns the corresponding sub-crate the identifier `ark:59853/...`", alongside the file counts that were already there.

**Core `source_caveats` — item 15 rewritten.** The original projection note said only that CoreDistribution has no file-count field. It now records that CoreDistribution declares no file-count, name *or* description field, and that per-directory file counts, descriptive text *and* the sub-crate ARKs are therefore in `notes`, with the full record's `file_collections[].file_count` and `file_collections[].id` named as the structured forms. Items 10, 11 and 14 from the full record's caveats were also incorporated so the two records' caveat sets stay aligned.

Both records' `instances[0].notes` differ only in the closing cross-reference — the full record points to `file_collections`, the core record to `distributions` — reflecting the actual slot present in each.

---

## 4. Findings left as-is

**`conforms_to_standard` enum membership (full record).** Withdrawn by the audit itself on re-checking. All seven values are members of the declared enum. No change.

**`creators[0].source_caveats` admissibility (full record).** Withdrawn by the audit. The digest lists `source_caveats` among Creator's accepted slots. No change.

**`funders[0].grants` Grant `id` values remain RePORTER page URLs.** The audit noted these are attested (FAIRhub `awardURI`; README acknowledgement) so provenance is satisfied. `Grant.id` is `uriorcurie` and no schema-declared prefix covers NIH RePORTER project pages, so the URI fallback is correct. The structural defect — award number in `notes` rather than in the object — was fixed by populating `name`.

**`subsets[*].id` remain fragments on the FAIRhub dataset URL.** The audit flagged these for completeness only and confirmed the pattern is compliant: the splits are labels internal to this record with no referent outside it, no attested identifier exists for them, and fragment-on-an-attested-identifier is the sanctioned minting form. Unchanged in the full record; the core record has no `subsets` slot.

**`regulatory_restrictions.confidentiality_level` remains `restricted`.** The audit rated the HL7 2N → `restricted` mapping as transparency-adequate rather than defective. The value was retained because the operative facts — authenticated login, research-purpose attestation, binding license — describe restricted rather than unrestricted access. What changed is the disclosure: the `notes` now states plainly that 2N denotes normal confidentiality and that the enum value derives from access controls, not from the code.

**`license_and_use_terms.data_use_permission` remains `disease_specific_research`.** The audit recorded this as "no defect, noted for completeness". The enum is single-valued; the access condition restricting use to type 2 diabetes research is the closest match. The license's simultaneous grant of commercial use is described in `license_terms`.

**`instances[0].data_topic` remains `B2AI_TOPIC:43` (Diabetes).** The audit noted the slot is single-valued and that several alternatives are equally central. Diabetes is the dataset's subject and no other single term dominates it. The choice is now explained in the object's `notes` and in top-level `source_caveats` item 14, which was the audit's actual complaint ("the choice is not explained").

**Core `distributions` file counts remain in `notes`.** The audit judged this "acceptable given the schema constraint". `CoreDistribution` declares no file-count field, so there is nowhere else for them. The disclosure was strengthened rather than the placement changed.

**`conforms_to_class` values.** Confirmed correct and distinct: `Dataset` in the full record, `CoreDataset` in the core. No change required; the audit recorded this only to verify the pair differs appropriately.

**Retained telemetry-adjacent content.** The two repository notices in `notes` ("This repository is under review for potential modification in compliance with Administration directives"; "Platform is currently in beta") were kept. Unlike view and citation counts these are governance statements about the hosting arrangement that bear on whether and how the dataset can be obtained.

---

## 5. Referent

Both records describe the **public release of version 3.0.0** of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, DOI `10.60775/fairhub.3`, as published on FAIRhub on 17 November 2025. This choice was made in Phase 1 and is unchanged. The separate controlled-access release is described in both records only as a set of additional variables held back from the public one; the bundle gives it no DOI, size or file count, and it is not the record's subject. Top-level `source_caveats` item 13 states this in both records.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Slots populated at top level | 66 | 57 |
| Validation | passed (`Dataset`) | passed (`CoreDataset`) |
| Findings actioned | 24 of 25 applicable | 23 of 23 applicable |
| Findings left as-is with reason | 9 | 8 |

Three `uriorcurie` values that the bundle does not supply were removed rather than replaced. Nine identifiers that the bundle *does* supply, and that the original record had minted around, were substituted in. Fourteen multivalued slots were decomposed. No dataset fact was added, altered or removed in either record beyond the age-maximum retraction, which withdrew a claim the bundle does not support.