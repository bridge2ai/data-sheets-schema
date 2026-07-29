# CHORUS full/core reconciliation — 2026-07-27_claude-opus-5_rep3

**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Agent runtime:** Claude Code · **Provider:** Anthropic · **Model:** claude-opus-5[1m]
**Mode:** four-phase project agent · **Temperature:** 0.0 · **Generated:** 2026-07-27

| Artifact | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CHORUS_reconciliation.md` |

**Sole factual input:** `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
(4 documents + `CHORUS_crate_metadata_reduced.json` + `ai_ready_score.json`).
Structure/selection references consulted, not used as fact sources:
`data_sheets_schema_all.yaml` (class `Dataset`), `data_sheets_schema_core_all.yaml`
(class `CoreDataset`), `D4D_Core.yaml`, `source_manifest.yaml`, `crate_manifest.yaml`.

---

## Phase 1 — full record

Structure derived at runtime from class `Dataset` via LinkML `SchemaView`, following
`is_a`, inherited slots, induced ranges, cardinality, inlining, and enum constraints.
No prior D4D record was read as a template or fact source.

Two schema behaviours were probed empirically before writing (probe file, discarded):
single-valued `Person`/`Organization`/`Grantor` ranges (`principal_investigator`,
`contact_person`, `reviewing_organization`, `governance_committee_contact`, `grantor`)
are **not** inlined, because those classes carry an identifier — they take a
`uriorcurie` reference string, not a nested object. Where the source supplies a real
identifier, the reference preserves it (`mailto:EROSENTHAL@mgh.harvard.edu`,
`mailto:cmccrary@mgh.harvard.edu`, `mailto:irbreliance@mgb.org`); otherwise a `d4d:`
CURIE is used and the human-readable content is carried in the sibling
`name`/`description` slots.

## Phase 2 — core record

`CoreDataset` field inventory derived from the merged core schema (76 shared slots +
`distributions` + `dialect` + core-scoped `resources`). Core was produced by projecting
the Phase 1 full record through that inventory, so every shared slot is byte-identical by
construction rather than re-narrated. The source bundle was re-read for core-only slots;
it supports no value for `dialect`, `conforms_to*`, or `resources`, and none was invented.
No core field was populated that the full record or the sources do not support, and no
Phase 2 discovery required back-porting into full.

Full-only slots dropped from core (not in `CoreDataset`): `citation`, `total_file_count`,
`total_size_bytes`, `file_collections`, `relationships`, `splits`, `direct_collection`,
`collection_consents`, `participant_privacy`, `third_party_sharing`, `related_datasets`.

---

## Per-field evidence attribution (the primary result of this arm)

### Populated ONLY from crate evidence

Content below is absent from the four-document CHORUS corpus and was extracted from
`CHORUS_crate_metadata_reduced.json` / `ai_ready_score.json`.

| Field | Crate-only content |
|---|---|
| `id`, `doi`, `version_access.latest_version_doi` | `10.18130/V3/XNBOPG` |
| `title` | Full dataset title, from the crate citation |
| `version`, `issued` | `1.0 Beta`; `2026-04-03` |
| `status` | Interim-release characterisation (crate `completeness`) |
| `license` | `Data Use Agreement available at 'https://chorus4ai.org/dataset/'` |
| `publisher`, `download_url` | `B2AI CHoRUS` (mapped to a URI); crate `contentUrl` |
| `citation` | Recommended citation string |
| `keywords` | All 5 keywords |
| `total_file_count` | 1,477 files (`ai_ready_score` checksum coverage 1469/1477) |
| `total_size_bytes` | 1,201,585,609,503 (sum of the two sub-crate `contentSize` values; the root states "1.2 tb") |
| `file_collections` / core `distributions` | Both sub-crates, their UUIDs, and their exact byte counts |
| `known_biases` | **All six** bias entries (`rai:dataBiases` / `rai:potentialBiases`) and the "bias assessment is ongoing" mitigation |
| `known_limitations` | Seven of eight entries (`rai:dataLimitations`); the eighth combines crate `completeness` with document counts |
| `anomalies` | All anomaly details |
| `sensitive_elements` | All ten `rai:personalSensitiveInformation` items |
| `ethical_reviews[0]` | **IRB protocol #2022P000707**, Mass General Brigham IRB, its postal address and reliance contact, the five named ethical reviewers, HIPAA exemption 4 (45 CFR 46.104(d)(4)) |
| `human_subject_research` | `irb_approval`, `ethics_review_board`, FDA-regulated status, HIPAA/NIST/OT compliance (except PICU/NICU `special_populations`) |
| `informed_consent` | IRB approval-or-waiver basis and exemption documentation |
| `at_risk_populations.special_protections` | Layered privacy protection; **confidentiality level HL7:2V** |
| `participant_privacy` | `anonymization_method`, `reidentification_risk`, `privacy_techniques` |
| `is_deidentified` | Entire object (crate `deidentified`, Safe Harbor method, RSNA CTP / IbisWorks EICON) |
| `data_protection_impacts` | Periodic re-identification risk assessment, export restrictions, output review |
| `intended_uses` | **All nine** `rai:intendedUseCases` examples plus the governance usage note |
| `discouraged_uses` | All three "Not recommended" items |
| `prohibited_uses` | All four items (re-identification, enclave export, commercial use) |
| `license_and_use_terms` | DUA URL, Data-Agreement-9.30.2025.docx, the six-condition access framework, non-commercial clause, and all five `data_use_permission` enum values |
| `ip_restrictions` | Entire object — the MGH copyright notice and subaward/joint-software clauses |
| `regulatory_restrictions` | Entire object — enclave restriction, OT terms, FDA-regulated flag, `hipaa_compliant`, `confidentiality_level`, governance contact |
| `updates` | Entire object — `rai:maintenancePlan` / `rai:dataReleaseMaintenancePlan` |
| `retention_limit` | Entire object — enclave archival / incremental change records |
| `version_access` | Entire object |
| `maintainers[0]`, `maintainers[1]` | CHoRUS Data Pillar + institutional data stewards; data governance committee |
| `third_party_sharing` | Entire object — `rai:conditionsOfAccess` |
| `future_use_impacts` | Entire object — deprecation policy, population-inference limit, ongoing bias assessment |
| `direct_collection` | Entire object — data repurposed from clinical workflows, observational and not randomized |
| `preprocessing_strategies[1]` | Entire object — RSNA Clinical Trial Processor, IbisWorks EICON pixel-level de-identification |
| `distribution_dates` | Both release dates |
| `distribution_formats[5]` | RO-Crate metadata package entry |
| `instances[5]` | Crate file inventory: 1,477 files, 1,468 datasets, 44 schemas, 2 computation steps, 1 software instance, formats `.ipynb` / `text/tab-separated-values` / `wfdb` |
| `creators[0]` | The 41-name author list and **all 15 institutional affiliations** |
| `creators[1]`, `creators[3]` | PI and program-manager email addresses |
| `sampling_strategies.why_not_representative` | All three items |
| `data_collectors` | "CHoRUS Data Pillar in collaboration with institutional data stewards" |
| `subpopulations.distribution[0]` | Socioeconomic/demographic distribution statement |
| `external_resources[2]` | The Data Use Agreement document URL |
| `splits[1]` | Hold-out / development-split overfitting caveat |
| `purposes[1]` | Secure, auditable, reproducible AI research statement |

The arm note's expectation held: **IRB protocol #2022P000707, the Mass General Brigham
IRB, confidentiality level HL7:2V, the RAI biases and limitations, the DUA terms, the
1.2 TB content size, and "no DICOM images included" are all crate-only** — the document
corpus contains none of them.

### Populated ONLY from the document corpus

`name`, `page`; `purposes[0]`, `purposes[2]`; all `tasks`; all `addressing_gaps`;
`funders.grants` (application ID 10472824, project number 1OT2OD032701-01, FY2022,
award amount 5,880,300, project period 2022-09-01 → 2026-11-30, awardee organization);
`creators[2]` (leadership team); `instances[0]`–`instances[4]` (50,000 admissions,
1.6 billion OMOP rows, 7,642 radiology admissions, 23 TB waveform, tokenized notes);
`subpopulations.identification`; `existing_uses`; `use_repository`; `other_tasks`;
`cleaning_strategies` (entire object); `labeling_strategies` (all but one bullet);
`ethical_reviews[1]` (community ethics focus groups); `external_resources[0]`
(GitHub organization and all eleven `used_software` entries), `external_resources[1]`,
`external_resources[3]`; `extension_mechanism` (entire object);
`distribution_formats[0]`–`distribution_formats[4]` (the modality/standard/access table);
`raw_data_sources` source and format rows; `maintainers[2]` access-request contacts.

### Populated from both sources

`description`, `acquisition_methods`, `collection_mechanisms`, `collection_timeframes`,
`missing_data_documentation`, `confidential_elements`, `machine_annotation_tools`,
`participant_privacy.data_linkage`, `preprocessing_strategies[0]`, `raw_sources`,
`relationships`, `human_subject_research.special_populations`,
`at_risk_populations.description`, `license_and_use_terms.license_terms` (crate DUA terms
+ document training-program and MIT-license terms), `known_limitations[7]`, `funders`.

---

## Phase 3 — source and provenance audit

**Provenance.** Every factual input path is on the Phase 1/2 allowlist. No file under
`data/d4d_concatenated/` or `data/d4d_individual/` was read other than this run's own two
outputs; no prior D4D record, evaluation, or reconciliation report was read; no live web
content was fetched. The withheld crate artifacts
(`CHORUS_crate_d4d.yaml`, `CHORUS_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
`ro-crate-datasheet.html`, and any `ro-crate-preview.html`) were **not** opened, globbed,
or cited. The core file's declared full-record input carries this run's exact version
label `2026-07-27_claude-opus-5_rep3`.

**Source findings.**

1. **Ambiguous crate dates.** The root entity gives `datePublished: 2026-04-03` and
   `releaseDate: 03/04/2026`; the EHR sub-crate gives `datePublished: 03/04/2026`. Taken
   together the crate's own convention is DD/MM/YYYY, so all three denote 2026-04-03.
   `issued` is set to `2026-04-03T00:00:00Z` throughout and the ambiguity is stated
   explicitly in `collection_timeframes` and `distribution_dates` rather than silently
   resolved.
2. **Contact-email typo in the document corpus.** `chorus4ai.org` prints
   `cmccrary@mgh.havard.edu` ("havard"); the crate gives `cmccrary@mgh.harvard.edu`.
   The crate spelling is used and the typo was not propagated.
3. **Admission counts differ by date, not by contradiction.** The webinar states "as of
   August 2025 … over 45K unique admissions"; the project website states 50,000 admissions
   for the current released dataset. Both are retained with their scope stated.
   Similarly the NIH abstract's "more than 100,000 critically ill patients" and the
   website's "100,000 patient admissions (anticipated final)" are preserved with their own
   wording rather than merged.
4. **`total_size_bytes` is arithmetic, not a quoted value.** The root states "1.2 tb"; the
   two sub-crates state 1.201567472832 tb and 18.136671 mb, both of which are exact
   integers under decimal SI (1,201,567,472,832 and 18,136,671 bytes). Their sum,
   1,201,585,609,503, is recorded and is consistent with the root's "1.2 tb".
   The 23 TB of waveform data reported by the project website is a statement about the
   released dataset, not about this 1.0 Beta crate package; both are retained in their own
   scopes and do not conflict.
5. **`publisher` required a URI.** The crate value is the literal string `B2AI CHoRUS`,
   but the slot range is `uriorcurie`; `https://chorus4ai.org/` (the CHoRUS project site,
   documented in the corpus) is used as its identifier.
6. **`confidentiality_level` enum is coarser than the source.** The crate records
   `HL7:2V (very restricted)`; `ConfidentialityLevelEnum` offers only
   `unrestricted`/`restricted`/`confidential`. `confidential` is used and the exact HL7
   value is preserved verbatim in `regulatory_restrictions.other_compliance`,
   `confidential_elements`, and `at_risk_populations.special_protections`.
7. **Award period is not a collection window.** `collection_timeframes.start_date` /
   `end_date` were deliberately left unset: the only dated interval in the sources is the
   NIH award period (2022-09-01 → 2026-11-30), which is not a data-collection timeframe.
   It is recorded as prose with that scope stated.
8. **Deliberate omissions.** `imputation_protocols`, `annotation_analyses`, `errata`,
   `variables`, `content_warnings`, `consent_revocations`, `collection_notifications`,
   `participant_compensation`, `subsets`, `resources`, `dialect`, `conforms_to*`, and
   `compression` are unsupported by the bundle and were left empty rather than filled.
   Note in particular that the AIM-AHEAD training programme's $8,000 trainee stipend was
   **not** recorded as `participant_compensation` — trainees are data users, not data
   subjects.
9. **Internal consistency verified.** DOI, version `1.0 Beta`, `issued`, sub-crate byte
   counts, licence statements, access conditions, PI and program-manager identities, and
   the 14-of-20-centre network figure are repeated consistently within each file. The two
   distinct licence strings (root `Data Use Agreement available at …` vs sub-crate
   `See Data Use Agreement`) belong to different crate entities and are each preserved
   verbatim on the entity that states them; this is not a contradiction.

No corrections to either record were required by the Phase 3 audit; both files were
already source-consistent, and both were re-validated after the audit.

---

## Phase 4 — strict full/core reconciliation

Shared slots derived at runtime with LinkML `SchemaView` from `Dataset` and `CoreDataset`
— no hand-maintained field list.

**Result: `PASS: 76 schema-identical slots; projected slots=['resources']`.**
All 76 schema-identical slots are present-in-both or absent-from-both and deeply
identical, including every narrative field. Core condenses, paraphrases, reorders, and
omits nothing. `--sync-core` produced no changes, confirming the pair was already
consistent before synchronisation.

`resources` is the declared projected slot (`Dataset` in full, `CoreDataset` in core);
it is absent from both records, so the projection is vacuously equal.

**Semantic review of related, non-identical representations** (the validator's
`semantic-review-required` warning is a prompt for this review, not evidence it happened):

| Full `file_collections` | Core `distributions` | Verdict |
|---|---|---|
| `urn:uuid:08cf7419-…` CHoRUS RO-Crate EHR SubRoCrate, `total_bytes: 18136671` | same id/name/description, `bytes: 18136671` | identical where representable |
| `urn:uuid:b9b41c72-…` CHoRUS RO-Crate Waveforms SubRoCrate, `total_bytes: 1201567472832` | same id/name/description, `bytes: 1201567472832` | identical where representable |

Coverage is equal (2 ↔ 2, no unmatched core distributions). `FileCollection` slots with no
`CoreDistribution` counterpart — `version`, `issued`, `collection_type`, `license`,
`download_url`, `keywords` — are correctly omitted from the projection rather than
relocated. `CoreDistribution.format`, `media_type`, `encoding`, `compression`, `path`,
`hash`, `md5`, `sha256` are left unset: the bundle reports formats only at package level
(`.ipynb`, `text/tab-separated-values`, `wfdb`) and never per sub-crate, so assigning one
would be invention. Checksums exist upstream (1,469 of 1,477 files) but no per-sub-crate
digest is given.

**Cross-scope numeric checks.** `total_file_count` (1,477) and `total_size_bytes`
(1,201,585,609,503) are full-only. The latter equals the sum of the two distribution
`bytes` values exactly, so full and core agree on size at their respective scopes.
`is_tabular: false` is schema-identical and matches in both. `distribution_formats`,
`distribution_dates`, `license`, `version`, `doi`, `issued`, and `version_access` are all
schema-identical and byte-identical across the pair; the top-level identity, version, and
access facts agree with `version_access`, `license_and_use_terms`,
`regulatory_restrictions`, and the distribution entries in both files.

**No unresolved contradictions** were found within either record or between them.

---

## Files changed

- created `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml`
- created `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml`
- created `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CHORUS_reconciliation.md`

No existing file was overwritten.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — schema validation | No issues found |
| Full — ontology term validation | Validation passed |
| Core — schema validation | No issues found |
| Core — ontology term validation | Validation passed |
| Pair consistency (`--sync-core`) | PASS, 76 schema-identical slots, no changes written |
| Pair consistency (independent re-run) | PASS, 76 schema-identical slots |
| Semantic review of `file_collections` ↔ `distributions` | Completed, 2/2 matched, no conflicts |
| Provenance audit | Clean — no prior D4D, evaluation, or withheld crate artifact used |

Line counts (informational metadata only, not a quality gate):
full 1,444 lines; core 1,089 lines.
