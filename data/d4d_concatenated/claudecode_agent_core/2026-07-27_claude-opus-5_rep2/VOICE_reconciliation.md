# VOICE full/core reconciliation — 2026-07-27_claude-opus-5_rep2

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent
- Temperature: 0.0
- Generated: 2026-07-27
- Arm: BASELINE (document corpus only)

## Files

| Role | Path | Lines |
| --- | --- | --- |
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml` | 2309 |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml` | 1707 |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/VOICE_reconciliation.md` | this file |

Line counts are informational metadata only, not a quality gate.

## Phase 3 — source and provenance audit

### Provenance result

Factual inputs read during this run were exactly:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (the only source of dataset facts)
- `data/preprocessed/source_manifest.yaml` (source inventory and curation notes)

Structure-only inputs read: `data_sheets_schema_all.yaml` (class `Dataset`),
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), `D4D_Composition.yaml`
(to confirm the `values_from` constraints on `data_topic` / `data_substrate`), and
`src/data_sheets_schema/d4d_pair_consistency.py` (to derive the Phase 4 rules).
Procedure inputs read: `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`.

No prior full or core D4D record, evaluation, reconciliation report, or RO-Crate
artifact was read, searched, globbed, or cited. `data/d4d_concatenated/` and
`data/d4d_concatenated/claudecode_agent_core/` were listed only to confirm that the
`2026-07-27_claude-opus-5_rep2` output directories did not already exist; no file
inside any other version directory was opened. No live web content was fetched. No
D4D content from the parent conversation was used as evidence.

Structure was derived at runtime from the schemas via `SchemaView.induced_class`,
not from any example record. `d4d:docExample` annotations were not copied.
`data_topic` and `data_substrate` were deliberately left unpopulated: both declare
`values_from: B2AI_TOPIC` / `B2AI_SUBSTRATE`, and neither enum is resolvable in the
merged schemas, so no defensible value exists.

### Source-audit findings and corrections

Three corrections were made to the full record during Phase 3 and then propagated to
core. In each case the full record was corrected first.

1. **Mis-scoped release statistic (corrected).** The draft attributed "12,523
   recordings for 306 participants" to adult v1.1. The v1.1 PhysioNet page states
   this of **v1.0**: "Bridge2AI-Voice v1.0, the initial release, provides 12,523
   recordings for 306 participants collected across five sites in North America."
   The figure was moved to the v1.0 entry of
   `resources[d4d:VOICE-adult].version_access.version_details`, attributed to the
   page that states it. The v1.1 entry now carries only what v1.1 itself claims
   (MFCCs added; adult-cohort-only; files no longer available).

2. **Mis-scoped conformance claim (corrected).** The draft asserted
   `conforms_to: Brain Imaging Data Structure (BIDS) v1.9.0` on the adult PhysioNet
   resource. The corpus states BIDS v1.9.0 conformance of the **raw audio files and
   questionnaire exports** ("The raw audio files and the questionnaire data retrieved
   from ReproSchema-UI or exported from REDCap were converted to be compliant with the
   Brain Imaging Data Structure v1.9.0"), with a `b2ai-voice-audio` tree, whereas the
   PhysioNet feature release uses a `features` / `phenotype` / `metadata` layout. The
   slot was removed from the adult resource and retained only at the project level,
   where the BIDS layout is also documented under
   `raw_data_sources[d4d:VOICE-raw-source-audio].raw_data_format`.

3. **Conflicting size targets (represented, not silently resolved).** The corpus
   gives two different target sizes. Current project documentation: "a flagship,
   standardized, and ethically sourced dataset of 10,000 voices" and "Enrollment Count
   (Anticipated by 2027): 10,000". The 2024 audiomics white paper: "a publicly
   available database of 30 000 human voices". The IRB protocol: "Sample Size 30 000
   participants" with "up to 5000 participants per category". Both were recorded in
   `purposes[d4d:VOICE-purpose-flagship-voice-dataset].response` with explicit source
   and date attribution rather than picking one.

### Consistency checks that passed unchanged

- **Participant arithmetic is internally consistent.** v1.0 = 306 participants;
  v2.0 adds 136; v3.0.0 adds 391; 306 + 136 + 391 = 833, matching the v3.0/v3.1
  abstracts ("data for 833 participants across five sites in North America") and the
  healthsheet ("There are currently around 833 instances", "833").
- **DOIs.** Adult 1.1 `10.13026/249v-w155`, 3.0.0 `10.13026/k81f-qr68`, 3.1.0
  `10.13026/8xbn-nq66`, adult latest `10.13026/37yb-1t42`; pediatric 1.1.0
  `10.13026/h995-bt35`, pediatric latest `10.13026/mf9s-5r03`; adult v1.0 on Health
  Data Nexus `10.57764/qb6h-em84`. Each is used only where its page states it.
- **Access rules.** Adult v1.1 is "Restricted Access … Only registered users who sign
  the specified data use agreement"; adult v3.0.0 / v3.1.0 and pediatric v1.1.0 are
  "Credentialed Access … Only credentialed users who sign the DUA", no training
  required. Both are recorded with version scope, so the difference is a version
  history, not a contradiction.
- **Funding.** `OT2OD032720` (core project); `3OT2OD032720-01S1` (PhysioNet
  acknowledgements); `3OT2OD032720-01S3` (NIH RePORTER project number for application
  11376382, FY2025, award 4,660,942, 2022-09-01 to 2026-11-30). All three appear in
  the corpus and are recorded together with their sources.
- **Hosting.** The healthsheet names Health Data Nexus (T-CAIREM, University of
  Toronto) as host; current releases are on PhysioNet, maintained by the MIT
  Laboratory for Computational Physiology. The Health Data Nexus maintainer entry is
  explicitly flagged "Historical scope", so the two statements coexist without
  conflict.

### Discrepancies noted but deliberately not resolved

- **Name spelling.** The docs healthsheet writes "Jennifer Sui, MD (Hospital for Sick
  Children)"; the PhysioNet v3.0.0, v3.1.0 and pediatric v1.1.0 author lists and
  citations write "Siu, Jennifer" / "Siu, J.". Each spelling is reproduced only inside
  a quotation of its own source (healthsheet-derived consortium description vs. the
  PhysioNet citation strings). No corpus evidence identifies which is correct.
- **HIPAA framing.** The study metadata answers "Does this dataset apply the HIPAA
  de-identification rules? Yes", and the collection apps and storage are described as
  HIPAA-compliant, so `regulatory_restrictions.hipaa_compliant` is set to `compliant`.
  The Data Transfer and Use Agreement separately states that the transferred Data "is
  Personally Identifiable Information, as that is defined in OMB Memorandum M-07-16,
  and not covered under HIPAA, FERPA, or similar laws … that require the addition of
  special terms". Both statements are carried verbatim in
  `regulatory_restrictions.other_compliance` and
  `confidential_elements[…].confidentiality_details`; they describe different objects
  (the released dataset vs. the transfer instrument) and are not reconciled into one
  claim.
- **Institution counts.** The white paper says "50 multidisciplinary experts from 12
  North American institutions"; the IRB protocol says "11 different academic sites
  across the US"; the healthsheet lists 12 collaborator institutions. Each figure is
  attributed to its source rather than averaged.

### Adult / pediatric cohort separation

The corpus covers two distinct PhysioNet projects. They are represented as two sibling
entries under the project-level `resources` slot, never merged:

| | `d4d:VOICE-adult` | `d4d:VOICE-pediatric` |
| --- | --- | --- |
| PhysioNet project | `b2ai-voice` | `b2ai-voice-pediatric` |
| Current version | 3.1.0, published 2026-05-01 | 1.1.0, published 2026-05-01 |
| Version DOI | 10.13026/8xbn-nq66 | 10.13026/h995-bt35 |
| Latest-version DOI | 10.13026/37yb-1t42 | 10.13026/mf9s-5r03 |
| Participants | 833 adults, five North American sites | 300, aged 2–18, Hospital for Sick Children |
| Recordings | v3.0 documented as ~61,937 voice-derived recordings; v3.1.0 per-feature record counts 28,640–32,522 | 23,533 derived recordings |
| Collection software | Bridge2AI-Voice iOS and Web app on iPad, 22 acoustic tasks | reproschema-ui on tablets, pediatric protocol |
| Ethics | USF Single IRB (+ subsite IRBs) | Research Ethics Board, Hospital for Sick Children |
| Raw audio | Synapse `syn72370534` | Synapse `syn73617068` |
| Version series | 1.1 → 2.0.0 → 2.0.1 → 3.0.0 → 3.1.0 | 1.0.0 → 1.1.0 |

Additional safeguards against conflation:

- The project-level `description` states outright that the two are "separate projects
  and separate participant cohorts rather than versions of one another".
- `instances` carries three separately named and separately counted entries
  (`…-instance-adult-participant` 833, `…-instance-pediatric-participant` 300,
  `…-instance-pediatric-recording` 23,533); no summed figure appears anywhere.
- The pediatric instance description states explicitly that "the counts must not be
  combined with the adult count".
- `version_access.version_details` at project level states "The adult and pediatric
  datasets are separate PhysioNet projects with independent version series; pediatric
  v1.1.0 is not a version of adult v1.1."
- Each resource's `related_datasets` links the other with `relationship_type:
  references` (not `is_version_of`), matching the PhysioNet cross-reference banners.
  Only the Health Data Nexus v1.0 release is linked with `is_new_version_of`, and only
  from the adult resource.
- Access routes are kept per resource: `license_and_use_terms`, `version_access`,
  `distribution_formats`, `raw_sources` and `ethical_reviews` are all resource-scoped.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with LinkML `SchemaView` over `Dataset` and `CoreDataset`; no
hand-written field list was used.

- Schema-identical slots: **76**
- Projected slots: **1** (`resources`, `Dataset` in full vs `CoreDataset` in core)
- Core-only slots used: `distributions` (`CoreDistribution`), `dialect`
  (`FormatDialect`)
- Full-only top-level slots correctly absent from core: `citation`,
  `collection_consents`, `collection_notifications`, `consent_revocations`,
  `direct_collection`, `participant_compensation`, `participant_privacy`,
  `related_datasets`, `relationships`, `splits`, `third_party_sharing`, `variables`
- Full-only resource-level slots correctly absent from the core projection:
  `citation`, `file_collections`, `related_datasets`

### Identity result

All 76 schema-identical slots are present in both records or absent from both, and
every parsed YAML value is deeply identical including nested mapping values and list
order. No narrative field was condensed, paraphrased, reordered, or omitted in core.
The `resources` projection has equal coverage (`d4d:VOICE-adult`,
`d4d:VOICE-pediatric` in both) and deep identity for every nested schema-identical
slot.

### Related-content mapping and semantic review

Full `file_collections` live on the two resources, so core `distributions` were placed
on the matching resources; there are no top-level `file_collections`, so no top-level
`distributions` were emitted.

| Resource | Full `file_collections` | Core `distributions` | Review |
| --- | --- | --- | --- |
| adult | `…-adult-features` (path `features`) | `…-adult-dist-features` (path `features`), `…-adult-dist-static-features` (`features/static_features.tsv`, TSV), `…-adult-dist-audio-quality-metrics` (`features/audio_quality_metrics.tsv`, TSV) | paths agree; the two TSV distributions expand the documented plain-text members of the same folder |
| adult | `…-adult-phenotype` (path `phenotype`) | `…-adult-dist-phenotype` (path `phenotype`, TSV, `text/tab-separated-values`) | paths agree; TSV matches "tab delimited file" and `pd.read_csv(..., sep="\t")` |
| adult | `…-adult-metadata` (path `metadata`) | `…-adult-dist-metadata` (path `metadata`) | paths agree |
| adult | — | `…-adult-dist-data-dictionaries` (JSON, `application/json`) | describes the per-file JSON data dictionaries documented for every feature and phenotype file; no path asserted |
| pediatric | `…-pediatric-features`, `…-pediatric-phenotype`, `…-pediatric-metadata` | the six `…-pediatric-dist-*` entries, same pattern | paths agree; same review |

Checks performed:

- **Names, descriptions, paths.** No conflicts. Every core `path` either equals the
  matched full `path` or is a documented file inside it.
- **Formats.** Apache Parquet is not a member of `FormatEnum`/`MediaTypeEnum`, so no
  `format` or `media_type` is asserted for the Parquet bundles; each such distribution
  says so in its description. TSV and JSON members carry `format` + `media_type` that
  agree with the corpus.
- **Compression, checksums, byte counts.** Not stated anywhere in the corpus, so
  `compression`, `hash`, `md5`, `sha256` and `bytes` are omitted from every
  distribution. Nothing to contradict.
- **`total_file_count` / `total_size_bytes`.** Not stated in the corpus; absent from
  full, so there is no scope comparison to make against distribution-level values.
- **Access URLs and release scope.** Full `distribution_formats.access_urls` and
  resource `download_url` point at the same PhysioNet and Synapse locations that the
  corpus states, version by version; core `distributions` assert no access URLs, so no
  conflict is possible.
- **`dialect` vs formats vs `is_tabular`.** Core `dialect` sets `delimiter: "\t"` and
  a header note, consistent with the full record's description of tab-delimited
  phenotype and feature tables. `is_tabular` is deliberately unset in both records:
  the releases mix dense Parquet tensors with tabular TSV, and the corpus makes no
  single claim, so asserting either value would be unsupported.
- **Top-level identity/version/access vs resources.** Project-level `license`
  (Bridge2AI Voice Registered Access License) matches both resources.
  `distribution_dates.release_dates` matches, date for date, the two resources'
  `version_access.versions_available`. Project-level `version_access` carries no
  `latest_version_doi` (there are two distinct latest DOIs); each resource carries its
  own. Project-level `version` / `doi` / `download_url` are intentionally unset for
  the same reason.
- **Historical vs current releases.** Version-scoped differences (v1.1 registered
  access vs v3.x credentialed access; Health Data Nexus vs PhysioNet hosting; the
  healthsheet's v2.0.0-scoped "current dataset contains only adult populations") are
  recorded as history with explicit scope, not treated as contradictions.

Zero unresolved contradictions within or between the two records.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/VOICE_d4d_core.yaml
```

### Final results

| Check | Result |
| --- | --- |
| Full — `linkml-validate` (`Dataset`) | PASS — no issues found |
| Full — `linkml-term-validator` | PASS — validation passed |
| Core — `linkml-validate` (`CoreDataset`) | PASS — no issues found |
| Core — `linkml-term-validator` | PASS — validation passed |
| Pair consistency (`--sync-core`) | PASS — 76 schema-identical slots; projected slots=['resources'] |
| Pair consistency (final, no sync) | PASS — 76 schema-identical slots; projected slots=['resources'] |

Files changed in Phase 3/4: the full record (three scope corrections listed above) and
the core record (regenerated projection plus the `--sync-core` pass, which also added
the `# Phase 4 reconciliation: completed` header line). All four schema and term
validations and both pair-consistency runs were re-run after the last change and pass.
