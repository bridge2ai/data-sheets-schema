# Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/CM4AI_crate_only.txt`
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d_core.yaml`

---

## 1. Referent declaration

Both records take as their single `Dataset` referent the **top-level June 2026 release crate**:

```
https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release
"Cell Maps for Artificial Intelligence - June 2026 Data Release (Beta)", version 1.0,
datePublished 2026-06-30, DOI 10.18130/V3/HIGT4C
```

The nine component crates (two AP-MS, three IF-imaging, two SEC-MS, two perturb-seq) are expressed as `resources`, not as alternative referents. The January 2026 and October 2025 release identifiers appear in the bundle only as `isPartOf` targets on component crates; they are represented as *relationships*, never merged into the referent. This choice is held identically in both records and was re-verified in Phase 4.

---

## 2. What the audit found

Fifteen findings: **zero high**, **zero medium**, **thirteen low**, **two informational**.

No fabricated facts were detected. Every substantive claim sampled traced to the declared bundle — the entity counts (55,859 total / 53,877 datasets / 1,976 computations / 6 software / 20 schemas), both size representations (19.9 TB and 21,051,331,945,400 bytes), the DOI, the 47-author roster with ORCIDs and affiliations, the nine component crates with their per-crate sizes, versions, MD5s, MassIVE accessions and the CC0 / CC-BY-NC-SA licence split, the full set of `rai:*` strings, the human-subject exemption, `d4d:informedConsent`, `d4d:atRiskPopulations`, and the checksum-coverage (8/55,859) and zero-summary-statistics gaps from `ai_ready_score.json`.

No prior-D4D reuse was detected. The two withheld D4D-shaped artifacts (`CM4AI_crate_d4d.yaml`, `ro-crate-linkml.yaml`) and the withheld `ro-crate-datasheet.html` leave no detectable fingerprint: nothing in either record asserts a fact absent from `CM4AI_crate_only.txt`.

The findings cluster into four kinds:

| Kind | Count | Example |
|---|---|---|
| Over-specification beyond the evidence | 3 | funder glosses; expanded personal names; the "465 antibody entries" reading of an `id_families` key |
| Normalization asserting unstated precision | 4 | timezone coercion on date-only values; diacritic loss; silent name correction; EDAM topics folded into `keywords` |
| Supported omission | 4 | `related_datasets`; dataset-level `page`; MassIVE publisher; one unaccounted collection timeframe |
| Full/core pairing divergence with no factual conflict | 2 | resource-level `keywords` present in core, absent in full |
| Informational (no defect) | 2 | core-record slot relocation into prose; referent consistency confirmation |

---

## 3. Changes applied

### 3.1 Both records

**Removed the "465 antibody entries" interpretation.**
The normalizer reports `id_families: {"b2ai": 465}` for each IF-imaging crate. Nothing in the bundle says what those entities are. The gloss "465 B2AI antibody/protein entries per condition" was replaced with a neutral statement that each imaging crate's part inventory includes 468 experiment entities, 465 entities under a `b2ai` identifier family, and three stain entities, alongside the directly stated 464 proteins of interest. The 464 figure comes from the crate `description` and is retained verbatim.

**Stripped funder characterizations.**
`1OT2OD032742-01 (the Bridge2AI CM4AI award…)` and the "instrumentation award" label on `#S10 OD026929` were removed. The bundle supplies only a flat funder string with agency groupings and award numbers; the grantor/identifier decomposition is retained because it is a faithful parse, but the added interpretation is not.

**Reverted name expansions.**
`Prashant Mali laboratory` → `Mali, P` with the crate contact email `pmali@ucsd.edu` recorded as the contact, and the lab-ownership attribution dropped: the perturb-seq crates name a 22-person author list and no laboratory. `Emma Lundberg` → `Lundberg, E`, contact `emmalu@stanford.edu`.

**Preserved the source spelling in `ethical_reviews`.**
Now rendered as `Vardit Ravistky` — the literal `ethicalReview` value — with a parenthetical noting the Person entity `Ravitsky, V` (ORCID `0000-0002-7080-8801`). The reader can see both the source string and the near-certain intended referent without the record silently overwriting evidence.

**Restored the diacritic.**
`Belisle-Pipon JC` → `Bélisle-Pipon JC` throughout, so that the citation string, `creators`, and the core record's `external_resources` citation entry are byte-faithful to the bundle.

**Completed `collection_timeframes`.**
A third grouping was added for the SEC-MS KOLF2 neuronal/cardiomyocyte differentiation crate (`9/1/2022`–`6/1/2026`), which previously fell into neither the `1/31/2026` nor the `10/13/25` partition. All three `rai:dataCollectionTimeframe` end-dates present in the bundle are now accounted for, and the record states which component crates carry which.

**Populated dataset-level `page`.**
Set to `https://doi.org/10.18130/V3/HIGT4C`, the persistent identifier the bundle gives in both the crate `identifier` field and the `ai_ready_score.json` findability assertion. `https://dataverse.lib.virginia.edu/` remains recorded as the publisher.

**Added `related_datasets`.**
The `isPartOf` edges are now typed rather than narrated:

- the October 2025 release crate,
- the January 2026 release crate,
- the CM4AI project record and the UC San Diego organization record.

Each entry carries both required keys (`relationship_type`, `target_dataset`). The prior prose in `external_resources` and `version_access` was trimmed to avoid duplicating the same statement in two registers.

**Aligned resource-level `keywords`.**
The full record now carries `keywords` on all nine component resources, matching the core record. Both variants were bundle-supported; the divergence was a pairing defect. Every keyword value is copied from the corresponding component crate's own `keywords` array.

### 3.2 Core record only

**Removed the constructed `https://figshare.com/` publisher URI.** See §3.3 for the reasoning, which departs from the audit's recommendation.

---

## 3.3 Deviation from an audit recommendation

The audit recommended (a) replacing the fabricated `https://figshare.com/` with the literal `FigShare`, and (b) adding `publisher: MassIVE` to the two MassIVE-hosted SEC-MS resources.

Both recommendations were **partially declined** and resolved differently, for one shared reason: `publisher` has range `uriorcurie`, and the bundle gives these two publishers only as bare labels — `"FigShare"` and `"MassIVE"` — with no URI anywhere in the evidence. Substituting a bare label would either fail validation or, if it passed, would encode a non-identifier in an identifier slot. Manufacturing a URI is what created the defect in the first place.

Resolution applied to both records:

- the constructed `https://figshare.com/` was **removed** from the perturb-seq resource;
- the publisher names `FigShare` and `MassIVE` are recorded as literal text on the relevant resource entries (in `description`, and in the core record's `distribution_formats` where the MassIVE distribution channel was already described);
- the MassIVE accessions and FTP/query URLs that *are* URIs in the bundle (`MSV000101915`, `MSV000101917`, `MSV000100676`, `ftp://massive-ftp.ucsd.edu/v10/MSV000098237/`, and the two `massive.ucsd.edu` query URLs) remain in place unchanged.

Net effect: the publisher facts the audit wanted surfaced are now present in both records, and no slot carries a value the bundle does not contain.

---

## 4. What was left as-is, and why

**EDAM topic labels in `keywords` (`Proteomics`, `RNA-Seq`, `Functional genomics`).**
Left in place. The values are bundle-supported — they are the `name` fields of DefinedTerms in the crate's `about` block — and `keywords` is the schema's only discovery-term slot at dataset level; there is no `subject` slot to move them to. The crate's own `keywords` array already mixes casing variants of the same concepts (`machine learning` / `Machine learning`), so the addition does not distort the term set. The provenance distinction is recorded here rather than in the record. The MeSH and Cellosaurus DefinedTerms remain where they were, as subject annotations rather than keywords.

**Timestamp coercion on `issued` and `resources[*].issued`.**
Left as-is. The slot range is `datetime`; the bundle gives date-only values (`2026-06-30`) and, on the three IF crates, an ambiguous `02/28/2025`. Emitting `2026-06-30T00:00:00+00:00` and `2025-02-28T00:00:00+00:00` is the only way to satisfy the range. The US month/day reading of `02/28/2025` is unambiguous (28 cannot be a month). The added time-of-day and UTC offset carry no evidentiary weight and should be read as datatype padding, which is why the fact is flagged here rather than corrected in the record. Where the bundle supplies genuine timestamps — the two AP-MS crates and the SEC-MS differentiation crate — those are transcribed exactly, including sub-second precision and offset.

**Core-record relocation of full-record slots into prose** (citation, byte total, third-party sharing, instance relationships, direct collection).
Left as-is; classified informational by the audit. The core record is a condensed rendering, and no factual divergence from the full record was detected in any of the five relocated items. The byte total appears in the core `description` as `21,051,331,945,400 bytes (19.9 TB as stated by the crate)`, matching the full record's `total_size_bytes` exactly.

**Two size representations retained side by side.**
The crate states `contentSize: "19.9 TB"` and `evi:totalContentSizeBytes: 21051331945400`, which do not reconcile under either the decimal or binary convention. Both are reported, attributed, and left unreconciled, per the rule against silently selecting among disagreeing sources.

**Per-crate licence heterogeneity.**
The top-level crate is CC-BY-NC-SA-4.0; the two AP-MS crates and the SEC-MS differentiation crate are CC0-1.0. This is not an error to resolve — it is a fact about the release — and both records state the dataset-level licence and the per-resource exceptions explicitly.

**Embargo and completeness language.**
The `url: "Embargoed"` on the perturb-seq raw sequence crate, the `completeness` string, and `rai:dataCollectionMissingData` are transcribed rather than harmonized, even though they overlap heavily in wording across all ten crates. Compressing them would have obscured that the statement is asserted independently at each level.

---

## 5. Post-reconciliation state

| | Before | After | Δ |
|---|---|---|---|
| Full record — populated top-level slots | 63 | 65 | +2 (`related_datasets`, `page`) |
| Core record — populated top-level slots | 41 | 43 | +2 (`related_datasets`, `page`) |
| Slots removed | — | — | 0 |
| Slots with corrected values | — | — | 7 full / 7 core |

Value-level corrections (not slot-count changes): `funders`, `data_collectors`, `maintainers`, `ethical_reviews`, `citation`/`creators` (diacritic), `collection_timeframes`, `instances`; plus `resources[*].keywords` alignment in the full record and the publisher-URI removal in the core record.

**Validation**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d.yaml
→ PASS (0 errors)

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d_core.yaml
→ PASS (0 errors)
```

All object-range entries satisfy their required keys: `DatasetRelationship` entries carry `relationship_type` + `target_dataset`; `RawDataSource` entries carry `source_description`; `FileCollection` and nested `Dataset` entries carry `id`; `VariableMetadata` entries carry `variable_name`. Enum-ranged slots carry only permitted values; `compression` is unpopulated, as the bundle's `evi:formats` list (`fastq.gz`, `.d`, `h5ad`, …) describes file formats rather than a dataset-level compression scheme.

**Provenance record**

```
poetry run d4d provenance record --project CM4AI \
  --method claudecode_agent_crate_only \
  --label 2026-07-31_claude-opus-5-api-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
→ recorded
```

---

## 6. Provenance attestation

No previously generated D4D record was read, opened, grepped, or consulted at any phase. Nothing under `data/d4d_concatenated/` was accessed, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was accessed. The only factual inputs were `data/preprocessed/concatenated/CM4AI_crate_only.txt` and the two schema files, which were consulted for structure only.

Three artifacts declared withheld by the bundle header — `CM4AI_crate_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html` — were not present in the bundle and were not sought.

## 7. Outcome

**Reconciled.** Both records validate clean, hold a single consistent referent, and after the changes above contain no claim unsupported by the declared bundle. Residual imprecision is confined to datatype coercion on three date values, documented in §4, and to the keyword/subject-term conflation, documented in §4 and traceable to the schema's slot inventory rather than to the evidence.