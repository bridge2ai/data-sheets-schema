# AI_READI full/core reconciliation — 2026-08-24_claude-opus-5-claudecode-generic-v5_rep1

Runtime: Claude Code. Provider: Anthropic. Model: claude-opus-5. Reasoning effort: high
(asserted by the launcher; this runtime cannot observe its own accounting).
Mode: four-phase project agent, generic-v5 prompt. Arm: BASELINE (input documents only).

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1/AI_READI_d4d_core.yaml`
- Declared input bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt`

Full record: 74 populated top-level slots, 1947 lines. Core record: 60 populated
top-level slots, 1407 lines. Line and slot counts are informational, not a quality gate.

## Referent

`Dataset` admits one referent. This record is about **the AI-READI dataset as published
on FAIRhub, at version 3.0.0, DOI 10.60775/fairhub.3** — the referent the manifest's
`scope:` block declares for this project. The manifest's referent note states that
fairhub.1 and fairhub.2 are earlier releases of the same dataset rather than separate
datasets, and this record follows that: the three releases are represented through
`version_access` and `distribution_dates`, not as separate datasets and not through
`related_datasets`. The project declares no related-but-distinct dataset, so there was
nothing for the record to conflate. The referent is held consistently across both files;
`id`, `doi`, `version`, `license`, `issued`, `status` and `page` are identical in each.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs were the declared bundle and the two LinkML schemas, nothing else.
Structure was derived from the schemas at runtime with `SchemaView` rather than read from
any example record. Supporting non-factual reads were the run instruction, the provenance
guard, the four-phase playbook, `/d4d-agent`, the uniform decision rules, and the source
manifest (for the scope declaration, the `source_priority` ranking and the `naming:`
canonical label).

No prior full or core D4D record was read, from any arm, label or date. Nothing under
`data/d4d_concatenated/` was opened except the two files this run wrote. The run's own
label directory was listed by filename only, to establish that no AI_READI artifact
existed under it and that this was therefore a fresh run rather than a resume; the
`CHORUS_d4d.yaml` that sits in that directory belongs to another project and was not
opened, since a current-run full record for another project is forbidden as a factual
source. No evaluation report, reconciliation report or `*_crate_d4d.yaml` was read.

### Source disagreements and how each was decided

The manifest ranks AI_READI's sources in four tiers: tier 1 the FAIRhub data resource
records and the RO-Crate, tier 2 the documentation, license and IRB protocol, tier 3 the
BMJ Open and Nature Metabolism publications, tier 4 the NIH RePORTER page.

| Disagreement | Sources | Decision |
|---|---|---|
| Expanded project name — "Equitable" vs "Exploratory" Atlas | BMJ Open (t3) vs FAIRhub API, README, healthsheet, RO-Crate, RePORTER | Preferred tier 1: "Exploratory" |
| Target enrollment — 4600 vs 4000 | IRB protocol (t2) vs FAIRhub study description (t1), BMJ Open, Nature, RePORTER | Preferred tier 1: 4000 |
| Enrolment start — 18 July 2023 vs 2023-07-19 | BMJ Open (t3) vs FAIRhub (t1) | Preferred tier 1: 2023-07-19 |
| De-identification — "NoDeIdentification" vs HIPAA Safe Harbor | FAIRhub API (t1) vs Nature Metabolism (t3) | Stated tier 1; tier 3 recorded alongside, not dropped |
| PI affiliation — Washington University in St. Louis vs University of Washington | FAIRhub API (t1) vs RO-Crate (t1) | **Same tier: not decided.** Both organizations carried as affiliations |
| Publisher — FAIRhub vs AI-READI Consortium | FAIRhub API (t1) vs RO-Crate (t1) | **Same tier: not decided.** `publisher` is single-valued, so left unpopulated |
| IRB name — "Washington University IRB" vs University of Washington IRB | RO-Crate (t1) vs BMJ Open, healthsheet, IRB protocol | Both readings recorded on the review entry |

Each is recorded in the record's own `source_caveats`, naming what each source said and
which was preferred, so a reader of the record sees the disagreement without reading this
report. Where the ranking could not decide, no value was silently selected.

The award number is a further identifier discrepancy: the healthsheet writes
`OT2ODO32644`, with a letter O in place of the zero, while the FAIRhub funding reference,
the FAIRhub study description, NIH RePORTER, the RO-Crate and both publications give
`OT2OD032644`. The corrected form is stated and the typo is recorded on the funder entry.

### Internal consistency checks against the bundle

Arithmetic in the record was checked against the bundle rather than assumed. The
recommended split figures reconcile in every direction: 1576 + 352 + 352 = 2280; within
each split the race/ethnicity, sex and diabetes-status counts each sum to that split's
total; and the per-group totals across the three splits reproduce the published totals
(380 / 545 / 519 / 836 by race and ethnicity, 951 / 1329 by sex, 776 / 560 / 686 / 258 by
diabetes status). The version participant counts reconcile likewise: 204, then 863 more
for 1067, then 1213 more for 2280.

Two figures do **not** reconcile, and the record says so rather than smoothing them. The
nine datatype directories sum to 356,334 files and 3,815,969,360,064 bytes, which is 9
files and 419,614 bytes short of the declared totals of 356,343 files and
3,815,969,779,678 bytes. The bundle does not say what the remainder is; no attribution
was invented and `total_file_count` and `total_size_bytes` state the declared totals.

### Evidence the record deliberately does not carry

- **`publisher`** — two tier-1 sources disagree and the slot admits one value.
- **`related_datasets`** — the bundle records a child FAIRhub dataset (id 4, "A smaller
  version is available for pipeline development") but states no DOI or URL for it, and
  `target_dataset` wants an identifier. The associated publications and documentation
  sites are not datasets, so they are carried in `external_resources` instead, which is
  the slot for them.
- **`labeling_strategies`, `annotation_analyses`, `machine_annotation_tools`,
  `imputation_protocols`, `existing_uses`, `use_repository`** — the healthsheet answers
  each of these with a bare "N/A" or "No". Recording "no labels are provided" in a slot
  whose fields ask for the labeling platform, protocol and inter-annotator agreement
  would populate the slot without answering it. The fact itself is carried structurally
  by `instances[0].label: false` and in that instance's `notes`.
- **`at_risk_populations`, `errata`** — the corresponding IRB checkboxes and healthsheet
  answers are blank in the bundle.
- **`data_substrate`** — declared range `uriorcurie` and documented as a term from the
  Bridge2AI standards registry, which the bundle states none of.
- **Per-test clinical laboratory variables** — Table 2 of the BMJ Open protocol lists
  roughly 50 assays with units, reference ranges and rationales, but the PDF-to-text
  extraction emits the test names, units, ranges and rationales as four separate runs
  rather than aligned rows. Reconstructing the pairings would have meant inventing them,
  so only variables stated unambiguously in prose were recorded in `variables`.

### Shape and slot-filling corrections made in Phase 3

The audit found evidence commentary sitting in `description` slots that have a
`source_caveats` sibling. Corrected in the full record and then re-projected into core:

1. Sixteen `creators` entries carried "recorded in the FAIRhub study description" inside
   `description`; the attribution moved to `source_caveats` and `description` now carries
   the person's role.
2. The two `Organization` objects representing Aaron Lee's disputed affiliations carried
   the whole source-disagreement argument in `description`; moved to `source_caveats`.
3. `data_governance.accountable_organization.description` carried attribution; split
   between `description` and `source_caveats`.
4. `regulatory_restrictions.description` explained why the confidentiality-level
   enumeration was left unpopulated; that reasoning moved to `source_caveats`.
5. `is_deidentified.method` was largely attribution; it now states the method and the
   attribution, including the tier-3 Safe Harbor divergence, sits in `source_caveats`.
6. `ethical_reviews[1].reviewing_organization` held "AI-READI ethics team", a name the
   bundle does not supply. Removed; the four named reviewers stay in `review_details`.
7. `data_collectors[*].role` held a prose list of job titles; reduced to a role name with
   the detail left in `collector_details`, where it belongs.

Attribution remains inside a handful of typed content slots — `other_compliance`,
`consent_scope`, `anonymization_method`, `deidentification_details` — where naming which
source supplies a figure is part of the substance rather than commentary about it. That
is a deliberate stopping point, not an oversight.

### Back-porting from Phase 2

None was required. Phase 2 derived the core record from the validated Phase 1 file by
schema-driven projection rather than by re-extraction, so it discovered no fact the full
record lacked and had nothing to back-port. The Phase 3 corrections above were made in
the full record first and the core record was re-projected from it afterwards, so full is
canonical for every shared slot by construction.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView` from `Dataset` and `CoreDataset`;
no hand-written field list was used. The comparison covers **79 schema-identical slots**,
one projected slot (`resources`, `Dataset` in full and `CoreDataset` in core, absent from
both records), and two per-record slots the validator exempts (`conforms_to_class`,
`conforms_to_schema`, unpopulated in both).

Every schema-identical slot is present in both records or absent from both, and every
populated one is deeply identical including nested mapping values and list order. Nothing
was condensed, paraphrased, reordered or omitted to make core shorter: the core record's
narrative fields, including the long `description`, `source_caveats`, and the license
terms, are byte-for-byte the full record's.

### Full-only slots

Fifteen populated slots have no counterpart in `CoreDataset` and are absent from core by
schema, not by editorial choice: `citation`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `direct_collection`,
`file_collections`, `participant_compensation`, `participant_privacy`, `relationships`,
`splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
`variables`. One core-only slot is populated, `distributions`; the other core-only slot,
`dialect`, is unpopulated because the bundle states no CSV dialect parameters.

### Projection and semantic review: file_collections → distributions

The nine `file_collections` map one-to-one onto the nine `distributions`, matched by `id`;
coverage is equal and no core distribution is unmatched. Field-by-field verification found
no mismatch: `name`, `path`, `description`, `conforms_to` and `conforms_to_standard` are
identical across the projection, and `total_bytes` maps to `bytes` with identical values
summing to 3,815,969,360,064 on both sides.

`collection_type` and `file_count` are full-only nested slots that `CoreDistribution` does
not declare, and are omitted from the projection. `format` and `media_type` are added on
one distribution only: `clinical_data`, whose files the bundle explicitly describes as
CSV, one per OMOP CDM table. The other eight are left unset because `FormatEnum` and
`MediaTypeEnum` do not include DICOM, WFDB or the Open mHealth encodings — those
standards are recorded instead in `conforms_to_standard`, which does declare them. No
checksums, compression or encodings are asserted anywhere, because the bundle states
none.

Related content was checked for conflict rather than merely for presence. `is_tabular` is
`false` in both. The shared `distribution_formats` block is identical in both records and
its CSV entry agrees with the one `CoreDistribution.format` value set. All nine
collections and both records describe the same release scope, version 3.0.0. The
`total_file_count` and `total_size_bytes` comparison against the distribution-level values
is the 9-file, 419,614-byte shortfall recorded above; the represented scopes are the same,
the discrepancy is in the source, and both records carry it in `source_caveats`.

### Identifier grounding

`check_run` over both records against the declared bundle reports **11 grounded, 16
minted_fragment, 0 absent**. No identifier in either record is one the bundle does not
state. The 16 minted identifiers are all fragments on the dataset's own DOI CURIE
(`doi:10.60775/fairhub.3#…`) naming nine file collections, three recommended splits and
four distribution formats — parts of this dataset with no referent outside this record.
No prefix was invented and no registry identifier was supplied from model knowledge: every
ROR and ORCID in the record appears in the bundle, written as a CURIE against a schema-
declared prefix rather than as a resolver URL. `download_url` and `access_urls` are
declared `uri` and carry URLs; the `doi` slot carries the bare DOI.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset <full>
poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
# grounding.check_run over both records against the bundle
# report_claims.check_report over this report against both records
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep1 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt ...
poetry run d4d runs check --strict
poetry run d4d download scope --check --project AI_READI
```

`--sync-core` was not used. The pair-consistency validator passed on its own before any
synchronization was attempted, because core was projected from the audited full record
rather than extracted independently, so there was no divergence to synchronize away.

### Results

- Full record: schema validation **passed**, term validation **passed**.
- Core record: schema validation **passed**, term validation **passed**.
- Pair consistency: **PASS**, 79 schema-identical slots, one semantic-review warning for
  the `file_collections` ↔ `distributions` projection, reviewed above.
- Identifier grounding: **0 absent**.
- No repair phase ran. Nothing the checkers reported required changing either record
  after Phase 4 began, so there is no `repair` phase and no post-repair report; the
  Phase 3 corrections listed above were made before Phase 4 and both records were
  re-validated afterwards.
