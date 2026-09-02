# Phase 4 Reconciliation Report — VOICE

**Project:** VOICE (Bridge2AI Precision Public Health Grand Challenge — Voice as a Biomarker of Health)
**Records reconciled:** full (`VOICE_d4d.yaml`) and core (`VOICE_d4d_core.yaml`)
**Audit findings received:** 24 (1 high, 4 medium, 19 low)
**Findings acted on:** 8 · **Findings left as-is:** 16

---

## 1. Audit summary

The audit found no fabricated facts. Every populated value traced to the declared bundle; identifier forms followed the `uriorcurie` / `doi` rules (bare DOI in `doi`, `doi:` CURIEs in `related_datasets` and `latest_version_doi`, URLs in the `uri`-ranged `access_urls`); all enum values were schema-declared; and no source commentary had leaked into name, identifier or affiliation fields.

The findings clustered into four kinds of problem:

1. **One internal inconsistency** (high) — a `source_caveats` value that described sibling content the record did not actually carry.
2. **Scope drift** (medium/low) — several entries described the pediatric cohort, which the record itself treats as a *separate dataset* via `related_datasets`, while the stated referent is the adult feature-only release.
3. **Under-specification** (medium/low) — the referent choice was never stated; `conforms_to` asserted BIDS more broadly than the evidence supports; `variables` sampled six columns from a much larger released set without saying so; `annotation_analyses` was omitted although the bundle supports it.
4. **Cosmetic redundancy** (medium/low) — a landing-page URL duplicating `page`; a thin external resource; a bare-origin publisher URL; a debatable substrate mapping.

Twelve of the low findings were checks confirming that an *omission* was evidence-backed rather than an oversight. Those required no action and are listed in §4.

---

## 2. Changes made to the full record

### 2.1 `purposes[0]` — internal inconsistency repaired (high)

The caveat claimed "both figures are recorded", but the response carried only the 10,000 figure. The 30,000 figure has been added to the response, and the caveat now says the figures are recorded "in the response above".

*Before (response, final clause):*
> …to fuel research and discovery in voice biomarkers and to promote the integration of voice as a biomarker of health in clinical care.

*After:*
> …integration of voice as a biomarker of health in clinical care. **The multi-site IRB protocol for the underlying data acquisition study states a sample size of 30,000 participants, to be reached through collaboration with other participating institutions and existing cohorts.**

Both equal-ranked sources now appear in the value the caveat annotates, which is what the disagreement rule requires when the ranking cannot decide.

### 2.2 `source_caveats` (top level) — referent choice stated (medium)

The audit noted that `id` carries the version DOI while `related_datasets` also asserts `is_version_of` against the concept DOI, and that the referent choice should be stated explicitly. A sentence was prepended:

> The referent of this record is the adult Bridge2AI-Voice feature-only release published on PhysioNet, and `id` carries the version-specific DOI for v3.1.0; the version-independent concept DOI 10.13026/37yb-1t42 is recorded separately in `version_access.latest_version_doi` and in a `related_datasets` entry.

`id` itself was **not** changed. The version DOI identifies the artifact this record actually describes — 833 participants, the v3.1.0 file inventory, the v3.1.0 feature counts. The concept DOI would name a moving target that the record's counts would immediately misdescribe.

The same caveat gained a sentence covering the `variables` sample (see §2.5), and lost the sentence about BIDS scoping, which moved into `conforms_to` itself (see §2.3).

### 2.3 `conforms_to` — scope narrowed to match the evidence (medium)

*Before:* `Brain Imaging Data Structure (BIDS) v1.9.0`
*After:* `Brain Imaging Data Structure (BIDS) v1.9.0, applied to the audio dataset layout and the phenotype folder organization rather than to the Parquet feature files of the published feature-only release.`

The qualification previously lived only in `source_caveats`, where a reader consulting `conforms_to` alone would miss it. It now sits in the slot it qualifies. `conforms_to_standard: [BIDS]` was retained — the bundle does state BIDS conformance, and the term slot exists so the corpus can be queried; the prose slot carries the scope.

### 2.4 `distribution_formats[0].access_urls` — removed (medium)

The value duplicated the top-level `page` and conveyed no format-specific access route. It was deleted; the `notes` listing the nine Parquet files is unchanged.

### 2.5 `variables` — expanded from 6 to 13 entries (medium)

Seven entries were added, each grounded in the v3.1.0 Data Description: `mfcc`, `pitch` (with `minimum_value: 80.0`, `maximum_value: 500.0`), `sparc_ema`, `sparc_loudness`, `sparc_periodicity`, `sparc_pitch` (with `unit: Hz`, range 50–550), and `ppgs`. This now covers every dense feature the bundle describes.

The list is still not exhaustive — the phenotype tables and the openSMILE/Praat static features run to hundreds of columns the bundle does not enumerate — so `source_caveats` gained:

> The variables listed in `variables` are the identifying and dense-feature columns shared across the released files, not a complete enumeration of the released columns…

### 2.6 `annotation_analyses` — slot added (low)

The bundle states single-labeler annotation, no agreement assessment, and widely varying human-level performance. This was carried inside `labeling_strategies[0].inter_annotator_agreement`; `AnnotationAnalysis` is the class the schema declares for it. A single entry was added with `analysis_method`, `annotation_quality_details` and `notes`, and the `inter_annotator_agreement` field was removed from `labeling_strategies[0]` so the fact is stated once.

### 2.7 Pediatric scope drift — three entries relocated (low ×3)

The record's own `related_datasets` treats the pediatric dataset as separate. Three entries described it anyway, each with a disclaiming caveat. Rather than delete grounded evidence, it was moved to the entry that already names the pediatric dataset:

| Removed from | What it said | Where it went |
|---|---|---|
| `collection_mechanisms[3]` | reproschema-ui, pediatric protocol, REDCap transform | `related_datasets[0].description` |
| `ethical_reviews[1]` | Hospital for Sick Children REB approval | `related_datasets[0].description` |
| `at_risk_populations.assent_procedures`, `.guardian_consent`, `.source_caveats` | assent, parental permission | `related_datasets[0].description` |

`collection_mechanisms` went from four entries to three; `ethical_reviews` from two to one. `at_risk_populations.special_protections` was retained and extended with "…and the adult release contains only participants aged 18 and over", which is what the deleted `source_caveats` was there to say.

### 2.8 `instances[0].data_substrate` — removed (low)

`B2AI_SUBSTRATE:41` ("Tab-separated values") was applied to an instance whose type is "Study participant". A participant is not a substrate. The slot was omitted per the enum instruction ("If no term fits, omit the slot"), and the storage fact moved into `notes`: "Participant-level information is distributed as tab-separated phenotype tables." `instances[1].data_substrate: B2AI_SUBSTRATE:30` (Parquet) was retained — that instance *is* a feature record, and Parquet is genuinely its substrate.

### 2.9 `external_resources[5]` — thinness explained (low)

The FHIR entry had `notes` only. The bundle supplies no URL — the documentation renders "Navigate to Source Code" as text without capturing the href. The note now says so: "…The documentation links to the source code but the bundle does not record the repository URL." No fabricated URL was supplied.

---

## 3. Changes made to the core record

The core record was re-derived by projection from the reconciled full record. Every §2 change that touches a core-declared slot propagated:

- `purposes[0]` — 30,000 figure added, caveat repaired
- `source_caveats` — referent statement and `variables` note added, BIDS sentence removed
- `conforms_to` — scope qualification added
- `distribution_formats[0]` — `access_urls` removed
- `annotation_analyses` — slot added
- `labeling_strategies[0]` — `inter_annotator_agreement` removed
- `collection_mechanisms` — 4 → 3 entries
- `ethical_reviews` — 2 → 1 entry
- `at_risk_populations` — assent/guardian/caveat fields removed, `special_protections` extended
- `instances[0]` — `data_substrate` removed, `notes` extended
- `related_datasets[0].description` — pediatric detail absorbed
- `external_resources[5].notes` — URL absence explained

`variables` is **not** a core-declared slot, so the seven added entries appear in the full record only. The core header retains `# Sources:` pointing at the full record and now carries `# Phase 4 reconciliation: completed`.

---

## 4. Findings left as-is

### 4.1 Deliberate decisions, not defects

| Finding | Why left |
|---|---|
| `id` as version DOI (medium) | Kept. Documented in `source_caveats` rather than changed — the version DOI names the artifact whose counts the record states. |
| `publisher` bare origin URL (low) | Kept. `publisher` is `uriorcurie`; the bundle supplies no registry identifier for PhysioNet, and inventing one would violate the identifier rule. `https://physionet.org` is the permitted URI fallback. |
| `keywords` from v3.1.0 (low) | Kept. The audit confirmed preferring the non-superseded source's four-term list over the two-term v3.0.0 list is correct. No repair requested or made. |

### 4.2 Omissions confirmed evidence-backed — no action

Twelve findings were checks that an absent slot was correctly absent. All remain absent in both reconciled records:

- **`use_repository`** — the healthsheet answers "No" explicitly.
- **`is_tabular`** — the release is mixed (TSV tables and Parquet tensors); a boolean cannot state this honestly.
- **`total_file_count`**, **`total_size_bytes`** — no total stated; derivation across an incompletely enumerated tree would be inference.
- **`compression`** — Parquet is a container, not one of the enum codecs; no codec attested.
- **`download_url`** — files sit behind credentialed access; only landing pages and the Synapse route exist, and both are already carried elsewhere.
- **`imputation_protocols`** — no cleaning was performed; `missing_data_documentation.handling_strategy` already records that no imputation is applied.
- **`subsets`**, **`file_collections`** — nothing in either record points at a subset or collection by identifier, so minting fragments would produce labels no value uses. Cohorts are carried in `subpopulations`; the folder tree in `preprocessing_strategies` and `distribution_formats`.
- **`created_on`** — the NIH RePORTER project start (tier 4) dates the award, not the record.
- **`last_updated_on`** — no modification timestamp distinct from `issued`.

---

## 5. Outcome

Both records validate. The high-severity inconsistency is repaired; all four medium findings are either fixed or explicitly documented; eight low findings produced edits and eleven were confirmed correct as they stood. The full record's referent — the adult Bridge2AI-Voice feature-only release, v3.1.0, on PhysioNet — is now stated in `source_caveats` and held consistently: pediatric material appears only inside the `related_datasets` entry that names the pediatric dataset, and no slot describes a population outside the stated referent without saying so.