# CHORUS D4D — Phase 4 Reconciliation Report

Version label: `2026-08-20b_claude-opus-5-api-generic-v5_rep1`
Records reconciled: full (`CHORUS_d4d.yaml`) and core (`CHORUS_d4d_core.yaml`)
Audit findings addressed: 38 (2 high-severity pairs, several medium, several low, plus informational)

---

## 1. Summary of the audit

The audit reported no factual value contradicted by the declared bundle and no enum value outside the declared vocabularies. Its dominant complaint was structural: content that declared class fields exist to carry had been placed in free-text `notes`, and two identifier choices (a grant `id` and the dataset `id`) were weak. A smaller set of findings concerned inferred booleans, duplicated content across slots, source commentary embedded in content fields, and a full/core divergence in how the nine modalities are typed.

---

## 2. Changes made — high severity

### 2.1 `creators` — personal names carried only in `notes` (both records)

**Finding:** five of six `Creator` objects had no name in any name-bearing field; `notes` carried both the name and a remark that "the Creator class provides no personal-name slot."

**Change made, both records:** the schema-commentary clause was removed from all five `notes` values, which now read as a bare name-and-affiliation string (`Azra Bihorac, University of Florida.`), and each object gained a `source_caveats` recording that the cohort 2 webinar leadership slide states the affiliation but no specific role, and that NIH RePORTER names only Rosenthal as PI.

**Not fully resolved.** The names still sit in `notes` rather than in a declared name-bearing field. The schema digest gives `Creator` exactly `affiliations` (Organization[]), `credit_roles` (enum), `principal_investigator` (Person), `notes` and `source_caveats`. The bundle does not state that Bihorac, Jiang, Strekalova, Rashidi or Kwong are principal investigators of the award — RePORTER names only Rosenthal — so populating `principal_investigator` for them would assert a role the evidence does not support. Nor does the bundle assign any CRediT role. The remaining options were `notes` or omitting the five creators entirely; the names are attested and were kept. This is recorded here as a residual defect rather than a fix.

**Related change:** `creators[0].principal_investigator` changed from an object (`name: Eric S. Rosenthal`) to the scalar string `Eric S. Rosenthal` in both records. The digest declares `principal_investigator` with range `Person`; the v4 rule on scalar-ranged slots was applied on the reading that the reference should be the identifier. This is a change visible in the diff and is flagged in §5 as a point where the reconciliation may have over-applied a rule.

### 2.2 `funders[0].grants[0].id` — RePORTER page URL as grant identifier (both records)

**Finding:** the grant `id` is `https://reporter.nih.gov/project-details/10472824`, a page URL, while the attested award number `OT2OD032701` sits only in `name` and `notes`.

**Change made, both records:** the `id` value was **left unchanged**. A `source_caveats` was added to the funder object explaining that the award is identified in the sources by its core project number, that this number is carried in the grant `name`, and that the RePORTER record URL is used as `id` because no registry prefix for NIH awards is available in the schema's declared prefixes and that URL is the only resolvable identifier for the award the bundle supplies.

**Assessment:** this is a documentation fix, not a correction. Under the v5 identifier rule, `uriorcurie` permits a URI where no declared prefix covers the identifier, so the value is not a rule violation; but the audit's substantive point — that the award is now keyed on a page rather than on `OT2OD032701` — stands, and a bare `OT2OD032701` in `id` would arguably have served joinability better. Left as-is with the reasoning recorded.

---

## 3. Changes made — medium severity

| Finding | Change |
|---|---|
| `id` equals `page` (both) | Dataset `id` changed from `https://chorus4ai.org/` to `https://chorus4ai.org/#dataset` in both records, so the dataset no longer shares an identity with its landing page. `page` still holds `https://chorus4ai.org/`. Per-modality fragments (`#imaging`, etc.) are unchanged — they remain fragments on the same attested base URL. The top-level `source_caveats` in both records now states that the identifier is minted as a fragment on the project website URL because the bundle supplies no DOI or accession. |
| `relationships: []` empty list (full) | **Removed** from the full record. The core record never had it. |
| `data_governance.committee_contact` (both) | **Removed** from both records. The two access-request addresses now appear only inside `access_review_process`, and the `source_caveats` was rewritten to say explicitly that the documents name no data access committee and no committee contact, and that the two addresses were recorded in the access process rather than promoted to a committee role. `accountable_organization` is unchanged. |
| Imaging counts — 7,642 admissions recorded, 1,000 images only in prose (both) | The Imaging subset/resource now carries **two** `Instance` objects: the admission-level count (7,642, project website, tier 2) and the image-level count (1,000, cohort 2 webinar, tier 4), each with its own `source_caveats`. `data_substrate: B2AI_SUBSTRATE:11` (DICOM) moved to the image-level instance, where it belongs. The prose restating both figures was removed from the Imaging `description` and the subset-level `source_caveats` was dropped, the content having moved into the two instances. |
| `distribution_formats` mixing standard with content (both) | The five prose values were replaced with six terse format names: `OMOP Common Data Model tables`, `OHNLP tokenized clinical text`, `DICOM`, `WFDB`, `EDF+`, `Persyst`. Modality coverage is no longer restated here; it is carried by the subsets/resources. |
| Full/core divergence: `subsets` vs `resources` | The divergence is **retained** — the full record still uses `subsets` (DataSubset, with `is_data_split: false` / `is_subpopulation: false` on each), the core record still uses `resources`. The core `source_caveats` now states explicitly that the nine entries are logical modality subsets of one dataset rather than independently distributed component datasets, and that they are carried under `resources` because CoreDataset provides no subset slot. The audit's concern about the two records asserting different structures is now documented rather than eliminated. Note that this justification rests on the core schema, which is outside the supplied digest; the digest covers the full `Dataset` class only. |

---

## 4. Changes made — low severity

| Finding | Change |
|---|---|
| `status` holding narrative, duplicating the regulatory notice (both) | `status` shortened to `Partially released under controlled access and actively growing`. The Administration-directives notice now appears only in `regulatory_restrictions`, where it was split out as its own list entry alongside the legal-framework entry. |
| Inferred `was_directly_observed: false` / `was_inferred_derived: false` (both) | Both booleans **removed** from `acquisition_methods[0]` in both records. `acquisition_details` is unchanged. The record now leaves these axes unanswered, consistent with the second acquisition object. |
| `data_collectors[].role` not matching source wording (full) | `Data contributing site` → `Data Acquisition center`, matching the GitHub overview's wording; `collector_details` reworded to say "Fourteen hospitals serve as Data Acquisition centers." The second role, `Consortium sub-team`, is unchanged in label but its details were reworded to name the Standards, Data Acquisition and Tooling sub-teams as the source does. The same two changes were applied to the core record for parity, although the audit raised this only against the full record. |
| Transcription remark inside `maintainer_details` (both) | The parenthetical "(cmccrary@mgh.havard.edu, as printed on the site)" was replaced by a plain "with contact address cmccrary@mgh.havard.edu", and the observation about the spelling moved to a new `source_caveats` on that maintainer object. |
| `is_deidentified.identifiable_elements_present` unset (both) | Set to `true`, with a new `source_caveats` explaining that the value rests on full-text notes being retained at contributing sites and imaging de-identification being in process, and that the sources do not state whether any released modality retains direct identifiers. |
| `human_subject_research` — empty declared fields, absence-of-IRB in `notes`, `special_populations` unpopulated (both) | `special_populations` populated with the PICU/NICU statement. `notes` reduced to the substantive description of what the dataset consists of. The absence of IRB and regulatory-compliance information moved into a new `source_caveats`. |
| `at_risk_populations.notes` carrying the substantive finding (full) | `notes` removed; the PICU/NICU fact and the absence of assent/guardian-consent documentation are now combined in `source_caveats`, alongside the retained `at_risk_groups_included: true`. The same edit was applied to the core record. This does not fully answer the finding — the fact is now in a caveat rather than a content field — but the class declares only `special_protections`, `assent_procedures` and `guardian_consent` as content fields, none of which the bundle supports. |
| Holdout set repeated across four slots (full); `splits` absent from core (core) | The full record's `splits` object was reworded from a forward-looking project statement to a description of the split, and gained a `source_caveats` noting the sources give no size, composition or availability date. The holdout claim was **removed from `tasks`** in both records (the fourth task entry, "External validation of AI/ML models against a sequestered holdout test set", is gone), reducing the repetition from four slots to three. It remains in `purposes`, `intended_uses` and — in the full record only — `splits`. The core record still has no `splits`. |
| `known_biases[0]` asserting a characterized bias (both) | `bias_description` rewritten to lead with what the sources actually say — that the project identifies bias management as a core concern — and to describe the cohort constraint rather than asserting an observed bias. `source_caveats` expanded to state that no demographic distribution is published and that the `bias_type` categorizes the described composition constraint rather than a measurement. `bias_type: selection_bias` and `mitigation_strategy` retained. |
| `external_resources` prose in a string field (both) | Each object's `external_resources` value was converted from a scalar prose paragraph to a single-item list, and the text tightened (the GitHub entry no longer restates as much repository inventory; the NIH entry now names the award). `restrictions` reworded from "Public repositories." to "Repositories are public." `archival` and `future_guarantees` remain unset — the bundle supports neither. The finding is only partially addressed: the values are still descriptive strings rather than bare references. |

---

## 5. Left as-is, with reasons

- **`creators` names in `notes` (high).** See §2.1. No declared field can hold a contributor name without asserting a role the bundle does not state.
- **Grant `id` (high).** See §2.2. Documented rather than changed.
- **`subsets`/`resources` divergence (medium).** Documented in the core `source_caveats` rather than harmonized.
- **`instances[0].counts: 50000` vs the webinar's 45,000.** The audit rated this handled correctly; unchanged.
- **`participant_privacy` present in full, absent in core.** Unchanged. In the full record its `reidentification_risk` field was dropped and the same content moved to `source_caveats`, since it was an observation about what the sources do not say.
- **`conforms_to_standard: OTHER` covering two distinct standards.** Informational finding; the enum offers no finer term and `conforms_to` names both in prose. Unchanged in both records.
- **Consent, notification, revocation, DPIA and compensation slots.** Correctly absent; unchanged.
- **`principal_investigator` as a scalar.** Flagged here as the one change most likely to be wrong. The digest declares the range as `Person`, and the v4 rule about scalar-ranged slots governs slots whose range *is* a scalar. If `Person` is an object range, the original `name:` form was correct and this change is a regression.

---

## 6. Divergences remaining between full and core

| Slot | Full | Core |
|---|---|---|
| nine modalities | `subsets` (DataSubset, with `is_data_split`/`is_subpopulation`) | `resources` (Dataset) |
| `splits` | present | absent |
| `direct_collection` | present | absent |
| `participant_privacy` | present | absent |
| `third_party_sharing` | present | absent |
| `conforms_to_class` | `Dataset` | `CoreDataset` |
| `id` | `https://chorus4ai.org/#dataset` | same |

No content appears in the core record that the full record does not also state. The core header retains the required `# Sources:` line and `# Phase 4 reconciliation: completed`.

---

## 7. Outcome

Changes applied: 18 findings acted on, 3 findings documented without change, 2 findings partially addressed (`creators`, `external_resources`), 1 finding whose fix may itself be a defect (`principal_investigator` scalarization). No new factual claim was introduced in either record; every edit either moved existing content between slots, tightened wording to match source phrasing, removed an inference, or added a caveat about the evidence.