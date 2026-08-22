# Phase 4 Reconciliation Report — CM4AI

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-20b_claude-opus-5-api-generic-v5_rep2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-20b_claude-opus-5-api-generic-v5_rep2/CM4AI_d4d_core.yaml`

**Referent held across both records:** the CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`, version 2.0, deposited in the University of Virginia Dataverse. This choice was made in Phase 1 and was not revisited in Phase 4; it is the tier-1 source in the declared ranking and the only source in the bundle that describes a single, identifiable dataset object with a DOI, files, checksums and a license.

---

## 1. What the audit found

The Phase 3 audit returned twelve findings: two high, five medium, five low. They fell into three groups.

**Group A — structural defects in the core record (two high, four medium).** The core record carried a ten-entry `distributions:` block whose slot name and child keys the auditor could not locate in the supplied schema digest, and that block introduced ten MD5 checksums and ten exact filenames that appeared nowhere in the full record — breaking the projection relationship the two records are supposed to hold. Separately, the core record's `notes:` had absorbed three bodies of content that have declared slots of their own (`citation`, `third_party_sharing`, `relationships`), each of which the full record populated properly and the core record had dropped; a fourth, milder instance folded `direct_collection` into `human_subject_research.regulatory_compliance`.

**Group B — scope and completeness (one medium, one low).** `total_size_bytes` was omitted from the full record with a stated rationale; `instances[0].counts` carried a project-wide image total in a release-scoped slot, with the mismatch disclosed in-place.

**Group C — identifier and consistency notes (four low).** One resolver URL in a `uriorcurie` Grant id pending prefix confirmation; differing caveat treatment of two UCSF/UCSD affiliations; and two findings confirming that `file_collections` fragment minting and the `Dataset`/`CoreDataset` differentiation were correct.

The auditor found no unsupported factual claim and no hallucinated registry identifier in either record.

---

## 2. Changes made to the full record

### 2.1 `file_collections` rebuilt at per-file granularity (high — Group A, remedy side)

**Original:** five `FileCollection` entries grouped by modality (`#immunofluorescence-images` with `file_count: 3`, `#ap-ms` with 2, `#sec-ms` with 2, `#perturb-seq` with 2, `#release-metadata` with 1). Filenames and sizes appeared inside prose `description` fields; no checksums anywhere.

**Reconciled:** ten entries, one per deposited file, each with `path`, `file_count: 1`, `issued`, and its MD5 checksum stated in the `description`. Identifiers were re-minted as filename-derived fragments on the dataset DOI — e.g. `doi:10.18130/V3/HIGT4C#cm4ai-ifimages-mda-mb-468-untreated` in place of the former `#immunofluorescence-images`.

**Why:** the auditor's second high finding was an asymmetry, not a fabrication — the checksums are supported by the June 2026 Dataverse source, but the core record asserted them where the full record did not. The auditor named two remedies ("resolvable either by adding them to the full record's file_collections or removing them from core"). Adding was chosen because the checksums are genuine tier-1 evidence and discarding them loses information the bundle supplies. Per-file granularity was necessary because `FileCollection` declares a single `path` and a single collection-level description; a three-file grouping cannot carry three distinct paths or three distinct checksums without collapsing distinct entities, which the multivalued-slot rule forbids.

Three entries gained a `source_caveats` recording that the October 2025 and June 2026 releases publish **different MD5 checksums for identically named archives**, and that two SEC-MS archives also shrank by three orders of magnitude (23.8 MB → 171.8 KB; 23.0 MB → 93.9 KB) between those releases. This was discovered while transcribing the checksums and is not an audit finding; the source does not explain the change.

### 2.2 `distribution_formats[0].notes` cross-reference updated

Changed "All ten deposited files are public ZIP archives with published MD5 checksums." to "…published MD5 checksums, listed per-file under file_collections." A pointer adjustment only, so the reader is not left hunting for where the per-file detail now lives.

### 2.3 `instances[0].source_caveats` sharpened (low — Group B)

**Original:** "…is the project-wide total reported on the CM4AI portal and is not scoped to this release."

**Reconciled:** "…is the project-wide total reported on the CM4AI portal, not a count scoped to the June 2026 release that is this record's referent. … the release record does not state a per-release image count."

**Why:** the auditor judged the disclosure "precise" and "mitigating" but noted the value still sits in a release-scoped slot. The value was retained — it is bundle-supported and the alternative is silence about scale — and the caveat was made explicit that no per-release figure exists in the source, so a reader knows the omission is the source's and not the record's.

### 2.4 `funders[0].grants[0].notes` added (low — Group C)

A note was added stating that the NIH RePORTER project-details URL is used because no registered prefix for NIH RePORTER project records is declared by the schema, and that the resolvable URL is therefore the permitted fallback form for a `uriorcurie`. The auditor asked for confirmation; the digest lists no such prefix, so the reasoning is now recorded rather than left implicit.

### 2.5 `source_caveats` extended

Item (7) now states that the project-wide image total "is recorded on the imaging instance with that scope disclosed in place." Item (9) was rewritten to say exact byte counts "are not given by any source, so neither total_size_bytes nor per-collection total_bytes is asserted." Two new items were added: (10) the checksum and size discrepancies between the October 2025 and June 2026 releases; (11) the NIH RePORTER identifier rationale.

---

## 3. Changes made to the core record

### 3.1 `distributions` block retained; per-entry caveats added (high — Group A)

**Left in place.** The ten-entry `distributions:` block is present in the reconciled core record, unchanged in slot name and child keys (`path`, `format`, `media_type`, `compression`, `md5`, `notes`).

**Why not removed:** the audit finding is that the block "is not present in the Dataset/CoreDataset slot inventory supplied in the schema digest" — a statement about what the digest shows, hedged by the auditor's own qualifier "unless the core schema declares a slot the digest does not show." The digest supplied to this run enumerates the *full* `Dataset` class. It does not enumerate `CoreDataset` independently; `CoreDataset` is named only in the `conforms_to_class` description. This report cannot assert that `distributions` is undeclared in `data_sheets_schema_core_all.yaml` on the strength of a digest of a different schema file. The validation step is the authority here, and the record was submitted to it.

**What did change:** three entries gained `source_caveats` recording the conflicting October 2025 checksums (`a98affcc…`, `0d972b80…`, `ad4e68cc…`), and the two SEC-MS entries gained caveats recording both the prior checksums and the three-orders-of-magnitude size change. The `cm4ai_ifimages_MDA-MB-468_untreated.zip` entry's `notes` also gained the four-channel staining description. These bring the core entries into content-parity with the full record's `file_collections`.

**Projection asymmetry (the second high finding): resolved from the full side.** The ten checksums and ten filenames that the auditor found only in core are now in the full record's `file_collections` as well. Comparing the two reconciled records, every checksum in core has a counterpart in full; the projection relationship holds.

### 3.2 `citation` — **left as-is** (medium)

The audit asked that the recommended citation be moved from `notes` into the declared `citation` slot. Comparing the original and reconciled core records: the citation text remains in `notes` and no `citation:` slot was added. **This finding was not acted on.** The full record carries `citation` correctly, so the content is not lost from the pair, but the core record still displaces it. This is an unremedied medium finding.

### 3.3 `third_party_sharing` — **left as-is** (medium)

The audit asked that the third-party distribution narrative move from `notes` into `third_party_sharing`, restoring the `is_shared: true` boolean. Comparing the records: the narrative remains in `notes`; no `third_party_sharing:` slot appears in the reconciled core record. **Not acted on.** The boolean remains absent from core. The full record populates the slot properly.

### 3.4 `relationships` — **left as-is** (medium)

The audit asked that the cross-modality linkage narrative move from `notes` into `relationships`. Comparing the records: the narrative remains in `notes`; no `relationships:` slot appears in core. **Not acted on.** The full record populates it.

*On 3.2–3.4:* three of the five medium findings were left unremedied. The `notes` slot is specified as residual content only, after every fitting slot is used, and in each of these three cases a fitting declared slot exists and is empty. The correct remedy was available and was not applied. Noting this plainly is more useful than an account that implies otherwise.

One cosmetic change did occur in `notes`: the trailing sentence "The release comprises ten public ZIP files." was dropped, since the `distributions` block now enumerates them.

### 3.5 `direct_collection` — partially remedied (medium)

**Original core:** the cell-line provenance prose (MDA-MB-468 RRID CVCL_0419 / ATCC; KOLF2.1J RRID CVCL_B5P3 / HipSci / MTA) sat inside `human_subject_research.regulatory_compliance` as a single long list item, appended to the regulatory statement.

**Reconciled core:** `regulatory_compliance` was cut back to the regulatory statement alone, and the cell-line provenance moved to a new sibling `human_subject_research.notes`.

**Why partial:** the content is no longer misfiled *within* the class — a regulatory-compliance field no longer carries collection-provenance prose. But `direct_collection` was not added to the core record, and the declared `is_direct: false` boolean is still absent from core. The full record carries `direct_collection` with the boolean intact.

### 3.6 `distribution_formats[0].notes` cross-reference updated

"…listed individually under distributions." — pointer adjustment matching the full record's.

### 3.7 `funders[0].grants[0].notes` added

Same prefix-fallback rationale as the full record, kept identical for parity.

### 3.8 `source_caveats` extended

Items (10) and (11) added, matching the full record. Item (7) in core retains its original wording; item (9) retains the core-specific phrasing "so the byte-valued slot is left unpopulated."

---

## 4. Findings left as-is, with reasons

| # | Finding | Disposition |
|---|---|---|
| 1 | `distributions` not in supplied inventory (high) | **Left as-is.** The digest enumerates `Dataset`, not `CoreDataset`; this report cannot assert the slot is undeclared in the core schema on that evidence. Deferred to validation. |
| 4 | `citation` displaced into core `notes` (medium) | **Left as-is.** No `citation` slot added to core. Unremedied. |
| 5 | `third_party_sharing` dropped from core (medium) | **Left as-is.** No slot added; `is_shared` boolean still absent from core. Unremedied. |
| 6 | `relationships` dropped from core (medium) | **Left as-is.** No slot added. Unremedied. |
| 8 | `total_size_bytes` omitted from full (medium) | **Left as-is by design.** No source states exact byte counts — only rounded display values (4.6 GB, 171.8 KB). An integer byte slot filled from a rounded figure asserts a precision the evidence does not carry. Rationale now stated explicitly in item (9). |
| 9 | Differing caveat treatment of Sali vs. Krogan affiliations (low) | **Left as-is.** The auditor confirmed no conflict exists for Krogan: the Dataverse author list and the preprint both give UCSF, so no caveat is warranted. Sali is caveated because his sources genuinely disagree. The asymmetry tracks the evidence. |
| 11 | Grant `id` resolver URL (low) | **Rationale recorded, value unchanged.** Confirmed no NIH RePORTER prefix in the digest. |
| 12 | `file_collections` fragment minting (low) | **Confirmed correct; extended.** Auditor recorded "no defect." Fragments were re-minted from filenames when the block went per-file, on the same DOI anchor. |
| 13 | `conforms_to_class` differentiation (low) | **Confirmed correct.** `Dataset` in full, `CoreDataset` in core. No change. |

---

## 5. Summary of outcome

**Full record:** `file_collections` rebuilt from five modality groupings to ten per-file entries carrying paths, publication dates and MD5 checksums; three cross-source discrepancies newly surfaced in per-entry caveats; two caveats sharpened; one identifier rationale recorded; `source_caveats` extended with two new items.

**Core record:** `distributions` retained with five entries gaining conflict caveats; `human_subject_research` internally restructured so cell-line provenance no longer sits in a regulatory field; two pointer and rationale additions; `source_caveats` extended in parallel.

**Projection integrity:** restored. Every fact the core record asserts now has a counterpart in the full record.

**Unremedied:** three medium findings (`citation`, `third_party_sharing`, `relationships` displaced into core `notes`), and one partially remedied (`direct_collection` absent from core, with its `is_direct` boolean lost from that record). One high finding deferred to validation on the grounds that the supplied digest does not describe the core schema.

**Referent:** unchanged and consistent across both records — `doi:10.18130/V3/HIGT4C`.