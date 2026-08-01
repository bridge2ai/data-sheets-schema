# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 sources: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14)
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent declaration

`Dataset` admits one referent. The referent held across both records is **the CHoRUS multimodal critical-care dataset** — the AI-ready, controlled-access data resource assembled by the CHoRUS data generation project from 14 contributing hospitals and distributed via a cloud enclave.

Explicitly **not** the referent, though all three appear in the bundle and were the main source of Phase 3 mis-assignment risk:

- the **chorus-ai GitHub organization** and its 28 repositories (treated as tooling/provenance evidence *about* the dataset, surfaced through `machine_annotation_tools`, `preprocessing_strategies`, and `external_resources`, never as the dataset itself);
- the **AIM-AHEAD Bridge2AI for Clinical Care Training Program** (treated as an `existing_uses` / access-pathway fact, not as dataset composition);
- the **NIH award OT2OD032701** (treated as `funders`, not as the resource being described).

This choice was already consistent in both Phase 1 and Phase 2 outputs and required no correction.

---

## 2. What the audit found

Phase 3 returned 14 findings: 2 high, 5 medium, 7 low. All populated content traced to one of the four bundled sources; **no evidence of prior-D4D reuse was detected** in either record, and no content originated outside the declared bundle.

The findings clustered into five root causes:

1. **A shared scale error (high, ×2).** Both records stated in `human_subject_research` that the dataset is derived from "more than 100,000 critically ill patients." The bundle never asserts this as realized coverage. The NIH abstract frames 100,000+ as an *acquisition* challenge; chorus4ai.org places 100,000 admissions under **"Anticipated Final Dataset"** against **50,000** under "Current Released Dataset"; the September 2025 webinar states **"over 45K unique admissions"** as of August 2025. Both records already handled this conflict correctly in `known_limitations`, so each record contradicted itself.
2. **An unsupported value introduced in core only (medium).** `publisher` was set to `https://chorus4ai.org/`. The bundle names no publishing entity; a project homepage is not evidence of a publisher. The full record correctly omitted the slot.
3. **A systematic slot-semantics mismatch (medium, ×2).** `machine_annotation_tools` — defined as automated *annotation* tools — carried `privacy_scan_tool`, `CTP-deid`, `UF-Geocoding`, and `CHoRUSReports` in both records. The repository facts are well supported by the GitHub source; their placement in an annotation slot is not. Only the OHNLP toolkit (clinical notes "extracted and tokenized using OHNLP toolkit") is a defensible fit.
4. **Pair asymmetry (medium/low, ×4).** `at_risk_populations` and `version_access` appeared only in core; `third_party_sharing`, `participant_privacy`, and `direct_collection` only in full. The `at_risk_populations` case is the significant one: the bundle plainly supports it (released admissions span **ICU, PICU, and NICU**), so its absence from the full record was an evidenced omission, not a scope decision.
5. **Inferential stretches and one normalization (low, ×5).** Geographic attribution of the 20 academic centers to the United States; geocoding asserted as an *applied* preprocessing step; a negative claim about non-direct collection; a single `is_tabular` boolean over a documented mixed-structure resource; and silent typo-correction inside a quoted source string.

---

## 3. Changes made — full record

| Slot | Action | Rationale |
|---|---|---|
| `human_subject_research` | **Corrected.** Population description rewritten to: retrospective hospital records of critically ill ICU/PICU/NICU patients; ~50,000 admissions in the current released dataset (webinar reports over 45K unique admissions as of August 2025); 100,000 admissions stated as the anticipated final target. | Removes an assertion the bundle contradicts and aligns the slot with `known_limitations`, which already carried the correct target-vs-released distinction. |
| `at_risk_populations` | **Added**, mirroring the core record. Notes that released admissions include PICU and NICU populations, i.e. minors and neonates; that patients are critically ill and therefore may lack decisional capacity; and that the bundle documents community-facing ethics focus groups and patient-focused legal/ethical work on privacy and bias, but states **no** assent procedure, surrogate-consent process, or specific safeguard for these groups. | Evidenced by chorus4ai.org ("Patient admissions from ICU, PICU, and NICU") and the NIH abstract. Its absence was an omission against available evidence and an unjustified divergence from the paired record. The explicit negative on assent/safeguards prevents the addition from over-reading. |
| `machine_annotation_tools` | **Reduced** to the OHNLP toolkit entry only (clinical note extraction and tokenization; OHNLP open-source schema; access controlled; metadata planned). | Restores slot semantics. The other four entries are not annotation tools. |
| `is_deidentified` | **Extended** to carry the de-identification tooling facts displaced from `machine_annotation_tools`: existence of a `privacy_scan_tool` repository (privacy scan tool for medical records, Python) and a `CTP-deid` repository in the chorus-ai organization; imaging "de-id in process for larger cohort"; NIH abstract statement that data are transformed "using approaches that limit re-identification." Retains the existing explicit note that no de-identification standard, method detail, or residual-risk assessment is stated. | Re-homes supported facts into a slot whose definition they fit, without adding new claims. |
| `external_resources` | **Extended** with the `UF-Geocoding` and `CHoRUSReports` repositories as referenced repository resources, described by their own README text only. | Preserves the repository evidence displaced from `machine_annotation_tools` without asserting a function the bundle does not confirm. |
| `preprocessing_strategies` | **Reworded.** The geocoding entry no longer asserts that geocoding was applied to CHoRUS data; it now records that the organization hosts `UF-Geocoding` (forked from `bihorac-LAB/Exposome`), described as open-source code to geocode OMOP Location entities via DeGauss, and states that the bundle does not confirm this was run against the released dataset. | The bundle establishes repository existence, not application. |
| `direct_collection` | **Reworded.** Now states only what is sourced: the webinar describes "Retrospective data collection"; the GitHub SOP material describes site-level clinical data extracts created and submitted by 14 data-acquisition centers. The inference that data "are not collected directly from individuals for research purposes" was removed. | Negative framing was not stated in any source. |
| `known_biases` | **Corrected.** "20 academic centers in the United States" → "20 academic centers, of which 14 contribute as Data Acquisition centers"; geographic attribution removed. | The bundle locates only the *GitHub organization* in the United States and establishes US federal funding; it does not state the centers' geography. |
| `status` | **Corrected to verbatim quotation**, retaining the source spelling with a `[sic]` marker: "This repoitory [sic] is under review for potential modification in compliance with Administration directives." | Quoted source strings are not silently normalized. |

---

## 4. Changes made — core record

| Slot | Action | Rationale |
|---|---|---|
| `human_subject_research` | **Corrected**, identically to the full record. | Same root cause; resolves the record's internal contradiction with its own `known_limitations`. |
| `publisher` | **Removed.** | No publishing entity is named anywhere in the bundle. A project website URL is not publisher evidence. Restores agreement with the full record, which correctly omitted the slot. |
| `machine_annotation_tools` | **Reduced** to the OHNLP toolkit entry only. | Same slot-semantics correction as the full record. |
| `is_deidentified` | **Extended** with the displaced de-identification tooling facts (`privacy_scan_tool`, `CTP-deid`, imaging de-id in process, re-identification-limiting transformation), retaining the existing negative on standards and residual risk. | Keeps the pair aligned on where these facts live. |
| `version_access` | **Removed.** | The slot's content restated access-control facts already carried by `license_and_use_terms` and then concluded that the bundle says nothing about versioned or archival access. Where evidence is absent, omission is the correct answer; the slot was doing no work. Restores agreement with the full record. |
| `license_and_use_terms` | **Extended** with the access-request pathway: the GitHub overview names `dbold@emory.edu` and `jared.houghtaling@tuftsmedicine.org` for access requests; the training-program route requires a registration form and a signed licensing agreement, and notes a `.edu` email requirement for dataset access. | Closes the most substantive gap created by `third_party_sharing` having no core counterpart, without importing a slot the core reduction does not carry. |
| `preprocessing_strategies` | **Reworded**, identically to the full record. | Same over-reading of the geocoding repository. |
| `known_biases` | **Corrected**, identically to the full record. | Same unsupported geographic attribution. |
| `status` | **Corrected to verbatim quotation** with `[sic]`. | Same normalization defect. |

---

## 5. Left as-is, and why

- **`third_party_sharing` and `participant_privacy` remain full-only.** The core record is an intentional reduction, not a mirror. The substantive access facts that these slots carried have been folded into core `license_and_use_terms` (access contacts, licensing agreement, `.edu` requirement) and core `at_risk_populations` / `is_deidentified` (privacy protections), so no evidenced fact is now unique to the full record. The asymmetry is a scope decision, not an inconsistency.
- **`direct_collection` remains full-only.** After rewording it adds no fact beyond what core carries in `acquisition_methods`; duplicating it into the reduced record would add length without adding evidence.
- **`splits` remains full-only.** The holdout test set "sequestered for external validation" is described in the NIH abstract as a project deliverable with no partition sizes, boundaries, or membership criteria. It is thin enough to justify carrying in the full record only.
- **`is_tabular: false` retained in both records.** The audit is right that this flattens a mixed structure — the resource includes 1.6 billion rows of OMOP tabular EHR data alongside DICOM imaging, WFDB waveforms, and EDF+/Persyst EEG. But the slot is a plain boolean with no qualification mechanism, and the referent as a whole is a multimodal composite rather than a table. `false` is the less misleading of the two available values. The mixed structure is documented explicitly in `distribution_formats` and `file_collections`, where it can be stated rather than flattened.
- **The 50,000 / 45,000 / 100,000 conflict is retained as a conflict, not resolved.** `known_limitations` in both records continues to attribute each figure to its source and date (chorus4ai.org: 50,000 released, 100,000 anticipated; webinar: over 45K unique admissions as of August 2025) rather than selecting one. Per the uniform decision rules, disagreeing sources are represented, not silently reconciled.
- **All explicit "not stated in the bundle" negatives retained.** Both records carry these for IRB protocol number and approving body, consent and consent-revocation procedures, de-identification standard and residual re-identification risk, dataset license identifier (the MIT license in the GitHub README governs *software*, not the dataset, and both records say so), retention limits, errata, and update cadence. These are correct answers to absent evidence and were not converted into inferred content.
- **`citation`, `doi`, `download_url`, `version`, `total_file_count`, `total_size_bytes` remain unpopulated in both records.** The bundle gives a funding award number, a website, a GitHub org, and a "23 Tb" waveform figure — none of which is a dataset citation, DOI, direct download endpoint, version identifier, or a total across all collections. The 23 Tb figure is retained descriptively in `file_collections` rather than promoted to `total_size_bytes`, which would misrepresent a single-modality figure as a dataset total.

---

## 6. Final state

| | Full | Core |
|---|---|---|
| Schema | `data_sheets_schema_all.yaml` / `Dataset` | `data_sheets_schema_core_all.yaml` / `CoreDataset` |
| Populated slots | **56** | **29** |
| Slots added in Phase 4 | 1 (`at_risk_populations`) | 0 |
| Slots removed in Phase 4 | 0 | 2 (`publisher`, `version_access`) |
| Slots corrected in Phase 4 | 7 | 6 |
| Validation | **PASS** | **PASS** |

Both files validated with `linkml-validate` against their respective schema and target class after the Phase 4 edits.

**Reconciliation outcome: RESOLVED.** Both high-severity findings corrected in both records; the core-only unsupported value removed; the `machine_annotation_tools` slot-semantics defect corrected in both records with displaced facts re-homed rather than discarded; the one evidenced omission (`at_risk_populations`) added to the full record. Remaining asymmetries are deliberate core-reduction scope decisions with no evidenced fact left stranded in a single record. No prior D4D record was read or consulted at any phase; every retained claim traces to one of the four sources in the declared bundle.