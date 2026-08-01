# Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d_core.yaml`

---

## 1. Referent

`Dataset` admits a single referent. The declared bundle contains five distinct Dataverse releases in the CM4AI series (B35XWX, F3TD5R, K7TGEM, HIGT4C) plus a separate U2OS cell-map study published in *Nature*. The referent held across both records is:

> **Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta)**, DOI `10.18130/V3/HIGT4C`, Dataverse version 2.0 / citation V2, published 2026-06-17, version 2 released 2026-07-15T20:28:19Z, ten files.

This is the current release identified by the bundle's own curation annotation, and it supersedes the October 2025 release (K7TGEM) that the input sheet had selected. Earlier releases in the series are represented as historical context, not as the referent. The *Nature* U2OS study is represented only under `external_resources` with an explicit scope note; it describes a different dataset in a different cell line and contributed no factual content to either record.

---

## 2. Audit findings, in summary

Both records were found substantially well grounded. File inventories (names, byte sizes, MD5 checksums, per-file publication dates), DOIs, release dates, the creator roster with ORCIDs and affiliations, licensing terms, governance contacts, and the producers' own statements on completeness, limitations, prohibited uses and potential bias all track the sources closely and frequently verbatim. Several handling decisions were confirmed correct and left untouched: the hedging of portal-level aggregate counts, the explicit surfacing of the Sali affiliation conflict, the documentation of the imaged-protein count discrepancy across releases, the flagging of the portal/Dataverse release-date inconsistency, and the quarantining of the *Nature* U2OS paper.

The audit returned forty-two findings: one high, sixteen medium, twenty-five low. They fall into four classes.

1. **A structural defect in the core record.** The core record carried a slot named `distributions`, which has no counterpart in the full-schema `Dataset` inventory. This was the only finding capable of causing a validation failure or silent content loss.
2. **Core omissions of bundle-supported content** that the full record carried, producing an unmotivated asymmetry between the paired records.
3. **Unstated inferences** presented as fact — chiefly `language`, `is_tabular`, one unqualified choice between two variant institution lists, and a small number of attributions and analytic claims not made by any source.
4. **Minted identifiers** on subordinate objects, where the schema requires an `id` but the bundle supplies none.

No finding indicated reuse of a prior D4D record, and no content was traced to any source outside the declared bundle.

---

## 3. Changes to the core record

### 3.1 `distributions` → `file_collections` (high severity, resolved)

The core schema (`data_sheets_schema_core_all.yaml`, class `CoreDataset`) was inspected directly. It defines no slot named `distributions`. The content was migrated to `file_collections`, which the core schema does define, and restructured to the `FileCollection` shape. The migration recovered the `file_count` integers that the ad-hoc `distributions` structure had dropped, and restored the structured collection identifiers.

This was the single change that could not be deferred: left in place, the slot would have failed validation or been discarded without warning.

### 3.2 Restored omissions

Six slots present in the full record and exposed by the core schema had been omitted from the core record despite clear bundle support. All six were restored, in each case by carrying forward the full record's content unchanged:

| Slot | Evidence basis for restoration |
|---|---|
| `citation` | Recommended citation appears verbatim on the Dataverse landing page. |
| `total_file_count` | "1 to 10 of 10 Files"; consistent with the sum of `file_collections[].file_count`. |
| `relationships` | PPI edges from AP-MS and SEC-MS; containment relations in the hierarchical cell-map DAG; perturbation-to-phenotype relations. |
| `variables` | Eight descriptors: cell line, differentiation state, treatment condition, four IF channel definitions, targeted gene. |
| `third_party_sharing` | Five distinct arrangements documented in the bundle, including deposition to MassIVE, SRA, Figshare and NDEx, and the non-commercial redistribution restriction. |
| `direct_collection` | "Human Subjects: No"; "De-identified Samples: Yes"; cell-line provenance from ATCC and HipSci; the KOLF2.1J MTA condition. |

The `direct_collection` restoration matters most: `is_deidentified` and `human_subject_research` carried part of this content, but the third-party sourcing of the cell lines and the MTA condition existed only in the full record.

### 3.3 `resources` retained rather than realigned to `subsets`

The audit flagged the full record's use of `subsets` (`DataSubset`) against the core record's use of `resources` (`Dataset`) for the same seven cell-line/condition partitions. Inspection resolved this as a schema difference rather than an authoring inconsistency: `CoreDataset` exposes `resources` and does not expose `subsets`. `resources` is therefore the only available carrier and was retained. The mapping between the two slots is recorded here so the divergence is traceable rather than surprising.

---

## 4. Changes applied to both records

### 4.1 `language` removed

Value `en` was not stated anywhere in the bundle. No Dataverse language field, no explicit declaration. It was an inference from the language of the source documents. Under the governing rule — prefer omission over inference; an absent slot is a correct answer when the evidence is absent — the slot was removed from both records.

### 4.2 `is_tabular` removed

Value `false` was likewise unstated. The inference from content (ZIP archives of TIFF images, mass-spectrometry crates, RO-Crate metadata) is near-certain, but no source characterises the dataset's tabularity. Removed from both records for consistency with the same rule. The underlying facts remain fully recoverable from `file_collections` and `distribution_formats`.

### 4.3 `description` amended for institution-list variance

The bundle contains two collaborating-institution lists that do not agree:

- cm4ai.org/data-releases: "UCSD, UCSF, Stanford, UVA, Yale, UT Austin, UA Birmingham, Simon Fraser University, and the Hastings Center"
- March 2025 Dataverse description: the same list **without UT Austin**

Both records had adopted the first variant silently. This was inconsistent with the treatment applied elsewhere in the same records to the Sali affiliation conflict, where disagreement is surfaced rather than resolved. The description in both records now states the fuller list and notes that an earlier Dataverse description omits UT Austin, without adjudicating between them.

### 4.4 `instances` — portal aggregates removed

The final `instances` entry reproduced project-wide portal figures (1,374 protein interactions; 53,788 immunofluorescent images; 7,023 proteins; 11,739 genes targeted) with an explicit hedge that they are not verified as release-specific. The hedge was adequate, but the placement was not: figures sitting inside `instances` invite reading as instance counts for this release, which they are not. They are current project-wide "Data Insights" spanning all releases and all cell lines.

The entry was removed from `instances` in both records. The same figures remain in `description`, where they retain their hedge and their project-level framing, so no evidence was lost.

### 4.5 `known_biases` — confounding claim re-attributed

The donor facts are bundle-supported (MDA-MB-468: 51-year-old Black female, metastatic mammary adenocarcinoma; KOLF2.1J: healthy male Northern European donor). The sentence "Ancestry, sex and disease context are therefore confounded with cell line identity" is the record's own synthesis, adjacent to but exceeding the producers' stated caveat about derivation from commercially available cell lines. The wording in both records now presents the donor characteristics as sourced and the confounding as an implication drawn in this datasheet, not as a producer statement.

### 4.6 `data_collectors` — unsupported laboratory attribution removed

Perturb-seq screen generation had been attributed to "University of California San Diego (including the Mali laboratory and collaborators)". No source in the bundle names a generating laboratory for the CRISPR screens; the parenthetical was inferred from authorship on the perturbation-atlas preprint. This contrasts with the explicit "Lundberg Lab at Stanford University" and "Nevan Krogan laboratory at the University of California San Francisco" attributions that appear verbatim in Dataverse file descriptions. The parenthetical was removed from both records; the UCSD attribution, which the bundle does support, was retained.

### 4.7 `sampling_strategies` — design target qualified by reported achievement

Both records stated the CM4AI design as 100 chromatin modifiers and 100 metabolic enzymes, which is accurate to the preprint's stated objective. The same preprint reports Year 1 achievement as 17 genes endogenously tagged in MDA-MB-468 with 34 more in progress, and SEC-MS identification of 72 of 100 chromatin modifiers. Both figures now appear, so the design target is no longer presented as coverage. `known_limitations` had covered this only partially.

### 4.8 `conforms_to_schema` — temporal scope noted

The FAIRSCAPE / RO-Crate / JSON-LD / ARK description derives from the 2024 preprint. The June 2026 release ships a metadata archive but does not expose its internal schema in the bundle. A scope note now records that the packaging framework is described as of the preprint rather than verified against this release.

### 4.9 `anomalies` — fourth count variant added (full record)

The imaged-protein count discrepancy already covered 563 (March 2025), 464 (June 2025, October 2025, June 2026) and 523 (portal). The CM4AI preprint's Year 1 statement — 100 chromatin regulators mapped with roughly 500 further proteins pending — was added, completing the picture of how the imaged-protein figure has moved across the project's own documentation.

### 4.10 `errata` — inferential wording softened

The observation that `(2025-06-30)` terminates the June 2025, October 2025 and June 2026 descriptions alike is directly verifiable. The causal reading — that the text was carried forward — is inference, though well grounded. The entry now separates the observation from the reading.

---

## 5. Findings deliberately left unchanged

### 5.1 Minted identifiers on subordinate objects

`DataSubset`, `Dataset` and `FileCollection` each require an `id`. The bundle supplies no per-subset or per-collection identifiers; Dataverse assigns identifiers only at dataset level. Fragment URIs constructed on the release DOI (for example `https://doi.org/10.18130/V3/HIGT4C#apms`) were therefore minted.

These were retained. Populating a required structural slot with a locally-scoped, deterministically constructed identifier is a schema obligation, not a factual assertion about the world: the fragment makes no claim beyond "this object belongs to that dataset," which is true. The alternative — omitting the objects entirely to avoid minting — would discard substantial well-evidenced content, including the complete file inventory with checksums. The minting convention is recorded here so no reader mistakes these for identifiers the producers issued.

### 5.2 Synthesised time components on date-only fields

`created_on` and `issued` derive from Dataverse fields that supply a date only (Data Creation Date and Deposit Date 2025-02-27; Publication Date 2026-06-17). The `T00:00:00Z` components exist solely to satisfy the `datetime` range. Retained as a range-conformance artefact, not as a claim about time of day. `last_updated_on` (2026-07-15T20:28:19Z) carries a genuine timestamp and required no synthesis.

### 5.3 `created_by`

The bundle names a Depositor (Niestroy, Justin) and a Point of Contact (Ideker, Trey) but no single party "primarily responsible for creating the resource." The project-level attribution to CM4AI as the Functional Genomics Data Generation Project of NIH Bridge2AI is a defensible synthesis and the closest available reading of the slot's intent. Retained; the synthesis is noted here.

### 5.4 `publisher`

`https://dataverse.lib.virginia.edu` encodes "University of Virginia Dataverse" / "LibraData" as a `uriorcurie`. The host URL is not itself asserted as a publisher identifier in any source, but it is the correct dereferenceable form of the named publisher. Retained.

### 5.5 ROR resolution in `creators`

The June 2026 Dataverse record gives `https://ror.org/0153tk833` for Clark, Al Manir, Levinson, Niestroy and Ratcliffe, where earlier releases spell out "University of Virginia". Resolving the ROR to the spelled-out name is a benign normalisation supported by the earlier releases in the same bundle. Retained.

### 5.6 `compression: zip`

Correct for this release — all ten files are ZIP archives. Prior releases in the series included JSON and HTML files. Since the referent is the June 2026 release specifically, the value stands; the scoping is noted so it is not read as a property of the series.

### 5.7 `total_file_count: 10`

Verified against both the page listing ("1 to 10 of 10 Files") and the sum of `file_collections[].file_count` (2+3+2+2+1). Consistent in both records following the core restoration in §3.2.

### 5.8 `machine_annotation_tools` — MUSE attribution

The CM4AI preprint cites Bao *et al.*, "Integrative spatial analysis of cell morphologies and transcriptional states with MUSE," as the reference for the co-embedding step, while describing the step inline as contrastive deep learning. The attribution is bundle-grounded. Retained.

### 5.9 `external_resources` — *Nature* U2OS scope note

Confirmed correct. The note states plainly that the paper describes a different dataset in a different cell line (U2OS; 5,147 proteins; 275 assemblies; 20,660 images) and is included as methodological background. No U2OS figures leaked into any factual slot of either record. Specifically confirmed: `acquisition_methods` follows the CM4AI preprint's endogenous tagging, not the *Nature* paper's lentiviral ORFeome expression. Left as written.

### 5.10 `status`

"Dataverse version 2.0 / citation version V2" is supported by both the page header and the citation string, and is consistent with `version: 2.0`. Recorded as a passed consistency check.

---

## 6. Net effect

| Record | Slots removed | Slots added | Slots renamed | Within-slot amendments | Net slot delta |
|---|---|---|---|---|---|
| Full | 2 (`language`, `is_tabular`) | 0 | 0 | 7 | −2 |
| Core | 2 (`language`, `is_tabular`) | 6 (restored) | 1 (`distributions` → `file_collections`) | 6 | +4 |

Both records were re-validated after reconciliation:

- Full — `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` → pass
- Core — `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` → pass

The two records now agree on referent, on every shared factual claim, and on the treatment of every source disagreement. Remaining structural differences between them are attributable to slot availability in the respective schemas and are documented in §3.3.

---

## 7. Provenance boundary

No previously generated D4D record was read, opened, searched or consulted at any phase. Nothing under `data/d4d_concatenated/` outside this run's own two output paths was accessed, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was accessed. All factual content derives from the declared bundle; all structural decisions derive from the two schema files. The audit found no evidence to the contrary.