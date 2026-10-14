# AI_READI full/core reconciliation — 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2

Run label: `2026-08-24_claude-opus-5-claudecode-generic-v5_rep2`
Mode: four-phase project agent, generic-v5 prompt, BASELINE arm (input documents only)
Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5 · Temperature 0.0
Reasoning effort: high (asserted by the launcher; this runtime cannot capture its own
reasoning accounting)

Files produced by this run:

| Artifact | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_reconciliation.md` |

Declared inputs: `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
(md5 `0f3abb51a333555456bedd63891fcd99`, 7376 lines, 11 source documents) and
`data/preprocessed/source_manifest.yaml`, plus the two LinkML schemas.

---

## Referent

`Dataset` admits one referent. This record is about **the AI-READI dataset as released at
version 3.0.0** — "Flagship Dataset of Type 2 Diabetes from the AI-READI Project", DOI
`10.60775/fairhub.3`, published 17 November 2025, 2280 participants, 356,343 files, 3.82 TB.
That is the referent the manifest's `scope:` block declares (`referent_id:
https://doi.org/10.60775/fairhub.3`), and the manifest's `referent_note` states that
`fairhub.1` and `fairhub.2` are earlier releases of the same dataset rather than separate
datasets. Both records hold to that choice: `id`, `doi`, `version`, `issued`,
`version_access.latest_version_doi` and the version-3 entry in `distribution_dates` all name
release 3.0.0, and the earlier releases appear only as `related_datasets` entries
(`is_new_version_of`) and as historical entries in `version_access.versions_available`, each
with its release scope stated explicitly.

The project's declared canonical label, `AI-READI`, is used in every sentence composed for
these records; the string appears 50 times and no variant spelling appears. Quoted source
text, proper nouns and identifiers keep the form their source used.

Two candidate referents were rejected. The version 2.0.0 FAIRhub record, retained in the
bundle as the only surviving account of the 2.01 TB / 165,051 file figures, describes an
earlier release of the same dataset and is recorded as such. The "smaller version available
for pipeline development" that the FAIRhub v3 page and the v3 documentation mention is a
distinct resource, but the bundle gives no identifier for it (only an unlabeled `"child": 4`
in the API payload), so it is named in the record's top-level `source_caveats` and not
recorded as a related dataset.

---

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, from any arm, label or date. Nothing under
`data/d4d_concatenated/` was opened except the two artifacts this run wrote, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened.
The complete read history for factual content is: the declared bundle, the source manifest
(read for the `scope:`, `naming:` and `source_priority:` blocks), and the two schema files.
The remaining files read were method documents — the instruction, the provenance guard, the
four-phase playbook, the uniform decision rules, the Phase 1 method file — and three source
modules read to understand what the Phase 4 checkers verify (`d4d_pair_consistency.py`,
`grounding.py`, `identifiers.py`). No factual value in either record came from any of them.

### Source disagreements resolved by the manifest ranking

The manifest ranks AI-READI sources in four tiers, lowest strongest: tier 1 the data
resources, structured metadata and RO-Crate; tier 2 documentation, license and IRB; tier 3
the publications; tier 4 the NIH RePORTER page. Six disagreements were found. In each case
the preferred value is stated in the record and the disagreement recorded in a
`source_caveats` slot on the object that carries it.

| # | Disagreement | Sources | Resolution |
|---|---|---|---|
| 1 | Expansion of the acronym: "Exploratory" vs "Equitable" Atlas for Diabetes Insights | FAIRhub structured metadata and NIH RePORTER (tiers 1, 4) vs BMJ Open protocol (tier 3) | Tier 1 preferred; the BMJ wording recorded in top-level `source_caveats` |
| 2 | Institution associated with the study lead: Washington University in St. Louis vs University of Washington | FAIRhub structured metadata (tier 1) vs RO-Crate (tier 1); license (tier 2) and NIH RePORTER (tier 4) split the same way | **Same rank — the ranking cannot decide.** Both statements are represented: the FAIRhub affiliation is carried in `creators[Aaron Lee].affiliations` with the RO-Crate's wording in that object's `source_caveats`, and the conflict is restated in top-level `source_caveats` |
| 3 | Target enrollment: 4000 vs 4600 participants | FAIRhub study metadata `enrollmentCount: 4000` (tier 1), Nature and BMJ 4000 (tier 3) vs IRB protocol 4600 / "4,600" (tier 2) | Tier 1 preferred; 4000 is not asserted as a slot value anywhere (the record states observed counts, not targets) but the recruitment target of ~1000 per group is recorded in `subpopulations` |
| 4 | Enrollment start: 18 July vs 19 July 2023 | BMJ Open (tier 3) vs FAIRhub study metadata (tier 1) | Tier 1's 2023-07-19 used for the release collection window; the pilot timeframe records the publication's 2023-07-18 with the conflict in its `source_caveats` |
| 5 | Study end: 30 November 2026 vs 1 January 2027 | BMJ Open (tier 3) vs FAIRhub study metadata (tier 1) | Tier 1 preferred in `collection_timeframes[Overall study period]`; the publication's date noted in that object's `source_caveats` |
| 6 | De-identification method: HIPAA Safe Harbor vs no identifiers collected | Nature Metabolism (tier 3) vs FAIRhub `datasetDeIdentLevel` (tier 1) | Tier 1 preferred in `is_deidentified.method` and `participant_privacy.anonymization_method`; the publication's account noted in both objects' `source_caveats` |
| 7 | Governance body: "Data Access Committee" vs "AI-READI Consortium" | BMJ Open (tier 3) vs RO-Crate (tier 1) | Tier 1 preferred in `data_governance.committee_name`; the publication's term noted in that object's `source_caveats` |

### Same-rank disagreements, represented rather than selected

Two conflicts are between sources the manifest gives the same tier, so the ranking cannot
decide and both statements are represented rather than one being chosen.

- **Study-lead institution** (row 2 above). FAIRhub structured metadata and the RO-Crate are
  both tier 1.
- **Presence of sensitive elements.** The FAIRhub healthsheet states that the public dataset
  contains no data considered sensitive; the RO-Crate enumerates six categories of personal
  sensitive information present (EHR, wearable monitoring, ECG, environmental sensor,
  continuous glucose monitor, wearable accelerometer). Both tier 1. The
  `sensitive_elements[0].sensitive_elements_present` boolean is therefore **left unset** and
  both accounts are stated in `sensitivity_details`, with the conflict named in
  `source_caveats`. Setting the boolean either way would silently select one tier-1 source
  over another.

### Within-source inconsistencies recorded, not reconciled

- The FAIRhub structure metadata's per-directory figures sum to 3,815,969,360,064 bytes across
  356,334 files, while the same payload declares totals of 3,815,969,779,678 bytes and 356,343
  files. The declared totals are recorded in `total_size_bytes` and `total_file_count`; the
  per-directory figures in `file_collections`; the arithmetic difference is stated in
  top-level `source_caveats`, and no cause is inferred. These are the only two numbers in the
  record that do not appear verbatim in the bundle, and both are labeled in the record as
  sums computed over bundle-stated figures.
- The healthsheet answers "No" to whether the dataset identifies demographic sub-populations,
  while the same document's README publishes a split table with counts by race, ethnicity and
  sex, and the dataset description states that sex and race or ethnicity were removed from the
  released data. All three statements are recorded in `subpopulations[0].source_caveats`.
- The healthsheet's sampling answer says "all participants who have been enrolled during the
  first year of data collection", while the same document states elsewhere that this release
  covers 19 July 2023 to 1 May 2025, through the end of the second study year. Recorded in
  `sampling_strategies[0].source_caveats`.
- The BMJ Open abstract labels `STUDY00016228` a "Clinicaltrials.org approval number", whereas
  every other source treats it as the IRB approval number and FAIRhub gives `NCT06002048` as
  the ClinicalTrials.gov identifier. Recorded in `ethical_reviews[0].source_caveats`.
- The follow-up proportion is 10% of the cohort in the FAIRhub study description and the IRB
  protocol, but "approximately 4% of participants are expected to undergo a follow-up
  examination in Year 4" in BMJ Open. Both are recorded in
  `known_limitations[Cross-sectional design].source_caveats` because they describe different
  quantities — those invited versus those expected to attend.

### Internal consistency of repeated values

Every repeated identifier, count, version, date and license reference was checked
programmatically across both records.

- **Splits sum to the whole**: 1576 + 352 + 352 = 2280, matching `instances[0].counts`. Every
  internal breakdown also sums correctly — training 204+369+343+660 = 599+977 =
  600+384+487+105 = 1576; validation and test each 4×88 = 176+176 = 352, with diabetes-status
  rows 88+88+109+67 and 88+88+90+86.
- **Release totals**: 380+545+519+836 = 951+1329 = 776+560+686+258 = 2280.
- **Identity**: `id` = `doi:10.60775/fairhub.3`, `doi` = `10.60775/fairhub.3` (bare, matching
  the slot's anchored pattern), `version_access.latest_version_doi` = `doi:10.60775/fairhub.3`
  — one thing written one way.
- **Dates**: `issued` 2025-11-17 agrees with the version-3 `distribution_dates` entry; the v1
  and v2 entries agree with the FAIRhub version list and with `version_access`.
- **Versions**: `version: 3.0.0` agrees with every version statement in `version_access`,
  `related_datasets` and the file collection descriptions.
- **License**: the same license (AI-READI custom license v2.0, `doi:10.5281/zenodo.17555036`)
  is named consistently in `license`, `license_and_use_terms`, `ip_restrictions`,
  `regulatory_restrictions`, `prohibited_uses` and `related_datasets`.

### Shape audit and the corrections it produced

The shape audit checked for prose in list-ranged slots, enum values the schema does not
define, commentary embedded in name or identifier values, structured slots left empty while
their content sits in prose, narrative in `notes`, and evidence commentary outside
`source_caveats`. `notes` is unused in both records; no name value carries commentary. Four
corrections were made to the full record and then reprojected into core:

1. `regulatory_restrictions.description` carried an explanation of *why* the RO-Crate's
   confidentiality level was stated in prose rather than in `confidentiality_level`. That is
   evidence commentary; it was moved to a new `regulatory_restrictions.source_caveats` and the
   description now states the value only.
2. `collection_mechanisms[Retinal imaging devices]`: "macula- and disc-centred undilated
   colour fundus photography" → "centered", "color". This is composed prose paraphrasing BMJ
   Table 4, not a quotation, so house style applies.
3. The same object: "macula-centred" → "macula-centered".
4. `collection_mechanisms[Visual function testing]` and
   `variables[visual_acuity_logmar].measurement_technique`: "4 metres" → "4 meters".

Three British spellings were deliberately **not** changed, under the carve-outs: the enum
token `ConsentSpecifiedNotElsewhereCategorised` quoted from the FAIRhub metadata, and the
proper nouns and quoted titles that keep their sources' spelling.

Two shape decisions are worth recording because they cost content:

- **`Creator.principal_investigator` is a non-inlined reference.** Its declared range is
  `Person`, but the slot is not inlined, so the schema requires the person's *identifier*, not
  the object. The first draft wrote inlined `Person` objects there and failed validation with
  16 errors. Each was replaced by the ORCID CURIE, and the person's name, degree, title and
  email — which then had no structured home — were moved into the `Creator.description`. This
  is the v4 rule applied literally: an object in a scalar-ranged slot loses the reference it
  was meant to record.
- **`EthicalReview.contact_person` was left unpopulated.** The RO-Crate supplies an IRB
  contact point — the "IRB Reliance Team" at `hsdrely@uw.edu` — but `Person` requires an `id`,
  the team is external to this record so no identifier may be minted for it, and the bundle
  supplies none. Representing a team as a `Person` would also be a shape error. The contact
  route is stated in `review_details` instead.

### Slots deliberately left empty

`prefer omission over inference` was applied throughout. The notable omissions, and why:
`imputation_protocols`, `annotation_analyses` and `machine_annotation_tools` (no labels are
provided, so none of these exist); `at_risk_populations` (the exclusion criteria imply an
answer but no source states one, and the IRB form's protected-population checkboxes are not
readable from the extracted text); `errata` (the healthsheet's erratum answer is an empty
string); `other_tasks` and `use_repository` (the only available content is that none exists);
`discouraged_uses` (everything the sources discourage they in fact prohibit, and is recorded
in `prohibited_uses`); `download_url` (the bundle gives an access route, which belongs in
`distribution_formats.access_urls`, not a download URL); `status`, `created_on`,
`last_updated_on`, `modified_by`, `compression`, `was_derived_from`, `parent_datasets` and
`resources` (nothing in the bundle answers them). `Instance.data_substrate` was omitted
because the bundle supplies no Bridge2AI registry term; the prose characterization sits in
`instance_type`, which is ranged `string` for that purpose.

### Identifier form

Every `uriorcurie`-ranged slot carries a CURIE where the schema declares a prefix:
`doi:10.60775/fairhub.3`, `ORCID:0000-0002-7452-1648`, `ROR:01yc7t268` and so on — 16 ORCIDs,
9 RORs and 5 DOIs, none written as a resolver URL. The `doi` slot, ranged `string` with an
anchored pattern, carries the bare DOI. `download_url` and `access_urls`, ranged `uri`, carry
URLs. `publisher` carries `https://fairhub.io/`: no declared prefix covers FAIRhub, so the
`uri` half of `uriorcurie` is the correct fallback. `Instance.data_topic` carries the MeSH IRI
`https://meshb.nlm.nih.gov/record/ui?ui=D003924` for the same reason — the schema declares no
MeSH prefix, and the slot's own description records that MeSH IRIs are the expected form.
No prefix was invented.

Nine ARK identifiers (`ark:59853/rocrate-b2ai-…`) are used as `FileCollection.id` and
`CoreDistribution.id`. They name subcrates of this release that the bundle attests, so they
are taken from the evidence rather than minted.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

The shared-slot set was derived at runtime with LinkML `SchemaView` by
`data_sheets_schema.d4d_pair_consistency`, not from any hand-written list:

- **79 schema-identical slots.** Every one is present in both records or absent from both, and
  every populated one has deeply identical parsed YAML content, including nested mapping values
  and list item order. 63 of the 79 are populated.
- **1 projected slot** (`resources`, `Dataset` in full and `CoreDataset` in core). Unpopulated
  in both records, so the projection is vacuously equal.
- **2 per-record slots**, exempt and required to differ: `conforms_to_class`
  (`Dataset` / `CoreDataset`) and `conforms_to_schema` (identical value here, but exempt by
  annotation).

Core was produced by projecting the Phase 3-audited full record: the 63 populated identity
slots were copied verbatim rather than paraphrased, condensed or reordered, then
`--sync-core` was run once and the independent check re-run without it.

### Full-only content with no core home

15 populated full slots have no counterpart in `CoreDataset` and are therefore absent from
core by schema, not by omission: `total_file_count`, `total_size_bytes`, `citation`,
`file_collections`, `subsets`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing` and `variables`.

### Semantic review of `file_collections` → `distributions`

The pair validator reports this mapping as requiring semantic review; the warning marks
related content, it does not certify that the review happened. The review was performed and
is recorded here.

Nine full `file_collections` map one-to-one onto nine core `distributions`, matched by the ARK
identifier. The mapping is evidence-supported rather than inferred: each RO-Crate subcrate
declares the directory it packages via its `ro-crate-metadata` path (`cardiac_ecg/…`,
`clinical_data/…`, `retinal_flio/…`, and so on), so the correspondence between subcrate and
directory is stated in the bundle. Field-by-field, all nine pairs agree on `id`, `path`,
byte count (`total_bytes` → `bytes`), `conforms_to` and `conforms_to_standard`, and each core
description begins with the full description verbatim.

Three asymmetries, all schema-driven:

- **`file_count` has no core home.** `CoreDistribution` declares `bytes` but no file count.
  Rather than drop the nine counts, each is appended to the core distribution's `description`
  ("This directory holds 4,515 files."). The core record therefore states the same counts the
  full record does, in the only slot available.
- **`media_type` is `string` in `DistributionFormat` but `MediaTypeEnum` in
  `CoreDistribution`.** `application/dicom` is not a value that enum defines, so the six DICOM
  and WFDB/Open-mHealth directories carry no `media_type` in core; only `clinical_data` and
  `environment`, which the bundle states are CSV, carry `text/csv` and `format: CSV`. The full
  record's `distribution_formats` block, which is schema-identical and copied verbatim into
  core, still records `application/dicom` as a distributed media type, so the information is
  not lost from the pair.
- **`compression`, `hash`, `md5` and `sha256` are unpopulated in every distribution** because
  the bundle states no checksum and no compression for any directory.

Scope and totals were compared where the represented scopes are the same. `total_size_bytes`
(3,815,969,779,678) and `total_file_count` (356,343) are the release-level declared totals;
the distribution-level figures sum to 3,815,969,360,064 and 356,334. The gap is the
within-source arithmetic difference documented above, not a full/core divergence: both records
carry the same per-directory figures, and only the full record carries the declared totals.
`is_tabular` is `false` in both. `conforms_to` (Clinical Dataset Structure v0.1.1) and
`conforms_to_standard` (7 terms) are identical in both. `dialect`, a core-only slot, is
unpopulated because the bundle states no delimiter, header or quoting convention for the CSV
files.

### Checker results

| Check | Result |
|---|---|
| `linkml-validate` full against `Dataset` | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core against `CoreDataset` | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` (final run, no `--sync-core`) | PASS — 79 identical slots, 1 projected, 2 per-record; 1 warning (semantic review, performed above) |
| `grounding.check_run` | 19 grounded, 3 minted_fragment, **0 absent** |
| `report_claims.check_report` | checked, 0 findings, 0 claims unnamed |
| `form` (house style, GC label, prefixes) | 0 British spellings, 0 label variants, 0 undeclared prefixes, 0 organisational fragments |
| `d4d runs validate` | valid |
| `d4d runs check --strict` | exit 0 — 39 runs subject to the live-provenance requirement, 0 failing; this run appears in no warning list |
| `d4d download scope --check --project AI_READI` | in scope |

The `pair_consistency`, `report_claims`, `grounding` and `form` blocks were written into the
provenance record by `d4d provenance backfill-checks --execute`, scoped to this run, and
therefore carry `recorded_by: backfill_checks`. `d4d provenance record` does not write them on
this path — only `d4d api run` does — so without this step the record would have read
`unrecorded` for all four despite the checks having been run. The recomputation was performed
against the same bytes this run produced: the md5s the blocks name are the md5s in the
`validation` block, and the results are identical to the independent runs reported above.

The three `minted_fragment` identifiers are the recommended-split subsets —
`doi:10.60775/fairhub.3#split-train`, `#split-validation` and `#split-test`. Each names a part
of this dataset that exists nowhere outside this record, so no evidence can supply an
identifier for it, and each is a fragment on the dataset's own attested DOI rather than a new
namespace. Zero identifiers are `absent`: no ROR, ORCID, DOI or ARK in either record comes
from anywhere but the declared bundle.

### Repair

**No repair phase ran.** None of the Phase 4 checkers — grounding, report claims, or the final
pair-consistency run — reported a finding requiring either record to change. The four
corrections listed above were made during the Phase 3 shape audit, before Phase 4 began, and
core was regenerated from the corrected full afterwards; they are recorded as part of
`source_audit` rather than as a `repair` phase, and no empty `repair` phase is recorded.

### Divergences

Between the full and core records: **none.** Every schema-identical shared slot has identical
presence and deeply identical parsed content; the one projected slot is unpopulated in both;
the two per-record slots differ exactly as their annotation requires; and the one related
mapping, `file_collections` → `distributions`, was reviewed field by field above with zero
contradictions.

---

## Commands run

```bash
# Scope and ranking
poetry run d4d download scope --project AI_READI
poetry run d4d download priority --project AI_READI

# Phase 1 and Phase 2 validation (run after every correction)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 synchronization, then the independent check
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml

# Identifier grounding against the bundle, and report claims against the record
poetry run python -c "... data_sheets_schema.grounding.check_run ..."
poetry run python -c "... data_sheets_schema.report_claims.check_report ..."

# Provenance and gates
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt_v5.md \
  --prompt-text /tmp/agentic_fanout/AI_READI_rep2.md --condition generic_v5 \
  --runtime 'Claude Code' --provider Anthropic --reasoning-effort high \
  --phase '{"name":"generate_full","completed":true,"artifacts":["AI_READI_d4d.yaml"]}' \
  --phase '{"name":"generate_core","completed":true,"artifacts":["AI_READI_d4d_core.yaml"]}' \
  --phase '{"name":"source_audit","completed":true}' \
  --phase '{"name":"reconcile","completed":true,"iterations":2}' \
  --phase '{"name":"report","completed":true,"artifacts":["AI_READI_reconciliation.md"]}'
poetry run d4d runs check --strict
poetry run d4d download scope --check --project AI_READI
```

## Final results

| Measure | Full | Core |
|---|---|---|
| Top-level slots populated | 80 | 66 |
| Slots including nested objects | 755 | 604 |
| Lines (informational, not a quality gate) | 2144 | 1336 |
| Schema validation | pass | pass |
| Term validation | pass | pass |

Slot counts are observations, not targets. This condition sets no expected density and no
expected relationship to any other arm, project or replicate; the counts are what the declared
bundle supported.
