# CM4AI D4D Reconciliation Report

**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep2`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep2/CM4AI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep2/CM4AI_d4d_core.yaml`

---

## 1. Referent declaration

The declared bundle describes two nested things: the CM4AI **project** (a four-year NIH Bridge2AI Data Generation Project, 2022-09-01 to 2026-08-31, with six modules and a portal reporting cumulative counts) and a series of quarterly **data releases**, of which June 2026 is the most recent.

**Chosen referent: the June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`.**

Rationale: this is the only entity in the bundle with a persistent identifier, a licence, a file manifest, checksums, a publication date, and an authoritative self-description ("This dataset is the June 2026 Data Release of Cell Maps for Artificial Intelligence"). The project has no DOI in the bundle. `Dataset` admits one referent, and the release is the one the evidence best supports as a *dataset*.

This choice is now held consistently. Corrections made in this phase to enforce it are recorded in §3.

---

## 2. Audit findings and disposition — summary table

| # | Severity | Slot | Disposition |
|---|---|---|---|
| 1 | high | core `distributions` | **Removed**; content redistributed |
| 2 | high | full `id` / referent straddle | **Corrected** — description and purposes rescoped |
| 3 | high | full `total_file_count` | **Corrected** to 10 with `file_count` populated per collection |
| 4 | medium | full `creators` collapse | **Expanded** to per-person Creator objects |
| 5 | medium | minted org CURIEs | **Retained**, caveat strengthened |
| 6 | medium | minted grant CURIEs | **Retained**, caveat strengthened |
| 7 | medium | `FileCollection.file_count` / `total_bytes` | **Populated** |
| 8 | medium | checksum duplication | **Resolved** — canonical location fixed |
| 9 | medium | core `notes` holding citation | **Moved** to `citation` |
| 10 | medium | core `relationships` dissolved | **Restored** to slot |
| 11 | medium | core `variables` dropped | **Restored** |
| 12 | medium | core `direct_collection` folded away | **Restored** |
| 13 | low | full `created_by` | **Corrected** |
| 14 | low | `status: Beta` | **Corrected** |
| 15 | low | date time-components | **Corrected** |
| 16 | low | `license` string form | **Retained**, unchanged |
| 17 | low | `publisher` URI | **Retained**, caveat added |
| 18 | low | `data_substrate` terms | **Retained**, caveat added |
| 19 | low | `data_topic` terms | **Changed** (one), caveat added |
| 20 | low | `hipaa_compliant` inference | **Removed** |
| 21 | low | `conforms_to_standard` partial coverage | **Retained**, caveat added |
| 22 | low | `collection_timeframes` dates | **Removed** from structured fields |
| 23 | low | Dataverse Subject in `keywords` | **Removed** |
| 24 | low | `existing_uses[0]` directional claim | **Softened** |
| 25 | low | `known_biases[1]` provenance | **Retained**, caveat added |
| 26 | low | `maintainers[].role` inconsistency | **Corrected** |
| 27 | low | `download_url` omitted | **Populated** |
| 28 | low | consent-family omissions | **Retained**, documented here |
| 29 | low | other omissions | **Retained**, documented here |
| 30 | low | U2OS methodological bleed | **Retained**, caveat sharpened |
| 31 | low | core `source_caveats` unverified claim | **Rewritten** |
| 32 | low | project statistics in release description | **Corrected** |

---

## 3. Changes made

### 3.1 Core `distributions` block removed (finding 1)

The core record contained a `distributions:` list of ten objects keyed on `path`, `md5`, `format`, `media_type`, `compression`, `conforms_to`, `conforms_to_standard`. Neither the slot nor a `Distribution` range class appears in the schema material available to this run, and none of those keys is declared for any listed range class. Under #380 this is invented structure.

**Action:** the block was deleted. Its content was redistributed:

- Format and media-type facts → `distribution_formats` (one `DistributionFormat` object, with `format: ZIP archives (immunofluorescence TIFF/PNG image sets; tabular mass-spectrometry results; RO-Crate JSON metadata)`, `media_type: application/zip`, `download_url` and `access_urls`).
- Per-file MD5 checksums → `file_collections[].notes` in the full record only; the core record now carries a single sentence in `notes` recording that per-file MD5 checksums are published on the Dataverse landing page, without transcribing all ten.
- File count → `total_file_count`.
- `compression: zip` → promoted to the top-level `compression` slot, which is declared and enum-valid.
- `conforms_to` / `conforms_to_standard` → already present at top level; the duplicate per-file copies were dropped.

### 3.2 Referent discipline enforced (findings 2, 32)

`id` remains `https://doi.org/10.18130/V3/HIGT4C`. The record around it was brought into line.

**Changed in both records:**

- `description` no longer opens with a project summary. It now opens: *"The June 2026 Data Release (Beta) of Cell Maps for Artificial Intelligence (CM4AI)…"* and describes the ten archives actually in this release.
- The portal aggregate statistics (1,374 protein interactions; 53,788 immunofluorescent images; 7,023 proteins investigated; 11,739 genes targeted; 21.4 TB) were **removed from `description`**. They describe cumulative project output across all releases, not this release's contents, and their presence inside a release-scoped description invited exactly the conflation the caveat warned against. They are now recorded once, explicitly labelled, in `notes`.
- `purposes` and `addressing_gaps` were rewritten to state the purposes *of the release* — making these multimodal measurements available as AI-ready packaged data — with the project's own stated mission attributed to the project rather than asserted of the release.
- `tasks` retained, since the bundle's "Intended Use" section is written about this dataset specifically.

### 3.3 File counts and sizes (findings 3, 7)

`total_file_count: 10` was ambiguous — ten collections, ten files, coincidentally equal. It is now unambiguous:

- Each of the ten `FileCollection` objects carries `file_count: 1` (each is a single published ZIP artefact).
- Each carries `total_bytes`, converted from the repository-reported size. Because Dataverse reports rounded sizes (3.8 GB, 113.3 KB), the byte values are **approximations** and each collection's `notes` now states the source string it was converted from, e.g. `total_bytes: 3800000000` with `notes: "Repository-reported size 3.8 GB; byte value is a conversion of that rounded figure. MD5: 6c1a86520eec2696ec19444eb8a8b428."`
- `total_file_count: 10` retained, now consistent with the aggregation rule in the slot description.
- `total_size_bytes` **remains omitted**: summing ten rounded figures would present false precision at the dataset level, and the bundle gives no authoritative total.

Size-in-prose was removed from the collection `description` fields, which now describe content only.

### 3.4 Creators expanded (finding 4)

The single institutional Creator object absorbing forty-seven authors was replaced. The bundle names every author with affiliation and, for most, an ORCID.

**Action:** `creators` now contains one Creator object per named author for whom the bundle supplies an ORCID and affiliation, with `principal_investigator` populated as a `Person` (name + ORCID as `id`) and `affiliations` as a single-element `Organization` list. Authors without ORCIDs in the source (Axelsson, Chinn, Fall, Johannesson, Khaliq, Muralidharan, Pan, Polacco, Zhang) are represented with name and affiliation and no `id`, rather than being dropped or given a minted identifier.

Trey Ideker additionally carries `credit_roles: [supervision, funding_acquisition, project_administration]`, supported by the NIH RePORTER PI designation and the Dataverse Point of Contact field. No other credit roles were assigned: the bundle's Nature contributions statement covers a *different* study (see §5.3) and cannot be transferred.

### 3.5 Checksum canonicalisation (finding 8)

Checksums appeared in two places with neither canonical. Resolved:

- **Full record:** MD5 digests live in `file_collections[].notes`, one per collection, alongside the size-provenance note. This is the residual slot on the object that owns the file.
- **Full record `distribution_formats[].checksum`:** now holds only `MD5` (the algorithm), which is what the field's name asks for, not a prose summary.
- **Core record:** carries a single sentence in `notes` recording that per-file MD5 checksums are published, without transcription.

### 3.6 Core projection losses restored (findings 9–12)

Four slots had been dissolved into prose during projection. Each is declared on `CoreDataset` and each has been restored:

- **`citation`** — the full 47-author Dataverse citation moved out of `notes` into the slot that declares it.
- **`relationships`** — the cross-modality linkage statement (modalities join on protein/gene identity; coverage overlaps only partially) restored as a `Relationships` object. It is a dataset-level statement and does not belong inside one `Instance`'s notes.
- **`variables`** — the nine `VariableMetadata` entries restored. The bundle explicitly describes the four immunofluorescence channels (DAPI/blue → nucleus; calreticulin/yellow → endoplasmic reticulum; tubulin/red → microtubules; green → protein of interest), the three treatment conditions, the four cell types, and the six-guides-per-gene CRISPRi design. These are stated facts, not inferences.
- **`direct_collection`** — restored with `is_direct: false` and the ATCC / HipSci provenance. The boolean assertion that no data were collected directly from individuals is a substantive claim that was being lost.

`sampling_strategies[0].source_data` was correspondingly trimmed to describe sampling only.

### 3.7 Smaller corrections

**`created_by`** (13) — changed from *"Cell Maps for Artificial Intelligence (CM4AI) consortium"* to *"Cell Maps for Artificial Intelligence (CM4AI)"*. "Consortium" was an interpolation; the bundle says "collaboration".

**`status`** (14) — changed from `Beta` to `published`. The slot description gives the register as draft/published/deprecated. The release is published (V2, files public, DOI minted). The authors' own "Beta" label is a maturity claim, not a publication status, and is now recorded in `description` and in `known_limitations` where it belongs.

**Dates** (15) — fabricated `T00:00:00Z` components removed:
- `issued: 2026-06-17` (Dataverse Publication Date — supported)
- `created_on` **removed**. The bundle gives "Data Creation Date 2025-02-27" and "Deposit Date 2025-02-27" as the same value; treating a deposit date as a creation date is an inference, and 2025-02-27 predates this release's content in any case.
- `last_updated_on: 2026-07-15` retained as a date, with a `source_caveats` note that this is the publication date of the three image archives, the latest file-level activity in the record, and not a dataset-level modification date the bundle asserts.

**`hipaa_compliant`** (20) — **removed**. The record's own caveat conceded HIPAA is never discussed in the sources. Under the omission-over-inference rule an enum value should not be minted from silence. The two supported statements ("Human Subjects: No", "FDA Regulated: No") remain in `regulatory_restrictions`.

**`collection_timeframes`** (22) — structured `start_date` / `end_date` **removed**. 2022-09-01 and 2026-08-31 are the NIH award period from RePORTER, not a collection window. `timeframe_details` retains the award period as prose, explicitly labelled as such, and states that the bundle does not report actual acquisition dates.

**`keywords`** (23) — "Medicine, Health and Life Sciences" removed. It is the Dataverse *Subject* field, a different metadata element. It now appears in `notes`.

**`existing_uses[0].examples`** (24) — softened from an assertion that the released atlas "underlies" the Nourreddine preprint to a statement that the Dataverse record lists that preprint as a Related Publication describing a CRISPRi perturbation atlas of human iPSCs. The directional claim was not in the bundle.

**`maintainers[].role`** (26) — made consistent. All four maintainers are named individuals; all now carry `role: researcher`, with the institution in `maintainer_details`. Using `academic_institution` for a named person was a category error.

**`download_url`** (27) — populated with `https://dataverse.lib.virginia.edu/api/access/datafile/`, the Data Access API pattern the bundle supplies. `page` retains the landing page. The slot description distinguishes the two.

**`data_topic`** (19) — the AP-MS instance changed from `B2AI_TOPIC:21` (Networks And Pathways) to `B2AI_TOPIC:26` (Protein), closer to what the sources say ("protein-protein interaction"). `B2AI_SUBSTRATE:19` (Microscale Imaging) retained for the IF images: the bundle describes confocal subcellular imaging, and 19 is more specific than the generic `15` (Image).

**Core `source_caveats`** (31) — rewritten. The previous text justified the `distributions` block with an unverifiable claim about what the core schema does and does not declare. Since that block is gone and the claim could not be checked, the assertion was deleted. The caveat now records only verifiable things.

---

## 4. Retained without change — and why

### 4.1 Minted CURIEs (findings 5, 6)

Fifteen identifiers (`cm4ai:org/…`, `cm4ai:grant/…`) are locally minted under an undeclared prefix. **Retained.**

`Organization` and `Grant` require `id` of range `uriorcurie`. The bundle supplies exactly one institutional URI (`https://ror.org/0153tk833`, UVA) and gives grants as bare strings. The alternatives were: omit the objects entirely (losing supported facts about funders and affiliations), or invent ROR IDs from memory (a far worse violation — fabricating identifiers that resolve to real records the bundle never cited).

Minting a transparently local, non-resolving CURIE is the least-harm option: it satisfies the range without asserting anything about an external registry. The top-level `source_caveats` now states this explicitly and enumerates which identifier is source-supported.

### 4.2 `license` (16), `publisher` (17)

`license: CC-BY-NC-SA-4.0` normalises "CC BY-NC-SA 4.0". Retained: `license` is a string slot whose description gives "CC-BY-4.0" as the exemplar form, so the normalised identifier matches the schema's own register. The licence URL the bundle supplies appears in `license_and_use_terms.license_terms`.

`publisher: https://dataverse.lib.virginia.edu/` retained; a `source_caveats` note now records that the bundle's publishing hierarchy is four levels deep and that the repository root was chosen as the publisher identity.

### 4.3 `data_substrate` terms (18)

All four retained. `B2AI_SUBSTRATE:59` (SEC-MS Data) and `:64` (Perturb-seq Data) are exact. `:56` (Immunofluorescence Image) is exact. `:58` (Mass Spectrometry Data) for AP-MS is a genus term where the vocabulary offers no AP-MS-specific child — using the parent is the correct behaviour when no exact term exists, and this is now noted in `source_caveats`.

### 4.4 `conforms_to_standard: [RO_CRATE]` (21)

Retained without adding `OTHER`. RO-Crate is genuinely the packaging standard. JSON-Schema, EVI and ARK are components *of* the FAIRSCAPE approach rather than data standards the content conforms to in the sense the slot means; they remain in `conforms_to` prose. Adding `OTHER` would make the enum list less informative, not more. A caveat now records the partial coverage.

### 4.5 Consent-family omissions (28)

`collection_consents`, `collection_notifications`, `consent_revocations`, `informed_consent`, `participant_privacy`, `participant_compensation`, `at_risk_populations` — all omitted.

**This is deliberate and evidence-based, not oversight.** The bundle states "Human Subjects: No", "De-identified Samples: Yes", and describes both lines as commercially/institutionally sourced (ATCC; HipSci). It also notes that KOLF2.1J derives from "a healthy male Northern European donor" and MDA-MB-468 from "a 51-year-old black female" — so originating human sources exist, but the bundle says nothing about their consent, notification, compensation, or revocation arrangements. Populating any of these slots would require inventing facts about donors the sources do not discuss.

`human_subject_research` **is** populated (`involves_human_subjects: false`), which is what the bundle actually asserts. `ethical_reviews` is populated with the two named ethics contacts. `is_deidentified` is populated.

### 4.6 Other omissions (29)

`data_protection_impacts`, `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols`, `splits`, `subsets`, `content_warnings`, `parent_datasets`, `resources`, `was_derived_from`, `modified_by`, `total_size_bytes` — all unsupported by the bundle for this release.

On `raw_sources` vs `raw_data_sources`: `raw_data_sources` is populated (external repository routing — MassIVE, SRA/BioProject, Figshare, plus the embargoed items). `raw_sources` is omitted. The two overlap in intent; `raw_data_sources` was chosen because it requires `source_description`, forcing the substantive content into a declared field, whereas `RawData` would put the same content in `raw_data_details` prose. This choice is now stated in `source_caveats` rather than left implicit.

### 4.7 `known_biases[1]` (25)

Retained. The bundle's own "Potential Sources of Bias" section lists only the cell-line-representativeness point (now `known_biases[0]`, `representation_bias`). The second entry — targeted selection of chromatin modifiers and metabolic enzymes rather than proteome-wide sampling — is derived from the methods descriptions rather than labelled as bias by the sources. It is a fair reading of stated facts (the CM4AI preprint is explicit that 100 chromatin modifiers and 100 metabolic enzymes were selected), but the framing is the record's. `source_caveats` now marks the distinction.

---

## 5. Standing evidence-boundary notes

### 5.1 The U2OS / Nature study is not this dataset

`www_nature_com_articles-s41586-025-08878-3_row2.txt` (Schaffer et al., *Nature* 642:222–231) describes a **U2OS osteosarcoma** cell map with 5,147 proteins, 275 assemblies, and its own data deposits (NDEx, MassIVE MSV000097168, PXD052362, HPA v23, ModelArchive). It shares authors and the MuSIC methodology with CM4AI, and acknowledges Bridge2AI funding — but it is a different study on a different cell line with different deposits.

**No U2OS-specific fact enters either record.** Not the 5,147/275 counts, not the pediatric cancer analysis, not the SEC–MS protein totals, not the NDEx or MassIVE accessions, not the AlphaFold structures.

### 5.2 Methodological bleed (finding 30)

`preprocessing_strategies` describes the MuSIC pipeline: node2vec on the PPI network, an HPA-pretrained CNN on the images, contrastive co-embedding, multi-resolution community detection. The audit correctly observed that this is described in both documents.

**Retained**, because the CM4AI preprint (`biorxiv_2024.05.21.589311v1_row4.txt`, §3 Tools) independently and completely describes all four steps as CM4AI's own pipeline, citing node2vec and the HPA model directly. The content is therefore supportable from the CM4AI source alone. `source_caveats` now states that the pipeline description is drawn from the CM4AI preprint's Tools section, so the boundary is traceable.

**Important scope note, now in `notes`:** the June 2026 release explicitly states "Computed cell maps not included in this release." The pipeline is documented because it is what the project applies to these inputs, not because map outputs are present here.

### 5.3 Contributions statement not transferred

The Nature article's detailed CRediT-style contributions paragraph applies to the U2OS study. It was **not** used to populate `credit_roles` on CM4AI creators. Only Ideker's PI role carries credit roles, supported by NIH RePORTER and the Dataverse Point of Contact field.

### 5.4 The 563 / 464 protein-count discrepancy

The March 2025 release describes IF images for **563** proteins; June 2025 and later describe **464** for the same cell line and conditions. The bundle never explains the change. Both figures are recorded in `source_caveats`; **464** is used in the June 2026 file-collection descriptions, because that is what the June 2026 record states about its own files. No reconciliation of the two figures is asserted.

### 5.5 Embargo status

Two Perturb-seq external links are marked "Embargoed" in the June 2026 record while the October 2025 record listed the KOLF2.1J SRA link as live. This is recorded in `raw_data_sources` and `confidential_elements` as stated, without inferring a re-embargo or a source error.

---

## 6. Validation

| Record | Command | Result |
|---|---|---|
| Full | `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` | **PASS** |
| Core | `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` | **PASS** |

Both re-validated after all changes above. The core record's `# Phase 4 reconciliation: completed` line was written only after this phase ran.

---

## 7. Outcome

**Reconciled.** Two high-severity findings (invented `distributions` slot; referent straddle) and one high-severity count error resolved. Four medium findings resolved by expanding collapsed structure (creators) or restoring dissolved slots (citation, relationships, variables, direct_collection). Two medium findings resolved by populating declared fields (`file_count`, `total_bytes`) and canonicalising duplicated content (checksums). Eleven low findings corrected; the remainder retained with explicit justification recorded in `source_caveats` rather than left silent.

The records are now consistent with each other on the June 2026 release as referent, and no fact in either originates outside the declared bundle.