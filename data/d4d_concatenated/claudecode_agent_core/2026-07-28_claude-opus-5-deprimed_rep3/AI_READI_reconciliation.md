# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep3

**Run label:** `2026-07-28_claude-opus-5-deprimed_rep3`
**Arm:** BASELINE (input documents only)
**Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`
**Mode:** four-phase project agent, de-primed. Temperature 0.0.

| Artifact | Path |
| --- | --- |
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_reconciliation.md` |

Declared factual inputs: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 source
documents) and, for curation guidance and provenance only,
`data/preprocessed/source_manifest.yaml`. Structural authority:
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`) and
`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`).

---

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped, or cited. Nothing under
`data/d4d_concatenated/` or `data/d4d_individual/` was accessed except the exact same-run pair
written by this run. The complete read history for factual content is: the concatenated AI_READI
bundle, the source manifest, the two LinkML schemas, and the repository generation/validation
instructions (`.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
`.claude/commands/d4d-agent.md`). No live web content was fetched. No evaluation report,
reconciliation report, test fixture, or `d4d:docExample` value supplied any dataset fact.

Structure was derived at runtime from the two schemas with LinkML `SchemaView` rather than from
any prior record. One schema-shape correction was needed during Phase 1: `Instance.sampling_strategies`
has a class range whose target (`SamplingStrategy`) declares no identifier slot, so LinkML requires
it inlined rather than referenced. The intended cross-reference was removed and the sampling
strategy is carried once, at the dataset level.

### Source-conflict resolutions

The bundle contains documentation and metadata for more than one release of the AI-READI dataset,
and they disagree on several figures. Following the manifest's curation guidance (prefer the
current upstream capture where it supersedes a sheet-selected entry; retain a historical value
only with its scope made explicit), the following were resolved:

| Item | Conflict | Resolution |
| --- | --- | --- |
| Dataset version in scope | `dataset_documentation` / `fairhub_dataset` describe v2.0.0 (2.01 TB, 165,051 files); `dataset_documentation_v3`, `fairhub_dataset_v3`, `fairhub_dataset_v3_api` describe v3.0.0 | Record describes **v3.0.0** (DOI 10.60775/fairhub.3, 3.82 TB, 356,343 files, 2280 participants). v2.0.0 figures retained only in `version_access` with explicit version scope, where the FAIRhub statement that v2.0.0 "is no longer accessible" is also recorded. |
| Licence | Bundle carries the full text of AI-READI Data License v1.0 (Zenodo 10.5281/zenodo.10642459); the v3.0.0 FAIRhub record cites "AI-READI custom license v2.0" (Zenodo 10.5281/zenodo.17555036) | `license` and `license_and_use_terms` name **v2.0** as the operative licence for this release; the v1.0 clause-by-clause terms are recorded with an explicit statement that they are the v1.0 text applying to earlier releases. |
| Lead / managing organization | FAIRhub v3.0.0 structured metadata names "Washington University in St. Louis" (ROR `01yc7t268`) as managing organization, lead sponsor, and PI/central-contact affiliation. NIH RePORTER (awardee `UNIVERSITY OF WASHINGTON`), the data licence (Licensor "UNIVERSITY OF WASHINGTON"), the IRB approval (UW IRB STUDY00016228), and both publications place the lead at the University of Washington, which the same FAIRhub record lists as a Seattle study location (ROR `00cvxb145`) | Record uses **University of Washington**. The discrepancy is stated verbatim in `maintainers[0].maintainer_details` rather than being silently dropped. |
| Target enrolment | IRB protocol narrative states 4600 twice; its own subject-group table gives 4 x 1000 = 4000. Protocol publication, Nature comment, NIH RePORTER, README and FAIRhub `enrollmentInfo` all give 4000 | Record uses **4000**, with the 4600 figure and its source noted in `sampling_strategies[0].strategies`. |
| Project name expansion | "Artificial Intelligence Ready and **Equitable** Atlas…" (BMJ, Nature) vs "…and **Exploratory** Atlas…" (RePORTER, healthsheet, README, FAIRhub `officialTitle`) | Both renderings recorded in `description`. |
| Enrolment start | Protocol publication: 18 July 2023. FAIRhub `startDateStruct`: 2023-07-19 (Actual), and the collected-date range begins 2023-07-19 | `collection_timeframes[0].start_date` = **2023-07-19** (the value tied to this release's collection window); the 18 July 2023 protocol figure is retained in `timeframe_details` with attribution. |
| Blood volume | Protocol publication: 53 mL. IRB protocol: approximately 50–60 mL | Both recorded together in `collection_mechanisms`. |
| EHR screening window | Protocol publication: encounters between 2020 and 2025. Healthsheet: encounters "within the past 2 years" | Both recorded together in `sampling_strategies[0].source_data`. |
| Longitudinal follow-up fraction | RePORTER abstract and README: longitudinal data from 10% of the cohort. IRB: intend to invite 10%. Healthsheet: ~4% expected to undergo follow-up in Year 4 | Both recorded, attributed, in `known_limitations` (`limitation_cross_sectional_scope`). Not treated as a contradiction: one figure is invitations, the other expected completions. |
| Award number rendering | Healthsheet motivation Q5 renders the award as `OT2ODO32644` (letter O for zero) | Record uses `OT2OD032644`, matching NIH RePORTER, the FAIRhub funding reference and the README. |

### Internal-consistency checks against the sources

All arithmetic below was verified against values stated in the bundle; none of it was imported
from any other record.

- **File counts.** The nine datatype directories sum to 4515 + 7 + 2232 + 7969 + 56,478 + 173,721
  + 93,921 + 15,245 + 2246 = **356,334**. The reported dataset total is **356,343**. The residual
  of 9 equals the nine root-level metadata files enumerated in `datasetStructureDescription`
  (`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`,
  `healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`,
  `study_description.json`). Recorded as `file_collection_root_metadata` (file_count 9).
- **Byte counts.** The nine datatype directory sizes sum to **3,815,969,360,064**; the reported
  dataset size is **3,815,969,779,678** (FAIRhub `data.size`, consistent with the "3.82 TB" string
  on the landing page). The 419,614-byte residual is attributed, with that framing made explicit
  in both records, to the root-level metadata files, whose size the sources do not report.
- **Participant counts.** 2280 (v3.0.0) is stated identically in the FAIRhub abstract, the README,
  the healthsheet composition section and the split table. The version history 204 → 1067 → 2280
  is consistent with the README changelog increments 204 / +863 / +1213 (204 + 863 = 1067;
  1067 + 1213 = 2280).
- **Split totals.** 1576 + 352 + 352 = 2280. Race/ethnicity totals 380 + 545 + 519 + 836 = 2280.
  Sex totals 951 + 1329 = 2280. Diabetes-status totals 776 + 560 + 686 + 258 = 2280. All four
  partitions reconcile.
- **Version identifiers and dates.** `id`, `doi`, `version`, `version_access.latest_version_doi`,
  `versions_available`, `distribution_dates` and `issued` all agree on v3.0.0 / 10.60775/fairhub.3 /
  2025-11-17; v2.0.0 / 10.60775/fairhub.2 / 2024-11-08; v1.0.0 / 10.60775/fairhub.1 / 2024-05-03.
  The Unix timestamps in the FAIRhub `versions` array decode to the same three dates.
- **People and organizations.** Aaron Lee is named consistently as principal investigator across
  NIH RePORTER and the FAIRhub responsible-party, central-contact and overall-official records;
  ORCID `0000-0002-7452-1648` is used once, as `creators[0].principal_investigator` and as
  `ethical_reviews[0].contact_person`. Every ROR identifier used appears verbatim in the bundle.
- **Access rules.** The access statement (verified-ID login, T2DM-only research self-attestation,
  licence acceptance) appears identically in the FAIRhub `accessDetails` and the README, and is
  recorded consistently in `license_and_use_terms`, `distribution_formats` and
  `participant_privacy`. The public/controlled tier split and its element list (5-digit ZIP, sex,
  race, ethnicity, genetic sequencing data, past health records, medications, traffic and accident
  reports) are recorded identically in `sensitive_elements`, `subpopulations`,
  `participant_privacy`, `is_deidentified` and `third_party_sharing`.

### Corrections applied during Phase 3

Two defects were found in the Phase 1 record and corrected in the full record first, then carried
into core by regeneration:

1. **Unsupported inference removed.** `funders[0].grants[1]` (P30DK035816) asserted that the award
   "corresponds to the University of Washington Nutrition and Obesity Research Center". The bundle
   names both the award and the NORC laboratory but never links them; this was model prior
   knowledge, not evidence. Replaced with an explicit statement that the sources do not say what
   the award supports.
2. **Unrecorded source conflict added.** The 4600 vs 4000 target-enrolment disagreement inside the
   IRB protocol was resolved in favour of 4000 but not disclosed. The resolution and its basis are
   now stated in `sampling_strategies[0].strategies`. The EHR screening-window difference was
   likewise made explicit.

No fact discovered during Phase 2 required back-porting: the core schema exposes no factual slot
that the full schema lacks, so Phase 2 surfaced no content absent from the full record. Both files
were re-validated after every correction.

### Deliberate omissions

Slots left absent because the bundle does not support them: `compression`, `created_by`,
`created_on`, `modified_by`, `last_updated_on`, `conforms_to_class`, `resources`, `errata`
(the healthsheet erratum question is answered with an empty string), `imputation_protocols`,
`annotation_analyses`, `machine_annotation_tools`, and, in core, `dialect`. `Instance.data_topic`
and `Instance.data_substrate` were left absent because their `uriorcurie` range calls for ontology
terms that the bundle does not supply; guessing them would have been invention.

`parent_datasets` is present as an empty list in the full record, reflecting that no parent dataset
is asserted.

---

## Phase 4 — strict full/core reconciliation

### Method

The core record was derived from the Phase 3-audited full record by a schema-driven projection:
`CoreDataset`'s induced slot inventory was read at runtime with LinkML `SchemaView`, and every
shared slot was copied from the parsed full YAML without paraphrase, condensation or reordering.
No hand-written field list was used, and no older core record was consulted for field selection,
wording, identifiers or values. Because the projection is generated rather than transcribed,
`--sync-core` was not required; the pair validator was run only in its independent checking mode.

### Deterministic result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml

PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=10, unmatched core distributions=[]
```

**76 schema-derived identity slots**, zero errors. Every schema-identical slot is present in both
records or absent from both, with deeply identical parsed YAML content including nested mapping
values and list order. Narrative fields are byte-identical; nothing was shortened for core.

`resources` is the one projected slot (`Dataset` in full, `CoreDataset` in core). It is absent from
both records, so the projection is vacuously equal and there is no coverage gap.

### Root-slot accounting

- Full: **83** root slots populated.
- Core: **67** root slots populated (66 shared + `distributions`).
- Full-only, by schema (16, all absent from `CoreDataset`): `citation`, `total_file_count`,
  `total_size_bytes`, `subsets`, `relationships`, `splits`, `direct_collection`,
  `collection_notifications`, `collection_consents`, `consent_revocations`, `participant_privacy`,
  `participant_compensation`, `third_party_sharing`, `variables`, `parent_datasets`,
  `related_datasets`.
- Core-only: `distributions` (projected from full `file_collections`). `dialect` is core-only in
  the schema but is unpopulated, because the sources state no delimiter, header or quoting
  convention for the dataset's tabular files.

83 − 16 (full-only) = 67 shared populated slots in full; 66 of those are carried in core plus
`distributions`, giving 67. The 76 identity slots reported by the validator is the schema-derived
count of shared slots eligible for identity checking, which exceeds the 66 actually populated
because identity also requires jointly-absent slots to stay jointly absent.

### Semantic review of related, non-identical content

`file_collections` (full, `FileCollection`) ↔ `distributions` (core, `CoreDistribution`). Ten
collections, ten distributions, matched 1:1 by name and path with no unmatched entries on either
side.

| Property | Full (`FileCollection`) | Core (`CoreDistribution`) | Verdict |
| --- | --- | --- | --- |
| Name | `name` | `name` | Identical for all 10. |
| Path | `path` | `path` | Identical for the 9 datatype directories; neither record sets a path for the root-metadata entry, which has no directory. |
| Byte count | `total_bytes` | `bytes` | Identical integers for the 9 datatype directories. Neither reports a size for the root-metadata entry, because the sources do not state one. |
| File count | `file_count` | no such slot | Carried verbatim into the core distribution `description` ("File count: N."). Values agree with the full record for all 10 entries. |
| Standard conformance | `conforms_to` | no such slot | Carried verbatim into the core distribution `description` ("Conforms to: …"). No conflict. |
| Title | `title` | no such slot | Prefixed onto the core `description`. No content lost, none added. |
| Format / media type / encoding | not asserted | not asserted | Neither record commits to a `FormatEnum` or `MediaTypeEnum` value. This is deliberate: the enums do not include DICOM or WFDB, which dominate the release, and most directories are format-mixed. Distributed media types are instead stated once, identically in both records, in the shared `distribution_formats` slot (`application/dicom`, `text/markdown`, `text/csv`, `application/json`). No contradiction. |
| Compression | not asserted at any level | not asserted at any level | Consistent; the sources describe no archive-level compression. |
| Checksums | no such slot | `hash` / `md5` / `sha256` not asserted | The sources publish no checksums. Correctly absent rather than fabricated. |
| Access URLs | shared `distribution_formats` | shared `distribution_formats` | Schema-identical slot, deeply identical. |
| Release scope | v3.0.0 throughout | v3.0.0 throughout | Both records scope every distribution to the v3.0.0 release. |

**Scope arithmetic across the two representations.** Full `total_file_count` (356,343) and
`total_size_bytes` (3,815,969,779,678) have no `CoreDataset` counterpart. They were checked against
the distribution-level values, which cover the same scope: distribution bytes sum to
3,815,969,360,064 and distribution file counts sum to 356,334, with the residuals (419,614 bytes,
9 files) attributed to the root-level metadata files in both records using identical wording. The
two representations therefore agree; they do not contradict.

**`is_tabular`.** `false` in both records, consistent with the sources' statement that the dataset
comprises tabular, imaging and physiological signal/waveform data. Consistent with the absence of
`dialect` in core.

**Top-level identity, version and access facts** were re-checked against the distribution and
version-history content in both records: `id`/`doi`/`version`/`issued` agree with
`version_access.latest_version_doi` and `versions_available`, with `distribution_dates`, and with
the access statements in `license_and_use_terms` and `distribution_formats`. Historical releases
(v1.0.0, v2.0.0) are labelled with their versions everywhere they appear and are never presented as
current, so their differing size, file-count and participant-count values are version scope, not
contradiction.

### Full-only content not represented in core

Because `CoreDataset` omits the slots listed above, the following content exists only in the full
record and is not recoverable from core: the three recommended-split `subsets`, the `splits`
narrative and its counts, the `variables` inventory (9 entries), `participant_privacy`,
`participant_compensation`, `direct_collection`, `collection_notifications`, `collection_consents`,
`consent_revocations`, `relationships`, `third_party_sharing`, `citation`, `related_datasets` and
the dataset-level file/byte totals. This is a schema property of the core exchange layer, not a
reconciliation defect.

---

## Validation record

All commands run from the repository root.

```bash
# Phase 1 / Phase 3 / Phase 4 — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 / Phase 4 — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — schema-derived pair consistency
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml

# Provenance
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

| Check | Result |
| --- | --- |
| Full — LinkML schema validation (`Dataset`) | No issues found |
| Full — ontology term validation | Validation passed |
| Core — LinkML schema validation (`CoreDataset`) | No issues found |
| Core — ontology term validation | Validation passed |
| Pair consistency (schema-derived) | PASS, 76 identity slots, 0 errors, 1 semantic-review warning (reviewed above) |
| Provenance record `record_mode` | `live` |

## Files changed by this run

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml` (created; edited twice in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml` (created; regenerated after Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_provenance.yaml` (live provenance record)

## Outcome

Reconciliation passed. Two Phase 3 corrections were applied to the full record — one unsupported
inference removed, one source conflict disclosed — and carried into core. After those corrections,
no divergence remains between the pair: all 76 schema-identical slots are deeply identical, the one
projected slot is jointly absent, and the single related-content mapping
(`file_collections` ↔ `distributions`) was reviewed entry by entry with zero unresolved
contradictions within or between the two records.
