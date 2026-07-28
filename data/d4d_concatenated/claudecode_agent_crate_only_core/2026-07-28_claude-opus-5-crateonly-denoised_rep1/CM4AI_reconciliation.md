# CM4AI full/core reconciliation — crate-only (denoised) arm, rep1

**Run label:** `2026-07-28_claude-opus-5-crateonly-denoised_rep1`
**Agent runtime:** Claude Code · **Provider:** Anthropic · **Model:** `claude-opus-5[1m]`
**Mode:** four-phase project agent, crate-only · **Temperature:** 0.0 · **Generated:** 2026-07-28

**Files**

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_provenance.yaml` |

**Sole factual input:** `data/preprocessed/concatenated/CM4AI_crate_only.txt`
(2,208 lines; `CM4AI_crate_metadata_reduced.json` + `ai_ready_score.json`).
Structure was derived only from `data_sheets_schema_all.yaml` (class `Dataset`) and
`data_sheets_schema_core_all.yaml` (class `CoreDataset`).

---

## Referent chosen

**The root RO-Crate entity of the CM4AI June 2026 Data Release (Beta)** —
`https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`,
DOI `https://doi.org/10.18130/V3/HIGT4C`, version 1.0, published 2026-06-30.

The crate itself makes this choice unambiguous. `ro-crate-metadata.json` declares
`about` → that ARK, and the ARK carries the release name, DOI, version, licence,
publisher, and the release-wide `rai:*` fields. The nine other `EVI#ROCrate` entities
in the graph all declare `isPartOf` the same ARK, so they are components rather than
alternative referents. They are recorded under `resources` (and, for their packaged
form, under `file_collections` / `distributions`) rather than as separate datasheets.

The referent is a *data release*, not the CM4AI project — nothing in the crate
describes the project independently of this release.

---

## Phase 3 — Source and provenance audit

### Provenance boundary

- Read for facts: `CM4AI_crate_only.txt` only.
- Read for structure: `data_sheets_schema_all.yaml`, `data_sheets_schema_core_all.yaml`
  (traversed with `SchemaView`, not by eye).
- **Not read:** `CM4AI_preprocessed.txt`, `CM4AI_preprocessed_with_crate.txt`,
  `data/preprocessed/individual/CM4AI/`, `data/raw/CM4AI/`, `source_manifest.yaml`,
  `CM4AI_crate_d4d.yaml`, `CM4AI_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
  `ro-crate-datasheet.html`, any `ro-crate-preview.html`, any other directory under
  `data/d4d_concatenated/` or `data/d4d_individual/`, any evaluation or reconciliation
  report, and live web content. No prior D4D record was opened or cited.
- One disclosure about the provenance tool: `d4d provenance record` independently
  stats and md5s `data/preprocessed/source_manifest.yaml` when writing its record. That
  file is on this arm's forbidden list and was **never opened by the generation
  process**; no value in either datasheet derives from it. Its hash appears in
  `CM4AI_provenance.yaml` as a tool-side artefact only.
- One incidental note: the session scratchpad is shared across concurrently running
  agents, and a schema-dump helper script written there was overwritten by another
  agent mid-run. Both schema dumps were regenerated under run-unique filenames
  (`dn1rep1_*`) and re-verified before use. No dataset facts were involved.

### Internal contradictions found in the crate

These are recorded in the datasheet rather than silently resolved.

1. **Stale citation strings on every component.** The root entity's `citation` names
   the *June 2026* release with DOI `10.18130/V3/HIGT4C`. All nine component crates
   carry a `citation` naming the *"March 2025 Data Release (Beta)"* with DOI
   `10.18130/V3/B35XWX` or `10.18130/V3/K7TGEM`. Recorded verbatim per component and
   flagged in `version_access.version_details`.
2. **Two disagreeing size statements.** Root `contentSize` = `"19.9 TB"`;
   `evi:totalContentSizeBytes` = `21051331945400` (≈21.05 TB decimal, ≈19.15 TiB
   binary). Neither reading reproduces "19.9 TB" exactly. The byte count is used for
   `total_size_bytes`; both statements and the arithmetic are recorded under
   `distribution_formats` → "Declared release size".
3. **Malformed component identifiers.** Several `isPartOf` ARKs end with a trailing
   comma (e.g. `...June-2026-data-release,`), and every component lists both the
   comma'd and clean forms of the June 2026 ARK. Flagged in `version_access`.
4. **Licence divergence between root and components.** Root is CC BY-NC-SA 4.0; the
   two EndoTag AP-MS crates and the SEC-MS KOLF2 differentiation crate are **CC0 1.0**;
   the rest use the CC BY-NC-SA 4.0 `deed.en` URL. Per-component licences are recorded
   on each resource, and the divergence is stated in the root
   `license_and_use_terms.description`.
5. **Entity counts do not sum.** `evi:datasetCount` 53877 + `computationCount` 1976 +
   `softwareCount` 6 + `schemaCount` 20 = 55879, against `evi:totalEntities` 55859.
   Because of this, **no `total_file_count` is asserted** — see gaps below.
6. **Divergent collection end dates.** Root `rai:dataCollectionTimeframe` ends
   `6/1/2026`; components end `1/31/2026` or `10/13/25`. Recorded per component; the
   root value is used at release level and the divergence noted in
   `collection_timeframes.timeframe_details`.
7. **Name-spelling variants preserved verbatim**, not corrected: `"Vardit Ravistky"`
   (vs. author-list `Ravitsky, V`), `"Ballllosero Navarro"` / `"Ballllosera Navarro"`,
   `"Idkeker T"` in the SRA component author string, and `"cardiomycyte"` in the
   SEC-MS description.

### Interpretive steps taken (disclosed, not hidden)

- **Within-crate person identity resolution.** `principalInvestigator: "Trey Ideker"`,
  `contactEmail: tideker@health.ucsd.edu`, `ethicalReview: "Vardit Ravistky …"`, and
  `dataGovernanceCommittee: "Jilian Parker"` are free text. Each was matched to the
  crate's own ORCID-bearing `Person` records (`Ideker, T` 0000-0002-1708-8454;
  `Ravitsky, V` 0000-0002-7080-8801; `Bélisle-Pipon, JC` 0000-0002-8965-8153;
  `Parker, J` 0000-0003-4535-3486). The matches are surname + initial within a single
  document; each is stated in the surrounding `description`.
- **No organization inferred from an email domain.** `ravitskyv@thehastingscenter.org`
  conflicts with that person's crate affiliation (University of Montreal), so
  `ethical_reviews[].reviewing_organization` is left empty for both ethics contacts.
- **Enum encodings.** `bias_type: representation_bias`, four `limitation_type` values,
  `collection_type` (`raw_data`/`processed_data`, set only where the crate's own words
  say "raw"/"aggregated"), `data_use_permission: no_commercial_use` (from the
  `by-nc-sa` licence URI), and `confidentiality_level: unrestricted` (from
  `confidentialityLevel: "Unrestricted"`). These are encodings of stated facts into
  schema-required vocabularies, not new claims.
- **Date normalisation.** `rai:dataCollectionTimeframe` values (`9/1/2022`, `6/1/2026`,
  `1/31/2026`, `10/13/25`) were normalised to ISO for the `date`-ranged `start_date` /
  `end_date`; the literal crate strings are preserved in `timeframe_details`. The
  non-ISO `datePublished: "02/28/2025"` on the three IF crates was **not** normalised —
  it is kept verbatim in `distribution_dates.release_dates`, and `issued` is left empty
  for those components. Root `datePublished: "2026-06-30"` is date-only and fails the
  `date-time` range of `issued`, so it too lives in `distribution_dates` and `issued` is
  empty release-wide.
- **Ontology-term placement.** The two Cellosaurus terms are carried on `Instance.
  data_substrate`; three topic terms (EDAM `topic_3170`, `topic_0121`, MeSH `D005453`)
  are carried on `Instance.data_topic` for the matching modality. The assignment of a
  topic to a modality is mine; the terms are the crate's.

### Facts deliberately **not** asserted

- `total_file_count` — `evi:totalEntities` counts entities (including computations,
  software and schemas), not files. `ai_ready_score.json` loosely calls them "files"
  ("0% of files have checksums (8/55859)"), but the counts do not reconcile (see 5
  above). The counts are recorded as `instances` with exact labels instead.
- `addressing_gaps` — the crate states goals and use cases but never an unmet need.
- `acquisition_methods` booleans (`was_directly_observed` etc.) — the crate names the
  assays but never characterises acquisition in those terms.
- `hipaa_compliant` — plausible as `not_applicable` given no human subjects, but the
  crate makes no determination.
- Sub-crate `contentSize` strings (`441.2 GB`, `16.7TB`, …) as `total_bytes` / `bytes` —
  unit ambiguity makes byte conversion an invention. Kept verbatim in descriptions.

### Corrections applied during Phase 3

Three source-supported items surfaced on the Phase 2/3 re-read of the bundle and were
back-ported into the **full** record first, then re-projected into core:

1. `conforms_to_schema` — schema.org + Croissant RAI + EVI, from
   `ai_ready_score.json` `interoperable` / `semantics`.
2. The two disagreeing size statements (item 2 above), as a `distribution_formats` entry.
3. The root `isPartOf` FAIRSCAPE organization and project ARKs, added to the leadership
   `Creator.description` (the crate does not include those records' contents).

A fourth change was structural, not factual: the schema declares
`principal_investigator`, `contact_person`, `grantor` and `governance_committee_contact`
as **non-inlined** single-valued references, so they must be id strings. Inline `Person`
objects were replaced by ORCID URIs (or `mailto:emmalu@stanford.edu` where the crate
gives only an email), and the names/emails they carried were moved into the adjacent
`description` / `review_details` text so no fact was lost.

No fact in either record originates anywhere but the crate bundle.

---

## Phase 4 — Strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView` from `Dataset` and `CoreDataset`
— no hand-written field list.

| Measure | Value |
|---|---|
| `Dataset` induced slots | 94 |
| `CoreDataset` induced slots | 79 |
| Schema-identical shared slots | 77 (76 + `resources`, which is a projection) |
| Shared slots populated | 50 |
| Full-only slots populated | 5 — `citation`, `file_collections`, `relationships`, `third_party_sharing`, `total_size_bytes` |
| Core-only slots | `dialect` (empty — crate gives no dialect), `distributions` (projection of `file_collections`) |
| Deep-identity mismatches across the 76 identical slots | **0** |
| Slots present in core but absent from full | **0** |

**`resources` projection.** 9 resources in full, 9 in core, matched by `id`, equal
coverage. Every nested slot that exists in `CoreDataset` is deeply identical. The only
full-only nested slot omitted from the core projection is `citation` (9 × 1), which
`CoreDataset` does not declare.

**`file_collections` ↔ `distributions` semantic review** (the validator's
`semantic-review-required` warning — reviewed here, not merely acknowledged). 9 ↔ 9,
matched by `id`, no unmatched core distributions.

| Component | path | name/description identical | md5 in core |
|---|---|---|---|
| AP-MS paclitaxel | `AP-MS/apms-paclitaxel-rocrate/` | yes | — (none declared) |
| AP-MS vorinostat | `AP-MS/apms-vorinostat-rocrate/` | yes | — (none declared) |
| Paclitaxel IF | `Images/paclitaxel/` | yes | `9422486c…` |
| Untreated IF | `Images/untreated/` | yes | `0b4d129f…` |
| Vorinostat IF | `Images/vorinostat/` | yes | `ac577109…` |
| SEC-MS KOLF2 | `mass-spec/iPSCs/` | yes | — (none declared) |
| Treated SEC-MS | `mass-spec/cancer-cells/` | yes | `cb67e774…` |
| Perturb-seq SRA | `Perturb-Seq/sra/` | yes | `cbdb263b…` |
| Perturb-seq atlas | `Perturb-Seq/cell-atlas/` | yes | `1cafefa3…` |

`FileCollection` has no checksum slot while `CoreDistribution` has `md5`, so the six
crate-declared MD5s are structurally expressible only in core. To keep full canonical,
each MD5 is **also** stated in the corresponding `file_collections[].description`, and
those descriptions are byte-identical in both files. No fact therefore exists only in
core. Formats, compression, encoding, media types and byte counts are absent from both
sides because the crate declares none per component (only a release-wide `evi:formats`
list and unit-ambiguous `contentSize` strings). No conflict was found.

**Cross-record consistency of repeated facts.** DOI, version, licence, publisher,
confidentiality level, PI, contact email, collection timeframe, maintenance plan and
prohibited-use statement each appear in several places; all repetitions agree within
each file and between the two files. Historical values (earlier-release ARKs, March 2025
citations) are marked as historical in `version_access` rather than merged with current
values.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-denoised_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Results

| Check | Result |
|---|---|
| Full — LinkML schema (`Dataset`) | PASS |
| Full — ontology term validation | PASS |
| Core — LinkML schema (`CoreDataset`) | PASS |
| Core — ontology term validation | PASS |
| Pair consistency (`--sync-core`) | PASS — 76 schema-identical slots, projected `resources` |
| Pair consistency (final, independent) | PASS — 76 schema-identical slots, projected `resources`; 1 semantic-review warning, reviewed above |
| Provenance record | present, `record_mode: live` |

Line counts (informational metadata only, not a quality gate): full 2,265; core 1,783.

`--sync-core` made no factual change; it reformatted the core YAML (1,808 → 1,783 lines)
and left the header comments and all values intact. Nothing diverged between the two
records at any point.

---

## PRIMARY RESULT — what one RO-Crate could not support

**Full record: 55 of 94 `Dataset` slots populated (39 empty).
Core record: 51 of 79 `CoreDataset` slots populated (28 empty).**

### A. D4D areas the crate supports with no gaps

Identity and versioning; licensing, copyright and conditions of access; funding
(5 grantors, 9 grant numbers); authorship (47 authors, 41 with ORCID, 11 institutions);
release-level purposes, intended uses and prohibited uses; known biases and limitations;
maintenance and preservation plan; confidentiality and de-identification status; human
subjects status and exemption; ethics contacts; provenance/packaging structure
(9 components, EVI graph, RO-Crate 1.2 + FAIRSCAPE 1.1.3, Croissant RAI).

### B. Areas the crate supports only thinly

| Area | What the crate gives | What is missing |
|---|---|---|
| Collection methodology | assay names + a bioRxiv DOI | the protocol itself is delegated to an external preprint; the crate says "additional data collection details will be subsequently published once finalized" |
| Ethical review | two named contacts + an exemption sentence | no IRB/board name, protocol number, review date, or determination document |
| Preprocessing | Spectronaut/timsTOF/R-MSstats for SEC-MS; one named computation for the atlas; `evi:computationCount` 1976 | no parameters, versions or steps for 1975 of the 1976 computations; the 6 software records are collapsed out |
| Integrity | 6 component MD5s | `evi:entitiesWithChecksums` = 8 of 55,859 — the crate's own score reports 0% checksum coverage |
| Distribution formats | one release-wide `evi:formats` list | no format, media type, encoding or compression per component |
| Sizes | `contentSize` strings | no exact byte counts per component; the two release-level size statements disagree (Phase 3, item 2) |
| Subject annotation | 13 `about` terms (7 MeSH, 4 EDAM, 2 Cellosaurus) | 8 of the 13 have no D4D home at all — see D below |

### C. D4D areas the crate could **not** support at all

Empty in **both** records (crate silent):

- **Composition detail** — `addressing_gaps`, `anomalies`, `content_warnings`,
  `subpopulations`, `is_tabular`, `compression`.
- **Preprocessing/labelling chain** — `cleaning_strategies`, `labeling_strategies`,
  `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`.
- **Downstream use tracking** — `use_repository`, `other_tasks`, `discouraged_uses`.
- **Maintenance operations** — `errata`, `extension_mechanism` (no contribution route,
  no erratum channel, no statement of how updates reach users).
- **Data protection** — `data_protection_impacts` (no DPIA or equivalent).
- **Dublin-Core-style bookkeeping** — `created_by`, `created_on`, `last_updated_on`,
  `modified_by`, `issued`, `language`, `page`, `was_derived_from`, `conforms_to_class`,
  `download_url` at release level.
- **Core-only** — `dialect`.

Empty in full and **not expressible in core at all** (full-only slots the crate also
leaves empty): `total_file_count`, `subsets`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `variables`, `parent_datasets`,
`related_datasets`.

Two clusters deserve separate mention:

- **The human-subjects consent cluster is empty by design, not by omission.** The crate
  states there are no human subjects, so `collection_consents`,
  `consent_revocations`, `collection_notifications`, `direct_collection`,
  `participant_privacy` and `participant_compensation` have nothing to record. This is a
  *correct* empty, unlike the rows above.
- **`variables` is empty despite the crate claiming 20 schemas.** `evi:schemaCount` = 20
  and one schema entity is named
  (`schema-kolf-pan-genome-aggregate-20250529-143000`), but no field definitions are
  present, so not one variable could be described. This is the single largest gap
  relative to what the crate *asserts* it contains.

### D. A schema finding, not a crate finding

The crate carries 13 `about` ontology annotations for the dataset as a whole, but
**`Dataset` has no multivalued subject/topic slot**. The only ontology-valued slots are
`Instance.data_topic` and `Instance.data_substrate`, which force a per-instance
attribution. Five terms were placed that way; the remaining eight — MeSH `D001943`
(Breast Neoplasms), `D057026` (Induced Pluripotent Stem Cells), `D064113` (CRISPR-Cas
Systems), `D013058` (Mass Spectrometry), `D017239` (Paclitaxel), `D000077337`
(Vorinostat), and EDAM `topic_3320` (Functional genomics), `topic_3474` (Machine
learning) — survive only as keyword strings. Structured subject annotation is available
in the source and is lost in translation to D4D.

### E. Overall read

An RO-Crate of this quality carries the *administrative* half of a datasheet almost
completely — who, what, when, licence, funding, ethics posture, packaging, provenance
topology — and it carries it in machine-readable form with stable identifiers. What it
does not carry is the *methodological* half: how the data were actually produced, how
they were cleaned and labelled, what the variables mean, and what is known about
downstream use. Those sections are either delegated to an external publication or simply
absent. The 39 empty slots in the full record are concentrated almost entirely in that
methodological half.
