# Reconciliation Report — CM4AI

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Subject record:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Version label:** 2026-08-31_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (declared input bundle only)
**Phase:** 4 — strict reconciliation of Phase 1 (full) and Phase 2 (core) against Phase 3 audit findings

---

## 1. Audit summary

Phase 3 returned **18 findings** against the full record: 1 high, 4 medium, 13 low. No fabricated dataset facts, no enum violations, and no prior-D4D reuse were detected. The findings clustered into five kinds:

1. **A semantically wrong scalar** — `publisher` pointing at the dataset's own DOI (high).
2. **Fidelity to source form** — an accented proper noun altered inside a quoted citation (medium).
3. **Internal inconsistency** — preprocessing and labeling strategies asserting processing of content the subject release states it does not contain (medium).
4. **Range and derivation defects** — a bare grant number in a `uriorcurie` slot, and byte counts derived by expanding rounded display strings inconsistently across siblings (medium).
5. **Under-specification, collapsed multivalued slots, inferred linkages, and supported omissions** (low, thirteen findings).

All 18 findings were addressed. Fourteen produced edits to both records; four were resolved by removal of the offending value rather than replacement; none was dismissed outright, though two were resolved differently from the audit's suggested remedy and one was resolved by omission where the audit offered a choice.

---

## 2. Changes made

### 2.1 High severity

**`publisher` — replaced (both records).**
Was `doi:10.18130/V3/HIGT4C`, the dataset's own DOI. Now `ROR:0153tk833`. The bundle attests the University of Virginia Dataverse as the distributing repository, and the June 2026 creator affiliations supply `ROR:0153tk833` for the University of Virginia — an identifier the evidence contains rather than one supplied from outside it. The slot's declared range is `uriorcurie`, and a ROR CURIE is the correct form.

### 2.2 Medium severity

**`citation` and `creators[Bélisle-Pipon JC].name` — accent restored (both records).**
The citation string and the creator entry both now read `Bélisle-Pipon JC`, matching all four Dataverse release records in the bundle. The American-English rule governs composed prose only; a quoted citation and a proper noun keep their source form. The same correction was applied to the `ethical_reviews` contact person, now `Jean-Christophe Bélisle-Pipon`.

**`preprocessing_strategies` and `labeling_strategies` — scoped, not removed (both records).**
Each of the four preprocessing entries and both labeling entries now opens with an explicit scope statement — "Project-level cell map construction pipeline, not applied to the contents of this release" / "Project-level cell map annotation, applied to computed cell maps rather than to the files in this release" — and each carries a new `source_caveats` naming the tier-3 `biorxiv_preprint` as the source and the tier-1 `june_2026_dataverse_release` statement that computed cell maps are not included. The audit offered scoping or omission; scoping was chosen because the pipeline is genuinely attested project material and its removal would lose evidence the bundle supplies, while the caveat removes the inconsistency the audit identified.

**`funders[0].grants[0].id` — removed, content relocated (both records).**
The grant object no longer carries an `id`. The award number `1OT2OD032742-01` now sits in `name`, with a new `description` identifying it. The bundle supplies no identifier scheme for NIH awards, and `id` is declared `uriorcurie` on every object in the digest, so a bare grant number there was a range defect.

**`file_collections[*].total_bytes` — removed throughout, sizes moved to prose (full record); `distributions[*].bytes` correspondingly removed (core record).**
All seven derived byte counts (113300, 135800, 171800, 93900, 30200, 73300, 1100000) were removed. Each collection's `description` now records the displayed size verbatim — "Dataverse displays the size as 113.3 KB", and so on — including the three GB-scale image collections that previously had no size recorded at all. This resolves both halves of the finding: the false precision and the inconsistent population across siblings.

### 2.3 Low severity

**`instances[0].data_substrate` — `B2AI_SUBSTRATE:19` → `B2AI_SUBSTRATE:56` (both records).** The vocabulary supplies "Immunofluorescence Image" as an exact match; the generic "Image" term was an approximation where a specific one exists.

**`instances[0].label_description` — removed; content moved to `notes` (both records).** `label` remains `false`. The four-channel composition is now carried in the instance's `notes`, together with the protein count.

**`instances[0].counts` — added, value 464 (both records).** Attested by the tier-1 October 2025 and tier-5 June 2025 release records for each MDA-MB-468 immunofluorescence collection. The `notes` states which collections the count applies to.

**`related_datasets` — one entry added (both records).** The second Related Publication, Nourreddine S et al., "A PERTURBATION CELL ATLAS OF HUMAN INDUCED PLURIPOTENT STEM CELLS", now appears as `is_described_by` / `doi:10.1101/2024.11.03.621734`, with the full author list and PMCID in `notes`.

**`version_access.versions_available` — split into five entries (both records).** Was one prose string enumerating four prior releases. Now one entry per release: June 2026 (2.0), October 2025 (2.1), June 2025 (2.1), March 2025 (1.4), and May 2024.

**`distribution_dates` — split into six entries (both records).** Was one merged blob. Now one entry per release event, including the separate 2026-07-15 publication of the image files within the June 2026 release.

**`ethical_reviews[*].review_details` — removed; `notes` added (both records).** The pointer-style text ("is identified in the release record as the responsibility of named ethics leads") is gone. Each entry now carries `contact_person` and a `notes` recording the contact email and stating explicitly that the bundle names no reviewing body, approval number or determination.

**`data_governance.committee_contact` — ORCID removed (both records).** Now `name: Jillian Parker` only. The bundle never equates "Jillian Parker (jillianparker@health.ucsd.edu)" with the creator "Parker J"; the ORCID linkage was inferred. The attested email is now recorded in `data_governance.notes`.

**`data_governance.accountable_organization` — removed (both records).** A new `data_governance.source_caveats` explains why: the bundle names no accountable organization, and neither the copyright statement nor the preservation commitment is an accountability assignment. Long-term preservation remains under `retention_limit`.

**`language: en` — removed (both records).** Unattested. The omission and its reasoning are recorded in the top-level `source_caveats`.

**`created_by` — added, value `Niestroy, Justin` (both records).** Attested as "Depositor: Niestroy, Justin". The third `maintainers` entry was correspondingly rewritten to drop the depositor claim; the two remaining programmatic contacts (Thaker, Sembay) were also split into separate entries rather than sharing one.

**`keywords` — `Medicine, Health and Life Sciences` added (both records).** Attested as the Dataverse Subject in all four release records. The `description` also now names it.

**`known_limitations[2].limitation_type` — `integration_limitation` → `temporal_limitation` (both records).** Embargo and incomplete final form are temporal conditions, not integration constraints. The enum offers no completeness term.

---

## 3. What was left as-is

Nothing was dismissed as unfounded. Three resolutions differ from what the audit proposed, and are recorded here as such rather than as unchanged:

- **Preprocessing and labeling** were scoped with caveats rather than omitted — one of the two remedies the audit offered.
- **File sizes** were moved to prose rather than simply omitted — the audit permitted either.
- **`data_governance.accountable_organization`** was removed rather than repointed. The audit noted the inference was unsupported and that the attested preservation statement sits elsewhere; no attested accountable organization exists in the bundle, so omission is the only faithful outcome.

Everything else in the record that the audit did not flag was carried through unchanged, including the referent choice (the June 2026 Dataverse release, not the project or the U2OS Nature dataset), the Sali affiliation conflict handling, the U2OS scope exclusion, and the project-level aggregate counts held out of slot values — all of which the audit assessed as correctly reasoned.

---

## 4. Core-record parity

Every change above was applied identically to the core record by re-projection from the reconciled full record. The core record's own header block was preserved verbatim, including `# Sources:` and `# Phase 4 reconciliation: completed`. The core record carries `distributions` where the full record carries `file_collections`; the `bytes` key was removed from all ten core distribution entries in step with the removal of `total_bytes` from the full record's collections, and the same prose sizes appear in the core descriptions.

`conforms_to_class` remains `CoreDataset` in the core record and `Dataset` in the full record; `conforms_to_schema` differs correspondingly. These are properties of each record, not of the data, and were left alone.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Slots populated | 62 | 59 |
| Validated against declared schema | yes | yes |
| Findings addressed | 18 / 18 | 18 / 18 |
| Unresolved findings | 0 | 0 |

Reconciliation outcome: **complete**. No finding was left standing; no change introduced a value the declared bundle does not support.