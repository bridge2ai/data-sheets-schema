# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep1

- **Project**: VOICE
- **Arm**: BASELINE (input documents only)
- **Prompt**: `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- **Runtime / provider / model**: Claude Code / Anthropic / claude-opus-5[1m]
- **Mode**: four-phase project agent
- **Declared input bundle**: `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 source
  documents, 377,706 bytes)
- **Manifest**: `data/preprocessed/source_manifest.yaml`
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d_core.yaml`

## Referent decision

`Dataset` admits one referent. The bundle describes both an adult and a pediatric PhysioNet
project, and the manifest records explicitly that the pediatric release "is a separate PhysioNet
project from the adult b2ai-voice dataset, not a version of it". The project documentation,
however, presents a single "Bridge2AI-Voice Dataset" whose adult and pediatric parts are described
together on one page.

**Chosen referent**: the Bridge2AI-Voice dataset as the consortium's ethically-sourced voice /
speech / respiratory-sound dataset linked to health information, with the adult PhysioNet project
(`https://physionet.org/content/b2ai-voice/`, current v3.1.0) and the pediatric PhysioNet project
(`https://physionet.org/content/b2ai-voice-pediatric/`, current v1.1.0) as `resources`.

Rationale: this is the only choice that covers every dataset-bearing source in the bundle without
either dropping the pediatric cohort or asserting a version/derivation relationship between two
projects that the sources say are distinct cohorts under separate ethics approvals. Version-,
DOI-, date- and access-level facts are held at resource level, where they are unambiguous; the
top-level record carries only facts that hold for both components. The choice is applied
identically in the full and the core record.

## Phase 3 — source and provenance audit

### Provenance

- Factual inputs read: the declared bundle, `data/preprocessed/source_manifest.yaml`, the full and
  core LinkML schemas, and the repository generation/validation instructions
  (`.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`).
- No prior generated D4D record was read, opened, grepped or consulted. Nothing under
  `data/d4d_concatenated/` was read except the same-run Phase 1 file when deriving core; no
  `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was touched. No
  evaluation report, reconciliation report or test fixture was used as evidence.
- No live web content was fetched.
- The output directory listing of `data/d4d_concatenated/claudecode_agent/` was inspected once, to
  confirm the run label `2026-07-28_claude-opus-5-generic_rep1` did not already exist. No record
  contents were read.

### Structure

Every emitted slot and nested object shape was derived at run time from the schemas via LinkML
`SchemaView` (induced slots per class, ranges, cardinality, inlining, required flags, enum
permissible values). No prior record or `d4d:docExample` supplied structure or values. Two
consequences worth recording, because a name-based guess would have been wrong:

- `Creator.principal_investigator`, `EthicalReview.contact_person`,
  `EthicalReview.reviewing_organization`, `LicenseAndUseTerms.contact_person`,
  `FundingMechanism.grantor` and `ExportControlRegulatoryRestrictions.governance_committee_contact`
  are **plain strings**, not nested objects, because the referenced classes carry identifiers and
  the slots are not inlined.
- `Creator.affiliations`, `Instance.sampling_strategies` and `Instance.missing_information` *are*
  inlined object lists.

### Source disagreements, represented rather than silently resolved

1. **Target dataset size.** Project documentation and study metadata state 10,000 voices /
   anticipated enrollment 10,000 by 2027; the audiomics white paper states a primary deliverable of
   30,000 human voices and the IRB protocol states a sample size of 30,000 participants (5,000 at
   USF, remainder via collaborating institutions). Both figures with their attributions were added
   to `purposes[flagship-dataset].response` during Phase 3.
2. **Grant number.** The bundle gives OT2OD032720 (core), 3OT2OD032720-01S1 (PhysioNet
   acknowledgements), 3OT2OD032720-01S3 (NIH RePORTER), "1OT2OD032720-01" (feasibility
   publication), "OT2 OD032720" (white paper), "Award #3Tf-OTOD03272001S2" (documentation footer),
   and a corrupted "3TF-OT2ActfOD032720Projectf01S1" (healthsheet). All variants are listed in
   `funders[0].description`; only the three cleanly attested numbers are emitted as `Grant`
   objects.
3. **Access policy wording.** PhysioNet labels adult v1.1 "Restricted Access / only registered
   users who sign the specified data use agreement" and adult v3.0.0, v3.1.0 and pediatric v1.1.0
   "Credentialed Access / only credentialed users who sign the DUA", while the documentation page
   says "Available under Registered Access ... Credentialed users must be approved and sign DUA".
   Both formulations are recorded, scoped by version, in the adult `version_access.version_details`
   and in `license_and_use_terms.license_terms`.
4. **Hosting platform.** The healthsheet states the dataset is hosted by the Health Data Nexus
   (T-CAIREM, University of Toronto); the current releases are on PhysioNet, maintained by the MIT
   Laboratory for Computational Physiology. Both are recorded as `maintainers` with explicit scope,
   and both appear as separate `distribution_formats` entries.
5. **Collection duration.** The healthsheet says data was collected over 12 months; the IRB
   protocol describes a 4-year prospective cohort study with four phases. Recorded as two separate
   `collection_timeframes` entries with their scopes named.
6. **Institution counts.** The white paper says 50 experts from 12 North American institutions; the
   documentation says lead investigators from 10 other universities; the IRB says 11 other
   participating institutions and lists 9 named institutions in its participating-institutions
   table; the healthsheet lists 12 collaborators. Each figure is carried with its attribution
   inside `creators[consortium].description`; no single number is asserted as the count.

### Scoping applied to historical or version-specific values

- `61,937` voice-derived recordings is scoped in the instance description to version 3.0, which is
  the version the documentation attributes it to.
- `12,523` recordings / `306` participants is scoped to v1.0.
- Per-feature record counts (28,640–32,522 adult; 23,532–23,533 pediatric) are scoped to v3.1.0 and
  pediatric v1.1.0 respectively, with the stated reason that some files could not generate certain
  features.
- The top-level `citation` reproduces the documentation's instruction to cite version 2.0.0 and is
  attributed as such. It is stale relative to the current v3.1.0 release; it is retained because
  it is what the current documentation states, not corrected to a version the sources do not
  instruct users to cite.
- The healthsheet's "current v.2.0.0 dataset contains only adult populations" is retained in
  `version_access.version_details` as an explicitly historical statement, since a pediatric cohort
  now exists.
- The Data Transfer and Use Agreement in the bundle is a blank template stamped "Approved for use
  through August 31, 2025"; a note recording this was added to `license_and_use_terms.license_terms`
  so its clauses are not read as an executed instrument.

### Corrections made in Phase 3

All four corrections were applied to the **full** record first, then propagated to core by
regeneration (see Phase 4). None were prompted by the core pass; all were prompted by re-reading
the bundle against the full record.

| # | Slot | Change |
|---|---|---|
| 1 | `purposes[flagship-dataset].response` | Added the 30,000-participant target from the white paper and IRB protocol alongside the 10,000 figure, with attributions. |
| 2 | `funders[0].description` | Added the full set of grant-number variants found in the bundle and stated which are emitted as `Grant` objects. |
| 3 | `sampling_strategies[adult].strategies` | Added the study-design and eligibility facts from the study metadata (observational, cohort, cross-sectional; sex all; min age 18, max age 120; healthy volunteers accepted; anticipated enrollment 10,000 by 2027). |
| 4 | `license_and_use_terms.license_terms` | Added the DTUA template/approval-stamp scoping note. |

### Facts deliberately omitted

- `download_url`, `compression`, `created_on`, `modified_by`, `was_derived_from`: no supporting
  statement in the bundle. The releases are behind registered/credentialed access and no direct
  download URL is published.
- `imputation_protocols`: the bundle contains no statement about imputation.
- `annotation_analyses`: a single labeler is used per instance, so no inter-annotator agreement
  analysis exists; the fact is stated once, in `labeling_strategies.inter_annotator_agreement`,
  rather than duplicated as an empty analysis object.
- `variables`: the phenotype JSON data dictionaries are described but the bundle does not enumerate
  individual variables with types, ranges or units, so no `VariableMetadata` was fabricated.
- `Instance.data_topic` and `Instance.data_substrate` (`uriorcurie`): no ontology terms are given in
  the bundle; inventing CURIEs would have failed the term validator for the right reason.
- `total_file_count` / `total_size_bytes`: the bundle gives record counts inside Parquet files, not
  file counts or byte sizes.
- Core-only `dialect` (`FormatDialect`): the phenotype and static-feature text files are
  tab-delimited, but the dataset as a whole is not a single tabular resource (`is_tabular: false`
  in both records). A dataset-level dialect would contradict that, so the delimiter information is
  carried in the distribution descriptions instead. This is the one core-only slot left unpopulated
  and it is left unpopulated deliberately.

### Internal consistency checks performed

Repeated identifiers, versions, dates, counts, licences and access rules were checked for internal
agreement within each file:

- DOIs: adult 3.1.0 `10.13026/8xbn-nq66`, adult 3.0.0 `10.13026/k81f-qr68`, adult 1.1
  `10.13026/249v-w155`, adult latest `10.13026/37yb-1t42`, adult v1.0 `10.57764/qb6h-em84`,
  pediatric 1.1.0 `10.13026/h995-bt35`, pediatric latest `10.13026/mf9s-5r03`. Each appears
  identically wherever it recurs (`resources[].doi`, `version_access` at resource and top level).
- Release dates agree between `distribution_dates`, both `version_access` blocks and
  `resources[].issued` (adult and pediatric current releases both 2026-05-01, matching top-level
  `last_updated_on`).
- Participant counts agree between `instances`, `resources[].description` and the subpopulation and
  bias statements (833 adult, 300 pediatric).
- Licence string "Bridge2AI Voice Registered Access License" is identical at top level and on both
  resources, matching all four PhysioNet pages in the bundle.
- `is_deidentified.identifiable_elements_present: false` agrees with the de-identification level
  statement and with `regulatory_restrictions.hipaa_compliant: compliant`;
  `confidentiality_level: restricted` agrees with the registered/credentialed access rules.
- `confidential_elements` carries two entries with opposite booleans. This is not a contradiction:
  one is scoped to the released dataset (healthsheet answer "No") and one to data transferred under
  the DTUA (Certificate of Confidentiality). Both scopes are named in the entry names and details.

## Phase 4 — strict full/core reconciliation

### Method

The shared slot set was derived at run time from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used. The core record was then **generated
programmatically from the Phase 3-audited full record**, copying every schema-identical shared slot
by value, so deep identity is guaranteed by construction rather than by transcription.

### Schema-derived slot inventory

- **Schema-identical shared slots: 76** (identical induced range and cardinality in both classes).
- **Projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).
- **Full-only slots: 17** — `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`, `splits`,
  `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`.
- **Core-only slots: 2** — `dialect`, `distributions`.

Nested class shapes were compared across the two schemas: all shared nested classes are
structurally identical except `Grantor.id`, which is `required` in the full schema and optional in
the core schema. That difference is inert here, because `FundingMechanism.grantor` is a plain
string in both.

### Presence and identity

- Populated top-level slots: **full 76**, **core 65**. The 11-slot difference is exactly the
  full-only slots that the full record populates (`citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `participant_compensation`, `participant_privacy`, `relationships`, `splits`, `subsets`,
  `third_party_sharing`). No core-only top-level slot is populated. Counting nested keys, full 850
  / core 753.
- Every schema-identical shared slot present in full is present in core and absent from core where
  absent from full.
- Every schema-identical shared value is deeply identical, including every nested mapping value and
  every list item in the same order. Narrative fields were **not** condensed, paraphrased,
  reordered or truncated in core.

### `resources` projection

Both resources match by `id` with equal coverage:

| `id` | full nested slots | core nested slots | dropped (full-only) | added (core-only) |
|---|---|---|---|---|
| `https://physionet.org/content/b2ai-voice/` | 19 | 17 | `file_collections`, `related_datasets`, `citation` | `distributions` |
| `https://physionet.org/content/b2ai-voice-pediatric/` | 17 | 16 | `file_collections`, `related_datasets` | `distributions` |

Every schema-identical nested slot inside each resource (`id`, `name`, `title`, `description`,
`version`, `doi`, `page`, `publisher`, `issued`, `status`, `language`, `license`, `conforms_to`,
`is_tabular`, `keywords`, `version_access`) is deeply identical between the two records.

### Related, non-identical content — semantic review

`file_collections` (full, `FileCollection`) → `distributions` (core, `CoreDistribution`):

| full FileCollection | core CoreDistribution | mapping |
|---|---|---|
| `id`, `name`, `description`, `path` | same slots | carried unchanged, byte-identical |
| `collection_type` (`FileCollectionTypeEnum`, multivalued) | — | **no core counterpart**; dropped. The information it encoded (`processed_data`, `metadata`) is restated in prose inside the descriptions that both records share, so nothing is lost that the core reader cannot recover. |
| — | `bytes`, `hash`, `md5`, `sha256`, `format`, `encoding`, `compression`, `media_type` | left unpopulated: the bundle publishes no checksums, byte counts or archive formats, and each collection mixes Parquet, TSV and JSON, so `format` (a single-valued `FormatEnum` that lacks a Parquet value) cannot be set without over-claiming. |

Six distributions total (three per resource: `features`, `phenotype`, `metadata`), matching the six
file collections one-for-one by `id` and `path`.

Cross-checks required by the playbook:

- `total_file_count` / `total_size_bytes` versus distribution-level values: both are absent from
  full and no distribution carries `bytes`, so there is no scope mismatch to reconcile.
- `dialect`, formats and `is_tabular`: `is_tabular: false` in both records at top level and on both
  resources; no `format` is asserted on any distribution and no `dialect` is asserted, so the three
  cannot conflict. See the deliberate-omission note above.
- Top-level identity/version/access facts versus resources, version history and distributions:
  checked and agreeing. The top-level record asserts no `version` or `doi` (the referent spans two
  independently versioned components); every version, DOI and release date lives on the resource it
  belongs to and is repeated identically in the top-level `version_access` summary.
- Historical versus current releases: v1.0/v1.1/v2.x/v3.0.0 and pediatric v1.0.0 are represented as
  version history, not as competing current values. Differing figures across versions (306 vs 833
  participants; 12,523 vs ~61,937 recordings) are version-scoped, not contradictions.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d_core.yaml

poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt
```

`--sync-core` was **not** run. Synchronization is optional and the independent check already passed
without it, because core was generated from the audited full record rather than written by hand.

### Results

- `linkml-validate` full (`Dataset`): **No issues found**
- `linkml-term-validator` full: **Validation passed**
- `linkml-validate` core (`CoreDataset`): **No issues found**
- `linkml-term-validator` core: **Validation passed**
- `d4d_pair_consistency`: **PASS — 76 schema-identical slots; projected slots = ['resources'];
  errors 0; warnings 0**

### Files changed in this run

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d.yaml` (created, then amended by the four Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_d4d_core.yaml` (created, regenerated after Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/VOICE_provenance.yaml`

### Divergence summary

After Phase 3, no schema-identical shared slot diverged between the full and core records — every
one is deeply identical and identically present. The only differences between the two files are
those the schemas require: 11 populated full-only top-level slots that `CoreDataset` does not
define, the `resources` range projection, and the `file_collections` → `distributions`
representation change documented above.
