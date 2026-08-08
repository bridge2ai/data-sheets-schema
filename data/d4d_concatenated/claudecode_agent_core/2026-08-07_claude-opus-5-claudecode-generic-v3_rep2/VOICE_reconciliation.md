# VOICE full/core reconciliation

- **Run label:** `2026-08-07_claude-opus-5-claudecode-generic-v3_rep2`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Runtime / provider / model / reasoning effort:** Claude Code / Anthropic / `claude-opus-5` / `high`
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d_core.yaml`

## Pinned referent

`Dataset` admits one referent. The bundle describes two things at once: an ongoing
data-generation programme ("Bridge2AI: Voice as a Biomarker of Health", NIH
OT2OD032720) and the versioned dataset that programme publishes. **The referent is
the published Bridge2AI-Voice adult dataset**, identified by its version-independent
PhysioNet DOI `10.13026/37yb-1t42`, whose current release is v3.1.0 (published
2026-05-01, DOI `10.13026/8xbn-nq66`, 833 participants across five North American
sites).

Consequences held consistently across both records:

- Top-level identity, version, licence, page, publisher and `issued` describe v3.1.0.
- The six releases (v1.0 on Health Data Nexus, and v1.1, v2.0.0, v2.0.1, v3.0.0 and
  v3.1.0 on PhysioNet) are enumerated as `resources`, each with its own dates, DOIs
  where published, and release notes. Historical figures stay attached to the release
  they describe rather than being merged into the current one.
- Programme aims and infrastructure (federated learning, STRIDES hosting, the phased
  four-year acquisition plan, module leads) are recorded only where they document how
  the published dataset was produced.
- Participant *targets* stated for the programme — 10,000 voices in the current
  project documentation and the study metadata's anticipated 2027 enrollment, 30,000
  in the NIH RePORTER abstract, the JAMA Otolaryngology viewpoint and the IRB
  protocol, and up to 5,000 per disease category in the IRB protocol's sample-size
  section — are recorded as programme goals in `source_caveats` and are **not**
  asserted as properties of any release. The only participant count asserted for the
  dataset is 833.

## Relationship to the pediatric dataset

The Bridge2AI-Voice Pediatric Dataset is **not** represented as a nested object,
a `resource`, a `subset`, or a version of this dataset. It appears once, in the
full record's schema-provided relationship slot:

```yaml
related_datasets:
  - id: b2aivoice:related-pediatric
    name: Bridge2AI-Voice Pediatric Dataset
    target_dataset: https://doi.org/10.13026/h995-bt35
    relationship_type: references
```

`references` was chosen over `has_part`, `is_supplemented_by` or `is_version_of`
because the only relation the bundle actually evidences is a pointer: the adult
PhysioNet landing page carries the note "Note that the Bridge2AI-Voice Pediatric
Dataset is also available on PhysioNet", and the project documentation lists the two
datasets side by side with separate PhysioNet registration links. The two are
distinct PhysioNet projects with separate cohorts, protocols, recruitment sites and
DOIs; nothing in the bundle asserts a part-whole or version relation, so none is
claimed. `related_datasets` is a full-only slot (`CoreDataset` does not carry it),
so the core record makes no statement about the pediatric dataset at all.

Pediatric-specific content that the bundle mixes into shared documents was excluded
from both records: the pediatric acoustic task rows of Table 2, the pediatric
questionnaires in Table 3, the ReproSchema-UI collection path, the SickKids
recruitment site, the pediatric Synapse identifier `syn73617068`, and the pediatric
participant count. The adult Synapse identifier `syn72370534` is the one recorded.
`data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt` was not read.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior D4D record was read, opened, grepped or consulted, from any arm, label or
date. Nothing under `data/d4d_concatenated/` was read except this run's own two
outputs; no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was read. The complete factual read set was:

1. `data/preprocessed/concatenated/VOICE_preprocessed.txt` (the declared bundle)
2. `data/preprocessed/source_manifest.yaml`
3. `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
4. `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
5. `src/data_sheets_schema/d4d_pair_consistency.py` (to derive the Phase 4 contract)
6. the three playbook files named in the task

Structure was derived at runtime from the schemas with `SchemaView` — every emitted
slot name, range, cardinality, inlining behaviour and enum value came from the
induced-slot listing for `Dataset` and `CoreDataset`, not from any example record.
No `d4d:docExample` value was copied.

### Source disagreements found, and how they were represented

Each was represented rather than silently resolved:

| Disagreement | Representation |
|---|---|
| Hosting platform: the healthsheet names Health Data Nexus (T-CAIREM, University of Toronto); PhysioNet pages name the MIT Laboratory for Computational Physiology | Both recorded as separate `maintainers` entries, with a `source_caveats` noting the healthsheet answer appears to describe the v1.0 distribution |
| Access tier: project documentation says "Registered Access" for the featurized adult dataset while stating credentialed approval and DUA in the same paragraph; PhysioNet's policy is registered for v1.1 and credentialed for v3.0.0/v3.1.0 | Both recorded in `distribution_formats` description plus a `source_caveats` |
| High volume expert clinic threshold: >50 patients/month (study metadata) vs >1,000 patients/year (IRB protocol) | Both reported in `sampling_strategies.strategies` with a `source_caveats` |
| Confidentiality: healthsheet answers "No"; the DTUA calls the transferred data Personally Identifiable Information under a Certificate of Confidentiality | `confidential_elements` records the healthsheet answer with a `source_caveats` explaining the DTUA governs the controlled-access raw-audio transfer, not the de-identified feature release |
| Institution list: the study metadata names twelve collaborators; IRB Annex C adds Massachusetts Eye and Ear and Emory University | Both lists merged into `creators[0].affiliations` with a `source_caveats` stating which list each came from |
| Grant number renderings: `3TF-OT2ActfOD032720Projectf01S1` (healthsheet) and `Award #3Tf-OTOD03272001S2` (site footer) | Neither recorded as a grant identifier; `funders.source_caveats` states both appear to be corrupted renderings of an OT2OD032720 supplement number. The three clean numbers `OT2OD032720`, `3OT2OD032720-01S1` and `3OT2OD032720-01S3` are recorded as `Grant` objects |
| Study metadata is written against v2.0.0 ("The current v.2.0.0 dataset contains only adult populations"; a v2.0.0 citation string) while PhysioNet publishes v3.1.0 | `citation` carries the PhysioNet v3.1.0 citation; the version-scoped study-metadata statements were not carried forward as current facts |

### Stale, unsupported or mis-scoped assertions checked for

- **IRB 004890** appears in the bundle as the approval for a *separate* USF feasibility
  study of the collection app (47 participants, no audio collected). It is **not**
  recorded as an approval for this dataset; `ethical_reviews[1].source_caveats` says so
  explicitly. The dataset's approvals are the USF Single IRB and the separate Canadian
  REBs.
- **The 47-participant feasibility study** contributed no composition, count or
  collection fact to this record. Its only role was corroborating the app's task list
  and the consortium's institutional composition.
- **Feature counts** were taken from the v3.1.0 page (spectrogram/mel/MFCC n=29,278;
  pitch n=32,522; sparc_ema n=28,640; loudness n=31,855; periodicity and sparc_pitch
  n=31,872; ppgs n=29,289), not the differing v3.0.0 figures, and are labelled as
  v3.1.0 figures in `file_collections`.
- **~61,937 voice-derived recordings** is attributed to version 3.0 as the project
  documentation states, not to v3.1.0.
- **Placeholder emails.** The captured documentation redacts several contact addresses
  to the literal string `[email protected]`. No email was reconstructed from a
  placeholder. The only contact addresses recorded are the two that appear in full:
  `DACO@b2ai-voice.org` and the PI correspondence address, and
  `maintainers[3].source_caveats` records that the platform-team and curator addresses
  were unavailable.
- **Absent evidence, slots omitted:** `total_file_count`, `total_size_bytes`,
  `is_tabular`, `compression`, `dialect`, `variables`, `subsets`, `parent_datasets`,
  `imputation_protocols`, per-cohort participant counts, demographic distributions of
  the released cohort, and start/end dates for the twelve-month collection period. In
  each case the bundle states no value; the collection period is recorded as a duration
  only, with a `source_caveats` saying no endpoints are given.

### Internal consistency checks

Repeated values were verified to agree within each file and between them: the
version-independent DOI `10.13026/37yb-1t42` in `doi` and
`version_access.latest_version_doi`; version `3.1.0` in `version`, `resources`,
`page`, `citation` and `version_access.versions_available`; `issued` 2026-05-01
matching the v3.1.0 resource and `distribution_dates`; the licence string in the
top-level `license`, the v1.1/v3.0.0/v3.1.0 resources and `license_and_use_terms`;
833 participants in `instances.counts`, `instances.description` and the top-level
description; and the six release dates identical in `resources`,
`distribution_dates.release_dates` and `version_access.versions_available`.

### Shape audit

- Every enum value used is declared by the schema: `collection_type`
  (`processed_data`, `metadata`), `bias_type`, `limitation_type`,
  `CreatorOrMaintainerEnum` roles, `data_use_permission: general_research_use`,
  `hipaa_compliant: compliant`, `confidentiality_level: restricted`,
  `relationship_type: references`.
- `principal_investigator` has range `Person`, which declares `id` as an identifier and
  is not inlined, so the schema requires a scalar reference rather than an inline
  object. It carries a `mailto:` URI built from the correspondence address given in the
  IRB protocol and the feasibility publication; `creators[0].source_caveats` records
  that no ORCID or other persistent person identifier appears in the bundle.
- No prose was placed in a list-valued slot and no list content was flattened into
  prose. `irb_approval`, `regulatory_compliance`, `restrictions`, `warnings`,
  `examples`, `tools`, `tool_accuracy`, `versions_available`, `release_dates`,
  `keywords`, `annotator_demographics` and `affiliations` are all lists.
- No commentary is embedded inside any `name`, `id` or affiliation value.
- Slot-filling order was enforced: structured slots first (`grants` carry grant numbers
  rather than leaving them in prose; `used_software` carries b2aiprep, SenseLab and the
  REDCap repository rather than naming them only in narrative), then the class's own
  content slot (`response`, `*_details`, `strategies`) as the home for narrative.
- Evidence commentary is confined to `source_caveats` (nine instances). `notes` is used
  once, at the root, and was rewritten during this audit — see corrections below.

### Corrections applied in Phase 3

Two, both to the full record first, then propagated to core by regeneration:

1. **Sibling restatement in `notes`.** The original root `notes` inventoried supporting
   materials including b2aiprep and the REDCap repository, both of which are already
   `used_software` objects on `preprocessing_strategies` and `collection_mechanisms`.
   Restating a sibling's value in `notes` is a slot-filling violation. `notes` was
   rewritten to carry only the two artifacts with no other home: the FHIR profiles and
   the documentation/dashboard source with its Zenodo archive.
2. **Unrecorded source disagreement.** The registered-versus-credentialed access
   discrepancy was represented in the distribution description but not flagged as a
   source conflict. A `source_caveats` was added to
   `distribution_formats[b2aivoice:distribution-physionet]`.

A third change was made before the first validation rather than as an audit finding:
`conforms_to_schema` had been set to the REDCap repository URL, which over-claims —
`conforms_to` already records BIDS v1.9.0, and the REDCap data dictionary is a
phenotype instrument definition rather than a schema the whole dataset conforms to.
The slot was removed.

**No Phase 2 discovery required back-porting.** Core is a strict schema-driven subset
of full plus one projection, so Phase 2 surfaced no fact the full record lacked and no
value the sources contradicted.

## Phase 4 — strict full/core reconciliation

### Shared slots, derived at runtime

Derived with `SchemaView` from `Dataset` and `CoreDataset` by
`data_sheets_schema.d4d_pair_consistency`; no hand-written field list was used.

- **Schema-identical slots: 78.** All 78 have identical presence and deeply identical
  parsed YAML content in the two records, including every nested mapping value and list
  item in the same order. Narrative fields were not condensed, paraphrased, reordered or
  omitted in core.
- **Projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).

Core was produced by loading the validated Phase 1 YAML, retaining exactly the keys
that `CoreDataset` induces, and copying their values verbatim. Deep identity is a
property of how the file was built, and is then verified independently by the
validator. `--sync-core` was not needed and was not run.

### Full-only slots omitted from core (12)

`CoreDataset` does not declare these, so their absence from core is required, not a
divergence: `citation`, `file_collections`, `relationships`, `splits`,
`direct_collection`, `collection_notifications`, `collection_consents`,
`consent_revocations`, `participant_privacy`, `participant_compensation`,
`third_party_sharing`, `related_datasets`.

Full slot count 81; core slot count 70 (81 − 12 full-only + 1 core-only
`distributions`).

### `resources` projection

Six release resources, matched by `id`, with equal coverage in both directions:

| `id` | version |
|---|---|
| `https://doi.org/10.57764/qb6h-em84` | 1.0 |
| `https://doi.org/10.13026/249v-w155` | 1.1 |
| `https://physionet.org/content/b2ai-voice/2.0.0/` | 2.0.0 |
| `https://physionet.org/content/b2ai-voice/2.0.1/` | 2.0.1 |
| `https://doi.org/10.13026/k81f-qr68` | 3.0.0 |
| `https://doi.org/10.13026/8xbn-nq66` | 3.1.0 |

Every slot used on a resource — `id`, `name`, `title`, `version`, `doi`, `issued`,
`publisher`, `page`, `license`, `status`, `description`, `source_caveats` — is one of
the 78 schema-identical slots, and every one is deeply identical between the full and
core projections. No full-only nested slot was used on any resource, so nothing was
dropped in the projection. No resource carries nested `resources`.

### Related, non-identical content: semantic review

The validator emitted one warning:

```
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=3, unmatched core distributions=[]
```

Reviewed as required — the warning marks content for review, it does not perform it.

Full `file_collections` (range `FileCollection`) maps to core `distributions` (range
`CoreDistribution`). Three collections, three distributions, matched one-to-one on
`id`, no unmatched items on either side:

| id | full `FileCollection` | core `CoreDistribution` |
|---|---|---|
| `…/3.1.0/features/` | `name`, `path`, `collection_type: processed_data`, `description`, `source_caveats` | `name`, `path`, `description`, `source_caveats` |
| `…/3.1.0/metadata/` | `name`, `path`, `collection_type: metadata`, `description` | `name`, `path`, `description` |
| `…/3.1.0/phenotype/` | `name`, `path`, `collection_type: processed_data`, `description` | `name`, `path`, `description` |

Findings:

- `name`, `path`, `description` and `source_caveats` are byte-identical between each
  pair; no name, description, path or release-scope conflict exists.
- `collection_type` is declared by `FileCollection` and not by `CoreDistribution`, so
  it is dropped in the projection. This is a schema difference, not a contradiction.
- `format`, `compression`, `media_type`, `encoding`, `bytes`, `hash`, `md5` and
  `sha256` are unset on every core distribution, and `file_count` and `total_bytes` are
  unset on every full collection, because the bundle publishes none of them. Nothing to
  conflict.
- Formats are deliberately unset rather than guessed: each of the three directories is
  heterogeneous (Parquet binaries with TSV tables and JSON dictionaries in `features`;
  paired TSV and JSON in `phenotype`), and `FormatEnum` has no Parquet member, so any
  single value would misstate the contents. The composition is described in prose
  instead.
- `total_file_count` and `total_size_bytes` are absent from full, so there is no
  aggregate to compare against distribution-level values.
- `dialect`, `is_tabular` and `compression` are absent from both records; no
  disagreement is possible.
- Top-level identity, version and access facts (`version` 3.1.0, `doi`, `issued`,
  `page`, `license`, `publisher`) agree with the `resources` entry for v3.1.0, with
  `version_access.versions_available`, with `distribution_dates.release_dates` and with
  the repeated statements in `distribution_formats` and `license_and_use_terms`, in
  both files.
- Historical versus current releases are distinguished rather than treated as
  contradictions: v1.0's 12,523 recordings / 306 participants and v2.0's +136 and
  v3.0.0's +391 participants are attached to those releases, while 833 is the count for
  v3.0.0 and v3.1.0.

**Zero unresolved contradictions within or between the two records.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/VOICE_d4d_core.yaml

poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 --project VOICE
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2
```

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | PASS — no issues found |
| Full ontology term validation | PASS |
| Core schema validation (`CoreDataset`) | PASS — no issues found |
| Core ontology term validation | PASS |
| Full/core pair consistency | PASS — 78 schema-identical slots, 1 projected slot (`resources`), 0 errors |
| Semantic review of related content | Completed — 3/3 `file_collections` ↔ `distributions` matched, 0 conflicts |
| Full slot count | 81 (informational) |
| Core slot count | 70 (informational) |
| Prior-D4D reuse | None |
