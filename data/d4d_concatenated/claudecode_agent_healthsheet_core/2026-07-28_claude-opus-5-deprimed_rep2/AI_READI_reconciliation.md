# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep2

**Arm:** HEALTHSHEET-ONLY (single structured upstream source)
**Mode:** four-phase project agent, de-primed
**Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`
**Temperature:** 0.0

## Declared inputs

| Role | Path |
|---|---|
| Source bundle (only factual input) | `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`) |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`) |
| Phase 2 additional input | the same-run Phase 1 full record (path below) |

Source manifest was **not** used; this arm declares its single source bundle explicitly. The
`d4d provenance record` output hashes `data/preprocessed/source_manifest.yaml` as a repository-state
field; it was not read as an input to generation.

## Outputs

| Artifact | Path | Lines | Top-level slots |
|---|---|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d.yaml` | 1049 | 72 |
| Core | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d_core.yaml` | 683 | 61 |
| Provenance | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_provenance.yaml` | — | `record_mode: live` |

Line counts are informational metadata, not a quality gate.

---

## Phase 3 — source and provenance audit

### Provenance boundary

- No prior full or core D4D record, from any arm, label, or date, was read, opened, grepped, or
  consulted. Nothing under `data/d4d_concatenated/` was read except the same-run full record as the
  declared Phase 2 input and the same-run outputs of this run.
- No other AI-READI input document was consulted. The declared bundle and the two schema files are
  the only inputs.
- Record structure was derived at runtime from the schemas via LinkML `SchemaView`
  (`class_induced_slots` on `Dataset` and `CoreDataset`, plus induced slots of every nested class and
  the permissible values of every enum used). No prior YAML, checklist, or `d4d:docExample` supplied
  or altered structure.

### Internal consistency checks against the bundle

| Check | Result |
|---|---|
| Participant counts (v1 204, v2 +863 = 1067, v3 2280) | Consistent; arithmetic checks out; 2280 used in `instances.counts`, `version_access`, and `splits` |
| Collection window 2023-07-19 → 2025-05-01 | Consistent across `collection_timeframes`, `known_limitations`, `version_access` |
| Release dates (May 2024 / Nov 2024 / Nov 2025) | Consistent; "released fall 2025" in COMPOSITION agrees with "November 2025" in DISTRIBUTION |
| DOI `10.60775/fairhub.3` | Consistent in `id`, `doi`, `version_access.latest_version_doi`, `distribution_formats.access_urls` |
| License `https://doi.org/10.5281/zenodo.17555036` | Consistent in `license`, `license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions`, `discouraged_uses`, `prohibited_uses` |
| IRB facts (UW, 2022-12-20, STUDY00016228 letter, 90-day renewal, site reliance) | Consistent between `ethical_reviews` and `human_subject_research` |
| Consent facts (e-consent via REDCap, UW form URL, withdrawal leaves shared data in place) | Consistent between `collection_consents`, `consent_revocations`, `informed_consent` |

### Source-internal discrepancies found, and how they were resolved

1. **Award number spelled two ways.** MOTIVATION renders it `OT2ODO32644`; COLLECTION renders it
   `OT2OD032644`. Resolved by authority and format plausibility toward `OT2OD032644` (used as
   `funders[0].grants[0].grant_number`), with **both** renderings recorded verbatim in the grant
   `description` so the discrepancy is not silently erased.

2. **Stale enrollment scope in COMPOSITION.** The answer to "does the dataset contain all possible
   instances" states the dataset contains data "from all participants who have been enrolled during
   the first year of data collection" — which conflicts with VERSIONING and COLLECTION, both of which
   scope this version to data collected through the end of the **second** year (2023-07-19 →
   2025-05-01). Resolved by scope and specificity toward the VERSIONING/COLLECTION statements, which
   agree with each other and with the 2280-participant count. `sampling_strategies` records
   "all participants who had been enrolled during the covered data collection period" rather than
   repeating the stale "first year" claim. The supported part of the answer (`is_sample: false`,
   contains all possible instances) is retained.

3. **Demographic sub-populations answered "No" while race/ethnicity/sex are described elsewhere.**
   DEMOGRAPHIC INFORMATION answers "No" to sub-population identification, while COMPOSITION places
   race, ethnicity, and sex in the controlled-access tier and LABELING describes splits balanced on
   those variables. Resolved by keeping the source's literal answer
   (`subpopulations.subpopulation_elements_present: false`) and recording both qualifying facts
   verbatim in `identification` and `distribution`, so neither statement is dropped.

4. **Sensitive data answered "No" for the public tier only.** COMPOSITION answers "No, the public
   dataset will not contain data that is considered sensitive. However, the controlled access dataset
   will contain data regarding racial and ethnic origins, location (5-digit zip code), as well as
   motor vehicle accident reports." The record describes the dataset as a whole (its `id` is the
   FAIRhub DOI covering both tiers), so `sensitive_elements_present: true`, with both tier statements
   preserved verbatim in `sensitivity_details` and the genetic-sequencing / past-health-records items
   from the GENERAL INFORMATION summary added as a third detail.

5. **"Pilot study is not balanced" is historical scope.** The CHALLENGE answer describes the pilot
   phase, not version 3. The word "pilot" is retained verbatim in
   `known_biases[sampling_bias].bias_description` so the historical scope stays explicit rather than
   reading as a claim about the current release.

### Interpretive schema mappings (recorded so they are auditable, not hidden)

| Slot | Value | Basis in the bundle |
|---|---|---|
| `is_tabular` | `false` | Dataset "encompass[es] tabular data, imaging data, and physiological signal/waveform data"; the slot is false for non-tabular formats such as images |
| `language` | `English` | "English language was used for communication with study participants"; inclusion criterion "must speak and read English". Inferred for the dataset from the study-communication statement |
| `publisher` | `http://fairhub.io/` | "The dataset will be available through the FAIRhub platform (http://fairhub.io/)"; slot means the entity responsible for making the resource available. URL form matched to the source (`http`, not `https`) so it agrees with `distribution_formats.access_urls` |
| `regulatory_restrictions.confidentiality_level` | `restricted` | Two-tier access: public download under license agreement, full dataset under a data use agreement. Enum projection of that access model |
| `maintainers[0].role` | `academic_institution` | "The AI-READI team will be supporting and maintaining the dataset"; consortium members are at UAB, UCSD, and UW. Enum projection |
| `known_biases[*].bias_type`, `known_limitations[*].limitation_type` | see file | Enum projections of narrative CHALLENGE / COMPOSITION / VERSIONING content |
| `at_risk_populations.special_protections` | eligibility criteria | Capacity-to-consent requirement and pregnancy / gestational-diabetes exclusion mapped as protective eligibility rules. `at_risk_groups_included` deliberately left **unset**: the bundle does not answer it, and MoCA screening implies cognitively impaired participants are not categorically excluded |

### Slots deliberately left absent

`file_collections`, `total_file_count`, `total_size_bytes`, `distributions` (core),
`dialect`, `subsets`, `variables`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`, `raw_data_sources`, `errata`, `parent_datasets`, `resources`,
`issued`, `created_on`, `status`, `download_url`, `was_derived_from`,
`license_and_use_terms.data_use_permission`, `regulatory_restrictions.hipaa_compliant`,
`creators[*].principal_investigator`.

The healthsheet is a narrative questionnaire: it carries no file inventory, byte counts, checksums,
formats, variable-level metadata, imputation or annotation-agreement content, and it names no
individual. Three of its 84 questions are explicitly unanswered (de-identification preprocessing,
re-identification measures, erratum); the two de-identification gaps are recorded as an explicit
statement inside `is_deidentified.deidentification_details` rather than being inferred, and `errata`
is omitted because an unanswered question is not a fact about the dataset.
`data_use_permission` was left unset rather than forced onto a `DataUsePermissionEnum` value: the
license permits commercial and research reuse under strong conditions, which no single permissible
value represents.

### Corrections made during Phase 3

- `publisher` changed from `https://fairhub.io/` to `http://fairhub.io/` to match the bundle's URL
  form and eliminate an intra-record http/https mismatch with `distribution_formats.access_urls`.
  Core was regenerated from the corrected full record afterward.
- No Phase 2 discovery required back-porting into the full record: every core-eligible fact the
  bundle supports was already present in the Phase 1 full record, and Phase 2 found nothing the full
  extraction had missed.

### Validation after corrections

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>          → No issues found
poetry run linkml-term-validator validate-data <full> --schema .../data_sheets_schema_all.yaml --target-class Dataset      → Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core> → No issues found
poetry run linkml-term-validator validate-data <core> --schema .../data_sheets_schema_core_all.yaml --target-class CoreDataset → Validation passed
```

---

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` over `Dataset` and `CoreDataset`; no
hand-written field list was used.

**Result: 76 schema-identical slots checked, all deeply identical or identically absent. Nothing
diverged. `--sync-core` was not needed and was not run.**

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
PASS: 76 schema-identical slots; projected slots=['resources']
```

### How identity was guaranteed

The core record was produced by projecting the Phase 3-audited full record onto the `CoreDataset`
induced-slot inventory: for every slot present in both classes, the parsed value was carried across
unchanged, including every nested mapping value and list item in original order. No narrative field
was condensed, paraphrased, reordered, or truncated to make core shorter. The 366-line difference
between the files is entirely attributable to full-only slots, not to shortened shared content.

### Full-only slots (11) omitted from core because `CoreDataset` does not define them

`citation`, `relationships`, `splits`, `direct_collection`, `collection_notifications`,
`collection_consents`, `consent_revocations`, `participant_privacy`, `participant_compensation`,
`third_party_sharing`, `related_datasets`.

### Projected and related content

- **`resources`** — the one range-differing shared slot (`Dataset` in full, `CoreDataset` in core).
  Absent from both records; the bundle describes no component sub-datasets. Coverage is trivially
  equal and there is nothing to match by `id`.
- **`file_collections` → `distributions`** — the related, non-identical representation the playbook
  calls out. Both are absent: the healthsheet lists no files, paths, formats, compression,
  checksums, byte counts, or per-distribution access URLs. There is no mapping to review and no
  possible conflict.
- **`total_file_count` / `total_size_bytes` vs distribution-level values** — all absent; no scope
  comparison applies.
- **`dialect`, formats, `is_tabular`** — `dialect` and formats are absent from both records;
  `is_tabular: false` is present and identical in both, and does not conflict with the absence of
  format detail.
- **Top-level identity/version/access facts vs version history and repeated statements** —
  `id`, `doi`, `version: "3"`, and `license` agree with `version_access` (which carries the v1/v2/v3
  history and `latest_version_doi`), with `distribution_dates`, with `distribution_formats`, and with
  the repeated license references in `license_and_use_terms`, `ip_restrictions`,
  `regulatory_restrictions`, `discouraged_uses`, and `prohibited_uses`. Historical releases (v1, v2)
  are labelled as such throughout and are not treated as contradicting the current release. The
  full-only `related_datasets` entries (`is_new_version_of` v1 and v2) restate the same history and
  do not conflict with `version_access` in either record.

### Unresolved contradictions

None, within either record or between the two.

## Completion audit

- [x] Every factual input path is on the phase allowlist.
- [x] No prior generated YAML was read or cited.
- [x] Every emitted slot and nested object is permitted by the applicable schema, including inherited
      and `slot_usage` constraints.
- [x] The core input full record carries this run's exact label.
- [x] No Phase 2 discovery needed back-porting; none was invented.
- [x] Schema and ontology term validation pass for both files.
- [x] Schema-derived pair validator passes without `--sync-core`.
- [x] All projected and related content received semantic review (above).
- [x] Phase 3 provenance result and Phase 4 consistency result recorded here.
- [x] Live provenance record present with `record_mode: live`.
