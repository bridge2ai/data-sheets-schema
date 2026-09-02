# CM4AI Reconciliation Report

**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep3`
**Records reconciled:** full (`CM4AI_d4d.yaml`, class `Dataset`) and core (`CM4AI_d4d_core.yaml`, class `CoreDataset`)
**Arm:** BASELINE (declared bundle only, `data/preprocessed/concatenated/CM4AI_preprocessed.txt`, md5 `50037fc631eafda807e19f83f6579818`)

---

## 1. Audit summary

The Phase 3 audit returned 22 findings against the full record: 3 high, 8 medium, 11 low. The referent choice (June 2026 Data Release, `doi:10.18130/V3/HIGT4C`), the DOI/ORCID CURIE forms, the enum values, the fragment-identifier minting scheme and the four documented source conflicts were all confirmed sound and were not disturbed.

The three high-severity findings shared a single root cause: identifiers and affiliations asserted beyond what the bundle attests, together with nine attested authors dropped from `creators` for lacking ORCIDs. Six medium findings concerned governance — an invented committee name, ethical-review contacts promoted to committee members, and three ORCID identifications resting on name similarity or role adjacency rather than statement.

---

## 2. Changes made — full record

### 2.1 `publisher` — removed (high)

The original carried `publisher: ROR:0153tk833`. The bundle contains `https://ror.org/0153tk833` only inside the June 2026 Dataverse *author-affiliation* fields, where it stands in for an institution name for the five University of Virginia authors. No source states that the University of Virginia is the publisher of the release. The slot is absent from the reconciled full record and from the reconciled core record. A note explaining the omission was added to `source_caveats`.

### 2.2 `creators` — nine authors restored, affiliations regularized, names recorded (high, two findings)

The original listed 38 creators, each a bare `id` with an ORCID, and attached `affiliations: [{id: ROR:0153tk833}]` to five of them.

The reconciled record lists **47** creators, matching the Dataverse citation. The nine authors the bundle names without an ORCID (Axelsson U, Chinn B, Fall J, Johannesson A, Khaliq H, Muralidharan M, Pan E, Polacco B, Zhang Y) now appear with fragment identifiers minted on the release DOI — for example `doi:10.18130/V3/HIGT4C#creator-axelsson-u` — with the attested name and affiliation in `notes` and the explicit remark "No ORCID given in the bundle."

Every creator now carries a `notes` value giving the name and the institution the Dataverse listing prints for that author. This removes the asymmetry the audit identified: previously the record appeared to know UVA affiliations and no others, when in fact the bundle prints institution names for all 47 and a ROR URL only for the five UVA entries. The five ROR affiliations are retained, because that is what the source prints for those authors, and each of their `notes` now states so explicitly.

The creators are also reordered to match the Dataverse citation sequence, with the nine restored authors inserted at their cited positions.

### 2.3 `funders[*].grants` — grant identifiers moved from prose into `Grant` objects (low)

The original held all grant identifiers as prose in `funders[*].notes`, with a `source_caveats` entry explaining that the Grant class structure was unavailable. The schema digest does declare `grants: Grant[]` on `FundingMechanism`, and `id` is available on every object. The reconciled record therefore carries three `Grant` objects with minted fragment identifiers on the release DOI:

- `doi:10.18130/V3/HIGT4C#grant-1OT2OD032742-01`
- `doi:10.18130/V3/HIGT4C#grant-OT2OD032742`
- `doi:10.18130/V3/HIGT4C#grant-5U54HG012513-02`

The award amount, project period, application number and principal investigator remain in each grant's `notes`, since `Grant` has no declared field for them in the digest. The Frederick Thomas Fund entry keeps a bare `notes`, as no identifier is given for it. The explanatory clause about the Grant class was dropped from the top-level `source_caveats`.

### 2.4 `data_governance` — committee name, contact and members removed (medium, three findings)

The original carried `committee_name: CM4AI Data Access Committee`, `committee_contact: {id: ORCID:0000-0003-4535-3486}` and two `committee_members` (Ravitsky, Bélisle-Pipon).

All three are absent from the reconciled record. The bundle contains two differently named bodies that no source equates: the June 2026 release names a **Data Governance Committee** contact (Jillian Parker), while the May 2024 preprint states in the future tense that "A Data Access Committee will supervise ethical matters related to dataset distribution and potential dual licensing for commercial use," without naming it or listing members. The string "CM4AI Data Access Committee" appears nowhere in the bundle. Ravitsky and Bélisle-Pipon are named only as **ethical review** contacts, a role recorded separately in the release.

The named individuals remain in `stewardship_roles` in the roles the sources give them, and `access_review_process` now attributes the Data Access Committee statement to the preprint explicitly ("The project preprint states that a Data Access Committee will supervise…"). A new `source_caveats` on `data_governance` records the two-body problem and the decision not to assert a name, membership or contact identifier.

### 2.5 `regulatory_restrictions.governance_committee_contact` — removed (medium)

The original carried `{id: ORCID:0000-0003-4535-3486}`, which the bundle attests as the ORCID of the author "Parker J". Equating that author with the governance contact "Jillian Parker" is an inference no source makes. The slot is absent from the reconciled record; the attested contact string is now carried in `other_compliance`: "The release names Jillian Parker (jillianparker@health.ucsd.edu) as the Data Governance Committee contact."

### 2.6 `license_and_use_terms.contact_person` — removed (medium)

The original assigned Trey Ideker (`ORCID:0000-0002-1708-8454`) as the licensing contact. The bundle lists him as the dataset's Dataverse Point of Contact but nowhere as a contact for license or use terms; for commercial licensing it directs users to the copyright holder. The slot is absent. `license_terms` now closes with the parenthetical "(UCSD, Stanford, and/or UCSF depending upon the specific data package in question)", and `notes` records that no source names a licensing contact.

### 2.7 `instances[*].data_topic` — two reassignments (medium)

- Instance 1 (immunofluorescence images): `B2AI_TOPIC:19` (Microscale Imaging) → **`B2AI_TOPIC:15`** (Image).
- Instance 4 (perturb-seq): `B2AI_TOPIC:34` (Transcriptome) → **`B2AI_TOPIC:12`** (Gene).

The `data_substrate` values (56, 59, 58, 64) were confirmed correct and are unchanged.

### 2.8 `instances[0].instance_type` and `sampling_strategies` — 464-protein figure withdrawn (low)

The original asserted "one of 464 proteins of interest" in the image instance and "464 proteins of interest" in the sampling strategies. The June 2026 file listing carries no per-file descriptions; 464 came from the October 2025 descriptions, and the June 2026 image archives have *different MD5 checksums* from the October 2025 ones, indicating regeneration. The reconciled record says "a protein of interest" and "a defined panel of proteins of interest" respectively. A `source_caveats` on `sampling_strategies` records the 464/563 disagreement and the reason no count is carried over; the top-level `source_caveats` conflict (2) was rewritten accordingly.

### 2.9 `last_updated_on` — removed (low)

The original derived `2026-07-15T00:00:00Z` from the latest per-file publication date. No source states a dataset-level modification date. Removed from both records; noted in `source_caveats`.

### 2.10 `status` — narrowed (low)

`Beta release, published` → **`Beta`**. The composed two-part phrasing was replaced by the term the sources use in the title and on the portal.

### 2.11 `language` and `is_tabular` — removed (low)

`language: en` and `is_tabular: false` are unattested inferences. Both are absent from the reconciled full record. (`is_tabular` is likewise absent from the reconciled core record; `language` was not present in the original core record.)

### 2.12 `compression` at top level — removed (low)

The dataset comprises ten separate ZIP archives rather than being itself one compressed object. The top-level slot is absent from the reconciled full record. The per-collection `compression: zip` values, which are directly attested, are retained on all five file collections.

### 2.13 `collection_timeframes[0]` — `start_date`/`end_date` withdrawn (low)

The original populated these with the NIH RePORTER grant-period boundaries (2022-09-01 / 2026-08-31). Those are a project period, not a collection window, and RePORTER is the lowest-ranked source carrying them. The reconciled entry retains the same dates inside `timeframe_details` with the explicit qualifier "no source states a data collection start or end date for this release," and the scalar date slots are gone.

### 2.14 `preprocessing_strategies` and `cleaning_strategies` — caveats extended (low)

The original carried a caveat on only the fourth preprocessing entry. All four preprocessing entries and `cleaning_strategies[0]` now carry a `source_caveats` stating that the step belongs to the MuSIC pipeline, whose cell-map outputs the release explicitly does not contain. The first preprocessing caveat adds "so this step was not applied to the artifacts distributed here." The cleaning caveat notes that the release itself *is* distributed with FAIRSCAPE-produced RO-Crate metadata, distinguishing the two claims.

### 2.15 Nature 2025 publication — moved to `related_datasets` (low)

The sixth `external_resources` entry (Schaffer et al., Nature 642) was removed from that slot and re-expressed as a `related_datasets` entry with `relationship_type: references` and `target_dataset: doi:10.1038/s41586-025-08878-3`. The explanatory note about U2OS cells moved into that entry's `source_caveats`. `external_resources` now has five entries rather than six.

### 2.16 `related_datasets[3]` — composed title corrected (low)

`Cell Maps for Artificial Intelligence - Data Release (May 2024)` → **`Cell Maps for Artificial Intelligence - Data Release`**. A `source_caveats` records the exact preprint citation and notes that the portal's "May 2024 Data Release" archive entry carries no DOI, so the association is not stated by any source. The corresponding entry in `version_access.versions_available` was changed from `May 2024 Data Release, doi:10.18130/V3/DXWOS5` to `Cell Maps for Artificial Intelligence - Data Release, doi:10.18130/V3/DXWOS5`.

### 2.17 Multivalued string slots converted from lists to prose where the schema declares a scalar

Three slots whose declared ranges are scalar strings held YAML lists in the original and are now single prose values: `sampling_strategies[0].strategies`, `missing_data_documentation[0].missing_data_patterns`, and `missing_data_documentation[0].missing_data_causes`. The content is unchanged; only the serialization differs.

### 2.18 `ethical_reviews[0].contact_person` — flattened to a scalar

`contact_person: {id: ORCID:0000-0002-7080-8801}` → `contact_person: ORCID:0000-0002-7080-8801`.

### 2.19 `notes` — scope disambiguation added

The reconciled `notes` adds a sentence distinguishing the portal's project-wide "11,739 genes targeted" from the same figure appearing at release scope as the KOLF2.1J perturbation atlas gene count, per the audit's observation that one number was arriving from two scopes without the record separating them.

### 2.20 `source_caveats` — rewritten

Conflict (2) now records that *no* protein count is asserted rather than that 464 was adopted; the MD5-checksum observation now explains why the October 2025 count is not carried over; new sentences record the omission of `publisher` and `last_updated_on`, the basis for creator affiliations, and the fragment-identifier treatment of the nine ORCID-less authors; the Grant-class clause was dropped.

---

## 3. Changes made — core record

The core record was re-projected from the reconciled full record. All projections of the changes above are present: the 47-creator list with names in `notes`, the `Grant` objects, the reassigned `data_topic` values, the withdrawn 464 figure with its caveat, the `Beta` status, the extended MuSIC caveats, the scalar-string conversions, the flattened `ethical_reviews.contact_person`, the Nature paper as a `related_datasets` entry, the governance and licensing removals, and the rewritten `notes` and `source_caveats`.

Slots absent from the reconciled core record that were present in the original core record: `publisher`, `language`, `is_tabular`, `last_updated_on`, `compression` (top level), `data_governance.committee_name`, `data_governance.committee_contact`, `data_governance.committee_members`, `regulatory_restrictions.governance_committee_contact`, `license_and_use_terms.contact_person`.

`# Phase 4 reconciliation: completed` was added to the core header, and `# Sources:` retained.

---

## 4. Findings left as-is

**`total_size_bytes` (medium, §2.8 of the audit).** The audit noted the aggregate is derivable from the ten per-file sizes. The reconciled full record still omits it. The sizes are given in mixed decimal units (GB, MB, KB) with one decimal place, so any byte figure would be a converted approximation presented as an exact integer. `total_file_count: 10` is retained, being directly stated.

**`related_datasets[*].name` (low, §2.11 of the audit).** The audit recorded this as "no defect," noting only the composed-title issue handled at §2.16 above. The `name` field is retained on all seven entries.

**`conforms_to_standard: RO_CRATE` (low).** Recorded by the audit as a positive check. Unchanged in both records.

**`file_collections[*].compression` (medium, §2.9 of the audit).** The audit judged the per-collection values supported and flagged only the top-level redundancy, which was resolved at §2.12. All five per-collection `compression: zip` values are retained.

---

## 5. Referent

Unchanged and consistent across both records: the **CM4AI June 2026 Data Release (Beta)**, `doi:10.18130/V3/HIGT4C`, which the declared ranking places at tier 1 and marks as superseding the October 2025 release. The four earlier quarterly releases and the two describing preprints are held in `related_datasets`; the Nature 2025 U2OS study now joins them under `references`.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 44 | 47 |
| Validated | yes | yes |
| Creators | 47 | 47 |
| Findings actioned | 19 of 22 | projected |
| Findings left as-is | 4 (one overlapping) | — |

Validation commands run against `data_sheets_schema_all.yaml` (class `Dataset`) and `data_sheets_schema_core_all.yaml` (class `CoreDataset`); both passed. Provenance recorded via `d4d provenance record`.