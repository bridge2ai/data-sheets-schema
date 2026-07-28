# CM4AI full/core reconciliation — crate-only arm

**Run label:** `2026-07-28_claude-opus-5-crateonly-denoised_rep2`
**Agent runtime:** Claude Code · **Provider:** Anthropic · **Model:** `claude-opus-5[1m]`
**Mode:** four-phase project agent, crate-only · **Temperature:** 0.0 · **Generated:** 2026-07-28

**Files**

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep2/CM4AI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep2/CM4AI_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep2/CM4AI_provenance.yaml` |

**Allowed factual input (sole):** `data/preprocessed/concatenated/CM4AI_crate_only.txt`
(release-level RO-Crate JSON-LD with file inventories collapsed, plus
`ai_ready_score.json`). No source manifest applies to this arm.

---

## Referent

**Subject of the datasheet:** the **CM4AI June 2026 Data Release (Beta)**, the entity
the crate's `ro-crate-metadata.json` names in its `about` field:
`https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`,
DOI `10.18130/V3/HIGT4C`, version 1.0, published 2026-06-30.

**Why this referent and not another.** Three candidates were available: (a) the CM4AI
*project*, (b) the June 2026 *release*, (c) the nine constituent sub-crates individually.
The crate itself settles it — the root entity, the `about` pointer, the DOI, the
release-level licence, the release-level `rai:*` responsible-AI block and the
AI-readiness self-assessment are all scoped to the release. The CM4AI project appears
only as a `isPartOf` target with no descriptive content of its own, so it cannot be
documented from this bundle. The nine sub-crates are modelled as `resources` (and their
file-level facts as `file_collections` / `distributions`) rather than as separate
referents, because each declares `isPartOf` the June 2026 release. The record's `id` is
the crate's own `@id`; the DOI is carried in `doi`.

---

## Phase 1 — Full record

Structure derived at runtime from class `Dataset` in
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` via LinkML `SchemaView`
(induced slots, ranges, cardinality, inlining, enums, `slot_usage`). No prior D4D record,
no `d4d:docExample` value, and no documentation template was consulted for structure or
for content.

**Coverage:** 56 of 94 induced `Dataset` slots populated.

One structural correction was required during validation: `issued` is enforced as
`date-time`. The crate states the release date as `2026-06-30` and the three IF-image
crate dates as `02/28/2025` — dates without times. Rather than fabricate `T00:00:00Z`,
`issued` was left empty for those four entities and the crate-stated date strings were
preserved verbatim in `distribution_dates.release_dates` and in the resource
descriptions. `issued` *is* populated for the four constituent crates whose crate values
are full timestamps.

## Phase 2 — Core record

Structure derived from class `CoreDataset` in
`data_sheets_schema_core_all.yaml`. Core was produced by schema-derived projection of the
Phase 1 full record: every slot in the induced `CoreDataset` inventory that is present in
full is copied byte-for-byte from the parsed full value, so shared-slot identity is
guaranteed by construction rather than by hand-copying. No older core record was opened,
including as a template.

**Coverage:** 52 of 79 induced `CoreDataset` slots populated.

The re-read of the crate during Phase 2 surfaced no fact that the full record had missed,
with one exception routed through Phase 3 (the IF-image contact-email split, below).
Nothing was added to core that is absent from both the full record and the crate.

## Phase 3 — Source and provenance audit

### Provenance

- Every factual input path is on the phase allowlist. The only file read for dataset
  facts was `data/preprocessed/concatenated/CM4AI_crate_only.txt`.
- **No prior generated D4D YAML was read or cited.** The withheld artifacts named in the
  task (`CM4AI_crate_d4d.yaml`, `CM4AI_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
  `ro-crate-datasheet.html`, any `ro-crate-preview.html`), the full `CM4AI_preprocessed*`
  bundles, `data/preprocessed/individual/CM4AI/`, `data/raw/CM4AI/`,
  `data/preprocessed/source_manifest.yaml`, and all other records under
  `data/d4d_concatenated/` and `data/d4d_individual/` were not opened. No live web
  content was fetched.
- Output directories were listed by **name only**, to confirm the target label was unused;
  no directory contents were read.
- Non-factual reads: the three procedural documents named in the task, the two LinkML
  schemas (structure only), and `project/jsonschema/data_sheets_schema.schema.json`
  (to determine which class-ranged slots are inlined objects versus identifier
  references — `principal_investigator`, `contact_person`, `reviewing_organization`,
  `governance_committee_contact` and `grantor` are all non-inlined string references).

### Corrections applied to the full record, then re-projected into core

1. **Marquez, C attribution.** The full record initially stated this person was "not
   present in the release-level author list". Programmatic check against the crate's
   `author` array showed the ORCID *is* listed. Corrected to: listed in the release-level
   author list and in constituent-crate citation strings, but absent from the
   release-level citation string — which is the actual discrepancy in the crate.
2. **IF-imaging contact email.** The full record attributed `emmalu@stanford.edu` to the
   Lundberg Lab collector generally. The crate records that email on the paclitaxel and
   vorinostat IF crates only; the untreated IF crate records `tideker@health.ucsd.edu`.
   Corrected to state both.
3. **Crate-internal inconsistencies recorded** as a new `anomalies` entry
   (`d4d:anomaly-metadata-quality`) rather than silently resolved — see below. A second
   detail was added to the checksum anomaly noting `evi:entitiesWithSummaryStats` is 0.

### Source disagreements found and how they were resolved

| Disagreement in the crate | Resolution |
|---|---|
| Release size given twice: `contentSize` "19.9 TB" vs `evi:totalContentSizeBytes` 21,051,331,945,400 (= 21.05 TB decimal / 19.15 TiB) | Not reconcilable from the crate. The exact byte count is recorded in `total_size_bytes`; both figures and the arithmetic are documented in `anomalies`. "19.9 TB" is close to the sum of the nine constituent `contentSize` values. |
| Licence: release-level CC BY-NC-SA 4.0 vs CC0 on the two AP-MS crates and the SEC-MS KOLF2 crate vs CC BY-NC-SA 4.0 `deed.en` on the rest | Not a contradiction — different scopes. Release licence at top level; each constituent licence on its own `resources` entry; the divergence stated explicitly in `license_and_use_terms.license_terms`. |
| Collection timeframe: release says 9/1/2022–6/1/2026; constituents say 10/13/25 or 1/31/2026 as end dates | Release-level values used for `collection_timeframes.start_date`/`end_date`; constituent end dates recorded in `timeframe_details` as narrower historical scopes, explicitly labelled. |
| Constituent-crate `citation` strings all cite the **March 2025** release (DOIs `10.18130/V3/B35XWX`, `10.18130/V3/K7TGEM`) even for crates published in 2026 | Stale and mis-scoped. Constituent `citation` values were **not** carried into `resources`. The two DOIs are recorded only in `version_access.versions_available`, labelled as references appearing in constituent-crate citation strings. |
| `isPartOf` identifiers with trailing commas; two FAIRSCAPE organization ARKs for UCSD; `10.25345` DOI written as `https://doi.org/doi:10.25345/...` | Recorded verbatim where they are values (the DOI), and documented as metadata-quality anomalies. Not silently repaired. |
| Affiliation spellings: "University of California, San Diego" (3) vs "University of California San Diego" (14); "The University of Alabama at Birmingham" (1) vs "University of Alabama at Birmingham" (1) | Normalised to the majority spelling with a single minted organization key per institution; the variants are documented in `anomalies`. "University of Alabama" (Payne-Foster) is kept distinct from UAB. |
| Ethical review contact "Vardit Ravistky" (email `@thehastingscenter.org`) vs Person record "Ravitsky, V" (affiliation University of Montreal) | Both recorded; the name spelling and the affiliation/email mismatch are stated in `ethical_reviews.review_details` and in `anomalies`. Not resolved — the crate gives no basis to choose. |

### Internal consistency within each file

Authors: 47 release-level authors (38 with ORCID + Person record, 9 name-only) are all
represented; all 38 ORCID→name→affiliation triples were verified against the crate's
Person records programmatically, with the four normalisations above as the only
differences. Nine constituent sub-crates are present in `resources`, `file_collections`
and `distributions`, matching the crate's `hasPart` `rocrate` family count of 9. All
part/output counts quoted in descriptions were checked to sum to the crate's stated
totals.

### Identifier minting

The schema requires an `id` on `Organization`, `Grantor`, `Grant` and `Software`, and the
crate supplies none. Locally minted `d4d:`-prefixed keys are used for those, and for
inlined `DatasetProperty` objects. This is stated in the file header. They assert no
external identity. All `https://fairscape.net/`, `https://orcid.org/` and
`https://doi.org/` identifiers are verbatim from the crate.

## Phase 4 — Strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` by the validator; no
hand-written field list was used.

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: deterministic matches=9, unmatched core distributions=[]

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: deterministic matches=9, unmatched core distributions=[]
```

The `--sync-core` pass made **no changes** — core was already byte-identical on every
shared slot, because Phase 2 built it by projection from the Phase 3-corrected full
record. All 76 schema-identical slots are present-in-both or absent-from-both with deeply
identical parsed values, including every narrative field. Core condenses, paraphrases,
reorders and omits nothing that full asserts on a shared slot.

### Projected slot: `resources`

Range differs (`Dataset` in full, `CoreDataset` in core). All 9 resources match by `id`
with equal coverage. Every nested value in each core resource is deeply identical to its
full counterpart; the set of full-only nested slots is **empty** — every slot used on the
sub-crate resources exists in both classes, so nothing was lost in the projection.

### Related, non-identical representations: `file_collections` ↔ `distributions`

Reviewed semantically, all 9 pairs, one-to-one by identifier, zero unmatched:

- **Names and descriptions** — identical text in both files for all 9.
- **Paths** — identical for all 9 (`AP-MS/…`, `Images/…`, `mass-spec/…`, `Perturb-Seq/…`).
- **Checksums** — 6 of 9 crates state an MD5. Those 6 appear as
  `distributions[].md5` in core, and the same hash string appears verbatim in the
  corresponding full `file_collections[].description` (`FileCollection` has no checksum
  slot). Verified string-for-string. The 3 without a crate MD5 (both AP-MS crates, SEC-MS
  KOLF2) say so explicitly in both files. No conflict.
- **Byte counts** — `distributions[].bytes` and `file_collections[].total_bytes` are both
  empty everywhere. The crate states per-crate sizes only as human strings ("441.2 GB",
  "16.7TB", "1.11 TB"); converting these would require choosing a GB/GiB convention the
  crate never states. The verbatim strings are preserved in the shared description text.
  No conflict, and no scope comparison against `total_size_bytes` is possible because the
  crate provides no distribution-level byte counts.
- **File counts** — `file_collections[].file_count` is empty and `total_file_count` is
  empty. The crate's `hasPart` counts mix files with samples, instruments, experiments and
  schemas, so none of them is a file count. The entity counts are instead recorded, clearly
  labelled as entity counts, in `instances` (`d4d:instance-provenance-graph-entities`) —
  a slot shared by both files, so both carry them identically.
- **Formats / media types / encoding / compression** — empty in `distributions` and at
  release level. The crate's `evi:formats` values (`.d`, `.d directory group`, `fastq.gz`,
  `h5`, `h5ad`, `image/jpeg`, `executable`, `unknown`, …) have no counterpart in
  `FormatEnum`, `MediaTypeEnum` or `CompressionEnum`. The full list is preserved verbatim
  in `distribution_formats`, which is a shared slot and therefore identical in both files.
  No conflict.
- **Full-only keys**: `collection_type` and `download_url` (`CoreDistribution` has
  neither). The single `download_url`
  (`ftp://massive-ftp.ucsd.edu/v10/MSV000098237/`) is **not** lost from core: the same URL
  appears in `raw_sources`, a shared slot, so both files carry it. `collection_type` is a
  full-only classification and creates no contradiction.
- **Core-only key**: `md5`, as described above.

### Other cross-checks

- `is_tabular: false` in both, consistent with the heterogeneous `evi:formats`.
- `dialect` empty in core — the crate makes no statement about tabular dialect.
- `total_size_bytes` (21,051,331,945,400) is full-only; `CoreDataset` has no equivalent
  slot. This is a known projection loss, documented here; the "19.9 TB" companion figure
  survives in core inside the shared `anomalies` narrative.
- `citation`, `relationships` and `third_party_sharing` are full-only slots. Their
  substance is not contradicted anywhere in core; the third-party repositories also appear
  in the shared `external_resources` slot.
- Top-level identity/version/access facts (`id`, `doi`, `version`, `license`, `publisher`,
  `status`, `conforms_to`) agree between the two files, with `version_access`,
  `distribution_dates` and the `resources` entries.

**No unresolved contradiction was found within either record or between them.**

---

## Primary result: D4D areas the crate could NOT support at all

38 of 94 induced `Dataset` slots are empty. Grouped by what the gap means:

**Human-subjects and consent machinery — vacuously empty.** `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `data_protection_impacts`. The crate
states there are no human subjects (`humanSubjectResearch: "None"`, an explicit exemption,
`d4d:informedConsent: "Not applicable"`, `d4d:atRiskPopulations: "None"`), so these are
correctly empty rather than unknown. The crate *does* support `human_subject_research`,
`informed_consent`, `at_risk_populations`, `is_deidentified` and `ethical_reviews` — but
only as bare determinations. It names two ethical review *contacts* and gives **no IRB or
ethics board, no protocol number, no review date, and no review outcome**.

**Preprocessing and annotation — a genuine blind spot.** `cleaning_strategies`,
`labeling_strategies`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`. The crate asserts 1,976 computation entities and 6 software
entities exist in its provenance graph, but the reduced release-level view does not
enumerate any of them. The only concrete processing facts recoverable anywhere in the
bundle are three tool names in one sub-crate's free-text description (Bruker timsTOF,
Spectronaut, R/MSstats). A consumer cannot learn from this crate how any dataset was
cleaned, labelled or imputed.

**Composition detail.** `subsets`, `splits`, `subpopulations`, `content_warnings`,
`variables`, `total_file_count`. No ML train/test/validation splits, no subpopulation
breakdown, and — most consequentially — **no variable-level metadata at all**: not one
column name, type, unit, range or missing-value code. `total_file_count` is unfillable
because every count the crate offers is an entity count, not a file count.

**Uses.** `discouraged_uses`, `other_tasks`, `future_use_impacts`, `use_repository`,
`errata`. The crate supports intended uses, prohibited uses and associated publications
well, but says nothing about uses to avoid short of the clinical-use prohibition, nothing
about downstream impacts of future use, and lists no downstream users or errata.

**Lineage and extension.** `parent_datasets`, `related_datasets`, `was_derived_from`,
`extension_mechanism`. The crate has a rich internal provenance graph but no statement of
what the release derives from, and no contribution mechanism.

**Dublin-Core housekeeping.** `created_by`, `created_on`, `last_updated_on`, `modified_by`,
`language`, `page`, `compression`, `conforms_to_class`, `conforms_to_schema`,
`download_url` (release level), `issued` (release level — date-only, see Phase 1).
Notably the release itself has **no resolvable download URL** in the crate; access is only
via the Dataverse DOI and the per-constituent repository links.

**Two vocabulary-binding gaps worth calling out.** `Instance.data_topic` and
`Instance.data_substrate` are bound by the schema to the Bridge2AI standards registry
(`values_from: B2AI_TOPIC` / `B2AI_SUBSTRATE`). The crate annotates itself richly — 7 MeSH
terms, 4 EDAM topics, 2 Cellosaurus cell lines — but **none of these are B2AI registry
terms**, so both slots are empty despite the crate being unusually well annotated. The
terms are preserved as text in the `instances` and `raw_data_sources` descriptions. This
is a vocabulary-alignment gap, not a metadata gap in the crate.

**What the crate supports unusually well**, by contrast: authorship (47 authors, 38 with
ORCID and affiliation), funding (5 funders, 10 grant numbers), licensing and copyright,
prohibited uses, biases, limitations, maintenance and retention plan, confidentiality
level and governance contact, and per-constituent distribution identity. The
Croissant `rai:*` block is doing most of that work — every one of `rai:dataLimitations`,
`rai:dataBiases`, `rai:dataUseCases`, `rai:dataReleaseMaintenancePlan`,
`rai:dataCollection`, `rai:dataCollectionType`, `rai:dataCollectionMissingData` and
`rai:dataCollectionTimeframe` mapped cleanly onto a D4D slot.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset <full>                                            # No issues found
poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  --target-class Dataset                                       # Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset <core>                                        # No issues found
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  --target-class CoreDataset                                   # Validation passed
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project CM4AI \
  --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-denoised_rep2 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

All validations were re-run after every correction. Final state: all four validations
clean, pair consistency PASS, provenance `record_mode: live`.

## Files changed

- Full record — created, then corrected in Phase 3 (three edits: Marquez attribution, IF
  contact email, added metadata-quality and summary-statistics anomalies).
- Core record — created in Phase 2 by projection, rebuilt after the Phase 3 corrections.
  Phase 4 `--sync-core` changed nothing.
- Provenance record — created after Phase 4.

## Informational metadata

| | Lines | Slots populated |
|---|---|---|
| Full | 1543 | 56 / 94 |
| Core | 1194 | 52 / 79 |

Line counts are informational only and are not a quality gate.
