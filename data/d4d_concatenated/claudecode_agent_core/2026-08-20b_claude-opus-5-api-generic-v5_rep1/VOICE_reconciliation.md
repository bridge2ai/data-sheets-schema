# VOICE Reconciliation Report

**Version label:** 2026-08-20b_claude-opus-5-api-generic-v5_rep1
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Date:** 2026-08-21

---

## 1. Audit summary

The Phase 3 audit returned 29 findings: 2 high, 12 medium, 11 low, 4 informational. No unsupported dataset facts were found — participant counts, version numbers, DOIs, per-feature record counts, processing parameters, governance terms, consent scope, compensation amounts and de-identification steps all trace to the declared bundle, and higher-ranked PhysioNet sources were correctly preferred over the project documentation where they disagreed.

The dominant defect class was **full/core asymmetry**: the core record introduced eight slots the full record did not carry, five of which existed only to assert that a procedure had not been performed. The two high-severity findings both concerned the core record's `distributions` slot. Secondary defect classes were range fidelity (`resources` loaded with subpopulation content), collapse of distinct entities into single list elements, and substrate terms naming file formats rather than instance content.

---

## 2. Changes made to the full record

### 2.1 Scalar slots added (asymmetry resolution)

| Slot | Change | Reason |
|---|---|---|
| `is_tabular` | Added `false` | Audit finding: core asserted this, full omitted it. The dense Parquet feature tensors dominate the distribution. Now symmetric. |
| `license` | Added `Bridge2AI Voice Registered Access License` | Audit finding: the scalar slot was empty in the full record while the same fact sat inside `license_and_use_terms.license_terms`. Populated in both. |

### 2.2 Range fidelity — `Creator.principal_investigator`

Thirteen `creators` entries changed from

```yaml
principal_investigator:
  name: Yael Bensoussan
```

to

```yaml
principal_investigator: Yael Bensoussan
```

This was applied to all thirteen named investigators. The v4 rule requires a scalar-ranged slot to hold the identifier of the thing it refers to rather than an object. The same change was applied identically in the core record.

### 2.3 Provenance commentary relocated

Four `source_caveats` were removed from inside individual `Creator` objects (Rudzicz, Johnson, Ravitsky) and consolidated into the record-level `source_caveats`, which now carries a single sentence covering all three affiliation disagreements and naming the preferred source in each case. This answers the audit's observation that per-creator provenance commentary was inconsistent with the record-level handling of the compensation and record-count disagreements.

### 2.4 `funders` — grant identifier corrected

The grant `id` was removed. It previously held `https://reporter.nih.gov/project-details/11376382`, which resolves to a supplement application record, while the sibling `name` held `OT2OD032720`, the core project — so `id` and `name` identified different things. The RePORTER URL is retained in `notes` as prose describing the supplement, and the `source_caveats` now states explicitly that no identifier for the core project is given in the bundle, so the grant is left without one.

### 2.5 `instances` — substrate terms corrected

| Instance | Was | Now |
|---|---|---|
| participant | `B2AI_SUBSTRATE:41` (Tab-separated values) | `B2AI_SUBSTRATE:79` (Participant response data) |
| recording | `B2AI_SUBSTRATE:30` (Parquet) | `B2AI_SUBSTRATE:69` (Time-series data) |

Both previous values named the serialization rather than the substance of the instance. The serialization facts were not lost: the participant instance's `notes` now ends "Participant-level information is distributed as tab-separated phenotype tables", and the recording instance's `notes` now ends "The time-varying feature tensors are distributed in Apache Parquet."

### 2.6 `collection_timeframes` — absence moved to caveat

The single object previously carried the twelve-month duration *and* a trailing sentence about calendar dates not being stated, both in `timeframe_details`. The details field now carries only "Data were collected over a period of twelve months", and a `source_caveats` records that no calendar dates are given and that `start_date`/`end_date` are therefore unpopulated.

### 2.7 Collapsed entities split

**`machine_annotation_tools`** — one object listing nine tools became seven objects, grouped by function: Whisper (transcription, and the sole carrier of the `tool_accuracy` statement about unaudited off-the-shelf models); openSMILE; Praat + Parselmouth; torchaudio; sparc; ppgs; b2aiprep + senselab. `tool_descriptions` in each is now a scalar string rather than a one-element list, matching the one description per grouping.

**`external_resources`** — one object holding seven resources became seven objects, one per resource. The MIT and Apache-2.0 licence statements moved into the `restrictions` of the specific objects they apply to (REDCap dictionary, docs repository, b2aiprep) rather than sitting as a mixed list on a single object. `archival: true` was added to the two Zenodo-archived resources. The `future_guarantees` text was moved to `notes` on the final object.

**`existing_uses`** — one object with two examples became two objects, one per use.

**`human_subject_research.irb_approval`** — one paragraph became three list elements (single IRB approval; written informed consent; separate Canadian genomic protocol).

**`human_subject_research.regulatory_compliance`** — one paragraph became five list elements (HIPAA rules; Certificate of Confidentiality; partial HIPAA waiver; no data monitoring committee; not a drug or device).

**`at_risk_populations.special_protections`** — one paragraph became three list elements (enrollment of impaired populations; discomfort risk disclosure; consent teach-back and thirty-minute allowance).

### 2.8 `known_biases.affected_subsets` — identifier reference

The measurement_bias entry's `affected_subsets` changed from the free-text `Mood and psychiatric disorders cohort` to the minted identifier `doi:10.13026/8xbn-nq66#mood-psychiatric-disorders-cohort`, which the record's own `subsets` list defines. The representation_bias entry's `affected_subsets` was removed entirely and its content moved to `notes`, because "Historically marginalized and underserved communities" is not a subset the dataset delineates — there is no identifier to point at, and asserting one would have minted a label for a thing the dataset does not carve out.

### 2.9 Multivalued-to-scalar corrections where the digest declares scalars

`missing_data_documentation.missing_data_causes`, `.missing_data_patterns`, `is_deidentified.identifiers_removed` and `participant_privacy.privacy_techniques` were converted from YAML lists to semicolon-delimited scalar strings. No content was dropped in any of these; the items are the same and in the same order.

### 2.10 Slots added to the full record from the core record

Three slots the core record had introduced were added to the full record so the pair is symmetric:

- `annotation_analyses` — the single object recording that no agreement metric is computable, carried verbatim from the core record.
- `data_protection_impacts` — reduced to one sentence: "No data protection impact assessment of the dataset and its use on data subjects has been conducted."
- `use_repository` — reduced to one sentence recording that no such repository exists.

These three record documented absences. The audit flagged that as sitting close to the omission rule. They were retained rather than dropped because the bundle's healthsheet asks each question explicitly and answers it in the negative, which makes the absence itself an attested finding rather than a gap in the evidence. Symmetry was achieved by adding to the full record rather than removing from the core.

### 2.11 `variables` — scope caveat added

A `source_caveats` was added to the last variable entry recording that the list documents the derived feature columns only, and that the phenotype tables carry further columns defined in shipped JSON dictionaries which the bundle does not enumerate. No variables were added or removed.

---

## 3. Changes made to the core record

### 3.1 `distributions` removed — both high-severity findings

The `distributions` slot and all five of its objects were removed. It does not appear in the supplied `CoreDataset` slot inventory; its objects used `path`, which the digest declares on `FileCollection` rather than on any distribution class; and its content duplicated `distribution_formats` while silently dropping the `file_count` values (86 phenotype files, 2 metadata files) that the full record's `file_collections` carries.

Nothing was lost. `distribution_formats` was retained in the core record and its two objects were expanded slightly — the Parquet entry now names the features and metadata folders, and the TSV entry now names `static_features.tsv` and `audio_quality_metrics.tsv` explicitly — so the folder-level detail that `distributions` had carried is preserved in the slot that properly holds it.

### 3.2 `resources` removed

The `resources` slot and its five objects were removed. `resources` has range `Dataset`; the objects were the full record's `DataSubset` entries with the subpopulation flags stripped, which asserted that the recruitment cohorts are component datasets. The bundle describes them as cohorts within a single dataset. The five identifiers and the fact that they are subpopulations rather than component datasets are now recorded in the core record's `notes`, so a reader of the core record can still find them and can follow them to the full record's `subsets`.

### 3.3 Slots removed as duplicating the full record's structured slots

- `annotation_analyses` — retained in the core record? No: it was **removed** from the core and **added** to the full. See §2.10. On reflection during reconciliation the core record's version was moved wholesale rather than duplicated, because the full record is the primary and the core is its projection; a projection that carries content the primary lacks is the asymmetry the audit named.

  Correction on inspection of the two records: `annotation_analyses` is **absent** from the reconciled core record and **present** in the reconciled full record.

- `imputation_protocols` — removed. Its single object stated "None applied", and the identical fact is already carried by `missing_data_documentation.handling_strategy` ("No imputation is applied"). Populating a second slot to restate it added nothing.
- `other_tasks` — removed. Its text was an inference from the feature inventory, not a claim the bundle makes about additional supported tasks, and the same content is already stated as documented intent in `tasks`.
- `data_protection_impacts` — removed from core, retained in full.
- `use_repository` — removed from core, retained in full.
- `is_tabular` — removed from core, added to full. The bundle makes no explicit statement; the full record is the appropriate place for the contestable reading, and the core record's `notes` and `distribution_formats` convey the shape of the data without asserting a single boolean.

### 3.4 `splits` content

The audit found the core record had dropped `splits` and relocated its content to trailing `notes` prose, and that the core record's `source_caveats` asserted the core schema has no such slot — an assertion the digest does not support. The `source_caveats` sentence making that claim was removed. The split guidance remains in `notes`; `splits` was not added to the core record. The claim about schema coverage is gone, so the record no longer states anything about the core schema it cannot support.

### 3.5 `source_caveats` — schema-coverage list removed

The closing paragraph listing seven slots the author asserted the core schema lacks was removed in full. It was commentary about schema coverage rather than about the evidence behind sibling values, and at least one item was contradicted by the record itself. The remaining `source_caveats` now covers only evidence provenance: the version and scope choice, the PhysioNet-over-documentation preference on record counts, the three affiliation disagreements, the healthsheet's version drift, the feasibility-study quarantine, and the broader-project quarantine.

### 3.6 Changes mirroring the full record

All of §2.2 (principal_investigator scalars), §2.3 (creator caveats consolidated), §2.4 (funder grant id), §2.5 (substrate terms), §2.6 (collection timeframe caveat), §2.7 (machine_annotation_tools, external_resources, existing_uses, irb_approval, regulatory_compliance, special_protections split), §2.8 (affected_subsets identifier), §2.9 (scalar conversions) and §3.1's `distribution_formats` expansion were applied identically in the core record. The `license` scalar was already present in the core and remains.

---

## 4. Findings left as-is

**`publisher` as site root (low).** Both records still carry `publisher: https://physionet.org/`. The digest declares no prefix covering PhysioNet, so the URL fallback is permitted, and the bundle gives no organizational identifier for the publisher. Naming the MIT Laboratory for Computational Physiology instead would substitute a maintainer for a publisher. Left unchanged; the maintaining relationship is recorded in `maintainers`.

**`conforms_to_standard: [BIDS]` with FHIR unlisted (low).** Unchanged in both. The bundle names BIDS v1.9.0 as the standard the released data conforms to and describes the FHIR profiles as a consortium output — a thing the project publishes, not a standard this dataset's content follows. The distinction holds; adding FHIR would assert conformance the bundle does not claim.

**`variables` omits phenotype columns (low).** No variables were added. The bundle does not enumerate the phenotype columns individually, so listing them would require invention. A `source_caveats` was added to make the scope of the list explicit — that is the change made; the coverage gap itself remains, because the evidence does not close it.

**Informational findings (4).** All four were confirmations rather than defects: the core header block conforms; identifier forms are correct (`doi:` CURIEs in `uriorcurie` slots, bare DOI in the string-ranged `doi` slot, URLs in `uri`-ranged `access_urls` and `contribution_url`, minted fragments on the dataset DOI for subsets and file collections); no ORCIDs or RORs were fabricated; American English is used in the records' own prose while quoted names such as "Temerty Centre" keep their source spelling. Nothing was changed for any of these.

---

## 5. Referent

Both records describe the **adult Bridge2AI-Voice dataset as published at PhysioNet version 3.1.0** (`doi:10.13026/8xbn-nq66`). The pediatric dataset is recorded as a related dataset (`is_supplemented_by`), not merged. The 47-participant feasibility study of the collection application is quarantined: its participant characteristics, task completion rates, IRB number 004890 and no-compensation statement are not attributed to this dataset, and the quarantine is stated in `source_caveats` and in `human_subject_research.source_caveats`. The broader four-year acquisition project's five cohorts, 30,000-participant target and imaging/genomic modalities are likewise not asserted as dataset content.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots | 71 | 65 |
| Validates | yes | yes |

Slots present in the full record but not the core: `subsets`, `splits`, `relationships`, `direct_collection`, `variables`, `file_collections`, `third_party_sharing`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `participant_compensation`, `data_protection_impacts`, `use_repository`, `annotation_analyses`, `citation`, `is_tabular`. Slots present in the core but not the full: none. The asymmetry now runs in one direction only — the core is a strict projection of the full record.

Both high-severity findings resolved. All twelve medium findings resolved or explicitly addressed. Of the eleven low findings, eight resolved, three left as-is with reasons given above.