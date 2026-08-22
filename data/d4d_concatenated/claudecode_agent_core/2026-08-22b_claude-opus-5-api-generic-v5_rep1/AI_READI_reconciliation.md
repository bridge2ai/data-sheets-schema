# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-22b_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Audit findings addressed:** 25 (2 high on the core record, 9 medium, 12 low, 3 info)

---

## 1. Summary of outcome

The audit found no fabricated dataset facts and no unsupported external identifiers in either record. Every ORCID and ROR CURIE is transcribed from the FAIRhub `study_description` module; no registry identifier was supplied from outside the bundle. Source conflicts were disclosed and, where the manifest ranks the sources, resolved with the reasoning recorded.

The reconciliation therefore concentrated on three classes of defect:

1. **Structural defects in object-ranged slots** — `Creator` and `DataGovernance` objects placing a `Person` object where the schema digest declares a scalar or does not declare that key at all; `DistributionDate.release_dates` and `ExternalResource.external_resources` given as scalars where the object listing implies a list.
2. **Content placed in a field that does not ask for it** — the core record's use of `notes`, `description`, `instance_type`, `consent_type` and `withdrawal_mechanism` as carriers for content that has its own declared slot.
3. **Author-side inferences presented as source statements** — two enum mappings and one relationship type asserted without a caveat distinguishing them from transcribed facts.

Both records were changed. The core record was changed substantially more than the full record, because most audit findings were core-only.

---

## 2. Changes made to the full record

### 2.1 `creators` — Person object replaced by scalar `id` + scalar name (finding: object-range shape)

Every one of the sixteen `Creator` objects was restructured. Original form:

```yaml
- principal_investigator:
    id: ORCID:0000-0002-7452-1648
    name: Aaron Lee
```

Reconciled form:

```yaml
- id: ORCID:0000-0002-7452-1648
  principal_investigator: Aaron Lee
```

The schema digest declares `id` as `uriorcurie` **on every object below**, and declares `principal_investigator` with range `Person`. The original nested an object with `id` and `name` keys under `principal_investigator`; the reconciled form promotes the ORCID CURIE to the object's own declared `id` slot and leaves the investigator's name as the value of `principal_investigator`. This preserves both facts and puts the CURIE in a slot whose range the digest states explicitly.

### 2.2 `creators[0].affiliations` — dual affiliation reduced to one, conflict moved wholly into the caveat (finding: low, "asserts as fact that Aaron Lee holds both affiliations")

Original: two `Organization` objects (Washington University in St. Louis, University of Washington) under Aaron Lee, with a caveat explaining the conflict.

Reconciled: one `Organization` object (Washington University in St. Louis, `ROR:01yc7t268`), with an expanded `source_caveats` that names the RO-Crate value, its ROR, the tier-three and tier-four sources that agree with it, and states explicitly that the FAIRhub value was recorded "because it is the affiliation the release metadata attaches to this role; the RO-Crate value is not asserted here because no source states that he holds both simultaneously."

The audit was correct that the two-affiliation list encoded a claim neither source makes. The conflict is not lost — it is now stated in the field designed to hold trust annotations rather than in the field that asserts affiliation.

The record-level `source_caveats` was amended in parallel: the sentence "so both attributions are recorded where they apply" became "so both attributions are recorded in the affiliation-level caveats; no source states that the investigator holds both affiliations simultaneously."

### 2.3 `funders[0].grants[0]` — award number moved from `notes` prose into the Grant object (finding: low)

Original:

```yaml
grants:
  - id: https://reporter.nih.gov/project-details/10471118
notes: >-
  The core award is OT2OD032644, "Bridge2AI: Salutogenesis Data Generation Project",
  application 10471118 / project 1OT2OD032644-01, ...
```

Reconciled: the Grant object now carries `name: OT2OD032644` and a `description` holding the award title, application number, project number, awardee, principal investigator, award amount and project period. The `notes` slot on `FundingMechanism` retains only the residual fact it alone can hold — the two additional NIH grants reported by the protocol publication.

The audit observed that "the grant's own identifier (award number OT2OD032644) … appears only in `notes` prose rather than in any identifier position." It now appears as the Grant's name. The resolver URL is retained as `id` because no prefix for NIH RePORTER project records exists in the digest; a sentence to that effect was added to `funders[0].source_caveats`.

### 2.4 `data_governance.committee_contact` — Person object replaced by scalar (finding: v4 rule, scalar-ranged slot)

Original:

```yaml
committee_contact:
  id: ORCID:0000-0002-7452-1648
  name: Aaron Lee
```

Reconciled:

```yaml
committee_contact: Aaron Lee (ORCID:0000-0002-7452-1648)
```

`accountable_organization` was left as an `Organization` object, because the digest declares that range explicitly (`accountable_organization`: Organization).

### 2.5 `sensitive_elements[1].sensitive_elements_present` — boolean added (finding: low)

The second `SensitiveElement` object omitted the boolean while its sibling carried it. `sensitive_elements_present: false` was added, with a closing sentence in `sensitivity_details` explaining the value: "The boolean is false because these elements are absent from the release this datasheet describes." The object describes controlled-access variables that are *not* in this release, so `false` is the correct reading and the asymmetry the audit noted is resolved.

### 2.6 `human_subject_research.regulatory_compliance` — split into three, FDA/DMC duplication removed from `regulatory_restrictions` (finding: low)

Original: one long `regulatory_compliance` string containing HIPAA, NIH GDS, FDA/DMC and ClinicalTrials.gov facts, with the FDA/DMC sentence *also* appearing at the end of `regulatory_restrictions.other_compliance`.

Reconciled: `regulatory_compliance` is now three list entries — HIPAA/GDS, FDA and DMC status, ClinicalTrials.gov registration — and the duplicated FDA/DMC sentence has been deleted from `regulatory_restrictions.other_compliance`, which now ends at the storage restriction. The audit's point that "the FDA/DMC facts belong to the oversight module … not the export-control class" is accepted.

### 2.7 `regulatory_restrictions.confidentiality_level` and `license_and_use_terms.data_use_permission` — caveats added for author-side mappings (findings: low, two)

Neither enum value changed. Both caveats were rewritten to open with an explicit statement that the value is a mapping rather than a source statement:

- `regulatory_restrictions.source_caveats` now begins "The value of confidentiality_level is a mapping performed for this record rather than a term any source states" and states that neither `HL7:2N (normal)` nor `PublicDownloadSelfAttestationRequired` is an enum term.
- `license_and_use_terms.source_caveats` was **added** — the original had none. It states that no source names a data-use-permission code, quotes the two access statements the mapping rests on, and notes that the license permits commercial use so no commercial restriction is implied.

The audit flagged that the confidentiality mapping was caveated but the data-use mapping was not; that asymmetry is now closed.

### 2.8 `related_datasets` — `replaces` removed, `target_dataset` given an identifier (findings: low, two)

Original three entries: `is_new_version_of` → `10.60775/fairhub.2`; `replaces` → `10.60775/fairhub.2`; `is_source_of` → a prose sentence describing FAIRhub dataset 4.

Reconciled two entries:

- `is_new_version_of` → `10.60775/fairhub.2`, with a `notes` carrying the participant count and the no-longer-accessible statement.
- `is_source_of` → `https://fairhub.io/datasets/4`, with a `notes` recording the `"child": 4` API field, the landing-page sentence, and the fact that no DOI for the subset appears in the sources.

The `replaces` entry was deleted. The audit was right that it is an inference from "no longer accessible" and that no source uses replacement language; `is_new_version_of` is directly supported and carries the same information.

### 2.9 `known_biases[2].affected_subsets` — prose replaced by a subset reference (finding: low)

Original: a single prose string giving aggregate counts.

Reconciled: `affected_subsets: [doi:10.60775/fairhub.3#split-train]`, referencing the DataSubset entity the full record already declares, with the aggregate counts and the balancing contrast moved into a new sibling `notes` field.

### 2.10 `distribution_dates[].release_dates` and `external_resources[].external_resources` — scalars converted to lists

Both slots were given as bare strings in the original. Each is now a single-item list. This is a shape correction rather than a content change; no wording was altered.

### 2.11 `description`, `notes`, `source_caveats` — three amendments

- `description`: gained the exact byte count alongside the TB figure, and a closing sentence on the recommended split (previously present only in `splits`).
- `notes`: unchanged in content.
- `source_caveats`: the closing sentence on the release-scope inconsistency was expanded. The audit noted that "No caveat … addresses the FAIRhub statement that release 3.0.0 covers data 'up through the end of the second year' against the collection end date of 2025-05-01 and the three-tranche changelog, beyond noting the inconsistency exists." The reconciled caveat now names both tier-one/tier-two sources that make the second-year statement, quotes it, sets it against the three changelog tranches by their labels and counts, states which value is recorded, and states plainly that the year-labelling "is not resolvable from the bundle."

---

## 3. Changes made to the core record

### 3.1 `distributions` — **left as-is** (finding: high, two entries)

The audit's most severe finding was that `distributions` "does not exist in the supplied schema digest for the Dataset/CoreDataset class," and that ten objects carrying the entire per-datatype file inventory sit under it.

**This was not changed.** The slot and all ten objects remain in the reconciled core record, byte counts and paths intact.

The reason is the constraint this report operates under: I must not state that a slot is undeclared without the schema digest supporting me. The digest supplied to me enumerates the 98 slots of the **`Dataset`** class and states in its own header that it is "Derived from `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`" — the *full* schema. It does not enumerate `CoreDataset`'s slots. `CoreDataset` appears in the digest only once, in the `conforms_to_class` description, as the value that class expects. The digest therefore cannot tell me whether `CoreDataset` declares `distributions`, and the audit's own finding concedes this ambiguity: "If CoreDataset genuinely declares this slot it is outside the digest and cannot be verified."

Removing ten objects holding every byte count and directory path in the record on the strength of a digest that does not scope the class in question would destroy verified content to satisfy an unverified structural claim. The safer action was to leave the content and record the uncertainty here. If validation against `data_sheets_schema_core_all.yaml` rejects `distributions`, the correct repair is to move these objects into `file_collections` — which the full record already demonstrates, with the same paths, byte counts, file counts and standards.

### 3.2 `distributions[9].notes` — release totals added (finding: high, `total_file_count`/`total_size_bytes`)

The audit found the core record dropped the scalar `total_file_count` and `total_size_bytes` that the full record populates. Two things were done:

- The root-metadata distribution entry's `notes` gained a closing sentence: "The whole release comprises 356,343 files totaling 3,815,969,779,678 bytes (approximately 3.82 TB)."
- `description` gained the exact byte figure alongside the TB figure.

The scalar slots themselves were **not** added, for the same scoping reason as §3.1: the digest does not tell me whether `CoreDataset` declares `total_file_count` or `total_size_bytes`. The figures are now stated twice in the record rather than once, so no fact is lost, but they remain in prose. This is a partial remedy and is recorded as such.

### 3.3 `notes` — citation removed from `notes` (finding: medium)

The original core `notes` opened with "Recommended citation: AI-READI Consortium. (2025). Flagship Dataset…". That sentence has been **deleted**.

The audit was correct that `notes` is reserved for residual content after every fitting slot is used. The `citation` slot was not added, again because the digest does not scope `CoreDataset`. The citation is recoverable from the full record, which carries it in `citation`. The core `notes` now opens with the repository-review statement and closes with the third-party-sharing summary described in §3.6.

### 3.4 `description` — split composition and variable inventory absorbed (findings: medium, `subsets`/`splits` and `variables`)

The core record omits `subsets`, `splits` and `variables`, which the full record populates as three DataSubset objects, one Splits object and 35 VariableMetadata objects. Rather than add slots whose availability on `CoreDataset` I cannot verify, the content was folded into `description`, which every version of both records declares:

- **Split composition**: the original core `description` closed with one sentence noting a 70/15/15 split. It now gives the per-partition counts by race/ethnicity, sex, diabetes status and mean age for all three partitions — the full contents of the README table.
- **Variables**: a new closing passage names the variables the full record enumerates, with units and reference ranges: HbA1c (4.0–6.0 %), glucose (62–125 mg/dL), insulin, C-peptide, NT-pro-BNP, troponin-T, hs-CRP, the lipid panel, creatinine, BUN, urine albumin and creatinine, continuous glucose, MoCA total (0–30), logMAR acuity, Mars log CS, blood pressures, heart rate, BMI, waist-hip ratio, monofilament response, and the wearable and environmental measures.

This is a mitigation, not a repair. The audit's characterization stands: variable-level structure is absent from the core record and the content now survives only as prose.

### 3.5 `instances[0]` — relationship content moved out of `instance_type` (finding: medium)

The audit found that the full record's `Relationships` object had been folded into the core record's `instances[0].instance_type`, "which the digest describes as the instance type field, not a relationship field."

Reconciled: `instance_type` was truncated back to the description of what an instance *is* — matching the full record's wording exactly. The relationship content (one project, one visit per participant, linkage by participant directory identifier and participants.tsv) was moved into `instances[0].notes`, joining the earlier-release counts already there. `notes` is a poorer home than a `Relationships` object, but a better one than a type field.

### 3.6 `notes` — third-party sharing added (finding: medium)

The core record omits `third_party_sharing`, which the full record carries with `is_shared: true`. A closing sentence was added to the core `notes` recording the onward-conveyance restriction and the model-vendor prohibition. The boolean fact — that the dataset *is* distributed to third parties — is still not machine-readable in the core record; the audit's finding stands in that respect.

### 3.7 `informed_consent[0]` — notification content moved from `consent_type` to `notes` (finding: medium)

The audit found three distinct full-record slots (`collection_consents`, `consent_revocations`, `collection_notifications`) collapsed into `informed_consent[0]`, with the notification narrative appended to `consent_type`.

Reconciled: `consent_type` now carries only consent-mechanism content (written consent, e-signature or in-person, required before any protocol element, the remote-consent route, the no-internet fallback). The notification narrative — contact pools, personalized letters and emails, QR codes, the REDCap interface, FAQ, call-back option, screening survey — was moved to a new `informed_consent[0].notes` field.

The revocation limitation remains in `withdrawal_mechanism` and the reuse-scope statement remains in `consent_scope`. Both readings are defensible: withdrawal mechanism is what `ConsentRevocation` describes, and consent scope is what the reuse limitation constrains. Those two parts of the finding were left as-is.

### 3.8 `known_biases[2].affected_subsets` — prose retained, reworded (finding: low, adapted)

In the full record this became a subset reference (§2.9). The core record declares no subsets, so no reference target exists. The prose was instead rewritten to name what it affects: "The release as a whole, most visibly the recommended training partition, which was not balanced," followed by the counts and the balancing contrast. It remains prose.

### 3.9 Changes mirroring the full record

The following were applied identically to both records and are described in §2: `creators` restructuring (§2.1), Aaron Lee's affiliation and caveat (§2.2), the Grant object (§2.3), `committee_contact` (§2.4), `sensitive_elements[1]` boolean (§2.5), the `regulatory_compliance` split and FDA/DMC de-duplication (§2.6), both enum mapping caveats (§2.7), `related_datasets` (§2.8), the `release_dates` and `external_resources` list conversions (§2.10), and the expanded record-level `source_caveats` (§2.11).

---

## 4. Findings left as-is, with reasons

| Finding | Severity | Disposition |
|---|---|---|
| `distributions` slot undeclared | high | **Left as-is.** Digest scopes `Dataset`, not `CoreDataset`; cannot verify. See §3.1. |
| `distributions[].bytes/path/format` in undeclared class | high | **Left as-is**, consequence of the above. |
| `total_file_count` / `total_size_bytes` absent from core | high | **Partially addressed** (§3.2): figures added to prose in two places; scalar slots not added. |
| `citation` absent from core | medium | **Partially addressed** (§3.3): removed from `notes`; slot not added. |
| `subsets` / `splits` absent from core | medium | **Partially addressed** (§3.4): full split table absorbed into `description`. |
| `variables` absent from core | medium | **Partially addressed** (§3.4): variable inventory with units and ranges absorbed into `description`. |
| `relationships` absent from core | medium | **Partially addressed** (§3.5): moved from `instance_type` to `notes`. |
| `collection_consents` / `consent_revocations` / `collection_notifications` collapsed | medium | **Partially addressed** (§3.7): notification content separated into `notes`; revocation and scope left in place. |
| `participant_privacy` / `participant_compensation` absent from core | medium | **Left as-is.** Cannot verify these slots on `CoreDataset`; the re-identification fragment already survives in `is_deidentified.deidentification_details` and `future_use_impacts[0]`. The USD 200 stipend and the returned-results schedule are absent from the core record. |
| `third_party_sharing` absent from core | medium | **Partially addressed** (§3.6): substance added to `notes`; boolean not machine-readable. |
| `funders[0].grants[0].id` is a resolver URL | low | **Left as-is** as an identifier; award number promoted to `name` (§2.3) and the absence of an NIH RePORTER prefix noted in the caveat. |
| `confidentiality_level: restricted` is an inference | low | **Value left as-is**; caveat strengthened (§2.7). |
| `data_use_permission: disease_specific_research` is an inference | low | **Value left as-is**; caveat added (§2.7). |
| `at_risk_groups_included: false` in tension with `special_protections` | low | **Value left as-is.** `special_protections` was split into three list entries and the first now states explicitly that no minors, pregnant women, neonates or fetuses are enrolled and that prisoners are not a target population. A `source_caveats` was added explaining the boolean and addressing the prisoner questions. |
| `conforms_to_schema` points at the full schema URI in the core record | low | **Left as-is.** The digest states this slot is "normally `https://w3id.org/bridge2ai/data-sheets-schema`" and describes it as a statement about the record's schema family, not the file path. `conforms_to_class: CoreDataset` is correct and distinguishes the two records. |
| `instances[0].data_topic` narrows a multimodal dataset to one topic | low | **Left as-is.** `data_topic` is single-valued on `Instance`; `B2AI_TOPIC:43` (Diabetes) is the dataset's stated subject. `data_substrate` remains omitted — the digest instructs omission where no single term fits, and the dataset spans DICOM, WFDB, CSV and TSV substrates with no single correct choice. |
| `subsets[].id` and `file_collections[].id` minted fragments | low | **Left as-is.** These label parts of this dataset with no external referent, so minting is permitted, and each is a fragment on the attested DOI. |
| `source_caveats` coverage (info) | info | **Addressed** (§2.11): the release-scope inconsistency now has a full caveat. |
| `conforms_to_standard` enum members (info) | info | No defect; unchanged. |
| `issued` RFC 3339 offset (info) | info | No defect; unchanged. |
| Core header block (info) | info | No defect; unchanged. All fourteen lines verbatim, including `# Sources:` and `# Phase 4 reconciliation: completed`. |

---

## 5. Referent consistency

Both records describe the same referent throughout: **FAIRhub dataset 3, release 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, DOI 10.60775/fairhub.3**, published 2025-11-17, comprising 2,280 participants and 356,343 files. Facts about the *study* (target enrollment of 4,000, the year-four longitudinal arm, the biorepository) are recorded where the schema asks about study conduct — `sampling_strategies`, `collection_timeframes`, `human_subject_research` — and are marked as study-level rather than release-level. Facts about *other releases* are confined to `distribution_dates`, `version_access` and `related_datasets`. This choice is unchanged by reconciliation.

---

## 6. Residual risk

The single largest residual risk is §3.1. If `CoreDataset` does not declare `distributions`, the core record will fail validation and the remedy is mechanical: rename the slot to `file_collections`, add an `id` to each object (fragments on the DOI, as the full record does), rename `bytes` to `total_bytes` and `path` stays as `path`, and lift the file counts out of `notes` into `file_count`. The full record contains a working template for all ten collections.

The secondary residual risk is that six declared full-record slots — `citation`, `subsets`, `splits`, `variables`, `relationships`, `participant_compensation`, `participant_privacy`, `third_party_sharing` — have no structured counterpart in the core record. Where the content was recoverable it now sits in `description` or `notes`; where it was not (the USD 200 stipend, the returned-results schedule, the 35 variable objects as objects) it is available only from the full record.