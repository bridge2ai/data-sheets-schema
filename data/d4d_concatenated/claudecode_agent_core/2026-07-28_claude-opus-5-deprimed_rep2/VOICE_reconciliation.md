# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep2

Run label: `2026-07-28_claude-opus-5-deprimed_rep2`
Arm: BASELINE (input documents only)
Mode: four-phase project agent, de-primed
Runtime / provider / model: Claude Code / Anthropic / `claude-opus-5[1m]`
Temperature: 0.0

Files:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml`

---

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual inputs read during this run, in full:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 source documents)
- `data/preprocessed/source_manifest.yaml` (provenance only)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (structure only)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (structure only)
- the same-run Phase 1 full record, as the Phase 2 starting point

No prior full or core D4D record, from any arm, label or date, was opened, grepped or
cited. One directory listing of `data/d4d_concatenated/claudecode_agent/` was taken to
confirm that the assigned version label did not collide with an existing directory; only
directory names were observed and no file under `data/d4d_concatenated/` was read. No
evaluation report, reconciliation report, test fixture or schema example supplied any
factual value. Every populated slot traces to the declared bundle.

### Cohort scoping

The bundle covers two distinct PhysioNet projects under separate ethics approvals, and
the record keeps them separate throughout rather than merging them:

- adult `b2ai-voice` v3.1.0, DOI `10.13026/8xbn-nq66`, published 2026-05-01, 833
  participants across five North American sites;
- pediatric `b2ai-voice-pediatric` v1.1.0, DOI `10.13026/h995-bt35`, published
  2026-05-01, 300 participants aged 2-18, 23,533 derived recordings, recruited at the
  Hospital for Sick Children.

Both appear as separate entries under `resources`, with separate `file_collections` /
`distributions`, separate ethics approvals under `ethical_reviews` (USF single IRB for
the adult cohort, SickKids Research Ethics Board for the pediatric cohort), separate
release-date lists, separate raw-audio Synapse endpoints (`syn72370534` /
`syn73617068`), and an explicit statement in `related_datasets` and in the pediatric
resource description that the pediatric release is a separate project rather than a
version of the adult dataset. No participant count, recording count, DOI, version, or
ethics approval was pooled across the two cohorts.

### Source disagreements resolved

| Item | Divergent sources | Resolution |
|---|---|---|
| Hosting platform | The healthsheet in `docs_b2ai-voice_org` says the dataset is distributed and hosted by Health Data Nexus; the PhysioNet 3.1.0 / pediatric 1.1.0 pages are the current releases | Current releases recorded as PhysioNet. Health Data Nexus retained only with explicit historical scope in `distribution_formats` ("earlier version of the feature-only dataset") and `maintainers` ("This describes the earlier feature-only release; current releases are distributed on PhysioNet") |
| Enrolment target | Docs overview and study metadata: 10,000 voices, anticipated enrolment 10,000 by 2027. Audiomics white paper (2024) and IRB protocol: 30,000 | 10,000 recorded (`purposes`, `sampling_strategies`), from the current dataset-facing documentation. The 30,000 figure was not asserted |
| Access label | Docs: "Registered Access", "Credentialed users must be approved and sign DUA". PhysioNet 3.0.0/3.1.0/pediatric 1.1.0: "Credentialed Access", "Only credentialed users who sign the DUA can access the files". PhysioNet v1.1: "Restricted Access", "Only registered users who sign the specified data use agreement" | Both recorded without conflation in `license_and_use_terms`: current releases are credentialed access; the v1.1 restricted/registered wording is carried with explicit version scope. The licence name itself is "Bridge2AI Voice Registered Access License" on every release |
| Number of sites | Dataset: "There are five recording sites included in the dataset" / "five sites in North America". IRB protocol: 11 academic sites planned | Five recorded as the dataset fact (`known_biases`); 11 recorded only as protocol scope inside `collection_timeframes` |
| Language | Docs: only language option is English, Spanish under development, "Does not read or speak English" is an exclusion criterion. IRB protocol V11 (2025-02-10): inclusion criteria read "Speaking the English or Spanish language" | Recorded as a single reconciled statement in `known_limitations`: protocol scope has widened to Spanish while the released data remains English-only |
| Grant identifiers | Clean forms `OT2OD032720`, `3OT2OD032720-01S3`, `3OT2OD032720-01S1`. Corrupted extraction strings also appear in the bundle (`3Tf-OTOD03272001S2` in the docs footer, `3TF-OT2ActfOD032720Projectf01S1` in the healthsheet) | Only the three clean forms recorded, each attributed to the source that carries it. Corrupted strings excluded as extraction artefacts |
| Project contact address | The docs page renders the project contact address as a redacted `[email protected]` placeholder; `DACO@b2ai-voice.org` is recoverable from PhysioNet | No project contact address invented. `maintainers` refers to "the Bridge2AI-Voice project contact address published in the dataset documentation"; `DACO@b2ai-voice.org` is recorded where the bundle states it |

### Historical values retained with explicit scope

- v1.0: 12,523 recordings, 306 participants, Health Data Nexus DOI `10.57764/qb6h-em84`
- v2.0 added 136 participants; v3.0.0 added 391 participants
- v3.0 described in the docs as ~61,937 voice-derived recordings from 833 participants
- Adult v1.1 files "no longer available"
- App feasibility study (USF IRB 004890, 47 participants, 5 June – 28 July 2023),
  recorded in `ethical_reviews` with an explicit note that audio data was not collected
  at that stage of app development, so it contributed no recordings to the dataset
- Health Data Nexus hosting and the end-of-November-2024 publication date

### Corrections applied in Phase 3

All four corrections were made to the full record first; the core record was then
regenerated from the corrected full record.

1. `collection_timeframes` — replaced a paraphrase ("across eleven participating academic
   sites") with the protocol's own wording: "involving 11 different academic sites across
   the US, with the potential of adding extra data collection sites in phases 3-4". The
   bundle contains both "11 different academic sites across the US" and "USF and 11 other
   participating institutions"; the record now follows the first without arithmetic of its
   own.
2. `version_access.version_details` — softened "Both PhysioNet projects carry
   RRID:SCR_007345" to "The PhysioNet citations for both projects include
   RRID:SCR_007345", since the RRID appears in the citation strings as PhysioNet's
   resource RRID.
3. `known_limitations` (language) — added the IRB protocol's "English or Spanish"
   inclusion criterion and the V11 revision note, with the reconciliation between protocol
   scope and released-data scope stated explicitly. `scope_impact` narrowed from "the
   dataset" to "the released data".
4. `file_collections[d4d:VOICE-pediatric-1-1-0-features]` — removed `file_count: 9`. Nine
   is the count of Parquet feature files, not of files in the collection, which also holds
   `static_features.tsv`, `audio_quality_metrics.tsv` and JSON data dictionaries. The
   nine-Parquet statement was moved into the description.

No Phase 2 discovery required a back-port beyond these, because the core record was built
as a strict schema projection of the audited full record rather than as an independent
extraction.

### Internal consistency checks

- Adult participant count 833 is identical in the top-level `instances`, in the adult
  resource, and in every narrative mention; it matches the v3.0.0 abstract, the v3.1.0
  abstract, the docs overview and the healthsheet.
- Pediatric 300 participants / 23,533 recordings appear only in pediatric-scoped slots.
- Version/date/DOI triples are internally consistent across `resources`,
  `distribution_dates`, `version_access.versions_available` and `errata`.
- The `errata` release notes for v3.1.0 and the adult resource description carry the same
  change list.
- Licence string "Bridge2AI Voice Registered Access License" is identical at top level, on
  both resources, and on all six PhysioNet-hosted file collections / distributions.
- No unresolved contradiction was found within either file.

### Validation re-run after corrections

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four: pass.

---

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with LinkML `SchemaView`, no hand-written field list.

- `Dataset` induced slots: 94
- `CoreDataset` induced slots: 79
- Schema-identical shared slots: **77** (`resources` is the one projected slot, ranging
  over `Dataset` in full and `CoreDataset` in core)
- Populated in full: **76** of 94
- Populated in core: **64** of 79

### Deterministic check

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml
```

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=8, unmatched core distributions=[]
```

`--sync-core` was **not** needed and was not run. The core record was generated as a
deterministic schema projection of the Phase 3-audited full record — shared slots were
copied byte-for-byte rather than rewritten — so every schema-identical slot was already
deeply identical on first check, including all narrative fields. Nothing in core was
condensed, paraphrased, reordered or omitted relative to full.

### Presence parity

Full-only populated slots (absent from the `CoreDataset` schema, correctly omitted from
core): `citation`, `collection_consents`, `collection_notifications`,
`consent_revocations`, `direct_collection`, `file_collections`,
`participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
`splits`, `subsets`, `third_party_sharing`, `variables`.

Core-only populated slots (absent from the `Dataset` schema): `distributions`, `dialect`.

Every other populated slot is present in both files. No slot is populated in one file and
schema-available-but-empty in the other.

### Projected slot: `resources`

Matched by `id`, equal coverage, both files:

| id | full | core |
|---|---|---|
| `https://doi.org/10.13026/8xbn-nq66` (adult v3.1.0) | present | present |
| `https://doi.org/10.13026/h995-bt35` (pediatric v1.1.0) | present | present |

Every nested schema-identical slot on both resources — `name`, `title`, `description`,
`version`, `doi`, `download_url`, `publisher`, `license`, `page`, `language`, `keywords`,
`instances` — is deeply identical, including list order. The two full-only nested slots,
`citation` and `related_datasets`, are omitted from the core projection as required; no
other nested content differs.

### Semantic review: `file_collections` ↔ `distributions`

The validator's warning marks this pair as requiring review; the review below was
performed and is the evidence, not the warning.

All 8 members match 1:1 by `id` and `name`, with no unmatched entries on either side:

| id | full `path` | core `path` | reviewed |
|---|---|---|---|
| `d4d:VOICE-adult-3-1-0-features` | `features/` | `features/` | no conflict |
| `d4d:VOICE-adult-3-1-0-phenotype` | `phenotype/` | `phenotype/` | no conflict |
| `d4d:VOICE-adult-3-1-0-metadata` | `metadata/` | `metadata/` | no conflict |
| `d4d:VOICE-pediatric-1-1-0-features` | `features/` | `features/` | no conflict |
| `d4d:VOICE-pediatric-1-1-0-phenotype` | `phenotype/` | `phenotype/` | no conflict |
| `d4d:VOICE-pediatric-1-1-0-metadata` | `metadata/` | `metadata/` | no conflict |
| `d4d:VOICE-adult-raw-audio` | — | — | no conflict |
| `d4d:VOICE-pediatric-raw-audio` | — | — | no conflict |

Field-by-field review of the related, non-identical representations:

- **Names and paths**: identical strings on both sides for all eight.
- **Descriptions**: core descriptions are the full descriptions plus a trailing sentence
  carrying the access URL and licence, which `CoreDistribution` has no dedicated slots for
  (`download_url`, `license` and `version` exist on `FileCollection` but not on
  `CoreDistribution`). Nothing was dropped and no assertion differs.
- **Formats**: `format` / `media_type` are set only on the two phenotype distributions
  (`TSV`, `text/tab-separated-values`), which the bundle supports directly ("phenotype.tsv
  — a tab delimited file", `pd.read_csv("demographics.tsv", sep="\t", header=0)`). The
  feature, metadata and raw-audio collections mix Parquet binaries, plain-text tables and
  JSON dictionaries, so no single `FormatEnum` value applies; `format` is left absent and
  the mixture is stated in the description. `FormatEnum` has no Parquet member, so no
  value was forced. This does not conflict with full, which carries no format assertion.
- **Compression**: absent in both files at every level. No conflict.
- **Checksums and byte counts**: `hash`, `md5`, `sha256` and `bytes` are absent from every
  distribution because the bundle publishes none; `total_bytes` is likewise absent from
  every file collection. No conflict.
- **File and size counts**: `total_file_count` and `total_size_bytes` are absent from full,
  and no distribution asserts a size. `file_count` is absent everywhere after the Phase 3
  correction. Scope-matched, so no full-vs-core count comparison is possible or needed.
- **Access URLs**: full carries `download_url` per collection; core carries the same URLs
  inside the distribution descriptions. Every pair agrees:
  `https://physionet.org/content/b2ai-voice/3.1.0/` for the three adult collections,
  `https://physionet.org/content/b2ai-voice-pediatric/1.1.0/` for the three pediatric
  collections, `syn72370534` and `syn73617068` for the two raw-audio collections. These
  also agree with `distribution_formats.access_urls` and with each resource's
  `download_url`.
- **Release scope**: each adult collection carries `version: 3.1.0` and each pediatric
  collection `version: 1.1.0` in full; the core descriptions name the same versions. No
  collection mixes releases.
- **`is_tabular` / `dialect`**: `is_tabular` is absent from both files, since the releases
  mix dense tensor Parquet with tabular TSV and a single boolean would misrepresent them.
  Core's `dialect` (tab delimiter, header present, `"` quote char) describes only the
  plain-text tables and is consistent with the two `TSV` distributions and with the
  absence of an `is_tabular` claim in full.

### Top-level identity, version and access cross-check

- Top-level `id`, `name`, `title`, `description`, `license`, `page`, `publisher`,
  `language`, `conforms_to` and `keywords` are byte-identical between full and core.
- Top-level `license` agrees with both resources' `license`, with all six PhysioNet
  file collections / distributions, and with `license_and_use_terms.license_terms`.
- No top-level `version` or `doi` is asserted, because the record covers two concurrently
  current releases with distinct versions and DOIs; versions and DOIs live on the
  resources, in `version_access.versions_available` and in `distribution_dates`. This is
  identical in both files.
- `version_access.latest_version_doi` carries the adult latest-version DOI
  `10.13026/37yb-1t42` and states in `version_details` that it is the adult project's DOI,
  naming the pediatric latest-version DOI `10.13026/mf9s-5r03` alongside it — the slot is
  single-valued, so the scope is made explicit rather than left ambiguous. Identical in
  both files.
- Access facts agree across `license_and_use_terms`, `regulatory_restrictions`,
  `raw_sources`, `raw_data_sources`, `distribution_formats` and the raw-audio collections:
  featurised data is credentialed access on PhysioNet under a signed DUA; raw audio is
  controlled access via Synapse after DACO review and institutional sign-off.
- Historical releases are distinguished from current releases everywhere they appear
  (v1.0/v1.1/v2.0/v2.0.1/v3.0.0 adult, v1.0.0 pediatric, Health Data Nexus hosting), so no
  differing historical value is treated as a contradiction.

### Result

Phase 4 passes. 77 schema-identical shared slots, 76 populated and deeply identical in
both files; 1 projected slot (`resources`) with equal coverage and deep identity on every
nested schema-identical slot; 1 related-content pair (`file_collections` ↔
`distributions`) mapped 1:1 and semantically reviewed with zero contradictions. No
`--sync-core` write was required.

### Files changed in Phases 3 and 4

- `VOICE_d4d.yaml` — four Phase 3 corrections listed above.
- `VOICE_d4d_core.yaml` — regenerated from the corrected full record; no independent edit.
- `VOICE_reconciliation.md` — this report.

### Final status

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | pass |
| `linkml-term-validator` full | pass |
| `linkml-validate` core (`CoreDataset`) | pass |
| `linkml-term-validator` core | pass |
| `d4d_pair_consistency` (no `--sync-core`) | PASS, 76 schema-identical slots |
| Prior-D4D reuse | none |
| Full populated slots | 76 / 94 |
| Core populated slots | 64 / 79 |
| Full line count (informational) | 2,303 |
| Core line count (informational) | 1,711 |
