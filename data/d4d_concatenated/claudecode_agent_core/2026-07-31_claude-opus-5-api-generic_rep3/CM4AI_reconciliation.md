# CM4AI D4D Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep3/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep3/CM4AI_d4d_core.yaml`

---

## 1. Referent selection

The declared bundle contains four distinct Dataverse release records (March 2025 `B35XWX`, June 2025 `F3TD5R`, October 2025 `K7TGEM`, June 2026 `HIGT4C`), a Nature publication describing a **U2OS** cell map, a bioRxiv project preprint, an NIH RePORTER project record, two project web pages, and a license page.

`Dataset` admits one referent. The referent chosen and held in both records is:

> **Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta)**, DOI `10.18130/V3/HIGT4C`, version 2.0, publication date 2026-06-17, version 2 released 2026-07-15T20:28:19Z, 10 files.

Rationale, stated for the record:

- The bundle's own curation note designates HIGT4C as the **current** CM4AI data release and explicitly marks the sheet-selected K7TGEM (October 2025) as *"superseded upstream."*
- HIGT4C is the only release captured with a verification URL against live Dataverse API metadata.
- The earlier releases carry curation notes identifying them as *"historical supplement"* retained for DOI/checksum/version preservation.

Prior releases are therefore **not** treated as the referent. They appear only in `version_access`, `distribution_dates`, and `errata`, which is where the schema locates superseded-version information.

The **U2OS** cell map of the Nature paper is a related but **distinct** resource. It is not the referent, and no U2OS-specific fact is asserted of this release. See §3.

---

## 2. What the audit found

The audit returned 43 findings: 0 critical, 1 high (resolved as non-defect), 12 medium, 30 low. No fabricated identifiers, DOIs, dates, checksums, file sizes, or affiliations were found — every such value traces verbatim to the bundle.

The defects were **interpretive**, not factual. They clustered into five kinds:

1. **Derived cross-record claims** presented as reported fact (checksum comparison).
2. **Agent-constructed bias categories** not identified as biases by any source.
3. **A whole slot synthesized by reframing** (`discouraged_uses` from `known_limitations`).
4. **Temporal transfer** — May-2024 preprint progress figures applied as 2026 release limitations.
5. **Coverage overstatement** — modality claims exceeding the ten-file listing.

Plus minor precision and fidelity issues (fabricated time components, unsourced defaults, a dropped accent).

---

## 3. What was left as-is, and why

### 3.1 U2OS boundary hedging — retained unchanged

The audit flagged the U2OS hedging pattern only to confirm it had been checked. It is compliant and was **not** altered.

The full record carries U2OS-derived instrumentation, QC, annotation, and confidence-score content in `collection_mechanisms`, `cleaning_strategies`, `labeling_strategies`, and `annotation_analyses`, each prefixed with an explicit disclaimer of the form:

> *"Reported for the related U2OS cell map in the associated Nature publication and not asserted of this release."*

This is the correct handling. The Nature paper is inside the declared bundle and describes methods developed by the same investigators, but it characterizes a different cell line and a different map. Deleting the content would discard evidence that is in the bundle; asserting it unhedged would conflate two resources. The hedge preserves both the evidence and the boundary. Retained verbatim in both records.

### 3.2 The June 2026 / June 17 2025 date discrepancy — retained as an anomaly

The project release page labels HIGT4C the *"June 2026 Data Release"* while displaying *"Released on: June 17, 2025."* Official Dataverse metadata gives publication date 2026-06-17.

Both records surface this in `anomalies` rather than silently selecting one date. `issued` uses the Dataverse-authoritative 2026-06-17. This follows the uniform rule on disagreeing sources: represent what the evidence states, do not merge.

### 3.3 `status: "Beta (interim release)"` — retained

Composite phrasing, but both components are sourced: *"Beta"* from the title, *"This is an interim release"* from the Limitations section. No change.

### 3.4 `compression: zip` — retained

All ten files in the June 2026 listing are ZIP archives. The dataset-level assertion is an aggregation over a complete and uniform file set, not an inference.

### 3.5 Synthetic per-file identifiers in `resources` — retained

The full record mints fragment URIs of the form `https://doi.org/10.18130/V3/HIGT4C#<filename>`. No per-file PID appears in the bundle (Dataverse assigns numeric datafile IDs not exposed in the captured HTML). `Dataset` requires `id`. The fragment URI is derived deterministically from the parent DOI plus the filename as listed, introduces no new factual claim, and is the least-inventive construction available. Retained, with the construction noted here.

### 3.6 Core-record omissions — resolved as non-defects

The audit could not verify the `CoreDataset` slot inventory and flagged five omissions provisionally (`citation`, `relationships`, `direct_collection`, `third_party_sharing`, `total_file_count`) plus one possible validation blocker (`distributions`).

Checked against `data_sheets_schema_core_all.yaml`:

| Slot | On `CoreDataset`? | Disposition |
|---|---|---|
| `distributions` | yes | valid; retained |
| `citation` | no | correctly omitted |
| `relationships` | no | correctly omitted |
| `direct_collection` | no | correctly omitted |
| `third_party_sharing` | no | correctly omitted |
| `total_file_count` | no | correctly omitted |

No change. The core record is a genuine schema-driven projection, not a lossy copy.

### 3.7 `publisher` URI form — retained

`https://dataverse.lib.virginia.edu/` is the repository named as publisher of record in the citation block. URI form is a rendering of a sourced fact.

---

## 4. What was changed

All changes were applied to **both** records where the slot exists in both, keeping the pair consistent.

### 4.1 `anomalies` — removed the derived checksum claim (medium, both records)

**Removed:**

> *"Checksums for the three MDA-MB-468 immunofluorescence archives differ between the October 2025 release and the June 2026 release despite identical filenames and identical reported sizes, indicating the archives were regenerated or altered between releases."*

This was a cross-record MD5 comparison performed by the agent, plus a causal conclusion (*"regenerated or altered"*). The bundle lists the checksums; it never compares them, never characterizes any difference as an anomaly, and never offers a cause. Two layers of inference on top of tabulated values.

The individual checksums remain in `resources` / `distributions` per file, exactly as listed. A reader can perform the comparison; the record does not perform it for them.

The date-discrepancy anomaly (§3.2) and the embargo anomaly are retained — both are stated in the sources.

### 4.2 `known_biases` — reduced from four entries to one (medium, both records)

**Removed three agent-constructed biases:**

- *Antibody- and reagent-dependent coverage in the immunofluorescence modality.* The bundle states HPA antibodies were used and quality-scored; it never frames this as a bias.
- *Targeted-panel selection bias … coverage of the proteome is deliberately non-random.* Panel composition is sourced; the bias framing and the word *"deliberately"* are not.
- *Narrow donor representation … findings therefore carry the genetic background of these two donors.* Donor descriptions are sourced from the preprint; the inheritance conclusion is not.

**Retained the one sourced bias**, which reproduces the release's own *"Potential Sources of Bias"* section:

> Data derived from commercially available de-identified human cell lines; does not represent all biological variants which may be seen in the population at large.

The release document has a bias section. It lists one thing. The record now lists one thing.

### 4.3 `discouraged_uses` — slot removed entirely (medium, both records)

All four entries were reframings of sourced `known_limitations` and `known_biases` content into a usage-recommendation voice the sources never use:

- *"Treating this release as a complete or final resource"*
- *"Integrated cross-modality analysis that assumes full protein overlap"*
- *"Analysis without domain expertise"*
- *"Generalizing findings to population-level human biological variation"*

The bundle distinguishes **Limitations** from **Prohibited Uses** and has no discouraged-uses category. Every underlying fact is already carried, sourced and unreframed, in `known_limitations`, `known_biases`, and `prohibited_uses`. The slot added an interpretive layer and duplicated content. Per the omission-over-inference rule, an absent slot is the correct answer here.

`prohibited_uses` is retained verbatim — the release states it explicitly (no clinical decision-making or patient care without regulatory oversight).

### 4.4 `future_use_impacts` — struck the downstream-inheritance clause (medium, both records)

**Was:** *"…conclusions drawn from downstream AI/ML models trained on these data may inherit that limitation."*

The cell-line bias premise is sourced. The consequence for downstream models is agent inference. The entry now states the sourced premise and stops.

### 4.5 `known_limitations` — qualified the Year-1 progress figures (low, both records)

The entry citing *"17 genes had been endogenously tagged"* and *"SEC-MS identified 72 of 100 targeted chromatin modifiers"* quotes the preprint accurately but presented ~May-2024 Year-1 status as a current limitation of a June-2026 release — roughly a two-year transfer.

**Now reads** as an explicitly time-stamped preprint report of Year-1 progress, not a property of this release.

The adjacent AI-readiness entry was already attributed and hedged; it received the same date stamp for consistency.

The four limitations sourced from the release's own **Limitations** section (interim release; no predicted cell maps; suited to per-dataset bioinformatics analysis; requires domain expertise) are unchanged.

### 4.6 `subpopulations` — corrected two coverage overstatements (low, both records)

- **MDA-MB-468 treated conditions.** Claimed coverage by *"AP-MS, SEC-MS, immunofluorescence imaging, and perturb-seq."* MDA-MB-468 perturb-seq appears in the release **description** but its external link is marked **Embargoed** and no such file appears in the ten-file listing. Perturb-seq is now recorded as *described in the release but externally embargoed and not present as a file in this release*.
- **MDA-MB-468 untreated (DMSO control).** Per-modality coverage was assembled by the agent from the series rather than stated for this release. Now scoped to what the June 2026 listing supports: immunofluorescence images (`cm4ai_ifimages_MDA-MB-468_untreated.zip`), with the mass-spec archive described as covering treatment conditions as the source states.

### 4.7 `data_collectors` — removed two inferred laboratory attributions (low)

- *"(Mali laboratory and collaborators)"* → removed. Prashant Mali is a UCSD co-corresponding author and a perturbation-atlas co-author; no source names a "Mali laboratory" as performing the CRISPR screens. Attribution is now to UCSD, which is sourced.
- *"Ideker laboratory"* for the Tools module → changed to UCSD / CM4AI Tools module. The bundle attributes the module to CM4AI and the software to the `idekerlab` GitHub organization, which is not the same claim.

**Retained unchanged:** *Lundberg Lab at Stanford University* and *Nevan Krogan laboratory at UCSF* — both stated verbatim in the Dataverse file descriptions.

Applied in the full record; the core record's `data_collectors` received the identical correction.

### 4.8 `existing_uses` — removed the download-count entry (low, both records)

**Removed:** *"Recorded Dataverse download counts for the release series indicate active reuse: 181 downloads for the June 2026 release…"*

The counts are verbatim. Reading access metrics as evidence of *use*, and labelling that *"active reuse"*, is inference. Downloads are not documented uses. The counts are not otherwise relocated, as no slot in either schema is a natural home for repository access statistics.

The sourced `existing_uses` content — the CM4AI descriptive preprint, the iPSC Perturbation Cell Atlas preprint (PMCID PMC11580897), and the CodeFest training use — is retained.

### 4.9 Datetime precision (low, both records)

- `issued`: `2026-06-17T00:00:00Z` → `2026-06-17`
- `created_on`: `2025-02-27T00:00:00Z` → `2025-02-27`

Both sources give dates without times. The `T00:00:00Z` suffix asserted a midnight UTC timestamp that no source provides. Both slots accept `date`.

The note that `created_on` (2025-02-27) is identical across all four release records — and so is plausibly a series-level rather than release-level value — is retained in the record's commentary.

### 4.10 `language` and `is_tabular` — removed (low, both records)

- `language: en` — inferred from the language of the documentation, not stated of the data.
- `is_tabular: false` — inferred from the presence of images, mass-spec archives, and sequence data.

Both defensible; neither sourced. Under omission-over-inference, both removed. Modality is already described in prose in `description`, `instances`, and `distribution_formats`.

### 4.11 `conforms_to` — qualified (medium, both records)

**Was:** bare `RO-Crate`.

The June 2025 record itemizes `ro-crate-metadata.json` files and an RO-Crate metadata file type. The June 2026 listing does **not** itemize RO-Crate files; it has `cm4ai_release_metadata.zip`, whose contents are not enumerated. The conformance claim rested on the general project description, not on this release's manifest.

Now records RO-Crate packaging **as described for CM4AI output data generally**, noting that the June 2026 listing does not itemize RO-Crate files and that release metadata is distributed in `cm4ai_release_metadata.zip`. The FAIRSCAPE framework attribution is retained — it is stated in the preprint and the release descriptions.

### 4.12 Accent fidelity (low, both records)

`Bélisle-Pipon` was transliterated as `Belisle-Pipon` in `citation`, `creators`, and `external_resources`. Restored to match the Dataverse citation string. Cosmetic, but the citation block should reproduce the source exactly.

### 4.13 `total_file_count`

Verified as 10 against the June 2026 file listing. **Unchanged** in the full record. Correctly absent from core (§3.6).

---

## 5. Cross-record consistency after reconciliation

| Property | Full | Core |
|---|---|---|
| Referent | June 2026 release, DOI `10.18130/V3/HIGT4C`, V2 | identical |
| Shared slots | — | byte-identical content where the slot exists in both |
| Per-file detail | `resources` | `distributions` |
| Full-only slots | `citation`, `relationships`, `direct_collection`, `third_party_sharing`, `total_file_count` | not defined on `CoreDataset` |
| `discouraged_uses` | removed | removed |
| `known_biases` | 1 entry | 1 entry |

Every change in §4 was applied to both records wherever the slot exists in both. No slot now carries different content in the two files.

---

## 6. Provenance-guard compliance

- No previously generated D4D record was read, opened, grepped, or consulted, from any arm, label, or date. Nothing under `data/d4d_concatenated/` and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was accessed.
- Factual inputs were the declared bundle and the two schema files only.
- Ontology CURIEs appearing in `keywords` (NCIT, EFO, CHEBI, CL, GO, BAO, MeSH, LOINC, SWO) are reproduced from the Dataverse keyword block, not supplied from external knowledge.
- No target slot count was pursued. Twelve slot-level removals or reductions were made; the records are shorter than at Phase 1/2 and correctly so.

---

## 7. Outcome

| | Full | Core |
|---|---|---|
| Populated slots | **62** | **48** |
| Schema validation | **pass** | **pass** |

**Validation commands:**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep3/CM4AI_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep3/CM4AI_d4d_core.yaml
```

**Reconciliation outcome:** 43 findings adjudicated — 1 high resolved as non-defect, 12 medium and 11 low corrected, 19 low retained with rationale recorded above. One slot removed entirely (`discouraged_uses`), two slots removed as unsourced defaults (`language`, `is_tabular`), one slot reduced from four entries to one (`known_biases`), and eight slots corrected or qualified. Both records validate. Referent selection is coherent and identically held across the pair.