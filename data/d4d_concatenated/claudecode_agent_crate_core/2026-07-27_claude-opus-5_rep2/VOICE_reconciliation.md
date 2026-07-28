# VOICE full/core reconciliation — 2026-07-27_claude-opus-5_rep2

Arm: **de novo with crate** (documents + RO-Crate evidence)
Runtime: Claude Code · Provider: Anthropic · Model: `claude-opus-5[1m]`
Mode: four-phase project agent · Temperature: 0.0 · Generated: 2026-07-27

| Artifact | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_reconciliation.md` |

---

## Phase 3 — source and provenance audit

### 3.1 Provenance boundary

Every factual input read during this run:

- `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` (the only fact source)
- `data/preprocessed/source_manifest.yaml` (selection reference)
- `data/ro-crate_packages/crate_manifest.yaml` (structure/selection reference; **no dataset fact
  was taken from it** — crate identity, version, DOI, size and Merkle root were read from the
  crate JSON-LD inside the bundle)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`,
  `data_sheets_schema_core_all.yaml`, `D4D_Core.yaml` (structure only)
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md` (procedure)
- Phase 2 additionally read the exact same-run Phase 1 full record above.

**No prior D4D record, evaluation, or reconciliation report was read.** The only contact with
`data/d4d_concatenated/` outside this run's own output paths was a directory *name* listing
(`ls`) used solely to confirm that the `2026-07-27_claude-opus-5_rep2` label was unused; no file
inside `2026-07-27_claude-opus-5_rep1` was opened.

**Withheld crate artifacts were not read, opened, globbed or cited.** Confirmed for all four:
`VOICE_crate_mapped_d4d.yaml`, `ro-crate-datasheet.html`, `ro-crate-preview.html`,
`ro-crate-croissant.json`. The bundle header's exclusion list was treated as disclosure, not as
a pointer.

Structure was derived at runtime from LinkML `SchemaView` over class `Dataset` and class
`CoreDataset`, not from any example record. `d4d:docExample` annotations were not consulted for
values.

### 3.2 Fields populated ONLY from crate evidence

These have **no counterpart in the VOICE document corpus**; the crate is genuinely additive here.
All are scoped to PhysioNet release **v3.0.0**, which is what the crate
(`ark:59853/rocrate-b2ai-voice-3.0.0`) describes.

| D4D field | Crate source |
|---|---|
| `known_biases` (all 5 crate-derived entries: sampling, geographic/cultural, clinical spectrum, device/environment, machine-annotation) | `rai:dataBiases` |
| `known_limitations` (first 5 entries) | `rai:dataLimitations` |
| `imputation_protocols` | `rai:dataImputationProtocol` |
| `annotation_analyses` | `rai:dataAnnotationAnalysis` |
| `machine_annotation_tools` (tool list, descriptions, accuracy caveat) | `rai:machineAnnotationTools`, `rai:dataBiases` |
| `labeling_strategies.data_annotation_platform` / `.data_annotation_protocol` / `.annotator_demographics` / narrative `labeling_details` | `rai:datannotationPlatform`, `rai:dataAnnotationProtocol`, `rai:annotatorDemographics`, `rai:annotationsPerItem` |
| `missing_data_documentation.missing_data_patterns` | `rai:dataCollectionMissingData` |
| `cleaning_strategies` (the pre-release data-manipulation protocol) | `rai:dataManipulationProtocol` |
| `preprocessing_strategies` (the consolidated pipeline narrative; the crate's computation records) | `rai:dataPreprocessingProtocol`, `EVI#Computation` entities |
| `raw_data_sources.source_description` / `.access_details` | `rai:dataCollectionRawData` |
| `collection_mechanisms` / `sampling_strategies` (the consolidated prospective-study narrative) | `rai:dataCollection`, `rai:dataCollectionType` |
| `collection_timeframes` first entry (2023-onward, ~3,000 by Nov 2026, v3.0.0 ≈ 2023–2025) and the static-snapshot entry | `rai:dataCollectionTimeframe` |
| `updates.update_details` (release-coordination narrative) | `rai:dataReleaseMaintenancePlan` |
| `sensitive_elements` (4 of 6 entries) | `rai:personalSensitiveInformation` |
| `data_protection_impacts` (social-impact statement) | `rai:dataSocialImpact` |
| `intended_uses`, `tasks` (benchmarking / acoustic-correlates / fairness entries), `discouraged_uses` (non-operational-use clause) | `rai:dataUseCases` |
| `ethical_reviews` → Hastings Center review by Vardit Ravitsky | `ethicalReview` |
| `ethical_reviews` → USF IRB postal address, telephone, `RSCH-IRB@usf.edu` | `irb` |
| `regulatory_restrictions.confidentiality_level: restricted` | `confidentialityLevel` |
| `regulatory_restrictions` governance contact (Satrajit Ghosh) | `dataGovernanceCommittee` |
| `human_subject_research` FDA-regulated / exemption statements | `fdaRegulated`, `humanSubjectExemption`, `humanSubjects` |
| `license_and_use_terms` licence URL, DUA URL, copyright notice | `license`, `conditionsOfAccess`, `copyrightNotice` |
| `file_collections` / core `distributions`: **all 15 artifacts, all 11 sha256 checksums, all byte counts** | crate `EVI#Dataset` entities |
| crate content size 12.9 GB, Merkle root `f1663e10…`, crate ARK, "117 authors" | root entity, `evi:merkleRootHash`, `ai_ready_score.json` |
| `preprocessing_strategies.used_software` b2aiprep **v3.0.2**, dateModified 2026-01-06 | `EVI#Software` entity |
| `maintainers` — both computations run by "Alastair" (2025-12-16 phenotype ETL, 2026-01-29 feature processing) | `EVI#Computation` entities |
| `known_limitations` → AI-readiness gaps rendering (Data Quality, Domain-appropriate, Associated, Contextualized) | cross-checked against `ai_ready_score.json`; the *table* is also in the docs corpus |
| `anomalies` → crate naming inconsistencies | direct observation of the crate JSON-LD |

### 3.3 Fields populated ONLY from documents (no crate counterpart)

Everything version-current, everything pediatric, and all governance detail the crate omits:

- Adult **v3.1.0** identity: `version`, `doi 10.13026/8xbn-nq66`, `issued 2026-05-01`,
  `page`, `download_url`, release notes, per-feature record counts (29,278 / 32,522 / 28,640 /
  31,855 / 31,872 / 29,289).
- The entire **pediatric** cohort: `resources` entry, `subsets` pediatric entry, `instances`
  pediatric participant and recording entries, SickKids REB approval, reproschema-ui collection,
  pediatric Synapse `syn73617068`, DOIs `10.13026/h995-bt35` / `10.13026/mf9s-5r03`.
- `subsets` (all six disease-cohort entries, with inclusion/exclusion criteria and gold-standard
  validation methods) — Table 1 of the project documentation.
- `funders` (NIH RePORTER award amount, dates, all five grant numbers), `creators` role table,
  affiliations, consortium membership.
- `participant_compensation`, `informed_consent`, `consent_revocations`,
  `collection_notifications`, `collection_consents`, `participant_privacy`, `retention_limit`,
  `at_risk_populations` — IRB protocol and project documentation.
- `ip_restrictions`, most of `license_and_use_terms`, `regulatory_restrictions` export-control
  and Certificate-of-Confidentiality clauses — the Data Transfer and Use Agreement.
- `is_deidentified` identifier inventory, `subpopulations`, `content_warnings`,
  `confidential_elements`, `relationships`, `splits`, `existing_uses`, `use_repository`,
  `errata`, `version_access`, `extension_mechanism`, `external_resources`,
  `related_datasets`, `variables`, `conforms_to` (BIDS v1.9.0).
- `collection_mechanisms` hardware detail (iPad 9th/10th gen, iPad Air 5th gen, Avid AE-36
  microphone, Apple dongle) and the five-recording-site count.

### 3.4 Version scoping — hazard 1: crate v3.0.0 vs documents v3.1.0

Rule applied: **the documents govern the current release; every crate-derived value is labelled
as v3.0.0 evidence.**

| Fact | Value used | Scoping |
|---|---|---|
| Root `version` / `doi` / `issued` / `page` | 3.1.0 / `10.13026/8xbn-nq66` / 2026-05-01 | documents (crate says 3.0.0 / `k81f-qr68`; not used at root) |
| Root `id` | `https://doi.org/10.13026/37yb-1t42` | adult **latest-version** DOI, stable across releases |
| Participant count | 833 | agrees in both; v3.1.0 added no new participants — stated in `instances.label_description` |
| Recording counts | v3.1.0 counts at top level, v3.0.0 counts named as such | both given, each labelled, in `instances` and the v3.0.0 `resources` entry |
| File inventory, sizes, sha256 | crate values | every `file_collections` entry carries `version: 3.0.0`; every core `distributions` description says "as documented in the v3.0.0 RO-Crate" |
| 12.9 GB, Merkle root, crate ARK | crate values | confined to the v3.0.0 `resources` entry description |
| `rai:*` governance content | crate values | each carrying object's `description` says "recorded in the v3.0.0 RO-Crate" |
| Licence / DUA URLs, copyright | crate values | quoted with their explicit `/3.0.0/` paths |
| b2aiprep version | 3.0.2 (crate) | description also records that PhysioNet states the 3.0.0 release was generated with b2aiprep v3.0.0 — both retained, neither silently preferred |
| Release history | full list v1.0 → v3.1.0 | `distribution_dates`, `version_access`, `related_datasets` (`is_new_version_of` → `10.13026/k81f-qr68`) |

No crate value was allowed to override a v3.1.0 document value, and no crate value was
presented as current without its 3.0.0 label.

### 3.5 Version scoping — hazard 2: adult vs pediatric cohorts

The two cohorts are separate PhysioNet projects, not versions of one another. **No crate fact is
attached to the pediatric cohort anywhere in either record.** Enforcement:

- The pediatric cohort appears as its own `resources` entry, its own `subsets` entry, its own
  `instances` entries, its own `ethical_reviews` entry (SickKids REB), and a
  `related_datasets` entry typed `supplements` — explicitly annotated "not a version of the
  adult b2ai-voice dataset".
- Phase 3 corrected three `known_biases.affected_subsets` values that had generalised
  crate-derived (adult) bias statements to "all cohorts"/"all sites"; they now name the adult
  cohort as the crate's scope and add the separately document-sourced pediatric facts as
  distinct list items.
- The `adult-only` limitation records the pediatric dataset in `scope_impact` rather than
  folding the two cohorts together.
- Pediatric collection facts (reproschema-ui, built-in tablet microphone, SickKids-only
  recruitment, ages 2–18, 300 participants, 23,533 recordings, Synapse `syn73617068`) are all
  document-derived.

### 3.6 Corrections made during Phase 3

Five corrections, all applied to the **full** record first, then propagated by regenerating core:

1. **Removed `created_on: 2025-01-17`.** That is the publication date of PhysioNet v1.1, not a
   source-stated dataset creation date; the v1.0 feature release predates it on Health Data
   Nexus. Release chronology is already carried, correctly scoped, in `distribution_dates` and
   `version_access`.
2. **Removed `total_file_count: 15`.** The crate documents 15 `EVI#Dataset` entities but
   `ai_ready_score.json` counts 17 files, and 4 of the 15 `file_collections` are directory
   groupings rather than single files — no single source-supported file count exists at this
   scope. `total_size_bytes` was likewise never asserted (12.9 GB is a rounded, 3.0.0-scoped
   crate value, not a byte count).
3. **Removed `credit_roles` from the Vardit Ravitsky creator entry.** Conducting an ethical
   review is not a CRediT role; the crate's `ethicalReview` statement is retained verbatim in
   the entry description and in `ethical_reviews`.
4. **Removed `external_resources.archival: false`.** The documentation answers "NA", not "no",
   to whether official archival versions exist; the "NA" answer is now recorded as text in
   `future_guarantees` instead of being asserted as a boolean.
5. **Rescoped three `known_biases.affected_subsets` values** (§3.5).

Nothing was back-ported from Phase 2 into Phase 1 as a *new* fact: Phase 2 discovered no
source-supported value missing from the full record. The only core-only content is
`distributions`, which is the schema's own projection of `file_collections`.

### 3.7 Internal consistency checks

Repeated identifiers, versions, dates, counts, licences, access rules, people and organizations
were checked for internal agreement within each file:

- `833` participants: consistent across `instances`, the v3.0.0 and v3.1.0 `resources` entries,
  and the root `description`.
- `10.13026/8xbn-nq66` (v3.1.0), `10.13026/k81f-qr68` (v3.0.0), `10.13026/37yb-1t42` (adult
  latest), `10.13026/h995-bt35` (pediatric v1.1.0), `10.13026/mf9s-5r03` (pediatric latest),
  `10.13026/249v-w155` (v1.1), `10.57764/qb6h-em84` (HDN v1.0): each appears with the same
  version attached everywhere it occurs.
- Access tiers: "registered/credentialed access to features, controlled access to raw audio via
  Synapse after DACO approval" is stated identically in `license_and_use_terms`,
  `distribution_formats`, `raw_sources`, `raw_data_sources` and the `resources` entries.
- Grant numbers `OT2OD032720`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3`, `U24EB037545`,
  `R01EB030362`: each attached to the same grantor throughout.
- One genuine tension is *retained and attributed*, not resolved by fiat: the documentation says
  HIPAA de-identification rules are applied (→ `hipaa_compliant: compliant`) while the DUA says
  the transferred data "is not covered under HIPAA, FERPA or similar laws". Both statements are
  quoted, each with its source, in `regulatory_restrictions`.
- Historical values are kept only with explicit historical scope: the Health Data Nexus
  distribution platform, the semi-annual release cadence statement, the v1.1 512-point-FFT
  spectrogram parameters, the "v.2.0.0 dataset contains only adult populations" study-population
  statement, and the "12 months" collection window are each labelled with the release or document
  they belong to.

### 3.8 Phase 3 result

**PASS.** Both records validate against schema and ontology terms after correction; no
unsupported, stale or mis-scoped assertion remains; no forbidden input was used.

---

## Phase 4 — strict full/core reconciliation

### 4.1 Schema-derived shared slots

Derived at runtime with `SchemaView` over `Dataset` and `CoreDataset` — no hand-written list.

- **Schema-identical slots: 76.** 71 are populated in this pair; 5 (`compression`,
  `conforms_to_class`, `conforms_to_schema`, `modified_by`, `was_derived_from`) are absent from
  both, satisfying the present-in-both-or-absent-from-both rule.
- **Projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).
- **Full-only slots (17), correctly absent from core:** `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`, `file_collections`,
  `parent_datasets`, `participant_compensation`, `participant_privacy`, `related_datasets`,
  `relationships`, `splits`, `subsets`, `third_party_sharing`, `total_file_count`,
  `total_size_bytes`, `variables`.
- **Core-only slots (2):** `distributions` (populated), `dialect` (omitted — the release is not
  tabular, and `is_tabular: false` agrees in both records).

Core was built by copying the 71 populated identity slots verbatim from the Phase 3-audited full
record, so deep identity holds by construction rather than by post-hoc repair. No narrative field
was condensed, paraphrased, reordered or omitted in core.

### 4.2 `resources` projection

Matched by `id`; coverage is equal (5 in both). Every nested key present in the full resource
entries is a `CoreDataset` slot, so the projection dropped nothing (the build step reported zero
dropped keys). Independent re-parse confirms every nested value is identical:

| `id` | scope |
|---|---|
| `https://doi.org/10.13026/8xbn-nq66` | adult v3.1.0 (current) |
| `https://doi.org/10.13026/k81f-qr68` | adult v3.0.0 (the crate's release) |
| `https://doi.org/10.13026/mf9s-5r03` | pediatric v1.1.0 (separate project) |
| `https://www.synapse.org/Synapse:syn72370534` | adult raw audio, controlled access |
| `https://www.synapse.org/Synapse:syn73617068` | pediatric raw audio, controlled access |

### 4.3 Related-content semantic review: `file_collections` ↔ `distributions`

The validator flags this pair for mandatory semantic review. Review performed and recorded here.

15 full `file_collections` ↔ 15 core `distributions`, matched 1:1 on identifier; zero unmatched
on either side. Independently re-parsed and compared:

| Property | Full (`FileCollection`) | Core (`CoreDistribution`) | Result |
|---|---|---|---|
| name | `name` | `name` | identical, 15/15 |
| path | `path` | `path` | identical, 15/15 |
| byte count | `total_bytes` | `bytes` | identical, 11/11 where present; the 4 directory groupings carry none in either record |
| checksum | *(no slot)* | `sha256` | 11 checksums, core-only — no conflict possible |
| compression | `compression` (unset) | `compression` (unset) | agree: no artifact is compressed |
| format / media type | `collection_type` (`processed_data`, `metadata`) | `format`, `media_type` | complementary, not conflicting. The 5 TSV groupings carry `TSV` / `text/tab-separated-values`, matching the crate's declared `text/tab-separated-values`. The 9 Parquet artifacts carry **no** `format`/`media_type`: neither `FormatEnum` nor `MediaTypeEnum` has a Parquet member, so the slots are omitted and Parquet is named in the description instead of being coerced to a wrong enum value. |
| access URL | *(none per file)* | *(none per file)* | agree; per-release access URLs live in `distribution_formats.access_urls` |
| release scope | `version: 3.0.0` on all 15 | "as documented in the v3.0.0 RO-Crate" in all 15 descriptions | agree |
| descriptions | technical description of each artifact | same description plus the Parquet/enum note | no contradiction |

Scope-comparison checks required by the procedure:

- `total_file_count` / `total_size_bytes` are absent from full (Phase 3 §3.6), so there is no
  aggregate-versus-distribution-level scope mismatch to reconcile.
- `dialect` is absent from core and `is_tabular` is `false` in both — consistent with a release
  that is predominantly dense tensor Parquet plus tabular phenotype TSVs.
- Top-level identity/version/access facts (`version` 3.1.0, `doi`, `license`, `publisher`,
  `page`, `download_url`) agree between the two files by identity, and agree in substance with
  `resources`, `version_access`, `distribution_dates` and `distribution_formats`.
- The distributions describe the **v3.0.0** artifact inventory while the root record describes
  **v3.1.0**. This is a labelled historical-release relationship, not a contradiction: v3.1.0 is
  recorded as a minor update with no new participants, the v3.0.0 `resources` entry carries the
  crate's identity, and `related_datasets` types the relationship `is_new_version_of`.

**Result: zero unresolved contradictions** within or between the two records.

### 4.4 Commands run

```bash
# Phase 1
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 3: corrections applied to full, core regenerated, all four validations re-run (above)

# Phase 4
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml \
  --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml
```

### 4.5 Files changed

| File | Change |
|---|---|
| `…/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml` | created (Phase 1); five Phase 3 corrections applied |
| `…/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml` | created (Phase 2); regenerated after Phase 3 corrections |
| `…/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/VOICE_reconciliation.md` | created (Phase 4) |

No previous version directory was written to or overwritten.

### 4.6 Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | **No issues found** |
| `linkml-term-validator` full | **Validation passed** |
| `linkml-validate` core (`CoreDataset`) | **No issues found** |
| `linkml-term-validator` core | **Validation passed** |
| `d4d_pair_consistency --sync-core` | **PASS: 76 schema-identical slots; projected slots=['resources']** — no edits required |
| `d4d_pair_consistency` (independent re-run) | **PASS: 76 schema-identical slots; projected slots=['resources']** |
| Outstanding validator warning | 1 — `semantic-review-required` on `file_collections ↔ distributions`; the review it requires is recorded in §4.3 (15 deterministic matches, 0 unmatched core distributions) |
| Core header `Phase 4 reconciliation: completed` | present |
| Line counts (informational metadata only, **not** a quality gate) | full 2,885 · core 1,993 |
