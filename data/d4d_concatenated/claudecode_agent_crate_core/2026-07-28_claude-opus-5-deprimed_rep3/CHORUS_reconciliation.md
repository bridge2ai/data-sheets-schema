# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep3

- **Arm**: DE NOVO WITH CRATE (documents + RO-Crate evidence)
- **Runtime / provider / model**: Claude Code / Anthropic / `claude-opus-5[1m]`
- **Mode**: four-phase project agent, de-primed; temperature 0.0
- **Input bundle (only factual source)**: `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
- **Manifests consulted for provenance only**: `data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`
- **Full**: `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml` — 75 top-level slots, 1575 lines
- **Core**: `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml` — 65 top-level slots, 1266 lines

Line counts are informational metadata, not a quality gate.

---

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual inputs read during this run were, in full: the declared bundle above; the two manifests
(provenance metadata only — no dataset fact was taken from either); the two LinkML schema files;
and this repository's own generation/validation instructions (`.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`).

No previously generated D4D record was read, opened, grepped, or consulted. Nothing under
`data/d4d_concatenated/` was read except the two files this run wrote. No `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was read. No evaluation report,
reconciliation report, test fixture, or schema example supplied a value. Every structure emitted was
derived from class `Dataset` in `data_sheets_schema_all.yaml` and class `CoreDataset` in
`data_sheets_schema_core_all.yaml`; `d4d:docExample` annotations were treated as illustrations only.

The core file's Phase 1 input carries this run's exact version label
(`2026-07-28_claude-opus-5-deprimed_rep3`).

### Source disagreements resolved

The bundle carries document-derived and crate-derived evidence. Both were weighed on their merits;
where they disagreed, the disagreement was resolved by **scope and date**, not by preferring one
class of evidence.

| # | Disagreement | Resolution |
|---|---|---|
| 1 | Admission count: "over 45K unique admissions" as of August 2025 (Cohort 2 webinar) vs "50,000 Patient admissions from ICU, PICU, and NICU" (project website, current released dataset) vs "more than 100,000 critically ill patients" / "100,000 Patient admissions" (NIH abstract, anticipated final) | `instances[].counts = 50000` for the current released dataset; the August 2025 snapshot and the anticipated final figure are recorded in the same instance's `description` with their dates and scope stated. |
| 2 | Imaging availability: ~1,000 images with de-identification in process (webinar, Sept 2025) vs 7,642 admissions with radiology data (website) vs "No DICOM images are included" (crate `completeness`, v1.0 Beta) | Different scopes. The crate statement is about the published version 1.0 Beta package; the other two describe the enclave-resident released dataset at earlier dates. All three recorded with explicit scope on the imaging instance; the crate statement additionally recorded as a `coverage_limitation`. |
| 3 | Waveform volume: "23 Tb Waveform data" (website, current released dataset) vs `contentSize` 1.201567472832 tb (Waveforms sub-crate) | Different scopes; both recorded on the waveform instance. Top-level `total_size_bytes` is scoped to the published package, and the record's top-level `description` states that scope explicitly. |
| 4 | Contact email: `cmccrary@mgh.harvard.edu` (crate `contactEmail`) vs `cmccrary@mgh.havard.edu` (project website) | Crate form used; the website's misspelled domain is noted in the maintainer entry rather than propagated. |
| 5 | Release date form: `datePublished` 2026-04-03 (package, Waveforms sub-crate) vs `releaseDate` 03/04/2026 (package) and `datePublished` 03/04/2026 (EHR sub-crate) | Same date. The recommended citation places the release in April 2026, which fixes 03/04/2026 as day/month/year. `issued` and `distribution_dates` use the ISO form; the alternate form is documented on `distribution_dates`. |
| 6 | Recommended citation names "Harvard Dataverse", while the dataset DOI prefix `10.18130` is not Harvard's | **Not resolvable from the declared bundle.** The citation is recorded verbatim as the publisher-supplied recommended citation and the discrepancy is flagged here rather than silently corrected. The crate manifest was *not* used to resolve it — it is a provenance-only input. |
| 7 | Manlik Kwong affiliation: "Tufts University" (webinar) vs "Tufts CTSI / Tufts Medical Center" (crate author key) | Both recorded in the Creator `description`; the crate form used for the `Organization` entry. |
| 8 | `rai:dataBiases` / `rai:potentialBiases` are byte-identical, as are `rai:dataReleaseMaintenancePlan` / `rai:maintenancePlan` | Duplication, not conflict. Each recorded once. |

### Mis-scoped assertions deliberately excluded

- The **$8,000 stipend, travel allowances, mentorship, and eligibility rules** in the AIM-AHEAD
  webinar apply to *training-program trainees*, not to the patients whose data constitute the
  dataset. They are **not** recorded under `participant_compensation`, which is left absent. The
  training program itself is recorded under `existing_uses` and `external_resources`, where it
  belongs.
- `Instance.data_topic` and `Instance.data_substrate` are omitted: their ranges bind to the
  `B2AI_TOPIC` / `B2AI_SUBSTRATE` dynamic vocabularies and the bundle supplies no such CURIEs.
- Slots left absent for want of support in the bundle: `content_warnings`, `consent_revocations`,
  `collection_notifications`, `errata`, `imputation_protocols`, `annotation_analyses`, `variables`,
  `use_repository`, `other_tasks`, `parent_datasets`, `related_datasets`, `language`, `created_on`,
  `last_updated_on`, `download_url`, `compression`, `was_derived_from`, `modified_by`,
  `dialect` (core), and `CollectionTimeframe.start_date` / `end_date` (the award project period is
  recorded as text in `timeframe_details`, explicitly labelled as the award period, because the
  clinical encounter window is not stated in any source).

### Representation choices recorded

- `publisher` is set to `https://chorus4ai.org/`. The crate states the publisher as the plain name
  "B2AI CHoRUS"; the slot's range is `uriorcurie` and its own schema documentation directs against
  plain names, so the CHoRUS web identity is used. The plain name is not otherwise lost — the
  recommended citation in `citation` names the CHoRUS for Clinical Care AI Network.
- `regulatory_restrictions.confidentiality_level` is `confidential`, the most restrictive value in
  `ConfidentialityLevelEnum`. The crate's literal `HL7:2V (very restricted)` is preserved verbatim in
  `other_compliance` so no precision is lost to the enum mapping.
- Non-inlined object references (`Creator.principal_investigator`, `FundingMechanism.grantor`,
  `EthicalReview.contact_person` / `reviewing_organization`, `LicenseAndUseTerms.contact_person`,
  `ExportControlRegulatoryRestrictions.governance_committee_contact`) carry identifier strings, as
  the schema requires. The person and organization detail those objects would otherwise hold —
  names, emails, the MGB IRB postal address and telephone — is preserved in the enclosing object's
  `description` or detail lists.
- `page` is normalised to `https://chorus4ai.org/dataset/`, the form used by both sub-crates and by
  the package `license` field; the package `contentUrl` gives the same location as
  `http://chorus4ai.org/dataset`.

### Phase 2 discovery back-ported into full

Deriving `CoreDataset` exposed `distributions` (range `CoreDistribution`), the core-side counterpart
of full's `file_collections`. The bundle supports two distribution-level groupings with exact byte
counts — the EHR sub-crate (`contentSize` 18.136671 mb) and the Waveforms sub-crate (`contentSize`
1.201567472832 tb). `file_collections` was therefore **added to the full record** before core was
written, so the pair carries the same distribution-level evidence rather than stranding it in core.

This also makes `total_size_bytes` a genuine aggregation as the schema describes it:
18,136,671 + 1,201,567,472,832 = **1,201,585,609,503** bytes, consistent with the package's rounded
`contentSize` of "1.2 tb". `total_file_count` is 1,477, from the AI-readiness assessment's
"99% of files have checksums (1469/1477)"; the bundle gives no per-collection file counts, so no
per-collection cross-check is possible and `FileCollection.file_count` is left absent.

Both files were re-validated after this correction.

---

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared-slot result

Shared slots were derived at runtime from `Dataset` and `CoreDataset` by
`data_sheets_schema.d4d_pair_consistency`, not from a hand-written list.

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: ... deterministic matches=2, unmatched core distributions=[]
```

- **76 schema-identical slots**: present in both or absent from both, with deeply identical parsed
  YAML including nested mapping values and list order. Narrative fields were copied verbatim — core
  condenses, paraphrases, reorders and omits nothing.
- **11 full-only slots**, absent from `CoreDataset` and therefore carrying no consistency
  requirement: `citation`, `total_file_count`, `total_size_bytes`, `file_collections`, `subsets`,
  `splits`, `relationships`, `direct_collection`, `collection_consents`, `participant_privacy`,
  `third_party_sharing`.
- **1 core-only slot**: `distributions` (see the related-content review below).

### Projected slot: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. Both records carry the same two
sub-resources, matched by `id` with equal coverage:

| `id` | full slots | core slots |
|---|---|---|
| `d4d:CHORUS-subcrate-ehr` | id, name, description, version, issued, page, license, total_size_bytes, conforms_to | same, minus `total_size_bytes` |
| `d4d:CHORUS-subcrate-waveforms` | id, name, description, version, issued, page, license, total_size_bytes, conforms_to | same, minus `total_size_bytes` |

Every nested schema-identical slot is deeply identical. `total_size_bytes` is dropped from the core
projection because `CoreDataset` does not declare it — the only full-only nested slot, and the byte
figures survive in core through `distributions[].bytes`.

### Related-content semantic review: `file_collections` ↔ `distributions`

The validator's warning marks this mapping as requiring review; the review was performed and is
recorded here.

| Property | full `file_collections` | core `distributions` | Verdict |
|---|---|---|---|
| Coverage | 2 entries (EHR, waveforms) | 2 entries (EHR, waveforms) | Equal, matched 1:1 |
| Name | "CHoRUS electronic health record content" / "CHoRUS waveform content" | identical | Agree |
| Description | version 1.0 Beta release scope, OMOP / WFDB | identical | Agree |
| Byte count | `total_bytes` 18,136,671 / 1,201,567,472,832 | `bytes` 18,136,671 / 1,201,567,472,832 | Agree exactly |
| Path, checksums (`hash`/`md5`/`sha256`), `format`, `encoding`, `compression`, `media_type` | absent | absent | No conflict; the bundle's crate JSON has file inventories collapsed, so no file-level evidence exists |
| Release scope | version 1.0 Beta, licence "See Data Use Agreement", page `https://chorus4ai.org/dataset/`, `conforms_to` OMOP / WFDB | `CoreDistribution` declares none of these | Full-only detail, not a divergence |
| Collection type | `processed_data` | not declared by `CoreDistribution` | Full-only detail |

No contradiction. `CoreDistribution` is the narrower class; every property it declares and both
records populate agrees exactly.

### Aggregate and cross-field checks

- `total_size_bytes` (1,201,585,609,503) equals the sum of both `file_collections[].total_bytes` and
  the sum of both `distributions[].bytes`. Same represented scope — the published package.
- `total_file_count` (1,477) has no per-collection decomposition in the bundle; nothing to
  contradict.
- `is_tabular` is `false` in both, consistent with a dataset spanning DICOM imaging, WFDB and EDF+
  waveforms, and tokenized note text alongside tabular OMOP content. No `format` or `dialect` values
  are asserted anywhere, so there is nothing for them to conflict with.
- Identity, version and access facts agree across every representation in both files: `version`
  `1.0 Beta` at top level, in both `resources`, in both `file_collections`/`distributions`, and in
  `version_access.versions_available`; `doi` `10.18130/V3/XNBOPG` at top level and as
  `version_access.latest_version_doi`; `issued` `2026-04-03` at top level, on both `resources`, and
  in `distribution_dates.release_dates`; `page`/`access_urls` all resolving to
  `https://chorus4ai.org/dataset/` and the DOI.
- Licence wording differs by level — the package carries "Data Use Agreement available at
  'https://chorus4ai.org/dataset/'" and the sub-crates carry "See Data Use Agreement". Both are
  verbatim from their own crate entity and point at the same agreement. Not a contradiction.
- Historical and current statements are kept distinct rather than treated as contradictions: the
  August 2025 admission snapshot, the September 2025 imaging and EEG status, and the project-site
  "current released dataset" figures all sit in instance descriptions with their dates attached,
  while the top-level record describes the published version 1.0 Beta release.

### Commands run

```bash
# Phase 1 / Phase 3 re-validation — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 re-validation — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — synchronisation pass, then final independent check
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml \
  --core  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml \
  --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml \
  --core  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml

# Live provenance record
poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt
```

### Files changed

| File | Change |
|---|---|
| `.../claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml` | Written in Phase 1; `file_collections` back-ported in Phase 3 (see above). Unchanged by Phase 4. |
| `.../claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml` | Written in Phase 2; rewritten by the Phase 4 `--sync-core` pass, which changed formatting only — the parsed content, the 65-slot inventory, and the provenance header are unchanged. |
| `.../claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_reconciliation.md` | This report. |

### Final results

- Full: `linkml-validate` **No issues found**; `linkml-term-validator` **Validation passed**.
- Core: `linkml-validate` **No issues found**; `linkml-term-validator` **Validation passed**.
- Pair consistency: **PASS**, 76 schema-identical slots, 1 projected slot (`resources`), 1
  semantic-review warning reviewed and resolved above with no contradiction found.
- Provenance audit: **clean** — no prior-run full or core D4D, evaluation artifact, or reconciliation
  report contributed any value to either record.
- **No unresolved contradiction** exists within or between the two records. The only disagreement the
  bundle does not settle is item 6 above (citation names "Harvard Dataverse" against a non-Harvard
  DOI prefix); it is flagged rather than resolved, because resolving it would require a source
  outside the declared bundle.
