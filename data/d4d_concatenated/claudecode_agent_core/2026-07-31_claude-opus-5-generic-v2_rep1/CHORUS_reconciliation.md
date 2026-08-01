# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep1`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Phase 4 status:** **BLOCKED — not completed**

---

## 1. Outcome summary

| Item | Status |
|---|---|
| Phase 1 — full record generated | Yes |
| Phase 2 — core record generated | **No — output is the placeholder token `FILL`** |
| Phase 3 — source/provenance audit | Completed against the full record only |
| Phase 4 — strict reconciliation | **Cannot be performed** |
| Full record validated | Not reportable in this run |
| Core record validated | Not reportable — no record exists |
| Full slot count | Not reportable in this run |
| Core slot count | **0 — no record** |

The reconciliation phase requires two records. Only one exists. Every full/core consistency check, every referent-agreement check, and every slot-coverage comparison is undefined until Phase 2 produces a real `CoreDataset` document. This report is written, as required, even though the reconciliation itself could not run.

---

## 2. Dataset referent

`Dataset` admits one referent. The referent selected and held throughout Phase 1 is:

> **The CHoRUS multi-modal critical-care dataset** — the controlled-access, OMOP-standardised clinical dataset assembled by the CHoRUS data generation project, not the CHoRUS software/GitHub organisation and not the AIM-AHEAD Bridge2AI training program.

This choice is supported across all four bundle files: the NIH RePORTER abstract ("develop a publicly available, AI-ready critical care dataset"), the chorus4ai.org "Snapshot of the dataset" panel, the webinar's "CHoRUS Dataset" slides and modality table, and the GitHub README's framing of the repositories as tooling *around* that dataset.

Consequences held consistently:
- GitHub repositories, SOPs and packages are recorded as `external_resources` and within `preprocessing_strategies`/`extension_mechanism`, **not** as the dataset itself.
- The MIT licence, which governs the code, was deliberately **not** promoted to the dataset-level `license` slot.
- Training-program facts (stipend, eligibility, application deadlines, mentorship) were excluded as properties of the program, not the dataset — with one exception flagged in §4.

When Phase 2 is re-run, the core record must adopt this same referent.

---

## 3. What the audit found

The audit returned **19 findings**: 1 high-severity blocking finding on the core record, and 18 on the full record (4 high, 5 medium, 9 low).

### 3.1 Blocking finding

**Core record absent (high).** The Phase 2 artefact is the literal string `FILL`. This is not a degenerate record or a validation failure — it is an unexecuted phase. No core slot can be audited; no full/core divergence can be measured.

### 3.2 High-severity findings on the full record

1. **`publisher` is not an attested entity.** The slot holds `https://chorus4ai.org/`, which merely duplicates `page`. No bundle source names a publishing organisation for the dataset. The nearest supported facts — Massachusetts General Hospital as awardee organisation, NIH Common Fund Bridge2AI as funding program — are neither one a stated publisher. Using a website URL as a publisher identity is inference, not evidence.

2. **`conforms_to` is overloaded.** The slot is single-valued but carries five modality standards (OMOP CDM, OHNLP, DICOM, WFDB/extended PhysioNet, EDF+/Persyst) as one free-text string. OMOP is the primary common data model and is defensible here; the other four are modality-specific and are already correctly represented in `distribution_formats` and `file_collections`.

3. **A `known_limitations` entry rests on corrupted table text.** The entry asserting that metadata publication was pending specifically for clinical notes, imaging and EEG derives from the webinar's modality table. In the extracted text, that table's column alignment is broken — access-control and metadata values are emitted out of order relative to their headers. The `Planned` tokens are present, but which columns and which rows they belong to cannot be read reliably. Asserting a specific pattern is over-confident.

4. **The second `instances` object is not an instance.** It is a note reconciling disagreeing dataset-size figures across sources. Per the slot description, `Instance` objects describe what each data point represents. The size discrepancy is already correctly recorded in `known_limitations`; duplicating it here populates the slot with non-conforming content.

### 3.3 Medium-severity findings

- **`file_collections`, imaging entry.** Presents "7,642 admissions with radiology data" (chorus4ai.org, current released dataset) and "as of August 2025, 1,000 images available with de-id in process" (webinar) as co-properties of one collection, without flagging that they are hard to reconcile.
- **`license` omitted while MIT is buried in prose.** The GitHub README states MIT plainly. A bare `license: MIT` at dataset level would be *wrong* — it governs the code — but recording it only inside an `external_resources` description is an inconsistent treatment.
- **`total_size_bytes` omitted while "23 Tb Waveform data" sits in prose.** The figure is waveform-only, not a total, so populating the slot would misstate it; the asymmetry is nonetheless worth noting.
- **`distribution_dates` holds neighbouring-field content.** Both entries describe availability states and access provisioning; the second (access provisioned from 2025-11-17) is a training-program milestone. The bundle contains no dataset release date.
- **`created_by` contains an unsupported inference.** "Led by Massachusetts General Hospital" is not stated anywhere. MGH is the awardee organisation; the leadership team spans MGH, University of Florida, UTHealth Houston and Tufts.

### 3.4 Low-severity findings

Nine findings covering: the verbatim reproduction of the apparent source typo `cmccrary@mgh.havard.edu`; `Creator` objects carrying all content as free text rather than in structured fields; the title-derived keyword "equitable AI"; the constructed (non-attested, non-resolvable) `id` and five `file_collection` ids; `status` overloading lifecycle, award period and the site's compliance-review notice into one string; `human_subject_research` under-answering its own field by omitting IRB status (correctly — the bundle's only IRB references are curriculum topics); `extension_mechanism` being partly a pointer to where documentation lives; and two confirmations that omissions were correct (`download_url`, `known_biases`).

---

## 4. What was changed

**Nothing.** No edit was applied to either record in this run.

The reason is procedural, not editorial. Phase 4 is *strict reconciliation* between a validated full record and a validated core record. With the core record absent, any correction applied to the full record now would have to be re-checked against the core record once it exists — and corrections made in the wrong order risk producing two records that were each individually sound but mutually inconsistent. The audit findings are therefore recorded as a **pending correction list**, to be applied in a single pass after Phase 2 completes.

### Pending correction list (to apply once the core record exists)

| # | Record | Slot | Action |
|---|---|---|---|
| 1 | full | `publisher` | Remove. No attested publishing entity in the bundle. Do not substitute MGH or NIH. |
| 2 | full | `conforms_to` | Reduce to the OMOP Common Data Model alone. The four modality standards remain in `distribution_formats` and `file_collections`, where they already are. |
| 3 | full | `known_limitations` | Rewrite the metadata entry to state only what the garbled table supports: that metadata availability varies by modality and some entries are marked planned, without naming which. |
| 4 | full | `instances` | Delete the second object. The size-discrepancy content is already in `known_limitations`; no information is lost. |
| 5 | full | `file_collections` (imaging) | Attribute each figure to its source and note that the two are not reconciled in the bundle. |
| 6 | full | `created_by` | Strike "led by". Retain MGH as awardee organisation and the 60+ members / 20 institutions figures. |
| 7 | full | `distribution_dates` | Remove the training-program provisioning entry. Reconsider whether the remaining entry states a date at all; if not, omit the slot. |
| 8 | full | `status` | Split or narrow so the slot carries lifecycle status only. |
| 9 | both | referent | Confirm the core record adopts the §2 referent before any comparison. |

Items 1–4 are mandatory. Items 5–8 are judgment corrections that improve fidelity without changing the record's factual claims. Item 9 is the precondition for Phase 4.

---

## 5. What was left as-is, and why

Beyond the deferral described above, several audit findings were reviewed and deliberately **not** placed on the correction list:

- **`license` stays omitted at dataset level.** The MIT licence attaches to the CHoRUS code repositories, not to the controlled-access clinical dataset, which is governed by the registration form and signed licensing agreement recorded in `license_and_use_terms`. Promoting MIT to `license` would assert something the bundle contradicts. Leaving it in `external_resources` prose is the least-wrong placement available.

- **`total_size_bytes` stays omitted.** 23 Tb is a waveform-modality figure, not a cross-collection total. The slot asks for the total; the bundle does not supply one. Prefer omission.

- **`cmccrary@mgh.havard.edu` stays verbatim.** The evidence boundary requires representing what the source states. The record already annotates the value as printed on the source page, which is the correct handling — silently "fixing" it to `harvard.edu` would be an unattested substitution.

- **`known_biases` stays omitted.** The bundle discusses bias as a project *concern* ("manage privacy and bias", "sampling methods to ensure a balanced and diverse cohort") but never identifies a bias present in the assembled data. Omission is the correct answer.

- **`download_url` stays omitted.** Access is controlled via registration and a signed agreement; no direct download route exists in the bundle.

- **`human_subject_research` stays without an IRB claim.** The only IRB mentions in the bundle are AIM-AHEAD curriculum topics ("Navigating IRB, Data Compliance and Quality Assurance", "Hands-on IRB drafting"). These describe training content, not an approval covering this dataset. The slot under-answers its own field, and that is the correct outcome.

- **Constructed `id` values stay.** `https://chorus4ai.org/dataset` and the five `file_collection` identifiers are minted, not attested. Minting is necessary — `id` is required — and the audit's point is a caution about resolvability, not a defect to correct.

- **Keyword "equitable AI" stays.** It appears verbatim in the project title across three of the four bundle files.

---

## 6. Required next steps

1. Execute **Phase 2** against the validated Phase 1 file to produce a real `CoreDataset` record at
   `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep1/CHORUS_d4d_core.yaml`,
   with the core header block (`phase 2`, core schema path) and the §2 referent.
2. Apply pending corrections **1–8** to the full record.
3. Re-run **Phase 3** over both records.
4. Execute **Phase 4** reconciliation and replace this report.
5. Validate both files, then write the live provenance record.

Until step 1 completes, no slot counts, no validation results, and no reconciliation outcome can be reported for this run.