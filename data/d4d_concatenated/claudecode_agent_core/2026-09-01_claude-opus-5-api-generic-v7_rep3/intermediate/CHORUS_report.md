# CHoRUS D4D Reconciliation Report

**Project:** CHORUS
**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep3`
**Arm:** BASELINE (input documents only)
**Records:** full (`CHORUS_d4d.yaml`), core (`CHORUS_d4d_core.yaml`)
**Referent held across both records:** the CHoRUS dataset — the multicenter, multimodal, controlled-access critical care data collection described at `https://chorus4ai.org/#chorus-dataset` — not the CHoRUS project, network, software organization, or the AIM-AHEAD training program. Project-level statements from NIH RePORTER and the GitHub overview were used only where they describe the data.

---

## 1. Audit summary

The Phase 3 audit returned eleven findings against the full record: two high, four medium, five low. It found no enum value outside the schema digest and no range violation. Its criticism was concentrated in three areas — minted identity, unsupported inference, and slot placement — rather than in factual accuracy. It affirmed the record's handling of the release-size disagreement (project documentation, tier 2, 50,000 admissions; cohort 2 webinar, tier 4, over 45K; higher tier preferred, both recorded) and its omission of `doi`, `citation`, `version`, `license`, `errata`, `retention_limit`, and `known_biases`.

---

## 2. Changes made

### 2.1 `creators` — leadership team removed from `principal_investigator` (high)

**Original:** seven Creator objects. Six carried a `principal_investigator` Person: Rosenthal, Bihorac, Jiang, Strekalova, Rashidi, Kwong. Five of those carried an embedded `source_caveats` conceding that the webinar names them as leadership team members, not PIs.

**Reconciled:** two Creator objects.

1. `principal_investigator: {name: Eric S. Rosenthal}`, `affiliations: [{name: Massachusetts General Hospital}]` — the sole individual NIH RePORTER identifies as PI of OT2OD032701.
2. A consortium Creator with `affiliations: [{name: CHoRUS Consortium}]`, whose `notes` names Bihorac (University of Florida), Jiang (UTHealth Houston), Strekalova (University of Florida), Rashidi (University of Florida), and Kwong (Tufts University) as the remaining Bridge2AI CHoRUS leadership team, and whose `source_caveats` states why they are in prose rather than in the `principal_investigator` field.

**Why:** a caveat that a slot is being misused does not undo the misuse. `principal_investigator` is a typed assertion; the bundle contradicts it for five of the six. The names, roles, and affiliations survive in full — nothing was dropped, only relocated out of a field that asserted something the evidence does not support. Applied identically in both records.

### 2.2 Minted person and organization identifiers removed (high)

**Removed from both records:**

- `creators[*].principal_investigator.id` — `#person-eric-s-rosenthal`, `#person-azra-bihorac`, `#person-xiaoqian-jiang`, `#person-yulia-strekalova`, `#person-parisa-rashidi`, `#person-manlik-kwong`
- `creators[*].affiliations[*].id` — `#organization-massachusetts-general-hospital`, `#organization-university-of-florida`, `#organization-uthealth-houston`, `#organization-tufts-university`, `#organization-chorus-consortium`
- `data_governance.accountable_organization.id` — `#organization-massachusetts-general-hospital`

Persons and organizations now carry `name` only.

**Why:** each names an entity with a referent outside this record, so the identifier is a fact about the world and must come from the evidence or be omitted. The bundle supplies no ORCID, ROR, or equivalent for anyone. Additionally, a fragment on `https://chorus4ai.org/#…` asserts that the entity is a part of that resource, which is false of a hospital and of a person.

### 2.3 Minted Creator and grant identifiers removed (medium)

**Removed:** `creators[*].id` (`#creator-rosenthal` … `#creator-consortium`) and `funders[0].grants[0].id` (`https://reporter.nih.gov/project-details/10472824`).

**Why:** the first — no value anywhere in either record points at a Creator, so these were labels for nothing. The second combines two defects the audit raised separately: it is an identifier nothing references, and (per the low-severity finding) the RePORTER URL identifies a *landing page*, not the grant. The grant retains `name: OT2OD032701`, and the RePORTER URL is preserved as prose inside `funders[0].notes` and in `external_resources`, so no source location is lost.

### 2.4 Named contacts moved into declared Person-ranged fields (medium)

**Added to `data_governance`:** `committee_contact: {name: Jared Houghtaling}`.
**Added to `license_and_use_terms`:** `contact_person: {name: Ciera McCrary}`.
**Extended `data_governance.source_caveats`** to state that Houghtaling is recorded because he is one of two named access-request contacts in the GitHub overview, not because any source calls him a committee contact, and that the second contact appears only as the bare address `dbold@emory.edu` with no name.
**Added `license_and_use_terms.source_caveats`** noting that McCrary is the published program-manager contact and that no source names a licensing-specific contact.

Both are `name`-only Person objects, consistent with §2.2.

**Why:** the bundle names these people; the declared Person-ranged fields were empty while the names sat in prose. The caveats record that the mapping from "named access contact" to "committee contact" is the record's placement decision rather than a source claim.

### 2.5 `at_risk_populations` removed (medium)

**Original:** `at_risk_groups_included: true` with a `source_caveats` admitting the inference and admitting that no assent, guardian consent, or special protection is described.

**Reconciled:** slot absent. Justification moved to the record-level `source_caveats`.

**Why:** the object was inferred from ICU/PICU/NICU unit types and carried none of the protection information the class exists to hold. The PICU/NICU composition remains stated in `description`, in `instances[0].instance_type`, and in `subpopulations[0].identification`, so no content was lost.

### 2.6 `human_subject_research` — inference standard made consistent (medium)

**Reconciled:** slot remains absent, and the record-level `source_caveats` now states explicitly that no source characterizes the dataset as human subjects research and that this is why both `human_subject_research` and `at_risk_populations` are unpopulated.

**Why:** the audit's point was internal inconsistency — inferring one ethics slot while omitting a neighbour supported by the same evidence. Removing `at_risk_populations` (§2.5) resolves it toward the stricter reading; the caveat now makes the single standard visible instead of leaving two silent omissions.

### 2.7 `instances[1].data_substrate` removed (low)

**Removed:** `B2AI_SUBSTRATE:37` (Relational Database) from the OMOP EHR-rows instance.

**Why:** the bundle states a count of rows and a data model, never a storage substrate. The digest directs omission over approximation. The three substrate terms that *are* attested — `:43` Text for tokenized notes, `:11` DICOM for imaging, `:49` Waveform Data for telemetry and EEG — are unchanged, as each names a format the sources state.

### 2.8 `subpopulations[2]` removed (low)

**Removed:** the entry casting SDoH and geographic contextual factors as a subpopulation identification.

**Why:** the bundle presents these as data elements, not as a reported basis for subgroup definition; "allow subgroups to be distinguished" was the record's own inference. The content is unchanged in `sensitive_elements[1]` and `preprocessing_strategies[4]` (DeGauss geocoding of OMOP Location entities). Two subpopulation entries remain — ICU/PICU/NICU setting, and contributing hospital.

### 2.9 `acquisition_methods[0].was_directly_observed` removed (low)

**Removed:** the boolean. The `acquisition_details` prose describing retrospective extraction from EHR, PACS, telemetry, and EEG holdings is unchanged.

**Why:** the sources describe "Retrospective data collection" from pre-existing records; nothing characterizes acquisition as direct observation for this dataset. The neighbouring `was_inferred_derived: true` on the second entry is retained — tokenization, OMOP mapping, and re-identification-limiting transforms are explicitly derivations. `direct_collection[0].is_direct: false` also remains, and no longer sits in tension with a `was_directly_observed: true`.

### 2.10 License/governance duplication reduced (low)

**`license_and_use_terms.license_terms`** now states the terms: controlled access for all data types, a signed licensing agreement required, a `.edu` email address required, administrator assistance available.
**`data_governance.access_review_process`** now states the process: request from the named contacts; for the training program, complete the registration form giving name, email, and institution; email sent once access is granted and compute provisioned.

**Why:** the registration-and-licensing sequence was stated near-verbatim in both slots. The split follows each slot's description — terms in the terms field, procedure in the review-process field. No fact was dropped.

### 2.11 `data_governance.stewardship_roles` split into three entries

**Original:** one long string covering site data managers, clinical collaborators, and the program manager.
**Reconciled:** three list entries, one per role.

**Why:** the slot is multivalued and the v2 rule directs one object per distinct entity. Not an audit finding; corrected while the surrounding object was open.

### 2.12 Record-level `source_caveats` extended

Added: the human-subjects/at-risk omission rationale (§2.5–2.6) and a statement that no personal or organizational registry identifiers appear anywhere in the bundle (§2.2). The existing referent-scope note and the release-size disagreement passage are unchanged.

---

## 3. Left as-is

| Item | Reason |
|---|---|
| Release-size disagreement handling | Affirmed by the audit. Tier-2 project documentation (50,000 admissions) preferred over tier-4 webinar (over 45K); both figures recorded in `instances[0].source_caveats` and in record-level `source_caveats`. |
| Omitted `doi`, `citation`, `version`, `license`, `issued`, `retention_limit`, `errata`, `known_biases`, `download_url` | The bundle supplies none of these for the dataset. Affirmed by the audit. |
| `license` left empty while `license_and_use_terms.notes` records the MIT/Apache-2.0 repository licensing | The GitHub licenses govern CHoRUS software, not the dataset. Placing MIT in the dataset's `license` slot would misattribute it. |
| `conforms_to_standard: [OMOP_CDM, DICOM, WFDB, OTHER]` | Each term is attested; `OTHER` carries EDF+, Persyst, and the OHNLP schema, which the enum does not name. Not raised by the audit. |
| `data_governance.accountable_organization: Massachusetts General Hospital` (name retained, id removed) | Retained with its existing caveat that MGH is recorded as awardee institution and program-manager host, no formal accountable body being named. Only the minted `id` was removed. |
| `notes` recording the website's "repoitory" banner, spelling as published | A verbatim quotation; source spelling preserved per the naming rule. |
| `external_resources` including the RePORTER URL and `www.bridge2ai.org/chorus` | URLs inside prose are text, exempt from the CURIE rule. |
| `extension_mechanism.contribution_url: https://github.com/chorus-ai` | Declared range is `uri`; a URL is correct there. |
| `splits`, `participant_privacy`, `third_party_sharing`, `ethical_reviews` | Not raised by the audit; each is attested and correctly placed. `ethical_reviews` retains its caveat that no IRB or protocol number is named. |

No finding was rejected. Findings 2.6 and 2.10 were addressed by clarification and reorganization rather than deletion, as described above.

---

## 4. Full-to-core projection

The core record is a projection of the reconciled full record. Every change in §2 that touches a slot the core schema declares was applied identically to both files: the `creators` restructuring, all identifier removals, the two Person contacts and their caveats, the removal of `at_risk_populations`, the removal of `instances[1].data_substrate`, the removal of `subpopulations[2]`, the removal of `was_directly_observed`, the license/governance split, the three-entry `stewardship_roles`, and the extended record-level `source_caveats`.

Slots present in the full record and absent from the core record — `splits`, `direct_collection`, `participant_privacy`, `third_party_sharing`, `funders`… (`funders`, `instances`, `subpopulations` and the rest are in fact carried in core) — differ only where the core schema does not declare the slot. `conforms_to_class` reads `CoreDataset` and `conforms_to_schema` points at the core schema file, as required for the core record. No fact appears in the core record that is not in the full record.

---

## 5. Outcome

Eleven findings, eleven addressed: eight by removal of a value or object, one by relocating content into declared Person-ranged fields, one by redistributing duplicated prose across two slots, one by making an omission explicit in the caveat. Two records, one referent, one set of facts. Both validated against their schemas.