# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep3

- Project: CHORUS
- Arm: CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- Mode: four-phase project agent, crate-only, de-primed
- Runtime: Claude Code · Provider: Anthropic · Model: `claude-opus-5[1m]` · Temperature 0.0
- Declared input bundle: `data/preprocessed/concatenated/CHORUS_crate_only.txt`
- Source manifest: not used (crate-only arm declares a single source bundle)
- Full: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CHORUS_d4d_core.yaml`

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual inputs used in this run, in full:

1. `data/preprocessed/concatenated/CHORUS_crate_only.txt` (357 lines; the reduced crate JSON-LD
   `CHORUS_crate_metadata_reduced.json` plus `ai_ready_score.json`).
2. `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (structure only, class `Dataset`).
3. `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (structure only, class `CoreDataset`).
4. Repository generation/validation instructions: `.claude/agents/d4d-provenance-guard.md`,
   `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`.

No prior generated D4D record was read, from any arm, label, or date. Nothing under
`data/d4d_concatenated/` other than this run's own two output files was opened, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened.
`data/preprocessed/source_manifest.yaml` and the document corpus were withheld by the arm
definition and were not read. Structure was derived at runtime with LinkML `SchemaView` against the
two schema files, not from any example record; no `d4d:docExample` value was carried into either
output.

### Evidence quality of the declared bundle

The crate is rich in governance, ethics, access, and responsible-AI (`rai:*`) narrative and thin in
quantitative composition. It supports identity, creators, funding, purpose, intended and prohibited
use, bias, limitations, de-identification, IRB/ethics, collection and preprocessing mechanisms,
licensing, access conditions, and maintenance in the crate's own words. It does not support cohort
counts, participant demographics, subpopulation breakdowns, variable-level metadata, collection
timeframes, sampling strategy, instance-level structure, informed-consent detail, existing uses, or
errata. Those slots were left absent rather than inferred. The crate's own AI-readiness assessment
independently reports the same gap for quantitative content: *"No statistical characterization
available."*

File inventories were deliberately collapsed in this bundle, so no per-file paths, checksums,
formats, or byte counts are available. `file_collections` (full) and `distributions` (core) were
therefore left absent in both records.

### Value-level checks against the bundle

| Claim | Source evidence | Result |
|---|---|---|
| `doi: 10.18130/V3/XNBOPG`, `id` = its resolvable form | crate `identifier`; ai-ready `findable`/`persistent` | consistent in three places |
| `version: 1.0 Beta` | package and both sub-crates | consistent |
| `issued: 2026-04-03` | package `datePublished` `2026-04-03`; `releaseDate` `03/04/2026`; EHR sub-crate `datePublished` `03/04/2026` | consistent — the ISO form disambiguates `03/04/2026` as DD/MM (3 April 2026); not a contradiction |
| `total_size_bytes: 1201585609503` | `contentSize` `1.201567472832 tb` (waveforms) + `18.136671 mb` (EHR); package `contentSize` `1.2 tb` | aggregation of the two exact sub-crate values; agrees with the package's rounded `1.2 tb` |
| `total_file_count: 1477` | ai-ready `verifiable`: "99% of files have checksums (1469/1477)" | denominator taken as the file count |
| `license` (package) vs `license` (sub-crates) | `Data Use Agreement available at 'https://chorus4ai.org/dataset/'` vs `See Data Use Agreement` | different wording of the same instrument; both retained verbatim at their own level, not merged |
| `hipaa_compliant: compliant` | "maintaining compliance with HIPAA"; "De-identification consistent with HIPAA Safe Harbor" | supported |
| IRB facts (`#2022P000707`, MGB IRB, address, `irbreliance@mgb.org`, `+1-857-282-1900`) | crate `irb`, `irbProtocolId`, `ethicalReview` | consistent |
| Imaging in `raw_data_sources` vs "No DICOM images are included" | crate `description` vs `completeness` | not a contradiction: imaging is an in-scope modality, absent from this interim release. Recorded in both `raw_data_sources[imaging].access_details` and `missing_data_documentation`. |
| Bias list appears twice (`rai:dataBiases`, `rai:potentialBiases`) | byte-identical in the crate | recorded once in `known_biases`; no conflict |
| Maintenance plan appears twice (`rai:dataReleaseMaintenancePlan`, `rai:maintenancePlan`) | byte-identical in the crate | recorded once in `updates`; no conflict |

### Judgment calls, recorded explicitly

- **`confidentiality_level: confidential`.** The crate states `HL7:2V (very restricted)`. The
  `ConfidentialityLevelEnum` offers only `unrestricted | restricted | confidential`; `confidential`
  is the most restrictive permissible value. The verbatim crate string is preserved in
  `confidential_elements.confidentiality_details`.
- **`is_tabular: false`.** Inferred from the declared multimodal content (imaging, WFDB waveforms,
  tokenized text) and the declared formats (`.ipynb`, `text/tab-separated-values`, `wfdb`). The
  crate makes no direct tabularity statement.
- **`issued` timestamps.** LinkML `datetime` requires a full date-time; the crate supplies a date.
  Rendered as `2026-04-03T00:00:00Z`. The time component carries no evidentiary claim.
- **`sensitive_elements`.** The crate's `rai:personalSensitiveInformation` array lists *protective
  controls*, not sensitive elements. The list is recorded verbatim as
  `sensitivity_details` with a `description` that states what the crate actually asserts, and the
  same controls are also mapped to their semantically correct home in `participant_privacy`
  (full-only slot). No control was restated as if it were a data element.
- **Non-inlined object references.** The schema declares `principal_investigator`, `grantor`,
  `contact_person`, `reviewing_organization`, and `governance_committee_contact` as single-valued
  slots over identified classes, i.e. non-inlined — the value must be an identifier string, not an
  object. Each is a CURIE reference; the human-readable identity behind it (name, email,
  affiliation) is preserved in the parent object's `description` or detail list so no crate fact is
  lost to the structural constraint.
- **`created_on` dropped.** The crate gives a publication date, not a creation date. `issued`
  carries it; `created_on` was left absent rather than aliased.

### Phase 2 discoveries back-ported to full

None. Core was derived from the Phase 1 full record after that record had itself been built directly
from the bundle. Re-reading the bundle against the `CoreDataset` inventory in Phase 2 surfaced no
core-permitted slot that the full record had left empty and no fact the full record had missed, so
no back-port into the full record was required and no correction was made in either direction.

### Validation after audit

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CHORUS_d4d.yaml
→ No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
→ Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CHORUS_d4d_core.yaml
→ No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
→ Validation passed
```

## Phase 4 — Strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime by intersecting the induced attributes of `Dataset`
(full schema) and `CoreDataset` (core schema) via LinkML `SchemaView`. No hand-written field list
was used. The core record was produced by projecting the audited full record through that derived
inventory, so schema-identical slots are identical by construction rather than by later
synchronization.

- Schema-identical shared slots checked: **76**
- Projected slots: **`resources`** (`Dataset` in full → `CoreDataset` in core)

### Result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml
→ PASS: 76 schema-identical slots; projected slots=['resources']
```

`--sync-core` was not needed and was not run: the projection produced no divergence for the
validator to repair. Every schema-identical shared slot is present in both records or absent from
both, with deeply identical parsed YAML including nested mapping values and list order. No narrative
field was condensed, paraphrased, reordered, or dropped in core.

### Projected slot: `resources`

Both records carry the same two sub-resources, matched by `id` with equal coverage:

| `id` | name | core-permitted slots | full-only slots omitted from projection |
|---|---|---|---|
| `urn:uuid:08cf7419-b94d-4508-8f64-c99c557351d7` | CHoRUS RO-Crate EHR SubRoCrate | id, name, title, description, keywords, version, issued, license, download_url | `citation`, `total_size_bytes` (18136671) |
| `urn:uuid:b9b41c72-0895-4ec2-9e39-8de2a83abcd6` | CHoRUS RO-Crate Waveforms SubRoCrate | id, name, title, description, keywords, version, issued, license, download_url | `citation`, `total_size_bytes` (1201567472832) |

Every nested schema-identical slot is deeply identical across the pair. `citation` and
`total_size_bytes` are not declared on `CoreDataset`, so they are legitimately full-only.

### Related, non-identical representations — semantic review

- **`file_collections` (full) → `distributions` (core).** Absent from both. The bundle collapses
  file inventories, so there is no per-file path, format, checksum, or byte-count evidence. Nothing
  to map; no conflict.
- **`total_file_count` / `total_size_bytes` (full-only) vs distribution-level values.** No
  distribution-level values exist to compare against. Internally, `total_size_bytes`
  (1,201,585,609,503) equals the sum of the two sub-resource `total_size_bytes` values
  (1,201,567,472,832 + 18,136,671) and is consistent with the package's own `1.2 tb`. Scope is the
  same in both statements: the whole package.
- **`dialect`, formats, `is_tabular`.** `dialect` is core-only and absent (no delimiter or header
  evidence). `is_tabular: false` is identical in both records and agrees with
  `distribution_formats` — TSV, WFDB, and `.ipynb` — which is a mixed, non-tabular set.
- **Top-level identity/version/access vs resources, version history, and repeated statements.**
  `version: 1.0 Beta` matches both sub-resources; `issued` matches both sub-resources;
  `version_access.latest_version_doi` resolves to the same DOI as `id` and `doi`;
  `license_and_use_terms`, `regulatory_restrictions`, `prohibited_uses`, and
  `confidential_elements` all describe the same controlled-access enclave regime without
  contradiction. All identical across full and core.
- **Historical vs current release.** Only one release (1.0 Beta) is described. The maintenance plan
  refers to prospective versions and archived prior versions; no prior version's values are asserted
  as current, so there is no historical/current conflict to resolve.

### Files changed in Phases 3 and 4

None. No correction was required in either record after Phase 1 and Phase 2 validation.

## Outcome

Reconciliation clean. Both records pass schema and term validation; the schema-derived pair
validator reports PASS over 76 schema-identical slots with `resources` correctly projected; the
semantic review of projected and related content found zero unresolved contradictions within or
between the two records.

Informational metadata (never a quality gate): full 872 lines / 57 populated top-level slots /
475 populated slot instances including nested; core 820 lines / 50 populated top-level slots /
445 populated slot instances including nested. Seven top-level slots are full-only because
`CoreDataset` does not declare them: `citation`, `total_file_count`, `total_size_bytes`,
`participant_privacy`, `direct_collection`, `splits`, `third_party_sharing`.
