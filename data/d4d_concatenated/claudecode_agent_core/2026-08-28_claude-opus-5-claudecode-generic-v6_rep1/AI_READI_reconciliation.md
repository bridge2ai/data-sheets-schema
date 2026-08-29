# AI_READI reconciliation — 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1

Four-phase project agent, generic-v6 prompt, BASELINE arm (input documents only).
Runtime Claude Code, provider Anthropic, model claude-opus-5, temperature 0.0.

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_coverage_receipt.yaml`
- Declared input bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
  (md5 `0f3abb51a333555456bedd63891fcd99`, 7,376 lines, 28 chunks)

## Referent

`Dataset` admits one referent. The record is about **the AI-READI dataset,
version 3.0.0** — "Flagship Dataset of Type 2 Diabetes from the AI-READI
Project", `doi:10.60775/fairhub.3`. This is the referent the manifest's `scope:`
block declares for AI_READI (`AI-READI dataset <https://doi.org/10.60775/fairhub.3>`),
and it is the release the tier-1 sources in the bundle describe. Facts belonging
to earlier releases (v1.0.0's 204 participants, v2.0.0's 1067 participants and
2.01 TB across 165,051 files) are recorded under `version_access`, explicitly
scoped to those versions, and are not asserted of the current release. The
referent is held consistently across both records; `d4d download scope --check
--project AI_READI` reports the record is not about a dataset the project
declares distinct.

## Phase 1 — full record from the input documents

Read the chunk manifest first (`d4d bundle chunk --check --project AI_READI`
reported `current` for both the document bundle and its healthsheet-only
companion), then read all 28 chunks in manifest order with the file-reading
tool, writing each chunk's coverage-receipt entry before opening the next.

**Receipt outcome:** chunks 28/28 reviewed, snippets 580/580 verified, no
findings. Twenty-five chunks are `extracted`; three are `nothing_relevant`
— c001, the concatenation tool's preamble and table of contents, which states
no fact about the dataset, and c025 and c026, both unfilled sections of the
University of Washington IRB protocol form (instruction text and unticked
checkbox options with no study-specific answer). The filled-in AI-READI answers
to that same form appear in c027 and c028 and are extracted there.

`slots without a receipt` is reported and not gated: 348 of 639 populated slot
paths carry a receipt, 28 are exempt by construction. The uncovered remainder
is mostly leaf prose inside objects whose entry-level facts are receipted.

## Phase 2 — core derived by projection

`d4d derive core` was run on the validated Phase 1 file and re-run in Phase 4
with `--phase4-complete`. No model judgement is involved. The command printed:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": ".../AI_READI_d4d.yaml", "md5": "<full record md5 after repair; see AI_READI_provenance.yaml>"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

## Phase 3 — source and provenance audit

**Provenance result: clean.** No prior full or core D4D record, from any arm,
label or date, was read, opened, grepped or consulted. Nothing under
`data/d4d_concatenated/` and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml`
under `data/ro-crate_packages/` was touched. The factual inputs were the
declared bundle, `data/preprocessed/source_manifest.yaml` (for the scope,
naming and `source_priority` declarations) and the LinkML schemas. Structure
was derived from class `Dataset` in `data_sheets_schema_all.yaml` via
`SchemaView`, not from any prior record.

### Source disagreements resolved by the declared ranking

The manifest ranks AI_READI's sources in four tiers: tier 1 data resource,
structured metadata and RO-Crate; tier 2 documentation, license and IRB; tier 3
publications; tier 4 the NIH RePORTER page. Seven disagreements were found and
each is recorded in a `source_caveats` slot naming what each source said and
which was preferred.

| Disagreement | Sources | Resolution |
|---|---|---|
| Acronym expansion: "Equitable" vs "Exploratory" Atlas | tier 3 BMJ Open vs tier 1 FAIRhub metadata and README | tier 1 preferred; both recorded in `source_caveats` |
| Target enrollment 4000 vs 4600 | tier 1 FAIRhub (4000, Anticipated) and tier 3 publications vs tier 2 IRB protocol (4600) | tier 1 stated |
| Blood volume 53 mL vs 50-60 mL | tier 3 BMJ Open vs tier 2 IRB protocol | tier 2 stated |
| Study visit 2.5-4 h vs 3-4 h | tier 3 BMJ Open vs tier 2 IRB and tier 3 Nature | tier 2 stated |
| Publisher: FAIRhub vs AI-READI Consortium | tier 1 FAIRhub metadata vs tier 1 RO-Crate | **same rank — ranking cannot decide**; `publisher` left unpopulated and both recorded in `source_caveats` |
| Enrollment window 2023-07-18/2026-11-30 vs 2022-2026 | tier 3 BMJ Open vs tier 3 Nature | **same rank**; both recorded as separate `collection_timeframes` entries with a caveat |
| Grant number `OT2ODO32644` vs `OT2OD032644` | tier 1 healthsheet vs tier 1 RO-Crate, FAIRhub funding reference and tier 4 RePORTER | the three-source spelling stated; the healthsheet's typo recorded in `funders[0].grants[0].source_caveats` |

Two further within-source tensions are recorded rather than silently resolved:
the RO-Crate names the reviewing board "Washington University IRB" while giving
a University of Washington Human Subjects Division address and the UW protocol
number (`ethical_reviews[0].source_caveats`); and the FAIRhub metadata records
`deIdentType: NoDeIdentification` with `deIdentDirect` and `deIdentHIPAA` both
true while the RO-Crate records `deidentified: true`
(`is_deidentified.source_caveats`).

### Back-ports into the full record

Two source-supported omissions were back-ported, each with its `{slot, snippet}`
pair added to the existing receipt entry of the chunk the passage sits in:

| Slot | Value added | Chunk |
|---|---|---|
| `version_access.versions_available[1]` | v2.0.0 size, 2.01 TB across 165,051 files | c013 |
| `created_by` | AI-READI Consortium (the RO-Crate `author`) | c022 |

`d4d receipts check --strict` was re-run after the back-port and reports 580/580
snippets verified with no findings.

### Shape audit

No shape violations were found in the audit pass. Two shape corrections were
made during Phase 1 in response to `linkml-validate`, before the record was
first declared valid:

- `principal_investigator`, `contact_person` and `committee_contact` declare a
  `Person` range that is **not inlined**, so the schema requires the referent's
  identifier rather than the object. Each was written as the person's `ORCID:`
  CURIE (and `mailto:hsdrely@uw.edu` for the IRB reliance contact, where the
  bundle supplies an address but no registry identifier), with the person's
  name, degree and email moved into the enclosing `Creator`'s `name` and
  `description` and their organization into `Creator.affiliations`.
- `FileCollection.id` is required. Each of the ten collections was given a
  fragment on the dataset's own attested DOI CURIE
  (`doi:10.60775/fairhub.3#cardiac-ecg` and so on).

`credit_roles` was left unpopulated: the bundle records the role
"Study Principal Investigator", which no CRediT term in the schema's enum
expresses, and omission is preferred to forcing a near-match.
`limitation_type` and `bias_type` were populated only where the bundle names the
category — `selection_bias` is populated because the BMJ Open protocol writes
"there is selection bias known as volunteer bias" — and omitted elsewhere.

## Phase 4 — re-derivation, checks, repair

The core was re-derived from the corrected full record with `--phase4-complete`
(which wrote the `# Phase 4 reconciliation: completed` header line), and every
check re-run.

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` | PASS: 79 schema-identical slots; projected `resources`; 1 semantic warning |
| grounding (`check_run`) | grounded 22, minted_fragment 10, **absent 0** |
| `d4d receipts check --strict` | chunks 28/28, snippets 580/580, no findings |
| `d4d download scope --check` | in scope |

**Grounding.** No identifier in either record is `absent` — that is, the record
states no identifier the bundle does not. All 15 ORCIDs and all 9 RORs are
transcribed from the tier-1 FAIRhub study description, which supplies them
directly; none was supplied from model knowledge. The 10 `minted_fragment`
identifiers are the `file_collections` ids, each a fragment on the dataset's own
attested DOI CURIE. Under the v6 minting rule a fragment is minted only where
another value in the record points at that part: these are pointed at, because
the derived core's `distributions` are built from `file_collections` and carry
those ids, and the schema requires `FileCollection.id`. No fragment was minted
for a part that is only described — the sub-directory modalities and devices
(`ecg_12lead`, `philips_tc30`, `heidelberg_spectralis`, and so on) are described
in each collection's `description` and carry no identifier.

**Repair.** One finding did require a change. The `form` check written into the
provenance record reported 9 British spellings across the pair. Each sat in prose
this record composes rather than in a quotation, a title, a name or an
identifier, so the American-English rule applies and its carve-outs do not: the
full record was repaired (`Enrolment`/`enrolment` → `Enrollment`/`enrollment`
×3, `strict licence agreement` → `strict license agreement`, `haemodynamic` →
`hemodynamic`, `tumour` → `tumor`, `optic disc oedema` → `optic disc edema`,
`colour fundus photograph` → `color fundus photograph`, `minimise` →
`minimize`), the core re-derived from it, and every validation and check from
steps 1-3 re-run clean. The repair touched the full record only; the core is its
projection.

The same check reported 2 occurrences of the label variant `AI READI`. Both are
the RO-Crate's own `name` for one subcrate, "AI READI Wearable Activity
Monitoring Subcrate" — a proper noun as the source states it, which the naming
rule's carve-out exempts. It was left exactly as written. Note also that
`analysis` and `analyses` appear throughout and are correct American English
(the British form is the verb `analyse`); they are not defects.

Receipt snippets were not touched by the repair: a snippet is verbatim source
text and keeps the spelling its chunk uses, which is why all 580 still verify
against the bundle after the record's prose was Americanized.

## Claims

No slots were removed.

## Semantic review

| Review | Finding |
|---|---|
| `file_collections` ↔ `distributions` (the pair checker's only `semantic-review-required` warning) | 10 deterministic matches at collection level, 0 at nested resource level, no unmatched core distributions. Each core distribution carries the same id, name, description, path, `conforms_to` and `conforms_to_standard` as its source collection, and `bytes` from the collection's `total_bytes`. The nested level is empty in both records because no individual `File` entries were emitted — **reviewed: consistent** |
| `total_file_count` / `total_size_bytes` against the entries beneath them (unprompted) | The nine data-type collections' `file_count` values sum to 356,334; the root metadata collection adds 9, giving exactly the declared `total_file_count` of 356,343. Their `total_bytes` sum to 3,815,969,360,064 against a declared `total_size_bytes` of 3,815,969,779,678; the 419,614-byte residual is the nine root metadata files, whose size the bundle does not state, so that collection correctly carries `file_count` and no `total_bytes` — **reviewed: consistent** |
| `dialect` / `is_tabular` against the files (unprompted) | `dialect` is absent from both records, correctly: the derivation emits it only when every `File` entry agrees on one value, and no `File` entries were emitted. `is_tabular` is `false`, which matches the healthsheet's statement that the modalities "encompass tabular data, imaging data, and physiological signal/waveform data" — the dataset is not structured as a table — **reviewed: consistent** |
| Historical release read as the current one (unprompted) | Checked every count, size, date, DOI and participant figure for release scope. The current-release values (2280 participants, 3.82 TB, 356,343 files, `doi:10.60775/fairhub.3`, issued 2025-11-17, collection window 2023-07-19 to 2025-05-01) are asserted at the top level. Historical values are confined to `version_access.versions_available`, `version_access.version_details`, `distribution_dates` and `instances[0].notes`, each naming the version it belongs to. The v2.0.0 documentation chunk (c010), which the bundle marks "no longer accessible", contributed no top-level current-release fact that the v3.0.0 sources do not also support — **reviewed: consistent** |
| Instance count against the enrollment target (unprompted) | `instances[0].counts` is 2280, the participants in release 3.0.0, not the 4000 target enrollment; the target is held separately in `sampling_strategies[0].strategies` and `source_data` and labelled as anticipated — **reviewed: consistent** |

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_d4d.yaml` (created)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_d4d_core.yaml` (derived, re-derived in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_coverage_receipt.yaml` (created)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/AI_READI_reconciliation.md` (this file)

## Commands run

```bash
poetry run d4d bundle chunk --check --project AI_READI
poetry run d4d download scope --project AI_READI
poetry run d4d download priority --project AI_READI
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 \
    --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --strict
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> \
    --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d derive core --full <full> --out <core>
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> \
    --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -c "... data_sheets_schema.grounding.check_run ..."
poetry run python -c "... data_sheets_schema.report_claims.check_report ..."
poetry run d4d download scope --check --project AI_READI
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
    --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 \
    --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
poetry run d4d runs validate --project AI_READI --method claudecode_agent \
    --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1
```

## Final results

- Full record: 82 top-level slots, 1,478 lines (informational metadata, not a quality gate).
- Core record: 69 top-level slots, 1,366 lines (informational metadata, not a quality gate).
- Both records pass schema and ontology-term validation.
- Pair checker passes on the re-derived pair with its one expected semantic warning, reviewed above.
- Coverage receipt complete and verified; grounding reports no ungrounded identifier.
