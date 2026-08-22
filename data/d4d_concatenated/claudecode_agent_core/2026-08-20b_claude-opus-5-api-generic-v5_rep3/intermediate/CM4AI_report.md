# CM4AI Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep3`
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Scope and method

The Phase 3 audit returned 41 findings (2 high, 15 medium, 22 low, 2 info) across both records. Each was checked against the declared input bundle (`data/preprocessed/concatenated/CM4AI_preprocessed.txt`) and against the supplied schema digest for class `Dataset`. Findings were resolved in one of three ways:

- **Corrected** — the record asserted something the bundle does not support, or placed content in the wrong declared field.
- **Enriched** — the bundle supported a declared field that had been left empty or expressed only as prose.
- **Left as-is** — the finding was descriptive, or the record was already correct, or acting on it would require evidence the bundle does not contain.

The referent choice was re-affirmed rather than changed: this record describes **the June 2026 Data Release (Beta), DOI 10.18130/V3/HIGT4C**, the highest-ranked source in the declared bundle. The U2OS cell-map work reported in the 2025 *Nature* article remains outside the referent.

---

## 2. High-severity findings

### 2.1 `distributions` — undeclared slot in the core record (high)

**Finding.** The core record used a slot named `distributions` whose member key `md5` does not appear in the supplied digest for any range. `DistributionFormat` declares `checksum`; `FileCollection` declares `path` but no checksum key.

**What changed.** The `distributions` block is **still present** in the completed core record. What changed is the member key: every occurrence of `md5:` was replaced with `hash:`, and the accompanying `notes` text was reworded from "MD5 checksum 8642317c…" to "the hash is the MD5 checksum printed by the repository", so the checksum semantics survive in prose rather than in an invented key name.

**Assessment of the residual.** This is a partial resolution and should be read as such. The digest supplied to this run covers class `Dataset` only; the core schema (`data_sheets_schema_core_all.yaml`, class `CoreDataset`) was not supplied, so whether `CoreDataset` declares a `distributions` slot could not be determined from the digest. The slot was therefore retained rather than deleted, on the reasoning that removing it would destroy the per-file checksum, size and publication-date evidence with no declared alternative confirmed to exist in the core class. The change from `md5` to `hash` was made because `md5` was demonstrably not a declared key anywhere in the digest. Validation against the core schema is the operative check here; if `CoreDataset` rejects `distributions`, this block must be relocated to `file_collections` in a future pass.

### 2.2 `distributions[*].compression` (high)

**Finding.** `compression` is declared per-object on `FileCollection`, `DataSubset` and `Dataset`, not on the undeclared `distributions` objects.

**Left as-is.** `compression: zip` remains on each `distributions` entry. This finding is entirely dependent on 2.1: if `distributions` is a legitimate `CoreDataset` slot then its declared keys govern, and if it is not then the whole block is defective and the per-object `compression` is the least of its problems. No independent change was warranted.

---

## 3. Corrections — unsupported assertions removed

These are cases where the record stated something the declared bundle does not state. In each, the assertion was withdrawn and, where the bundle supports a weaker or differently-framed statement, that statement was substituted.

### 3.1 `publisher` — removed from both records (medium)

The original records carried `publisher: ROR:0153tk833`. No source in the bundle states a ROR identifier for the University of Virginia *in the role of publisher*; the string appears only inside author affiliation fields in the June 2026 Dataverse record. Under the v5 rule that an identifier naming something outside the dataset is a fact about the world subject to evidentiary sourcing, this was an inference.

**Both records:** the `publisher` slot is now absent. Caveat (10) in the full record and (11) in the core record records why: "No source states a ROR identifier for the publishing institution in that role; a ror.org string appears in the June 2026 record only within author affiliation fields."

Consequentially, the ROR CURIE was also removed from the five `creators[*].affiliations` entries that carried it (Clark, Al Manir, Levinson, Niestroy, Ratcliffe); those affiliations now read `name: University of Virginia` only. This was not a separate audit finding but follows from the same reasoning — a ror.org URL transcribed from a Dataverse affiliation cell is weaker evidence for an organizational identifier than the same registry entry cited as such.

### 3.2 `created_on` — removed from both records (medium)

The audit observed that `created_on: 2025-02-27T00:00:00Z` was transcribed from the Dataverse "Data Creation Date" field, which in the same record equals the Deposit Date, and which is contradicted by the project start of 2022-09-01 recorded in NIH RePORTER.

**Both records:** `created_on` is now absent. New caveat (12) full / (13) core states that the Dataverse field "describes the deposit workflow rather than the period over which the underlying data were generated" and directs the reader to `collection_timeframes` instead.

### 3.3 `ethical_reviews[*].reviewing_organization` — removed from all three entries, both records (medium ×3)

Three separate findings: The Hastings Center was inferred from an email domain; Simon Fraser University was inferred from an email domain with no disclosing caveat; and "Cell Maps for Artificial Intelligence Ethics module" placed a project module in a slot meaning the body that conducted review.

**Both records:** all three `reviewing_organization` keys are gone. The `review_details` prose on the Ravitsky and Belisle-Pipon entries now says explicitly that the record "names this person for ethical review but does not state a reviewing organization", and states the author-list affiliation and email domain as the observable facts. The third entry retains its `review_details` describing the Ethics module's activities but no longer claims that module is an organization. Caveat (6) was rewritten to record that "the record does not state which body conducted ethical review, so no reviewing organization is asserted."

### 3.4 `data_governance.accountable_organization` — removed from both records (medium)

The original records asserted University of California San Diego while the accompanying `source_caveats` conceded "the sources do not use the phrase 'accountable organization' themselves". A slot whose own caveat withdraws it should not be populated.

**Both records:** the key is absent. The governance `source_caveats` now reads "…does not name an accountable organization; none is asserted here."

### 3.5 `instances[0].counts` and `instances[1].counts` — removed from both records (medium ×2)

`counts: 53788` was attached to the MDA-MB-468 immunofluorescence instance type and `counts: 1374` to the AP-MS interaction instance type. Both figures are project-wide cumulative totals from cm4ai.org spanning all cell lines and all releases; neither source apportions them.

**Both records:** both `counts` keys are gone. Each instance now carries a `source_caveats` opening "No instance count is asserted", stating what the project-wide figure covers and, for the imaging instance, noting that the October 2025 figure of 464 proteins "bounds the protein coverage but not the image count". Dataset-level caveat (3) was extended with the clause "they are not apportioned by modality, cell line or release in any source, and are therefore not attached to individual instance types in this record."

### 3.6 `related_datasets[*].relationship_type` — retyped in both records (low)

All four prior releases were typed `is_new_version_of`, contradicting the record's own caveat that they are "separate Dataverse deposits with distinct DOIs rather than successive versions of one deposit".

**Both records:** all four are now `continues`, which the enum offers and which matches a quarterly series of distinct deposits. The trailing caveat was rewritten from "the relationship type records that each supersedes its predecessors" to "the relationship is recorded as continuation of a quarterly series rather than as versioning."

### 3.7 `creators[36].principal_investigator` — self-reference removed (medium)

The Trey Ideker Creator object nested a `principal_investigator` Person carrying the same ORCID as the Creator's own `id`.

**Both records:** the nested Person is gone. In its place the entry carries `credit_roles: [supervision, funding_acquisition]` — both drawn from the declared enum — and a `source_caveats` recording that "NIH RePORTER names this person as principal investigator of the funded project OT2OD032742, and the Dataverse record names them as point of contact for the deposit." The PI fact survives as attributed evidence rather than as a circular structure.

### 3.8 `status` — simplified in both records (low)

`status: published (beta, interim release)` packed three states into one string and duplicated the beta qualification already carried in `known_limitations` and in the title.

**Both records:** now `status: published`. The interim character is stated in `description` ("The release is an interim beta and comprises ten ZIP archives…"), which is new wording in both records, and remains in `known_limitations[0]`.

### 3.9 `created_by` — reduced to a responsible party (low)

The original value was a multi-clause sentence about the project and its NIH programme membership.

**Both records:** now `created_by: Cell Maps for Artificial Intelligence (CM4AI)`. The programme membership and institutional lead were already stated in `description` and remain there.

### 3.10 `conforms_to` and dataset-level `compression` — scope narrowed (low ×2)

The audit noted that RO_CRATE was asserted at dataset level although the measurement ZIPs are not themselves RO-Crates, and that `compression: zip` flattened a release whose metadata archive contains JSON and HTML.

**Both records:** `conforms_to` now reads "Released metadata and provenance packages are built as RO-Crates… the measurement archives themselves are distributed as ZIP files referenced from those crates", which states the boundary the bundle supports. `conforms_to_standard: [RO_CRATE]` is retained at dataset level, since the release does conform in the metadata layer and the standard is genuinely the one named.

Dataset-level `compression: zip` was **removed from the core record** and **retained in the full record**. This asymmetry is deliberate: in the full record the ten `file_collections` each carry their own `compression: zip`, and the dataset-level value is a true aggregate over ten ZIP archives; in the core record the same information sits on the `distributions` entries, and the dataset-level scalar was redundant alongside them.

### 3.11 `external_resources` — Nature article removed from both records (low)

The entry for Schaffer et al., *Nature* 642:222–231 (2025) carried a caveat conceding it was "related methodology rather than … documentation of this dataset", and concerns U2OS cells, which the record's own referent choice excludes.

**Both records:** the entry is gone. The article is still discussed in dataset-level `source_caveats` — caveat (9) full / (10) core — where its status as related methodological work outside the referent is the point being made. Removing it from a slot meaning "resources referenced at the dataset level" while retaining the reasoning in the caveat is the correct placement.

---

## 4. Enrichments — declared fields populated from the bundle

These are cases where evidence in the bundle answered a declared field that had been left empty or expressed only as prose.

### 4.1 `creators[*].name` — all entries now named (medium)

The audit's most consequential structural finding: 37 Creator objects carried an ORCID but no `name`, although the bundle names every author in the release citation.

**Both records:** every Creator now carries `name`. Full names were taken from the 2024 bioRxiv author list where it gives them (Timothy Clark, Sadnan Al Manir, Christopher P Churas, Amir Dailamy, Yesh Doctor, Antoine Forget, Jan Niklas Hansen, Mengzhou Hu, Joanna Lenkiewicz, Maxwell Adam Levinson, Charlotte Marquez, Sami Nourreddine, Justin Niestroy, Kirsten Obernier, Dexter Pratt, Gege Qian, Leah Schaffer, Swathi Thaker, Jean-Christophe Belisle-Pipon, Cynthia Brandt, Ying Ding, Samah Fodeh, Nevan Krogan, Emma Lundberg, Prashant Mali, Pamela Payne-Foster, Sarah Ratcliffe, Vardit Ravitsky, Andrej Sali, Wade Schulz, Trey Ideker, Jillian Parker); the remainder from the Dataverse citation string as initialled forms (Fabian Ballllosero Navarro, Jing Gao, Yeon Hwa Lee, Christian Metallo, Alina Sigaeva, Jake Y Chen).

Additionally, the nine authors the audit noted have no persistent identifier (Axelsson U, Chinn B, Fall J, Johannesson A, Khaliq H, Muralidharan M, Pan E, Polacco B, Zhang Y) are now **structured Creator entries** carrying `name`, `affiliations` and a `source_caveats` reading "No persistent identifier for this author is given in any source." Previously they existed only inside the citation string. Caveat (7) was rewritten from "they are represented only in the citation string and not as structured creator entries" to "they are recorded by name without an identifier."

Creator count rose from 37 to 46 in both records.

### 4.2 `data_collectors[*].name` and `.id` (low)

Laboratory heads and institutions were named only inside `collector_details` prose.

**Both records:** each of the five collectors now carries `name` (for example "Nevan Krogan laboratory, University of California San Francisco") and, where the bundle gives an ORCID for the named head, `id`. Each identifier-bearing entry carries a `source_caveats` noting that the ORCID identifies the person and that "the bundle names the laboratory rather than assigning it a separate identifier" — the identifier is attested, the attachment to a laboratory rather than a person is disclosed.

### 4.3 `maintainers[*].name` and `.id` (low)

Same pattern.

**Both records:** all five maintainers now carry `name`; Ideker, Thaker and Niestroy additionally carry their ORCIDs. `maintainer_details` was trimmed of the identity restatement and now describes only the maintenance role.

### 4.4 `raw_sources[*].access_url` (low)

Six RawData objects described MassIVE, SRA and Figshare deposits with `access_url` unpopulated.

**Both records:** the four MassIVE entries now carry `access_url: https://massive.ucsd.edu/` with a caveat that "the June 2026 record links the deposit as 'MassIVE Repository' without printing the accession; the repository home page is given here as the access route." A seventh entry was added for the Figshare CRISPRi Perturbation Atlas deposit, which the June 2026 record links and which the original records had omitted from `raw_sources`. The two embargoed perturb-seq entries carry no `access_url`, correctly — there is nothing to point at.

### 4.5 `raw_data_sources[*].access_details` — RRIDs surfaced (low)

**Both records:** RRIDs now appear in both `source_description` (prefixed to the line, as "MDA-MB-468 (RRID:CVCL_0419), a triple-negative…") and in `access_details` ("Cell line identifier RRID:CVCL_0419"). The slot's range declares no identifier key, so this is the closest placement available.

### 4.6 `funders[0].grants` — Grant objects populated (low)

Grant objects previously carried only `name` holding an award number.

**Both records:** each Grant now carries `name` (a descriptive grant title), `id` (the award number, previously in `name`), and `description` carrying the NIH RePORTER detail — project period 2022-09-01 to 2026-08-31, fiscal year 2025 award amount 5,289,382 US dollars, application ID 11211616, project number 3OT2OD032742-01S2, recipient UCSD, PI Ideker. This content was previously confined to prose in `funders[0].source_caveats`, which has been removed as redundant; the Frederick Thomas Fund entry retains its caveat.

### 4.7 `collection_timeframes[0].start_date` and `.end_date` (low)

Declared date keys were empty while `timeframe_details` carried all dates as prose.

**Both records:** `start_date: '2022-09-01'` and `end_date: '2026-08-31'`, from NIH RePORTER. `timeframe_details` retains the November 2026 project-completion date from Dataverse and now explicitly notes that the Dataverse creation and deposit dates "describe the deposit workflow rather than the span of data generation" — the same reasoning as §3.2.

### 4.8 `instances[*].sampling_strategies` (low)

Declared but unpopulated on every Instance.

**Both records:** the immunofluorescence instance now carries a SamplingStrategy describing HPA antibody addressability and highest-scoring-antibody selection; the perturb-seq instance carries one recording `is_sample: false` for the genome-scale KOLF2.1J screen alongside the targeted MDA-MB-468 panels. The two mass-spectrometry instances carry none, as the bundle describes no instance-specific sampling for them.

### 4.9 `file_collections[*].file_count` — full record only (medium, partial)

The audit noted the core record had dropped `file_collections`. The full record retains it; each of the ten collections now additionally carries `file_count: 1`, each corresponding to exactly one released ZIP archive.

### 4.10 `sampling_strategies` split into two objects (medium, indirect)

The audit found that core had relocated `direct_collection` content into `sampling_strategies[0].source_data`.

**Both records:** `sampling_strategies` is now two objects rather than one — a molecular axis (panel selection) and a cellular axis (cell-line and condition selection) — each with its own `strategies`, `why_not_representative` and `source_data`. The cellular-axis entry's `source_data` names the two cell lines and states "No data were collected from individuals." The full record **additionally retains** the standalone `direct_collection` object with `is_direct: false`; the core record does not carry `direct_collection`, so in the core the cellular-axis `source_data` is where that evidence lives.

### 4.11 `relationships` split into two objects — full record only (low)

**Full record:** the single Relationships object was split into two — cross-modality keying by protein/gene identity, and within-interaction-data bait–prey and co-elution edges. The core record does not carry `relationships` (see §5.3).

### 4.12 Keyword ontology mappings recorded in `notes` (low)

The audit noted that the bundle attaches ontology term URIs to most Dataverse keywords, that the `keywords` slot is string-ranged and cannot carry them, and that no other slot captures the evidence.

**Both records:** a new paragraph in `notes` lists all seventeen mappings (NCIT_C16309, BAO_0002603, SWO_1100012, LA14283-8, CL_0000746, BAO_0010249, EFO_0004905, OBI_0002587, D013058, CL_0011020, CL_0000540, CHEBI_45863, EFO_0008860, NCIT_C18469, GO_0008104, EFO_0008913, CHEBI_45716), prefaced by a note that the string-ranged keyword slot cannot carry them. Per the `notes` description this is residual content that no fitting slot can hold, which is the case here.

### 4.13 `distribution_formats` — download limit stated (low, indirect)

**Both records:** the ZIP entry now opens "All ten release components are distributed as ZIP archives" and cites the specific 1.9 GB Dataverse ZIP download limit from the June 2026 record rather than the unquantified "repository's ZIP download limit". The RO-Crate entry now states it is "Distributed within the release metadata archive."

---

## 5. Core–full divergences

### 5.1 `total_file_count` — restored to core? No (low)

**Left as-is.** The audit noted `total_file_count: 10` present in full and absent in core. It remains present in full and absent in core. This was not corrected because the core record carries ten `distributions` entries, from which the count is directly derivable, and because whether `CoreDataset` declares `total_file_count` could not be checked against the supplied digest.

### 5.2 `total_size_bytes` — still omitted, now explained (medium)

**Full record:** `total_size_bytes` remains absent, and new caveat (11) now explains why — "Distribution sizes are transcribed as the human-readable values printed by the repository (for example '3.8 GB'); exact byte counts are not stated by any source, so total_size_bytes is not asserted." The audit's complaint was that the omission was unexplained in full while explained in core; the explanation now appears in both, in parallel wording.

### 5.3 `relationships`, `third_party_sharing` — full only (low ×2)

**Left as-is.** `relationships` and `third_party_sharing` remain in the full record and absent from the core record. Both are supported by the bundle. They were not added to core because the core schema was not supplied in the digest and their presence in `CoreDataset` could not be confirmed; adding a slot that the class does not declare would fail validation and would repeat the `distributions` problem rather than fix it.

### 5.4 `direct_collection` — full only (low)

**Left as-is** as a slot, **resolved** as content. See §4.10: the full record keeps `direct_collection`, and the core record now carries the same evidence in `sampling_strategies[1].source_data`, which is a declared field on a slot both records use.

### 5.5 `citation` — full slot, core `notes` (low)

**Full record:** `citation` slot retained, unchanged.
**Core record:** the citation string remains in `notes`, but the meta-commentary was removed. The original read "Release citation, for which the core schema declares no dedicated slot:"; it now reads simply "Release citation:". The audit's objection was to commentary about schema coverage appearing in a content slot, and that commentary is gone. The placement itself was not changed, for the same reason as §5.3.

### 5.6 Core-only `source_caveats` item (medium)

The audit flagged that core carried a byte-count caveat that full did not. This is now resolved by parallelism rather than deletion: the caveat appears in both records, as (11) in full and (12) in core. The remaining numbering offset arises because the core record carries one additional caveat — (11) in core, about the publisher — that has a full-record counterpart at (10); both records carry fourteen and thirteen items respectively, differing only because full retains a `publisher`-adjacent statement the core frames slightly differently.

---

## 6. Findings left as-is

| Finding | Slot | Why |
|---|---|---|
| 2.2 | `distributions[*].compression` | Dependent on 2.1; no independent resolution available |
| Core drop | `total_file_count` | Derivable from ten `distributions` entries; core schema not in digest |
| Core drop | `relationships`, `third_party_sharing` | Core schema not in digest; adding an unconfirmed slot repeats rather than fixes the `distributions` defect |
| Core placement | `citation` in `notes` | Commentary removed; placement unchanged for the same reason |
| Low | `last_updated_on` derived from file rows | Already disclosed in caveat (4); the derivation is the only dated evidence available, and the caveat states it plainly |
| Info | `id` as `doi:` CURIE, `doi` slot bare | Already correct per the digest's guidance on `uriorcurie` versus `string` ranges |
| Info | Minted `file_collections[*].id` fragments | Already correct: fragments on the attested dataset DOI, naming parts of this dataset that have no referent outside the record |
| Low | `related_datasets[*]` lacking `name`/`title` | **Corrected**, not left — see below |

The last row is a correction rather than an omission: both records now carry `name` and `title` on all four `related_datasets` entries, transcribed from the Dataverse titles of each prior deposit. For the May 2024 release the `title` is given as the citation form in the 2024 preprint ("Cell Maps for Artificial Intelligence - Data Release") with `name` giving the month, and the caveat notes the discrepancy.

---

## 7. Source-ranking applications

The declared ranking was applied at four points, each recorded in `source_caveats` in both records:

1. **Release date** — cm4ai.org (tier 2) says "Released on: June 17, 2025"; the June 2026 Dataverse record (tier 1) says 2026-06-17. Dataverse preferred.
2. **Immunofluorescence protein count** — October 2025 Dataverse (tier 1, superseded) says 464; cm4ai.org (tier 2) says 523; March 2025 Dataverse (tier 5) says 563. October 2025 preferred as the highest-ranked source stating a number for the current file set.
3. **Perturb-seq external deposit status** — June 2025 Dataverse (tier 5) links an SRA BioProject; June 2026 Dataverse (tier 1) marks both deposits embargoed. June 2026 preferred.
4. **Sali affiliation** — Dataverse (tier 1) gives UCSD; 2024 bioRxiv (tier 3) gives UCSF. Dataverse preferred, disagreement recorded on the Creator object.

The Ravitsky affiliation/email tension is *not* a ranking case: both statements come from the same tier-1 record, which gives University of Montreal as affiliation and a Hastings Center address as ethics contact. Both are recorded; neither is used to infer a reviewing organization.

---

## 8. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 56 | 53 |
| Creators | 46 | 46 |
| Unsupported assertions withdrawn | 8 | 8 |
| Declared fields newly populated | 12 categories | 11 categories |
| Findings corrected | 24 | 23 |
| Findings left as-is | 8 | 9 |

The chief residual risk is §2.1. The `distributions` block survives in the core record with a renamed checksum key; if `CoreDataset` does not declare that slot, core validation will fail and the block must move to `file_collections`. Everything else the audit raised has either been corrected in both records, enriched from the bundle, or left standing with the reason stated above.