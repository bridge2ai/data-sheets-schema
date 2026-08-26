# CM4AI — Phase 3 / Phase 4 reconciliation report

- **Run label:** `2026-08-24_claude-opus-5-claudecode-generic-v5_rep3`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic-v5 prompt
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- **Input manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is the one the manifest's `scope:`
block declares for CM4AI: the CM4AI (Cell Maps for Artificial Intelligence) dataset,
`referent_id` `https://cm4ai.org/`, held as **the release program as an ongoing quarterly
series**, with the individual University of Virginia Dataverse releases enumerated as
`resources`. The manifest's `referent_note` states that the Dataverse releases in the
bundle are releases of this dataset, not separate datasets, and the `retained_because`
note on `october_2025_dataverse_release` states the same pinning explicitly. The manifest
declares `related_but_distinct: []` for CM4AI, so no dataset needed expressing through
`related_datasets`. The same referent and the same `id` are held in both records.

Five releases are enumerated: `doi:10.18130/V3/DXWOS5` (cited only by the preprint),
`doi:10.18130/V3/B35XWX` (March 2025), `doi:10.18130/V3/F3TD5R` (June 2025),
`doi:10.18130/V3/K7TGEM` (October 2025) and `doi:10.18130/V3/HIGT4C` (June 2026, the
current release).

## Phase 3 — source and provenance audit

### Provenance boundary

Confirmed from the read history of this run. The only factual inputs opened were the
declared bundle, `data/preprocessed/source_manifest.yaml` (via `d4d download scope`,
`d4d download priority` and a direct read of the CM4AI project block), the full and core
LinkML schemas, and the repository playbooks (`d4d-provenance-guard.md`,
`d4d-full-core.md`, `d4d-agent.md`, `d4d-uniform-rules.md`). **No prior full or core D4D
record, from any arm, label or date, was read, opened, grepped or consulted**, and no
evaluation report or reconciliation report from an earlier run was used. Phase 2 read the
declared bundle plus the exact Phase 1 full record under this run's own label. The output
directory for this label contained no CM4AI file at the start of the run, so no phase was
resumed and nothing was skipped.

### Source disagreements resolved

The manifest ranks CM4AI's sources in five tiers: data resource (tier 1), documentation
and license (tier 2), publication and preprint (tier 3), NIH project page (tier 4),
historical data release (tier 5).

| Disagreement | What each source says | Resolution |
|---|---|---|
| Date of the June 2026 release | `data_release_documentation` (tier 2) gives "Released on: June 17, 2025"; `june_2026_dataverse_release` (tier 1) gives publication date 2026-06-17, with files published 2026-06-17 and 2026-07-15 | Tier 1 preferred. `2026-06-17` recorded in `distribution_dates` and in the release resource's `issued`; disagreement recorded in `source_caveats` on both. The input manifest records the same discrepancy in its own curation note. |
| Affiliation of Sali A | Dataverse release records (tier 1) give University of California San Diego; the preprint (tier 3) and the Nature article (tier 3) give University of California San Francisco | Tier 1 preferred; UCSD recorded, disagreement recorded in `source_caveats` on that creator. |
| End of the project period | NIH RePORTER (tier 4) gives project end 2026-08-31; Dataverse release records (tier 1) give "the end of the project in November 2026" | Tier 1 preferred, but it states only a month, so no `end_date` is written to the structured field. Both values and the reason are recorded in `collection_timeframes[0]`. The start date, 2022-09-01, is uncontested and is recorded. |
| Release version number | Every Dataverse release page header and its own recommended citation disagree (1.4 vs V1; 2.1 vs V2; 2.0 vs V2) | Same source, same rank, so the ranking cannot decide. The page-header value is recorded in `version` and the citation form is preserved verbatim in `citation`, with the disagreement named in each release's `source_caveats`. |
| Consortium membership | The March 2025 release (tier 1) lists UCSD, UCSF, Stanford, UVA, Yale, UA Birmingham, Simon Fraser University and the Hastings Center; the data releases page (tier 2) adds UT Austin; the preprint (tier 3) lists ten institutions including the University of Montreal | Not asserted as a single membership list. Institutional attribution is carried per person through `creators[].affiliations`, taken from the current (tier 1) release author list, so no source's list had to be selected over another's. |

### Unsupported, stale or mis-scoped assertions checked for

- **Nature article scope.** The bundle contains "Multimodal cell maps as a foundation for
  structural and functional genomics" (Nature 642, 222–231, 2025), which reports a
  multimodal cell map of U2OS osteosarcoma cells and acknowledges the same Bridge2AI award
  (OT2 OD032742). Its data are deposited at NDEx, MassIVE (MSV000097168), ProteomeXchange
  (PXD052362) and ModelArchive rather than in the CM4AI Dataverse releases, and no release
  record enumerates them. Nothing from that study is represented as a component of this
  dataset: it is carried as an external resource and a related publication, with the
  distinction stated in `source_caveats` on both the top-level record and that
  `external_resources` entry. For the same reason `labeling_strategies`,
  `annotation_analyses` and `machine_annotation_tools` are **absent**: the annotation
  jamborees and GPT-4 assembly naming belong to the U2OS study, and every CM4AI release
  states that computed cell maps are not included.
- **Stale "coming soon" statements.** The data releases page marks AP-MS interactomes for
  the TNBC series as coming soon, but the June 2026 Dataverse release contains AP-MS data
  for MDA-MB-468 with treatment. Both facts are recorded and the staleness is named in
  `missing_data_documentation[0].source_caveats`.
- **Aggregate versus per-release counts.** 53,788 immunofluorescent images and 1,374
  protein interactions come from the project-wide Data Insights panel, not from any
  release. Recorded in `instances[].counts` with that scope stated in `source_caveats`.
  The per-release protein counts differ legitimately across releases (563 proteins in the
  March 2025 image archives, 464 in June 2025 and October 2025) and are recorded per
  release rather than reconciled to one figure.
- **Rounded byte sizes.** Dataverse displays file sizes as rounded values ("3.8 GB",
  "343.4 KB"). `File.bytes`, `FileCollection.total_bytes` and `total_size_bytes` are
  integers, and writing one would assert a precision the source does not have, so they are
  **absent** and the displayed size is stated in each file's `description`. The project's
  "21.4 TB" data volume figure is likewise carried in prose, not converted to an integer.
- **Identifiers.** No registry identifier was supplied from model knowledge. The only ROR
  in the record, `ROR:0153tk833`, is the one the June 2026 release record itself prints in
  place of an affiliation name for five University of Virginia authors; the name attached
  to it comes from those same authors' affiliation strings in the other three releases.
  ORCIDs are those the release author lists print. Where the bundle supplies no identifier
  for an organization (every affiliation other than the University of Virginia), the
  organization carries a name only.

### Internal consistency verified

- Every MD5 checksum written into the record occurs verbatim in the bundle (34 of 34).
- Every asserted count occurs verbatim in the bundle: 53,788; 1,374; 7,023; 11,739;
  5,289,382; and the four download counts 302, 256, 405 and 181.
- Per-release `total_file_count` equals the sum of `file_count` over that release's
  collections for March 2025 (6), October 2025 (8) and June 2026 (10). For June 2025 the
  record states `total_file_count: 21` while the collections cover 10 files, because the
  captured page lists only 10 of 21; this is stated in that release's `source_caveats`.
- `version_access.latest_version_doi` resolves to a release present in `resources`, and
  every entry of `versions_available` matches its resource's `version` and `issued`.
- `distribution_dates` agree with the `issued` of the corresponding release resources.
- `license` and `publisher` are identical at the top level and on all five releases;
  `status: Beta` is held at the top level and on the four releases the bundle labels
  "(Beta)". `doi:10.18130/V3/DXWOS5` carries no `status` and no `issued` because the
  preprint, its only source, gives neither — an absence, not a contradiction.

### Shape audit and corrections applied in Phase 3

Six corrections were made to the full record and then carried into core by re-deriving
the projection. No fact changed; every correction moved content into the field that asks
for it or removed a restatement.

1. `human_subject_research.regulatory_compliance` **removed**. It held a restatement of
   `involves_human_subjects`, `is_deidentified` and the FDA status rather than a
   regulatory framework, which the bundle names for none.
2. `regulatory_restrictions.regulatory_restrictions` trimmed to the FDA statement alone,
   for the same reason.
3. `external_resources` entry "External data repositories linked from the release records"
   **removed**. Its `external_resources` list held link labels ("MassIVE Repository",
   "NCBI BioProject", "Figshare") rather than links or identifiers, because the captured
   pages preserve the label and not the target URL. The same content is carried properly
   by the seven `raw_data_sources` entries, whose `access_details` say exactly that.
4. The "under review for potential modification" notice was removed from the CM4AI portal
   `external_resources.restrictions` and kept once, in `retention_limit`, where continued
   availability is the subject.
5. `prohibited_uses[1].description` trimmed so the copyright-holder list stays in
   `ip_restrictions` and the Data Access Committee stays in `data_governance`.
6. The October 2025 release's single mixed `Measurement and release metadata archives`
   collection was split into three (`SEC-MS results`, `Perturb-seq packages`,
   `Release metadata`), so that each `collection_type` describes what its collection
   actually holds, matching the structure used for the June 2026 release.

A seventh correction was required by the schema rather than by the audit and was applied
during Phase 1: `Creator.principal_investigator`, `EthicalReview.contact_person` and
`DataGovernance.committee_contact` all have range `Person` and are **not inlined**, so
they take a Person identifier and not a Person object. Each now holds the person's ORCID
CURIE, and the name, email and affiliation that the object would have carried are stated
in the neighbouring `description` / `review_details` so nothing is lost.

### Facts back-ported from Phase 2 to Phase 1

None. Phase 2 derived core from the validated Phase 1 record plus the bundle and found no
core field that the bundle supports and the full record left empty, and no value on which
the bundle and the full record disagreed. The Phase 3 corrections above were made to the
full record first and core was then re-derived from it.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot inventory

Derived at runtime with LinkML `SchemaView` from `Dataset` in
`data_sheets_schema_all.yaml` and `CoreDataset` in `data_sheets_schema_core_all.yaml`. No
hand-written field list was used.

- **82** slots are shared between the two classes.
- **81** of those have the same induced range and cardinality. Of these, **79** are
  compared for deep identity; `conforms_to_class` and `conforms_to_schema` are exempt as
  per-record slots that must differ, and they do: `Dataset` versus `CoreDataset` for the
  class, with the same schema URI on both.
- **1** shared slot is a projection: `resources`, which is `Dataset` in full and
  `CoreDataset` in core.
- **16** slots are full-only: `file_collections`, `total_file_count`, `total_size_bytes`,
  `subsets`, `relationships`, `splits`, `direct_collection`, `collection_notifications`,
  `collection_consents`, `consent_revocations`, `participant_privacy`,
  `participant_compensation`, `third_party_sharing`, `variables`, `citation`,
  `parent_datasets`. Of these the record populates four: `file_collections` (inside the
  release resources), `total_file_count` (likewise), `direct_collection` and
  `third_party_sharing`, plus `citation` on each release resource.
- **2** slots are core-only: `distributions` and `dialect`. `distributions` is populated
  from the projection described below; `dialect` is **absent**, because the bundle
  describes no format dialect.

### Deep-identity result

```
PASS: 79 schema-identical slots; projected slots=['resources'];
per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']
```

Every schema-identical shared slot is present in both records or absent from both, and
every parsed value is deeply identical including nested mapping values and list order.
Narrative fields are included: nothing in core is condensed, paraphrased, reordered or
omitted relative to full. The validator was run **without** `--sync-core` and passed on
the first run, so no synchronization step was needed and none was performed.

### Projection: `resources`

Full and core carry the same five releases in the same order, matched by `id`, so
coverage is equal. For each release every nested slot that both `Dataset` and
`CoreDataset` declare is deeply identical: `id`, `name`, `title`, `doi`, `version`,
`status`, `license`, `publisher`, `page`, `issued`, `created_on`, `conforms_to`,
`conforms_to_standard`, `description` and `source_caveats`. The full-only nested slots
`file_collections`, `total_file_count` and `citation` are omitted from the core
projection, as the core schema requires.

### Related-content mapping: `file_collections` → `distributions`

Each `File` inside a release's `file_collections` maps to one `CoreDistribution` in that
release's `distributions`, in the same order. **34 file/distribution pairs** were compared
field by field across `id`, `name`, `path`, `format`, `media_type`, `compression`, `hash`
and `description`: **zero conflicts**. Checksums, paths, formats, compression and release
scope agree on every pair, and no distribution carries a key its `File` does not.

Two `File` fields are not carried into core because `CoreDistribution` does not declare
them: `issued` (each file's publication date) and `file_type`. This is a schema-imposed
loss in the projection, not a divergence — nothing in core contradicts them.

The grouping level differs by design and does not conflict: full groups files into named
`FileCollection` objects with `collection_type`, `file_count` and a `path`, while core
holds a flat list of distributions. The collection descriptions therefore survive only in
full. `total_file_count`, which is full-only, is consistent with the number of files in
each release's collections as reported in the Phase 3 consistency checks above.

### Access, identity and version facts

`is_tabular`, `compression`, `download_url`, `language`, `created_by`, `modified_by`,
`was_derived_from` and `last_updated_on` are **absent from both records**: the bundle
supports none of them at the level of the release program. `total_size_bytes` is absent
for the reason given in Phase 3. There is no historical-versus-current contradiction to
resolve: each release is a separately published, separately citable dataset with its own
DOI and version history, and the record says so in `version_access.version_details`
rather than treating the differing per-release values as conflicting.

### Grounding check

```
{'grounded': 44, 'minted_fragment': 51, 'absent': 0}
```

**Zero identifiers are absent from the bundle.** The 51 minted fragments are the ids of
the `FileCollection` and `File` objects (and, in core, of the distributions): each names a
part of this dataset with no referent outside the record, and each is hung as a fragment
on the DOI CURIE of the release it belongs to — for example
`doi:10.18130/V3/HIGT4C#cm4ai_apms_MDA-MB-468_paclitaxel.zip`. No new prefix was invented;
every identifier uses `doi:`, `ORCID:` or `ROR:` from the schema's declared prefixes, or a
resolvable URL where no declared prefix fits (`https://cm4ai.org/` for the dataset itself,
`https://dataverse.lib.virginia.edu/` for the publisher, and the ontology IRIs on
`Instance.data_topic`, for which the schema declares no prefix).

### Prompt condition

The run was launched under `generic_v5`, from
`src/download/prompts/d4d_generic_arm_prompt_v5.md`, rendered to
`/tmp/agentic_fanout/CM4AI_rep3.md`. Both file headers name the condition on their
`# Mode:` line and the prompt file on their `# Prompt:` line. The canonical-pin status of
that prompt is reported by `d4d api prompts check` and `d4d runs check`; the outcome of
`d4d runs check --strict` for this run is recorded with the run.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d.yaml` (created, Phase 1; corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d_core.yaml` (created, Phase 2; re-derived in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_reconciliation.md` (this report)

No file outside this run's three declared outputs was written.

## Commands run

```bash
# scope and source ranking
poetry run d4d download scope --project CM4AI
poetry run d4d download priority --project CM4AI

# Phase 1 validation
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 validation
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 pair consistency (run without --sync-core; passed first time)
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CM4AI_d4d_core.yaml

# Phase 4 grounding check
poetry run python -c "
from pathlib import Path
from data_sheets_schema.grounding import check_run
from data_sheets_schema.identifiers import uriorcurie_slots
r = check_run(Path('.../CM4AI_d4d.yaml'), Path('.../CM4AI_d4d_core.yaml'),
              Path('data/preprocessed/concatenated/CM4AI_preprocessed.txt'), uriorcurie_slots())
print(r['distinct'])"

# Phase 4 report-claims check
poetry run python -c "
from pathlib import Path
from data_sheets_schema.report_claims import check_report, declared_slots
import yaml
full = yaml.safe_load(Path('.../CM4AI_d4d.yaml').read_text())
core = yaml.safe_load(Path('.../CM4AI_d4d_core.yaml').read_text())
out = check_report(Path('.../CM4AI_reconciliation.md'), full, core, declared_slots())
[print(f) for f in out['findings']]"

# provenance and gates
poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt ...
poetry run d4d runs check --strict
poetry run d4d download scope --check --project CM4AI
```

## Final results

| Check | Result |
|---|---|
| `linkml-validate`, full, class `Dataset` | No issues found |
| `linkml-term-validator`, full | Validation passed |
| `linkml-validate`, core, class `CoreDataset` | No issues found |
| `linkml-term-validator`, core | Validation passed |
| `d4d_pair_consistency` (no `--sync-core`) | PASS — 79 schema-identical slots deeply identical |
| Grounding against the bundle | 44 grounded, 51 minted fragments, **0 absent** |
| File → distribution semantic review | 34 pairs, **0 conflicts** |
| Checksums traced to the bundle | 34 of 34 |

Populated slot counts, informational only and not a quality gate: the full record has 56
top-level slots and 1,063 populated slots counting nested objects, in 1,795 lines; the
core record has 54 top-level slots and 860 populated slots, in 1,302 lines. The
difference is accounted for entirely by the full-only slots listed above and by the
`File` fields `CoreDistribution` does not declare.

**Nothing diverged between the two records.** Every schema-identical shared slot is
deeply identical, the one projected slot has equal coverage and deep identity on every
nested schema-identical field, and the one related-content mapping has zero conflicts
across all 34 pairs. No repair was required, so no `repair` phase and no
`report_after_repair` phase were performed or recorded.
