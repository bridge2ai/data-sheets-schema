# Reconciliation Report — CM4AI

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Version label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep1
**Records reconciled:** full (`CM4AI_d4d.yaml`) and core (`CM4AI_d4d_core.yaml`)
**Referent:** the June 2026 Data Release (Beta) of CM4AI, doi 10.18130/V3/HIGT4C, version 2.0, in the University of Virginia Dataverse. Held consistently across both records.

---

## 1. Audit findings and disposition

The audit returned thirteen findings: three high, three medium, seven low. Six of the low findings were recorded as checks that passed rather than defects. Disposition follows.

### 1.1 HIGH — core `distributions` slot not in the schema digest

**Finding.** The `distributions` slot and its `Distribution` object range do not appear in the supplied `Dataset` digest, which carries `file_collections` (range `FileCollection`) as the declared slot for per-file grouping.

**Disposition: left as-is, with a compensating change to the full record.**

The digest supplied to this run describes the **full** schema's `Dataset` class. It is not a digest of `CoreDataset`, and the audit's own wording concedes the point — "unless `CoreDataset` declares a slot the digest does not show". The absence of `distributions` from a `Dataset` digest is not evidence about what `CoreDataset` declares, and the instructions for this phase forbid stating that a slot is undeclared without the digest supporting it. The digest does not support it either way. `distributions` therefore remains in the core record unchanged, as ten objects, and validation against `data_sheets_schema_core_all.yaml` is the arbiter.

What *did* change is the full record. Because the audit correctly observed that the full record's `file_collections` carried the same per-file content in a grouped form, and because grouping several files under one `FileCollection` object collapses distinct entities, `file_collections` in the full record was restructured from **six grouped collections to ten single-file collections**, one per released archive, each with `path`, `name`, `collection_type`, `file_count: 1`, `compression`, and its MD5 in `notes`. The identifiers were re-minted accordingly — `#files-apms` became `#file-apms-paclitaxel` and `#file-apms-vorinostat`, `#files-if-images` became three per-condition fragments, and so on. All ten remain fragments on the release DOI, which the audit confirmed as the correct minting pattern. This brings the full record into one-to-one correspondence with the core record's `distributions` entries.

### 1.2 HIGH — core `distributions[*].bytes` back-computed

**Finding.** Seven byte counts (116019, 139059, 175923, 96154, 30925, 75059, 1153434) were derived from rounded human-readable sizes ("113.3 KB", "1.1 MB") that the bundle states. No source gives exact byte counts.

**Disposition: accepted and fixed.**

All seven `bytes` keys were **removed** from the core record's `distributions` objects. The human-readable sizes the release actually states are retained in each object's `notes` ("Listed as 113.3 KB, published 2026-06-17"), which is what the evidence supports. A new clause (8) was added to `source_caveats` in **both** records:

> File sizes are recorded as the human-readable values the Dataverse release states (for example "113.3 KB", "4.6 GB"); no exact byte counts are given by any source, so none are asserted.

This aligns the core record with the full record's existing treatment, which the audit noted as correct: `total_size_bytes` was omitted from the full record for exactly this reason, and `total_file_count: 10` was retained because ten files are enumerated.

### 1.3 HIGH — core `conforms_to_standard` scalar where multivalued

**Finding.** `distributions[9].conforms_to_standard: RO_CRATE` was a bare scalar; the digest declares `conforms_to_standard` as `DataStandardEnum [many]`.

**Disposition: accepted and fixed.**

Changed to list form in the core record:

```yaml
conforms_to_standard:
  - RO_CRATE
```

The top-level `conforms_to_standard` in both records was already a list and is unchanged. The full record's release-metadata file collection likewise uses list form.

### 1.4 MEDIUM — core `media_type` divergence for the RO-Crate package

**Finding.** The core record changed `distribution_formats[1].media_type` from `application/ld+json` (full) to `application/json`, justified by a `source_caveats` asserting that "the schema's media_type enumeration has no term for JSON-LD". The digest declares no enumeration on `media_type`.

**Disposition: accepted and fixed.**

The core record's value was reverted to `application/ld+json`, matching the full record, and the `source_caveats` making the unsupported schema claim was **deleted**. The bundle describes RO-Crate metadata as JSON-LD throughout; `application/ld+json` is the accurate media type and nothing in the digest constrains the field. The silent divergence between the two records is now closed.

### 1.5 MEDIUM — core `notes` used to relocate full-record content

**Finding.** The core `notes` slot carried the full citation, the `direct_collection` content, the `third_party_sharing` content, and a summary of `file_collections`/`subsets`. The digest defines `notes` as residual content only, after every fitting slot is used.

**Disposition: accepted and fixed.**

The entire `notes` block was **removed** from the core record. Where `CoreDataset` declares no counterpart slot for a fact, omission is the correct answer; relocating that fact into `notes` populates a field with something it does not ask for. The affected content remains in the full record in its proper slots: `citation`, `direct_collection`, `third_party_sharing`, `file_collections`, `subsets`.

### 1.6 MEDIUM — full `funders[0].grants[0].id` is a resolver URL naming a web page

**Finding.** `Grant.id` (range `uriorcurie`) held `https://reporter.nih.gov/project-details/11211616`, which identifies a RePORTER page rather than the grant. The bundle supplies the grant number itself.

**Disposition: accepted and fixed in both records.**

The `id` key was **removed** from the grant object in both the full and core records, leaving:

```yaml
grants:
  - name: 1OT2OD032742-01
```

The bundle names the grant but supplies no identifier for it in any declared prefix scheme, and under the v5 rules an identifier for something outside this dataset is taken from the evidence or omitted. The RePORTER URL was not discarded: it was moved into the existing `notes` on that funder ("The RePORTER project page for that application is at https://reporter.nih.gov/project-details/11211616") and a new `external_resources` entry was added to **both** records recording the RePORTER page with its application ID, project numbers, PI, organization, fiscal year, award amount and project period. A URL inside prose is text and is left as written.

### 1.7 LOW — full `instances[3].counts` conflates targeted genes with records

**Finding.** `counts: 11739` on the gene-level CRISPRi instance is supported as a gene count but equating targeted genes with atlas records is an inference the bundle does not make explicit.

**Disposition: accepted, annotated rather than removed.**

`counts: 11739` is retained in both records, and a `source_caveats` was **added** to that instance in both:

> The count is the number of targeted genes stated by the release (11,739); the sources do not separately state a record count for the atlas.

The number is attested; what was missing was the disclosure that its interpretation as an instance count is a reading rather than a statement.

### 1.8 Findings left as-is

| Finding | Severity | Why unchanged |
|---|---|---|
| `instances[*].data_substrate` assignments interpretive | low | The audit recorded this "for transparency" and found "no defect". B2AI_SUBSTRATE:59 and :64 are well supported; :56, :58 and :63 are defensible readings of the declared vocabulary. Both records are byte-identical here. |
| ORCID normalization for Marquez C | low | The audit found the normalization to `ORCID:0000-0003-3960-420X` correct and consistently applied. No change. |
| Core `creators` reproduces all 46 verbatim | low | Recorded as "consistent with the full record and supported by the bundle; no divergence found". Unchanged in both. |
| `publisher: ROR:0153tk833` | low | The audit verified the ROR identifier appears verbatim in the June 2026 release affiliations and is correctly rendered as a CURIE rather than a resolver URL. Recorded as a check that passed. Unchanged. |
| `distributions[*].md5` | low | All ten checksums transcribe correctly, and the caveats correctly flag that the three IF archives differ from the same-named October 2025 files. Recorded as a check that passed. Checksums are unchanged in the core record and now appear per-file in the full record's ten file collections. |
| `total_file_count: 10`, `total_size_bytes` omitted | low | Confirmed correct. `total_file_count: 10` is retained in the full record; `total_size_bytes` remains absent. |
| `issued` / `last_updated_on` | low | Confirmed correct: the tier-1 June 2026 Dataverse release beats the tier-2 portal's conflicting "June 17, 2025", and the conflict is disclosed in caveat (1). `last_updated_on: 2026-07-15T00:00:00Z` matches the later IF-archive publication. Unchanged in both. |

---

## 2. Summary of edits by record

### Full record

| Slot | Change |
|---|---|
| `file_collections` | Restructured from 6 grouped collections to 10 single-file collections, one per released archive; identifiers re-minted as per-file DOI fragments; each carries `path`, `file_count: 1`, and its MD5 in `notes`. |
| `funders[0].grants[0].id` | Removed; RePORTER URL relocated into the funder's `notes`. |
| `external_resources` | One entry added, recording the NIH RePORTER project page and its stated fields. |
| `instances[3]` | `source_caveats` added disclosing that 11,739 is the targeted-gene count. |
| `source_caveats` | Clause (8) added on file sizes and the absence of byte counts. |

Unchanged: `citation`, `direct_collection`, `third_party_sharing`, `subsets`, `total_file_count`, `distribution_formats`, and all remaining slots.

### Core record

| Slot | Change |
|---|---|
| `distributions[*].bytes` | All seven removed; stated human-readable sizes retained in `notes`. |
| `distributions[9].conforms_to_standard` | Scalar changed to list. |
| `distribution_formats[1].media_type` | Reverted to `application/ld+json`; the unsupported schema-constraint `source_caveats` deleted. |
| `funders[0].grants[0].id` | Removed; RePORTER URL relocated into the funder's `notes`. |
| `external_resources` | Same NIH RePORTER entry added, matching the full record. |
| `instances[3]` | Same `source_caveats` added. |
| `source_caveats` | Same clause (8) added. |
| `notes` | Removed in full. |

Unchanged: `distributions` as a slot and all ten `path`/`format`/`media_type`/`compression`/`md5` values; all 46 creators; every shared prose slot.

---

## 3. Cross-record consistency after reconciliation

No shared fact differs between the two records. The two divergences the audit identified — the media_type change and the `notes` relocation — are both closed. Both records now:

- name the same referent (doi:10.18130/V3/HIGT4C, v2.0, June 2026 Beta);
- resolve the release-date conflict the same way, in favor of the tier-1 Dataverse record, with the conflict disclosed;
- treat the tier-1 October 2025 release as superseded and cite it only through `related_datasets` and per-file checksum caveats;
- quarantine the Nature U2OS article as a distinct dataset in `external_resources`;
- assert no byte counts;
- carry the same grant representation, the same RePORTER external resource, and the same eight-clause `source_caveats`.

The ten `distributions` objects in the core record and the ten `file_collections` in the full record now describe the same ten archives in the same order of content.

---

## 4. Outstanding risk

One item cannot be settled from the material available in this phase: whether `CoreDataset` declares `distributions` with the keys used. The digest supplied covers `Dataset`, not `CoreDataset`, so it neither confirms nor refutes the audit's high-severity claim. Validation against `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` is the decisive test; if it fails on that slot, the correct remedy is to project the content onto whatever grouping slot `CoreDataset` does declare, mirroring the ten per-file collections now present in the full record. No other finding leaves residual risk.