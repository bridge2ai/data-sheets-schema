# Reconciliation Report — AI_READI

Version label: `2026-08-20b_claude-opus-5-api-generic-v5_rep2`
Records reconciled: full (`Dataset`) and core (`CoreDataset`)
Phase 3 audit findings: 47 items (2 high on core shape, 2 high on creator identity, and a long tail of medium/low provenance, structure and drift issues)

---

## 1. What the audit found

The audit grouped its findings into three clusters:

1. **Shape defects in the core record.** The core had collapsed three distinct declared ranges — `file_collections` (range `FileCollection`), `subsets` (range `DataSubset`) and the split partitions — into a single `resources` slot (range `Dataset`), and had attached an invented `distributions` key to every entry. Several `categories` values were semicolon-delimited strings where the slot is multivalued.
2. **Unsupported identity and contact assignments.** A website URL was used as an organization identifier and simultaneously as that organization's own affiliation; Aaron Lee was assigned as license contact, governance committee contact and data access committee contact with no source naming him in any of those roles; six CRediT roles and a composed committee name were inferred rather than evidenced; one NIH award appeared as two Grant objects.
3. **Phase-4 reconciliation drift.** The core stated content the full record did not (`labeling_strategies`, `use_repository`, `extension_mechanism`, `versions_available`), while omitting declared slots the full record populated and restating their content as prose in `notes`.

A tail of smaller items covered concatenated URLs, a synthetic date range, non-resolvable DOI-fragment identifiers, an interpretive confidentiality mapping, an omitted `data_substrate`, a prose value in `missing_value_code`, and British spellings in agent-composed prose.

---

## 2. Changes made — full record

### 2.1 Creator identity and roles (high / medium)

`creators[0].affiliations` no longer contains an entry whose `id` is `https://aireadi.org` naming the AI-READI Consortium. The self-affiliation is gone; the list now begins at `ROR:00cvxb145` (University of Washington). The Creator `id` remains `https://aireadi.org`, and the `source_caveats` was extended to state explicitly that the input sources supply no registry identifier for the consortium, so the project website URL is used as its identifier.

`credit_roles` was removed entirely. The six CRediT values (`conceptualization`, `methodology`, `investigation`, `data_curation`, `project_administration`, `funding_acquisition`) are absent from the reconciled record, and the caveat now states: "No source assigns CRediT contributor roles to the creator, so `credit_roles` is left unpopulated."

The caveat also gained a note that the affiliation list draws on the FAIRhub location and collaborator lists, excludes NIH (recorded under funders), and deliberately excludes the additional institutions that appear only in the Nature Metabolism per-author affiliation list.

### 2.2 Duplicate grant (medium)

`funders[0].grants` now holds one Grant object rather than two. The second entry, keyed on the RePORTER application 10471118 URL, was removed; its content — the 5,026,499 USD award amount, project period, PI and awardee organization — moved into `funders[0].notes`, and `source_caveats` now records that the two sources cite different RePORTER records for the same core award and that the higher-ranked FAIRhub award URI was used.

### 2.3 Unsupported contacts (medium)

Three contact assignments were removed:

- `license_and_use_terms.contact_person` — removed. The `notes` now states that no source names an individual as the licensing contact, names Washington University in St. Louis as licensor, and gives contact@aireadi.org as the study central contact.
- `regulatory_restrictions.governance_committee_contact` — removed. The `notes` now states that the sources name no individual as a governance committee contact.
- `data_governance.committee_contact` — removed, resolving the internal contradiction with the sibling caveat.

### 2.4 Committee name (medium)

`data_governance.committee_name` changed from `AI-READI Data Access Committee` to `Data Access Committee`, which is the wording the BMJ Open protocol uses. The caveat now records that this is the only name the sources give the body and that the RO-Crate instead names the AI-READI Consortium.

### 2.5 Confidentiality level (medium)

`regulatory_restrictions.confidentiality_level: restricted` was removed. The slot is now absent, and the `notes` explains why: the only source classification is HL7:2N (normal), which does not map onto the enumerated terms without interpretation in either direction. The previous note, which asserted the `restricted` reading, was replaced.

### 2.6 Data use permission conflict (medium)

`data_use_permission` remains `disease_specific_research`, but a new `source_caveats` was added to `license_and_use_terms` recording that the single enumerated value cannot represent both constraints: the T2DM-only attestation on one hand, and the license's grant of "research, commercial and non-commercial purposes" plus the five DataCite consent flags set to false on the other.

### 2.7 Instances and data substrate (medium)

The audit flagged `data_substrate` as omitted where the enumeration supplies fitting terms. Because a single Instance carries one substrate, the fix was to expand the slot. `instances` grew from one object to eleven: the original participant-level instance (retained, with `counts: 2280` and the label description), plus ten new objects each carrying one `data_substrate` and one `data_topic` — OMOP clinical rows (`B2AI_SUBSTRATE:6`), questionnaire responses (`:80`), ECG waveform (`:49`), retinal photography (`:65`), OCT (`:67`), OCTA (`:68`), FLIO (`:66`), CGM (`:78`), wearable activity (`:73`) and environmental time-series (`:69`).

### 2.8 Labeling strategies (drift, resolved in the full record's favour of adding)

`labeling_strategies` was added to the full record. The audit noted the core stated it and the full did not; since the underlying fact is well supported by the healthsheet, the resolution was to add it to the full record rather than strip it from the core.

### 2.9 Version access (drift)

`version_access.versions_available` was added to the full record, listing 1.0.0, 2.0.0 and 3.0.0 — again resolving the drift by adding to the full record, since the values are directly attested.

### 2.10 External resources split (low)

The single `external_resources` entry holding `https://zenodo.org/communities/aireadi and https://github.com/AI-READI` was split into two objects, one per URL, each with its own `notes`.

### 2.11 Collection timeframe (low)

The third `collection_timeframes` entry changed `start_date` from `2023-07-19` to `2023-07-18`, so that both endpoints of the planned recruitment window come from the BMJ Open protocol rather than blending FAIRhub's start with BMJ's end. A `source_caveats` was added explaining that choice and noting FAIRhub's differing start date and its anticipated completion date of 1 January 2027.

### 2.12 Minted identifiers (medium)

All minted fragment identifiers moved from `doi:10.60775/fairhub.3#…` to `https://fairhub.io/datasets/3#…`, across the three `subsets` entries and all eleven `file_collections` entries. A DOI does not admit a resolvable fragment; the FAIRhub landing page does. A new item (12) in the top-level `source_caveats` records this.

### 2.13 Variable list (low)

Four `categories` values became proper lists:

- `recommended_split`: `Train`, `Val`, `Test`
- `diabetes_status_group`: four separate category strings
- `sex`: `male`, `female`
- `race_ethnicity`: `Asian`, `Black`, `Hispanic`, `White`
- `monofilament_response`: `yes (filament felt)`, `no (insensate)`

`continuous_glucose.missing_value_code` was removed; its prose content moved into `quality_notes`, prefixed with "No missing-value code is documented in the input sources."

### 2.14 De-identification flag (low)

`is_deidentified.method` was rewritten to state the DataCite flags precisely (deIdentDirect and deIdentHIPAA true; deIdentDates, deIdentNonarr, deIdentKAnon false) rather than the vaguer earlier wording. `source_caveats` gained a passage recording that the deIdentDirect flag on a plain reading contradicts the accompanying "no identifiers were collected" statement, that no source reconciles them, and that the flag is reported as stated rather than interpreted. `identifiable_elements_present` remains `false`.

### 2.15 Conforms-to and RO-Crate (low)

`conforms_to` prose changed from "An RO-Crate metadata file accompanies the dataset root and each data type directory" to "…is declared at the dataset root and within each data type directory". `RO_CRATE` remains in `conforms_to_standard`, and a new caveat item (11) records that ro-crate-metadata.json is not among the nine CDS root metadata files and that the crate was retrieved standalone, while noting the crate's own declared conformance.

### 2.16 American English (low)

Throughout the full record: totalling→totaling, generalisability→generalizability, prioritising→prioritizing, prioritisation→prioritization, modelling→modeling, colour→color, centred→centered, metres→meters, centimetre→centimeter, dioptre→diopter, behaviour→behavior, enrolment→enrollment, haemodynamic→hemodynamic, minimise→minimize, programme→program. Quoted source strings — the dataset title, the "Artificial Intelligence Ready and Equitable Atlas…" expansion in the caveats, the license quotation — were left as their sources wrote them.

### 2.17 Notes (low)

`notes` gained a sentence recording that the healthsheet states there is no extension mechanism and no use-tracking repository, and that both slots are therefore left unpopulated rather than used to record an absence. The view and citation counts were retained.

---

## 3. Changes made — core record

### 3.1 The `resources` slot (high)

This was the largest single change. The reconciled core `resources` entries no longer carry a `distributions` key. The invented sub-object — with its `path`, `bytes`, `format`, `media_type`, `conforms_to` and `conforms_to_standard` keys — is gone from all ten data-directory entries and the metadata entry. The file counts and byte totals survive in each entry's `description` prose, and the `conforms_to` / `conforms_to_standard` slots (both declared on `Dataset`, which is the range of `resources`) remain populated at the entry level.

The three split partitions remain in `resources` alongside the ten directories. Their identifiers changed to the FAIRhub-fragment form.

### 3.2 Creator, funders, contacts, committee, confidentiality, permission

All of the changes described in §2.1, §2.2, §2.3, §2.4, §2.5 and §2.6 were applied identically to the core record. Specifically, in the core:

- the self-affiliation entry is gone and `credit_roles` is absent;
- `funders[0].grants` holds one object, with the second RePORTER record moved to `notes`;
- `license_and_use_terms.contact_person`, `regulatory_restrictions.governance_committee_contact` and `data_governance.committee_contact` are all absent;
- `committee_name` is `Data Access Committee`;
- `confidentiality_level` is absent with an explanatory `notes`;
- the `data_use_permission` conflict caveat is present.

### 3.3 Instances (medium)

The core `instances` slot was expanded to the same eleven objects as the full record, carrying the same `data_substrate` and `data_topic` terms.

### 3.4 Content folded back out of prose (medium)

The audit found four cases where the core had moved structured content into `notes` or into a neighbouring object's free-text field. Two were addressed by restoring structure, two by consolidating deliberately:

- **`participant_privacy`** — the audit noted the core had folded part of it into `is_deidentified.deidentification_details` and lost `reidentification_risk` and `data_linkage`. The reconciled core still does not populate `participant_privacy` as a separate slot, but `is_deidentified.deidentification_details` was expanded to carry the participant-ID linkage mechanism, the controlled-access linkage under a DUA, the contractual bars on re-identification and contacting subjects, and the residual re-identification risk. The content is recovered; the slot is not.
- **`relationships`** — the sentence about all instances belonging to one project and being linked by participant ID was removed from `instances[0].notes` in the core. It is not restored as a `relationships` slot in the core; the participant-ID linkage is now carried in `is_deidentified.deidentification_details`.
- **`collection_notifications` / `direct_collection`** — the notification pathway (mailed letter, personalized email, REDCap interface, phone alternative) and the direct-versus-EHR-screening distinction were added to the core as `informed_consent[0].notes`, recovering content the audit found had been lost entirely.
- **`participant_compensation` and `splits`** — these remain as prose in the core `notes`. See §4.

### 3.5 Drift resolved

- `labeling_strategies` — no longer core-only; the full record now states it too, and the two texts were harmonized to the same wording.
- `versions_available` — no longer core-only; added to the full record's `version_access`.
- `use_repository` — removed from the core. The slot was being used to record that no such repository exists, which per the guidance should be an omission; the substantive fact (citation required, per the documentation) moved into the `external_resources` entry for docs.aireadi.org.
- `extension_mechanism` — removed from the core. Both the internally inconsistent `contribution_url` and the "there is no mechanism" text are gone; the absence is recorded in the full record's `notes` instead.

### 3.6 Scale figures (low)

The audit noted the core dropped `total_file_count` and `total_size_bytes` without them being recoverable except by summation. Those slots are still absent from the core, but the figures — 356,343 files and 3,815,969,779,678 bytes — were added to the core `notes`.

### 3.7 External resources, timeframes, identifiers, spelling

The URL split (§2.10), the timeframe start-date change (§2.11), the identifier scheme change (§2.12), the de-identification flag rewrite (§2.14), the `conforms_to` wording (§2.15) and the American English pass (§2.16) were all applied to the core identically.

### 3.8 Source caveats

The core `source_caveats` item (11) was rewritten: it previously described only the core's omission of variable-level detail. It now covers the identifier-scheme decision (as item 11) and the core/full divergence (as item 12), the latter noting that file counts and sizes are carried in the `resources` descriptions.

---

## 4. What was left as-is, and why

**`citation` omitted from the core.** The audit flagged this as a supported omission of a declared, evidenced slot. It remains absent from the core. The full record carries it, and the core's `external_resources` entry for docs.aireadi.org now states that use requires citation of the resources specified there.

**`total_file_count` and `total_size_bytes` omitted from the core.** Still absent as slots. The figures were added to `notes` instead (§3.6), so the numbers are recoverable, but the structured slots were not restored.

**`participant_compensation` and `splits` as core prose.** Both remain in the core `notes` rather than in their declared slots. The compensation sentence and the 70/15/15 split sentence are unchanged. The full record carries both in structured form.

**`participant_privacy` and `relationships` as core slots.** Neither was restored to the core as a slot; their content lives in `is_deidentified.deidentification_details` (§3.4).

**`collection_consents` and `consent_revocations` in the core.** These remain unpopulated in the core; their content is carried by `informed_consent[0].consent_documentation` and `informed_consent[0].withdrawal_mechanism`, as the audit noted was partly the case already.

**`publisher` as `https://fairhub.io/`.** Unchanged in both records. No declared prefix covers FAIRhub, and the audit itself characterized this as tolerable.

**`RO_CRATE` in `conforms_to_standard`.** Retained in both records; the concern was documented in a caveat rather than acted on (§2.15).

**`identifiable_elements_present: false`.** Retained in both. The DataCite `deIdentDirect: true` tension is now recorded in the caveat rather than resolved by changing the value, because no source reconciles the two.

**`data_use_permission: disease_specific_research`.** Retained. The conflict is now flagged rather than resolved, since both readings are attested.

**`funders[0].grants[0].id` as a RePORTER URL.** Retained. No declared prefix covers NIH RePORTER; the duplication, which was the actual defect, was fixed.

**Volatile platform statistics in `notes`.** The 24,636 view count and zero citation count remain in both records. Low durability, but attested by the captured API record and explicitly dated to capture.

**Minted identifiers as fragments.** The scheme changed from DOI to landing-page URL, but fragments are still minted for parts of this dataset. These name things with no referent outside the record, so minting remains the right treatment; only the base was made resolvable.

---

## 5. Referent

Both records describe version 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project (DOI 10.60775/fairhub.3, released 17 November 2025, 2,280 participants). Version 2.0.0 material in the bundle is treated as superseded per the declared ranking. This choice is unchanged from the original records and is held consistently across both.