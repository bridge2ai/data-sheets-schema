# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_crate_only.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. Both records resolve to **the CHoRUS RO-Crate Package**, identified by `https://doi.org/10.18130/V3/XNBOPG`, version `1.0 Beta`, published `2026-04-03`.

The crate graph also carries a crate-native root `@id` of `ark:59853/rocrate-chorus-ro-crate-package/`. The DOI was selected because the crate declares it as `identifier` and because both the AI-readiness assessment's `findable` and `persistent` criteria cite the DOI as the dataset's persistent identifier. The ARK is not asserted anywhere in either record; this is a deliberate single-referent choice, not an omission of contested evidence.

The two sub-crates (`CHoRUS RO-Crate EHR SubRoCrate`, `CHoRUS RO-Crate Waveforms SubRoCrate`) are modelled as `resources` in both records rather than as separate referents, consistent with their `isPartOf` linkage to the root.

---

## 2. What the audit found

The audit returned 26 findings: 2 high, 4 medium, 20 low. No fabricated entities, no cross-record referent drift, and no evidence of prior-D4D reuse. The verbatim-heavy governance and ethics slots — `rai:dataLimitations`, `rai:dataBiases`, `rai:intendedUseCases`, `rai:conditionsOfAccess`, `rai:dataCollection`, `rai:personalSensitiveInformation`, the IRB/ethical-review block, the maintenance plan, the copyright notice, and the HL7:2V confidentiality level — were all confirmed grounded in the declared bundle.

Defects clustered into four kinds:

1. **Boundary violations** — values asserted with no supporting statement anywhere in the bundle (`language`, `is_tabular`).
2. **Scoring-artifact inference** — a dataset property read out of an AI-readiness metric rather than a declared inventory (`total_file_count`).
3. **Slot-semantics stretches** — verbatim-supported text placed in slots whose documented meaning it does not match (`status`, `sampling_strategies`, `addressing_gaps`, `machine_annotation_tools`), plus mild over-specification in prose (`data_collectors`, `direct_collection`).
4. **Full/core divergence on identical evidence** — supported facts present in one record and silently absent from the other, and the same fact encoded structurally in one record and as prose in the other.

---

## 3. Changes made — full record

| Slot | Action | Reason |
|---|---|---|
| `language` | **Removed** | `en` is unsupported. The crate JSON-LD carries no `inLanguage` or equivalent field, and the AI-readiness file makes no language claim. The value was inferred from the metadata prose being written in English, which is a property of the documentation, not of the dataset. Under the provenance guard, omission is the correct answer. |
| `is_tabular` | **Removed** | No boolean is stated. The bundle's format evidence is mixed — `text/tab-separated-values` appears alongside `wfdb` and `.ipynb` — so neither `true` nor `false` is defensible. The dataset is explicitly multimodal (EHR, imaging, waveforms, tokenized text); collapsing that to a tabularity flag is inference. |
| `total_file_count` | **Removed** | `1477` was read from the AI-readiness string `99% of files have checksums (1469/1477)`, which counts checksum-bearing entities in the crate graph. The same file separately reports `1468 dataset(s) documented`, and the bundle explicitly states that file inventories were collapsed. The figure is a scoring artifact, not a declared file count. Qualification was considered and rejected as still asserting a dataset property the source does not make. |
| `data_collectors` | **Edited** | Removed the clause attributing harmonization coordination to the CHoRUS Data Pillar. The bundle names the Data Pillar only as `Primary maintainers: CHoRUS Data Pillar in collaboration with institutional data stewards`. The maintainer role is retained under `maintainers`; the collection role is not asserted. |
| `direct_collection` | **Edited** | Struck "harmonized centrally". The bundle states `Standardized harmonization to common data model` and that raw note text is `retained locally`; it never characterises harmonization as central. Retained the supported contrast between locally retained raw text and harmonized shared data. |
| `addressing_gaps` | **Removed** | The bundle contains no statement of a gap in existing datasets or knowledge. The populated object restated the crate `description` under a gap framing that the source never uses. The underlying descriptive content is already carried by `description` and `purposes`. |
| `sampling_strategies` | **Removed** | The object held the crate's `completeness` statement (`Interim release with partial data. Not all patients in the CHoRUS full cohort are included. No DICOM images are included.`). That describes release scope, not a sampling design. Placing it here implied a sampling methodology the bundle does not describe. The text is retained, once, under `missing_data_documentation`. |
| `status` | **Edited** | Replaced the `completeness` prose with the supported lifecycle value drawn from the version and release evidence (`1.0 Beta`, `datePublished: 2026-04-03`). The slot is documented for lifecycle state; the completeness text now lives only in `missing_data_documentation`, eliminating the three-way duplication the audit flagged. |
| `machine_annotation_tools` | **Edited** | Retained the OHNLP toolkit entry but narrowed its description to the stated function — tokenization of note and report text — rather than characterising it as producing annotations or labels, which the bundle does not claim. |
| `external_resources` | **Added** | Represents provenance artifacts the AI-readiness file explicitly documents and which were previously unused: 2 computation/experiment steps, 1 software instance, and 44 documented schemas within the crate provenance graph. Recorded as counts attributed to the AI-readiness assessment, not as named entities. |
| `total_size_bytes` | **Left absent — see §5** | |

**Full record populated slot count: 58** (down from 61).

---

## 4. Changes made — core record

| Slot | Action | Reason |
|---|---|---|
| `language` | **Removed** | Same violation as the full record. |
| `is_tabular` | **Removed** | Same violation as the full record. |
| `data_collectors` | **Edited** | Same correction as the full record: the "coordinates harmonization" attribution to the Data Pillar is removed. |
| `addressing_gaps` | **Removed** | Same unsupported gap framing as the full record. |
| `citation` | **Added** | The bundle states a formal recommended citation on the root crate and on both sub-crates: *The CHoRUS for Clinical Care AI Network. The Bridge2AI CHoRUS for Clinical Care AI Dataset: A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset, version 1.0 Beta. Harvard Dataverse, Apr. 2026.* This is unambiguously supported and its absence from core was an unexplained omission, not a scope decision. |
| `publisher` | **Added** | `B2AI CHoRUS` is declared on the root crate and repeated in the AI-readiness `computationally_accessible` criterion. Same reasoning as `citation`. |
| `resources` | **Edited** | Sub-crate content sizes were carried as free text inside `description` (`content size recorded as 18.136671 mb`, `1.201567472832 tb`). Converted to `total_size_bytes` integers to match the full record's encoding of the same evidence. The stated units are preserved in the conversion; no precision was invented. |
| `splits` | **Added** | The hold-out/development split statement from `rai:dataLimitations` was previously folded into `instances` prose. Promoted to a `splits` object so both records represent the same fact in the same place. |
| `third_party_sharing` | **Added** | The `rai:conditionsOfAccess` controlled-access framework was folded into `license_and_use_terms` prose. Promoted to a distinct object matching the full record. The license slot retains only the license/DUA statement. |
| `acquisition_methods` / `direct_collection` | **Split** | Core had merged the direct-collection fact into `acquisition_methods`. Separated to mirror the full record, since the bundle distinguishes the derivation of data from routine clinical care from the mechanisms of extraction and transformation. |

**Core record populated slot count: 34** (up from 31).

---

## 5. What was left as-is, and why

| Item | Disposition |
|---|---|
| `total_size_bytes` on the root dataset | **Left absent.** The root crate declares `contentSize: "1.2 tb"` — an explicitly rounded value, unlike the sub-crates' precise figures (`18.136671 mb`, `1.201567472832 tb`). Converting a one-significant-figure string to an integer byte count would assert precision the source does not carry. The asymmetry with the children is a faithful reflection of an asymmetry in the evidence. Noted here rather than silently resolved. |
| `resources` identifiers as `urn:uuid:…` | **Left as-is.** The crate's raw `@id` values are bare UUID strings, which are not valid `uriorcurie`. The URN prefix is the minimal schema-conformant normalisation and preserves the identifier verbatim in its final component. Recorded as a normalisation, not a source value. |
| `publisher` as a plain label | **Left as-is.** The slot range is `uriorcurie` but the only publisher evidence in the bundle is the string `B2AI CHoRUS`. Minting a URI for it would fabricate an identifier. The type-semantics mismatch is preferred over invention; both records validate. |
| `created_by: The CHoRUS for Clinical Care AI Network` | **Left as-is, now flagged.** The bundle carries three distinct actor statements: `author` (a 41-name investigator list with affiliations), `publisher` (`B2AI CHoRUS`), and the corporate author in the citation string. These are not merged. The full record represents the investigator list under `creators`, `B2AI CHoRUS` under `publisher`, and the corporate author under `created_by`. This preserves all three rather than selecting one; the disagreement is represented, not resolved. |
| `informed_consent` | **Left absent.** Consent-adjacent facts do exist — `IRB approval or waiver as appropriate` and `humanSubjectExemption: HIPAA exemption 4 ((45 CFR 46.104(d)(4))` — but the bundle describes a waiver/exemption posture for data repurposed from clinical workflows, not an informed-consent procedure. These facts are carried under `human_subject_research` and `ethical_reviews`, where they are accurate. Populating `informed_consent` would imply a consent process the evidence contradicts. |
| `variables`, `instances` detail, `subpopulations` | **Left absent.** File inventories were collapsed in this bundle by design, and the AI-readiness file explicitly records `statistics: has_content: false` — "No statistical characterization available." No variable-, instance-, or subpopulation-level facts are recoverable. |
| Duplicated bias text (`rai:dataBiases` / `rai:potentialBiases`) | **Left as a single `known_biases` set.** The two crate fields are byte-identical; representing them twice would imply two independent assessments. Not a merge of distinct entities. |
| Sub-crate `license: "See Data Use Agreement"` vs root `license: "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"` | **Both retained at their respective levels.** The sub-crate strings are less specific but not contradictory; each is recorded where it appears rather than normalised to the root value. |

---

## 6. Validation

| Record | Schema | Class | Result |
|---|---|---|---|
| Full | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` | `Dataset` | **PASS** |
| Core | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` | `CoreDataset` | **PASS** |

All object-range required keys satisfied: `resources` entries carry `id`; no `DatasetRelationship`, `FileCollection`, `RawDataSource`, or `VariableMetadata` objects were emitted, so their required keys are not in scope.

---

## 7. Outcome

Reconciled. Both records validate. The two high-severity boundary violations (`language`, `is_tabular`) and the one medium inference (`total_file_count`) were removed from both records rather than qualified. Three supported facts were restored to core (`citation`, `publisher`, `splits`) and two structural divergences were aligned (`third_party_sharing`, `direct_collection`, plus size encoding in `resources`). Four slot-semantics stretches were corrected in the full record by relocating or narrowing verbatim content rather than discarding it; two unsupported framings (`addressing_gaps`, the `sampling_strategies` placement) were dropped entirely. One previously unused evidence source — the crate provenance counts in the AI-readiness file — was added to `external_resources`.

Residual known divergences between full and core are scope-driven only: the core schema does not admit `external_resources`, `machine_annotation_tools`, `status`, or `missing_data_documentation`, so those full-record slots have no core counterpart. No factual claim appears in one record and is contradicted in the other.