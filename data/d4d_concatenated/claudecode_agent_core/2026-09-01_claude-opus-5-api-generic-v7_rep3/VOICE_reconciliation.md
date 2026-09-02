# VOICE D4D Reconciliation Report

**Project:** VOICE (the Bridge2AI Precision Public Health Grand Challenge)
**Label:** 2026-09-01_claude-opus-5-api-generic-v7_rep3
**Arm:** BASELINE (input documents only)
**Phase:** 4 — strict reconciliation of the Phase 1 full record and the Phase 2 core record against the Phase 3 audit.

---

## 1. Audit summary

Phase 3 returned thirteen findings against the full record: two major, three moderate, eight minor. No findings were raised against the core record independently — the core is a projection, so every full-record change propagates to it.

The audit found no defects in referent selection (the adult v3.1.0 PhysioNet release), version and DOI handling, enum usage, CURIE-versus-URI discipline, required-key satisfaction, or source-conflict handling in `source_caveats`.

---

## 2. Findings addressed

### 2.1 `updates` emitted as a list (major) — **fixed**

The schema digest declares `updates` as *UpdatePlan* with no `[many]` marker: a single-valued object slot. The original full record emitted it as a YAML sequence:

```yaml
updates:
- frequency: Semi-annual, that is twice a year.
```

The reconciled record emits it as a mapping:

```yaml
updates:
  frequency: Semi-annual, that is twice a year.
```

This was a validation-blocking shape defect — an array where the schema requires an object. The same correction was applied in the core record, which had inherited the list form.

### 2.2 `creators` omitted (major) — **fixed**

The original full record left `creators` empty and packed authorship into the free-text `created_by` string, which ran to a paragraph naming both co-PIs and eleven institutions.

The reconciled record populates `creators` with eighteen Creator objects. Seventeen name an individual in `principal_investigator` with an `affiliations` entry carrying a minted fragment `id` and the affiliation string as the source gives it; six carry `credit_roles` drawn from the CRediT statement in the feasibility publication. The eighteenth entry carries no `principal_investigator` and exists to record, in `notes`, that the PhysioNet v3.1.0 author list names 117 further contributors and that the project documentation states over 50 investigators contributed.

`created_by` was correspondingly trimmed from the eleven-institution paragraph to a single sentence naming the consortium and the two co-PIs, since the institutional detail now lives in the structured affiliations.

Two `source_caveats` were attached: one on Vardit Ravitsky, whose affiliation differs between the feasibility publication (University of Montreal) and the white paper and documentation (The Hastings Center); one on Alistair Johnson, whose credit roles are inferred from described project roles rather than a CRediT statement. One further caveat on the collective entry records that individual entries are limited to contributors for whom the bundle supplies an affiliation or a named role.

### 2.3 Unattested content warning (moderate) — **fixed**

The original `content_warnings[0].warnings` carried two items. The first asserted that phenotype tables contain responses covering "depression, suicidal ideation, anxiety, post-traumatic stress, substance use and psychiatric history, which some users may find distressing." The audit found this unattested: the bundle's healthsheet answers the offensive/safety-risk question solely with reference to free-speech transcription, and "suicidal ideation" is supplied from outside knowledge of PHQ-9 item content that the bundle never enumerates.

The reconciled record removes that item. `warnings` now carries only the free-speech item, which is directly attested. The accompanying `source_caveats` was rewritten: it previously said residual exposure "is limited to questionnaire content and static features"; it now says "is limited to static features," dropping the reference to the removed claim.

### 2.4 Grant identifiers in `notes` rather than `grants` (moderate) — **fixed**

The original `funders[0]` placed every award identifier into a prose `notes` field. FundingMechanism declares `grants` with range Grant[].

The reconciled record populates `grants` with four Grant objects, each with a minted fragment `id`, a `name` carrying the identifier as its source writes it, and a `description` giving the surrounding facts (project period, principal investigator, application ID, award amount, which source cites it). `grantor` was shortened from a sentence naming both the funder and the awardee institution to the funder alone, since the awardee is now stated in the grant description. A `notes` field survives, but holds only the two apparently corrupted award strings from the documentation acknowledgement text, and a `source_caveats` records that identifiers differ across sources and are each recorded as written.

### 2.5 `file_collections` omitted (moderate) — **fixed**

The bundle supplies explicit named directory trees. The reconciled full record populates `file_collections` with four FileCollection objects — `features`, `metadata`, `phenotype` and `b2ai-voice-audio` — each with a minted fragment `id`, a `name`, a `path`, a `collection_type` from the declared enum (`processed_data`, `metadata`, `processed_data`, `raw_data` respectively) and a `description` naming the files the bundle names. The audio collection additionally carries `conforms_to` and `conforms_to_standard: [BIDS]`.

No `file_count` or `total_bytes` values were supplied: the bundle states neither.

In the core record these appear under `distributions`, the core schema's corresponding slot, carrying the same identifiers, names, paths and descriptions.

### 2.6 `instances[1].counts` inferred (minor) — **fixed**

The original recorded `counts: 32522` for the recording instance. The bundle gives 32,522 as the record count for `torchaudio_pitch.parquet` specifically, not as a recording total for v3.1.0.

The reconciled record removes `counts` from that instance entirely. The per-feature counts survive in `notes`, now prefaced with "The v3.1.0 release does not state a single recording total." A `source_caveats` was added recording that the documentation gives approximately 61,937 voice-derived recordings for v3.0, that the preferred PhysioNet source gives only per-feature counts, and that no value is therefore recorded.

The participant instance retains `counts: 833`, which is directly attested and consistent across sources.

### 2.7 Non-resource entry in `external_resources` (minor) — **fixed**

The original final ExternalResource entry stated the dataset "is self-contained and does not rely on external resources for interpretation" with `archival: false` — a negative statement occupying a slot meant to name a resource.

The reconciled record replaces that entry with one naming the Bridge2AI Voice Scholars training program at `https://www.b2aivoicescholars.org/`. That URL had previously sat inside `existing_uses[0].examples`, where it described a training offering rather than an existing use of the data; moving it puts it in the slot it answers and vacates the misused ExternalResource entry in one step. `existing_uses[0].examples` accordingly now carries a single item, the Summer School and hackathon use.

### 2.8 `inter_annotator_agreement` inferred (minor) — **fixed**

The original read "Not assessed; a single labeler provides one label per instance." The bundle states only that there is a single labeler; it never states that agreement was not assessed.

The reconciled value reads: "A single labeler provides one label per instance, so no inter-annotator agreement is reported." This states the attested fact and its consequence without asserting a decision the sources do not record.

### 2.9 `data_governance.accountable_organization` omitted (minor) — **fixed**

The reconciled record populates it as an Organization with a minted fragment `id` and `name: University of South Florida Board of Trustees`, which the Data Transfer and Use Agreement names as the provider institution.

The `stewardship_roles` list was also restructured while the slot was open: it was a single 100-word blob covering four distinct roles, and is now four separate list items. A `notes` field was added recording NIH support and the hosting platform's technical role, which the audit had noted as displaced content.

### 2.10 Tension between `errata` and `updates.update_details` (minor) — **fixed**

`updates.update_details` originally asserted flatly that "There is no separate erratum document," while `errata` carried three entries — a reading that looked self-contradictory.

Two changes reconcile them. `update_details` now says corrections "are communicated through a changelog published online with the dataset metadata for each version rather than through a separate erratum document," which states the mechanism rather than denying the content. Each of the three `errata` entries gained a `source_caveats` recording that the item comes from the PhysioNet release notes rather than from an erratum document; the first also notes the documentation's contrary statement.

### 2.11 v1.0 release date missing from `distribution_dates` (minor) — **fixed**

The original list began at 2025-01-17 (v1.1). The reconciled list opens with "End of November 2024 (version 1.0, on the Health Data Nexus)," and a `source_caveats` records that the date comes from the project documentation and that the PhysioNet version list does not carry it.

### 2.12 `external_resources[5].archival: true` inferred (minor) — **fixed**

The original asserted `archival: true` for the Interspeech protocol publication on the strength of its ISCA archive URL. The bundle supplies the URL but makes no archival claim; the healthsheet answers the external-resource permanence questions with "NA."

The reconciled entry drops `archival` and instead carries `future_guarantees`, recording that the healthsheet answers those questions with "NA." The three other entries retaining `archival: true` — the REDCap repository and the documentation repository, both explicitly Zenodo-archived — were left unchanged, since Zenodo deposition is an archival statement the bundle makes directly.

### 2.13 `subsets` omitted (minor) — **fixed**

The reconciled full record populates `subsets` with eight DataSubset objects. Five are the disease cohorts — voice disorders, respiratory, neurological and neurodegenerative, mood and psychiatric, controls — each with `is_subpopulation: true`, `is_data_split: false`, and a description compiling the inclusion criteria, exclusion criteria and gold-standard validation methods that Table 1 of the documentation gives per cohort. Three are the release's structural components: derived audio features, phenotype tables, and recording metadata, each with both boolean flags false.

Each carries a minted fragment `id` on the dataset DOI.

---

## 3. Findings left as-is

None. All thirteen findings were addressed.

---

## 4. Changes made beyond the audit findings

Three structural corrections were made while adjacent slots were open. Each is a shape correction, not a content change.

**`missing_data_documentation[0]`** — `missing_data_patterns` and `missing_data_causes` were emitted as YAML lists in the original. Neither is marked `[many]` in the schema digest for MissingDataDocumentation. Both were collapsed into single strings preserving all the original content.

**`sampling_strategies[0].strategies`** — likewise a list in the original, not marked `[many]`; collapsed into a single string preserving all three strategies.

**`machine_annotation_tools[0].tool_descriptions`** and **`is_deidentified.identifiers_removed`** and **`participant_privacy[0].privacy_techniques`** — the same correction, applied for the same reason. `tools` and `tool_accuracy` remain lists, as the digest permits.

These follow the same rule that produced fix 2.1: a scalar-ranged slot emitted as a sequence is a shape defect regardless of how readable the sequence is.

---

## 5. Core record

The core record was regenerated as a projection of the reconciled full record. Every change above propagates. The specific core consequences:

- `updates` is now a mapping.
- `creators` is populated with the same eighteen entries.
- `distributions` (the core counterpart to `file_collections`) is populated with the four collections.
- `content_warnings[0].warnings` carries one item.
- `funders[0].grants` is populated.
- `instances[1]` has no `counts`.
- `existing_uses` and `external_resources` reflect the Scholars-program move.
- The five scalar/list shape corrections carry through.

The core header block carries `# Phase 4 reconciliation: completed` and the required `# Sources:` line pointing at the full record.

`conforms_to_class` is `CoreDataset` and `conforms_to_schema` points at the core schema, as the core projection requires; these differ from the full record by design, not by defect.

---

## 6. Referent

Both records describe a single referent: **the Bridge2AI-Voice adult dataset, PhysioNet version 3.1.0** (DOI 10.13026/8xbn-nq66, published 1 May 2026). This was the Phase 1 choice and it was held through reconciliation.

The pediatric dataset (DOI 10.13026/h995-bt35) is a distinct PhysioNet project with its own participants, its own ethics approval (The Hospital for Sick Children REB rather than the USF IRB) and its own version series; it is recorded through `related_datasets` with `relationship_type: is_supplemented_by` rather than folded into the referent. The controlled-access raw audio on Synapse is likewise recorded through `related_datasets` with `derives_from`, since the released features derive from it but it is disseminated under a separate mechanism.

Earlier versions are recorded through `is_new_version_of` and the version-independent DOI through `is_version_of`.

---

## 7. Source-conflict handling

The declared ranking was applied where sources disagree:

| Conflict | Resolution |
|---|---|
| v3.0.0 vs v3.1.0 on FFT parameters, record counts, file layout | v3.1.0 preferred (v3.0.0 is marked SUPERSEDED BY v3.1.0) |
| Hosting: Health Data Nexus (documentation, tier 2) vs MIT LCP (PhysioNet, tier 1) | PhysioNet preferred; caveat records that the documentation statement describes v1.0 |
| Recording total: ~61,937 (documentation, tier 2) vs per-feature counts only (PhysioNet, tier 1) | PhysioNet preferred; `counts` omitted, caveat records both |
| Enrollment target: 10,000 (documentation) vs 30,000 (IRB protocol) | Both tier 2 — ranking cannot decide, so both figures recorded in `source_caveats` |
| Ravitsky affiliation: University of Montreal (publication, tier 3) vs The Hastings Center (documentation tier 2, white paper tier 3) | Documentation preferred; caveat records both |

---

## 8. Validation

| Record | Command | Result |
|---|---|---|
| Full | `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` | Pass |
| Core | `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` | Pass |

---

## 9. Outcome

Thirteen of thirteen audit findings addressed; none deferred. Five additional shape corrections applied. Both records validate. Referent held constant across both records and stated here.