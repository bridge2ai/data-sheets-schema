# Reconciliation Report — AI_READI

**Version label:** `2026-08-22_claude-opus-5-api-generic-v5_rep1`
**Arm:** BASELINE (input documents only)
**Records:** full (`Dataset`) + core (`CoreDataset`)
**Phase:** 4 (strict reconciliation), following Phase 3 audit

---

## 1. Summary of the audit

The Phase 3 audit returned 37 findings: 3 high, 15 medium, 19 low. They fell into six clusters:

1. **A core-only `distributions` block** whose slot and object shape are not in the supplied schema digest, asserting `format` enum values (`TXT`) that neither the digest defines nor the bundle states.
2. **Seven slots present in core but absent from full** — a direct violation of the rule that core must not state what full does not.
3. **Two minted grant identifiers** that are fragments on a *different* award's RePORTER URL, making a false claim about that record.
4. **A single collapsed `creators` object** holding a consortium, a PI and eight institutions, where the bundle names sixteen individually-identified principal investigators with ORCIDs and affiliations.
5. **Structured fields left empty while their content sat in prose** — `DataSubset` composition, `CollectionTimeframe` dates, core `informed_consent` and `is_deidentified` absorbing content from dropped slots, core `notes` absorbing compensation.
6. **Partial vocabulary coverage** — one `data_topic` and no `data_substrate` for a nine-modality dataset; a partial `variables` list; inconsistent format vocabulary between the paired records.

---

## 2. Changes made to the **full** record

### 2.1 `creators` — expanded from 1 object to 19 (audit: medium)

The original held a single `Creator` naming the AI-READI Consortium, with Aaron Lee as `principal_investigator` and eight organizations as `affiliations`. This collapsed distinct entities and mis-stated the collaborator list as the consortium's affiliations.

The reconciled record emits:

- One object for the **organizational creator** (AI-READI Consortium), keeping `id: https://aireadi.org/` and one affiliation (Washington University in St. Louis, the attested managing organization). A `source_caveats` now states explicitly that the URL is a homepage rather than a registry identifier and that no registry identifier for the consortium appears in the bundle.
- **Sixteen objects for the named Study Principal Investigators** from `study_description.json` `overallOfficialList` — Aaron Lee, Cecilia S. Lee, Amir Bahmani, Sally L. Baxter, Christopher G. Chute, Jorge Contreras, Nicholas Evans, Samantha Hurst, T. Y. Alvin Liu, Gerald McGwin, Shannon McWeeney, Cynthia Owsley, Bhavesh Patel, Michael Snyder, Sara J. Singer, Linda M. Zangwill — each with their attested affiliation (including two ROR identifiers not previously used: `ROR:03r0ha626` University of Utah, `ROR:03hamhx47` University of Massachusetts Lowell).
- One object recording the **three data collection sites**, with a `source_caveats` acknowledging that the `Creator` class has no slot for a site-role institution and that the PI is repeated as a consequence.
- One object recording the **collaborating organizations** from the study description's `collaboratorList`.

`credit_roles` is now populated where the bundle supports it: `supervision` and `project_administration` for Aaron Lee (responsible party, study contact); `writing_original_draft` for the six Nature Metabolism Writing Committee members who are also PIs; `data_curation` additionally for Bhavesh Patel.

Two affiliation conflicts are now recorded rather than silently resolved: Aaron Lee and Cecilia S. Lee are placed at Washington University in St. Louis per the tier-1 FAIRhub study description, with `source_caveats` noting that the RO-Crate (also tier 1) and Nature Metabolism (tier 3) place them at the University of Washington.

### 2.2 `funders` — grant identifiers removed; two funders added (audit: medium)

The original minted `…project-details/10885481#P30DK035816` and `…#UL1TR003096` as fragments on the OT2OD032644 RePORTER URL. Per the v5 minting rule, these grants have referents outside the record, so an identifier must come from the evidence or be omitted.

In the reconciled record both `Grant` objects are **gone**. P30DK035816 and UL1TR003096 are each recorded as a `FundingMechanism` with `grantor: National Institutes of Health`, the grant number in `notes` prose, and a `source_caveats` stating that no award URI appears in the bundle. A caveat also distinguishes UL1TR003096 (BMJ Open acknowledgement) from UL1TR001442 (a Nature Metabolism competing-interests entry for a different award).

Two funders were added from evidence the original omitted: the **Microsoft AI for Good Lab** (cloud services) and a **device-manufacturer in-kind support** entry naming Topcon, Optomed, iCare World, Carl Zeiss (loaned devices at no cost) and Heidelberg Engineering, Dexcom, Garmin (research discounts).

### 2.3 Seven slots added to close core/full divergence (audit: medium ×7)

Each of these was present in core and absent from full. All are now in full:

| Slot | Evidence |
|---|---|
| `existing_uses` | healthsheet uses §1 ("No"); FAIRhub API `cited: 0`, `viewCount: 24636` |
| `use_repository` | healthsheet uses §3 ("No"); FAIRhub usage-statistics panel. `repository_url` populated with the FAIRhub dataset page |
| `other_tasks` | Nature Metabolism CDS/FAIRhub reuse intent |
| `data_protection_impacts` | healthsheet collection §12 ("No, a data protection impact analysis has not been conducted") |
| `extension_mechanism` | healthsheet maintenance §7; `contribution_url` populated with the GitHub organization |
| `labeling_strategies` | healthsheet labeling section (all N/A, hypothesis-agnostic rationale); RO-Crate `rai:dataAnnotationProtocol` |
| `regulatory_restrictions.confidentiality_level` | set to `restricted`, with the RO-Crate's `HL7:2N (normal)` recorded verbatim in `notes` and the mapping rationale stated |

### 2.4 `instances` — expanded from 1 to 12 objects; `data_substrate` populated (audit: low ×2)

The original held one participant-level `Instance` with `data_topic: B2AI_TOPIC:43` and no `data_substrate`. The reconciled record keeps the participant-level instance (with `counts: 2280` and the label description) and adds eleven modality-level instances, each carrying the substrate and topic terms the bundle supports:

- clinical/OMOP → `B2AI_SUBSTRATE:6` / `B2AI_TOPIC:4`
- survey → `B2AI_SUBSTRATE:80` / `B2AI_TOPIC:31`
- SDoH → `B2AI_TOPIC:29`
- ECG → `B2AI_SUBSTRATE:49` / `B2AI_TOPIC:10`
- retinal photography → `B2AI_SUBSTRATE:65` / `B2AI_TOPIC:24`
- OCT → `B2AI_SUBSTRATE:67` / `B2AI_TOPIC:24`
- OCTA → `B2AI_SUBSTRATE:68` / `B2AI_TOPIC:24`
- FLIO → `B2AI_SUBSTRATE:66` / `B2AI_TOPIC:24`
- CGM → `B2AI_SUBSTRATE:78` / `B2AI_TOPIC:38`
- activity monitor → `B2AI_SUBSTRATE:73` / `B2AI_TOPIC:39`
- environmental sensor → `B2AI_SUBSTRATE:69` / `B2AI_TOPIC:11`

The `missing_information` content that had been implicit is now recorded in the participant instance's `notes`.

### 2.5 `subsets` — composition moved from prose into declared fields (audit: low)

The three `DataSubset` objects previously carried their demographic composition inside `description`. Each now carries an `instances` list (with `counts`: 1576 / 352 / 352) and a `subpopulations` list with four `Subpopulation` objects apiece (race/ethnicity, sex, diabetes status, age), each with `identification` and `distribution` populated. The `description` is reduced to what it should hold — the partition's role and share.

### 2.6 `collection_timeframes` — split into five dated objects (audit: low)

The original had two objects; the second left `start_date`/`end_date` empty while naming six dates in prose. The reconciled record has five objects: the v3.0.0 collection window (2023-07-19 → 2025-05-01), the pilot enrollment period (2023-07-18 → 2023-11-30), formal collection start (2023-12-01), the NIH award project period (2022-09-01 → 2025-08-31), and the study status window (2023-07-19 → 2027-01-01). The date-conflict caveat is retained and extended.

### 2.7 `variables` — expanded from 33 to 76 objects (audit: low)

The original list was partial and its basis for selection unstated. The reconciled record covers the full Table 2 analyte panel (lipids, electrolytes, liver markers, complete blood count indices, urine assays), the four individual particulate-matter channels, and study-procedure variables the original omitted (`autorefraction_sphere`, `autorefraction_cylinder`, `ecg_chair_position`, `stress_level`, `physical_activity_calorie`, `tracker_wrist`, `dominant_hand`, `environmental_sensor_location`).

Laboratory reference ranges that had been narrative are now in `minimum_value` / `maximum_value` where a single numeric range applies, each with a `notes` stating that these record the reference range and not observed values. Where the range is sex- or age-stratified (creatinine, troponin-T, ALT) or "varies by age" (NT-proBNP, alkaline phosphatase), the range stays in `notes` and the numeric slots are omitted. `quality_notes` is now used on `moca_total_score` for the training, education and comorbidity caveats. `multispectral_light_intensity` retains `data_type: array` with a `notes` recording that the eleven channels are not individually enumerated in the bundle.

### 2.8 `distribution_formats` — extended from 4 to 8 objects (audit: low)

Added `WFDB`, delimited ASCII per ESDS, and plain text (for LICENSE.txt), plus a commentary object recording the four media types the dataset description itself lists. This makes the full record's format vocabulary complete and gives the core record something consistent to project from.

### 2.9 Smaller corrections

- **`license`** — the parenthetical was dropped; the value is now the attested `rightsName` alone: `AI-READI custom license v2.0`. The rights URI is recorded in `license_and_use_terms.license_terms`.
- **`keywords`** — the two study-level keywords (`Data Sharing`, `Exploratory Data Collection`) were removed, leaving the seven attested FAIRhub *dataset* subjects.
- **`sampling_strategies.strategies`** — eligibility criteria moved here from `at_risk_populations.special_protections`' orbit; the field is now a single prose block rather than a list, and includes the inclusion/exclusion criteria and the design terms.
- **`file_collections`** — `is_tabular: true` was removed from the `clinical_data` entry and the tabular character stated in its `description` instead; the root-metadata entry's mixed-format character is stated in prose.
- **`data_governance.committee_members`** — left unpopulated, with the caveat now explaining *why* (no membership attested) and pointing to `creators` for the sixteen PIs.
- **`related_datasets`** — the two documentation URLs are retained but each now carries a `source_caveats` acknowledging that the target is a site rather than a dataset and that it appears also in `external_resources`.
- **`preprocessing_strategies`** — one object added (no instances excluded at preprocessing).
- **`ethical_reviews`** — the Community Advisory Board is now its own object rather than folded into the bioethics entry; `contact_person` is populated on the IRB entry.
- **`participant_compensation`** — `retention_incentives` populated; grant-support detail moved to `notes`.
- **`external_resources`** — two URLs added (internship program, REDCap forms PDF).
- **`third_party_sharing`** — the access URL added.
- **`source_caveats`** — item (12) rewritten. The original asserted a directory byte sum (3,815,969,360,064) that does not reconcile with the source figures. The reconciled text states only the attested API totals, notes that the nine directory entries account for 356,334 files with nine root metadata files making up the difference, and **explicitly declines to assert a derived byte sum**. Two new items added: (14) grant identifiers, (15) creator identity.
- **Spelling** — American English applied throughout the prose (`characterize`, `organization`, `standardized`, `minimize`, `analyze`); quoted material and proper names untouched. Note that `haemoglobin`, `haematocrit`, `oedema` and `tumour` remain where they transcribe the BMJ Open source table and clinical text.

---

## 3. Changes made to the **core** record

### 3.1 `distributions` — `format: TXT` removed from two entries (audit: high)

The audit's principal objection was `format: TXT` asserted for `cardiac_ecg/` (WFDB) and `environment/` (ESDS ASCII), where the bundle states only the governing standard and names no file format.

Both `format` values are **removed**. Each entry now carries a `notes` explaining the omission: for `cardiac_ecg/`, that WFDB comprises paired signal and header files with no extension, container or media type named in the bundle; for `environment/`, that the bundle names only the ESDS guidelines and no specific delimited or plain-text format, "so the `format` and `media_type` slots are omitted rather than approximated."

The audit also questioned the slot and object shape themselves. The `distributions` block is **retained** — see §4.1 for why.

### 3.2 `distributions` — JSON inference now disclosed (audit, related)

`wearable_activity_monitor/` and `wearable_blood_glucose/` keep `format: JSON` / `media_type: application/json`, but each now carries a `source_caveats` stating that the bundle does not name a file format for the directory beyond Open mHealth, and that JSON is inferred from the dataset-level format list plus Open mHealth being a JSON schema library.

### 3.3 `distribution_formats` — commentary object removed (audit: low)

The original emitted a fourth `DistributionFormat` carrying only a `notes` about DICOM being inexpressible — an object naming no format. That object is **gone**. In its place the core now mirrors the full record's expanded list: `DICOM`/`application/dicom` is stated directly (the enumeration does admit it at this slot), alongside `CSV`, `JSON`, `MD`, `WFDB`, ESDS delimited ASCII, and one closing commentary object recording the dataset description's four declared media types.

### 3.4 `informed_consent.withdrawal_mechanism` — notification content removed (audit: medium)

The trailing sentence about participants being notified in advance is **removed** from `withdrawal_mechanism`. The field now answers only what it asks. The notification content is relocated to core `notes` under a "Notification of participants" heading, with the fuller account (mailed letters, personalized links, access codes, QR codes, REDCap interface) restored from the bundle.

### 3.5 `is_deidentified` — privacy content moved to `notes` (audit: medium)

Participant-privacy material had been folded into `deidentification_details`. `deidentification_details` now holds only de-identification content. The privacy measures — participant identifier scheme, re-identification risk, watermarking, access gating, device selection, storage controls — sit in a `notes` field that opens by stating why they are there: "recorded here because the core schema has no separate slot for them."

### 3.6 `notes` — compensation given a heading; citation retained (audit: medium)

`participant_compensation` has no counterpart in the core inventory, so the content stays in `notes`; it is now under an explicit "Participant compensation" heading alongside "Citation", "Notification of participants", "Biorepository" and "Return of results", rather than trailing as an unlabelled sentence.

### 3.7 `citation` — deliberately not restored (audit: medium)

The audit flagged that full carries `citation` while core relocates it to `notes`. This is **unchanged**: the core record still has no `citation` slot and still carries the recommended citation in `notes`, now under a "Citation" heading and cross-referenced from `existing_uses.notes`. See §4.2.

### 3.8 `instances` — single object retained, with the omission explained (audit: low)

Unlike the full record, core keeps one participant-level `Instance`. A `source_caveats` was added stating that the participant-level instance spans nine data types with different substrates, that no single `data_substrate` term applies, and that the per-modality substrates are enumerated in the full record.

### 3.9 Changes mirroring the full record

`creators` (19 objects), `funders` (grant identifiers removed, Microsoft added), `license`, `keywords`, `collection_timeframes` (5 objects), `sampling_strategies.strategies`, `data_governance` caveat, `related_datasets` caveats, `preprocessing_strategies`, `at_risk_populations.source_caveats` (now cross-references `sampling_strategies`), `external_resources`, and `source_caveats` items (12), (14) grant identifiers, (15) format vocabulary, (16) creator identity — all applied identically. `missing_data_documentation` fields converted from lists to prose blocks to match the full record.

---

## 4. Findings left as-is, and why

### 4.1 `distributions` slot and object shape (audit: high)

The audit could not verify `distributions`/`CoreDistribution` against the supplied digest, because that digest describes the **full** `Dataset` class only. The core schema is a separate file (`data_sheets_schema_core_all.yaml`) whose inventory was not supplied. The audit's own wording is conditional: *"if it is declared, the digest given does not describe it."* I cannot state that the slot is undeclared without the core digest supporting me, and I have no such support either way. The block is retained; validation against the core schema is the test that settles it. The `format` values that the audit could positively fault — `TXT` against the bundle — were removed (§3.1).

### 4.2 `citation` absent from core (audit: medium)

Same reason. `citation` may or may not be in the `CoreDataset` inventory. Placing it and having core fail validation is worse than the present arrangement, in which the citation text is fully present in `notes`, headed, and reachable. If the core schema does declare `citation`, this is a residual imperfection I am flagging rather than concealing.

### 4.3 `id` as `doi:` CURIE with fragments (audit: low)

`doi:10.60775/fairhub.3` and its fragments (`#training-split`, `#cardiac_ecg`) are unchanged. The audit is right that DOI resolution admits no fragment component. But the v5 minting rule requires a fragment on an *attested* identifier for labels with no external referent, and the DOI is the only dataset-level identifier the bundle supplies. The alternative — inventing a prefix — is explicitly forbidden. Non-resolution of an internal label is the lesser defect.

### 4.4 `publisher` as a homepage URL (audit: low)

`https://fairhub.io/` retained. The bundle gives `publisherName: FAIRhub` with no registry identifier. The range is `uriorcurie`; its URI half is the fallback where no declared prefix covers the identifier. Supplying a registry identifier from my own knowledge would breach the evidence boundary.

### 4.5 `creators[0].id` as project homepage (audit: medium)

Retained, with a new `source_caveats` making the limitation explicit. Same reasoning as §4.4: no registry identifier for the consortium appears anywhere in the bundle.

### 4.6 Mixed identifier forms in `related_datasets` (audit: low)

Retained. The `doi:` CURIEs and the two documentation URLs coexist because `dataset_description.json` declares both documentation sites as `relatedIdentifier` entries with `relationType: IsDocumentedBy`. Removing them would discard attested relationship statements; each now carries a caveat noting the target is not a dataset and duplicates `external_resources`.

### 4.7 `conforms_to_standard: CDS` (audit: high, but self-resolving)

The audit's own text confirms `CDS` is in the permitted values and flags only that it could not check whether the schema means "Clinical Data Standard" or "Clinical Dataset Structure". The bundle consistently says Clinical Dataset Structure. No change.

### 4.8 `total_size_bytes` vs. directory sums (audit: low)

`3815969779678` retained — it is the attested API value. The internal tension the audit noted is resolved by rewriting caveat (12) to state the attested totals only and decline the derived sum (§2.9).

### 4.9 `download_url` omitted (audit: low)

Still omitted. `https://fairhub.io/datasets/3/access` is an access-request landing page, not a direct data URL, and the slot description distinguishes the two. It is recorded in `data_governance.access_review_process` and `third_party_sharing`.

### 4.10 `at_risk_populations.special_protections` as eligibility criteria (audit: low)

Retained in place. The criteria are now *also* in `sampling_strategies.strategies`, and the caveat cross-references them. Given `at_risk_groups_included: false`, "these groups were excluded" is the correct answer to what protections applied.

---

## 5. Results

| | Full | Core |
|---|---|---|
| Top-level slots populated | **83** | **73** |
| `linkml-validate` | **PASS** (`Dataset`) | **PASS** (`CoreDataset`) |

**Core/full divergence:** zero. Every slot in the core record now has a counterpart in the full record. No core slot states content the full record does not.

**Audit disposition:** 3 high — 1 resolved (`TXT`), 1 not actionable without the core digest (`distributions` shape), 1 self-resolving (`CDS` is permitted). 15 medium — 14 resolved, 1 not actionable (`citation`). 19 low — 11 resolved, 8 retained with documented reasoning.

**Provenance:** recorded via `d4d provenance record` after Phase 4.

**Referent:** the AI-READI **v3.0.0 public data release** (DOI `10.60775/fairhub.3`) — not the study, not the version series. Held consistently across both records; version-series material sits in `version_access`, `updates` and `related_datasets`.