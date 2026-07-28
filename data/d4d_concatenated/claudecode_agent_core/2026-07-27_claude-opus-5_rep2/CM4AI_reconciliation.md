# CM4AI full/core reconciliation report

- **Run label:** `2026-07-27_claude-opus-5_rep2`
- **Arm:** BASELINE (document corpus only)
- **Agent runtime:** Claude Code
- **Provider:** Anthropic
- **Model:** claude-opus-5[1m]
- **Mode:** four-phase project agent
- **Temperature:** 0.0
- **Generated:** 2026-07-27

## Files

| Role | Path | Lines |
|------|------|-------|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml` | 2473 |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml` | 1615 |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CM4AI_reconciliation.md` | this file |

Line counts are informational metadata, not a quality gate.

## Phase 3 - Source and provenance audit

### Provenance

Factual inputs read during this run were limited to the phase allowlist:

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (10 documents, 7873 lines)
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `src/data_sheets_schema/schema/D4D_Core.yaml`
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`

No prior full or core D4D record, evaluation, reconciliation report, RO-Crate artifact, or live
web content was read, searched, globbed, or cited. The only generated YAML read in Phase 2 was
the exact same-run full record at the `2026-07-27_claude-opus-5_rep2` path. Structure was derived
at runtime from the LinkML schemas with `SchemaView` (induced slots, ranges, cardinality,
inlining, enums); no prior record was used as a template and no `d4d:docExample` value was copied.

### Release scoping

The corpus contains four Dataverse release pages. They are kept distinct rather than merged:

| Release | DOI | Dataverse version | Publication date | Files | Status in record |
|---------|-----|-------------------|------------------|-------|------------------|
| June 2026 Data Release (Beta) | 10.18130/V3/HIGT4C | 2.0 (citation V2) | 2026-06-17 | 10 | current |
| October 2025 Data Release (Beta) | 10.18130/V3/K7TGEM | 2.1 (citation V2) | 2025-10-31 | 8 | historical, superseded |
| June 2025 Data Release (Beta) | 10.18130/V3/F3TD5R | 2.1 (citation V2) | 2025-07-01 | 21 | historical |
| March 2025 Data Release (Beta) | 10.18130/V3/B35XWX | 1.4 (citation V1) | 2025-03-03 | 6 | historical |

Top-level identity, `file_collections`, and core `distributions` describe HIGT4C only. The three
historical releases appear as `resources` entries with explicit `status` values and release-scoped
descriptions, and as `related_datasets` with `relationship_type: replaces`. A fifth, May 2024
release is listed in the cm4ai.org archive and is recorded in `version_access` and
`distribution_dates` without asserting a file inventory.

### Source conflicts identified and resolved

1. **Release date of the current release.** `cm4ai.org/data-releases/` labels the current release
   "June 2026 Data Release (Beta)" with DOI `doi.org/10.18130/V3/HIGT4C` but displays
   "Released on: June 17, 2025". The Dataverse record for the same DOI gives Publication Date
   `2026-06-17` and a 2026 citation year. **Resolved in favour of the Dataverse metadata**, as
   directed by the source manifest curation note. The website's date is recorded explicitly as a
   conflict in `version_access.version_details` and in `distribution_dates.release_dates`.
2. **Project end date.** NIH RePORTER records project end `2026-08-31`; the Dataverse maintenance
   plan states the dataset will be augmented "through the end of the project in November 2026".
   Both values are recorded with attribution in `collection_timeframes` and `updates`; neither is
   suppressed, because the two statements come from different authorities describing different
   things (award period vs. data-augmentation horizon).
3. **Institution list.** `cm4ai.org/data-releases/` lists "UCSD, UCSF, Stanford, UVA, Yale, UT
   Austin, UA Birmingham, Simon Fraser University, and the Hastings Center"; the March 2025
   Dataverse description gives the same list without UT Austin. The fuller, more recent portal
   list is used in `creators`, and the divergence plus the additional affiliations appearing in the
   preprint (University of Alabama, University of Montreal) and Dataverse author metadata (KTH) is
   stated in the creator description.
4. **IF protein counts.** Per-condition protein coverage is stated as 563 (March 2025 archives),
   464 (June 2025 and October 2025 archives), and 523 ("IF images for 523 proteins" among the TNBC
   flagship datasets on cm4ai.org). The June 2026 IF archives carry MD5 checksums that differ from
   the same-named June 2025 / October 2025 archives and state no protein count. No single number
   is asserted for the current release; the divergence is recorded in `anomalies` and each figure
   is attributed to its release in `subsets` and `file_collections`.
5. **Archive sizes across releases.** `cm4ai_mass-spec_KOLF2.zip` is 23.8 MB in October 2025 and
   171.8 KB in June 2026; `cm4ai_mass-spec_MDA-MB-468.zip` is 23.0 MB and 93.9 KB respectively.
   The captured pages do not explain the change. Recorded as an anomaly rather than reconciled.
6. **Ethical-review contact affiliation.** Dataverse author metadata lists Vardit Ravitsky with
   affiliation "University of Montreal", while the Data Governance & Ethics block gives a Hastings
   Center email address. Both are recorded in `ethical_reviews`; neither is discarded.
7. **Copyright year.** Dataverse release descriptions state "Copyright (c) 2025 The Regents of the
   University of California"; the 2024 preprint states 2024. Both are recorded in `ip_restrictions`
   with their sources.
8. **Cell-map data scope.** The Nature 2025 publication in the corpus reports a U2OS osteosarcoma
   cell map with its own depositions (NDEx, MassIVE `MSV000097168`, ProteomeXchange `PXD052362`,
   ModelArchive, HPA v23). U2OS is a different cell context from the MDA-MB-468 / KOLF2.1J data in
   the CM4AI Dataverse releases. These resources are recorded in `external_resources` as associated
   project outputs with an explicit scope caveat and are **not** merged into the release
   composition, instance counts, or file inventory.
9. **Sali affiliation.** Dataverse author metadata lists "Sali A (University of California San
   Diego)" while the Nature paper and the CM4AI preprint place Andrej Sali at UCSF. No affiliation
   for Sali is asserted anywhere in the record; the conflict is noted here only.

### Unsupported or omitted content

- `total_size_bytes` and `CoreDistribution.bytes` are omitted throughout: the sources give only
  human-readable sizes ("3.8 GB", "113.3 KB") whose base is ambiguous. Sizes are carried verbatim
  as text in the corresponding descriptions instead.
- `variables`, `imputation_protocols`, and `annotation_analyses` are omitted: the corpus contains
  no variable-level data dictionary, imputation procedure, or inter-annotator statistic for the
  released data.
- `data_topic` and `data_substrate` are omitted from `Instance` objects: their `values_from`
  enumerations (`B2AI_TOPIC`, `B2AI_SUBSTRATE`) are not resolvable in the merged schema, and no
  identifier could be supplied without invention.
- `participant_compensation` is omitted rather than set to `false`, since there are no participants.
- Ontology CURIEs were not minted for organizations that the corpus does not identify with a
  persistent ID. Local `d4d:CM4AI/organization/...` identifiers are used; the one exception is the
  University of Virginia, for which the June 2026 Dataverse author metadata supplies ROR
  `https://ror.org/0153tk833`. Person references use the ORCIDs given in the Dataverse metadata.

### Internal consistency checks

- `total_file_count: 10` == number of `file_collections` (10) == number of core `distributions` (10).
- Top-level `doi` == `resources[HIGT4C].doi` == `version_access.latest_version_doi` (as URL form).
- Top-level `issued` (`2026-06-17T00:00:00Z`) == `resources[HIGT4C].issued` == the HIGT4C entry in
  `distribution_dates`.
- `license` is `https://creativecommons.org/licenses/by-nc-sa/4.0/` at top level, on all four
  `resources`, and on all ten `file_collections`, with no divergence.
- `compression: zip` at top level matches `resources[HIGT4C].compression` and every
  `file_collections[*].compression`; it is deliberately absent on F3TD5R (mixed HTML/JSON/ZIP) and
  B35XWX (mixed JSON/ZIP).
- Human-subject statements are consistent across `human_subject_research`, `is_deidentified`,
  `sensitive_elements`, `confidential_elements`, `at_risk_populations`, `participant_privacy`, and
  `regulatory_restrictions`: no human subjects, de-identified samples, not FDA regulated.

### Corrections applied during Phase 3

None to fact content. Phase 2 surfaced no source-supported value that the full record was missing,
so no back-port into the full record was required. The only core-exclusive content is file-level
`format`, `media_type`, and `md5`, which `FileCollection` does not declare in the full schema; every
one of those MD5 values is also quoted in the corresponding full `file_collections` description, and
this was verified mechanically (10/10 matches).

Schema-conformance fixes made during Phase 1 (before any validation passed) were structural, not
factual: RFC 3339 offsets added to all `datetime` values; single-valued object-range slots
(`principal_investigator`, `grantor`, `contact_person`, `reviewing_organization`,
`governance_committee_contact`) converted from inline objects to identifier references per the
schema's non-inlined ranges, with the displaced names, emails, and affiliations preserved in
adjacent description or detail text; `scope_impact`/`recommended_mitigation` removed from a
`DatasetBias` object (they belong to `DatasetLimitation`) and folded into `mitigation_strategy`;
`Instance.missing_information` inlined object replaced by prose in the instance description, since
that slot is a reference list rather than an inlined list.

## Phase 4 - Strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via `SchemaView`; no
hand-written field list was used.

- **Schema-identical shared slots: 76.** All are present in both records or absent from both, and
  all parsed YAML values are deeply identical, including narrative fields, nested mappings, and
  list ordering. Core condenses, paraphrases, reorders, and omits nothing.
- **Projected slots: 1** (`resources`, range `Dataset` in full and `CoreDataset` in core).
- **Core-only slots: 2** (`distributions`, `dialect`). `dialect` is unpopulated, consistent with
  `is_tabular: false` in both records and with a release consisting of ZIP archives.
- **Full-only slots populated: 13** (`citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `participant_privacy`,
  `related_datasets`, `relationships`, `splits`, `subsets`, `third_party_sharing`,
  `total_file_count`). These have no `CoreDataset` counterpart and are correctly absent from core.

### `resources` projection

Coverage is equal: the same four release identifiers appear in both records, in the same order
(HIGT4C, K7TGEM, F3TD5R, B35XWX). Every nested slot that is schema-identical between `Dataset` and
`CoreDataset` is deeply identical across the pair. The only full-only nested slot in use,
`total_file_count`, is omitted from the core projection, as required.

### Related, non-identical content - semantic review

The validator emits one `semantic-review-required` warning for
`$.file_collections <-> $.distributions`. That warning marks content for review; the review below
is the record of it having been performed.

- **Mapping.** 1:1 by name across all ten members of the current release; deterministic matcher
  reports 10 matches and zero unmatched core distributions.
- **Names and paths.** Identical in both records for all ten files (`path` equals the archive file
  name; `id` equals `https://doi.org/10.18130/V3/HIGT4C#<file name>` on both sides). Verified
  mechanically: zero mismatches.
- **Descriptions.** Core distribution descriptions are the full `file_collections` descriptions
  with the MD5 clause moved into the structured `md5` slot. No fact appears in one and contradicts
  the other.
- **Formats and compression.** `compression: zip` on both sides for all ten. Core additionally
  carries `format: ZIP` and `media_type: application/zip`, which the full `FileCollection` class
  cannot express; these agree with the Dataverse file table ("ZIP Archive") and with the full
  record's `compression`. No conflict.
- **Checksums.** All ten `md5` values in core are byte-identical to the MD5 quoted in the matching
  full description; verified mechanically.
- **Byte counts.** Omitted on both sides (`total_size_bytes`, `FileCollection.total_bytes`,
  `CoreDistribution.bytes`), so no scope mismatch is possible. Human-readable sizes appear as text
  in both descriptions and agree.
- **Access URLs.** Neither side carries a per-file download URL, because the source gives none;
  release-level access URLs appear in `distribution_formats.access_urls` and `download_url`, which
  are schema-identical shared slots and therefore already proven deeply identical.
- **Release scope.** All ten distributions and all ten file collections belong to HIGT4C; none mix
  in a historical release's files. `total_file_count: 10` (full) matches the ten distributions in
  core, describing the same scope.
- **Historical vs current.** The differing values between releases (file counts 10/8/21/6, DOIs,
  publication dates, Dataverse versions, and the differing MD5s of same-named archives) are
  release-scoped facts, not contradictions, and are labelled as such through `resources[*].status`
  and explicit wording in each description.
- **Identity/version/access agreement.** Top-level `doi`, `issued`, `version`, `license`,
  `publisher`, and `download_url` agree with `resources[HIGT4C]`, with `version_access`, with
  `distribution_dates`, and with the per-file `license`/`publisher` on the file collections.

**Unresolved contradictions within or between the two records: none.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml
```

## Final results

| Check | Result |
|-------|--------|
| Full schema validation (`Dataset`) | No issues found |
| Full ontology term validation | Validation passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core ontology term validation | Validation passed |
| Pair consistency (`--sync-core`) | PASS: 76 schema-identical slots; projected slots=['resources'] |
| Pair consistency (final, independent) | PASS: 76 schema-identical slots; projected slots=['resources'] |
| Semantic review of related content | Performed; `file_collections <-> distributions`, 10 deterministic matches, 0 unmatched, 0 conflicts |
| Prior D4D factual reuse | None; provenance boundary held |
