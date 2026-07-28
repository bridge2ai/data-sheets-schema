# VOICE full/core reconciliation — 2026-07-27_claude-opus-5_rep1

## Run identity

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Arm | BASELINE (document corpus only) |

### Files

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml` (3039 lines)
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml` (1996 lines)
- Report: this file

Line counts are informational metadata only and are not a quality gate.

## Phase 3 — source and provenance audit

### Provenance boundary

The only factual input read in any phase was
`data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 documents, 5750 lines), with
`data/preprocessed/source_manifest.yaml` used for source scoping and curation notes.
Structure was derived exclusively from `data_sheets_schema_all.yaml` (class `Dataset`) and
`data_sheets_schema_core_all.yaml` (class `CoreDataset`) via LinkML `SchemaView`, plus
`D4D_Core.yaml` for the core field inventory.

No prior full or core D4D record, no evaluation or reconciliation report, no RO-Crate
artifact, and no live web content was read, searched, globbed, or cited. Nothing under
`data/d4d_concatenated/` or `data/d4d_individual/` was read other than this run's own two
outputs. The only generated YAML read in Phase 2 was the exact same-run Phase 1 full
record at the `2026-07-27_claude-opus-5_rep1` version label. Both headers state
`Prior D4D factual reuse: prohibited`.

### Schema-derived structure

Every emitted slot and nested object shape was resolved at runtime from the schemas:
inherited slots, class ranges, cardinality, `inlined` / `inlined_as_list`, and enum
permissible values. Four structural facts were established by probing the schema rather
than assumed, and each corrected an initial draft:

- `Creator.principal_investigator`, `FundingMechanism.grantor`,
  `EthicalReview.contact_person`, `EthicalReview.reviewing_organization`,
  `LicenseAndUseTerms.contact_person`, and
  `ExportControlRegulatoryRestrictions.governance_committee_contact` are **not** inlined
  and take string references.
- `Creator.affiliations` and `FundingMechanism.grants` **are** inlined as lists of
  `Organization` / `Grant` objects.
- `datetime`-ranged slots (`issued`) require a timezone-qualified value.
- `FormatEnum` has no Parquet member, so `format` is omitted on the Parquet-bearing
  distributions rather than approximated.

No `d4d:docExample` value was copied; no field name was invented.

### Source resolution decisions

The corpus describes **two distinct PhysioNet projects**, and the manifest curation note
for `physionet_pediatric_1_1_0` states explicitly that they are separate projects and
distinct cohorts, not versions of one another. This drove the central modelling decision
(see "Adult / pediatric distinction" below).

Version conflicts were resolved in favour of the current release in every case, with the
superseded value retained only where its historical scope is explicit:

| Conflict | Resolution |
|---|---|
| adult `physionet_3_0_0` vs `physionet_3_1_0` | v3.1.0 is canonical (manifest: "prefer this over physionet_3_0_0"). v3.0.0 feature counts and release notes appear only inside version history with explicit version labels. |
| adult `physionet_1_1` | Retained only as historical scope: 12,523 recordings / 306 participants for v1.0, 512-point FFT, registered-access wording. Never presented as current. |
| Health Data Nexus hosting (healthsheet) vs PhysioNet hosting | Both recorded. The healthsheet maintainer answer is retained verbatim and annotated that it describes the earlier feature-only release, while the current releases are on PhysioNet. |
| Docs "~61,937 voice-derived recordings" (v3.0) vs per-feature counts (v3.1.0) | Both retained with their version scope. No release-level recording count is asserted for adult v3.1.0, because none is published; `counts` is deliberately left unset on the adult recording instance. |

Three genuine source disagreements were recorded rather than silently resolved, because
no source in the bundle is authoritative over the others:

1. **Target scale.** Documentation and study metadata state 10,000 voices (anticipated
   enrollment 10,000 by 2027); the audiomics viewpoint states a 30,000-voice deliverable;
   the IRB states a sample size of 30,000. All three are reported with attribution in
   `purposes`.
2. **Person-name and degree variants.** "Jennifer Sui" (docs) vs "Jennifer Siu"
   (PhysioNet); "Alexandros Sigaras, MSc" (docs) vs "PhD" (IRB); Rudzicz affiliated to
   University of Toronto (IRB) vs Dalhousie (consortium list); Ravitsky affiliated to The
   Hastings Center (viewpoint) vs University of Montreal (consortium list). Each variant
   is noted in the relevant `Creator.description`.
3. **Grant-number corruption.** The scraped documentation contains garbled award strings
   (`3TF-OT2ActfOD032720Projectf01S1`, `Award #3Tf-OTOD03272001S2`). These were treated as
   extraction artifacts and excluded; only the clean identifiers were emitted —
   `OT2OD032720`, `3OT2OD032720-01S1` (PhysioNet acknowledgements), and
   `3OT2OD032720-01S3` (NIH RePORTER, application ID 11376382).

### Corrections applied during the audit

| # | Correction | Reason |
|---|---|---|
| 1 | `grantor` changed from a nested object to a string reference (both funders) | Schema: slot is not inlined. Caught by `linkml-validate`. |
| 2 | "Temerty Centre" → "Temerty Center" (3 occurrences) | Verbatim source spelling is "Temerty Center for Artificial Intelligence Research and Education in Medicine". |
| 3 | Pediatric participant-count provenance tightened | The docs attribute "300 participants" to pediatric v1.0; the v1.1 release notes state no new participants were released. Both facts now stated, rather than attributing the count to the docs unqualified. |

No Phase 2 discovery required a back-port, because core is a strict subset projection of
full plus the `distributions` mapping; no fact reached core that was not already in full.

### Spot-checked assertions

Every numeric and identifier assertion was re-verified by literal string match against the
source bundle: participant counts (833, 300, 306), recording counts (23,533, 12,523,
61,937, and all nine v3.1.0 per-feature counts), all seven DOIs, both Synapse identifiers,
all five NIH grant numbers, the award amount, project start/end dates, all seven release
dates, compensation amounts, IRB number 004890 (verified as belonging to the *feasibility
study*, not the data-acquisition protocol, and scoped accordingly), the AI-readiness score
table, and the hardware identifiers. Internal consistency was checked: no combined
adult+pediatric count appears anywhere, and every occurrence of 833 is adult-scoped while
every occurrence of 300 / 23,533 is pediatric-scoped.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with `SchemaView` — no hand-written field list.

- **Schema-identical slots: 76** — present-or-absent and deeply identical in both records.
- **Projected slots: 1** (`resources`, `Dataset` in full → `CoreDataset` in core).
- **Full-only slots (13, correctly absent from core):** `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `participant_compensation`, `participant_privacy`,
  `related_datasets`, `relationships`, `splits`, `third_party_sharing`, `variables`.
- **Core-only slots (1):** `distributions`. `dialect` and `is_tabular` are absent from both
  (see below).

A direct set comparison of every shared key confirms zero differing identity slots. No
narrative field was condensed, paraphrased, reordered, or omitted in core.

### `resources` projection

Both resources match by `id` with equal coverage:

| id | version | DOI | published |
|---|---|---|---|
| `d4d:VOICE_adult` | 3.1.0 | 10.13026/8xbn-nq66 | 2026-05-01 |
| `d4d:VOICE_pediatric` | 1.1.0 | 10.13026/h995-bt35 | 2026-05-01 |

Every nested key used on the resources (`description`, `distribution_formats`, `doi`,
`download_url`, `id`, `issued`, `keywords`, `license`, `name`, `page`, `publisher`,
`status`, `title`, `version`, `version_access`) exists on `CoreDataset`, so the projection
is lossless — no full-only nested slot needed dropping. Nested `version_access` objects,
including the two distinct version-independent DOIs, are deeply identical across the pair.

### Related-content mapping: `file_collections` → `distributions`

Six `FileCollection` objects map one-to-one onto six `CoreDistribution` objects.
Distribution `id` values were made identical to their source `file_collection` ids so the
mapping is deterministic rather than inferred; the validator now reports
**deterministic matches=6, unmatched=0**.

| id | path | full `FileCollection` | core `CoreDistribution` additions |
|---|---|---|---|
| `d4d:VOICE_files_adult_features` | `features/` | v3.1.0, `processed_data` | — |
| `d4d:VOICE_files_adult_phenotype` | `phenotype/` | v3.1.0, `processed_data`+`metadata` | `format: TSV`, `media_type: text/tab-separated-values` |
| `d4d:VOICE_files_adult_metadata` | `metadata/` | v3.1.0, `metadata` | — |
| `d4d:VOICE_files_pediatric_features` | `features/` | v1.1.0, `processed_data` | — |
| `d4d:VOICE_files_pediatric_phenotype` | `phenotype/` | v1.1.0, `processed_data`+`metadata` | `format: TSV`, `media_type: text/tab-separated-values` |
| `d4d:VOICE_files_pediatric_metadata` | `metadata/` | v1.1.0, `metadata` | — |

Semantic review of the mapping (the validator's warning marks that this review is
required; it is not evidence the review happened, so it is recorded here explicitly):

- **Names, descriptions, paths** are byte-identical between each pair, so no conflict is
  possible.
- **Formats.** `format` is set only on the two phenotype distributions, whose data files
  are tab-separated with accompanying JSON dictionaries. It is omitted on the four
  Parquet-bearing distributions because `FormatEnum` has no Parquet member; approximating
  it would assert a false format. `compression` is unset on both sides — no source states
  any archive compression.
- **Checksums and sizes.** `bytes`, `hash`, `md5`, `sha256` are omitted; the corpus
  publishes no byte counts or checksums for either release. Correspondingly
  `file_count`/`total_bytes` are unset on the full side and `total_file_count` /
  `total_size_bytes` are unset at top level, so there is no scope mismatch to reconcile.
- **Release scope.** Each collection/distribution pair carries a cohort-scoped name and,
  on the full side, an explicit `version` (3.1.0 or 1.1.0) and cohort-specific
  `download_url`, so adult and pediatric file trees are never merged despite sharing the
  same relative path names.
- **`dialect` and `is_tabular`** are deliberately unset in both records. The releases are
  not a single tabular artifact — they combine Parquet tensor files with TSV tables — so a
  single top-level dialect or a single `is_tabular` boolean would be an unsupported
  assertion. Absent in both, so the identity rule is satisfied.
- **`distribution_formats` vs `distributions`.** These are complementary, not redundant:
  `distribution_formats` (identical in both records, and additionally present per-resource)
  describes access routes and platforms; `distributions` describes the file layout. No
  access URL, platform, or version statement conflicts between them.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml
```

### Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency --sync-core` | PASS — 76 identical slots, projected `['resources']` |
| `d4d_pair_consistency` (independent re-run) | PASS — 76 identical slots, projected `['resources']` |
| Distribution relation | 6 deterministic matches, 0 unmatched, 0 content conflicts |
| Errors | none |
| Warnings | 1 — `semantic-review-required`, discharged in the section above |

Files changed by Phase 4: only the core record, by the single permitted `--sync-core`
synchronization plus the distribution-id alignment described above. The full record was
not modified after Phase 3.

## Adult / pediatric distinction

The corpus covers two distinct cohorts published as two separate PhysioNet projects. They
are represented as two sibling entries under `resources`, not as versions of one another
and not as `subsets` — `subsets` exists only on `Dataset`, so it would have been dropped
from the exchange layer, whereas `resources` projects into core and preserves the
distinction end to end.

- **Top-level record** is the Bridge2AI-Voice programme. It deliberately carries **no**
  top-level `version`, `doi`, or `issued`, because any single value would conflate the two
  release lines. Programme-level `version_access` likewise omits `latest_version_doi` and
  instead lists both lines separately, with an explicit statement that "pediatric v1.1.0 is
  not an earlier version of adult v3.1.0".
- **`d4d:VOICE_adult`** — PhysioNet project `b2ai-voice`, v3.1.0, DOI 10.13026/8xbn-nq66,
  latest-version DOI 10.13026/37yb-1t42, published 2026-05-01, 833 participants across five
  North American sites, collected with the Bridge2AI-Voice iOS/Web app on iPads with an
  Avid AE-36 microphone, governed by the USF Single IRB, raw audio via Synapse
  `syn72370534`. Full version history: v1.0 (Health Data Nexus) → v1.1 → v2.0.0 → v2.0.1 →
  v3.0.0 → v3.1.0.
- **`d4d:VOICE_pediatric`** — PhysioNet project `b2ai-voice-pediatric`, v1.1.0, DOI
  10.13026/h995-bt35, latest-version DOI 10.13026/mf9s-5r03, published 2026-05-01, 300
  participants aged 2–18 and 23,533 derived recordings, recruited solely at the Hospital
  for Sick Children (SickKids), collected with reproschema-ui, governed by the SickKids
  Research Ethics Board, raw audio via Synapse `syn73617068`. Version history: v1.0.0 →
  v1.1.0.

The distinction is carried consistently through every affected slot rather than only in
`resources`:

| Slot | How the two cohorts are kept separate |
|---|---|
| `instances` | Four separate instances: adult participant (833), pediatric participant (300), adult recording (count deliberately unset), pediatric recording (23,533). The pediatric participant entry states the count "must not be added to or conflated with the 833 adult participants". |
| `collection_mechanisms` | Two entries: adult (Bridge2AI-Voice app, iPads, Avid AE-36, REDCap export) vs pediatric (reproschema-ui, headset or built-in tablet mic, single session, parent-completed surveys). |
| `ethical_reviews` | Three entries: USF Single IRB (adult), SickKids REB (pediatric), separate UofT/MSH REB (genomic sub-study). |
| `raw_data_sources` / `raw_sources` | Separate adult and pediatric entries with distinct Synapse identifiers. |
| `file_collections` / `distributions` | Three adult + three pediatric collections, each version-stamped and with a cohort-specific download URL, so the shared relative paths (`features/`, `phenotype/`, `metadata/`) are never merged. |
| `distribution_formats` / `distribution_dates` | Separate adult and pediatric entries; the two release-date lists are never interleaved. |
| `sampling_strategies` | Separate eligibility criteria: adult ≥18 with English or Spanish; pediatric 2–18 with English proficiency, excluding non-verbal participants and those over 18. |
| `at_risk_populations` / `participant_compensation` | Pediatric-specific assent and guardian-consent procedures; compensation recorded as adult-only. |
| `version_access` | Independent version lines with independent latest-version DOIs, plus an explicit warning against comparing or merging the two version numbers. |
