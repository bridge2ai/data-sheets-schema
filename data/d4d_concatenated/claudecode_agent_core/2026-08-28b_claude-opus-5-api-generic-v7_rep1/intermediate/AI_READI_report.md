# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-28b_claude-opus-5-api-generic-v7_rep1`
**Records:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Audit findings:** 17 (0 high, 4 medium, 13 low)

---

## 1. Audit summary

The Phase 3 audit found no fabricated facts and no prior-D4D contamination. Quantitative claims (2,280 participants; 356,343 files; 3,815,969,779,678 bytes; per-directory counts; the 1,576/352/352 split; DOIs and release dates; laboratory reference ranges; device models and export formats) all reconcile against tier-1 sources. Enum usage and identifier ranges were clean throughout.

The findings clustered into four kinds:

- **Supported omissions** — slots the bundle plainly answers that the record did not carry (`creators`, `extension_mechanism`, `data_protection_impacts`, `existing_uses`).
- **Shape nonconformance** — content in free text where a declared structured field exists (`funders[].grants`, `informed_consent.withdrawal_mechanism`, `data_governance.accountable_organization`).
- **Accuracy** — one misstatement against the README changelog, one unattested numeric bound, and one unrepresented tier-1 statement in tension with an emitted value.
- **Slot hygiene** — source commentary, descriptive prose and non-conforming targets in the wrong fields.

---

## 2. Changes made to the full record

### 2.1 Medium findings

**`creators` — added (was absent).**
The record previously carried only the scalar `created_by: AI-READI Consortium`. A `Creator` object is now emitted with `id` (a fragment minted on the managing organization's ROR identifier as the bundle supplies it), `name`, `description` naming the member institutions, and a nested `principal_investigator` Person carrying Aaron Lee's ORCID as stated in the FAIRhub study description. A `source_caveats` on the Creator records that the two tier-1 sources give different affiliations for the PI (Washington University in St. Louis in the FAIRhub study description; Department of Ophthalmology, University of Washington in the RO-Crate) and that both are recorded rather than one being selected.

**`funders[0].grants` — added; award details moved out of `notes`.**
The NIH entry now carries three `Grant` objects: the primary award (`id` = the award URI the FAIRhub dataset description supplies, `name` = the stated award title, `description` = award number, amount, fiscal year and project period from NIH RePORTER), plus `P30DK035816` and `UL1TR003096`. The latter two are identified by fragments minted on the primary award URI, because the bundle names them only by number; a `source_caveats` on the funder states this. The `notes` field was rewritten to carry only what the grants do not: the NIH ROR identifier, its collaborator role, and the statement that the funder neither creates nor manages the dataset.

**`updates.update_details` — corrected.**
The record previously stated "three additional imaging devices had been added across the year 2 and year 3 data relative to the pilot," which collapsed and understated the README changelog table. It now reads: "one additional imaging device in the year 2 data and three additional imaging devices in the year 3 data, with the release as a whole still spanning 15 or more data types."

**`sensitive_elements` — expanded from two entries to three.**
The RO-Crate's `rai:personalSensitiveInformation` list (EHR, wearable monitoring, ECG, environmental sensor, continuous glucose monitor, wearable accelerometer) was previously unrepresented and stood in unacknowledged tension with `sensitive_elements_present: false`. A second entry now carries that list with `sensitive_elements_present: true`, and a `source_caveats` on the first entry states that two tier-1 sources differ in framing, that neither ranks above the other, and that both are therefore represented. The controlled-access entry is unchanged and is now third.

### 2.2 Low findings — changed

**`extension_mechanism` — added.** Carries the healthsheet's explicit negative: no mechanism exists for others to extend or augment the dataset outside the project.

**`data_protection_impacts` — added.** Carries the healthsheet's statement that no DPIA has been conducted.

**`existing_uses` — added.** Carries the healthsheet's two negatives (no prior tasks; no use-tracking repository) as a single `examples` entry.

**`regulatory_restrictions.hipaa_compliant` — removed.** The value `compliant` was an inference; the bundle attests only de-identification checks and a storage requirement, not a compliance determination. The `source_caveats` now states why the field is unpopulated.

**`regulatory_restrictions.confidentiality_level` — retained as `restricted`, caveat strengthened.** The value is unchanged. The caveat now says explicitly that the emitted value is "a mapping judgment rather than a value the bundle states verbatim."

**`regulatory_restrictions.other_compliance` — commentary moved.** The sentence "No export control regime is named in the source material" was removed from the content slot and now appears in `source_caveats`. The slot instead carries the FDA/DMC statement, the HIPAA de-identification check, and the license's Business Associate Agreement storage requirement.

**`external_resources[0]` — restrictions and description separated.** `restrictions` now carries only the restriction content ("None. The documentation is shared under the CC-BY 4.0 license..."); the descriptive material about self-containment, per-domain descriptions and the version selector moved to a new `notes` field on the same object.

**`known_biases[1].affected_subsets` — removed; content moved to `notes`.** The single prose sentence is now `notes: "The sampling frame governs cohort composition as a whole, so the effect is not confined to any one modality or subset."`

**`variables[Montreal Cognitive Assessment total score].minimum_value` — removed.** The floor of the scale is not attested. `maximum_value: 30.0` is retained (stated). The `notes` were extended to record the below-24 impairment threshold alongside the existing 26-and-above normal threshold.

**`informed_consent[0].withdrawal_mechanism` — added.** Now carries the withdrawal terms. The separate `consent_revocations` entry was left in place; both slots are declared and both are answered by the same source passage.

**`data_governance.accountable_organization` — added.** An Organization object with `id` = the ROR identifier the FAIRhub dataset description supplies, `name`, and a `description` recording the three roles (managing organization, lead sponsor, Licensor). A `source_caveats` was also added to `data_governance` noting that the RO-Crate names the AI-READI Consortium as governance committee while the BMJ protocol refers to a Data Access Committee.

**`publisher` — changed from `https://fairhub.io/` to `FAIRhub`.** The FAIRhub dataset description states `publisherName: "FAIRhub"`; the resolver URL was neither stated publisher name. The top-level `source_caveats` wording was adjusted accordingly ("names the publisher in the dataset description metadata" replacing "names the distributing platform").

**`related_datasets[4]` — removed.** The entry pointed `target_dataset` at `https://docs.aireadi.org/`, which is not a dataset. The resource is still recorded under `external_resources`, and a fifth `external_resources` entry was added noting its registration in the FAIRhub dataset description as an `IsDocumentedBy` related identifier. `related_datasets` now has four entries.

### 2.3 Collateral edits

The top-level `source_caveats` was renumbered from nine items to nine (a new item 5 covering the sensitive-elements disagreement was inserted; the former item 9 about unused registry identifiers was rewritten to state which identifiers *are* now carried — ROR 01yc7t268 and ORCID 0000-0002-7452-1648 — and which are not). Item 2 gained the clause "both are recorded on the Creator object."

---

## 3. Changes made to the core record

The core record was re-projected from the reconciled full record. All full-record changes that fall within `CoreDataset` propagated:

- `creators` added (with nested principal investigator and caveat)
- `funders[0].grants` added; `notes` rewritten
- `sensitive_elements` expanded to three entries with caveat
- `known_biases[1].affected_subsets` → `notes`
- `existing_uses`, `data_protection_impacts`, `extension_mechanism` added
- `informed_consent[0].withdrawal_mechanism` added
- `data_governance.accountable_organization` and `source_caveats` added
- `regulatory_restrictions.hipaa_compliant` removed; `other_compliance` and `source_caveats` rewritten
- `external_resources[0]` restrictions/notes split; fifth entry added
- `related_datasets` reduced from five entries to four
- `updates.update_details` corrected
- `publisher` changed to `FAIRhub`
- top-level `source_caveats` renumbered

The header block gained `# Phase 4 reconciliation: completed`.

Three full-record repairs did not propagate, because the affected slots are not projected into the core record at all: the `variables` list (MoCA `minimum_value`), and the `splits`/`relationships` blocks. These are carried only in the full record in both the original and reconciled versions.

---

## 4. Findings left as-is

**`regulatory_restrictions.confidentiality_level`** (low). The value `restricted` is unchanged in both records. The audit characterized it as a mapping judgment rather than a stated value, which is correct — but the schema enum admits only `unrestricted`, `restricted`, `confidential`, and `HL7:2N (normal)` is not among them. Omitting the slot would lose an attested fact; emitting `unrestricted` would misstate the access regime. The judgment is now disclosed in the caveat rather than concealed, which is the available remedy.

**`consent_revocations`** — retained alongside the newly populated `informed_consent[0].withdrawal_mechanism`. Both are declared slots and the audit did not ask for the former's removal; the duplication is between two slots the schema declares separately, not within one.

---

## 5. Verification

| | full | core |
|---|---|---|
| Top-level slots populated | 63 | 59 |
| Validates against declared schema | yes | yes |

Validation commands run:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-28b_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-28b_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d_core.yaml
```

**Outcome:** 17 findings addressed — 16 repaired, 1 retained with strengthened disclosure. Both records validate. Referent held constant across both records as version 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project (`doi:10.60775/fairhub.3`).