# VOICE D4D Reconciliation Report

**Project:** VOICE (the Bridge2AI Precision Public Health Grand Challenge)
**Label:** 2026-09-01_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (input documents only)
**Phase:** 4 — strict reconciliation of the full and core records against the Phase 3 audit

---

## 1. Scope

The Phase 3 audit returned twelve findings against the full record: one high severity, three medium, and eight low. No fabrication, no out-of-bundle content, and no out-of-enum value was detected. Every finding was adjudicated. Where a finding was accepted, the change was applied to the full record and then carried into the core record by re-projection. Where a finding was declined, the reason is given below.

Both records were reviewed against the declared bundle before any edit; no new facts were introduced during reconciliation. All values in the reconciled records trace to passages already receipted in Phase 1.

---

## 2. Findings accepted and changed

### 2.1 Identifier / version inconsistency (high, `id`; medium, `issued`)

**Audit finding.** The record declared `version: 3.1.0`, `issued: 2026-05-01T00:00:00Z`, and a citation carrying DOI `10.13026/8xbn-nq66`, but was identified by `doi:10.13026/37yb-1t42` — the version-agnostic DOI that PhysioNet resolves to the latest version — in both `id` and `doi`. A version-pinned record identified by a version-agnostic DOI is internally inconsistent.

**Adjudication.** Accepted. The `source_caveats` block already declared the referent as "the adult Bridge2AI-Voice dataset published on PhysioNet, at version 3.1.0", so the version pin is the correct reading and the identifier was the defective element. The bundle supplies both DOIs explicitly (chunk c018 gives `10.13026/8xbn-nq66` as the version 3.1.0 DOI and `10.13026/37yb-1t42` as the latest-version DOI), so the repair is a re-selection among attested values rather than a new claim.

**Changes in the full record.**

| Slot | Before | After |
|---|---|---|
| `id` | `doi:10.13026/37yb-1t42` | `doi:10.13026/8xbn-nq66` |
| `doi` | `10.13026/37yb-1t42` | `10.13026/8xbn-nq66` |
| `version_access.latest_version_doi` | `doi:10.13026/8xbn-nq66` | `doi:10.13026/37yb-1t42` |

The two DOIs were, in effect, transposed: the version-agnostic DOI now sits in `version_access.latest_version_doi`, where the schema's description of that slot places it, and the version-pinned DOI identifies the record. `version_access.version_details` was left unchanged, since it already listed both DOIs correctly and explained which resolves to what.

`issued` was **left unchanged** at `2026-05-01T00:00:00Z`. The audit flagged it only as collateral to the identifier problem, and once the identifiers are pinned to 3.1.0 the issuance date agrees with them.

`source_caveats` was amended to state the identifier decision explicitly. The opening sentence now reads that the record "is identified by that version's DOI, 10.13026/8xbn-nq66; the version-agnostic latest-version DOI, 10.13026/37yb-1t42, is recorded in version_access.latest_version_doi."

**Carried to core.** `id`, `doi`, `version_access.latest_version_doi`, and `source_caveats` were updated identically in the core record.

### 2.2 `was_derived_from` naming a distribution endpoint (medium)

**Audit finding.** `was_derived_from: https://www.synapse.org/Synapse:syn72370534/` named the Synapse controlled-access landing page. The bundle presents Synapse as an access route for the raw audio, not as a resource this dataset was derived from, and the same URL already appears in `raw_data_sources[0].access_details`.

**Adjudication.** Accepted. The slot asks for a resource from which this resource was derived; a landing page for a gated distribution of the raw audio is a route to that audio, not a provenance antecedent. Omission is the correct answer under the "prefer omission over inference" rule, because the bundle does not name any external resource as the derivation source — the raw audio was collected under this project's own protocol.

**Change in the full record.** The `was_derived_from` slot was **removed entirely**. The Synapse URL survives in `raw_data_sources[0].access_details` and in `distribution_formats[2].access_urls`, where it describes what it actually is.

**Carried to core.** `was_derived_from` was removed from the core record as well.

### 2.3 `instances[0].data_substrate` approximating a substrate (medium)

**Audit finding.** The participant-level instance carried `data_substrate: B2AI_SUBSTRATE:41` (Tab-separated values). A participant's data in this release is carried across both Parquet feature files and TSV phenotype tables; assigning TSV to the participant instance and Parquet to the recording instance encodes a file-format split rather than a property of the instance, and the bundle does not state that a participant instance is a TSV.

**Adjudication.** Accepted. The schema digest is explicit: "If no term fits, omit the slot rather than approximate."

**Change in the full record.** `data_substrate` was removed from `instances[0]`. `data_topic: B2AI_TOPIC:25` (Phenotype) was retained, and `instances[1]` retains both `data_topic: B2AI_TOPIC:36` (Voice) and `data_substrate: B2AI_SUBSTRATE:30` (Parquet), which the audit did not challenge and which the bundle supports directly — the dense derived features are distributed as Parquet.

**Carried to core.** Identical change in the core record's `instances[0]`.

### 2.4 `sampling_strategies[0].is_random` — a supported omission (low)

**Audit finding.** `is_random` was omitted while `is_sample: true` and `is_representative: false` were set. The bundle states the sampling method explicitly — "Sampling Method: Non-Probability Sample" (chunk c008) — which supports `is_random: false`.

**Adjudication.** Accepted. This is the only finding in the audit that added a value rather than removing or relocating one, and the evidence is a direct statement.

**Change in the full record.** `is_random: false` was added to `sampling_strategies[0]`, between `is_sample` and `is_representative`.

**Carried to core.** Identical addition.

### 2.5 Creator object standing in for the consortium (low)

**Audit finding.** The sixteenth Creator entry carried no `principal_investigator`, only an `affiliations` entry named "Bridge2AI-Voice Consortium" plus a `notes` string about the consortium's size. `affiliations` is declared `Organization[]`; using it to stand in for an unnamed collective author, with the substance in `notes`, populates the object shape without populating the field the class declares for the creating party. The consortium already occupies `created_by`.

**Adjudication.** Accepted. The entry duplicated `created_by` and carried no declared-field content.

**Change in the full record.** The sixteenth Creator entry was **removed**. The `creators` list now holds fifteen entries, each with a named `principal_investigator`. The consortium remains recorded in `created_by: Bridge2AI-Voice Consortium`. The consortium-size information, which was the substance of the removed `notes`, is preserved in `source_caveats`, where the sentence about consortium size was extended to add "the PhysioNet author list for version 3.1.0 names over 120 contributors" — so no bundle-supported fact was lost.

**Carried to core.** Identical removal; the core `creators` list also now holds fifteen entries.

### 2.6 `existing_uses[0].examples` shaped as prose (low)

**Audit finding.** `examples` was populated with a single prose string on ExistingUse, while the sibling `intended_uses[*].examples` in the same record were emitted as lists. The same-named slot was shaped two ways in one record.

**Adjudication.** Accepted as an internal-consistency repair.

**Change in the full record.** `existing_uses[0].examples` was converted from a scalar string to a one-item list. The text is unchanged.

**Carried to core.** Identical change.

### 2.7 ContentWarning pointing against its own caveat (low)

**Audit finding.** The `warnings` list asserted that the protocol includes free speech tasks whose content cannot be fully controlled, while the `source_caveats` recorded that the higher-ranked PhysioNet source states the free-speech transcripts and derived features were removed from the release. The warning and its caveat pulled in opposite directions: the warning read as applying to the released artifact, which per the preferred source no longer carries that text.

**Adjudication.** Accepted. The fix is to make the warning distinguish the collection protocol from the released artifact, which both sources support.

**Change in the full record.** The single `warnings` entry was rewritten. It now opens "The collection protocol includes free speech tasks…" and closes "In the released feature-only dataset this risk is reduced: transcripts of free speech audio were removed, and spectrogram-family features derived from free speech recordings were excluded." The `source_caveats` was extended by the clause "and is the one reflected in the warning above", tying the caveat to the resolved warning text.

**Carried to core.** Identical rewrite.

### 2.8 AI-readiness rubric occupying `notes` (low)

**Audit finding.** `notes` carried the full AI-readiness rubric scoring including criterion-level pass/fail detail. The schema directs `notes` to residual content only, after every fitting slot is used. The aggregate scores are dataset commentary that `description` could hold; the criterion-level failures overlap `known_limitations`.

**Adjudication.** Accepted. This is a placement question rather than a factual one, and the schema's ordering — structured slots first, then description, then notes — decides it.

**Changes in the full record.**

- The `notes` slot was **removed**.
- `description` gained a closing sentence carrying the aggregate scores: 100 percent FAIRness, 100 percent provenance, 80 percent characterization, 100 percent pre-model explainability, 100 percent ethics, 50 percent sustainability, 75 percent computability.
- A sixth entry was added to `known_limitations` with `limitation_type: methodological_limitation`, recording the four criteria the self-assessment does not meet: data quality under characterization, domain-appropriate and associated under sustainability, and contextualized under computability.

No rubric fact from the bundle was dropped; the content was redistributed across `description` and `known_limitations`.

**Carried to core.** `notes` removed from the core record; `description` and `known_limitations` updated identically.

### 2.9 Pediatric related dataset identified by a latest-version DOI (low)

**Audit finding.** `related_datasets[0].target_dataset` was `doi:10.13026/mf9s-5r03`, the pediatric project's latest-version DOI, while the `description` described version 1.1.0, whose own DOI is `10.13026/h995-bt35`. The same mismatch as finding 2.1, at lower stakes.

**Adjudication.** Accepted, for consistency with the identifier decision taken in 2.1.

**Changes in the full record.**

| Field | Before | After |
|---|---|---|
| `related_datasets[0].target_dataset` | `doi:10.13026/mf9s-5r03` | `doi:10.13026/h995-bt35` |
| `related_datasets[0].version` | *(absent)* | `1.1.0` |
| `related_datasets[0].description` | *(no DOI sentence)* | closes "The DOI 10.13026/mf9s-5r03 resolves to the latest version of the pediatric dataset." |

A `version: '1.0'` field was also added to `related_datasets[1]`, the Health Data Nexus first release, so that both relationship entries state the version they name. Both DOIs remain in the record; only which one identifies the target changed.

**Carried to core.** Identical changes to both `related_datasets` entries.

### 2.10 Thin FHIR external resource (low)

**Audit finding.** The FHIR profiles entry carried only a prose string with no URL, while every sibling carried at least one. The bundle (chunk c010) gives the description and a "Navigate to Source Code" link whose target is not captured in the text, so no URL can be supplied. Correctly grounded; noted as thin.

**Adjudication.** Accepted in part. No URL can be added without inventing one, so the entry stays URL-less. What can be added is a statement that the absence is deliberate, so a reader can distinguish it from oversight.

**Change in the full record.** The entry text was extended to "…published by the consortium as supporting material alongside the dataset documentation. The documentation lists the resource and links to its source code, but does not give a repository URL in the captured text."

**Carried to core.** Identical extension.

### 2.11 `distribution_formats[*].download_url` absent without explanation (low)

**Audit finding.** No DistributionFormat carried a `download_url`, and the top-level `download_url` was unpopulated. Defensible, since the PhysioNet files are gated, but the record nowhere stated that no direct download URL exists, so a reader could not tell deliberate omission from oversight. The audit judged that "no repair is strictly required."

**Adjudication.** Accepted as an optional clarification, on the same reasoning as 2.10.

**Change in the full record.** A `notes` field was added to each of the three `distribution_formats` entries, each opening "No direct download URL is published:" and giving the gating reason — credentialing plus a signed data use agreement for the two PhysioNet formats, and DACO review plus an institutionally signed DTUA for the Synapse raw audio. No `download_url` was added anywhere; the `access_urls` are unchanged.

Separately, the top-level `page` slot was changed from `https://physionet.org/content/b2ai-voice/` to `https://physionet.org/content/b2ai-voice/3.1.0/`, so that the landing page agrees with the version the record is now pinned to.

**Carried to core.** Identical `notes` additions and the identical `page` change.

### 2.12 Uncaveated tension in `collection_timeframes` (low)

**Audit finding.** `timeframe_details` recorded a 12-month collection period from the project documentation healthsheet, which sits in tension with the IRB protocol's four-year phased study (pilot collection begun November 2023, ongoing November 2024) and with the feasibility study's June–July 2023 window. No caveat recorded the tension, whereas comparable tensions elsewhere were caveated.

**Adjudication.** Accepted. The disagreement is between a tier-2 documentation source and a tier-2 IRB source, so the declared source ranking does not settle it; the rule for same-rank disagreement is to represent what the evidence states rather than silently selecting one.

**Change in the full record.** A `source_caveats` field was added to `collection_timeframes[0]` naming all three statements — the 12-month figure, the four-year phased protocol with its November 2023 and November 2024 markers, and the 5 June to 28 July 2023 feasibility window — and stating that the 12-month figure is recorded because the project documentation is the source describing the released dataset's collection window, while noting that "the sources do not settle whether the 12 months are a subset of the wider study period." `timeframe_details` is unchanged, and `start_date`/`end_date` remain omitted.

**Carried to core.** Identical caveat added.

---

## 3. Findings left as-is

No finding was declined outright. Two were accepted only in part, and the unadopted portions are recorded here:

- **`issued` (2.1).** Flagged as collateral to the identifier problem. The value `2026-05-01T00:00:00Z` is unchanged in both records, because pinning `id` and `doi` to version 3.1.0 resolves the inconsistency in the identifiers' favour rather than the date's.
- **FHIR external resource URL (2.10).** No URL was added. The bundle's captured text names the resource and mentions a source-code link but does not give its target; supplying one would be an out-of-bundle claim.
- **`distribution_formats[*].download_url` (2.11).** No `download_url` was added to any entry or to the top level. Only explanatory `notes` were added.

---

## 4. Referent

Unchanged from Phase 1 and held consistently across both records: the record describes **the adult Bridge2AI-Voice dataset published on PhysioNet, at version 3.1.0**. The pediatric release is recorded as a related dataset (`is_supplemented_by`), not as a part or subset. This choice is stated in `source_caveats` in both records, and the identifier repair in 2.1 brings `id`, `doi`, `version`, `issued`, `page`, and `citation` into agreement with it.

---

## 5. Source-conflict handling

The `source_caveats` block, retained and extended, records the conflicts the bundle contains and the ranking applied:

| Conflict | Sources | Resolution |
|---|---|---|
| Recording counts | Project documentation (~61,937 for v3.0) vs PhysioNet per-feature counts | PhysioNet preferred (tier 1 over tier 2) |
| Grant identifier rendering | Five variants across five sources | All five recorded; none preferred |
| Consortium size | 50/12 institutions (white paper), 14 institutions (feasibility publication), 2+10 (documentation), 120+ authors (PhysioNet) | All recorded; none preferred |
| Enrollment target | 30,000 (IRB, white paper) vs 10,000 (documentation, study metadata) | 10,000 recorded as the more recent statement |
| Investigator name spellings | "Jennifer Sui"/"Jennifer Siu", "Frank Rudzizc"/"Frank Rudzicz" | PhysioNet spellings used (tier 1) |
| Free-speech content in release | Documentation vs PhysioNet | PhysioNet preferred; resolved in `content_warnings` (2.7) |
| Collection window | Documentation (12 months) vs IRB protocol (four-year phased) | Both stated; ranking does not decide (2.12) |

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Slots populated (before) | 76 | 72 |
| Slots populated (after) | 75 | 70 |
| Findings accepted | 12 of 12 | carried by projection |
| Slots removed | `was_derived_from`, `notes` | `was_derived_from`, `notes` |
| Slots added | *(none at top level)* | *(none at top level)* |
| Validation | passed | passed |

The net slot-count movement is downward because two top-level slots were removed and none added; the substantive content of both was preserved by redistribution into `description`, `known_limitations`, and `raw_data_sources`.

Both records validate against their declared schemas. The core record is a projection of the reconciled full record and carries `# Sources:` naming it, together with `# Phase 4 reconciliation: completed`.

**Reconciliation outcome: complete. All twelve findings adjudicated; twelve accepted in whole or part, none declined outright; both records validated.**