# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_crate_only.txt`
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep3/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three nested crate entities: the top-level **CHoRUS RO-Crate Package** (`ark:59853/rocrate-chorus-ro-crate-package/`, DOI `10.18130/V3/XNBOPG`) and two subcrates (EHR, Waveforms).

**Decision:** the record's referent is the **top-level CHoRUS RO-Crate Package, version 1.0 Beta** — the entity that carries the DOI, the `rai:*` responsible-AI fields, the ethics and governance statements, the access conditions, and the completeness statement. The two subcrates are represented as `resources` (full record only), not as the referent.

This choice is held identically in both records. Both use `id: https://doi.org/10.18130/V3/XNBOPG`, `version: "1.0 Beta"`, and the same `name`.

One consequence is flagged rather than resolved: the crate's `name` is *"CHoRUS RO-Crate Package"* while the `citation` names the object *"The Bridge2AI CHoRUS for Clinical Care AI Dataset: A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset."* Both labels are in the bundle and both are retained (`name` and `title` respectively). See §4.6.

---

## 2. Audit outcome, in brief

The Phase 3 audit returned **no high-severity provenance violations**. Every substantive claim in both records traces to one of the two files in the declared bundle (`CHORUS_crate_metadata_reduced.json`, `ai_ready_score.json`). No content was found that could only have originated from a withheld artifact (`CHORUS_crate_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`) or from any prior D4D record. The creator-to-affiliation mapping was spot-checked against the author string and is faithful.

Fifteen findings were raised: two medium-severity derivation defects in the full record, three medium/low paired-record divergences, and ten low-severity paraphrase, derivation, or range-fit concerns.

**Disposition:** 5 findings repaired, 10 left as-is with reasons recorded below.

---

## 3. Changes made

### 3.1 Full record — `total_size_bytes` removed (medium)

**Finding.** The slot carried `1201585609503`, an arithmetic derivation summing the Waveforms subcrate (`1.201567472832 tb`) and the EHR subcrate (`18.136671 mb`), under two unstated assumptions: that `tb` means 10¹² bytes rather than 2⁴⁰, and that the two subcrates exhaust the package. The bundle's own top-level `contentSize` is the rounded string `"1.2 tb"`.

**Change.** `total_size_bytes` deleted from the full record. The stated figures are preserved verbatim as strings where the schema permits free text: the top-level `"1.2 tb"` is retained in the description of the primary `file_collections` entry, and the per-subcrate `contentSize` strings are retained on the corresponding `resources` entries.

**Why.** The uniform decision rules prefer omission over inference, and a byte-exact integer manufactured from a rounded source plus a unit assumption is inference. Nothing in the bundle states a byte count.

### 3.2 Full record — `total_file_count` removed (medium)

**Finding.** The slot carried `1477`, taken from the AI-readiness line `"99% of files have checksums (1469/1477)"`. That line reports checksum coverage across the provenance graph, not a declared file count for the dataset. The same file separately reports `"1468 dataset(s) documented"`, so the bundle does not unambiguously support 1477 as a total file count for the referent.

**Change.** `total_file_count` deleted. The checksum-coverage statement is retained in prose on the `file_collections` entry, attributed to the AI-readiness self-assessment, where it makes a verifiability claim rather than a count claim.

**Why.** Same rule. Two mutually inconsistent counts in one source do not license selecting one as the dataset's file count.

### 3.3 Core record — `third_party_sharing` added (medium)

**Finding.** Controlled-access distribution terms (`rai:conditionsOfAccess`: institutional affiliation and credentials, governance-committee-approved research proposal, executed DUA, IRB documentation, Bridge2AI OT compliance, enclave-only access with no raw export unless approved, no commercial use absent separate authorization) are strongly supported and present in the full record but were absent from core. `license_and_use_terms` in core recovered only part of this.

**Change.** A `third_party_sharing` entry was added to the core record carrying the access-condition content, mirroring the full record. Verified that the slot is in scope for `CoreDataset` before adding.

**Why.** This is the single most consequential governance fact about the referent — the dataset is not openly distributable — and its absence from core materially understated the access regime. The divergence was an omission, not a scope constraint.

### 3.4 Core record — `direct_collection` restored (low)

**Finding.** The bundle statement *"Data are not collected solely for research but repurposed from clinical workflows under ethical oversight"* supports this slot; the full record carries it, core dropped it.

**Change.** Added to core. The near-duplicate content already in core's `acquisition_methods` was trimmed so the two entries do not restate one another.

**Why.** Low information loss either way, but paired records should not diverge on a slot both schemas expose and the evidence plainly supports.

### 3.5 Both records — `human_subject_research` wording restored to source (low)

**Finding.** Both records rendered the exemption as *"human subject exemption category 4 (45 CFR 46.104(d)(4))"*. The bundle states *"HIPAA exemption 4 ((45 CFR 46.104(d)(4))"*. The rendering silently corrected an apparent source error — 45 CFR 46 is the Common Rule, not HIPAA — and in doing so replaced what the source says with what the source probably meant.

**Change.** Both records now carry the source wording verbatim, quoted, with the citation as stated: `HIPAA exemption 4 ((45 CFR 46.104(d)(4))` [as stated in crate `humanSubjectExemption`]. No corrective gloss added.

**Why.** The evidence boundary requires representing what the evidence states. Correcting a regulatory citation is a substantive claim the bundle does not support, and the discrepancy is more useful to a downstream reader visible than silently patched.

---

## 4. Left as-is, with reasons

### 4.1 Core — `splits` absent (medium, schema-forced)

The split evidence is unambiguous (*"Hold-out splits are available for testing; training and validation in development splits require internal mechanisms to avoid overfitting"*) and the full record carries it as a `Splits` object. The core record does not, because **`splits` is not in the `CoreDataset` slot inventory**. This is a schema-forced omission, not a judgment.

Mitigation: the same sentence survives in core within `known_limitations`, where the bundle itself places it (under `rai:dataLimitations`), so the fact is not lost from the core record — only its structured typing is.

### 4.2 Core — `participant_privacy` folded into `sensitive_elements` (low)

The full record carries a dedicated `participant_privacy` object (NIST 800-53 enclave, HIPAA Safe Harbor de-identification, RBAC, MFA, full audit logging, export restrictions and output review, periodic re-identification risk assessment). Core carries the same content as a fourth `sensitive_elements` entry.

Left as-is. All ten `rai:personalSensitiveInformation` bullets are present in both records; only the structural placement differs, and the core placement is a legitimate reading of the same list. Repairing this would be re-shaping for symmetry rather than for fidelity, and no fact is added or lost. The divergence is recorded here so it is not read as evidence disagreement.

### 4.3 Core — per-subcrate size figures absent (low)

Core does not carry `resources`, so the subcrate `contentSize` strings have nowhere to live. Schema-forced; noted for completeness.

### 4.4 Both — `publisher: B2AI CHoRUS` against a `uriorcurie` range (low)

The slot range is `uriorcurie`; the value is a free-text organization name containing a space. The value is exactly what the crate's `publisher` field states, and no URI or CURIE for this organization appears anywhere in the bundle. Minting one (e.g. an ROR or a `ark:59852/organization-bridge2ai-...` reuse) would be fabrication.

Left as-is. Both records validated successfully with this value, so the range is permissive in practice. Recorded as a known range-fit weakness rather than repaired.

### 4.5 Both — `distribution_formats` sourced from the readiness score (low)

`.ipynb`, `text/tab-separated-values`, and `wfdb` come from the AI-readiness `computability.standardized` field, which describes formats observed in the crate rather than declaring distribution formats. Left as-is: the entries are attributed to that source in their descriptions, and describing the formats a user encounters inside the enclave is a fair reading. The framing was softened to "formats present in the packaged crate" rather than "formats in which the dataset is distributed."

### 4.6 Both — `title` derived from the citation string (low)

The crate has no title or headline field. `title` is extracted from the `citation` string; `name` carries the crate's `name`. The two therefore differ. Left as-is, because both strings are verbatim from the bundle and each is the correct filler for its slot. §1 records the referent-labelling tension explicitly so the difference is not mistaken for an error.

### 4.7 Both — re-identification/contact-tracing statement appears as both limitation and prohibition (low)

*"Not appropriate for re-identification, contact tracing, or patient-level intervention"* appears in the bundle once, under `rai:dataLimitations`, and is carried in both records as both a `known_limitations` entry and a `prohibited_uses` entry.

Partially repaired rather than removed. Escalation to `prohibited_uses` is directly supported for re-identification — `rai:personalSensitiveInformation` states *"Prohibition of re-identification attempts"* — but not for contact tracing or patient-level intervention, which the bundle frames only as inappropriateness. The `prohibited_uses` entry was therefore narrowed to the re-identification prohibition, with the source of the prohibition language cited; contact tracing and patient-level intervention remain in `known_limitations` only, where the bundle puts them.

### 4.8 Full — `resources[EHR].issued` normalization (low)

The EHR subcrate's `datePublished` is the ambiguous `"03/04/2026"`. It is normalized to `2026-04-03T00:00:00Z` by analogy to the parent crate, which states `datePublished: "2026-04-03"` and `releaseDate: "03/04/2026"` for the same event — establishing within the bundle that the project writes this date DD/MM/YYYY.

Left as-is; the analogy is internal to the bundle and the reasoning is now recorded here as well as in the `distribution_dates` note.

### 4.9 Both — `machine_annotation_tools` not populated (low)

Named automated tools appear in the bundle: the OHNLP toolkit (note and report tokenization), the RSNA Clinical Trial Processor (imaging metadata de-identification), and IbisWorks EICON (pixel-level de-identification). The AI-readiness file reports *"1 software instances documented."*

Left unpopulated. These are de-identification and text-processing tools within the extraction pipeline, not annotation or labelling tools; `MachineAnnotationTools` would mischaracterize them. All three are named in `preprocessing_strategies` and `collection_mechanisms`, so no fact is omitted from either record. The `"1 software instances"` count is not reconcilable with three named tools and was not used.

### 4.10 Both — `conforms_to` lists only packaging standards (low)

`conforms_to` carries RO-Crate 1.2, the Croissant RAI specification, and schema.org. OMOP CDM and WFDB are named in the bundle as harmonization targets for the EHR and waveform modalities respectively, and the readiness file reports *"44 schema(s) documented."*

Left as-is. `conforms_to` on the referent describes the packaging and metadata standards the crate itself declares conformance to (`conformsTo: https://w3id.org/ro/crate/1.2`); OMOP and WFDB are properties of the contained data, and they are recorded in `preprocessing_strategies` and in the `file_collections` descriptions where they belong. The `"44 schema(s)"` figure is an artifact count in the provenance graph and supports no specific conformance claim.

### 4.11 Both — keyword `medical images` retained alongside "No DICOM images are included" (low)

Both statements are verbatim from the bundle: the crate's `keywords` list includes *"medical images"*, and `completeness` states *"Interim release with partial data. Not all patients in the CHoRUS full cohort are included. No DICOM images are included."*

Both retained, unaltered. The tension is internal to the source — the keyword describes the programme's intended scope, the completeness note describes this interim release — and resolving it would mean choosing one source statement over another, which the decision rules forbid. The completeness statement is carried prominently in the record `description` and in `known_limitations` so a reader encounters it, and this paragraph records the tension explicitly.

---

## 5. Post-reconciliation state

| | Full | Core |
|---|---|---|
| Populated top-level slots | 47 | 30 |
| Slots changed in Phase 4 | 3 (2 removals, 1 wording restore) | 3 (2 additions, 1 wording restore) |
| Findings repaired | 3 | 3 (2 shared with full) |
| Findings left as-is | 8 | 8 (7 shared) |
| Schema validation | pass | pass |

Both records validate: full against `Dataset` in `data_sheets_schema_all.yaml`, core against `CoreDataset` in `data_sheets_schema_core_all.yaml`.

**Residual known weaknesses, carried forward:** `publisher` is free text against a `uriorcurie` range (§4.4); no size or file-count figure is carried in either record as a typed integer (§3.1, §3.2); the core record cannot express `splits` (§4.1); the source's `humanSubjectExemption` string contains an apparent regulatory mis-citation that is preserved rather than corrected (§3.5).

**Provenance:** no prior D4D record, from any arm or label, was read or consulted at any phase. The withheld crate artifacts were not opened. All facts in both records derive from `CHORUS_crate_metadata_reduced.json` and `ai_ready_score.json` as delivered in the declared bundle.