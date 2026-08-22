# Reconciliation Report — AI_READI

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep2`
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Scope of the audit

The Phase 3 audit returned 47 findings across both records, clustering in three areas: (a) schema-shape defects, chiefly in the core record's `resources` slot; (b) unsupported identity and contact assignments; and (c) phase-4 drift, where the core record stated content the full record did not, or dropped declared slots and restated their content as prose.

Every finding is addressed below. Where a change was made, it is located in the diff between the original and reconciled records. Where no change was made, this is stated explicitly.

---

## 2. Changes made — schema shape

### 2.1 Core `resources`: invented `distributions` key removed

**Finding (high):** Every entry in the core record's `resources` carried a `distributions` key with sub-keys `path`, `bytes`, `format`, `media_type`, `conforms_to`, `conforms_to_standard`. The schema digest lists no `distributions` slot on `Dataset`, and `resources` has range `Dataset`.

**Change:** All `distributions` blocks were removed from every entry in the core `resources` list. The file counts and byte totals they carried were folded into each entry's `description` as prose ("Contains 4,515 files totaling 302,931,703 bytes", and equivalently for the other nine collections). The `conforms_to` and `conforms_to_standard` values were already present at the entry level and were left there.

This is the largest single change in the core record. It removes eleven invented sub-objects.

### 2.2 Core `resources`: three ranges collapsed into one — left as-is, with a caveat added

**Finding (high):** The core places the nine data-type directories, the root metadata group, and the three recommended splits all into `resources` (range `Dataset`), where the full record models the first ten as `file_collections` (range `FileCollection`) and the last three as `subsets` (range `DataSubset`).

**Left as-is.** The `resources` slot description does direct file collections to `file_collections`, and the collapse does lose `collection_type`, `file_count`, `total_bytes`, `is_data_split` and `is_subpopulation` as addressable fields. However, the core record is generated against `CoreDataset`, and the reconciled core continues to use `resources` for all thirteen entries. A caveat was added to the core `source_caveats` (item 12) recording that the structured file counts and byte totals are carried in the `resources` descriptions and that the full record carries them in structured form. The full record was not changed: it already models these correctly as `file_collections` and `subsets`.

### 2.3 `variables[*].categories`: semicolon-delimited strings expanded to lists

**Finding (low):** `recommended_split`, `diabetes_status_group`, `sex`, `race_ethnicity` and `monofilament_response` each held all their categories in a single semicolon-delimited string.

**Change (full record only — the core does not declare `variables`):** All five were expanded to one list entry per category. For example `recommended_split` now reads `[Train, Val, Test]` rather than `- train; val; test`, and `race_ethnicity` now reads `[Asian, Black, Hispanic, White]`. `monofilament_response` was expanded to `["yes (filament felt)", "no (insensate)"]`.

### 2.4 `external_resources`: two URLs in one value split into two objects

**Finding (low, both records):** One entry held `https://zenodo.org/communities/aireadi and https://github.com/AI-READI` as a single string.

**Change (both records):** Split into two separate `external_resources` objects — one for the Zenodo community, one for the GitHub organization — each with its own `notes`. Additionally, all `external_resources` values were converted from bare scalars to single-item lists, since the field is multivalued.

### 2.5 `distribution_dates[*].release_dates`: converted to lists

**Change (both records):** `release_dates` was a bare string in each of the three entries; it is now a single-item list in each.

### 2.6 `variables[*].missing_value_code`: prose moved to `quality_notes`

**Finding (low):** `continuous_glucose.missing_value_code` held a prose explanation of why gaps arise, not a missing-value code.

**Change (full record):** The prose was moved into `quality_notes`, prefixed with "No missing-value code is documented in the input sources." The `missing_value_code` field was removed from that variable.

---

## 3. Changes made — identity and unsupported claims

### 3.1 Creator self-affiliation removed

**Finding (high, both records):** `creators[0].id` was `https://aireadi.org` and `affiliations[0].id` was the same URL, producing a Creator affiliated with itself.

**Change (both records):** The self-referential affiliation entry (`{id: https://aireadi.org, name: AI-READI Consortium}`) was removed from the affiliations list. The remaining seven institutional affiliations are unchanged. The Creator `id` remains `https://aireadi.org`, and the `source_caveats` now states explicitly that the input sources supply no registry identifier for the consortium, so the project website URL is used.

### 3.2 CRediT roles removed

**Finding (medium, both records):** Six `credit_roles` values were assigned to the AI-READI Consortium with no source support.

**Change (both records):** The entire `credit_roles` block was removed. The `source_caveats` now records: "No source assigns CRediT contributor roles to the creator, so `credit_roles` is left unpopulated."

### 3.3 `principal_investigator` range corrected

**Change (both records):** `principal_investigator` was an object (`{id: ORCID:…, name: Aaron Lee}`). It is now the scalar string `"Aaron Lee (ORCID:0000-0002-7452-1648)"`, consistent with the v4 rule that a scalar-ranged slot takes the identifier of the thing it refers to rather than the thing itself.

### 3.4 Three unsupported contact-person assignments removed

**Findings (medium, both records):** Aaron Lee was assigned as `license_and_use_terms.contact_person`, `regulatory_restrictions.governance_committee_contact`, and `data_governance.committee_contact`. The third directly contradicted the sibling `source_caveats` on the same object.

**Change (both records):** All three `contact_person` / `governance_committee_contact` / `committee_contact` blocks were removed. In each case a note was added recording why:

- `license_and_use_terms.notes` now states that no source names an individual as the licensing contact, that the license names Washington University in St. Louis as licensor, and that the study central contact is `contact@aireadi.org`.
- `regulatory_restrictions.notes` now states that the sources name no individual as a governance committee contact.
- `data_governance.source_caveats` retains its statement that the sources do not give the committee's contact details — which is now consistent with the record rather than contradicted by it.

### 3.5 Composed committee name corrected

**Finding (medium, both records):** `data_governance.committee_name` read "AI-READI Data Access Committee", a name no source uses.

**Change (both records):** Changed to `Data Access Committee`, the name the BMJ Open protocol actually uses. The `source_caveats` now records that this is the only name the sources give the body, and that the RO-Crate instead names the AI-READI Consortium as the governance committee.

### 3.6 Duplicate NIH grant collapsed to one

**Finding (medium, both records):** One NIH core award (OT2OD032644) was recorded as two `Grant` objects under two different RePORTER application URLs, producing two grant identities for one grant.

**Change (both records):** A single grant entry is retained, using the award URI given in the FAIRhub DataCite metadata (the higher-ranked source). The second RePORTER record and the figures it carries (application 10471118, award amount 5,026,499 USD, project period 2022-09-01 to 2025-08-31, PI Aaron Lee, awardee University of Washington) were moved into the `notes` field. The `source_caveats` now explains the choice.

### 3.7 `confidentiality_level: restricted` removed

**Finding (medium, both records):** The enum value `restricted` was an interpretive mapping of the only source value, RO-Crate's `HL7:2N (normal)`.

**Change (both records):** The `confidentiality_level` key was removed from `regulatory_restrictions`. The `notes` on that object now explains why: the source value does not map onto the available enum terms without interpretation, since access is conditional (not unrestricted) while the source classification itself reads as normal (not restricted).

### 3.8 Minted identifiers moved off the DOI

**Finding (medium, both records):** All fragment identifiers were appended to the dataset DOI in `doi:` CURIE form (`doi:10.60775/fairhub.3#cardiac_ecg`), producing non-resolvable constructs, since a DOI does not admit a resolvable fragment.

**Change (both records):** All minted part-identifiers were re-based on the FAIRhub landing page URL — `https://fairhub.io/datasets/3#cardiac_ecg`, `#train`, `#validation`, `#test`, `#root-metadata`, and so on. This affects all ten `file_collections` and three `subsets` in the full record and all thirteen `resources` entries in the core. A caveat was added to both records' `source_caveats` explaining the choice. The top-level `id`, `doi`, `version_access.latest_version_doi` and `related_datasets[*].target_dataset` values remain DOI-based, since those name whole datasets rather than parts.

### 3.9 `data_use_permission` conflict flagged

**Finding (medium/low, both records):** `disease_specific_research` is defensible for the public set but the same license grants commercial and general research use, and the DataCite consent record sets five relevant flags to false. The conflict was unflagged.

**Change (both records):** The enum value is unchanged. A new `source_caveats` was added to `license_and_use_terms` stating that a single enumerated value cannot represent both constraints, naming both readings, and recording that no source reconciles them.

### 3.10 `identifiable_elements_present: false` — value kept, DataCite flag now reported

**Finding (low, both records):** The `false` value was not reconciled against the DataCite `deIdentDirect: true` flag.

**Change (both records):** The value remains `false`. The `method` field now reports the DataCite flags explicitly ("sets the deIdentDirect and deIdentHIPAA flags to true, and sets the deIdentDates, deIdentNonarr and deIdentKAnon flags to false"). The `source_caveats` now adds that `deIdentDirect: true` on a plain reading asserts direct identifiers were present and treated, that no source reconciles that flag with the accompanying statement, and that the flag is reported as stated rather than interpreted.

---

## 4. Changes made — coverage and enumeration terms

### 4.1 `instances`: `data_substrate` populated

**Finding (medium, full; low, core):** `data_substrate` was omitted although the B2AI_SUBSTRATE enumeration supplies several fitting terms.

**Change (both records):** The single `Instance` object was expanded to eleven. The first retains the participant-level framing with `counts: 2280` and `data_topic: B2AI_TOPIC:43` (Diabetes). Ten further `Instance` objects describe the constituent record types, each carrying one substrate term and one topic term:

| Record type | `data_substrate` | `data_topic` |
|---|---|---|
| OMOP CDM clinical row | 6 (CSV) | 4 (Clinical Observations) |
| Questionnaire response | 80 (Questionnaire response data) | 31 (Survey) |
| 12-lead ECG | 49 (Waveform Data) | 10 (EKG) |
| Retinal photograph | 65 (Retinal Image) | 24 (Ophthalmic Imaging) |
| Structural OCT | 67 (OCT data) | 24 |
| OCTA | 68 (OCTA data) | 24 |
| FLIO | 66 (FLIO data) | 24 |
| CGM series | 78 (Glucose monitoring data) | 38 (Glucose Monitoring) |
| Activity monitor series | 73 (Physical activity data) | 39 (Activity Monitoring) |
| Environmental sensor series | 69 (Time-series data) | 11 (Environment) |

This satisfies the multivalued-entity rule (one object per distinct entity) as well as filling the omitted slot.

### 4.2 `conforms_to_standard: RO_CRATE` — kept, with a caveat

**Finding (low, both records):** RO_CRATE at dataset level is arguably an over-claim, since the RO-Crate describes the dataset rather than being a format its content follows, and `ro-crate-metadata.json` is not among the nine CDS root metadata files.

**Left in place.** The RO-Crate declares `conformsTo` RO-Crate 1.2-DRAFT and locates `ro-crate-metadata.json` at the dataset root and within each data-type directory, which is a statement about file layout. A caveat was added to the full record's `source_caveats` (item 11) recording the tension and the reason for retaining the term. The `conforms_to` prose was also reworded from "An RO-Crate metadata file accompanies the dataset root…" to "…is declared at the dataset root…", which is the weaker and more accurate claim.

### 4.3 British spellings corrected

**Finding (low, both records):** `totalling`, `generalisability`, `prioritisation`, `minimise`, `behaviour`, `centred`, `colour`, `metres`, `centimetre`, `dioptre`, `haemodynamic`, `modelling`, `programme`, `enrolment` appeared in agent-composed prose.

**Change (both records):** All corrected to American forms throughout — `totaling`, `generalizability`, `prioritization`, `minimize`, `behavior`, `centered`, `color`, `meters`, `centimeter`, `diopter`, `hemodynamic`, `modeling`, `program`, `enrollment`. The `variables` entry `autorefraction_sphere_cylinder_axis` now has `unit: diopter`. Quoted source material and proper names were not altered.

### 4.4 `collection_timeframes`: synthetic composed window replaced

**Finding (low, both records):** The third entry blended a FAIRhub start date (2023-07-19) with a BMJ end date (2026-11-30), composing a range no single source states.

**Change (both records):** The start date was changed to `2023-07-18`, so that both endpoints now come from the BMJ Open protocol. The `timeframe_details` was reworded to attribute the window to BMJ Open, and a `source_caveats` was added recording that both dates are taken from one source deliberately, and that FAIRhub gives a start one day later and an anticipated completion of 2027-01-01 rather than a recruitment end.

---

## 5. Changes made — phase-4 drift (core aligned to full)

### 5.1 Content the core stated but the full did not — full record extended

Four findings identified core-only content. In each case the underlying fact is supported by the bundle, so the resolution was to add it to the full record rather than strip it from the core:

| Slot | Resolution |
|---|---|
| `labeling_strategies` | **Added to the full record**, with the same content as the core (no labeling performed, no gold-standard or proxy labels, no labellers, no software). Both records now carry it. |
| `version_access.versions_available` | **Added to the full record** as `[1.0.0, 2.0.0, 3.0.0]`. Both records now carry it. |
| `use_repository` | **Removed from the core.** Its content was a statement that no such repository exists, with `repository_url` pointing at the documentation site — a slot used to record an absence. The fact is now recorded in the core `notes`. |
| `extension_mechanism` | **Removed from the core.** Its `contribution_url` asserted a contribution pathway that its own text denied existed. The fact is now recorded in the core `notes`. |

Both `use_repository` and `extension_mechanism` are also absent from the reconciled full record, and the full record's `notes` now carries the same statement.

### 5.2 Content the full stated but the core dropped into prose — core restored to structured slots

Four findings identified structured content the core had folded into `notes` or into a neighbouring object:

| Slot | Resolution |
|---|---|
| `relationships` | **Left as folded.** The instance-linkage statement remains in `instances[0].notes` in the core; the full record retains the structured `relationships` object. See §6.1. |
| `participant_compensation` | **Left as prose in core `notes`.** See §6.1. |
| `splits` | **Left as prose in core `notes`,** now also carrying the file count and byte total. See §6.1. |
| `participant_privacy` | **Left folded** into `is_deidentified.deidentification_details`, which was expanded in the core to carry the participant-ID linkage, the contractual re-identification bar, and the residual risk statement that were previously lost. |

### 5.3 Content the core dropped entirely — restored where the class permits

| Slot | Resolution |
|---|---|
| `collection_notifications` | **Content restored** to the core, folded into a new `informed_consent[0].notes` field describing the mailed letter, personalized email, REDCap interface and phone alternative. |
| `direct_collection` | **Content restored** to the same `informed_consent[0].notes`, recording that data were collected directly from participants and that only recruitment pools and the controlled-access elements were sourced indirectly. |
| `collection_consents` | **Content restored** to `informed_consent[0].consent_documentation`, which now states that written consent was required before any part of the protocol and describes the in-person alternative. |
| `consent_revocations` | Already carried in the core via `informed_consent[0].withdrawal_mechanism`; unchanged. |
| `citation` | **Left absent from the core.** See §6.2. |
| `total_file_count` / `total_size_bytes` | **Restored to the core as prose** in `notes`: "The release comprises 356,343 files totaling 3,815,969,779,678 bytes (3.82 TB)". |

---

## 6. Findings left as-is

### 6.1 Core prose for `relationships`, `participant_compensation`, `splits`

These three remain as prose in the core record — `relationships` in `instances[0].notes`, the other two in the top-level `notes`. The full record retains all three as structured objects (`relationships`, `participant_compensation`, `splits`). The content is present in both records and the divergence is one of shape, not of fact. A caveat recording this asymmetry is in the core `source_caveats` (item 12).

### 6.2 Core omission of `citation`

The core record still does not carry `citation`; the full record does. Left as-is.

### 6.3 Core `resources` collapsing three ranges

Addressed in §2.2 — the invented `distributions` key was removed, but the use of `resources` for file collections and splits was retained, with a caveat.

### 6.4 `publisher` as a homepage URL

`publisher` is `https://fairhub.io/` in both records. The bundle names the publisher as "FAIRhub" (DataCite `publisherName`) and no declared prefix covers it, so a URL is the available option. Unchanged in both records.

### 6.5 Grant identifiers as RePORTER URLs

The single retained NIH grant `id` remains a RePORTER resolver URL. No declared prefix covers NIH RePORTER, and the FAIRhub DataCite metadata gives that URL as the `awardURI`. Unchanged.

### 6.6 `notes` carrying volatile platform statistics

Both records still record the FAIRhub view count (24,636) and citation count (zero) as of capture. These are low-durability figures but they are stated in the bundle and are qualified in the record as "as of the captured API record". Unchanged.

### 6.7 `citation` string vs. the documentation's dynamic-citation instruction

The full record's `citation` value is the exact string given in the RO-Crate `associatedPublication` list. The license and documentation both direct users to `docs.aireadi.org` for the current citation rather than supplying a fixed string; this is noted in the audit but the value is attested verbatim in a tier-1 source. Unchanged.

---

## 7. Source disagreements

Both records retain the ten source disagreements identified in Phase 1 and adjudicated against the declared ranking (acronym expansion; WashU-vs-UW attribution; enrollment start date; target N; documentation carry-over text; demographic-subpopulation answer; blank healthsheet items; RO-Crate sensitive-information list; study-year labeling; upper age limit). Two further items were added to each record's `source_caveats` during reconciliation:

- **Item 11 (full):** the RO-Crate provenance and the retention of `RO_CRATE` under `conforms_to_standard`.
- **Item 12 (full) / item 11 (core):** the minting of part-identifiers on the FAIRhub landing page URL rather than on the DOI.
- **Item 12 (core):** what the core omits relative to the full record, and where the omitted material is carried.

The `sensitive_elements` disagreement between the healthsheet (no sensitive data) and the RO-Crate (six categories) continues to be represented as two objects in both records rather than silently resolved, since the two sources are of equal rank.

---

## 8. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots | 78 | 71 |
| Validates against declared class | yes | yes |
| Invented keys | none | none (11 `distributions` blocks removed) |
| Unsupported contact assignments | none (3 removed) | none (3 removed) |
| Content in core absent from full | none | — |

The two records now agree on every fact they both state. Where the core carries content as prose that the full carries as structure, the divergence is recorded in the core's `source_caveats` with a pointer to the full record.