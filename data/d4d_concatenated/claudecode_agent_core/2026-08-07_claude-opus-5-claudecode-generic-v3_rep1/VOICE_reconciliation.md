# VOICE full/core reconciliation

Run label: `2026-08-07_claude-opus-5-claudecode-generic-v3_rep1`
Arm: BASELINE (input documents only)
Runtime / provider / model: Claude Code / Anthropic / claude-opus-5, reasoning effort `high`, temperature 0.0
Mode: four-phase project agent, generic prompt
(`src/download/prompts/d4d_generic_arm_prompt.md`)

Files:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The one chosen is the **adult Bridge2AI-Voice
dataset** — the PhysioNet project `b2ai-voice`, "Bridge2AI-Voice: An
ethically-sourced, diverse voice dataset linked to health information" — taken at
its current release **v3.1.0**, published 1 May 2026, DOI `10.13026/8xbn-nq66`,
833 participants across five sites in North America.

The declared bundle supports this choice better than any alternative: seven of its
eleven documents describe the adult dataset or the protocol that produced it, and
four of those are PhysioNet records of this exact project. The source manifest
instructs that v3.1.0 be preferred over the v3.0.0 capture where the two disagree,
which fixes the release as well as the project.

Two candidate referents were rejected:

- **The Bridge2AI-Voice programme as a whole.** The NIH RePORTER page, the IRB
  protocol and the audiomics white paper describe a multi-year grand-challenge
  project with six modules, targets of 10,000 or 30,000 voices, and deliverables
  that are not datasets. Treating the programme as the referent would attach
  aspirational targets and non-dataset deliverables to a released artifact. The
  programme-level material is retained where it is genuinely about this dataset's
  purpose, funding, collection protocol and ethics, and is scoped in
  `source_caveats` where it is not.
- **The Bridge2AI-Voice Pediatric Dataset.** See below.

## Relationship to the pediatric dataset

The pediatric dataset is **not** represented as this dataset, as a version of it,
as a subset, or as a nested object. It appears in exactly one place, as a single
entry in `related_datasets`:

```yaml
- id: d4d:VOICE-related-pediatric
  target_dataset: https://doi.org/10.13026/h995-bt35
  relationship_type: references
```

`references` was chosen from `DatasetRelationshipTypeEnum` because that is what the
evidence actually states: the PhysioNet record for the adult dataset carries a
notice that "the Bridge2AI-Voice Pediatric Dataset is also available on PhysioNet"
with its URL. Nothing in the bundle supports a part/whole, version, or derivation
relationship, and the bundle states the opposite — a separate PhysioNet project,
a separate DOI (`10.13026/h995-bt35`), a separate cohort (300 participants aged
2–18, 23,533 derived recordings), a separate protocol (ReproSchema-UI with the
Bridge2AI-Voice pediatric protocol), a separate recruitment site (Hospital for
Sick Children), separate ethics approval (the SickKids Research Ethics Board
rather than the USF IRB) and separate raw-audio distribution (Synapse
`syn73617068` rather than `syn72370534`).

`related_datasets` is a full-only slot; `CoreDataset` does not define it, so the
core record carries no pediatric content at all. The pediatric bundle
`data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt` was not read.
The pediatric facts above come from the pediatric PhysioNet capture that is
inside this project's own declared bundle, and are recorded only to identify the
relationship, with a `source_caveats` note stating that scope boundary.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior D4D record was read, opened, grepped or consulted, from any arm, label or
date. Nothing under `data/d4d_concatenated/` other than this run's own two outputs
was accessed, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was accessed.
The factual inputs were the declared bundle
`data/preprocessed/concatenated/VOICE_preprocessed.txt` and
`data/preprocessed/source_manifest.yaml`. The non-factual inputs were the two
schemas, `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`,
`src/download/prompts/d4d_generic_arm_prompt.md` and
`src/data_sheets_schema/d4d_pair_consistency.py`. Record structure was derived at
runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView`; no `d4d:docExample`
annotation supplied a value.

### Source disagreements represented rather than resolved

The bundle is a release programme captured at different times, and several of its
documents describe superseded states. Each disagreement below is recorded in the
records themselves rather than silently decided.

| Disagreement | How it is represented |
|---|---|
| Overall enrollment target: 10,000 (project documentation, "Enrollment Count (Anticipated by 2027)") vs 30,000 (audiomics white paper and IRB protocol sample size) | All three stated in `sampling_strategies[0].source_caveats`; no single target asserted |
| Access tier: "Credentialed Access" (PhysioNet v3.0.0/v3.1.0) vs "Restricted Access"/registered (PhysioNet v1.1) vs "registered access" then "credentialed users must be approved" in one paragraph of the project documentation | Current tier recorded as credentialed; all wordings recorded in `license_and_use_terms.source_caveats` |
| Hosting: Health Data Nexus / T-CAIREM, University of Toronto (project documentation healthsheet) vs PhysioNet / MIT Laboratory for Computational Physiology (current releases) | Both recorded as separate `maintainers` entries, the Health Data Nexus entry scoped in its own `source_caveats` |
| Distribution platform: `healthdatanexus.ai`, published end of November 2024 (healthsheet) vs PhysioNet v1.1–v3.1.0 | Healthsheet statement kept as the historical release in `distribution_dates.description` and `version_access.version_details`; current platform used for `download_url`, `publisher`, `doi` |
| Free-speech transcriptions present (healthsheet content warning) vs transcripts and open-response features removed (v1.1 and v3.0.0 de-identification) | Both recorded; the conflict stated in `content_warnings[0].source_caveats` |
| Sensitive fields present (healthsheet) vs all sensitive REDCap-flagged fields removed at v3.0.0 | Both recorded; conflict stated in `sensitive_elements[0].source_caveats` |
| Recording count: ~61,937 for v3.0 (project documentation) vs per-feature counts 28,640–32,522 for v3.1.0 (PhysioNet) | Both recorded in `instances[1]`, with a `source_caveats` stating they are not comparable and neither was derived from the other |
| Collection timeframe: "12 months" (healthsheet) vs a four-year phased schedule (IRB) vs release dates spanning Jan 2025 – May 2026 | Both statements recorded in `collection_timeframes[0]`, with a `source_caveats` saying they cannot be reconciled and that no start or end date is stated |
| Institution counts: 12 collaborators (documentation), 9 participating institutions (IRB definitions), 11 academic sites (IRB procedures), 12 North American institutions / 50 experts (white paper), 5 recording sites (PhysioNet and healthsheet) | Twelve-collaborator list recorded as `creators[2].affiliations`; every other count and the unnamed five recording sites recorded in `creators[2].source_caveats` |
| HIPAA: de-identification rules applied (documentation) vs "not covered under HIPAA" (Data Transfer and Use Agreement, Attachment 2) | Both recorded; the difference in legal scope stated in `regulatory_restrictions.source_caveats` |

### Mis-scoping actively prevented

- **The feasibility publication (PMC12037532) is not this dataset.** It reports a
  47-participant, single-site study of the data-collection *application* at USF
  Health Voice Center between 5 June and 28 July 2023, in which audio data was not
  collected. Its participant count, completion rates and demographics are recorded
  only inside
  `known_limitations[d4d:VOICE-limitation-collection-instrument]`, explicitly as
  evidence about the collection instrument, with a `source_caveats` stating that
  those 47 participants are not part of this dataset's 833 and that no source
  claims overlap. Its IRB number (USF 004890) is deliberately **not** listed in
  `human_subject_research.irb_approval`, because it approved that study and not the
  data acquisition protocol.
- **v2.0.0-era healthsheet answers** are attributed to v2.0.0 where they carry a
  version-bound claim, notably the study-population statement quoted in
  `at_risk_populations.description`.
- **BIDS conformance** is recorded under `preprocessing_strategies` and scoped to
  the audio dataset layout rather than asserted as top-level `conforms_to`, because
  the PhysioNet feature-only release is organised into `features`/`metadata`/
  `phenotype` and its documentation does not restate BIDS conformance.

### Shape audit

- Every enum-ranged value is a defined permissible value:
  `bias_type` (`selection_bias`, `representation_bias`, `measurement_bias`),
  `limitation_type` (`representativeness_limitation`, `coverage_limitation`,
  `scope_limitation`, `methodological_limitation`), `collection_type`
  (`processed_data`, `metadata`), `role` (`academic_institution`,
  `government_agency`), `format` (`TSV`, `JSON`), `media_type`,
  `data_use_permission` (`general_research_use`), `hipaa_compliant` (`compliant`),
  `confidentiality_level` (`restricted`), `relationship_type` (`references`,
  `is_new_version_of`).
- No prose stands where the schema requires a list. Every multivalued slot
  (`irb_approval`, `regulatory_compliance`, `special_populations`, `restrictions`,
  `external_resources`, `tool_accuracy`, `annotator_demographics`, `warnings`,
  `missing`, `why_missing`, `examples`, `release_dates`, `versions_available`,
  `affected_subsets`) holds discrete items.
- No commentary is embedded in a `name`, `id` or affiliation value.
- `notes` is unused in both records. All evidence commentary — source conflicts,
  what a value was transcribed from, questions the sources leave open — is in
  `source_caveats`, at the top level and on eleven nested objects.
- Structured slots are filled before prose: `creators` carry `affiliations` and
  `principal_investigator`; `funders` carry `grants` with `grant_number`;
  `instances` carry `counts`, `sampling_strategies` and `missing_information`.
- Two slots were deliberately left unset rather than approximated. `format` and
  `media_type` on the Parquet distribution entry have no Parquet value in
  `FormatEnum` or `MediaTypeEnum`; the omission is stated in that entry's
  `source_caveats`. `principal_investigator` has range `Person` but is not inlined,
  so it takes a scalar reference; the bundle gives no ORCID for either co-PI, so the
  reference carries the name as stated in the sources and the substitution is
  recorded in each creator's `source_caveats`.
- Slots omitted for want of evidence rather than filled by inference:
  `is_tabular`, `dialect`, `conforms_to`, `total_file_count`, `total_size_bytes`,
  `subsets`, `parent_datasets`, `resources`, `variables`, `imputation_protocols`,
  `annotation_analyses`, `other_tasks`, and all `File`-level `bytes`, `md5`,
  `sha256` and `checksum` values.

### Corrections made in Phase 3

Four corrections were applied to the **full** record first, after which the core
record was regenerated from the corrected full record so that the corrections
propagated by construction. Both records were re-validated after the change.

1. `funders[0].grants` — the fiscal-year-2025 award amount of 4,660,942 was moved
   from the core-project entry (`OT2OD032720`) to the supplement entry
   (`3OT2OD032720-01S3`), because NIH RePORTER reports it against application
   11376382 rather than against the core project. Principal investigator,
   organization and project period stay on the core-project entry, where RePORTER
   reports them.
2. `license_and_use_terms.source_caveats` — added, recording the
   credentialed/registered/restricted wording divergence across the three sources.
3. `at_risk_populations.description` — the study-population claim was attributed to
   the v2.0.0 healthsheet text it comes from, rather than stated as a current fact.
4. `creators[2].source_caveats` — added the observation that the five recording
   sites are a smaller set than any institution list in the bundle and that no
   source names them.

No Phase 2 discovery required back-porting: the core schema defines no factual slot
absent from the full schema other than `distributions`, and the source review found
nothing the full record had missed.

## Phase 4 — strict full/core reconciliation

### Shared-slot identity

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView` by `data_sheets_schema.d4d_pair_consistency`; no hand-written field
list was used.

- **Schema-identical slots: 78.** All present-in-both slots have deeply identical
  parsed YAML content, including every nested mapping value and list item in the
  same order. Narrative fields are byte-for-byte the same text; nothing was
  condensed, paraphrased, reordered or omitted to make core shorter. This holds by
  construction: the core record is generated from the parsed full record, copying
  each shared slot's value verbatim, then serialised.
- **Projected slots: 1** (`resources`, `Dataset` in full and `CoreDataset` in core).
  Absent from both records, so coverage is trivially equal.
- **Presence parity** holds for every schema-identical slot: 63 present in both, the
  remainder absent from both.

Slots present in full and absent from core are exactly the twelve the core schema
does not define — `citation`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing`,
`file_collections`, `related_datasets`. One slot is present in core and absent from
full: `distributions`, which the full schema does not define.

Counts: full **75** populated top-level slots, core **64**.

### Related, non-identical content — semantic review

The validator flags `file_collections` ↔ `distributions` as requiring semantic
review and reports 3 deterministic matches with 0 unmatched core distributions.
That review was performed and is recorded here; the warning is not itself evidence
that it happened.

| full `file_collections` | core `distributions` | review |
|---|---|---|
| `d4d:VOICE-fc-features`, name `features`, path `features/`, `collection_type: processed_data` | same `id`, `name`, `path` | Matched on `id`. Name, path and description are identical strings. `collection_type` is full-only and has no core counterpart; `format`, `media_type`, `compression`, `encoding`, `bytes`, `hash`, `md5`, `sha256` are unset in core, so nothing can conflict. |
| `d4d:VOICE-fc-metadata`, name `metadata`, path `metadata/`, `collection_type: metadata` | same `id`, `name`, `path` | Matched on `id`. Identical name, path, description. Same reasoning. |
| `d4d:VOICE-fc-phenotype`, name `phenotype`, path `phenotype/`, `collection_type: processed_data` | same `id`, `name`, `path` | Matched on `id`. Identical name, path, description. Same reasoning. |

Remaining semantic checks required by the playbook:

- **Names, descriptions, paths** — identical in every matched pair, as above.
- **Formats and compression** — no `compression` is asserted anywhere in either
  record. Formats are asserted only in `distribution_formats`, a schema-identical
  slot whose content is deeply identical in both records, so full and core cannot
  disagree about format. The Parquet entry leaves `format`/`media_type` unset in
  both, for the enum reason given above.
- **Checksums and byte counts** — none asserted in either record; the bundle states
  none.
- **`total_file_count` / `total_size_bytes` vs distribution-level values** — both
  top-level counts are absent from the full record and no `bytes` is set on any
  distribution, so there is no scope pair to compare and no conflict.
- **Access URLs** — asserted only in `distribution_formats.access_urls` and
  `download_url`, both schema-identical and deeply equal.
- **`dialect`, formats, `is_tabular`** — `dialect` (core-only) and `is_tabular` are
  unset in both records; formats agree as above. No disagreement is possible.
- **Release scope** — all three collections and all three distributions describe the
  same release, v3.1.0. No historical release is mixed into them; the earlier
  releases appear only in `version_access`, `distribution_dates`, `errata` and
  `related_datasets`, where they are labelled by version.
- **Top-level identity, version and access facts vs the rest of the record** —
  checked in both files and consistent: `version: 3.1.0`, `doi: 10.13026/8xbn-nq66`,
  `issued: 2026-05-01T00:00:00Z` and
  `download_url: https://physionet.org/content/b2ai-voice/3.1.0/` agree with
  `version_access.versions_available` (1.1, 2.0.0, 2.0.1, 3.0.0, 3.1.0), with
  `version_access.version_details` (per-version DOIs `10.13026/249v-w155`,
  `10.13026/k81f-qr68`, `10.13026/8xbn-nq66`, latest `10.13026/37yb-1t42`), with
  `distribution_dates.release_dates` (3.1.0 = 1 May 2026), and with the release
  notes summarised in `version_access`. The participant count 833 is stated
  identically in `instances[0].counts`, `instances[0].description` and the top-level
  `description`. `license` matches the licence named in `license_and_use_terms` and
  in `regulatory_restrictions`.
- **Historical versus current releases** — treated as different scopes, not as
  contradictions: the Health Data Nexus v1.0 (`10.57764/qb6h-em84`) is a
  `related_datasets` entry with `relationship_type: is_new_version_of`; the v1.1
  access tier, the v2.0.0-era healthsheet answers and the November 2024 Health Data
  Nexus publication date are each labelled with the version or platform they belong
  to.

### Result

No divergence between the two records. Zero unresolved contradictions within either
record and zero between them.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d_core.yaml

poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1 --project VOICE

poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1
```

`--sync-core` was not needed and was not run: the core record is generated from the
parsed full record, so schema-identical slots are equal by construction, and the
independent check without `--sync-core` passed on the first attempt.

## Results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (`CoreDataset`) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency | PASS — 78 schema-identical slots, projected slots `['resources']`, 1 expected semantic-review warning, reviewed above |
| Full populated top-level slots | 75 (1612 lines, informational only) |
| Core populated top-level slots | 64 (1138 lines, informational only) |
| Divergence | None |

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d.yaml` (created, Phase 1; corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_d4d_core.yaml` (created, Phase 2; regenerated from the corrected full record in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_provenance.yaml` (written by `d4d provenance record`)

No file outside this run's label directories was written.
