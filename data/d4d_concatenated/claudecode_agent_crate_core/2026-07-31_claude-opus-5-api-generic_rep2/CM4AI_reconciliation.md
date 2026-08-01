# D4D Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared input bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. Both records describe **the CM4AI June 2026 Data Release (Beta), DOI `10.18130/V3/HIGT4C`**, as published in the University of Virginia Dataverse and as described by the RO-Crate root entity `https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`.

This referent was selected because it is the only release in the bundle that is simultaneously (a) the current release per the CM4AI data-releases page and the curation note on the HIGT4C source file, (b) the subject of the included RO-Crate evidence, and (c) the subject of the included AI-readiness self-assessment. The March 2025 (`B35XWX`), June 2025 (`F3TD5R`), and October 2025 (`K7TGEM`) releases present in the bundle are treated as **prior versions of the same conceptual resource**, not as the record's referent; they are represented under `related_datasets`, `errata`, and `version_access` rather than as competing subjects.

The CM4AI *project* — the Bridge2AI Functional Genomics Data Generation Project, NIH award `1OT2OD032742` — is treated as **context**, not as the referent. Project-level facts (six modules, the three-pillar structure, workforce development, teaming) appear only where they bear on the dataset's provenance, governance, or maintenance.

This choice is held consistently across both records.

---

## 2. Audit outcome summary

The audit traced all high-salience factual claims to the declared bundle. Every verifiable identifier, quantity, date, checksum, accession, license term, and governance statement resolved to source. No prior-D4D-shaped content was detected in either record. The four cross-source conflicts recorded under `anomalies` are genuine conflicts present in the evidence and were correctly surfaced rather than silently resolved.

The findings were predominantly **structural** rather than factual. One finding (`distributions` in the core record) carried validation risk. One finding identified a small unsupported inference. The remainder concerned redundancy, under-signalled qualifiers, or slot-scope drift.

| Severity | Count | Changed | Left as-is |
|---|---|---|---|
| High | 1 | 1 | 0 |
| Medium | 5 | 4 | 1 |
| Low | 9 | 3 | 6 |
| **Total** | **15** | **8** | **7** |

---

## 3. Changes made

### 3.1 Core record — `distributions` block re-expressed as `file_collections` *(high)*

**Finding:** The core record carried a `distributions` block. `distributions` is not present in the `CoreDataset` slot inventory; the file-level inventory is carried by `file_collections`.

**Action taken:** Verified against `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`. `distributions` is not a declared `CoreDataset` slot. The block was re-expressed as `file_collections` entries, one per distributed archive, each assigned a required `id` derived from the release DOI plus the archive filename (e.g. `https://doi.org/10.18130/V3/HIGT4C#file-cm4ai_ifimages_MDA-MB-468_untreated`). Per-entry `description`, `file_count` where stated, `total_bytes` where stated, and MD5 checksums were preserved without alteration.

**Rationale:** This was the only finding with validation-failure potential. Re-expression preserves every evidenced fact while conforming to the core schema. No content was dropped.

### 3.2 Core record — `citation` added *(medium)*

**Finding:** The full record populated `citation` with the verbatim recommended citation; the core record omitted it.

**Action taken:** Confirmed `citation` is a declared `CoreDataset` slot. Added the verbatim citation string from the RO-Crate root `citation` property, matching the full record exactly.

**Rationale:** Directly stated evidence, present in a declared core slot, with no justification for omission. Omitting it made the two records inconsistent on a slot both support.

### 3.3 Core record — `total_size_bytes` added *(medium)*

**Finding:** The full record carried `total_size_bytes: 21051331945400` from `evi:totalContentSizeBytes`; the core record omitted it.

**Action taken:** Confirmed `total_size_bytes` is a declared `CoreDataset` slot. Added the value, matching the full record.

**Rationale:** As above — directly stated, core-declared, unjustifiably omitted.

### 3.4 Full record — `known_biases`: "aneuploid" removed *(low, but factual)*

**Finding:** The bias entry "Cancer cell line genomic context" asserted MDA-MB-468 is "aneuploid". The bundle states the line is triple-negative, derived from a metastatic pleural effusion of a 51-year-old Black female, and well characterised by transcriptomic, mutational-profile, and whole-genome-sequencing data. It does not state aneuploidy.

**Action taken:** Deleted "aneuploid" from both records. Retained "transformed", which is supported by the line's carcinoma origin as described.

**Rationale:** This was the only unsupported factual inference located in either record. Aneuploidy is a reasonable expectation for a metastatic carcinoma line, but expectation is not evidence. Under the provenance guard, an inference that the bundle does not carry is a defect regardless of its biological plausibility. Removal was applied to both records to preserve consistency.

### 3.5 Both records — `subsets`: external-deposition qualifier added *(medium)*

**Finding:** The KOLF2.1J NPC, neuron, and cardiomyocyte subset descriptions asserted representation "by SEC-MS protein correlation profiling" without noting that the distributed archive (`cm4ai_mass-spec_KOLF2.zip`, 171.8 KB) is a metadata/manifest archive and the 1.11 TB of profiling data resides externally at MassIVE `MSV000100676`. The qualifier was present under `known_limitations` and in the file-collection descriptions but absent from `subsets`, so `subsets` read as though the profiling data ship with the release.

**Action taken:** Appended "via external deposition at MassIVE MSV000100676" to the affected subset descriptions in both records.

**Rationale:** The original wording was not false, but it under-signalled a material access condition at the point a reader would most likely consult it. The correction adds no new claim; it relocates an already-recorded qualifier to where it is load-bearing.

### 3.6 Full record — `subsets`: DMSO/control conflation tightened *(medium)*

**Finding:** The untreated MDA-MB-468 subset description conflated the SEC-MS "control" condition with the AP-MS "DMSO vehicle control", presenting both as untreated-subset content. The release description states AP-MS data are "for MDA-MB-468 breast cancer cells + treatment", and the AP-MS crates describe DMSO-treated samples as vehicle controls *within* treated batches.

**Action taken:** Rewrote the description to attribute SEC-MS control replicates (1, 2, 4) to the untreated subset, and to describe the AP-MS DMSO samples separately as within-batch vehicle controls belonging to the paclitaxel and vorinostat AP-MS experiments rather than to the untreated subset.

**Rationale:** The two control types are not interchangeable. SEC-MS controls are untreated-condition samples; AP-MS DMSO samples are vehicle controls internal to a treated experimental design. Merging them misrepresents the AP-MS batch structure, which the bundle describes explicitly.

### 3.7 Full record — `errata`: "identical" softened to "identical reported sizes" *(low)*

**Finding:** The third erratum stated IF archive sizes are "identical" across the October 2025 and June 2026 releases. The bundle reports 4.6 GB / 3.8 GB / 4.2 GB in both, so the claim holds at the stated precision — but these are rounded one-decimal display values, and "identical" overstates what such a figure can establish.

**Action taken:** Changed to "identical reported sizes" in the full record.

**Rationale:** The erratum's substantive point is that the archives changed MD5 while retaining the same displayed size, which is the noteworthy observation. Softening the wording preserves that point without asserting byte-level equality the evidence cannot support.

### 3.8 Full record — `data_protection_impacts` empty list removed *(low)*

**Finding:** The slot was present with an explicit empty list (`[]`).

**Action taken:** Removed the slot.

**Rationale:** Under the stated decision rule — prefer omission over inference, and an absent slot is a correct answer when evidence is absent — an explicit empty list adds no information and risks being read as an assertion that DPIAs were sought and none were found. The bundle contains no DPIA evidence either way. Omission is the cleaner and more honest encoding.

---

## 4. Findings left as-is

### 4.1 Full record — `citation` / `creators` author-set divergence *(medium — left as-is)*

**Finding:** The recommended citation names 47 authors including Park S and Zhao X while omitting Marquez C; the `creators` list includes Marquez C and omits Park S and Zhao X. The audit recommended a cross-reference in `citation`.

**Left as-is because:** The divergence is real and present in the bundle — the RO-Crate `citation` string and the RO-Crate `author` array genuinely disagree, as do the Dataverse author list and the citation. It is **already recorded explicitly under `anomalies`**, which is the slot designed to carry exactly this class of documented discrepancy. Adding an editorial parenthetical inside `citation` would modify a verbatim recommended-citation string, which is the one field where verbatim reproduction has independent value: a user copying it for attribution should receive what the publisher supplied, not an annotated variant. The anomaly record is the correct locus. No change.

### 4.2 Both records — `version` compound narrative string *(low — left as-is)*

**Finding:** `version` carries `"2.0 (University of Virginia Dataverse published version 2.0 ... the RO-Crate root metadata for the same release declares version \"1.0\")"`, embedding a conflict in an identifier field and degrading machine usability.

**Left as-is because:** The two authoritative sources in the bundle disagree on the version of the same release, and the decision rules direct that where sources disagree, the record should represent what the evidence states rather than silently selecting one. Reducing the slot to a bare `"2.0"` would be a silent selection: a consumer reading only `version` would have no signal that the RO-Crate — the very artifact the record is partly derived from — says otherwise. The conflict is also recorded under `anomalies`, but `anomalies` is not consulted by a machine reading `version`. Retaining the qualifier keeps the disagreement visible at the point of use. The usability cost is real but is the lesser harm. Applied consistently in both records.

### 4.3 Full record — `status` mixing maturity and policy notice *(low — left as-is)*

**Finding:** `status` combines release maturity ("Beta release; published in the University of Virginia Dataverse") with the repository-level notice about review "in compliance with Administration directives", which is also recorded under `retention_limit` and `regulatory_restrictions`.

**Left as-is because:** The notice is well evidenced — it appears on the Dataverse collection banner, on both Dataverse dataset pages, and twice on the CM4AI site — and it materially conditions the resource's current availability status. A consumer reading `status` to determine whether the dataset is dependably retrievable needs that signal. The redundancy across three slots is intentional layering, not duplication error: each slot addresses a different question (current state, retention horizon, regulatory posture). No change.

### 4.4 Full record — `creators` affiliation and ORCID in `description` *(low — left as-is)*

**Finding:** Creator entries pack affiliation and ORCID into free-text `description` rather than dedicated structured slots.

**Left as-is because:** Inspection of the `Creator` class confirms it does not expose dedicated affiliation or identifier slots in this schema version. `description` is the only available carrier. All values are directly supported by the RO-Crate `Person` entities and the Dataverse author block. This is a schema-expressiveness limitation, not a record defect. No change.

### 4.5 Both records — `collection_timeframes` vs. `created_on` tension *(low — left as-is)*

**Finding:** The Dataverse "Data Creation Date" of 2025-02-27 (identical to "Deposit Date") sits oddly against a stated collection window of 2022-09-01 to 2026-06-01, and is more plausibly a record-creation artifact than a data-creation date. The audit suggested flagging it under `anomalies`.

**Left as-is because:** The record already reproduces the field faithfully and does not over-claim: `collection_timeframes` carries the rai-declared 2022–2026 window, and `created_on` carries the Dataverse field value with its source identified. Adding an anomaly entry would require asserting that the Dataverse field is *wrong* or *mislabelled* — a judgment the bundle does not support. The bundle supplies both values without comment; inferring that one is an artifact is exactly the kind of plausible-but-unevidenced reasoning the guard excludes. Recording both accurately and letting the reader observe the tension is the correct handling. No change.

### 4.6 Full record — `external_resources`: Schaffer et al. 2025 entry *(low — left as-is)*

**Finding:** The entry cites Schaffer et al. 2025 (*Nature* 642:222–231), which describes U2OS-cell mapping — a different cell line and dataset from anything in this release. The audit suggested clearer phrasing to prevent a reader inferring U2OS content is present.

**Left as-is because:** The entry is already described as a "Related full-scale multimodal cell map study cited by the release", which locates it as related-work rather than release-content, and its inclusion is directly warranted: it appears in the RO-Crate `associatedPublication` array. The record nowhere lists U2OS among the cell lines, subsets, or file collections; `subsets` and `file_collections` are unambiguous that the release covers MDA-MB-468 and KOLF2.1J only. The risk of misreading is low and the existing phrasing is adequate. No change.

### 4.7 Full record — `relationships` scope drift *(low — left as-is)*

**Finding:** The "Hierarchical containment relationships" entry describes the cell-map DAG, then notes it is "produced downstream from these data and not included in this release". Since `relationships` concerns relationships between instances *in* the dataset, describing an absent structure stretches the slot.

**Left as-is because:** The entry is accurate and explicitly self-qualifying — it states its own absence from the release in the same breath. The DAG structure is the organising concept the release's instances are collected to support, and documenting the intended relational target aids interpretation of what the AP-MS, SEC-MS, IF, and perturb-seq instances are *for*. The caveat prevents any over-claim. This is mild scope drift with clear interpretive value and no factual cost. No change.

---

## 5. Provenance-guard assessment

No content in either record derives from a previously generated D4D artifact. `CM4AI_crate_d4d.yaml`, `ro-crate-linkml.yaml`, and `ro-crate-datasheet.html` were withheld from the bundle by design and were not consulted. Nothing under `data/d4d_concatenated/` was read at any phase.

All factual content resolves to one of:
- the ten source documents in the concatenated bundle,
- `CM4AI_crate_metadata_reduced.json`,
- `ai_ready_score.json`.

Verbatim `rai:*` field text (limitations, biases, use cases, maintenance plan, collection description, missing-data statement) was carried through with attribution to the crate rather than paraphrased, preserving traceability.

---

## 6. Consistency between records

After reconciliation, the two records agree on every shared slot: identifier, title, version string, license and use terms, subsets, cell lines, biases, limitations, prohibited uses, ethics and governance statements, funders, collection timeframe, and citation. The core record is a proper subset of the full record's factual content; it contains no claim absent from the full record.

---

## 7. Results

| Metric | Value |
|---|---|
| Full record — populated slots | **58** |
| Core record — populated slots | **29** |
| Full record — validates against `Dataset` | **Yes** |
| Core record — validates against `CoreDataset` | **Yes** |
| Reconciliation outcome | **Complete — 8 changes applied, 7 findings retained with documented rationale** |

**Validation commands run:**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d_core.yaml
```

Both returned clean.

**Provenance record written:**

```
poetry run d4d provenance record --project CM4AI \
  --method claudecode_agent_crate \
  --label 2026-07-31_claude-opus-5-api-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt
```