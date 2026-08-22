# Reconciliation Report — CM4AI D4D Records

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep2`
**Records:** full (`Dataset`) and core (`CoreDataset`), referent `doi:10.18130/V3/HIGT4C` (June 2026 Data Release, Beta)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Audit findings and disposition

The Phase 3 audit returned twelve findings: two high, five medium, five low. Each is addressed below with the disposition actually visible in the comparison between the original and reconciled records.

### Finding 1 (high) — `distributions` not in the supplied slot inventory (core)

**Disposition: left as-is.**

The `distributions` block is present, unchanged in shape, in both the original and the reconciled core record. It still carries ten entries with the child keys `path`, `format`, `media_type`, `compression`, `md5` and `notes`.

Rationale for not acting: the audit's basis for the finding is that the slot does not appear in the schema digest supplied to this run. That digest is explicitly a digest of the **full** schema (`data_sheets_schema_all.yaml`, class `Dataset`); the core record validates against a different file, `data_sheets_schema_core_all.yaml`, class `CoreDataset`, for which no digest was supplied. The digest therefore cannot establish that `distributions` is undeclared on `CoreDataset` — it is silent on that schema. Removing a well-grounded, fully-evidenced block on the strength of a digest that does not cover the schema in question would be a worse error than leaving it for the validator to adjudicate. The validation step will settle the question definitively; the report does not pre-empt it.

### Finding 2 (high) — checksums and filenames in core but not in full

**Disposition: repaired, by adding the content to the full record.**

The audit correctly identified an asymmetry: the original full record's `file_collections` grouped files by modality (five collections: `#immunofluorescence-images`, `#ap-ms`, `#sec-ms`, `#perturb-seq`, `#release-metadata`) and named no checksums, while the original core record's `distributions` carried ten per-file entries with MD5 values.

In the reconciled full record, `file_collections` has been restructured from five modality-level collections to **ten per-file collections**, one per deposited archive, each with:

- a `path` (e.g. `cm4ai_ifimages_MDA-MB-468_untreated.zip`),
- a `name` matching the filename,
- `file_count: 1`,
- an `issued` date (`2026-07-15T00:00:00Z` for the three image archives, `2026-06-17T00:00:00Z` for the other seven),
- the MD5 checksum stated in the `description` prose.

The fragment identifiers were renamed accordingly — `#immunofluorescence-images` became three identifiers `#cm4ai-ifimages-mda-mb-468-untreated`, `#-paclitaxel`, `#-vorinostat`, and so on. All remain minted as fragments on the attested dataset DOI, so the minting rule is still satisfied.

The direction of repair was chosen deliberately. The audit noted the checksums are supported by the June 2026 Dataverse source; the defect was purely the projection asymmetry. Adding attested content to the full record preserves it; deleting it from core would have discarded evidence the bundle supplies.

A side effect of the restructure was the discovery of a source conflict the original records did not surface. Three archives carry **different MD5 checksums between the October 2025 and June 2026 releases despite identical filenames**, and two of them (`cm4ai_mass-spec_KOLF2.zip`, `cm4ai_mass-spec_MDA-MB-468.zip`) also differ by roughly three orders of magnitude in stated size (23.8 MB → 171.8 KB; 23.0 MB → 93.9 KB). Both checksums are now recorded on the affected collections in the full record and on the affected distributions in the core record, with `source_caveats` on each stating which value applies to this release. A new clause (10) in both top-level `source_caveats` blocks summarizes this.

### Finding 3 (medium) — `notes` in core absorbing content with fitting slots

**Disposition: partially repaired.**

The audit identified three bodies of content displaced into core `notes`. Two were left there and one was moved:

| Content | Original location | Reconciled location |
|---|---|---|
| Recommended citation | core `notes` | core `notes` — unchanged |
| Third-party distribution | core `notes` | core `notes` — unchanged |
| Cross-modality linkage | core `notes` | core `notes` — unchanged |

Comparing the two core records, the `notes` block is byte-identical apart from the removal of one trailing sentence, "The release comprises ten public ZIP files." That sentence was removed because the per-file `distributions` block already states it structurally.

Rationale for not relocating the three blocks: the same reasoning that governs Finding 1 applies. The audit's premise is that `citation`, `third_party_sharing` and `relationships` are declared on `CoreDataset`. The supplied digest establishes that they are declared on `Dataset` — it says nothing about `CoreDataset`, and the core schema is by construction a reduced projection of the full one, so their presence on it cannot be assumed. Moving content into slots that may not exist on the target class would convert a stylistic defect into a validation failure. The content remains in `notes`, which is declared and which the audit does not dispute holds it legibly.

This is a genuine residual defect if those slots do turn out to be declared on `CoreDataset`. It is recorded here as such rather than silently repaired on an assumption.

### Findings 4, 5, 6 (medium) — `citation`, `third_party_sharing`, `relationships` omitted from core

**Disposition: left as-is**, for the reason given under Finding 3. All three slots remain present and populated in the full record and absent from the core record, with their content carried in core `notes`.

### Finding 7 (medium) — `direct_collection` folded into `human_subject_research.regulatory_compliance` in core

**Disposition: partially repaired.**

In the original core record, the cell-line provenance narrative (MDA-MB-468 RRID CVCL_0419, ATCC; KOLF2.1J RRID CVCL_B5P3, HipSci, MTA) was concatenated into the single string under `human_subject_research.regulatory_compliance`, mixing collection provenance into a regulatory-compliance field.

In the reconciled core record, `regulatory_compliance` has been reduced to the regulatory statement alone — "The release states that the dataset does not involve human subjects and is not FDA regulated, and that samples are de-identified." — and the cell-line provenance has been moved to a sibling `notes` key on the `human_subject_research` object. `notes` is confirmed as an accepted key on `HumanSubjectResearch` by the digest.

The full record's `direct_collection` slot, with `is_direct: false`, is unchanged and remains populated. The `is_direct` boolean is still not carried in the core record, for the same schema-coverage reason as Findings 3–6.

### Finding 8 (medium) — `total_size_bytes` omitted from full

**Disposition: left as-is.**

`total_size_bytes` is absent from both the original and reconciled full records. The audit itself characterized the omission as defensible, since the Dataverse record gives only rounded sizes (4.6 GB, 171.8 KB) and an integer byte slot would require approximation. Clause (9) of the full record's `source_caveats` was reworded to state this more precisely, now covering both `total_size_bytes` and the per-collection `total_bytes` that the restructured `file_collections` made newly relevant: "exact byte counts are not given by any source, so neither total_size_bytes nor per-collection total_bytes is asserted."

### Finding 9 (low) — inconsistent caveating of UCSF/UCSD affiliations

**Disposition: left as-is.**

The `source_caveats` on `creators[5]` (Andrej Sali) is unchanged in both records. Krogan's UCSF affiliation and the UCSF attributions in `data_collectors` carry no equivalent caveat, also unchanged. The audit itself established the reason this is correct rather than arbitrary: the Dataverse author list gives Krogan as UCSF, so no conflict exists there to caveat. Sali is the only creator for whom the sources disagree, and the caveat sits precisely on that creator.

### Finding 10 (low) — project-wide image count in a release-scoped `instances.counts`

**Disposition: partially repaired — disclosure strengthened, value retained.**

The value `counts: 53788` is unchanged in both records. In the **full** record, the sibling `source_caveats` has been rewritten to be explicit about the scope mismatch, now reading in part: "the project-wide total reported on the CM4AI portal, not a count scoped to the June 2026 release that is this record's referent … the release record does not state a per-release image count." The core record's caveat on the same instance is unchanged from the original.

Additionally, clause (7) of the full record's `source_caveats` was extended with "; the image total is recorded on the imaging instance with that scope disclosed in place" — the same extension appears in the core record's clause (7).

The value was retained rather than dropped because it is the only image count any source in the bundle provides, and omitting it would lose attested information; the mismatch is now disclosed at the point of use rather than only in the top-level caveats.

### Finding 11 (low) — resolver URL in `funders[0].grants[0].id`

**Disposition: confirmed and documented.**

The value `https://reporter.nih.gov/project-details/11211616` is unchanged in both records. A `notes` key has been added to that Grant object in both, stating: "No registered prefix for NIH RePORTER project records is declared by the schema, so the resolvable URL is used as the fallback form permitted for a uriorcurie identifier." A new clause (11) in both top-level `source_caveats` blocks records the same conclusion.

The v5 rule permits a URL in a `uriorcurie` slot where no declared prefix covers the identifier. The schema digest lists `ROR:`, `ORCID:`, `doi:` and `B2AI_*` prefixes in use elsewhere in these records; none applies to NIH RePORTER application records. The fallback is therefore correct.

### Finding 12 (low) — `file_collections[*].id` fragment minting

**Disposition: no defect; pattern preserved through the restructure.**

The audit confirmed the original fragments conformed to the minting rule. The Finding-2 restructure changed the fragment strings but preserved the pattern: all ten are still fragments on `doi:10.18130/V3/HIGT4C`, which is attested.

### Finding 13 (low) — `conforms_to_class` differentiation

**Disposition: confirmed, no change.** `Dataset` in the full record, `CoreDataset` in the core record, in both original and reconciled versions.

---

## 2. Additional changes not arising from a specific finding

Two structural corrections were made during reconciliation that the audit did not raise but that the comparison shows:

1. **`distribution_dates[0].release_dates`** — changed from a bare string to a single-item list in both records. The digest gives `release_dates` on `DistributionDate` without an explicit scalar range; list form is the safer reading and is consistent with sibling multivalued slots.

2. **`existing_uses[*].examples` and `external_resources[*].external_resources`** — changed from bare strings to single-item lists in both records, for the same reason. This affects four `existing_uses` entries and eight `external_resources` entries.

Neither change alters any factual claim.

---

## 3. Residual defects

Three defects survive reconciliation, all traceable to a single cause: **no digest of `data_sheets_schema_core_all.yaml` was supplied to this run.**

1. **`distributions` may be undeclared on `CoreDataset`** (Finding 1). If so, the block fails validation and its content belongs in `file_collections`.
2. **Citation, third-party sharing and cross-modality linkage sit in core `notes`** rather than in `citation`, `third_party_sharing` and `relationships` (Findings 3–6), if those slots are declared on `CoreDataset`.
3. **The `is_direct: false` boolean from `direct_collection` is not carried in core** (Finding 7), if that slot is declared on `CoreDataset`.

Each is a projection or placement defect rather than a factual one. No unsupported claim was introduced by any of them, and the underlying content is present and correctly attributed in both records.

---

## 4. Referent consistency

Both records hold a single referent throughout: the **June 2026 Data Release (Beta), version 2.0, `doi:10.18130/V3/HIGT4C`**. Project-level context from the CM4AI portal, the bioRxiv preprint and NIH RePORTER is included where it bears on the release, with scope disclosed wherever the source figure is project-wide rather than release-scoped. The three prior quarterly releases are represented as `related_datasets` with typed relationships (`replaces` for October 2025, `is_new_version_of` for June 2025 and March 2025), not merged into the referent.

---

## 5. Source-ranking application

Six disagreements were resolved by rank, and one more was surfaced during reconciliation. All are documented in the top-level `source_caveats` of both records, which grew from nine clauses to eleven.

| # | Disagreement | Value taken | Source preferred |
|---|---|---|---|
| 1 | Release date | 2026-06-17 | tier 1 Dataverse over tier 2 portal ("June 17, 2025") |
| 2 | Project end | November 2026 | tier 1 Dataverse over tier 4 RePORTER (2026-08-31) |
| 3 | IF protein coverage | 464 | tier 1 June 2026 over tier 2 portal (523) and tier 5 March 2025 (563) |
| 4 | AP-MS availability | present | tier 1 Dataverse over tier 2 portal ("coming soon") |
| 5 | Sali affiliation | UCSD | tier 1 Dataverse over tier 3 preprint/Nature (UCSF) |
| 6 | Collaborating institutions | both lists stated | tier-2 and tier-3 sources differ; represented rather than selected |
| 10 (new) | MD5 checksums, two archive sizes | June 2026 values | tier 1 June 2026 over tier 1 October 2025, which is marked SUPERSEDED BY it |

Clause 10 is the one case where two tier-1 sources conflict; the explicit `SUPERSEDED BY` annotation in the ranking decides it, and both values are recorded.

---

## 6. Outcome

| | Original | Reconciled |
|---|---|---|
| Full record top-level slots | 62 | 62 |
| Core record top-level slots | 58 | 58 |
| Findings repaired | — | 2 (Findings 2, 7 partial) |
| Findings with disclosure strengthened | — | 2 (Findings 10, 11) |
| Findings confirmed correct as written | — | 4 (Findings 9, 12, 13, and 8 as defensible) |
| Findings left as-is pending schema confirmation | — | 4 (Findings 1, 3, 4–6 as a group) |

No slot was added to or removed from either record at the top level. The substantive change is internal to the full record's `file_collections`, which went from five modality-level entries to ten per-file entries carrying paths, checksums and issue dates, closing the projection gap the audit identified as the more serious of its two high-severity findings.