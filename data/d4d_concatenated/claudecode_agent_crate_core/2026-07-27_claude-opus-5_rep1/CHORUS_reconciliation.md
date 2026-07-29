# CHORUS full/core reconciliation — 2026-07-27_claude-opus-5_rep1

Arm: **DE NOVO WITH CRATE** (documents + RO-Crate evidence)

## Run identity

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Version label | 2026-07-27_claude-opus-5_rep1 |

## Files

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CHORUS_reconciliation.md` |

## Inputs and evidence boundary

Sole factual input: `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
(2,060 lines / 66 KB). It contains four documents —
`reporter_nih_gov_project-details-10472824_row7.txt`,
`bridge2ai-for-clinical-care-informational-webinar-cohort-2_row9.txt`,
`chorus4ai_org_row11.txt`, `github_chorus_ai_overview_2025-11-14.txt` — plus two
crate artifacts: `CHORUS_crate_metadata_reduced.json` and `ai_ready_score.json`.

Structure/selection references read but not used as fact sources:
`data_sheets_schema_all.yaml` (class `Dataset`), `data_sheets_schema_core_all.yaml`
(class `CoreDataset`), `D4D_Core.yaml` (via the merged core schema),
`data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`,
and `src/data_sheets_schema/d4d_pair_consistency.py`.

Withheld artifacts were **not** read, opened, globbed, or cited:
`CHORUS_crate_d4d.yaml`, `CHORUS_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
`ro-crate-datasheet.html`, any `ro-crate-preview.html`. Nothing under
`data/d4d_concatenated/` or `data/d4d_individual/` was read other than this run's
own outputs. No prior D4D record, evaluation, or reconciliation report was read.
No live web content was fetched.

One consequence of the boundary worth stating: `crate_manifest.yaml` records a
Dataverse dataset URL, a Dataverse publication date of 2026-04-21, and a
Dataverse version 1.1 for this crate. Because the manifest is a selection
reference rather than a fact source, none of those values appear in the record.
The DOI that does appear, `10.18130/V3/XNBOPG`, was taken from the crate's own
`identifier` field inside the bundle, where it is independently corroborated by
`ai_ready_score.json`.

## Phase 1 — full record from the crate-augmented bundle

Structure was derived at runtime from class `Dataset` in
`data_sheets_schema_all.yaml` using `SchemaView.class_induced_slots`, following
`is_a`, slot ranges, required flags, cardinality, inlining, and enums. No prior
D4D was used as a template and no `d4d:docExample` value was copied.

75 top-level slots populated. Four schema-driven structural decisions are worth
recording because they shaped how source facts were placed:

1. `principal_investigator`, `grantor`, `contact_person`,
   `reviewing_organization`, and `governance_committee_contact` are **not**
   inlined in this schema, so they take identifier strings, not objects. The
   person and organization detail (names, emails, the MGB IRB postal address and
   phone) was moved into the adjacent `description` / `review_details` /
   `license_terms` fields rather than dropped.
2. `publisher` has range `uriorcurie`. The crate's publisher value is the literal
   string "B2AI CHoRUS", which is not a URI. `publisher` carries
   `https://chorus4ai.org/`; the literal "B2AI CHoRUS" is preserved in
   `created_by` and as a `creators` entry.
3. `confidentiality_level` is an enum of `unrestricted | restricted |
   confidential`. The crate value "HL7:2V (very restricted)" has no exact
   permissible value; `confidential` was used and the verbatim crate string is
   recorded in `regulatory_restrictions.other_compliance`.
4. The nine data modalities from the webinar table were modelled as
   `subsets` (`DataSubset`), not as `file_collections`, because `file_collections`
   projects onto core `distributions` and the crate documents exactly two
   distributable sub-crates. This keeps the modality inventory in the full record
   without fabricating core distributions.

## Phase 2 — core record

Core structure was derived from class `CoreDataset` in
`data_sheets_schema_core_all.yaml`. No older core record was read, including as a
template. Each core field that also exists in the full record started from the
full record's value; the source bundle was then re-consulted for gaps. No fact
was added to core that is absent from both the full record and the bundle.

Core omits twelve full-record slots that `CoreDataset` does not declare:
`citation`, `collection_consents`, `direct_collection`, `file_collections`,
`participant_privacy`, `related_datasets`, `relationships`, `splits`, `subsets`,
`third_party_sharing`, `total_file_count`, `total_size_bytes`.

Core adds one slot the full schema does not declare: `distributions`
(`CoreDistribution`), authored as the projection of the two `file_collections`.
`dialect` was left unpopulated — the bundle supplies no delimiter, header, or
quoting information.

Phase 2 surfaced no fact that the full record had missed, so no back-port to full
was required on that basis. The Phase 3 audit did produce corrections, and those
were applied to full first and then propagated (see below).

## Phase 3 — source and provenance audit

### Provenance result

Every factual input path is on the Phase 1/2/3 allowlist. No prior generated
YAML was read or cited. No withheld crate artifact was accessed. Every emitted
slot and nested object is permitted by its applicable schema, confirmed by
`linkml-validate` against `Dataset` and `CoreDataset`. The core record's declared
full-record input carries this run's exact version label.

### Corrections applied to the full record, then propagated to core

| # | Finding | Correction |
|---|---|---|
| 1 | `language: en` was an inference. No source states a dataset language. | Slot removed from both records. |
| 2 | `keywords` carried six terms beyond the crate's stated list (`critical care`, `acute illness`, `OMOP Common Data Model`, `waveforms`, `EEG`, `intensive care unit`). Supported by content but not stated as keywords. | Trimmed to exactly the five keywords the crate states. |
| 3 | The EHR sub-crate's `datePublished` is written `03/04/2026`; Phase 1 read it as 2026-03-04. | Corrected to 2026-04-03. The root entity records the same publication event as both `datePublished: "2026-04-03"` and `releaseDate: "03/04/2026"`, so within this crate `03/04/2026` is 3 April 2026. The reasoning is stated in the file collection description and in `distribution_dates`. |
| 4 | `maintainers` gave data-access email addresses without their capture scope. Their only source is the GitHub organization overview captured 2025-11-14, which the manifest flags as a historical supplement. | Capture date and scope stated inline. |
| 5 | `extension_mechanism` described the GitHub contribution surface (28 repositories, discussions, package status page) without capture scope, from the same historical source. | Capture date and scope stated inline. |
| 6 | The project website banner — "This repoitory is under review for potential modification in compliance with Administration directives." — was omitted, but bears on dataset maintenance. | Added verbatim to `updates.update_details`, with the original typographical error preserved and an explicit note that the sources do not say what is in scope. |

### Source disagreements resolved, with reasoning

| Disagreement | Resolution |
|---|---|
| Dataset size: project website reports 23 Tb of waveform data; crate reports `contentSize` "1.2 tb". | Not a contradiction — different scopes. The website describes the CHoRUS enclave dataset; the crate describes the packaged v1.0 Beta interim release. Both are recorded with their scope named. `total_size_bytes` uses the crate scope, and the record's `description` says so. |
| Imaging: webinar reports ~1,000 images available as of August 2025; crate `completeness` says "No DICOM images are included." | Same scope split. Recorded in the `Imaging` subset and in `known_limitations` → "Interim release completeness", whose `scope_impact` states that the limitation applies to the crate package and not to the enclave. |
| Admissions: website reports 50,000 in the current released dataset; webinar reports "over 45K unique admissions" as of August 2025. | Different dates, not a conflict. Both recorded as separate `instances` entries with their dates explicit; the webinar figure is labelled a stated lower bound. |
| Program manager email: website has `cmccrary@mgh.havard.edu`; crate has `cmccrary@mgh.harvard.edu`. | The website form is missing an `r` in `harvard`. The crate form is used; both forms and the assessment are recorded in `license_and_use_terms.description`. |
| Citation names "Harvard Dataverse" while the DOI prefix is `10.18130`. | **Unresolved and left unresolved.** The citation is recorded verbatim. The bundle does not otherwise identify the hosting repository, and the only artifact that would settle it is a selection reference, not a fact source. Flagged here for downstream attention. |
| Crate `rai:dataBiases` and `rai:potentialBiases` are byte-identical; `rai:maintenancePlan` and `rai:dataReleaseMaintenancePlan` are byte-identical. | Duplicate representations, not two facts. Each recorded once. |

### Unit interpretation recorded explicitly

The crate expresses sub-crate sizes as `"18.136671 mb"` and
`"1.201567472832 tb"`. Read as exact byte counts scaled by 10^6 and 10^12 these
are 18,136,671 and 1,201,567,472,832 bytes; the decimal precision (6 and 12
places) is consistent with that reading and with the root's rounded "1.2 tb".
`total_bytes` / `bytes` carry those integers, `total_size_bytes` carries their sum
(1,201,585,609,503), and every affected description states the reading and quotes
the original string so the interpretation is auditable and reversible.

### Assertions deliberately not made

`is_tabular` (content is mixed tabular and waveform), `compression`,
`variables`, `imputation_protocols`, `annotation_analyses`, `errata`,
`retention_limit`, `content_warnings`, `collection_notifications`,
`consent_revocations`, `participant_compensation`, `use_repository`,
`parent_datasets`, and `updates.frequency` are omitted — the bundle supports none
of them. `informed_consent.consent_obtained` is left unset: the crate states "IRB
approval or waiver as appropriate" and a HIPAA exemption, which establishes a
regulatory basis without establishing whether individual consent was obtained.

One scope trap was avoided: the Cohort 2 webinar's $8,000 trainee stipend,
citizenship rules, and application deadlines describe the AIM-AHEAD training
program, not the dataset or its data subjects. None of it appears in
`participant_compensation` or in any collection field; the training program
appears only in `existing_uses`, described as a use of the dataset.

### Interpretation flagged for the reader

`credit_roles` values are a schema-required CRediT categorization inferred from
stated activities (the crate labels these people `author`; the NIH abstract
describes their work). They are the one place in the record where the value is a
categorization rather than a source assertion.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime by `d4d_pair_consistency.load_pair_schema`,
not from a hand-written list.

- Schema-identical slots: **76**
- Projected slots: **`resources`** — absent from both records, so no projection was required.
- Synchronization was run once, after the Phase 3 audit made full canonical, then the validator was re-run without `--sync-core` as an independent check.

Result: **PASS**, zero errors. One warning is emitted by design —
`semantic-review-required` on `$.file_collections <-> $.distributions` — marking
related content for the manual review below. Deterministic matches: 2. Unmatched
core distributions: 0.

### Semantic review of related, non-identical content

**`file_collections` → `distributions`.** Two collections, two distributions,
matched deterministically on both `id` and `name`.

| Property | Full `file_collections` | Core `distributions` | Verdict |
|---|---|---|---|
| id | `urn:uuid:08cf7419-…` / `urn:uuid:b9b41c72-…` | identical | consistent |
| name | EHR SubRoCrate / Waveforms SubRoCrate | identical | consistent |
| size | `total_bytes` 18,136,671 / 1,201,567,472,832 | `bytes`, same integers | consistent |
| path | absent (crate publishes no internal path) | absent | consistent |
| compression | absent | absent | consistent |
| format / media type | not applicable to `FileCollection` | deliberately unset | see note |
| checksums | not applicable to `FileCollection` | deliberately unset | see note |
| access URL | `download_url: https://chorus4ai.org/dataset/` | stated in `description` | consistent |
| release scope | `version: 1.0 Beta`, `issued: 2026-04-03` | stated in `description` | consistent |

Note on format and checksums: the crate reports formats (`.ipynb`,
`text/tab-separated-values`, `wfdb`) and checksum coverage (1,469 of 1,477 files)
only at package level, never per sub-crate. Assigning TSV to the EHR distribution
would have been an inference, and `wfdb` is not a permissible value of the core
`FormatEnum` or `MediaTypeEnum`. Both fields are therefore left unset, and each
distribution's `description` states the package-level values and the reason for
the omission.

**Counts and sizes across scopes.** `total_file_count` (1,477) and
`total_size_bytes` (1,201,585,609,503) exist only in the full record. The sum of
the two `distributions[].bytes` equals `total_size_bytes` exactly. Both figures
are scoped to the crate package, which the record `description` states; neither
purports to describe the CHoRUS enclave dataset.

**`dialect`, formats, `is_tabular`.** All three unset in both records; nothing to
reconcile and nothing in conflict.

**Identity, version, and access facts.** `id`, `doi`,
`version_access.latest_version_doi`, and the DOI cited in `distribution_formats`
all resolve to `10.18130/V3/XNBOPG`. `version` is "1.0 Beta" at top level and on
both file collections. `issued` is 2026-04-03 at top level and on both file
collections. Access rules stated in `license_and_use_terms`,
`regulatory_restrictions`, `third_party_sharing`, `external_resources.restrictions`,
and `confidential_elements` agree: controlled access, DUA, governance-committee
review, enclave-only, no unapproved export. No internal contradiction found.

**Historical versus current.** The webinar's August 2025 snapshot and the
website's current-release figures are recorded as distinct dated statements, not
as competing values for one field. The GitHub-derived material carries its
2025-11-14 capture date. Nothing in either record treats a dated historical value
as a current one.

## Per-field evidence attribution

This is the primary result of the with-crate arm: which populated content came
from crate evidence alone, from the document corpus alone, or from both.

### Crate-only (28 top-level slots)

Content that the CHoRUS document corpus does not supply at all:

`doi`, `version`, `issued`, `citation`, `created_by`, `conforms_to_schema`,
`keywords`, `total_file_count`, `total_size_bytes`, `file_collections` (core:
`distributions`), `anomalies`, `known_biases`, `known_limitations`,
`sensitive_elements`, `direct_collection`, `collection_consents`,
`data_protection_impacts`, `human_subject_research`, `informed_consent`,
`intended_uses`, `discouraged_uses`, `prohibited_uses`, `future_use_impacts`,
`distribution_dates`, `ip_restrictions`, `version_access`, `is_deidentified`,
`related_datasets`.

The governance content the arm note predicted is confirmed absent from the
documents and present only in the crate: IRB protocol `#2022P000707`, the Mass
General Brigham IRB as reviewing body with its contact point, the
`HL7:2V (very restricted)` confidentiality level, the six `rai:dataBiases`
entries, the seven `rai:dataLimitations` entries, the DUA document URL and
`rai:conditionsOfAccess` terms, the `1.2 tb` content size, and
"No DICOM images are included."

Also crate-only and not anticipated by the arm note: the 41-author list with 15
institutional affiliations, the copyright notice, the formal citation, the
`fdaRegulated` and `deidentified` declarations, the HIPAA exemption-4 basis, the
named de-identification tooling (RSNA Clinical Trial Processor, IbisWorks EICON),
the NIST 800-53 alignment, the nine intended use cases and three not-recommended
uses, the versioned-release and deprecation policy, and the AI-readiness
inventory (1,477 files, 1,469 checksums, 1,468 datasets, 44 schemas, 2
computation steps, 1 software instance).

### Document-only (10 top-level slots)

Content the crate does not supply:

`page`, `tasks`, `addressing_gaps`, `subsets`, `data_collectors`,
`cleaning_strategies`, `labeling_strategies`, `existing_uses`, `other_tasks`,
`extension_mechanism`.

Specifically: the NIH award record (application 10472824, project number
1OT2OD032701-01, FY2022, $5,880,300, 2022-09-01 to 2026-11-30); the three-pillar
structure; the enclave-scale figures (50,000 released admissions, 100,000
anticipated, 1.6 billion OMOP rows, 7,642 admissions with radiology, 23 Tb
waveform, 14 hospitals, 20 institutions, 60+ members); the August 2025 snapshot;
the nine-modality data-standard table; the chorus-ai repository, SOP, semantic
mapping, and status-tracking infrastructure; the MIT and Apache-2.0 software
licensing; the AIM-AHEAD training program as an existing use; and the
`.edu`-email and registration access path for trainees.

### Both (37 top-level slots)

`id`, `name`, `title`, `description`, `status`, `download_url`, `publisher`,
`license`, `was_derived_from`, `conforms_to`, `external_resources`, `purposes`,
`creators`, `funders`, `instances`, `relationships`, `splits`, `subpopulations`,
`confidential_elements`, `acquisition_methods`, `collection_mechanisms`,
`sampling_strategies`, `collection_timeframes`, `missing_data_documentation`,
`raw_data_sources`, `ethical_reviews`, `at_risk_populations`,
`participant_privacy`, `preprocessing_strategies`, `raw_sources`,
`machine_annotation_tools`, `distribution_formats`, `third_party_sharing`,
`license_and_use_terms`, `regulatory_restrictions`, `maintainers`, `updates`.

Within these, the two sources are complementary rather than redundant. Typical
pattern: `collection_mechanisms` takes the pipeline steps and de-identification
tooling from the crate and the modality sources (PACS, bedside monitors and
gateway/middleware, hospital EEG databases, OHNLP tokenization) from the webinar;
`ethical_reviews` takes the IRB of record, protocol number, and reviewer names
from the crate and the community-facing ethics focus groups from the NIH abstract
and project website; `creators` takes the author network from the crate and the
leadership team from the webinar; `maintainers` takes the CHoRUS Data Pillar and
governance contact from the crate and the program manager and access-request
addresses from the website and GitHub overview.

### Summary

Of 75 populated top-level slots in the full record, **28 are crate-only**,
**10 are document-only**, and **37 draw on both**. The crate is the sole source
for essentially the entire governance, ethics, licensing, bias, limitation, and
release-management surface of this datasheet. The documents are the sole source
for funding provenance, scale figures, modality inventory, and the software and
SOP ecosystem. Neither source alone would have produced this record.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` against `Dataset` | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` against `CoreDataset` | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency (post-sync, independent run) | PASS — 76 schema-identical slots, 0 errors |
| Schema-identical slot divergence | None |
| Projected slot (`resources`) | Absent from both; no projection needed |
| Related-content contradictions | None unresolved |
| Provenance audit | No prior-run D4D, evaluation, or reconciliation report used; no withheld crate artifact accessed |
| Core header `Phase 4 reconciliation: completed` | Present |

Line counts, informational only and not a quality gate: full 1,500 lines,
core 1,124 lines.
