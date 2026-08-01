# CHORUS — D4D Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_crate_only.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three nested crate entities:

| Entity | `@id` | Role |
|---|---|---|
| CHoRUS RO-Crate Package | `ark:59853/rocrate-chorus-ro-crate-package/` | root; carries all `rai:*`, ethics, access, governance evidence |
| CHoRUS RO-Crate EHR SubRoCrate | `08cf7419-b94d-4508-8f64-c99c557351d7` | `hasPart` of root |
| CHoRUS RO-Crate Waveforms SubRoCrate | `b9b41c72-0895-4ec2-9e39-8de2a83abcd6` | `hasPart` of root |

**Decision (held unchanged through Phase 4):** the referent is the **root CHoRUS RO-Crate Package**, identified by its `identifier` DOI `https://doi.org/10.18130/V3/XNBOPG`. The two sub-crates are represented as `resources` entries, not as separate `Dataset` records and not merged into the root's claims. Substantially all substantive evidence in the bundle (`rai:dataLimitations`, `rai:dataBiases`, `rai:intendedUseCases`, `rai:conditionsOfAccess`, `rai:maintenancePlan`, `rai:personalSensitiveInformation`, IRB block, `completeness`, `confidentialityLevel`) attaches only to the root entity; the sub-crates carry description, size, and boilerplate. This choice is applied identically in both records.

---

## 2. Audit summary

The audit returned **18 findings**: 3 medium, 11 low, 4 informational.

No prior-D4D content, no out-of-bundle content, and no document-corpus content was detected in either record. Author names and the 15 institutional affiliations map exactly to the crate `author` string. The verbatim `rai:*` blocks, IRB protocol `#2022P000707`, `humanSubjectExemption`, `fdaRegulated`, `confidentialityLevel: HL7:2V`, copyright notice, funder `NIH Common Fund OT2OD032701`, and the sub-crate structure were all confirmed faithful to source.

Defect classes found:

1. **Unsupported values** — content asserted with no basis in the bundle (`language`, `total_file_count`).
2. **Supported omission** — `citation` present in source and in the full record, absent from core.
3. **Slot-semantics mismatch** — `machine_annotation_tools`, `sampling_strategies`, `addressing_gaps`, `anomalies`, `download_url`.
4. **Cross-record placement divergence** — the same source sentence slotted differently in full vs. core (`splits`/`sampling_strategies`, `participant_privacy`/`data_protection_impacts`, `intended_uses`/`other_tasks`).
5. **Range risk** — `publisher` label supplied where `uriorcurie` is declared.

---

## 3. Changes applied — full record

| Slot | Action | Rationale |
|---|---|---|
| `language` | **Removed** | The bundle contains no `inLanguage` declaration and no natural-language statement. `en` was inferred from the prose being English. Under the omission-over-inference rule, an absent slot is the correct answer. |
| `total_file_count` | **Removed** | `1477` was taken from the AI-readiness string `"99% of files have checksums (1469/1477)"`. That denominator is a checksum-coverage population, not a declared file count, and the crate's file inventories were explicitly collapsed in this bundle. Not a stated dataset fact. |
| `download_url` | **Removed** | `https://chorus4ai.org/dataset/` is the sub-crates' `contentUrl` and functions as a landing page — the same host path already populates `page`. The slot requires a direct data URL. The bundle affirmatively states access is enclave-restricted with "no raw data export permitted unless explicitly approved," so no direct download URL exists. Access route retained in `page` and `license_and_use_terms`. |
| `addressing_gaps` | **Removed** | The bundle makes no claim that existing datasets are inadequate or that a research gap is filled. The single entry paraphrased the crate `description` and duplicated `purposes`. Interpretive, not evidenced. |
| `sampling_strategies` | **Removed** | The entry restated `completeness` ("Interim release with partial data… No DICOM images are included"), which is release scope, not sampling methodology. No inclusion criteria, cohort definition, or selection procedure appears anywhere in the bundle. Content is already carried correctly in `status` and `missing_data_documentation`. |
| `machine_annotation_tools` | **Reduced to one entry** | RSNA Clinical Trial Processor and IbisWorks EICON are described in `rai:dataCollection` as imaging-metadata and pixel-level **de-identification** tooling, never as annotation tooling. Both remain represented in `preprocessing_strategies` and `is_deidentified`. Only the OHNLP toolkit (note/report tokenization) is retained as an automated annotation tool. |
| `anomalies` | **Reduced to one entry** | Retained the variable-sampling-rate anomaly, which the crate states independently under `rai:dataCollectionMissingData`. Removed the "institutional heterogeneity in coding" entry (sourced only from `rai:dataLimitations`, already in `known_limitations`) and the MNAR entry (sourced only from `rai:dataBiases`/`rai:potentialBiases`, already in `known_biases`). Prevents one source bullet being asserted under three slots. |
| `confidential_elements` | **Reworded** | The claim that raw note and report text "is not distributed" is a corollary the bundle never states. Reworded to the source formulation: raw text is "retained locally across participating institutions," with tokenized text harmonized via the OHNLP toolkit. |
| `known_limitations` | **Two entries added** | The AI-readiness assessment supplies two documentation limitations the record had dropped: (a) 8 of 1477 files lack checksums (`"99% of files have checksums (1469/1477)"`); (b) no statistical characterization is available (`statistics.has_content: false`, "To add statistics, set 'contentSize' and/or 'hasSummaryStatistics'"). Both are in-bundle and material to reuse. |
| `total_size_bytes` | **Added — `1201585609503`** | Derived by summing the two sub-crate `contentSize` values: Waveforms `1.201567472832 tb` (1,201,567,472,832 B) + EHR `18.136671 mb` (18,136,671 B). The digit patterns are byte-exact under decimal TB/MB, which is the reading the values themselves indicate. **Stated assumption:** decimal (10¹²/10⁶) units, not binary. The root entity's rounded `1.2 tb` is consistent with this sum. Prose size statements retained in `distribution_formats`. |
| `external_resources` | **One entry added** | The crate root's own `@id`, `ark:59853/rocrate-chorus-ro-crate-package/`, appeared nowhere in the record once the DOI was chosen as `id`. Added as an external resource so the ARK identifier is not silently lost. |

---

## 4. Changes applied — core record

| Slot | Action | Rationale |
|---|---|---|
| `citation` | **Added** | The crate states a citation verbatim on all three entities: *"The CHoRUS for Clinical Care AI Network. The Bridge2AI CHoRUS for Clinical Care AI Dataset: A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset, version 1.0 Beta. Harvard Dataverse, Apr. 2026."* The full record carried it; the core record dropped it with no evidentiary basis. Restored verbatim. |
| `language` | **Removed** | Same basis as the full record. |
| `addressing_gaps` | **Removed** | Same basis as the full record. |
| `download_url` | **Removed** | Same basis as the full record. |
| `other_tasks` | **Removed** | The four entries (retrospective hypothesis testing, comparative effectiveness research, trustworthy-AI methods research, trial emulation/powering) are enumerated verbatim in the same record's `intended_uses` and appear in the bundle inside a single undifferentiated `rai:intendedUseCases` block. The bundle draws no "beyond original intent" distinction, so `other_tasks` asserted one the source does not make, and duplicated content within the record. The full record slotted all of these under `intended_uses` only; core now matches. |
| `sampling_strategies` → `splits` | **Re-slotted** | The completeness content was removed for the same reason as in the full record. The hold-out statement — *"Hold-out splits are available for testing; training and validation in development splits require internal mechanisms to avoid overfitting"* — was moved from `sampling_strategies` to `splits`, matching the full record's placement of the identical sentence. Net slot count unchanged; cross-record divergence eliminated. |
| `machine_annotation_tools` | **Reduced to one entry** | Same basis as the full record. |
| `anomalies` | **Reduced to one entry** | Same basis as the full record. |
| `confidential_elements` | **Reworded** | Same basis as the full record. |
| `known_limitations` | **Two entries added** | Same basis as the full record. |

---

## 5. Left as-is, with reasons

| Slot / issue | Disposition | Reason |
|---|---|---|
| `publisher: "B2AI CHoRUS"` (range `uriorcurie`) | **Retained verbatim in both** | This is the exact string the crate supplies in its `publisher` field; the bundle offers no URI or CURIE for the publishing entity. Coining one would be fabrication. Both records were run through `linkml-validate` with the value in place and both pass, so the range risk is latent rather than blocking. Flagged here so the label is not mistaken for a resolvable identifier. |
| `data_protection_impacts` merge in core | **Retained** | The audit flagged that core folds the full record's `participant_privacy` content (layered protection, RBAC, MFA, audit logging, export restriction) into `data_protection_impacts`. Checked against the `CoreDataset` slot inventory: `participant_privacy` is not available in the core projection, so the merge is forced, not arbitrary. The merged entry's text was tightened to distinguish the standing safeguards (from `rai:personalSensitiveInformation` and `rai:dataCollection`) from the one genuine assessment statement — *"Re-identification risk is periodically assessed and mitigation strategies updated as needed."* The full record keeps the two separated. |
| `issued: 2026-04-03T00:00:00Z` | **Retained in both** | The `00:00:00Z` component is datatype coercion required by the `datetime` range, not a factual claim about time of issuance. |
| Conflicting publication dates (`2026-04-03` vs. `03/04/2026`) | **Retained as handled** | The root and Waveforms sub-crate give `datePublished: 2026-04-03`; the EHR sub-crate gives `03/04/2026` and the root `releaseDate` gives `03/04/2026`. The ambiguity (D/M/Y vs. M/D/Y) is disclosed in a `distribution_dates` entry rather than silently resolved, and the EHR sub-resource's `issued` is deliberately left unpopulated. This satisfies the disagreement rule: represent what the evidence states, do not silently select. |
| `conforms_to_schema` — "44 documented schemas" | **Retained with attribution** | Sourced from the AI-readiness self-assessment, not the crate graph, and the underlying schema list is not present in this bundle. Retained because it is in-bundle, but the wording explicitly attributes it ("The AI-readiness assessment of the crate records 44 documented schemas") rather than asserting it as an independently verified property. |
| `external_resources` — Bridge2AI organization | **Retained as-is; verified** | The root's `isPartOf` target `ark:59852/organization-bridge2ai-s6VouUf8Gkm` is an Organization entity, not a dataset. Both records correctly route it to `external_resources` rather than fabricating a `parent_datasets` or `related_datasets` edge. No change. |
| `id` = DOI rather than root ARK | **Retained** | `https://doi.org/10.18130/V3/XNBOPG` is the crate's declared `identifier` and is the more resolvable, more citable handle; it is also what the AI-readiness assessment names as the persistence anchor. The ARK is no longer lost — see the `external_resources` addition in §3. Applied identically in both records. |
| `is_tabular` | **Remains unpopulated in both** | The dataset is explicitly multimodal (EHR/OMOP tables, WFDB waveforms, imaging, tokenized text). A single boolean would misrepresent it, and the bundle makes no tabularity claim. |
| Sub-crate `resources` entries | **Retained** | EHR and Waveforms sub-crates kept as `resources` with their own name, description, version, size, and `contentUrl`. Not promoted to `parent_datasets` (the direction is `hasPart`, not `isPartOf`) and not collapsed into the root. |

---

## 6. Cross-record consistency check

After reconciliation, the paired records agree on: referent and `id`; `citation`; the absence of `language`, `addressing_gaps`, `download_url`, and `sampling_strategies`; the single-entry `machine_annotation_tools`; the single-entry `anomalies`; the placement of the hold-out statement in `splits`; the `confidential_elements` wording; and the two added `known_limitations`.

One documented, non-factual divergence remains: privacy safeguards occupy `participant_privacy` + `data_protection_impacts` in the full record and `data_protection_impacts` alone in the core record, because `participant_privacy` is not exposed by `CoreDataset`. This is a schema-projection artefact, not a content difference; no fact appears in one record and not the other.

---

## 7. Final state

| | Before Phase 4 | After Phase 4 |
|---|---|---|
| Full record — populated slots | 61 | **57** |
| Core record — populated slots | 37 | **34** |

Full: 5 slots removed (`language`, `addressing_gaps`, `sampling_strategies`, `download_url`, `total_file_count`), 1 added (`total_size_bytes`); 5 slots revised in place.
Core: 4 slots removed (`language`, `addressing_gaps`, `other_tasks`, `download_url`), 1 added (`citation`), 1 re-slotted (`sampling_strategies` → `splits`); 4 slots revised in place.

**Validation**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d.yaml
→ PASS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d_core.yaml
→ PASS
```

**Provenance record**

```
poetry run d4d provenance record --project CHORUS \
  --method claudecode_agent_crate_only \
  --label 2026-07-31_claude-opus-5-api-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/CHORUS_crate_only.txt
→ recorded
```

**Provenance guard:** no previously generated D4D record was read or consulted at any phase. Factual inputs were the declared bundle and the two schema files only.

**Outcome:** reconciled — 3 medium findings resolved, 11 low findings resolved or documented, 4 informational findings verified and retained.