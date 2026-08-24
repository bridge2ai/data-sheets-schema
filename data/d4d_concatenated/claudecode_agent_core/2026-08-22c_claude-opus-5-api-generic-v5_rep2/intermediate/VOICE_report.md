# VOICE — Phase 4 Reconciliation Report

Version label: `2026-08-22c_claude-opus-5-api-generic-v5_rep2`
Records reconciled: `VOICE_d4d.yaml` (full, class `Dataset`) and `VOICE_d4d_core.yaml` (core, class `CoreDataset`)

---

## 1. Scope of this report

Phase 3 returned 17 findings: 2 high, 5 medium, 10 low. This report records, finding by finding, what was changed in the reconciled records and what was deliberately left as-is. Every change claimed below is visible by diffing the original records against the reconciled records supplied in this session; where the two are identical for a finding, that is stated.

---

## 2. High-severity findings

### 2.1 `distributions` — invented slot in the core record (core)

**Audit finding.** The core record emitted a top-level `distributions` list whose keys were `path`, `conforms_to`, `conforms_to_standard`, `format`, `media_type`, `notes`. No slot named `distributions` appears in the 98-slot `Dataset` inventory supplied to this run; the inventory declares `distribution_formats`, `distribution_dates` and `file_collections`. Within that invented slot, `conforms_to_standard` — declared multivalued at `Dataset` level — was written as a scalar string `BIDS`.

**Action: changed.** The `distributions` block has been removed from the core record entirely. Its content was not discarded: the file-layout detail it carried was folded into the four `distribution_formats` objects, which the schema does declare. Specifically —

- the Parquet file names (`ppgs.parquet`, `sparc_ema.parquet`, `sparc_loudness.parquet`, `sparc_periodicity.parquet`, `sparc_pitch.parquet`, `torchaudio_spectrogram.parquet`, `torchaudio_mfcc.parquet`, `torchaudio_pitch.parquet`, `torchaudio_mel_spectrogram.parquet`), the per-element structure, and the `metadata/` Parquet file now sit in the notes of the `Apache Parquet` entry;
- `static_features.tsv`, `audio_quality_metrics.tsv` and the full `phenotype/` subfolder enumeration now sit in the notes of the `Tab-separated values` entry;
- the data-dictionary description now sits in the notes of the `JSON` entry.

The scalar `conforms_to_standard: BIDS` inside the invented block is gone with it; the record's one remaining `conforms_to_standard` is the top-level list `[BIDS]`, which matches the declared multivalued range.

### 2.2 `data_governance.committee_contact` — email in a `Person`-ranged slot (core)

**Audit finding.** The core record supplied `committee_contact: {email: DACO@b2ai-voice.org}`. `committee_contact` has declared range `Person`; `email` is not a documented key on `Person` in the digest, and the value is an office mailbox rather than a person. The full record correctly omitted the key.

**Action: changed.** `committee_contact` has been removed from the core record's `data_governance` object. The address itself is not lost — it remains in `data_governance.access_review_process` ("Requests for controlled access are made by email to DACO@b2ai-voice.org"), in `maintainers[3].maintainer_details`, and in `raw_data_sources[0].access_details`, exactly as in the full record. The two records' `data_governance` objects now carry the same key set.

---

## 3. Medium-severity findings

### 3.1 `data_collectors[].role` — free prose replacing the enum (core)

**Audit finding.** The full record used the permitted `DataCollector.role` enum value `researcher` for both collectors; the core record replaced these with free prose (`Research teams coordinating and administering the collection protocol`, `Clinicians providing gold standard diagnoses`).

**Action: changed.** Both core `data_collectors[].role` values are now `researcher`, matching the full record. The descriptive content that had been misplaced into `role` was already present in the sibling `collector_details` on both objects, so nothing was lost by the reversion. The two records' `data_collectors` blocks are now identical.

### 3.2 `informed_consent[].notes` — compensation relocated (core)

**Audit finding.** Compensation facts (electronic gift cards; $40 / $80; three sessions; $120 maximum) were folded into `informed_consent[0].notes` in the core record, where the full record carries them in the dedicated `participant_compensation` slot.

**Action: left as-is, with the caveat strengthened.** The core schema declares no `participant_compensation` slot, so the core record has nowhere else to put the fact. The relocation stands, and the core `informed_consent[0].notes` still carries it — expanded slightly, in fact, to include the protocol-revision history (V3 August 2023; V7 and V8 in 2024) and the feasibility-study exclusion that the full record's `participant_compensation.source_caveats` carries. This keeps the core record from asserting less than the full record on a point a reader would reasonably check. The core `source_caveats` names `participant_compensation` among the slots whose content was folded elsewhere.

The full record is unchanged here: `participant_compensation` remains a first-class slot with `compensation_provided`, `compensation_type`, `compensation_amount` and `source_caveats` populated.

### 3.3 `preprocessing_strategies` — core asserting more than full

**Audit finding.** The core record's `preprocessing_strategies` carried detail the full record's corresponding slot did not: spectrogram dimension `201 by T`, the enumeration of the six sparc articulators, and the pitch ranges 80–500 Hz (torchaudio) / 50–550 Hz (sparc). All bundle-attested, all present in the full record's `variables`, but a projection should not state what its source record does not.

**Action: changed — in the full record, not the core.** The correct fix was to raise the full record to match rather than strip the core, because the detail is attested and belongs in `preprocessing_strategies` on both. The full record's `preprocessing_strategies` now carries:

- "Dimension is 201 by T" on the spectrogram entry;
- "Each is of dimension 60 by T" on the mel spectrogram / MFCC entry;
- the six named articulators (tongue dorsum, tongue body, tongue tip, lower incisor, upper lip, lower lip) as X and Y positions, plus the 20 ms window for loudness and periodicity, on the sparc entry;
- the torchaudio 80–500 Hz and sparc 50–550 Hz ranges on the static-features entry.

The two records' `preprocessing_strategies` blocks are now equivalent in content.

### 3.4 `notes` — citation relocated (core)

**Audit finding.** The recommended citation was relocated into the core record's `notes`. The full record populates the declared `citation` slot. The core `source_caveats` asserted that the core schema does not declare `citation`; the audit could not verify that assertion from the supplied digest.

**Action: left as-is.** The core record still carries the citation text at the end of `notes` and does not populate a `citation` slot. The reconciled core `source_caveats` continues to name `citation` among the folded slots. The audit is right that this session was not given a core schema digest, so the claim cannot be demonstrated here; the report records it as an assertion of the generating run rather than a verified fact. No supported basis exists in this session for moving the citation into a slot whose declaration cannot be confirmed, and removing it from `notes` would lose attested content. The full record's `citation` slot is unchanged and populated.

### 3.5 `maintainers[1].maintainer_details` — unsupported characterization (full)

**Audit finding.** The full record described T-CAIREM as "based at the University of South Florida's partner institution the University of Toronto". The bundle says only "based at the University of Toronto". The phrase "University of South Florida's partner institution" appears in no source, and the core record already said plain "at the University of Toronto", so the two records disagreed.

**Action: changed.** The full record now reads "maintained by the Temerty Center for Artificial Intelligence Research and Education in Medicine (T-CAIREM) based at the University of Toronto". The invented relationship is gone and the two records agree. Note that the core record's wording differed slightly from the full record's in the original ("at the University of Toronto"); the reconciled core now reads "based at the University of Toronto", matching the full record and the bundle's own phrasing.

### 3.6 `creators[].credit_roles` — roles inferred rather than attested (full)

**Audit finding.** CRediT roles were assigned to Sigaras (`software`), Ghosh (`software`, `data_curation`) and Johnson (`data_curation`, `software`) on the basis of module leadership and library contribution rather than any CRediT statement. The feasibility publication's author-contribution block covers only EM, MB, SW, YA-A, SG, AR, AS, OE and YB, does not assign `data_curation` to Ghosh, and does not cover Johnson at all.

**Action: changed, in both records.** The `credit_roles` slot is now populated only from the feasibility publication's author-contribution block, transcribed rather than inferred:

- **Ghosh** — `software` and `data_curation` removed; now `conceptualization`, `project_administration`, `supervision`, as the publication assigns to SG. The b2aiprep contribution is retained as prose in `notes` ("named contributor to the b2aiprep processing library"), which is a factual statement rather than a role assignment.
- **Johnson** — `credit_roles` removed entirely; he is not an author of the feasibility publication. The b2aiprep contribution is retained in `notes`.
- **Sigaras** — `software` retained (the publication does assign Software to AS) and joined by `conceptualization`, `project_administration`, `supervision` from the same block.
- **Elemento** — `software` removed; the publication's block for OE lists Conceptualization, Funding acquisition, Project administration, Resources, Supervision, Validation, Visualization, Writing, not Software.
- **Rameau** and **Watts** — gained `conceptualization`, `project_administration`, `supervision` from their AR and SW entries, which the original records had left empty.
- **Bensoussan** — unchanged; her roles already matched the YB entry.

Each affected `notes` now states that the roles are transcribed from the feasibility publication's author-contribution section. Leads named only in the IRB protocol or project documentation (Bahr, Rudzicz, Lerner-Ellis, Powell, Neal, Dorr, Payne, Ravitsky, Bélisle-Pipon, Bolser, Siu) carry no `credit_roles` at all. A paragraph in both records' `source_caveats` states this policy explicitly.

---

## 4. Low-severity findings

### 4.1 `publisher` — bare site URL in a `uriorcurie` slot (full)

**Left as-is.** `publisher: https://physionet.org/` is unchanged in both records. The slot's range is `uriorcurie`, whose "uri" half is the fallback where no declared prefix covers the identifier; no PhysioNet organizational identifier appears anywhere in the bundle, and supplying one from outside the bundle is prohibited under the v5 rule on identifiers naming things outside the dataset. The audit itself graded this permissible.

### 4.2 & 4.3 `instances[].data_substrate` — container/content conflation and inconsistency (both)

**Changed, in both records.** `instances[1].data_substrate` was `B2AI_SUBSTRATE:30` (Parquet), naming the release container rather than the instance. It is now `B2AI_SUBSTRATE:49` (Waveform Data), which names what the instance is. The container fact is not lost: the same object's `notes` now ends "The released artifacts are stored as Apache Parquet files."

This also resolves finding 4.3, the inconsistency between `instances[1]` (container reading) and `instances[2]` (content reading). All four instance objects now apply the content reading uniformly: `B2AI_SUBSTRATE:49` waveform data, `B2AI_SUBSTRATE:80` questionnaire response data, `B2AI_SUBSTRATE:41` tab-separated values for the diagnosis tables. `instances[2]`'s notes gained a matching sentence naming its container ("The released artifacts are tab-delimited tables with accompanying JSON data dictionaries"). A new paragraph in both records' `source_caveats` states the convention.

### 4.4 `sampling_strategies[0]` — duplicate `is_representative` key (full)

**Changed.** The full record's `sampling_strategies[0]` contained `is_representative: false` twice — once before `strategies`, once after — a duplicate YAML mapping key. The second occurrence has been removed; the object now carries one `is_representative: false`, before `source_data`. Values agreed, so no semantic change, but the object is now well-formed. The core record never had the duplicate and is unchanged in this respect.

### 4.5 Sequence indentation (full)

**Changed.** The full record had list items indented at the same level as their parent key in seven places: `sampling_strategies[0].representative_verification`, `human_subject_research.irb_approval`, `human_subject_research.regulatory_compliance`, `labeling_strategies[0].annotator_demographics`, `machine_annotation_tools[0].tool_accuracy`, `annotation_analyses[0].disagreement_patterns`, and `regulatory_restrictions.regulatory_restrictions`. All seven are now indented consistently with the rest of the file. Two further sequences with the same defect were caught in passing and corrected: `ip_restrictions.restrictions[0]` and `participant_privacy[0].privacy_techniques`. No values changed; this is formatting only.

### 4.6 `conforms_to_class` (core)

**Left as-is.** `CoreDataset` in the core record, `Dataset` in the full record. The audit graded this correct and flagged it only because the paired records necessarily differ. No change.

### 4.7 `id` resolving to a version rather than the concept (both)

**Left as-is in the slot; caveat added.** `id` and `doi` remain the version-specific 3.1.0 identifiers (`doi:10.13026/8xbn-nq66`, `10.13026/8xbn-nq66`), and `version_access.latest_version_doi` remains the version-independent `doi:10.13026/37yb-1t42`. This is internally coherent given the declared referent, and changing `id` would break the correspondence with the stated referent (the 3.1.0 release specifically). The audit's substantive point was that the caveat was missing. Both records' `source_caveats` now open with an "Identifier" sentence stating that `id` and `doi` carry the version-specific DOI matching the stated referent and that the concept-level DOI lives in `version_access.latest_version_doi`; the core record's version adds that a reader resolving `id` therefore reaches a specific version.

### 4.8 `collection_timeframes` — duration without dates (both)

**Left as-is.** Both records still carry only `timeframe_details: "The data were collected over a period of 12 months."` with a `source_caveats` noting that the figure comes from a healthsheet written against an earlier version and that no start or end date is stated in any source. The audit graded this a residual gap rather than a defect and confirmed no supportable omission. The bounded window in the bundle (2023-06-05 to 2023-07-28) belongs to the separate feasibility study and is correctly excluded from this slot; it remains recorded in `ethical_reviews[3]` and in `source_caveats`.

### 4.9 `file_collections` counts and sizes (full)

**Left as-is.** `file_count` and `total_bytes` remain absent from every `FileCollection`, and `total_file_count` / `total_size_bytes` remain absent at `Dataset` level. The bundle gives per-feature record counts but no file counts or byte sizes. The audit confirmed the omission is correct.

### 4.10 Core `source_caveats` claims about the core schema

**Left as-is, with the wording adjusted.** The core `source_caveats` still lists the slots whose content was folded elsewhere. The original phrasing asserted these are slots "the core schema does not declare"; the reconciled wording is "slots this record's schema does not declare … was folded into the nearest declared slot", and now names the three destinations concretely (file-layout detail into `distribution_formats`, compensation into the `informed_consent` notes, the citation into `notes`). This is the same claim, but the reader can now see where each piece went and check it. As with finding 3.4, no core schema digest was available in this session to verify the underlying claim, and the report records that limitation rather than papering over it.

---

## 5. Changes not arising from a numbered finding

Two consequential edits follow from the fixes above rather than standing on their own:

- **Core `distribution_formats` expanded.** Because `distributions` was removed (§2.1), the four `distribution_formats` entries in the core record absorbed its content and are now substantially longer than the full record's. The full record retains the same information across `distribution_formats` *and* `file_collections`, a slot the core schema does not declare. The two records assert the same facts by different routes.
- **`source_caveats` extended in both records.** Both now carry, in addition to the original paragraphs, an "Identifier" paragraph (§4.7), a "Substrate mappings" paragraph (§4.2/4.3), and an expanded "Authorship and roles" paragraph (§3.6). The core record's "Core projection" paragraph was rewritten (§4.10).

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Findings addressed by a change | 6 | 6 |
| Findings left as-is with reasoning | 4 | 5 |
| Findings not applicable to this record | 7 | 6 |

Both high-severity findings were structural defects in the core record and both were fixed by relocating content into declared slots rather than by discarding it. Of the five medium findings, three were fixed (enum reversion, full-record preprocessing detail raised to match, unsupported T-CAIREM characterization removed) and two were left standing with the reasoning recorded (compensation and citation relocation, both forced by the core schema's slot set as this run understands it). The one unsupported factual claim in either record — the T-CAIREM phrasing — is gone. The CRediT roles are now transcribed from a named source section rather than inferred, which reduced the number of populated `credit_roles` on two creators and expanded it on three others.

The two records no longer disagree on any factual point. Where their content differs, it differs only in routing: the core record folds into declared slots what the full record carries in slots the core schema does not declare, and its `source_caveats` says so.