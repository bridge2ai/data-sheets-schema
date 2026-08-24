# CM4AI Reconciliation Report

**Project:** CM4AI (Cell Maps for Artificial Intelligence)
**Referent:** June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep2
**Phase:** 4 (strict reconciliation)

---

## 1. Audit summary as received

The audit returned 34 findings: 4 high, 12 medium, 18 low. All four high-severity findings concerned the core record. Three broad classes emerged:

1. **Phase-2 projection defects** — core stating content the full record did not, and core omitting content the full record carried.
2. **Scope drift on numeric values** — project-wide portal counters bound to narrower Instance objects, and a derived aggregate size stated in `description`.
3. **Range and structure defects** — objects placed in scalar-ranged slots, single objects carrying several distinct entities, and content routed into free text where a declared field existed.

The audit also confirmed several things as sound: single-referent scoping to the June 2026 release, tier-1 preference with local caveats on carry-overs, correct CURIE usage throughout, no fabricated external identifiers, and the one minted-identifier pattern (fragments on the release DOI) falling squarely inside the permitted case.

---

## 2. Changes made to the full record

### 2.1 `creators` — object placed in a scalar-ranged slot (not audit-raised; found during reconciliation)

**Before:** every Creator carried a nested `principal_investigator` object with `id`, `name` and sometimes `email`.

**After:** `principal_investigator` now holds the person's name as a string, and the ORCID has been lifted to the Creator object's own `id`.

**Why:** the digest declares `principal_investigator` with range `Person` in the object listing, but the v4 rule governs the *scalar* case and the schema's own validation rejected the nested form. The reconciled shape keeps every ORCID and every name; it moves the identifier to the slot that accepts it. No creator was dropped and no affiliation altered.

### 2.2 `data_governance.committee_contact` and `regulatory_restrictions.governance_committee_contact`

**Before:** nested Person objects with `name` and `email`.

**After:** strings — `Jillian Parker (jillianparker@health.ucsd.edu)`.

**Why:** same scalar-range correction. The audit's low finding on this slot (no `id` on the Person) is now moot in form but preserved in substance: a new `source_caveats` on `data_governance` records that the release gives only a name and email, that the author list carries `ORCID:0000-0003-4535-3486` for "Parker J", and that the two are deliberately not linked because no source states they are the same person.

### 2.3 `ethical_reviews[].contact_person`

**Before:** nested Person objects.

**After:** strings carrying name, ORCID CURIE and email — e.g. `Vardit Ravitsky (ORCID:0000-0002-7080-8801; ravitskyv@thehastingscenter.org)`.

**Why:** scalar range. Both ORCIDs are retained in CURIE form inside the string.

### 2.4 `distribution_dates[].release_dates` and `external_resources[].external_resources`

**Before:** single strings.

**After:** single-item lists.

**Why:** both slots are multivalued; the scalar form failed validation.

### 2.5 `instances` — portal counters removed (audit findings, medium)

**Before:** `counts: 53788` on the immunofluorescence Instance; `counts: 1374` on the AP-MS Instance.

**After:** both `counts` removed. Each Instance now carries a `source_caveats` explaining that the portal figure is a project-wide total spanning cell lines and releases, that the June 2026 release states no such count, and that the figure therefore cannot be attached to that instance type. The AP-MS caveat additionally notes that 1,374 is a "protein interactions" counter rather than a count of pull-downs.

**Why:** the audit was right that a caveat acknowledging the mismatch does not undo the mismatch. The numbers remain available in `description`, where they are correctly attributed to the portal and correctly scoped as project-wide.

### 2.6 `description` — derived aggregate removed (audit finding, medium)

**Before:** "distributed as ten ZIP archives totalling roughly 12.6 GB".

**After:** "distributed as ten ZIP archives" — the individual archive sizes are still given.

**Why:** the bundle states ten per-file sizes and no aggregate. The records elsewhere decline `total_size_bytes` precisely because the sizes are rounded; deriving and stating a rounded total contradicted that. The reasoning is now recorded in `source_caveats`.

### 2.7 `description` — tier-3 definition removed (audit finding, medium)

**Before:** "computed cell maps, hierarchical directed acyclic graphs whose nodes are protein assemblies resolved at increasing physical scale".

**After:** "Computed cell maps — the eventual product of the project — are not included in this release."

**Why:** the DAG definition comes from the preprint (tier 3) and was presented without the source flagging applied to comparable carry-overs. The fact that matters here — that computed maps are absent — is tier-1 and survives.

### 2.8 `total_file_count` added (audit finding, low)

**Added:** `total_file_count: 10`.

**Why:** the audit correctly observed that the rounded-size argument justifies omitting `total_size_bytes` but not the file count. The release page states "1 to 10 of 10 Files" directly. `total_size_bytes` remains omitted, and `source_caveats` now separates the two reasons.

### 2.9 `publisher` removed (audit finding, medium)

**Before:** `publisher: ROR:0153tk833`.

**After:** slot omitted; `source_caveats` explains that the bundle attests the University of Virginia Dataverse as hosting repository and depositing institution but never as publisher, and that the release's own copyright statements assign rights to the Regents of the University of California and to Stanford.

**Why:** the ROR was attested in the bundle only as an author affiliation string. Asserting a publishing role from a hosting relationship is inference.

### 2.10 `external_resources` — collapsed objects split (audit findings, low ×2)

**Before:** four MassIVE deposits in one object; three software resources in another.

**After:** four separate MassIVE objects (SEC-MS KOLF2.1J; SEC-MS MDA-MB-468; AP-MS paclitaxel; AP-MS vorinostat), each with its own caveat about the unexposed URL. Three separate software objects (Cell Mapping Toolkit; FAIRSCAPE; IMP), each with its own URL and license. The SRA and Figshare deposits, previously combined, are also now separate, as are the two related publications.

**Why:** the v2 rule requires one object per distinct entity. The software resources were individuable by URL and license; the MassIVE deposits are individuable by content even though no accession is exposed.

### 2.11 `existing_uses` — content moved from `notes` to `examples` (audit finding, low)

**Before:** all three objects populated only `notes`.

**After:** all three populate `examples` instead. Content is unchanged apart from adding the PMCID to the perturbation-atlas citation.

**Why:** v3 rule — where the evidence answers a declared field, populate that field.

### 2.12 `errata` removed; content relocated (audit finding, low)

**Before:** an Erratum describing the June 2025 release revision, with a caveat saying no errata apply to June 2026.

**After:** `errata` omitted entirely. The June 2025 revision now appears in two places where it belongs: as part of the `related_datasets` description for `doi:10.18130/V3/F3TD5R`, and in `version_access.version_details`, with a `version_access.source_caveats` noting it is sibling-version history rather than a correction to this dataset.

**Why:** `errata` is scoped to errors in *this* dataset. Another release's correction is version history.

### 2.13 `other_tasks` added (audit finding, high — projection direction reversed)

**Added:** the Cell Mapping Toolkit OtherTask that core had stated and full had not.

**Why:** the content is grounded in the bundle (the Nature paper describes the toolkit as "a flexible and generalizable framework"). The divergence was resolvable in either direction; adding to full was the better answer because the fact is real.

### 2.14 Smaller corrections

- `subpopulations[0].distribution`: "Black female" → "black female", matching the preprint's own wording, with the caveat now stating that the description is reproduced in the source's wording.
- `preprocessing_strategies[0].source_caveats`: "applied to these input data streams" → "to be applied to these input data streams", removing the implication that the pipeline had already run on the deposited files.
- `regulatory_restrictions`: new `source_caveats` distinguishing the `unrestricted` level (true of the ten Dataverse files) from the dataset as a whole (two embargoed external deposits; a Data Access Committee).
- `is_deidentified`: new `source_caveats` noting that the boolean reflects the release's unqualified statement while the preprint's supporting statement is hedged.
- `collection_timeframes[0].source_caveats`: extended to say no source states per-modality acquisition windows.
- `instances[2].source_caveats`: extended to explain why the general Mass Spectrometry Data substrate term is used for AP-MS where SEC-MS gets a specific one.
- `creators[].credit_roles`: still not populated; the reason is now stated in the top-level `source_caveats` — the preprint's contributions breakdown covers a partially overlapping author set, so no role can be assigned without inference.
- Top-level `source_caveats`: rewritten to carry the reasoning for the ROR asymmetry, the `publisher` omission, the counter placement, and the two distinct file-count/size decisions.

---

## 3. Changes made to the core record

### 3.1 `informed_consent.consent_obtained` removed (audit finding, high)

**Before:** `consent_obtained: false`.

**After:** the boolean is gone. `consent_documentation` and `source_caveats` remain; the caveat now states that no source says whether donor consent was or was not obtained by the originating repositories, so no consent status is asserted.

**Why:** this was the most serious finding. The bundle states that no human subjects are involved — which is not the same as stating that consent was not obtained. The original caveat tried to rescue the boolean by glossing it ("recorded as false because no consent was sought"), but a reader consuming the field rather than the prose would read a false claim.

### 3.2 `informed_consent` retained alongside full's `collection_consents` (audit finding, medium — partially accepted)

The audit asked that core use the same slot the full record uses. Core retains `informed_consent`; full retains `collection_consents`. Both now carry equivalent content and equivalent caveats, and neither asserts a consent status.

**Why left as-is:** the two schemas are not identical, and the projection is content-faithful even where the slot name differs. Having removed the offending boolean, the residual difference is one of slot choice rather than of claim.

### 3.3 `distributions` retained (audit finding, high — not accepted)

The audit flagged `distributions` and its `md5` members as absent from the supplied schema digest and predicted validation failure.

**Left as-is.** The core record validated against `data_sheets_schema_core_all.yaml` with `distributions` present. The digest supplied to this run describes the **full** `Dataset` class; it is not a listing of the core schema's slots, and its silence about `distributions` is therefore not evidence that the core schema lacks it. The audit's inference was reasonable from what it had, but the validator is the authority and it accepted the slot.

One change was made inside it: `conforms_to_standard: RO_CRATE` on the release-metadata entry became a single-item list, matching the slot's multivalued declaration.

### 3.4 `file_collections` — still not in core (audit finding, high — not accepted as stated)

The audit asked that core carry `file_collections` as full does. It does not. Core carries the same per-file content through `distributions`, which the core schema accepts and which is the shape the core schema appears to intend for this material. The minted fragment identifiers and `collection_type` terms are full-record structure; core expresses paths, formats, checksums and descriptions instead.

**Why left as-is:** the two records are not required to use identical slots where their schemas differ. The information a reader needs — which file, what it holds, how to verify it — is present in both.

### 3.5 `other_tasks` (audit finding, high — resolved in full)

Core's `other_tasks` is unchanged. The divergence was resolved by adding the entry to the full record (§2.13), not by deleting it from core.

### 3.6 Core omissions the audit raised (medium ×4)

- **`relationships`** — still absent from core. Full carries it.
- **`third_party_sharing`** — still absent from core. Full carries it.
- **`citation`** — still absent from core. Full carries it.
- **`collection_consents`** — still absent from core; the equivalent content sits in `informed_consent` (§3.2).

**Why left as-is:** these are core-schema scope decisions rather than factual divergences. Nothing core states contradicts full, and nothing the bundle supports has been lost from the pair taken together. Had core *asserted* something full denied, that would be a defect; a shorter record is not.

### 3.7 Changes mirrored from full

Every substantive change in §2 that touches a slot core also carries was applied identically: the `creators` restructuring, the two governance-contact strings, the `ethical_reviews` contact strings, the `distribution_dates` and `external_resources` list forms, the two `instances` counter removals, the `description` edits, the `publisher` removal, the `external_resources` splits, the `existing_uses` move to `examples`, the `errata` removal with relocation to `related_datasets` and `version_access`, the "black female" wording, the preprocessing tense, and all the added or extended caveats.

Core does **not** carry `total_file_count`; that slot was added to full only.

Core's top-level `source_caveats` was rewritten in parallel with full's, with one addition specific to core: a note that the ten per-file sizes are not summed because the repository states no aggregate.

---

## 4. Findings left as-is, with reasons

| Finding | Severity | Reason |
|---|---|---|
| `distributions` / `md5` not in digest | high | Core validated with the slot present. The digest describes the full class, not the core class. |
| `file_collections` omitted from core | high | Core expresses the same per-file content through `distributions`; slot choice differs, content does not. |
| `informed_consent` vs `collection_consents` slot mismatch | medium | Content and caveats now equivalent; neither asserts a consent status. |
| `relationships`, `third_party_sharing`, `citation` absent from core | medium | Core-scope decisions; no contradiction with full. |
| ROR on UVA affiliations only | medium | Reflects the source exactly. Now explained in `source_caveats`; adding RORs from outside the bundle would violate the identifier rule. |
| `funders[].grants` carrying only `name` | low | The digest does not expose Grant's declared keys, so no structured home for the award amount or period exists. Both remain in `source_caveats`. |
| `collection_timeframes` without `start_date` / `end_date` | low | RePORTER dates describe the award period. The caveat now also records that no per-modality windows are stated. |
| `conforms_to_standard` listing only `RO_CRATE` | low | JSON-Schema, EVI and PROV-O have no enum term; `OTHER` would lose more than it gains. `conforms_to` prose names all three. |
| `sensitive_elements_present: false` | low | Grounded in the release's explicit governance statements; the inference is flagged locally. |
| `is_deidentified.identifiable_elements_present: false` | low | Reflects the release's unqualified statement; the preprint's hedge is now noted in a new caveat. |
| `preprocessing_strategies` describing an unapplied pipeline | low | The pipeline is the project's stated workflow for these streams; the caveat now uses "to be applied". |
| `maintainers` using free-text only | low | Maintainer declares no structured person fields. Schema limitation. |
| `instances[].data_substrate` asymmetry | low | No AP-MS-specific term exists. Now explained in a caveat. |
| `related_datasets[3]` May 2024 DOI from tier 3 | low | The DOI is attested in the bundle; the caveat records its provenance. |
| Minted `file_collections` ids | low | Permitted minting case: parts of this dataset, anchored to the attested release DOI. |
| `creators[].credit_roles` unpopulated | low | Preprint contributions cover a partially overlapping author set. Reason now stated in `source_caveats`. |

---

## 5. Outcome

Both records validated after reconciliation:

- Full: `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — passed.
- Core: `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — passed.

The single-referent choice is unchanged: this pair describes the June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`, with earlier releases as prior versions and the U2OS Nature dataset as a related external resource, not merged.

No unsupported claim was added. Three claims were withdrawn (`publisher`, the two Instance counters), one boolean was withdrawn (`consent_obtained`), one derived figure was withdrawn (12.6 GB), and one directly attested figure was added (`total_file_count: 10`).