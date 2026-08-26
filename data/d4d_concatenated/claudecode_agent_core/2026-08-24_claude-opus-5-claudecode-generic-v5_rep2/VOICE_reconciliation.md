# VOICE full/core reconciliation — 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2

Runtime: Claude Code. Provider: Anthropic. Model: claude-opus-5. Mode: four-phase
project agent, generic-v5 prompt. Arm: BASELINE (input documents only).

Declared input bundle: `data/preprocessed/concatenated/VOICE_preprocessed.txt`
(md5 `dcd717170da6762569c0b4eeafc1c3d2`, 11 sources).

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/VOICE_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is the **adult Bridge2AI-Voice
dataset published on PhysioNet**, identified by `doi:10.13026/37yb-1t42`, the
version-independent DOI the PhysioNet pages label "DOI (latest version)". The record
describes version 3.1.0 (published 1 May 2026, version DOI 10.13026/8xbn-nq66) as the
current release and carries the earlier releases through `version_access` and
`distribution_dates`.

This is the referent the project's scope declaration names. The bundle also contains
the PhysioNet page for the **Bridge2AI-Voice Pediatric Dataset**
(`doi:10.13026/mf9s-5r03`), which the manifest declares related but distinct. Its
facts are not merged: it appears once, in `related_datasets`, with a description
stating what distinguishes it (300 participants aged 2–18 at the Hospital for Sick
Children, collected with reproschema-ui, approved by that hospital's research ethics
board rather than by the USF IRB). Those pediatric counts, that ethics approval and
that PhysioNet page are confined to the one related-dataset description; `instances`
counts adult participants and adult recordings, `ethical_reviews` records the reviews
governing the adult collection, and `distribution_formats` records the access routes
for this dataset alone. The same referent is held in both records: `id`, `doi`,
`version`, `page` and `publisher` are identical in full and core.

Two further scoping decisions worth naming, because the bundle invites conflating them
with the referent:

- The **IRB protocol** (`irb_protocol`) describes the Bridge2AI Voice Data Acquisition
  study, not any published release. Its statements are used where they describe how
  the released data came to exist (consent, compensation, oversight, retention) and
  are marked as protocol-level where they describe intentions rather than the release
  (the phased four-year acquisition, the 30,000-participant target).
- The **feasibility publication** (`feasibility_publication`) reports a separate 2023
  single-site study of the collection application with 47 participants, in which audio
  was not collected. None of its counts appear anywhere in either record.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs were the declared bundle and the two schema files, plus the manifest
read through `d4d download scope --project VOICE` and `d4d download priority --project
VOICE`. No prior full or core D4D record was read, opened, grepped or consulted; no
file under `data/d4d_concatenated/` or `data/ro-crate_packages/` was accessed. No
evaluation report or reconciliation report from any earlier run was used. No live web
content was fetched. Structure was derived at runtime from the schemas with LinkML
`SchemaView` (`Dataset` in the full schema, `CoreDataset` in the core schema, plus the
induced shape of every nested class used), not from any prior record or documentation
example.

### Source ranking and how disagreements were resolved

The manifest ranks VOICE sources: tier 1 the four PhysioNet data-resource pages, tier 2
the project documentation site, IRB protocol and DUA, tier 3 the feasibility
publication and the audiomics white paper, tier 4 the NIH RePORTER page. Six
disagreements were found. Each is recorded on the object it affects rather than in a
single lump.

| # | Disagreement | What each source said | Resolution |
|---|---|---|---|
| 1 | Recording count | Documentation (t2): "~61,937 voice-derived recordings" for v3.0. PhysioNet (t1): per-feature row counts 28,640–32,522 for v3.1.0 | Higher rank preferred; no single total asserted, since the two are not the same quantity. Recorded in `instances[1].source_caveats` |
| 2 | Enrollment target | IRB protocol (t2): 30,000 participants. Documentation (t2): "10,000 voices", "Enrollment Count (Anticipated by 2027): 10,000" | **Same rank — ranking cannot decide.** Neither figure is asserted as the dataset's target; the disagreement is stated in the record-level `source_caveats` |
| 3 | Instance relationships | Documentation (t2): "No, they are unrelated". PhysioNet (t1): participant_id / session_id / task_name make the linkage explicit, and a participant may have several sessions | Higher rank preferred; recorded in `relationships[0].source_caveats` |
| 4 | Maintainer | Documentation (t2): Health Data Nexus / T-CAIREM, University of Toronto. PhysioNet (t1): MIT Laboratory for Computational Physiology | Read as applying to different platforms and releases; both retained as separate `maintainers` entries with the Health Data Nexus one scoped to the earlier release, and the disagreement recorded on it |
| 5 | Availability of old versions | Documentation (t2): older versions continue to be supported by default. PhysioNet (t1): "The files for this version of the project (1.1) are no longer available" | Higher rank preferred; recorded in `version_access.source_caveats` |
| 6 | Two personal names | Documentation (t2): "Jennifer Sui", "Frank Rudzizc". PhysioNet author lists (t1): "Jennifer Siu", "Frank Rudzicz" | Higher rank preferred; recorded on each `creators` entry |

Two further tensions were resolved by **scope rather than by rank**, because the
sources describe different releases rather than contradicting each other: the access
policy (v1.1 "restricted access, registered users"; v3.0.0 and v3.1.0 "credentialed
access") and the distribution platform (v1.0 on Health Data Nexus under
10.57764/qb6h-em84; v1.1 onward on PhysioNet). Both are stated with their version
scope explicit, in `distribution_formats` and `related_datasets`.

One tension is internal to a single source. The documentation site both lists race,
sexual orientation and socioeconomic data as sensitive elements present, and states in
its v3.0.0 de-identification notes that all fields encoded as sensitive in the REDCap
dictionary were removed. Both statements are carried in `sensitive_elements`, with the
narrower scope of the current release named.

### Identifier audit

The v5 rule that an identifier naming something outside this dataset must come from the
evidence was applied strictly, and it removed content that would otherwise have been
easy to supply:

- **No ROR values.** The bundle names 15-plus organizations in prose and supplies a
  registry identifier for none of them. Every `Organization` carries `name` only.
- **No ORCID values, and no `Person` objects at all.** `Person` declares `id` as
  required and as its identifier slot. A person has a referent outside this record, so
  a minted fragment on the dataset's DOI would not identify them, and the bundle
  supplies no ORCID. The four `Person`-ranged slots the schemas declare —
  `Creator.principal_investigator`, `LicenseAndUseTerms.contact_person`,
  `EthicalReview.contact_person`, `DataGovernance.committee_contact` and
  `committee_members`, `ExportControlRegulatoryRestrictions.governance_committee_contact`
  — are therefore left absent in both records. The people themselves are not lost: they
  are named in `creators` entries with their affiliations, and the governance contact
  address `DACO@b2ai-voice.org` is stated in `data_governance.access_review_process`
  and in `raw_data_sources`.
- **CURIE form where a prefix is declared.** `id`, `doi`, `latest_version_doi` and the
  three `related_datasets.target_dataset` values use the `doi:` prefix the schema
  declares, never the doi.org resolver form. The `doi` slot, whose declared range is
  `string` with an anchored pattern, carries the bare DOI `10.13026/37yb-1t42` —
  neither prefixed nor resolved.
- **URLs only where the range is `uri` or where no declared prefix fits.**
  `access_urls`, `access_url`, `contribution_url` and `Software.url` are declared `uri`
  and hold URLs. `publisher` is `uriorcurie`; PhysioNet's only identifier in the bundle
  is `RRID:SCR_007345`, whose prefix the schema does not declare, so rather than invent
  a prefix the record uses the resolvable `https://physionet.org/`. The two
  `Software.id` values use the GitHub URLs the bundle supplies for the same reason.
- **Minting only for parts of this dataset.** The three file collections and the eleven
  files under them exist nowhere outside this record, so each is a fragment on the
  dataset's own attested DOI CURIE (`doi:10.13026/37yb-1t42#features`,
  `…#features-ppgs`, and so on). No new namespace was invented.

`check_run` against the bundle reports **grounded 1, minted_fragment 14, absent 0**.

### Corrections made in Phase 3

One. Phase 2 found a core field the Phase 1 full record had left empty and the bundle
supports: `machine_annotation_tools`. Whisper Large generated the transcripts, and
openSMILE, Praat, parselmouth, torchaudio, sparc and ppgs produced the released
features; the documentation's audit answer states that off-the-shelf models used for
transcription have not been audited for correctness, which fills `tool_accuracy`. It
was **written into the full record first**, in the full-schema slot, and the full
record was re-validated before core was rebuilt from it.

Three other empty core fields were examined and deliberately left empty, because
populating them would record an absence rather than answer the field:
`annotation_analyses` (a single labeler per instance, so no agreement metric exists),
`imputation_protocols` (no imputation is performed), and `use_repository` (the
documentation answers that no repository of downstream uses exists).
`at_risk_populations` was left empty because whether the mood and psychiatric cohort
constitutes an at-risk group is a judgement the bundle does not make. `other_tasks` was
left empty because the only candidate content is already `intended_uses`. `is_tabular`
and `dialect` were left empty because the release mixes tensor Parquet files with
tab-delimited phenotype tables and no dataset-level answer is supported.

### Shape audit

Every emitted value was checked against its slot's declared range and description.
Enum values are drawn from the schema's own permissible values only
(`limitation_type`, `bias_type`, `collection_type`, `relationship_type`,
`data_use_permission`, `hipaa_compliant`, `confidentiality_level`,
`CreatorOrMaintainerEnum` roles, `DataStandardEnum`, `FormatEnum`). No prose sits in a
slot the schema declares as a list, and no list item carries commentary embedded inside
a name or affiliation value. Evidence commentary — source conflicts, what a value was
transcribed from, the version scope of a claim — is in `source_caveats` at nine places
and nowhere else; `notes` is not used in either record. Multivalued slots emit one
object per distinct entity rather than collapsing: 17 creators, 3 grants, 3 purposes, 3
addressing gaps, 2 instances, 3 known biases, 4 known limitations, 3 preprocessing
strategies, 4 prohibited uses, 3 intended uses, 3 distribution formats, 3 maintainers,
2 ethical reviews, 2 collection mechanisms, 2 data collectors, 2 subpopulations, 2
anomalies, 3 related datasets.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used.

`d4d_pair_consistency` reports **PASS: 79 schema-identical slots**; projected
slots `['resources']`; per-record slots exempt and required to differ
`['conforms_to_class', 'conforms_to_schema']`. It emits one warning, the standing
`semantic-review-required` flag on `$.file_collections <-> $.distributions`, which is a
request for the review below rather than a defect.

`--sync-core` was **not run**. It was not needed: the core record was constructed as a
schema-derived projection of the Phase 3-audited full record, so every schema-identical
slot was already deeply identical, including nested mapping values and list order. The
independent check above was run on the artifacts as they stand.

### Slot inventory

The full record populates **78** top-level slots; the core record populates **68**.

Eleven slots are populated in full and absent from core because `CoreDataset` does not
declare them: `citation`, `collection_consents`, `collection_notifications`,
`consent_revocations`, `direct_collection`, `file_collections`,
`participant_compensation`, `participant_privacy`, `relationships`, `splits`,
`third_party_sharing`. One slot is populated in core and absent from full because
`Dataset` does not declare it: `distributions`. 78 − 11 + 1 = 68, so no slot is
unaccounted for. Presence matches in both directions for every schema-identical slot:
no slot is present in one record and absent from the other.

### Related-content mapping and semantic review

**`file_collections` (full) → `distributions` (core).** The validator matched all three
collections deterministically, with no unmatched core distributions. Reviewed field by
field:

| full `FileCollection` | core `CoreDistribution` | outcome |
|---|---|---|
| `id`, `name`, `path`, `description` | same slots | byte-identical for all three (`#features`, `#phenotype`, `#metadata`) |
| `collection_type` (`processed_data`, `processed_data`, `metadata`) | not declared | full-only; dropped in the projection |
| `resources` (11 `File` objects under `features`) | not declared | full-only; dropped in the projection. Their content is recoverable from the full record only |
| `bytes`, `hash`, `md5`, `sha256`, `format`, `encoding`, `compression`, `media_type` | declared | absent in both — the bundle states no byte counts, checksums or archive formats for the release, so nothing can conflict |

`total_file_count` and `total_size_bytes` are absent from the full record and are not
declared by `CoreDataset`, so there is no aggregate to compare against
distribution-level values. `is_tabular` and `dialect` are absent from both. No
conflict exists between the two representations.

**Top-level identity, version and access facts** were checked against the nested
statements that repeat them, in both records:

- `version: 3.1.0` agrees with `version_access.versions_available` (which lists 3.1.0
  last), with `distribution_dates.release_dates` (3.1.0 on 1 May 2026), and with
  `last_updated_on: 2026-05-01T00:00:00Z`.
- `issued: 2025-01-17T00:00:00Z` agrees with the first PhysioNet release date in
  `distribution_dates`.
- `doi: 10.13026/37yb-1t42` agrees with `id` and with
  `version_access.latest_version_doi`; the per-version DOIs in
  `version_access.version_details` are distinct from it by design and are labelled as
  such.
- `license: Bridge2AI Voice Registered Access License` agrees with
  `license_and_use_terms.name` and with the access description in
  `distribution_formats[0]`.
- `publisher: https://physionet.org/` agrees with `maintainers[0]` and with the
  PhysioNet access route in `distribution_formats[0]`.
- `conforms_to: Brain Imaging Data Structure v1.9.0` agrees with
  `conforms_to_standard: [BIDS]` and with `preprocessing_strategies[2]`.
- The 833-participant count in `instances[0]` agrees with the description and is not
  contradicted anywhere; the smaller historical counts (306 at v1.0, +136 at v2.0, +391
  at v3.0.0) are carried in that object's `source_caveats` with their release scope
  explicit, so a historical release is distinguished from the current one rather than
  read as a contradiction.

No unresolved contradiction remains within either record or between them.

### Prompt condition

The run was launched from the rendered instruction at `/tmp/agentic_fanout/VOICE_rep2.md`,
built from `src/download/prompts/d4d_generic_arm_prompt_v5.md`, condition
`generic_v5`. Both file headers name the condition on their `# Mode:` line and the
prompt file on their `# Prompt:` line.

## Repair

No repair phase ran. `d4d_pair_consistency` returned PASS with only the standing
semantic-review warning; `check_run` returned zero `absent` identifiers; both schema
validations and both term validations passed on the first run after the single Phase 3
back-port, which was itself re-validated. No finding required changing either record
after the report was written, so no `report_after_repair` phase exists either.

`check_report` did return one finding on its first run, and it was a finding about this
report rather than about either record: a sentence listing where the pediatric
dataset's facts had been kept out read as a claim that `instances` is not a declared
slot (`false_schema_claim`). The sentence was rewritten in place, in the Referent
section above, to say the same thing positively. Neither YAML file changed, so this is
not a repair in the sense step 9 defines. `check_report` now returns zero findings.

## Commands run

```bash
poetry run d4d download scope --project VOICE
poetry run d4d download priority --project VOICE

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run python -c "... data_sheets_schema.grounding.check_run ..."
poetry run python -c "... data_sheets_schema.report_claims.check_report ..."

poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt ...
poetry run d4d runs check --strict
poetry run d4d download scope --check --project VOICE
```

## Final results

- Full record: schema validation **passed**, term validation **passed**, 78 top-level
  slots.
- Core record: schema validation **passed**, term validation **passed**, 68 top-level
  slots.
- Pair consistency: **PASS**, 79 schema-identical slots, 1 semantic-review warning
  reviewed above.
- Identifier grounding: grounded 1, minted_fragment 14, **absent 0**.
- Corrections: one Phase 3 back-port (`machine_annotation_tools`). Nothing else
  diverged between the two records.
