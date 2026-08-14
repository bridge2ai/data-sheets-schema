# Phase 4c — Reconciliation Report: VOICE

**Project:** VOICE (Bridge2AI-Voice)
**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep1`
**Arm:** BASELINE (input documents only)
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/VOICE_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/VOICE_d4d_core.yaml`
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 files)

---

## 1. Referent declaration

The declared bundle describes several distinct artefacts: the Bridge2AI-Voice adult flagship dataset across five PhysioNet versions (1.0 through 3.1.0), a separate pediatric dataset (1.0.0, 1.1.0), an earlier Health Data Nexus release, a REDCap data dictionary, a smartphone application, and the umbrella NIH grand-challenge project.

`Dataset` admits one referent. **The referent chosen is the Bridge2AI-Voice adult flagship dataset, version 3.1.0**, the most recent adult release attested in the bundle. This choice is held consistently across both records:

- `version: 3.1.0`, `doi: 10.13026/8xbn-nq66`, `issued: 2026-05-01`
- Feature-file row counts, folder layout, and de-identification description are taken from the v3.1.0 page, not from earlier versions
- Earlier adult versions are carried in `version_access` and `errata`, not conflated into the current description
- The pediatric dataset is represented in `related_datasets` under a typed relationship, not merged into the referent
- The REDCap dictionary and `b2aiprep`/`senselab` toolkits are represented as `external_resources` and in preprocessing slots, not as the referent

---

## 2. Audit findings and disposition

Eighteen findings were returned. Disposition below, grouped by action taken.

### 2.1 Changed — structural defects

#### (a) `distributions` removed from the core record — **HIGH**

The core record carried a `distributions` block with keys `path`, `format`, `media_type`, `notes`, `source_caveats`. This slot is not declared on `CoreDataset`, and the key set is a hybrid of `FileCollection` (`path`) and `DistributionFormat` (`format`, `media_type`). An undeclared slot is not a validation-neutral extra; it is content the schema cannot carry.

**Action:** the block was removed. Its content was already fully represented by the declared `distribution_formats` slot, which was retained and left unchanged. No evidence was lost. The folder-level grouping that `path` was carrying survives in the full record's `file_collections`, which is a declared slot there.

#### (b) `format: TSV` inconsistency — **HIGH** (resolved by (a))

The second `distributions` entry asserted `format: TSV` for the phenotype folder while noting that each table is paired with a JSON data dictionary; the first entry withheld `format` on exactly that mixed-format reasoning. Two entries reached opposite conclusions from identical evidence.

**Action:** resolved as a consequence of removing the block. The surviving `distribution_formats` entries do not make a per-folder `format` assertion, so the inconsistency does not recur.

#### (c) `use_repository` empty list removed — **MEDIUM**

The full record emitted `use_repository: []`. The healthsheet does answer the underlying question — "Is there a repository that links to any or all papers or systems that use the dataset? … No" — but an empty list does not encode that answer. It encodes an unpopulated multivalued slot, which is indistinguishable from an omission that was never considered.

**Action:** the slot was omitted. Under the stated preference for omission over inference and over empty structure, an absent slot is the correct representation. The healthsheet's negative answer remains recoverable from the bundle itself.

#### (d) `errata[0]` removed — **MEDIUM**

The first `Erratum` object read, in substance, "no erratum is maintained." An object whose content is the assertion that its own subject does not exist populates the slot without answering it.

**Action:** the object was dropped. Its one substantive remark — that a changelog is published with the dataset metadata in place of a formal erratum — was folded into the surviving `Erratum` object, which carries the actual per-version correction history (v2.0 spectrogram reprocessing, v2.0.1 authorship correction, v3.1.0 broken-parquet repair and gold-standard variable renaming). The slot now holds one object that answers the field.

### 2.2 Changed — identifier and reference defects

#### (e) CURIE prefixes bound — **MEDIUM**

Approximately forty identifier values per record used the prefixes `b2ai-voice:` and `nih:` with no binding anywhere in either file. Unbound CURIEs in a `uriorcurie` slot do not resolve and are not recoverable by a consumer.

**Action:** all such identifiers were rewritten as absolute IRIs under a namespace derived from the project's own documented web presence (`https://b2ai-voice.org/`), so that every `id` in both records is dereferenceable in form without depending on an out-of-band prefix map. Grant identifiers under `funders[*].grants[*].id` were rewritten against the NIH RePORTER project URL attested in the bundle, which the bundle supplies directly for core project `OT2OD032720`.

#### (f) `id` disambiguated between records — **MEDIUM**

Both records shared the identical `id`, set to the version-independent DOI `https://doi.org/10.13026/37yb-1t42`, while every other slot described v3.1.0 specifically (`10.13026/8xbn-nq66`). The identifier denoted the version series; the content denoted one version. Two distinct records also sharing one identifier makes them indistinguishable by reference.

**Action:** `id` in both records was changed to the version-specific DOI matching the declared referent, `https://doi.org/10.13026/8xbn-nq66`. The version-independent DOI was moved into `version_access.latest_version_doi`, which is the slot that asks for it. The core record's `id` was given a distinct suffix so that the two records are separately addressable while remaining evidently paired via the `# Sources:` header line.

#### (g) `conforms_to_schema` corrected on the core record — **LOW**

The core record's `conforms_to_schema` pointed at the full-schema IRI while its header declared the core schema file.

**Action:** the core record's value was set to the core schema IRI. `conforms_to_class` was already correct on both records (`Dataset` / `CoreDataset`) and was left alone.

### 2.3 Changed — misplacement

#### (h) `participant_compensation` restored to the core record — **LOW**

The core record had folded compensation detail (40 USD under 90 minutes, 80 USD over, three-session cap, 120 USD maximum) into `informed_consent[0].notes`, with a `source_caveats` claiming the core schema lacks a slot for it. That claim was not verifiable from the digest and turned out to be wrong.

**Action:** the content was moved into a `HumanSubjectCompensation` object populating `compensation_provided`, `compensation_type`, `compensation_amount` and `compensation_rationale`, matching the full record. The structured amounts are no longer lost to prose, and the unfounded `source_caveats` claim was removed.

#### (i) `collection_notifications` restored to the core record — **LOW**

Same pattern: the full record carried a `CollectionNotification` object; the core record had relocated the text into `informed_consent[0].notes`.

**Action:** the object was restored to the core record in the slot that asks for it.

#### (j) `data_governance.committee_contact` populated — **LOW**

The DACO mailbox `DACO@b2ai-voice.org` is stated plainly in the bundle (twice, in both PhysioNet notices) and appeared in `access_review_process` prose, but the `committee_contact` field — range `Person` — was empty.

**Action:** a `Person` object carrying the mailbox as the committee contact point was added in both records. The narrative mention in `access_review_process` was left in place, as it describes the review workflow rather than merely repeating the address.

### 2.4 Changed — internal contradiction

#### (k) `relationships` rewritten — **LOW**

The single `Relationships` object opened by asserting the healthsheet's "No, they are unrelated" and then went on to describe `participant_id`/`session_id` linkage across feature and phenotype tables — denying and affirming inter-instance relationships in one value.

**Action:** the object was rewritten to separate the two claims explicitly: no semantic or graph-structured relationships hold *between participants* (the healthsheet's actual claim), while structural key-based linkage does hold *within* a participant across sessions, recordings and feature tables. Both halves are supported; the contradiction was one of framing.

### 2.5 Changed — over-assertion

#### (l) `keywords` narrowed — **LOW**

The list mixed the four topic terms actually attached to the v3.1.0 PhysioNet project page (`health`, `biomarkers`, `bridge2ai`, `voice`) with four terms inferred from body text (`speech`, `audiomics`, `artificial intelligence`, `voice disorders`).

**Action:** the four attested topic terms were retained. The four inferred terms were dropped. `keywords` transcribes a keyword field; it is not a place to summarise subject matter, and the distinction between "the source labelled it thus" and "the text is about this" is exactly what the slot loses if inference is admitted.

### 2.6 Changed — narrowing with disclosure

#### (m) `instances[1].counts` removed — **MEDIUM**

`counts: 32522` was presented as the recording-instance count. That figure is the row count of one feature file (`torchaudio_pitch.parquet`) in v3.1.0 — the largest of eleven differing counts, ranging from 23,533 to 32,522 across feature types, because different extractors failed on different files. It is a maximum-across-features proxy, not an attested count of recordings. The bundle gives an explicit recording count for the *pediatric* release (23,533) but never for the adult release.

**Action:** the integer assertion was removed. The per-feature row counts are retained in `variables` and in `file_collections`, where they are correctly scoped to the files they describe, and a `source_caveats` note records that the bundle supplies no authoritative adult recording count for v3.1.0. An integer-ranged slot carrying a proxy is a stronger claim than the evidence licenses, and disclosure in `source_caveats` mitigates but does not cure that.

---

## 3. Left as-is, with reasoning

### (n) `subsets[*]` carry content in `description` — **MEDIUM, not changed**

The five disease-cohort `DataSubset` objects hold their inclusion criteria, exclusion criteria and gold-standard validation methods in `description` prose rather than in declared fields.

**Not changed.** The finding is correct that `DataSubset` accepts the full slot inventory. But the candidate targets do not fit the content. Table 1's inclusion/exclusion criteria are eligibility rules, not `sampling_strategies` (which asks how instances were selected from a population — already answered at dataset level as non-probability sampling from high-volume expert clinics). The gold-standard validation column describes diagnostic confirmation, which is nearer `labeling_strategies` — but the dataset-level `labeling_strategies` already states that diagnostic labels come from a single site clinician per participant against Bridge2AI protocols and ICD-10, and per-cohort duplication of that with only the modality varying would repeat rather than refine. Forcing this content into declared fields would produce five objects each restating the dataset-level answer with one clause changed. The prose is the honest shape for it. `is_data_split: false` and `is_subpopulation: true` are populated and correct.

### (o) `variables` covers only feature columns — **LOW, not changed**

Eleven feature-file columns are described; no phenotype columns are.

**Not changed.** The bundle names the phenotype tables and states that each has a JSON data dictionary with per-column descriptions, questions and data types — but it does not enumerate a single phenotype column. Emitting `VariableMetadata` objects for columns the bundle never names would be fabrication. The distinction is recorded in `source_caveats` on the slot so the list is not read as complete. This is the correct outcome of the omission-over-inference rule, not a gap.

### (p) `license` under-describes the two-tier arrangement — **LOW, not changed**

`license: Bridge2AI Voice Registered Access License` is the PhysioNet label for the registered tier only; raw audio moves under a separate DTUA.

**Not changed.** The string is exactly what the source states for the release the referent denotes. `license` is a scalar and cannot carry two tiers; `license_and_use_terms` does carry both, correctly, and `data_governance` describes the DACO route to the audio. Substituting a synthesised composite string would misquote the source in order to say more.

### (q) `instances[*].data_substrate` describes packaging over content — **LOW, not changed**

Participant instances carry `B2AI_SUBSTRATE:41` (TSV), recording instances `B2AI_SUBSTRATE:30` (Parquet), rather than waveform or participant-response terms.

**Not changed after reconsideration of the referent.** The referent is the v3.1.0 PhysioNet release, which contains no raw audio — only derived features in Parquet and phenotype tables in TSV. `B2AI_SUBSTRATE:49` (Waveform Data) would name a substrate the referent does not distribute. The chosen terms describe what is actually in the release. This is the right answer for this referent even though it would be the wrong answer for the raw-audio distribution on Synapse, and that distinction is noted in `source_caveats`.

### (r) `collection_consents` duplicates `informed_consent[0]` — **LOW, not changed**

**Not changed.** The two slots ask different questions — how consent was requested and documented at collection time versus the consent instrument, its scope and its withdrawal mechanism — and the bundle speaks to both. The overlap is in the underlying facts, not in the fields. Dropping either would leave a declared slot unanswered where evidence exists.

---

## 4. Cross-record consistency

Full and core were re-checked against each other after the edits above:

| Property | Full | Core | Consistent |
|---|---|---|---|
| Referent | adult flagship v3.1.0 | adult flagship v3.1.0 | yes |
| `version` / `doi` | 3.1.0 / 10.13026/8xbn-nq66 | 3.1.0 / 10.13026/8xbn-nq66 | yes |
| `id` | version-specific, distinct | version-specific, distinct | yes, and separately addressable |
| Participant count | 833 | 833 | yes |
| Sites | five, North America | five, North America | yes |
| Compensation | structured | structured (restored) | yes |
| Identifier form | absolute IRIs | absolute IRIs | yes |

The core record's `# Sources:` header line names both the declared bundle and the full record path, as required.

---

## 5. Source conflicts retained rather than resolved

The bundle disagrees with itself in several places. Per the stated rule, these are represented rather than silently adjudicated, each carried in the relevant `source_caveats`:

- **Award identifier.** Appears as `OT2OD032720`, `3OT2OD032720-01S3`, `3OT2OD032720-01S1`, `1OT2OD032720-01`, `OT2 OD032720`, and the evidently corrupted `3Tf-OTOD03272001S2` and `3TF-OT2ActfOD032720Projectf01S1`. The core project number `OT2OD032720` is used as the stable value; the supplement suffixes and corruptions are noted.
- **Investigator name.** `Jennifer Siu` (PhysioNet author lists) versus `Jennifer Sui` (documentation site). Both forms recorded.
- **HIPAA characterisation.** The documentation healthsheet states the HIPAA de-identification rules were applied; the DTUA states the data is Personally Identifiable Information "not covered under HIPAA." Both retained; not reconciled.
- **Host platform.** The healthsheet describes distribution via Health Data Nexus with a DOI; the PhysioNet pages are the current host and Synapse is named for raw audio. All three recorded, with the Health Data Nexus statement scoped to the earlier release it describes.
- **Cleaning.** The healthsheet answers "No" to pre-processing for cleaning while describing an audit protocol with missingness tables, outlier checks, schema validation and audio QC. Both recorded; `cleaning_strategies` distinguishes audit from cleaning.
- **Enrollment target.** 10,000 voices (documentation, PhysioNet project site) versus 30,000 (NIH RePORTER abstract, IRB protocol). Both recorded.
- **Collection timeframe.** "12 months" (healthsheet) against a 2022-09-01 to 2026-11-30 project period and a four-year IRB protocol. Both recorded; the 12-month figure is scoped to the release it accompanied.

---

## 6. Outcome

| | Before | After |
|---|---|---|
| Full record slots populated | 71 | 69 |
| Core record slots populated | 44 | 45 |
| Full validates against `Dataset` | — | yes |
| Core validates against `CoreDataset` | — | yes |
| Prior-D4D factual reuse | none | none |

Net slot movement is small because most edits corrected the *shape* of existing values rather than adding or removing evidence. Three slots were removed from the full record (`use_repository`, `instances[1].counts`, one `errata` object merged), and one core slot was removed while two were restored.

No prior D4D record from any arm, label or date was read, opened, grepped or consulted at any phase. All factual content derives from the eleven files in the declared bundle.

**Phase 4 reconciliation: completed.**