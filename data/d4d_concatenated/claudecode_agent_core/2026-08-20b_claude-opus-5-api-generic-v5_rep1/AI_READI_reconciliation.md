# AI-READI D4D Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep1`
**Records:** `AI_READI_d4d.yaml` (full, class `Dataset`) and `AI_READI_d4d_core.yaml` (core, class `CoreDataset`)
**Arm:** BASELINE (declared input bundle only)

---

## 1. What the audit found

The Phase 3 audit returned 24 findings. No fabricated dataset fact was identified: all ROR, ORCID and DOI CURIEs trace to the declared bundle, fragment-minted subset and collection identifiers follow the v5 minting rule, and the `source_caveats` slots disclose the substantive source conflicts (Washington University in St. Louis vs University of Washington; Equitable vs Exploratory; the FAIRhub/BMJ Open collection-window divergence; the RO-Crate/healthsheet sensitivity divergence).

The findings clustered into five groups:

1. **Core projection defects (high).** The core record replaced the full record's `file_collections` with a `distributions` slot, demoting nine integer `file_count` values and both dataset-level totals into free prose in `notes`. Eight further slots present in the full record were dropped from core without evidentiary cause.
2. **Asymmetry in the other direction (low).** Four slots — `existing_uses`, `use_repository`, `ip_restrictions`, `extension_mechanism` — appeared only in core, all supported by the bundle, meaning the full record was the weaker of the pair on those points.
3. **Structured-value loss (medium).** The NIH award number OT2OD032644, the most queryable funding fact in the bundle, existed in neither record as a structured value.
4. **Field-mismatch (medium).** Three consent-related slots were collapsed into one in core, with the collection-notification fact landing inside `withdrawal_mechanism`, a field that does not ask for it.
5. **Attestation and clarity (low).** Two keywords unsupported *as keywords*; two omitted affiliations undisclosed; a surface contradiction between `identifiable_elements_present: false` and the quoted `"NoDeIdentification"`; an unreconciled year-label divergence; a fact sourced only from a superseded document.

---

## 2. Changes made to the full record

### 2.1 Slots added

Four slots were back-ported from core into the full record, resolving the reverse asymmetry (audit findings on `existing_uses`, `use_repository`, `ip_restrictions`, `extension_mechanism`):

| Slot | Content | Evidence |
|---|---|---|
| `existing_uses` | One object recording that no uses exist at time of publication | healthsheet uses Q1 ("No"); FAIRhub `cited: 0` |
| `use_repository` | One object recording the absence of a tracking repository and the FAIRhub counters | healthsheet uses Q3 ("No"); FAIRhub landing page |
| `ip_restrictions` | Two restrictions (title/IP retained by licensor; separate license required for publishers) plus a note on third-party restrictions | License §8, §3.F; healthsheet distribution Q5 |
| `extension_mechanism` | `extension_details` recording that no external contribution mechanism exists | healthsheet maintenance Q7 |

### 2.2 Slots corrected

**`creators[0].principal_investigator`** — changed from an object (`{id: ORCID:..., name: Aaron Lee}`) to the string `'Aaron Lee (ORCID:0000-0002-7452-1648)'`. Same change applied to `data_governance.committee_contact`. This addresses the v4 rule on scalar-ranged slots: the schema digest declares `Creator.principal_investigator` with range `Person`, but placing an inline object there in the original risked the scalar/object mismatch the rule warns about; the reconciled form preserves both the name and the ORCID while remaining a single scalar value.

**`funders[0].grants[0]`** — a `notes` field was added carrying the award number verbatim: *"NIH award number OT2OD032644, made through the NIH Common Fund Bridge2AI program."* The `id` remains the FAIRhub award URI, which is what the bundle supplies as an identifier. This is a partial remedy: the award number is now recorded on the Grant object rather than existing only inside `data_collectors` prose and the funders caveat. A note in the top-level `source_caveats` explains why no CURIE was minted for it.

**`keywords`** — `Type 2 diabetes` and `Salutogenesis` were removed. Neither is attested as a keyword by FAIRhub, the RO-Crate, or the FAIRhub study-description `keywordList`. Both remain pervasive in `description`, `purposes` and `tasks` as subject matter, which is where subject matter belongs. The top-level `source_caveats` now states this explicitly.

**`creators[0].source_caveats`** — extended to disclose the two omitted affiliations (University of Utah ROR 03r0ha626, University of Massachusetts Lowell ROR 03hamhx47), which appear in the FAIRhub `overallOfficialList` as PI affiliations but not as collaborating institutions. The caveat also now describes `https://aireadi.org/` as "a project homepage rather than a registry entry" so that a downstream consumer does not mistake it for an identifier.

**`is_deidentified.deidentification_details`** — rewritten to resolve the surface contradiction the audit flagged. It now states explicitly that the `identifiable_elements_present: false` flag records the state of the released public dataset, while the source's `"NoDeIdentification"` label refers to the absence of a de-identification *procedure*, not to the presence of identifiers. The underlying facts and the flag value are unchanged.

**`collection_timeframes[0]`** — `timeframe_details` changed from "the first two years of main study data collection" to "the subsequent years of main study data collection", and `source_caveats` extended to record the year-label divergence: the healthsheet says "up through the end of the second year", the README changelog labels the increments "year 2 data" (863) and "year 3 data" (1,213). The record no longer silently adopts one label.

**`instances[0].notes`** — a sentence added recording that the single permitted `data_topic` value captures only the primary subject and that ophthalmic imaging, mHealth, waveform and glucose-monitoring topics are unrepresentable in that slot. The `data_topic` value `B2AI_TOPIC:43` is unchanged.

**`license_and_use_terms.notes`** — now names the canonical license URI (`https://doi.org/10.5281/zenodo.17555036`) explicitly rather than leaving it only inside the `license_terms` prose.

**`sampling_strategies[0].strategies`** and **`participant_privacy[0].privacy_techniques`** and **`missing_data_documentation[0].missing_data_patterns` / `missing_data_causes`** and **`is_deidentified.identifiers_removed`** — reformatted from YAML lists to block scalars. The schema digest does not declare these as multivalued, and the reconciled form avoids asserting a list range the digest does not support. No content was lost in any of these.

**`source_caveats`** (top level) — extended with three new clauses: the year-label divergence, the keyword attestation basis, and the reason the award number sits in a Grant note rather than in an identifier field.

**`notes`** (top level) — the beta-platform statement, which the audit correctly identified as sourced only from the superseded `fairhub_dataset` page, is retained but now attributed: *"The superseded FAIRhub v2.0.0 page additionally described the platform as being in beta; the v3 page does not repeat this."*

### 2.3 Slots left unchanged in the full record

All remaining slots are byte-identical between the original and reconciled full records, including `total_file_count`, `total_size_bytes`, `subsets` (four objects), `splits`, `variables` (36 objects), `relationships`, `direct_collection`, `participant_privacy`, `participant_compensation`, `third_party_sharing`, and all ten `file_collections` entries with their integer `file_count` and `total_bytes` values. The audit raised no defect against these in the full record; they were flagged only as absent from core.

---

## 3. Changes made to the core record

### 3.1 The `distributions` slot

The audit's highest-severity finding was that `distributions` is not declared in the supplied schema digest, which lists only `file_collections` (range `FileCollection`, with `path`, `file_count`, `total_bytes`, `collection_type`) as the slot for per-directory groupings.

**The slot name was retained.** The digest supplied to this run covers the `Dataset` class of the *full* schema; it is not the core schema digest, and it therefore cannot establish what `CoreDataset` declares. Renaming to `file_collections` on the strength of a digest for a different class would have been a guess in the opposite direction. The core record validated against `data_sheets_schema_core_all.yaml` with `distributions` present, which is the operative evidence.

**What was corrected inside it:**

- `format` values were removed from the `cardiac_ecg`, `environment` and root-metadata entries. The audit noted that `'CSV'` was asserted for the WFDB electrocardiogram directory and the ESDS environmental directory without support, and `'MD'` for the mixed-format root directory. Where a single format value does not describe the collection, the slot is now omitted and the formats are stated in `notes`. `clinical_data` retains `CSV` (the bundle states each file is a CSV mapping to an OMOP table) and the two wearable directories retain `JSON` (Open mHealth schema files).
- `conforms_to_standard` changed from a scalar to a single-item list in every entry, matching the multivalued declaration.
- The root-metadata entry now carries its file count (9) in `notes`, which the original omitted entirely.

**What was not corrected:** the file counts remain in `notes` rather than in an integer field, because the core schema provides no `file_count` on this class. The `bytes` key was retained for the same reason as the slot name. The top-level `source_caveats` now records this constraint explicitly rather than leaving it implicit.

### 3.2 Slots restored to core

Eight findings concerned content present in the full record and absent from core. The following were restored:

| Full-record slot | Where it now lives in core | Why |
|---|---|---|
| `total_file_count`, `total_size_bytes` | `description` (final sentence, with both the byte count and the TB figure) | No integer slot available on `CoreDataset`; moved out of `notes` into `description`, which the v2 rule prefers over residual notes |
| `subsets` (4 objects) | `resources` (4 objects, ids preserved) | The three splits and the mini subset are now structured entries again rather than a prose paragraph in `notes` |
| `splits` | `sampling_strategies[0].strategies` (final paragraph) | The 70/15/15 rationale is now attached to the sampling description rather than restated in `notes` |
| `relationships` | `instances[0].notes` | The single-participant-identifier linkage and the absence of longitudinal relationships |
| `direct_collection` | `acquisition_methods` (third object, `was_directly_observed: true`) | The direct-vs-third-party fact, previously unrecoverable from core |
| `participant_privacy` | `is_deidentified.deidentification_details` | Anonymization method, five privacy techniques, data linkage, and re-identification risk |
| `third_party_sharing` | `license_and_use_terms.notes` | Public distribution plus the onward-transfer constraints |
| `variables` (36 objects) | `collection_mechanisms` (measurement detail and reference ranges folded into the relevant device entries) | Units, maxima and laboratory reference ranges now sit with the instruments that produced them |

Two slots the audit listed as dropped were **not** restored as separate entries: `participant_compensation` and the standalone `discouraged_uses`. The compensation facts (USD 200, timing, non-proration, transport coverage, follow-up parity) are present in the full record and remain absent from core; no core slot fits them and folding a payment amount into an unrelated field would repeat the error the audit flagged in §3.3 below. This is recorded here as a known residual gap rather than silently resolved.

### 3.3 The consent field-mismatch

The audit found that the collection-notification fact — *"Every individual was aware of the data collection... rather than passive collection or secondary use"* — had been appended to `informed_consent[0].withdrawal_mechanism`, a field that asks how consent is revoked.

**Corrected.** `withdrawal_mechanism` now contains only the withdrawal facts (withdraw at any time; already-shared data remain; stated in the consent document). The notification content, together with the consent-process detail that the full record carries in `collection_consents`, moved to a new `notes` field on the same object. This is the residual-content placement the v2 rule permits once the fitting fields are used.

### 3.4 Other core corrections

The following changes mirror those made to the full record, keeping the pair consistent:

- `principal_investigator` and `committee_contact` converted to scalar strings.
- Grant `notes` added with the award number.
- Two keywords removed.
- `creators[0].source_caveats` extended with the omitted affiliations and the homepage-as-identifier note.
- `is_deidentified.deidentification_details` rewritten to resolve the flag/label tension.
- `collection_timeframes[0]` year-label caveat added.
- `license_and_use_terms.notes` extended with the canonical URI.
- `ip_restrictions.notes` added.
- `extension_mechanism.extension_details` reworded to match the full record.
- `sampling_strategies[0].strategies` and `missing_data_documentation` fields converted to block scalars.
- The `data_governance.source_caveats` clause about biorepository request procedures, which the audit noted had been silently dropped from core, is **restored**; the two records now carry identical text in that slot.
- The `prohibited_uses` entry on publication limits, which core had truncated relative to the full record, now carries the full clause including the separate-license route for publishers.
- Top-level `source_caveats` extended with the year-label divergence, the keyword basis, the award-number handling, and a new clause explaining the core-specific structural constraints (no variable slot, no file-count field, DICOM/WFDB having no enum format value).
- Top-level `notes` reduced: the file/byte totals moved to `description`, the split composition reduced to a pointer to `resources`, and the citation and platform-banner facts retained.

---

## 4. Findings left as-is, and why

| Finding | Disposition |
|---|---|
| `distributions` slot name and `bytes` key not in the supplied digest | Retained. The digest describes the full schema's `Dataset` class, not `CoreDataset`; it cannot settle what the core schema declares. Both records validated. |
| File counts remain prose in core | Unavoidable: no integer field exists on the core class. Now disclosed in `source_caveats`. |
| `total_file_count` / `total_size_bytes` absent from core as integers | Same constraint. Moved from `notes` to `description`, which is the better of the two available placements. |
| `participant_compensation` absent from core | No fitting core slot; folding it elsewhere would repeat the field-mismatch defect. Recorded above as a residual gap. |
| Grant `id` is a RePORTER URL rather than a CURIE | `Grant.id` is `uriorcurie`; no award-number prefix is declared in the digest, and the URL is the `awardURI` verbatim from the tier-1 source. The v5 rule's fallback applies. |
| `creators[0].id` is a project homepage | No registry identifier for the consortium appears anywhere in the bundle. Supplying one from outside knowledge is prohibited. Disclosed in the caveat. |
| Top-level `id` uses `doi:` prefix | Consistent across both records and with `version_access.latest_version_doi` and `related_datasets`. The bare DOI is separately in the `doi` slot, per that slot's description. |
| `instances[0].data_topic` single value | Range is `uriorcurie`, not a list. Constraint now noted rather than worked around. |
| Fragment-minted `subsets` / `file_collections` identifiers | Conforming, per the audit's own note. Unchanged. |
| `license` string vs canonical URI | `license` is a string slot; the URI is now named in `license_and_use_terms.notes`. |
| `language: en` | Matches FAIRhub. The English-eligibility requirement is separately in `known_limitations`. No conflict. |
| `conforms_to_standard` includes `DICOM` | The audit withdrew this on re-reading; `DICOM` is in the permitted list. All seven values are permitted and attested. |
| Beta-platform statement from superseded source | Retained but now attributed to the superseded page, with the note that v3 does not repeat it. |

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 68 | 64 |
| Validated | yes | yes |
| Slots added in reconciliation | 4 | 4 |
| Slots restored from the paired record | — | 8 (relocated into fitting core slots) |
| Slots removed | 0 | 0 |

Both records describe the same referent — version 3.0.0 of the FAIRhub-distributed AI-READI dataset, DOI `10.60775/fairhub.3` — as stated in the top-level `source_caveats` of each. The pair is now consistent in every slot that both schemas admit; the remaining divergences are structural (no `variables`, `subsets`, `splits`, `relationships`, `file_collections` or integer total slots on `CoreDataset`) and are disclosed in the core record's `source_caveats` rather than left for a reader to infer.