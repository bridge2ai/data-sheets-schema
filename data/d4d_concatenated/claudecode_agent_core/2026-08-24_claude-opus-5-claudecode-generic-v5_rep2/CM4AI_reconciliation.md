# CM4AI full/core reconciliation — 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2

Runtime: Claude Code. Provider: Anthropic. Model: claude-opus-5. Reasoning effort: high
(asserted by the launcher). Mode: four-phase project agent, generic-v5 prompt. Arm:
BASELINE (input documents only).

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d_core.yaml`
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (md5 `1dfd34e5610fed7c22bea1f09c0bc60c`, 7,866 lines, 10 source documents)

## Referent

`Dataset` admits one referent. The referent chosen is **CM4AI as an ongoing quarterly data
release programme**, identified by `https://cm4ai.org/`, with the four DOI-identified
University of Virginia Dataverse deposits in the bundle enumerated as `resources`:
`doi:10.18130/V3/B35XWX` (March 2025), `doi:10.18130/V3/F3TD5R` (June 2025),
`doi:10.18130/V3/K7TGEM` (October 2025) and `doi:10.18130/V3/HIGT4C` (June 2026).

This is what the declared bundle best supports. The CM4AI data releases page states that
CM4AI "will deliver machine-readable hierarchical maps of cell architecture as AI-ready
data, together with quarterly data releases of map-input data streams", presents the June
2026 deposit as "Our latest data release" and lists the earlier ones under "Archive"; each
deposit carries its own DOI, version and file inventory but the same author list, license,
funding, governance, intended use, limitations and bias statements. Treating one deposit as
the referent would discard the other three; treating the four as separate datasets would
assert four datasets where the sources describe one release series. The choice is held
consistently across both records: the top-level identity, license, governance, ethics, use
and maintenance slots describe the programme, and release-specific facts — version, DOI,
landing page, depositor, file inventory, publication dates — sit inside the corresponding
resource.

Two consequences are recorded in the records' `source_caveats` rather than left implicit:
no source states a file count or byte total for the programme as a whole, so
`total_file_count` and `total_size_bytes` are unasserted at the top level and asserted per
release; and the reported data volume of 21.4 TB is given to three significant figures with
no stated unit base, so it is kept as prose rather than converted to an integer byte count.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs were the declared bundle, `data/preprocessed/source_manifest.yaml` (read for
the scope declaration, the canonical naming block and `source_priority` only), the two
LinkML schemas, and — in Phase 2 onward — this run's own Phase 1 full record. No prior
generated D4D record from any arm, label or date was read, opened, grepped or consulted;
nothing under `data/d4d_concatenated/` other than this run's own label was accessed, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was
accessed. No live web content was fetched.

`d4d download scope --project CM4AI` declares the referent as the CM4AI dataset with
`referent_id: https://cm4ai.org/` and `related_but_distinct: []`. The record's `id` is that
referent id, and the record does not identify itself as any dataset the project declares
distinct.

### Source disagreements resolved by the manifest ranking

`source_priority` for CM4AI, lowest tier strongest: tier 1 data resource
(`october_2025_dataverse_release`, `june_2026_dataverse_release`); tier 2 documentation and
license (`project_documentation`, `data_release_documentation`, `dataset_license`); tier 3
publication and preprint (`nature_publication`, `biorxiv_preprint`); tier 4 NIH project page
(`nih_reporter_project`); tier 5 historical data release (`march_2025_dataverse_release`,
`june_2025_dataverse_release`).

| Disagreement | Sources | Preferred | Where recorded |
|---|---|---|---|
| Release date of the current release | data releases page (tier 2): "Released on: June 17, 2025"; HIGT4C Dataverse record (tier 1): publication date 2026-06-17, files published Jun 17 2026 | tier 1, `2026-06-17` | `distribution_dates`, the June 2026 resource, `version_access.versions_available` |
| Immunofluorescence protein coverage | data releases page (tier 2): 523 proteins; K7TGEM and HIGT4C (tier 1): 464; B35XWX (tier 5): 563 | tier 1, 464 for current archives; 563 kept only as the March 2025 release's own value | image `file_collections` of each release |
| Collaborating institutions | data releases page (tier 2) includes UT Austin; B35XWX description (tier 5) omits it | tier 2, list including UT Austin (corroborated by the preprint's affiliation list) | top-level `description` |
| End of project | Dataverse maintenance plan (tier 1): November 2026; NIH RePORTER (tier 4): project end 2026-08-31 | tier 1 for the maintenance statement; the tier 4 award period is kept with the grant it belongs to | `updates.update_details`, `funders[0].grants[1].description` |
| Name of the governing body | Dataverse records (tier 1): "Data Governance Committee"; preprint (tier 3): "Data Access Committee" | tier 1 for `committee_name`; the preprint statement kept in `access_review_process` | `data_governance` |
| Affiliation of Sali A | Dataverse author lists (tier 1): UC San Diego; preprint and Nature paper (tier 3): UC San Francisco | tier 1 | `creators` |
| Perturbation scale | Dataverse (tier 1): 11,739 targeted genes in KOLF2.1J; data releases page (tier 2): ">11,000 genes" for iPSC and "200 genes" for TNBC; preprint (tier 3): 100 chromatin regulators in MDA-MB-468 as of May 2024 | only the tier 1 figure asserted as a count; no count asserted for MDA-MB-468, which no tier 1 source states | `instances`, `sampling_strategies` |

Every one of these is also stated in the top-level `source_caveats` of both records, with
what each source said and which was preferred.

### Values deliberately not asserted

- **Human-subject, consent and compensation content.** The release records state Human
  Subjects: No and De-identified Samples: Yes. `human_subject_research`,
  `is_deidentified`, `sensitive_elements` and `confidential_elements` record that
  positively; `informed_consent`, `at_risk_populations`, `participant_privacy`,
  `participant_compensation`, `direct_collection`, `collection_notifications`,
  `collection_consents` and `consent_revocations` are omitted rather than filled with
  statements that they do not apply.
- **`hipaa_compliant`.** No source in the bundle mentions HIPAA. Writing
  `not_applicable` would have been an inference, so the field is absent.
- **Collection start and end dates.** All four Dataverse records report the same
  repository Data Creation Date and Deposit Date, `2025-02-27`, including the June 2026
  release published 2026-06-17. Those are deposit fields, not measurement dates, so
  `collection_timeframes.start_date` and `end_date` are absent and the observation is
  recorded in that object's `source_caveats`.
- **Organization identifiers.** The bundle contains no ROR for any of the named
  institutions. `Organization` objects therefore carry `name` only; no registry identifier
  was supplied from model knowledge.
- **Byte sizes.** File sizes appear only as rounded human-readable strings ("3.8 GB",
  "113.3 KB"). `bytes`, `total_bytes` and `total_size_bytes` are absent; the stated sizes
  are kept verbatim in each file's `description`.
- **`credit_roles`.** No source states CRediT roles for any creator.

### Cross-record and cross-source consistency checks performed

- All 34 enumerated file names and all 34 MD5 checksums were checked to occur verbatim in
  the bundle. All 34 do.
- Per release, `sum(file_collections[].file_count)` equals the number of enumerated `File`
  objects: 6, 10, 8, 10. `total_file_count` equals that sum for B35XWX (6), K7TGEM (8) and
  HIGT4C (10). For F3TD5R `total_file_count` is 21 while 10 files are enumerated, because
  the captured page shows "1 to 10 of 21 Files"; that gap is stated in the resource's
  `source_caveats`.
- The three immunofluorescence archives in F3TD5R and K7TGEM carry identical MD5s
  (`0d972b80…`, `a98affcc…`, `ad4e68cc…`); the identically named archives in HIGT4C carry
  different MD5s (`6c1a8652…`, `6d066e6b…`, `df796327…`). Both facts are stated where the
  collections describe each other, and no duplicate MD5 occurs within any single release.
- Version numbers, DOIs, landing pages, publication dates and license agree between each
  resource, the top-level `distribution_dates`, and `version_access`.
  `version_access.latest_version_doi` (`doi:10.18130/V3/HIGT4C`) is the id of the June 2026
  resource.
- The same person is named by the same ORCID everywhere: `ORCID:0000-0003-4535-3486` in
  both `data_governance.committee_contact` and
  `regulatory_restrictions.governance_committee_contact`;
  `ORCID:0000-0002-7080-8801` and `ORCID:0000-0002-8965-8153` in `ethical_reviews`.
- Two within-document identifications were made and are stated in `source_caveats`: the
  data governance contact "Jillian Parker (jillianparker@health.ucsd.edu)" with the author
  entry "Parker J (University of California, San Diego) — ORCID
  https://orcid.org/0000-0003-4535-3486", and the two ethical review contacts with their
  author entries. Affiliation strings were normalized to one form per organization where a
  source renders one organization several ways; University of Alabama and University of
  Alabama at Birmingham are kept distinct.

### Shape findings and corrections applied

Auditing shape as well as evidence produced one systematic finding and fourteen
corrections, all applied to the full record first and then carried into core by
re-projection.

**Finding: evidence commentary was sitting in descriptive fields rather than
`source_caveats`.** Fourteen values ended in sentences of the form "No source in the bundle
states…", "No accession is given in the captured pages", "The captured page gives no
description for this file", or explained why a slot had been filled as it was. That is
commentary about the evidence, which `source_caveats` exists to hold, not content of the
field. Each was moved into the `source_caveats` of the object it belonged to
(`instances[4]`, `collection_timeframes[0]`, `cleaning_strategies[0]`, `raw_sources[1]`,
`retention_limit`, `version_access`, `is_deidentified`, three `external_resources`,
`regulatory_restrictions`, `related_datasets[2]`, and one `File` under the October 2025
release).

**Correction: the top-level `description` restated counts carried structurally by
`instances`.** The sentence listing 1,374 protein interactions, 53,788 immunofluorescent
images, 7,023 proteins and 11,739 genes duplicated four `Instance.counts` values. It was
reduced to the one figure that has no structured home, the 21.4 TB data volume.

No other shape problems were found: no prose sits in a list-ranged slot, no enum value
outside the schema's permissible values is used (both term validations pass), no commentary
is embedded inside a name, identifier or affiliation value, and `notes` is unused in both
records — narrative sits in `description` and evidence commentary in `source_caveats`.

### Identifier grounding

`data_sheets_schema.grounding.check_run` over the `uriorcurie` slots
(`data_substrate`, `data_topic`, `id`, `latest_version_doi`, `publisher`) reports
**4 grounded, 55 minted_fragment, 0 absent**. The four grounded identifiers are the release
DOIs. The 55 minted fragments are `file_collections` and `File` labels hung on the release
DOI that contains them — parts of this dataset with no referent outside the record, which is
the one case in which minting is right, and each traceable to an attested base.

Identifiers for objects that exist only in this record and belong to the programme rather
than to one release are hung on the dataset's own identifier as `https://cm4ai.org/#…`.
`d4d runs identifiers` reports every identifier in the run as an absolute IRI or a CURIE on
a declared prefix: **0 CURIEs on an undeclared prefix and 0 bare tokens**.

CURIE form was applied where the schema declares a prefix: release identifiers are written
`doi:10.18130/V3/…` rather than as doi.org URLs, and person references are written
`ORCID:0000-…` rather than as orcid.org URLs. The exempt cases were left alone: `doi` is
declared `string` with pattern `^10\.\d{4,}\/.+$` and carries the bare DOI;
`access_urls` and `download_url` are declared `uri` and carry URLs; DOIs and URLs inside
prose, citations and `versions_available` entries are text and are left exactly as written.
No identifier that names something outside this dataset was supplied from model knowledge —
in particular no ROR, since the bundle contains none.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView` by `data_sheets_schema.d4d_pair_consistency`; no hand-written field list was
used.

- **79 schema-identical slots.** Every one is present in both records or absent from both,
  and every present one has deeply identical parsed YAML content including nested mapping
  values and list order. Narrative fields are included: core condenses, paraphrases,
  reorders and omits nothing.
- **1 projected slot: `resources`** (`Dataset` in full, `CoreDataset` in core). Coverage is
  equal — the same four DOI ids in both — and every schema-identical nested slot is deeply
  identical within each matched resource.
- **2 per-record slots exempt from identity: `conforms_to_class`, `conforms_to_schema`.**
  Neither record populates them.

The core record was produced by projecting the audited full record onto the `CoreDataset`
slot inventory, so identity holds by construction rather than by later synchronization.
`--sync-core` was therefore **not** run: the final independent check passed on the first
pass, and running a synchronizer that had nothing to change would have added a write with
no effect to attest.

Slots dropped in the projection, because `CoreDataset` does not declare them: `citation`
and `third_party_sharing` at the top level, and `file_collections` and `total_file_count`
inside each resource. Nothing else was dropped, and nothing was added.

Two `CoreDataset` slots that have no `Dataset` counterpart were considered and left absent.
`distributions` would require top-level `file_collections` in the full record; this record
places file collections inside the release resources, where files actually belong, so the
top level has neither and the pair's distribution-relation check is satisfied by both being
absent. `dialect` describes a tabular format; the released data are ZIP archives of images,
mass spectrometry output, sequence data and JSON or HTML metadata, and no source describes a
tabular dialect. `is_tabular` is absent for the same reason: no source asserts it either
way.

Related, non-identical representations were reviewed for contradiction rather than only for
presence. Formats and access routes in `distribution_formats` (ZIP archives, RO-Crate JSON,
HTML datasheet and provenance graphs) agree with the file inventories inside the resources;
the release dates in the top-level `distribution_dates` agree with each resource's own
`distribution_dates`, which additionally record the staged later publication of individual
files (2025-10-22 for F3TD5R images, 2025-12-22 for two K7TGEM archives, 2026-07-15 for
HIGT4C images); historical release values are kept as the historical release's own values
rather than treated as contradicting the current ones. No unresolved contradiction remains
within or between the two records.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d_core.yaml
# grounding check over uriorcurie slots (data_sheets_schema.grounding.check_run)
# report-claims check (data_sheets_schema.report_claims.check_report)
poetry run d4d runs identifiers --method claudecode_agent --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2
poetry run d4d download scope --check --project CM4AI
poetry run d4d runs check --strict
```

### Final results

| Check | Result |
|---|---|
| `linkml-validate` full, class `Dataset` | pass |
| `linkml-term-validator` full | pass |
| `linkml-validate` core, class `CoreDataset` | pass |
| `linkml-term-validator` core | pass |
| `d4d_pair_consistency` (final, no `--sync-core`) | pass — 79 identical slots, 1 projected, 2 per-record |
| Identifier grounding | 4 grounded, 55 minted_fragment, 0 absent |
| `d4d runs identifiers` | 0 undeclared-prefix CURIEs, 0 bare tokens |

No finding from the grounding check, the report-claims check or the final pair-consistency
run required a change to either record, so there is no repair phase and this report is not a
rewrite. The fourteen shape corrections and the one description correction above were made
during Phase 3, before the pair was reconciled, and both records were re-validated after
them.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d.yaml` — created in Phase 1, corrected in Phase 3
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_d4d_core.yaml` — created in Phase 2, re-projected after the Phase 3 corrections
- `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CM4AI_reconciliation.md` — this report
