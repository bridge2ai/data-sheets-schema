# Reconciliation Report — VOICE

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep3`
**Arm:** BASELINE (declared input bundle only)
**Bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep3/VOICE_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep3/VOICE_d4d_core.yaml`

---

## 1. Referent

`Dataset` admits a single referent. Both records are held to:

> **The Bridge2AI-Voice adult dataset as published on PhysioNet, at release 3.1.0 (1 May 2026), comprising derived audio features and linked phenotypic data for 833 participants.**

This choice is forced by the bundle's own weighting: the declared sources include four PhysioNet release pages for `b2ai-voice` and the project documentation site, which together describe one continuously versioned adult resource. The Bridge2AI-Voice **Pediatric** dataset is a distinct PhysioNet project with a separate cohort, a separate protocol, a separate REB (Hospital for Sick Children), and its own DOI lineage; the bundle's own curation note states it is "not a version of it." It is therefore treated as a related dataset, not as part of the referent. Version 3.1.0 is selected over 3.0.0 because the bundle's curation note for the 3.0.0 capture explicitly marks it superseded and directs preference to 3.1.0 on disagreement.

The referent choice is applied consistently across both records: counts, file inventories, feature record totals, and release metadata all describe 3.1.0, with earlier releases represented historically rather than as the subject.

---

## 2. Audit outcome

Thirteen findings, none high severity: two medium affecting content, one medium affecting cross-record consistency, ten low. No fabricated identifiers, URLs, grant numbers, or counts were detected. No evidence of prior-D4D factual reuse. The bulk of both records verified cleanly against source text, including per-feature record counts, preprocessing parameters, the v3.0.0→v3.1.0 phenotype-tree migration, DUA and IP terms, and de-identification procedure.

| # | Severity | Record | Slot | Disposition |
|---|---|---|---|---|
| 1 | medium | both | `description` | **Corrected** |
| 2 | medium | full vs core | `is_tabular` | **Corrected** (core) |
| 3 | medium | full | `external_resources` → `related_datasets` | **Corrected** |
| 4 | low | both | `doi` | **Corrected** |
| 5 | low | both | `confidential_elements` | **Corrected** |
| 6 | low | both | `content_warnings` | **Corrected** |
| 7 | low | both | `errata` | **Corrected** |
| 8 | low | both | `data_protection_impacts` | **Corrected** |
| 9 | low | both | `sampling_strategies` | **Corrected** |
| 10 | low | core | `human_subject_research` | **Left as-is** |
| 11 | low | core | eleven omitted slots | **Partially corrected** |
| 12 | low | full | `creators` | **Corrected** |
| 13 | low | both | `known_biases` | **Partially corrected** |

---

## 3. Changes to the full record

**Finding 1 — `description`.** The enumeration of cohort categories substituted "controls" for "pediatric." Both the PhysioNet Methods section ("five predetermined groups (Respiratory disorders, Voice disorders, Neurological disorders, Mood disorders, Pediatric)") and the documentation site give the same five, with controls appearing separately as an additional non-disease group throughout the protocol tables. The description was rewritten to name the five categories as stated and to note controls as an additional recruited group. This matters beyond tidiness: the substitution would have implied the adult release covers all five stated categories, when the pediatric category is served by a separate dataset.

**Finding 3 — `related_datasets`.** The pediatric dataset and the superseded releases (1.1, 2.0.0, 2.0.1, 3.0.0) were carried in `external_resources`. `DatasetRelationship` is the field that asks for typed inter-dataset relationships, and the bundle supplies both a relationship characterization and resolvable targets. Five `DatasetRelationship` objects were added — one per prior release with a prior-version relationship, one for the pediatric dataset typed as a related but non-derivative resource, consistent with the bundle's explicit statement that the two are distinct cohorts rather than versions. `external_resources` was reduced to the publications, code repositories (`b2aiprep`, `senselab`, `bridge2ai-redcap`, `bridge2ai-docs`), the Zenodo REDCap deposit, the Synapse raw-audio location, and the documentation site — i.e. resources that are not themselves datasets in this sense.

**Finding 4 — `doi`.** `version`, `page`, and `citation` all pinned release 3.1.0 while `doi` carried the concept-level "latest version" identifier `10.13026/37yb-1t42`. PhysioNet distinguishes the two explicitly on the release page. `doi` was changed to the version DOI `10.13026/8xbn-nq66`, aligning the four fields. The concept DOI was retained as an `external_resources` entry so the information is not lost.

**Finding 5 — `confidential_elements`.** Two problems. The second object described REDCap-flagged sensitive fields that were *removed before release*; these are not confidential information within the dataset and the object was deleted. The first object (controlled-access raw audio) is well founded — raw waveforms are genuinely withheld and gated through DACO and Synapse — and was retained, but the healthsheet's direct negative answer to the confidentiality question ("Does the dataset contain data that might be considered confidential…? No") was added to the object's text so the disagreement between the healthsheet and the access architecture is visible rather than silently resolved.

**Finding 6 — `content_warnings`.** The second object warned that item-level mental-health instrument responses may distress readers. The bundle documents these tables but nowhere characterizes them as distressing or issues any warning about them; this was generator inference. Deleted. The free-speech transcription warning, which the source does state, was retained.

**Finding 7 — `errata`.** The four errata are each individually documented in release notes and were retained. The healthsheet's statement — "There is no erratum. A changelog for each dataset version is published online with the dataset metadata" — was added as a fifth entry recording the maintainers' position, so a reader is not left with the impression that the project publishes formal errata when it explicitly disclaims doing so.

**Finding 8 — `data_protection_impacts`.** One object asserted both that a structured re-identification assessment was conducted by ethicists and that no impact analysis had been conducted. Both statements are in the bundle, from different sources. Split into two objects: one recording the ethicist-led sensitive-field review, the controlled-access memorandum, and the transcript screening; one recording the healthsheet's "No" to the impact-analysis question. The disagreement is now representable rather than collapsed.

**Finding 9 — `sampling_strategies`.** The HVEC definition used the documentation site's ">50 patients per month from the same disease category." The IRB protocol in the same bundle defines HVEC as ">1000 patients per year" with multidisciplinary programs. Both figures were included with attribution to their respective sources.

**Finding 12 — `creators`.** Four role attributions extended past the evidence: Sigaras as co-lead of the application (bundle: co-lead of tools/software/IT infrastructure); Ghosh as owner of the preprocessing toolchain (bundle: lead, Mood Disorders — his toolchain authorship is separately evidenced and was kept, but not as a consortium role); Bélisle-Pipon and Ravitsky assigned to "the Ethics module"; Bolser to "respiratory and cough acoustics" (bundle gives no module assignment for either). Each was trimmed to the role the bundle states, or to affiliation alone where no role is stated. No creator was removed.

**Finding 13 — `known_biases`.** `BiasTypeEnum` was consulted and `bias_type` populated for the four entries where a permissible value corresponded defensibly to the described bias. Two entries — site-device confounding, and the site-dependent screening/device coupling — remained description-only, as no listed value corresponds and forcing an approximate category would misrepresent the evidence more than leaving the field unset. `DatasetBias` requires no keys, so both states validate.

---

## 4. Changes to the core record

Findings 1, 4, 5, 6, 7, 8, 9, and 13 were applied to the core record identically to the full record, in the same wording where the core schema exposes the same slot.

**Finding 2 — `is_tabular`.** The core record asserted `false`; the full record omitted the slot. The referent is mixed: Parquet tensor arrays (spectrograms, MFCCs, PPGs, EMA traces) alongside TSV phenotype and feature tables. A single boolean cannot represent this, and neither value is defensible. `is_tabular` was **removed from the core record**, matching the full record's omission. Omission is the correct answer where a boolean field cannot express what the evidence shows.

**Finding 11 — omitted slots.** The eleven full-record slots absent from core were checked against `data_sheets_schema_core_all.yaml`. Ten (`subsets`, `variables`, `file_collections`, `relationships`, `direct_collection`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `third_party_sharing`) are not in `CoreDataset`'s slot inventory; their absence is structural, not a defect. `citation` **is** in the inventory, is basic descriptive metadata, and is fully supported — PhysioNet supplies a formatted citation for 3.1.0. It was added to the core record, matching the full record verbatim.

---

## 5. Left as-is

**Finding 10 — core `human_subject_research`.** `CoreDataset` does not expose `participant_compensation`. The compensation tiers ($40 under 90 minutes, $80 over, three-session and $120 caps) are therefore not misplaced in core; they have no other field to occupy, and dropping them would lose evidenced information that the core record can otherwise carry. Left unchanged. The full record continues to carry the same facts in `participant_compensation`, which is the correct field there.

**Represented disagreements left standing.** Four source conflicts were already handled correctly by both records and were not touched: Ravitsky's affiliation (The Hastings Center vs. University of Montreal), the healthsheet's claim that instances are unrelated against the actual participant/session key structure, the documentation site's "~61,937 voice-derived recordings" against the per-feature counts on the 3.1.0 release page, and the Health Data Nexus vs. PhysioNet hosting question. In each case both positions are stated with attribution. This is the correct treatment and no change was warranted.

**Verified content.** Participant counts (833 at 3.1.0; 306 at 1.0; +136 at 2.0; +391 at 3.0.0), per-feature record counts (28,640–32,522), preprocessing parameters (16 kHz monaural, Butterworth anti-aliasing, 25 ms window / 10 ms hop / 400-point FFT, 60 Mels, 40 phoneme PPGs at 100 Hz, sparc at 50 Hz), the full v3.1.0 phenotype directory tree including the migration of `adhd_adult`, `ptsd_adult`, and `psychiatric_history` from `diagnosis/` to `questionnaire/`, the acoustic task inventory, validated-questionnaire coverage by cohort, DUA and intellectual-property terms, the Fort Lauderdale commitment, and the de-identification procedure were all confirmed line-by-line against source text and required no correction.

---

## 6. Cross-record consistency after reconciliation

Both records now describe the same referent at the same version, with the same cohort enumeration, the same DOI level, the same treatment of the confidentiality and erratum contradictions, the same split DPIA, and the same dual HVEC definition. The single remaining populated/omitted asymmetry is `is_tabular`, now omitted in both. All other core omissions correspond to slots `CoreDataset` does not declare.

---

## 7. Validation

Both files were validated after reconciliation:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep3/VOICE_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep3/VOICE_d4d_core.yaml
```

Both pass. Required keys are present on every object of a constrained range: `id` on `Dataset`, `DataSubset`, and `FileCollection`; `relationship_type` and `target_dataset` on all five new `DatasetRelationship` objects; `variable_name` on all `VariableMetadata`; `source_description` on all `RawDataSource`.

---

## 8. Provenance

No previously generated D4D record was read, opened, searched, or consulted at any phase. Factual inputs were the declared bundle and the two schema files only. The live provenance record was written with:

```
poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-07-31_claude-opus-5-generic-v2_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt
```