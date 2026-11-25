# CM4AI reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2`
- Method: `claudecode_release`; arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic-v9 prompt
- Agent runtime: Claude Code (release); provider: Anthropic; model: claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). No sampling
  setting was observed or inferred in this run.
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CM4AI_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CM4AI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CM4AI_coverage_receipt.yaml`
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
  (md5 `50037fc631eafda807e19f83f6579818`, 7866 lines, 28 chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Chunk manifest: `data/preprocessed/chunks/CM4AI_chunks.yaml`

## Referent

The declared scope names the referent as "CM4AI (Cell Maps for Artificial
Intelligence) dataset" with the identifier `https://cm4ai.org/`, declares no
related-but-distinct dataset, and notes that the Dataverse releases in the
bundle are releases of this dataset, not separate datasets.

The record holds to that referent:

- `id` is `https://cm4ai.org/`, the identifier the manifest declares and the
  bundle carries as the source URL of the project site.
- `doi`, `version`, `status`, `issued`, `citation`, `total_file_count` and
  `file_collections` describe the June 2026 Data Release (Beta), which the
  project's data-releases page presents as the latest release. The record's
  top-level `source_caveats` says so.
- The May 2024, March 2025, June 2025 and October 2025 releases are recorded
  as versions under `version_access`, not as `related_datasets`, because the
  scope declares them releases of the same dataset. `related_datasets` is not
  populated: no passage states a typed relation to any other dataset.
- The file collection carries the release DOI as its `id`
  (`doi:10.18130/V3/HIGT4C`), an identifier the evidence states for that part.
  The ten file ids are labels minted on the record's own id
  (`https://cm4ai.org/#june-2026-release-<file name>`), since the bundle states
  no identifier for individual files.

The bundle's first source is a Nature article about a U2OS osteosarcoma cell
map (chunks c002 to c009). Its subject is that study's map, and a search of the
bundle found no passage in the CM4AI sources (lines 2894 to 7866) that cites it
or names U2OS. No value in the record is taken from its description of that
map. One receipt comes from it: the line pairing the full name "Trey Ideker"
with the ORCID that the release page lists for author "Ideker T".

## Phase 1 - full generation

All 28 chunks were opened with the file-reading tool in manifest order and
each has a receipt entry. Three departures from the prescribed order, recorded
here as they happened:

1. The edit that should have written the c008 entry failed on a string
   mismatch, so c009 was read before c008's entry existed. Both entries were
   written immediately afterwards.
2. c021 and c022 were read in one window (c022 is five lines), so c022 was
   read before c021's entry was written.
3. Receipt entries were first written with provisional slot paths while
   reading, then re-addressed to the final record's paths once the record was
   composed, before Phase 2. No chunk changed status in that correction. Slots
   that the first-pass entries anticipated and the record does not carry (a
   website program-manager contact as a maintainer, machine annotation tools,
   an access-review process, data subsets, related-dataset entries) have no
   receipt because they have no value.

Two further process notes. The executable playbook view was first redirected
to a scratch file under `.temp/`, compared with the source playbook and then
deleted; nothing of the run remains there. The `Dataset` schema structure was
read by printing the repository's own schema digest
(`data_sheets_schema.schema_digest.digest_text`) to the terminal and by
inspecting class attributes of
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml`; no digest file was
written.

Phase 1 validation: schema validation "No issues found"; term validation
"Validation passed"; strict receipt check before Phase 2: chunks 28/28
reviewed, snippets 246/246 verified, slots 339/339 with a receipt (32 exempt).

## Phase 2 - core derivation

The core was derived by `derive core` from the validated full record. The
facts printed by the final derivation (after the last full-record correction):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CM4AI_d4d.yaml", "md5": "63f505fb7e4efb06722543f208037b52"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derivation ran four times in all: once in Phase 2 (full record md5
`8c92ef995c536ca27a6bb6c78f17c4a7`) and three times in Phase 4 with
`--phase4-complete` (full record md5 `85db06e1db4db28c2fb915ddc0563655`,
`f14f128d3e2fa49f20f435c56d8834a6` and `63f505fb7e4efb06722543f208037b52`).
The core was never edited by hand.

## Phase 3 - source and provenance audit

### Provenance

- Factual inputs read: the declared bundle, the source manifest (scope, naming
  and priority declarations) and the two schema files. Repository playbooks,
  the provenance guard, the uniform rules and the receipt and grounding
  validator sources were read as instructions and instruments.
- No previously generated D4D record, evaluation or reconciliation report was
  opened. The label's output directories already held files of two sibling
  projects (AI_READI, CHORUS); their names were listed when the directories
  were inspected and none was read.
- The only generated YAML read was this run's own full record, core record and
  coverage receipt.

### Source conflicts

| Subject | Sources and values | Resolution |
|---|---|---|
| Publication date of the June 2026 release | Dataverse release page (tier 1): 2026-06-17. Project data-releases page (tier 2): "Released on: June 17, 2025" | Genuine conflict on one release's date. The higher-ranked Dataverse value is stated in `issued` and `distribution_dates`; both values are in the top-level `source_caveats` |
| Affiliation of author Sali A | Dataverse release page (tier 1): University of California San Diego. Preprint (tier 3): University of California San Francisco | Genuine conflict. The Dataverse value is stated; both are in that creator's `source_caveats` |
| AP-MS data | Dataverse release page (tier 1): AP-MS data included. Project data-releases page (tier 2): "AP-MS interactomes (coming soon!)" | The release page is preferred; both are in `instances[2].source_caveats` |
| End of project | Release maintenance plan: "end of the project in November 2026". NIH RePORTER: "Project end: 2026-08-31" | Not treated as a conflict: one is the project's own statement, the other the end date of an award record. Each is recorded where its source places it (`updates.update_details`, `funders[0].grants[1].description`) |

### Findings

Nine findings were recorded. Counted from the rows below: 2 medium, 4 low and
3 informational (2 + 4 + 3 = 9); 6 led to a change in the full record and 3
did not.

| No. | Severity | Slot | Finding | Outcome |
|---|---|---|---|---|
| F1 | medium | `ethical_reviews[0]`, `ethical_reviews[1]` | The entry-level `description` held a note on where the name was transcribed from, which is evidence commentary | Corrected: the note now sits in each entry's `source_caveats`, which also says the page describes no review process, body or outcome |
| F2 | low | `retention_limit.retention_details` | Long-term preservation was stated without the "Maintenance Plan" heading that governs it | Corrected: the value now attributes it to the release's maintenance plan |
| F3 | medium | `instances[0]` | Perturb-seq data for MDA-MB-468 cells was stated as included without the qualifier the same page supplies: its file list names perturb-seq archives for KOLF2 only and its external data links mark perturb-seq data as "Embargoed" | Corrected: `instances[0].source_caveats` added; the supported description is kept |
| F4 | low | `instances[3].source_caveats` | "per treatment condition" was a unit the source does not use for the 464 and 563 protein figures | Corrected: reworded to the unit the source uses, each image archive's file description |
| F5 | low | `preprocessing_strategies[0].used_software` | The preprint states the FAIRSCAPE framework's URL and license; the record named the software only in prose | Added from the bundle, with receipts in c011 and c012. This is an addition, not a relocation |
| F6 | low | `updates.update_details` | The Dataverse collection's notice of review for potential modification was not recorded beside the project site's equivalent notice | Added from the bundle, with a receipt in c026 |
| F7 | informational | `data_governance.committee_contact.id` | The ORCID is listed for author "Parker J" (University of California, San Diego); the governance line names "Jillian Parker" with a UC San Diego health address. The bundle does not state in one place that they are the same person | Kept, with the join stated in that object's `source_caveats` |
| F8 | informational | `publisher` | The value is the host root of the release's landing URL; the bundle names the publisher as "University of Virginia Dataverse" and states no registry identifier for it | Kept as a resolvable URL the evidence supplies; no registry identifier was added |
| F9 | informational | (record scope) | The Nature article in the bundle describes a U2OS map that no CM4AI source cites | No value taken from it; noted in the top-level `source_caveats` |

### Other checks made in the audit, with no finding

- All 47 creators were compared with the author rows of the June 2026 release
  page, entry by entry, including each ORCID. Five authors' affiliations are
  given on that page only as a ROR URL; the record carries the ROR as a CURIE
  and does not add an organization name the page does not give.
- `principal_investigator` is populated only for Trey Ideker, whom NIH
  RePORTER designates with that title for the CM4AI data generation project.
  The Dataverse "Point of Contact" is recorded as that role under
  `maintainers`, not promoted.
- Counts: `total_file_count` and `file_collections[0].file_count` restate the
  page's "1 to 10 of 10 Files". The project-site figures (1,374 protein
  interactions, 53,788 immunofluorescent images, 7,023 proteins, 11,739 genes,
  21.4 TB) are quoted in `description` with the site's own labels and are not
  entered as instance counts, because the site does not break them down by
  release.
- Plans are stated as plans: future delivery of cell maps, future addition of
  predicted cell maps, the Data Access Committee the preprint says will
  supervise distribution, and the maintenance plan.
- Privacy: `is_deidentified` quotes the page's "De-identified Samples: Yes"
  and the preprint's statement; no method and no presence boolean is asserted.
  `human_subject_research.involves_human_subjects` is false on the page's
  "Human Subjects: No".
- Enumerations: `bias_type`, `limitation_type`, `collection_type` and
  `Maintainer.role` are left empty because no passage states the category.
  `data_use_permission` carries `no_commercial_use` on the license deed's
  NonCommercial term. File `format`, `file_type` and `media_type` are read from
  the file names and the page's "ZIP Archive" label.
- Facts about earlier releases are confined to `version_access` or carry an
  explicit attribution to the release page that states them.
- Not recorded, by decision: file sizes in bytes (the page gives rounded
  units only), a dataset creation date (see top-level `source_caveats`),
  `conforms_to` for the current release (RO-Crate packaging is stated for the
  2024 and 2025 releases, not for the June 2026 page), the project-site
  program-manager contact, and the depositor.

## Phase 4 - re-derivation, checks, report

### Corrections made in Phase 4

Two changes to the full record, both from the semantic review; the core was
re-derived after each.

| No. | Slot | Change |
|---|---|---|
| R1 | `file_collections[0]` | The release title was carried in `title`, which the core distribution does not share, so the core's collection-level distribution had no label. The value now sits in `name`; the collection has no `title` |
| R2 | `external_resources[0].description` | Reworded to what the preprint states (citation of the article is among the attribution requirements for the datasets); its receipt now quotes that sentence |

No repair phase ran: the grounding check, the report-claims check and the
final pair-consistency run reported nothing that required a change.

### Deterministic checks on the final pair

- Pair consistency: PASS, 79 schema-identical slots, projected slots
  `resources`, per-record slots `conforms_to_class` and `conforms_to_schema`.
  One warning, `semantic-review-required` on `file_collections` and
  `distributions`: 11 deterministic matches (1 at collection level, 10 at
  nested resource level), no unmatched core distribution.
- Grounding: 40 distinct identifiers grounded, 0 minted fragments, 0 absent.
- Scope check: 2 records checked against the declaration; none is about a
  dataset the project declares distinct.
- Receipts (strict, final full record): chunks 28/28 reviewed; snippets
  255/255 verified; slots 342/342 with a receipt, 35 exempt. Reported
  diagnostics: 1 snippet bearing on no token of its value and 1 entry receipt
  overlapping one leaf. The per-snippet list is written by the `--write` run
  that follows the provenance record.
- Schema and term validation: both records pass (see Final results).

## Claims

No slots were removed.

Two nested keys changed home inside their own entries (F1: the note under
`ethical_reviews` entries moved to `source_caveats`; R1: the file collection's
label moved to `name`). No top-level slot left either record, and no slot was
found to be undeclared in either schema.

## Semantic review

- `file_collections` and `distributions` (the checker's `semantic-review-required` warning): the core's eleven distributions were read against the full record's one collection and ten files. Ids, names, descriptions, formats, media types and hashes agree; the collection-level distribution lacked a label because the full record held it in `title`. The label was moved to `name` in the full record and the core re-derived. **reviewed: corrected**
- Counts and sizes against the entries beneath them: `total_file_count` is 10, `file_collections[0].file_count` is 10 and ten File entries are listed; no `total_size_bytes`, `total_bytes` or `bytes` value is recorded, so no size total can disagree with its parts. **reviewed: consistent**
- `dialect` and `is_tabular` against the files: neither is populated in either record; the ten files are ZIP archives and no File entry carries a dialect, so none was derived. **reviewed: consistent**
- Historical versus current release: `doi`, `version`, `status`, `issued`, `citation` and the file list are those of the June 2026 release; statements about the 2024 and 2025 releases sit in `version_access` or name the release page they come from. **reviewed: consistent**

## Files changed

- Created: the full record, the core record, the coverage receipt and this
  report, at the paths listed at the top.
- No other file in the repository was created or modified by this run before
  the provenance step.

## Commands

Run from the checkout root, in this order (validation commands were repeated
after every full-record change):

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project CM4AI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 --project CM4AI --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c "<grounding check_run program from the playbook>"
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI --check --record <full> --record <core> --strict
.venv/bin/python -c "<report-claims check_report program from the playbook>"
```

The chunk check reported `current`: 28 canonical chunks under the selected
rule. The declared source priority places the October 2025 and June 2026
Dataverse releases in tier 1, the project site, data-releases page and license
in tier 2, the Nature article and the preprint in tier 3, the NIH RePORTER page
in tier 4, and the March 2025 and June 2025 Dataverse releases in tier 5.

## Final results

- Full record: schema validation "No issues found"; term validation
  "Validation passed". 43 populated top-level slots; 842 lines; md5
  `63f505fb7e4efb06722543f208037b52`.
- Core record: schema validation "No issues found"; term validation
  "Validation passed". 43 populated top-level slots; 686 lines; md5
  `7bf89ad50c81ed59b8fcd374e163d531`. Header carries
  `# Sources:` naming the same-run full record and
  `# Phase 4 reconciliation: completed`.
- Reconciliation outcome: pair consistent after three derive-and-check loops
  in Phase 4; nine Phase 3 findings (six corrected, three kept with stated
  reasons); two Phase 4 semantic-review corrections; no repair phase.
- Line and slot counts are informational, not a quality measure.
- Not verified by this run: that each receipt snippet entails the value it
  sits under beyond the validator's literal match, and that the chunks marked
  `nothing_relevant` hold nothing a different reading of scope would use.
  Those remain review work, addressable by chunk id and slot path.
