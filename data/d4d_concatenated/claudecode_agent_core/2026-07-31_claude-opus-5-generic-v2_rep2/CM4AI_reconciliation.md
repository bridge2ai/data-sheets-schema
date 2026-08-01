# CM4AI — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep2`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep2/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep2/CM4AI_d4d_core.yaml`

---

## 1. Referent

Both records take a single referent: the **CM4AI June 2026 Data Release (Beta)**, DOI `10.18130/V3/HIGT4C`, version 2.0, publication date 2026-06-17, version 2 released 2026-07-15T20:28:19Z, ten files.

This is the current release in the declared bundle. The four earlier releases (DXWOS5, B35XWX, F3TD5R, K7TGEM) are treated as prior versions of the same resource and are carried as release-lineage evidence, not as the record's subject. The bundle's own curation note records that the input sheet still selected K7TGEM while the release page names HIGT4C; the record follows HIGT4C, and the divergence is preserved rather than suppressed.

The Nature article `s41586-025-08878-3` is **not** a CM4AI release. It reports a U2OS osteosarcoma cell map produced by an overlapping author group. It is retained only under `external_resources` with an explicit scope note. The audit confirmed this handling and it is unchanged.

---

## 2. What the audit found

| Severity | Record | Locus | Finding |
|---|---|---|---|
| High | Core | `at_risk_populations` | Key written as `_risk_populations:` — leading `at` dropped, key begins with underscore. Not a CoreDataset slot. |
| High | Core | `conditions_of_access` | Not a slot in the inventory. Evidence well grounded but placed in a non-schema key. |
| High | Core | whole record | Only four top-level entries; required `id` absent. Cannot validate as `CoreDataset`. |
| Medium | Full | `total_size_bytes` | Supported in the bundle (ten displayed file sizes) but omitted. |
| Medium | Full | `download_url` | Partial Dataverse endpoint present in bundle; omitted. |
| Medium | Full | `language` | Not asserted by any source; omitted. |
| Low | Full | `acquisition_methods` | Fifth entry describes RO-Crate packaging, not instance acquisition. |
| Low | Full | `anomalies` | Entry describes a repository governance notice, not a data quality issue. |
| Low | Full | `errata` | Entry documents the June 2025 revision — a prior release version, off-referent. |
| Low | Full | `related_datasets` | Typed relationships to the four prior releases are supported but omitted. |
| Info | Full | several | Multivalued decomposition (47 creators, 4 intended uses, 6 limitations) correct per the one-object-per-entity rule. |

The audit's summary is accepted: the full record is substantially sound; the core record was not a valid instance.

---

## 3. Changes to the full record

### 3.1 `acquisition_methods` — one entry removed

The entry *"Derived AI-ready packaging of directly acquired data"* was removed. `InstanceAcquisition` declares how dataset instances were sourced — observed, measured, derived. RO-Crate/FAIRSCAPE packaging is a processing and distribution step, not an acquisition of instances. The same evidence is already carried, in the fields that declare it, at `preprocessing_strategies` (FAIRSCAPE AI-readiness packaging) and `distribution_formats` (RO-Crate). Removing the entry loses no evidence and stops the slot from answering a question it was not asked.

Slot remains populated with four entries (SEC-MS, AP-MS, IF confocal imaging, CRISPRi perturb-seq).

### 3.2 `anomalies` — entry relocated, slot removed

The single entry, *"Repository-level review notice"*, quoted the notice displayed on both the CM4AI site and the UVA Dataverse collection page regarding review for potential modification in compliance with Administration directives. The quotation is accurate. It is not a data anomaly: `DataAnomaly` declares quality issues, errors, or irregularities in the data, and this is a governance notice attached to the hosting repository.

The evidence was already present at `retention_limit` and `regulatory_restrictions`, which are the slots it answers. The `anomalies` entry was therefore removed. As it was the only entry, **`anomalies` is now absent from the record** and the populated-slot count drops by one. Omission is the correct state: the bundle documents no data-quality anomaly in this release.

### 3.3 `errata` — entry removed

The single erratum recorded the June 2025 (F3TD5R) revision: addition of RGB immunofluorescent images, RO-Crate metadata corrections, naming-convention changes. This is accurately drawn from the bundle but describes a correction to a **different release version** than the record's referent. `Erratum` declares errors discovered in *this* dataset since publication; the bundle documents none for HIGT4C.

The entry was removed and the release-lineage information it carried is preserved at `version_access` and `distribution_dates`, where inter-release history properly sits. As it was the only entry, **`errata` is now absent** and the populated-slot count drops by one.

### 3.4 `related_datasets` — added

`DatasetRelationship` requires `relationship_type` and `target_dataset`, both of which the bundle supplies for each prior release. Four entries were added, one per prior release, each typed as a version relationship:

- `10.18130/V3/DXWOS5` — May 2024 release
- `10.18130/V3/B35XWX` — March 2025 release
- `10.18130/V3/F3TD5R` — June 2025 release (revision notes retained here)
- `10.18130/V3/K7TGEM` — October 2025 release

This is the slot that declares typed inter-dataset relationships. The prior handling — carrying the lineage only inside `distribution_dates` and `version_access` narrative — recorded the facts but not the relationship structure. Populated-slot count rises by one, offsetting one of the two removals above.

No other slot was altered. In particular, the five preserved source disagreements (project end date, release-page vs. Dataverse date labelling, K7TGEM/HIGT4C sheet selection, AP-MS tagging counts across preprint and release, and IF protein counts across the March and June releases) are retained as stated in the sources, not resolved.

---

## 4. Changes to the core record

The core record was **reconstituted**. As audited it was not a `CoreDataset` instance and could not have validated; the earlier report of successful core validation is withdrawn.

### 4.1 `id` — added

`id` is the sole required slot on `CoreDataset` and was absent. It is now set to the release DOI as a CURIE, matching the full record's `id` so that the two records share a referent identifier.

### 4.2 `_risk_populations` → `at_risk_populations`

The malformed key was corrected. The content was retained unchanged: the release asserts Human Subjects: No, de-identified samples, and no FDA regulation, and the material is derived from commercially available immortalised cell lines, so no protection regime for minors, prisoners, or pregnant persons is engaged and none is described.

### 4.3 `content_warnings` — retained

Carried forward unchanged from the pre-reconciliation core file. Supported by the bundle.

### 4.4 `conditions_of_access` — removed, evidence redistributed

`conditions_of_access` is not a slot in the schema. Its content was well grounded and has been redistributed to the slots that declare it:

| Evidence | Destination |
|---|---|
| Public file access; ZIP packages; 1.9 GB per-file browser download limit; Data Access API for programmatic retrieval | `distribution_formats` |
| Perturb-seq links (KOLF2.1J and MDA-MB-468) under pre-publication embargo | `confidential_elements` |
| CC BY-NC-SA 4.0; attribution to copyright holders and authors; commercial use requires separate negotiation with UCSD / Stanford / UCSF | `license_and_use_terms` |
| Bridge2AI Open House Code of Conduct attestation prior to data access | `license_and_use_terms` |

No evidence was discarded. Each fragment now sits in the field that asks for it rather than in a synthetic key that asks for nothing.

### 4.5 Remaining core content

The reconstituted core record carries only those slots that (a) exist on `CoreDataset` and (b) are supported by the declared bundle. It is a strict projection of the full record: every value in the core record appears, identically, in the full record. No core-only claim exists.

---

## 5. What was left as-is, and why

### 5.1 Supported but omitted — omission retained

**`total_size_bytes`.** All ten June 2026 files carry displayed sizes (3.8 GB, 4.6 GB, 4.2 GB, 113.3 KB, 135.8 KB, 171.8 KB, 93.9 KB, 30.2 KB, 73.3 KB, 1.1 MB). These are rounded display strings from a web table, not byte counts. The slot's range is `integer` and its description asks for size in bytes. Deriving an integer from rounded GB/KB display values would introduce a precision the bundle does not have. Left omitted.

**`download_url`.** The bundle supplies `https://dataverse.lib.virginia.edu/api/access/datafile/` as the package-download endpoint, explicitly documented for use with Wget or a download manager. This is a prefix requiring a per-file identifier, not a URL that points to the data. The slot description distinguishes a direct data URL from a landing page; this is neither. Left omitted. The access route is recorded at `distribution_formats`, where it belongs.

**`language`.** No source asserts a language for the dataset. That the documents are written in English is an observation about the bundle, not a claim any source makes about the resource. Left omitted under the evidence boundary.

### 5.2 Correctly omitted — confirmed

The following remain absent, and the audit confirms absence is the right answer. The release record states **Human Subjects: No** and **De-identified Samples: Yes**; the material derives from two commercially available immortalised cell lines (MDA-MB-468, ATCC; KOLF2.1J, HipSci, available under simple MTA).

- `collection_consents`, `collection_notifications`, `consent_revocations`, `informed_consent`, `participant_compensation`, `participant_privacy` — no human participants were enrolled; no consent, notification, revocation, compensation, or participant-privacy process is described. Donor provenance for both lines is stated in the preprint but no consent documentation accompanies it. Privacy status is carried at `is_deidentified` and `human_subject_research`.
- `data_protection_impacts` — no DPIA described.
- `imputation_protocols` — no imputation described.
- `splits` — no train/validation/test partitioning described for this release.
- `sensitive_elements` — no sensitive attribute identified; the embargoed perturb-seq links are access-restricted rather than sensitive and sit at `confidential_elements`.
- `conforms_to_class` — RO-Crate and FAIRSCAPE are named; no class within a schema is.
- `modified_by` — a version-2 release timestamp exists; no source says who performed the modification. Justin Niestroy is recorded as *depositor*, which is a different role and is captured elsewhere.
- `parent_datasets` — the Dataverse path (UVA Dataverse › LibraData › School of Medicine › Cell Maps for Artificial Intelligence) is repository organisation, not dataset composition. No hasPart/isPartOf relationship is asserted.
- `resources` — correctly deferred to `file_collections` per that slot's own description.

### 5.3 Overlapping slot pairs — choice retained

**`raw_sources` vs. `raw_data_sources`.** Seven entries sit at `raw_data_sources`; `raw_sources` is empty. The bundle's raw-data evidence consists of external-repository pointers (MassIVE for SEC-MS and AP-MS, NCBI BioProject / SRA, Figshare for the CRISPRi atlas, plus two embargoed perturb-seq deposits). `RawDataSource` requires `source_description`, which those pointers supply directly. Populating both slots would duplicate. Choice retained.

**`subsets` vs. `subpopulations` + `file_collections`.** The release is organised by cell line, treatment condition, and assay modality rather than by named logical partitions. That structure is carried at `subpopulations` and `file_collections`. `subsets` left omitted.

### 5.4 Duplication accepted

The project-end-date divergence (NIH RePORTER 2026-08-31 vs. the release maintenance plan's November 2026) appears at both `collection_timeframes` and `updates`. Both slots legitimately touch the project timeline and both readings are preserved in each. The duplication is accepted rather than resolved to one location, because collapsing it would make one of the two slots silently incomplete.

### 5.5 `total_file_count` — verified, unchanged

`total_file_count: 10` matches the June 2026 file table and the bundle's curation note. The five `file_collections` entries declare `file_count` values of 3, 2, 2, 2, 1, summing to 10. Aggregate is internally consistent. No change.

---

## 6. Slot-count effect

| Record | Change |
|---|---|
| Full | `anomalies` removed (−1), `errata` removed (−1), `related_datasets` added (+1). **Net −1 populated slot.** Two intra-slot entries removed (`acquisition_methods` 5→4) with no effect on slot count. |
| Core | Reconstituted. `id` added; `at_risk_populations` key repaired; `conditions_of_access` removed and its four evidence fragments redistributed into `distribution_formats`, `confidential_elements`, and `license_and_use_terms`. |

Every core slot value is present verbatim in the full record. No divergence between the two records survives reconciliation.

---

## 7. Outcome

Reconciliation **completed with corrections to both records**.

- The full record required three slot-level edits and two intra-slot removals. Its referent, its disagreement handling, its exclusion of the U2OS material, and its multivalued decomposition were all confirmed sound and are unchanged.
- The core record was not a valid instance as generated and was rebuilt. The prior claim that it validated is withdrawn and superseded by this report.
- Both records now share the HIGT4C referent, share an `id`, and carry no claim the declared bundle does not support.

Validation was re-run against both schemas after the edits above; the provenance record was written after validation, not before.