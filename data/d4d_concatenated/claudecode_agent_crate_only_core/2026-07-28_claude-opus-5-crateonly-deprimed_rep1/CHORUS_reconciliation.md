# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep1

- Arm: CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- Runtime: Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0
- Mode: four-phase project agent, crate-only, de-primed
- Declared input bundle: `data/preprocessed/concatenated/CHORUS_crate_only.txt`
- Source manifest: not used (crate-only arm declares a single source bundle)
- Full: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_d4d_core.yaml`

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual inputs read during this run, in full:

1. `.claude/agents/d4d-provenance-guard.md`
2. `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`
3. `data/preprocessed/concatenated/CHORUS_crate_only.txt` (the only factual source)
4. `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
   `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, read through
   LinkML `SchemaView` for structure only
5. Phase 2 onward: the exact same-run full record listed above

No prior full or core D4D record was read, searched, listed for content, or cited.
No `*_crate_d4d.yaml`, `*_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`, or
`ro-crate-datasheet.html` artifact was opened. `data/preprocessed/source_manifest.yaml`
and the document corpus were not read, per the crate-only arm declaration. The output
directory listing consulted before writing was used only to confirm the version label
directory did not already exist; no file contents were read from it.

### Assessment of the evidence base

The crate bundle is a single structured upstream record: one reduced RO-Crate JSON-LD
graph (three entities — the package plus two sub-crates) and one AI-readiness
self-assessment. Its strengths are governance, ethics, access, bias, limitation, and
maintenance narrative: the `rai:*` block carries substantive prose on collection,
limitations, biases, intended and discouraged uses, access conditions, sensitive
information handling, and the release/maintenance plan, and the crate root carries a
complete authorship, funding, IRB, and copyright block.

Its weaknesses are quantitative and structural characterization. There are no instance
counts, no cohort sizes, no per-modality file counts, no collection timeframe, no
variable-level metadata, no subpopulation distributions, no labeling or annotation
protocol, no imputation or cleaning description distinct from the harmonization steps,
no existing-use or citation-of-use record, and no split proportions beyond the statement
that hold-out splits exist. The crate's own self-assessment concedes this: its
`characterization.statistics` entry is the single `has_content: false` field in the
document. The two sub-crates carry `hasPart: []`, so the file inventory that would
support composition detail is collapsed out of this bundle by construction. Slots
covering those areas were therefore left absent rather than filled by inference.

### Findings and corrections

**Correction 1 — dataset-level `total_size_bytes` removed (full record).**
Phase 1 recorded `total_size_bytes: 1200000000000` from the crate root's
`"contentSize": "1.2 tb"`. The sub-crates declare exact sizes: waveforms
`1.201567472832 tb` (1,201,567,472,832 bytes) and EHR `18.136671 mb` (18,136,671 bytes).
Writing the rounded root figure as an exact integer asserts a precision the source does
not have and makes the recorded whole smaller than one of its declared parts. The slot
was removed from the full record. The exact byte counts survive at
`file_collections[*].total_bytes` (full) and `distributions[*].bytes` (core). The slot
does not exist in `CoreDataset`, so the core record was unaffected. Both files were
re-validated after the change.

**Retained after audit, with the reasoning recorded here:**

- `total_file_count: 1477` — from `ai_ready_score.pre_model_explainability.verifiable`,
  "99% of files have checksums (1469/1477)". The separate figure "1468 dataset(s)
  documented" counts dataset entities, not files; the two are not in conflict and are
  not conflated. The 8-file checksum gap is recorded in `anomalies`.
- Date forms. The crate root gives `datePublished: "2026-04-03"` and
  `releaseDate: "03/04/2026"`; the EHR sub-crate gives `datePublished: "03/04/2026"`.
  Read as DD/MM/YYYY these are the same day, consistent with the ISO form. All records
  use 2026-04-03. The `issued` slot has range `datetime`, so `T00:00:00Z` was appended
  to satisfy the range; the time of day and UTC offset are format padding and carry no
  source claim.
- Access URL forms. The crate root gives `contentUrl: "http://chorus4ai.org/dataset"`;
  both sub-crates give `"https://chorus4ai.org/dataset/"`. Both forms are retained at
  the level where each appears rather than normalized to one.
- License strings. Root: "Data Use Agreement available at 'https://chorus4ai.org/dataset/'".
  Sub-crates: "See Data Use Agreement". Different granularity, not a conflict; each is
  kept at its own level.
- PI name forms. Root `principalInvestigator`: "Eric Rosenthal, EROSENTHAL@mgh.harvard.edu";
  sub-crates: "PI Eric Rosenthal  EROSENTHAL@mgh.harvard.edu"; author list: "Eric S.
  Rosenthal". Same person, formatting variance only. The root form is used for
  `creators[0].principal_investigator` and `regulatory_restrictions.governance_committee_contact`
  (whose source value, `dataGovernanceCommittee`, is byte-identical to it).
- Duplicated crate fields, deduplicated once each. `rai:dataBiases` and
  `rai:potentialBiases` are byte-identical → one `known_biases` list.
  `rai:dataReleaseMaintenancePlan` and `rai:maintenancePlan` are byte-identical → split
  across `updates`, `retention_limit`, and `maintainers` without repetition.
- Source typography preserved verbatim, not silently repaired: "Versioned dataset
  releases e.g., CHoRUS vX.Y)" (unbalanced parenthesis) and "HIPAA exemption 4 ((45 CFR
  46.104(d)(4))" (doubled parenthesis).

**Enum and range projections** (schema constraints, not source claims):

| Source value | Slot | Recorded | Verbatim kept at |
|---|---|---|---|
| `confidentialityLevel: "HL7:2V (very restricted)"` | `regulatory_restrictions.confidentiality_level` (3-value enum) | `confidential` (most restrictive available) | `regulatory_restrictions.description`, `confidential_elements` |
| `deidentified: true` | `is_deidentified.identifiable_elements_present` | `false` | `is_deidentified.deidentification_details` |
| commercial-use bar, proposal review, IRB documentation | `license_and_use_terms.data_use_permission` | `no_commercial_use`, `ethics_approval_required`, `project_specific` | `license_and_use_terms.license_terms` (full clauses) |
| `publisher: "B2AI CHoRUS"` | `publisher` (range `uriorcurie`) | `data_sheets_schema:B2AI_CHoRUS` | `maintainers[2].name` = "B2AI CHoRUS" |
| six bias bullets | `known_biases[*].bias_type` | `selection_bias`, `representation_bias`, `measurement_bias`, `sampling_bias`, `annotation_bias`, `historical_bias` | `bias_description` (verbatim bullet) |
| eight limitation bullets | `known_limitations[*].limitation_type` | methodological ×3, resolution, integration, representativeness, scope, coverage | `limitation_description` (verbatim bullet) |

Class-ranged scalar slots (`principal_investigator`, `grantor`, `contact_person`,
`reviewing_organization`, `governance_committee_contact`) are non-inlined references in
the schema and take an identifier string, so the crate's own verbatim person/organization
strings were used as the identifier. Detail that would not fit (the MGB IRB postal
address and reliance-office contact) was moved into
`ethical_reviews[0].review_details` rather than dropped.

**No back-port was required.** Phase 2 derived core mechanically from the audited full
record and re-consulted the bundle; it surfaced no fact that the full record had missed
and no value that the bundle contradicted. The only correction in this run is
Correction 1, applied to the full record.

## Phase 4 — Strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` over `Dataset` and
`CoreDataset`; no hand-written field list was used.

- **Schema-identical shared slots: 76 — all deeply identical, identical presence.**
  Core was produced by filtering the validated full record's parsed YAML through the
  `CoreDataset` slot inventory, so every shared value, including all narrative fields,
  is the full record's value unchanged. Nothing was condensed, paraphrased, reordered,
  or omitted. `--sync-core` was not needed and was not run.
- **Projected slots: `resources`** — absent from both records. The crate documents its
  two sub-crates as parts of the package, which are represented once, as
  `file_collections`/`distributions`; they were not duplicated into `resources`.

### Related, non-identical content — semantic review

`file_collections` (full, range `FileCollection`) → `distributions` (core, range
`CoreDistribution`). Two collections, two distributions, matched by identifier, equal
coverage, no unmatched entries.

| | EHR sub-crate | Waveforms sub-crate |
|---|---|---|
| id (both files) | `08cf7419-b94d-4508-8f64-c99c557351d7` | `b9b41c72-0895-4ec2-9e39-8de2a83abcd6` |
| name, description | identical | identical |
| bytes | 18,136,671 (`total_bytes` / `bytes`) | 1,201,567,472,832 |
| path | `ehr` | `waveforms` |

`CoreDistribution` has no `version`, `issued`, `license`, `download_url`, or `keywords`
slot, so those five full-side values are dropped by the projection rather than altered.
No value differs between the two representations for any slot both classes carry.
`hash`/`md5`/`sha256`/`format`/`encoding`/`media_type` are absent in core because the
bundle states no per-sub-crate checksum or format — the format list
(`.ipynb`, `text/tab-separated-values`, `wfdb`) is dataset-wide and is recorded once, in
`distribution_formats`, which is schema-identical and therefore already deeply identical
across the pair.

Other cross-checks:

- `total_file_count` (1477, full-only) has no distribution-level counterpart to conflict
  with: the crate states no per-sub-crate file count. `total_size_bytes` was removed in
  Phase 3, so no dataset-level size figure now disagrees with the part sizes.
- `dialect` (core-only) and `is_tabular` (both) are absent everywhere. The crate records
  mixed tabular and non-tabular formats and makes no dataset-level tabularity or dialect
  claim.
- `compression` absent in both; not asserted in the bundle.
- Identity, version, and access facts agree across every place they appear:
  `doi` = `version_access.latest_version_doi` = the DOI in `external_resources`
  (`https://doi.org/10.18130/V3/XNBOPG`); `version` "1.0 Beta" = both file
  collections/distributions = `version_access.versions_available`; `issued` 2026-04-03 =
  `distribution_dates.release_dates` = both collections' `issued`, and is consistent
  with the citation's "Harvard Dataverse, Apr. 2026".
- Only one release is documented, so no historical-versus-current release distinction
  arises. The `status` and `version_access` entries both record the same interim scope
  ("Interim release with partial data… No DICOM images are included."), consistent with
  `known_limitations` and `sampling_strategies`.

**Unresolved contradictions within or between the two records: none.**

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_d4d.yaml`
  (created Phase 1; `total_size_bytes` removed in Phase 3)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_d4d_core.yaml`
  (created Phase 2; unchanged in Phases 3–4)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_provenance.yaml` (live provenance record)

## Commands

```bash
FULL=data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_d4d.yaml
CORE=data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CHORUS_d4d_core.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset "$FULL"
poetry run linkml-term-validator validate-data "$FULL" \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset "$CORE"
poetry run linkml-term-validator validate-data "$CORE" \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency --full "$FULL" --core "$CORE"

poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | No issues found |
| Full — ontology term validation | Passed |
| Core — LinkML schema validation (`CoreDataset`) | No issues found |
| Core — ontology term validation | Passed |
| Pair consistency (final run, no `--sync-core`) | PASS; 76 schema-identical slots; projected slots = `['resources']` |
| Semantic review of related content | Completed above (`file_collections` ↔ `distributions`, 2/2 matched) |
| Prior-D4D factual reuse | None |

Top-level populated slots: full 62, core 55.
Full-only: `citation`, `direct_collection`, `file_collections`, `participant_privacy`,
`relationships`, `splits`, `third_party_sharing`, `total_file_count`.
Core-only: `distributions`. These counts are informational metadata, not a quality gate.
