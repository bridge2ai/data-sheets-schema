# CHoRUS full/core reconciliation

- **Run label:** `2026-08-24_claude-opus-5-claudecode-generic-v5_rep1`
- **Mode:** four-phase project agent, generic-v5 prompt
- **Arm:** BASELINE (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The record is about **the CHoRUS dataset** — the
multicenter critical care dataset assembled by the Patient-Focused Collaborative
Hospital Repository Uniting Standards for Equitable AI project — and not about
the project, the consortium, the GitHub organization or the AIM-AHEAD training
program that uses the data. This matches the manifest's `scope:` declaration for
CHORUS (`referent: CHoRUS dataset`, `referent_id: https://chorus4ai.org/`,
`related_but_distinct: []`). The same referent is held in both records.

The dataset identifier is `https://chorus4ai.org/`. No DOI, accession or version
identifier for the dataset appears in any source in the declared bundle, which is
what the manifest's `referent_note` records; the project site is the identifier
the sources themselves use. The `title` is the project's official title as the
GitHub organization README states it, because the bundle states no separate title
for the dataset.

## Phase 3 — source and provenance audit

### Provenance

The evidence boundary held. The factual inputs read during this run were the
declared bundle, `data/preprocessed/source_manifest.yaml` (through
`d4d download scope` and `d4d download priority`), and the two LinkML schemas.
No prior full or core D4D record was read, from this or any other label, and no
evaluation or reconciliation report was consulted. Both output directories were
created empty at the start of the run, so no phase was resumed and no artifact
was inherited: every phase in this run was performed, and none was skipped.

Structure was derived from the schemas at run time with `SchemaView` — the
induced attributes of `Dataset` and `CoreDataset`, the induced shape of every
nested class used, and the permissible values of every enum used. No prior record
was consulted as a template.

### Source ranking and the one disagreement

`d4d download priority --project CHORUS` gives the bundle's ranking, lowest tier
strongest: tier 2 `project_documentation` (chorus4ai.org), tier 4
`nih_reporter_project` and `cohort_2_webinar`, tier 5
`github_organization_overview`.

One substantive disagreement was found. The size of the released dataset is given
as **50,000 patient admissions** by the project site (tier 2) and as **over 45K
unique admissions, as of August 2025** by the cohort 2 webinar (tier 4). The
ranking decides: the tier 2 value is stated in `instances[0].counts`, and the
disagreement, both values and the preference are recorded in that object's
`source_caveats`. The two may also be measuring different moments — the webinar
figure is explicitly dated and the project site capture is undated — and the
caveat says so rather than presenting the ranking as the whole explanation.

Two further figures look like a conflict and are not one, and are recorded
separately with a caveat saying why: the project site's **7,642 admissions with
radiology data** counts admissions, and the webinar's **1000 images available,
de-identification in process** counts images.

### Findings and corrections

Every numeric claim, name, date, award identifier, email address and repository
name in the record was checked back against the bundle text. All were found. Ten
corrections were made to the full record during this phase; the core record was
then re-derived from the corrected full record, so all ten are present in both.

1. **Mis-scoped existing use.** `existing_uses[0]` cited the AIM-AHEAD cohort 2
   training program as an existing use. The webinar states dataset use for
   training in the present tense, but the cohort 2 program it describes was still
   recruiting on the webinar date (applications closed 2025-09-26, program start
   2025-11-17). A `source_caveats` now records that the cohort numbering implies
   an earlier cohort the bundle does not describe, so the extent of training use
   already completed cannot be established from it.
2. **Evidence commentary outside `source_caveats`** in four objects, moved there
   from `description` or from a details field: `sampling_strategies[0]`,
   `future_use_impacts[0]`, `raw_sources[0]` and `preprocessing_strategies[2]`
   (transformation to limit re-identification). Each `description` now states
   what the evidence says; each `source_caveats` states what it does not.
3. **Over-attribution.** `data_collectors[1]` credited the project sub-teams with
   hosting the discussion locations where sites raise extract issues; the source
   states only that the workflow diagram links to documentation compiled by them,
   and names the discussion locations separately. Reworded to match.
4. **Misquoted source.** `updates` said site statuses are tracked in the Standards
   Project *and* the Data Acquisition Project; the source says *either … or*.
5. **Off-target slot value.** `human_subject_research.special_populations` listed
   admissions ("Admissions from pediatric intensive care units") where the slot
   asks for the populations requiring protection. Now names children and neonates,
   with the admission types as the evidence for each.
6. **Padding removed.** `maintainers[1]` carried the GitHub organization's
   follower count and country, which bear on nothing the slot asks about.
7. **Caveat scope made explicit.** The webinar's data-type table is a slide table
   flattened by PDF text extraction, and its columns cannot be aligned to rows by
   position. The `distribution_formats` caveat now states that it governs all five
   entries, and states the basis on which each recorded value survives the
   flattening: the published-schema names were matched to modalities **by name**,
   not by row position (OHNLP for notes, DICOM for imaging, an extended PhysioNet
   schema for waveform telemetry, an open source EDF+ and Persyst schema for EEG),
   and controlled access is recorded because every row carries it. The table's
   metadata column (values "Yes" and "Planned") cannot be attributed to individual
   rows and is recorded for no format. For the same reason the OMOP entry states
   that one of those data types carries a schema with extensions without asserting
   which.

### Deliberate omissions

These are recorded because an absent slot is a claim about the evidence, and a
reviewer should be able to see it was a decision:

- **No `license` at dataset level.** The chorus-ai GitHub README (tier 5) states
  "This project is licensed under the MIT License", in a README describing the
  organization's software repositories, several of which carry their own MIT and
  Apache-2.0 licenses in the same listing. No source states a license for the
  *data*, which are instead governed by a signed licensing agreement. The MIT
  statement, its source tier and the reason it is not recorded as the dataset's
  license are in `license_and_use_terms.source_caveats`.
- **No `Person` objects anywhere.** `Person` requires an `id` of range
  `uriorcurie`, and the bundle contains no ORCID or any other personal
  identifier. Supplying one from model memory is exactly the failure the
  identifier rule prohibits. People are instead carried where the schema allows a
  name: the six named leadership members as `creators` entries with
  `affiliations`, the NIH-recorded principal investigator in
  `creators[0].principal_investigator` (declared range `Person`, uninlined against
  an identifier slot, so the value is a scalar and the slot description asks for a
  person's name), and contact points in `data_governance.access_review_process`
  and `maintainers[].maintainer_details`.
- **No `Organization` identifiers.** Affiliations carry `name` only. The bundle
  names Massachusetts General Hospital, the University of Florida, UTHealth
  Houston and Tufts University, and states no ROR for any of them. Naming the
  organization is grounded; adding its registry identifier from memory is not.
- **No HIPAA or GDPR compliance claim.** Both appear in the bundle solely as
  topics of an AI-LEARN training curriculum session. Recorded as such nowhere in
  the record, and the reason is stated in
  `human_subject_research.source_caveats` and
  `regulatory_restrictions.source_caveats`.
- **No IRB approval, ethics board, consent or `ethical_reviews`.** The project
  describes community-facing ethics focus groups and a legal framework, but no
  source names an IRB, an approval number, a reviewing board or any participant
  consent arrangement for this dataset.
- **No byte count for the waveform data.** The project site writes "23 Tb".
  Whether that is terabytes or terabits is not stated, so it is described in
  `instances` and no size field is populated.
- **No `is_tabular`, `version`, `status`, `doi`, `publisher`,
  `distribution_dates`, `citation`, `known_biases`, `anomalies`,
  `content_warnings`, `errata`, `retention_limit`, `version_access`,
  `discouraged_uses`, `prohibited_uses`, `use_repository`, `other_tasks`,
  `informed_consent`, `ethical_reviews`, `related_datasets` or `variables`.**
  Nothing in the bundle supports them. `is_tabular` is omitted rather than set:
  the dataset holds 1.6 billion rows of tabular OMOP data alongside imaging and
  waveforms, and neither value is true of it.
- **No `file_collections` in full and therefore no `distributions` in core.** The
  bundle describes modalities, standards and volumes, but no files, paths, counts,
  checksums or byte sizes. The modality breakdown is carried by
  `distribution_formats` and `instances` instead.
- **No `dialect` in core.** No delimiter, quoting or header convention is stated
  anywhere in the bundle.

### Identifier form

The bundle contains no ROR, ORCID, DOI or ARK, so there was no external
identifier to ground and none to write. The grounding checker accordingly reports
zero in all three categories — zero `grounded`, zero `minted_fragment`, zero
`absent` — and zero is the correct and expected reading here rather than a
failure to measure: it reflects a bundle with no registry identifiers in it, in a
record that invented none.

One identifier was minted: `https://chorus4ai.org/#holdout-test-set` on
`subsets[0]`, whose `id` is required by the schema. The holdout test set has no
referent outside this record, so no evidence can supply its identifier; it is
hung as a local fragment on the dataset's own attested identifier, which is the
one case in which minting is right. No prefix was invented. The undeclared-prefix
count is zero.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time from `Dataset` and `CoreDataset` with
LinkML `SchemaView` through `load_pair_schema()`; no hand-written field list was
used. The derivation gives **79 schema-identical slots**, **1 projected slot**
(`resources`, `Dataset` in full and `CoreDataset` in core), and **2 per-record
slots** (`conforms_to_class`, `conforms_to_schema`), which carry the
`d4d:perRecord` annotation and must differ.

**Result: PASS, with no synchronization performed and no divergence to
reconcile.** Core was projected from the Phase-3-corrected full record rather
than extracted independently, so schema-identical slots are deeply identical by
construction, including every nested mapping value and list item in order, and
including all narrative fields — nothing was condensed, paraphrased, reordered or
omitted in core. `--sync-core` was therefore never needed and was not run; the
validator was run only in its independent checking mode, and passed.

- **Slots carried into core:** 46 of the full record's 49 populated top-level
  slots.
- **Full-only slots, absent from core because `CoreDataset` does not declare
  them:** `subsets`, `direct_collection`, `third_party_sharing`. Their content is
  not lost from the corpus, only from the core projection, which is what the core
  subset is for.
- **Per-record slots, correctly differing:** `conforms_to_class` is `Dataset` in
  full and `CoreDataset` in core; `conforms_to_schema` is
  `https://w3id.org/bridge2ai/data-sheets-schema` in full and
  `https://w3id.org/bridge2ai/data-sheets-schema/core-schema` in core.
- **Projected slot `resources`:** populated in neither record, so coverage is
  equal and there is nothing to match by `id`.

### Related, non-identical representations

- **`file_collections` (full) → `distributions` (core):** both absent, for the
  reason given under deliberate omissions. There is no mapping to review and no
  conflict possible.
- **`total_file_count` / `total_size_bytes` versus distribution-level values:**
  all absent. No count or size is asserted at either level, so no scope mismatch
  can arise.
- **`dialect`, formats and `is_tabular`:** `dialect` and `is_tabular` are absent
  from both records. `distribution_formats` is schema-identical across the pair
  and deeply identical in content, and its five entries agree with
  `conforms_to_standard` (`OMOP_CDM`, `DICOM`, `WFDB`, `OTHER`) and with the prose
  of `conforms_to`, which names OMOP CDM, the OHNLP toolkit schema, DICOM, WFDB
  and EDF+/Persyst. `OTHER` covers the OHNLP and EDF+/Persyst standards, which the
  `DataStandardEnum` vocabulary lacks, and their names are kept in `conforms_to`
  so nothing is lost.
- **Top-level identity, version and access facts versus the rest of the record:**
  checked and consistent. `id` and `page` are both `https://chorus4ai.org/`. The
  access rules stated in `license_and_use_terms.license_terms` (registration form,
  signed licensing agreement, `.edu` email address) agree with
  `data_governance.access_review_process`, with
  `regulatory_restrictions.confidentiality_level: restricted`, with the controlled
  access recorded on all five `distribution_formats` entries and with
  `third_party_sharing.is_shared: true` in the full record. No version or release
  date is asserted anywhere, so there is nothing to contradict.
- **Historical versus current release:** the bundle's distinction between the
  *current released dataset* (50,000 admissions, 1.6 billion OMOP rows, 7,642
  admissions with radiology data, 23 Tb of waveforms) and the *anticipated final
  dataset* (100,000 admissions, 9 modalities, 14 hospitals) is preserved as two
  scopes rather than flattened into a contradiction: current figures are in
  `instances`, the anticipated figures are in `updates` and
  `known_limitations[0]`, and each states which it is.

### Checkers

- Pair consistency: **PASS**, 79 identical slots.
- Grounding: 0 `absent`, 0 findings — no unattested identifier, and no resolver
  URL in any `uriorcurie` slot.
- Form facts: 0 undeclared prefixes, 0 British spellings, 0 organizational
  fragments, 0 non-canonical GC label variants. The canonical label `CHoRUS`
  declared in the manifest's `naming:` block is used throughout the prose in both
  records.
- Report claims: run against this report and both records after writing it.

No finding required a change to either record after the Phase 4 checks, so **no
repair phase was run** and this report was not rewritten after one.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d_core.yaml` (created, re-derived after the Phase 3 corrections, Phase 4 header line added)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_provenance.yaml` (written by `d4d provenance record`)

Nothing outside these four paths was written.

## Commands

```bash
# Scope and source ranking
poetry run d4d download scope --project CHORUS
poetry run d4d download priority --project CHORUS

# Phase 1 validation (full)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 validation (core)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 pair consistency (independent check; --sync-core not required, not run)
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CHORUS_d4d_core.yaml

# Phase 4 grounding, form facts and report claims
poetry run python -c "from data_sheets_schema.grounding import check_run, form_facts; ..."
poetry run python -c "from data_sheets_schema.report_claims import check_report, declared_slots; ..."

# Provenance and gates
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt_v5.md \
  --prompt-text /tmp/agentic_canary/CHORUS_instruction.md \
  --condition generic_v5 --runtime 'Claude Code' --provider Anthropic \
  --reasoning-effort high \
  --phase '{"name":"generate_full","completed":true,"artifacts":["CHORUS_d4d.yaml"]}' \
  --phase '{"name":"generate_core","completed":true,"artifacts":["CHORUS_d4d_core.yaml"]}' \
  --phase '{"name":"source_audit","completed":true}' \
  --phase '{"name":"reconcile","completed":true,"iterations":1}' \
  --phase '{"name":"report","completed":true,"artifacts":["CHORUS_reconciliation.md"]}'
poetry run d4d runs validate --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep1 --project CHORUS
poetry run d4d runs check --strict
poetry run d4d download scope --check --project CHORUS
```

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full term validation | Passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core term validation | Passed |
| Pair consistency, 79 schema-identical slots | PASS |
| Identifiers absent from bundle | 0 |
| Resolver URLs in identifier slots | 0 |
| Undeclared prefixes | 0 |
| British spellings | 0 |
| Non-canonical GC label variants | 0 |

Populated top-level slots: **49 full, 46 core**. Reported as an observation, not
against a target — there is no expected slot count, density or relationship to
any other arm or project, and none was used in deciding what to populate.
