# CM4AI full/core reconciliation

- **Run label:** `2026-08-07_claude-opus-5-claudecode-generic-v3_rep3`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Agent runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Reasoning effort:** high (`$CLAUDE_EFFORT`, read at run time)
- **Temperature:** 0.0
- **Declared input bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the CM4AI data release
programme** — the ongoing quarterly series of CM4AI Data Releases published in
LibraData, the University of Virginia's Dataverse instance — with the individual
releases enumerated under `resources`.

The bundle supports this choice over any single release. It contains the project
website (`cm4ai.org`), the data releases page (`cm4ai.org/data-releases/`), the CM4AI
preprint, the NIH RePORTER project record, the CC BY-NC-SA 4.0 licence deed, and
**four separate Dataverse release landing pages with four distinct DOIs**
(10.18130/V3/B35XWX, F3TD5R, K7TGEM, HIGT4C), plus a fifth release DOI
(10.18130/V3/DXWOS5) cited in the preprint. The releases page frames the deliverable
as maps "together with quarterly data releases of map-input data streams". Pinning
the referent to any one release would have discarded the evidence carried by the
other four; pinning it to the programme keeps all five and preserves their distinct
identities as `resources`. The choice is held consistently in both records.

### Entity kept distinct rather than merged

The bundle also contains a Nature research article — Schaffer et al., *Multimodal
cell maps as a foundation for structural and functional genomics*, Nature 642,
222–231 (2025), doi:10.1038/s41586-025-08878-3 — which is by page count the largest
single document in the bundle (roughly 2,870 of 7,873 lines). It describes a
multimodal cell map of **U2OS osteosarcoma cells**, and it is **not** part of the
CM4AI release programme:

- different cell line (U2OS, not MDA-MB-468 or KOLF2.1J);
- distributed through NDEx (uuid f693137a-d2d7-11ef-8e41-005056ae3c32), MassIVE
  (MSV000097168), ProteomeXchange (PXD052362), the Human Protein Atlas v23 release,
  the EBI Complex Portal and ModelArchive — none of which is a CM4AI Dataverse
  release;
- none of the four CM4AI release records lists it among their contents, and every
  one of them names the CM4AI preprint (and, for two, the Nourreddine et al.
  perturbation-atlas preprint) as its Related Publication, not this article;
- its funding acknowledgement names "the Bridge2AI Program (NIH Common Fund;
  OT2 OD032742)" among roughly a dozen other funders, and several authors overlap
  with CM4AI.

Under the rule "do not merge distinct entities into a single claim", its
composition figures (5,147 proteins, 275 assemblies, 36,842 interactions, 20,660
images, 772 paediatric tumours), its funders, its access points and its methods
detail were **not** folded into this record. The decision and its basis are stated
in the top-level `source_caveats` of both files. Nothing from that article was used
as evidence for a CM4AI release fact.

## Phase 1 — full generation

Structure was derived at run time from class `Dataset` in
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` using LinkML
`SchemaView` (`class_induced_slots`, recursively through every class-ranged slot),
not from any prior record. No `d4d:docExample` value was copied.

Result: **55 populated top-level slots**, 5 `resources`, 4 `file_collections`
enumerating **34 files** with their exact MD5 checksums.

## Phase 2 — core generation

Core structure was derived from class `CoreDataset` in
`data_sheets_schema_core_all.yaml` by the same mechanical route. The schemas share
**79 slots**, of which **78 are schema-identical** and **1 (`resources`) is a
projection** (`Dataset` in full, `CoreDataset` in core).

- All 78 schema-identical slots present in full were carried into core with deeply
  identical parsed values — no condensing, paraphrasing or reordering.
- The three populated full-only slots — `citation`, `direct_collection`,
  `third_party_sharing` — were dropped, because `CoreDataset` does not declare them.
- The core-only slot `distributions` was populated by projecting the full record's
  nested `file_collections` (see below). The other core-only slot, `dialect`, was
  left empty: the bundle states nothing about delimiters, quoting or headers.
- Consulting the source documents for core fields the full record left empty
  produced **no new facts**: `CoreDataset` adds no evidential slot beyond `dialect`
  and `distributions`, so there was nothing for Phase 2 to back-port into full.

Result: **52 populated top-level slots**, 5 `resources`, **34 `distributions`**.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior D4D record was read, opened, grepped or consulted. The only files read for
facts were `data/preprocessed/concatenated/CM4AI_preprocessed.txt` and
`data/preprocessed/source_manifest.yaml`; the only files read for structure were the
two schema files and `src/data_sheets_schema/d4d_pair_consistency.py`. Nothing under
`data/d4d_concatenated/` other than this run's own two outputs was opened, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was
touched. The directory listing of `data/d4d_concatenated/claudecode_agent/` was seen
once while creating the output directory; no file inside it was read. No prior D4D
content was present in the launching message.

### Mechanical re-verification against the bundle

Every transcribed identifier was checked programmatically for verbatim presence in
the declared bundle:

| class of value | count checked | not found |
|---|---|---|
| `md5` checksums | 34 | 0 |
| `doi` values | 5 | 0 |
| file names (`.zip`/`.json`/`.html`) | 34 | 0 |
| per-file publication dates and download counts | 34 + 34 | 0 |
| ORCIDs, emails, grant numbers, award figures, counts, dates | 24 | 0 |

202 quoted spans were extracted and matched against the whitespace-normalised
bundle. One genuine defect was found and fixed:

- **Fixed:** the SEC-MS quotation in `collection_mechanisms[1].mechanism_details`
  began `"We have performed SEC-MS on MDA-MB-468 cells..."`; the source reads
  `"In addition, we have performed SEC-MS on MDA-MB-468 cells..."`. Corrected in the
  full record and propagated to core.

All other non-matches were artefacts of the checker (spans caught between two
adjacent quotations, typographic vs. ASCII apostrophes, and inline citation-marker
digits that the PDF-to-text conversion leaves inside preprint sentences). The
quotation convention — reference-marker digits removed, typographic characters
ASCII-ised, no other alteration — is stated in the top-level `source_caveats`.

### Source disagreements represented rather than resolved

Each of these is carried in both records with both readings stated:

1. **Current release date.** The data releases page heads the current release
   "June 2026 Data Release (Beta)" but shows "Released on: June 17, 2025"; the
   Dataverse record for the same DOI gives Publication Date 2026-06-17. Recorded in
   `resources[HIGT4C].source_caveats` and `distribution_dates[0].source_caveats`.
2. **Collaborating institutions.** Four different lists appear (releases page with
   UT Austin; Dataverse descriptions without it; preprint affiliations adding the
   University of Alabama and the University of Montreal; Dataverse author
   affiliations adding KTH). The union is listed in `creators[0].affiliations`, with
   the variation documented in `creators[0].source_caveats`.
3. **Project end date.** NIH RePORTER: 2026-08-31. Release maintenance plan: "the
   end of the project in November 2026". Both in
   `collection_timeframes[0].timeframe_details` and `updates.source_caveats`.
4. **Version numbering.** Every release displays a version number that disagrees
   with the version in its own data citation (1.4/V1, 2.1/V2, 2.1/V2, 2.0/V2).
   Displayed values populate `version`; the disagreement is in
   `version_access.source_caveats` and in each resource's `source_caveats`.
5. **Data creation date.** All four releases, including the June 2026 one, repeat
   Data Creation Date and Deposit Date 2025-02-27. Recorded as stated in a separate
   `CollectionTimeframe` with an explicit caveat that it cannot be read as the
   collection date of the later content, rather than being silently corrected or
   converted into `start_date`/`end_date`.
6. **Protein counts for the IF images.** 563 per condition (March 2025), 464 per
   condition (June 2025 onward), 523 in the flagship-dataset summary. All three are
   recorded; the sources do not reconcile them.
7. **Ethics contact affiliation.** Ravitsky's Dataverse affiliation is the
   University of Montreal while the ethical-review email is at
   thehastingscenter.org. Both stated, neither chosen.

### Data anomalies found in the sources and recorded

- The three MDA-MB-468 immunofluorescence archives appear in the June 2025, October
  2025 and June 2026 releases with **identical file names and identical displayed
  sizes but different MD5 checksums in the June 2026 release**
  (`0d972b80…`/`a98affcc…`/`ad4e68cc…` versus `6c1a8652…`/`6d066e6b…`/`df796327…`).
  The bundle does not explain the change. Recorded in `anomalies[1]`.
- The June 2025 release describes itself as a revision correcting RO-Crate metadata
  and naming conventions, and its page carries `Info – The "DRAFT" version was not
  found. This is version "2.1".` Recorded in `anomalies[0]` and `errata[0]`.
- The June 2025 untreated-image description reads "MDA-MB-468 treated as imaged by",
  omitting the treatment name its siblings carry. Recorded in that file's
  `source_caveats`.

### Deliberate omissions (prefer omission over inference)

- `total_size_bytes` (Dataset) and `bytes` (every File): cm4ai.org reports "21.4 TB"
  and Dataverse displays rounded sizes ("3.8 GB", "31.1 KB"), but no source states
  whether these are decimal or binary units. Converting would fabricate precision;
  the displayed strings are recorded in the corresponding descriptions instead, and
  the omission is explained in the top-level `source_caveats`.
- `total_file_count` at programme level: no source states a programme total. Set
  per release (6, 21, 8, 10) where the files table states it.
- `related_datasets`: no enum value in `DatasetRelationshipTypeEnum` matches the
  actual relation between the release programme and the Nature U2OS dataset ("a
  separate dataset by overlapping investigators under a shared award"), and the
  sources assert no relation. Omitted, with the reasoning in `source_caveats`.
- `confidential_elements`, `subpopulations`, `sensitive_elements`,
  `informed_consent`, `at_risk_populations`, `participant_privacy`,
  `participant_compensation`, `collection_notifications`, `collection_consents`,
  `consent_revocations`, `retention_limit`, `extension_mechanism`, `variables`,
  `imputation_protocols`, `annotation_analyses`, `labeling_strategies`,
  `use_repository`, `splits`, `is_tabular`, `language`, top-level `compression`:
  the bundle supports none of these for this referent.
- No `Software` object for the MuSIC / Tools pipeline: the CM4AI sources state its
  licence (BSD-3) and hosting (GitHub / Zenodo) but give no URL, and `Software.id`
  is required. The only CM4AI-stated software URLs — FAIRSCAPE and IMP — do carry
  `Software` objects. Using the `github.com/idekerlab/cellmaps_pipeline` URL from
  the Nature article would have attributed that article's toolkit to CM4AI.

### Shape and slot-filling corrections applied in Phase 3

- Four `Person`-ranged slots (`principal_investigator`, two `contact_person`,
  `governance_committee_contact`) were initially written as inlined objects. The
  schema does not inline them, so they were rewritten as identifier references
  (ORCID URIs and one `mailto:` URI) and the person's name, email and affiliation
  moved into the enclosing object's `description` / `review_details`, with the
  reference convention noted in `source_caveats`. Both records re-validated after
  the change.
- `distribution_formats[0].format` held a prose list ("ZIP archives, JSON RO-Crate
  metadata and HTML provenance graphs and datasheets") in a scalar slot; reduced to
  `ZIP, JSON, HTML`, with the detail already present in `description`.
- Three resource-level `notes` values held narrative that belongs in `description`
  (release naming conventions, archive status, current-release status); folded into
  the respective `description` values. The one remaining `notes` value, at top
  level, describes the producing project's pillar/module organisation, which is not
  a description of the dataset.
- Evidence commentary is confined to `source_caveats` throughout; no sibling slot's
  value is restated in `notes`.

### Post-audit re-validation

Both files were re-validated after every correction; the results below are from the
final state.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time with LinkML `SchemaView`, not from a
hand-written list:

- **79 shared slots** between `Dataset` and `CoreDataset`
- **78 schema-identical** (equal range, multivalued, required, cardinality and
  `inlined_as_list`) — all required to be present in both or neither, with deeply
  identical parsed YAML including nested mapping values and list order
- **1 projected**: `resources` (`Dataset` → `CoreDataset`)
- **17 full-only** slots, of which 3 were populated and correctly absent from core:
  `citation`, `direct_collection`, `third_party_sharing`
- **2 core-only** slots: `distributions` (populated by projection), `dialect`
  (unpopulated — no evidence)

### `resources` projection

Five resources, matched by `id`, with equal coverage in both records:

| `id` | release | version | files |
|---|---|---|---|
| `https://doi.org/10.18130/V3/DXWOS5` | Data Release (V1, preprint citation) | V1 | not captured |
| `https://doi.org/10.18130/V3/B35XWX` | March 2025 (Beta) | 1.4 | 6 |
| `https://doi.org/10.18130/V3/F3TD5R` | June 2025 (Beta) | 2.1 | 21 (10 enumerated) |
| `https://doi.org/10.18130/V3/K7TGEM` | October 2025 (Beta) | 2.1 | 8 |
| `https://doi.org/10.18130/V3/HIGT4C` | June 2026 (Beta), current | 2.0 | 10 |

Every schema-identical slot inside each projected resource is deeply identical
between full and core. The full-only nested slots `file_collections` and
`total_file_count` are omitted from the core projection, as the schema requires.

### Related-content semantic review (`file_collections` → `distributions`)

The full record carries `file_collections` only inside the release resources (there
is no programme-level file collection, because the bundle states none). Each `File`
was mapped to one `CoreDistribution`, restricted to the slots `CoreDistribution`
declares: `id`, `name`, `description`, `path`, `format`, `media_type`,
`compression`, `md5`, `source_caveats`. **34 files → 34 distributions**, matching
one-to-one across all four enumerated releases (6 + 10 + 8 + 10).

Reviewed for conflict, with none found:

- **Names, paths, formats, media types, compression, checksums:** identical in both
  representations, value by value.
- **`file_type`** (`data_file`/`metadata_file`/`archive_file`/`documentation_file`)
  has no `CoreDistribution` counterpart and is dropped in the projection; it adds no
  fact absent elsewhere, since every dropped value is recoverable from the file's
  `format` and name.
- **`FileCollection`-level `name`, `description` and `file_count`** have no
  counterpart in the flat `distributions` list. `file_count` is preserved at the
  resource level as `total_file_count` in the full record; the collection
  descriptions restate the files-table summary, which the enumerated distributions
  themselves carry. No fact is lost that is not also stated in a surviving slot.
- **`total_file_count` vs. distribution count:** the two agree for B35XWX (6 = 6),
  K7TGEM (8 = 8) and HIGT4C (10 = 10). For F3TD5R they differ by design —
  `total_file_count: 21` is what the files table reports, while only the 10 files
  visible on the table's first page appear in the capture and are therefore
  enumerated. This is stated in `resources[F3TD5R].source_caveats` and in the file
  collection's `description`; it is a capture limit, not a contradiction.
- **`total_size_bytes` vs. distribution `bytes`:** both absent everywhere, for the
  unit-ambiguity reason above. Consistently absent, so no scope mismatch arises.
- **`dialect`, formats and `is_tabular`:** `dialect` and `is_tabular` are absent from
  both records; formats agree. No conflict.
- **Identity, version and access facts vs. resources and version history:** the
  top-level `version_access.latest_version_doi`
  (`https://doi.org/10.18130/V3/HIGT4C`) agrees with the resource marked current and
  with the releases page's "Our latest data release"; `versions_available` lists
  exactly the five resource DOIs and their displayed version numbers;
  `distribution_dates.release_dates` lists exactly the four captured Publication
  Dates; the top-level `license`, `publisher` and `status` agree with the per-release
  values, which are identical across all captured releases (CC BY-NC-SA 4.0,
  University of Virginia Dataverse, Beta).
- **Historical vs. current releases:** the four archived releases and the current one
  are represented as distinct resources with distinct DOIs, dates and file
  inventories, not as contradictory values of one release. `version_access` states
  which is current and which are archived. The differing IF-image checksums between
  October 2025 and June 2026 are recorded as an anomaly rather than reconciled away.

### Commands run

```bash
echo "$CLAUDE_EFFORT"                                   # -> high

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 --project CM4AI
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3
```

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_d4d_core.yaml` (created, rebuilt from the audited full record, then `--sync-core`)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/CM4AI_provenance.yaml` (written by `d4d provenance record`, then by `d4d runs validate`)

No file outside this run's three declared outputs, plus the provenance record the
finalisation sequence writes, was modified.

## Results

| check | result |
|---|---|
| full — `linkml-validate` (`Dataset`) | **No issues found** |
| full — `linkml-term-validator` | **Validation passed** |
| core — `linkml-validate` (`CoreDataset`) | **No issues found** |
| core — `linkml-term-validator` | **Validation passed** |
| pair consistency (final, no `--sync-core`) | **PASS: 78 schema-identical slots; projected slots=['resources']** |
| validator warnings | none |
| full populated top-level slots | 55 |
| core populated top-level slots | 52 |
| shared slots (schema-derived) | 79 (78 identical + 1 projected) |
| resources (full / core) | 5 / 5, equal coverage by `id` |
| files → distributions | 34 → 34 |

**Reconciliation outcome: no divergence.** Every schema-identical shared slot is
present in both records with deeply identical parsed content; the one projected slot
matches by `id` with equal coverage and deep identity on every nested
schema-identical slot; the `file_collections` → `distributions` related-content
mapping was reviewed field by field with zero unresolved contradictions within or
between the two records. The only corrections made during the run were the Phase 3
source-audit fixes listed above, all applied to the full record first and then
propagated to core.
