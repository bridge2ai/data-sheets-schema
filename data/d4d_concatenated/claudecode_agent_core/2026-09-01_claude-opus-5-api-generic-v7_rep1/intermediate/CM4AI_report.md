# CM4AI D4D Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Version label:** 2026-09-01_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (input documents only)
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`

---

## 1. Summary of the audit

The Phase 3 audit returned 26 findings: 7 high, 10 medium, 9 low. It found no fabricated dataset facts. The referent selection (June 2026 release, following the manifest's `SUPERSEDED BY` ranking over the October 2025 release) was confirmed as correct, as was the resolution of the 464-vs-563 imaged-protein conflict toward the higher-ranked source, and the decision to hold the Nature U2OS cell map apart from the CM4AI releases.

The substantive problems were structural rather than factual: invented object keys that would fail validation, minted person identifiers with real-world referents, and inconsistent identifier form for the same object within one record.

---

## 2. Changes made

### 2.1 Invented keys removed (high)

**`instances[*].instance_details`** — The schema digest lists Instance's accepted keys as `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats` (plus `id`, `used_software`). `instance_details` is not among them. In all three Instance objects the key was removed and its content folded into `notes`, which the digest does declare. Where an Instance already carried a `notes` value (the imaging instance), the two texts were merged into a single `notes` string.

**`funders[*].grants`** — The digest gives no accepted-key list for `Grant`, so `grant_number` and `grant_title` could not be verified. Rather than guess at Grant's shape, all three `grants` lists were removed entirely and the award numbers and titles moved into `funders[*].notes`, which FundingMechanism does declare. Nothing was lost: award 1OT2OD032742-01 and its title, 5U54HG012513-02 and its title, and the Frederick Thomas Fund all still appear, now as prose in `notes`. The first funder's `notes` was expanded to carry the RePORTER detail (application ID, project number, PI, organization, period, amount) that previously sat partly in the Grant object.

**`Person.email`** — The digest gives no accepted-key list for `Person`. Four Person objects carried `email`. In every case the key was removed and the address preserved in a `notes` value on the *parent* object, which does declare `notes`:

| Location | Address preserved in |
|---|---|
| `ethical_reviews[0].contact_person` | `ethical_reviews[0].notes` |
| `ethical_reviews[1].contact_person` | `ethical_reviews[1].notes` |
| `data_governance.committee_contact` | `data_governance.notes` |
| `license_and_use_terms.contact_person` | `license_and_use_terms.notes` |

`regulatory_restrictions.governance_committee_contact` also carried `email`; the key was removed there and the address was not restated, since it is identical to the one already recorded in `data_governance.notes`.

**`Organization.name`** — The audit flagged this as unverifiable against the digest, affecting ~45 affiliation objects. It was **left unchanged**. Removing `name` from every affiliation would strip the only content those objects carry and would leave affiliations that are empty or, worse, identified only by ROR where a ROR was available and absent entirely where it was not. The finding is recorded here as an open uncertainty rather than acted on. If `Organization` does not in fact declare `name`, validation will catch it; the record was validated before completion.

### 2.2 Minted person identifiers removed (high)

Nine creators without an ORCID in the bundle had carried fragment identifiers minted on the dataset DOI landing URL — Axelsson, Chinn, Fall, Johannesson, Khaliq, Muralidharan, Pan, Polacco, Zhang. A person has a referent outside this record, so under the v5 rule the identifier must come from the evidence or be omitted; the bundle supplies none for these nine. Nothing in the record pointed at the fragments either, so they were not functioning as labels. All nine `id` values were removed; each creator now carries `name` and `affiliations` only.

### 2.3 Grant landing-page identifier removed (high)

`funders[0].grants[0].id` had held `https://reporter.nih.gov/project-details/11211616` — a project page used as the identity of a grant entity. This disappeared with the removal of the `grants` lists (§2.1). The application ID 11211616 is now stated as prose in `funders[0].notes`, where it is a transcribed fact rather than an asserted identity.

### 2.4 Identifier form made consistent (medium)

**Record `id`** — changed from `https://doi.org/10.18130/V3/HIGT4C` to `doi:10.18130/V3/HIGT4C`. The resolver form created two identities for one object, since `version_access.latest_version_doi` and every `related_datasets[*].target_dataset` already used the `doi:` CURIE. The `doi` slot, whose range is `string` and whose description calls for the bare DOI, retains `10.18130/V3/HIGT4C` unchanged.

**`publisher`** — changed from `https://dataverse.lib.virginia.edu` (a bare hostname identifying no registered entity) to `ROR:0153tk833`, the University of Virginia identifier already attested in the bundle and already used in four creator affiliations.

**`file_collections[*].id`** — all ten fragment identifiers were rebased from `https://doi.org/10.18130/V3/HIGT4C#…` to `doi:10.18130/V3/HIGT4C#…`, so that parts of the dataset hang off the same form of the dataset identifier the record now uses at top level.

### 2.5 Inferred timestamps and attributions withdrawn (medium)

**`last_updated_on`** — removed. The value `2026-07-15T00:00:00Z` had been derived from the file-level publication date of the three immunofluorescence archives. The bundle presents that as a per-file publication date, never as a dataset-level modification date. The omission is disclosed in `source_caveats`.

**`created_by`** — removed. It had held `Niestroy, Justin`, transcribed from the Dataverse *Depositor* field. The bundle distinguishes Depositor from Author and from Point of Contact, and names no single primary creator. The depositor is recorded in `source_caveats` instead, with the reason for the omission.

**`collection_timeframes`** — removed. The single entry had set `start_date: 2025-02-27` by reusing the Dataverse "Data Creation Date". That field is a deposit-metadata value carried unchanged across four distinct releases in the bundle; it does not mark a collection boundary. The bundle states no collection start or end for the underlying experiments. Disclosed in `source_caveats`.

### 2.6 Over-precise byte counts removed (low)

Seven `file_collections[*].total_bytes` values had been back-computed from Dataverse's rounded human-readable sizes (113.3 KB → 116019, and so on). All seven were removed. The human-readable size the bundle actually displays is retained in each collection's `description`, where it already appeared. `total_size_bytes` remains omitted; the reason is now stated in `source_caveats` rather than left implicit.

### 2.7 Count/slot mismatch corrected (low)

`instances[2].counts: 11739` was removed. 11,739 is the number of *targeted genes* in the CRISPRi atlas, not a count of instances of that type. The figure remains in `notes`, with an explicit statement that the bundle gives the gene count and not the number of profiled cells.

### 2.8 Slots added on the audit's prompting

Three findings identified evidence the record was carrying inconsistently or not at all:

**`acquisition_methods[2].was_validated_verified: true`** with a `notes` recording that antibody quality was scored per the standard Human Protein Atlas protocol. The audit noted this was arguably supported and had been left unset.

**`cleaning_strategies`** — added, with one entry recording that CRISPR screen data were reported as undergoing quality control at the time of the CM4AI preprint. The audit observed that omitting this while populating `preprocessing_strategies` from the same methods material was inconsistent.

**`subsets`** — added, with seven DataSubset entries covering the three MDA-MB-468 conditions and the four KOLF2.1J cell states. The audit noted that `subsets` is the slot whose description names logical partitions, and that the condition structure was represented only through `subpopulations` and `file_collections`. Each carries a minted fragment on the dataset DOI; unlike the creator fragments, these name parts of *this* dataset and so fall under the minting rule rather than the evidence rule.

### 2.9 `related_datasets` restructured (high, flagged for review)

The audit observed that each DatasetRelationship carried a `description` describing the *target* dataset rather than the relationship, while the target was already identified by `target_dataset`. In the reconciled record each entry now carries `name` holding the target's title, with `notes` used for the one entry needing extra commentary (the May 2024 release, referenced only in the preprint's availability statement). The two bioRxiv entries now carry the article titles under `name` rather than full citations under `description`.

### 2.10 `notes` folded into `description` (low)

The dataset-level `notes` had held the project's three-pillar / six-module organization and the collaborating institution list. Under #385, `notes` is for residual content after `description` and the structured slots are used. That text now closes the `description` and the `notes` slot is gone.

---

## 3. Findings left as-is

**`Organization.name` (high).** Discussed at §2.1. Left unchanged, as removal would empty ~45 affiliation objects on an unverified inference about the schema.

**`conforms_to` / `conforms_to_standard` = RO-Crate (medium).** Unchanged. The audit accepted this as supported and noted only that RO-Crate describes packaging rather than content. The bundle names no imaging or waveform content standard, and the record correctly claims none.

**`total_size_bytes` omitted (medium).** Unchanged as a decision; only the disclosure moved, from an implicit note to explicit text in `source_caveats`.

**`creators[*].credit_roles` (medium).** Unchanged — still absent. The audit itself judged omission defensible: the bundle assigns CRediT roles for neither the CM4AI release nor its author list.

**`status: Beta` (low).** Unchanged. "Beta" appears verbatim in the release title, so the value is attested even though it mixes release maturity with publication status.

**`created_on: 2025-02-27T00:00:00Z` (low).** Retained, with a `source_caveats` note added recording that the same date is carried unchanged across four release records in the bundle and is unlikely to be specific to this release's content. The audit asked for a caveat rather than removal.

**`language: en` (low)** and **`is_tabular: false` (low).** Both retained. Each is an inference rather than an attested fact; both are now disclosed as inferences in `source_caveats`.

**`download_url` omitted (low).** Unchanged. The bundle supplies only an incomplete API access pattern, so omission remains correct.

**`source_caveats` length and placement (low).** Partly addressed rather than fully. The image-count conflict moved out of the dataset-level caveat and onto `instances[0].source_caveats`, where it belongs. The byte-size commentary was rewritten but stayed at dataset level, since it now concerns an omission spanning all ten collections rather than any one of them.

**`keywords` synonym pairs (low).** Unchanged. The list is a faithful transcription from Dataverse; the redundancy is inherited, and editing it would depart from the source.

**`annotation_analyses` omitted (low).** Unchanged. The GPT-4 naming-reproducibility analysis belongs to the Nature U2OS work; the scoping decision recorded in `source_caveats` holds.

---

## 4. Core record

The core record was re-derived by projection from the reconciled full record. Every change above propagates: the nine creator `id` values are gone, the `grants` lists are gone with award detail in `funders[*].notes`, `Person.email` keys are gone with addresses in parent `notes`, `distributions[*].id` use the `doi:` fragment form with `bytes` removed, `id` and `publisher` use CURIEs, `created_by` / `last_updated_on` / `collection_timeframes` / `notes` are absent, `cleaning_strategies` is present, and `description` and `source_caveats` match the full record's text.

Two core-only differences are deliberate. `conforms_to_class` is `CoreDataset` and `conforms_to_schema` names the core schema path, per the core header block. `subsets` does not appear in the core record; the core schema's `distributions` carries the file-level structure and the condition partitioning remains represented through `subpopulations`.

---

## 5. Outcome

All seven high findings were acted on except `Organization.name`, which is recorded as an open uncertainty about the schema digest rather than the record. All medium findings concerning identifier form and unsupported inference were acted on. Low findings were acted on where they concerned precision or slot fit, and disclosed in `source_caveats` where they concerned inference that remains in the record. No factual content was added that the bundle does not attest; the net effect is a record with fewer asserted identities, fewer derived numbers, and fuller disclosure of what it inferred.