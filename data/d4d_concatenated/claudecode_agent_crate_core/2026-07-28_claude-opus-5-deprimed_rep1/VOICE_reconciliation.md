# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep1

- **Project:** VOICE (Bridge2AI-Voice)
- **Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
- **Mode:** four-phase project agent, de-primed
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5[1m]
- **Temperature:** 0.0

## Inputs

| Role | Path |
|---|---|
| Source bundle (only factual source) | `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` |
| Source manifest (provenance only) | `data/preprocessed/source_manifest.yaml` |
| Crate manifest (provenance only) | `data/ro-crate_packages/crate_manifest.yaml` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset` |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset` |

## Outputs

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml` |
| Report | this file |

---

## Phase 3 — source and provenance audit

### Provenance boundary

Read history for this run consists of the two governing documents
(`.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`), the Phase 1
method file `.claude/commands/d4d-agent.md`, the declared source bundle, the two manifests, the
two LinkML schemas, and the two output files written by this run. **No prior full or core D4D
record was read, searched, grepped, or cited**, from any arm, label, or date. Nothing under
`data/d4d_concatenated/` other than this run's own two output paths was opened, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened. The
version-label directory was listed (names only) once, to confirm no VOICE file already existed
there; it contained only CHORUS files from a different project agent, which were not read.

Structure was derived at runtime from the schemas with `SchemaView` (`class_induced_slots` on
`Dataset` and `CoreDataset` and on every nested class range), not from any example record. No
`d4d:docExample` annotation value was copied into either output.

### Scope decision

The bundle documents two distinct cohorts under separate protocols and separate ethics approvals,
plus a crate that describes one specific adult release. These are represented as four sibling
`resources` under a top-level Bridge2AI-Voice dataset rather than merged:

| Resource | Version | DOI | Scope |
|---|---|---|---|
| Adult, PhysioNet | 3.1.0 | 10.13026/8xbn-nq66 | current adult release, 833 participants |
| Adult, PhysioNet | 3.0.0 | 10.13026/k81f-qr68 | release described by the RO-Crate |
| Pediatric, PhysioNet | 1.1.0 | 10.13026/h995-bt35 | 300 participants aged 2–18, SickKids only |
| Adult, PhysioNet | 1.1 | 10.13026/249v-w155 | historical, files no longer available |

The top-level record carries no `version`, `doi`, `issued`, `total_file_count` or
`total_size_bytes`, precisely so that no release-specific fact is asserted at family level.
Pediatric-specific facts (SickKids recruitment, REB approval, reproschema-ui collection, Synapse
`syn73617068`) are stated only where scoped to the pediatric cohort.

### Source disagreements resolved

1. **Adult 3.1.0 vs 3.0.0.** `physionet_3_0_0` carries a curation note marking it superseded by
   `physionet_3_1_0`. Both are represented as distinct releases with distinct DOIs, dates,
   per-feature recording counts and release notes; neither is used to overwrite the other.
   Crate-derived facts (checksums, byte counts, `contentSize`, Merkle root, computations) are
   attached exclusively to the 3.0.0 resource, per the crate manifest's instruction to treat them
   as evidence about 3.0.0.
2. **Collection timeframe.** The healthsheet states "The data was collected over a period of 12
   months"; the crate states collection began after project launch in 2023 with v3.0.0
   participants collected roughly 2023–2025. The healthsheet block is v2.0.0-era (it repeatedly
   says "the current v.2.0.0 dataset"). Both statements are retained, with the 12-month figure
   explicitly scoped to the earlier release and the crate window used for the current releases.
3. **License representation.** The crate gives the 3.0.0 license as
   `https://physionet.org/content/b2ai-voice/view-license/3.0.0/`; every PhysioNet page names it
   "Bridge2AI Voice Registered Access License". These are the same license. The structured
   `license` slot was harmonised to the name across all four resources so that repeated license
   statements do not appear to disagree; the crate URL and the conditions-of-access URL are
   preserved verbatim in `license_and_use_terms.description`.
4. **Name spelling.** The project documentation writes "Jennifer Sui"; the PhysioNet author lists
   write "Jennifer Siu". Both spellings are recorded in the creator description rather than one
   being silently chosen.
5. **b2aiprep version.** The release notes say adult 3.0.0 was generated with b2aiprep v3.0.0; the
   crate registers the software entity at v3.0.2 (dateModified 2026-01-06). Both are stated. Only
   the crate-registered value is carried in a structured `Software.version` slot; the
   repository-pointer `Software` object carries no version, so the two do not conflict.
6. **Award identifiers.** The bundle contains `OT2OD032720`, `3OT2OD032720-01S1`,
   `3OT2OD032720-01S3`, `1OT2OD032720-01` and the documentation's printed
   "Award #3Tf-OTOD03272001S2". Each is recorded against the source that states it rather than
   normalised into a single number.

### Corrections applied to the full record (full is canonical)

| # | Slot | Change | Reason |
|---|---|---|---|
| 1 | `resources[3.0.0].total_file_count: 15` | removed | 15 is the count of crate-registered *dataset entities*, not files. The crate's own AI-readiness score reports 11 of 17 files with checksums, so 15 is not the release file count. The "15 component datasets" fact is retained in the resource description. |
| 2 | `file_collections[*].file_count` (9, 9, 6, 9) | removed | Each value counted crate-registered entities or Parquet files, not the number of files in the folder — the folders also hold TSV and JSON data dictionaries. Counts are retained, correctly scoped, in the collection descriptions. |
| 3 | `resources[3.0.0].conforms_to: https://w3id.org/ro/crate/1.2` | removed | RO-Crate 1.2 is what the crate metadata file conforms to, not what the dataset conforms to. Retained in the description. |
| 4 | `resources[3.0.0].license` | URL → license name | see disagreement 3 above. |
| 5 | `license_and_use_terms.data_use_permission` | dropped `publication_required` | The DTUA says the recipient "is encouraged to" publish, not required. Retained permissions: `general_research_use`, `health_medical_biomedical_research`, `ethics_approval_required`, `user_specific`, `project_specific`, `time_limit`. |
| 6 | `instances` | `Participant` split into adult (`counts: 833`) and pediatric (`counts: 300`) | A single family-level participant instance carrying 833 conflated the two cohorts. |
| 7 | `instances[recording].counts: 61937` | removed | The documentation states "~61,937" for adult v3.0 only. Asserting an approximate, single-release figure as an exact family-level count is unsupported. Both the approximate figure and the exact per-feature counts remain in the description. |
| 8 | `collection_timeframes[0]` | renamed and annotated | `start_date`/`end_date` are the NIH project period from RePORTER, not a published collection window; the record now says so explicitly. |
| 9 | `version_access.versions_available[v1.0]` | reworded | The end-of-November-2024 date and the Health Data Nexus platform come from two different statements; the entry now attributes each. |
| 10 | `external_resources[b2aiprep].used_software.version` | removed | see disagreement 5 above. |

Both files were re-validated after every correction.

### Unsupported-assertion sweep

No value in either record originates outside the declared bundle. Facts checked but deliberately
**omitted** for lack of support: ROR/ORCID identifiers for any organization or person (none appear
in the bundle); `data_topic` and `data_substrate` on `Instance` (no B2AI standards-registry CURIEs
appear in the bundle); `compression`; `issued`/`created_on`/`last_updated_on` (the schema range is
`datetime` and the bundle gives only dates — release dates are carried in `distribution_dates` and
`version_access` instead); a computed `total_size_bytes`.

`Grantor`, `Person` and `Organization` are non-inlined single-valued ranges in this schema, so
slots such as `principal_investigator`, `grantor`, `contact_person`, `reviewing_organization` and
`governance_committee_contact` can only hold identifier references. Readable `d4d:` CURIEs are
used and the referenced entity is named in adjacent description text; these CURIEs are structural
placeholders, not factual claims about a registry.

---

## Phase 4 — strict full/core reconciliation

### Method

The core record was produced by projecting the Phase 3-audited full record with a schema-derived
script: shared slot names were computed at runtime from `Dataset` and `CoreDataset` induced slots,
and each shared value was copied by reference from the parsed full record, so parsed YAML content
is identical by construction rather than by re-authoring. Core-only content was then added from
the source bundle. No hand-written field list was used, and `--sync-core` was not needed.

### Deterministic result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml \
  --core  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml
→ PASS: 76 schema-identical slots; projected slots=['resources']
```

`errors: []`, `warnings: []`. **76** schema-derived shared slots are deeply identical and
identically present or absent in both records, narrative fields included; core condenses,
paraphrases, reorders and omits nothing that is shared.

### Projection: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. Resource coverage matched by `id` is
equal (4 in each, same IDs). For every matched pair, every schema-identical nested slot is deeply
identical — verified for `id`, `name`, `title`, `description`, `version`, `doi`, `download_url`,
`publisher`, `license`, `keywords`, `is_tabular`. Full-only nested slots omitted from the core
projection: `citation`, `total_file_count`, `file_collections`.

### Related, non-identical representations — semantic review

**`file_collections` (full) → `distributions` (core).** Reviewed, no contradictions.

- *Folder-level.* Every full `file_collection` has exactly one core `distribution` with the same
  `name`, `path` and byte-identical `description`; ordering matches. Verified programmatically:
  adult 3.1.0 `features/`, `phenotype/`, `metadata/`; adult 3.0.0 `features/`, `phenotype/`;
  pediatric 1.1.0 `features/`, `phenotype/`, `metadata/`; adult 1.1 none in either record.
- *File-level (core-only enrichment).* The core adds 11 file-level `CoreDistribution` entries for
  adult 3.0.0 — the nine Parquet feature files and the two crate-registered phenotype TSVs — each
  carrying `path`, `bytes` and `sha256`, and for the TSVs `format: TSV` and
  `media_type: text/tab-separated-values`. This is **not** a divergence: the full schema has no
  checksum slot anywhere reachable from `Dataset` (`FileCollection` exposes `path`, `compression`,
  `collection_type`, `file_count`, `total_bytes` and the generic metadata slots, and no `files`
  slot links `File`), so these digests cannot be back-ported. Every byte count carried in a core
  distribution appears verbatim in the corresponding full collection description, and every core
  distribution `path` lies under a `path` declared by a full collection — both checked
  programmatically, zero exceptions.
- *Two upstream crate defects are recorded rather than silently repaired,* in the core
  distribution descriptions: the crate entity for `sparc_periodicity.parquet` carries
  `name: "sparc_loudness.parquet"`, and the entity for `torchaudio_pitch.parquet` carries
  `name: "torchaudio_spectrogram.parquet"`; in both cases the `contentUrl` disambiguates. The
  crate also gives `sparc_pitch.parquet` a `datePublished` of `08/18/2025` where every other
  feature file carries `12/16/2025`.

**`total_file_count` / `total_size_bytes` vs distribution-level values.** Both slots are absent
from the full record after Phase 3 correction 1, so there is nothing to contradict. For the
record: the 11 crate-registered files sum to 13,789,023,450 bytes = 12.84 GiB, against the crate
entity's stated `contentSize` of "12.9 GB". These agree under a binary (GiB) reading and disagree
under a decimal reading. Because the discrepancy is an ambiguity in the upstream unit, no derived
total is asserted in either record; the crate's "12.9 GB" is quoted as the crate's own claim in
the 3.0.0 resource description.

**`dialect`, formats and `is_tabular`.** `dialect` is core-only (no counterpart in `Dataset`), set
on all four resources as `delimiter: "\t"`, `header: "true"`, from the release documentation's own
load instruction `pd.read_csv("demographics.tsv", sep="\t", header=0)` and the description of the
phenotype files as tab-delimited with one row per participant. `is_tabular: false` is identical in
both records at family level and on every resource, and does **not** contradict `dialect`: each
release is a mixture of dense Parquet tensors and tabular TSV, so the release as a whole is not
tabular while its tabular components are tab-delimited with a header row. `FormatEnum` and
`MediaTypeEnum` have no Parquet member, so `format`/`media_type` are set only on the two TSV
distributions and omitted for Parquet rather than approximated.

**Top-level identity/version/access vs resources, version history and distributions.** Checked and
consistent. Every DOI appearing anywhere in either record is one of the six the bundle states
(`10.13026/8xbn-nq66`, `10.13026/k81f-qr68`, `10.13026/249v-w155`, `10.13026/h995-bt35`,
`10.13026/37yb-1t42`, `10.13026/mf9s-5r03`), and each is used with a consistent version scope.
`version_access.latest_version_doi` holds the adult project's version-independent DOI
(`10.13026/37yb-1t42`); the pediatric version-independent DOI (`10.13026/mf9s-5r03`) is stated in
`version_details` and in `related_datasets`, because the slot is single-valued. Release dates in
`distribution_dates` and `version_access.versions_available` agree with the per-resource
descriptions. Access statements agree across `distribution_formats`, `license_and_use_terms`,
`raw_data_sources` and `raw_sources`: features under registered/credentialed PhysioNet access,
raw audio under controlled access via Synapse `syn72370534` (adult) and `syn73617068` (pediatric)
through `DACO@b2ai-voice.org`.

**Historical vs current releases.** Adult 1.1 and the Health Data Nexus v1.0 record are marked
historical in their own descriptions ("files no longer available", "an earlier version"), and
`related_datasets` types the relationships explicitly (`is_new_version_of`, `is_replaced_by`,
`is_version_of`, `supplements`). Differing participant counts (306 at v1.0 vs 833 at v3.x) and
differing FFT parameters (512-point at v1.1 vs 400-point from v3.0.0) are release-scoped facts,
not contradictions.

### Divergences found

None. Every schema-identical shared slot is deeply identical; the single projected slot matches on
coverage and on every shared nested slot; the two related-content mappings above were reviewed
semantically and contain zero contradictions within or between the records.

---

## Validation log

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml
→ No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
→ Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml
→ No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
→ Validation passed

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
→ PASS: 76 schema-identical slots; projected slots=['resources']

poetry run d4d provenance record --project VOICE --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt
```

All validations were re-run after the Phase 3 corrections and after the core was regenerated from
the corrected full record.

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml` (created; 10 Phase 3 corrections applied)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml` (created; regenerated after Phase 3)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_provenance.yaml` (live provenance record)

## Size metadata (informational, not a quality gate)

| Record | Top-level slots populated | Lines |
|---|---|---|
| Full (`Dataset`) | 76 of 94 induced slots | 2463 |
| Core (`CoreDataset`) | 63 of 79 induced slots | 1765 |
