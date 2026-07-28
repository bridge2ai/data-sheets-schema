# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep1

- **Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
- **Mode:** four-phase project agent, de-primed
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0
- **Input bundle (only factual source):** `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
- **Provenance-only manifests:** `data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml` (76 top-level slots, 1307 lines)
- **Core:** `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml` (67 top-level slots, 1034 lines)

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, searched, or cited. The complete read history for
factual content is: the declared input bundle (both pages, lines 1–2059), the full schema
`data_sheets_schema_all.yaml`, and the core schema `data_sheets_schema_core_all.yaml`. Structure
was derived at runtime with LinkML `SchemaView` (`induced_class` for `Dataset`, `CoreDataset`,
and every nested range), not from any example record. No file under `data/d4d_concatenated/`
other than this run's own two outputs was opened, and no `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened.

### Source disagreements resolved

| Fact | Disagreement | Resolution |
|---|---|---|
| Program manager email | Website: `cmccrary@mgh.havard.edu`; crate: `cmccrary@mgh.harvard.edu` | Crate value used. The website form contains an evident typo in the domain, and the crate spelling matches the `mgh.harvard.edu` domain used for the PI contact in the same bundle. |
| Package publication date | Crate `datePublished` `2026-04-03`; crate `releaseDate` `03/04/2026`; EHR sub-crate `datePublished` `03/04/2026` | All resolve to 3 April 2026 (`03/04/2026` is DD/MM/YYYY, consistent with the parent's ISO value and with the citation "Harvard Dataverse, Apr. 2026"). All `issued` values normalised to `2026-04-03T00:00:00Z`. |
| Imaging in the release | Website "Current Released Dataset": 7,642 admissions with radiology data; webinar (Aug 2025): 1,000 images with de-id in process; crate `completeness`: "No DICOM images are included" | Not a contradiction — different scopes and dates. All three are recorded with explicit scope in the `Imaging study` instance, in `known_limitations` (`Interim release completeness`), and in `missing_data_documentation`. The crate statement is scoped to the version 1.0 Beta package; the crate's `hasPart` contains only EHR and waveform sub-crates, corroborating it. |
| Waveform volume | Website: 23 Tb; crate waveforms sub-crate `contentSize`: 1.201567472832 tb | Different scopes (broader released waveform corpus vs. the packaged v1.0 Beta sub-crate). Both recorded with scope in the `Waveform telemetry record` instance. Byte-level slots use only the crate's exact sub-crate values. |
| Admission counts | Webinar (Aug 2025): >45,000; website current release: 50,000; website/NIH anticipated: 100,000 | Current release (50,000) used for `instances[].counts`; the August 2025 figure retained as an explicitly dated historical value; the 100,000 figure retained as explicitly anticipated. |
| License string | Parent crate: "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"; sub-crates: "See Data Use Agreement" | Both verbatim, not in conflict — the sub-crates defer to the same DUA. Parent value used at top level; sub-crate values retained on the corresponding `resources` entries. |

### Corrections applied to the full record (full made canonical)

1. `regulatory_restrictions.confidentiality_level`: `restricted` → `confidential`. The crate records
   `HL7:2V (very restricted)`, and the schema's `confidential` value is defined as requiring IRB
   approval, formal data use agreements, and institutional authorization — which is exactly the
   documented CHoRUS access framework. `restricted` understated it.
2. Added top-level `publisher: organization:b2ai_chorus`. The crate states `"publisher": "B2AI CHoRUS"`.
   The slot range is `uriorcurie`, so the literal name cannot be the value; it is encoded as a CURIE
   consistent with the `organization:*` reference style used elsewhere in this record, and the literal
   name was added to the top-level `description`. This was found while auditing what core loses when
   `citation` (a full-only slot) is dropped, and was back-ported to full first.
3. Removed the `subsets` block (EHR / waveform entries). Both had `is_data_split: false` and
   `is_subpopulation: false`, making them semantically empty under `DataSubset`, and they duplicated
   byte counts already carried by `resources` and `file_collections` — three parallel representations
   of one partition is an internal-consistency hazard with no added evidence.
4. Extended the RO-Crate JSON-LD `distribution_formats` description with the remaining AI-readiness
   provenance counts from the bundle (1,468 datasets, 2 computation/experiment steps, 1 software
   instance), alongside the 44 documented schemas and 1,469/1,477 checksums already present.
5. `issued` values normalised to RFC 3339 with explicit UTC offset (schema range `datetime`).

Core was regenerated from the corrected full record after every change, so no correction exists in
one file only.

### Internal consistency checks (each file)

- `total_size_bytes` (1,201,585,609,503) = EHR 18,136,671 + waveforms 1,201,567,472,832, matching
  the two `resources` entries, the two `file_collections`, and the two core `distributions`; also
  consistent with the crate's rounded parent `contentSize` of "1.2 tb". The addition of two
  exhaustively enumerated `hasPart` sizes is the only arithmetic performed on source values.
- `total_file_count` 1477 is taken from the crate's own checksum statistic (1,469/1,477 files) and is
  scoped to the packaged release.
- `id` = `doi` = `version_access.latest_version_doi` = `https://doi.org/10.18130/V3/XNBOPG`.
- `version` "1.0 Beta" agrees across top level, both `resources`, and `version_access.versions_available`.
- Grant number `OT2OD032701` agrees between `funders`, the crate `funder` string, the NIH RePORTER
  core project number, and the project website acknowledgement.
- Contacts: PI `EROSENTHAL@mgh.harvard.edu` used consistently for `creators`, `ethical_reviews`, and
  `regulatory_restrictions.governance_committee_contact` (the crate names Eric Rosenthal as both PI
  and data governance committee contact).

### Assertions flagged as interpretation rather than verbatim source

- `informed_consent.consent_obtained: false` — read from the recorded exemption
  "HIPAA exemption 4 ((45 CFR 46.104(d)(4))" (quoted verbatim in the record) plus "IRB approval or
  waiver as appropriate"; the bundle does not state the boolean directly.
- `sampling_strategies.is_representative: false` — read from "Limited generalizability beyond
  participating hospitals", the referral-bias entry, and the not-recommended use "Population
  inference beyond participating institutions".
- `acquisition_methods.was_reported_by_subjects: false` — read from "not through prospective research
  interactions with patient".
- `is_tabular: false` — the packaged release combines OMOP TSV, WFDB waveforms, and notebooks.

### Evidence deliberately not emitted

- The crate's `isPartOf` target `ark:59852/organization-bridge2ai-s6VouUf8Gkm` is an Organization,
  not a dataset, so it was not encoded as `parent_datasets` or `related_datasets`.
- The crate's own `ark:59853/rocrate-chorus-ro-crate-package/` identifier was not emitted; the DOI is
  the dataset identifier and the ARK is crate-internal.
- The AIM-AHEAD trainee `$8,000 stipend` and travel allowance were **not** recorded under
  `participant_compensation`; they compensate training-program trainees, not data subjects.
- No `variables`, `imputation_protocols`, `annotation_analyses`, `content_warnings`,
  `consent_revocations`, or `collection_notifications` — the bundle supports none of them.
- Artifacts listed as withheld in the bundle header were not sought out or read.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via LinkML `SchemaView`;
no hand-written field list was used. Core was produced by projecting the audited full record
through the `CoreDataset` induced-attribute set, so schema-identical slots are identical by
construction rather than by manual copying.

**Validator result:** `PASS: 76 schema-identical slots; projected slots=['resources']`

### Full-only slots (absent from `CoreDataset`, correctly dropped)

`citation`, `total_file_count`, `total_size_bytes`, `file_collections`, `relationships`, `splits`,
`direct_collection`, `collection_consents`, `participant_privacy`, `third_party_sharing`.

### Core-only slots

- `distributions` — populated as the projection of `file_collections` (see below).
- `dialect` — deliberately left absent. The package is not wholly tabular (`is_tabular: false`), so a
  single top-level `FormatDialect` would mis-scope the WFDB and notebook content.
- `publisher`, `compression`, `language`, `conforms_to_class`, `conforms_to_schema`,
  `content_warnings`, `imputation_protocols`, `annotation_analyses`, record-level `created_*` /
  `modified_*` — `publisher` is populated (and shared with full); the rest are unsupported by the
  bundle and absent from both files.

### Projected slot: `resources` (`Dataset` in full → `CoreDataset` in core)

Matched by `id`, equal coverage (2 in each), no unmatched entries.

| `id` | Shared slots deeply identical | Full-only nested slots omitted from core |
|---|---|---|
| `urn:uuid:08cf7419-…351d7` (EHR SubRoCrate) | `id`, `name`, `description`, `version`, `issued`, `license`, `download_url`, `keywords` | `citation`, `total_size_bytes` |
| `urn:uuid:b9b41c72-…abcd6` (Waveforms SubRoCrate) | same set | `citation`, `total_size_bytes` |

`citation` and `total_size_bytes` are not slots of `CoreDataset`; their omission is required by the
core schema, not a content decision. Both values remain in the full record.

### Related-content mapping: `file_collections` → `distributions`

The validator emitted one warning (`semantic-review-required`, 2 deterministic matches, 0 unmatched
core distributions). The review it requires was performed:

| Full `file_collections` | Core `distributions` | Review |
|---|---|---|
| `CHoRUS EHR files` — `path: ehr/`, `total_bytes: 18136671`, `collection_type: [processed_data]` | `CHoRUS EHR files` — `path: ehr/`, `bytes: 18136671`, `format: TSV`, `media_type: text/tab-separated-values` | Name, description, path and byte count identical. `format`/`media_type` are core-only slots; `TSV` and `text/tab-separated-values` are the bundle's own format strings for the EHR data and agree with the `distribution_formats` entry present identically in both files. No compression declared in either. No conflict. |
| `CHoRUS waveform files` — `path: waveforms/`, `total_bytes: 1201567472832` | `CHoRUS waveform files` — `path: waveforms/`, `bytes: 1201567472832` | Name, description, path and byte count identical. `format`/`media_type` intentionally unset: the bundle's format is WFDB, which is not a permissible value of `FormatEnum` or `MediaTypeEnum`, and inventing a nearest match would misstate the format. No conflict. |

Additional cross-checks required by Phase 4 step 4:

- **Counts and sizes vs. distribution-level values.** Full `total_size_bytes` equals the sum of both
  distributions' `bytes`; full `total_file_count` (1477) is the crate-wide file count and is not
  contradicted by any per-distribution value (the bundle gives no per-collection file counts).
  Same scope, no conflict.
- **Checksums.** No per-distribution `md5`/`sha256`/`hash` emitted: the bundle reports only the
  aggregate "1,469 of 1,477 files have checksums", which is recorded in the RO-Crate
  `distribution_formats` entry in both files.
- **Access URLs.** `download_url` (`https://chorus4ai.org/dataset/`) agrees at top level, on both
  `resources`, and with every `distribution_formats.access_urls` value in both records.
- **Formats and `is_tabular`.** `is_tabular: false` in both; the seven `distribution_formats` entries
  are byte-identical in both records; `dialect` absent from core, consistent with `is_tabular: false`.
- **Identity / version / access facts.** `id`, `doi`, `version`, `issued`, `license`, `status`,
  `page`, `download_url`, `publisher` agree between top level, `resources`, `version_access`,
  `distribution_dates`, and `license_and_use_terms` in both records.
- **Historical vs. current releases.** The August 2025 snapshot, the website's "current released
  dataset", and the version 1.0 Beta package are each carried with explicit scope wording rather
  than being reconciled into a single number; they are not treated as contradictions.

No condensing, paraphrasing, reordering, or omission of shared narrative content was performed in
core.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml
poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt
```

`--sync-core` was not used. Core is a mechanical projection of the audited canonical full record, so
there was nothing to synchronise; the consistency check above is the independent, non-syncing run.

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml` (created, Phase 1; corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml` (created, Phase 2; regenerated after Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_provenance.yaml` (written by `d4d provenance record`, `record_mode: live`)

Nothing outside this run's version directories was modified.

## Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | PASS (no issues found) |
| Full — ontology term validation | PASS |
| Core — LinkML schema validation (`CoreDataset`) | PASS (no issues found) |
| Core — ontology term validation | PASS |
| Schema-derived full/core pair consistency | PASS — 76 schema-identical slots, projected: `resources` |
| Related-content semantic review (`file_collections` ↔ `distributions`) | Completed, 0 contradictions |
| Provenance boundary audit | PASS — no prior-run D4D, evaluation, or report used |
| Live provenance record | Present, `record_mode: live` |

Divergences between the pair: none beyond the schema-mandated full-only slots and the
`resources`/`distributions` projections documented above.
