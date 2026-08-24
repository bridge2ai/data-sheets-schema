# Reconciliation Report — CHORUS

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep3`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 (strict reconciliation), following Phase 3 source/provenance audit

---

## 1. Scope and referent

Both records describe the **CHoRUS clinical care dataset** — the multicenter, multimodal critical care data resource assembled by the Bridge2AI AI/ML for Clinical Care Grand Challenge — and not the CHoRUS GitHub software repositories, nor the AIM-AHEAD Bridge2AI for Clinical Care Training Program. Both of the latter appear in the declared bundle and are recorded only where they bear on the dataset (tooling under `collection_mechanisms` and `preprocessing_strategies`; the training program under `existing_uses`, `data_governance.access_review_process`, and `intended_uses`). This referent choice is unchanged from Phase 1/2 and is stated in the `source_caveats` of both reconciled records.

---

## 2. What the audit found

The Phase 3 audit returned 34 findings across four families:

1. **Full/core divergence (3 high, several low).** Three facts appeared in the core record in slots where the full record did not carry them, because the core dropped `direct_collection`, `third_party_sharing`, and `splits` and folded their content into `acquisition_methods[0]`, `data_governance.notes`, and `notes`. The core also reclassified the nine modalities from `subsets` (DataSubset) into `resources` (Dataset), reusing identical identifiers for objects of different classes across the pair.
2. **Unsupported role and identity assertions (medium).** Five of six `creators` were placed in `principal_investigator` on the strength of a leadership-team slide; `license_and_use_terms.contact_person` re-scoped an access-request contact to licensing; `data_governance.accountable_organization` asserted MGH as the accountable steward; `ethical_reviews.reviewing_organization` carried a coined body name.
3. **Interpretive inflation (low–medium).** Three `addressing_gaps` entries converted project goals into claims about deficiencies in the wider field; two `known_limitations` were the record's own analysis; `known_biases[0].bias_type` was self-assigned; `regulatory_restrictions.confidentiality_level` mapped "controlled access" to an enum term without saying so.
4. **Precision and transcription hygiene (low).** `instances[1].counts` rendered a rounded magnitude as an exact integer without a caveat; one of the two column-order attributions in the garbled webinar table carried no local caveat; `status` held narrative rather than a state token; `external_resources[2]` gave a scheme-less URL without explanation.

The audit also confirmed a clean bill on several axes: no external registry identifiers, ORCIDs, RORs, or DOIs were supplied beyond the bundle; the misspelled MGH contact email was transcribed rather than silently corrected; tier ranking was applied correctly on both source conflicts; and a set of omissions (`doi`, `citation`, `version`, `license`, consent slots, size/count/compression/download slots) were verified as correct.

---

## 3. Changes made — full record

### 3.1 `creators` — role demotion (audit findings on `principal_investigator`)

Only the Rosenthal entry now populates `principal_investigator`, and its value is the plain string `Eric S. Rosenthal` with a `notes` line stating the NIH RePORTER attribution. The five leadership-team members (Bihorac, Jiang, Strekalova, Rashidi, Kwong) no longer populate `principal_investigator` at all: each entry now carries `affiliations` plus a `notes` line naming the person and citing the Bridge2AI CHoRUS Leadership Team slide, and a per-object `source_caveats` recording that the bundle names them as leadership rather than as PIs. The top-level `source_caveats` was rewritten to match and to add that the sources do not state these six individuals created the dataset.

### 3.2 `data_governance.accountable_organization` — removed

The `accountable_organization: {name: Massachusetts General Hospital}` object is gone from the reconciled full record. MGH's actual documented role (award recipient, program-management host) moved into `data_governance.notes`, and a new `data_governance.source_caveats` explains that no committee, review timeframe, appeal process, or accountable organization is described in the sources.

### 3.3 `license_and_use_terms.contact_person` — removed

The `contact_person: {name: Jared Houghtaling}` object is gone. Both access-request contacts remain in `notes` exactly as before, and a new `source_caveats` on the object states that the sources give these as access-request contacts rather than licensing contacts.

### 3.4 `ethical_reviews[0].reviewing_organization` — removed

The coined value `CHoRUS consortium ethics pillar` is gone. `review_details` is unchanged. The object's `source_caveats` was extended to say the sources do not name a reviewing body, so the field is left empty.

### 3.5 `addressing_gaps` — three entries reworded, caveats added

- Entry 1 now says the need "is described as a critical first step" rather than asserting it flatly.
- Entry 2 no longer opens "Existing resources lack…"; it states the harmonization requirement and the project's stated goal, with a `source_caveats` noting this is the project's goal rather than a documented deficiency.
- Entry 3 no longer asserts holdout sets "have been unavailable"; it states what the project provisions, with a caveat that prior unavailability is not asserted by the sources.
- Entry 4 no longer asserts contextual factors "are commonly absent from clinical datasets"; it states the project's commitment about its own data elements, with a matching caveat.

### 3.6 `known_limitations` — two entries softened

- The `representativeness_limitation` entry drops "rather than to general hospital or ambulatory care" from the description and moves that framing into a new `source_caveats` as this record's inference.
- The `temporal_limitation` entry drops "rather than prospectively designed measurements" and gains a `source_caveats` stating that the sources say only "Retrospective data collection" and the limitation framing is the record's own.

### 3.7 `known_biases[0].source_caveats` — strengthened

The caveat now opens by stating that no source names or categorizes any bias, and that the framing as a bias and the `selection_bias` assignment are this record's own analysis. The prior sentence about unmeasured statistics is retained.

### 3.8 `regulatory_restrictions` — caveat added

A new `source_caveats` states that the enum term `restricted` is this record's mapping of the sources' "controlled access" description.

### 3.9 `instances[1]` — rounding caveat added

A `source_caveats` was added stating that `1600000000` is the source's rounded "1.6 Billion" expressed in full and is not an exact count. The integer value itself is unchanged.

### 3.10 `subsets` — second column-order caveat added

The nursing-flowsheets subset gained an object-level `source_caveats` for the "OMOP schema with extensions" attribution (previously disclosed only in the top-level caveat), and the waveform-telemetry subset gained an equivalent caveat for the "PhysioNet schema extended" attribution (previously undisclosed at either level).

### 3.11 `status` — shortened

The three-sentence release-progress narrative was replaced by a single clause: released under controlled access while assembly continues toward the larger anticipated final dataset. The dropped detail (EEG extraction, imaging de-identification, size of the anticipated set) was already carried in `updates.update_details` and `known_limitations`, so nothing was lost.

### 3.12 `instances[3].notes` and `external_resources[2]` — transcription flags

The telemetry instance note now says "23 Tb of waveform data (unit transcribed as published)". The Bridge2AI program-page resource now quotes the source line as `"Website: www.bridge2ai.org/chorus" (transcribed as published, without a URL scheme)`.

### 3.13 `maintainers[0]` — typo flag inlined

The MGH program-manager entry now flags the published email as "transcribed exactly as published and apparently containing a typographical error in the domain," so the disclosure sits beside the address rather than only in the far-separated top-level caveat.

### 3.14 `existing_uses` and `external_resources` — list-valued `examples` / `external_resources`

In the original full record these inner fields held bare strings; in the reconciled record each is a one-item list. This aligns the shape with the multivalued declaration.

### 3.15 Top-level `source_caveats` — extended

Added: the dataset identifier is a minted fragment with no published anchor; the single `OTHER` term in `conforms_to_standard` stands for two distinct non-registered standards (OHNLP note schema, EDF+/Persyst) that the enum cannot distinguish, with the prose in `conforms_to` naming both; and an explicit list of verified-correct omissions (DOI, citation, version, license, consent documentation, file counts, total size, compression, download URL).

---

## 4. Changes made — core record

All fourteen substantive changes in §3 that apply to slots the core carries were applied identically to the core record: the `creators` demotion, removal of `accountable_organization`, removal of `license_and_use_terms.contact_person`, removal of `reviewing_organization`, the four `addressing_gaps` rewordings, the two `known_limitations` softenings, the strengthened bias caveat, the regulatory caveat, the rounding caveat on `instances[1]`, the two modality-level column-order caveats (now on `resources` entries), the shortened `status`, the transcription flags, the inlined maintainer typo flag, and the list-valued `examples` / `external_resources`.

Core-specific changes:

### 4.1 `acquisition_methods[0]` — core-only clause removed

The clause "The data are drawn from clinical systems rather than gathered directly from patients for research purposes." was deleted. The reconciled core `acquisition_methods[0].acquisition_details` is now word-for-word identical to the full record's.

### 4.2 `data_governance.notes` — core-only sentence removed

The sentence "The dataset is shared beyond the contributing consortium under controlled access, including with trainees provisioned compute on the Bridge2AI AI/ML for Clinical Care Collaborative Cloud." was deleted. Core `data_governance.notes` now matches the full record's, plus the MGH-role sentence added to both in §3.2.

### 4.3 `notes` — core-only sentence removed

The sentence about the holdout test set and the absence of a split-level slot was deleted. Core `notes` now matches the full record's exactly.

### 4.4 `source_caveats` — core-only sentence removed, minting note adjusted

The sentence "The nine standardized data modalities are carried in `resources` as component datasets." was deleted. The core `source_caveats` otherwise matches the full record's, with one deliberate difference: where the full record says the dataset identifier is a minted fragment, the core adds "the nine component modality identifiers are minted the same way," because the core carries those nine objects under `resources` and the disclosure belongs where the objects are.

---

## 5. What was left as-is, and why

### 5.1 `subsets` (full) vs `resources` (core) — divergence retained

The audit flagged as high severity that the core moved the nine modalities from `subsets` into `resources`, and that the two records now assign identical `id` values to objects of different declared classes (`DataSubset` in full, `Dataset` in core). **This was not changed.** The core record still uses `resources`; the full record still uses `subsets`. The nine identifiers are still shared across the pair.

The reason is that the core record is written against `data_sheets_schema_core_all.yaml`, and the schema digest supplied to this run covers the full `Dataset` class only. I cannot state from the digest whether `subsets` is declared on `CoreDataset`, and the instruction is explicit that a slot must not be reported as undeclared without digest support. Changing the core to `subsets` on an assumption would risk a validation failure; leaving it produces a documented, disclosed divergence. The consequence — one identifier denoting a `DataSubset` in one record and a `Dataset` in the other — is real and is recorded here rather than repaired.

Note also that the `is_data_split: false` / `is_subpopulation: false` flags present on every full-record `subsets` entry have no counterpart on the core `resources` entries, since those two fields are declared on `DataSubset` and not on `Dataset`.

### 5.2 `splits`, `direct_collection`, `third_party_sharing` — full-only, not added to core

These three slots remain present in the full record and absent from the core record. Their content was removed from the core's neighbouring slots (§4.1–4.3), so no fact is now core-only — the asymmetry runs the other way, with three facts full-only. The same digest limitation applies: I cannot confirm from the supplied digest that `CoreDataset` declares these slots, so they were not introduced. The structured values lost to the core are `direct_collection[0].is_direct: false`, `third_party_sharing[0].is_shared: true`, and the holdout-set `split_details`.

### 5.3 `instances[0].counts: 50000` — retained

The audit rated this medium, noting that pairing a 50,000 figure with an `instances` entry implies it is the dataset's instance count while the bundle also reports 45K+ admissions and 1.6 billion OMOP rows. The value is retained in both records because the tier-2 project documentation states it directly and the tier-4 webinar figure is recorded alongside it in the object's own `source_caveats`. The disagreement is disclosed at both the object and the record level; no better-supported value exists.

### 5.4 `data_collectors[*].role` free strings — retained

The digest constrains `role` to an enum on `Maintainer` only, not on `DataCollector`. The three values ("Data contributing site", "Site data manager", "Coordinating sub-team") are record-coined labels but violate no declared constraint and describe roles the bundle attests. Retained unchanged in both records.

### 5.5 `conforms_to_standard: OTHER` — single term retained

The audit noted that one `OTHER` stands for two distinct non-registered standards. The enum offers no way to distinguish them, and duplicating `OTHER` in the list would not add information. The list is unchanged; the ambiguity is now disclosed in the top-level `source_caveats` of both records, and `conforms_to` names both standards in prose.

### 5.6 `id` fragment minting — retained

`https://chorus4ai.org/#chorus-dataset` and the nine modality fragments are minted on the attested project URL, which is the prescribed treatment for labels with no referent outside the record. Retained; the fact that the fragments correspond to no published anchor is now disclosed in `source_caveats`.

### 5.7 Verified-correct omissions — retained

`doi`, `citation`, `version`, `license`, `total_size_bytes`, `total_file_count`, `compression`, `download_url`, `collection_consents`, `informed_consent`, `consent_revocations`, and `collection_notifications` remain absent from both records. The bundle states none of them. These omissions are now named explicitly in the top-level `source_caveats` so that their absence reads as a finding rather than an oversight.

---

## 6. Outcome

**Reconciliation outcome: converged with one documented divergence.**

- No fact appears in the core record that the full record does not carry (three core-only statements removed).
- Three structured slots remain full-only (`splits`, `direct_collection`, `third_party_sharing`), retained as a schema-uncertainty divergence rather than repaired by assumption.
- The nine modality objects are carried under `subsets` in the full record and `resources` in the core, with shared identifiers across differing classes — the one substantive structural divergence, disclosed above and in the core's `source_caveats`.
- Four unsupported assertions were removed outright (`accountable_organization`, licensing `contact_person`, `reviewing_organization`, five `principal_investigator` values).
- Nine slots gained or strengthened `source_caveats` disclosing inference, rounding, enum mapping, or column-order attribution.
- All prose in both records is American English; quoted source text, emails, and URLs are transcribed as published, including the misspelled MGH domain and the scheme-less Bridge2AI address.