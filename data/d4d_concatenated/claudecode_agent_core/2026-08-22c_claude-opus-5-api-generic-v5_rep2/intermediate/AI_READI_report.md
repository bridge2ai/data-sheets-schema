```markdown
# Phase 4 Reconciliation Report — AI_READI

Version label: `2026-08-22c_claude-opus-5-api-generic-v5_rep2`
Records reconciled: full (`Dataset`) and core (`CoreDataset`)
Source of findings: Phase 3 source/provenance audit (31 findings: 2 high, 9 medium, 18 low, 2 info)

---

## 1. What the audit found

The audit judged both records densely and largely faithfully grounded, with tier-preference reasoning applied correctly at each point where sources conflict. It raised two high-severity issues, nine medium, eighteen low and two informational (no-defect) notes. The dominant medium-severity pattern was **projection loss** in the core record: content that the full record carried in dedicated objects had been folded into free-text `notes` on neighbouring objects. The dominant low-severity pattern was **list-shaped slots holding a single multi-clause prose entry**. No fabricated identifiers were found.

---

## 2. Changes made — full record

### 2.1 `conforms_to_standard`: `RO_CRATE` removed (high)

**Finding:** `RO_CRATE` was asserted on the strength of an RO-Crate metadata document existing as a source, not on any statement that the release is RO-Crate packaged.

**Change:** `RO_CRATE` is gone from the top-level `conforms_to_standard` list, which now reads `CDS, DICOM, WFDB, OMOP_CDM, OPEN_MHEALTH, ESDS`. A paragraph in `source_caveats` records the removal and its reasoning. A new `external_resources` entry records the RO-Crate document itself (`ark:59853/rocrate-b2ai-aireadi-release-3-0-0`, RO-Crate 1.2-DRAFT and FAIRscape 0.1 profiles, nine subcrates) with a note distinguishing the packaging description from the distributed tree.

### 2.2 `file_collections`: subcrate ARKs no longer used as directory identifiers (medium)

**Finding:** Nine `file_collections` entries reused `ark:59853/rocrate-b2ai-ai-readi-*` identifiers that the RO-Crate assigns to *subcrate documents*, conflating two referents.

**Change:** All nine `id` values are now fragments on the dataset DOI — `doi:10.60775/fairhub.3#cardiac_ecg`, `#clinical_data`, `#environment`, `#retinal_flio`, `#retinal_oct`, `#retinal_octa`, `#retinal_photography`, `#wearable_activity_monitor`, `#wearable_blood_glucose`. Each of those nine entries gains an `external_resources` block naming its subcrate ARK and the path of its `ro-crate-metadata.json`, so the ARK is retained as a reference rather than reused as a label. The tenth entry, root metadata files, moved from `https://fairhub.io/datasets/3#root-metadata-files` to `doi:10.60775/fairhub.3#root-metadata-files` for consistency of base.

### 2.3 `subsets`: fragment base changed to the DOI (medium)

**Finding:** Three `DataSubset` ids hung off the landing-page URL while the dataset `id` is the DOI, giving two identifier bases within one record.

**Change:** `doi:10.60775/fairhub.3#training-split`, `#validation-split`, `#test-split`. A `source_caveats` paragraph states the minting rule applied.

### 2.4 `creators`: one object per entity (low, but structurally significant)

**Finding:** A single `Creator` carried eight `affiliations` spanning the sponsor, seven collaborating organizations and three sites, plus fifteen further PIs named only in prose — collapsing distinct entities and making a false affiliation claim about the named individual.

**Change:** `creators` is now twenty-one objects. The first records the organizational creator (AI-READI Consortium) in `notes` with no fabricated identifier. The remaining twenty are one per named principal investigator, each with its own `principal_investigator` and, where the sources attest one, a single `affiliations` entry. Aaron Lee now carries **no** affiliation, with a local `source_caveats` recording the unresolved tier-1 disagreement (Washington University in St. Louis vs. University of Washington). Cecilia S. Lee likewise carries no affiliation, with its own caveat. Four PIs named only in the Nature Metabolism list (Hiroshi Ishikawa, Camille Nebeker, Aaron Y. Lee, Jeffrey C. Edberg) are recorded without ORCIDs, as the sources give none. Two new ROR values appear (`ROR:03r0ha626` University of Utah, `ROR:03hamhx47` University of Massachusetts Lowell) — both attested in the FAIRhub `overallOfficialList`.

The audit's separate note that `ROR:00cvxb145` (University of Washington) was drawn from a location list rather than a creatorship statement is now moot for the sponsor-affiliation use: that ROR appears only once, on Aaron Y. Lee, whose University of Washington affiliation the Nature Metabolism author list states directly.

### 2.5 `funders`: distinct awards as distinct objects (low)

**Finding:** P30DK035816 and UL1TR003096 were named in prose inside `funders[0].notes` rather than as entries.

**Change:** Two new `FundingMechanism` objects, one for P30 DK035816 (grantor: National Institute of Diabetes and Digestive and Kidney Diseases) and one for UL1TR003096 (grantor: National Institutes of Health), each with a `grants` entry and a local `source_caveats` stating that the identifier is minted as a fragment on the attested RePORTER URL because the bundle contains no separate RePORTER record. `funders` is now five objects. The 10471118 vs. 10885481 discrepancy the audit flagged is now recorded explicitly in `funders[0].source_caveats` and in top-level `source_caveats`.

### 2.6 `collection_timeframes`: dates moved into date fields (low)

**Finding:** Only the first of three entries used `start_date`/`end_date`; the pilot window was in prose despite both dates being stated.

**Change:** Four entries now. The pilot entry carries `start_date: '2023-07-18'` and `end_date: '2023-11-30'`. A new entry carries `start_date: '2023-12-01'` for the formal collection start. The overall study period entry carries `start_date: '2023-07-19'` and `end_date: '2027-01-01'`.

### 2.7 List-shaped slots split into one entry per fact (low)

- `human_subject_research.irb_approval`: one entry → three (approval and date; renewal requirement; reliance agreements).
- `human_subject_research.regulatory_compliance`: one entry → five (registration; FDA status; DMC; review status; GDS obligation).
- `human_subject_research.special_populations`: one entry → two.
- `at_risk_populations.special_protections`: one paragraph → five entries.
- `data_governance.stewardship_roles`: one paragraph → six entries.
- `ip_restrictions.restrictions`: one paragraph → four entries.
- `regulatory_restrictions.regulatory_restrictions`: one entry → two.
- `version_access.versions_available`: one paragraph → three entries, one per version.

### 2.8 `known_biases.affected_subsets`: prose replaced by subset references (low)

**Change:** The `sampling_bias` entry's `affected_subsets` (`'All participants.'`) was dropped as vacuous. The `representation_bias` entry now references `doi:10.60775/fairhub.3#training-split` rather than a sentence.

### 2.9 `variables`: internal inconsistency resolved, categories split (low)

- **MoCA:** `maximum_value: 30.0` removed. The ceiling of 30 is now stated in `notes`, with an explicit sentence explaining that it is treated like a laboratory reference range because the sources do not state the observed range. This makes the treatment consistent across the slot.
- **Monofilament:** `categories: ['yes; no']` → `categories: ['yes', 'no']`.
- The list grew from 30 to 47 entries, adding total cholesterol, triglycerides, HDL cholesterol, blood urea nitrogen and the BUN/creatinine ratio, albumin, calculated globulin and A/G ratio, urine creatinine, waist-hip ratio, mesopic contrast sensitivity, autorefraction spherical component, respiratory rate, stress level, physical activity calorie, volatile organic compounds and multi-spectral light intensity — all attested in the bundle. Reference-range notes were reworded to say explicitly that they describe clinical normality rather than the observed range.

### 2.10 `regulatory_restrictions`: interpretive enums flagged (low)

**Finding:** `confidentiality_level: restricted` overrides a tier-1 value; `hipaa_compliant: compliant` is inferred over an enum.

**Change:** Both values are retained, but the justification moved from `notes` to a `source_caveats` field, rewritten to say plainly that the RO-Crate (tier 1) records `HL7:2N (normal)`, that no source states a confidentiality level in the schema's terms, and that both values are interpretations rather than transcriptions. The `notes` field is gone from this object.

### 2.11 `license_and_use_terms`: two-layer restriction explained (low)

**Change:** `data_use_permission: disease_specific_research` retained; `notes` gains a sentence stating that the term reflects the access self-attestation and that the licence grant itself permits research, commercial and non-commercial use.

### 2.12 `related_datasets`: v1.0.0 and documentation relations added; inference flagged (low)

**Change:** A second `is_new_version_of` entry for `doi:10.60775/fairhub.1` was added (previously mentioned only in the v2 entry's notes), plus two `is_documented_by` entries for `https://docs.aireadi.org/` and `https://aireadi.org/`, both attested as DataCite `relatedIdentifier` values. The `has_part` caveat for `https://fairhub.io/datasets/4` was expanded to state plainly that the URL is constructed from the integer `4` and should be treated as inferred rather than attested.

### 2.13 `ethical_reviews`: `contact_person` populated (structural)

**Change:** The AI-READI ethics team entry now carries `contact_person: {name: Camille Nebeker}`, using a declared field of `EthicalReview` rather than leaving the named reviewers only in prose.

### 2.14 New slots populated

Three slots absent from the original full record are now present, each answering a datasheet question the bundle addresses:

- `data_protection_impacts` — records that no DPIA was conducted.
- `existing_uses` — records the creators' "No" answer and the zero citation count.
- `extension_mechanism` — records that no external contribution mechanism exists.

`use_repository[0].notes` was trimmed accordingly, since the "not used for any tasks" claim now sits in `existing_uses`.

### 2.15 American English (low)

**Change:** `tumour` → `tumor` and `oedema` → `edema` in `data_collectors`; `centimetre` → `centimeter` in `anomalies`; `labelling` → `labeling` in `instances` and `updates`; `licence` → `license` in the BMJ Open restriction line. `enrolment` remains in several places in the full record — see §4.4.

---

## 3. Changes made — core record

### 3.1 `distributions`: retained, with per-entry corrections (high, partially addressed)

**Finding:** The `distributions` slot and its `path`/`bytes` keys are not in the supplied schema digest for `Dataset`/`CoreDataset`; the full record's equivalent content sits in `file_collections`, which does declare `path`, `file_count` and `total_bytes`.

**Change:** The slot and its `path`/`bytes` keys are **unchanged** — the core schema is `data_sheets_schema_core_all.yaml`, and the digest supplied to this task is the *full* schema's `Dataset` inventory, so it cannot settle whether the core schema declares `distributions`. Rather than restructure on an unverifiable premise, the entries were corrected in two respects the digest does settle:

- `conforms_to_standard` on each entry changed from a list to a single value (`WFDB`, `OMOP_CDM`, `ESDS`, `DICOM`, `OPEN_MHEALTH`, `CDS`), with the CDS organizing standard moved into `conforms_to` and the entry `notes`.
- Each of the nine directory entries gained a sentence in `notes` naming its RO-Crate subcrate ARK and serialization path, mirroring the full record's `external_resources` treatment.

A `source_caveats` paragraph records both the single-valued change and the subcrate-ARK handling. This finding is therefore **partially addressed**: the identifier and cardinality issues are fixed, the slot-declaration question is left open and flagged.

### 3.2 `conforms_to_standard`: `RO_CRATE` removed (high)

Same change and same reasoning as §2.1. The core `source_caveats` carries the equivalent paragraph.

### 3.3 `creators` and `funders`: rebuilt to match the full record (low/structural)

The core record now carries the same twenty-one `Creator` objects and five `FundingMechanism` objects as the full record, with the same local caveats.

### 3.4 Projection losses partially repaired (medium, five findings)

The audit raised five distinct demotion-to-prose issues. Each was addressed by making the core prose complete and explicit rather than by adding slots whose presence in the core schema cannot be verified from the supplied digest:

| Audit finding | Disposition |
|---|---|
| `instances[0].notes` absorbs `relationships` and `splits` | Note **expanded** — now states the per-participant directory linkage, the follow-up-visit relationship, the 70/15/15 split, and the full per-arm composition of all three splits (race/ethnicity, sex, diabetes status, mean age). |
| `informed_consent[0].notes` absorbs compensation | Note **expanded** — amount, timing, non-proration, travel reimbursement, rideshare assistance, personnel-effort funding, and the 25-dollar transport cap. |
| `informed_consent[0].consent_documentation` absorbs notification | Notification content **moved out of** `consent_documentation` into `notes`, alongside the consent-request mechanics; `consent_documentation` now holds only documentation facts. |
| `is_deidentified.deidentification_details` absorbs privacy techniques | **Expanded** to include the re-identification risk statement and the data-linkage description, both of which the original core record had dropped entirely. |
| `data_governance.notes` absorbs third-party sharing | Note **retained and reworded** to state the public distribution and the licensee-to-licensee constraint explicitly. |

Three further slots the audit noted as core-absent were **added**, since the bundle plainly supports them and they mirror the full record: `data_protection_impacts`, `existing_uses`, `extension_mechanism`.

### 3.5 `description` and `citation` (medium)

**Finding:** The core `description` appended citation text while the digest declares a `citation` slot.

**Change:** The citation sentence was **removed from `description`** and relocated to the opening of core `notes`. The `citation` slot itself remains unpopulated in the core record — see §4.2.

### 3.6 `acquisition_methods` gains the direct-collection fact (low)

**Finding:** The core record omitted `direct_collection` with no substitute.

**Change:** A fifth `InstanceAcquisition` entry now records direct collection from participants at the three sites, EHR-based pool identification, and `was_directly_observed: true`.

### 3.7 `collection_timeframes`, list splits, `affected_subsets`, spelling

The core record received the same four-entry timeframe treatment (§2.6), the same list splits for `irb_approval`, `regulatory_compliance`, `special_populations`, `special_protections`, `stewardship_roles`, `restrictions`, `regulatory_restrictions` and `versions_available` (§2.7), and the same MoCA/monofilament-equivalent prose treatment in `notes`. `affected_subsets` changed to `['suggested training split']` — a label rather than a DOI fragment, since the core record has no `subsets` slot for the fragment to reference.

Core spelling was corrected further than the full record: `enrolment` → `enrollment` throughout, `licence` → `license` throughout, plus the same `tumour`/`oedema`/`centimetre`/`labelling` fixes.

### 3.8 Core `notes` rewritten (medium)

**Finding:** Core `notes` closed with a compressed variable inventory where the full record has 30 (now 47) structured `VariableMetadata` objects.

**Change:** The inventory was **retained and expanded** to match the enlarged full-record list, but reframed: it now closes with an explicit statement that laboratory reference ranges and the MoCA ceiling of 30 describe clinical or instrument normality rather than the observed range — the same reasoning the full record now applies in `variables`.

---

## 4. Left as-is, and why

### 4.1 `distributions` slot declaration (high, §3.1)

The slot survives. The supplied digest is the full schema's `Dataset` inventory and does not describe `CoreDataset`; I cannot state from it that the core schema fails to declare `distributions`, and restructuring on an unverified premise risks destroying correct content. The per-entry defects the digest *does* settle were fixed. If validation against `data_sheets_schema_core_all.yaml` rejects the slot, the content maps cleanly onto `file_collections`.

### 4.2 `citation` in the core record

Removed from `description` but not added as a `citation` slot, for the same reason as §4.1: the digest does not establish that `CoreDataset` declares it. The citation text is preserved in core `notes`.

### 4.3 `conforms_to_schema` identical in both records (medium)

Both still carry `https://w3id.org/bridge2ai/data-sheets-schema`. The audit correctly notes that if the core schema has a distinct IRI this is wrong — but also notes the bundle supplies no evidence either way, and neither does the digest. Changing it would substitute a guess for a value that is at least defensible as the schema family IRI.

### 4.4 `enrolment` in the full record

Corrected in the core record; several instances remain in the full record's `collection_timeframes`, `sampling_strategies`, `known_biases`, `discouraged_uses` and `source_caveats`. This is an incomplete fix and a residual defect against the American-English rule.

### 4.5 `funders[0].grants[0].id` as a resolver URL (low)

`https://reporter.nih.gov/project-details/10471118` remains. It is attested verbatim, no schema-declared prefix covers NIH RePORTER application IDs, and `uriorcurie` admits the URI fallback where no prefix fits. The 10471118/10885481 discrepancy is now flagged rather than silently resolved.

### 4.6 `instances[0].data_topic` and omitted `data_substrate` (low)

`B2AI_TOPIC:43` (Diabetes) retained, `data_substrate` still omitted. The instance genuinely spans tabular, imaging and waveform substrates, and the slot is single-valued; the digest's instruction is to omit rather than approximate.

### 4.7 `hipaa_compliant` and `confidentiality_level` values (low)

Both enum values retained. Removing them would lose real information the bundle supports; the correct remedy for an interpretation is to mark it as one, which `source_caveats` now does in both records.

### 4.8 `related_datasets` constructed target URL (low)

`https://fairhub.io/datasets/4` retained with an expanded caveat. The relationship is real and stated; only the identifier form is inferred, and omitting the entry would lose the relationship.

### 4.9 Two informational findings

The audit's two `info` findings — that top-level `source_caveats` handles the four source conflicts exemplarily, and that the Safe Harbor vs. no-identifiers conflict is resolved correctly toward tier 1 — record no defect. Both treatments are unchanged and extended: `source_caveats` in both records gained paragraphs covering the award-identifier discrepancy, the identifier-minting rule and the `RO_CRATE` removal.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Findings addressed | 1 high, 2 medium, 12 low | 1 high (partial), 6 medium, 10 low |
| Findings flagged rather than changed | 1 medium (`conforms_to_schema`), 4 low | 1 high (`distributions` declaration), 1 medium (`conforms_to_schema`), 4 low |
| Fabricated identifiers found | none | none |

No factual content was drawn from any prior D4D record. Every identifier added in this phase is either attested in the declared bundle or minted as a fragment on an attested identifier, with the minting rule stated in `source_caveats`.
```