# CM4AI full/core reconciliation — 2026-08-11_claude-opus-5-claudecode-generic_rep1

- **Project:** CM4AI
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
  (10 source documents, listed in `data/preprocessed/source_manifest.yaml`)
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the CM4AI (Cell Maps for
Artificial Intelligence) dataset as published through its quarterly Dataverse
data releases**, identified as `https://cm4ai.org/`. This matches the `scope:`
declaration for CM4AI in `data/preprocessed/source_manifest.yaml`
(`referent_id: https://cm4ai.org/`; `related_but_distinct: []`), which also
states that the Dataverse releases are releases of this dataset rather than
separate datasets. The releases are therefore represented as `resources` — five
entries: DXWOS5, B35XWX (March 2025), F3TD5R (June 2025), K7TGEM (October 2025)
and HIGT4C (June 2026) — and the same choice is held in both records.

The bundle contains one source that describes a **different** resource: the 2025
Nature article "Multimodal cell maps as a foundation for structural and
functional genomics", which reports a multimodal cell map of U2OS osteosarcoma
cells built from Human Protein Atlas imaging and BioPlex-style AP–MS data and
distributed via NDEx, MassIVE, ProteomeXchange, the EBI Complex Portal and
ModelArchive. It is CM4AI-funded and shares investigators, but it is neither a
CM4AI cell line nor a CM4AI Dataverse release. It is recorded under
`external_resources` — with an explicit `source_caveats` saying so — rather than
merged into this dataset's composition, distribution or identifiers. This is the
one place in the bundle where merging distinct entities was a live risk.

## Phase 1 — full record

Structure was derived at runtime from class `Dataset` in
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` via `SchemaView`
(induced slots, ranges, required flags, cardinality, inlining, enums). No prior
D4D record was read, searched, or listed for content; only output *directory
names* were listed, to confirm the target paths were unoccupied.

Populated: 53 top-level slots, 734 populated keys including nested objects,
1,828 lines.

Three schema constraints materially shaped the record and are worth recording:

1. **`Person` is not inlined.** `Creator.principal_investigator`,
   `EthicalReview.contact_person` and
   `ExportControlRegulatoryRestrictions.governance_committee_contact` all have
   range `Person`, which carries an identifier, and none declares `inlined`.
   The JSON Schema therefore admits only a string. The structured contact
   information those slot descriptions promise ("name, email, affiliation, and
   optional ORCID") cannot be expressed. ORCID IRIs were used as the reference
   values — `https://orcid.org/0000-0002-1708-8454` (Trey Ideker),
   `https://orcid.org/0000-0003-4060-7360` (Timothy Clark),
   `https://orcid.org/0000-0002-7080-8801` (Vardit Ravitsky),
   `https://orcid.org/0000-0003-4535-3486` (Jillian Parker) — rather than bare
   names, because a bare name in a `uriorcurie` slot is exactly the
   unresolvable value `identifiers.py` (#402) reports as worse than an absent
   one. The names and emails are carried in the containing objects'
   `description` / `review_details` so nothing is lost to a reader.
   `principal_investigator`'s own description ("a person's name such as 'Aaron
   Lee'") points the other way; the two pieces of schema guidance conflict.
2. **`FileCollection` requires `id`.** It inherits the required `id` from
   `Information`. Twelve collection identifiers were minted as DOI-fragment
   IRIs (`https://doi.org/10.18130/V3/HIGT4C#collection/AP-MS-interactomes`).
   File identifiers use the same convention with the file name as the fragment.
   All 69 `uriorcurie` values in the full record classify as absolute URIs under
   `data_sheets_schema.identifiers.classify`; none is a bare token or an
   undeclared CURIE.
3. **File sizes could not be recorded structurally.** Dataverse reports rounded
   sizes ("3.8 GB", "113.3 KB"). `File.bytes` and `FileCollection.total_bytes`
   are integers, so writing them would require inventing precision the source
   does not have. `bytes` is left absent and the reported size appears in each
   file's `description`. `total_size_bytes` is omitted for the same reason; the
   project-level "21.4 TB" figure sits in the top-level `description`.

## Phase 2 — core record

Core structure was derived from class `CoreDataset` in
`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`. No older core
record was read or used as a template.

Populated: 50 top-level slots, 610 populated keys including nested objects,
1,311 lines.

The three full-record slots that core does not define, and which are therefore
absent from the core record, are `citation`, `direct_collection` and
`third_party_sharing`. Nothing else populated in full was dropped.

Core defines two slots full does not: `distributions` (`CoreDistribution`) and
`dialect` (`FormatDialect`). `dialect` is left absent — no source in the bundle
describes a CSV delimiter, header convention or comparable structural dialect.
`distributions` is the projection of the full record's `file_collections`,
described below.

Phase 2 found no core field that the bundle supports and the full record left
empty, so no fact was back-ported to full from Phase 2. The back-ports listed
below came from the Phase 3 source audit.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs were the declared bundle, `data/preprocessed/source_manifest.yaml`,
and the two LinkML schema files. No file under `data/d4d_concatenated/`,
`data/d4d_individual/` or `data/ro-crate_packages/` was read, grepped or opened
at any point, and no evaluation or reconciliation report from any earlier run was
consulted. The ABSOLUTE CONSTRAINT held for all four phases.

`d4d api prompts check --strict` passes: 10 prompt files, 0 not at their pin,
including `src/download/prompts/d4d_generic_arm_prompt.md`, the file this run's
header names. The condition is therefore `generic` at its published text, not
`uncanonical`.

### Corrections made to the full record during Phase 3

**Facts back-ported from a re-read of the bundle:**

- The Flagship Datasets block of `cm4ai.org/data-releases` gives a **third**
  protein count for the IF imaging arm — "IF images for 523 proteins" — beside
  the 563 in the March 2025 file descriptions and the 464 in the June 2025,
  October 2025 and June 2026 file descriptions. All three are now recorded in
  the IF `Instance`'s `source_caveats`; no source reconciles them and none was
  silently preferred.
- The same block states "Perturb-seq of 200 genes" for the TNBC arm and
  "Perturb-seq of >11,000 genes (whole-genome)" for the iPSC arm, and names the
  TNBC untreated condition as a **DMSO control**. Added to the perturb-seq
  `Instance`.
- The same block still advertises "AP-MS interactomes (coming soon!)" for the
  TNBC arm and "IF images (coming soon!)" for the iPSC arm, on the same page
  that presents the June 2026 release — which does distribute AP-MS
  interactomes. Recorded as a staleness conflict in the AP-MS `Instance`'s
  `source_caveats`.

**Shape corrections (values whose form did not match their slot's range):**

- `status` held a sentence ("Beta; the releases state that the data are not yet
  in completed final form"). Reduced to `Beta`; the completeness statement is
  already carried by `known_limitations`.
- `created_by` held an organisation name plus an apposition. Reduced to
  `Cell Maps for Artificial Intelligence (CM4AI)`.
- `FundingMechanism.grantor` held "National Institutes of Health (NIH Common
  Fund, Bridge to Artificial Intelligence program)". Reduced to the
  organisation name; the programme detail is in the object's `description`.
- One `DistributionFormat.format` held a prose sentence. Removed; `media_type`
  and `description` carry it.
- Release `version` values held two version representations in one string
  ("Dataverse V1; page version 1.4"). Reduced to the page-header version
  (`1.4`, `2.1`, `2.1`, `2.0`), with the citation's V-number recorded in each
  release's `source_caveats`.
- `ExportControlRegulatoryRestrictions.regulatory_restrictions` held two
  negative statements ("FDA Regulated: No", "Human Subjects: No") that are not
  restrictions. Moved to `other_compliance`; the list now holds only the actual
  access condition (the Bridge2AI Open House Code of Conduct attestation).
- `known_biases[0].affected_subsets[0]` had parsed as a mapping rather than a
  string because of an unquoted `: ` inside the value. Quoted.

**Two slots removed from both records rather than falsified.**
`conforms_to_schema` and `conforms_to_class` are statements about the record,
and they must differ between a full and a core record
(`https://w3id.org/bridge2ai/data-sheets-schema` + `Dataset` versus
`https://w3id.org/bridge2ai/data-sheets-schema/core-schema` + `CoreDataset`).
Both are classified as **schema-identical** by
`d4d_pair_consistency.load_pair_schema`, so any truthful pair fails the identity
rule on them, and `--sync-core` would "fix" it by copying `Dataset` into the
core record — a false claim. They are omitted from both records; each file's
header block states its schema path, and the provenance record will too, so no
information is lost. **This is a schema/tooling defect worth filing:** these two
slots should be excluded from the identity set, or given per-class defaults.

### Source disagreements represented rather than resolved

None of these was silently decided; each is recorded where the affected value
lives.

| Disagreement | Sources | Where recorded |
|---|---|---|
| Release date of the June 2026 release | `cm4ai.org/data-releases`: "Released on: June 17, 2025"; Dataverse HIGT4C: publication date 2026-06-17 | `distribution_dates[0].source_caveats`, HIGT4C resource `source_caveats` |
| Project end date | NIH RePORTER: 2026-08-31; release pages: "end of the project in November 2026" | `collection_timeframes[0].source_caveats` |
| IF imaging protein count | 563 / 464 / 523 (see above) | IF `Instance.source_caveats` |
| Collaborating institution list | data releases page (9, incl. Hastings Center, excl. UAlabama and Montreal); preprint (10, incl. UAlabama and Montreal, excl. Hastings Center); Dataverse affiliations (adds KTH) | `creators[0].source_caveats`; the union is recorded in `affiliations` |
| Copyright year | preprint: © 2024; Dataverse releases: © 2025 | `ip_restrictions.restrictions` (both stated) |
| Data Creation Date | 2025-02-27 on all four captured releases, including the 2026 one | `collection_timeframes[0].source_caveats` |
| Identity of "Jillian Parker" (governance contact) vs "Parker J" (author) vs "Jillian Mohan" (preprint author) | release pages, Dataverse author list, preprint author list | `regulatory_restrictions.source_caveats` — the ORCID is used, and the fact that the sources never state the identification is named |
| IF image archives, same names and sizes, different MD5s in June 2026 vs June 2025 / October 2025 | Dataverse file tables | `errata[1]` |

### Deliberate omissions

`total_size_bytes`, `total_file_count` at dataset level, `subsets`, `splits`,
`relationships`, `variables`, `anomalies`, `content_warnings`,
`confidential_elements`, `sensitive_elements`, `subpopulations`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`informed_consent`, `at_risk_populations`, `participant_privacy`,
`participant_compensation`, `data_protection_impacts`, `cleaning_strategies`,
`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`,
`missing_data_documentation`, `use_repository`, `retention_limit`,
`extension_mechanism`, `parent_datasets`, `related_datasets`, `language`,
`issued`, `created_on`, `last_updated_on`, `download_url`, `doi` (dataset
level), `version` (dataset level), `compression` (dataset level). In each case
the bundle either says nothing or says only that the concept does not apply
(e.g. no human subjects, so no consent record) — and an absent slot is the
correct answer when the evidence is absent.

Note in particular that no dataset-level `doi` is asserted: CM4AI has no
project-level DOI in the bundle, only per-release DOIs, which are carried on the
release `resources`.

### Re-validation after corrections

Both records were re-validated after every correction; results in the closing
table.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` via
`data_sheets_schema.d4d_pair_consistency.load_pair_schema`. No hand-written
field list was used.

- **Schema-identical slots: 78.** Every one is either present in both records
  with deeply identical parsed content, or absent from both. Narrative fields
  are included: core condenses, paraphrases, reorders and omits nothing.
- **Projected slots: 1 — `resources`** (`Dataset` in full, `CoreDataset` in
  core). All five release ids match exactly in both directions; coverage is
  equal; every schema-identical slot within each matched resource is deeply
  identical.

`--sync-core` was **not** needed and was not run: the core record was built as a
schema-derived projection of the Phase-3-audited full record, so it was
identical by construction. The validator was run once, without `--sync-core`, as
the independent check:

```
PASS: 78 schema-identical slots; projected slots=['resources']
```

### Related, non-identical content — semantic review

Validator warnings are not evidence that this review happened; it was performed
by hand and is recorded here.

**`file_collections` (full) → `distributions` (core).** Full carries 12
`FileCollection` objects across four releases, holding 34 `File` objects. Core
carries 34 `CoreDistribution` objects, one per file, distributed across the same
four release resources (6 / 10 / 8 / 10; the DXWOS5 resource has none in either
record, because the bundle gives it no file inventory). For each file the
projected fields — `id`, `name`, `path`, `format`, `md5`, `description` — are
byte-identical to the full record's. No name, path, format, compression,
checksum, byte count or access URL conflicts between the two records, because
none was rewritten.

Two things are genuinely lost in the projection, both inherent to `CoreDataset`
having no `FileCollection` class:

- **Collection grouping.** Which files belonged to "Protein Localization
  Subcellular Images" versus "Protein-protein Interaction SEC-MS" survives only
  where the file's `path` happens to carry the folder prefix — true for the
  March 2025, June 2025 and October 2025 releases, false for June 2026, whose
  Dataverse listing has no folders. No conflict is created; information is
  narrowed.
- **`total_file_count`.** Full-only. In three releases it equals the number of
  distributions (6, 8, 10). In the June 2025 release it is 21 while only 10
  files are enumerated, because the capture shows only the first page of the
  file table — stated in that resource's `source_caveats` in both records, since
  `source_caveats` is schema-identical and therefore carried into core.

**`total_file_count` / `total_size_bytes` versus distribution-level values.**
No dataset-level `total_file_count` or `total_size_bytes` is asserted in either
record, so there is nothing to contradict the per-release counts. Per-release
counts agree with the enumerated distributions as described above.

**`dialect`, formats, `is_tabular`.** `is_tabular: false` is identical in both
records and consistent with every distribution's `format` (ZIP, JSON, HTML —
no tabular format appears anywhere in the release inventories). `dialect` is
absent from core and has no full-record counterpart. No conflict.

**Top-level identity, version and access facts versus resources, version
history and repeated statements.** Checked and consistent:

- top-level `license: CC BY-NC-SA 4.0` matches every release resource's
  `license` and `license_and_use_terms.license_terms`;
- top-level `publisher` matches each release resource's `publisher`;
- `version_access.latest_version_doi` (`https://doi.org/10.18130/V3/HIGT4C`)
  matches the resource the record and the CM4AI site both present as the latest
  release, and `version_access.versions_available` enumerates exactly the five
  resources, with the same DOIs and version numbers those resources carry;
- `updates.frequency: Quarterly` matches the release pages' Maintenance Plan and
  the data releases page FAQ, and matches the observed release cadence;
- `citation` (full only) names the June 2026 release, the same release
  `version_access.latest_version_doi` points at.

**Historical versus current releases.** The March 2025, June 2025 and October
2025 releases are earlier releases of the same dataset, not contradictions of
the June 2026 one. Their differing file inventories, protein counts and
checksums are held inside their own resource objects and are not promoted to
dataset level, so no dataset-level value asserts a superseded fact.

## Scope check

```
d4d download scope --check --project CM4AI --strict
79 record(s) checked against the declaration
   ✓ none is about a dataset its project declares distinct
```

CM4AI declares `related_but_distinct: []`, so there is no related-dataset slot
placement to audit for this project.

## Commands run

```bash
# Phase 1 / Phase 3 — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d_core.yaml

# Provenance boundary and scope
poetry run d4d api prompts check --strict
poetry run d4d download scope --check --project CM4AI --strict
```

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d.yaml` (created, Phase 1; corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_d4d_core.yaml` (created, Phase 2; rebuilt after Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CM4AI_reconciliation.md` (this file)

No other file in the repository was modified.

## Results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` (no `--sync-core`) | PASS — 78 schema-identical slots, 0 errors, 0 warnings |
| `d4d download scope --check --strict` | in scope |
| `d4d api prompts check --strict` | canonical (10 files, 0 off-pin) |
| Identifier syntax (`identifiers.classify`) | 69/69 `uriorcurie` values are absolute URIs; 0 bare tokens, 0 undeclared CURIEs |
| Prior-D4D reuse | none — no generated record from any run was read |

**Full record:** 53 top-level slots, 734 populated keys including nested
objects, 1,828 lines, 103,849 bytes.
**Core record:** 50 top-level slots, 610 populated keys including nested
objects, 1,311 lines, 88,425 bytes.

Line and slot counts are informational metadata, not a quality gate. There was
no target density for this run.

**Outcome: clean.** After the Phase 3 corrections listed above, nothing diverged
between the pair. Every schema-identical slot is deeply identical or absent from
both; the single projected slot matches on ids, coverage and nested identity;
the two related-content mappings (`file_collections` → `distributions`, and the
full-only counts) were reviewed by hand and hold no contradiction. The one
declared exception is the deliberate omission of `conforms_to_schema` and
`conforms_to_class` from both records, explained above.

## Provenance record

Not written by this agent. The launcher records it, per the launch instruction
that overrode the corresponding step in the rendered prompt. The command it
should run is:

```bash
poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-08-11_claude-opus-5-claudecode-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
```

Reasoning effort is not asserted here: this run's route did not carry an effort
suffix and the launcher did not state one, so the honest record is an absent
field, not a guess (#397).
