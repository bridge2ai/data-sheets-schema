# AI_READI full/core reconciliation report

Run label: `2026-07-23_gpt-5.6-sol-ultra-fast`

Runtime: Codex CLI; provider: OpenAI; model: `gpt-5.6-sol`; reasoning
effort: `ultra`; mode: `fast`; generation date: `2026-07-23`.

## Evidence and provenance boundary

The only factual inputs used were:

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- `data/preprocessed/source_manifest.yaml`, restricted to the seven
  `projects.AI_READI` entries:
  - `bmj_protocol_publication` /
    `bmjopen-2024-097449_row2.txt`
  - `nature_metabolism_publication` /
    `s42255-024-01165-x_row3.txt`
  - `nih_reporter_project` /
    `reporter_nih_gov_project-details-10471118_row7.txt`
  - `dataset_documentation` /
    `docs_aireadi_org_docs-2_row10.txt`
  - `dataset_license` /
    `AI-READI-LICENSE-v1.0_row11.txt`
  - `fairhub_dataset` /
    `fairhub_dataset_2_row12.txt`
  - `irb_protocol` /
    `gdrive_1rJsa5kySlBRRNhsO_WY7N3bfSKtqDi-Q_row13.txt`
- From Phase 2 onward, the exact same-run full record:
  `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml`
- From Phase 3 onward, the exact same-run core record:
  `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml`

The LinkML schemas, required repository instructions, pair-validation
implementation, and normal validator configuration were read only as structural
or procedural authorities, never as sources of AI_READI facts.

No prior-run full or core D4D, prior reconciliation report, evaluation output,
test-fixture fact, git history, live web content, or model-memory fact was read
or used. No output for another project was used. Schema annotations and examples
were not treated as facts or defaults.

## Phase 3

### Source authority, version, date, and scope findings

- The direct dataset resource supplies the canonical title, `AI-READI
  Consortium` creator, release history, and latest identified release:
  version `3.0.0`, DOI `10.60775/fairhub.3`, dated `2025-11-17`.
- The selected resource URL is `https://fairhub.io/datasets/2`; it states that
  the selected version is no longer accessible. The `165,051 files` and
  `2.01 TB` display is therefore attached only to the explicitly legacy
  version-2 collection and is not promoted to a version-3 or dataset-family
  total.
- The source does not define whether `2.01 TB` is decimal or binary and does
  not provide an exact integer byte count. It remains a scoped narrative value;
  `total_size_bytes`, collection `total_bytes`, and core `bytes` are omitted.
- The source provides no version-3 file count, participant count, direct
  download URL, checksum, MIME type, archive/compression value, or exact
  release timestamp. Those optional assertions are omitted.
- `4,000` is retained only as the later protocol's target enrollment. It is
  not represented as an actual participant or released-instance count. The
  older IRB value of `4,600` and NIH wording `4,000+` do not override the later
  Nature/BMJ target.
- The later project expansion “Artificial Intelligence Ready and Equitable
  Atlas for Diabetes Insights” is used. The older NIH/IRB “Exploratory” wording
  is not presented as the current name.
- The study is described as primarily cross-sectional, with a planned 10%
  longitudinal follow-up subset. This resolves the later protocol design
  against the older NIH/IRB longitudinal aim without collapsing their scopes.
- Recruitment, award, publication, documentation-update, and release dates are
  kept separate. In particular, the `2026-06-04` documentation update is not a
  dataset modification or release date.
- The direct University of Washington Data License Agreement and FAIRhub
  `Health Data License` label govern dataset licensing. The BMJ article's
  `CC BY-NC 4.0` license is publication-only and is not used as the dataset
  license.
- Detailed later sources override broad NIH public-availability language:
  AI_READI has a public/deidentified access layer and a controlled/full access
  layer. Public access requires license agreement; controlled access requires
  an agreement and approval.
- `STUDY00016228` is recorded as the University of Washington IRB approval
  identifier because the Methods section explicitly establishes that scope. It
  is not represented as a ClinicalTrials.gov identifier.
- Aaron Y. Lee is scoped as the NIH award principal investigator; the
  AI-READI Consortium remains the dataset creator. University of Washington is
  scoped as award recipient and dataset licensor. UAB, UCSD, and UW are the
  three data-collection sites; other consortium affiliations are not mislabeled
  as collection sites.
- Supported released representations are recorded as CSV, XML, DICOM, and an
  mHealth standard representation. Proprietary `.fda`, `.sdt`, and FIT values
  are described as source-device exports that are converted, not silently
  asserted as current distribution formats.
- The source-level discrepancy about the exact participant coverage of version
  2 was not resolvable without outside evidence, so no version-2 temporal or
  participant coverage claim was emitted.

### Corrections

All source-audit corrections were applied to the full record first and then to
the core record where the core schema permits the slot:

1. Removed top-level and collection `issued` timestamps. The sources provide
   calendar dates, not times, so fabricated midnight timestamps were not kept.
   Exact dates remain in `distribution_dates`, `version_access`, and narrative
   release scope.
2. Removed `sampling_strategies.is_random: false`; targeted recruitment is
   supported, but the sources do not establish whether selection within every
   recruitment pool was random.
3. Removed the inaccessible legacy FAIRhub page from
   `distribution_formats.access_urls`. It remains a provenance resource and the
   legacy version-2 collection path, not a working format download URL.
4. Corrected proprietary retinal extensions to `.fda` and `.sdt`, preserving
   their source meaning as extensions rather than organizations or standards.
5. Removed the ordinary adult cohort from
   `human_subject_research.special_populations`; the sources support age and
   health eligibility but do not classify the whole cohort as a protected
   special population.

No source-supported core-only discovery required an additional factual
back-port. Core `distributions` were the expected schema projection of the
source-audited full `file_collections`.

### Internal audit result

- Root `id`, DOI, title, name, version, creator, status, and license are
  internally consistent.
- Version `3.0.0` is consistently latest; version `2.0.0` is consistently
  historical and inaccessible; all three DOI/date pairs agree wherever
  repeated.
- The only structured file count is `165051` on the legacy version-2
  collection. Root totals and version-3 totals are absent.
- The public/controlled access distinction, license restrictions,
  deidentification description, sensitive elements, and prohibited uses agree.
- People, organizations, grants, study dates, collection sites, IRB identifier,
  and intended target count have consistent roles and scopes.
- No unsupported factual assertion remained after the corrections.
- Phase 3 result: **zero unresolved within-record or cross-record factual
  contradictions**.

### Phase 3 validation

At Phase 3 entry, and again after the corrections, all four commands passed:

```bash
poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  --target-class Dataset

poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  --target-class CoreDataset
```

Results for each run: `linkml-validate` reported `No issues found`; each term
validator reported `Validation passed`.

For completeness, the first Phase 1 schema-validation attempt identified only
serialization-shape issues: timezone-less datetimes and class references
serialized inline where the merged schema expected identifier strings. Those
references were corrected, both Phase 1 validators then passed, and the
unsupported timestamps were subsequently removed during the Phase 3 factual
audit. Phase 2 core schema and term validation passed on its first run.

## Phase 4

### Schema-derived synchronization

The audited full record was treated as canonical. The one permitted sync command
was:

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml \
  --sync-core
```

Result:

```text
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
Phase 4 must semantically review related distribution content;
deterministic matches=2, unmatched core distributions=[]
```

The validator-reported schema-derived shared-slot count is **76**. The sole
projected root slot is `resources`. The sync added the exact required core
header line:

```text
# Phase 4 reconciliation: completed
```

### Warning and related-content semantic review

Both deterministic mappings were reviewed:

| Full file collection | Core distribution | Match | Scope and semantic disposition |
|---|---|---|---|
| `https://doi.org/10.60775/fairhub.3` | `https://doi.org/10.60775/fairhub.3` | `id` | Names, descriptions, and DOI paths are identical. Full metadata scopes it to version `3.0.0`; shared release history gives `2025-11-17`. No file count, byte total, direct download URL, singular format, compression, or checksum is asserted. |
| `https://doi.org/10.60775/fairhub.2` | `https://doi.org/10.60775/fairhub.2` | `id` | Names, descriptions, and legacy `/datasets/2` paths are identical. Full metadata scopes it to version `2.0.0`, released `2024-11-08`, and no longer accessible. `file_count: 165051` exists only in the full collection because CoreDistribution has no file-count slot. The `2.01 TB` display remains narrative; both numeric byte fields are absent. |

The remainder of the required semantic review found:

- **Descriptions and names:** deeply equal for each matched collection and
  distribution.
- **Paths and access:** v2 uses the exact selected legacy path and is explicitly
  labeled inaccessible. v3 uses its DOI locator; it is not mislabeled as a
  direct download URL. No unsupported format-level access URL remains.
- **Formats:** shared `distribution_formats` is deeply identical and contains
  CSV, XML, DICOM, and the mHealth standard representation. The two release
  collections are mixed-format, so no single `CoreDistribution.format` value is
  asserted.
- **Compression:** absent from root, both collections, and both distributions;
  the source supplies none.
- **Checksums:** hash, MD5, and SHA-256 are absent; the source supplies none.
- **Byte counts:** full `total_size_bytes`, collection `total_bytes`, and core
  `bytes` are absent. No conversion from the ambiguous `2.01 TB` display was
  invented.
- **File totals:** full root `total_file_count` is absent because no
  current/dataset-family total is supported. The legacy v2 collection count is
  not compared to v3 or treated as a core byte/count value.
- **Release/version scope:** top-level version and DOI identify v3; the v2 and
  v3 collection scopes, release dates, status text, `distribution_dates`, and
  `version_access` have no contradiction.
- **Access and license:** shared license and access terms are deeply identical.
  Public/deidentified versus controlled/full access remains explicit.
- **Resources:** `resources` is absent from both records. Projected coverage is
  therefore identical, with no unmatched nested resource.
- **Dialect and tabularity:** `dialect` is absent and `is_tabular` is absent in
  both records because the source describes a mixed-modal dataset and supplies
  no single tabular dialect applicable to the whole release.
- **Repeated facts:** root identity, creator, funders, purpose, study design,
  target count scope, release history, ethics, formats, maintenance, access,
  and license assertions agree across the pair.

The pair validator's warning is therefore fully reviewed and dispositioned. It
does not represent an unresolved contradiction.

### Final independent pair validation

The required non-sync command was:

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml
```

Result:

```text
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
Phase 4 must semantically review related distribution content;
deterministic matches=2, unmatched core distributions=[]
```

There were no pair errors. All 76 schema-identical slots have identical
presence and deeply identical parsed YAML values. The warning is the expected
manual-review marker documented above.

### Final schema and term validation

After sync, semantic review, and the independent pair check, the same four
schema/term commands documented under Phase 3 were run again. Final results:

- Full `Dataset` schema validation: **PASS** (`No issues found`)
- Full `Dataset` term validation: **PASS** (`Validation passed`)
- Core `CoreDataset` schema validation: **PASS** (`No issues found`)
- Core `CoreDataset` term validation: **PASS** (`Validation passed`)
- Independent full/core pair validation: **PASS**
- Unresolved contradictions: **0**

## Changed artifacts

Exactly these artifacts were created or changed:

1. `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml`
2. `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml`
3. `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_reconciliation.md`

Informational line counts after reconciliation are 758 lines for full and 483
lines for core. These counts are metadata only and were not used as quality or
completeness criteria.
