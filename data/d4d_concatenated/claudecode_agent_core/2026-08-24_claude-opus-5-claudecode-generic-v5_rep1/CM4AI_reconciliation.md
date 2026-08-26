# CM4AI full/core reconciliation

- Run label: `2026-08-24_claude-opus-5-claudecode-generic-v5_rep1`
- Arm: BASELINE (input documents only)
- Condition: generic_v5
- Mode: four-phase project agent (Claude Code, Anthropic, claude-opus-5)
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- Full record: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CM4AI_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/CM4AI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the CM4AI dataset**, identified
by `https://cm4ai.org/`, which is the referent the project's `scope:` block in
`data/preprocessed/source_manifest.yaml` declares. The five Dataverse deposits named in
the input documents (DXWOS5, B35XWX, F3TD5R, K7TGEM, HIGT4C) are represented as
component `resources` of that one dataset rather than as separate referents, which is
what the manifest's `referent_note` states about them. `related_but_distinct` is
declared empty for this project, and no dataset is expressed through
`related_datasets`. The same choice is held in both records: the core record carries
the same `id` and the same five resources, matched by `id`.

Two identifier decisions follow from the referent. The dataset has no dataset-level DOI
in the input documents, so no top-level `doi` is asserted and the project landing page
is the identifier; each release carries its own DOI as a `doi:` CURIE and as a bare DOI
in the pattern-constrained `doi` slot. `publisher` and
`data_governance.accountable_organization` carry `ROR:0153tk833`, which the June 2026
release records in the affiliation field for the five authors that the earlier releases
place at the University of Virginia; no other organization named in the input documents
carries a registry identifier there, so none was supplied for any other organization.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs were the declared bundle, `data/preprocessed/source_manifest.yaml` (for
the scope declaration, the `source_priority` ranking and the `naming:` canonical label),
and the two LinkML schemas. No prior full or core D4D record, from any arm, label or
date, was read, opened, grepped or consulted; nothing under `data/d4d_concatenated/` or
`data/ro-crate_packages/` was read other than the two output paths this run writes. No
live web content was fetched. Record structure was derived from `SchemaView` over class
`Dataset` and class `CoreDataset`, not from any example record.

### Source disagreements resolved

Resolved by the manifest's `source_priority` tiers (tier 1 data resource > tier 2
documentation > tier 3 publication/preprint > tier 4 NIH project page > tier 5
historical data release). Each is recorded in `source_caveats` on the object it affects
as well as at the top level.

| Fact | Lower-ranked source | Preferred (higher-ranked) source | Recorded value |
|---|---|---|---|
| June 2026 release date | cm4ai.org data-releases (tier 2): "Released on: June 17, 2025" | Dataverse HIGT4C record (tier 1): Publication Date 2026-06-17 | 2026-06-17 |
| AP-MS availability | cm4ai.org data-releases (tier 2): "AP-MS interactomes (coming soon!)" | Dataverse HIGT4C record (tier 1): two AP-MS archives listed | present in the June 2026 release |
| Proteins imaged per condition | cm4ai.org data-releases (tier 2): 523 | Dataverse release records (tier 1): 563 (March 2025), 464 (later releases) | per-release Dataverse figures |
| Collaborating institutions | cm4ai.org (tier 2) adds UT Austin; the preprint (tier 3) adds UT Austin, U Alabama, U Montreal | Dataverse release description (tier 1) | the Dataverse list |
| End of project | NIH RePORTER (tier 4): project end 2026-08-31 | Dataverse maintenance plan (tier 2): "through the end of the project in November 2026" | November 2026 |

Two disagreements the ranking cannot decide, because both readings come from the same
source, are represented rather than resolved. Each Dataverse page shows a page-level
version (1.4, 2.1, 2.1, 2.0) that differs from the version in its own citation string
(V1, V2, V2, V2); the page version is in `version` and the citation string is reproduced
verbatim in `citation`. And all four releases record the same Data Creation Date and
Deposit Date of 2025-02-27, including the release published in 2026, so that date is
described in `collection_timeframes` rather than used as a collection start or end date.

### Scope discipline against the Nature publication

The bundle's Nature publication reports a multiscale map of U2OS osteosarcoma cells and
acknowledges Bridge2AI funding (OT2 OD032742), but its measurements are deposited at
NDEx, MassIVE MSV000097168 and ProteomeXchange PXD052362 and appear in no CM4AI release
file table. It is recorded as an external resource with that fact in its
`source_caveats`, and none of its instruments, counts or deposits — the Q-Exactive HFX,
the Leica SP5, the TimsTOF Pro2, the 5,147 proteins, the 275 assemblies — is attributed
to this dataset. Collection mechanisms are taken only from the CM4AI project preprint.

### Corrections made during the audit

Four defects were found by the audit and corrected in the full record before the core
record was rebuilt from it.

1. **Resolver URLs in identifier slots.** Three `external_resources[].id` values held
   `https://doi.org/…` where the schema declares the `doi` prefix. Rewritten as
   `doi:10.1101/2024.05.21.589311`, `doi:10.1101/2024.11.03.621734` and
   `doi:10.1038/s41586-025-08878-3`. The URLs inside those objects'
   `external_resources` lists are `string`-ranged and were left exactly as the bundle
   writes them.
2. **Product name altered from its source.** "3'HT kit" was written with a straight
   apostrophe where the bundle writes "3’HT kit" with U+2019. Restored to the source
   form, since a product name is a proper noun.
3. **Repository name altered from its source.** "PRIDE" was written where the bundle
   writes "Pride"; restored to the source spelling for the same reason.
4. **Unsupported compound claim.** "the inaugural CM4AI CodeFest in March 2024" joined
   two separate statements in the preprint — that a CodeFest was held in March 2024, and
   that a virtual CodeFest event was the inaugural one. Reduced to "the CM4AI CodeFest in
   March 2024".

### Shape audit

Every populated slot was checked against its induced range. Three findings changed the
record's shape during Phase 1 and are noted here because they constrain what the record
can carry:

- `Creator.principal_investigator`, `EthicalReview.contact_person` and
  `DataGovernance.committee_contact` are `Person`-ranged and not inlined, so they take a
  Person identifier string rather than an object. They carry ORCID CURIEs, and
  `mailto:jillianparker@health.ucsd.edu` for the one governance contact the input
  documents give no ORCID for. The associated names sit in the enclosing object's `name`
  or `description` because the schema offers nowhere else for them.
- `Creator` therefore has no person-shaped slot other than `principal_investigator`, so
  the 46-name author list of each release is not expanded into 46 `Creator` objects,
  which would have asserted that 45 people are principal investigators. Four creators are
  recorded — the two individuals the input documents identify by role (Trey Ideker as
  principal investigator and point of contact, Timothy Clark as first-listed author) and
  the two laboratories the file-level descriptions name as having generated data (the
  Lundberg Lab and the Nevan Krogan laboratory). The full author list is carried verbatim
  in each release's `citation`.
- File sizes are displayed by Dataverse as "2.6 GB", "31.1 KB" and similar, which cannot
  be converted to an exact `bytes` integer without assuming a multiplier. `bytes` and
  `total_size_bytes` are omitted and the displayed size is stated in each file's
  `description`. `total_file_count` is populated only from counts the release states
  exactly ("1 to 6 of 6 Files" and so on).

No prose was found in a slot requiring a list, no undefined enum value was written, and
no commentary was found embedded in a name, identifier or affiliation value. Evidence
commentary is in `source_caveats` throughout; `notes` carries only the depositor and
deposit-date facts, which have no fitting slot.

### Back-porting from Phase 2

Phase 2 discovered no fact absent from the full record, so nothing was back-ported. The
core schema's slot set is a subset of the full schema's apart from `distributions` and
`dialect`, and `dialect` is unpopulated because the input documents describe no tabular
format dialect. All four Phase 3 corrections were made in the full record first, and the
core record was then rebuilt from the corrected full record.

### Validation after correction

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>            → No issues found
poetry run linkml-term-validator validate-data <full> --schema …data_sheets_schema_all.yaml --target-class Dataset    → Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>   → No issues found
poetry run linkml-term-validator validate-data <core> --schema …_core_all.yaml --target-class CoreDataset             → Validation passed
```

## Phase 4 — strict full/core reconciliation

### Shared slots

Derived at runtime with `SchemaView` from `Dataset` and `CoreDataset`. The two classes
share 82 slot names. Of these, 81 have the same induced range and cardinality; the
validator compares the 79 that are not per-record-exempt. `resources` is the one
projected slot (`Dataset` in full, `CoreDataset` in core). `conforms_to_class` and
`conforms_to_schema` carry the `d4d:perRecord` annotation and are exempt from identity
because they describe the record rather than the dataset: `conforms_to_class` is
`Dataset` in the full record and `CoreDataset` in the core one.

The core record was produced by projecting the validated full record through the
schema-derived slot sets rather than by re-serializing prose, so every schema-identical
slot is deeply identical by construction, including narrative fields. Nothing was
condensed, paraphrased, reordered or omitted.

### Full-only slots

Two populated top-level slots have no counterpart in `CoreDataset` and are absent from
the core record: `direct_collection` and `third_party_sharing`. Both are omitted from
the core projection, not removed from the full record. Within `resources`, three
populated slots are full-only and likewise omitted from the core projection:
`citation`, `total_file_count` and `file_collections`.

### Projected and related content

**`resources` (projection).** Coverage is equal: five resources in each record, matched
by `id` — `doi:10.18130/V3/DXWOS5`, `doi:10.18130/V3/B35XWX`, `doi:10.18130/V3/F3TD5R`,
`doi:10.18130/V3/K7TGEM`, `doi:10.18130/V3/HIGT4C` — and every nested schema-identical
slot is deeply identical.

**`file_collections` → `distributions` (semantic mapping, reviewed).** The full record
places files in `FileCollection` objects grouped by content type within each release;
`CoreDataset` has no nesting file class, so each `File` maps to one `CoreDistribution`.
Coverage is equal file for file: 0, 6, 10, 8 and 10 for the five releases in the order
above, matching the full record exactly. `id`, `name`, `path`, `format`, `media_type`,
`compression`, `hash` and `description` carry over unchanged; `issued` and `file_type`
have no counterpart in `CoreDistribution` and are dropped, as is the collection-level
grouping (`collection_type`, `file_count`, and the collection `name`/`description`).
Checked for conflict and none found: no name, path, format, compression or checksum
differs between the two representations, and the release-scope of every distribution is
unchanged. `total_file_count` in the full record (6, 21, 8, 10) is consistent with the
distribution counts, with the June 2025 release the one case where they differ by design
— its Dataverse capture shows 10 of 21 file rows, which is why that release asserts no
per-collection `file_count` and states the partial capture in its `source_caveats`.

`total_size_bytes`, `dialect` and `is_tabular` are unpopulated in both records, so no
scope comparison arises for them. `compression` is stated per distribution rather than
at dataset level, consistently in both.

### Deterministic checks

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
  → PASS: 79 schema-identical slots; projected slots=['resources'];
    per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
  → PASS (same counts)
```

`--sync-core` changed nothing, which is the expected result of building core by
projection from the audited full record.

Identifier grounding against the declared bundle, over both records pooled:

```
grounded 9, minted_fragment 42, absent 0; no resolver_url_in_identifier_slot findings
```

Zero `absent` means every identifier either occurs in the bundle or is a fragment minted
on one that does. The 42 minted fragments are the local labels for file collections,
files and dataset properties; each hangs off an attested identifier — a release DOI or
the project landing page — rather than a namespace of our own. Supplementary form checks
over both records: undeclared CURIE prefixes 0, British spellings 0, non-canonical CM4AI
label variants 0.

### Repair

None. No finding from the pair validator, the grounding checker or the report-claims
checker required a change to either record after the core record was rebuilt, so no
`repair` or `report_after_repair` phase was performed and none is recorded in provenance.
The four Phase 3 corrections listed above were made during the source audit, before Phase
4 ran.

## Result

- Full record: 54 populated top-level slots, 1,754 lines (informational, not a quality gate).
- Core record: 52 populated top-level slots, 1,244 lines (informational, not a quality gate).
- Both records pass schema validation and ontology term validation.
- Full/core pair consistency: PASS in both directions, 79 schema-identical slots compared.
- Reconciliation outcome: **consistent, with no unresolved contradiction within or between
  the two records.** The only divergences are the schema-mandated ones — two full-only
  top-level slots, three full-only slots inside `resources`, the `resources` range
  projection, the `file_collections` to `distributions` mapping, and the two per-record
  exempt slots.
