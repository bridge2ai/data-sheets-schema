# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep3

Run label: `2026-07-28_claude-opus-5-deprimed_rep3`
Arm: BASELINE (input documents only)
Runtime: Claude Code · Provider: Anthropic · Model: `claude-opus-5[1m]` · Temperature 0.0
Mode: four-phase project agent, de-primed

Files:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d_core.yaml`

Declared factual inputs:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 documents, 5,750 lines)
- `data/preprocessed/source_manifest.yaml` (provenance only)

Structural authority:

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset`
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset`

---

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record was read, opened, grepped, or cited at any phase. The only
directory listing performed against `data/d4d_concatenated/` was of directory *names*, to confirm
that the target version directory did not already exist; no file contents were read. Phase 2 read
exactly one generated YAML file, the same-run Phase 1 full record at the path containing the run's
verbatim version label. No evaluation report, reconciliation report, test fixture, schema example,
or `d4d:docExample` value supplied a fact.

Record structure was derived at runtime from the two LinkML schemas via `SchemaView`
(`induced_class`), including inherited slots, ranges, cardinality, inlining behaviour, and enum
permissible values. Three structural facts were established empirically rather than assumed and
changed the emitted shape:

- `Creator.principal_investigator`, `Creator`/`EthicalReview` organization slots of range
  `Person`/`Organization`/`Grantor`, and `FundingMechanism.grantor` are **not** inlined (their
  ranges carry a required identifier), so they take reference strings, not nested objects.
- `Instance.sampling_strategies` and `Instance.missing_information` are multivalued and therefore
  take lists.
- `FormatDialect` does not inherit `NamedThing`; it admits only `comment_prefix`, `delimiter`,
  `double_quote`, `header`, `quote_char`.

`data_topic` and `data_substrate` (`Instance`) draw from the `B2AI_TOPIC` and `B2AI_SUBSTRATE`
vocabularies. The bundle contains no verified terms from either vocabulary, so both slots were
omitted rather than populated with guessed CURIEs.

### Source-disagreement resolution

The bundle covers two distinct PhysioNet projects under separate protocols. They are represented
as two `resources` entries, never merged: the adult release (`10.13026/8xbn-nq66`, v3.1.0, 833
participants, five North American sites, Bridge2AI-Voice app) and the pediatric release
(`10.13026/h995-bt35`, v1.1.0, 300 participants aged 2–18, 23,533 derived recordings, SickKids,
reproschema-ui, SickKids REB). Slots that would have forced a merge were deliberately left empty
at the top level and carried per resource instead: `doi`, `version`, `download_url`, and
`VersionAccess.latest_version_doi` (single-valued, and the two projects have different values).
`issued` (2026-05-01) and `license` (Bridge2AI Voice Registered Access License) are set at the top
level because both current releases agree.

| # | Disagreement | Resolution |
|---|---|---|
| 1 | Enrollment target: current documentation says a flagship dataset of 10,000 voices and "Enrollment Count (Anticipated by 2027): 10,000"; the IRB protocol and the 2024 audiomics white paper say 30,000 participants. | **Corrected in Phase 3.** Both figures are now recorded with their dates and scopes in `sampling_strategies[0].strategies`, noting that released data is far smaller than either target. |
| 2 | Update cadence and extension mechanism: "semi-annual", "new versions … on the Health Data Nexus platform", "publish a derivative dataset on the Health Data Nexus" — statements scoped to the Health Data Nexus distribution, while the current releases are versioned PhysioNet projects. | **Corrected in Phase 3.** `updates.update_details` and `extension_mechanism.extension_details` had generalised "the publishing platform"; they now name Health Data Nexus explicitly and note that the current releases are separate versioned PhysioNet projects. |
| 3 | Adult access policy: v1.1 is "Restricted Access — only registered users who sign the specified data use agreement"; v3.0.0/v3.1.0 are "Credentialed Access — only credentialed users who sign the DUA". | Both retained as an explicit historical transition in `version_access.version_details`; `resources[0].status` states only the current credentialed-access policy. |
| 4 | Hosting/maintenance: the documentation's healthsheet section says the dataset is hosted by the Health Data Nexus (T-CAIREM, University of Toronto); the current releases are on PhysioNet, maintained by the MIT Laboratory for Computational Physiology. | Both retained as separate `maintainers` entries; the Health Data Nexus entry states explicitly that it describes the Health Data Nexus release rather than the current PhysioNet releases. |
| 5 | Recording sites: documentation says "There are five recording sites included in the dataset"; the IRB protocol describes 11 other participating institutions and lists 12 collaborators. | No contradiction — different scopes. Five sites are asserted as sites *represented in the released data*; the larger institution list appears only as participating/planned institutions in creator and sampling context. |
| 6 | Name spelling: the project documentation lists "Jennifer Sui, MD (Hospital for Sick Children)"; the current PhysioNet author lists give "Jennifer Siu" (3 occurrences). | "Siu" retained, following the current, more authoritative dataset-authorship source. |
| 7 | Grant identifiers: the documentation footer and healthsheet contain OCR-garbled variants ("Award #3Tf-OTOD03272001S2", "3TF-OT2ActfOD032720Projectf01S1"). | Garbled variants not carried. Only the clean identifiers stated by NIH RePORTER and the PhysioNet acknowledgements are recorded: `OT2OD032720`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3`, `1OT2OD032720-01`. |
| 8 | Participant compensation: the released-dataset documentation reports $40/$80 gift cards to a $120 maximum; the app feasibility publication states participants received no financial incentives. | Both retained. The feasibility-study statement is explicitly scoped as such in `participant_compensation[0].compensation_rationale`. |
| 9 | Recording counts: documentation reports "~61,937 voice-derived recordings" for version 3.0, while v3.1.0 per-file element counts range from 28,640 to 32,522. | Retained with explicit historical scope: the 61,937 figure is labelled as the documentation's figure for v3.0, and the v3.1.0 per-file counts are enumerated in the same `Instance.description`. |
| 10 | Feasibility-study metrics (47 participants, 68% task completion, 41% acoustic success) describe the collection application, not the released dataset. | Retained in `known_limitations` with an explicit scope statement that it concerns the 2023 USF pilot of the app and that no audio was collected at that stage. |

### Values deliberately not asserted

- `is_tabular` — the release mixes tensor Parquet features with tabular TSV phenotype files; neither
  boolean is supported. Omitted from **both** records (presence is therefore consistent).
- `compression`, `total_file_count`, `total_size_bytes`, `CoreDistribution.bytes/md5/sha256/hash` —
  the bundle states no archive compression, no aggregate file count or size, and no checksums.
- `ExternalResource.archival` — the source answers "NA", which is not a boolean.
- `imputation_protocols`, `annotation_analyses` — no supporting evidence in the bundle.
- The Data Transfer and Use Agreement in the bundle is stamped "Approved for use through
  August 31, 2025", i.e. the captured template predates the current releases. Its terms are
  recorded as DTUA terms and attributed to that agreement, not asserted as current PhysioNet
  access terms.

### Internal consistency checks (each file)

Repeated identifiers, versions, dates, counts, licenses, access rules, people and organizations
were checked for internal agreement within each file:

- DOIs `10.13026/8xbn-nq66`, `10.13026/37yb-1t42`, `10.13026/h995-bt35`, `10.13026/mf9s-5r03`
  agree across `citation`, `version_access.version_details` and `resources`.
- Synapse identifiers `syn72370534` (adult) and `syn73617068` (pediatric) agree across
  `raw_data_sources`, `raw_sources`, `distribution_formats`, `file_collections` (full) /
  `distributions` (core), and `resources`.
- Counts 833 / 300 / 23,533 agree across `description`, `instances`, and `resources`.
- Publication date 2026-05-01 agrees across top-level `issued`, both `resources.issued`,
  `distribution_dates`, and `version_access.versions_available`.
- The single license string agrees across top level, both resources, and `license_and_use_terms`.

### Phase 2 discoveries back-ported to full

Three corrections were made to the **full** record first (items 1 and 2 of the disagreement
table), and the core record was regenerated from the corrected full record afterwards. No fact was
introduced into core that is absent from both the full record and the source bundle.

### Phase 3 validation

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Result: `No issues found` and `✅ Validation passed` for both files, before and after the Phase 3
corrections.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot inventory

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with `SchemaView`; no
hand-written field list was used.

- `Dataset` induced slots: 94. `CoreDataset` induced slots: 79.
- Populated top-level slots shared by both classes and present in both records: **63**
  (62 schema-identical + 1 projected).
- Deterministic validator report: **76 schema-identical slots**, all consistent.
- Full-only populated slots (absent from `CoreDataset`, correctly omitted from core): 14 —
  `citation`, `subsets`, `relationships`, `splits`, `direct_collection`,
  `collection_notifications`, `collection_consents`, `consent_revocations`, `participant_privacy`,
  `participant_compensation`, `third_party_sharing`, `variables`, `related_datasets`,
  `file_collections`.
- Core-only slots (absent from `Dataset`): 2 — `distributions`, `dialect`. Both are populated
  from the source bundle, not invented, and are reviewed as related content below.

### Schema-identical slot identity

Every schema-identical shared slot is present in both records or absent from both, and its parsed
YAML value is deeply identical including every nested mapping value and list item in order. This
was enforced structurally: the core record was generated by copying shared-slot values verbatim
from the Phase 3-audited full record, so no narrative field was condensed, paraphrased, reordered,
or truncated for brevity. Verified: 62 of 62 non-projected shared slots compare equal under parsed
`==`; the non-identical set is empty.

`--sync-core` was **not** required and was not run: the pair was already consistent on first
independent check.

### Projected slot: `resources`

`resources` has range `Dataset` in full and `CoreDataset` in core.

- Coverage is equal: 2 resources in each, matched by `id`
  (`https://doi.org/10.13026/8xbn-nq66`, `https://doi.org/10.13026/h995-bt35`).
- Every nested schema-identical slot is deeply identical between the full and core projections.
- Full-only nested slots dropped from the core projection: **none**. Every slot used on the two
  full resource entries (`id`, `name`, `title`, `version`, `doi`, `issued`, `download_url`, `page`,
  `publisher`, `license`, `language`, `conforms_to`, `keywords`, `status`, `description`) is
  permitted on `CoreDataset`, so the projection is total rather than lossy.

### Related, non-identical content: `file_collections` → `distributions`

The deterministic validator matched 2 of 9 core distributions and flagged the remaining 7 for
semantic review. That review was performed; the mapping is one-to-many, since the full record
groups files by release folder while core enumerates individual distribution artefacts.

| Full `file_collections` entry | Core `distributions` entries | Review |
|---|---|---|
| `filecollection:adult-v3-1-0-features` (path `features/`) | `distribution:adult-v3-1-0-parquet-features`, `…-static-features-tsv`, `…-audio-quality-tsv`, `…-data-dictionaries` | Consistent. Paths refine, never contradict: `features/` → `features/static_features.tsv`, `features/audio_quality_metrics.tsv`. |
| `filecollection:adult-v3-1-0-phenotype` (path `phenotype/`) | `distribution:adult-v3-1-0-phenotype-tsv` (deterministic match) | Consistent; same path, same release scope. |
| `filecollection:adult-v3-1-0-metadata` (path `metadata/`) | `distribution:adult-v3-1-0-recording-metadata` (deterministic match) | Consistent; same path, same Parquet-plus-dictionary description. |
| `filecollection:pediatric-v1-1-0-features` (path `features/`) | `distribution:pediatric-v1-1-0-parquet-features`, `…-plain-text-features` | Consistent; the 23,533 / 23,532 element counts agree with the full record and with `instances`. |
| `filecollection:raw-audio-bids` | `distribution:raw-audio-wav` | Consistent; both state the BIDS layout, WAV-plus-JSON-sidecar naming, and controlled-access-via-Synapse scope. |

Field-level checks across the mapping:

- **Names and descriptions** — no conflicting claims; core descriptions are drawn from the same
  source sentences as the full descriptions.
- **Paths** — every core path is either identical to, or a strict refinement of, the corresponding
  full `path`.
- **Formats** — `FormatEnum` has no Parquet member, so `format` is left unset on the Parquet
  distributions and Parquet is named in prose, matching the full record. `TSV` and `JSON` are set
  only where the sources say tab-delimited or JSON data dictionary. No conflict with any full
  assertion.
- **Compression** — unset in both; the bundle asserts no archive compression.
- **Checksums and byte counts** — unset in both; the bundle contains none. No `total_file_count`
  or `total_size_bytes` in full to compare against, so there is no scope mismatch to resolve.
- **Access URLs** — carried on full `file_collections.download_url`; `CoreDistribution` has no URL
  slot, so no conflict is possible. The same URLs appear in core via `distribution_formats`
  (schema-identical, deeply identical) and `resources.download_url`.
- **Release scope** — every entry on both sides is labelled adult v3.1.0, pediatric v1.1.0, or
  controlled-access raw audio; no entry mixes releases.

### Related content: `dialect` and `is_tabular`

`dialect` is core-only (`delimiter: "\t"`, `header: "true"`), supported directly by the sources'
`pd.read_csv(..., sep="\t", header=0)` usage examples and by the "tab delimited file" description.
It agrees with the core `distributions` entries typed `TSV` / `text/tab-separated-values` and with
the full record's statement in `intended_uses.usage_notes` that phenotype files are tab-delimited.
`is_tabular` is absent from both records, so presence is consistent and there is nothing to
contradict.

### Top-level identity/version/access agreement

Top-level identity, version and access facts were checked against `resources`, the version
history, the distribution entries and repeated statements: all agree (see the internal consistency
checks above). Historical releases (Health Data Nexus v1.0, adult v1.1/v2.0/v2.0.1/v3.0.0,
pediatric v1.0.0) are labelled as historical wherever they appear and are never treated as
contradicting the current v3.1.0 / v1.1.0 values.

### Phase 4 commands and results

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/VOICE_d4d_core.yaml
```

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: Phase 4 must
  semantically review related distribution content; deterministic matches=2,
  unmatched core distributions=[0, 1, 2, 4, 6, 7, 8]
```

The single warning marks related content requiring the semantic review recorded in the table
above. That review found **zero contradictions**. Schema and term validation were re-run for both
records after the final core regeneration; both pass.

---

## Outcome

- Both records pass schema validation and ontology term validation.
- Every emitted structure is permitted by its applicable schema, derived from `SchemaView` at
  runtime.
- 62 of 62 schema-identical shared slots are deeply identical with identical presence;
  the deterministic validator reports 76 schema-identical slots consistent.
- The one projected slot (`resources`) has equal coverage, id-matched entries, deep identity on
  every projected slot, and no dropped full-only nested slots.
- All related content (`file_collections` ↔ `distributions`, `dialect`, `is_tabular`) was mapped
  and reviewed; zero unresolved contradictions within or between the two records.
- Phase 3 made three source-driven corrections to the full record; no divergence between full and
  core survived into Phase 4, and `--sync-core` was never needed.
- No prior-run D4D record, evaluation, or report was read or used at any phase.

Informational metadata (not a quality gate): full 77 top-level slots / 607 populated slots
including nested; core 65 top-level slots / 527 populated slots including nested.
