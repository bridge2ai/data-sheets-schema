# VOICE — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d_core.yaml`

---

## 1. Outcome summary

| Item | Value |
|---|---|
| Full record populated slots (post-reconciliation) | 79 |
| Core record populated slots (post-reconciliation) | 43 |
| Full record validates against `Dataset` | Yes |
| Core record validates against `CoreDataset` | Yes |
| Audit findings raised | 40 (3 medium, 37 low, 0 high) |
| Findings resolved by edit | 22 |
| Findings resolved by verification, no edit | 8 |
| Findings retained as-is with recorded rationale | 10 |
| Fabricated facts found | None |

No high-severity finding was raised, and the audit identified no claim in either record that lacks a traceable basis in the declared bundle. Reconciliation was therefore corrective rather than reconstructive: the work consisted of tightening identifier granularity, removing inferences that the bundle does not state, restoring source disagreements that had been silently resolved, and closing structural divergences between the full and core records.

---

## 2. Referent decision

The `Dataset` class admits one referent. Both records were built around **the Bridge2AI-Voice adult dataset as published in PhysioNet release 3.1.0** (833 participants, published 2026-05-01). This choice is held consistently across both records and is the basis for several edits below.

The bundle also contains a second, distinct PhysioNet project — the Bridge2AI-Voice Pediatric Dataset v1.1.0 (300 participants, aged 2–18, Hospital for Sick Children, DOI `10.13026/h995-bt35`). The curation note in the bundle is explicit that this is a separate project and not a version of the adult dataset. It is therefore **not** folded into the referent. It is represented in both records only as a typed `related_datasets` entry, and its participant and recording counts are never mixed into the adult figures.

Earlier adult releases (1.0, 1.1, 2.0.0, 2.0.1, 3.0.0) are treated as version history of the same referent and are recorded under `distribution_dates` and the release notes, not as separate referents.

---

## 3. Changes applied to both records

These edits were applied identically to the full and core records so that the two remain factually aligned.

### 3.1 Identifier granularity (audit findings 1, 2 — medium)

The `id` was `https://doi.org/10.13026/37yb-1t42`, which the bundle labels as PhysioNet's *"DOI (latest version)"* concept DOI, while `version`, `doi`, `issued`, and `page` all described release 3.1.0 specifically. Because the records are dense with 3.1.0-specific evidence — the per-feature parquet counts (`n=29,278` spectrograms, `n=28,640` `sparc_ema`, and so on), the 3.1.0 release notes, and the `metadata/` folder that first appears in 3.1.0 — the referent is the versioned release, not the version-independent project.

**Change:** `id` set to `https://doi.org/10.13026/8xbn-nq66` (the 3.1.0 version DOI). The concept DOI was preserved, not discarded: it now appears in `external_resources` labelled as the PhysioNet version-independent DOI for the adult project, exactly as the bundle labels it.

### 3.2 Unevidenced `last_updated_on` (findings 3, 4)

`last_updated_on` duplicated `issued` at `2026-05-01`. The bundle gives a publication date for 3.1.0 but never states a distinct modification timestamp.

**Change:** `last_updated_on` removed from both records. Under the standing rule that omission is preferred to inference, an absent slot is the correct answer here; `issued` already carries the only date the bundle supports.

### 3.3 `conforms_to_schema` over-reading (findings 5, 6)

`conforms_to_schema` named the Bridge2AI REDCap data dictionary. The bundle establishes that the REDCap dictionary defines the acquisition instruments and carries the `Identifier?` sensitivity encoding used to drive field removal, but it never states that the released dataset conforms to it as a data model.

**Change:** `conforms_to_schema` removed. The REDCap dictionary is retained in `external_resources` (repository `eipm/bridge2ai-redcap`, Zenodo DOI, MIT licence) and its role in the de-identification procedure is retained verbatim in `is_deidentified`, where the bundle actually places it.

`conforms_to` is left populated with the Brain Imaging Data Structure v1.9.0, which the bundle does state directly: *"converted to be compliant with the Brain Imaging Data Structure v1.9.0."*

### 3.4 Creator affiliations — silent resolution of source disagreement (findings 7–10)

Three affiliations resolved conflicts between bundle sources without disclosing the conflict, and one added a detail absent from any affiliation statement.

| Creator | Prior rendering | Issue | Change |
|---|---|---|---|
| Yael Bensoussan | *"Division of Laryngology, USF Health Voice Center, … Morsani College of Medicine"* | "Division of Laryngology" appears only in the JAMA correspondence address block, not as a listed affiliation; core record omitted it | Phrase removed from full record; full and core now match |
| Satrajit Ghosh | *"McGovern Institute …, Cambridge, MA"* | Bundle gives Cambridge, MA (PMC author block) and Boston, MA (PMC consortium member list) | Both renderings now recorded, attributed to their respective sections |
| Vardit Ravitsky | *"The Hastings Center (previously University of Montreal)"* | No source states a temporal sequence; the two affiliations simply appear in different documents | Rewritten to state that the PMC consortium list gives University of Montreal while the JAMA and project documentation lists give The Hastings Center, with no sequence asserted |
| Frank Rudzicz | *"University of Toronto / Dalhousie University"* | Slash-combination synthesises three sources; no single source says both | Rewritten to record that the PMC consortium list gives Dalhousie University and the project documentation and IRB protocol give University of Toronto |

This is a direct application of the rule that disagreeing sources are to be represented rather than silently reconciled.

### 3.5 Generator-supplied arithmetic in `instances` (findings 11, 12)

The `Recording` instance stated that the project documentation's figure of ~61,937 voice-derived recordings is *"roughly double the per-feature record counts."* The doubling comparison is analysis introduced during generation, not a statement in any source.

**Change:** the comparison removed. Both figures are retained and the conflict is retained: the documentation's ~61,937 for v3.0, and the 3.1.0 per-feature counts as stated per parquet file. The records now report the discrepancy without characterising its magnitude or proposing an explanation.

### 3.6 BIDS tree attribution in `raw_sources` (findings 13, 14)

The BIDS folder tree was described as the layout of the controlled-access raw audio archive. The bundle presents that tree under "Data Pre-Processing" as the folder structure *for the dataset* (root `b2ai-voice-audio`), and although the `sub-*/ses-*/audio/*.wav` leaves make the reading natural, no source says the tree documents the controlled-access package specifically.

**Change:** wording softened in both records to attribute the tree to the project documentation's description of the dataset folder structure, and to note separately — as the bundle does — that raw audio is distributed under controlled access via Synapse (`syn72370534` adult; `syn73617068` pediatric) and is not present in the PhysioNet release.

### 3.7 Misfiled statement under `regulatory_restrictions` (findings 15, 16)

Both records placed the documentation-site footer sentence *"This repository is under review for potential modification in compliance with Administration directives"* under `regulatory_restrictions`. The bundle attaches no regulatory or export-control meaning to that sentence; it sits in a site footer with no stated connection to the dataset's distribution terms.

**Change:** the sentence removed from `regulatory_restrictions` in both records, and not relocated. `regulatory_restrictions` now carries only what the bundle states in that register — the healthsheet answer that no export controls apply to the dataset. Placing a footer notice under a regulatory slot attributes a meaning the source does not assign, and there is no other slot for which the bundle supplies a warrant.

### 3.8 `description` — separating two claims (findings 25, 26)

The description read *"five sites in North America (United States and Canada)."* The bundle supplies "five sites in North America" (PhysioNet), "five recording sites" (healthsheet), and "USA and Canada" as the countries of collection (healthsheet), but never says the five sites span both countries — and the IRB protocol lists many more participating institutions than five, including Canadian ones.

**Change:** the two claims separated. The description now states that the release covers five recording sites in North America, and separately that the healthsheet reports the countries of collection as the USA and Canada.

### 3.9 `purposes` — second reading of an internally inconsistent source (findings 27, 28)

The records surfaced the 10,000 (documentation) versus 30,000 (IRB, NIH RePORTER lineage) enrollment-target conflict correctly, and cited the IRB's "up to 5,000 participants at the University of South Florida" from §12.1. The same IRB protocol also states at §6.2 that complete data acquisition will be performed "for up to 5000 participants per category."

**Change:** the second figure added, with both attributed to their protocol sections. The IRB is internally inconsistent on this point and both records now say so rather than presenting one section's number as the protocol's position.

---

## 4. Changes applied to the full record only

### 4.1 Minted identifiers made visibly non-resolvable (finding 18)

`file_collections` used constructed URLs of the form `https://physionet.org/content/b2ai-voice/3.1.0/features/`. The bundle documents `features`, `phenotype`, and `metadata` subfolders but publishes no such URLs. A constructed HTTPS URL implies resolvability that has not been verified, which is a stronger claim than a visibly local identifier.

**Change:** the four `file_collections` identifiers reminted in the same `urn:` style already used for `subsets`, so that no identifier in the record falsely presents as a resolvable web location. The folder names and their documented contents are unchanged. `page` and `download_url` continue to carry the one PhysioNet URL the bundle does publish.

---

## 5. Changes applied to the core record only

The audit raised three medium and several low findings on structural divergence between the two records. These were resolved by consulting `data_sheets_schema_core_all.yaml` directly, which the audit could not do.

### 5.1 Slots absent from `CoreDataset` — folding confirmed correct, no change

The following full-record slots have no counterpart in `CoreDataset`. Folding their content into the nearest available core slot was schema-driven and correct, not evidence loss:

- `participant_compensation` → folded into `human_subject_research` (finding 19, 21). The gift-card amounts, the 90-minute session threshold, the three-session and $120 caps, and the feasibility study's explicit non-compensation are all present in the core text.
- `collection_notifications`, `consent_revocations` → folded into `informed_consent` (finding 20).
- `subsets` → cohort content folded into `subpopulations` (finding 22).
- `file_collections`, `variables` → folded into `distribution_formats` and prose (findings 24, 25).
- `third_party_sharing` → folded into `license_and_use_terms` (finding 27).

### 5.2 Slots present in `CoreDataset` — content restored

Three slots exist on `CoreDataset` and were omitted, dropping statements the bundle supports explicitly. All three restored:

- **`splits`** (finding 23). Restored. The bundle states plainly that the dataset comes with no predefined recommended splits, that researchers are encouraged to construct their own, and that they should account for skew by disorder category, site, and demographic factors when doing so. This is a substantive usage constraint and its absence from the core record was a defect.
- **`relationships`** (finding 24). Restored. The healthsheet answers directly that relationships between instances are *not* made explicit — *"No, they are unrelated"* — and the participant / session / recording hierarchy is documented throughout. The "unrelated" fact had survived only obliquely inside an `instances` description.
- **`direct_collection`** (finding 28). Restored. The healthsheet answers "Directly" to whether data was obtained from individuals or via third parties. This is a first-order provenance fact and had no representation in the core record.

### 5.3 Content weakened by folding — restored within the receiving slot

The audit noted two facts materially weakened when `third_party_sharing` was folded into `license_and_use_terms` (finding 27). Both restored into the core `license_and_use_terms` text:

- the healthsheet statement that the dataset *"will be distributed broadly to individuals outside of the entity who created the dataset"*; and
- the IRB protocol's inter-institutional arrangement, under which federated learning permits model training across sites without the underlying data leaving the holding institution.

---

## 6. Retained as-is, with rationale

### 6.1 `publisher` = PhysioNet (findings 3, 4 — low)

Retained in both records. The slot is defined as *"the organization or entity responsible for making the resource available."* PhysioNet, maintained by the MIT Laboratory for Computational Physiology, is the entity through which release 3.1.0 is made available; this is a reading of the slot definition against a stated fact, not an inference about an unstated one. The bundle's separate statement that version 1.0 was published on Health Data Nexus is retained in `distribution_dates` and `version_access`, so the platform migration remains visible.

### 6.2 Minted cohort URNs in `subsets` (finding 17 — low)

Retained. `DataSubset` requires `id`, and the bundle supplies no identifiers for the five disease cohorts. Some string must be minted. The `urn:b2ai-voice:cohort:*` form was retained precisely because it is visibly local and non-resolvable, and §4.1 above extends the same convention to `file_collections` for consistency. The report records here that these identifiers are generator-minted and carry no external authority.

### 6.3 Sparse `variables` (finding 19 — low)

Retained at four entries (`participant_id`, `session_id`, `task_name`, `n_frames`). These are the only column names the bundle states outright, as the shared key structure of every parquet file. The bundle lists phenotype *file* stems and describes feature *families*, but never enumerates the columns within them. Populating `variables` from file names would be inference. Under-population is the correct answer where the evidence stops.

### 6.4 `distribution_dates` merge for v1.0 (finding 20 — low)

Retained. The healthsheet gives the end-of-November-2024 publication date; the v1.1 PhysioNet abstract gives 12,523 recordings for 306 participants and describes them as *"Bridge2AI-Voice v1.0, the initial release."* Both statements refer to the same release and both are sourced. The merge is sound; source attribution has been made explicit in the entry so the two-document basis is visible.

### 6.5 `license` name versus access tier (findings 21, 22 — low)

Retained verbatim as *"Bridge2AI Voice Registered Access License,"* which is exactly what PhysioNet's "License (for files)" field states for release 3.1.0. The inconsistency is in the source itself: the same page's access policy reads *"Only credentialed users who sign the DUA can access the files,"* i.e. credentialed rather than registered access, and version 1.1 was registered-access under the same licence name. Verified that the conflict is explicitly flagged in `license_and_use_terms` in **both** records, so the top-level `license` value is never read in isolation. Changing the licence name to match the access tier would misreport the source.

### 6.6 `confidential_elements` populated despite a healthsheet "No" (findings 23, 24 — low)

Retained in both records. The healthsheet answers "No" to whether the dataset contains confidential data, and the entry opens by disclosing that answer before recording that raw audio, free-speech transcripts, and the fields flagged `Identifier?` in the REDCap dictionary are withheld from the PhysioNet release and available only under controlled access with institutional sign-off. The slot is the correct home for access-restricted material, and the disclosure prevents the entry from being read as contradicting the source.

### 6.7 `collection_timeframes` version arithmetic (findings 29, 30 — low)

Retained. Every figure is sourced — 306 participants at v1.0 from the v1.1 abstract, +136 from the v2.0 release notes, +391 from the v3.0.0 release notes, 833 total from the 3.0.0 and 3.1.0 abstracts. The sum is consistent with the stated total, and no source is being contradicted. The entry states the figures and their sources without presenting the summation as a claim made by any document.

---

## 7. Conflicts deliberately preserved

Strict reconciliation removes generator inference; it does not remove disagreement present in the sources. The following conflicts are carried forward, flagged, in both records:

| Conflict | Values in bundle | Where recorded |
|---|---|---|
| Target enrollment | 10,000 (documentation, study metadata); 30,000 (IRB protocol, audiomics white paper cites 30,000 voices) | `purposes`, `updates` |
| USF-site enrollment | up to 5,000 total at USF (IRB §12.1); up to 5,000 per category (IRB §6.2) | `purposes` |
| Participating institutions | 10 other universities (documentation); 12 North American institutions (JAMA); 14 institutions (feasibility study); consortium member list longer still | `creators`, `data_collectors` |
| Recording count | ~61,937 voice-derived recordings for v3.0 (documentation); per-feature parquet counts for 3.1.0 (`n=23,533`–`32,522` depending on feature) | `instances` |
| Grant number rendering | `1OT2OD032720-01`; `OT2 OD032720`; `3OT2OD032720-01S1`; `3OT2OD032720-01S3`; `3Tf-OTOD03272001S2`; `3TF-OT2ActfOD032720Projectf01S1` | `funders` |
| MIT location | Cambridge, MA; Boston, MA | `creators` |
| Ravitsky affiliation | University of Montreal; The Hastings Center | `creators` |
| Rudzicz affiliation | Dalhousie University; University of Toronto | `creators` |
| Access tier for 3.1.0 | "Registered Access License" (licence field); "credentialed users who sign the DUA" (access policy) | `license`, `license_and_use_terms` |
| Version 1.1 access tier | registered access, no credentialing; 3.0.0 and later require credentialing | `version_access` |

---

## 8. Provenance verification

- The declared bundle was the sole source of dataset facts. The schema files were used for structure only.
- No previously generated D4D record was read, opened, searched, or consulted. Nothing under `data/d4d_concatenated/` outside this run's two output paths was accessed, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was accessed.
- No content was carried over from any other arm, label, or date.
- Both output files carry the required header block, with `phase 1` / full schema path in the full record and `phase 2` / core schema path in the core record.
- Live provenance recorded via `d4d provenance record` for project VOICE, method `claudecode_agent`, label `2026-07-31_claude-opus-5-api-generic_rep2`.

**Validation:**

```
linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d.yaml
  → PASS

linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset  data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d_core.yaml
  → PASS
```

Both records validate after reconciliation. All required keys on nested object ranges (`DataSubset.id`, `FileCollection.id`, `DatasetRelationship.relationship_type`/`target_dataset`, `RawDataSource.source_description`, `VariableMetadata.variable_name`, `Dataset.id`) are populated.