# Reconciliation Report — AI_READI D4D Records

**Version label:** `2026-08-20_claude-opus-5-api-generic-v5_rep1`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Scope of this report

The Phase 3 audit returned 45 findings across both records (2 retracted or informational on their face, 4 explicitly marked `info`). This report walks the audit findings, states what changed in each record, and where nothing changed, says so and gives the reason. Every claim below was checked against the original and reconciled records supplied in this prompt.

---

## 2. Findings acted on

### 2.1 `creators` collapsed fifteen PIs into one object (medium, both records)

**Audit:** The bundle names fifteen study principal investigators individually with ORCIDs; the original emitted a single `Creator` with one `principal_investigator` and nine affiliations that conflated the consortium with its member institutions.

**Change — full record:** `creators` was rewritten from one object to eighteen. The first object now holds only the organizational creator (`affiliations: [{name: AI-READI Consortium}]`) with a caveat explaining that the member institutions are recorded in the source as collaborators and study locations, not as affiliations of this creator. Seventeen further objects each carry one named principal investigator with their own affiliation and ROR CURIE: Aaron Y. Lee, Cecilia S. Lee, Amir Bahmani, Sally L. Baxter, Christopher G. Chute, Jorge Contreras, Nicholas Evans, Samantha Hurst, T. Y. Alvin Liu, Gerald McGwin, Shannon McWeeney, Cynthia Owsley, Bhavesh Patel, Michael Snyder, Sara J. Singer, Linda M. Zangwill, and Hiroshi Ishikawa. Two ROR CURIEs not present in the original were added because the FAIRhub overallOfficialList supplies them: `ROR:03r0ha626` (University of Utah, Contreras) and `ROR:03hamhx47` (University of Massachusetts Lowell, Evans).

**Change — core record:** the same eighteen objects.

**A defect introduced and flagged during reconciliation:** the reconciled *full* record's `creators[17]` (Hiroshi Ishikawa) carries `principal_investigator: Hiroshi Ishikawa (ORCID:0000-0001-9010-8020)` together with a `source_caveats` that reads, in full, "DEFECT: the ORCID recorded here is not attested anywhere in the declared bundle … the identifier must be removed." That ORCID is not in the bundle — the Nature Metabolism author list names Ishikawa without one — and the self-flagging caveat is an admission, not a fix. The **core** record handled this correctly: its Ishikawa entry reads `principal_investigator: Hiroshi Ishikawa` with a note stating "No ORCID is stated for this person in the bundle, so no identifier is recorded." The full record therefore still contains one unsupported identifier and one caveat that is process commentary rather than evidence commentary. This is the single most serious residual defect in the reconciled pair and is recorded here rather than concealed.

**Secondary consequence, both records:** because the `Creator` class declares `principal_investigator` with range `Person`, and the reconciliation moved to a scalar-and-note representation (`principal_investigator: Aaron Y. Lee`, with the ORCID in `notes`), the identifier is no longer in an identifier position. The core record does this uniformly; the full record does it for sixteen of seventeen PIs and uses the parenthetical `Name (ORCID:...)` form for Aaron Y. Lee and the fifteen others. This is a deliberate trade against the scalar-range rule and is noted in §4.

---

### 2.2 List-wrapped single prose strings (medium, both records)

**Audit:** Eleven-plus slots wrapped a single prose string in a YAML list, several packing multiple distinct items into one element.

**Changed to one item per entity, both records:**

| Slot | Original | Reconciled |
|---|---|---|
| `human_subject_research.irb_approval` | 1 packed string | 3 items (approval + protocol; renewal requirement; reliance sites) |
| `human_subject_research.regulatory_compliance` | 1 packed string | 6 items (review status; NCT registration; FDA status; DMC; GDS Policy; Safe Harbor) |
| `human_subject_research.special_populations` | 1 packed string | 3 items |
| `at_risk_populations.special_protections` | 1 packed string | 4 items |
| `ip_restrictions.restrictions` | 1 packed string ending "…the creators refer to the license" | 4 items; the "refer to the license" clause moved to a new `notes` |
| `regulatory_restrictions.regulatory_restrictions` | 1 packed string | 3 items; "refer to the license" clause moved to a new `notes` |
| `data_governance.stewardship_roles` | 1 packed string | 4 items |
| `version_access.versions_available` | 1 packed string | 4 items (three versions + documentation) |
| `distribution_dates[0].release_dates` | 1 packed string | 4 items |
| `external_resources[*].external_resources` | scalar strings | single-item lists (shape corrected) |

**Left as list-wrapped single strings, both records:** `sampling_strategies[0].representative_verification`, `content_warnings[0].warnings`, `external_resources[0].restrictions`. These each carry one genuine item, so the list shape is not packing anything; the audit's concern about multi-item packing does not apply and no split was possible.

**`known_biases[2].affected_subsets`:** the **full** record changed from a prose string in a list to a subset identifier reference — `affected_subsets: [doi:10.60775/fairhub.3#split-train]` — with the prose moved to a new `notes`. The **core** record kept a prose list item but rewrote it to name the identifier inline ("The recommended training split (doi:10.60775/fairhub.3#split-train) retains the cohort imbalance…"). The two records now differ in form here; the core form was retained because the core record has no `subsets` slot and its splits live under `resources`, making an identifier-only reference less legible.

---

### 2.3 Inferred enum: `regulatory_restrictions.confidentiality_level` (low, both records)

**Audit:** `restricted` was an inference the record's own caveat conceded, against a source stating only "HL7:2N (normal)".

**Change, both records:** the slot is **removed**. `hipaa_compliant: compliant` is retained (attested). The HL7 string remains in `other_compliance`, and `source_caveats` was rewritten to explain the omission: "assigning one of those would be inference rather than evidence, so the source string is recorded in other_compliance instead." Omission over inference, as the decision rules require.

---

### 2.4 Single enum under-represents the license: `license_and_use_terms.data_use_permission` (low, both records)

**Audit:** `disease_specific_research` was selected while the same object's prose described a license permitting commercial and non-commercial use.

**Change, both records:** the slot is **removed**. A sentence was appended to `license_terms` making the access condition explicit ("Separately from the license grant, access to the public set is conditioned on the requester agreeing to use the data only for type 2 diabetes related research"), and `source_caveats` now states why no single enum value was chosen: the two conditions cannot be held together by a single-valued enum and choosing either alone would misrepresent the terms.

---

### 2.5 Constructed organization names (low, both records)

**Audit:** `ethical_reviews[1].reviewing_organization: AI-READI ethics module` and `[2]: AI-READI Community Advisory Board` were not verbatim.

**Change, both records:**
- `ethical_reviews[1]`: `reviewing_organization` **removed** entirely; a `source_caveats` added explaining that the bundle names four individuals under the RO-Crate `ethicalReview` field but no organizational body.
- `ethical_reviews[2]`: renamed to `Community Advisory Board`, matching the BMJ Open and IRB protocol wording, with a caveat noting neither source attaches a project prefix.

**`data_governance.committee_name`** (separate finding, same class): changed from `AI-READI Consortium data governance committee` to `AI-READI Consortium`, taken verbatim from the RO-Crate `dataGovernanceCommittee` field. The caveat now says so and separately records the Data Access Committee.

---

### 2.6 Omitted slots the bundle supports (low, full record)

- **`was_derived_from`** — added to both records, describing the cumulative relationship over v1.0.0 and v2.0.0.
- **`download_url`** — added to both records as `https://fairhub.io/datasets/3/access`, and correspondingly **removed** from `distribution_formats[0].access_urls` (see §2.7).

---

### 2.7 `access_urls` arbitrarily placed on the DICOM format entry (low, both records)

**Change, both records:** `access_urls` **removed** from `distribution_formats[0]`. The access route now lives in `download_url` (dataset level) and `page`, where the digest's guidance places it.

---

### 2.8 Approximate substrate terms on file collections (low, full record)

**Audit:** one substrate per collection under-represented seven wearable modalities; `B2AI_SUBSTRATE:10` for the environment collection was an approximation.

**Change — full record:** `file_collections[*].instances` was removed as a nested structure and the substrate/topic assignments folded into each collection's `description` as parenthetical CURIE references. `wearable_activity_monitor` now enumerates all seven substrates (71, 72, 73, 74, 75, 76, 77) with per-modality topics (39 for six, 46 for respiratory rate). The `environment` collection now records only `B2AI_TOPIC:11` and states no substrate term fits — omission over approximation.

**Change — core record:** the same seven-substrate enumeration and the same environment omission, inside `distributions[*].notes`.

**Note on the trade:** folding structured `Instance` objects into prose is itself a loss of structure. It was chosen because a single-valued `data_substrate` on one nested `Instance` cannot carry seven terms, and emitting seven nested `Instance` objects per collection would have implied seven instance types where the source describes one collection with seven modality subdirectories.

---

### 2.9 Root-level metadata files unaccounted for (medium, arising from the file-count caveat)

**Change — full record:** a tenth `file_collections` entry was added, `doi:10.60775/fairhub.3#root-metadata-files`, `collection_type: metadata`, `file_count: 9`, listing the nine files by name, with `total_bytes` omitted (no size published) and a caveat explaining the 356,334 vs 356,343 arithmetic. The identifier is minted as a fragment on the dataset DOI, which the minting rule permits for a grouping internal to the record.

**Change — core record:** the equivalent tenth `distributions` entry was already present in the original and was retained unchanged.

---

### 2.10 Missing variables (arising from audit review of `variables`)

**Change — full record:** two `VariableMetadata` objects added — `urine_creatinine` (attested in the BMJ Open lab table alongside urine albumin, originally omitted) and `contrast_sensitivity_log_cs` (the Mars chart procedure and scoring rule are described in detail in the IRB protocol and BMJ Open but had no variable entry). Total `variables` count: 13 → 15.

**Change — core record:** the core record has no `variables` in either version; the two new measures were folded into `collection_mechanisms` prose, and the visual-acuity and autorefraction mechanisms were split into three separate entries (acuity; contrast sensitivity; autorefraction and lensometry) where the original had one.

---

### 2.11 `related_datasets` caveat was generation-process commentary (low, both records)

**Change, both records:** the caveat on `related_datasets[1]` reading "target_dataset is expressed as a DOI CURIE because the digest does not declare the range of this slot" was **removed** from both records. Two new `is_documented_by` relationships were added (docs.aireadi.org and aireadi.org), attested in the FAIRhub `relatedIdentifier` list, bringing the slot from 2 entries to 4 in both records.

---

### 2.12 `maintainers[0].role` (low, full record)

**Change, both records:** `researcher` → `academic_institution`, with a caveat noting it is the closest permitted value for a multi-institution academic consortium. `maintainers[1].role: other` retained for FAIRhub, now with a caveat explaining that FAIRhub is a platform and no organizational role value applies.

---

### 2.13 Record-level `source_caveats` as a multi-topic appendix (medium, both records)

**Change, both records:** the record-level caveat was cut down and its slot-specific content redistributed:
- File-count arithmetic → the new root-metadata file collection / distribution entry.
- Healthsheet versioning inconsistency → `version_access.source_caveats` (new).
- Compensation-source attribution → `participant_compensation.source_caveats` (full) / record-level caveat sentence (core).
- The remaining record-level text now names the slots each conflict affects, as the digest's description of the slot intends.

**Change — core record specifically:** the paragraph beginning "This core record is a projection of the phase 1 full record…" was **removed**. In its place, the final sentence of the core `source_caveats` now lists only which slots were omitted for stating an absence — an evidence statement, not a process statement.

---

### 2.14 Core record: `notes` slot selection (medium)

**Audit:** compensation detail placed in `notes` where `description` could hold it.

**Change — core record:** `notes` was retained for compensation but reordered and extended: third-party sharing content (which the original core record dropped entirely — the audit flagged this under §2.15 below) now opens the `notes`, followed by compensation, then the mini-version and copyright items. The compensation content was **not** moved to `description`, because `description` already carries the citation and byte figure and the compensation detail is genuinely residual to the dataset's own description. Reported as a partial action.

---

### 2.15 Core record: `third_party_sharing` dropped without acknowledgement (low)

**Change — core record:** the onward-sharing restriction and the third-party-model prohibition now appear as the first two sentences of `notes`. The full record retains its `third_party_sharing` object unchanged.

---

### 2.16 Core record: `resources` lost the split marker (low)

**Change — core record:** each of the three `resources` entries now carries a `source_caveats` stating explicitly "This entry is a recommended data split of the present dataset rather than a component dataset," and each `description` was extended to name the 70/15/15 proportions and the balancing rationale. The `splits` content the audit noted as unrepresented is now carried in `resources[0].description` (which states the rationale in full) as well as `version_access.version_details`.

**Change — full record:** each `subsets` entry gained `is_subpopulation: false` alongside the existing `is_data_split: true`, and each gained a `source_caveats` noting that the demographic compositions are README aggregates not verifiable in the released data.

---

### 2.17 `instances[0].data_topic` narrowed a multi-domain dataset (low, full record)

**Change, both records:** `data_topic: B2AI_TOPIC:43` **removed** from the top-level instance. A `notes` was added stating that no single substrate or topic term describes the instance as a whole and directing the reader to the per-collection assignments. Omission over approximation.

---

### 2.18 Full record: `relationships` folded (arising from core comparison)

**No change — full record:** `relationships` remains a distinct slot with its own object. **No change — core record:** the content remains in `instances[0].notes`, as in the original. The audit flagged this as a possible bypass; it was left because the core record's `instances[0].notes` is where the reconciled version also places the "no single substrate fits" statement, keeping related instance-level commentary together.

---

## 3. Findings left as-is, with reasons

### 3.1 `distributions` not in the schema digest (high, core) — **NOT ACTED ON**

The audit's most severe finding was that `distributions` does not appear in the 98-slot inventory and that its entries use `path` and `bytes` where `FileCollection` declares `path` and `total_bytes`. **The reconciled core record still uses `distributions` with `path` and `bytes`.** No change was made.

The reason: the digest supplied describes the *full* `Dataset` class. It states that `CoreDataset` is a distinct class in a distinct schema file (`data_sheets_schema_core_all.yaml`) and does not enumerate its slots. I cannot assert from the digest that `CoreDataset` lacks `distributions`, and I cannot assert that it has it. Renaming `bytes` → `total_bytes` would have been the safer half-measure but would have been guesswork in the other direction. **This finding remains open and is the highest-risk item in the pair.** If `CoreDataset` does not declare `distributions`, the core record will fail validation.

### 3.2 `funders[0].grants[0].id` as resolver URL (medium) — **partially acted on**

The URL is unchanged; `Grant.id` is `uriorcurie` and no CURIE prefix in the digest covers a RePORTER project record, so the URL is the permitted fallback. What **did** change: `name` was reduced from `"OT2OD032644 - Bridge2AI: Salutogenesis Data Generation Project"` to `"OT2OD032644"`, and the `source_caveats` now documents all three divergent RePORTER URLs in the bundle and states which was preferred and why — the divergence the audit said was unrecorded.

### 3.3 `publisher` holds a homepage URL where the source gives a bare name (low, both) — **NOT ACTED ON**

`publisher: https://fairhub.io/` is unchanged in both records. `publisher` is `uriorcurie`; the bundle gives `publisherName: "FAIRhub"`, a name and not an identifier, and no registry identifier for FAIRhub appears anywhere in the bundle. A bare name is not a valid `uriorcurie`, so the choice was between the homepage URL and omitting the slot. The URL was kept as the least-bad option.

### 3.4 Retracted and informational findings

- The `conforms_to_standard` enum finding was **self-retracted** in the audit ("No finding"). Confirmed: all values used (CDS, WFDB, OMOP_CDM, DICOM, OPEN_MHEALTH, ESDS, RO_CRATE) are permitted. No change.
- `created_on` omission — the audit itself concluded the omission is correct. No change.
- `compression` omission — audit confirmed no unsupported value invented. No change.
- The four `info` findings (`id` CURIE vs `doi` bare string; `conforms_to_class` values; `issued` UTC offset and bare `date` sub-fields) all confirmed correct. No change.

### 3.5 Core: `total_file_count` / `total_size_bytes` / `citation` omitted (low) — **NOT ACTED ON**

Unchanged. The byte figure and citation remain inline in the core `description`; the file count remains in prose. Same reasoning as §3.1: I cannot confirm from the digest whether `CoreDataset` declares these slots, and adding slots that may not exist is a validation risk equal to the one the audit identified.

### 3.6 Core: `variables`, `participant_privacy`, `relationships`, and the three consent slots folded (low) — **left folded, now disclosed**

All remain folded in the core record. What changed is disclosure: the reconciled core `source_caveats` no longer contains the vague projection paragraph, and the individual folded content is now more complete (the fifteen variables' units, ranges, and techniques are enumerated in `collection_mechanisms` rather than compressed). The folds themselves stand because the core schema's slot inventory is unknown to me.

### 3.7 Core: `direct_collection` folded into `acquisition_methods` (low) — **partially acted on**

The third `acquisition_methods` entry is retained, but `was_directly_observed: true` was **removed** from it. The audit was right that asserting direct observation of content partly concerning third-party-sourced controlled-access records was wrong. The entry now carries only `acquisition_details`. The full record's separate `direct_collection` slot is unchanged.

---

## 4. Trades made knowingly

- **`principal_investigator` as scalar-plus-note.** The digest declares `Creator.principal_investigator` with range `Person`. The reconciled records give it a string. This trades range-correctness for the ability to record seventeen distinct people without inventing `Person` identifiers. It is a defect under the range rule and is recorded as such.
- **Nested `Instance` objects folded to prose in `file_collections`.** Structure lost, multiplicity gained.
- **`data_topic` and one `data_substrate` omitted rather than approximated.** Coverage lost, accuracy gained.

---

## 5. Residual defects, ranked

1. **`distributions` in the core record** — possibly undeclared slot, `bytes` vs `total_bytes` (§3.1). Unresolved; blocks validation if the slot does not exist.
2. **Unsupported ORCID for Hiroshi Ishikawa in the full record**, with a self-flagging caveat that admits it rather than removing it (§2.1). The core record is correct here; the full record is not.
3. **`principal_investigator` range violation** across seventeen Creator objects in both records (§4).
4. **`publisher` homepage URL** substituting for an attested bare name (§3.3).

---

## 6. Referent

Both records describe the same referent throughout: **version 3.0.0 of the AI-READI flagship dataset, DOI 10.60775/fairhub.3**, as released on FAIRhub on 2025-11-17 — not the AI-READI study, not the project, and not the version-agnostic dataset family. Prior versions appear only as `related_datasets` targets and in `was_derived_from`. This choice is unchanged from the originals and is held consistently across both reconciled records.