```markdown
# VOICE — Phase 4 Reconciliation Report

Version label: `2026-08-20b_claude-opus-5-api-generic-v5_rep2`
Arm: BASELINE (input documents only)
Records reconciled: `VOICE_d4d.yaml` (full, class `Dataset`) and `VOICE_d4d_core.yaml` (core, class `CoreDataset`)

---

## 1. Scope of this reconciliation

The Phase 3 audit returned 24 findings across three broad classes:

1. **Core-record divergence** — content present in the core record that the full record did not state, or content stated differently in the two records.
2. **Schema-shape defects** — objects populated with values of the wrong kind, or slots not attested in the supplied `Dataset` digest.
3. **Under-recorded caveats** — deliberate omissions and loose term choices that were correct but undocumented.

Phase 4 treated the full record as the reference and the core record as a strict projection of it. Where the two disagreed, the correction was applied to whichever record was wrong on the evidence, and then propagated so the pair agrees.

---

## 2. Changes applied to both records

### 2.1 Creator roles (audit finding: `creators[*].principal_investigator`, medium)

**Found:** All twenty `Creator` objects placed the named individual in the `principal_investigator` field, though the declared bundle names only Yael Bensoussan and Olivier Elemento as co-principal investigators. Isaac Bevers (library developer) and Micah Boyer (no stated leadership role) were among those misdescribed.

**Changed:** Only the two attested co-PIs retain `principal_investigator`. The remaining eighteen creators now carry their affiliation in `affiliations`, their CRediT roles in `credit_roles` where the bundle supports one, and their name plus stated role in `notes` — for example `Anais Rameau, co-lead of the data acquisition module.` and `Isaac Bevers, developer of the b2aiprep preprocessing library.` Both records were changed identically.

**Cost acknowledged:** eighteen individuals are now named only in free text. The `Person` object is the schema's place for a name, and moving these names into `notes` trades one defect for a weaker one. The alternative — asserting a PI role the bundle contradicts — was judged worse. A caveat in `source_caveats` records the reasoning.

### 2.2 Version DOI as record identifier (audit finding: `id`, medium)

**Found:** `id: doi:10.13026/8xbn-nq66` is the version-specific DOI for 3.1.0, while `related_datasets` declares `is_version_of` against the concept DOI `10.13026/37yb-1t42`. Defensible, but undocumented.

**Changed:** `source_caveats` in both records now states that the identifier is the version-specific DOI because the record describes that specific release, and points to where the concept DOI is recorded (`related_datasets` and `version_access.latest_version_doi`). The `id` value itself is unchanged.

### 2.3 Ontology term choices for the participant instance (audit findings: `instances[0].data_topic`, `instances[0].data_substrate`, low)

**Found:** `B2AI_TOPIC:25` (Phenotype) was one of several defensible choices; `B2AI_SUBSTRATE:41` (Tab-separated values) describes the storage format rather than the participant.

**Changed:** Both values are unchanged. A `source_caveats` field was added to `instances[0]` in both records recording that Phenotype was chosen as the closest single term with Demographics and Voice equally applicable, and that the substrate value records the form in which the participant record is realized in the release rather than a property of the participant.

### 2.4 Partial variable list (audit finding: `variables[*]`, low)

**Found:** Nineteen `VariableMetadata` entries against a far larger released column set, with no flag that the list is a selection.

**Changed:** The dataset-level `source_caveats` in both records now states that the variables list is representative rather than complete, and names the per-file JSON data dictionaries as the authoritative column-level documentation. The nineteen entries are unchanged. (The core schema carries no `variables` slot, so the caveat appears in the core record for consistency of the shared caveat block only.)

### 2.5 Language scalar vs IRB eligibility (audit finding: `language`, low)

**Found:** `language: en` is right for the released data but sits against IRB text admitting English *or* Spanish speakers.

**Changed:** A caveat was added to both records noting that the released cohort is English-only while the IRB criteria admit Spanish and Spanish protocols were under development.

### 2.6 `conforms_to_standard` scope (audit finding, low)

**Found:** Only BIDS declared, though the consortium also publishes FHIR profiles.

**Changed:** The value is unchanged. A caveat records that the FHIR profiles are a consortium output rather than a standard the released content follows, which is why they appear only in `external_resources`.

### 2.7 License tier scope (audit finding: `license`, low)

**Found:** The scalar names only the registered-access license, though the record's referent spans both access tiers.

**Changed:** A caveat records that the scalar governs the features-only tier and points to `license_and_use_terms` and `data_governance` for the controlled-access instruments.

### 2.8 Collection timeframe vs feasibility-study window (audit finding, low)

**Found:** The 5 June – 28 July 2023 window belongs to the feasibility study, not dataset collection; the distinction was implicit.

**Changed:** `collection_timeframes[0].source_caveats` in both records now states explicitly that the dated window recorded elsewhere in the datasheet belongs to the separate feasibility study.

### 2.9 Affiliation identifiers (audit finding, medium)

**Found:** Every `Organization` carries `name` only, with no `id`.

**Changed:** No values changed — the bundle supplies no registry identifiers and inventing them is prohibited under the evidence boundary. A caveat now records the omission and its reason, so a reader can tell deliberate restraint from oversight.

### 2.10 File-collection record counts (audit finding, medium)

**Found:** Per-feature record counts sat only in `instances[1].notes`, not on the collection they describe; `total_bytes` and `total_size_bytes` absent.

**Changed (full record only):** `file_collections[0].notes` now repeats the per-feature counts against the file names they belong to and states that the bundle gives no byte sizes, which is why `total_bytes` and `total_size_bytes` are omitted. The counts in `instances[1].notes` remain.

---

## 3. Changes applied to the core record only

These are the Phase-4 divergence corrections. In each case the core record was brought into line with the full record.

### 3.1 `distributions` slot removed (audit findings, two entries, high)

**Found:** The core record carried a `distributions` slot with sub-keys `format`, `media_type`, `path`, `conforms_to`, `conforms_to_standard`. That slot is not in the supplied `Dataset` digest. Two of its three entries also carried unsupported values: `format: ZIP` / `media_type: application/zip` for the features folder (no source states a zip archive) and `format: JSON` / `media_type: application/json` for the metadata folder (which the bundle describes as a Parquet file plus dictionary). A third defect: `conforms_to_standard: BIDS` was written as a scalar where the digest declares the slot multivalued.

**Changed:** The `distributions` slot is gone from the core record. Its recoverable content — the Parquet file names, the phenotype folder layout, the BIDS conformance of the phenotype tables, the metadata folder contents — was folded into the `notes` of the corresponding `distribution_formats` entries, which both records already carried. No zip archive and no JSON distribution format is now asserted anywhere.

### 3.2 `data_collectors[*].role` aligned (audit finding, high)

**Found:** The full record used `researcher`, `academic_institution`, `third_party`; the core record used free prose `Site research teams`, `Clinicians and physicians`, `Hospital staff` for the same three collectors. A direct contradiction between the paired records.

**Changed:** The core record now carries the same three enum-style values as the full record. The descriptive text was already present in `collector_details` in both, so nothing was lost.

### 3.3 Inferred IRB contact person removed (audit finding, high)

**Found:** `ethical_reviews[3].contact_person: {name: Yael Bensoussan}` in the core record. The bundle names Bensoussan as corresponding author of the feasibility publication, not as IRB contact for the review. Content the full record did not state.

**Changed:** `contact_person` removed from that entry. The two records' `ethical_reviews` blocks are now identical.

### 3.4 Person objects holding an office mailbox removed (audit findings, two entries, medium)

**Found:** `data_governance.committee_contact: {email: DACO@b2ai-voice.org}` and `regulatory_restrictions.governance_committee_contact: {email: DACO@b2ai-voice.org}` — `Person`-ranged fields populated with a shared mailbox and no name, both absent from the full record.

**Changed:** Both removed from the core record. In their place, both records gained a `notes` field on the parent object stating that the bundle names the DACO mailbox as the contact point but names no individual, which is why the person-ranged field is omitted. The address itself remains in `access_review_process` prose in both records, where it was already.

### 3.5 `subsets` vs `resources` (audit finding, medium)

**Found:** The full record placed the five disease cohorts in `subsets` (`DataSubset`, `is_subpopulation: true`, `is_data_split: false`); the core record placed them in `resources` (`Dataset`). Different slots, different semantics — a cohort is a subpopulation, not a component sub-resource.

**Changed:** The core record no longer carries `resources`. Because the core schema has no `subsets` slot, the five cohort descriptions were moved into core `notes`, prefaced by an explicit statement that they are subpopulations of this dataset rather than separate component resources. The full record's `subsets` block is unchanged. The core record no longer makes the sub-resource claim.

### 3.6 `other_tasks` and `raw_sources` retained by promoting them to the full record

**Found:** The core record introduced `other_tasks` (pediatric developmental norms and early screening) and `raw_sources` (raw WAV audio plus Synapse URL) that the full record did not carry — a Phase-4 violation in both cases.

**Changed:** Rather than delete supportable content, both slots were added to the **full** record and the divergence closed in that direction. `other_tasks` now appears in both records with the same single entry. `raw_sources` now appears in both with two entries — the WAV recordings via Synapse, and the REDCap/ReproSchema responses via the published instrument repository. Both slots are in the `Dataset` digest and both entries are supported by the bundle, so promotion was the better repair.

---

## 4. Findings left as-is

| Finding | Slot | Why unchanged |
|---|---|---|
| `id` version-vs-concept DOI | `id` | Value correct for a version-specific record; the gap was documentation, now supplied via caveat. |
| `publisher` as bare origin URL | `publisher` | `https://physionet.org` remains. The slot is `uriorcurie`; no declared prefix covers PhysioNet, so a URL is permitted. The site root is a weak referent but the bundle offers no better identifier. |
| Affiliation `id` absent | `creators[*].affiliations[*]` | Supplying ROR identifiers from model knowledge is prohibited. Omission is correct; a caveat now records it. |
| `created_on` / `last_updated_on` omitted | both | The bundle supports no creation or modification timestamp. `issued` is populated from the v3.1.0 publication date. Confirmed deliberate. |
| `download_url` omitted at top level | `download_url` | Correct: files are behind credentialed access and PhysioNet exposes no direct download URI. Landing pages sit in `distribution_formats[*].access_urls`, which is `uri`-ranged and the right home for them. |
| Core `notes` absorbing compensation, splits, relationships | core `notes` | The core schema carries no `participant_compensation`, `splits` or `relationships` slots, so `notes` is the only available home. This inverts structured-slots-first within the core record, but the alternative is losing the content. |
| `file_collections[*]` missing `file_count` / `total_bytes` | full `file_collections` | The bundle gives no byte sizes. Record counts were added to `notes`; the integer slots stay empty because no integer is attested. |
| Five source conflicts (hosting, award number, recording totals, compensation, healthsheet version lag) | `source_caveats` | Already handled correctly in Phase 1 with the higher-ranked source preferred and the disagreement recorded. Carried forward unchanged, with five further caveats appended. |

---

## 5. Referent

Both records describe **Bridge2AI-Voice v3.1.0, the adult dataset on PhysioNet** (`doi:10.13026/8xbn-nq66`). The pediatric dataset (`10.13026/h995-bt35`) is treated as a related dataset under `is_supplemented_by`, not as part of this record's referent, and the pediatric-specific content that appears in `at_risk_populations`, `collection_mechanisms` and `human_subject_research` describes the consortium's protocol rather than the contents of this release. This choice is held consistently across both records.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Slots populated | 71 | 66 |
| Validates against declared schema | yes | yes |

Phase-4 divergences at the start of reconciliation: seven (six core-only additions, one contradiction, plus the `subsets`/`resources` semantic split). Divergences remaining: none. Every slot in the core record is now either a projection of the same slot in the full record, or — for the five cohorts, compensation, splits and instance relationships — content moved to core `notes` because the core schema declares no slot for it, with the relocation stated in the text.
```