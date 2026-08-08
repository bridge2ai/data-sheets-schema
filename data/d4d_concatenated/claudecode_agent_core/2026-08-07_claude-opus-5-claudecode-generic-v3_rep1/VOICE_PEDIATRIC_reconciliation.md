# VOICE_PEDIATRIC — Phase 3 / Phase 4 reconciliation

- Label: `2026-08-07_claude-opus-5-claudecode-generic-v3_rep1`
- Mode: four-phase project agent, generic prompt
- Arm: BASELINE (input documents only)
- Runtime / provider / model / reasoning effort: Claude Code / Anthropic / claude-opus-5 / high
- Temperature: 0.0
- Declared bundle: `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d_core.yaml`

This is the first VOICE_PEDIATRIC datasheet generated in this repository. No prior record
of the project exists in any method directory, so nothing was available to compare against
and no established shape was matched. Everything below is derived from the declared bundle
and the two LinkML schemas.

## Referent

`Dataset` admits one referent. The referent chosen is:

> **Bridge2AI-Voice Pediatric Dataset, version 1.1.0, published on PhysioNet on 1 May 2026,
> DOI 10.13026/h995-bt35.**

Why this one, and not an alternative:

- The bundle's first and only dataset-specific document is the PhysioNet landing page for
  pediatric v1.1.0, captured 2026-07-24. It is the only source in the bundle that describes a
  concrete, published, citable dataset with its own DOI, access policy, licence, file
  inventory and ethics approval. Every other document in the bundle is consortium-level.
- **Not the Bridge2AI-Voice programme.** The other five sources (the USF single-IRB protocol,
  the docs.b2ai-voice.org site, the NIH RePORTER supplement record, the Data Transfer and Use
  Agreement template, the eipm/bridge2ai-docs README) describe the Bridge2AI-Voice project as a
  whole. Taking the programme as the referent would have made the 300-participant pediatric
  cohort a footnote inside a 10,000-voice programme description and would have contradicted the
  scope this run was given.
- **Not the pediatric PhysioNet project across all versions.** v1.0.0 exists and is listed on the
  captured page, but only v1.1.0's page was captured, and v1.1.0 has its own version DOI distinct
  from the latest-version DOI. Pinning the referent to v1.1.0 keeps every count, file listing and
  release note attributable to one artifact. v1.0.0 is represented through `version_access` and
  through a `related_datasets` entry typed `is_new_version_of`.
- **Not the adult dataset.** See the next section.

The referent is held identically in both records: `id`, `name`, `title`, `version`, `doi`,
`page`, `publisher` and `issued` are byte-identical across the pair.

## Relationship to the adult VOICE dataset

`data/preprocessed/concatenated/VOICE_preprocessed.txt` was not read. Four of this bundle's six
documents are shared with the adult project's corpus, so the adult cohort is discussed inside
this bundle; it is represented here only as a distinct related resource:

- `related_datasets[related_dataset_adult_physionet]` — `target_dataset:
  https://physionet.org/content/b2ai-voice/`, `relationship_type: references`. The description
  records what the sources actually say: the pediatric release page notes the adult dataset is
  also available on PhysioNet; the two are separate PhysioNet projects covering distinct cohorts
  under different protocols and different ethics approvals; the adult dataset is not a version of
  this one; and the documentation site advertises adult v3.1.0 and pediatric v1.1.0 as
  concurrently available releases behind separate PhysioNet links.
- `references` was chosen over `supplements`, `is_variant_form_of` or any version relation because
  the enum has no sibling-cohort member and the sources assert only that the pediatric page points
  to the adult one. Asserting a stronger relation would have been an inference.
- The programme link is carried separately by
  `related_datasets[related_dataset_bridge2ai_voice_project]`, `relationship_type: is_part_of`,
  `target_dataset: Bridge2AI-Voice`.

Adult-scoped assertions were excluded from the record rather than reused. Named exclusions,
recorded in the dataset-level `source_caveats`: the 833-instance count, dataset versions 2.0.0 and
3.0.0, the 18-year minimum age, Health Data Nexus hosting, the semi-annual update cadence, the five
recording sites, the diagnostic labelling of the five adult disease cohorts, and the v3.0.0 HIPAA
de-identification statements. Concretely, this is why `labeling_strategies`, `existing_uses`,
`content_warnings`, `confidential_elements`, `splits`, `updates` and `errata` are all absent: the
only answers the bundle offers for those questions are adult-scoped.

## Phase 3 — source and provenance audit

### Provenance

Every factual input is on the Phase 1/2/3 allowlist. Read during this run:
`.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
`.claude/commands/d4d-agent.md`, the declared bundle, the VOICE_PEDIATRIC section of
`data/preprocessed/source_manifest.yaml`, both schemas via `SchemaView`,
`src/data_sheets_schema/d4d_pair_consistency.py`, and this run's own two outputs.

No prior D4D record, from any arm, label or date, was read, opened, grepped or cited. No
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was touched. No prior D4D content from the parent
conversation was treated as evidence. **Disclosure:** one `ls` of
`data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/`
returned four CHORUS *filenames* while confirming the output directory. No file content was read
and no `VOICE*` glob was used at any point.

Structure was derived only from the schemas. `Dataset` (96 induced slots) and `CoreDataset`
(81 induced slots) were enumerated with `SchemaView`, together with the induced shape of every
nested class used and the permissible values of every enum used. No `d4d:docExample` value was
copied.

### Source audit findings

**Source disagreements, represented rather than resolved:**

1. *Which grant funded the release.* The pediatric release acknowledges supplement
   `3OT2OD032720-01S1`; the NIH RePORTER page in the bundle documents supplement
   `3OT2OD032720-01S3` of the same core project. Both are recorded as separate `Grant` entries
   under one NIH `FundingMechanism`, with the disagreement stated in that object's
   `source_caveats`.
2. *Which ethics body governs the pediatric cohort.* The release page cites the Research Ethics
   Board at the Hospital for Sick Children. The USF protocol states that pediatric patients are
   enrolled only at pediatric sites and that the Canadian institutions do not follow the single-IRB
   process, yet its own revision history summarises V2 (2023-05-03) as "Modified to include
   pediatric cohort under single IRB". Two `EthicalReview` entries are recorded — the SickKids REB
   as the approval the release itself cites, and the USF single IRB as the review governing the
   wider consortium study — with the tension stated in the second entry's `source_caveats`.
3. *Author name spellings.* The release byline gives "Jennifer Siu" and "Frank Rudzicz"; the
   documentation site gives "Jennifer Sui" and "Frank Rudzizc". The byline spellings are used
   because they are this dataset's own citation, and each discrepancy is noted on the individual
   creator entry.
4. *Row counts across feature tables.* The torchaudio and phonetic-posteriorgram tables report
   23,533 rows; the four sparc tables report 23,532. Both counts are carried, on the individual
   file descriptions and in `missing_data_documentation`; the release does not explain the
   difference and no reconciliation was invented.
5. *Retention.* The consortium says contributed data is retained as long as it is useful, possibly
   indefinitely; the Data Transfer and Use Agreement obliges recipients of controlled-access raw
   audio to destroy it after two years or on project completion. Both are recorded in
   `retention_limit.retention_details`, and `retention_period` is deliberately left unset because
   the two rules bind different parties.

**Mis-scoping risks checked and handled.** Four documents in the bundle are consortium-level. Every
value taken from one carries a `source_caveats` naming the document and stating that the release
page does not restate it: `at_risk_populations` (USF protocol §22.6 assent and parental permission),
`participant_compensation` (USF protocol §21.1, the only statement in the bundle that speaks to
pediatric compensation, and which says compensation goes to adults only), `informed_consent`
(consent mechanisms from the USF protocol), `regulatory_restrictions` (Certificate of
Confidentiality and OMB M-07-16 from the DTUA template), `ip_restrictions` (registered access
agreement text quoted on the documentation site), `discouraged_uses`, `intended_uses`,
`data_protection_impacts`, `extension_mechanism`, `subpopulations` and `variable_task_name`.

The PhysioNet site footer credits NIBIB, NHLBI and the NIH Office of the Director under grants
U24EB037545 and R01EB030362, and names the MIT Laboratory for Computational Physiology. That footer
describes the PhysioNet platform, not this dataset; it is recorded on the PhysioNet `Maintainer` and
explicitly excluded from `funders`.

**Gaps left empty rather than estimated,** listed in the dataset-level `source_caveats`: the
pediatric collection timeframe, per-file byte counts and checksums, `total_file_count` and
`total_size_bytes`, participants per age band, the patient/volunteer split, the pediatric REB
protocol number and approval date, pediatric diagnostic labelling, predefined data splits, and any
prior use of the pediatric release.

**Values deliberately left unset where a boolean or enum would have been an inference:**
`SamplingStrategy.is_random` and `.is_representative`; `Deidentification.identifiable_elements_present`
(the page says "low risk" and describes a PII screen, but never claims the data is free of
identifiable elements); `ExportControlRegulatoryRestrictions.hipaa_compliant`;
`RetentionLimits.retention_period`; `Instance.data_topic` and `.data_substrate` (no ontology term is
given in the bundle, and inventing a CURIE would have created an unverifiable term).

### Shape and slot-filling corrections applied in Phase 3

All nine were found by auditing the Phase 1 output against the schema and the slot-filling contract,
and all were fixed in the full record before core was re-derived:

| # | Finding | Fix |
|---|---|---|
| 1 | `citation` and a creator name dropped the acute accent the release page uses | restored "Bélisle-Pipon" in both places |
| 2 | evidence commentary ("the release does not report which recordings…") sat inside `anomalies[0].anomaly_details` | moved to that object's `source_caveats` |
| 3 | evidence commentary sat inside `file_collections[metadata].description` | moved to that collection's `source_caveats` |
| 4 | `distribution_dates[0].description` restated its sibling `release_dates` verbatim | description now states only the date-to-version mapping |
| 5 | `version_access.versions_available` embedded publication dates inside version strings | list reduced to `1.0.0`, `1.1.0`; dates moved into `version_details` |
| 6 | `regulatory_restrictions.regulatory_restrictions` held "No export controls apply", i.e. an assertion of absence inside a list of restrictions that apply | list left empty; the statement moved to the object's `description` |
| 7 | `variables[*].name` duplicated the structured `variable_name` sibling | `name` removed from all five variables |
| 8 | `related_datasets[*].target_dataset` carried an identifier plus commentary | reduced to a bare identifier (a URL where one exists); the qualifying text moved to `description` |
| 9 | two Person-reference slots left empty with their content in prose and no explanation | `license_and_use_terms.contact_person` and `regulatory_restrictions.governance_committee_contact` now carry a caveat explaining that the access contact the sources give is an office (DACO@b2ai-voice.org), not a named individual, and that the slot takes a Person reference the schema gives no container to define |

A tenth, structural, issue was found during Phase 1 validation rather than Phase 3:
`Creator.principal_investigator` ranges over `Person` but is **not inlined**, so it takes a string
reference, and `Dataset` exposes no container in which to define a `Person`. An inline PI object was
rejected by `linkml-validate`; the role and contact address were moved into the creator's
`description` and the constraint recorded in that creator's `source_caveats`.

**Phase 2 discoveries back-ported to full:** one. Re-reading the release page while deriving core
surfaced two statements with no home slot — the conflicts-of-interest declaration ("None to
declare.") and the acknowledgement of participant contribution. Both were added to the full record's
top-level `notes` before core was re-derived, so they appear identically in both.

No Phase 2 discovery contradicted a Phase 1 value, so no fact in the full record was corrected on
factual grounds.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime from `Dataset` and `CoreDataset` with `SchemaView`; no hand-written field list.

- **78 schema-identical slots** (equal induced range, multivalued, required, cardinality and
  `inlined_as_list`). All 78 must be present in both or absent from both, with deeply identical
  parsed YAML.
- **1 projected slot**: `resources` (`Dataset[]` in full, `CoreDataset[]` in core). Populated in
  neither record — the bundle declares no sub-datasets — so the projection is vacuous and equal.

### Result

```
PASS: 78 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=1, unmatched core distributions=[0..11]
```

Zero errors. Core was **not** synchronised with `--sync-core`: it was built by projecting the
Phase 1 full record's shared slots programmatically, so deep identity held on the first
independent check. The command was run once, without `--sync-core`, as the final check.

Slot counts: **full 65 populated top-level slots, core 57**.

- Full-only, populated (10): `citation`, `collection_consents`, `direct_collection`,
  `file_collections`, `participant_compensation`, `participant_privacy`, `related_datasets`,
  `relationships`, `third_party_sharing`, `variables`. None of these exists in `CoreDataset`.
- Core-only, populated (2): `distributions`, `dialect`. Neither exists in `Dataset`.
- Shared and populated in both: 55. 65 − 10 = 55 = 57 − 2. The arithmetic closes, so no shared slot
  is populated on one side only.

No narrative field was condensed, paraphrased, reordered or omitted in core. `description`, `notes`
and `source_caveats` — the three longest narrative slots — are byte-identical.

### Semantic review of related, non-identical content

The validator's warning is not evidence that review occurred, so the review was performed
explicitly and is recorded here.

**`file_collections` (full) → `distributions` (core).** The two slots have different shapes by
design: `FileCollection` is folder-level (`collection_type`, `file_count`, `total_bytes`, `path`,
nested `File[]`), while `CoreDistribution` is file-level (`bytes`, `hash`, `md5`, `sha256`, `path`,
`format`, `encoding`, `compression`, `media_type`). Core therefore projects the full record's
*nested* `File` resources one level up. The validator's deterministic matcher compares core
distributions only against the top-level collections, which is why 12 of 13 are reported unmatched.

A programmatic review compared each core distribution against its counterpart across both levels:

- 12 core distributions matched a full `File` resource by `id`. For every one, `name`, `path`,
  `format`, `media_type`, `description` and `compression` are equal, and each file's `path` sits
  under its parent collection's `path` (`features/…`, `phenotype/…`).
- 1 core distribution (`file_collection_metadata`) matched a full `FileCollection`, because the
  release page describes that folder without naming its contents. `name`, `path` and `description`
  are equal.
- The two remaining full collections (`file_collection_features`, `file_collection_phenotype`) have
  no folder-level counterpart in core; their entire contents are covered file-by-file. Coverage is
  complete in both directions: every released file named anywhere in the full record appears in
  core, and every core distribution has a counterpart in full.
- **One intentional difference:** `file_collection_metadata.source_caveats` differs between the two
  records. Full explains why no file resources are listed; core additionally explains that the entry
  projects a collection rather than a file, and why byte counts, checksums and media types are
  absent from every distribution. This is evidence commentary about the records, not a dataset fact,
  and the two texts do not conflict. It sits in the projected pair rather than in a schema-identical
  slot, so it does not affect strict identity.

**Counts and sizes.** `total_file_count` and `total_size_bytes` are unset in full, and no
`CoreDistribution.bytes` is set, so there is no scope mismatch to reconcile. The release page
publishes no file sizes or hashes; nothing was estimated.

**Formats, `is_tabular` and `dialect`.** `is_tabular: true` in both. Core-only `dialect` is
`{delimiter: "\t"}`, consistent with the tab-delimited files declared in both records
(`static_features.tsv`, `audio_quality_metrics.tsv`, `phenotype/demographics.tsv`, each carrying
`format: TSV` and `media_type: text/tab-separated-values` identically on both sides). Only
`delimiter` is set: the release page's worked example confirms a header row but the `header` slot
takes a string with no stated convention, so it was left unset rather than guessed. The Parquet
files carry no `format` or `media_type` on either side, because `FormatEnum` and `MediaTypeEnum`
have no Parquet member; the format is stated in prose and the omission is caveated in both records.

**Identity, version and access facts checked for internal agreement.** `id`, `doi`, `page`,
`version`, `publisher`, `issued` and `license` agree with each other and with
`version_access.latest_version_doi` (the distinct latest-version DOI, 10.13026/mf9s-5r03),
`distribution_dates.release_dates` (2025-12-17, 2026-05-01), the `is_new_version_of` relation to
v1.0.0, and `license_and_use_terms`. Both records state the same access design throughout: a
registered-access featurised release on PhysioNet under the Bridge2AI Voice Registered Access
License and Agreement, and a separate controlled-access route for raw audio via Synapse
(syn73617068) through the Data Access Compliance Office. The historical release (v1.0.0) is kept
distinct from the current one rather than treated as a contradiction.

**Participant and recording counts checked for internal agreement.** 300 participants and 23,533
recordings appear in the top-level `description`, in `instances`, and in the per-file descriptions,
consistently, in both records — with the 23,532-row sparc exception stated wherever it applies.

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d.yaml` (Phase 1, then 9 Phase 3 corrections + 1 Phase 2 back-port)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d_core.yaml` (Phase 2, re-derived after the Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_reconciliation.md` (this report)

### Commands

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/VOICE_PEDIATRIC_d4d_core.yaml

poetry run d4d provenance record --project VOICE_PEDIATRIC --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1 --project VOICE_PEDIATRIC
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1
```

### Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | pass, no issues found |
| Full — ontology term validation | pass |
| Core — LinkML schema validation (`CoreDataset`) | pass, no issues found |
| Core — ontology term validation | pass |
| Full/core pair consistency | PASS, 78 schema-identical slots, 0 errors, 1 semantic-review warning (reviewed above) |
| Phase 3 corrections | 9 shape/slot-filling, 1 Phase 2 back-port, 0 factual contradictions |
| Phase 4 divergence between full and core | none |

Nothing diverged between the two records on any schema-identical slot. The only difference in the
projected pair is a `source_caveats` string on the metadata distribution, which is evidence
commentary about the projection itself and carries no conflicting dataset fact.
