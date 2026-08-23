# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Basis:** Phase 3 source/provenance audit findings, checked against the declared input bundle only.

---

## 1. Summary of audit outcome

The Phase 3 audit found no fabricated dataset facts. Participant counts, byte and file totals, the collection window, the DOI, the split arithmetic, the device inventory, the laboratory panel, the license clauses and the IRB details all trace to the declared bundle. Two initially-flagged items were withdrawn by the auditor on re-checking the schema digest (`conforms_to_standard` enum membership; `Creator.source_caveats` admissibility) and required no action.

The defects requiring action clustered in four groups:

1. **Identifier provenance** — three `uriorcurie` values minted from homepages or team mailboxes rather than taken from the evidence, and one ROR asserted in a role the bundle does not support.
2. **List granularity** — nine multivalued slots carrying semicolon-delimited or paragraph-length single elements.
3. **Attested identifiers not used** — nine RO-Crate ARKs existed for the nine file collections and were passed over in favour of minted fragments.
4. **Lower-severity issues** — source attribution embedded in content fields, an eligibility ceiling recorded as an observed value bound, DOIs concatenated into date strings, an interpretive enum mapping insufficiently disclosed, and platform telemetry retained in `notes`.

All actionable findings were addressed. Several were deliberately left as-is, with reasons given in §4.

---

## 2. Changes made — full record

### 2.1 Identifier provenance

**`creators[0].id` — removed.** The original carried `https://aireadi.org/`, the project marketing website, as an identifier for the organizational creator "AI-READI Consortium". The bundle supplies `creatorName: "AI-READI Consortium"` with `nameType: "Organizational"` and no registry identifier anywhere. Under the v5 rule, an identifier naming something outside this dataset must be taken from the evidence or the slot omitted. The `id` key is gone from the reconciled record and the `notes` field now states explicitly: *"No registry identifier for the consortium as an entity appears anywhere in the bundle, so the creator object carries no id."*

**`publisher` — removed.** The original carried `https://fairhub.io/`. The DataCite block gives only `publisherName: "FAIRhub"` — a string, no identifier. The portal home URL was minted, not evidenced. The slot is now absent; the FAIRhub landing page for this dataset remains in `page` (`https://fairhub.io/datasets/3`), which is a `string` slot and is the right home for it. This is recorded in `source_caveats` item (11).

**`ethical_reviews[0].contact_person` — removed.** The original instantiated a `Person` with `id: mailto:hsdrely@uw.edu`. The RO-Crate gives this as a `ContactPoint` with `contactType: "IRB Reliance Team"` — an organizational mailbox, not an individual. Instantiating a Person from it misrepresents the entity type. The `contact_person` key is gone; the mailbox and postal address are preserved in `review_details`, and a new `notes` field on that object states: *"No named individual is given as the review contact in any source; the contact is a team mailbox, so no contact_person is recorded."*

**`creators[0].affiliations` — `ROR:00cvxb145` removed.** The University of Washington ROR appears in the bundle only inside the FAIRhub `locationList` as a study-site location identifier, never in the collaborator or lead-sponsor lists from which the other seven affiliations were drawn. The affiliation list is now seven entries. The `notes` field explains the removal and records that the publications nonetheless place several investigators there.

**`funders[*].grants` — award numbers moved into the Grant objects.** The original carried the award number `OT2OD032644` only inside `funders[0].notes`, with the Grant objects holding nothing but RePORTER page URLs as `id`. The reconciled record adds a `name` to each Grant (`OT2OD032644`, `1OT2OD032644`), so the identifying content sits in the object rather than in a sibling free-text field. The RePORTER URLs are retained as `id` — they are attested in the bundle (the FAIRhub `awardURI` and the README acknowledgement).

**`funders` — P30DK035816 and UL1TR003096 separated out.** The original mentioned both grants only in the prose of `funders[0].notes`. They are now two additional `FundingMechanism` entries with their own `grants[].name`, since they are distinct awards.

### 2.2 File collection identifiers

**`file_collections[*].id` — nine minted fragments replaced with nine attested ARKs.** The original minted fragments on the FAIRhub dataset URL (`https://fairhub.io/datasets/3#cardiac_ecg` and so on). The pattern was defensible, but the RO-Crate supplies real ARK identifiers for nine sub-crates that map one-to-one onto these directories. The reconciled record uses them:

| path | reconciled `id` |
|---|---|
| `cardiac_ecg` | `ark:59853/rocrate-b2ai-ai-readi-ecg` |
| `clinical_data` | `ark:59853/rocrate-b2ai-ai-readi-omop` |
| `environment` | `ark:59853/rocrate-b2ai-ai-readi-environmental-sensor` |
| `retinal_flio` | `ark:59853/rocrate-b2ai-ai-readi-flio` |
| `retinal_oct` | `ark:59853/rocrate-b2ai-ai-readi-retinal-oct` |
| `retinal_octa` | `ark:59853/rocrate-b2ai-ai-readi-retinal-octa` |
| `retinal_photography` | `ark:59853/rocrate-b2ai-ai-readi-retinal-photography` |
| `wearable_activity_monitor` | `ark:59853/rocrate-b2ai-ai-readi-wearable-activity-monitor` |
| `wearable_blood_glucose` | `ark:59853/rocrate-b2ai-ai-readi-wearable-blood-glucose` |

Each object gains a `notes` field naming the corresponding sub-crate.

### 2.3 List granularity

Six multivalued slots were split from single collapsed elements into one element per entity:

- **`known_biases[1].affected_subsets`** — one semicolon-delimited string became five elements (Pacific Islanders; Native Americans; non-English speakers; rural populations; populations outside academic health systems).
- **`known_biases[2].affected_subsets`** — one string became three (Hispanic participants; male participants; insulin-controlled participants).
- **`human_subject_research.irb_approval`** — one paragraph became four elements (protocol number and approval date with letter URL; renewal cadence; reliance agreements; FAIRhub review status).
- **`human_subject_research.regulatory_compliance`** — one paragraph became five elements (FDA status; DMC absence; HIPAA Safe Harbor; ClinicalTrials.gov registration; NIH GDS obligations).
- **`data_governance.stewardship_roles`** — one paragraph became seven elements, one per role.
- **`at_risk_populations.special_protections`** — one paragraph became five elements.
- **`ip_restrictions.restrictions`** — one paragraph became five elements.
- **`regulatory_restrictions.regulatory_restrictions`** — one paragraph became four elements.
- **`external_resources[9]`** — the entry bundling the REDCap forms PDF, the IRB approval letter and the consent form was split into three separate `ExternalResource` objects, taking the list from ten entries to twelve.

Two `VariableMetadata.categories` lists were also split from single delimited strings into proper lists: **`Biological sex`** (was `"male; female"`, now two elements), **`Race and ethnicity`** (was `"Asian; Black; Hispanic; White"`, now four), **`Diabetes study group`** (was one long string, now four), and **`Recommended split assignment`** (was `"train; val; test"`, now three).

**`intended_uses[0].examples`** — one semicolon-delimited string became three separate examples.

### 2.4 Slot-fit and evidence-boundary corrections

**`sampling_strategies[0].representative_verification` — removed; content moved to `why_not_representative`.** The original populated a slot asking what verification was performed with a statement that none was performed. That is the anti-pattern the v2 rule names. The negation and its mitigating context are now appended to `why_not_representative`, which is the field that fact answers.

**`variables[1].maximum_value` — removed.** The original asserted `85.0` as an observed data bound. The bundle gives 85 only as an eligibility ceiling ("Adults older than 85 years of age" is an exclusion criterion); no observed maximum age appears anywhere. The 85-year figure now sits in `notes` and `source_caveats` on that variable, described as an eligibility criterion.

**`instances[0].data_substrate` — added (`B2AI_SUBSTRATE:11`, DICOM).** The audit noted the slot was omitted despite bundle support. DICOM is the substrate of the largest holding by volume. Both `data_topic` and `data_substrate` are single-valued on `Instance`, so a new `notes` clause explains that these are closest-single-match terms and that the per-directory `file_collections` entries carry the full modality picture.

**`license` — changed from `AI-READI Data License Agreement, Version 2.0` to `AI-READI custom license v2.0`.** The original composed a fourth wording from the license document's title block while three tier-1 renderings existed unremarked. The DataCite `rightsName` value is now used, and a new `source_caveats` on `license_and_use_terms` enumerates all three renderings (DataCite; the FAIRhub pages' "Health Data License"; the document's own title) and states which was preferred and why.

### 2.5 Embedded source attribution moved to caveats

- **`is_deidentified.identifiers_removed`** — the clause "stated in the Nature Metabolism comment to be" was struck from the content; a new `source_caveats` on `is_deidentified` records that the rationale comes from that source while the fact of removal is stated in the FAIRhub description, README and documentation.
- **`known_biases[0].bias_description`** — "The BMJ Open protocol states explicitly that" was struck; a new `source_caveats` on that bias object carries the attribution.
- **`license_and_use_terms.license_terms`** — the opening phrase naming the license was reworded to "a custom license, published at…" so the disputed name is not restated inside the terms text.

### 2.6 Other

**`distribution_dates[*].release_dates`** — the version number and DOI were concatenated into each date string. `release_dates` is multivalued; each entry now carries a bare ISO date as a list element, with the version and DOI moved into `notes`. The version 2.0.0 entry additionally gains the 2.01 TB / 165,051 file figures that were already present elsewhere in the record.

**`regulatory_restrictions.notes`** — the HL7 2N → `restricted` mapping was disclosed in the original but not flagged as interpretive. The note now states that HL7 2N denotes *normal* confidentiality, that the enum value reflects the access controls rather than the code, and that this is *"an interpretive mapping, not a value the sources state."*

**`notes` (top level)** — the FAIRhub view count (24,636) and citation count (0) were removed. These are point-in-time platform telemetry that will be stale immediately and are not durable dataset facts. The two repository notices remain.

**`source_caveats` (top level)** — expanded from eleven numbered points to fourteen. New items: (10) the three-way license-name disagreement; (11) identifiers not supplied by the bundle and the resulting omissions of `creators[0].id`, `publisher` and `ethical_reviews[0].contact_person`; (14) the single-valued constraint on `Instance.data_topic` and `data_substrate`. Item (7) was rewritten to record that the 85-year figure is an eligibility criterion rather than an observed bound.

---

## 3. Changes made — core record

The core record received every change above that has a `CoreDataset` counterpart, and no others. Specifically:

- `creators[0].id` removed; `notes` updated identically.
- `publisher` removed; `page` retained.
- `creators[0].affiliations` reduced to seven, `ROR:00cvxb145` dropped.
- `funders` restructured identically: `Grant.name` added, P30DK035816 and UL1TR003096 separated into their own entries.
- `ethical_reviews[0].contact_person` removed; mailbox moved to `review_details`; explanatory `notes` added.
- `license` changed to `AI-READI custom license v2.0`; `license_and_use_terms.source_caveats` added.
- Nine multivalued slots split into per-entity elements, identically to the full record.
- `sampling_strategies[0].representative_verification` removed; content folded into `why_not_representative`.
- `instances[0].data_substrate` added; `notes` updated (pointing to `distributions` rather than `file_collections`, per the core schema).
- Embedded source attributions struck from `is_deidentified.identifiers_removed` and `known_biases[0].bias_description`; caveats added in both places.
- `distribution_dates[*].release_dates` converted to bare-date lists with version and DOI in `notes`.
- `regulatory_restrictions.notes` rewritten to flag the HL7 mapping as interpretive.
- `external_resources` split from ten to twelve entries.
- Top-level `notes` telemetry removed.

**Core-specific change.** The audit noted that per-directory file counts sit in `distributions[*].notes` because `CoreDistribution` declares no file-count field. That placement was retained — there is nowhere else for them — but each `distributions` entry now also carries the corresponding RO-Crate ARK inside its `notes`, since `CoreDistribution` likewise declares no `id`. The core `source_caveats` item (15) was rewritten to say so explicitly: it now records that `CoreDistribution` declares no file-count, name or description field, that counts, descriptive text and ARKs therefore live in `notes`, and that the full record's `file_collections[].file_count` and `file_collections[].id` are the structured forms.

The core `source_caveats` also gained the same new items (10), (11) and (14) as the full record, and its projection item was renumbered from (12) to (15).

**Verified:** the core record states nothing the full record does not.

---

## 4. Findings left as-is, with reasons

**Two withdrawn findings.** The auditor withdrew the `conforms_to_standard` enum finding (all seven values are enum members) and the `Creator.source_caveats` finding (the digest lists it among Creator's accepted slots). No action was warranted and none was taken.

**`subsets[*].id` fragments retained.** Three split identifiers remain as fragments on `https://fairhub.io/datasets/3`. The audit itself judged this compliant: the splits are labels internal to this record with no referent outside it, no attested identifier exists for them, and fragment-on-an-attested-identifier is the sanctioned minting pattern.

**`funders[0].grants[*].id` RePORTER URLs retained.** These are attested in the bundle. The defect was that the award number lived only in `notes`; adding `Grant.name` fixed that without requiring the URLs to change.

**`instances[0].data_topic` single term retained.** The audit observed that several alternatives (Clinical Observations, Ophthalmic Imaging, mHealth) are equally central. The slot is single-valued on `Instance`, so only one is permissible. `B2AI_TOPIC:43` (Diabetes) was kept as the subject term and the constraint is now disclosed in `notes` and in `source_caveats` (14).

**`license_and_use_terms.data_use_permission` retained as `disease_specific_research`.** The audit recorded this as "no defect, noted for completeness". The enum is single-valued; the access condition ("agree to use the data only for type 2 diabetes related research") is the operative restriction and is the better fit.

**Both `sensitive_elements` entries retained side by side.** Two tier-1 sources disagree and the ranking does not separate them. Under the v5 rule, where disagreeing sources share a rank the ranking cannot decide, so both are represented rather than one selected. The `source_caveats` on the first entry explains the disagreement.

**`distributions[*].notes` prose in the core record retained.** As above: `CoreDistribution` has no field for file counts, names, descriptions or identifiers, so `notes` is the only available home. The full record carries the structured forms.

**Two withdrawn-adjacent items with no change.** `conforms_to_class` was confirmed correct in both records (`Dataset` / `CoreDataset`) and needed no edit.

---

## 5. Referent consistency

Both records describe a single referent: **the public release of AI-READI dataset version 3.0.0, DOI 10.60775/fairhub.3**, as distributed through FAIRhub. The separate controlled-access release is described only as a set of withheld variables — the bundle gives it no DOI, size or file count — and this distinction is stated in `source_caveats` item (13) of both records. No change was needed at reconciliation; the choice was already consistent.

---

## 6. Outcome

Reconciliation complete. Every actionable audit finding was either corrected in both records or explicitly retained with a documented reason. No finding was left silently unaddressed.