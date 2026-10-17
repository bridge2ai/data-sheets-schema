# AI_READI reconciliation report

- **Version label:** 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2
- **Condition:** generic_v6, BASELINE arm (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Mode:** four-phase project agent
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
  (md5 `0f3abb51a333555456bedd63891fcd99`, 7376 lines, 28 chunks)
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d_core.yaml`
- **Coverage receipt:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. This record is about the **Flagship Dataset of Type 2
Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, which
is what the project's `scope:` block in `data/preprocessed/source_manifest.yaml`
declares (`about AI-READI dataset <https://doi.org/10.60775/fairhub.3>`). The choice
is held consistently across both records: `id`, `doi` and
`version_access.latest_version_doi` all name that release, and the earlier releases
1.0.0 and 1.0.0's successor 2.0.0 appear only as `related_datasets` with
`is_new_version_of`, never as the record's subject. `d4d download scope --check
--project AI_READI` reports 124 records checked and none identifying itself as a
dataset the project declares distinct.

The AI-READI *study* and the AI-READI *dataset release* are distinct, and the bundle
describes both. Where a fact belongs to the study rather than the release — the 4000
target enrollment, the 2022-2026 project timeline, the "Enrolling by invitation"
status — it is recorded on the collection and sampling properties, not on the
dataset's own identity slots.

## Phase 1 - full record generated from the declared bundle

The bundle was read chunk by chunk in manifest order with the file-reading tool, and
a coverage-receipt entry was written for each chunk before the next was opened.
`d4d bundle chunk --check --project AI_READI` reported the manifest `current` against
the bundle before reading began.

Final receipt state: **28/28 chunks reviewed, 328/328 snippets verified, 222 of 536
populated slots carry a receipt (22 exempt), no findings.**

Two chunks are marked `nothing_relevant`, both with reasons:

- `c001` - the concatenation preamble and table of contents.
- `c025`, `c026` - the first two thirds of the IRB protocol source, which is an
  **unfilled** University of Washington Human Subjects Division application form:
  instructions, question text, consent-term definitions and the form's own worked
  examples (which mention acupuncture and MRI gadolinium agents and have nothing to do
  with this study). The study's actual answers begin at `c027`, and everything taken
  from that source comes from `c027` and `c028`.

## Phase 2 - core derived by projection

The core was produced by `d4d derive core` from the validated Phase 1 file. No model
judgement entered this phase. The command reported:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d.yaml", "md5": "26752847b04f37100cf2875b533367c6"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The md5 above is the corrected full record produced after the Phase 3 repair; the core
was re-derived from it in Phase 4 with `--phase4-complete`.

## Phase 3 - source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped or consulted. The read history
for this run consists of: the four playbook and guard files named in the instruction
(`d4d-provenance-guard.md`, `d4d-full-core.md`, `d4d-agent.md`,
`d4d-uniform-rules.md`), the chunk manifest, the 28 chunks of the declared bundle, and
the two LinkML schemas (read through `SchemaView`, not as text). Nothing under
`data/d4d_concatenated/` other than this run's own label directory was opened, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was touched. Structure was derived
entirely from class `Dataset` in `data_sheets_schema_all.yaml` via the resolved
(induced) slot definitions, never from an example record.

### Source disagreements resolved by the declared ranking

`source_priority` in the manifest ranks AI-READI's sources: tier 1 the FAIRhub dataset
pages and API and the RO-Crate; tier 2 documentation, license and IRB; tier 3 the
publications; tier 4 NIH RePORTER. Five disagreements were found and each is recorded
in `source_caveats` with what each source said and which was preferred.

| Fact | Lower-ranked source | Higher-ranked source | Recorded |
|---|---|---|---|
| Acronym expansion | "…**Equitable** Atlas…" (BMJ Open, Nature Metabolism, tier 3) | "…**Exploratory** Atlas…" (FAIRhub API healthsheet/README/study description and RO-Crate, tier 1) | Exploratory, per tier 1 |
| Target enrollment | 4600 (IRB protocol, tier 2) | 4000 (FAIRhub study description, tier 1; BMJ, tier 3) | 4000 |
| Blood volume per visit | 53 mL (BMJ Open, tier 3) | 50-60 mL (IRB protocol, tier 2) | 50-60 mL, with the BMJ figure named beside it |
| Collection start date | 18 July 2023 (BMJ Open, tier 3) | 2023-07-19 "Actual" (FAIRhub study description, tier 1) | 2023-07-19 |
| Data governance committee | "Data Access Committee" (BMJ Open, tier 3) | "AI-READI Consortium" (RO-Crate, tier 1) | AI-READI Consortium, with the BMJ statement noted |

### Disagreements the ranking cannot decide

Two tier-1 sources disagree with each other, so the ranking does not settle them and
the evidence is represented rather than one value selected:

- **Lead investigator's affiliation.** The FAIRhub study description gives Aaron Lee's
  affiliation, the lead sponsor and the managing organization as Washington University
  in St. Louis (ROR 01yc7t268); the RO-Crate gives "Aaron Lee, Department of
  Ophthalmology, University of Washington"; NIH RePORTER (tier 4) records the awardee
  organization as UNIVERSITY OF WASHINGTON. `creators[3].affiliations` carries **both**
  organizations. Only the Washington University in St. Louis ROR is attested *as this
  person's affiliation identifier*, so no registry identifier is attached to the second
  affiliation — the University of Washington ROR that appears in the bundle does so as a
  study *location*, and attaching it here would combine two separate facts.
- **Publisher.** The FAIRhub API gives `publisherName: FAIRhub`; the RO-Crate gives
  `publisher: AI-READI Consortium`. The slot admits one value and the ranking cannot
  separate the sources, so `publisher` is left **unset** and both statements are
  recorded in `source_caveats`. Omission is the faithful answer here; picking either
  would silently resolve a tie the evidence does not resolve.
- **Ethics board name.** The RO-Crate labels the board "Washington University IRB"
  while giving the University of Washington Human Subjects Division address and a
  `uw.edu` contact; the healthsheet and BMJ Open both name the University of Washington
  IRB. `ethical_reviews[0].reviewing_organization` records the University of Washington
  IRB and the object's `source_caveats` names the RO-Crate's label rather than dropping
  it.

### Corrections made to the full record

Two values asserted more than the bundle supports and were repaired in the full record
(never in the core, which was re-derived afterwards):

- `at_risk_populations.at_risk_groups_included: false` was **removed**. The eligibility
  criteria exclude minors and pregnant participants, but the IRB form's protected-
  populations, prisoners and cognitively-impaired sections carry no answers, so a
  blanket "no at-risk groups included" over-claims. The eligibility facts remain in the
  object's `description`, which now says explicitly that no overall determination is
  recorded.
- `external_resources[3].archival: false` was **removed**. Nothing in the bundle states
  whether the RO-Crate packaging is an archival version; the boolean was an inference.

### Shape and slot-filling audit

- Every emitted slot name, range, cardinality and enum value was resolved from the
  schema. `linkml-validate` and `linkml-term-validator` both pass on both records.
- `creators[].principal_investigator` is declared range `Person` and **not inlined**, so
  it takes the person's identifier, not a nested object. The first draft nested a full
  `Person` under it and failed validation with 15 errors; each was corrected to the
  person's `ORCID:` CURIE, with the person's title and contact address folded into the
  `Creator.description` (there is no email slot on `Creator`).
- `Person.id` is required. Consequently a `Person` is emitted only where the bundle
  supplies an ORCID; no person identifier was minted, and in particular no person is
  identified by a fragment on an organization's ROR. The IRB Reliance Team contact,
  which has an email but no ORCID, is recorded in `ethical_reviews[0].review_details`
  rather than as a `contact_person` object.
- Identifier form: `uriorcurie` slots carry CURIEs against declared prefixes — `doi:`,
  `ROR:`, `ORCID:` — never resolver URLs. `download_url` and `access_urls` are declared
  `uri` and carry URLs. The `doi` slot is declared `string` and carries the bare DOI per
  its own description. URLs inside prose and citations are left exactly as the sources
  wrote them.
- No prose sits in a slot whose range is a list; no `notes` slot is populated anywhere in
  the record; all evidence commentary is in `source_caveats`, at the top level and on the
  four objects that needed it.

### Omissions, and why

- `variables` — the bundle's laboratory table (chunks c003, c004) carries test names,
  units and reference ranges, but the PDF-to-text conversion has scrambled the column
  alignment so that no unit or range can be attributed to a specific test without
  guessing. Emitting bare `variable_name` entries with nothing else would be structure
  without content. Omitted; the healthsheet's pointer to per-variable documentation at
  `docs.aireadi.org` is recorded as an external resource, not as a variable list.
- `existing_uses`, `use_repository`, `other_tasks`, `discouraged_uses` — the healthsheet
  answers each of these "No" or refers the reader to the license. A value recording that
  something is absent, or a pointer to where information lives, does not answer the
  field, so the slots are omitted rather than populated with the pointer. The license
  restrictions themselves are recorded in `prohibited_uses`, which is where they belong.
- `publisher`, `regulatory_restrictions.confidentiality_level` — omitted for the reasons
  given above (an undecidable tie, and an HL7 value with no defensible mapping onto the
  schema's three-term enum).
- `download_url` — the bundle gives an access page requiring login, not a direct
  download URL. The access route is recorded in `distribution_formats[].access_urls`
  and `data_governance.access_review_process`, the fields that ask for it.
- `resources` — the RO-Crate's nine sub-crates and the FAIRhub structure description's
  nine datatype directories are the same nine parts described by two sources. They are
  recorded once, as `file_collections`, using the FAIRhub view because it carries file
  counts and byte sizes; the crate's ARK identifiers are recorded under
  `external_resources`. Recording both decompositions would have doubled the same nine
  parts.

### Minted identifiers

Thirteen fragment identifiers were minted, all as fragments on the dataset's own
attested DOI CURIE (`doi:10.60775/fairhub.3#…`), and all because the schema **requires**
an `id` on the class: ten `FileCollection` entries and three `DataSubset` entries. No
fragment was minted for a part that is only described in prose, and no new prefix was
invented. The grounding checker reports `{'grounded': 10, 'minted_fragment': 13,
'absent': 0}` — no identifier in this record is one the bundle does not contain.

## Phase 4 - re-derivation, checks and repair

1. Core re-derived from the corrected full record with `--phase4-complete`, which wrote
   the `# Phase 4 reconciliation: completed` header line. `--sync-core` was not used.
2. `d4d_pair_consistency` on the re-derived pair: **PASS**, 79 schema-identical slots,
   projected slots `['resources']`, per-record slots `['conforms_to_class',
   'conforms_to_schema']`. One warning, `semantic-review-required`, reviewed below.
3. Grounding check: `{'grounded': 10, 'minted_fragment': 13, 'absent': 0}` — no
   findings.
4. `d4d receipts check --strict`: 28/28 chunks, 328/328 snippets, no findings, exit 0.
5. `d4d download scope --check --project AI_READI`: in scope.
6. Schema and ontology-term validation re-run on both records after every correction;
   all four pass.

No finding from step 2's checkers or from the pair-consistency run required a further
change, so there is no `repair` phase after Phase 4 and no `report_after_repair`. The
two corrections named above were made during Phase 3, before the core was derived for
shipping.

### Provenance recording note

The launcher's mechanical note directed that `--prompt-text` be passed the v6 prompt
file itself. Doing so made `d4d runs check` report a render-gate `mismatch`: the gate
re-renders the instruction from the record's spec and compares, and the raw prompt file
is not the instruction — substitution of project, arm, label, runtime and bundle is what
makes the two different objects. The playbook's own route was followed instead:
`d4d prompt render --project AI_READI --label … --condition generic_v6 --runtime 'Claude
Code' --out <file>`, and that rendered text was recorded as `--prompt-text`, so the text
and its hash come from the same place.

A second render-gate mismatch followed, because `d4d provenance record` defaults the
spec's provider to `LBL CBORG (proxy to Anthropic)` while `d4d prompt render` defaults
it to `Anthropic`. This run declares `# Provider: Anthropic` in both headers and did not
go through the CBORG proxy, so `--provider Anthropic` was passed to the recorder; the
spec and the render then agree and the gate reports no mismatch. The prompt file itself
is hashed separately under `prompts.files` and is canonical against the registry.

`d4d runs check --strict` finally reports 1 run checked, 0 failing, no render mismatch.
It lists `model.temperature` and `model.reasoning_effort` as recorded-but-not-observed.
Temperature is 0.0 asserted by this agent; **reasoning effort was not passed and no value
was written** — this runtime does not expose it and the run was not launched at a known
effort, so the field is absent and the gap is named, rather than being filled with
"default" or a guess. Reasoning capture on this path remains
`runtime_cannot_capture` (#400): no reasoning log exists or can exist for an agentic run.

## Claims

No slots were removed.

## Semantic review

| Review | Basis | Outcome |
|---|---|---|
| `file_collections` ↔ `distributions` (the checker's `semantic-review-required` warning) | 10 deterministic matches at collection level, 0 at nested resource level, no unmatched core distributions. Each core distribution carries the same `id`, `name`, `description`, `conforms_to` and `conforms_to_standard` as its source collection, and `bytes` equal to the collection's `total_bytes`. The full record lists no `File` entries, so no file-level distributions exist and none were expected. | **reviewed: consistent** |
| `total_file_count` against the entries beneath it | Declared `total_file_count` is 356343. The nine datatype collections sum to 356334, leaving exactly 9 — the nine root metadata files (`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`, `healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`, `study_description.json`) that the FAIRhub structure description lists at the dataset root. A tenth `file_collections` entry with `file_count: 9` and `collection_type: metadata` was added so the aggregate reconciles to the source figure exactly. | **reviewed: corrected** (tenth collection added; totals now reconcile) |
| `total_size_bytes` against the entries beneath it | Declared `total_size_bytes` is 3815969779678 and the nine datatype collections sum to 3815969360064, a difference of 419614 bytes attributable to those same nine root metadata files. The bundle gives no byte size for them, so `total_bytes` is left unset on that tenth collection rather than being back-computed from the difference. The 3.82 TB figure the sources quote is consistent with the byte count (3.816 TB). | **reviewed: consistent** |
| `dialect` against the files | The full record lists no `File` entries, so the derivation's conditional rule left `dialect` absent, which is correct: there is nothing for it to agree on. No dialect is stated anywhere in the bundle. | **reviewed: consistent** |
| `is_tabular` against the files | Set `false`. The healthsheet states the release encompasses "tabular data, imaging data, and physiological signal/waveform data", and seven of the ten collections are imaging or waveform. A release that is majority DICOM and WFDB is not a table. | **reviewed: consistent** |
| Historical vs current release scope | The bundle contains a FAIRhub page for **version 2.0.0** as well as for 3.0.0. The v2.0.0 page states 2.01 TB and 165,051 files; those figures are **not** in this record, which carries only the v3.0.0 figures of 3.82 TB and 356,343 files. Likewise the v2.0.0 documentation page (c010) is superseded by the v3.0.0 page (c011), and only the latter's version claim is used. Participant counts for versions 1.0.0 (204) and 2.0.0 (1067) appear only in `version_access.version_details` as version history, never as this release's `instances[].counts`, which is 2280. | **reviewed: consistent** |
| Counts across the record | 2280 participants appears in `description`, `instances[0].counts` and `splits[0].split_details`, and the split table's own totals (1576 + 352 + 352, and 380 + 545 + 519 + 836, and 951 + 1329, and 776 + 560 + 686 + 258) each sum to 2280. The 4000 and 4600 target figures are recorded only as study targets, in `instances[0].source_caveats` and the sampling strategies, never as this release's count. | **reviewed: consistent** |
| Dates across the record | `issued` 2025-11-17, the RO-Crate `datePublished` 11/17/25, the FAIRhub "Available" date 2025-11-17 and the third entry of `distribution_dates[0].release_dates` all agree. The collection window 2023-07-19 to 2025-05-01 appears in `collection_timeframes[0]` and in `description`, and matches the FAIRhub "Collected" range. Release dates 2024-05-03 and 2024-11-08 match the `version_access` entries for 1.0.0 and 2.0.0. | **reviewed: consistent** |
| Identifiers repeated across the record | `10.60775/fairhub.3` appears as `doi:10.60775/fairhub.3` in `id` and `version_access.latest_version_doi` (both `uriorcurie`) and bare in `doi` (declared `string`, whose description mandates the bare form). Every ROR appears in `ROR:` form and every ORCID in `ORCID:` form, each exactly once per organization or person. No identifier appears in two forms within a slot of the same declared range. | **reviewed: consistent** |
| Licensing statements | The license is named "AI-READI custom license v2.0" (FAIRhub `rightsName`) in `license`, and "AI-READI Data License Agreement (Version 2.0)" (the document's own title) in `license_and_use_terms.name`; both are the same instrument under the two names its sources give it, pointing to the same `zenodo.17555036` DOI. The article-level CC BY-NC 4.0 licence of the BMJ Open paper and the CC-BY 4.0 licence of the documentation are **not** conflated with the dataset licence: the first is absent from the record and the second appears only in `ip_restrictions.restrictions` as a statement about the documentation. | **reviewed: consistent** |

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d_core.yaml` (derived, then re-derived in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_coverage_receipt.yaml` (written during Phase 1)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_reconciliation.md` (this file)

## Commands run

```bash
poetry run d4d bundle chunk --check --project AI_READI
poetry run d4d download scope --project AI_READI
poetry run d4d download priority --project AI_READI
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2 --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --strict
poetry run d4d derive core --full <full> --out <core>
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run d4d download scope --check --project AI_READI
# grounding and report-claims checkers, per the playbook's Phase 4 step 2
```

## Final results

| Check | Result |
|---|---|
| Full record schema validation | pass |
| Full record ontology-term validation | pass |
| Core record schema validation | pass |
| Core record ontology-term validation | pass |
| Pair consistency | PASS, 79 identical slots, 1 semantic warning (reviewed above) |
| Coverage receipt (`--strict`) | 28/28 chunks, 328/328 snippets, 0 findings |
| Identifier grounding | grounded 10, minted_fragment 13, absent 0 |
| Scope check | in scope |
| Full record | 79 top-level slots, 635 populated slot instances, 1754 lines |
| Core record | 66 top-level slots, 569 populated slot instances, 1292 lines |

Line and slot counts are informational metadata about what the evidence supported, not
a quality gate; the uniform rules set no target slot count for any project or arm.
