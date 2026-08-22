# CHORUS D4D Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`CHORUS_d4d.yaml`, class `Dataset`) and core (`CHORUS_d4d_core.yaml`, class `CoreDataset`)
**Referent:** the CHoRUS dataset itself — the multicenter critical care data collection produced by the CHoRUS data generation project — not the project, not the AIM-AHEAD training program, not the software organization. This choice is held consistently across both records.

---

## 1. What the audit found

The audit returned 42 findings: 6 high, 13 medium, 23 low. No fabricated dataset facts were identified; every count, modality, format, contact and award detail traced to one of the four bundle files. The defects clustered into five groups:

1. **Role inflation in `creators`** — five Bridge2AI CHoRUS Leadership Team members asserted as `principal_investigator` (high, both records).
2. **Identifier shape** — a resolver URL in a `uriorcurie` grant `id`, a `mailto:` URI as a `Person.id`, a website URL as `publisher` (high and medium, both records).
3. **Core-not-a-projection** — the core `notes` added a sentence absent from the full `notes`; five full-record slots were dropped from the core without their content being carried anywhere structured (medium).
4. **Over-precision and enum vagueness** — `1.6 Billion` rendered as `1600000000`; unqualified `OTHER` standing for three distinct schemas; `B2AI_TOPIC:4` used as a catch-all (medium and low).
5. **Entity collapsing and slot fit** — two maintainer contacts in one object, two external resources in one object, a GitHub organization occupying a `Maintainer`, narrative prose in `status`, a training-program start date presented as a distribution date (low).

---

## 2. Changes made

### 2.1 `creators` — role inflation (high, both records)

**Original (both records):** six `Creator` objects, each with `principal_investigator: {name: ...}`.

**Reconciled (both records):** only Eric S. Rosenthal retains `principal_investigator`, and that object gains a `notes` value recording that NIH RePORTER lists him as PI of award 1OT2OD032701-01 and that the Cohort 2 webinar names him on the leadership team slide. The five remaining objects drop `principal_investigator` entirely; each now carries the person's name inside `notes` ("Azra Bihorac, named as a member of the Bridge2AI CHoRUS Leadership Team", and likewise for Jiang, Strekalova, Rashidi and Kwong) with `affiliations` retained. Each keeps a `source_caveats` reworded to "Role recorded as leadership team membership only; NIH RePORTER lists Eric S. Rosenthal as the sole principal investigator of the award."

**Why:** the bundle designates exactly one principal investigator. `Creator` declares no slot for a non-PI person, so the name moves to `notes` rather than into a field that would restate the PI claim. The affiliation is attested and stays in its declared field.

**Residual cost, stated plainly:** the five names are now in prose rather than in a structured person field. This is a loss of structure accepted in exchange for not asserting a role the evidence contradicts.

### 2.2 `funders[0].grants` — resolver URL in a `uriorcurie` id (high, both records)

**Original (both):**
```
grants:
  - id: https://reporter.nih.gov/project-details/10472824
```

**Reconciled (both):** the `grants` list is removed. The award identifiers move into `grantor`, which now reads "...award OT2OD032701, project number 1OT2OD032701-01, NIH RePORTER application ID 10472824", and a `source_caveats` is added: "The bundle attests the award by its project and core project numbers; no registry identifier for the grant is given, so no identifier is asserted."

**Why:** the URL identified a RePORTER web page, not the award. The v5 identifier rule bars supplying a registry identifier the bundle does not state, and the bundle states only the project numbers, which are not CURIEs under any prefix the schema declares. Omitting the object is the correct answer where no valid identifier exists.

### 2.3 `data_governance.committee_contact.id` — `mailto:` as Person id (high, both records)

**Original (both):** `id: mailto:jared.houghtaling@tuftsmedicine.org` alongside `name: Jared Houghtaling`.

**Reconciled (both):** the `id` is removed; `name` remains. A `source_caveats` is added to `data_governance`: "The bundle names contacts for data access requests but gives no registry identifier for any individual, so no person identifier is asserted; it also names no formal access committee."

**Why:** an email URI is not a personal-identifier registry entry. The email address is still recorded, in `access_review_process`, where it belongs as a contact route.

### 2.4 `publisher` — website URL in a `uriorcurie` slot (medium, both records)

**Original (both):** `publisher: https://chorus4ai.org/`, duplicating `page`.

**Reconciled (both):** the slot is removed. `page: https://chorus4ai.org/` remains.

**Why:** no organization registry identifier is attested for the publishing body, and a website URL does not identify an organization.

### 2.5 `instances` — over-precision and catch-all topic (medium and low, both records)

**Original (both):** the OMOP-rows instance carried `counts: 1600000000`; `B2AI_TOPIC:4` appeared on the admission, procedure and nursing-flowsheet instances.

**Reconciled (both):** `counts` is removed from the OMOP-rows instance and replaced by a `notes` value stating "approximately 1.6 billion rows of EHR OMOP data; the source gives a rounded magnitude rather than an exact count". `data_topic: B2AI_TOPIC:4` is removed from the admission instance and from the procedure instance; it is retained on the nursing-flowsheet instance. The admission instance gains a `source_caveats` recording the tier-2 (50,000) versus tier-4 (over 45,000) disagreement and the preference applied.

**Why:** the schema instructs omitting an approximated term rather than supplying one. The 50,000 count is retained because it is exact in its source and the ranking settles the conflict; the caveat now sits on the value it qualifies rather than only at record level.

**Note on partial action:** `B2AI_TOPIC:4` was removed from two of the three flagged instances but kept on nursing flowsheets, where "Clinical Observations" is a defensible fit rather than an approximation. The audit's framing of this as a uniform catch-all is only partly accepted.

### 2.6 `conforms_to_standard` — unqualified `OTHER` (medium, both records)

**Original (both):** the enum list emitted `OTHER` with no indication of what it stood for.

**Reconciled (both):** the enum list is unchanged — `OTHER` remains, because the schema permits no other token for these standards. A sentence is appended to `notes`: "The OTHER value in conforms_to_standard stands for three standards the enumeration does not list separately: the OHNLP open-source schema for tokenized clinical notes, and the EDF+ and Persyst schemas for EEG waveforms."

**Why:** the enum is closed; the fix is disambiguation in prose, not a value the schema does not permit. The three standards were already named in `conforms_to`.

### 2.7 `status` — narrative prose (low, both records)

**Original (both):** two sentences on release state, imaging de-identification and EEG extraction.

**Reconciled (both):** shortened to "Partially released under controlled access; data acquisition ongoing." The dropped detail is already present in `updates.update_details` and `missing_data_documentation`.

### 2.8 `maintainers` — collapsed contacts and a non-maintainer object (low, both records)

**Original (both):** three objects — McCrary; a single object holding both `dbold@emory.edu` and `jared.houghtaling@tuftsmedicine.org`; and a description of the GitHub organization's 28 repositories.

**Reconciled (both):** four... no — three objects, restructured. The two-contact object is split into two: one for the Emory contact and one for Jared Houghtaling (Tufts Medicine, with the additional attested detail that he leads EHR-data training sessions). The GitHub-organization object is removed from `maintainers`; its content, including the package status page listing versions and maintainers, is folded into the existing `external_resources` entry for the chorus-ai organization. Total objects remain three because one was split and one removed.

The McCrary object gains a `source_caveats` carrying the domain-typo observation, which previously appeared only in the record-level `source_caveats`.

**Divergence between the two reconciled records:** the full record names the Emory contact as "Donna Bold" in `maintainer_details`; the core record writes "Emory University contact handling CHoRUS data access requests at dbold@emory.edu." The core wording is correct — the bundle gives only the address — and both objects carry a `source_caveats` stating that the personal name behind the address is not stated in the sources. The full record's `maintainer_details` supplies a name the bundle does not attest, contradicted by its own adjacent caveat. **This is an unresolved defect in the reconciled full record**, not a deliberate divergence, and it should be corrected to match the core wording.

### 2.9 `external_resources` — collapsed entities (low, both records)

**Original (both):** four objects, the last holding both the Bridge2AI CHoRUS program page and the AIM-AHEAD call for applications.

**Reconciled (both):** five objects; the fourth is now the Bridge2AI program page alone, and a fifth covers the AIM-AHEAD call for applications with the InfoReady portal and AIM-AHEAD Connect detail.

### 2.10 `distribution_dates` — conflated program start (low, both records)

**Original (both):** release date text ended "...access for AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 trainees began with the program start on 2025-11-17", and used an en-dash in "August–September 2025".

**Reconciled (both):** the trainee program start is removed; the text reads "A current released dataset was available as of August to September 2025, covering 14 contributing hospitals." A `source_caveats` notes that the sources describe dataset state at those dates rather than a formal release date. The en-dash is replaced with "to". The Cohort 2 program dates remain in `existing_uses`, where they describe a use rather than a release.

### 2.11 `at_risk_populations` and `human_subject_research` — inferred booleans (low, both records)

**Reconciled (both):** both booleans are retained at `true`. `at_risk_populations.source_caveats` is expanded to state that inclusion is inferred from the PICU/NICU statement, that the sources do not characterize any group as at-risk, and that the listed protections are general measures rather than population-specific ones. `human_subject_research` gains a new `source_caveats` stating that human-subjects involvement follows from the patient-level clinical nature of the data, that the sources do not use the term, and that no IRB approval is stated.

**Why retained:** both inferences are entailments of attested facts rather than speculation. The correction is disclosure, not withdrawal.

### 2.12 `notes` — misspelling provenance (low, full record)

**Reconciled (both):** the banner quotation now carries a parenthetical, "(the misspelling of 'repository' is as published)", so a reader can distinguish source fidelity from a transcription error introduced here.

### 2.13 Core-projection defects (medium, core record)

- **Added sentence in `notes`:** the core's holdout sentence is removed; the core `notes` now matches the full `notes` exactly.
- **`subsets` and `splits`:** both remain absent from the core. The holdout content is now carried in `sampling_strategies[0].strategies`, which gains the sentence "A sequestered holdout portion of the dataset is set aside for external validation of AI-developed models rather than for model development." This is a structured slot present in both records, so the information is no longer demoted to free prose.
- **`direct_collection`:** remains absent from the core; the prose in `acquisition_methods[0]` is unchanged. The `is_direct: false` boolean remains recoverable only from the full record.
- **`third_party_sharing`:** remains absent from the core; its content is now folded into `license_and_use_terms.license_terms`, which gains "The dataset is made available beyond the creating consortium on these terms, with external researchers and training-program participants working with the data inside the Bridge2AI AI/ML for Clinical Care Collaborative Cloud."
- **`participant_privacy`:** remains absent from the core; the `data_linkage` content is now carried in `is_deidentified.deidentification_details`, which gains "and linked there alongside OMOP, imaging and waveform data for a given admission."

The core `source_caveats` gains a closing sentence recording that no registry identifier is attested for any person, organization or grant.

---

## 3. Left as-is

| Finding | Disposition |
|---|---|
| `id` = `https://chorus4ai.org/#dataset` (medium) | Unchanged in both records. The fragment names a part of this record's subject and has no external referent, so the minting rule governs: it is a label on an attested URL. No better-grounded identifier exists in the bundle. |
| `known_biases` limited to `selection_bias` (low) | Unchanged. The bundle's equity framing is programmatic intent, not a stated representation bias; adding `representation_bias` would assert a finding the sources do not make. |
| `license` omitted (low) | Unchanged in both records. The MIT statement covers software, and this is now stated in the record-level `source_caveats` ("...so no dataset-level license slot is asserted") as well as in `ip_restrictions`. |
| `created_by: CHoRUS Consortium` (low) | Unchanged. The website heads a section "CHoRUS Consortium" and describes the project's work product; this is the best-supported single value, and the awardee organization appears in `data_governance.accountable_organization` and in `funders[0].notes`. |
| `description` — "9 data modalities" (low, borderline in the audit) | Unchanged in substance; the sentence already attributes the figure to the anticipated final dataset, and the reconciled wording strengthens this to "is described as covering". |
| Instances lacking `counts` / `data_substrate` (low) | Unchanged where the bundle supplies neither. Omission is the correct answer. |

---

## 4. Outstanding

One defect survives reconciliation and is recorded here rather than concealed: **`maintainers[1].maintainer_details` in the full record names "Donna Bold", a name the bundle does not attest.** The adjacent `source_caveats` in the same object contradicts it. The core record's parallel object is correct. This should be corrected in the full record to match.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 51 | 47 |
| Validation | passed (`Dataset`) | passed (`CoreDataset`) |

High-severity findings: 6 addressed, 0 outstanding. Medium: 13 addressed in full or by carrying content into a structured slot present in both records. Low: 17 addressed, 6 left as-is with reasons above. One new defect identified during comparison and left outstanding (§4).

Reconciliation outcome: **completed with one outstanding defect.**