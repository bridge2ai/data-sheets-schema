# AI_READI full/core reconciliation — healthsheet-only arm

- **Run label:** `2026-07-27_claude-opus-5_rep1`
- **Agent runtime:** Claude Code
- **Provider:** Anthropic
- **Model:** claude-opus-5[1m]
- **Mode:** four-phase project agent (phases 1–4 run strictly sequentially)
- **Temperature:** 0.0
- **Generated:** 2026-07-27

## Arm definition

This arm measures what **one structured upstream source** yields on its own. The
sole factual input was:

```
data/preprocessed/concatenated/AI_READI_healthsheet_only.txt
```

(FAIRhub API record for DOI 10.60775/fairhub.3, `metadata.healthsheet`; 14
sections, 84 questions, 81 answered, 3 recorded as "(no response provided)").

Structure was derived exclusively from the LinkML schemas:

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset`
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset`
- `src/data_sheets_schema/schema/D4D_Core.yaml`

Class shapes, ranges, cardinality, inlining, required slots and enum
permissible values were extracted at runtime with `SchemaView`, not copied from
any example or prior record.

## Outputs

| Artifact | Path | Lines |
|---|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml` | 1379 |
| Core | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml` | 947 |

Line counts are informational metadata, not a quality gate. No pre-existing file
was overwritten; both version directories were created by this run.

---

## Phase 3 — source and provenance audit

### Provenance

- No publication, `docs.aireadi.org` capture, license text, IRB protocol,
  FAIRhub API record, RO-Crate, or `AI_READI_preprocessed.txt` corpus was opened.
- Nothing under `data/preprocessed/individual/`, `data/raw/`,
  `data/d4d_concatenated/`, or `data/d4d_individual/` was read, other than this
  run's own two output files.
- `data/preprocessed/source_manifest.yaml` was **not** read; this arm declares its
  single source bundle explicitly instead, and both file headers say so.
- No prior full or core D4D was read, at any phase, in any form. No D4D content
  from the parent conversation was used as evidence.
- No live web content was fetched. URLs appearing in the records are strings
  quoted from the Healthsheet; none were resolved.

### Mechanical evidence check

Every literal in both records was traced back to the source bundle:

- **14 distinct external URLs** in each record — all present in the source
  (verified both raw and percent-decoded). Internal minted identifiers of the
  form `https://doi.org/10.60775/fairhub.3#…` were excluded from this check; see
  "Identifier scheme" below.
- **51 distinct numeric tokens** (full) / **49** (core) — all present in the
  source.
- **41 named entities** spot-checked (every device make/model, all three
  recruitment sites, REDCap, OMOP, DICOM, FAIRhub, Microsoft Azure, NIH,
  Bridge2AI, AI-READI Consortium, ICD-10, Snellen, logMAR) — all present.

No fabricated identifier, count, date, organization, or device name was found.

### Identifier scheme

`Dataset.id` is the dataset DOI URL `https://doi.org/10.60775/fairhub.3`, taken
from the DISTRIBUTION section ("The dataset' DOI is
https://doi.org/10.60775/fairhub.3") and the bundle preamble. Nested objects use
fragment identifiers minted off that DOI (`…/fairhub.3#purpose-…`). These are
structural keys, not asserted facts, and no external identifier namespace was
invented.

### Assertions with provenance caveats

1. **`name` / `title`** — "Flagship Dataset of Type 2 Diabetes from the AI-READI
   Project" appears only in the source bundle's **preamble**, not in any
   Healthsheet question or answer. It is inside the one allowed file, so it is
   retained, but it is not Healthsheet Q&A content.
2. **Grant number** — the source renders the award two different ways:
   `OT2ODO32644` (MOTIVATION, funding question) and `OT2OD032644` (COLLECTION,
   compensation question). `grant_number: OT2OD032644` was recorded and the
   discrepancy is documented in the grant's `description`. This is an internal
   inconsistency in the single source and is deliberately **not** resolved
   against any other document.
3. **Sampling scope** — the COMPOSITION answer states the dataset contains data
   from "all participants who have been enrolled during the first year of data
   collection", while VERSIONING and COLLECTION both state this version covers
   July 19, 2023 – May 1, 2025 (through the end of the second year). The verbatim
   answer is preserved and a `Scope note` bullet was added to
   `sampling_strategies[0].strategies` recording that the source contradicts
   itself and that the conflict is unresolved within this source. **This was the
   only content correction made during Phase 3.**
4. **`status: published`** — much of the Healthsheet uses future tense ("The
   dataset will be distributed"), but DISTRIBUTION states "the third version of
   the dataset was distributed in November 2025". The past-tense statement was
   taken as authoritative.
5. **`publisher` / `page` = `http://fairhub.io/`** — derived from "The dataset
   will be available through the FAIRhub platform (http://fairhub.io/)" and "The
   dataset is hosted on FAIRhub through Microsoft Azure". This is the platform
   root; the Healthsheet gives no dataset-specific landing page URL.
6. **`license`** — set to `https://doi.org/10.5281/zenodo.17555036`, the license
   document the Healthsheet points to. The Healthsheet never names a standard
   license identifier for the dataset (it does name CC-BY 4.0, but for the
   *documentation*, not the data). No SPDX identifier was inferred.
7. **`regulatory_restrictions.confidentiality_level: restricted`** — the only
   enum value asserted anywhere in either record beyond the bias and limitation
   type vocabularies. Grounded in the two-tier access model: the public tier
   requires agreement with a license, the full dataset requires a data use
   agreement; neither tier is unrestricted.
8. **`is_tabular: false`** — grounded in "These encompass tabular data, imaging
   data, and physiological signal/waveform data", i.e. the dataset is multimodal
   and not solely tabular.
9. **`LicenseAndUseTerms.data_use_permission` deliberately left empty** — the
   Healthsheet says the license permits "commercial or research purpose" with
   "strong requirements around data usage, security, and secondary sharing", but
   does not enumerate permissions in a form that maps onto `DataUsePermissionEnum`
   without inference.
10. **Three upstream non-answers propagated as explicit gaps, not filled**:
    de-identification measures (COMPOSITION), de-identification preprocessing
    (PREPROCESSING), and erratum (MAINTENANCE). The first two are recorded as
    explicit "Upstream gap" / "Not documented" statements inside
    `is_deidentified.deidentification_details`,
    `preprocessing_strategies[0].preprocessing_details`, and
    `participant_privacy[0].anonymization_method`. `errata` is omitted entirely
    from both records.

### Phase 2 discoveries requiring back-port to full

None. Core is a strict schema projection of the full record; the source pass
performed for core found no fact the full record had missed, and no core-only
slot (`distributions`, `dialect`) is supported by the Healthsheet.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime by `data_sheets_schema.d4d_pair_consistency`
from `Dataset` and `CoreDataset` via `SchemaView`; no hand-written field list was
used.

- **76 schema-identical slots** compared.
- **1 projected slot**: `resources` (`Dataset` in full, `CoreDataset` in core).
  Unpopulated in both records — the Healthsheet describes no sub-resources or
  component datasets — so the projection is vacuously equal.
- **56 top-level slots populated** in both records, deep-equal on parsed YAML
  including every nested mapping value and list item in order (independently
  re-verified outside the validator).
- **0 illegal slots** in core: every emitted key is permitted by `CoreDataset`.
- No narrative field was condensed, paraphrased, reordered, or dropped in core.

### Full-only content (no `CoreDataset` slot exists)

Ten populated full-record slots have **no counterpart in `CoreDataset`** and are
therefore absent from core by schema, not by omission:

`related_datasets`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing`

Two of these carry substantive Healthsheet content that the semantic exchange
layer cannot express at all:

- **`splits`** — the recommended 70%/15%/15% training/validation/testing split
  balanced for sex, race/ethnicity and diabetes status. `CoreDataset` has neither
  `splits` nor `subsets`, so this is unrepresentable in core.
- **The consent cluster** (`collection_consents`, `collection_notifications`,
  `consent_revocations`, `participant_privacy`, `participant_compensation`) —
  core retains `informed_consent`, which covers consent type, documentation,
  withdrawal mechanism and scope, so consent itself survives the projection; the
  notification, revocation, privacy-technique and $200 compensation details do
  not.

This is a schema property of the exchange layer, not a defect of this run. It is
recorded in the core file's header comment.

### Related-content semantic review

`file_collections` → `distributions`, `total_file_count`, `total_size_bytes`,
`dialect`, `format`, `compression`, checksums and byte counts are **unpopulated
in both records**: the Healthsheet contains no file-level, format-level, or
size-level information whatsoever. There is consequently no full/core
distribution mapping to reconcile and no possible conflict between
`total_file_count`/`total_size_bytes` and distribution-level values.

`is_tabular` is present and identical (`false`) in both. Top-level identity,
version and access facts (`id`, `doi`, `version: '3'`, `license`, `page`,
`publisher`, `status`) are identical across the pair and agree with
`version_access`, `distribution_dates`, `distribution_formats` and
`license_and_use_terms` in both files.

Historical releases are distinguished from the current release rather than being
treated as contradictions: versions 1 (204 participants, May 2024) and 2 (1067
participants, November 2024) are described in `version_access.versions_available`
and `related_datasets` with explicit version scope, while `version`, `instances`
and `collection_timeframes` describe version 3 only.

### Result

**Zero unresolved contradictions** within either record or between them. The
validator reported no errors and no warnings.

---

## D4D areas the Healthsheet could not support at all

This is the primary result the arm exists to produce. The following schema areas
are **entirely empty** because the Healthsheet contains nothing to populate them
— not because they were skipped.

### Completely unsupported

| Area | Slots left empty | What is missing |
|---|---|---|
| **File and distribution structure** | `file_collections`, `total_file_count`, `total_size_bytes`, `compression`, `dialect`, core `distributions` | No file names, paths, counts, formats, media types, checksums, byte sizes, or compression. The Healthsheet answers "how will the dataset be distributed" with a platform name and a DOI only. |
| **Variable-level metadata** | `variables` | No variable names, data types, units, value ranges, categories, or missing-value codes. The only variable-level fact in the whole source is that Snellen visual acuity was dropped in favour of logMAR. |
| **Named people and organizations** | `creators[].principal_investigator`, `creators[].affiliations`, `creators[].credit_roles`, `EthicalReview.reviewing_organization`, `EthicalReview.contact_person`, `LicenseAndUseTerms.contact_person`, `regulatory_restrictions.governance_committee_contact`, `Maintainer.role` | Not one individual is named. No ORCID, no email, no institutional identifier, no CRediT role. Creators and team are cited only as URLs (`aireadi.org`, `aireadi.org/team`). Maintainer contact is deferred to "the README file included with the dataset". |
| **Sub-resources / composition hierarchy** | `resources`, `parent_datasets`, `subsets` | No component datasets, no parent collection, no named subsets. |
| **Citation** | `citation` | Citation is *required* by the dataset's terms, but the required citation string is never given — the Healthsheet points at `docs.aireadi.org`. |
| **Errata** | `errata` | Recorded upstream as "(no response provided)". |
| **Imputation** | `imputation_protocols` | Never discussed. |
| **Annotation quality / machine annotation** | `annotation_analyses`, `machine_annotation_tools` | Genuinely N/A — the dataset carries no labels — but nothing positive to record either. |
| **At-risk populations** | `at_risk_populations` | The Healthsheet has no question on this. Eligibility criteria (≥40, not pregnant, able to consent) imply the answer but do not assert it, so it was left empty rather than inferred. |
| **Prohibited uses** | `prohibited_uses` | The license is said to impose restrictions, but not one restriction is stated. Everything on this topic reduces to a pointer at the Zenodo license DOI. |
| **Standards conformance** | `conforms_to`, `conforms_to_schema`, `conforms_to_class` | OMOP CDM and DICOM are named as targets data were mapped to "when possible" — a qualified mapping claim, not a conformance assertion, so no conformance was recorded. |
| **Provenance and lifecycle dates** | `created_on`, `issued`, `last_updated_on`, `created_by`, `modified_by`, `was_derived_from`, `download_url` | Release *months* are given (May 2024, November 2024, November 2025) but no day-precision date usable as a `datetime`, and no direct download URL. |
| **Discovery metadata** | `keywords`, `language` | No keywords. English is stated only as the language used to communicate with participants, which is not a statement about the dataset's language, so `language` was left empty. |

### Supported only as a pointer (present but not machine-actionable)

These are populated, but every one resolves to "see the license" or "see the
documentation" rather than to a usable value:

- `license_and_use_terms` — no license identifier, no enumerated permissions;
  `data_use_permission` left empty.
- `ip_restrictions`, `regulatory_restrictions` — both answer "Refer to license".
- `discouraged_uses` — restrictions "described in the License files".
- `distribution_formats` — access URLs only, no formats.
- `collection_mechanisms[0]`, `preprocessing_strategies[0]` — per-domain detail
  deferred to `docs.aireadi.org`.

### Where the Healthsheet is strong

For balance, the source supports these areas richly and specifically:

- **Instrumentation** — 17 distinct collection mechanisms with device makes,
  models, imaging protocols, scan geometries, luminance and viewing-distance
  parameters, and operator-dependence notes. This is by far the densest part of
  the source.
- **Ethics and consent** — IRB date and approval letter, IRB reliance across
  sites, e-consent flow, consent form link, withdrawal terms, $200 compensation.
- **Version history** — three releases with participant counts, dates, prior
  datasheet URLs, and the specific field change between versions.
- **Cleaning and QC** — the four-point data-editing checklist and the site-PI
  approval rule.
- **Bias and limitation** — named, scoped, and paired with mitigations.

---

## Commands run

```bash
# Phase 1 — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — reconciliation (sync once, then independent re-check)
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml \
  --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (`CoreDataset`) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency (`--sync-core`) | PASS: 76 schema-identical slots; projected slots=`['resources']` |
| Pair consistency (independent re-check) | PASS: 76 schema-identical slots; projected slots=`['resources']` |
| Core header `Phase 4 reconciliation: completed` | Present |
| Prior D4D factual reuse | Prohibited, and none occurred |

All validations were re-run after the Phase 3 correction. Both files are clean.
