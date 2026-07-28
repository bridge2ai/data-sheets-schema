# CM4AI full/core reconciliation — 2026-07-27_claude-opus-5_rep3

Arm: BASELINE (document corpus only).

| Item | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Full record | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml` (2889 lines) |
| Core record | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml` (1838 lines) |
| Factual source | `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (7873 lines, 10 documents) |
| Source manifest | `data/preprocessed/source_manifest.yaml` |

Line counts are informational metadata only, not a quality gate.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs read during this run were exactly: the concatenated CM4AI source
bundle, the source manifest, and the two LinkML schemas plus `D4D_Core.yaml`
(structure only). No prior full or core D4D record, evaluation, reconciliation
report, or RO-Crate artifact was read, searched, or cited; no live web content
was fetched. One `ls` of `data/d4d_concatenated/` was run before generation to
confirm that the target version directories did not already exist; only
directory and file *names* were displayed and no file under those paths was
opened. Prior D4D content from the parent conversation was treated as forbidden
evidence. Both output headers state `Prior D4D factual reuse: prohibited`.

### Structural derivation

Structure was derived at runtime with LinkML `SchemaView`:

- Full: class `Dataset` in `data_sheets_schema_all.yaml` — induced slots,
  ranges, cardinality, inlining and enum ranges enumerated programmatically.
- Core: class `CoreDataset` in `data_sheets_schema_core_all.yaml`, cross-checked
  against `D4D_Core.yaml`.

Two schema behaviours were established empirically before authoring, because
they are not obvious from slot names: `principal_investigator`,
`reviewing_organization`, `contact_person`, `governance_committee_contact` and
`grantor` are **non-inlined** references and must be scalar identifier strings,
whereas `affiliations` is an inlined list of `Organization` objects. No field
name or nested shape was taken from any example, prior record, or
`d4d:docExample` annotation.

### Release scoping (arm-specific requirement)

The corpus contains four Dataverse release pages. They are kept distinct
throughout both records and are never merged:

| Release | DOI | Dataverse version | Publication date | Files | Status in record |
|---|---|---|---|---|---|
| June 2026 (Beta) | 10.18130/V3/HIGT4C | 2.0 | 2026-06-17 | 10 | **current** — top-level identity, `file_collections`/`distributions`, `resources` |
| October 2025 (Beta) | 10.18130/V3/K7TGEM | 2.1 | 2025-10-31 | 8 | historical — labelled in `version_access`, `distribution_dates`, `related_datasets` |
| June 2025 (Beta) | 10.18130/V3/F3TD5R | 2.1 | 2025-07-01 | 21 | historical — same, plus one `errata` entry |
| March 2025 (Beta) | 10.18130/V3/B35XWX | 1.4 | 2025-03-03 | 6 | historical — same |
| May 2024 (portal archive list) | 10.18130/V3/DXWOS5 (from the CM4AI preprint) | V1 | not stated | not stated | historical — labelled |

Every statement drawn from a historical release carries explicit scope in the
text (for example "The October 2025 release describes the identically named
archive as …"). Nothing from a historical release is asserted as a property of
the June 2026 release.

### Source conflicts resolved

1. **June 2026 release date.** `cm4ai.org/data-releases` labels HIGT4C the
   "June 2026 Data Release (Beta)" but displays "Released on: June 17, 2025".
   The Dataverse record for the same DOI gives Publication Date 2026-06-17.
   **Resolved in favour of the Dataverse metadata** (authoritative repository
   record for the release, and internally consistent with the release title, the
   2026 citation year, and file publication dates of Jun 17 2026). Recorded as
   `issued: 2026-06-17T00:00:00Z` and flagged explicitly in `anomalies` and in
   `distribution_dates`.

2. **Post-publication file update.** The three immunofluorescence archives carry
   a file publication date of 2026-07-15, after the release publication date.
   The manifest records the version 2 release time as 2026-07-15T20:28:19Z.
   Recorded as `last_updated_on: 2026-07-15T20:28:19Z`, with the corresponding
   `file_collections`/`distributions` and the IF `resources` entry carrying
   `issued: 2026-07-15`; flagged in `anomalies`.

3. **Immunofluorescence protein coverage.** Three different figures appear: 563
   proteins (March 2025 v0.6-beta archives), 464 proteins (June 2025 and October
   2025 archives), 523 proteins (CM4AI portal). The June 2026 release page
   states **no** protein count for its image archives, and their MD5 checksums
   differ from the October 2025 archives, so no figure can be carried forward.
   **Resolved by asserting no count for the current release** and recording all
   three source figures with their scopes in the IF `resources` description and
   in `anomalies`.

4. **Andrej Sali's affiliation.** Recorded as University of California San Diego
   in the Dataverse author lists and as University of California San Francisco
   in both the CM4AI preprint and the Nature publication. **Resolved in favour
   of the Dataverse release metadata** for the dataset-author field (it is the
   release record's own author metadata), with the publication discrepancy
   stated in the creator description and in `anomalies`.

5. **Project end date.** The Maintenance Plan states updates "through the end of
   the project in November 2026"; NIH RePORTER records project end 2026-08-31.
   **Both retained with attribution** rather than silently choosing one;
   recorded in `updates` and flagged in `anomalies`.

6. **Collaboration list.** The portal names UCSD, UCSF, Stanford, UVA, Yale, UT
   Austin, UA Birmingham, SFU and the Hastings Center; the March 2025 Dataverse
   description omits UT Austin; KTH Royal Institute of Technology appears as an
   author affiliation in every release but in neither list. **Portal list used**
   (it is current and consistent with the UT Austin author), KTH added to
   `creators[0].affiliations` with an explicit note, discrepancy flagged.

7. **Vardit Ravitsky's affiliation.** Dataverse author list gives University of
   Montreal while the ethical-review contact email on the same page is at
   thehastingscenter.org. Both recorded; flagged.

8. **Stale description timestamp.** The June 2025, October 2025 and June 2026
   Dataverse descriptions all end with "(2025-06-30)". Treated as a carried-over
   description stamp, not a release date; flagged.

9. **Portal "coming soon" vs. published AP-MS.** The portal lists AP-MS
   interactomes as "coming soon" while the June 2026 release already publishes
   AP-MS archives. **Resolved in favour of the release file table**; flagged.

### Scope separation: Nature U2OS publication

The corpus includes Schaffer, Hu et al., *Nature* 642, 222–231 (2025), which
acknowledges Bridge2AI OT2 OD032742 and shares the MuSIC methodology but reports
data generated in **U2OS osteosarcoma cells** — a different cell line from the
MDA-MB-468 and KOLF2.1J data in the CM4AI Dataverse releases, deposited in
different repositories (NDEx, MassIVE MSV000097168, ProteomeXchange PXD052362,
ModelArchive, EBI Complex Portal, HPA v23). Its counts (275 assemblies, 5,147
proteins, 2,174 baits, 36,842 interactions, and so on) are **not** merged into
CM4AI composition fields. It appears only in `related_datasets`
(`relationship_type: references`), `existing_uses`, and in
`labeling_strategies` / `annotation_analyses` / `machine_annotation_tools`
entries that state explicitly that the figures describe that publication and not
the CM4AI release contents. The same scoping is applied to the CM4AI preprint's
May 2024 Year-1 status figures (17 tagged genes, 72/100 chromatin modifiers,
>700 iPSC complexes, and so on), which are labelled as the preprint's reported
status rather than as release contents.

### Corrections made during the audit

Four factual errors and three presentational defects were found in the Phase 1
full record and corrected there first; the core was then regenerated from the
corrected full.

1. **Wrong release pair for RO-Crate consolidation.** `preprocessing_strategies`
   claimed the per-segment RO-Crate metadata files were consolidated into
   `cm4ai_release_metadata.zip` between October 2025 and June 2026. The October
   2025 release already contains `cm4ai_release_metadata.zip`; the consolidation
   occurred between June 2025 and October 2025. Corrected, and a separate
   statement added for what actually changed between October 2025 and June 2026
   (AP-MS archives added, IF checksums changed).
2. **Fabricated URL.** `raw_sources` carried `access_url: https://massive.ucsd.edu/`
   for the MassIVE deposits. The corpus gives only the link text "MassIVE
   Repository" and no URL. The slot was removed rather than guessed.
3. **Over-broad enum value.** `license_and_use_terms.data_use_permission`
   included `publication_required`. The sources require *citation* of the
   related publication and the data collection, not that results be published.
   Removed; `general_research_use` and `no_commercial_use` retained.
4. **Missing Production Location.** The Dataverse "Production Location" field
   (UCSD; UCSF; Stanford; UVA) was not represented. Added to `data_collectors`.
5. Self-contradictory sentence about the Bélisle-Pipon diacritic — reworded.
6. Version-monotonicity anomaly text was miscounted ("three of the four") —
   reworded, and two further anomalies added (collaboration list, post-release
   file publication date).
7. `creators[0]` prose listed nine collaborating institutions while its
   `affiliations` list had ten — the KTH addition is now stated explicitly.

### Deliberate omissions (unknowns preferred to estimates)

- **Byte counts.** The Dataverse file table publishes only rounded display sizes
  ("3.8 GB", "113.3 KB"). No exact byte value is derivable, so
  `total_size_bytes` (full) and every `CoreDistribution.bytes` (core) are
  omitted, and the displayed sizes are recorded verbatim in the file-level
  descriptions instead.
- `variables`, `splits`, `imputation_protocols`, `participant_privacy`,
  `participant_compensation`, `dialect` — not documented in the corpus; omitted.
- `Instance.data_topic` / `data_substrate` — no source-supported ontology terms;
  omitted rather than invented.
- **Coined identifiers.** `Organization.id` is required and the corpus supplies
  exactly one organizational PID (`https://ror.org/0153tk833`, University of
  Virginia, from the June 2026 author list). That ROR is used for UVA; all other
  organization identifiers are locally coined as `https://cm4ai.org/#org-<slug>`
  and carry no factual claim beyond the organization's name. Likewise,
  `Dataset`/`FileCollection` identifiers below the top level are coined as
  fragments of the release landing-page URL. Person references use ORCID URIs
  where the corpus supplies them and `mailto:` URIs for the governance and
  ethics contacts, whose ORCIDs are not stated in that context.

### Validation after Phase 3 corrections

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four: `No issues found` / `✅ Validation passed`.

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime with `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used.

- **76 schema-identical slots** (same induced range and cardinality).
- **1 projected slot**: `resources` (`Dataset` in full, `CoreDataset` in core).
- **2 core-only slots**: `distributions`, `dialect` (`dialect` unused).
- **17 full-only slots**: `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `parent_datasets`, `participant_compensation`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`,
  `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables` (6 of these are unused in the full record).

### Identity of shared content

The core record was generated mechanically from the Phase 3-audited full record:
every schema-identical slot value was copied verbatim, with no condensation,
paraphrase, reordering or omission — including the long narrative fields
(`description`, `purposes`, `tasks`, `known_limitations`,
`license_and_use_terms`, `preprocessing_strategies`, and so on). The 47 `creators`
entries, 3 `funders`, 5 `instances`, 8 `anomalies` and all other shared lists are
byte-for-byte identical in parsed form and in list order.

`resources` projection: 4 entries, matched by `id`, equal coverage in both
records, list order preserved. Every slot used by those entries (`id`, `name`,
`title`, `description`, `license`, `version`, `issued`, `status`, `page`,
`language`, `keywords`) exists in `CoreDataset`, so the projection is a total
copy with no full-only nested slot dropped.

### Semantic review of related, non-identical content

`file_collections` (full) ↔ `distributions` (core) — the validator's
`semantic-review-required` warning was discharged by the following review, not
by the warning's presence:

- **Coverage**: 10 file collections, 10 distributions, identical name sets, no
  unmatched distributions. Both equal `total_file_count: 10` in the full record
  and the "Released archive file" instance count of 10 shared by both records,
  which in turn matches the release page's "1 to 10 of 10 Files".
- **Identity fields**: `id`, `name`, `description`, `path` and `compression` are
  identical for all 10 pairs (verified programmatically). No paraphrase was
  introduced on the core side.
- **Formats**: every release file is listed by Dataverse as an Archive with a
  `.zip` extension, so all 10 distributions carry `format: ZIP`,
  `media_type: application/zip`, `compression: zip`. This agrees with the
  top-level `compression: zip` present in both records and with
  `is_tabular: false` in both.
- **Checksums**: 10 distinct MD5 values, each transcribed from the June 2026
  release file table. `FileCollection` has no checksum slot, so there is no
  full-side value to contradict; the three IF checksums are explicitly noted in
  the full record as differing from the identically named October 2025 archives.
- **Byte counts**: absent on both sides (see deliberate omissions). No
  `total_size_bytes` vs distribution-bytes comparison is possible and none is
  implied.
- **Access URLs**: the full record's `distribution_formats.access_urls` (release
  landing page, DOI, Data Access API base) and the shared `page` field are
  identical in both records; distributions carry relative `path` values that are
  the file names shown in the same release file table, with no conflicting
  access URL.
- **Release scope**: all 10 distributions belong to the June 2026 release only.
  Their `issued`-equivalent dates on the full side (2026-06-17 for seven files,
  2026-07-15 for the three IF archives) match the top-level `issued` and
  `last_updated_on` and the IF `resources` entry.

Other cross-record semantic checks, all clean:

- Top-level identity and access facts (`id`, `doi`, `version`, `issued`,
  `last_updated_on`, `license`, `publisher`, `status`) are identical in both
  records and agree with `version_access.latest_version_doi`
  (`https://doi.org/10.18130/V3/HIGT4C`), with `distribution_dates`, and with
  every `resources` entry (`version: "2.0"`).
- Historical releases are represented in `version_access` and
  `distribution_dates`, which are shared and identical, so the core record
  retains the same current-vs-historical labelling as the full record. The
  full-only `related_datasets` adds machine-readable
  `is_new_version_of`/`references` links; its loss in core removes structure,
  not facts, since the same release history is stated in the shared
  `version_access` narrative.
- Instance counts (53,788 images; 1,374 interactions; 7,023 proteins; 11,739
  targeted genes; 10 files) are identical in both records, each carrying its
  portal-level-versus-release-level scope caveat in the same wording.
- No contradiction was found within either file or between them.

### Commands run

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml
```

Both invocations returned:

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=10, unmatched core distributions=[]
```

The `--sync-core` pass made no substantive change (the core had already been
generated mechanically from the audited full record); the independent pass
confirms the result. Schema and term validation were re-run on both files after
the synchronization pass and both remain clean.

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml`
  — created (Phase 1), corrected (Phase 3).
- `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml`
  — created (Phase 2), regenerated from the corrected full record (Phase 3),
  synchronized and verified (Phase 4).
- `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CM4AI_reconciliation.md`
  — this report.

No existing file was overwritten.

## Result

Phase 3 provenance result: **clean** — no prior generated D4D content was read
or used; all factual inputs were on the phase allowlist.

Phase 4 consistency result: **PASS** — 76 schema-identical slots deeply
identical and identically present; 1 projected slot (`resources`) with equal
coverage and total copy; the single related-content warning
(`file_collections` ↔ `distributions`) reviewed and discharged with zero
unresolved contradictions.
