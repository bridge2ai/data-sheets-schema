# CHORUS reconciliation report

- **Version label:** 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3
- **Mode:** four-phase project agent, generic-v6 prompt
- **Arm:** BASELINE (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
  (md5 `9b2ef4b65d67957f79362266cab0bc7a`, 1698 lines, 8 chunks)
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d_core.yaml`
- **Coverage receipt:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The record is about the **CHoRUS dataset**, identified
by `https://chorus4ai.org/`, matching the manifest's `scope:` declaration for this
project (`referent: CHoRUS dataset`, `referent_id: https://chorus4ai.org/`,
`related_but_distinct: []`). No dataset DOI appears in any CHORUS source document, so
the project site is the identifier used, as the manifest's `referent_note` records.
`d4d download scope --check --project CHORUS` reports the record in scope.

The choice matters here because two of the four bundle documents are substantially
about something else. The cohort 2 webinar (chunks c003–c005) is a recruitment deck
for the **AIM-AHEAD Bridge2AI for Clinical Care Training Program**; the GitHub
organization overview (c007–c008) is about the **chorus-ai software organization**.
Facts belonging to those two entities — the training program's curriculum, trainee
eligibility, application deadlines and $8,000 trainee stipend; the repositories' star
counts and update timestamps — are not facts about the dataset and were not recorded
as such. The exceptions are the places where those documents speak about the data:
the webinar's data-type table and access conditions, and the README's account of the
tooling, SOPs and access-request route. Those chunk entries carry a `notes:` field
saying explicitly what was left out and why.

One consequence is deliberate: the **$8,000 stipend is not recorded under
`participant_compensation`**. It is paid to trainees of the training program, not to
the human research participants whose records constitute the dataset, and
`HumanSubjectCompensation` is about the latter.

## Phase 1 — full record from the input documents

Read the chunk manifest (`d4d bundle chunk --check --project CHORUS` reported
`current` for all three CHORUS bundles), then read all 8 chunks with the file-reading
tool in manifest order, writing each chunk's coverage-receipt entry before opening the
next.

| chunk | source | status |
|---|---|---|
| c001 | `<preamble>` | `nothing_relevant` — concatenation header and table of contents |
| c002 | `reporter_nih_gov_project-details-10472824_row7.txt` | `extracted` (19 receipts) |
| c003 | `bridge2ai-for-clinical-care-informational-webinar-cohort-2_row9.txt` (1/3) | `extracted` (24 receipts) |
| c004 | same document (2/3) | `extracted` (5 receipts) + `notes` on what was excluded |
| c005 | same document (3/3) | `extracted` (1 receipt) + `notes` on what was excluded |
| c006 | `chorus4ai_org_row11.txt` | `extracted` (19 receipts) |
| c007 | `github_chorus_ai_overview_2025-11-14.txt` (1/2) | `extracted` (27 receipts) |
| c008 | same document (2/2) | `extracted` (13 receipts) + `notes` on what was excluded |

`d4d receipts check --strict`: **chunks 8/8 reviewed · snippets 108/108 verified ·
no findings**. Slots with a receipt: 96 of 182 (23 exempt) — reported, not gated.

## Phase 2 — core derived by projection

One command, no model judgement. The command printed:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d.yaml",
          "md5": "a2ae15169a939758067acf6893b1bcb6"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The core was derived once after Phase 1 and re-derived in Phase 4 with
`--phase4-complete` from the audited full record; the md5 above is the audited one.
The core was never edited by hand and `--sync-core` was never passed.

## Phase 3 — source and provenance audit

### Provenance

No prior generated D4D record was read, from any arm, label or date. Nothing under
`data/d4d_concatenated/` was opened other than this run's own three output files, and
no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was opened. The factual inputs were
the declared bundle and the source manifest; the schema files supplied structure only.
The full record's structure was derived from class `Dataset` in
`data_sheets_schema_all.yaml` via the LinkML `SchemaView` induced-slot view, not from
any example record.

### Source disagreement, resolved by the manifest's ranking

**Admission count.** Two sources give a figure and they disagree:

| source | tier | value |
|---|---|---|
| `project_documentation` (chorus4ai.org) | 2 | "Current Released Dataset — 50,000 Patient admissions from ICU, PICU, and NICU" |
| `cohort_2_webinar` | 4 | "As of August 2025, covers 14 different hospitals with over 45K unique admissions" |

`source_priority` ranks documentation at tier 2 and the tutorial at tier 4, lowest
tier strongest, so **50,000 is stated** in `instances[0].counts` and the disagreement
is recorded in `instances[0].source_caveats` naming both figures and which was
preferred. The caveat also notes that only the webinar dates its figure, so the two
may describe different moments rather than contradicting each other.

**The 100,000 figure is not part of that disagreement.** NIH RePORTER's "more than
100,000 critically ill patients" matches the project site's *Anticipated Final
Dataset* of 100,000 patient admissions, not the released one. It is recorded under
`updates.update_details` as the growth target, not as a count of what exists.

**License.** The GitHub README states "This project is licensed under the MIT
License". Every data type in the same bundle is listed with an access control of
`Controlled`. These are not in conflict: the MIT statement governs the software
organization, not the data. The record therefore leaves the dataset's `license`
**unset**, records the MIT and per-repository licenses inside
`external_resources[0].description`, and explains the distinction in the record's
top-level `source_caveats`. Asserting MIT on the dataset would have been the error
this separation exists to avoid.

### Evidence the extraction could not fully resolve

The webinar's data-type table has five columns (data type, data standard, access
control, metadata, published metadata schema). PDF text extraction interleaved the
columns. Data standard and the uniformly `Controlled` access control could be aligned
to individual rows with confidence; the per-row *metadata* and *published metadata
schema* values could not. Those values are therefore reported at the dataset level in
`description` and the alignment limit is stated in the top-level `source_caveats`,
rather than assigned to rows on a reconstruction the text does not support.

### Identifiers

The bundle supplies **no ORCID for any named individual and no ROR for any
organization**. Under the identifier-from-evidence rule none was supplied from model
knowledge. This has a structural consequence worth stating: `Person` and `Software`
both declare `id` as **required**, so populating `Creator.principal_investigator`,
`EthicalReview.contact_person`, `LicenseAndUseTerms.contact_person`,
`DataGovernance.committee_contact` or any `used_software` entry would have forced an
identifier the evidence does not contain. Those slots are therefore left unset and
their content is carried in string-ranged slots that need no identifier —
`Creator.name` and `Creator.affiliations[].name` for people and their institutions,
`Maintainer.maintainer_details` for the program-manager contact,
`DataGovernance.access_review_process` for the access-request addresses, and
`ExternalResource.description` for the repositories. `Organization` and `Grant` both
declare `id` optional, so those objects are populated with names and numbers only.

No fragment identifier was minted. Under the v6 rule a fragment is minted only where
another value in the record must point at the part it names, and no value in this
record points at a part. This is also why the nine data types are recorded as
`distribution_formats` entries (whose `id` is optional and is omitted) rather than as
`file_collections` entries, which would have required nine minted ids that nothing
references.

Grounding check: **0 absent, 0 minted_fragment, 0 grounded** — the record states no
`uriorcurie`-slot identifier the bundle does not contain.

### Corrections made in Phase 3

Two source-supported facts were found missing from the full record and back-ported,
each with its receipt added to the existing entry of the chunk the passage sits in:

1. **`instances[0].description`** — extended with the NIH RePORTER abstract's account
   of what is acquired per instance, including *social determinants of health*, which
   is a tenth data category the webinar's nine-row table does not carry. Receipt added
   to c002.
2. **`variables[0]`** — a new entry for *geographic distance to the nearest hospital*,
   named in the abstract as an example of the contextual factors the project ensures
   data elements feature, with `derivation` recording the UF-Geocoding repository that
   geocodes OMOP Location entities via DeGauss. Receipts added to c002 and c008. Its
   `source_caveats` states that the sources do not themselves connect the factor to
   the tooling.

Twenty-eight receipt entries written during Phase 1 named a provisional slot path that
differed from where the fact finally landed (for example `file_collections[n]` →
`distribution_formats[n]`, and every `used_software[n]` →
`external_resources[0].description` once the required-`id` finding above ruled
`Software` objects out). Each was edited **in place** in its existing chunk entry; no
second entry was created for any chunk. A further seventeen were repointed so that
each snippet sits under a slot whose value it actually supports rather than a
neighbouring one — for example the "over 45K unique admissions" snippet now sits under
`instances[0].source_caveats`, where that figure is stated, not under
`instances[0].counts`, whose value is 50,000.

No stale, mis-scoped or unsupported assertion was found in the record beyond these.

## Phase 4 — re-derivation, checks, repair

1. Core re-derived from the corrected full record with `--phase4-complete`, which
   wrote the `# Phase 4 reconciliation: completed` header line.
2. Pair consistency: **PASS — 79 schema-identical slots; projected slots
   `['resources']`; per-record slots (exempt, must differ)
   `['conforms_to_class', 'conforms_to_schema']`.** No errors and **no
   `semantic-review-required` warning was emitted**, because the record carries no
   `file_collections` and the core therefore carries no `distributions`.
3. Grounding: `{'grounded': 0, 'minted_fragment': 0, 'absent': 0}`.
4. Schema and term validation re-run on both records after every correction.
5. **No repair phase.** No checker reported a finding that required a change, so
   neither `repair` nor `report_after_repair` is recorded.

## Claims

No slots were removed.

## Semantic review

The pair checker emitted no `semantic-review-required` warning. The unprompted reviews
are performed and recorded regardless, because the projection carries values without
checking them.

| review | finding |
|---|---|
| `file_collections` ↔ `distributions` (the checker's warning) | Not applicable: the record populates no `file_collections`, so the core has no `distributions`. The nine data types are carried as `distribution_formats`, a full-record-only slot, so nothing was projected here and nothing could diverge. **reviewed: consistent** |
| `total_file_count` / `total_size_bytes` against the entries beneath them | Both are **unset**, correctly. The bundle gives "23 Tb Waveform data" for one modality only, with a unit ("Tb") that does not distinguish terabits from terabytes, and gives no file counts at all. A total covering all modalities cannot be computed from one modality's ambiguous figure, so the figure is stated verbatim in `instances[0].description` and neither aggregate slot is populated. **reviewed: consistent** |
| `dialect` / `is_tabular` against the files | Both **unset**, correctly. `dialect` is derived only from `File` entries and the record has none. `is_tabular` was deliberately not set: the dataset spans OMOP tabular data *and* DICOM imaging, WFDB and EDF+/Persyst waveforms and tokenized text, so neither `true` nor `false` is true of it, and a single boolean would misrepresent nine modalities. **reviewed: consistent** |
| historical release read as the current one | Checked and corrected during drafting. Three figures in the bundle describe different moments and are kept apart: 50,000 admissions is the **current released** dataset (`instances[0].counts`); 100,000 admissions and 9 modalities are the **anticipated final** dataset (`updates.update_details`); "over 45K unique admissions" is the webinar's **August 2025** snapshot (`instances[0].source_caveats`). The imaging figure (approximately 1000 images, de-identification in process) and the EEG status (extraction in process) are likewise dated to August 2025 in `known_limitations`. Separately, the GitHub overview is a **2025-11-14 capture** retained as historical documentation; `external_resources[0].source_caveats` says so, and its repository inventory is not asserted as current. **reviewed: corrected** |
| creators as distinct entities | The six named members of the Bridge2AI CHoRUS Leadership Team are seven `Creator` entries (six people plus the consortium), one per entity, not one collapsed entry. **reviewed: consistent** |
| project naming | The manifest's canonical label `CHoRUS` is used throughout the prose this record composes. Source spellings are preserved where quoted, including the project site's own misspellings "repoitory" and the contact domain "mgh.havard.edu", both flagged in `source_caveats` rather than silently corrected. **reviewed: consistent** |

## Files changed

| file | phase |
|---|---|
| `.../claudecode_agent/2026-08-28_.../CHORUS_d4d.yaml` | 1 (written), 3 (back-port) |
| `.../claudecode_agent_core/2026-08-28_.../CHORUS_d4d_core.yaml` | 2 (derived), 4 (re-derived) |
| `.../claudecode_agent_core/2026-08-28_.../CHORUS_coverage_receipt.yaml` | 1 (written), 3 (slot paths corrected in place) |
| `.../claudecode_agent_core/2026-08-28_.../CHORUS_reconciliation.md` | 4 |
| `.../claudecode_agent_core/2026-08-28_.../CHORUS_provenance.yaml` | 4 |

## Commands

```bash
poetry run d4d bundle chunk --check --project CHORUS
poetry run d4d download scope --project CHORUS
poetry run d4d download priority --project CHORUS
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 \
  --project CHORUS --strict
poetry run d4d derive core \
  --full data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d.yaml \
  --out  data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CHORUS_d4d_core.yaml \
  --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset <core>
# grounding check (data_sheets_schema.grounding.check_run)
# report-claims check (data_sheets_schema.report_claims.check_report)
poetry run d4d download scope --check --project CHORUS
poetry run d4d prompt render --project CHORUS \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 \
  --condition generic_v6 --runtime 'Claude Code' --out <rendered>
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt \
  --condition generic_v6 --arm baseline --runtime 'Claude Code' --provider 'Anthropic' \
  --receipt-expected \
  --prompt src/download/prompts/d4d_generic_arm_prompt_v6.md \
  --prompt-text <rendered> \
  --phase '{"name":"generate_full",...}' --phase '{"name":"derive_core",...}' \
  --phase '{"name":"source_audit",...}' --phase '{"name":"reconcile",...}' \
  --phase '{"name":"report",...}'
poetry run d4d receipts check --label <label> --project CHORUS --strict --write
poetry run d4d runs validate --project CHORUS --method claudecode_agent --label <label>
poetry run d4d runs check --project CHORUS --strict
```

### The recorded instruction, and two corrections to how it was recorded

`--prompt-text` takes the instruction **as sent**, not the prompt file it was built
from. Recording the file instead made the render gate report `mismatch`, because the
gate re-renders the spec and compares. The instruction was therefore rendered with
`d4d prompt render` and that file passed instead — and it is **byte-identical
(md5 `f0a9e268ca869c588ace0f423d212ad1`) to the instruction this agent was actually
sent**, so the honest value and the gate-satisfying value are the same bytes here.

A second re-record was needed because the recorder inferred
`provider: LBL CBORG (proxy to Anthropic)` from the environment, while the
instruction was rendered — and the record's header written — under
`Provider: Anthropic`. A spec naming the wrong provider re-renders to different bytes,
so the gate still reported `mismatch` against a correct instruction. Passing
`--provider 'Anthropic'` (with `--arm baseline`) makes the recorded spec describe the
render that actually happened. `d4d runs check --project CHORUS --strict` then reports
**no finding of any kind against this run**.

Neither correction changed a value in either record; both concern how the run's own
provenance was described. They are recorded here rather than as a `repair` phase for
that reason.

## Final results

| check | result |
|---|---|
| full record — `linkml-validate` (class `Dataset`) | **No issues found** |
| full record — `linkml-term-validator` | **Validation passed** |
| core record — `linkml-validate` (class `CoreDataset`) | **No issues found** |
| coverage receipt — `d4d receipts check --strict` | **8/8 chunks, 108/108 snippets, no findings** |
| pair consistency | **PASS**, 79 identical slots, 0 errors, 0 warnings |
| grounding | 0 absent, 0 minted_fragment |
| scope | in scope |
| repair required | none |

Slot counts, informational only and never a quality gate: the full record populates
**50 top-level slots (249 including nested)**; the core populates **46 top-level slots
(232 including nested)**.
