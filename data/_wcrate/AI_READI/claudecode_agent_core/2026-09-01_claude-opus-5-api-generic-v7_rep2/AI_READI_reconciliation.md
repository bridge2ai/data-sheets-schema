# Reconciliation Report — AI_READI

**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep2`
**Records:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Audit findings addressed:** 23 (2 high/medium-severity structural, 21 medium and low)

---

## 1. Summary of the audit

The Phase 3 audit found the record broadly well-grounded: counts, sizes, dates, license terms, device inventory, split table and standards mapping all trace to attested passages in the declared bundle, and the three declared source conflicts were already resolved in favour of the higher-ranked source with the alternative recorded. No fabricated dataset facts and no prior-D4D contamination were found.

The defects clustered in four areas:

1. **`creators`** — one Creator object collapsing several distinct entities, carrying ten institutional RORs drawn from sponsor/collaborator/official rosters rather than from any statement about dataset authorship, plus source commentary in `notes`.
2. **`data_governance`** — a synthesized committee name and an inferred committee contact.
3. **Interpretive enum and boolean values** — `hipaa_compliant`, `is_representative`, `was_inferred_derived`, `data_topic`, and `RO_CRATE` in `conforms_to_standard`.
4. **Structural minor issues** — an unreferenced minted fragment identifier with a derived file count, inferred relationship types, and source commentary placed inline rather than in `source_caveats`.

---

## 2. Changes made

Every change below was applied identically to both records where the slot appears in both.

### 2.1 `creators` — split into two entities, affiliations pruned (findings 1, 2, 3)

**Was:** a single Creator object with `principal_investigator` as an object (`{id: ORCID:…, name: Aaron Y. Lee}`), ten `affiliations` entries with ROR CURIEs, a `notes` field explaining the assembly, and a `source_caveats`.

**Now:** two Creator objects.

- The first carries only `affiliations: [{name: AI-READI Consortium}]` — the single organizational creator FAIRhub actually records (`creatorName: "AI-READI Consortium", nameType: "Organizational"`), with a `source_caveats` noting that no source supplies an organizational identifier for the consortium, so none is asserted.
- The second carries `principal_investigator: Aaron Y. Lee` and a single affiliation, Washington University in St. Louis (`ROR:01yc7t268`) — the affiliation FAIRhub gives for him. Its `source_caveats` records the tier-1 disagreement with the RO-Crate's "Department of Ophthalmology, University of Washington" rendering.

**Nine RORs removed:** University of Washington, University of Alabama at Birmingham, UC San Diego, Johns Hopkins, OHSU, Stanford, California Medical Innovations Institute, University of Utah, University of Massachusetts Lowell. These are study sponsors, collaborators, and affiliations of individual overall officials — the bundle never attaches them to the dataset's creator. Utah and UMass Lowell appeared only as affiliations of two named officials (Contreras, Evans).

**`notes` rewritten:** the explanatory prose ("The creator of record is the AI-READI Consortium…") was trust annotation about sibling slots; it moved to `source_caveats` on the first object. The surviving `notes` on the second object carries only the ORCID identifier as a fact.

**Also fixed (not in the audit findings, found during reconciliation):** `principal_investigator` was an object in the original but the schema digest declares its range as `Person`; in the reconciled records it is written as a scalar name string, matching how the schema digest lists `principal_investigator: Person` alongside the v4 rule that a scalar-ranged slot takes the identifier or name rather than an object. This was applied consistently in both records.

### 2.2 `data_governance.committee_name` — synthesized name replaced (finding 4)

Changed from `AI-READI Data Access Committee` to `AI-READI Consortium`. The RO-Crate (tier 1) records `dataGovernanceCommittee: "AI-READI Consortium"`; the compound string was not stated by any source. The BMJ protocol's unnamed "Data Access Committee" is now recorded in `notes` and in `access_review_process` as prose rather than as the committee's name.

### 2.3 `data_governance.committee_contact` — removed (finding 5)

The whole `committee_contact` key (Aaron Y. Lee with ORCID) is gone from both records. He is attested as study PI, responsible party and central study contact, but no source designates him as contact for the access or governance committee. A new sentence opens `data_governance.source_caveats`: "No contact person is asserted for the governance committee: no source in the bundle designates one." Contact routes that *are* attested (`https://aireadi.org/contact`, `contact@aireadi.org`, the docs contact page) remain in `notes`.

### 2.4 `conforms_to_standard` — `RO_CRATE` removed (finding 6)

Removed from the dataset-level list in both records; the list is now `[CDS, DICOM, OMOP_CDM, WFDB, OPEN_MHEALTH, ESDS]`. RO-Crate is a metadata-packaging profile describing the dataset, not a standard the dataset's content follows. The per-collection `conforms_to_standard` lists were already free of it and were not touched.

### 2.5 Root metadata file collection — removed as a collection, retained as prose (findings 7, 8)

The eleventh `file_collections` entry (`ark:59853/rocrate-b2ai-aireadi-release-3-0-0#root-metadata`) is gone from the full record, and the corresponding eleventh `distributions` entry is gone from the core record. Two grounds: the minted fragment was referenced by nothing else in the record, and its `file_count: 9` was derived by counting `metadataFileList` entries the bundle never totals.

The content was not discarded. The nine filenames and the note that `participants.tsv` carries the split now appear in the `notes` slot of both records. `file_collections` / `distributions` now hold nine entries each — the nine data-type subcrates, each with an ARK the RO-Crate itself supplies.

### 2.6 `instances[0].data_topic` — removed (finding 9)

`B2AI_TOPIC:43` (Diabetes) is gone. The bundle supplies no topic classification for instances, and a single disease term poorly represents an instance the record itself describes as spanning survey, clinical, imaging, waveform, wearable and environmental data. A new `source_caveats` on the instance records that neither a topic nor a substrate term is asserted and why.

### 2.7 `related_datasets` — relationship types corrected (finding 11)

The two publication entries changed from `is_described_by` to `is_documented_by`, and each gained a `source_caveats` stating that no source types the relation and that the chosen term is the closest available rather than an attested one. The RO-Crate lists these under `associatedPublication`; FAIRhub's `IsDocumentedBy` relations point at `docs.aireadi.org` and `aireadi.org`, not at the publications. The two `is_new_version_of` entries were left unchanged — the FAIRhub versions list supports them directly.

### 2.8 `is_deidentified` — merged narrative split by source tier (finding 12)

`method` previously fused the FAIRhub statement and the Nature Metabolism Safe Harbor statement into one procedure. Now:

- `method` carries only the tier-1 FAIRhub statement (no identifiers collected, so no active de-identification necessary; HIPAA check performed).
- `deidentification_details` carries the FAIRhub flags, the RO-Crate `deidentified: true`, and — separately attributed — the tier-3 Nature Metabolism Safe Harbor statement as a quotation.
- `source_caveats` now names the tension explicitly and states which slot holds which tier.
- `identifiers_removed` dropped the phrase "per the HIPAA Safe Harbor method", which was the same merge in miniature.

`participant_privacy[0].anonymization_method` was correspondingly trimmed of "by the Safe Harbor method".

### 2.9 `sampling_strategies[0].is_representative` — removed (finding 13)

The `is_representative: false` boolean is gone. `why_not_representative` is retained, since the design rationale for deliberate balancing rather than population-mirroring is directly attested. `source_caveats` now opens: "No representativeness determination is asserted: no source in the bundle states one."

### 2.10 `regulatory_restrictions.hipaa_compliant` — removed (finding 14)

The `compliant` enum value is gone from both records. What the sources actually state — no PHI in the release, `deIdentHIPAA: true`, not FDA-regulated — is now in `other_compliance`, and a new `source_caveats` explains the omission.

### 2.11 `acquisition_methods[0].was_inferred_derived` — removed (finding 15)

The `false` value is gone. The healthsheet passage it drew on distinguishes only directly-observed from subject-reported acquisition and does not deny derivation, while the record's own `variables` slot documents derived values (BMI, waist-hip ratio, log CS). A new `source_caveats` on the object records both points. The three remaining booleans (`was_directly_observed`, `was_reported_by_subjects`, `was_validated_verified`) are directly attested and were kept.

### 2.12 `total_size_bytes` provenance noted (finding 16)

The value is unchanged (`3815969779678`, the FAIRhub API `data.size` field). A closing sentence was added to the top-level `source_caveats` of both records stating that the figure comes from the API rather than being summed from the per-collection `total_bytes` values, which cover the nine subcrates but not the root metadata files.

### 2.13 `human_subject_research.ethics_review_board` — conflict moved to `source_caveats` (finding 17)

The slot value previously presented the naming conflict inline ("The RO-Crate metadata names the reviewing body 'Washington University IRB' with a contact point of…"). It now states the body and its contact details plainly. A new `source_caveats` on `human_subject_research` carries the conflict, matching how the sibling `ethical_reviews[0]` object already handled it.

### 2.14 `external_resources[5].source_caveats` — inference removed (finding 11 in the low group)

The caveat previously asserted that the BMJ citation was "the University of Washington IRB protocol number rather than a trial registration" — the record's own judgment that a source erred. It now states the observable fact: that the BMJ Open publication gives the string "Clinicaltrials. org approval number STUDY00016228", and that this is the same string the same publication and the RO-Crate give as the IRB protocol number. The reader can draw the conclusion; the record no longer draws it for them.

### 2.15 Shape corrections found during reconciliation

Two multivalued slots were carrying scalars in both original records and were converted to lists:

- `distribution_dates[*].release_dates` — each object's `release_dates` is now a one-item list.
- `external_resources[*].external_resources` — each object's value is now a one-item list.

These were not audit findings but are defects under the schema digest's multivalued declarations, and correcting them was necessary for validation.

---

## 3. Findings left as-is

### 3.1 `publisher` as a resolver URL (finding 10, low)

`publisher: https://fairhub.io/` is unchanged in both records. The slot's declared range is `uriorcurie`; FAIRhub has no declared prefix in the schema, so a URL is the permitted fallback rather than a defect. The audit itself characterized the plain name as "weaker" only in a stylistic sense. Left as-is.

### 3.2 Confirmed-deliberate omissions (findings 18–23, all low)

Six findings were confirmations rather than defects, and nothing changed for any of them:

- **`errata`** — omitted. The healthsheet erratum question has an empty response, which is absence of information rather than an assertion of none.
- **`existing_uses`** — omitted. The healthsheet answers "No" to prior use, but `ExistingUse` has no field that carries a negative.
- **`use_repository`** — omitted, same reasoning.
- **`annotation_analyses`, `labeling_strategies`, `machine_annotation_tools`, `imputation_protocols`** — all omitted, all backed by repeated "N/A - no labels are provided" answers and `rai:dataAnnotationProtocol: "N/A - no labels are provided"`.
- **`compression`** — omitted. The FAIRhub `format` list contains no archive or compression media type.

Each of these remains absent from both records.

### 3.3 No shape violations to fix

The audit found none, and the reconciliation confirmed: enum values all drawn from permitted sets, `access_urls` carrying URLs in its `uri`-ranged slot, `doi` carrying the bare anchored form, both datetime slots carrying UTC offsets, all `uriorcurie` slots using CURIEs where a prefix is declared. The two list-shape corrections in §2.15 were outside the audit's scope but were the only structural problems found.

---

## 4. Net effect

| | Full | Core |
|---|---|---|
| Slots before | 76 | 72 |
| Slots after | 76 | 72 |
| Entries removed | 1 file collection, 1 governance sub-key, 1 instance sub-key, 1 enum member, 3 booleans/enums, 9 affiliations | same, projected |
| Entries added | 1 Creator object, 5 `source_caveats` | same, projected |

No top-level slot was added or removed in either record; the changes are all within objects. Both records validated after reconciliation. The core record remains a strict projection of the full record — every reconciled value in the core is identical to its counterpart in the full record, and the `# Phase 4 reconciliation: completed` line was added to the core header only after Phase 4 ran.