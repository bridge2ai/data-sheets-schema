# AI_READI D4D full/core reconciliation — healthsheet-only arm, rep3

## Run identity

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Version label | 2026-07-27_claude-opus-5_rep3 |
| Arm | HEALTHSHEET-ONLY |

## Inputs

Sole factual source:

- `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt` (539 lines; 14 sections;
  84 questions, 81 answered, 3 marked `(no response provided)`)

Structure references only (no dataset facts drawn from them):

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `src/data_sheets_schema/schema/D4D_Core.yaml`

## Outputs

- Full: `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml`

Neither directory existed before this run; nothing was overwritten.

---

## Phase 3 — source and provenance audit

### Provenance

No prior full or core D4D record was read, globbed, or cited. No file under
`data/d4d_concatenated/` or `data/d4d_individual/` was opened other than this run's own two
outputs. `AI_READI_preprocessed.txt`, `data/preprocessed/individual/AI_READI/`,
`data/raw/AI_READI/`, `data/preprocessed/source_manifest.yaml`, and live web content were not
accessed. Record structure was derived at runtime from the LinkML schemas via `SchemaView`
(induced slots, ranges, cardinality, inlining, enums), not from any example record.
`d4d:docExample` annotations were not copied.

### Facts cross-checked against the healthsheet

Participant counts (204 / 1067 / 2280) are stated twice in the source (versioning §c and
composition) and agree. The version-3 collection window (2023-07-19 to 2025-05-01) is stated
twice (versioning and collection) and agrees. The DOI `10.60775/fairhub.3`, the license DOI
`10.5281/zenodo.17555036` (four occurrences), the split proportions 70/15/15, the $200 visit
compensation, and the UW IRB initial approval date 2022-12-20 each appear consistently.

### Internal source disagreements found and how they were handled

1. **Grant number rendered two ways.** The motivation section writes `OT2ODO32644`; the
   collection section writes `OT2OD032644`. `grant_number` was set to `OT2OD032644` and the
   variant spelling is recorded verbatim in the `FundingMechanism.description` rather than
   silently normalised away.

2. **Stale scope statement in the composition section.** The composition answer says the dataset
   contains "data from all participants who have been enrolled during the *first year* of data
   collection", while the versioning and collection sections scope version 3 to 2023-07-19 through
   2025-05-01 with 2280 participants. **Correction applied to the full record in Phase 3**:
   `sampling_strategies[0].source_data` now reports the composition wording *and* flags it as stale
   relative to this version, instead of the generalisation written in Phase 1. The correction was
   then propagated to core.

3. **Demographic sub-populations answered "No" while sensitive elements list race/ethnicity.**
   The demographic section answers "No" to whether the dataset identifies demographic
   sub-populations, but the composition section says the controlled-access tier contains racial and
   ethnic origins. `subpopulations[0].subpopulation_elements_present` follows the explicit "No"; the
   controlled-access sensitive elements are recorded separately under `sensitive_elements`, and the
   reason the public tier omits sex/race/ethnicity is captured in
   `subpopulations[0].distribution`. No value was invented to resolve this.

4. **Sample vs. representativeness.** The composition section says the dataset "contains all
   possible instances" (so `is_sample: false`), while the challenge section says the cohort "may not
   provide a comprehensive representation of the population". Both were kept:
   `is_representative: false` with `why_not_representative` quoting the challenge section.

### Phase 2 discoveries back-ported to full

None. Phase 2 found no core field that the source supported and the full record had missed. The
only Phase 3 factual change was correction 2 above, which originated in the audit, was applied to
the full record first, and then flowed to core.

### Unanswered upstream questions — left empty, not filled

The three questions the input marks `(no response provided)` were not answered from any other
source:

| Healthsheet question | Effect on the records |
|---|---|
| Composition — measures taken to avoid re-identification after de-identification | No `Deidentification.method`; the omission is stated explicitly in `is_deidentified.description` and `participant_privacy[0].description` |
| Preprocessing — pre-processing performed for de-identification | No de-identification step in `preprocessing_strategies`; the omission is stated in `preprocessing_strategies[0].description` |
| Maintenance — is there an erratum | `errata` omitted entirely from both records |

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot analysis

Computed at runtime with `SchemaView` over `Dataset` and `CoreDataset`:

- shared slot names: **77**
- schema-identical (same induced range and cardinality): **76**
- projected (range differs): **1** — `resources` (`Dataset` in full, `CoreDataset` in core)
- of the 76 schema-identical slots, **57** are populated, and all 57 are populated in both files
  with deeply identical parsed YAML content; the remaining 19 are absent from both

Mismatches found: **none**. An independent parsed-YAML comparison outside the validator confirmed
zero differing values and zero presence differences across all 76 schema-identical slots.

### Projected slot

`resources` is unpopulated in both records — the healthsheet describes no sub-resources — so the
projection is vacuously consistent (equal coverage, empty on both sides).

### Related, non-identical representations reviewed semantically

- **`file_collections` (full) → `distributions` (core).** Both absent. The healthsheet contains no
  file-level information whatsoever, so there is nothing to map and no contradiction. Consistently,
  `total_file_count`, `total_size_bytes`, and `compression` are absent from full, and `dialect`,
  `compression`, and `download_url` are absent from core.
- **`is_tabular`.** `false` in both, consistent with the healthsheet statement that the data
  "encompass tabular data, imaging data, and physiological signal/waveform data".
- **Identity, version, and access facts.** `id`, `doi`, `version` (`3`), `license`, `publisher`,
  and `title` are identical across the pair and agree with `version_access.latest_version_doi`,
  `version_access.versions_available`, `distribution_formats[0].access_urls`,
  `distribution_dates[0].release_dates`, and `license_and_use_terms`. Version 3 (November 2025,
  2280 participants) is treated as current; versions 1 (May 2024, 204) and 2 (November 2024, 1067)
  are recorded as explicit history in `version_access` and, in the full record only, in
  `related_datasets` — a historical release, not a contradiction.

### Full-only content dropped by the core schema

These 12 populated slots exist in `Dataset` but not in `CoreDataset`, so their loss in core is a
schema projection, not a divergence: `citation`, `collection_consents`, `collection_notifications`,
`consent_revocations`, `direct_collection`, `participant_compensation`, `participant_privacy`,
`related_datasets`, `relationships`, `splits`, `subsets`, `third_party_sharing`.

Consent substance survives in core through `informed_consent` and `ethical_reviews`; the
re-identification-risk note survives through `is_deidentified` and `future_use_impacts`. No shared
value was condensed, paraphrased, reordered, or omitted to make core shorter.

---

## Primary result — D4D areas the healthsheet could not support at all

These slots are **empty in both records because the healthsheet contains no evidence for them**,
not because they were overlooked. This is the finding this arm exists to produce.

**Completely unsupported (no partial evidence):**

| D4D area | Slots left empty |
|---|---|
| File and distribution mechanics | `file_collections`, `total_file_count`, `total_size_bytes`, `compression`, `download_url`, core `distributions`, core `dialect` — no file formats, paths, counts, byte sizes, checksums, or direct download endpoints anywhere in the source |
| Variable-level metadata | `variables` — no variable names, types, units, ranges, or missingness codes; the only variable-level fact in the source is that Snellen visual acuity was dropped in favour of logMAR |
| Named people | `Creator.principal_investigator`, `LicenseAndUseTerms.contact_person`, `ExportControlRegulatoryRestrictions.governance_committee_contact`, `EthicalReview.contact_person` — the source defers all personnel to `aireadi.org/team` and defers dataset contact to "the README file included with the dataset" |
| CRediT roles and affiliations | `Creator.credit_roles`, `Creator.affiliations` — no role taxonomy or member-institution mapping |
| Imputation | `imputation_protocols` — never mentioned |
| Annotation quality | `annotation_analyses`, `machine_annotation_tools`, and the `LabelingStrategy` quantitative fields (`annotations_per_item`, `inter_annotator_agreement`, `annotator_demographics`, `data_annotation_platform`) — the source answers "N/A, no labels are provided" |
| Errata | `errata` — question marked `(no response provided)` |
| De-identification method | `Deidentification.method`, `Deidentification.identifiers_removed`, `ParticipantPrivacy.anonymization_method` — both de-identification questions marked `(no response provided)` |
| At-risk populations | `at_risk_populations` — no assent procedures, guardian consent, or special protections described |
| Schema conformance | `conforms_to`, `conforms_to_class`, `conforms_to_schema` — OMOP CDM and DICOM are described as terminologies data were "mapped to when possible", which is weaker than a conformance claim, so this was left empty and kept in `preprocessing_strategies` as prose |
| Data-use permission codes | `LicenseAndUseTerms.data_use_permission` — the source describes the license narratively (commercial or research use permitted, with requirements on usage, security, and secondary sharing) but no DUO-style permission maps cleanly onto it |
| HIPAA / compliance status | `ExportControlRegulatoryRestrictions.hipaa_compliant`, `other_compliance` — not stated |
| Sub-resources | `resources`, `parent_datasets` — no component datasets described |
| Keywords / status / dates | `keywords`, `status`, `issued`, `created_on`, `last_updated_on`, `page` — no keyword list; release months ("November 2025") lack the day component the `datetime` range requires, so they are held as text in `distribution_dates` |

**Supported only by deferral to an external document (recorded as a pointer, not as content):**
per-modality collection procedures, per-domain processing approaches, file formats and device
details beyond the device list, and citation targets all resolve to `https://docs.aireadi.org`.
Under this arm's boundary that documentation was not fetched, so the records carry the pointer
without the content.

**What the healthsheet supports unusually well** (for contrast): the device and instrument
inventory is the richest area by a wide margin — 19 device/instrument entries with acquisition parameters
(luminance, lux, scan geometry, wavelengths, viewing distances) — followed by data-quality
control procedures, eligibility criteria, consent mechanics, version history with participant
counts, and bias/generalisation discussion.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (`CoreDataset`) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency (final, without `--sync-core`) | PASS: 76 schema-identical slots; projected slots = `['resources']` |
| Phase 3 corrections applied | 1 (stale composition scope statement) |
| Phase 4 unresolved contradictions | 0 |

Line counts, informational only and not a quality gate: full 1106 lines, core 703 lines.

## Files changed

- created `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml`
- created `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml`
- created `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep3/AI_READI_reconciliation.md`
