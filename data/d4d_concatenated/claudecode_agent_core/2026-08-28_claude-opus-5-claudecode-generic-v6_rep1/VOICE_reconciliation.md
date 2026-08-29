# VOICE — Phase 3 / Phase 4 reconciliation

**Run label:** `2026-08-28_claude-opus-5-claudecode-generic-v6_rep1`
**Method:** `claudecode_agent` / `claudecode_agent_core`
**Arm:** BASELINE (input documents only)
**Mode:** four-phase project agent, generic-v6 prompt
**Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
(md5 `dcd717170da6762569c0b4eeafc1c3d2`, 5,746 lines, 22 chunks)

## Referent

`Dataset` admits one referent. The referent chosen is the **Bridge2AI-Voice adult
dataset published on PhysioNet**, current version **3.1.0**, identified by its
version-independent DOI `10.13026/37yb-1t42`. This is the referent the source
manifest's `scope:` block declares for VOICE. The record's `id` and `doi` carry
the version-independent DOI while `version` is `3.1.0` and
`version_access.latest_version_doi` is `doi:10.13026/8xbn-nq66`, the DOI of that
version; the earlier versions are recorded in `version_access.versions_available`
and `errata` rather than as separate referents.

The **Bridge2AI-Voice Pediatric Dataset** (`doi:10.13026/mf9s-5r03`) is declared
related-but-distinct by the manifest and is carried only in `related_datasets`,
with `relationship_type: is_supplemented_by`. Chunks c020 and c021 of the bundle
document it; their contents were deliberately not extracted into this record,
which the coverage receipt states explicitly on both entries. `d4d download scope
--check --project VOICE` reports no record identifying itself as a dataset its
project declares distinct, and this record does not appear in the 32 records that
place a related-but-distinct dataset's identifiers outside the declared slot.

## Phase 1 — coverage receipt

All 22 manifest chunks were read with the file-reading tool, in manifest order,
and each chunk's receipt entry was written before the next chunk was read.

```
chunks 22/22 reviewed · snippets 199/199 verified · slots 140/587 with a receipt (30 exempt)
```

`poetry run d4d receipts check --label … --project VOICE --strict` exits 0 with no
findings. Two chunks are `nothing_relevant`: c001 (concatenation preamble and
table of contents) and c004 (PMC site chrome, reference tail and citation-export
widgets for the feasibility publication). No chunk is `redundant_with` or
`duplicate_of`.

`slots 140/587 with a receipt` is reported, not gated. The unreceipted remainder is
dominated by structural and enumerated leaves whose supporting passage is the same
passage as a receipted sibling (for example each `Organization.name` under a
`Creator.affiliations`, each `File.path` under its `File.description`, each
`credit_roles` term). Nothing in the record was padded to raise the count.

## Phase 2 — core derivation

One command, no model judgement:

```bash
poetry run d4d derive core \
  --full data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/VOICE_d4d.yaml \
  --out  data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/VOICE_d4d_core.yaml
```

Derivation facts as printed by the command on the final (post-Phase-3) full record:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/VOICE_d4d.yaml", "md5": "e6f72e6cf91feb3b1e9e8603efe4b7ea"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The core was never edited by hand and `--sync-core` was never used.

## Phase 3 — source and provenance audit

### Provenance

No prior generated D4D record was read at any phase. The only factual inputs were
the declared bundle, `data/preprocessed/source_manifest.yaml` (read through
`d4d download scope` and `d4d download priority`), and the two LinkML schema files.
No `data/d4d_concatenated/**` or `data/ro-crate_packages/**` path was opened.

One incidental exposure is recorded for completeness: `d4d download scope --check
--project VOICE` prints, as part of its own report, offending slot values from the
32 *other* records in the corpus. That output arrived after this record was written
and no value from it was used; it is tool output about other records, not a factual
source consulted for this one.

### Source disagreements resolved by the manifest ranking

`source_priority` for VOICE: tier 1 the four PhysioNet data resources, tier 2
project documentation / IRB protocol / DUA / documentation repository, tier 3 the
feasibility publication and audiomics white paper, tier 4 the NIH RePORTER page.

| Disagreement | Sources | Resolution |
|---|---|---|
| Affiliation of Frank Rudzicz | feasibility publication (tier 3) says Dalhousie University; project documentation and IRB protocol (tier 2) say University of Toronto | tier 2 preferred; recorded in `creators[].source_caveats` |
| Affiliation of Vardit Ravitsky | feasibility publication (tier 3) says University of Montreal; white paper (tier 3) and project documentation (tier 2) say The Hastings Center | tier 2 preferred; recorded in `creators[].source_caveats` |
| Spelling "Sui" vs "Siu" | project documentation (tier 2) vs PhysioNet release author lists (tier 1) | tier 1 preferred ("Jennifer Siu"); recorded in `creators[].source_caveats` |
| Project website | PhysioNet v1.1 (tier 1) gives `docs.b2ai-voice.org`; PhysioNet v3.0.0 and v3.1.0 (tier 1) give `b2ai-voice.org` | same rank, but the current release's value is the one in scope; `page` carries `https://b2ai-voice.org/` and the documentation site is carried in `external_resources` |

### Disagreements the ranking cannot decide, represented rather than selected

| Disagreement | Sources | Handling |
|---|---|---|
| Target dataset size | project documentation (tier 2): 10,000 voices, anticipated enrollment 10,000 by 2027. IRB protocol (tier 2): sample size 30,000 participants. White paper (tier 3): primary deliverable 30,000 human voices | The two tier-2 sources share a rank, so both figures are stated — 10,000 in `purposes[1].response`, 30,000 in `purposes[1].source_caveats` and the top-level `source_caveats` |
| Award identifier surface form | `OT2OD032720`, `3OT2OD032720-01S3`, `3OT2OD032720-01S1`, `1OT2OD032720-01`, `OT2 OD032720`, `3Tf-OTOD03272001S2`, `3TF-OT2ActfOD032720Projectf01S1` across five sources | Two grants recorded — the core project number and the release supplement — with all variants listed in `funders[0].grants[0].source_caveats` |
| Distribution platform | project documentation healthsheet describes Health Data Nexus with registered access (the v1.0 release); PhysioNet pages describe the current credentialed-access series | Both recorded with their release scope explicit: PhysioNet in `distribution_formats` and `maintainers[1]`, Health Data Nexus in `maintainers[2]` and `external_resources[6]`, each saying which release it describes |

### Corrections made to the full record in Phase 3

All corrections were made to the full record only; the core was re-derived in
Phase 4.

1. **Evidence commentary moved out of `notes` into `source_caveats`** on
   `preprocessing_strategies[2]` (the v1.1 512-point FFT vs the v3.x 400-point
   FFT), `cleaning_strategies[1]` (the healthsheet answers "no" to cleaning while
   the release notes describe removals) and `maintainers[2]` (Health Data Nexus
   describes the v1.0 release). `notes` is not the home for source commentary.
2. **Unsupported media-type inferences removed.** `distribution_formats[0].media_type`
   and the `media_type` on the two TSV `File` entries stated MIME types that no
   source states; they were derived from file extensions. Removed. `format: TSV` is
   retained because the sources say "the following plain-text files:
   static_features.tsv" and "all of the TSV data files".
3. **A schema-commentary `notes` removed** from the first `File` entry. The absent
   `format` on the Parquet files is explained in the semantic review below rather
   than inside the record.
4. **In-value source attribution removed** from `confidential_elements[0].confidentiality_details`
   and `data_protection_impacts[0].impact_details`, which began "The healthsheet
   states/records that…". The finding is now stated directly.
5. **`sampling_strategies[0].representative_verification` removed.** It held a
   statement that no verification was reported — a statement of absence, which is
   an omission, not a value.
6. **`data_governance.access_decision_timeframe` removed.** It began "Not stated"
   and then restated the agreement term, which is not a decision timeframe; the
   term is in `license_and_use_terms.description`.
7. **Two figures back-ported** that the audit found source-supported and missing:
   the v3.0 figure of approximately 61,937 voice-derived recordings from 833 adult
   participants (into `version_access.versions_available[3]`) and the v1.0 figure of
   12,523 recordings for 306 participants across five sites (into
   `external_resources[6].description`). Both received receipts on the chunks
   holding their passages (c007 and c015), edited into those chunks' existing
   entries, and `d4d receipts check --strict` re-run clean.

### Deliberate omissions

- **No `Person` object anywhere.** `Person.id` is required by the schema and the
  bundle contains no ORCID or other personal-identifier registry entry. Supplying
  one from outside the evidence would be an unsupported claim, and a fragment on
  an organization's identifier does not identify a person. `Creator.name` and
  `Creator.affiliations[].name` carry the same content without asserting an
  identifier. This is why `license_and_use_terms.contact_person`,
  `data_governance.committee_contact`,
  `regulatory_restrictions.governance_committee_contact` and
  `ethical_reviews[].contact_person` are empty; the access committee address
  `DACO@b2ai-voice.org` is in `data_governance.access_review_process`, which is the
  field that asks how access is requested.
- **No `publisher`.** The slot is `uriorcurie` and the bundle states no ROR or
  other registry identifier for PhysioNet. PhysioNet is named in `maintainers[1]`.
- **No `total_file_count`, `total_size_bytes`, `file_collections[].file_count` or
  `total_bytes`.** No source states them, and counting the named files plus their
  data dictionaries would be an inference.
- **No `is_tabular`.** See the semantic review below.
- **No `use_repository`.** The healthsheet answers "No" to whether a repository
  links papers using the dataset; a value recording that absence is not an answer.

### Fragment minting under the v6 rule

19 minted fragments, all on the dataset's own DOI CURIE, all pointed at by another
value in the record:

- 5 disease-cohort `subsets` ids — pointed at by
  `known_biases[0].affected_subsets`, which records the unequal distribution across
  exactly those cohorts.
- 3 `file_collections` ids and 11 nested `File` ids — the rule's own example ("a
  collection a file belongs to"). `File.id` and `FileCollection.id` are *required*
  by the schema, so these objects cannot be emitted without them, and the core
  derivation consumes each id to build a `CoreDistribution`. Nothing was labeled
  that is only described: the phenotype directory tree, the acoustic task list and
  the questionnaire list are all carried as prose rather than as minted parts.

`grounding.check_run` reports `{'grounded': 2, 'minted_fragment': 19, 'absent': 0}`
— no identifier in the record is one the bundle does not contain.

## Phase 4 — re-derivation, checks and repair

### Commands

```bash
poetry run d4d bundle chunk --check --project VOICE                      # current
poetry run d4d download scope --project VOICE
poetry run d4d download priority --project VOICE
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset  <full>
poetry run linkml-term-validator validate-data <full> --schema …data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 --project VOICE --strict
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema …data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -c "… data_sheets_schema.grounding.check_run …"
poetry run python -c "… data_sheets_schema.report_claims.check_report …"
poetry run d4d download scope --check --project VOICE
poetry run d4d provenance record --project VOICE --method claudecode_agent --label … --input-bundle …
```

### Results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` | PASS — 79 schema-identical slots; projected `['resources']`; per-record exempt `['conforms_to_class', 'conforms_to_schema']`; 1 semantic warning |
| `grounding.check_run` | grounded 2, minted_fragment 19, **absent 0** |
| `d4d receipts check --strict` | chunks 22/22, snippets 199/199, no findings |
| `d4d download scope --check` | in scope; no related-but-distinct identifier outside `related_datasets` |
| `d4d bundle chunk --check` | current |

Full record: 78 top-level slots. Core record: 68 top-level slots.

### Repair

No finding from the grounding checker, the report-claims checker or the final
pair-consistency run required a change to the shipped bytes. The corrections listed
under Phase 3 were made during the audit, before the final derivation and checks, and
every check above was run against the corrected record. There is therefore **no
`repair` phase and no `report_after_repair` phase** in the provenance record.

## Claims

No slots were removed.

(No slot present in either record was removed by this run, and this report asserts
of no slot that the schema does not declare it. The removals listed under Phase 3
are of values written earlier in this same run's drafting, not of slots the shipped
record or a contributing record carries; recording them as `Removed` rows would
assert that the shipped record still contains them, which it does not.)

## Semantic review

| Review | Finding |
|---|---|
| `file_collections` ↔ `distributions` (the pair checker's `semantic-review-required` warning) | 14 deterministic matches — 3 at collection level (`#features`, `#phenotype`, `#metadata`) and 11 at nested resource level (the 9 Parquet feature files plus `static_features.tsv` and `audio_quality_metrics.tsv`); 0 unmatched core distributions. Each core distribution's `description`, `name`, `path` and `id` are byte-identical to the full record's collection or file it was projected from, and the projection dropped only slots `CoreDistribution` does not declare. **reviewed: consistent** |
| Counts and sizes against the entries beneath them (unprompted) | `total_file_count`, `total_size_bytes`, `file_collections[].file_count` and `file_collections[].total_bytes` are all absent, so no aggregate contradicts the 11 enumerated files — the sources state none of them and inferring a count from the named files plus their unenumerated JSON dictionaries would be a guess. The per-file record counts in the descriptions (n=29278 spectrogram / Mel spectrogram / MFCC, n=32522 pitch, n=28640 EMA, n=31855 loudness, n=31872 periodicity and sparc pitch, n=29289 PPGs) are the v3.1.0 figures and were checked one by one against chunk c019; the superseded v3.0.0 figures in c017 were not carried. `instances[0].counts: 833` matches the v3.1 abstract and the v3.0 abstract and the healthsheet's "around 833 instances". **reviewed: consistent** |
| `dialect` and `is_tabular` against the files (unprompted) | No `File` entry carries a `dialect`, so the derivation correctly emitted no core `dialect` — the sources describe Parquet as "column-oriented" and the phenotype files as "tab delimited" but state no dialect or profile. `is_tabular` is deliberately absent: the release mixes tab-separated phenotype and static-feature tables, which are tabular, with Parquet files whose payload is a per-recording tensor, which is not; a single boolean would assert something no source settles and half the files contradict. The `format` slot is likewise absent on the nine Parquet files because `FormatEnum` declares no Parquet value and no declared value describes them; it is present as `TSV` on the two tab-separated files, which the sources name as such. **reviewed: consistent** |
| Historical vs current release read as the current one (unprompted) | Corrected during the audit and re-checked. The record is about v3.1.0 (published 2026-05-01). Every value taken from a superseded source is either scoped or excluded: the v1.1 512-point FFT is in `preprocessing_strategies[2].source_caveats` and not in the value; the v3.0.0 per-file counts were replaced by the v3.1.0 counts; the healthsheet's Health Data Nexus distribution and its v2.0.0-era study population statement are carried only in `maintainers[2]` and `external_resources[6]` with the release named; the v1.0 and v3.0 participant and recording figures sit in `external_resources[6].description` and `version_access.versions_available[3]` labelled by version, not in `instances`. The healthsheet's citation for version 2.0.0 was **not** carried into `citation`, which holds the v3.1.0 PhysioNet citation. **reviewed: corrected** |
| Referent held consistently across both records (unprompted) | `id`, `doi`, `version`, `title`, `name` and `citation` agree in both records after projection, and the pediatric dataset appears in both only under `related_datasets`. **reviewed: consistent** |
| Project-label variants reported by the form checker (unprompted) | The form check reports `gc_label_variants: {"Bridge2AI-Voice": 43, "Bridge2AI Voice": 17}` across both records, 60 occurrences. Every one was inspected. The manifest's canonical label for the project is `Voice`, and the naming rule's carve-out for "proper nouns as a source states them" covers all 60: `Bridge2AI-Voice` is the dataset's own title on PhysioNet and the consortium's name; the space-separated form appears only inside source-stated proper nouns — `Bridge2AI Voice Registered Access License`, `Bridge2AI Voice Registered Access Agreement`, `Bridge2AI Voice Data Acquisition` (the IRB protocol title), `Bridge2AI Voice Web app`, `Bridge2AI Voice iOS app`, and `Bridge2AI Voice project` in the documentation repository's own stated description. No sentence composed by this run names the project in a form the sources do not state. `british_spellings: 0`, `undeclared_prefixes: {}`, `organisational_fragments: 0`. **reviewed: consistent** |
