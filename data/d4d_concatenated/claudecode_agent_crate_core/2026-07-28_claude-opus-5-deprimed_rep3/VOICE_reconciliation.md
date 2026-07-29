# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep3

Arm: DE NOVO WITH CRATE (documents + RO-Crate evidence)
Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5[1m] · Temperature 0.0
Mode: four-phase project agent, de-primed

Files:

- Full: `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d_core.yaml`
- Provenance: `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_provenance.yaml`

Declared factual inputs (the only ones used):

- `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt`
- `data/preprocessed/source_manifest.yaml` (provenance only)
- `data/ro-crate_packages/crate_manifest.yaml` (provenance only)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, `..._core_all.yaml` (structure only)

---

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped or cited. Nothing under
`data/d4d_concatenated/` was consulted except the exact same-run full record read by Phase 2, and
no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened. The
only crate content used was the `VOICE_crate_metadata_reduced.json` and `ai_ready_score.json`
blocks embedded in the declared bundle; the upstream `ro-crate-datasheet.html` is withheld from the
bundle by design and was not sought elsewhere. Record structure was derived at runtime from
`Dataset` and `CoreDataset` with LinkML `SchemaView`, not from any example record.

### Structural findings resolved during Phase 1

Five single-valued object slots (`principal_investigator`, `grantor`, `reviewing_organization`,
`contact_person`, `governance_committee_contact`) are non-inlined references in the schema and take
an identifier string, not a nested object. They were emitted as identifiers, and the descriptive
content that would otherwise have been lost (name, degrees, role, address, affiliation) was moved
into the enclosing object's `description`. `DatasetBias` has `mitigation_strategy` but no
`recommended_mitigation`; two bias entries were corrected accordingly.

### Quantitative claims verified against the bundle

Adult participants 833; pediatric participants 300 (aged 2–18) with 23,533 recordings; v1.0
12,523 recordings / 306 participants; ~61,937 voice-derived recordings for v3.0; per-feature
recording counts for v3.0.0 (ppgs 29,031; SPARC EMA/loudness 31,616; SPARC periodicity/pitch
31,633; torchaudio spectrogram/mel/MFCC 29,020; torchaudio pitch 32,236) and for v3.1.0 (29,278 /
32,522 / 28,640 / 31,855 / 31,872 / 29,289); 22 acoustic tasks; five recording sites; total content
size 12.9 GB; award amount 4,660,942; project 2022-09-01 to 2026-11-30; feasibility study n=47,
USF IRB 004890, 2023-06-05 to 2023-07-28; static features 135 columns; confounders 547 columns;
eligibility 42 columns; enrollment form 28 columns; b2aiprep 3.0.2, FAIRSCAPE 1.0.24; 15 documented
data files, 55 schemas, 2 computations, 1 software, 117 authors. All DOIs verified verbatim:
`10.13026/8xbn-nq66` (adult 3.1.0), `10.13026/k81f-qr68` (adult 3.0.0), `10.13026/249v-w155`
(adult 1.1), `10.13026/37yb-1t42` (adult latest), `10.13026/h995-bt35` (pediatric 1.1.0),
`10.13026/mf9s-5r03` (pediatric latest), `10.57764/qb6h-em84` (Health Data Nexus v1.0). Every
file size and SHA-256 in `file_collections` / `distributions` was copied from the crate graph.

### Internal defects found in the crate evidence, and how they were resolved

1. `ark:59853/b2ai-voice-dataset-feature-sparc-periodicity` carries `name: "sparc_loudness.parquet"`
   while its `contentUrl` is `file:///features/sparc_periodicity.parquet` and its schema is the
   SPARC Periodicity Schema. Resolved in favour of `contentUrl` and the PhysioNet file listing:
   recorded as `sparc_periodicity.parquet`.
2. `ark:59853/b2ai-voice-dataset-feature-torchaudio-pitch` carries
   `name: "torchaudio_spectrogram.parquet"` while its `contentUrl` is
   `file:///features/torchaudio_pitch.parquet` and its schema is the Torchaudio Pitch Schema.
   Resolved the same way: recorded as `torchaudio_pitch.parquet`.
3. `ark:59853/b2ai-voice-dataset-phenotype-task` carries `name: "VOICE Questionnaire Tables"`,
   duplicating the questionnaire entity, while its generated contents are the task and session
   tables. Recorded as "VOICE Task Tables" after the file inventory.
4. The graph contains two entities with `@id ark:59853/b2ai-voice-schema-phenotype-confounders`,
   named "Phenotype Confounders Schema" and "Phenotype Demographics Schema", carrying identical
   547-column property blocks. Neither the duplicate id nor the demographics column list was
   asserted; the demographics distribution is described without a column count.
5. Auto-generated schema stubs record `"separator": ","` for files that are tab-separated
   (`.tsv` extension, `format: text/tab-separated-values`, and PhysioNet usage notes showing
   `pd.read_csv(..., sep="\t")`). Because the release is mixed-format (Parquet tensors plus TSV
   tables) and the crate's separator field contradicts the file format, the core-only `dialect`
   slot was left absent rather than asserting a single dialect for the dataset.
6. `ark:59853/b2ai-voice-dataset-feature-ppgs` uses the key `size` where every other file entity
   uses `contentSize`; both are byte counts and were read as such. `sparc_pitch` carries
   `datePublished 08/18/2025` (the v2.0.1 date) while the crate root and all other files carry
   `12/16/2025`; no per-file publication date was asserted.

### Cross-source disagreements resolved by scope, not by preference

- **Enrollment targets.** Project documentation states a flagship dataset of 10,000 voices and an
  anticipated enrollment of 10,000 by 2027; the IRB protocol states 30,000 participants overall
  with up to 5,000 per category; the audiomics viewpoint states 30,000 human voices; the RO-Crate
  states approximately 3,000 participants by November 2026. These are targets of different scope
  and date, not contradictions. Phase 3 back-ported all four into
  `collection_timeframes[0].timeframe_details`, each attributed to its source; no single top-level
  enrollment target is asserted.
- **Distribution platform.** The healthsheet block describes distribution through Health Data Nexus
  with publication "at the end of November, 2024", and gives a semi-annual update cadence. Current
  releases are on PhysioNet. The Health Data Nexus statements were retained only with explicit
  historical scope (`maintainers`, `related_datasets`, `distribution_dates`, `updates.frequency`),
  and PhysioNet is recorded as the current publisher.
- **Version scope of the study-metadata block.** Several documentation answers are explicitly scoped
  to v2.0.0 ("The current v.2.0.0 dataset contains only adult populations"; "The only language
  option for v2.0.0 is English"). These were not promoted to current-release facts; the
  adult/pediatric split and the English-only-with-Spanish-in-development position are recorded
  through `resources`, `known_biases` and `known_limitations` instead.
- **Grant identifier variants.** The bundle carries `OT2OD032720` (study metadata),
  `3OT2OD032720-01S3` (NIH RePORTER), `3OT2OD032720-01S1` (PhysioNet acknowledgements),
  `3Tf-OTOD03272001S2` (crate funder string and site footer) and `3TF-OT2ActfOD032720Projectf01S1`
  (healthsheet). The clean core project number `OT2OD032720` is used as `grant_number`; the
  RePORTER and PhysioNet supplement numbers are recorded in the grant description; the crate string
  is quoted verbatim as a quotation. The evidently corrupted healthsheet variant was not propagated.
- **Institution counts.** The IRB protocol says data will be collected at USF and 11 other
  participating institutions while its Annex C table lists eight named sites besides USF, and the
  documentation lists twelve collaborators. No single institution count is asserted; the
  documentation's collaborator list populates `creators[0].affiliations` and the IRB's per-site
  lead-investigator table is recorded verbatim under `data_collectors`.
- **Adult vs pediatric cohorts.** The manifest and both PhysioNet pages state these are distinct
  cohorts under separate protocols and separate ethics approvals (USF IRB vs SickKids REB), not
  versions of one another. They are represented as separate entries in `resources`, each with its
  own DOI, version, publication date, participant count and access terms; separate `instances`
  entries carry the two participant counts; `ethical_reviews` carries both bodies. No count,
  date or identifier is shared between them anywhere in either record.

### Corrections applied in Phase 3 (full first, then mirrored to core)

1. `external_resources[0].archival: false` removed. The healthsheet answers "NA" to whether official
   archival versions exist; "NA" is not evidence of `false`.
2. `conforms_to: Brain Imaging Data Structure (BIDS) v1.9.0` removed from the v3.1.0 resource. The
   BIDS statement appears in the project documentation as a statement about the dataset as a whole;
   the PhysioNet 3.1.0 page does not make it, so it is asserted only at the top level.
3. The four scoped enrollment targets added to `collection_timeframes[0].timeframe_details`
   (source-supported content the Phase 1 pass had omitted).

No Phase 2 discovery required a factual correction to the full record: because `CoreDataset` is a
strict subset of the `Dataset` slots used here (plus the core-only `distributions` and `dialect`),
Phase 2 surfaced no fact the source documents supported and the full record lacked.

### Judgement calls recorded explicitly

- `regulatory_restrictions.hipaa_compliant: compliant` is a mapping of "Does this dataset apply the
  HIPAA de-identification rules? Yes", combined with the HIPAA-compliant collection apps and
  HIPAA-protected storage, onto `ComplianceStatusEnum`. The bundle does not use the word
  "compliant" as a status label.
- `regulatory_restrictions.confidentiality_level: restricted` maps the crate's
  "Limited dataset available with Data Use Agreement" onto `ConfidentialityLevelEnum`.
- `license_and_use_terms.data_use_permission: [general_research_use]` maps the registered access
  agreement ("intended solely for commercial and non-commercial research purposes by Authorized
  Researchers") plus the five consent-restriction answers, all "No", onto `DataUsePermissionEnum`.
  No commercial-use, geographic, methods-development or genetic-research restriction was asserted,
  because the documentation explicitly denies each.
- `is_tabular` was left absent in both records: the release mixes dense Parquet tensors with TSV
  phenotype tables, so neither value is supported.
- `total_file_count` / `total_size_bytes` were left absent. The crate reports "12.9 GB" as prose and
  the AI-readiness score reports "11/17" files with checksums against 15 documented data files;
  summing the per-file byte counts would be derived arithmetic rather than a stated fact, so the
  12.9 GB figure is recorded in the v3.0.0 resource description instead.

---

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` from `Dataset` and `CoreDataset`.

**Schema-derived shared-slot count: 76 schema-identical slots; projected slots: `resources`.**

Result of the schema-derived validator, run without `--sync-core`:

```
PASS: 76 schema-identical slots; projected slots=['resources']
```

`--sync-core` was **not** needed and was not run: the core record was projected from the
Phase 3-audited full record programmatically, so every schema-identical slot was deeply identical
on first construction. Narrative fields were copied verbatim — nothing in core is condensed,
paraphrased, reordered or truncated relative to full.

### Presence parity

Thirteen full-record slots have no counterpart in `CoreDataset` and are therefore absent from core
by schema, not by omission: `citation`, `subsets`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`, `participant_privacy`,
`participant_compensation`, `third_party_sharing`, `related_datasets`, `variables`.

Fifteen `CoreDataset` slots are absent from core: `is_tabular`, `dialect`, `compression`,
`conforms_to_class`, `conforms_to_schema`, `created_by`, `created_on`, `doi`, `download_url`,
`issued`, `last_updated_on`, `modified_by`, `version`, `was_derived_from` — all absent from full as
well, so presence matches — plus `distributions`, which is core-only and is discussed below.

### Projected slot: `resources`

Four resources, matched by `id`, with equal coverage in both records:

| id | full slots | core slots | outcome |
|---|---|---|---|
| `https://doi.org/10.13026/8xbn-nq66` | 12 | 12 | deep identity |
| `https://doi.org/10.13026/k81f-qr68` | 13 (12 + `file_collections`) | 13 (12 + `distributions`) | deep identity on the 12 shared; `file_collections` is full-only |
| `https://doi.org/10.13026/h995-bt35` | 12 | 12 | deep identity |
| `https://doi.org/10.13026/249v-w155` | 12 | 12 | deep identity |

`file_collections` is not a `CoreDataset` slot and is therefore dropped from the core projection,
as the guard requires for full-only nested slots.

### Related, non-identical representation: `file_collections` → `distributions`

The 15 `FileCollection` objects on the v3.0.0 resource were mapped one-to-one onto 15
`CoreDistribution` objects on the same core resource, preserving scope (both hang off the
crate-packaged v3.0.0 release, not the top level). Field mapping and semantic review:

| full `FileCollection` | core `CoreDistribution` | check |
|---|---|---|
| `name` | `name` | identical string in all 15 |
| `description` | `description` | identical string in all 15 |
| `path` | `path` | identical string in all 15 |
| `total_bytes` | `bytes` | identical integer in all 11 that carry one; the four directory-level entries carry none in either record |
| SHA-256 stated inside `description` | `sha256` | the 64-hex digest extracted from the description matches the crate's `sha256` for all 11 files that have one |
| `collection_type: [processed_data]` | — | no `CoreDistribution` counterpart; not represented in core |
| `version: 3.0.0` | — | no `CoreDistribution` counterpart; the version is carried by the enclosing resource in both records |
| — | `format: TSV`, `media_type: text/tab-separated-values` | added for the six phenotype entries only, from the crate's `format: "text/tab-separated-values"`; omitted for the nine Parquet entries because neither enum has a Parquet value |
| `file_count: 1` | — | no `CoreDistribution` counterpart; each core distribution describes one file, so nothing is lost |

No contradiction: names, paths, byte counts, checksums and release scope agree between the two
representations, and the format/media-type values added on the core side are consistent with the
`.tsv` paths they annotate.

### Other cross-field semantic checks

- **Counts vs distributions.** `total_file_count` and `total_size_bytes` are absent from both
  records, so there is nothing to reconcile against the distribution-level byte counts. The
  distribution byte counts are per-file and do not purport to sum to the 12.9 GB figure quoted in
  the v3.0.0 description.
- **Formats and `is_tabular`.** `is_tabular` is absent from both; `dialect` is absent from core.
  The only format assertions are the six `format: TSV` / `media_type: text/tab-separated-values`
  pairs, which agree with each other and with the `.tsv` paths and directory contents they annotate.
- **Identity, version and access facts.** The top-level `license`
  ("Bridge2AI Voice Registered Access License"), `publisher` (`https://physionet.org/`) and
  `status` agree with the four resources, with `version_access.versions_available` and
  `version_access.latest_version_doi`, with `distribution_dates.release_dates` and with
  `license_and_use_terms.license_terms` in both records. The v3.0.0 resource's release-specific
  license URL `https://physionet.org/content/b2ai-voice/view-license/3.0.0/` is the same licence
  named at top level, recorded in the form the crate uses.
- **Historical vs current releases.** v1.1 (2025-01-17, 306 participants at v1.0) and Health Data
  Nexus v1.0 are marked as superseded/historical; v3.1.0 and pediatric v1.1.0 are the current
  releases. Their differing participant counts, DOIs and access policies are release-scoped and are
  not treated as contradictions.

### Final validation

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset .../VOICE_d4d.yaml                                  -> No issues found
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset .../VOICE_d4d_core.yaml                         -> No issues found
poetry run linkml-term-validator validate-data .../VOICE_d4d.yaml \
  --schema .../data_sheets_schema_all.yaml --target-class Dataset      -> Validation passed
poetry run linkml-term-validator validate-data .../VOICE_d4d_core.yaml \
  --schema .../data_sheets_schema_core_all.yaml --target-class CoreDataset -> Validation passed
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../VOICE_d4d.yaml --core .../VOICE_d4d_core.yaml
  -> PASS: 76 schema-identical slots; projected slots=['resources']
poetry run d4d provenance record --project VOICE --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt
  -> VOICE_provenance.yaml (record_mode: live)
```

### Files changed

- `VOICE_d4d.yaml` — created in Phase 1; three Phase 3 corrections applied (listed above).
- `VOICE_d4d_core.yaml` — created in Phase 2, regenerated after the Phase 3 corrections.
- `VOICE_reconciliation.md` — this report.
- `VOICE_provenance.yaml` — live provenance record, `record_mode: live`.

### Outcome

Zero unresolved contradictions within or between the two records. Full: 77 populated top-level
slots. Core: 64 populated top-level slots. Both pass schema and term validation; the pair passes the
schema-derived consistency check with no synchronization step required.
