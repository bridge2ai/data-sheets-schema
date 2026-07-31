# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep3`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep3/CHORUS_d4d_core.yaml`

---

## 1. Declared referent

`Dataset` admits one referent. The referent held across both records is **the CHoRUS clinical dataset** — the multi-modal, controlled-access critical-care data collection assembled by the CHoRUS Network.

Two adjacent entities appear in the bundle and are **not** the referent:

- **The CHoRUS data generation project** (NIH award `OT2OD032701`). Project facts are recorded only where they are properties of the dataset (funder, purposes, creators, addressed gaps), never as dataset attributes in their own right.
- **The AIM-AHEAD Bridge2AI for Clinical Care Training Program.** This is a training programme that *consumes* the dataset. Its stipends, eligibility rules, application deadlines, curriculum and mentorship structure are not dataset properties and are excluded, except where the programme documents the dataset itself (the August 2025 modality table, the registration/licensing access route).

This choice is applied consistently in both records.

---

## 2. Audit outcome summary

The Phase 3 audit returned **19 findings**: 0 critical, 1 high, 6 medium, 5 low, 7 informational.

No fabrication of substantive dataset facts was found. All quantitative claims — 50,000 released admissions, 1.6 billion OMOP rows, 7,642 admissions with radiology data, 23 Tb of waveform data, 100,000 anticipated admissions, 9 modalities, 14 contributing hospitals, 20 institutions, 60+ consortium members, award `OT2OD032701`, `$5,880,300`, project window 2022-09-01 to 2026-11-30 — trace directly to the declared bundle.

---

## 3. High-severity finding and its resolution

**Finding:** the Phase 2 core record was declared complete but its body was not available to the audit, so Phase 3 coverage was limited to the full record and no pairwise comparison could be run.

**Resolution:** Phase 4 was not permitted to proceed on an unaudited core file. The core record was re-presented and audited against the bundle before reconciliation, then compared slot-by-slot with the corrected full record. The three specific divergence risks named by the audit were each checked:

| Check | Outcome |
|---|---|
| `license` handling | Consistent — omitted in both (see §5) |
| 50,000 vs 45,000 admissions | Consistent — held as attributed alternatives in both |
| Chosen referent | Consistent — CHoRUS clinical dataset in both |

No further divergence was found between the two records.

---

## 4. Changes made

### 4.1 `instances` — over-claim removed (full record)

**Was:** each admission carries linked records across the nine data modalities collected for that admission.

**Now:** each instance is a hospital admission of a patient with acute or critical illness, drawn from ICU, PICU and NICU populations.

**Why:** the bundle contradicts per-admission modality completeness in aggregate — only 7,642 of 50,000 released admissions have radiology data, imaging de-identification is "in process for larger cohort", and EEG "extraction in process at this point". The removed clause asserted a completeness the evidence disproves.

### 4.2 `collection_timeframes` — award period removed (full record)

**Was:** collection timeframe 2022-09-01 to 2026-11-30.

**Now:** only the "as of August 2025" snapshot is retained, described as the point at which the reported coverage was current.

**Why:** those dates are given in the bundle as NIH *project* start and end. The collection is explicitly retrospective, so the clinical period the records cover is a different and unstated interval. Presenting the award window as the collection window conflated the two.

### 4.3 `maintainers` — inferred person name removed (full record)

**Was:** a maintainer object naming "D. Bold, Emory University".

**Now:** the Emory address is recorded as an access-request contact only, with no name or role attributed.

**Why:** the name was reconstructed from the local part of `dbold@emory.edu`. The bundle supplies the address and nothing else. The MGH programme-manager contact, which the bundle names explicitly, is retained.

### 4.4 `machine_annotation_tools` — slot vacated (full record)

**Was:** `privacy_scan_tool` and `CTP-deid`, the latter glossed as "a de-identification repository".

**Now:** slot omitted. `privacy_scan_tool` is described under `is_deidentified` using the bundle's own wording ("A Privacy Scan tools for medical records"). `CTP-deid` is dropped entirely.

**Why:** two defects at once. The slot declares automated *annotation* tools used in dataset creation; neither tool is evidenced as one. And the `CTP-deid` gloss was inferred from the repository name — the bundle gives that repository no description at all.

### 4.5 `ethical_reviews` — slot vacated (full record)

**Was:** two objects describing community ethics focus groups and analysis of the legal/regulatory landscape.

**Now:** slot omitted.

**Why:** the slot declares IRB approvals, ethics-committee reviews and compliance certifications. The bundle records no oversight determination for CHoRUS; "IRB" appears only as an AIM-AHEAD curriculum topic belonging to the training programme, not to this dataset. The focus-group and legal-analysis content is genuine bundle evidence and remains where it answers the field asked — under `purposes` and `human_subject_research`.

### 4.6 Low-severity corrections applied

- **`file_collections`** — per-modality metadata states were recovered from a source table whose columns are interleaved in the extracted text, and the `Yes`/`Planned` tokens do not map unambiguously onto the nine rows. Assignments that could not be firmly established (imaging, waveform telemetry, EEG) were dropped; the data-standard and access-control values, which are unambiguous, are retained.
- **`preprocessing_strategies`** — two inferred conjunctions were split. The DeGauss/UF-Geocoding entry no longer asserts a link to distance-to-hospital and social-determinants aims (stated separately in the bundle, in different sources, and never connected). The waveform entry no longer joins the `chorus_waveform` repository description to the table's WFDB/PhysioNet row as a single claim.
- **`is_tabular`** — removed. The bundle makes no tabularity statement and documents a mixed collection of OMOP relational tables alongside DICOM, WFDB and EDF+ binaries. `false` was an editorial reading, not a bundle fact.
- **`direct_collection`** — the explicit "not collected directly from individuals" determination was withdrawn. What the bundle states is retained verbatim: the collection is retrospective, drawn from hospital EHR, PACS, bedside monitor and EEG systems. The direct/indirect classification is left unmade because the bundle does not make it.
- **`cleaning_strategies`** — reframed. `CHoRUSReports` is now described as producing characterization reports returned to sites after submission, and `Chorus_SOP` as curation and delivery best-practice documentation — the bundle's own characterisations. The prior framing implied outlier removal, deduplication or error correction, none of which the bundle describes.

---

## 5. Left as-is, with reasons

**`license` omitted at top level in both records.** The bundle's MIT and Apache-2.0 licences attach to `chorus-ai` software repositories, not to the data. Dataset access is governed by a signed licensing agreement whose terms are not reproduced. The software licensing is recorded under `license_and_use_terms`, where it is accurate; the dataset-level slot stays empty because the bundle does not answer it. Verified identical in the core record.

**Conflicting admission counts kept separate.** The website's 50,000 released admissions and the September 2025 webinar's "over 45K unique admissions as of August 2025" are held as two attributed subsets. They are not averaged, reconciled or silently resolved in favour of either. Preserved in both records.

**Source typo preserved.** The contact address `cmccrary@mgh.havard.edu` reproduces a misspelling present in the project website. Fidelity to the bundle governs; the address is not silently corrected.

**`participant_compensation` omitted.** The $8,000 stipend and travel allowance in the bundle are AIM-AHEAD *trainee* benefits. They compensate programme participants, not human subjects whose clinical data compose the dataset. Out of scope for the referent.

**`regulatory_restrictions` omitted.** HIPAA and GDPR appear once, as topics of an AIM-AHEAD workshop on compliance for OMOP/FHIR data. That is a curriculum item, not a restriction asserted of this dataset.

**`at_risk_populations` omitted despite PICU and NICU admissions.** The dataset demonstrably includes minors. The slot, however, asks for protections, safeguards and assent procedures — and the bundle documents none. Recording the presence of minors here would populate the slot without answering it; the population itself is captured under `instances` and `subpopulations`.

**`creators` scoping retained.** Six named CHoRUS leadership members plus the consortium entity, one object per entity. NIH programme officials and AIM-AHEAD leadership named in the webinar are excluded — they lead adjacent programmes, not the creation of this dataset.

**Multivalued slots kept decomposed.** Where several entities were evidenced, each is a separate object. No collapsing of multiple creators into one `Creator`, or multiple applications into one `IntendedUse`.

---

## 6. Final state

| | Full | Core |
|---|---|---|
| Slots populated | 47 | 21 |
| Schema | `data_sheets_schema_all.yaml` (`Dataset`) | `data_sheets_schema_core_all.yaml` (`CoreDataset`) |
| Validation | pass | pass |

Reconciliation outcome: **converged.** Five slots vacated or narrowed in the full record; no unsupported claim carried into either file; no divergence remaining between the pair on referent, licensing treatment, or the handling of the conflicting admission counts. No prior D4D record was consulted at any phase.