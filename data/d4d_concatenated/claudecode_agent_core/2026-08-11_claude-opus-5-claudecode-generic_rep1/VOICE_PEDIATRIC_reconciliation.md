# VOICE_PEDIATRIC — Phase 3 / Phase 4 reconciliation

- **Run label:** `2026-08-11_claude-opus-5-claudecode-generic_rep1`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/VOICE_PEDIATRIC_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/VOICE_PEDIATRIC_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is the **Bridge2AI-Voice
Pediatric Dataset**, the PhysioNet project `b2ai-voice-pediatric`, recorded at
its project-level DOI `https://doi.org/10.13026/mf9s-5r03`, with release 1.1.0
as the described version (`doi: https://doi.org/10.13026/h995-bt35`). This is
the only dataset in the bundle that the declared scope names as this project's
referent, and it is held to consistently in both records.

The choice is load-bearing here because **five of the six documents in the
bundle are shared with the adult Bridge2AI-Voice project**: the USF IRB
protocol, the project documentation site, the NIH RePORTER page, the Data
Transfer and Use Agreement and the documentation-repository README are written
mainly about the adult cohort or about the Bridge2AI-Voice programme as a
whole. Only `physionet_pediatric_1_1_0` is scoped to this dataset. As the
manifest puts it, the overlap is in the evidence, not in the referent.

The adult dataset is expressed through the declared slot, `related_datasets`,
as `relationship_type: references`, and nowhere else. An automated scan for the
adult project's identifiers (`10.13026/37yb-1t42`, `10.13026/8xbn-nq66`,
`10.13026/k81f-qr68`, `10.13026/249v-w155`,
`physionet.org/content/b2ai-voice/`) finds them **only** inside
`related_datasets` in the full record and **not at all** in core, which has no
such slot. In particular no adult URL appears in `resources`,
`distribution_formats[].access_urls` or any distribution — the failure mode
#441 describes for the sibling project.

`d4d download scope --check --project VOICE_PEDIATRIC` reports the record in
scope.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs used, all on the Phase 1–3 allowlist: the declared bundle, the
source manifest, and the full and core LinkML schemas. No prior D4D record was
read, from any arm, label or date; nothing under `data/d4d_concatenated/` was
opened other than this run's own two outputs, and no `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` was touched. One incidental exposure is worth
recording: creating the output directory listed it, and the listing showed a
`CHORUS_d4d.yaml` filename written into the same version directory by a
concurrent run. The filename was seen; the file was not opened, and nothing
from it entered this record. No web fetch was made and no source refresh was
requested.

Structure was derived entirely from the schemas with LinkML `SchemaView` —
class slots, induced ranges, cardinality, inlining and enum permissible values
— rather than from any example record.

### Scope corrections: adult-release facts deliberately excluded

The largest category of finding was material that is true of the *adult*
release and would have been wrong here. The following were excluded and the
exclusions are recorded in the record's own `source_caveats`:

| Excluded | Why |
|---|---|
| 833 participants; ~61,937 voice-derived recordings; "around 833 instances" | adult release figures; the pediatric release is 300 participants and 23,533 recordings |
| versions 2.0.0 / 3.0.0 / 3.1.0 | adult version line; the pediatric line is 1.0.0 and 1.1.0 |
| "data was collected over a period of 12 months" | answered for the adult release; no pediatric collection window is stated anywhere in the bundle |
| Health Data Nexus hosting, T-CAIREM maintenance, semi-annual release cadence, derivative-dataset mechanism | describe the earlier feature-only release on that platform, not this PhysioNet release |
| the BIDS folder tree | published for `b2ai-voice-audio` and enumerating adult-only tables (`adhd_adult.tsv`, `ptsd_adult.tsv`); only the audio file naming was taken from it, with a caveat |
| healthsheet labeling, existing-use, data-protection-impact and "instances are unrelated" answers | answered for the adult release |
| healthsheet sensitive-category enumeration (race, sexual orientation, socioeconomic) | answered for the adult release; not carried onto a cohort of children |
| "Non-Probability Sample" study metadata | sits in a block that states the current dataset contains only adult populations, so neither `is_random` nor `is_representative` is asserted |
| "data is not representative because it was collected at a limited number of geographic locations" | adult-scoped; the pediatric single-site fact is recorded directly instead |
| HIPAA compliance status | the documentation's HIPAA answer describes the adult release, and the pediatric cohort was collected in Canada under a Canadian REB; `hipaa_compliant` is left absent rather than guessed |
| gift-card compensation amounts as this cohort's compensation | the protocol states compensation was provided to the adult population only, so `compensation_provided: false` is recorded for the pediatric cohort with the adult schedule described as not applying |

Where a programme-level statement *was* used — the registered-access
restrictions, the audit protocol, the de-identification answers, the IP terms,
retention rules — it carries a `source_caveats` naming the document it came
from and the scope limit on it.

### Source disagreements represented rather than merged

1. **Grant identifiers.** Four renderings appear. The PhysioNet release
   acknowledges `3OT2OD032720-01S1`; NIH RePORTER records `3OT2OD032720-01S3`
   (application 11376382, FY2025, award 4660942, 2022-09-01 to 2026-11-30); the
   documentation site renders two further strings corrupted in extraction
   (`3TF-OT2ActfOD032720Projectf01S1`, `Award #3Tf-OTOD03272001S2`). The two
   legible supplement numbers are recorded as **separate `Grant` objects**
   alongside the core project number `OT2OD032720`; the corrupted strings are
   described in `source_caveats` and are not reproduced as identifiers.
2. **Contributor name.** The PhysioNet author list spells "Jennifer Siu"; the
   documentation site spells the SickKids lead investigator "Jennifer Sui, MD".
   The dataset's own citation spelling is used and the disagreement is recorded
   on that creator.
3. **Ethics approval.** The pediatric release cites the Research Ethics Board
   at the Hospital for Sick Children. The USF protocol also covers a pediatric
   cohort from version 2 (2023-05-03) but states that Canadian institutions do
   not abide by the single-IRB process. Both reviews are recorded as separate
   `EthicalReview` entries, with the SickKids REB named as the approval under
   which these data were actually collected.

### Corrections made during the audit

Eleven corrections were applied to the full record and the core record was then
rebuilt from the corrected canonical full:

1. Author count corrected from "more than 130" to **121**, counted from the
   author list in the bundle rather than estimated.
2. `instances[0].description` no longer restates the `counts` value 23533.
3. `instances[1].description` no longer restates the `counts` value 300.
4. `subpopulations[0].description` removed — it asserted that age banding
   determines task assignment, which the bundle does not state.
5. `distribution_formats[0].format` removed: `"Parquet, TSV and JSON files"` was
   prose in a scalar slot; the formats now sit in the description and are
   carried structurally per file.
6. `distribution_dates[0].description` removed — it restated `release_dates`
   verbatim.
7. `version_access.versions_available` reduced to the version strings; the dates
   belong to `distribution_dates`.
8. `at_risk_populations.special_protections` no longer restates the free-speech
   PII check that `is_deidentified` and `cleaning_strategies` carry.
9. `participant_privacy.anonymization_method` narrowed to the study-identifier
   point rather than duplicating the de-identification removal list.
10. `regulatory_restrictions`: commentary about how the schema models the
    governance contact moved from `description` into `source_caveats`.
11. `funders[0].grants[*].name` set to the award title for all three grants
    instead of descriptive labels in a name slot.

Two shape defects found and fixed during Phase 1 before validation, recorded
here because they were real and would have shipped:

- Creators and organizations were first given **ORCID- and ROR-shaped URLs that
  do not resolve** (`https://orcid.org/creator_yael_bensoussan`,
  `https://ror.org/org_...`). These were fabricated identifiers in identifier
  slots. They were replaced with plainly local ids (`creator_…`, `org_…`).
- `reproschema-ui` was given the invented repository URL
  `https://github.com/ReproNim/reproschema-ui`. The bundle names the software
  but gives no repository, version or licence; the id is now local and a
  `source_caveats` says so.

### Schema-range limitation, recorded rather than papered over

`issued` has range `datetime` and the jsonschema check requires an RFC 3339
date-time. The bundle gives a publication **date** (May 1, 2026). Emitting
`2026-05-01T00:00:00Z` would assert a time and a UTC offset that no source
states, so `issued` is **absent in both records** and the publication date is
carried faithfully in the string-ranged slots `distribution_dates.release_dates`
and `updates`. Same reasoning for `created_on` and `last_updated_on`.

`is_tabular` is absent in both. The release mixes Parquet columnar binaries
with tab-separated text tables, so a single boolean would misdescribe it and the
bundle asserts neither. `FormatEnum` does not define Parquet, so the nine
parquet files carry no `format` value in either record; the format is stated in
their descriptions instead of forcing an undefined enum value.

### Slots deliberately left empty

`confidential_elements`, `content_warnings`, `splits`, `subsets`,
`collection_timeframes`, `labeling_strategies`, `imputation_protocols`,
`annotation_analyses`, `existing_uses`, `use_repository`, `other_tasks`,
`errata`, `data_protection_impacts`, `parent_datasets`, `total_file_count`,
`total_size_bytes`, `compression`, `status`, `download_url`. In each case the
only candidate content in the bundle is adult-scoped or absent. An absent slot
is the correct answer where the evidence is absent.

### Validation after correction

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>          -> No issues found
poetry run linkml-term-validator validate-data <full> --schema .../data_sheets_schema_all.yaml --target-class Dataset   -> Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core> -> No issues found
poetry run linkml-term-validator validate-data <core> --schema .../data_sheets_schema_core_all.yaml --target-class CoreDataset -> Validation passed
```

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Computed at runtime with `SchemaView`, not from a hand-written list:

- **78 schema-identical shared slots** (present on both `Dataset` and
  `CoreDataset` with the same induced range and cardinality).
- **1 projected slot**: `resources`, `Dataset` in full and `CoreDataset` in
  core. Unpopulated in both records, so the projection is vacuous here.
- **17 full-only slots**, of which **12 are populated** and therefore dropped in
  core: `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`,
  `participant_compensation`, `participant_privacy`, `related_datasets`,
  `relationships`, `third_party_sharing`, `variables`.
- **2 core-only slots**: `distributions` (populated) and `dialect` (absent —
  the bundle states no delimiter, quoting or header convention).

Of the 78 schema-identical slots, **54 are populated and 24 are absent from
both**. Presence and parsed value are identical in every one; an independent
deep-equality check over the parsed YAML reports zero mismatches, as does the
schema-derived validator.

The core record was **constructed by projection from the Phase 3-audited full
record**, so identity holds by construction as well as by check. No shared
value was condensed, paraphrased, reordered or omitted, including the narrative
fields.

### Notable content that core cannot carry

This is a property of `CoreDataset`, not a divergence, but it is worth naming:
the pediatric-specific consent and assent detail (`collection_consents`,
`collection_notifications`, `consent_revocations`, `direct_collection`), the
`participant_compensation` finding that pediatric participants were not
compensated, `participant_privacy`, the four documented parquet columns in
`variables`, the PhysioNet `citation`, and — most significantly — the
`related_datasets` link to the adult dataset all have no home in the core
schema. **The scope relation the manifest asks to be expressed is therefore
expressible only in the full record.** The core record remains in scope because
its `id` is the pediatric project DOI, but a reader of core alone cannot see
that a distinct adult dataset exists.

### Related-content mapping: `file_collections` -> `distributions`

The validator's warning `semantic-review-required` is answered here; the review
was performed, and the warning is not itself evidence that it was.

Mapping: each full `FileCollection` that enumerates `File` resources
contributes one `CoreDistribution` **per file**; each collection with no
enumerated files contributes one `CoreDistribution` for the collection. That
gives 12 file-level entries from `features` plus `phenotype` and `metadata` =
**14 distributions**, with **no unmatched core distributions** and complete
coverage of the full record's file inventory. Ids are preserved verbatim so the
correspondence is checkable rather than positional.

Field-by-field review of the mapped content:

- **Names, descriptions and paths** — copied verbatim; byte-identical for every
  matched pair.
- **Formats** — `format` has the same `FormatEnum` range on `File` and
  `CoreDistribution`; the two `.tsv` entries carry `TSV` and the data-dictionary
  entry carries `JSON` in both. The nine parquet entries carry no `format` in
  either record, consistently.
- **Compression** — absent in both; the bundle states none.
- **Checksums and byte counts** — absent in both; the release publishes no md5,
  sha256 or file sizes. Accordingly `total_file_count` and `total_size_bytes`
  are absent in full and there are no distribution-level counts to contradict
  them.
- **Access URLs** — carried by `distribution_formats`, a schema-identical shared
  slot, deeply identical across the pair. The two access routes are the
  PhysioNet release page for the features and Synapse `syn73617068` for the raw
  audio; both are pediatric routes and no adult URL appears in either.
- **Release scope** — every path is relative to release 1.1.0 in both records;
  version 1.0.0 appears only as a prior release under `distribution_dates` and
  `version_access`, and the v1.1 release notes appear under `updates`. A
  historical release is therefore distinguished from the current one rather than
  read as a contradiction.
- **Full-only nested slots omitted from the projection** — `file_type` on `File`
  and `collection_type` on `FileCollection` have no `CoreDistribution`
  counterpart, and the collection-to-file nesting is flattened. Nothing else is
  lost.
- **Top-level identity and access facts versus distributions** — `id`, `doi`,
  `version`, `page`, `publisher`, `license`, `license_and_use_terms` and
  `regulatory_restrictions` are schema-identical and deeply identical, and agree
  with the distribution-level content: one restricted-access PhysioNet release
  under the Bridge2AI Voice Registered Access License, with raw audio held
  separately under controlled access.

**Unresolved contradictions within or between the two records: none.**

### Internal consistency spot-checks

Repeated values agree throughout both records: the release version (1.1.0), the
two DOIs, the recording count (23,533 with the sparc files at 23,532, stated
consistently in `instances`, `anomalies` and `missing_data_documentation`), the
participant count (300), the age range (2-18), the single collecting site
(Hospital for Sick Children), the licence and agreement names, the access
policy, and the organisations and people named across `creators`,
`data_collectors`, `ethical_reviews` and `maintainers`.

### Commands run

```bash
poetry run d4d download scope --project VOICE_PEDIATRIC
poetry run d4d download scope --check --project VOICE_PEDIATRIC
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project VOICE_PEDIATRIC --method claudecode_agent \
  --label 2026-08-11_claude-opus-5-claudecode-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt
poetry run d4d runs validate --project VOICE_PEDIATRIC --label 2026-08-11_claude-opus-5-claudecode-generic_rep1
poetry run d4d runs check --strict
poetry run d4d api prompts check --strict
```

`--sync-core` was **not** used. Core was built by projection from the audited
full record, so it was already identical; running the synchroniser would have
had nothing to do. The validator was run only in its independent, non-mutating
form.

### Header note

The header block was mandated verbatim by the rendered instruction and is used
exactly, with `phase 1` -> `phase 2` and the core schema path substituted in the
core file as instructed. Two lines required by the playbook's completion
criteria and absent from the mandated block were **added to the core header
only**: `# Full D4D input:` naming the same-run full record, and
`# Phase 4 reconciliation: completed`. No `# Reasoning effort:` line was added
to either header; reasoning effort is established by the provenance recorder,
not by the header, and this run's launcher did not state one.

## Prompt canonicality and the render gate

| check | result |
|---|---|
| `d4d api prompts check --strict` | 10 prompt files, **0 not at their pin** |
| `canonical_prompt_status` for this run | **canonical** |
| `verify_request` (render gate) for this run | **match** |
| `d4d runs check --strict --project VOICE_PEDIATRIC` | 4 runs, 0 failing, **exit 0** |

The instruction as sent was verified independently of the gate: rendering
`d4d prompt render --project VOICE_PEDIATRIC --label <this label> --condition
generic --arm baseline --runtime 'Claude Code' --bundle <declared bundle>`
produces a file **byte-identical** to the instruction this run received
(md5 `5bc9c8e417a58d236839ea50c305f23a`). Rendering under `generic_v2`,
`generic_v3` and `generic_v4` differs by 24, 36 and 44 diff lines
respectively. This run is unambiguously the `generic` condition, and the label
says `generic`, so the #420 label-versus-condition mismatch that affects the
three `2026-08-07 …-generic-v3` VOICE_PEDIATRIC runs does not affect this one.

### Finding: `--arm` means two different things across the two commands

Getting the gate to `match` exposed a defect worth filing. `d4d prompt render`
takes `--arm` as an enum (`baseline`) and expands it to the **display name**
`BASELINE (input documents only)` before substituting `{ARM}`, which is what
the prompt file documents `{ARM}` to be. `verify_request` re-renders by feeding
the stored `spec.arm` **verbatim** into `RunSpec`. So a record that stores the
canonical token `arm: baseline` — the obvious thing to store, and what
`d4d provenance record --arm` defaults to — can never re-render to what was
sent, and the gate reports a false `mismatch` naming an unchanged prompt file:

```
arm='baseline'                        -> ad6b4f3dd32a   (differs from sent)
arm='BASELINE (input documents only)' -> b83a6651edf2   (identical to sent)
```

The two differing lines are `ARM:` and `# Arm:`. The corpus convention is the
display string (3 existing records store it, and only this run's first attempt
stored `baseline`), so the record now stores the value that actually rendered,
which is both truthful and reproducible. But the two flags share a name and not
a value space, the failure is silent, and it points at the prompt file rather
than at the spec — a launcher following the playbook literally would record a
run that fails `--strict` for a reason that is not about its prompt.

### Note on who wrote the provenance record

The rendered instruction directs the agent to write the live provenance record
after Phase 4, and it was written here. The launching message separately said
the launcher would write it. The record is `record_mode: live`, names both the
prompt file and the instruction as sent, and carries its validation verdict
forward; re-recording is safe and non-destructive (#396), so the launcher may
re-record without losing the verdict.

## Outcome

- Both records pass schema validation and ontology term validation.
- 78 schema-identical shared slots: identical presence and deeply identical
  parsed content, zero mismatches.
- 1 projection (`resources`) — vacuous; 1 related-content mapping
  (`file_collections` -> `distributions`) — 14 matched, 0 unmatched,
  semantically reviewed above.
- Zero unresolved contradictions within or between the records.
- Record in scope; the related-but-distinct adult dataset expressed only through
  `related_datasets`.
