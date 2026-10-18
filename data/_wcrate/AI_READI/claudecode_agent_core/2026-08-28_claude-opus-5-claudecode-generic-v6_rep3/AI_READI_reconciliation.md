# AI_READI reconciliation — 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3

Four-phase project agent, generic-v6 prompt, BASELINE arm (input documents only).
Runtime Claude Code, provider Anthropic, model claude-opus-5, temperature 0.0.

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_coverage_receipt.yaml`
- Declared bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 `0f3abb51a333555456bedd63891fcd99`, 7,376 lines, 28 chunks)

## Referent

`Dataset` admits one referent. This record is about the **AI-READI dataset, version 3.0.0**,
"Flagship Dataset of Type 2 Diabetes from the AI-READI Project", DOI `10.60775/fairhub.3`, which is
the referent the project's `scope:` block declares. Versions 1.0.0 (`10.60775/fairhub.1`) and 2.0.0
(`10.60775/fairhub.2`) are earlier releases of the same dataset, not separate datasets; they are
carried as `version_access.versions_available` and as `related_datasets` entries with
`relationship_type: is_new_version_of`, and their figures are never used as this release's own.
The choice is held consistently across both records: the core is a projection of the full record and
carries the same `id`, `title`, `version` and `doi`. `d4d download scope --check --project AI_READI`
reports the record in scope.

## Phase 1 — full record from the declared bundle

The bundle was read chunk by chunk in manifest order with the file-reading tool, and each chunk's
coverage-receipt entry was written before the next chunk was opened. `d4d bundle chunk --check
--project AI_READI` reported the manifest `current` before reading began.

Sources consulted: the declared bundle, `data/preprocessed/source_manifest.yaml` (scope, naming and
`source_priority`), and the full and core LinkML schemas. No prior generated D4D record, from any arm
or label, was opened, searched or cited; nothing under `data/d4d_concatenated/` other than this run's
own output paths was read, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was read.

Three of the twenty-eight chunks are recorded `nothing_relevant`. **c001** is the concatenation
preamble and table of contents, which lists the eleven constituent filenames and carries no dataset
facts. **c025** and **c026** are the blank University of Washington Human Subjects Division IRB
application form — numbered questions, guidance paragraphs and unticked checkboxes with every answer
field empty; the study-specific answers to that form appear later in the same source and are recorded
from **c027** and **c028**. The other 25 chunks are `extracted`.

## Phase 2 — core derived by projection

`d4d derive core` was run on the validated Phase 1 file and re-run in Phase 4 with
`--phase4-complete`. The command reported:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d.yaml",
          "md5": "79f10fae60b2ab9ff2c902e805b73763"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "distribution_slots": {"collection": ["compression","conforms_to","conforms_to_standard","description","id","name","notes","path","source_caveats"],
                        "file": ["bytes","compression","conforms_to","conforms_to_standard","description","encoding","format","hash","id","md5","media_type","name","notes","path","sha256","source_caveats"]},
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The core was never edited by hand and `--sync-core` was never used.

## Phase 3 — source and provenance audit

Schema and ontology-term validation were re-run for the full record, and the record was checked
against the current bundle and manifest. Six discrepancies among the sources were found and resolved
by the manifest's `source_priority` ranking (lowest tier strongest); all six are recorded in the
record's own `source_caveats` rather than silently decided.

| # | Disagreement | Sources | Resolution |
|---|---|---|---|
| 1 | Expansion of the acronym | "Exploratory" in the FAIRhub structured metadata, healthsheet, README, RO-Crate (tier 1) and NIH RePORTER (tier 4); "Equitable" in the BMJ Open protocol and Nature Metabolism (tier 3) | tier 1 preferred; both recorded |
| 2 | Target enrollment | 4,000 in the FAIRhub study description (tier 1), BMJ Open and Nature Metabolism (tier 3); 4,600 in the UW IRB protocol (tier 2) | 4,000 stated; both recorded |
| 3 | Size and file count | 3.82 TB / 356,343 files for v3.0.0; 2.01 TB / 165,051 files on the retained v2.0.0 FAIRhub page | v3.0.0 figures stated; the v2.0.0 page marks itself no longer accessible |
| 4 | Start of data collection | 2023-07-19 (tier 1); "18 July 2023" (tier 3) | tier-1 date used for `collection_timeframes[0].start_date`; both recorded |
| 5 | Responsible organization, IRB and PI affiliation | Washington University in St. Louis / "Washington University IRB" in the FAIRhub metadata and RO-Crate (both tier 1); University of Washington HSD address in the same RO-Crate; University of Washington IRB approval STUDY00016228 with reliance agreements in tiers 2 and 3 | both accounts recorded, not merged |
| 6 | De-identification | "NoDeIdentification" with HIPAA checking (tier 1); PHI stripped via HIPAA Safe Harbor (tier 3) | both recorded in `is_deidentified` |

### Corrections made to the full record in Phase 3

1. **`principal_investigator` shape.** The slot's declared range is a scalar reference, not an
   inlined `Person`. Sixteen creator entries were rewritten to carry the person's ORCID CURIE in
   `principal_investigator`, with the person's title and contact address moved into the creator's
   `description` (there is no email slot on `Creator`).
2. **Two creator entries removed.** Hiroshi Ishikawa and Camille Nebeker are named among the
   consortium's principal investigators, but the bundle supplies no personal identifier for either,
   and `Person.id` is required. Rather than mint a fragment on someone else's ORCID — which would
   assert something false about that person — the entries were dropped; both are covered by the
   consortium creator and, for Camille Nebeker, by `ethical_reviews[1]`. The same reasoning removed
   an `EthicalReview.contact_person` for the "IRB Reliance Team", whose email is now stated in
   `ethical_reviews[0].review_details`.
3. **CRediT roles reduced to what the sources state.** Per-person `investigation`,
   `formal_analysis`, `data_curation`, `software`, `conceptualization`, `project_administration` and
   `writing_original_draft` assignments were inference. The only role the bundle states for these
   people is "Study Principal Investigator", so every creator with a named individual now carries
   `credit_roles: [supervision]` and nothing else, and the consortium creator carries none.
4. **Reference ranges are not value bounds.** `minimum_value`/`maximum_value` on the HbA1c and
   glucose variables held clinical laboratory reference ranges, which is not what those slots
   declare; they were removed and the ranges remain in the variables' `description`. The MoCA
   `minimum_value` was removed because only the maximum score of 30 is stated.
5. **An organization name that no source states was removed.** `ethical_reviews[1]` carried a
   `reviewing_organization` of "AI-READI ethics team"; the bundle names four individuals under
   `ethicalReview` and no such organization. The slot was dropped.
6. **American English.** Six spellings in composed prose were corrected: `programme` → `program`
   (four occurrences), `haemodynamic` → `hemodynamic`, `colour` → `color`. Quoted source text,
   proper nouns and identifiers were left as their sources write them.

### Back-ported omission

One source-supported fact the first pass omitted was added: a second `collection_notifications`
entry recording what individual results are returned to participants and how — the exam card at the
visit, the Dexcom report and yearly laboratory results by HIPAA-compliant encrypted email, the study
database access code with flagged abnormal values and its disclaimer, the incidental-finding
referral path, and the results that are deliberately not returned because they lack standard
interpretation methods. Its `{slot, snippet}` pairs were added to the existing **c004** and **c028**
receipt entries in place, and `d4d receipts check --strict` was re-run.

### Receipt maintenance

The receipt's slot paths were written while reading, before the record's array ordering existed, so
178 of them were remapped to the paths the finished record actually uses and 3 were dropped where
the fact they attest is not in the record (an NIH program-scientist list, a prepublication-history
note, and the healthsheet's "no prior uses" answer). Every snippet is unchanged and still verifies
verbatim against its own chunk.

### Provenance boundary

Confirmed: every factual input is on the Phase 1 allowlist; no prior generated YAML, evaluation or
reconciliation report was read or cited; the core's input full record carries this run's exact
version label. The prompt file `src/download/prompts/d4d_generic_arm_prompt_v6.md` is at its
canonical pin (`d4d api prompts check --strict`: 13 prompt files, 0 not at their pin).

## Phase 4 — re-derivation, checks and repair

Deterministic results after the Phase 3 corrections:

| check | result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` | PASS: 79 schema-identical slots; projected `resources`; per-record exempt `conforms_to_class`, `conforms_to_schema`; 1 semantic-review warning |
| grounding (`check_run`) | `{'grounded': 12, 'minted_fragment': 9, 'absent': 0}` |
| `d4d receipts check --strict` | chunks 28/28 reviewed · snippets 415/415 verified · slots 236/567 with a receipt (18 exempt) · no findings |
| `d4d download scope --check --project AI_READI` | in scope |
| form check (`d4d provenance record`) | 0 undeclared prefixes, 0 British spellings, 0 organizational fragments, 0 project-label variants |
| report-claims checker | `{'checked': True, 'claims_checked': 0, 'claims_unnamed': 0}`, no findings |
| `d4d runs check --strict` | no finding against this run |

No identifier in either record is `absent` from the bundle. The nine `minted_fragment` values are
the nine `file_collections` ids, each a fragment on the record's own DOI CURIE
(`doi:10.60775/fairhub.3#cardiac_ecg` and so on); `FileCollection.id` is schema-required and each
collection carries structured counts and sizes, so the label is used rather than decorative. No
fragment was minted for a part that is only described: `subsets` was deliberately left unpopulated
and the two access tiers, the four diabetes study groups and the recommended train/validation/test
split are described in `description`, `sensitive_elements`, `confidential_elements`,
`subpopulations` and `splits` instead.

Step 2's checkers and the final pair-consistency run reported no finding that required a change to
either record, so **no repair phase was run** and neither record was rewritten after one.

One finding did require a correction to the *provenance record* rather than to a record: the first
`d4d provenance record` call passed the prompt file itself to `--prompt-text`, and `d4d runs check
--strict` correctly reported `mismatch: recorded 57ac203090ee… but the spec renders f32eaf44658a…`.
`d4d prompt render --project AI_READI --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3
--condition generic_v6 --runtime 'Claude Code'` reproduces the launch instruction byte for byte
(md5 `93b2f31035444dbef335d422f2735aec`, sha256 `f32eaf44658a…`), so provenance was re-recorded with
the instruction as sent. `d4d runs check --strict` then exits 0 with no finding against this run, and
the earlier `d4d runs validate` verdict was carried forward because the artifacts still hash to what
it recorded.

## Claims

No slots were removed.

## Semantic review

| review | finding |
|---|---|
| `file_collections` ↔ `distributions` (the pair checker's `semantic-review-required` warning) | Nine collections project to nine core distributions, all matched at collection level, no unmatched core distributions and no nested `File` entries. Each distribution carries the collection's `id`, `name`, `path`, `description`, `conforms_to`, `conforms_to_standard` and byte size, and the descriptions read correctly as distribution content. **reviewed: consistent** |
| `total_file_count` and `total_size_bytes` against the entries beneath them | The nine collections sum to 356,334 files and 3,815,969,360,064 bytes against declared totals of 356,343 files and 3,815,969,779,678 bytes. The residual is exactly 9 files and 419,614 bytes, which is precisely the nine root-level metadata files the FAIRhub `metadataFileList` names (CHANGELOG.md, dataset_description.json, dataset_structure_description.json, healthsheet.md, LICENSE.txt, participants.json, participants.tsv, README.md, study_description.json). The totals and the parts agree. **reviewed: consistent** |
| `dialect` and `is_tabular` against the files | No `File` entries were emitted, because the bundle gives directory-level counts and sizes but not per-file metadata, so the derivation correctly left `dialect` absent from the core rather than inventing agreement. `is_tabular: false` is right for a release the sources describe as tabular, imaging and physiological signal or waveform data together. **reviewed: consistent** |
| historical release read as the current one | The record describes version 3.0.0 throughout: totals, DOI, dates, participant count and the release-specific split all come from the v3.0.0 sources. The bundle retains the superseded v2.0.0 documentation and FAIRhub record, whose 2.01 TB / 165,051 files and pilot-phase framing were kept out of the release-level slots and recorded in `source_caveats`; the v1.0.0 and v2.0.0 release dates appear only under `distribution_dates` and `version_access`, labeled as earlier versions. **reviewed: consistent** |
| creators against the sources after the role reduction | Sixteen named principal investigators and the consortium remain; each individual's ORCID and each affiliation's ROR is taken verbatim from the bundle, and no registry identifier was supplied from outside it. **reviewed: corrected** — per-person CRediT roles beyond `supervision` were removed, two creators without any attested personal identifier were dropped, and contact details moved into `description`. |

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d_core.yaml` (derived, re-derived in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_coverage_receipt.yaml` (written during Phase 1, extended and remapped in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_reconciliation.md` (this file)

## Commands run

```bash
poetry run d4d bundle chunk --check --project AI_READI
poetry run d4d download scope --project AI_READI
poetry run d4d download priority --project AI_READI
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 \
  --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --strict
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset <full>
poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d derive core --full <full> --out <core>
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -c "...data_sheets_schema.grounding.check_run..."
poetry run python -c "...data_sheets_schema.report_claims.check_report..."
poetry run d4d download scope --check --project AI_READI
poetry run d4d api prompts check --strict
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt \
  --condition generic_v6 --runtime 'Claude Code' --provider Anthropic --receipt-expected \
  --prompt src/download/prompts/d4d_generic_arm_prompt_v6.md \
  --prompt-text src/download/prompts/d4d_generic_arm_prompt_v6.md --phase ...
poetry run d4d runs validate --project AI_READI --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3
poetry run d4d runs check --strict
```

## Final result

Both records pass schema and ontology-term validation. The pair checker passes on the re-derived
pair with its one expected semantic-review warning, which is reviewed above. The coverage receipt is
complete and strict-clean. No identifier is ungrounded. The record is in scope. Informational
metadata only: the full record has 80 top-level slots and 656 populated leaf values across 1,718
lines; the core has 67 top-level slots and 544 populated leaf values across 1,313 lines.
