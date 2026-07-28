# VOICE full/core reconciliation — 2026-07-27_claude-opus-5_rep3

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent, phases 1-4 run sequentially
- Temperature: 0.0
- Generated: 2026-07-27
- Arm: BASELINE (document corpus only)

## Files

| Role | Path | Lines |
|---|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml` | 1993 |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml` | 1419 |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/VOICE_reconciliation.md` | this file |

Line counts are informational metadata only, not a quality gate.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual input was limited to `data/preprocessed/concatenated/VOICE_preprocessed.txt`
(11 documents, 5750 lines) and `data/preprocessed/source_manifest.yaml`. Structure was
derived from `Dataset` in `data_sheets_schema_all.yaml` and `CoreDataset` in
`data_sheets_schema_core_all.yaml` via LinkML `SchemaView`, not from any example record.

No prior full or core D4D record, evaluation, reconciliation report, or RO-Crate artifact was
read, searched, or cited. No live web content was fetched. No D4D content from the parent
conversation was used. The only generated YAML read during Phases 2-4 was this run's own
full record at the exact path above. Phase 2 additionally read the schemas and the source
bundle. The scratchpad directory is shared with sibling agents; only files written by this
agent (prefixed `rep3_voice_*`, plus `dump_schema.py` and its own dumps) were read.

### Adult / pediatric cohort separation

The corpus covers two distinct PhysioNet projects. They are represented as two entries under
the root `resources` slot (range `Dataset` in full, `CoreDataset` in core), never merged and
never treated as versions of one another:

| | Adult | Pediatric |
|---|---|---|
| `id` | `https://physionet.org/content/b2ai-voice/3.1.0/` | `https://physionet.org/content/b2ai-voice-pediatric/1.1.0/` |
| `title` | Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information | Bridge2AI-Voice Pediatric Dataset |
| `version` | 3.1.0 | 1.1.0 |
| `doi` | 10.13026/8xbn-nq66 | 10.13026/h995-bt35 |
| latest-version DOI | 10.13026/37yb-1t42 | 10.13026/mf9s-5r03 |
| participants | 833, five sites in North America | 300, aged 2-18, Hospital for Sick Children only |
| derived recordings | per-feature 28,640-32,522 in v3.1.0 | 23,533 |
| collection software | Bridge2AI-Voice iOS app / Web app on iPad | reproschema-ui on tablets |
| ethics approval | University of South Florida IRB (single IRB) | Research Ethics Board, Hospital for Sick Children |
| raw audio route | Synapse syn72370534 | Synapse syn73617068 |
| version lineage | 1.1, 2.0.0, 2.0.1, 3.0.0, 3.1.0 | 1.0.0, 1.1.0 |

Separation is additionally carried in `instances` (four entries: adult participant 833,
pediatric participant 300, pediatric derived recording 23,533, adult derived recording),
`ethical_reviews` (separate USF IRB and SickKids REB entries), `raw_sources` (separate Synapse
projects), `collection_mechanisms` (app versus reproschema-ui), `distribution_dates` (separate
release timelines), `version_access`, `sampling_strategies`, and six `file_collections` /
`distributions` split three per cohort. Each resource carries a `related_datasets` entry stating
explicitly that the other cohort is a distinct PhysioNet project and not a version of it. No
participant count, access route, protocol, DOI, or approval is shared between the two.

### Source disagreements resolved

1. **Hosting platform.** The healthsheet (written when v2.0.0 was current) says the dataset is
   distributed and updated on Health Data Nexus; the current documentation and both PhysioNet
   projects place the current releases on PhysioNet and describe Health Data Nexus as hosting
   "an earlier version of the feature-only dataset". Resolved by recency and scope: current
   distribution is PhysioNet; the Health Data Nexus statement is retained with explicit
   historical scope in `updates`, `maintainers`, and `distribution_formats`.
2. **Access policy wording.** PhysioNet 1.1 is labelled Restricted Access ("only registered
   users who sign the specified data use agreement"); 3.0.0, 3.1.0 and pediatric 1.1.0 are
   labelled Credentialed Access ("only credentialed users who sign the DUA"). Both are recorded
   in `license_and_use_terms` with the release each applies to.
3. **Enrollment targets.** Current documentation gives an anticipated enrollment of 10,000 by
   2027; the IRB protocol gives 30,000 participants (5,000 through USF); the audiomics white
   paper gives 30,000 voices. These are targets, not collected counts. All three are recorded
   in `sampling_strategies` with their sources and scopes, and `status` carries the current
   10,000-by-2027 figure. Actual counts (833 adult, 300 pediatric) come only from the PhysioNet
   releases.
4. **Recording sites.** The releases and the healthsheet report five recording sites; the IRB
   protocol describes 11 planned academic sites. Five is used for what the adult dataset
   contains; the protocol figure is scoped to the protocol in `collection_timeframes`.
5. **Grant identifiers.** The corpus carries OT2OD032720 (core), 3OT2OD032720-01S3 (NIH
   RePORTER), 3OT2OD032720-01S1 (PhysioNet acknowledgements), 1OT2OD032720-01 (feasibility
   publication) and 3Tf-OTOD03272001S2 (documentation footer). All five are recorded with their
   sources. The healthsheet's garbled variant `3TF-OT2ActfOD032720Projectf01S1` was treated as an
   extraction artifact and omitted.
6. **Institution counts.** 12 North American institutions (white paper), 14 institutions
   (feasibility study app development), 11 academic sites (IRB), "ten other universities"
   (healthsheet). The quoted figures are attributed to their sources in the creator description;
   the `affiliations` list contains only institutions named in the study-metadata collaborator
   list or in IRB Annex C.

### Corrections applied to the full record

The full record was corrected first, then core was regenerated from it.

1. `updates.update_details` — the Health Data Nexus distribution statement was mis-scoped as
   current. Rewritten to attribute it to the v2.0.0-era healthsheet and to state that current
   releases are distributed on PhysioNet.
2. `resources[b2ai-voice/3.1.0].conforms_to` — removed. BIDS v1.9.0 conformance in the corpus
   describes the raw audio and questionnaire conversion, not the PhysioNet feature release,
   whose layout is `features/`, `phenotype/`, `metadata/`. The statement is retained at the
   project level in root `conforms_to`.
3. `sampling_strategies` — added an explicit strategy entry reconciling the 10,000 / 30,000 /
   5,000 enrollment targets by source and scope (see disagreement 3 above).
4. `license_and_use_terms.contact_person` — normalized from a bare address to "Data Access
   Compliance Office (DACO@b2ai-voice.org)", matching
   `regulatory_restrictions.governance_committee_contact`.

No Phase 2 discovery required back-porting: core was derived from the Phase 1 full record plus
the schema, and the source pass found no fact present in the documents that core could carry and
full could not.

### Internal consistency checks

- Version arithmetic corroborates the participant count: v1.0 306 participants, v2.0 +136,
  v3.0.0 +391, v3.1.0 +0 = 833, matching the v3.1 abstract and the healthsheet's "833".
- Every DOI, publication date, Synapse identifier, release date and per-feature record count in
  both records was checked against the corresponding PhysioNet page.
- `license` (Bridge2AI Voice Registered Access License) and `publisher` (`https://physionet.org/`)
  agree between the root and both resources. Root `issued` (2026-05-01) is consistent because
  both current releases were published on that date.
- Root `version` and root `doi` are deliberately absent: the two cohorts have distinct version
  lineages and DOIs, so a single root value would conflate them.
- `total_file_count`, `total_size_bytes`, `compression`, `is_tabular` and byte counts are absent
  from both records because no source states them. Nothing was invented to fill them.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with LinkML `SchemaView` from `Dataset` and `CoreDataset`:

- **76 schema-identical slots** — must be present in both or neither, with deeply identical
  parsed YAML including nested mappings and list order.
- **1 projected slot** — `resources` (range `Dataset` in full, `CoreDataset` in core).

Result: **PASS**, 76/76 identical, no presence or content divergence. Narrative fields were
copied verbatim; core condenses, paraphrases, reorders and omits nothing.

Full-only slots correctly absent from core (12): `citation`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `direct_collection`, `file_collections`,
`participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
`splits`, `third_party_sharing`.

Core-only slot populated: `distributions`. Core-only slot `dialect` was deliberately left
unpopulated — the releases mix Parquet binaries with delimited text, so a single root dialect
would be mis-scoped.

### Resource projection

Both records carry the same two resource ids, in the same order. Every schema-identical nested
slot is deeply identical. Full-only nested content (`citation`, `related_datasets`) is omitted
from the core projection as the schema requires.

### Related-content semantic review (`file_collections` ↔ `distributions`)

Six full `file_collections` and six core `distributions`, matched 1:1 on `id` by the validator
(deterministic matches = 6, unmatched = 0). Reviewed manually:

| id suffix | name | path | description | full-only | core-only |
|---|---|---|---|---|---|
| b2ai-voice/3.1.0/features | equal | `features` | equal | `title`, `collection_type` | — |
| b2ai-voice/3.1.0/phenotype | equal | `phenotype` | equal | `title`, `collection_type` | `format`, `media_type` |
| b2ai-voice/3.1.0/metadata | equal | `metadata` | equal | `title`, `collection_type` | — |
| b2ai-voice-pediatric/1.1.0/features | equal | `features` | equal | `title`, `collection_type` | — |
| b2ai-voice-pediatric/1.1.0/phenotype | equal | `phenotype` | equal | `title`, `collection_type` | `format`, `media_type` |
| b2ai-voice-pediatric/1.1.0/metadata | equal | `metadata` | equal | `title`, `collection_type` | — |

- Names, paths and descriptions are identical in every pair; no conflict is possible on those.
- `compression`, checksums (`hash`, `md5`, `sha256`), `bytes`/`total_bytes`, `file_count`,
  `encoding` and access URLs are asserted in neither record, because no source states them for
  these folders. There is therefore no byte-count or scope conflict with the absent root
  `total_file_count` / `total_size_bytes`.
- `format: TSV` / `media_type: text/tab-separated-values` is asserted only on the two phenotype
  distributions, supported by the PhysioNet usage notes
  (`pd.read_csv("demographics.tsv", sep="\t", header=0)`) and by the description of the phenotype
  tables as tab-delimited. The paired JSON data dictionaries are named in the shared description,
  so the format value is not contradicted. Features and metadata distributions carry no `format`
  because Parquet is not a `FormatEnum` value; their content is described in prose instead.
- The two cohorts' `features`, `phenotype` and `metadata` paths repeat across cohorts by design,
  since these are the real in-release folder names. Matching is unambiguous because the ids are
  distinct and the validator matches on `id` first.
- Release scope agrees: adult collections describe v3.1.0 content, pediatric collections describe
  v1.1.0 content, matching the `version` and `issued` values on the corresponding resources.

No unresolved contradiction was found within or between the two records.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | PASS — no issues found |
| Full ontology term validation | PASS |
| Core schema validation (`CoreDataset`) | PASS — no issues found |
| Core ontology term validation | PASS |
| Pair consistency, after `--sync-core` | PASS — 76 schema-identical slots, projected `resources` |
| Pair consistency, independent re-run | PASS — 76 schema-identical slots, projected `resources` |

One validator warning remains, `semantic-review-required` on
`$.file_collections <-> $.distributions`. It is the validator's standing instruction to perform
the Phase 4 semantic review, not a defect; that review is recorded above and found zero conflicts.

Both files were re-validated after the Phase 3 corrections and after `--sync-core`. The core
header contains `# Phase 4 reconciliation: completed`, names both its source-document bundle and
its same-run full YAML input, and both headers state that prior D4D factual reuse is prohibited.
