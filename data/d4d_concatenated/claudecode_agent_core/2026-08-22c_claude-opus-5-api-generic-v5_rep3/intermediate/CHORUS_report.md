# Reconciliation Report — CHoRUS Dataset

**Project:** CHORUS
**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Referent

Both records describe a single referent: **the CHoRUS clinical care dataset** — the multicenter, multimodal critical care data resource assembled under NIH award OT2OD032701. They do **not** describe the CHoRUS software repositories on GitHub, nor the AIM-AHEAD Bridge2AI for Clinical Care Training Program, both of which appear prominently in the declared bundle. Those two entities are recorded only where they bear on the dataset: the GitHub organization under `extension_mechanism`, `external_resources`, `ip_restrictions` and `maintainers`; the training program under `data_governance.access_review_process`, `existing_uses` and `intended_uses`. This choice was already stated in both records' `source_caveats` and is unchanged by reconciliation.

---

## 2. Audit summary

The Phase 3 audit returned 34 findings: 3 high, 12 medium, 19 low (several of the low findings being verified-correct omissions rather than defects). They fall into four groups:

1. **Full/core divergence** — the core record carried three facts in slots where the full record did not, because core had dropped `direct_collection`, `third_party_sharing` and `splits` and folded their content into neighbouring slots; and core had reclassified the nine modalities from `subsets` to `resources`, reusing identical identifiers for objects of a different class.
2. **Role and identity over-assertion** — five of six `creators` placed in `principal_investigator`; a coined `reviewing_organization`; an access-request contact re-scoped as a licensing contact; an inferred `accountable_organization`.
3. **Inference presented as evidence** — three `addressing_gaps` entries converting project goals into claims about deficiencies in the field; two `known_limitations` that are the record's own analysis; a self-assigned bias category; an enum mapping presented without disclosure.
4. **Transcription precision** — a rounded magnitude rendered as an exact integer; two garbled-table attributions lacking local caveats.

No prohibited external facts were found in either record. No registry identifiers, ORCIDs, RORs or DOIs were supplied beyond the bundle; the misspelled contact email was transcribed rather than silently corrected; tier ranking was applied correctly on both genuine source conflicts.

---

## 3. Changes made

### 3.1 Full/core divergence (high severity)

**`direct_collection` — restored to core.**
Not changed. The full record retains `direct_collection` with `is_direct: false`; the core record still has no `direct_collection` slot. What *did* change is the core record's `acquisition_methods[0].acquisition_details`: the clause *"The data are drawn from clinical systems rather than gathered directly from patients for research purposes"* has been **removed** from the core record, so the core `acquisition_methods[0]` text is now byte-identical to the full record's. The core-only content is eliminated; the structured boolean remains full-only.

**`third_party_sharing` — core-only content removed.**
The core record's `data_governance.notes` previously read: *"Access requests are directed to… The dataset is shared beyond the contributing consortium under controlled access, including with trainees provisioned compute on the Bridge2AI AI/ML for Clinical Care Collaborative Cloud."* The second sentence has been **removed**. Core `data_governance.notes` now matches the full record's. The full record retains `third_party_sharing` with `is_shared: true`.

**`splits` — core-only note removed.**
The core record's `notes` previously ended: *"The project also sequesters a holdout test set for external model validation; the core schema provides no split-level slot, so this is recorded under purposes, tasks, and intended_uses."* That sentence has been **removed**. Both records' `notes` now consist solely of the website-banner quotation. The full record retains `splits`.

**`resources` vs `subsets` — left as-is, with disclosure added.**
The core record still carries the nine modalities under `resources`; the full record still carries them under `subsets` with `is_data_split: false` / `is_subpopulation: false` on each. The identifiers remain identical across the two records. This divergence was **not** resolved. What changed is the core `source_caveats`: the bare sentence *"The nine standardized data modalities are carried in `resources` as component datasets"* has been removed, and the identifier-minting caveat extended to read *"…the nine component modality identifiers are minted the same way."* The rationale for leaving the class assignment alone is in §4.1.

### 3.2 Creators (medium severity)

Applied identically to both records. Five of the six `Creator` objects previously used `principal_investigator: {name: …}`. In the reconciled records, only **Eric S. Rosenthal** retains `principal_investigator` — the one person NIH RePORTER names as PI. The other five (Bihorac, Jiang, Strekalova, Rashidi, Kwong) now carry:

- `affiliations` (unchanged),
- a `notes` field naming the person and stating the source: *"…listed on the Bridge2AI CHoRUS Leadership Team slide of the September 2025 AIM-AHEAD Bridge2AI for Clinical Care cohort 2 informational webinar."*,
- a per-object `source_caveats` recording that the bundle names them as leadership-team members, not principal investigators, and that `principal_investigator` is therefore left empty.

The Rosenthal entry gained a `notes` field stating the RePORTER attribution.

The audit's second creators finding — that the bundle does not state these six people created the *dataset* — was addressed in the top-level `source_caveats` of both records, which now include: *"The sources do not state that these six individuals created the dataset; they are named as project leadership."*

### 3.3 `ethical_reviews[0].reviewing_organization` (medium severity)

`reviewing_organization: CHoRUS consortium ethics pillar` has been **removed** from both records. The `review_details` prose is unchanged. The object's `source_caveats` was rewritten to state that the sources do not name a reviewing body and that the field is therefore left empty.

### 3.4 `license_and_use_terms.contact_person` (medium severity)

`contact_person: {name: Jared Houghtaling}` has been **removed** from both records. The `notes` field naming both access-request contacts is unchanged. A `source_caveats` was added: *"The two named contacts are given by the sources as access-request contacts, not as licensing contacts, so neither is recorded in contact_person."* Neither contact is now privileged over the other in a structured field.

### 3.5 `data_governance.accountable_organization` (medium severity)

`accountable_organization: {name: Massachusetts General Hospital}` has been **removed** from both records. MGH's documented role is preserved in `data_governance.notes`, which gained the sentence: *"Massachusetts General Hospital holds the NIH award and hosts the project's program manager."* A `source_caveats` was added recording that no access committee, timeframe, appeal process or accountable organization is described in the sources, and that MGH's role is recorded as award recipient and program-management host rather than asserted as accountable steward.

### 3.6 `addressing_gaps` (low severity, three entries)

Entries 2, 3 and 4 were reworded in both records so that each states what the sources state, and each gained a `source_caveats` disclosing the difference:

| # | Was | Now |
|---|---|---|
| 2 | *"Existing resources lack a diverse, high-resolution, ethically sourced, AI-ready dataset…"* | *"Multi-modal EHR, waveform, imaging, and text data require unified standards to be harmonized, and the project sets out to build the most diverse…"* + caveat: goal, not documented deficiency |
| 3 | *"Sequestered holdout datasets … have been unavailable, limiting marketplace adoption"* | *"The dataset provisions a sequestered holdout test set … which the project describes as aiding marketplace adoption"* + caveat: capability supplied, not prior unavailability |
| 4 | *"Contextual factors … are commonly absent from clinical datasets"* | *"The project ensures that data elements feature appropriate contextual factors…"* + caveat: commitment about CHoRUS data elements, not a claim about clinical datasets generally |

Entry 1 was lightly reworded (*"is a critical first step"* → *"is described as a critical first step"*) to mark it as reported rather than asserted.

### 3.7 `known_limitations` (low severity, two entries)

- **`representativeness_limitation`:** the clause *"rather than to general hospital or ambulatory care"* was removed from `limitation_description`, which now reads *"…so it is specific to acute and critical illness."* A `source_caveats` records that the scope is sourced but its characterization as a representativeness limitation is the record's inference.
- **`temporal_limitation`:** *"rather than prospectively designed measurements"* was removed; the description now reads *"…so the dataset comprises clinical documentation as it was recorded at the contributing hospitals."* A `source_caveats` records that the sources state only "Retrospective data collection".

Both applied identically to full and core.

### 3.8 `known_biases[0]` (low severity)

`bias_type: selection_bias` and the `bias_description` were **kept**. The `source_caveats` was expanded from the previous statement about unmeasured statistics to open with: *"No source names or categorizes any bias in the dataset; the cohort-composition facts are stated by the sources, but their framing as a bias and the assignment of the selection_bias category are this record's own analysis."*

### 3.9 `instances[1].counts` — rounded magnitude (medium severity)

A `source_caveats` was added to the OMOP-rows instance in both records: *"The source states a rounded magnitude, '1.6 Billion rows of EHR OMOP data'; the integer given here is that rounded figure expressed in full and is not an exact count."* The value `1600000000` is unchanged.

### 3.10 Garbled-table attributions (low severity, two entries)

Local `source_caveats` were added to two modality objects in both records — `Nursing flowsheets` (the "OMOP schema with extensions" attribution) and `Waveform telemetry` (the "PhysioNet schema extended" attribution) — each stating that the attribution rests on column order alone in a garbled table extraction. The top-level `source_caveats` in both records was updated to reference both entries rather than only the flowsheet case.

### 3.11 `status` (low severity)

The multi-sentence narrative was condensed in both records to: *"Released under controlled access while assembly continues toward the larger anticipated final dataset."* The release-progress detail it duplicated is retained in `updates.update_details`.

### 3.12 `regulatory_restrictions.confidentiality_level` (medium severity)

`restricted` was **kept**. A `source_caveats` was added to both records: *"The sources describe every modality as 'controlled access' but do not state a confidentiality level; the enum term `restricted` is this record's mapping of that description."*

### 3.13 `conforms_to_standard` — `OTHER` collision (medium severity)

The list is unchanged in both records. A sentence was added to both top-level `source_caveats`: *"The single OTHER term in conforms_to_standard stands for two distinct non-registered standards, the OHNLP note schema and the EDF+/Persyst EEG formats, which the enum cannot distinguish; the prose in conforms_to names both."*

### 3.14 Minor transcription and disclosure edits

- **`instances[3].notes`:** *"23 Tb of waveform data"* now carries *"(unit transcribed as published)"* in both records.
- **`maintainers[0].maintainer_details`:** the typo disclosure was moved from the distant `source_caveats` to the point of use — *"cmccrary@mgh.havard.edu, transcribed exactly as published and apparently containing a typographical error in the domain"* — in both records. The disclosure also remains in `source_caveats`.
- **`external_resources[2]`:** the bridge2ai.org entry now reads *'given in the GitHub organization contact section as "Website: www.bridge2ai.org/chorus" (transcribed as published, without a URL scheme)'*, making the scheme-less form visibly a quotation rather than an inconsistency.
- **Dataset `id`:** both `source_caveats` now note that the identifier is a fragment minted on the attested project URL and does not correspond to a published anchor.
- **Verified-correct omissions:** both `source_caveats` now close with an explicit list — *"No DOI, recommended citation, version identifier, dataset license, consent documentation, file counts, total size, compression, or direct download URL is stated anywhere in the bundle, so those slots are omitted."*

---

## 4. Left as-is

### 4.1 `resources` (core) vs `subsets` (full) — the class divergence

The nine modalities remain in `resources` in the core record and `subsets` in the full record, with identical identifiers across both. The audit flagged this as high severity on two grounds: unnecessary modeling divergence, and one identifier denoting objects of two different classes.

It was not changed. The schema digest supplied to this task describes the full `Dataset` class only; it does not enumerate `CoreDataset`'s slots, so whether `subsets` is declared on `CoreDataset` cannot be established from the material available here. Changing the core record on an assumption about a slot's availability risks a validation failure that is worse than the modeling inconsistency. The divergence is instead disclosed: the core `source_caveats` now records that the modality identifiers are minted on the project URL in the same way as the dataset identifier. This is the least satisfactory outcome in the reconciliation and should be revisited when the core schema is in hand.

### 4.2 `instances[0].counts: 50000`

Retained in both records. The audit rated the source-conflict exposure medium but noted it is transparency-mitigated. The value comes from the tier-2 project documentation, the tier-4 webinar's competing figure (45K+ unique admissions, August 2025) is recorded in the same object's `source_caveats`, and the tier ranking settles the disagreement in the documentation's favor. Both the top-level and object-level caveats state both figures. No change was warranted.

### 4.3 `data_collectors[*].role` free strings

Retained unchanged in both records: `Data contributing site`, `Site data manager`, `Coordinating sub-team`. The schema digest constrains `role` to an enum on `Maintainer` only, not on `DataCollector`, so these are valid. They are record-coined labels, but they summarize collector categories the bundle does describe (14 acquisition centers; site data managers following SOPs; Standards/Data Acquisition/Tooling sub-teams). Replacing them with nothing would lose information the sources support.

### 4.4 `known_biases[0].bias_type: selection_bias`

Retained rather than removed. The underlying cohort-composition facts — 14 contributing hospitals out of 20 academic centers, intensive care settings — are directly sourced, and the bias slot exists to carry exactly this kind of assessment. What was unsupported was presenting the categorization as though a source made it; that is now stated plainly in the object's `source_caveats`.

### 4.5 `regulatory_restrictions.confidentiality_level: restricted`

Retained. The bundle's uniform "Controlled" access marking across all nine modalities supports a non-`unrestricted` value, and `restricted` is the closer of the two candidates to "controlled access with a signed agreement". The judgment is now disclosed rather than silent.

### 4.6 `instances[3].notes` — "23 Tb"

The unit is transcribed exactly as the source publishes it. The audit explicitly noted transcription fidelity is correct here and flagged only the residual reading hazard; that hazard is now addressed by the parenthetical, without altering the quoted figure.

### 4.7 Verified-correct omissions

`doi`, `citation`, `version`, `license`, `collection_consents`, `informed_consent`, `consent_revocations`, `collection_notifications`, `total_size_bytes`, `total_file_count`, `compression` and `download_url` remain absent from both records. The audit confirmed each as correctly omitted. They are now enumerated in both `source_caveats` so that a reader can distinguish a deliberate omission from an oversight.

### 4.8 Slots present in full but not core

`direct_collection`, `third_party_sharing` and `splits` remain full-only, for the same reason as §4.1: the core schema's slot inventory is not available in the supplied digest. The reconciliation resolved the *content* asymmetry (no fact now appears in core that the corresponding full slot does not carry) without being able to resolve the *slot* asymmetry.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 58 | 55 |
| Core-only facts remaining | — | 0 |
| Unsupported role assertions removed | 5 creators, 1 reviewer, 1 contact, 1 accountable org | same |
| New disclosures added (`source_caveats`) | 13 object-level + expanded top-level | 13 object-level + expanded top-level |
| Slot-inventory divergence resolved | no (schema unavailable) | no (schema unavailable) |

Three high-severity core-only content items were eliminated. Eight unsupported or over-scoped structured assertions were removed across both records, each replaced by a caveat explaining the omission. Five inference-as-evidence statements were reworded to track what the sources say. Nine judgment calls that were previously silent — the bias category, the confidentiality enum mapping, the `OTHER` collision, the rounded count, the two garbled-table attributions, the minted identifiers, the creatorship inference, the two limitation framings — are now stated in the record. The one unresolved high-severity finding is the `resources`/`subsets` class divergence, which is documented rather than repaired.