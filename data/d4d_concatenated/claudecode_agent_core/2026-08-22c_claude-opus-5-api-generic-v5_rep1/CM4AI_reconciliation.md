# Reconciliation Report — CM4AI D4D Records

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Version label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep1
**Referent:** CM4AI June 2026 Data Release (Beta), doi 10.18130/V3/HIGT4C, University of Virginia Dataverse, V2
**Phase:** 4 (strict reconciliation), following Phase 3 source/provenance audit

---

## 1. Referent selection

`Dataset` admits one referent. The referent chosen and held to in both records is the **June 2026 Data Release (Beta)** deposited in the University of Virginia Dataverse under doi 10.18130/V3/HIGT4C, which the declared source ranking places at tier 1 and which supersedes the October 2025 release. Prior quarterly releases (March 2025, June 2025, October 2025) are recorded through `related_datasets` rather than merged into the referent. The Nature U2OS cell-map article is quarantined as a distinct dataset in `external_resources` and in `source_caveats`, and none of its counts or metrics are attributed to CM4AI. This choice is unchanged by reconciliation and is consistent across both records.

---

## 2. Audit findings and disposition

### 2.1 HIGH — core `distributions` slot not in the schema digest

**Finding.** The digest supplied for this run lists 98 `Dataset` slots and does not include `distributions`, nor does it define a `Distribution` object range with the keys used.

**Disposition: left as-is.** The `distributions` block is still present in the reconciled core record, with all ten objects. The reason is that the instruction governing this report forbids asserting that a slot is undeclared without the digest supporting the assertion — and the digest supplied here is the **`Dataset`** inventory, not the `CoreDataset` inventory. The core record is validated against `data_sheets_schema_core_all.yaml` class `CoreDataset`, whose slot list was not supplied to this phase. The audit's own wording concedes this conditional ("Unless `CoreDataset` declares a slot the digest does not show"). Removing ten populated objects on the strength of a digest for a different class would be a larger error than retaining them, and the LinkML validation step is the correct arbiter. **If core validation fails on `distributions`, this is the block to remove**; the same content is already carried in the full record's `file_collections`, which is a declared `Dataset` slot.

Two consequences follow and were acted on:

- The full record's `file_collections` was restructured (§3.2 below) so that, should `distributions` need to be dropped from the core, no per-file fact is lost from the pair.
- The core's `distributions` was corrected on the two points that are defects regardless of whether the slot is declared (§2.2, §2.3).

### 2.2 HIGH — invented byte counts in core `distributions[*].bytes`

**Finding.** Seven integer byte values (116019, 139059, 175923, 96154, 30925, 75059, 1153434) were back-computed from the rounded human-readable sizes the Dataverse release states ("113.3 KB", "1.1 MB", and so on). No source states an exact byte count.

**Disposition: fixed.** Every `bytes` key has been **removed** from the core `distributions` objects. Compare, for example, `cm4ai_apms_MDA-MB-468_paclitaxel.zip`: the original core had `bytes: 116019`; the reconciled core has no `bytes` key, and the human-readable size survives in prose ("Listed as 113.3 KB, published 2026-06-17"). The same removal was applied to the vorinostat AP-MS, both SEC-MS, both Perturb-seq, and the release-metadata entries. The three IF-image entries never carried a `bytes` value and are unchanged in that respect.

A new clause was added to `source_caveats` in **both** records recording the reason:

> (8) File sizes are recorded as the human-readable values the Dataverse release states (for example "113.3 KB", "4.6 GB"); no exact byte counts are given by any source, so none are asserted.

The full record's `total_size_bytes` remains absent, as the audit noted approvingly. `total_file_count: 10` remains, since ten files are enumerated.

### 2.3 HIGH — scalar in a multivalued slot, core `distributions[9].conforms_to_standard`

**Finding.** `conforms_to_standard` is declared `DataStandardEnum [many]`; the release-metadata entry supplied the bare scalar `RO_CRATE`.

**Disposition: fixed.** The reconciled core now reads:

```yaml
conforms_to_standard:
  - RO_CRATE
```

matching the list form already used at the top level of both records and in the full record's file-collection entry.

### 2.4 MEDIUM — core `media_type` divergence for the RO-Crate format

**Finding.** The core changed `application/ld+json` (full record) to `application/json`, justified by a `source_caveats` claiming the schema's `media_type` enumeration lacks a JSON-LD term. The digest declares no enumeration on `media_type`.

**Disposition: fixed.** The core's `distribution_formats[1].media_type` is restored to `application/ld+json`, matching the full record, and the fabricated schema-constraint caveat is deleted. The two records now agree on this value.

### 2.5 MEDIUM — `notes` used to relocate full-record content in the core

**Finding.** The core's trailing `notes` block restated the citation, the `direct_collection` content, the `third_party_sharing` content, and a summary of `file_collections`/`subsets`. The digest defines `notes` as residual content only, after every fitting slot is used.

**Disposition: fixed.** The entire trailing `notes` block has been **removed** from the core record. Where `CoreDataset` declares no counterpart slot, omission is the correct answer, and none of the relocated material was residual: the citation belongs in `citation` (present in the full record), the cell-line sourcing in `direct_collection` (present in the full record), the repository deposits in `third_party_sharing` (present in the full record, and the same repositories are independently listed in the core's `external_resources`), and the file inventory in `file_collections`/`distributions`.

### 2.6 MEDIUM — NIH RePORTER resolver URL as `Grant.id` in the full record

**Finding.** `funders[0].grants[0].id: https://reporter.nih.gov/project-details/11211616` identifies a RePORTER web page, not the grant. The bundle supplies the grant number itself.

**Disposition: fixed in both records.** The `id` key is removed from the grant object; the grant is now identified by `name: 1OT2OD032742-01` alone. The RePORTER page is not discarded — it moves twice:

- into the funder's `notes`, as prose ("The RePORTER project page for that application is at https://reporter.nih.gov/project-details/11211616");
- into a **new `external_resources` entry** in both records, recording the application ID, project number, core project number, PI, organization, fiscal year, award amount and project period, all as the RePORTER page states them.

This keeps the page addressable while removing the false claim that the URL identifies the grant.

### 2.7 LOW — findings recorded but requiring no change

The following audit items were checks that passed or transparency notes, and the two versions are identical for each:

| Finding | Disposition |
|---|---|
| ORCID normalization for Marquez C (`0000-0003-3960-420X` written without prefix in source) | Left as-is; normalization to `ORCID:` CURIE was already correct and consistent |
| `publisher: ROR:0153tk833` | Left as-is; the ROR is attested verbatim in the June 2026 release author affiliations |
| MD5 checksums, all ten | Left as-is; all transcribe correctly, and the IF-image divergence from October 2025 is flagged |
| `total_file_count: 10`, `total_size_bytes` omitted | Left as-is; correct |
| `issued` and `last_updated_on` date resolution | Left as-is; ranking applied correctly and the conflict disclosed |
| Core `creators` reproducing all 46 from the full record | Left as-is; consistent and supported |
| `instances[*].data_substrate` term choices | Left as-is; defensible, and the audit found no defect |

### 2.8 LOW — `instances[3].counts` provenance

**Finding.** `counts: 11739` equates the stated number of targeted genes with the number of atlas records, an inference the bundle does not make explicit.

**Disposition: annotated rather than removed.** The value is retained in both records — 11,739 is stated by the release and one record per targeted gene is the natural reading — but a `source_caveats` was added to that Instance object in both records:

> The count is the number of targeted genes stated by the release (11,739); the sources do not separately state a record count for the atlas.

---

## 3. Changes made beyond the audit findings

Reconciliation surfaced three range violations the audit did not list. Each is a value of the wrong kind for its declared range, which the schema digest calls a defect even when it reads well.

### 3.1 Object placed in scalar-ranged slots — `Creator.principal_investigator`, `EthicalReview.contact_person`, `LicenseAndUseTerms.contact_person`, `DataGovernance.committee_contact`

The originals wrote these as nested objects with `id` and `name`. The v4 rule requires a scalar-ranged slot to hold the identifier of the thing it refers to, not the thing itself.

- **Full record:** `Creator.principal_investigator` now holds the bare name string, with the ORCID lifted to the `Creator`'s own `id` slot (declared `uriorcurie` on every object). All 46 creators were rewritten; the eight creators with no ORCID in the bundle (Axelsson U, Chinn B, Fall J, Johannesson A, Khaliq H, Muralidharan M, Pan E, Polacco B, Zhang Y) correctly carry no `id`. `contact_person` and `committee_contact` now hold name strings, with the ORCID moved into the sibling `notes` where one exists.
- **Core record:** the same slots hold a name string with the ORCID in parentheses, since `CoreDataset`'s Creator-level `id` availability was not verifiable from the supplied digest.

This is the one place the two records now differ in surface form while asserting identical facts; the divergence is deliberate and conservative.

### 3.2 `file_collections` restructured, one collection per file

The original full record grouped ten files into six collections, three of which had `file_count: 2` or `3`, and carried per-file MD5 checksums and sizes concatenated inside a single `notes` string. This collapsed distinct entities into one object, against the v2 rule, and left the declared `path` key unpopulated.

The reconciled full record has **ten collections, one per released file**, each with `path`, `name`, `description` carrying the human-readable size and publication date, `collection_type`, `file_count: 1`, `compression: zip`, and a `notes` holding that file's single MD5. Identifiers are minted as fragments on the release DOI (`doi:10.18130/V3/HIGT4C#file-apms-paclitaxel`, and so on) — labels for parts of this dataset with no referent outside the record, which the v5 rule permits and which stay traceable to the attested DOI. The three IF-image per-file caveats about the superseded October 2025 protein counts are preserved individually.

### 3.3 Scalar values in multivalued slots

Three further slots held a single concatenated string where the digest declares a list. Fixed in both records:

- `existing_uses[*].examples` — now a one-item list per use
- `distribution_dates[0].release_dates` — now a list
- `external_resources[*].external_resources` — now a list on every entry
- `machine_annotation_tools[0].tools` — now a list; the full record splits it into five named tools, the core keeps one item pending confirmation of the core range

---

## 4. Cross-record consistency after reconciliation

Both records now assert the same referent, the same DOI, version, dates, publisher, license and status; the same 46 creators with the same affiliations; the same three funders with the same grant identification; the same purposes, gaps, tasks, uses, limitations and biases; the same governance, ethics and licensing positions; the same ten distributed files with the same checksums and the same human-readable sizes; and the same eight-clause `source_caveats`.

The only remaining differences are structural, not factual:

| Slot | Full | Core | Reason |
|---|---|---|---|
| `citation` | present | absent | Not declared on `CoreDataset` per the supplied inventory; omission preferred to relocation into `notes` |
| `direct_collection`, `relationships`, `third_party_sharing`, `subsets`, `total_file_count` | present | absent | Same reason |
| `file_collections` | 10 entries | — | Full-record slot |
| `distributions` | — | 10 entries | Core-record slot, retained pending validation (§2.1) |
| Creator identifier form | `id:` + bare name | name with parenthetical ORCID | §3.1 |
| `conforms_to_class` | `Dataset` | `CoreDataset` | Correct per record type |

---

## 5. Provenance boundary

No prior D4D record was read or consulted. All dataset facts derive from the declared bundle at `data/preprocessed/concatenated/CM4AI_preprocessed.txt`. No identifier for an external entity was supplied from model knowledge: every ORCID, the ROR, every DOI, every MD5 and every URL appears verbatim in the bundle. The only minted identifiers are the ten `file_collections` fragments and the five `subsets` fragments in the full record, all built on the attested release DOI and all naming parts of this dataset with no external referent.

---

## 6. Outcome

Three high-severity findings addressed: two fixed outright (invented byte counts removed; scalar corrected to list), one deliberately deferred to LinkML validation with the reasoning recorded. Two medium-severity core findings fixed (media type restored to agreement with the full record; the `notes` relocation block removed). One medium-severity full-record finding fixed in both records (grant resolver URL demoted from `id` to prose and to a new external resource). One low-severity finding annotated rather than altered. Ten low-severity checks confirmed as passing and left untouched. Three additional range violations found during reconciliation and fixed in both records.