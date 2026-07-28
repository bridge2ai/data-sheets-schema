# CHORUS full/core reconciliation — crate-only arm

- **Run label**: `2026-07-28_claude-opus-5-crateonly_rep2`
- **Agent runtime**: Claude Code
- **Provider**: Anthropic
- **Model**: claude-opus-5[1m]
- **Mode**: four-phase project agent, crate-only
- **Temperature**: 0.0
- **Generated**: 2026-07-28
- **Full**: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d.yaml` (910 lines)
- **Core**: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d_core.yaml` (804 lines)
- **Provenance**: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_provenance.yaml` (`record_mode: live`)

Line counts are informational metadata only, not a quality gate.

## Evidence boundary actually observed

The only factual input read in this run was:

```
data/preprocessed/concatenated/CHORUS_crate_only.txt
```

That bundle contains exactly two artifacts: `CHORUS_crate_metadata_reduced.json`
(crate JSON-LD with file inventories collapsed) and `ai_ready_score.json`.

Structure-only references read: `data_sheets_schema_all.yaml` (class `Dataset`),
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), and
`src/data_sheets_schema/d4d_pair_consistency.py`. Class shapes were resolved at
runtime with LinkML `SchemaView` rather than from any example record.

Nothing else was opened. Specifically **not** read: `CHORUS_preprocessed.txt`,
`CHORUS_preprocessed_with_crate.txt`, anything under
`data/preprocessed/individual/CHORUS/` or `data/raw/CHORUS/`,
`data/preprocessed/source_manifest.yaml`, the withheld crate artifacts
(`CHORUS_crate_d4d.yaml`, `CHORUS_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
`ro-crate-datasheet.html`), any file under `data/d4d_concatenated/` or
`data/d4d_individual/` other than this run's own outputs, and any evaluation or
reconciliation report. No live web content was fetched. No prior D4D content from
any parent conversation was used.

The run directory `2026-07-28_claude-opus-5-crateonly_rep2` already held a CM4AI
pair from a sibling agent. Those files were listed by name only (to confirm the
CHORUS outputs would not overwrite anything) and were never opened.

## Subject settled on, and why

**Subject**: the dataset described by the *CHoRUS RO-Crate Package*
(`ark:59853/rocrate-chorus-ro-crate-package/`), published as *The Bridge2AI CHoRUS
for Clinical Care AI Dataset*, **version 1.0 Beta**, DOI `10.18130/V3/XNBOPG`.

The crate offers three candidate referents and one distractor:

1. the root RO-Crate package entity;
2. the two sub-crates (EHR, Waveforms), which are `hasPart` members;
3. the CHoRUS *network/project* — the description opens by defining CHoRUS as "a
   clinical data network", and `project_name` is `CHoRUS`;
4. the RO-Crate *packaging* itself, which the AI-readiness file describes at
   length.

I settled on the root package entity as a **dataset release**, not as the network
and not as the packaging, because the crate's own identity fields describe a
versioned data product: it carries a dataset DOI, `version: "1.0 Beta"`,
`datePublished`, `contentSize`, a `citation` naming Harvard Dataverse as the
publication venue, a `completeness` statement about which patients and images are
in *this release*, and a licence expressed as a Data Use Agreement. The network is
the producer of that release, so network-level facts (governance, funding,
participating hospitals) are recorded as properties *of* the release — creators,
funders, collectors, governance — rather than as the subject. The two sub-crates
are recorded as `resources` (and as `related_datasets` with `has_part`), which is
where the crate's own part structure belongs.

## Phase 1 — full record

Structure derived from class `Dataset` via `SchemaView`: induced slots, ranges,
`multivalued`, `required`, `inlined`/`inlined_as_list`, and enum permissible
values. Two schema behaviours were confirmed empirically with throwaway probe
files before writing:

- `principal_investigator`, `contact_person`, `reviewing_organization`,
  `grantor`, and `governance_committee_contact` have class ranges but are **not
  inlined**, so they take a plain string reference, not a nested object.
- `issued`/`created_on`/`last_updated_on` are `datetime` and reject a bare date.

Validation:

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
```

First pass failed with seven `is not of type 'string'` errors: list items beginning
`Human subject exemption: …` and `Primary maintainers: …` were parsed by YAML as
single-key mappings. Fixed by quoting those scalars. Re-validated clean.

## Phase 2 — core record

Core structure derived from class `CoreDataset` in
`data_sheets_schema_core_all.yaml`. `CoreDataset` was compared slot-by-slot
against the Phase 1 full record: every core slot the full record populates was
carried over verbatim, and the crate was re-read for the core-only slots.

Core-only slots and why they are empty:

- **`distributions`** (`CoreDistribution`: `bytes`, `hash`, `md5`, `sha256`,
  `path`, `format`, `encoding`, `compression`, `media_type`) — the bundle states
  in its own header that it is the crate JSON-LD "with file inventories
  collapsed". The AI-readiness file reports aggregate facts about that inventory
  (1477 files, 1469 with checksums, formats `.ipynb` /
  `text/tab-separated-values` / `wfdb`) but no per-file path, checksum, byte
  count, or format. Nothing supports a distribution entry. The aggregate facts are
  recorded instead in `distribution_formats` and `total_file_count`, which exist
  in both records (`distribution_formats`) or in full only (`total_file_count`).
- **`dialect`** (`FormatDialect`: delimiter, quote char, header, …) — the crate
  says nothing about tabular dialect. `is_tabular` is also omitted from both
  records: the reported formats are mixed (notebooks, TSV, WFDB waveforms), so
  neither `true` nor `false` is supportable.

No fact appears in core that is absent from the full record, and Phase 2 found
nothing in the crate that the full extraction had missed.

Validation:

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Both clean on first run.

## Phase 3 — source and provenance audit

### Mechanical re-check of the creator block

The crate's `author` field is a single 41-name string with 15 numbered
affiliations. The record's 41 `creators` entries were parsed back out and diffed
against the source string programmatically: **name set, name order, and
affiliation assignment all matched exactly**, including the two authors carrying
dual affiliations (Xiaoqian Jiang and Hongfang Liu → UTHealth Houston *and* Mayo
Clinic). The only diff was a straight-vs-curly apostrophe in "Seattle Children's
Hospital" and "Nationwide Children's Hospital"; corrected to the crate's curly
form.

### Corrections applied to the full record (then propagated to core)

1. **Removed `machine_annotation_tools`.** It had recorded the OHNLP toolkit on
   the strength of `tokenized note and report text (via OHNLP toolkit)`.
   Tokenization is text processing, not annotation, and the crate never describes
   an annotation step. Mis-scoped assertion, deleted. OHNLP remains recorded where
   the crate actually places it: `collection_mechanisms`, `preprocessing_strategies`
   (both as `used_software`), and `is_deidentified.deidentification_details`.
2. **Unified `Software` identifiers.** The OHNLP toolkit, RSNA Clinical Trial
   Processor, and IbisWorks EICON had been given two id variants each because they
   appear under two parents. One entity now has one id.
3. **Unified the PI's name form.** `regulatory_restrictions.governance_committee_contact`
   read "Eric Rosenthal" (the `dataGovernanceCommittee` spelling) while
   `creators` and `ethical_reviews` read "Eric S. Rosenthal" (the `author` and
   `ethicalReview` spelling). Normalised to "Eric S. Rosenthal" so the same person
   resolves to one string across the record. Both forms are the crate's own.
4. **Apostrophe restoration** in the two hospital names, as above.

### Source disagreements inside the crate, and how they were resolved

- **Publication date format.** Root `datePublished` = `2026-04-03`; root
  `releaseDate` = `03/04/2026`; Waveforms `datePublished` = `2026-04-03`; EHR
  `datePublished` = `03/04/2026`. The ISO form is unambiguous and the citation
  says "Apr. 2026", so all four are the same day under a D/M/Y reading of the
  slashed form. Recorded as `release_dates: ["2026-04-03"]`, with both crate
  spellings quoted in the `distribution_dates` description rather than silently
  dropped.
- **Content URL.** Root `contentUrl` = `http://chorus4ai.org/dataset` (no TLS, no
  trailing slash); both sub-crates and the `license` string use
  `https://chorus4ai.org/dataset/`. Each level keeps its own verbatim value:
  `download_url` at root, `download_url` on each resource, and `page` for the
  https form. Not normalised, because doing so would assert a URL the crate does
  not carry at that level.
- **Licence wording.** Root `license` = "Data Use Agreement available at
  'https://chorus4ai.org/dataset/'"; sub-crates = "See Data Use Agreement". Kept
  verbatim at each level.
- **PI string.** Root `principalInvestigator` = "Eric Rosenthal,
  EROSENTHAL@mgh.harvard.edu"; sub-crates = "PI Eric Rosenthal
  EROSENTHAL@mgh.harvard.edu". Same person, same address; see correction 3.
- **Duplicated RAI fields.** `rai:dataBiases` and `rai:potentialBiases` are
  byte-identical, as are `rai:dataReleaseMaintenancePlan` and
  `rai:maintenancePlan`. Treated as one fact each (six biases; one maintenance
  plan), not as two independent sources.

### Judgement calls recorded rather than hidden

- **Byte counts.** `contentSize` is given as text: "18.136671 mb" (EHR) and
  "1.201567472832 tb" (Waveforms). Read as decimal SI units, both convert to exact
  integers — 18,136,671 and 1,201,567,472,832 — with no remainder, which the
  binary reading does not produce. Recorded as `total_size_bytes` on the two
  resources. The **root** `contentSize` of "1.2 tb" is a rounded figure, so
  top-level `total_size_bytes` is **left empty** rather than asserting
  1,200,000,000,000. The two part values sum to 1,201,585,609,503 bytes ≈ 1.2 tb,
  consistent with the rounded root value.
- **`total_file_count: 1477`** comes from the AI-readiness statement "99% of files
  have checksums (1469/1477)". Scope caveat: this is the count of files the crate
  documents, which may include crate-internal artifacts, not necessarily a count
  of data files only. Recorded because it is the only file-count evidence in the
  bundle.
- **`confidentiality_level: restricted`** is a lossy projection. The crate says
  `HL7:2V (very restricted)`; `ConfidentialityLevelEnum` offers only
  `unrestricted` / `restricted` / `confidential`. The verbatim string is preserved
  in `regulatory_restrictions.description` and `other_compliance` so nothing is
  lost.
- **`bias_type` left unset on two of six biases.** "Missingness not at random
  (MNAR)" and "Differential care pathways affecting label assignment" have no
  clean `BiasTypeEnum` member; the verbatim `bias_description` carries them.
  Assigning a type would have been invention.
- **`is_representative: false`** rests on three crate bullets quoted into
  `why_not_representative` ("Limited generalizability beyond participating
  hospitals", plus the referral-bias and institutional-distribution bullets). It is
  an interpretation of those statements, not a verbatim claim.
- **Text normalisation.** The crate's narrative fields use `•` + literal tab
  bullets and an en dash in "NIST 800-53–aligned". Bullets were rendered as YAML
  list items and the en dash as a hyphen. Wording is otherwise verbatim.

### Provenance findings

No prior-run D4D, evaluation, or reconciliation report was read at any point. Both
headers carry `Prior D4D factual reuse: prohibited`. The core header names both its
inputs (the crate-only bundle and the exact same-run full path, which contains this
run's label) and carries `Phase 4 reconciliation: completed`.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime by `load_pair_schema()` from `Dataset` and
`CoreDataset` — no hand-maintained list.

- **76 schema-identical shared slots**; all deeply identical or absent from both.
- **1 projected slot**: `resources` (`Dataset` in full, `CoreDataset` in core).

Because core was generated as a schema-filtered projection of the audited full
record, identity holds by construction: no narrative field was condensed,
paraphrased, reordered, or dropped in core.

**Resource projection.** Both records carry the same two resources, matched by id
and in the same order:

| id | name | full-only slots dropped in core |
|---|---|---|
| `08cf7419-b94d-4508-8f64-c99c557351d7` | CHoRUS RO-Crate EHR SubRoCrate | `citation`, `total_size_bytes` |
| `b9b41c72-0895-4ec2-9e39-8de2a83abcd6` | CHoRUS RO-Crate Waveforms SubRoCrate | `citation`, `total_size_bytes` |

Both dropped slots are absent from `CoreDataset`, so the omission is schema-forced,
not editorial. Every remaining nested slot (`id`, `name`, `description`, `version`,
`keywords`, `publisher`, `license`, `download_url`) is deeply identical.

**Full-only top-level slots** (present in `Dataset`, absent from `CoreDataset`, so
correctly missing from core): `citation`, `total_file_count`, `related_datasets`,
`splits`, `direct_collection`, `collection_consents`, `third_party_sharing`,
`participant_privacy`.

**Related, non-identical representations reviewed semantically:**

- `file_collections` → `distributions`: both empty. Nothing to contradict; see
  Phase 2 for why.
- `total_file_count` (1477, full only) vs distribution-level counts: no
  distribution-level count exists, so no scope comparison is possible and no
  conflict can arise.
- `total_size_bytes`: empty at root in both; present on resources in full only
  (schema-forced). The two resource values do not conflict with the rounded root
  `contentSize` the crate reports.
- `dialect`, formats, `is_tabular`: `dialect` empty; `is_tabular` omitted from
  both; format evidence lives in `distribution_formats`, which is schema-identical
  and deeply equal across the pair.
- Identity / version / access facts: `id`, `doi`, `version`, `license`,
  `publisher`, `download_url`, `page` agree across the pair, and agree with
  `version_access.latest_version_doi`, `version_access.versions_available`,
  `license_and_use_terms`, `regulatory_restrictions`, and the resource-level
  `version`/`license`/`download_url` values.
- Historical vs current release: only one release (1.0 Beta) is described. The
  maintenance plan's references to prior-version archiving are forward-looking
  policy, recorded in `version_access.version_details` and `updates`, and are not
  treated as evidence of a superseded release.

**Commands and results:**

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d_core.yaml \
  --sync-core
# PASS: 76 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full ... --core ...
# PASS: 76 schema-identical slots; projected slots=['resources']
```

`--sync-core` made no content change (the pair already passed before it ran).
Both files were re-validated against schema and ontology terms afterwards: all four
validations clean, zero warnings, zero unresolved contradictions within or between
the two records.

## Files changed

- created `…/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d.yaml`
- created `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_d4d_core.yaml`
- created `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_reconciliation.md`
- created `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CHORUS_provenance.yaml`

No existing file was overwritten.

## What the crate could NOT support at all

These D4D areas are empty in both records because the crate-only bundle contains
no evidence for them. This is the finding, not a gap that was papered over.

**Nothing at all from this source:**

| Area | Slot(s) left empty |
|---|---|
| Motivation — unmet need | `addressing_gaps` — the crate states what the dataset *is for*, never what gap or deficiency it exists to close |
| Composition — how many | `instances[].counts` — no patient, encounter, record, or signal counts anywhere; "1468 dataset(s) documented" counts crate entities, not data instances |
| Composition — instance relationships | `relationships` — no statement of how EHR, waveform, imaging, and note records link to each other or to a patient |
| Composition — subpopulations | `subpopulations` — biases mention demographic distribution and "ICU vs non-ICU populations", but no subpopulation is identified or quantified |
| Composition — content warnings | `content_warnings` |
| Collection — when | `collection_timeframes` — **no dates of any kind** for the clinical episodes; the only dates in the crate are publication dates |
| Collection — notification | `collection_notifications` |
| Collection — consent revocation | `consent_revocations` — no withdrawal mechanism described |
| Preprocessing — cleaning | `cleaning_strategies` — transformation and de-identification are described; cleaning/QC is not |
| Preprocessing — labelling | `labeling_strategies`, `annotation_analyses` — labels are referred to obliquely ("label assignment"), but no labelling process, protocol, annotator, or agreement statistic |
| Preprocessing — imputation | `imputation_protocols` — MNAR missingness is acknowledged with no handling strategy; `missing_data_documentation.handling_strategy` is also empty for the same reason |
| Uses — prior work | `existing_uses`, `use_repository`, `other_tasks` — no publication, benchmark, or downstream use is cited |
| Human subjects — vulnerable groups | `at_risk_populations` — two paediatric sites appear in the affiliation list, but the crate makes no statement about minors or other protected groups, and inferring one from an affiliation list would be invention |
| Human subjects — compensation | `participant_compensation` |
| Maintenance — retention | `retention_limit` |
| Maintenance — contribution | `extension_mechanism` |
| Variable-level metadata | `variables` — the AI-readiness file counts "44 schema(s) documented" but names none, and the file inventory that would carry them was collapsed out of the bundle |
| Distribution — file-level | `file_collections` (full) / `distributions` (core), `dialect`, `compression`, `is_tabular` |
| Aggregate size | top-level `total_size_bytes` — root value is rounded ("1.2 tb"); only the two parts have exact values |
| Language | `language` |

**Notably thin rather than absent:**

- **Consent.** `informed_consent` and `collection_consents` document a *regulatory
  exemption* (HIPAA exemption 4, 45 CFR 46.104(d)(4)) and "IRB approval or waiver
  as appropriate" — not consent obtained from individuals. `consent_obtained` is
  deliberately left unset rather than set to `false`: the crate documents a legal
  basis, and does not say consent was not obtained.
- **Composition.** Four modality-level `instances` could be described, but with no
  counts, no schema, no variables, and no timeframe. The crate says *what kinds of
  data* exist and almost nothing about *how much*.
- **Provenance of the crate's own claims.** The AI-readiness file is a
  self-assessment; where it is the sole support for a value (file count, format
  list, checksum coverage) that is stated in the record's own descriptions.

**Where the crate is strong.** Access and governance (`license_and_use_terms`,
`regulatory_restrictions`, `ip_restrictions`, `third_party_sharing`), ethics and
privacy (`ethical_reviews` with a named IRB, protocol number, and contact;
`participant_privacy`; `is_deidentified`; `data_protection_impacts`), risk
disclosure (six biases, eight limitations), intended and discouraged uses, the
maintenance plan, and attribution (41 named individual creators with
affiliations, plus a consortium entry carrying the PI, funder, publisher, and
contact) are all populated directly and largely verbatim. The
Croissant `rai:*` fields carry most of that weight — the crate is markedly
better at *responsible-use* documentation than at describing the data itself.
