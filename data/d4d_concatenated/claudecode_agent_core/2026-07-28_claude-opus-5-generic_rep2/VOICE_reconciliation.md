# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep2

- **Arm:** BASELINE (input documents only)
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- **Runtime / model:** Claude Code, Anthropic, `claude-opus-5[1m]`, temperature 0.0
- **Mode:** four-phase project agent (Phase 1 full, Phase 2 core, Phase 3 source/provenance audit, Phase 4 strict reconciliation), run sequentially
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 documents; source manifest `data/preprocessed/source_manifest.yaml`)
- **Outputs:**
  - Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d.yaml`
  - Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d_core.yaml`

## Referent choice

`Dataset` admits one referent. The declared bundle documents several distinct
published artefacts under the Bridge2AI-Voice name: an adult PhysioNet project
(`b2ai-voice`, versions 1.1 through 3.1.0), a separate pediatric PhysioNet
project (`b2ai-voice-pediatric`, versions 1.0.0 and 1.1.0), an earlier
feature-only release on Health Data Nexus, and a controlled-access raw-audio
collection on Synapse.

The referent chosen is **the Bridge2AI-Voice dataset as an umbrella resource**,
because that is how the project documentation in the bundle presents it ("The
Bridge2AI-Voice (B2AI-Voice) dataset is a large, ethically sourced ... voice
dataset", with the adult and pediatric releases described as its adult and
pediatric datasets). The adult and pediatric releases are carried as two
`resources` entries so that their distinct cohorts, versions, DOIs and counts
are never merged into a single claim, as the uniform decision rules require.

Consequences held to consistently in both records:

- Release-scoped identity facts (`version`, `doi`, `issued`, `last_updated_on`,
  `citation`, `version_access.latest_version_doi`, file inventories) are stated
  on the resources, not at the top level.
- Facts that genuinely span both releases (license, access model, funder,
  creators, ethics, purposes, collection method, de-identification) are stated
  at the top level.
- Top-level `version`, `doi`, `issued` and `citation` are deliberately absent:
  the umbrella has no single value for them and inventing one would merge
  distinct entities.

## Phase 3 — source and provenance audit

### Provenance boundary

- Factual inputs used: the declared bundle only, plus the full and core LinkML
  schemas for structure. Structure was derived at run time from
  `SchemaView` dumps of class `Dataset` and class `CoreDataset` rather than
  from any example record.
- No prior generated D4D record was read, opened, grepped or consulted. Nothing
  under `data/d4d_concatenated/` was read except the exact same-run full record
  during Phase 2, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
  `data/ro-crate_packages/` was touched.
- No live web content was fetched.
- Phase 2 read exactly
  `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d.yaml`,
  which carries this run's version label.

### Source review findings

1. **Conflicting definitions of "high volume expert clinic" (corrected).**
   The project documentation defines an HVEC as a clinic seeing more than 50
   patients per month from the same disease category; the IRB protocol defines
   it as a clinic or programme with a volume of over 1,000 patients per year.
   The Phase 1 record initially carried only the documentation figure. Corrected
   in `sampling_strategies` to state both definitions with attribution, and
   propagated to core (this slot is schema-identical).
2. **Conflicting stated dataset-size targets (represented, not resolved).**
   The documentation states a flagship dataset of 10,000 voices and an
   anticipated enrolment of 10,000 by 2027; the audiomics viewpoint states
   30,000 human voices; the IRB protocol states a sample size of 30,000
   participants. All three are recorded in a dedicated `purposes` entry rather
   than one being selected.
3. **Conflicting recording counts (represented, not resolved).**
   The documentation states ~61,937 voice-derived recordings for v3.0, while the
   PhysioNet v3.0.0 and v3.1.0 pages give per-feature counts in the 28,640 to
   32,522 range. The `instances` entry for adult recordings lists both and
   asserts no single total; `counts` is deliberately unset there.
4. **Conflicting confidentiality statements (represented, not resolved).**
   The healthsheet answers "No" to whether the dataset contains confidential
   data, while the Data Transfer and Use Agreement states the Data is
   Personally Identifiable Information covered by a Certificate of
   Confidentiality. These describe different scopes (the de-identified public
   release vs. data transferred under the DTUA) and are recorded as two
   separate `confidential_elements` entries with explicit scope notes.
5. **Conflicting statements about free-speech transcripts (represented).**
   The healthsheet says the dataset includes transcriptions of free speech; the
   PhysioNet release notes say transcripts of free speech audio were removed.
   Both are recorded in `content_warnings` with a scope note.
6. **Conflicting spelling of a pediatric lead investigator (represented).**
   "Jennifer Siu" in the PhysioNet author lists, "Jennifer Sui" in the project
   documentation. Both spellings are reproduced in the creator description.
7. **Stale-scoped facts kept only with explicit scope.** IRB number 004890, the
   47-participant feasibility metrics and the 2023-06-05 to 2023-07-28 dates
   belong to the single-site application feasibility study, not to the released
   dataset; each carries a scope note. The healthsheet's "v2.0.0" and "v3.0.0"
   statements are labelled by release where they conflict with v3.1.0.
8. **Preferred current release where sources disagree.** The manifest records
   that PhysioNet 3.1.0 supersedes the sheet-selected 3.0.0; v3.1.0 values are
   used for the adult resource's version, DOI, issue date and feature counts,
   with the v3.0.0 counts retained under explicit version scope.
9. **Fabricated-identifier removal.** Draft object identifiers minted in the
   `orcid.org` and `ror.org` namespaces were replaced with project-namespace
   URIs (`https://b2ai-voice.org/person/...`,
   `https://b2ai-voice.org/organization/...`,
   `https://b2ai-voice.org/software/...`), because the bundle supplies no ORCID
   or ROR identifiers and minting them would assert identifiers that are not in
   evidence. Software identifiers that *are* in the bundle
   (`https://github.com/sensein/b2aiprep`, `https://github.com/sensein/senselab`,
   `https://github.com/eipm/bridge2ai-redcap`) were kept.

No unsupported, stale or mis-scoped assertion was left uncorrected. No Phase 2
discovery required a back-port, because core was derived from the audited full
record and adds no independent factual content.

### Structural findings from validation

- `Creator.principal_investigator`, `Person.affiliation`,
  `FundingMechanism.grantor`, `EthicalReview.contact_person`,
  `EthicalReview.reviewing_organization` and `Instance.missing_information` are
  **not inlined** in the schema and take identifier references, not nested
  objects. The draft inlined them; corrected. The human-readable content that
  the nested objects carried was moved into the corresponding `description` and
  `review_details` fields so no evidence was lost.
- `issued` / `last_updated_on` are `datetime` and require a timezone-bearing
  ISO 8601 value; `2026-05-01T00:00:00` fails and `2026-05-01T00:00:00Z` passes.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time from `Dataset` and `CoreDataset` with
LinkML `SchemaView`; no hand-written field list was used.

- `CoreDataset` declares **79** slots.
- **76** of them are schema-identical to their `Dataset` counterparts (same
  induced range and cardinality). All 76 were copied from the Phase 3-audited
  full record without condensation, paraphrase, reordering or omission, and the
  validator confirms deep identity.
- **3** are core-only or projected: `distributions`, `dialect`, `resources`.
- **12** full slots have no `CoreDataset` counterpart and are therefore absent
  from core by schema, not by choice: `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `participant_compensation`, `participant_privacy`, `related_datasets`,
  `relationships`, `splits`, `subsets`, `third_party_sharing`, `variables`.
  Their absence was confirmed programmatically against `CoreDataset`.
- Top-level populated slots: full 79, core 67 (79 − 12). No core-only top-level
  slot exists.

### Projected slot: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. Resources match by
`id` with equal coverage (2 in each: the adult and pediatric PhysioNet
releases). Every nested schema-identical slot is deeply identical. Full-only
nested slots omitted from the projection: `file_collections` (both resources)
and `citation` (adult resource; `citation` is not a `CoreDataset` slot).

### Related, non-identical content: semantic review

- **`file_collections` → `distributions`.** Each of the 3 adult and 3 pediatric
  file collections maps one-to-one to a `CoreDistribution` with the same `id`,
  `name`, `description` and `path`; the id sequences are identical in order.
  `collection_type` has no `CoreDistribution` counterpart and is dropped.
  `format`, `compression`, `encoding`, `media_type`, `bytes`, `hash`, `md5` and
  `sha256` are left unset in core because the bundle states none of them, and
  because the collections are mixed-format folders (Parquet, TSV, JSON) for
  which the `FormatEnum` has no admissible value. No conflict: core asserts
  nothing the full record contradicts, and vice versa.
- **`total_file_count` / `total_size_bytes` vs. distribution-level values.**
  Both are absent from the full record because the bundle states no file count
  or byte total for any release; there is nothing to compare and no conflict.
- **`dialect`, formats and `is_tabular`.** `dialect` is core-only and is set on
  each resource as `delimiter: "\t"`, `header: "true"`, which is what the
  bundle states for the phenotype tables (`pd.read_csv("demographics.tsv",
  sep="\t", header=0)`; "tab delimited file with one row per unique
  participant"). `is_tabular` is `false` in both records and is not
  contradicted by the dialect: the dialect describes the phenotype tables,
  while the release as a whole is dominated by dense Parquet tensors, so the
  two statements are consistent at their respective scopes. No `format` value
  is asserted anywhere in either record.
- **Top-level identity/version/access vs. resources and version history.**
  Top-level `license` ("Bridge2AI Voice Registered Access License") matches the
  license on both resources and the `license_and_use_terms` narrative.
  Top-level `publisher`, `status` and `page` are consistent with both
  resources. `version_access` at the top level lists the adult releases 1.1,
  2.0.0, 2.0.1, 3.0.0, 3.1.0 and the pediatric releases 1.0.0, 1.1.0, which
  agree with the per-resource `version_access.versions_available`, with
  `distribution_dates`, and with the `version`/`issued` values on each
  resource. Historical releases are distinguished from current releases by
  explicit version labels throughout rather than being treated as
  contradictions.
- **Repeated identifiers.** Every DOI appears with a consistent version scope
  across the records: adult 1.1 `10.13026/249v-w155`, adult 3.0.0
  `10.13026/k81f-qr68`, adult 3.1.0 `10.13026/8xbn-nq66`, adult latest
  `10.13026/37yb-1t42`, pediatric 1.1.0 `10.13026/h995-bt35`, pediatric latest
  `10.13026/mf9s-5r03`, Health Data Nexus v1.0 `10.57764/qb6h-em84`. Grant
  numbers `OT2OD032720`, `3OT2OD032720-01S3`, `3OT2OD032720-01S1` and
  `1OT2OD032720-01` are each attributed to the source that states them.

### Files changed in Phase 3/4

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d.yaml`
  (HVEC definition correction; non-inlined reference corrections; datetime
  format corrections; identifier-namespace corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d_core.yaml`
  (regenerated from the corrected full record)

`--sync-core` was not needed: core is derived from the audited full record, so
the pair validator passed on its first independent run.

## Commands

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/VOICE_d4d_core.yaml

poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt
```

## Results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full ontology term validation | Validation passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core ontology term validation | Validation passed |
| Schema-derived pair consistency | PASS: 76 schema-identical slots; projected slots = `['resources']` |
| Prior-D4D reuse | None; provenance boundary held for all four phases |
| Unresolved contradictions within or between records | None |

Informational metadata (not a quality gate): full 1,480 lines / 79 top-level
slots / 952 populated slot instances including nested objects; core 1,222 lines
/ 67 top-level slots / 811 populated slot instances including nested objects.
