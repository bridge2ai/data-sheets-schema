# VOICE D4D Reconciliation Report

**Version label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep3
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Arm:** BASELINE (input documents only)
**Referent:** Bridge2AI-Voice adult flagship dataset, PhysioNet v3.1.0 (`doi:10.13026/8xbn-nq66`)

---

## 1. What the audit found

The Phase 3 audit returned 36 findings: 2 high, 16 medium, 18 low. The low-severity items included five positive checks (correct `conforms_to_class` split, bare-DOI form, `uri`-vs-`uriorcurie` handling, omitted collection dates, absent registry identifiers for external organizations) that required no action.

The findings clustered into five groups:

1. **An undeclared slot in the core record.** The core record carried a top-level `distributions` block whose member key `path` matches no object range in the supplied schema digest, and two `source_caveats` asserting that `format` and `media_type` are enumerated ranges the digest does not show as enumerated.
2. **Core content with no full-record counterpart.** That same `distributions` block restated `file_collections` material under different keys and added commentary absent from the full record, breaking core-from-full projection.
3. **Roughly a dozen slots dropped from core** that the full record populated from the bundle, several losing structured booleans or per-cohort detail rather than merely prose.
4. **A boolean contradicting the record's own neighbouring content**: `at_risk_populations.at_risk_groups_included: false` alongside `human_subject_research.special_populations` listing dementia, cognitive impairment and active psychiatric conditions.
5. **Three slots populated with adjacent activity** where the bundle answers directly in the negative (`data_protection_impacts`, `cleaning_strategies`, `confidential_elements`), each already caveated but each stating more than the source does.

Plus scattered structural items: a twelve-organization Creator collapse, a three-body `reviewing_organization` scalar, subset identifiers anchored on the landing page rather than the record `id`, an instance substrate encoding packaging, and several description-level inferences.

---

## 2. Changes made — full record

### 2.1 `creators` — twelve institutions split into twelve Creator objects

*Finding: low, `creators[2]`.* The original carried a single Creator with twelve `affiliations` and no `principal_investigator`. `creators` is multivalued and the institutions are individually nameable, so collapsing them populated the slot without representing what it declares.

The reconciled record has fifteen Creator entries: the two co-principal investigators as before, then one entry per collaborating institution (University of South Florida, Weill Cornell Medicine, Oregon Health & Science University, Massachusetts Institute of Technology, University of Toronto, Mount Sinai Hospital, Hospital for Sick Children, Simon Fraser University, The Hastings Center, Washington University in St. Louis, University of Florida, Vanderbilt University Medical Center). The `source_caveats` explaining the Creator-class name-field limitation now sits on the last entry and absorbs the "over 50 further investigators / 120 authors" note that was previously in `notes`.

### 2.2 `creators[*].principal_investigator` — object replaced by scalar

The original wrote `principal_investigator:` as a nested object with a `name:` key. The reconciled record writes the name directly (`principal_investigator: Yael Bensoussan`). Same change applied to `ethical_reviews[0].contact_person`.

### 2.3 `at_risk_populations` — boolean flipped to `true`

*Finding: medium, both records.* The bundle places participants with mild cognitive impairment, Alzheimer's disease, other dementias, bipolar disorder, schizophrenia and depression in the adult cohort — the same populations the record already listed under `human_subject_research.special_populations`. The IRB protocol additionally identifies mood-cohort questions as capable of triggering discomfort and negative emotions.

`at_risk_groups_included` is now `true`. `special_protections` was rewritten from one entry to three: the capacity-to-consent population with the thirty-minute teach-back safeguard; the mood-cohort discomfort risk; and the statement that minors are absent from the adult release. The `source_caveats` now records that the bundle never uses the phrase "at-risk population," so the boolean is an assessment of the described cohorts rather than a value any source states.

### 2.4 `ethical_reviews` — one entry split into three

*Finding: low.* The original packed "Research Ethics Boards of Mount Sinai Hospital, the Hospital for Sick Children and the University of Toronto" into one `reviewing_organization` scalar. The reconciled record has separate entries for Mount Sinai Hospital Research Ethics Board, Hospital for Sick Children Research Ethics Board and University of Toronto Research Ethics Board, with the genomic-protocol note attached to the two boards the bundle associates with it. Total entries: three to five.

### 2.5 `instances[1].data_substrate` — B2AI_SUBSTRATE:30 → :49

*Finding: medium.* Parquet (`:30`) describes the distribution container, not the instance. The instance is a waveform-derived feature tensor, so Waveform Data (`:49`) is now used. The `notes` field states explicitly that the packaging format is recorded under `distribution_formats` rather than as the substrate, and the `instance_type` wording changed from "released as derived features" to "released as derived feature tensors."

### 2.6 `subsets` and `file_collections` — identifiers re-anchored on the record `id`

*Finding: low.* Fragments previously hung off `https://physionet.org/content/b2ai-voice/3.1.0/`; they now hang off `doi:10.13026/8xbn-nq66`, the identifier the record uses as `id`. Eight identifiers changed (five subsets, three file collections). The fragments still name parts of this dataset with no external referent, so minting remains correct under the v5 rule.

### 2.7 `errata[0].erratum_url` — removed

*Finding: low.* The URL pointed at the version landing page, not at an erratum document, and the bundle states no erratum exists. The slot is gone; the `source_caveats` now explains why and points to the `page` slot for the release notes.

### 2.8 `collection_consents` — second entry removed

*Finding: medium.* The Consent Type restatement duplicated content already carried in `license_and_use_terms.data_use_permission` and in `informed_consent[0].consent_scope`. It is now stated once, inside `consent_scope`. `collection_consents` retains one entry.

### 2.9 Three "adjacent activity" caveats strengthened

*Findings: low ×3.* The content in `data_protection_impacts`, `cleaning_strategies` and `confidential_elements` was left in place — it is drawn from the bundle and describes real activity — but each caveat was rewritten to state plainly that the source answers negatively and that the slot describes something other than what its name asserts:

- `data_protection_impacts.source_caveats` now says "No formal data protection impact assessment is reported; the ethics review and access-governance work recorded here is adjacent activity, not a DPIA."
- `cleaning_strategies` now carries a caveat on **each** entry (previously one, on the second): the audit protocol is "quality assessment rather than cleaning," and the transcript review is "a privacy measure applied at release rather than a data cleaning step."
- `confidential_elements.source_caveats` opens with "This boolean records the project documentation's own answer and should be read against evidence pointing the other way," and closes by naming the tension.

### 2.10 Description and top-level `source_caveats`

*Findings: low ×2.* The description previously read "five sites in the United States and Canada," an inference neither source states. It now reads "five sites in North America" (the tier-1 wording) with "Data was collected in the United States and Canada" as a separate sentence. The eligibility bounds are now attributed inline: "the study metadata published against version 2.0.0 gives adult eligibility as 18 to 120 years of age."

The top-level `source_caveats` gained three items: the version-DOI-versus-concept-DOI choice for `id`; the note that the bundle does not state how five sites distribute across two countries; and a pointer to the three slots carrying negatively-answered material.

### 2.11 Scalar-range corrections

Several slots whose declared range is a scalar carried lists in the original. Converted to prose strings: `is_deidentified.identifiers_removed`, `participant_privacy[0].privacy_techniques`, `sampling_strategies[0].strategies`, `machine_annotation_tools[0].tool_descriptions`.

### 2.12 `notes` retained

*Finding: low.* The AI-readiness rubric stays in `notes`. No better-fitting slot exists in the 98-slot inventory, and the audit itself called the placement defensible.

### 2.13 `maintainers[3]` — reframed

*Finding: low.* The Health Data Nexus entry now reads in the past tense ("hosted version 1.0 … maintained the technical infrastructure for that earlier feature-only release") and carries a new `source_caveats` stating that this is a prior host, that the tier-2 documentation presents it as current, and that the tier-1 PhysioNet claim is preferred. This aligns the entry with the disagreement resolution already recorded in the top-level caveat and in `data_governance.source_caveats`.

### 2.14 `distribution_formats` — media types added

`media_type: text/tab-separated-values` and `media_type: application/json` added to the two entries where a registered media type exists. The Parquet and WAV entries carry none.

### 2.15 `external_resources[0].external_resources` — prose split into a list

The single prose blob naming seven resources is now seven list items.

---

## 3. Changes made — core record

### 3.1 `distributions` — undeclared slot

*Findings: high ×2.* The block is **retained** in the reconciled core record, contrary to what the audit recommended.

The audit's reasoning was that `distributions` does not appear in the supplied schema digest. That digest is the **`Dataset`** slot inventory; the core record validates against `CoreDataset`, whose inventory was not supplied. The digest therefore cannot establish that `distributions` is undeclared in `CoreDataset` — its silence is uninformative about a class it does not enumerate. Removing a slot on that basis would be acting on an inference the supplied material does not license.

What was changed within the block:

- The `features/` entry previously declared `format: TSV` and `media_type: text/tab-separated-values` for a collection that is predominantly Parquet. Both were removed; the caveat now says the collection mixes formats, the slots take one value each, and the formats are itemized under `distribution_formats`.
- The two `source_caveats` asserting that `format` and `media_type` are "enumerated" ranges were rewritten. The `metadata/` caveat now says only that "the permitted values for those slots include no Apache Parquet term," which is a claim about permitted values rather than about a range declaration the digest does not show.
- Each entry now opens its `notes` with the collection name ("Derived audio features," "Phenotype tables," "Recording metadata"), so the block carries the same naming the full record's `file_collections` carries.

The projection concern stands in reduced form: the core record still expresses this material through a slot the full record does not use. The content is now identical to the full record's `file_collections` content, and the two added caveats no longer assert anything the digest contradicts.

### 3.2 Slots restored to core

*Findings: medium ×11.* Content the full record carried and the core record dropped has been folded back. Because the `CoreDataset` inventory was not supplied, restoration was done into slots the core record already demonstrates it accepts, rather than by adding slots whose availability is unverified:

| Dropped content | Restored into |
|---|---|
| `collection_consents` (dissemination-tier consent detail) | `informed_consent[0].consent_scope` |
| `consent_revocations` (post-collection irrevocability, satisfaction survey) | `informed_consent[0].withdrawal_mechanism` |
| `collection_notifications` (IRB consent process, teach-back) | `informed_consent[0].notes` |
| `direct_collection` (`is_direct: true` + prose) | `acquisition_methods[0].acquisition_details` |
| `subsets` (five cohorts with criteria and validation methods) | `subpopulations` — five new entries, total two to seven |

The satisfaction-survey detail, previously lost entirely, is now present. The five cohort descriptions with their gold-standard validation methods, previously reduced to one summary line, are now itemized.

Not restored: `participant_privacy`, `participant_compensation`, `relationships`, `third_party_sharing`, `variables`, `file_collections`, `citation`. Each would require either asserting a slot exists in `CoreDataset` without the inventory to confirm it, or forcing content into a slot it does not answer. The compensation amounts and the privacy-technique list remain absent from core; this is a real loss and is recorded here rather than papered over.

### 3.3 Changes mirrored from the full record

All of §2.1–2.15 that applies to slots present in core was applied identically: the fifteen-way `creators` split, the scalar `principal_investigator` and `contact_person`, the `at_risk_populations` flip to `true` with three `special_protections`, the five-way `ethical_reviews` split, `data_substrate` :30 → :49, the `errata` URL removal, the three strengthened caveats, the description rewording, the scalar-range conversions, the `maintainers[3]` reframing, and the two added media types.

### 3.4 Top-level `source_caveats` — restored detail

*Finding: low.* The core caveat previously truncated the award-identifier discussion. It now quotes both corrupted forms verbatim, matching the full record.

---

## 4. Left as-is

| Finding | Severity | Why unchanged |
|---|---|---|
| `id` is the version DOI, not the concept DOI | low | Both are in the bundle; the version DOI pins the record to the release it describes. Now disclosed in `source_caveats`. |
| `funders[0].grants[0].id` is a URL | low | The digest declares no NIH RePORTER prefix, so a URL is the correct `uriorcurie` fallback. The audit recorded this as no defect. |
| Organization objects carry only `name` | low | Correct under the evidence boundary — the bundle supplies no ROR identifiers, and supplying them from prior knowledge is prohibited. |
| `collection_timeframes` has no dates | low | Positive check. Bundle supplies none; HIPAA Safe Harbor removed sub-year resolution. |
| `conforms_to_class`, bare `doi`, `uri`-ranged slots | low | Positive checks, all already correct. |
| `notes` holds the AI-readiness rubric | low | No better-fitting slot; audit called it defensible. |
| `distributions` present in core | high | See §3.1 — the supplied digest enumerates `Dataset`, not `CoreDataset`, and cannot settle the question. |
| Seven core slots not restored | medium | See §3.2 — restoring them requires an inventory that was not supplied. |

---

## 5. Referent

One referent throughout both records: the Bridge2AI-Voice **adult** flagship dataset at PhysioNet v3.1.0. The pediatric dataset (`doi:10.13026/h995-bt35`) is carried under `related_datasets` with `relationship_type: is_supplemented_by`, and the `at_risk_populations` caveat states explicitly that the pediatric assent provisions in the IRB protocol are not the referent of this record.

---

## 6. Provenance handling

Manifest ranking was applied and documented in all four contested cases: recording counts (tier 1 per-feature counts over the tier-2 aggregate of ~61,937), hosting (tier-1 PhysioNet over tier-2 Health Data Nexus, now also reflected in `maintainers[3]`), name spellings (tier-1 "Siu"/"Rudzicz"), and award identifiers (all variants recorded, none silently selected). The HIPAA disagreement between the DUA and the project documentation is left unresolved and labelled as such, both sources being tier 2.

No registry identifiers were supplied for any external organization, person or publication beyond what the bundle states. American spelling holds in composed prose; source spellings are preserved in the citation, in dataset titles, and in the "bioaccoustic" grant title as the NIH record writes it.