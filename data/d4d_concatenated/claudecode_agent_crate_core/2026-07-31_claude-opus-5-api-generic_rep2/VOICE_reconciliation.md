# VOICE — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared bundle:** `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt`
**Records reconciled:**
`data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d.yaml` (full)
`data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d_core.yaml` (core)

---

## 1. Referent declaration

`Dataset` admits one referent. Both records take as their referent the **adult Bridge2AI-Voice feature-only release distributed through PhysioNet, version 3.1.0** (published 2026-05-01, 833 participants, five North American sites).

Consequences of that choice, held consistently across both records:

- The **pediatric dataset** (`b2ai-voice-pediatric`, 300 participants aged 2–18, 23,533 derived recordings, Hospital for Sick Children, separate protocol, separate REB, separate DOIs, raw audio at Synapse `syn73617068`) is a **distinct PhysioNet project, not a version of the referent**. It is represented as a related resource, never folded into participant counts, cohort descriptions, or eligibility criteria.
- The **raw-audio distribution** (Synapse `syn72370534`, controlled access via DACO) is described as an access pathway to the underlying material, not as the content of this release. The referent contains derived features, phenotype tables, and per-recording metadata; it does not contain waveforms.
- The **smartphone-app feasibility study** (PMC12037532, n=47, USF only, no audio retained) is an associated publication about a data-collection instrument, not a description of the referent's contents.
- Superseded releases (1.0, 1.1, 2.0.0, 2.0.1, 3.0.0) are treated as version history, not as the referent. Where a figure is available only for an earlier version it is attributed to that version explicitly.

## 2. What the audit found

Thirty-six findings across the two records. No high-severity finding: the audit identified **no claim contradicted by the bundle and no fabricated dataset fact**. Three findings were medium; the remainder were low.

The findings sorted into six patterns:

| Pattern | Instances | Disposition |
|---|---|---|
| Identifier/version mismatch (`id`, `doi`) | 2 (both records) | Changed |
| Derived arithmetic presented as reported fact (`total_file_count`, `file_collections[].file_count`) | 2 (full only) | Changed |
| Coined URIs where the bundle gives a literal (`publisher`, subset/collection `id`) | 3 | Retained, documented |
| Unreconciled or one-sided source disagreement | 8 (4 pairs) | Changed — divergence made explicit |
| Slot-placement errors | 6 (3 pairs) | Changed |
| Entity merging in `creators` | 2 (both records) | Changed |
| Available typed slot left unpopulated (`related_datasets`) | 1 (full) | Changed |
| Evidence-consistent omissions confirmed | 7 (full) | Retained, documented |

## 3. Changes made

### 3.1 Identifier corrected to the version-specific DOI — both records

**Was:** `id` and `doi` set to `10.13026/37yb-1t42`, which the bundle identifies as PhysioNet's *latest-version* DOI for the `b2ai-voice` project.
**Now:** `id` and `doi` set to `10.13026/8xbn-nq66`, the DOI PhysioNet assigns to version 3.1.0.

**Why:** the record declares `version: 3.1.0`, `issued: 2026-05-01`, and a `citation` whose resolver is `10.13026/8xbn-nq66`. The latest-version DOI is a moving target that will resolve to 3.2.0 or later once published, so using it as the record identifier would make the record's own identifier disagree with its own version and date fields. The bundle supports both DOIs; they simply have different roles, and the version-pinned one is the correct role for a version-pinned record. The latest-version DOI was not discarded — it is retained under `version_access`, where the bundle's own framing ("DOI (latest version)") is preserved alongside the enumerated per-version DOIs.

### 3.2 Derived file counts removed — full record

**Was:** `total_file_count: 110`, with `file_collections[].file_count` of 22 (features), 86 (phenotype), 2 (metadata).
**Now:** all four values removed. The `file_collections` entries remain, described by content and format.

**Why:** no source in the bundle states a file count for any part of the release. The three component counts were produced by enumerating filenames in the v3.1.0 Data Description directory trees, and the features count additionally assumed a one-to-one data-file/JSON-dictionary pairing that the bundle asserts as a general convention but never enumerates. The total then compounded those estimates by addition. Under the rule preferring omission to inference, a computed count is not a reported count, and an aggregate of estimates is the weakest form of the claim. Omission is the correct answer where the evidence is absent.

### 3.3 BIDS conformance rescoped — both records

**Was:** `conforms_to` asserting BIDS v1.9.0 for the dataset.
**Now:** the same assertion, scoped in-string to the raw audio and REDCap-exported questionnaire data, with a note that the PhysioNet feature-only release is organized as `features/`, `phenotype/`, `metadata/`.

**Why:** the bundle attributes the BIDS v1.9.0 conversion specifically to the raw audio and REDCap exports, and shows a `b2ai-voice-audio` tree consistent with that. The v3.1.0 release under audit does not present that tree. The claim is real but was applied one scope level wider than the evidence establishes; narrowing the string preserves the fact without overreaching.

### 3.4 Source disagreements made explicit — both records

Four pairs of entries were internally at odds. In each case both sides were already bundle-supported and attributed, so the disagreement rule was not breached outright; what was missing was any signal to the reader that the sources diverge. Each pair now carries an explicit statement that the documentation is inconsistent on the point, with each figure bound to its source. No side was selected, dropped, or averaged.

- **`collection_timeframes`** — the healthsheet's "12 months" against the RO-Crate's "roughly between 2023 and 2025." Both retained; the divergence is now stated. The tempting reading, that the 12-month figure describes an earlier release, is *not* asserted: the bundle does not say so, and inferring it would replace one unsupported claim with another.
- **`cleaning_strategies`** — the healthsheet's "No" to whether cleaning pre-processing was performed, against the audit protocol, the removal of recordings containing identifying information or external speakers, and the removal of sensitive-record features. Now framed as answers to different questions asked in different documents, both retained verbatim in substance.
- **`confidential_elements`** — the healthsheet's "No" to the confidential-data question against the RO-Crate's `confidentialityLevel` of "Limited dataset available with Data Use Agreement." Same treatment.
- **`known_limitations`** (AI-readiness) — the docs Table 4 scores (characterization 80%, sustainability 50%, computability 75%, with `data_quality`, `domain_appropriate` and `associated` unmet) were represented alone. The entry now also records that `ai_ready_score.json` marks every criterion in every category as satisfied, including those three. The two self-assessments in the same bundle do not agree, and the record now says so.

### 3.5 Misplaced entries relocated or removed — both records

- **`existing_uses`** — the entry describing the citation requirement was removed. It states an obligation on users, not a use of the dataset. The requirement is already carried by the `citation` slot and by the protocol-publication entry in `external_resources`; nothing was lost.
- **`other_tasks`** — the pediatric developmental-norms entry was removed. It described a capability and then stated in its own text that the capability rests with the separate pediatric release "rather than by this adult dataset." An entry that negates its own applicability to the referent is not a task the referent supports. The pediatric release remains fully described elsewhere.
- **`anomalies`** — the entry about subjective success determination by research assistants in the app feasibility study was removed. That study is a different artifact with a different n, a different site, and no retained audio; its methodological limitation is not a data-quality anomaly in the released dataset. The feasibility study remains listed as an associated publication.

### 3.6 `creators` split into one entry per person — both records

Several `Creator` objects each bundled two or three individuals (for instance Bahr with Watts; Rudzicz with Lerner-Ellis and Siu). These were split so that each object describes exactly one person, with role and affiliation as the bundle gives them. Merging distinct entities into a single claim is barred regardless of how convenient the grouping is, and the bundle names these people individually.

### 3.7 `related_datasets` populated — full record

A typed `DatasetRelationship` for the pediatric dataset was added to the full record. Both required keys are satisfied directly from the bundle: `target_dataset` (the `b2ai-voice-pediatric` PhysioNet project, DOI `10.13026/h995-bt35` for v1.1.0, latest-version DOI `10.13026/mf9s-5r03`) and `relationship_type` (a companion cohort from the same consortium and funding award, explicitly not a version of the adult dataset).

The typed slot was available and the evidence supported it, so leaving the relation as prose was an under-population rather than a judgment call. The core record retains the prose description under `external_resources` rather than adding the typed entry, to keep that record inside the core profile; the factual content is identical between the two.

## 4. What was left unchanged, and why

### 4.1 `publisher` as `https://physionet.org/` — both records

The bundle's literal is `"PhysioNet"`. The slot range is `uriorcurie`, which a bare display name does not satisfy. The canonical PhysioNet URL is the minimal faithful rendering that meets the range, and the literal name appears verbatim in `citation` and in the descriptive text. Retained; flagged here so the coinage is visible rather than silent.

### 4.2 Coined identifiers for `subsets` and `file_collections` — full record

`DataSubset` and `FileCollection` both require an `id`. The bundle supplies no identifiers for individual cohorts or file groups. Fragment URIs anchored on the version-3.1.0 landing page (for example `…/3.1.0/#voice-disorders-cohort`) were coined to satisfy the requirement. They are structural handles, not evidenced identifiers, and carry no factual assertion beyond the subset's existence, which the bundle does establish. Retained by necessity.

### 4.3 Timestamps rendered as `T00:00:00Z` — both records

`issued` and `last_updated_on` are `2026-05-01T00:00:00Z`. The bundle gives "Published: May 1, 2026" with no time component. The zero time is an artifact of the `datetime` range, not an evidenced timestamp. Retained; no alternative exists within the range.

### 4.4 `created_by: Bridge2AI-Voice Consortium` — full record

The bundle uses the consortium name for collective authorship, lists 117 individual authors on the v3.0.0 crate, and names Yael Bensoussan as principal investigator. No source says "created by" in those words. The consortium attribution is the least specific claim consistent with all three, and is preferable to elevating any one individual. Retained.

### 4.5 The ~61,937 recordings figure under `instances` — full record

The figure comes from the project documentation's statement about version 3.0 and is attributed to version 3.0 in the record. Version 3.1.0 supplies its own per-feature row counts (29,278 spectrograms and mel spectrograms and MFCCs; 32,522 torchaudio pitch; 31,872 sparc pitch and periodicity; and so on). The two are not in conflict — they count different things at different granularities — and the audit did not ask that either be dropped. A sentence was added relating the version-3.0 aggregate to the version-3.1.0 per-feature counts so the adjacency is no longer bare. The figures themselves are unchanged.

### 4.6 `variables` as a sixteen-entry selection — full record

The bundle's crate schemas enumerate well over a thousand columns (`confounders` 547, `winograd` 282, `static_features` 135, `stroop` 64, plus the diagnosis tables). Sixteen `VariableMetadata` entries covering representative feature and phenotype fields were retained. No schema slot exists to mark a variable list as a sample, and fabricating a synthetic "this is a subset" variable entry would be a worse defect than the incompleteness. The limitation is recorded here instead: **the `variables` slot is illustrative, not exhaustive.**

### 4.7 Confirmed evidence-consistent omissions — full record

These slots are empty and correctly so. Recorded to distinguish deliberate omission from oversight:

- **`download_url`** — no direct data URL exists. Files are gated behind PhysioNet credentialing plus a signed DUA; raw audio is behind a separate DACO application and institutional sign-off.
- **`total_size_bytes`** — the crate's 12.9 GB total and its nine per-file `contentSize` values are all for v3.0.0, not the v3.1.0 referent. The 12.9 GB figure is retained as attributed prose under `version_access` rather than promoted to a size slot for the wrong version.
- **`compression`** — no distribution-level compression format is stated. Parquet's internal encoding is not a distribution compression format and is not described as one.
- **`created_on`** — publication dates exist; a creation timestamp does not.
- **`conforms_to_schema`, `conforms_to_class`** — the REDCap data dictionary and the crate's `EVI:Schema` objects are component schemas, not a data model to which the dataset as a whole declares conformance.
- **`modified_by`** — the crate names a person as `runBy` for the v3.0.0 feature-processing and phenotype-ETL computations, but spells the name inconsistently with the author list ("Alastair" against "Alistair Johnson"), and the attribution is to a computation for a superseded version rather than to modification of the referent. Caution preferred.

## 5. Full/core agreement

Every factual claim shared between the two records agrees after reconciliation. The core record differs from the full record only by profile scope:

- It never carried the file-count arithmetic, and so required no change there — a case where the narrower profile happened to avoid the full record's one substantive defect.
- It folds instance relationships into `instances` and consent detail into `informed_consent`. Both foldings restate content present in the full record; neither introduces an assertion the full record lacks.
- It carries the pediatric relation as prose rather than as a typed `DatasetRelationship` (§3.7).

No fact appears in the core record that is absent from the full record.

## 6. Net effect

**Full record:** one populated slot removed (`total_file_count`), one populated slot added (`related_datasets`), for no net change in populated-slot count. Within retained slots: three entries removed as misplaced, four entries rewritten to expose source disagreement, one entry rescoped, `creators` expanded from grouped to per-person objects, `id` and `doi` repointed, three `file_count` sub-values removed.

**Core record:** no change in populated-slot count. Three entries removed as misplaced, four rewritten to expose disagreement, one rescoped, `creators` expanded, `id` and `doi` repointed.

Both records were re-validated after reconciliation. No change introduced a fact absent from the declared bundle; every change either removed a derived or misplaced claim, narrowed an overbroad scope, exposed a divergence the bundle already contained, or populated a slot the evidence already supported.