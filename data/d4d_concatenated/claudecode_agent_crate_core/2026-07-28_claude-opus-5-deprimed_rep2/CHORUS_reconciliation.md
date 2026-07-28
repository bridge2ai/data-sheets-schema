# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep2

Arm: DE NOVO WITH CRATE (documents + RO-Crate evidence)
Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5[1m] · Temperature 0.0
Mode: four-phase project agent, de-primed

## Files

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_reconciliation.md` |

Declared factual input bundle: `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
Provenance-only manifests: `data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`

## Phase 1 — Full record

Structure derived at runtime from class `Dataset` in
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` via LinkML `SchemaView`
(induced slots, ranges, cardinality, inlining, enums). No prior D4D record, of any
arm or label, was read, opened, grepped, or consulted.

Two structural corrections were required during validation, both schema-driven:

1. `principal_investigator`, `grantor`, `contact_person`, `reviewing_organization`,
   and `governance_committee_contact` are single-valued class-range slots that are
   **not** inlined; they take identifier references, not inline objects. They were
   changed to `mailto:` / `urn:` identifier strings, and the human-readable name,
   email, telephone, and address were moved into the containing object's
   `description` so no evidence was lost.
2. `issued` is `datetime`; `2026-04-03T00:00:00` was rejected as not RFC 3339.
   Changed to `2026-04-03T00:00:00Z` at all three occurrences.

## Phase 2 — Core record

Field inventory derived from class `CoreDataset` in
`data_sheets_schema_core_all.yaml`. No older core record was consulted, as template
or otherwise. Every core slot that also exists in `Dataset` starts from the
validated Phase 1 value.

The bundle was re-read against the core-only and core-empty slots to look for
anything the full extraction missed. **No new facts were found**, so nothing was
back-ported to the full record. The core slots left absent, and why:

- `cleaning_strategies`, `imputation_protocols`, `annotation_analyses` — the bundle
  documents harmonization, tokenization, and de-identification, but no instance
  removal, missing-value processing, imputation, or inter-annotator analysis.
- `content_warnings`, `errata`, `retention_limit`, `use_repository`, `other_tasks` —
  no supporting statement anywhere in the bundle.
- `dialect` — `FormatDialect` describes tabular delimiter/quote/header conventions;
  the bundle states formats (`.ipynb`, `text/tab-separated-values`, `wfdb`, DICOM,
  EDF+/Persyst) but no dialect parameters.
- `language`, `created_on`, `last_updated_on`, `created_by`, `modified_by`,
  `was_derived_from`, `compression`, `conforms_to_class`, `conforms_to_schema` — not
  stated.

## Phase 3 — Source and provenance audit

### Provenance

- Factual inputs read: the declared bundle only. Structural inputs: the two LinkML
  schema files. Procedural inputs: `.claude/agents/d4d-provenance-guard.md`,
  `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`.
- `data/d4d_concatenated/` was listed once, for directory names only, to confirm the
  target label was unclaimed. No file under it was opened. No
  `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was opened.
- The source manifest and crate manifest were consulted for provenance framing only.
  The crate manifest's Dataverse landing-page facts (dataset title, publication date
  2026-04-21, Dataverse version 1.1, host) were **not** used as dataset facts, since
  the manifests are declared provenance-only for this run.
- Both headers carry `Prior D4D factual reuse: prohibited`; the core header names
  both its document bundle and its same-run full YAML, whose path contains the exact
  run label.

### Source disagreements resolved

| # | Disagreement | Resolution |
|---|---|---|
| 1 | Program-manager email: project website gives `cmccrary@mgh.havard.edu`; crate metadata gives `cmccrary@mgh.harvard.edu` | Used the crate form. The website string is a misspelling of the domain ("havard"), and the crate form is machine-readable metadata that agrees with the PI address `EROSENTHAL@mgh.harvard.edu` on the same domain. |
| 2 | Release date: crate top level and waveforms sub-crate give `datePublished: 2026-04-03`; the EHR sub-crate gives `datePublished: 03/04/2026`; top level also gives `releaseDate: 03/04/2026` | Same date. The ISO-8601 form is unambiguous and fixes `03/04/2026` as DD/MM/YYYY. `issued: 2026-04-03T00:00:00Z` recorded at all three levels; `distribution_dates.description` records that the RO-Crate also renders it as 03/04/2026. |
| 3 | Cohort scale: webinar (Sept 2025) "As of August 2025, covers 14 different hospitals with over 45K unique admissions"; website "Current Released Dataset: 50,000 patient admissions"; website "Anticipated Final Dataset: 100,000"; NIH abstract "more than 100,000 critically ill patients" | Not a contradiction — three different scopes/dates. Kept as three separately scoped `instances` entries, each naming its scope and source date in `description`. No single number was promoted to a top-level count. |
| 4 | Imaging: webinar "currently 1000 images available with de-id in process"; website "7,642 Admissions with Radiology Data"; crate `completeness` "No DICOM images are included" | Enclave holdings vs. the packaged v1.0 Beta release. Recorded distinctly: `instances` carries the Aug 2025 image count and the 7,642 radiology admissions; the imaging distribution description and top-level `status` state that the packaged release contains no DICOM images. |
| 5 | Waveform volume: website "23 Tb Waveform data"; crate waveforms sub-crate `contentSize: 1.201567472832 tb` | Different scopes — website describes the current released dataset in the enclave, the sub-crate describes the packaged interim release. The 23 Tb figure appears only inside the top-level `description` where it is attributed to the project website; the byte-exact 1,201,567,472,832 is recorded on the waveforms resource. |
| 6 | Package size: crate top level `contentSize: "1.2 tb"` vs. sub-crate sums (1.201567472832 tb + 18.136671 mb) | Top-level value is rounded. No top-level `total_size_bytes` was asserted, to avoid either a false-precision sum or a falsely rounded integer. Exact per-resource `total_size_bytes` recorded instead. |
| 7 | License: crate top level "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"; both sub-crates "See Data Use Agreement"; GitHub README "This project is licensed under the MIT License" | Each recorded verbatim at its own level. MIT is scoped explicitly in `license_and_use_terms.license_terms` to "the CHoRUS software project in the chorus-ai GitHub organization", not to the data. |
| 8 | GitHub organization overview is dated 2025-11-14 and marked "historical documentation" | The current source manifest explicitly selects it (curation note: the sheet no longer lists it and the website does not preserve its repository/SOP/tooling detail), so it is an allowed source. Facts drawn from it (repositories, SOPs, contribution mechanism, MIT license, access-request contacts) are scoped to the CHoRUS software/tooling layer. |

### Mis-scoping guarded against

The AIM-AHEAD Bridge2AI for Clinical Care Training Program occupies most of one
source document. Its trainee-facing facts — $8,000 stipend, travel allowance,
citizenship and degree eligibility, application deadlines, mentorship matching,
curriculum — are properties of a training program, not of the dataset, and were
excluded. `participant_compensation` is therefore absent from both records: no
compensation to *data subjects* is documented anywhere in the bundle. Only the
dataset-bearing content of that document was used: the modality/standard/access
table, retrospective collection, controlled access, the Aug 2025 snapshot, the
registration + licensing-agreement + `.edu` email access path (recorded in
`third_party_sharing` and explicitly attributed to the training-program route), and
"Datasets are being used for training activities and publications".

### Internal consistency

Repeated values were checked for agreement within each file: DOI
`10.18130/V3/XNBOPG` (5×), award `OT2OD032701` (5×), IRB protocol `2022P000707`
(4× full / 3× core), version `1.0 Beta`, date `2026-04-03`, and both contact
addresses appear in a single consistent form throughout. The three-count difference
in `1.0 Beta` and the one-count difference in `2022P000707` between full and core are
fully explained by the full-only slots `citation` and `collection_consents`.

### Corrections applied in Phase 3

None. No unsupported, stale, or mis-scoped assertion survived into either record, so
no fact required correction and no re-validation cycle was triggered by an audit
finding.

## Phase 4 — Strict full/core reconciliation

Shared slots derived at runtime with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list. 77 shared slot names, of which **76 have
identical induced range and cardinality** and 1 (`resources`) is a schema projection.

### Schema-identical slots

All 76 are present-in-both or absent-from-both, with deeply identical parsed YAML —
same nested mappings, same list items, same order. Narrative fields were copied
whole; nothing in core was condensed, paraphrased, reordered, or truncated.

### Projected slot: `resources`

`Dataset` in full, `CoreDataset` in core. Both records carry the same two resources,
matched by `id`, with equal coverage:

- `urn:uuid:08cf7419-b94d-4508-8f64-c99c557351d7` — CHoRUS RO-Crate EHR SubRoCrate
- `urn:uuid:b9b41c72-0895-4ec2-9e39-8de2a83abcd6` — CHoRUS RO-Crate Waveforms SubRoCrate

Every nested slot that both classes declare (`id`, `name`, `description`, `version`,
`issued`, `license`, `download_url`, `keywords`) is deeply identical. Two full-only
nested slots are omitted from the core projection because `CoreDataset` does not
declare them: `citation` and `total_size_bytes` (18,136,671 and 1,201,567,472,832
bytes). This is a schema-mandated omission, not a divergence.

### Related, non-identical representation: `file_collections` → `distributions`

Nine full `file_collections` map 1:1 onto nine core `distributions`; the validator
reports 9 deterministic matches and no unmatched core distribution. Semantic review
of the mapping:

| Property | Finding |
|---|---|
| Names, descriptions | Identical strings on all nine pairs. |
| Paths | Absent in both — the bundle states no file paths. |
| Formats | Full carries `conforms_to` (OMOP, OMOP with extensions, OHNLP, DICOM, WFDB, EDF+ and Persyst). `CoreDistribution.format` is a closed `FormatEnum` (CSV/TSV/XML/JSON/…) and `media_type` a closed `MediaTypeEnum`; none of the clinical standards is a member of either, and `conforms_to` has no `CoreDistribution` counterpart. No core format value is assertable, so none was invented. No conflict. |
| Compression | Absent in both — no evidence. |
| Checksums | The bundle reports checksum coverage only at package level ("99% of files have checksums (1469/1477)"), never per collection. `md5`/`sha256`/`hash` therefore absent in core; no conflict. |
| Byte counts | No per-collection sizes exist in the bundle, so `CoreDistribution.bytes` is absent throughout. `total_file_count: 1477` is full-only (no `CoreDataset` slot); with no distribution-level file counts asserted, there is no same-scope comparison to make and no conflict. |
| Access URLs | Carried by the shared slot `distribution_formats.access_urls` — identical in both. |
| Release scope | Carried by the shared slots `distribution_dates`, `status`, and `known_limitations` — identical in both. |
| `is_tabular` | `false` in both (shared slot). `dialect` absent in core, consistent with a multimodal, non-tabular-only dataset and with the absence of dialect evidence. |

### Identity, version, and access cross-check

`id`, `doi`, `version`, `license`, `publisher`, `issued`, `page`, `download_url`, and
`status` agree between the two records and with `version_access.latest_version_doi`
(`https://doi.org/10.18130/V3/XNBOPG`), with the DOI listed in
`distribution_formats.access_urls`, and with the citation string's "version 1.0 Beta"
in the full record. The single documented version, 1.0 Beta, is described
consistently as an interim release; the Aug 2025 snapshot and the anticipated final
cohort are labelled as such rather than presented as competing values for the current
release.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>

poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-deprimed_rep2 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt
```

### Files changed by Phase 3/4

Only the core file, and only by `--sync-core`, which added the header line
`# Phase 4 reconciliation: completed`. No slot value in either record was altered by
synchronization: core was built as a deterministic projection of the Phase-3-canonical
full record, so the sync pass was a content no-op. The full record was not modified
after Phase 1 validation.

## Results

- `linkml-validate` full (`Dataset`): **No issues found**
- `linkml-term-validator` full: **Validation passed**
- `linkml-validate` core (`CoreDataset`): **No issues found**
- `linkml-term-validator` core: **Validation passed**
- `d4d_pair_consistency` (final, no `--sync-core`): **PASS — 76 schema-identical
  slots; projected slots=['resources']**; one `semantic-review-required` warning for
  `file_collections` ↔ `distributions`, reviewed above with zero contradictions.
- Top-level slots populated: full **71**, core **61**. Line counts (informational
  only, not a quality gate): full 1135, core 799.
- Unresolved contradictions within or between the two records: **none**.
