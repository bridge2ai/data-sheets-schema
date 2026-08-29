# CM4AI reconciliation report

- **Run label**: `2026-08-28_claude-opus-5-claudecode-generic-v6_rep2`
- **Mode**: four-phase project agent, generic-v6 prompt
- **Arm**: BASELINE (input documents only)
- **Runtime / provider / model**: Claude Code / Anthropic / claude-opus-5
- **Declared input bundle**: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
  (md5 `1dfd34e5610fed7c22bea1f09c0bc60c`, 28 chunks in
  `data/preprocessed/chunks/CM4AI_chunks.yaml`, reported `current` by
  `d4d bundle chunk --check --project CM4AI`)
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_d4d_core.yaml`
- **Coverage receipt**: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the CM4AI dataset as the
project distributes it**: the AI-ready multimodal cell-architecture data of the
MDA-MB-468 breast cancer line and the KOLF2.1J iPSC line, published as a quarterly
numbered release series in LibraData, the University of Virginia's Dataverse. This
matches the manifest's `scope:` declaration (`referent: CM4AI (Cell Maps for
Artificial Intelligence) dataset`, `referent_id: https://cm4ai.org/`,
`referent_note`: the four Dataverse releases are releases of this dataset, not
separate datasets). The four releases are carried in `resources`, keyed by their
own DOIs; the record's top-level distribution slots describe the current (June
2026) release.

**The one scoping judgement worth stating.** The bundle's highest-content source by
volume is the Nature article *Multimodal cell maps as a foundation for structural
and functional genomics* (chunks c002-c009, roughly a third of the bundle). It
reports a **U2OS** osteosarcoma cell map, acknowledges the same Bridge2AI award
(OT2 OD032742), and is deposited in NDEx, MassIVE, ProteomeXchange and
ModelArchive. It is named in none of the CM4AI release inventories, whose cell
systems are MDA-MB-468 and KOLF2.1J, and none of its deposits appear on any release
page. Treating it as part of this dataset's composition would have merged two
distinct entities. It is therefore represented as a related publication and set of
external resources (`external_resources` entry *Multimodal cell maps publication
and its deposits*), and none of its counts (5,147 proteins, 275 assemblies, 36,842
interactions, 20,660 images), protocols (Leica SP5 imaging, DIA-NN search
parameters, HiDeF, AlphaFold-Multimer) or separate funders (Schmidt Futures, the
Cancer Cell Map Initiative, Knut and Alice Wallenberg Foundation, NHGRI U24
HG006673, and the rest of its acknowledgements) were carried into this record's
composition, collection or funding slots. The choice is recorded in the record's
top-level `source_caveats` and is held consistently across both records. Where the
Nature methods describe a step the CM4AI preprint independently attributes to the
CM4AI pipeline — node2vec PPI embedding, the Human Protein Atlas image-embedding
model — the CM4AI preprint is the source cited and the Nature text supplies only
corroborating software detail.

## Phase 1 - Full D4D generation

Generated from the declared bundle and the LinkML schemas only. Structure was
derived from class `Dataset` in `data_sheets_schema_all.yaml` via
`linkml_runtime.SchemaView` (induced slots, ranges, cardinality, inlining, enum
permissible values, declared prefixes). No prior D4D record, evaluation, report or
example was read.

All 28 manifest chunks were read with the file-reading tool in manifest order, and
each chunk's coverage-receipt entry was written before the next chunk was read.

```
poetry run d4d bundle chunk --check --project CM4AI      # current
poetry run linkml-validate -s .../data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema .../data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label <VERSION> --project CM4AI --strict
```

Receipt result: **chunks 28/28 reviewed, snippets 328/328 verified, no findings**
(209 of 472 populated slots carry a receipt; 21 exempt). Six chunks are recorded
`nothing_relevant` and one `redundant_with`, each with its reason: c001 (bundle
preamble and table of contents), c006 and c013 (bibliographies), c009 (nature.com
site chrome), c022 and c025 (Dataverse UI dialog labels and footers), c028
(redundant with c019, c021 and c024).

## Phase 2 - Core derivation

One command, no model judgement:

```
poetry run d4d derive core --full <full> --out <core>
```

Derivation facts as the command printed them:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_d4d.yaml",
          "md5": "4193930ac8855ecba31e066664e6d9fd"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"],
                        "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]},
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

`dialect` is absent because no `File` entry in the full record carries one. The md5
recorded above is the corrected full record; the derivation was re-run after every
Phase 3 correction.

## Phase 3 - Source and provenance audit

**Provenance.** Every factual input was on the phase allowlist: the declared bundle,
`data/preprocessed/source_manifest.yaml` (read for scope, source ranking and the
project's canonical label), and the two schema files. No prior full or core D4D was
read, and none was searched for. The output directory contains another project's
files from a concurrent run under the same label; they were not opened.

**Source disagreements**, resolved by `source_priority` in the manifest (lowest tier
strongest) and recorded in a caveat rather than silently selected:

| Disagreement | Sources | Resolution |
|---|---|---|
| Release date of the current release | data releases page (tier 2) displays "Released on: June 17, 2025" under the heading "June 2026 Data Release"; the HIGT4C Dataverse record (tier 1) gives Publication Date 2026-06-17 | Tier-1 value used; recorded in `resources[0].source_caveats` and `distribution_dates[0].source_caveats` |
| Proteins imaged per MDA-MB-468 condition | 464 (October 2025 and June 2026 releases, tier 1); 563 (March 2025 release, tier 5); 523 (data releases page, tier 2) | Tier-1 value 464 used; all three recorded in `instances[4].source_caveats` |
| Collaborating institutions | data releases page (tier 2) names 9 including UT Austin and the Hastings Center; March 2025 release (tier 5) omits UT Austin; the preprint (tier 3) names University of Alabama and University of Montreal and not the Hastings Center | Tier-2 list used for `creators[0].affiliations`; the other two recorded in `creators[0].source_caveats` |
| Project end | NIH RePORTER (tier 4) gives 2026-08-31; release pages (tiers 1-5) say "through the end of the project in November 2026" | Both recorded: RePORTER dates in `collection_timeframes[0].start_date`/`end_date`, the November 2026 maintenance statement in `updates.update_details`, the disagreement in `collection_timeframes[0].source_caveats`. The two are not the same claim (award end vs maintenance commitment), so neither was overwritten |
| Award number form | `1OT2OD032742-01` (cm4ai.org and Dataverse funding metadata); `3OT2OD032742-01S2` with core `OT2OD032742` (NIH RePORTER); `OT2 OD032742` (Nature acknowledgements) | `1OT2OD032742-01` used as `grant_number`; all three recorded in `funders[0].source_caveats` |
| March 2025 release version | page heading "Version 1.4"; data citation on the same page "V1" | Heading value used; both recorded in `resources[3].source_caveats` |

**Corrections made to the full record in this phase** (all applied to the full
record only; the core was re-derived afterwards):

1. **Removed 81 minted property identifiers.** Phase 1 minted
   `https://cm4ai.org/#…` fragment ids on every `DatasetProperty` entry (purposes,
   tasks, creators, funders, instances, limitations, distribution formats and the
   rest). `DatasetProperty.id` is declared optional, and no value in the record
   points at any of them, so under the v6 rule they were labels nothing used —
   noise that reads as structure. They were removed. The identifiers that remain
   are the ones the schema requires or the evidence supplies: the dataset's own
   `id`, the four release DOI CURIEs, the schema-required `FileCollection` and
   `File` ids (minted as fragments on the attested release DOI, and pointed at by
   the core's derived `distributions`), the required `Software` ids (both attested
   URLs), one `Person` id (an attested ORCID), and `ROR:0153tk833`.
2. **Removed `machine_annotation_tools`.** The entry asserted `tools: ["GPT-4
   unknown"]` for the CM4AI annotation step. The CM4AI pipeline description names
   the step only as "a large language model (LLM) approach that we developed";
   GPT-4 is named only in the Nature article, about a different cell map. Asserting
   it here would have been a fact carried across the referent boundary this record
   draws. The annotation step is described in
   `labeling_strategies[0].data_annotation_protocol`, and
   `labeling_strategies[0].source_caveats` records why no tool is named.
3. **Removed `regulatory_restrictions.regulatory_restrictions[0]`** (`"FDA
   Regulated: No"`). The slot takes applicable restrictions (HIPAA, ITAR, GDPR); a
   negative status is not one. The fact is stated in
   `regulatory_restrictions.description`, where it answers the field it belongs to.
4. **Trimmed `funders[0].description`** so it no longer restated
   `funders[0].grants[0].grant_number`, a sibling value.

**Back-ported omissions**: none. No source-supported fact was found in the bundle
that the full record omitted and that fits a schema slot; the audit's changes were
all removals or re-homings, and every value that moved kept its receipt (the two
re-pointed receipt entries were edited in place in the chunk entries they already
belonged to — c011 and c020 — and `d4d receipts check --strict` was re-run clean).

**Shape audit**: no prose in list-ranged slots, no undeclared enum values, no
commentary embedded in a name, identifier or affiliation value. Person-ranged
scalar slots (`principal_investigator`, `contact_person`, `committee_contact`) are
declared non-inlined and take a string; they carry the person's name as their
descriptions prescribe, with the attested ORCIDs carried in the enclosing object's
`notes` or `review_details`. The one Person object the schema admits inline
(`data_governance.committee_members`) carries the full structured record for the
named governance contact.

**Deliberate omissions** (evidence absent, so the slot is absent): `subsets`,
`total_size_bytes`, `is_tabular`, `variables`, `anomalies`, `splits`,
`relationships`, `content_warnings`, `sensitive_elements`, `subpopulations`,
`sampling_strategies`, `missing_data_documentation`, `imputation_protocols`,
`annotation_analyses`, `cleaning_strategies`, `use_repository`, `other_tasks`,
`future_use_impacts`, `discouraged_uses`, `extension_mechanism`,
`data_protection_impacts`, `parent_datasets`, and the whole human-participants
group (`collection_consents`, `collection_notifications`, `consent_revocations`,
`informed_consent`, `at_risk_populations`, `participant_privacy`,
`participant_compensation`) — the releases record `Human Subjects: No` and the data
are laboratory measurements of commercially available cell lines, so those fields
have no referent rather than an unknown value. `subsets` is omitted for a different
reason: `DataSubset` inherits `Dataset` and so requires an `id`, and the two
"flagship" groupings the project describes are pointed at by no other value in the
record, so under the v6 minting rule they are described in prose (top-level `notes`)
rather than labeled.

Re-validation after every correction:

```
poetry run linkml-validate -s .../data_sheets_schema_all.yaml -C Dataset <full>   # No issues found
poetry run linkml-term-validator validate-data <full> ...                          # Validation passed
poetry run d4d receipts check --label <VERSION> --project CM4AI --strict           # 28/28, 328/328, no findings
```

## Phase 4 - Re-derivation, checks, repair

```
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
```

Pair checker: **PASS — 79 schema-identical slots; projected slots `['resources']`;
per-record slots (exempt, must differ) `['conforms_to_class', 'conforms_to_schema']`.**
One warning, `semantic-review-required` on `$.file_collections <-> $.distributions`,
with 15 deterministic matches (5 at collection level, 10 at nested resource level)
and no unmatched core distributions. `--sync-core` was not used.

Grounding check against the bundle:

```
{'grounded': 6, 'minted_fragment': 15, 'absent': 0}
```

**No identifier in either record is absent from the bundle.** The 15
`minted_fragment` values are the `FileCollection` and `File` ids, each a fragment on
the attested release DOI `doi:10.18130/V3/HIGT4C`.

Scope check:

```
poetry run d4d download scope --check --project CM4AI
   111 record(s) checked against the declaration
   ✓ none is about a dataset its project declares distinct
```

Both records re-validated after re-derivation:

```
poetry run linkml-validate -s .../data_sheets_schema_all.yaml      -C Dataset     <full>  # No issues found
poetry run linkml-term-validator validate-data <full> ...                                  # Validation passed
poetry run linkml-validate -s .../data_sheets_schema_core_all.yaml -C CoreDataset <core>  # No issues found
poetry run linkml-term-validator validate-data <core> ...                                  # Validation passed
```

No Phase 4 checker reported a finding requiring a change, so there is no repair
phase and none is recorded in provenance.

### Provenance and the render gate

The launcher's mechanical note said to pass the prompt *file* as `--prompt-text`.
That field takes the instruction **as actually sent**, and passing the file failed
the render gate. The instruction this agent received was diffed against
`d4d prompt render --project CM4AI --label <VERSION> --condition generic_v6
--runtime 'Claude Code'` and found **byte-identical** (11,183 bytes, sha256
`7931ce31efb1…`), so that text is what the record now carries. A first record also
failed the gate because the recorder's default provider (`LBL CBORG (proxy to
Anthropic)`) is not the provider the instruction declares; `--provider Anthropic`
was passed and the record re-written. `d4d runs check --project CM4AI --strict`
then exits 0 with this run reporting no finding.

## Claims

No slots were removed.

The four Phase 3 corrections above removed *values* from the full record (81 minted
property ids, one `machine_annotation_tools` entry, one
`regulatory_restrictions.regulatory_restrictions` value) before the pair was shipped;
no slot was removed from either record relative to what the other carries, and the
core is a projection of the full record rather than an edited copy of it.

## Semantic review

| Review | Finding |
|---|---|
| `file_collections` ↔ `distributions` (the checker's `semantic-review-required` warning) | The core's 15 `distributions` are the 5 full-record `file_collections` plus their 10 nested `File` entries, projected over the shared slots. Names, paths, descriptions, `compression`, `md5`, `format` and `media_type` agree value-for-value; no core distribution is unmatched, and the collection-level entries carry no `bytes` because the full record states none. **reviewed: consistent** |
| `total_file_count` against the entries beneath it | Top-level `total_file_count: 10` equals the sum of the five `file_collections[].file_count` values (2 + 3 + 2 + 2 + 1) and the count of `File` entries (10), and equals the June 2026 release page's "1 to 10 of 10 Files". Each `resources[i].total_file_count` (10, 8, 21, 6) matches its own release page's file-count line. **reviewed: consistent** |
| `total_size_bytes` against the entries beneath it | Omitted, and correctly so. The release pages state file sizes only in rounded units ("3.8 GB", "113.3 KB"), which cannot be converted to an exact byte count, so no `File.bytes` value is asserted and no total could be summed from the entries. The project-wide "21.4 TB" counter on cm4ai.org describes all CM4AI data, not the ten files of the current release, and is recorded in `description` as prose rather than in `total_size_bytes`, where it would have contradicted the entries beneath it. **reviewed: consistent** |
| `dialect` against the files | Absent in both records. No `File` entry carries a `dialect`, so the derivation's condition ("only when every File-level dialect agrees on one value") correctly produced no value; the bundle states no format dialect for any released artifact. **reviewed: consistent** |
| `is_tabular` against the files | Omitted. The released artifacts are ZIP archives of immunofluorescence images and mass-spectrometry and single-cell sequencing outputs; the bundle makes no statement about tabular structure, so no boolean is asserted rather than one being inferred from the file list. **reviewed: consistent** |
| Historical release read as the current one | The top-level `status`, `total_file_count`, `file_collections`, `last_updated_on`, `citation` and `version_access.latest_version_doi` all describe the June 2026 release (`doi:10.18130/V3/HIGT4C`), which the data releases page names as the latest release and whose capture is dated 2026-07-24. The March 2025, June 2025 and October 2025 releases appear only under `resources`, each with its own DOI, version, publication date and file count, and the May 2024 release — for which the bundle holds no Dataverse capture — appears only under `related_datasets` as `is_previous_version_of`. No historical value is presented as current. The one trap here is the data releases page's "Released on: June 17, 2025" beneath the June 2026 heading, which would have dated the current release a year early; the tier-1 Dataverse value 2026-06-17 was used and the disagreement recorded. **reviewed: consistent** |
| Counts carried across the referent boundary | The Nature article's U2OS figures (5,147 proteins, 275 assemblies, 36,842 interactions, 20,660 images, 5,509 SEC-MS proteins) appear nowhere in `instances`, `file_collections` or `resources`; the record's counts come from the CM4AI site counters and the release file descriptions. Conversely no CM4AI release figure was attributed to the U2OS study. **reviewed: consistent** |

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_d4d_core.yaml` (derived, re-derived in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_coverage_receipt.yaml` (written during Phase 1, entries edited in place in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CM4AI_provenance.yaml` (live provenance record)

## Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` | PASS, 79 identical slots, 1 semantic warning reviewed above |
| `grounding.check_run` | grounded 6, minted_fragment 15, **absent 0** |
| `d4d receipts check --strict` | chunks 28/28, snippets 328/328, no findings |
| `d4d download scope --check` | in scope |
| Populated slots (full / core) | 548 / 509 across 57 / 53 top-level slots — informational, not a quality gate |
