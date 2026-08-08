# AI_READI — Phase 3 / Phase 4 reconciliation

- **Run label:** `2026-08-07_claude-opus-5-claudecode-generic-v3_rep2`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Runtime / provider / model / reasoning effort:** Claude Code / Anthropic / claude-opus-5 / high
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The pinned referent is **the FAIRhub-published "Flagship Dataset of
Type 2 Diabetes from the AI-READI Project" at its current release, version 3.0.0**
(DOI `10.60775/fairhub.3`, published 2025-11-17, 2,280 participants, 356,343 files, 3.82 TB).

Reasons for this choice over the alternatives the bundle would support:

- The bundle carries a single named dataset with a version history, not a release programme. Nine of
  its ten documents describe that dataset or the study that generated it.
- The manifest explicitly instructs that the v3 documentation and v3 FAIRhub record be preferred
  over their v2 counterparts where the two disagree, and marks the v2 record as superseded upstream
  and "no longer accessible".
- The single richest document in the bundle, the FAIRhub API capture, is metadata *for v3.0.0*.

Consequences held consistently across both records: v1.0.0 and v2.0.0 appear only inside
`version_access` (as historical scope) and `related_datasets` (as `is_new_version_of`), never as
top-level facts; the 2.01 TB / 165,051-file figures are confined to those two slots; and the
`total_file_count`, `total_size_bytes`, `version`, `doi`, `issued` and `file_collections` values are
all v3.0.0 values.

The public and controlled-access releases, and the recommended train/validation/test splits, are
represented as `subsets` of the pinned referent rather than as separate referents. `CoreDataset` has
no `subsets` slot, so this content is full-only; core carries the same information in prose within
the shared slots (`sampling_strategies`, `sensitive_elements`, `known_limitations`,
`license_and_use_terms`).

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped or consulted. The complete factual read set
for this run was:

1. `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (the declared bundle, read in full)
2. `data/preprocessed/source_manifest.yaml`
3. `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
   `data_sheets_schema_core_all.yaml`, both interrogated through `SchemaView` rather than read as
   text, so that every emitted slot name, range, cardinality and enum came from the induced schema
4. the three instruction files named in the task
   (`d4d-provenance-guard.md`, `d4d-full-core.md`, `d4d-agent.md`) and
   `src/download/prompts/d4d_generic_arm_prompt.md`
5. this run's own two output YAMLs

Nothing under `data/d4d_concatenated/` other than this run's own label directory was read; no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was read; no evaluation or reconciliation report
from any earlier run was read. Directory names under `data/d4d_concatenated/claudecode_agent/` were
listed once, to confirm the target label directory did not already exist — no file content was read.

### Source disagreements, represented rather than resolved

| # | Disagreement | Sources | Treatment |
|---|---|---|---|
| 1 | Release scope: 2.01 TB / 165,051 files vs 3.82 TB / 356,343 files | FAIRhub v2.0.0 record vs FAIRhub v3.0.0 record and API | v3.0.0 is the referent; v2.0.0 figures kept in `version_access` with explicit historical scope. Recorded in top-level `source_caveats`. |
| 2 | Lead institution: "Washington University in St. Louis" (ROR 01yc7t268) vs University of Washington | FAIRhub study description (lead sponsor, managing organization, PI affiliation) vs NIH RePORTER awardee organization, BMJ Open author affiliations, licence Licensor | Both recorded. `creators[0].affiliations` lists both organizations, each with a `description` naming the role the sources give it. Recorded in top-level `source_caveats`. Not merged into one claim. |
| 3 | Licence version: "AI-READI custom license v2.0" (Zenodo 17555036) vs the AI-READI-LICENSE-v1.0 text actually bundled (Zenodo 10642459) | FAIRhub v3 rights metadata vs the bundled licence PDF | `license` names both. `license_and_use_terms.license_terms` summarises the v1.0 clauses and its `source_caveats` states that the clause-level terms may not reflect v2.0. |
| 4 | Target enrolment: 4,000 vs "4,000+" vs 4,600 | BMJ Open and FAIRhub study description vs NIH RePORTER vs UW IRB application | 4,000 used where the sources describe the dataset design; the 4,600 and "4,000+" variants recorded in top-level `source_caveats`. No single figure asserted as the truth. |
| 5 | Enrolment start: 18 July 2023 vs 2023-07-19 | BMJ Open vs FAIRhub study description | Both recorded; `collection_timeframes` carries the discrepancy in the pilot entry's `source_caveats`. |
| 6 | De-identification framing: `deIdentType: NoDeIdentification` ("no identifiers were collected") vs "stripped of PHI ... via the 'Safe Harbor' method" | FAIRhub dataset description vs Nature Metabolism comment | Both reproduced in `is_deidentified.deidentification_details`; its `source_caveats` notes that the IRB application records identifiers *are* collected during the study, so the two statements describe the released dataset and the study record respectively. |
| 7 | Demographic subpopulations: healthsheet answers "No" vs README publishing aggregate race/ethnicity and sex counts | FAIRhub healthsheet vs FAIRhub README | Two `subpopulations` entries; the sex/race entry's `source_caveats` states that the reconciliation (individual-level labels withheld, aggregates reported) is inferred from the two statements rather than stated in either. |
| 8 | Coverage claim: "all participants ... enrolled during the first year of data collection" vs a stated collection window of 2023-07-19 to 2025-05-01 with 2,280 participants | FAIRhub healthsheet (composition Q4) vs the same healthsheet, README and dataset description | Recorded in `sampling_strategies[1].source_caveats` as apparently carried over from an earlier version of the answer. |

### Corrections made during Phase 3

Six defects were found in the Phase 1/2 output and corrected in the full record; core was then
regenerated from the corrected full record.

1. **Unsupported re-mapping of ICD-10 codes.** Phase 1 wrote "identifies T2DM and pre-diabetes by
   ICD-10 codes E11.X and R73.09 respectively" — the clinically conventional pairing, but the
   *reverse* of what the BMJ Open protocol literally says. Replaced with the verbatim quotation and
   a `source_caveats` note that the two codes appear transposed relative to their conventional
   meanings. This was the only case in the run where a source statement had been silently corrected.
2. **Boolean asserted where the source is silent.** `external_resources[0].archival: false` was
   removed. The healthsheet question about archival versions is not answered; asserting `false` was
   inference, not evidence. The caveat was reworded to say why both `archival` and
   `future_guarantees` are unpopulated.
3. **Distinct entities merged into one claim.** A single `FundingMechanism` carried seven vendors in
   one `grantor` scalar ("Topcon Corporation; Optomed; iCare World; ..."). Split into seven entries,
   one organization per `grantor`, preserving the loan/discount distinction the source draws.
4. **Two claims drawn from unfilled IRB template text.** The UW IRB application reaches the bundle
   with its checkbox states lost in extraction, so its prisoner and indigenous-recruitment questions
   appear as template text with no answer. The assertions "Prisoners ... are not enrolled" and
   "Native American or non-US indigenous populations are not actively recruited through a tribe"
   were removed, and `at_risk_populations.source_caveats` now states that those answers are
   unavailable. `at_risk_groups_included: false` is retained, resting only on the stated eligibility
   criteria.
5. **Scope mismatch in a slot name.** A `collection_timeframes` entry named "Overall study and
   enrolment period" carried the study completion date (2027-01-01) as its `end_date` while
   enrolment ends 2026-11-30. Renamed "Overall study period"; both dates remain in the details.
6. **Unattributed manifest-derived figure.** The Mini Version's "100 participants" comes from the
   manifest curation note, not from a bundle document; the attribution is now explicit.

### Shape and slot-filling audit

- Every emitted slot name, range, cardinality, inlining behaviour and enum value was derived from
  the induced schema via `SchemaView`; no slot was invented and no `d4d:docExample` value was copied.
- Two shape errors were caught at first validation and fixed before any content review:
  `Person` is referenced by identifier rather than inlined, so the sixteen nested
  `principal_investigator` objects and the two `contact_person` objects became ORCID string
  references, with the person detail (degree, title, email) moved into the enclosing `Creator`
  `description` and the institution into `Creator.affiliations` (`Organization`, which *is* inlined);
  and `issued` required a full `date-time`, so `2025-11-17T00:00:00` became
  `2025-11-17T00:00:00+00:00`.
- Structured slots are filled before prose: `grant_number`, `orcid`-bearing identifiers,
  `affiliations`, `start_date`/`end_date`, `counts`, `file_count`, `total_bytes`,
  `total_file_count`, `total_size_bytes`, `bias_type`, `limitation_type`, `collection_type`,
  `data_use_permission`, `hipaa_compliant`, `confidentiality_level` and the booleans are all
  populated where the evidence supports them, rather than being left empty with their content in
  prose.
- No list-valued slot holds prose and no scalar holds a list. Enum values are all schema-defined
  (confirmed by validation). No commentary is embedded in a `name`, `id` or affiliation value:
  where an organization needed qualification, the qualification went in `Organization.description`.
- Evidence commentary is confined to `source_caveats` (14 occurrences across the record). `notes`
  is used once, at top level, for project-programme context that `description` could not hold, and
  restates nothing.
- **Reference-range reconstruction, disclosed.** The BMJ Open Table 2 arrives in the extracted text
  with its analyte, unit, reference-range and rationale columns split into four separate runs. The
  70 `variables` entries pair them by preserved row order. The reconstruction is internally
  consistent across all four runs — the unit run skips exactly the two unitless ratios, and the
  reference-range run skips exactly the entries the table leaves blank — but it is a reconstruction,
  and the top-level `source_caveats` says so.

## Phase 4 — strict full/core reconciliation

### Schema-identical slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView`; no
hand-written field list was used. Core was generated by projecting the Phase-3-corrected full record
through that derived slot inventory, so every schema-identical slot is present in both records with
deeply identical parsed content, in the same order, including the narrative fields — nothing was
condensed, paraphrased, reordered or omitted to make core shorter.

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
```

Both runs report:

```
PASS: 78 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: deterministic matches=10, unmatched core distributions=[]
```

`--sync-core` changed nothing, because core was already a projection of the canonical full record.

### Projected slot

`resources` is `Dataset` in full and `CoreDataset` in core. It is unpopulated in both records: the
bundle describes one dataset with subsets and version history, not a set of constituent datasets.
Equal coverage is therefore trivially satisfied.

### Related, non-identical content — semantic review

The validator's warning marks content that requires review; the review was performed and is recorded
here.

**`file_collections` (full, 10) → `distributions` (core, 10).** All ten matched by `id`; no
unmatched core distribution. For each pair, `id`, `name`, `path`, `description` and (where present)
`source_caveats` are byte-identical, and `bytes` carries the full record's `total_bytes` for the
same directory-level scope. The `FileCollection` slots with no `CoreDistribution` counterpart —
`collection_type`, `file_count` and `conforms_to` — are omitted from the projection as full-only
nested slots, not dropped as a shortening. `CoreDistribution.format`, `media_type`, `encoding`,
`compression`, `hash`, `md5` and `sha256` are unpopulated because no per-directory checksum is
published and the directory-level standards (WFDB, OMOP CDM, DICOM, Open mHealth, NASA ESDS ASCII)
are not members of `FormatEnum` or `MediaTypeEnum`; forcing them into those enums would have been a
shape error. No value conflicts between the two representations.

**Counts and sizes.** `total_file_count` (356,343) and `total_size_bytes` (3,815,969,779,678) are
full-only, but their scope is the same as the sum of the distribution-level values, so they were
checked against it. The nine datatype directories sum to 356,334 files and 3,815,969,360,064 bytes,
leaving residuals of exactly 9 files and 419,614 bytes — matching the nine root-level metadata files
(`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`, `healthsheet.md`,
`LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`, `study_description.json`), for
which the structure description reports no size. Both totals therefore reconcile. The arithmetic is
recorded in the tenth file collection's `source_caveats`, and so appears identically in core.

**Formats and tabularity.** `distribution_formats` is a shared slot and is identical in both. Its
six entries (DICOM, CSV, JSON, Markdown, TSV, WFDB) are consistent with the per-directory standards
in `distributions`: CSV ↔ `clinical_data`/OMOP, JSON ↔ Open mHealth and the metadata files, DICOM ↔
the four retinal directories, WFDB ↔ `cardiac_ecg`, TSV ↔ the `manifest.tsv` files and
`participants.tsv`, Markdown ↔ the root documentation. Two of the six carry `source_caveats` noting
that TSV and WFDB are absent from FAIRhub's declared `format` array although the structure
description and README name both. `is_tabular: false` is identical in both and is consistent with a
mixed tabular / imaging / waveform release. `dialect` is core-only and unpopulated: no delimiter,
quoting or header convention is stated anywhere in the bundle.

**Top-level identity, version and access facts.** `id`, `doi`, `version`, `issued`, `publisher`,
`download_url`, `page`, `license`, `conforms_to`, `created_by` and `language` are shared slots and
identical in both records. Each was cross-checked against `version_access` (latest DOI
`10.60775/fairhub.3`, matching `doi` and `id`), `distribution_dates` (2025-11-17 for v3.0.0,
matching `issued`), `license_and_use_terms` and `regulatory_restrictions` (both describing the same
access regime as the top-level `license`), and the repeated statements in `subsets` and
`third_party_sharing`. No contradiction found.

**Historical versus current releases.** v1.0.0 and v2.0.0 values differ from the top-level values by
design, not by contradiction; every one of them appears inside a slot whose text states its
historical scope (`version_access.versions_available`, `version_access.version_details`,
`distribution_dates.release_dates`, `related_datasets` with `is_new_version_of`, and
`instances[0].description`). No historical figure leaks into a slot that describes the current
release.

### Slot counts (informational metadata, not a quality gate)

| | top-level slots | populated slots, counted recursively |
|---|---|---|
| full | 82 | 1223 |
| core | 67 | 794 |

### Outcome

Nothing diverged between the two records. All 78 schema-identical slots are present in both with
deeply identical content; the one projected slot is unpopulated in both; the one related-content
mapping (10 pairs) was reviewed and holds no contradiction. Six Phase 3 corrections were applied to
the full record and propagated to core by regeneration before Phase 4 ran.

## Commands run

```bash
# Phase 1 / 2 / 3 / 4 validation (re-run after every correction)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>

# Provenance (after all content edits; order is load-bearing)
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md
poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 --project AI_READI
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2
```

## Files changed by this run

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_d4d_core.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_reconciliation.md` (new, this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/AI_READI_provenance.yaml` (new, written by `d4d provenance record`)

No file outside these four was written.
