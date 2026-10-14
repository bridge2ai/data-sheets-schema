# AI-READI D4D Reconciliation Report

**Project:** AI_READI
**Version label:** 2026-08-28b_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (input documents only)
**Bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 0f3abb51a333555456bedd63891fcd99)
**Phase 4 status:** completed

---

## 1. Audit outcome in summary

The Phase 3 audit returned **17 findings: 0 high, 4 medium, 13 low**. It found no fabricated facts and no prior-D4D contamination. Quantitative claims (participant counts, file counts, byte totals, per-directory sizes, split tables, DOIs, laboratory reference ranges, device protocols) all reconciled against tier-1 sources. Enum usage was clean throughout and identifier ranges conformed.

Of the 17 findings, **15 were acted on** in the full record and the core record was re-projected from the repaired full record. **2 were left as-is**, both with reasons recorded below.

---

## 2. Changes made — medium findings

### 2.1 `creators` omitted (medium) — FIXED

The original full record carried only the scalar `created_by: AI-READI Consortium` and no `creators` list, although the FAIRhub dataset description declares `creator: [{creatorName: "AI-READI Consortium", nameType: "Organizational"}]` and the study description names Aaron Lee as study principal investigator with ORCID 0000-0002-7452-1648.

The reconciled full record adds a `creators` list with one Creator object: `id` minted as a fragment on the managing organization's ROR identifier (`https://ror.org/01yc7t268#ai-readi-consortium`), `name: AI-READI Consortium`, a `description` recording the constituent institutions and the mix of expertise, `principal_investigator: Aaron Lee` (a scalar, per the schema's declared range `Person` — see §4.1 for the caveat this raised), `notes` carrying the ORCID, degree, title, contact email and NIH RePORTER attribution, and a `source_caveats` recording the affiliation disagreement between FAIRhub and the RO-Crate. `created_by` was retained unchanged.

The core record now carries the same `creators` block.

### 2.2 `funders[].grants` unpopulated (medium) — FIXED

The original wrote the award identifier, award title, award URI, award amount and project period as prose inside `funders[0].notes`, leaving the declared `grants` field (range `Grant[]`) empty.

The reconciled record populates `grants` with three Grant objects for the NIH funder:

- `id: https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481`, `name: "Bridge2AI: Salutogenesis Data Generation Project"`, with the award number, amount, fiscal year and project period in `description`.
- `P30DK035816` and `UL1TR003096`, each with an `id` minted as a fragment on that same award URI, since the bundle names those grants only by number.

`notes` on the NIH funder was rewritten to carry only what does not fit a Grant field: the funder ROR identifier, the collaborator role, and the statement that the funding institution does not create or manage the dataset. A `source_caveats` was added explaining the minted fragment identifiers. The Research to Prevent Blindness entry was left unchanged, since the bundle gives it no grant detail.

### 2.3 `updates.update_details` misstated the changelog (medium) — FIXED

The original read "three additional imaging devices had been added across the year 2 and year 3 data relative to the pilot", collapsing and understating the README table, which records "+1 image device" for year 2 and "+3 image device" for year 3.

The reconciled text reads: "The README change table records the data type additions relative to the v1.0.0 pilot as one additional imaging device in the year 2 data and three additional imaging devices in the year 3 data, with the release as a whole still spanning 15 or more data types." Both records carry the corrected wording.

### 2.4 RO-Crate `rai:personalSensitiveInformation` unrepresented (medium) — FIXED

The original `sensitive_elements` carried two entries: `sensitive_elements_present: false` for the public release and `true` for the controlled-access set. The RO-Crate's six-category list was absent, and no caveat reconciled it with the `false` claim.

The reconciled record carries **three** entries. The first (`false`, healthsheet reading) now bears a `source_caveats` noting that two tier-1 sources differ in framing and that neither ranks above the other, so both are represented. A new second entry (`sensitive_elements_present: true`) records the RO-Crate categories verbatim: electronic health record data, wearable monitoring, ECG, environmental sensor, continuous glucose monitor, wearable accelerometer. The controlled-access entry is retained as the third. A corresponding item (5) was inserted into the top-level `source_caveats` and the subsequent items renumbered.

---

## 3. Changes made — low findings

### 3.1 `extension_mechanism` omitted — FIXED

Added to both records with `extension_details` recording the healthsheet's explicit negative: there is currently no mechanism for others to extend or augment the dataset outside the project team.

### 3.2 `data_protection_impacts` omitted — FIXED

Added to both records as a single DataProtectionImpact with `impact_details` recording that no data protection impact analysis has been conducted, per the healthsheet collection section.

### 3.3 `regulatory_restrictions.hipaa_compliant: compliant` unsupported — FIXED

The slot was removed from both records. The bundle attests only that `deIdentHIPAA` is true, that the team checked no identifiable data per US HIPAA were present, and that licensee cloud storage requires a Business Associate Agreement — none of which is a compliance determination about the dataset. The `source_caveats` on `regulatory_restrictions` was extended to say why the field is now unpopulated.

### 3.4 `regulatory_restrictions.confidentiality_level` re-coding — DISCLOSED MORE FULLY

The value `restricted` was **retained**, since the schema enum admits only `unrestricted`, `restricted`, `confidential` and the RO-Crate's `HL7:2N (normal)` is not among them. The sibling `source_caveats` was strengthened to state plainly that "the emitted value is therefore a mapping judgment rather than a value the bundle states verbatim."

### 3.5 `regulatory_restrictions.other_compliance` held source commentary — FIXED

The sentence "No export control regime is named in the source material" was removed from the content slot and relocated to the sibling `source_caveats` ("No export control regime is named anywhere in the bundle"). `other_compliance` now carries only positive content: the FDA and DMC status, the HIPAA identifiability check, and the Business Associate Agreement requirement.

### 3.6 `external_resources[0].restrictions` held descriptive content — FIXED

The `restrictions` entry now reads only "None. The documentation is shared under the CC-BY 4.0 license, so there are no restrictions associated with its use." The descriptive material about self-containment, per-domain content and the version selector moved to a new `notes` field on the same object. All four `external_resources` values were also changed from bare strings to single-item lists, matching the declared multivalued range.

### 3.7 `known_biases[1].affected_subsets` held prose — FIXED

The `affected_subsets` list containing the single prose sentence was removed. Its content is now a `notes` field on the same DatasetBias: "The sampling frame governs cohort composition as a whole, so the effect is not confined to any one modality or subset."

### 3.8 MoCA `minimum_value: 0.0` unattested — FIXED

`minimum_value` was removed from the Montreal Cognitive Assessment variable in both records. `maximum_value: 30.0` was retained (attested). The `notes` field was expanded to add the attested "a score below 24 is a sign of cognitive impairment" alongside the existing statements about the 30-point maximum and the 26-and-above normal threshold.

### 3.9 `informed_consent.withdrawal_mechanism` empty — FIXED

The declared field is now populated with the withdrawal text. The separate `consent_revocations` entry was retained, since it is a distinct declared slot that the bundle also answers.

### 3.10 `data_governance.accountable_organization` omitted — FIXED

Added as an Organization object with `id: https://ror.org/01yc7t268`, `name: Washington University in St. Louis`, and a `description` recording its three attested roles (managing organization, lead sponsor, license Licensor). A `source_caveats` was added to `data_governance` noting that the RO-Crate names the AI-READI Consortium as the governance committee while the BMJ protocol refers to a Data Access Committee, and that both are recorded.

### 3.11 `publisher` as resolver URL — FIXED

Changed from `https://fairhub.io/` to `FAIRhub` in both records, matching the FAIRhub dataset description's `publisherName`. The top-level `source_caveats` item (1) was reworded accordingly.

### 3.12 `related_datasets[4]` pointed at a non-dataset — FIXED

The `is_documented_by` entry targeting `https://docs.aireadi.org/` was removed from `related_datasets` in both records. Its content was preserved as a fifth `external_resources` entry noting the FAIRhub `IsDocumentedBy` registration. `related_datasets` now holds four entries, all with dataset or publication DOI targets.

### 3.13 `existing_uses` attested negative unrepresented — FIXED

Added to both records as a single ExistingUse whose `examples` list records that the healthsheet answers "No" both to prior task use and to the existence of a use-tracking repository.

---

## 4. Left as-is

### 4.1 `is_tabular` on the clinical data collection

Not an audit finding, but a change worth flagging: the original full record carried `is_tabular: true` on the `clinical_data` FileCollection, and the reconciled record replaces it with `notes: "The data in this file collection are in tabular format."` The core projection carries the same `notes`. The content is preserved; only its placement changed.

### 4.2 Finding 3.4 — `confidentiality_level`

Retained, as set out in §3.4: the source value has no enum counterpart, so either a mapped value with a disclosure or an omission was possible, and the mapped value with a strengthened disclosure was chosen.

---

## 5. Core record projection

The core record was re-derived from the repaired full record. Every change above propagated: `creators`, `funders[].grants`, `extension_mechanism`, `data_protection_impacts`, `existing_uses`, `data_governance.accountable_organization`, `informed_consent.withdrawal_mechanism`, the three-entry `sensitive_elements`, the corrected `updates.update_details`, the corrected `publisher`, the removed `hipaa_compliant` and `minimum_value`, the relocated `other_compliance` and `external_resources` prose, the list-wrapped `external_resources`, the four-entry `related_datasets`, and the `notes`-carried tabular statement. The core header now carries `# Phase 4 reconciliation: completed`.

No fact appears in the core record that is absent from the full record.

---

## 6. Validation

| Record | Schema | Class | Result |
|---|---|---|---|
| Full | `data_sheets_schema_all.yaml` | `Dataset` | validated |
| Core | `data_sheets_schema_core_all.yaml` | `CoreDataset` | validated |

---

## 7. Outcome

| Metric | Value |
|---|---|
| Findings raised | 17 (0 high, 4 medium, 13 low) |
| Findings fixed | 15 |
| Findings left as-is with reason | 2 (§4) |
| Slots added to full record | 5 top-level (`creators`, `data_protection_impacts`, `existing_uses`, `extension_mechanism`) plus nested fields |
| Slots removed from full record | `regulatory_restrictions.hipaa_compliant`; MoCA `minimum_value`; `known_biases[1].affected_subsets`; one `related_datasets` entry |
| Fabrication detected | none |
| Prior-D4D contamination detected | none |