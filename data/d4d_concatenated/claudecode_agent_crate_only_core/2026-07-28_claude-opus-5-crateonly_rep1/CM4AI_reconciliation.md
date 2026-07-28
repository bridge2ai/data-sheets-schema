# CM4AI — crate-only full/core reconciliation (rep1)

| | |
|---|---|
| Run label | `2026-07-28_claude-opus-5-crateonly_rep1` |
| Arm | CRATE-ONLY — one structured upstream source |
| Agent runtime | Claude Code |
| Provider / model | Anthropic / `claude-opus-5[1m]` |
| Mode | four-phase project agent, crate-only |
| Temperature | 0.0 |
| Generated | 2026-07-28 |
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d.yaml` (1189 lines) |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d_core.yaml` (1108 lines) |
| Provenance | `.../CM4AI_provenance.yaml` (`record_mode: live`) |

Line counts are informational metadata only, never a quality gate.

## Evidence boundary actually observed

The **only** file read for dataset facts was
`data/preprocessed/concatenated/CM4AI_crate_only.txt` (3771 lines; two
artifacts — `CM4AI_crate_metadata_reduced.json`, 62 graph entities, and
`ai_ready_score.json`).

Read for **structure only**: `data_sheets_schema_all.yaml` (class `Dataset`),
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), resolved at runtime
with LinkML `SchemaView`. No `d4d:docExample` value was copied.

Not read, per the arm's restriction: `CM4AI_preprocessed.txt`,
`CM4AI_preprocessed_with_crate.txt`, anything under
`data/preprocessed/individual/CM4AI/` or `data/raw/CM4AI/`,
`data/preprocessed/source_manifest.yaml`, the withheld D4D-shaped crate
artifacts (`CM4AI_crate_d4d.yaml`, `CM4AI_crate_mapped_d4d.yaml`,
`ro-crate-linkml.yaml`, `ro-crate-datasheet.html`, any
`ro-crate-preview.html`), any prior D4D record or evaluation under
`data/d4d_concatenated/` or `data/d4d_individual/`, and any live web content.
No prior D4D content from any parent conversation was used.

## Referent chosen

**The June 2026 Data Release RO-Crate**, id
`https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`,
DOI `10.18130/V3/HIGT4C`.

Why: this is the single entity the crate's `ro-crate-metadata.json` descriptor
declares itself to be `about`, it carries the release-level `rai:*` fields, and
it is the parent of the nine component crates via `hasPart` / `isPartOf`. The
crate does describe a *project* (`project-cell-maps-for-artificial-intelligence`,
referenced from `isPartOf`) but supplies no properties for it — only an ARK. So
the record is scoped to one dated release, not to CM4AI as a programme, and the
nine component crates are carried as `resources` (and, for packaging,
`file_collections` / core `distributions`).

## Phase 3 — source and provenance audit

**Method.** Every string literal in both records was walked and matched against
the source bundle after Unicode/whitespace/JSON-escape normalisation
(423 values in full, 401 in core). Matches were verified for: the root
description, citation, all 39 keywords, all 47 author names, all 38 ORCIDs and
their crate-stated affiliations, all 9 grant numbers, every `rai:*` block, every
component crate's name / description / version / licence / DOI / URL / MD5 /
in-crate path, and all four `associatedPublication` strings. Residual
non-verbatim values were reviewed individually and are of exactly four kinds:
record-authored slot labels (`name`), schema enum values
(`representation_bias`, `raw_data`, `no_commercial_use`, …), normalised
restatements of crate text, and the three documented derivations below.

**Derivations made from crate evidence (each recorded in the record itself).**

1. `collection_timeframes.start_date` / `end_date` = `2022-09-01` / `2026-06-01`
   from the crate's `rai:dataCollectionTimeframe` `["9/1/2022", "6/1/2026"]`,
   read as US month/day/year. The crate declares no date format; a note saying
   so is carried in `timeframe_details`.
2. `known_biases[0].bias_type = representation_bias` and
   `known_limitations[*].limitation_type` are enum classifications of the
   crate's own prose (`rai:dataBiases`, `rai:dataLimitations`, `completeness`);
   the prose is preserved verbatim in the adjacent `*_description` slot.
3. `license_and_use_terms.data_use_permission = [no_commercial_use]` reads the
   declared licence identifier `CC BY-NC-SA 4.0`.

**Internal consistency checks (all pass).** `doi` ≡
`version_access.latest_version_doi` ≡ the DOI inside `citation`; `id`, `name`,
`title`, `version`, `license`, `publisher` identical in full and core; 9
`resources` ≡ 9 `file_collections` ≡ 9 core `distributions`, matched by name and
id; component licences consistent between `resources` and `file_collections`.

**Source-internal disagreements found, resolved by explicit scoping rather than
by dropping either value.**

| Conflict | Resolution |
|---|---|
| Root `contentSize` `"19.9 TB"` vs `evi:totalContentSizeBytes` `21051331945400` (≈21.05 TB decimal / 19.14 TiB) | `total_size_bytes` carries the exact byte count. The two are reconcilable only if "19.9 TB" means TiB; the crate does not say. |
| Root licence CC BY-NC-SA 4.0 vs three components licensed CC0 1.0 (both EndoTag AP-MS crates, SEC-MS KOLF2) | Both recorded: release licence at top level, component licences per resource, and both stated explicitly in `license_and_use_terms.license_terms`. |
| Root `rai:dataCollectionType` includes AP-MS; several component crates omit AP-MS from the same field | Root value used at release scope; component variance noted in `collection_timeframes`/`acquisition_methods` prose. |
| `rai:dataCollectionTimeframe` end date 6/1/2026 (root, SEC-MS KOLF2) vs 1/31/2026 vs 10/13/25 (other components) | Root value in `start_date`/`end_date`; component values enumerated in `timeframe_details`. |
| `ethicalReview` spells "Vardit Ravistky"; the `Person` entity spells "Ravitsky, V" | Person-record spelling used; the `ethicalReview` spelling quoted verbatim in `review_details`. |
| `dataGovernanceCommittee: "Jilian Parker"` vs author `Parker, J` (ORCID 0000-0003-4535-3486) | **Not** merged. The crate never links them. The name is carried as prose in `regulatory_restrictions.description`; no identifier asserted. |
| `isPartOf` targets with trailing commas (`…June-2026-data-release,`) alongside the clean ARK | Treated as the same parent; noted as a crate data-quality issue here rather than minted as separate entities. |
| SEC-MS cancer-cell `identifier` is `https://doi.org/doi:10.25345/C5348GV4S` (malformed — `doi:` inside the resolver path) | Carried verbatim in `resources[].doi`; not silently repaired. |
| Component `author` "Idkeker T" (SRA crate) vs "Ideker T" (perturb-seq crate) | Both carried verbatim in the respective resource `creators`; the typo is upstream. |

**Back-ports from Phase 2 into full:** none were required. Phase 2 was a
projection of the Phase 1 record plus `distributions`; it surfaced no fact
absent from full. Two Phase 3 corrections were applied to **full** first and
then re-projected to core: restoring "(Unpublished data)" to the verbatim AP-MS
design sentence, and replacing a summarising sentence about raw-data retention
with the crate's own wording plus an explicit statement of what the crate does
not say.

**Provenance audit result: clean.** No prior generated YAML, evaluation, or
reconciliation report was read at any phase.

*Caveat on the machine-readable provenance record:* `d4d provenance record`
unconditionally stats and hashes `data/preprocessed/source_manifest.yaml` and
writes it under `inputs.source_manifest`. That entry reflects the tool's own
behaviour, not this run — the manifest was **not** read and contributed no fact.
The bundle hash (`bundle_md5: 73f47281e790ab4f5a71c85ad6e13947`) is the only
input hash that describes this arm's evidence.

## Phase 4 — strict full/core reconciliation

Shared slots derived at runtime from `Dataset` and `CoreDataset` via
`SchemaView` — no hand-written field list.

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=9, unmatched core distributions=[]
```

Run with `--sync-core` (no changes were needed — the core generator copies
shared values verbatim from the parsed full record, so deep identity holds by
construction), then re-run without it as the independent check. Both PASS.

**Schema-identical slots:** all 48 populated core slots are byte-identical to
their full counterparts, including every narrative field. Nothing was condensed,
paraphrased, reordered, or omitted in core.

**Projected slot `resources`** (`Dataset` in full, `CoreDataset` in core): 9
resources on both sides, matched by `id`, equal coverage, zero differences
across every nested schema-identical slot; no full-only nested slot needed
omitting because every populated resource slot exists in both classes.

**Related, non-identical representation — `file_collections` ↔ `distributions`,
semantically reviewed item by item (the warning above is a prompt for this
review, not evidence that it happened):**

- 9 ↔ 9, one-to-one by component name; no unmatched entry on either side.
- `path` identical in all 9 pairs (the in-crate directory holding each
  component's `ro-crate-metadata.json`).
- No contradiction possible on size: neither side asserts a byte count, because
  the crate gives component sizes only as human-readable strings
  (`441.2 GB`, `1.11 TB`, `16.7TB`, …). Both sides carry the stated string in
  `description` and leave `total_bytes` / `bytes` unset.
- `compression` unset on both sides; the crate states no component-level
  compression.
- `format` / `media_type` / `encoding` left unset on core distributions: the
  crate's `evi:formats` (`.d`, `.d directory group`, `fastq.gz`, `h5`, `h5ad`,
  `image/jpeg`, `executable`, `unknown`, …) has almost no overlap with
  `FormatEnum`/`MediaTypeEnum`, and it is a release-wide list not attributable
  per component. The full list is preserved verbatim in
  `distribution_formats[1].description`.
- **Asymmetry, by schema design, not a conflict:** the crate supplies MD5s for
  6 of 9 components. `CoreDistribution` has `md5`; the full schema's
  `FileCollection` has no checksum slot of any kind. The 6 MD5s are therefore
  carried on the core side only. This is a full-schema representational gap, not
  a divergence between the records.
- Access URLs: `download_url` appears on 2 full file collections (MassIVE FTP,
  FigShare); `CoreDistribution` has no URL slot, so those live on the core
  `resources` side instead, where `download_url` is shared and identical.
- Release scope: `total_size_bytes` (full only) is release-wide and is not
  compared against component values, whose scopes differ and whose units are
  unstated.
- `total_file_count` unset in full — see gaps below; nothing to compare.
- `is_tabular` and `dialect` unset on both sides; the crate makes no tabularity
  claim.

**Full-only slots, absent from `CoreDataset` and therefore legitimately dropped
in projection:** `citation`, `total_size_bytes`, `relationships`,
`file_collections`.

**Result: zero unresolved contradictions within or between the two records.**

## Primary result — what one RO-Crate could NOT support

Of 94 induced `Dataset` slots, **51 populated, 43 empty**. Of 79 `CoreDataset`
slots, **48 populated, 31 empty**. The empty slots are the finding.

### A. Whole D4D areas with no crate support at all

**Preprocessing / cleaning / labelling.** `cleaning_strategies`,
`labeling_strategies`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools` — all empty. The crate proves that 1976 computations
and 6 software instances exist, but names none of them and describes no
procedure. Only two `preprocessing_strategies` entries survive, both from a
single component's free-text description ("processed using Spectronaut …
downstream analysis in R using MSstats-compatible formats").

**Composition beyond counts.** `variables`, `splits`, `subsets`,
`subpopulations`, `anomalies`, `content_warnings`, `sampling_strategies` — all
empty. There is no variable-level or field-level description anywhere in the
crate; the 20 declared schemas are counted but not exposed. No train/test/
validation split is mentioned. No sampling frame is described.

**Human-subject collection machinery.** `collection_notifications`,
`collection_consents`, `consent_revocations`, `participant_privacy`,
`participant_compensation`, `data_protection_impacts` — all empty. Defensible
here: the crate asserts no human subjects. But note the crate answers those
questions only by negation (`humanSubjectResearch: "None"`), so a "not
applicable" is recorded as prose in `informed_consent` / `at_risk_populations`
rather than as structured content.

**Uses, beyond the single `rai:dataUseCases` sentence.** `addressing_gaps`,
`other_tasks`, `future_use_impacts`, `discouraged_uses` — all empty. The crate
states prohibited uses (clinical decision-making) and intended uses, but never
articulates the gap the dataset addresses, nor discouraged-but-permitted uses,
nor the societal impact of future use.

**Maintenance detail.** `errata`, `extension_mechanism` — empty. No erratum
mechanism and no contribution/extension route is described.

**Data lineage as typed relationships.** `parent_datasets`, `related_datasets`,
`was_derived_from` — empty. The crate has `isPartOf`/`hasPart`/`sameAs` and
prior-release references buried in citation strings, but no typed
dataset-to-dataset relationship a D4D `DatasetRelationshipTypeEnum` can consume
without inference. The prior-release evidence is recorded as prose in
`version_access.version_details` instead.

**Direct-collection provenance.** `direct_collection`, `third_party_sharing` —
empty. The crate does not say whether data were obtained directly from the
source or via third parties, nor whether they are shared onward.

### B. Slots left empty because the crate's value is not expressible

- `total_file_count` — the crate counts *entities* (`evi:datasetCount` 53877,
  `evi:totalEntities` 55859), not files. Mapping either to a file count would be
  an assertion the crate does not make; the counts are instead carried as
  `instances[*].counts` with the source property named in `instance_type`.
- `total_bytes` / `bytes` per component — human-readable sizes only (see above).
- `issued` at release level — the crate's `datePublished` is `2026-06-30`, a
  date, and the slot's range is `datetime`; adding a time would fabricate
  precision. Recorded verbatim in `distribution_dates` instead. Three components
  *do* carry ISO timestamps and those populate `resources[].issued`.
- `is_tabular`, `compression`, `language`, `page`, `status`,
  `conforms_to_class`, `conforms_to_schema` — never stated at release level.
- `download_url` at release level — the crate gives no direct download endpoint
  for the release, only the DOI and the Dataverse publisher URL.

### C. Structural friction between crate and schema (worth reporting upstream)

1. **`FileCollection` has no checksum slot**, while `CoreDistribution` has
   `md5`/`sha256`/`hash`. Six crate-supplied MD5s can only be expressed on the
   core side. This asymmetry inverts the usual full ⊃ core relationship.
2. **No slot for a human-readable content size.** Nine crate-stated sizes have
   nowhere to go but prose.
3. **`FormatEnum`/`MediaTypeEnum` cover document formats only** (CSV, JSON, PDF,
   …). None of this crate's scientific formats (`fastq.gz`, `h5ad`, `.d`,
   `image/jpeg`) is representable.
4. **Object-ranged singular slots are non-inlined** (`contact_person`,
   `principal_investigator`, `grantor`, `governance_committee_contact`), so they
   accept only an identifier string. Where the crate supplies a bare name and no
   identifier (`"Jilian Parker"`), the fact is unrepresentable structurally and
   had to become prose. The same applies to `grantor`: the crate names funders
   in one free-text string with no identifiers, so `FundingMechanism.grantor`
   is left unset and the funder name carried in `FundingMechanism.name`.
5. **`Creator.credit_roles` unpopulated for all 47 creators** — the crate
   asserts authorship but no CRediT roles.

### D. What the crate supported unusually well

Provenance and governance framing: `rai:*` fields gave limitations, biases, use
cases, maintenance plan, collection method and missing-data statements directly;
`ethicalReview`, `humanSubjectExemption`, `confidentialityLevel`,
`prohibitedUses`, `copyrightNotice` and `conditionsOfAccess` populated ethics,
licensing and regulatory slots without inference; 38 ORCID-identified creators
with affiliations; 9 grant numbers across 5 funders; and a complete nine-way
component inventory with paths, versions, licences and 6 checksums. The 47-author
list, DOI, publisher and citation are all first-class.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Final status

| Check | Result |
|---|---|
| Full — schema validation | PASS |
| Full — ontology term validation | PASS |
| Core — schema validation | PASS |
| Core — ontology term validation | PASS |
| Pair consistency (`--sync-core`, then independent) | PASS / PASS — 76 schema-identical slots, projected `resources` |
| Semantic review of related content | Completed; 9/9 distribution pairs, no contradictions |
| Provenance record | Present, `record_mode: live` |
