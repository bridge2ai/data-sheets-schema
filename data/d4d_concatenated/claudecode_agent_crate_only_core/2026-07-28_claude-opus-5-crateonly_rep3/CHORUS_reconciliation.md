# CHORUS full/core reconciliation — crate-only arm

| | |
|---|---|
| Run label | `2026-07-28_claude-opus-5-crateonly_rep3` |
| Arm | CRATE-ONLY (one structured source, no documents) |
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | `claude-opus-5[1m]` |
| Mode | four-phase project agent, crate-only |
| Temperature | 0.0 |
| Generated | 2026-07-28 |
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_provenance.yaml` (`record_mode: live`) |

Sole factual input: `data/preprocessed/concatenated/CHORUS_crate_only.txt`
(the reduced crate JSON-LD plus `ai_ready_score.json`).

---

## Referent

**Settled subject: the Bridge2AI CHoRUS for Clinical Care AI Dataset, version
1.0 Beta, as described by the CHoRUS RO-Crate Package.**

The crate's root entity is named "CHoRUS RO-Crate Package" and carries the ARK
`ark:59853/rocrate-chorus-ro-crate-package/`, but every substantive property
hanging off it describes the *data*, not the packaging: `rai:dataCollection`,
`rai:dataLimitations`, `rai:dataBiases`, `ethicalReview`, `irbProtocolId`,
`conditionsOfAccess`, `contentSize`, `completeness`. Its `identifier` is the DOI
`https://doi.org/10.18130/V3/XNBOPG`, and its `citation` names "The Bridge2AI
CHoRUS for Clinical Care AI Dataset ... version 1.0 Beta". So the crate is a
description *of* a dataset, and that dataset is the referent.

Consequences of that choice:

- `id` = the DOI URL (the crate's own `identifier`), not the ARK. The ARK is the
  identifier of the packaging entity, so it is recorded in
  `external_resources` ("CHoRUS RO-Crate Package") rather than as the dataset id.
- The two `hasPart` sub-crates (EHR, Waveforms) are recorded as
  `file_collections`. The full schema states that `file_collections` "Maps to
  nested RO-Crate Dataset entities via `schema:hasPart` in RO-Crate converters",
  which is exactly what these two entities are. `resources` is therefore absent
  from both records.
- `isPartOf` points at `ark:59852/organization-bridge2ai-s6VouUf8Gkm`, an
  *organization* ARK. It is not recorded in `parent_datasets` or
  `related_datasets`, because both of those slots range over datasets and the
  crate gives no evidence that this entity is one. It is recorded as an
  `ExternalResource` with a description saying exactly what the crate does and
  does not say about it.

---

## Phase 3 — source and provenance audit

### Provenance

- Files read for facts: `CHORUS_crate_only.txt` only.
- Files read for structure: `data_sheets_schema_all.yaml`,
  `data_sheets_schema_core_all.yaml`, `D4D_Core.yaml`, and
  `d4d_pair_consistency.py` (to learn the pair contract). Class shapes were
  derived at runtime with LinkML `SchemaView` (`class_induced_slots`), not from
  any example record.
- No prior full or core D4D was read, globbed, or cited. Nothing under
  `data/d4d_concatenated/` or `data/d4d_individual/` was read except this run's
  own two outputs. The withheld CHORUS artifacts
  (`CHORUS_preprocessed.txt`, `CHORUS_preprocessed_with_crate.txt`,
  `data/preprocessed/individual/CHORUS/`, `data/raw/CHORUS/`,
  `source_manifest.yaml`, `CHORUS_crate_d4d.yaml`,
  `CHORUS_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
  `ro-crate-datasheet.html`) were not opened. No web content was fetched.
- `# Source manifest:` in both headers records "not used" rather than naming
  `source_manifest.yaml`, because the manifest was withheld from this arm.

### Mechanical string audit

Every string leaf in the full record was compared against the crate text with
whitespace normalized. 64 strings did not match verbatim. Each was reviewed:

| Category | Count | Disposition |
|---|---|---|
| Authored provenance framing ("The crate records...", "Reported by the crate's AI-readiness assessment...") | 30 | Kept — these are labels on crate content, and they name their own source |
| Recombination of crate bullets (e.g. `updates.update_details[4]` folding the three `o`-level deprecation sub-bullets into one string) | 12 | Kept — content verbatim, nesting flattened |
| Capitalization/sentence-boundary normalization of a verbatim clause | 11 | Kept |
| Composed labels for `raw_data_sources` (modality + "recorded during routine clinical care at participating hospitals") | 8 | Kept — every component is stated |
| Date/unit normalization | 3 | Kept, flagged below |

Two strings drifted beyond restatement and were **corrected in Phase 3**:

1. `collection_mechanisms[1].mechanism_details[1]` read "Hospital waveform
   systems and middleware supply the real-world signal data, at variable
   sampling rates." — "supply the real-world signal data" was editorializing.
   Replaced with the crate's own clause: "Variable sampling rates across
   real-world data from hospital waveform systems and middleware".
2. `sampling_strategies[0].source_data[0]` read "The CHoRUS full cohort
   assembled from participating hospitals". "assembled from" was not stated.
   Replaced with "The CHoRUS full cohort".

Both corrections were made to the **full** record first; core was then
re-derived from the corrected full record.

### Derived (non-verbatim) values, itemized

These are the only places where the record states something the crate does not
state in those words. Each is arithmetic or format normalization, not inference
about the dataset.

| Field | Value | Derivation |
|---|---|---|
| `issued` (dataset and both file_collections) | `2026-04-03T00:00:00Z` | `datePublished: "2026-04-03"`. LinkML `datetime` requires an RFC3339 offset; the time-of-day and `Z` are format padding, not crate content. |
| `total_size_bytes` | `1201585609503` | `18136671` + `1201567472832`, the two sub-crates' `contentSize` ("18.136671 mb", "1.201567472832 tb") read as decimal SI. Both decode to exact integers under decimal SI and to non-integers under binary, which is why decimal is the right reading. The sum is consistent with the root entity's own rounded `contentSize: "1.2 tb"`. |
| `total_file_count` | `1477` | `ai_ready_score.pre_model_explainability.verifiable`: "99% of files have checksums (1469/1477)". |
| `conforms_to_schema` | "OMOP Common Data Model (electronic health record data); WFDB (high-resolution physiologic waveforms)" | `rai:dataCollection` states transformation to each. Per-collection: OMOP on the EHR sub-crate, WFDB on the Waveforms sub-crate. |
| `distribution_dates[0].release_dates` | `2026-04-03` | See date-format conflict below. |

### Controlled-vocabulary encodings

Where a schema slot has an enum range, crate free text was classified into that
vocabulary. The crate's own wording is preserved verbatim in the adjacent
description field, so nothing is lost if a classification is disputed.

- `known_biases[].bias_type` — six `rai:dataBiases` bullets mapped to
  `selection_bias`, `representation_bias`, `measurement_bias`, `sampling_bias`,
  `annotation_bias`, `historical_bias`. Verbatim text retained in
  `bias_description`.
- `known_limitations[].limitation_type` — seven `rai:dataLimitations` bullets
  mapped to `methodological_limitation` (×3), `resolution_limitation`,
  `integration_limitation`, `representativeness_limitation`,
  `scope_limitation`. Verbatim text retained in `limitation_description`.
- `regulatory_restrictions.confidentiality_level` = `confidential`. The crate
  says "HL7:2V (very restricted)". The enum's `confidential` value is defined as
  "Typically requires IRB approval, formal data use agreements, institutional
  authorization" — which matches the crate's stated access conditions exactly;
  `restricted` is defined as the weaker registration-level tier.
- `regulatory_restrictions.hipaa_compliant` = `compliant`, from "maintaining
  compliance with HIPAA and NIH data-sharing policies".
- `license_and_use_terms.data_use_permission` =
  `ethics_approval_required`, `institution_specific`, `project_specific`,
  `no_commercial_use` — one per bullet of `rai:conditionsOfAccess`.
- `maintainers[0].role` = `other`. The crate names the "CHoRUS Data Pillar", a
  consortium working group; no `CreatorOrMaintainerEnum` value fits, so the
  literal text carries the meaning in `maintainer_details`.
- `is_deidentified.identifiable_elements_present` = `false`, from
  `"deidentified": true` plus "Removal or tokenization of direct identifiers".
  The residual-risk statement is preserved in `deidentification_details`.

### Internal conflicts found in the crate itself

1. **Date format.** The root entity gives `datePublished: "2026-04-03"` and
   `releaseDate: "03/04/2026"`; the EHR sub-crate gives
   `datePublished: "03/04/2026"` while the Waveforms sub-crate gives
   `"2026-04-03"`. The slashed form is ambiguous (3 April vs 4 March). Resolved
   as **3 April 2026** on two independent grounds: the ISO form in the same
   entity, and the citation's "Harvard Dataverse, Apr. 2026". Both records use
   2026-04-03 throughout, and `distribution_dates[0].description` states the
   discrepancy rather than hiding it.
2. **License string varies by entity.** Root: "Data Use Agreement available at
   'https://chorus4ai.org/dataset/'". Both sub-crates: "See Data Use Agreement".
   Recorded per entity as written. Not a contradiction — both point at the same
   DUA, and `conditionsOfAccess` is identical across all three entities.
3. **Content URL scheme varies.** Root `contentUrl` is
   `http://chorus4ai.org/dataset`; both sub-crates use
   `https://chorus4ai.org/dataset/`. Recorded per entity; both forms are listed
   in the dataset-portal `ExternalResource`.
4. **Root `contentSize` looks like the waveform size alone.** "1.2 tb" vs the
   waveform sub-crate's "1.201567472832 tb". This is *not* a contradiction: the
   EHR sub-crate contributes only 18 MB, so the true sum (1.201585... tb) still
   rounds to 1.2 tb.
5. **`rai:dataBiases` and `rai:potentialBiases` are byte-identical**, as are
   `rai:dataReleaseMaintenancePlan` and `rai:maintenancePlan`. Recorded once
   each (in `known_biases` and `updates` respectively) rather than twice.
6. **PI name form varies.** Root: `principalInvestigator: "Eric Rosenthal,
   EROSENTHAL@mgh.harvard.edu"`; author list: "Eric S. Rosenthal(1)";
   sub-crates: "PI Eric Rosenthal  EROSENTHAL@mgh.harvard.edu". Same person,
   same email. Each slot uses the form the crate uses for that role.
7. **`humanSubjectExemption` mislabels its own citation:** "HIPAA exemption 4
   ((45 CFR 46.104(d)(4))" — 45 CFR 46.104(d)(4) is a Common Rule exemption
   category, not a HIPAA one, and the parenthesis is unbalanced. Quoted
   verbatim; not silently corrected.
8. **`ai_ready_score.characterization.statistics.has_content` is `false`** —
   the crate explicitly self-reports that it has no statistical
   characterization. This is consistent with the empty `instances` and
   `subpopulations` below.

### Cross-record consistency checks (each file internally)

Version `1.0 Beta` is stated at the dataset, both file collections, and
`version_access.versions_available` — consistent. The DOI appears as `id`,
`doi`, `version_access.latest_version_doi`, and an `ExternalResource` —
consistent. `2026-04-03` appears as `issued` (×3) and
`distribution_dates[0].release_dates` — consistent. Eric Rosenthal appears as
creator, PI reference, ethics contact, governance-committee contact, and
maintainer — consistent. Ciera McCrary appears as creator and as the license /
maintenance contact — consistent. Byte counts reconcile exactly (below).

### Phase 2 discoveries back-ported to full

None. Core is the exchange-layer subset of the same crate; re-reading the crate
against the `CoreDataset` inventory surfaced no fact the full record had
missed and no fact the full record had wrong. The only Phase 3 corrections were
the two wording tightenings listed above, and those originated in the string
audit, not in Phase 2.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime by `load_pair_schema` from `Dataset` and `CoreDataset`:

- **76 schema-identical slots**, all deeply identical between the two records.
- **1 projected slot**: `resources` — absent from both records, so the
  projection is vacuously satisfied.

Core was generated by copying every populated schema-identical slot from the
Phase 3-audited full record, preserving key order, then adding the one
core-only projection. `--sync-core` was subsequently run and changed nothing
material; the independent check then passed.

Slots present in full but outside `CoreDataset` (correctly absent from core):
`citation`, `direct_collection`, `file_collections`, `participant_privacy`,
`splits`, `third_party_sharing`, `total_file_count`, `total_size_bytes`.

### Related-content semantic review: `file_collections` ↔ `distributions`

The validator reports `deterministic matches=2, unmatched core
distributions=[]`. That warning marks the review as *required*; the review
itself is below.

| Property | EHR sub-crate | Waveforms sub-crate | Verdict |
|---|---|---|---|
| id | `08cf7419-…351d7` in both | `b9b41c72-…abcd6` in both | match (matching basis) |
| name | identical | identical | agree |
| description | identical | identical | agree |
| `total_bytes` ↔ `bytes` | 18136671 ↔ 18136671 | 1201567472832 ↔ 1201567472832 | agree |
| path | absent both | absent both | no conflict |
| compression | absent both | absent both | no conflict |
| format / media_type | absent both | absent both | no conflict — see below |
| checksums (hash/md5/sha256) | absent both | absent both | no conflict — see below |

- **Formats are deliberately not pushed down.** The crate reports formats
  (`.ipynb`, `text/tab-separated-values`, `wfdb`) only for the package as a
  whole, in `ai_ready_score`, never per sub-crate. Assigning TSV to the EHR
  collection and WFDB to the waveform collection would be a guess, so
  `CoreDistribution.format` and `.media_type` are left empty and the formats
  live at dataset level in `distribution_formats`. `CoreDistribution.media_type`
  would in fact have accepted `text/tab-separated-values` verbatim; it is still
  omitted, because the evidence does not attach that format to either
  distribution.
- **Checksums are stated to exist but not supplied.** `ai_ready_score` reports
  1469 of 1477 files carry checksums, but the crate JSON-LD in this bundle has
  its file inventories collapsed, so no checksum *values* are available.
  `hash`/`md5`/`sha256` are therefore empty in both records, and the 1469/1477
  figure is recorded in the RO-Crate `ExternalResource` description.
- **Access URLs do not project.** `FileCollection.page` carries
  `https://chorus4ai.org/dataset/` for both collections; `CoreDistribution` has
  no page or download_url slot, so this is a full-only detail, not a
  divergence.

### Scope and count cross-checks

- `total_size_bytes` (1201585609503) equals the sum of both distributions'
  `bytes` (18136671 + 1201567472832) — exact, same scope.
- `total_file_count` (1477) has no distribution-level counterpart: the crate
  gives no per-sub-crate `file_count`, so `FileCollection.file_count` is empty
  in both entries. Nothing to contradict.
- `is_tabular` and `dialect`: absent from both records. The package mixes TSV
  (tabular), WFDB (signal), and `.ipynb` (notebook), and the crate never asserts
  a tabular/non-tabular status, so a single boolean would be an invention.
- Historical vs current release: the crate documents exactly one release
  (1.0 Beta, 2026-04-03) and an archival *policy* for prior versions, but no
  prior version. `version_access.versions_available` lists only `1.0 Beta`.
  There is no historical/current split to disambiguate.

### Result

Zero unresolved contradictions within either record or between them.

---

## D4D areas the crate could NOT support at all

These slots are empty in both records because the crate says nothing about them.
This is the finding, not a gap to be filled.

**Composition — the largest hole.**

- `instances` — the crate never says what a data point is. No patient count, no
  encounter count, no record count, no cohort size. `completeness` says only
  "Not all patients in the CHoRUS full cohort are included", which implies
  patients are the unit but gives no number.
- `subpopulations` — no demographic breakdown at all. The crate acknowledges a
  "Socioeconomic and demographic distribution reflective of participating
  institutions" as a *bias*, but never characterizes the distribution.
- `variables` — despite `ai_ready_score` claiming "44 schema(s) documented",
  the reduced crate contains no variable, field, or column metadata.
- `relationships` — no inter-instance relationship structure.
- `content_warnings` — none stated.

**Collection.**

- `collection_timeframes` — **no collection period whatsoever.** No start date,
  no end date, no admission-window description. For a critical-care EHR corpus
  this is a substantial omission: a user cannot tell which years of clinical
  practice the data covers, which directly undercuts the crate's own
  "Temporal trends related to evolving clinical practice" bias note.
- `collection_notifications`, `collection_consents`, `consent_revocations`,
  `informed_consent` — the crate documents an IRB exemption ("HIPAA exemption 4
  ((45 CFR 46.104(d)(4))") and "IRB approval or waiver as appropriate", but
  never describes a consent process, a notification to patients, or a
  revocation route. An exemption is not a consent record, so none of these were
  populated from it.

**Preprocessing.**

- `cleaning_strategies` — no outlier handling, deduplication, or error
  correction described.
- `labeling_strategies` and `annotation_analyses` — the crate mentions "label
  assignment" only inside a bias bullet; there is no annotation protocol,
  annotator description, or agreement statistic.
- `imputation_protocols` — none, despite MNAR missingness being named as a
  known bias.
- `machine_annotation_tools` — the three named tools (RSNA Clinical Trial
  Processor, IbisWorks EICON, OHNLP toolkit) are de-identification and
  tokenization tools, not annotation tools, so they are attached as
  `used_software` on the relevant preprocessing strategies instead.
- `raw_sources` (Preprocessing `RawData`) — left empty to avoid duplicating
  `raw_data_sources`, which carries the same four modalities.

**Motivation and Uses.**

- `addressing_gaps` — the crate calls the dataset "flagship" and "multimodal"
  but never states a gap in existing datasets that it fills.
- `existing_uses` — no publication, no downstream project, no prior use.
- `use_repository` — no citation index, papers-with-code entry, or use registry.
- `other_tasks` — no uses beyond the nine intended ones.
- `future_use_impacts` — no forward-looking risk/benefit analysis distinct from
  the discouraged-use list.

**Ethics and maintenance.**

- `data_protection_impacts` — no DPIA. The crate describes layered privacy
  controls and periodic re-identification risk assessment, but never a formal
  impact assessment, so this slot was left empty rather than being filled from
  the privacy-controls list (which is recorded in `participant_privacy` and
  `sensitive_elements`).
- `at_risk_populations` — nothing, even though contributors include two
  children's hospitals (Seattle Children's, Nationwide Children's), which makes
  the silence on pediatric protections conspicuous.
- `participant_compensation` — nothing.
- `errata` — nothing. Release notes "documenting ... known issues" are
  *planned* in the maintenance plan; no erratum exists yet.

**Scalar metadata.** `language`, `status`, `created_on`, `created_by`,
`modified_by`, `last_updated_on`, `was_derived_from`, `download_url`,
`compression`, `conforms_to_class` — none stated.

### What the crate supports unusually well

For contrast, the crate is dense where a publication usually is not: the full
41-author list with numbered institutional affiliations, the IRB's name,
protocol number, postal address, and phone; the exact DUA document URL with its
revision date; a six-item bias inventory and a seven-item limitation inventory
written by the data producers; an explicit not-recommended-uses list; and a
versioning/deprecation policy. `known_biases`, `known_limitations`,
`license_and_use_terms`, `ethical_reviews`, and `creators` are all populated
directly from single crate fields with no synthesis required.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml

poetry run d4d provenance record --project CHORUS \
  --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep3 \
  --input-bundle data/preprocessed/concatenated/CHORUS_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (Dataset) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (CoreDataset) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair — `--sync-core` | PASS: 76 schema-identical slots; projected=['resources'] |
| Pair — independent check | PASS: 76 schema-identical slots; projected=['resources'] |
| Pair — outstanding warning | `semantic-review-required` on `file_collections` ↔ `distributions`; reviewed above, 2/2 matched, 0 unmatched, no conflicts |
| Provenance record | present, `record_mode: live` |

Informational only (not a quality gate): full 972 lines, core 823 lines;
provenance records 54 populated top-level slots in full, 47 in core.

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_d4d_core.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_provenance.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CHORUS_reconciliation.md` (this file)

No pre-existing file was overwritten.
