# CHoRUS D4D Reconciliation Report

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep2`
**Project:** CHoRUS (Bridge2AI AI/ML for Clinical Care Grand Challenge)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Arm:** BASELINE — declared bundle `data/preprocessed/concatenated/CHORUS_preprocessed.txt` only

---

## 1. Referent

Both records describe a single referent: **the CHoRUS dataset** — the multicenter, controlled-access critical care data collection assembled by the CHoRUS data generation project, not the funded project, not the AIM-AHEAD training program, and not the chorus-ai software estate. This choice was held before reconciliation and is unchanged after it. Facts about the award, the training program, and the GitHub repositories are retained only where they bear on the dataset (funding, existing uses, maintenance, extension mechanism, external resources), and the `notes` slot on both records continues to mark the MIT/Apache-2.0 software licensing as *not* the dataset's license.

---

## 2. What the audit found

The audit returned 33 findings across both records. Two dominant classes:

- **Caveated inference** — eight slots asserted content the bundle does not state, several of them booleans, several self-declaring the inference in their own `source_caveats`. A caveat cannot soften a boolean.
- **Structural misplacement** — grant identity carried by a resolver URL while attested award numbers sat in prose; nine `DistributionFormat` objects overloading the `format` string with access-control and metadata-status content; all six creators typed as `principal_investigator`.

Plus one unit mismatch, one unattested geographic claim, and three core-vs-full divergences to reconcile.

No fabricated registry identifiers, no resolver URL in a `uriorcurie` slot with a declared prefix available, no out-of-enum values, and no prose where a list is declared. The tier-2-over-tier-4 disagreement on released admission counts (50,000 vs. "over 45K") was correctly resolved and documented; it needed no change.

---

## 3. Changes made — both records unless noted

### 3.1 Removed: unsupported inference (high-value corrections)

| Slot | Original | Reconciled | Why |
|---|---|---|---|
| `machine_annotation_tools[2]` (CTP-deid) | Present, described as "supporting de-identification of clinical imaging data", with a caveat conceding the role was inferred from the repository name | **Removed entirely.** Both records now list two tools: OHNLP toolkit and privacy_scan_tool | The bundle lists `CTP-deid` in the repository index with no description at all. A self-declared inference is still an unsupported claim; omission is the correct answer |
| `ethical_reviews` | One object whose `review_details` described the project's ethics pillar (focus groups, legal-landscape analysis) with a caveat stating no IRB approval or ethics determination is reported | **Slot removed from both records** | The value did not answer the field. Per the v2 rule, a value recording that something is absent or lives elsewhere has not populated the slot |
| `human_subject_research` | `involves_human_subjects: true` plus `special_populations` | **Slot removed from both records** | `involves_human_subjects` is a regulatory determination. The bundle supplies only that the data are patient-derived and retrospectively extracted; it never makes that determination |
| `at_risk_populations` | `at_risk_groups_included: true` with `special_protections` repackaging general controlled-access statements | **Slot removed from both records** | PICU/NICU coverage is attested; the at-risk framing and group-specific protections are not. The bundle never ties any protection to minors |
| `direct_collection` (full record only) | `is_direct: false` with a caveat stating the sources do not use the terms direct or third-party collection | **Slot removed from the full record** | The boolean asserted what the caveat disclaimed. The retrospective-extraction fact it rested on is already carried in `acquisition_methods[0]` and `raw_data_sources` |
| `acquisition_methods[0].was_reported_by_subjects` | `false` | **Key removed;** `was_directly_observed: true` retained | The bundle never addresses whether any element originated as subject report. A negative boolean is an assertion, not a silence |
| `data_governance.committee_members` | Six named individuals (the Leadership Team roster) | **Key removed** | The bundle names them as the Bridge2AI CHoRUS Leadership Team, never as an access or governance committee. The record's own caveat conceded no such committee is described |
| `data_governance.committee_contact` | Ciera McCrary | **Key removed** | She is attested as "MGH, Program Manager" under a website "Contact Us" heading. Her contact details are retained in `maintainers[0].maintainer_details`, where the bundle supports the role |

`data_governance.source_caveats` was rewritten accordingly: it now states that no committee, decision timeframe, or appeal process is described, and that only the registration/licensing route and the access-request contacts are attested. `is_deidentified.deidentification_details` also dropped its trailing clause "and a de-identification repository", which rested on the same CTP-deid inference.

### 3.2 Corrected: unit mismatch

`instances[1].instance_type` changed from *"Radiology imaging study extracted from hospital PACS"* to *"Hospital admission with associated radiology imaging data extracted from hospital PACS."* The count `7642` is unchanged and now denominates the unit the bundle states ("7,642 Admissions with Radiology Data"). The reconciling clause in `notes` ("Count is admissions with radiology data…") was dropped as no longer needed; the 1,000-images-available fact remains.

### 3.3 Corrected: grant identity

`funders[0].grants[0]` gained `name: 1OT2OD032701-01` and a `description` carrying the core project number OT2OD032701, application ID 10472824, award amount, and project period. The free-text `notes` that previously held those numbers was removed, and a `source_caveats` was added to `funders[0]` explaining that the RePORTER project-details URL serves as the `id` because the bundle supplies no registry identifier. The `id` itself is unchanged — no declared prefix covers an NIH award in this schema digest, so the URL remains the right fallback.

### 3.4 Corrected: creator roles

`creators` retains six objects. Only Eric S. Rosenthal keeps `principal_investigator`, which the NIH RePORTER source states. The other five now carry `affiliations` plus a `notes` naming the individual and recording Leadership Team membership, with an explicit statement that the sources give no specific creation role. This preserves all six as creators (the bundle supports their involvement) without asserting a designation for five of them that the bundle does not make.

### 3.5 Corrected: distribution format overloading

All nine `DistributionFormat` objects were split. `format` now carries only the format and schema; the access-control level and metadata-publication state moved to `notes` on each object. Wording was normalized from "metadata planned" to "published metadata schema planned" for the three modalities the webinar table marks as planned (clinical notes, imaging, EEG). No object was added or dropped — nine before, nine after.

### 3.6 Corrected: unattested geographic scope

`known_limitations[2].limitation_description` dropped the trailing "in the United States". The bundle attests 14 contributing hospitals and separately gives "United States of America" as the GitHub organization's location; it does not state that the contributing hospitals are all US-based.

### 3.7 Corrected: status slot

`status` changed from a two-clause narrative sentence to `Released under controlled access; data acquisition ongoing.` The narrative content it carried is unchanged in `updates.update_details`, where it belongs.

### 3.8 Core-vs-full divergences resolved

- **`notes`** — the core record's extra sentence about the holdout test set ("drawn from the same collection") was **removed**. The core `notes` is now identical to the full `notes`. The holdout set remains in the full record's `subsets`.
- **`subsets`** — remains present in the full record and absent from the core. The core schema digest supplied to this run does not enumerate `CoreDataset` slots, so no claim is made here about whether `subsets` is declared on `CoreDataset`; the projection is left as the phase-2 record made it, with the holdout-set fact no longer duplicated as core prose.
- **`third_party_sharing`** — likewise remains present in the full record and absent from the core, unchanged. Same reasoning: no basis in the supplied digest to assert either that the slot is available on `CoreDataset` or that it is not.

---

## 4. Left as-is, with reasons

| Finding | Disposition |
|---|---|
| `subsets[0]` carries little beyond a restatement (low, "borderline rather than defective") | **Kept.** The holdout set is squarely attested and is a real partition of this dataset. A `source_caveats` was added recording that no size, composition, or separate access terms are stated. The minted fragment `https://chorus4ai.org/#holdout-test-set` is correct under the v5 minting rule: it names a part of this dataset, has no referent outside the record, and is anchored on an attested base URI |
| `conforms_to_standard: OTHER` collapsing EDF+/Persyst and OHNLP | **Kept.** The enum admits no finer distinction. This is a vocabulary limit, not a fabrication, and `conforms_to` names both in prose |
| `maintainers[0].maintainer_details` embedding the misspelled email inline | **Kept.** The `Maintainer` class in the digest declares no structured contact field; the transcription-as-printed plus the sibling `source_caveats` flagging the typo is the correct handling. This object now also carries the only surviving statement of Ciera McCrary's role |
| `notes` duplicating software-licensing content also stated in `license_and_use_terms.source_caveats` | **Kept.** The duplication is deliberate: a reader reaching either slot needs to know the MIT/Apache-2.0 licenses are software, not dataset, terms |
| `relationships`, `anomalies`, `splits` unpopulated | **Kept unpopulated.** The bundle supports none of them. Confirmed as audited omissions, not gaps |
| Released-count disagreement (50,000 vs. over 45K) | **Kept as resolved.** Tier 2 `project_documentation` preferred over tier 4 `cohort_2_webinar`, with both values and the preference recorded in top-level `source_caveats`. Unchanged in both records |

---

## 5. Slot counts

| | Full | Core |
|---|---|---|
| Top-level slots before | 47 | 44 |
| Top-level slots after | **43** | **40** |

Full record removed: `direct_collection`, `human_subject_research`, `at_risk_populations`, `ethical_reviews`.
Core record removed: `human_subject_research`, `at_risk_populations`, `ethical_reviews`.
No slot was added to either record. The full/core delta remains `subsets` and `third_party_sharing`, present in full only.

---

## 6. Validation

Both files validated after reconciliation:

- `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` → **pass**
- `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` → **pass**

Header blocks are verbatim as specified, including `# Sources:` and `# Phase 4 reconciliation: completed` on the core record, the latter written only after this phase ran.

---

## 7. Outcome

**Reconciled.** Eight unsupported-inference sites removed rather than hedged; one unit mismatch corrected at the instance type; grant identity, creator roles, and distribution formats restructured into their declared fields; one unattested geographic claim and one narrative status value corrected; the single core-vs-full prose divergence eliminated. The two records are now identical in content except for `subsets` and `third_party_sharing`, `conforms_to_class`, and the header block.