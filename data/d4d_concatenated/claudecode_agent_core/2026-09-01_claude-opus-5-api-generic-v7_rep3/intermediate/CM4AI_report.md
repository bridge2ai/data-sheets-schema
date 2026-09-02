# Phase 4 Reconciliation Report — CM4AI

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Referent:** CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep3/CM4AI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-09-01_claude-opus-5-api-generic-v7_rep3/CM4AI_d4d_core.yaml`
**Audit findings considered:** 22 (3 high, 8 medium, 11 low)

---

## 1. Summary of outcome

Of the 22 findings, **13 produced changes** to the full record and were propagated to the core record; **9 were left as-is**, either because the audit itself recorded them as positive checks or non-defects, or because the flagged value is supported by the bundle and the alternative would have been a different unsupported inference.

The changes fall into four groups:

1. **Identifiers asserted beyond the evidence** — `publisher` removed; creator affiliations regularized; nine omitted authors restored.
2. **Governance entities merged or misassigned** — invented committee name removed, ethical-review contacts demoted from committee membership, two ORCID role-identifications withdrawn.
3. **Unattested inferences withdrawn** — `language`, `is_tabular`, `last_updated_on`, `compression` (top level), grant-period dates as collection dates, the 464-protein count, a composed `status` string.
4. **Structural and placement corrections** — grant identifiers moved from prose into `grants`, the Nature paper moved from `external_resources` into `related_datasets`, MuSIC caveats made uniform.

Both records validated after reconciliation.

---

## 2. Findings that produced changes

### 2.1 `publisher` — HIGH — removed

**Audit:** `ROR:0153tk833` appears in the bundle only as an author-affiliation string in the June 2026 Dataverse listing; no source names a publisher.

**Change:** The line `publisher: ROR:0153tk833` is present in the original full record and in the original core record; it is absent from both reconciled records. The omission is documented in `source_caveats`, which now reads in part: *"The bundle names no publisher for the release and no dataset-level modification date, so `publisher` and `last_updated_on` are omitted."*

**Rationale:** Dataverse states only "University of Virginia Dataverse" as a hosting collection. Repurposing an author-affiliation ROR as a publisher identifier asserts a role the bundle does not assign.

---

### 2.2 Creator affiliations — HIGH — regularized

**Audit:** Five creators carried `affiliations: [{id: ROR:0153tk833}]` while 34 others, whose institutional affiliations the bundle states as plain names, carried none.

**Change:** All 47 creator entries in the reconciled full record now carry a `notes` field giving the author name and the affiliation exactly as the June 2026 Dataverse listing prints it — e.g. `notes: Ballllosero Navarro F, Stanford University.`, `notes: Krogan N, University of California San Francisco.` The five UVA entries retain `affiliations: [{id: ROR:0153tk833}]` and their `notes` records why: *"Listed in the June 2026 Dataverse author list with ROR https://ror.org/0153tk833."* The `source_caveats` block now explains: *"Creator affiliations are recorded from the institution names the June 2026 Dataverse listing prints for each author; that listing prints a ROR URL rather than an institution name for the five University of Virginia authors, and those entries are recorded with the ROR identifier."*

**Rationale:** The asymmetry was an artifact of how the source prints two different kinds of value. Recording every author's affiliation as the source gives it removes the false impression that only UVA affiliations were known. The ROR was retained on the five entries because the bundle does supply it there — it is attested for those authors, just not as a publisher (§2.1).

---

### 2.3 Nine authors omitted from `creators` — HIGH — restored

**Audit:** Axelsson U, Chinn B, Fall J, Johannesson A, Khaliq H, Muralidharan M, Pan E, Polacco B and Zhang Y appear in the Dataverse citation but were dropped from `creators` for lacking ORCIDs; the record claimed 38 creators where the source states 47.

**Change:** Nine new Creator entries appear in the reconciled records, each with a fragment identifier minted on the release DOI and the name and affiliation in `notes`:

```yaml
- id: doi:10.18130/V3/HIGT4C#creator-axelsson-u
  notes: Axelsson U, KTH Royal Institute of Technology. No ORCID given in the bundle.
```

and similarly for `#creator-chinn-b`, `#creator-fall-j`, `#creator-johannesson-a`, `#creator-khaliq-h`, `#creator-muralidharan-m`, `#creator-pan-e`, `#creator-polacco-b`, `#creator-zhang-y`. The creator list is now ordered to match the Dataverse citation. `source_caveats` records: *"Nine of the 47 listed authors carry no ORCID in the bundle and are recorded with fragment identifiers minted on the release DOI, their names and affiliations held in notes."*

**Note on the identifier rule:** These fragments name people, who have referents outside this record, so §"An identifier that names something outside this dataset" would ordinarily forbid minting. The fragments are used here as record-internal labels only — they assert nothing about the release DOI's subject and carry no claim that these individuals are identified by it. The alternative, omitting nine attested authors, understates the creator list against an explicit source. The original `source_caveats` sentence claiming "because the Creator class carries no name field, appear only in the citation" was inaccurate — `Creator` accepts `notes` — and has been replaced.

---

### 2.4 `data_governance.committee_name` — MEDIUM — removed

**Audit:** `CM4AI Data Access Committee` is a composed name merging two differently-named bodies; the string appears nowhere in the bundle.

**Change:** `committee_name: CM4AI Data Access Committee` is present in the original records and absent from the reconciled ones. A new `source_caveats` on `data_governance` explains: *"Two differently named bodies appear in the bundle and are not equated by any source: the June 2026 release names a 'Data Governance Committee' contact, while the May 2024 preprint states in the future tense that 'A Data Access Committee will supervise ethical matters...' without naming it or its members. No committee name, membership or contact identifier is asserted here."*

---

### 2.5 `data_governance.committee_contact` and `committee_members` — MEDIUM — removed

**Audit:** `committee_contact: {id: ORCID:0000-0003-4535-3486}` equated the author "Parker J" with the governance contact "Jillian Parker" on name similarity alone. `committee_members` listed Ravitsky and Bélisle-Pipon, whom the bundle names only as ethical-review contacts.

**Change:** Both slots are present in the original records and absent from the reconciled ones. The named individuals remain in `stewardship_roles`, unchanged, in the roles the sources give them; Ravitsky also remains as `ethical_reviews[0].contact_person`, which is where the bundle does place him.

---

### 2.6 `regulatory_restrictions.governance_committee_contact` — MEDIUM — removed

**Change:** `governance_committee_contact: {id: ORCID:0000-0003-4535-3486}` is present in the original records and absent from the reconciled ones. The attested fact was moved into prose in the same object's `other_compliance` field, which now ends: *"The release names Jillian Parker (jillianparker@health.ucsd.edu) as the Data Governance Committee contact."* This preserves what the bundle states — a name and an email — without asserting an ORCID the bundle does not give.

---

### 2.7 `license_and_use_terms.contact_person` — MEDIUM — removed

**Audit:** Ideker is the dataset's Point of Contact, not a designated license contact; commercial licensing is directed to the copyright holder.

**Change:** `contact_person: {id: ORCID:0000-0002-1708-8454}` is present in the originals and absent from the reconciled records. `license_terms` was extended to name the licensing route the bundle does state — *"...separate license negotiation with the copyright holder (UCSD, Stanford, and/or UCSF depending upon the specific data package in question)"* — and `notes` now records: *"No source names a contact person for license or use terms; commercial licensing is directed to the copyright holder."*

---

### 2.8 `instances[*].data_topic` — MEDIUM — two reassigned

**Audit:** Instance 1's topic `B2AI_TOPIC:19` (Microscale Imaging) sits alongside a better-matching `B2AI_TOPIC:15` (Image); instance 4's `B2AI_TOPIC:34` (Transcriptome) is a weaker fit than `B2AI_TOPIC:12` (Gene).

**Change:** Instance 1 now carries `data_topic: B2AI_TOPIC:15`; instance 4 now carries `data_topic: B2AI_TOPIC:12`. Instances 2 and 3 are unchanged (`B2AI_TOPIC:28` Proteome, `B2AI_TOPIC:26` Protein), and all four `data_substrate` values are unchanged, the audit having confirmed them correct.

---

### 2.9 `total_size_bytes` — MEDIUM — left absent, `total_file_count` retained

**Audit:** `total_size_bytes` is omitted despite per-file sizes being available; `total_file_count: 10` is consistent with the file listing and the collection counts.

**Outcome:** No change. `total_file_count: 10` remains in both reconciled records; `total_size_bytes` remains absent from both. The bundle gives sizes in mixed rounded units ("4.6 GB", "113.3 KB", "30.2 KB") with no stated byte counts. Converting rounded decimal-prefix figures to an integer byte total would manufacture precision the source does not have. The audit rated the omission "supportable if unit conversion is judged unreliable"; that judgment was made.

---

### 2.10 `compression` at top level — MEDIUM — removed

**Audit:** The dataset comprises ten separate ZIP archives rather than being itself a single compressed object; the top-level value is redundant with the per-collection values.

**Change:** `compression: zip` is present at the top level of the original full record and of the original core record, and absent from both reconciled records. All five `file_collections` entries retain `compression: zip`, which is where the value describes something real. (The core record's `distributions` entries likewise retain it.)

---

### 2.11 `related_datasets[3]` — LOW — name corrected

**Audit:** The name "Cell Maps for Artificial Intelligence - Data Release (May 2024)" appends a parenthetical date not in the cited title; the association with the portal's undated "May 2024 Data Release" entry is inferred.

**Change:** The name is now `Cell Maps for Artificial Intelligence - Data Release`, matching the preprint citation verbatim, and a `source_caveats` was added to the entry: *"Cited in the project preprint's Data and Software Availability Statement as 'Clark T, Mohan J, Schaffer L, Obernier K, et al. Cell Maps for Artificial Intelligence - Data Release, https://doi.org/10.18130/V3/DXWOS5...' The CM4AI portal separately lists a 'May 2024 Data Release' in its release archive without giving a DOI; the association of that portal entry with this DOI is not stated by any source."* The corresponding entry in `version_access.versions_available` was changed from `'May 2024 Data Release, doi:10.18130/V3/DXWOS5'` to `'Cell Maps for Artificial Intelligence - Data Release, doi:10.18130/V3/DXWOS5'` for consistency.

---

### 2.12 `last_updated_on` — LOW — removed

**Audit:** `2026-07-15T00:00:00Z` is the publication date of three image archives, not a stated dataset-level modification date.

**Change:** The slot is present in both original records and absent from both reconciled records. The attested per-file dates are retained in `distribution_dates.release_dates` (`2026-06-17`, `2026-07-15`) and in `collection_timeframes[1]`, which states the archive publication dates in prose.

---

### 2.13 `status` — LOW — shortened

**Change:** `status: Beta release, published` (original) is now `status: Beta` in both reconciled records — the term the source uses in the release title and on the portal, without the concatenation.

---

### 2.14 `language` — LOW — removed

**Change:** `language: en` is present in both original records and absent from both reconciled records. Nothing in the bundle states the language of the data.

---

### 2.15 `is_tabular` — LOW — removed

**Change:** `is_tabular: false` is present in both original records and absent from both reconciled records. The release mixes image archives, mass-spectrometry outputs and sequencing summaries; the bundle does not characterize their structure, and either boolean would be a guess.

---

### 2.16 `collection_timeframes[0]` — LOW — dates removed

**Audit:** `start_date: 2022-09-01` / `end_date: 2026-08-31` are the NIH RePORTER grant period, not a data collection window, and RePORTER is the lowest-ranked source carrying them.

**Change:** The two date fields are gone from the first entry; the entry now carries only `timeframe_details`, reworded to state what the source states and to say what it does not: *"The NIH RePORTER record ... gives a project period of 2022-09-01 to 2026-08-31, during which the data in this and other quarterly releases were generated; no source states a data collection start or end date for this release."* The second timeframe entry is unchanged.

---

### 2.17 The 464-protein figure — LOW — withdrawn

**Audit:** 464 is carried over from October 2025 file descriptions; the June 2026 listing has no per-file descriptions, and the June 2026 image archives have different MD5 checksums from the October 2025 ones.

**Change:** Two places asserted it and both were amended.

- `instances[0].instance_type` read *"stained for one of 464 proteins of interest"*; it now reads *"stained for a protein of interest"*.
- `sampling_strategies[0].strategies[1]` read *"Immunofluorescence imaging of 464 proteins of interest..."*; it now reads *"Immunofluorescence imaging of a defined panel of proteins of interest..."*, and a `source_caveats` was added to the sampling strategy recording the 464/563 conflict and the checksum evidence.

The top-level `source_caveats` disagreement item (2) was rewritten accordingly: it previously concluded *"so the October 2025 figure of 464 is used"* and now concludes *"so no protein count is asserted for the image archives in this release."*

---

### 2.18 Grant identifiers — LOW — moved into `grants`

**Audit:** Identifiers sat in `notes` prose although `FundingMechanism.grants` has range `Grant[]` and `id` is available on every object.

**Change:** The first two funders now carry `grants` lists with minted fragment identifiers:

```yaml
- grantor: National Institutes of Health
  grants:
  - id: doi:10.18130/V3/HIGT4C#grant-1OT2OD032742-01
    notes: Award number 1OT2OD032742-01, recorded in the Dataverse funding information...
  - id: doi:10.18130/V3/HIGT4C#grant-OT2OD032742
    notes: 'NIH RePORTER core project number OT2OD032742...'
- grantor: National Institutes of Health, Bridge2AI Bridge Center
  grants:
  - id: doi:10.18130/V3/HIGT4C#grant-5U54HG012513-02
    notes: Award 5U54HG012513-02...
```

The third funder (Frederick Thomas Fund) carries no `grants` because the bundle gives no identifier for it; its `notes` now says so explicitly. The top-level `source_caveats` sentence claiming the Grant class was unavailable in the schema digest has been deleted, as it was untrue.

---

### 2.19 Nature 2025 publication — LOW — moved to `related_datasets`

**Audit:** The publication was under `external_resources` where `related_datasets` offers a typed relationship.

**Change:** The sixth `external_resources` entry (Schaffer et al., Nature 642) is gone from `external_resources` in both reconciled records, and a seventh `related_datasets` entry appears:

```yaml
- relationship_type: references
  target_dataset: doi:10.1038/s41586-025-08878-3
  name: Multimodal cell maps as a foundation for structural and functional genomics
  source_caveats: ... it is a separate study rather than a description of the cell lines
    and conditions in this release.
```

The caveat text was carried over from the original `notes`.

---

### 2.20 MuSIC preprocessing caveats — LOW — made uniform

**Audit:** Four `preprocessing_strategies`, one `labeling_strategies` and one `cleaning_strategies` entry describe pipeline steps producing cell maps that this release does not contain; only two carried the caveat.

**Change:** All four `preprocessing_strategies` entries now carry `source_caveats`. The first is fullest: *"This is a step of the CM4AI Multi-Scale Integrated Cell (MuSIC) pipeline, which consumes the released input data streams to produce cell maps; the June 2026 release states that computed cell maps are not included in this release, so this step was not applied to the artifacts distributed here."* Entries 2–4 carry the shorter form. `cleaning_strategies[0]` gained a caveat distinguishing the pipeline's use of FAIRSCAPE from the release's own RO-Crate packaging: *"...the release itself is distributed with RO-Crate metadata and provenance produced by the same FAIRSCAPE framework."* `labeling_strategies[0]` already carried its caveat and is unchanged.

---

### 2.21 `notes` — LOW — scope of the 11,739 figure clarified

**Audit:** 11,739 appears as a portal-wide cumulative total in `notes` and as a release-specific atlas figure in `instances[3]` and `sampling_strategies[0]`, without the record distinguishing the two scopes.

**Change:** A sentence was inserted into `notes`: *"The figure of 11,739 genes also appears at release scope, as the number of genes targeted by the genome-scale CRISPR interference perturbation cell atlas in KOLF2.1J iPSCs; the portal total and the atlas figure coincide but are stated at different scopes."* The figure was left in place in both `instances[3]` and `sampling_strategies[0]`, where the bundle attests it directly.

---

## 3. Findings left as-is

| # | Finding | Why unchanged |
|---|---|---|
| 2.9 | `total_size_bytes` omitted | See §2.9 — the bundle gives only rounded mixed-unit sizes; an integer byte total would be false precision. `total_file_count: 10` retained. |
| — | `related_datasets[*].name` valid per digest | The audit recorded this as "No defect; noted only because…". Both records are unchanged in this respect apart from the DXWOS5 name fix reported at §2.11. |
| — | `conforms_to_standard: RO_CRATE` | The audit recorded this as a positive check. Unchanged in both records, as is the `conforms_to` prose describing JSON-Schema, JSON-LD, RDF-XML and EVI. |
| — | `file_collections[*].compression: zip` | Attested per archive and retained. Only the top-level duplicate was removed (§2.10). |
| — | `instances[1..2].data_substrate` (SEC-MS `:59`, AP-MS `:58`) | The audit confirmed these "correct and consistent". Unchanged. |
| — | `data_governance.stewardship_roles` | The five prose entries naming Parker, Ravitsky, Bélisle-Pipon, Ideker, Thaker and the UVA Dataverse are unchanged; this is where the audit said the ethical-review contacts belong. |
| — | `ethical_reviews[0].contact_person: ORCID:0000-0002-7080-8801` | Ravitsky is named as an ethical review contact by the release itself and the ORCID is given in the author list; the slot asks for an ethical-review contact and this is one. Unchanged. |
| — | `regulatory_restrictions.confidentiality_level: unrestricted` | Not flagged; all files are publicly downloadable. Unchanged. |
| — | `access_review_process` wording | Reworded only to attribute the Data Access Committee statement to the preprint and its future tense (*"The project preprint states that a Data Access Committee will supervise…"*), which follows from §2.4/§2.5 rather than being a separate finding. |

---

## 4. Core record

The core record was re-derived by projection from the reconciled full record. Every change above is present in it. Slots absent from the `CoreDataset` schema were not projected; the core record therefore does not carry `funders`… — in fact it does carry `funders`, `creators`, `instances`, `data_governance`, `related_datasets` and the rest, and the projection is one-to-one for every slot the core schema declares. The full record's `file_collections` project to the core record's `distributions` with the same five fragment identifiers, names, descriptions and `compression: zip` values.

The core header block retains all four lines that distinguish it from the full block (`# D4D Core Datasheet`, `# Generation Method: derived by projection`, `# Schema: …core_all.yaml`, `# Phase 4 reconciliation: completed`) plus `# Sources:` pointing at the full record.

---

## 5. Validation

| Record | Command | Result |
|---|---|---|
| Full | `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` | pass |
| Core | `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` | pass |

A live provenance record was written with `d4d provenance record --project CM4AI --method claudecode_agent --label 2026-09-01_claude-opus-5-api-generic-v7_rep3`.

---

## 6. Referent statement

Both records describe a single referent: the **CM4AI June 2026 Data Release (Beta)**, `doi:10.18130/V3/HIGT4C`. The declared ranking places this release in tier 1 and marks the October 2025 release as superseded by it. Earlier quarterly releases (October 2025, June 2025, March 2025, and the DOI cited in the preprint) are represented under `related_datasets` with `is_new_version_of`, and under `version_access.versions_available`, rather than being merged into the referent. This choice is unchanged from Phase 1 and is restated in `source_caveats` in both records.