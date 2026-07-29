# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep1

- **Project**: VOICE (Bridge2AI-Voice)
- **Run label**: `2026-07-28_claude-opus-5-deprimed_rep1`
- **Arm**: BASELINE (input documents only)
- **Runtime / provider / model**: Claude Code / Anthropic / `claude-opus-5[1m]`
- **Mode**: four-phase project agent, de-primed; temperature 0.0
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml`

## Phase 3 — source and provenance audit

### Evidence boundary

Factual inputs read during this run, and nothing else:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 documents, 377,706 bytes)
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)

Instruction inputs: `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
`.claude/commands/d4d-agent.md`, `src/data_sheets_schema/provenance.py` (slot-count semantics only).

No prior full or core D4D record was read, opened, grepped, or cited, from any arm, label or
date. The only listing of `data/d4d_concatenated/` performed was a directory-name listing
(`ls`) used to confirm that the declared output directory did not already contain a VOICE
record; no file under that tree was opened. No evaluation report, reconciliation report, test
fixture, schema example, or `d4d:docExample` value was used as a factual source. No web content
was fetched.

### Source disagreements resolved

The bundle contains several documents whose statements are superseded upstream. Each was
resolved in favour of the more recent, more authoritative source, and the superseded value was
either dropped or retained with explicit historical scope.

| Topic | Conflicting sources | Resolution |
|---|---|---|
| Current adult release | `physionet_3_0_0` (833 participants, v3.0.0, 16 Dec 2025) vs `physionet_3_1_0` (833 participants, v3.1.0, 1 May 2026) | v3.1.0 is canonical for the adult resource, per the manifest curation note. v3.0.0 retained only inside `version_access.version_details` and as a `related_datasets` `is_new_version_of` target. |
| Feature record counts | v3.0.0 counts (spectrogram 29020, sparc_ema 31616, ppgs 29031, …) vs v3.1.0 counts (29278, 28640, 29289, …) | v3.1.0 counts used in the adult `file_collections` description and in the `instances` range statement. v3.0.0 counts not carried. |
| Spectrogram FFT size | `physionet_1_1` (512-point FFT) vs v3.x (400-point FFT plus 2× time-domain downsampling) | 400-point recorded as current in `preprocessing_strategies`; the 512-point figure retained with explicit "earliest release" scope. |
| Distribution platform | Documentation healthsheet ("distributed through a data publishing platform accessible at healthdatanexus.ai"; "hosted by the Health Data Nexus … T-CAIREM … University of Toronto") vs PhysioNet project pages | PhysioNet + Synapse recorded as the current channels. Health Data Nexus recorded as a distinct `distribution_formats` entry titled "Historical release on Health Data Nexus" and as a scoped `maintainers` entry. |
| Access policy wording | `physionet_1_1` "only registered users who sign the specified data use agreement" vs v3.0.0/v3.1.0/pediatric "only credentialed users who sign the DUA" | Credentialed access recorded as current; the registered-access wording retained with explicit v1.1 scope inside `license_and_use_terms`. |
| Population scope | Documentation study-metadata block: "The current v.2.0.0 dataset contains only adult populations"; "Minimum Age 18 years (this will change when pediatric cohort is introduced)" | Not asserted as current. The pediatric release is represented as a separate resource; the 18–120 adult age band is recorded in `known_limitations` alongside the pediatric 2–18 band. |
| Pediatric release version | Documentation body ("The pediatric dataset v1.0 is now available") vs documentation banner and `physionet_pediatric_1_1_0` (v1.1.0, 1 May 2026) | v1.1.0 canonical; v1.0.0 retained in `version_access.versions_available` and as a `related_datasets` target. |
| Grant identifier strings | Documentation healthsheet funder field `3TF-OT2ActfOD032720Projectf01S1` (corrupted), site footer `3Tf-OTOD03272001S2`, RePORTER `3OT2OD032720-01S3`, PhysioNet acknowledgements `3OT2OD032720-01S1` | Only the two clean, source-attributable project numbers were recorded as `Grant` objects (`3OT2OD032720-01S3`, `3OT2OD032720-01S1`) plus the core project number `OT2OD032720`. The corrupted string was not reproduced; the site-footer string is quoted verbatim in the funder description as recorded, not normalised into a grant number. |

### Mis-scoped assertions avoided

- **App feasibility study**: the `feasibility_publication` describes a 47-participant study of the
  data acquisition application at USF Health Voice Center (5 June – 28 July 2023, IRB 004890),
  in which *audio data was not collected*. Its participants, task-completion rates and IRB number
  do not describe the released dataset. It is therefore recorded under
  `collection_mechanisms` ("Validation of the acquisition application through a feasibility
  study") and as a scoped `ethical_reviews` entry, and its 47 participants are **not** counted in
  `instances`.
- **Adult vs pediatric conflation**: per the manifest curation note, the two PhysioNet projects
  are distinct cohorts under separate protocols, not versions of one another. They are modelled as
  two entries under `resources`, each with its own version, DOI, download URL, issue date,
  version history and file inventory. No cross-cohort `DatasetRelationship` was asserted, because
  the sources state only that each is "also available on PhysioNet", not a typed relationship.
  Participant counts (833 adult, 300 pediatric) are never summed.
- **Source defect not propagated**: the PhysioNet background sections transpose the descriptions
  of "Neurological and Neurodegenerative Disorders" and "Mood and Psychiatric Disorders" (the
  neurological heading describes depressed-speech findings and vice versa). Neither transposed
  description was carried; the cohort descriptions in `subsets` were built from the
  documentation's Table 1 inclusion/exclusion and gold-standard columns instead.
- **Redacted contacts**: the documentation capture renders project contact addresses as the
  placeholder `[email protected]`. No address was invented. Only addresses that appear
  literally in the sources (the PhysioNet access-committee address, `DACO@b2ai-voice.org`) were
  recorded; the general contact address is referred to without being quoted.
- **HIPAA status**: `regulatory_restrictions.hipaa_compliant` is set to `compliant` on the basis
  of the documentation ("Does this dataset apply the HIPAA de-identification rules? Yes"), the
  HIPAA-compliant collection applications, and HIPAA-protected NIH STRIDES storage. The Data
  Transfer and Use Agreement separately states that the transferred Data "is not covered under
  HIPAA" because it is Personally Identifiable Information under OMB M-07-16. Both statements are
  recorded verbatim in `other_compliance`; they address different artefacts (the released
  de-identified dataset vs. data transferred under the DTUA) and are not treated as a
  contradiction.

### Corrections back-ported to the full record during Phase 3

Two source-supported additions were made to the full record after the initial Phase 1 pass, and
the core record was regenerated from the corrected full record.

1. **`creators[0].affiliations`** — added `Massachusetts Eye and Ear` and `Emory University`.
   Both are named in the IRB protocol's Annex C table of participating institutions and lead
   investigators per site (Phillip Song MD and Matthew Naunheim MD at MEEI; Anthony Law MD PhD at
   Emory), but are absent from the documentation's `Collaborators` list, which supplied the
   original twelve affiliations. Each carries a description recording which source names it.
   Individual-author home institutions appearing only in the feasibility publication's consortium
   group-member list (for example Florida Atlantic University, University of Central Florida,
   UT Health Houston, Dalhousie University, Boston Children's Hospital) were deliberately **not**
   added, because that list describes members' home affiliations rather than dataset
   collaborators or collection sites.
2. **`known_limitations`** — added "Criteria unmet in the project's own AI-readiness
   self-assessment", recording the criteria the project's published Precision Public Health
   (Voice) rating table scores 0: Data Quality (2.e), Domain-appropriate (5.b), Associated (5.d)
   and Contextualized (6.d), with the corresponding category percentages.

No fact was removed or altered; no fact was sourced from a generated record.

### Known residual inconsistencies in the sources

These are properties of the input documents, recorded here rather than silently normalised:

- **`Jennifer Sui` vs `Jennifer Siu`** — the documentation spells the SickKids investigator "Sui";
  the PhysioNet author lists and BibTeX spell it "Siu". The creator description quotes the
  documentation spelling; the citation strings quote the PhysioNet spelling verbatim.
- **`Frank Rudzizc`** — the documentation contains this typo once; the spelling `Frank Rudzicz`,
  used consistently elsewhere in the bundle, was recorded.
- **Site count** — the IRB protocol states "11 different academic sites across the US" in §6.1 and
  "USF and 11 other participating institutions" in §6.2, while the PhysioNet releases report five
  recording sites in the released data. Both are recorded, each attributed to its own scope
  (protocol-wide participation vs. sites contributing to the release).

### Internal consistency checks performed

Repeated identifiers, versions, dates and counts were checked for agreement within each file and
across the pair: adult DOI `10.13026/8xbn-nq66` and latest-version DOI `10.13026/37yb-1t42`;
pediatric DOI `10.13026/h995-bt35` and latest-version DOI `10.13026/mf9s-5r03`; historical DOIs
`10.13026/k81f-qr68`, `10.13026/249v-w155`, `10.57764/qb6h-em84`; Synapse identifiers
`syn72370534` and `syn73617068`; grant `OT2OD032720`; participant counts 833, 300; recording
counts 23,533 and ~61,937. The release-history arithmetic is self-consistent
(306 at v1.0, +136 at v2.0, +391 at v3.0.0 = 833). Top-level `last_updated_on`
(`2026-05-01T00:00:00Z`) agrees with both resources' `issued` values. Top-level `license` agrees
with both resources' `license`. `distribution_formats.access_urls` agree with the resources'
`download_url` values, and the raw-audio URLs agree with `raw_sources.access_url`.

### Phase 3 validation

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Results: `No issues found` (full schema), `Validation passed` (full terms), `No issues found`
(core schema), `Validation passed` (core terms). Re-run after the Phase 3 corrections with the
same results.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot inventory

Derived at run time with LinkML `SchemaView` over `Dataset` and `CoreDataset`; no hand-written
field list was used.

- **Schema-identical shared slots** (same induced range and cardinality): **76**
- **Projected shared slot** (range differs): **1** — `resources`, `Dataset` in full and
  `CoreDataset` in core
- **Full-only slots**: 17 — `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
  `splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`
- **Core-only slots**: 2 — `dialect`, `distributions`

### Populated-slot outcome

- Full top-level slots populated: **76**
- Core top-level slots populated: **64**
- Full-only slots populated in full and therefore absent from core (12): `citation`,
  `collection_consents`, `collection_notifications`, `consent_revocations`, `direct_collection`,
  `participant_compensation`, `participant_privacy`, `relationships`, `splits`, `subsets`,
  `third_party_sharing`, `variables`
- Full-only slots populated nowhere: `file_collections` at top level, `parent_datasets`,
  `total_file_count`, `total_size_bytes` (no source support for a dataset-wide file count or byte
  size; `file_collections` is populated only inside `resources`)

Every schema-identical slot is present in both records or absent from both, and every present
shared value is deeply identical, including nested mapping values and list item order. Core was
derived mechanically from the Phase 3-audited full record by selecting the `CoreDataset`-permitted
top-level slots and projecting `resources`; no shared narrative field was condensed, paraphrased,
reordered or omitted.

### Projection: `resources`

Both resources are present in both records and match by `id`, so coverage is equal:

| `id` | full nested slots | core nested slots |
|---|---|---|
| `https://physionet.org/content/b2ai-voice/` | id, name, title, description, version, doi, download_url, issued, license, publisher, page, keywords, citation, file_collections, version_access, related_datasets | id, name, title, description, version, doi, download_url, issued, license, publisher, page, keywords, version_access, distributions |
| `https://physionet.org/content/b2ai-voice-pediatric/` | same set | same set |

Every schema-identical nested slot (id, name, title, description, version, doi, download_url,
issued, license, publisher, page, keywords, version_access) is deeply identical between the two
records. The full-only nested slots `citation` and `related_datasets` are omitted from the core
projection, as required.

### Related, non-identical representations reviewed

- **`file_collections` → `distributions`.** Each of the three file collections on each resource
  (`features`, `metadata`, `phenotype`) maps one-to-one to a `CoreDistribution` with the same
  `id`, `name`, `description` and `path`. Coverage is exact in both directions (3 ↔ 3 for each
  resource, in the same order). No conflict exists on any comparable property: neither record
  asserts checksums (`hash`, `md5`, `sha256`), `bytes`, `encoding`, `compression`, `format` or
  `media_type`, because the sources supply none. `FormatEnum` has no Parquet member and the
  collections are format-mixed (Parquet plus TSV plus JSON sidecars), so `format` and
  `media_type` were deliberately left unset rather than approximated; the concrete file formats
  are stated in the shared `description` text, which is identical in both records. Release scope
  is identical: the adult collections describe v3.1.0 and the pediatric collections describe
  v1.1.0, matching each resource's `version`, `doi`, `download_url` and `issued`.
- **`total_file_count` / `total_size_bytes` vs distribution-level values.** Absent from the full
  record and from every core distribution, so there is nothing to reconcile and no scope mismatch.
  The sources report per-feature-file record counts (28,640–32,522 adult; 23,532–23,533
  pediatric) but no file count or byte size for any release.
- **`dialect`, formats, `is_tabular`.** All three are unset in both records and therefore agree.
  `is_tabular` was left unset because the releases mix dense Parquet tensor files with tabular
  TSV phenotype tables, and neither source states a dataset-level answer. `dialect` was left
  unset because `FormatDialect` carries no `name` or `description` and so cannot be scoped to the
  tab-delimited phenotype subset, which is the only part of the release for which the sources
  give a delimiter and header convention.
- **Top-level identity/version/access vs resources, version history and repeated statements.**
  Top-level `license`, `last_updated_on`, `publisher`, `page`, `status`, `keywords` and
  `description` agree with the per-resource values and with `version_access`,
  `distribution_formats`, `distribution_dates`, `raw_sources` and `license_and_use_terms`. The
  top-level record deliberately carries **no** `version` and **no** `doi`, because the two
  cohorts version independently and no single identifier in the sources covers both; the
  cohort-level `version` and `doi` live on the resources, and top-level `version_access` lists all
  eight releases with explicit cohort labels while each resource's `version_access` carries its
  own `latest_version_doi`.
- **Historical vs current releases.** Adult v1.0/v1.1/v2.0.0/v2.0.1/v3.0.0, the Health Data Nexus
  distribution channel and pediatric v1.0.0 are labelled as superseded wherever they appear, so
  their differing counts, DOIs, FFT parameters, access policies and hosting platforms are not
  contradictions of the current v3.1.0/v1.1.0 values.

### Deterministic validator

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml
```

Result: `PASS: 76 schema-identical slots; projected slots=['resources']`, with no warnings.

`--sync-core` was **not** run. The core record was generated by projection from the Phase
3-audited full record, so the pair was already deeply identical and the independent no-sync check
passed on first execution; running the mutating pass would have rewritten a file that needed no
change.

### Core coverage gaps recorded rather than worked around

`CoreDataset` has no slot for the following full-record content, so it is absent from core by
schema design and was not smuggled into a differently-named core slot:

- participant compensation amounts (`participant_compensation`)
- participant privacy and re-identification-risk detail, including the federated-learning
  architecture and the tiered-dissemination technique (`participant_privacy`) — the
  federated-learning objective itself does survive into core via `purposes`
- consent-process, notification and revocation detail (`collection_consents`,
  `collection_notifications`, `consent_revocations`) — the substantive consent content survives
  into core via `informed_consent`
- direct-collection status and countries of collection, USA and Canada (`direct_collection`)
- the six disease-cohort subsets (`subsets`) — cohort categories survive into core via
  `subpopulations.identification`, `purposes` and `instances`
- the variable dictionary for the Parquet feature files (`variables`)
- instance relationship statements (`relationships`) and split guidance (`splits`) — the
  "no recommended splits" statement survives into core via `tasks`
- third-party sharing status (`third_party_sharing`) and the citation block (`citation`) — the
  citation requirement survives into core via `use_repository`

### Files changed

- Created `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d.yaml`
  (2,633 lines, 142,068 bytes) — Phase 1, corrected in Phase 3.
- Created `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/VOICE_d4d_core.yaml`
  (1,665 lines, 108,842 bytes) — Phase 2, regenerated from the Phase 3-corrected full record.
- Created this report.

Line counts are informational metadata only, not a quality gate.

## Result

- Full: schema validation **pass**, term validation **pass**.
- Core: schema validation **pass**, term validation **pass**.
- Pair consistency: **PASS**, 76 schema-identical slots, projected slot `resources`, no warnings.
- Provenance audit: **clean** — no prior-run full or core D4D, evaluation artefact or
  reconciliation report was read or used as evidence.
- Divergence between the pair: **none**. Every schema-identical shared slot is deeply identical
  and identically present; the single projected slot and the one related-content mapping
  (`file_collections` → `distributions`) were reviewed semantically with zero unresolved
  contradictions.
