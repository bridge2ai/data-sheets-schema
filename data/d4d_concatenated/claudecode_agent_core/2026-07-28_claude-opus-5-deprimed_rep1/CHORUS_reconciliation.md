# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep1

- **Arm:** BASELINE (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`
- **Mode:** four-phase project agent, de-primed; temperature 0.0
- **Input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 documents, 1699 lines)
- **Manifest:** `data/preprocessed/source_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml` — 48 top-level slots
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml` — 43 top-level slots

---

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record was read, opened, grepped, or consulted, from any
arm, label, or date. The complete factual read history for this run is:

1. `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
2. `data/preprocessed/source_manifest.yaml`
3. `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (via `SchemaView`, class `Dataset`)
4. `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (via `SchemaView`, class `CoreDataset`)
5. The run's own Phase 1 full record, read only in Phase 2 and later.

Structure was derived entirely from the two schemas by programmatic induction
(`class_induced_slots`), not from any example record. A throwaway probe file was
used to confirm the inlining behaviour of `principal_investigator`, `grantor`, and
`contact_person` (all non-inlined, so string references rather than nested
objects) before any content was written.

### Source disagreements resolved

The bundle contains two independent, differently dated accounts of dataset size.
Neither was preferred over the other; both were retained with explicit scope,
which is why several `instances` entries carry a date qualifier.

| Fact | `chorus4ai.org` (undated) | Cohort 2 webinar (August 2025) | Resolution |
|---|---|---|---|
| Admissions | 50,000 (ICU, PICU, NICU) | over 45,000 unique admissions | Both retained; each labelled with its source scope. The webinar figure is a lower bound, so no exact count is asserted for it. |
| Imaging | 7,642 admissions with radiology data | 1,000 images available, de-id in process | Not a contradiction — different units (admissions vs images) and different capture dates. Both retained with scope. |
| Hospitals | 14 data contributing hospitals | 14 different hospitals | Agrees; also agrees with the GitHub overview's "20 academic centers, of which 14 will contribute as Data Acquisition centers". |
| Target size | 100,000 patient admissions (anticipated) | — | NIH abstract says "more than 100,000 critically ill patients". Admissions and patients are different units, so both are recorded verbatim and separately in `updates`, not merged. |

### Mis-scoped assertions identified and corrected

Four corrections were made to the full record during Phase 3, before core was
regenerated:

1. **`resources` / nursing flowsheets.** The Phase 1 text attached the webinar's
   "OMOP schema with extensions" metadata entry to the nursing flowsheets
   modality. The webinar's data-type table survives PDF extraction in scrambled
   column order, so that entry cannot be assigned to a single row. The claim was
   removed from the modality and restated at aggregate level in
   `distribution_formats`, where it is explicitly marked as unassignable.
2. **`distribution_formats.access_urls`.** `https://chorus4ai.org/` had been
   listed as an access URL for the controlled-access enclave. It is the project
   landing page, not a data access point, and the enclave has no published URL in
   the bundle. Removed; the site remains in `page` and `external_resources`.
3. **Duplicate organization identifiers.** Three separate `Organization` objects
   with distinct ids (`chorus_org_uf`, `chorus_org_uf_strekalova`,
   `chorus_org_uf_rashidi`) all named "University of Florida". Consolidated to a
   single id reused across the three affected creators.
4. **Back-port from source re-read.** The NIH abstract's statement of
   collaboration scope ("extensive collaboration between centers as well as
   through the NIH Bridge2AI program, the NIH Bridge2AI Bridge Center, external
   biomedical and clinical organizations, industry, and regulatory agencies") was
   absent from Phase 1 and was added to the consortium `Creator`.

### Scope boundaries deliberately enforced

The bundle's second document is largely about the AIM-AHEAD Bridge2AI for Clinical
Care **training program**, not the dataset. Program facts were excluded unless the
source states them as dataset properties:

- **Excluded:** the $8,000 trainee stipend and travel allowances (these are
  trainee compensation, *not* research-participant compensation — `participant_compensation`
  is therefore absent rather than populated), citizenship/permanent-residency and
  W-9 requirements, application deadlines, the 30-trainee cap, curriculum
  listings, and mentorship mechanics.
- **Included:** the registration form, the mandatory licensing agreement, and the
  ".edu" email requirement, because the source states these under "Accessing the
  Data" and "In order to gain access to the dataset".

The MIT licence is similarly scoped. The GitHub README's "This project is licensed
under the MIT License" covers the CHoRUS software organization, not the clinical
dataset, which is controlled-access. Top-level `license` was therefore left
**absent**, and the MIT/Apache-2.0 terms appear only inside
`license_and_use_terms.license_terms` with an explicit statement that they cover
software and documentation rather than the dataset.

### Judgement calls recorded

- **`keywords`.** The NIH RePORTER "Preferred terms" field supplies ~76 auto-indexed
  project terms. Substantive terms were kept (45); vacuous indexing artefacts
  ("Address", "Ensure", "Event", "Goals", "Discipline", "electronic structure",
  "improved") were dropped as misleading dataset keywords.
- **`conforms_to: OMOP Common Data Model`** at top level is reductive for a
  dataset that also carries DICOM, WFDB, EDF+/Persyst, and OHNLP content, but OMOP
  is the project's declared standardization target ("standardize data to the OMOP
  Common Data Model"). Per-modality standards are carried on `resources[].conforms_to`.
- **Inference-level booleans.** `acquisition_methods.was_directly_observed: true`
  and `was_reported_by_subjects: false` are inferred from the stated provenance
  (provider documentation, bedside monitors, PACS, hospital EEG databases) rather
  than asserted verbatim. `is_deidentified.identifiable_elements_present` and
  `human_subject_research.irb_approval` were left absent — the bundle reports
  de-identification *activity* but no residual-risk determination, and reports no
  IRB record at all.
- **`license_and_use_terms.contact_person: Jared Houghtaling`** links the GitHub
  README's access-request address to the person of that name identified in the
  webinar as a Tufts contributor. This is a cross-document name match, not a
  stated identity.
- **Verbatim reproduction of source defects.** The project website's contact
  address (`cmccrary@mgh.havard.edu`) and its banner ("This repoitory is under
  review...") both contain typographical errors in the source. Both are reproduced
  as printed, with the record noting that they are as-printed.
- **Absent by design.** `anomalies`, `known_biases`, `content_warnings`,
  `informed_consent`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `data_protection_impacts`, `imputation_protocols`,
  `annotation_analyses`, `use_repository`, `discouraged_uses`, `prohibited_uses`,
  `errata`, `retention_limit`, `version_access`, `distribution_dates`, `variables`,
  `is_tabular`, `doi`, `version`, `citation`, `publisher`, and `file_collections`
  are all unsupported by the bundle and were omitted rather than filled.

### Validation after correction

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# Validation passed
```

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot analysis

Shared slots were computed at runtime from `Dataset` and `CoreDataset` with
LinkML `SchemaView`; no hand-written field list was used.

- **Shared slots:** 77
- **Schema-identical (same induced range and cardinality):** 76
- **True projections (range differs):** 1 — `resources`, `Dataset` in full and
  `CoreDataset` in core
- **Full-only slots:** 17 (`citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `parent_datasets`, `participant_compensation`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`, `subsets`,
  `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`)
- **Core-only slots:** 2 (`dialect`, `distributions`)

Note on the 43 slots that a naive flag comparison reports as differing: for all of
them except `resources` the difference is only that the full schema sets both
`inlined: true` and `inlined_as_list: true` while core sets `inlined_as_list: true`
alone. These are semantically identical, and the schema-derived validator treats
them as such.

### Core derivation

Core was produced by copying every shared slot's parsed value from the Phase
3-audited full record, then projecting `resources` into `CoreDataset` shape by
filtering each nested object to slots the core schema permits. All nine modality
resources use only `id`, `name`, `description`, and `conforms_to`, every one of
which exists on `CoreDataset`, so the projection dropped nothing and coverage is
equal on both sides.

Five full-only slots carry content that has no core home and is therefore absent
from core by schema design, not by condensation: `subsets` (the holdout test set),
`splits`, `direct_collection`, `participant_privacy`, and `third_party_sharing`.

Before copying, every core slot was checked against the source bundle for content
the full extraction had missed. Two core-only slots were considered and left
absent:

- **`distributions`** — the bundle supplies no file paths, byte counts, checksums,
  or `FormatEnum`-compatible formats. The one volume figure available, "23 Tb of
  waveform data", is both modality-scoped and unit-ambiguous (Tb vs TB), so
  converting it to a `bytes` integer would fabricate precision. Recorded as prose
  on an `instances` entry instead.
- **`dialect`** — no delimiter, header, or quoting information exists in the
  bundle.

No Phase 2 discovery required back-porting to full; the one back-port listed
above was found during the Phase 3 source re-read.

### Related-content semantic review

| Related pair | Finding |
|---|---|
| full `file_collections` → core `distributions` | Both absent. Nothing to map; no conflict possible. |
| `total_file_count` / `total_size_bytes` vs distribution-level values | Absent on both sides. The only size figure in the bundle (23 Tb waveform) is modality-scoped, not a dataset total, and is not asserted as one. |
| `dialect`, formats, `is_tabular` | `is_tabular` absent in both (the dataset mixes OMOP tables with DICOM, WFDB, and EDF+ content, so neither value is supportable); `dialect` absent; `distribution_formats` deeply identical in both records. |
| Top-level identity/version/access vs `resources` and repeated statements | Consistent. "Controlled access" appears on all nine modality resources, in the top-level description, in `license_and_use_terms`, and as `regulatory_restrictions.confidentiality_level: restricted`, with no divergence. The grant identifier `OT2OD032701` is stated identically in `funders.grants[0].grant_number`, in the funder description, and in the NIH RePORTER external resource. The project period 2022-09-01 to 2026-11-30 appears identically in `funders` and `collection_timeframes`. |
| Historical release vs current release | Treated as distinct scopes rather than as a contradiction. The August 2025 webinar snapshot (45,000+ admissions, 1,000 images, EEG extraction in process) and the project website's current released figures (50,000 admissions, 1.6 billion OMOP rows, 7,642 admissions with radiology, 23 Tb waveform) each carry their scope in the entry text. |

### Deterministic check

`--sync-core` was **not** required: core was generated from the audited full record
by schema-derived copy, so it was already consistent on first check. The
independent check was run directly.

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml
# PASS: 76 schema-identical slots; projected slots=['resources']
# errors: []   warnings: []
```

### Final validation

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset <full>                                    # No issues found
poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
                                                       # Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset <core>                                # No issues found
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
                                                       # Validation passed
```

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_d4d_core.yaml` (created, regenerated after Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/CHORUS_provenance.yaml` (live provenance record)

Nothing outside these paths was modified.

### Outcome

**Clean.** Zero unresolved contradictions within or between the two records. All 76
schema-identical shared slots are deeply identical and identically present. The
single projected slot (`resources`, 9 entries) matches by `id` with equal coverage
and deep identity on every nested schema-identical slot. Every related,
non-identical representation was reviewed semantically and none conflicts.
