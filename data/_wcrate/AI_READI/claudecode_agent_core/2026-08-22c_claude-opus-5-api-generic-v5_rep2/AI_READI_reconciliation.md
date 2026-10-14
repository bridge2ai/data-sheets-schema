# Reconciliation Report — AI_READI

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep2`
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 (strict reconciliation following Phase 3 source/provenance audit)

---

## 1. Audit summary

The Phase 3 audit returned 32 findings: 2 high, 10 medium, 18 low, 2 informational. The dominant patterns were:

- an unsupported standard assertion (`RO_CRATE`) and a core-record slot whose shape did not match the digest (`distributions` with `path`/`bytes`);
- projection loss in the core record, where content the full record carried in dedicated objects had been demoted into free-text `notes` on neighbouring objects;
- identifier misuse, where RO-Crate subcrate ARKs were reused as file-collection identifiers and subset fragments hung off the landing-page URL rather than the DOI;
- list-shaped slots holding a single multi-clause prose entry;
- two enum values inferred rather than transcribed, one of them against a tier-1 value;
- consistent British spelling in record-authored prose against the declared American-English rule.

---

## 2. Changes made to the full record

### 2.1 `conforms_to_standard` — `RO_CRATE` removed (high)

`RO_CRATE` was dropped from the dataset-level `conforms_to_standard` list. The bundle supplies an RO-Crate metadata document *describing* the release; no source states that the distributed dataset is packaged as an RO-Crate, and the released tree is organized per CDS v0.1.1. The RO-Crate is now recorded instead as an `external_resources` entry, explicitly flagged as "a separate packaging description of the release rather than as a component of the distributed dataset". A sentence in the top-level `source_caveats` records the reasoning.

### 2.2 `creators` — one object per entity (low, but structurally significant)

The original single `Creator` object carried eight `affiliations` and named fifteen further PIs only in prose. It has been replaced by 21 objects:

- one for the AI-READI Consortium (the DataCite organizational creator), carrying only `notes` because no identifier for the consortium appears in any source;
- one per named principal investigator, each with its own `affiliations` and `credit_roles`.

Aaron Lee's object now carries **no** `affiliations`, with a local `source_caveats` recording that FAIRhub says Washington University in St. Louis and the RO-Crate says the Department of Ophthalmology, University of Washington — a same-tier disagreement the ranking cannot settle. Cecilia S. Lee carries a comparable local caveat. ORCID values moved from a `principal_investigator` object field into each `notes`, because `principal_investigator` in the reconciled record is a scalar name string.

Two entries were added that the original omitted: Hiroshi Ishikawa and Camille Nebeker (Nature Metabolism PI list), plus Aaron Y. Lee and Jeffrey C. Edberg. The Aaron Y. Lee entry carries an explicit note that the sources do not state whether this is the same individual as the Aaron Lee recorded as responsible party.

`ROR:00cvxb145` (University of Washington) is retained, but now only on Aaron Y. Lee, whose Nature Metabolism affiliation states it directly — not as a blanket affiliation of a single composite creator drawn from a location list.

### 2.3 `funders` — distinct awards as distinct entries (low)

P30 DK035816 and UL1TR003096 were named only in prose inside `funders[0].notes`. Each is now its own `FundingMechanism` object with its own `grants` entry. Their identifiers are minted as fragments on the attested NIH RePORTER award URL (`…/10471118#P30DK035816`), with a local `source_caveats` on each recording that the publications give the grant number alone. The RePORTER application-ID discrepancy (10885481 in FAIRhub vs 10471118 in the README and the RePORTER source) is now recorded in `funders[0].source_caveats` as well as the top-level caveat.

### 2.4 `file_collections` — identifiers re-minted (medium)

All nine datatype directories now use fragments on the dataset DOI (`doi:10.60775/fairhub.3#cardiac_ecg`, etc.) rather than the RO-Crate subcrate ARKs. Each entry gains an `external_resources` block naming the corresponding ARK and its `ro-crate-metadata.json` path, so the subcrate reference is preserved but no longer conflated with the directory it describes. The root-metadata entry, already a DOI-adjacent fragment, was changed from a landing-page fragment to a DOI fragment for consistency.

`conforms_to_standard` on each collection retains both the format standard and `CDS`, which the digest permits.

### 2.5 `subsets` — identifiers re-based on the DOI (medium)

`https://fairhub.io/datasets/3#training-split` and its siblings became `doi:10.60775/fairhub.3#training-split` and siblings, so that all parts of the dataset hang off the same attested base as the record `id`.

### 2.6 `known_biases[3].affected_subsets` — prose replaced by a reference (low)

The value was a sentence. It is now the subset identifier `doi:10.60775/fairhub.3#training-split`. The `affected_subsets` entry on `known_biases[1]` (`"All participants."`) was **removed** rather than rewritten, since "all participants" is not a subset reference and the same information is already in `bias_description`.

### 2.7 List-shaped slots split into entries (low)

- `human_subject_research.irb_approval`: 1 entry → 3 (protocol and initial approval; renewal requirement; reliance agreements).
- `human_subject_research.regulatory_compliance`: 1 entry → 5 (registration; FDA status; DMC; review status; GDS Policy obligation).
- `human_subject_research.special_populations`: 1 entry → 2.
- `at_risk_populations.special_protections`: 1 entry → 5.
- `data_governance.stewardship_roles`: 1 entry → 6.
- `ip_restrictions.restrictions`: 1 entry → 4.
- `regulatory_restrictions.regulatory_restrictions`: 1 entry → 2.
- `external_resources[*].external_resources`: each scalar string became a single-element list, matching the multivalued declaration.
- `distribution_dates[*].release_dates`: each scalar date became a single-element list.

### 2.8 `variables` — two internal defects corrected (low)

- `Monofilament test response.categories` was `['yes; no']`; it is now `['yes', 'no']`.
- `Montreal Cognitive Assessment (MoCA) total score` no longer sets `maximum_value: 30.0`. The ceiling is stated in `notes` with an explicit sentence explaining that this matches the treatment of laboratory reference ranges, since the sources do not state the observed range. Laboratory-range notes were reworded to say so consistently.

The list also grew (30 → 46 entries) to cover measured domains the sources name but the original omitted: total cholesterol, triglycerides, HDL, BUN, BUN/creatinine ratio, albumin, calculated globulin, A/G ratio, urine creatinine, waist-hip ratio, mesopic contrast sensitivity, autorefraction, respiratory rate, stress, calorie, VOCs and multi-spectral light.

### 2.9 Two enum values now flagged locally (low)

`regulatory_restrictions` gains a `source_caveats` stating that `confidentiality_level: restricted` is an interpretation set against the RO-Crate's tier-1 `HL7:2N (normal)`, and that `hipaa_compliant: compliant` is not stated in those terms by any source. The `notes` field that previously carried a partial version of this reasoning was replaced by the caveat. `license_and_use_terms.notes` gains a sentence explaining that `disease_specific_research` reflects the access self-attestation, not the licence grant, which permits commercial and research use.

### 2.10 Slots added

`data_protection_impacts`, `existing_uses`, `extension_mechanism` — each answers a question the healthsheet answers explicitly and each was previously carried only as a clause inside another object's `notes`. `ethical_reviews[1].contact_person` was added (Camille Nebeker). `related_datasets` gained an `is_new_version_of` entry for v1.0.0 and two `is_documented_by` entries recorded in the DataCite related-identifier block.

### 2.11 Spelling (low)

`tumour` → `tumor`, `oedema` → `edema`, `centimetre` → `centimeter`, `labelling` → `labeling`, `colour` → `color` in record-authored prose. `enrolment` was **not** changed in the full record (see §4.4). Quoted licence text retains its own spelling.

---

## 3. Changes made to the core record

### 3.1 `distributions` — retained, restructured (high finding, partially actioned)

The audit flagged `distributions` with `path`/`bytes` keys as not appearing in the supplied digest, which covers `Dataset` and `DataSubset`/`FileCollection` but not `CoreDataset`'s own slot inventory. The slot is **still present** in the reconciled core record with the same `path`/`bytes` key names. What changed:

- `conforms_to_standard` per entry was reduced to a single value (the format standard) rather than a two-element list, and the CDS organizing standard moved into `conforms_to` and `notes`. A sentence in `source_caveats` records that this was done "because conforms_to_standard on a distribution is single-valued".
- The RO-Crate subcrate ARKs, previously absent from the core record, are now named in each entry's `notes`.

The finding was therefore actioned in part rather than resolved. Validation against the core schema is the arbiter; if `distributions` is not declared, this remains an open defect.

### 3.2 `conforms_to_standard` — `RO_CRATE` removed (high)

Same change as the full record, with matching `source_caveats` text.

### 3.3 `creators` and `funders` — projected from the reconciled full record

Both slots now match the full record's restructured form: 21 creator objects, 5 funder objects, ORCIDs in `notes`, local caveats preserved.

### 3.4 Content returned from prose to structure — partially

- **`data_protection_impacts`, `existing_uses`, `extension_mechanism`** were added to the core record, matching the full record.
- **`acquisition_methods`** gained a fifth entry carrying the direct-collection fact (`was_directly_observed: true`), addressing the audit's note that the core record dropped `direct_collection` without substitute.
- **`is_deidentified.deidentification_details`** still absorbs the privacy-technique content, but now also states the re-identification risk and the data-linkage facts that the previous core record omitted entirely. The `participant_privacy` object remains absent from the core record.
- **`informed_consent[0].notes`** still carries the compensation and notification content; it was expanded to include the consent-mechanics detail (`collection_consents`) that the previous core record had dropped. The three separate objects in the full record (`collection_consents`, `collection_notifications`, `participant_compensation`) remain folded into this one core object.
- **`instances[0].notes`** still carries the relationship and split content. It was expanded to include the per-split composition figures, which previously lived only in the full record's `subsets`.
- **`data_governance.notes`** still carries the onward-sharing constraint; `third_party_sharing` with its `is_shared` boolean remains absent from the core record.

Where the core schema declares the dedicated slot, these remain projection defects. Where it does not, the folding is the correct projection and the expansion above reduces information loss.

### 3.5 `citation` content moved out of `description` (medium)

The trailing citation sentence was removed from `description` and now appears as the first sentence of the core `notes`. The full record's dedicated `citation` slot has no core counterpart in this record.

### 3.6 Variable inventory moved and expanded (medium)

The compressed variable list previously at the end of core `notes` was rewritten and expanded to match the full record's 46-entry inventory, with an explicit closing sentence that laboratory reference ranges and the MoCA ceiling describe normality rather than observed range.

### 3.7 List splits, spelling, subset reference

All the list splits in §2.7 were applied identically to the core record. `known_biases[3].affected_subsets` became `["suggested training split"]` — a label rather than the DOI fragment used in the full record, because the core record has no `subsets` slot for the fragment to resolve against. `known_biases[1].affected_subsets` was removed. Spelling was corrected as in §2.11, and additionally `enrolment` → `enrollment` throughout the core record.

---

## 4. Findings left as-is

### 4.1 `conforms_to_schema` identical in both records (medium)

Both still carry `https://w3id.org/bridge2ai/data-sheets-schema`. The bundle supplies no evidence of a distinct IRI for the core schema, and inventing one would be worse than repeating the one attested value.

### 4.2 `related_datasets[2].target_dataset` (low)

`https://fairhub.io/datasets/4` is unchanged. The `source_caveats` was strengthened to say the identifier "is constructed from that integer against the FAIRhub dataset URL pattern and should be treated as inferred rather than attested." The alternative — omitting the relationship — would lose a fact the API does state.

### 4.3 `funders[0].grants[0].id` as a resolver URL (low)

Unchanged. No schema-declared prefix covers NIH RePORTER application IDs, so the URI fallback in a `uriorcurie` slot is correct, and the URL is attested verbatim.

### 4.4 `enrolment` in the full record (low)

The core record was corrected; the full record still reads `enrolment` in `collection_timeframes`, `sampling_strategies`, `known_biases[3]`, `discouraged_uses[1]` and `at_risk_populations`. This is an inconsistency between the two records and an outstanding defect against the declared American-English rule.

### 4.5 `data_topic: B2AI_TOPIC:43` as the sole instance term (low)

Unchanged in both. `data_substrate` remains omitted, which the digest permits where no single term fits a multimodal instance.

### 4.6 The two informational findings

No action required; both concerned correct handling already in place (the tier-preference caveats and the Safe Harbor resolution), and both are preserved verbatim.

---

## 5. Consistency across the pair

Both records name the same referent — release v3.0.0 of the FAIRhub-hosted dataset, `doi:10.60775/fairhub.3` — and carry identical values for `id`, `doi`, `version`, `issued`, `license`, `conforms_to`, `conforms_to_standard`, `creators`, `funders` and every shared caveat. The differences are confined to: `conforms_to_class` (as required), the presence of `citation`/`total_file_count`/`total_size_bytes`/`splits`/`subsets`/`relationships`/`file_collections`/`variables`/`participant_privacy`/`collection_consents`/`collection_notifications`/`consent_revocations`/`participant_compensation`/`third_party_sharing`/`direct_collection` in the full record only; `distributions` in the core record only; and the two `affected_subsets` formulations noted in §3.7.