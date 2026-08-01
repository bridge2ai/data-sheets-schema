# Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep3`
**Arm:** BASELINE (input documents only)
**Referent:** CM4AI June 2026 Data Release (Beta), DOI `10.18130/V3/HIGT4C`, version 2.0
**Records reconciled:** full (`CM4AI_d4d.yaml`), core (`CM4AI_d4d_core.yaml`)

---

## 1. Referent selection

`Dataset` admits one referent. The declared bundle contains five distinct CM4AI
Dataverse releases (DXWOS5, B35XWX, F3TD5R, K7TGEM, HIGT4C) plus two
publications describing project-level and U2OS-specific work.

**Selected referent:** the June 2026 release, DOI `10.18130/V3/HIGT4C`.

Rationale: the bundle's curation notes explicitly designate HIGT4C as "Current
CM4AI data release" and mark K7TGEM as "superseded upstream." HIGT4C carries the
most complete file inventory (ten files, including AP-MS archives absent from all
prior releases) and the most recent version metadata (v2.0, published
2026-06-17, v2 released 2026-07-15T20:28:19Z). Both records hold to this referent
consistently after reconciliation.

Prior releases are represented as version history under `version_access` and
`distribution_dates`, not as the referent.

---

## 2. Changes made

### 2.1 Cross-source contamination removed

The audit identified a body of methodological detail imported from the U2OS
multimodal cell maps publication (Nature 642:222–231), which both records
themselves acknowledge describes a different cell line (U2OS osteosarcoma) and
different underlying data than the CM4AI release. The following were removed or
narrowed:

| Slot | Action | Reason |
|---|---|---|
| `machine_annotation_tools` | Removed the GPT-4 Gene Set AI entry's mechanism detail (engineered prompt, chain-of-thought, one-shot strategy, PubMed citation module). Retained only what the CM4AI preprint states: an LLM approach that names protein sets and assigns a name confidence score. | The mechanism is documented only in the U2OS paper. The CM4AI preprint's Tools section states the general approach without the pipeline internals. |
| `machine_annotation_tools` | Removed the Integrative Modeling Platform / Python Modeling Interface entry entirely. | IMP is a structure-modelling package, not an annotation tool. The CM4AI preprint places it under integrative structure modeling. Field misassignment compounded by the fact that no structural models appear in this release's file inventory. |
| `labeling_strategies` | Removed the Annotation Jamboree entry (dozen individuals working in pairs, named annotator initials). | Documented exclusively in the U2OS Nature paper, describing curation of the U2OS map. No evidence this process was applied to CM4AI material. |
| `external_resources` | Removed the U2OS multimodal cell maps publication entry. | The slot asks for resources referenced at the dataset level. Neither the HIGT4C release record nor any CM4AI Dataverse release lists this paper as a Related Publication. It entered the bundle as an independently selected source, not as a dataset-level reference. |
| `external_resources` | Removed the Multiscale Integrated Cell portal (musicmaps.ai/u2os-cellmap) entry. | U2OS-specific portal, not referenced by the CM4AI release record. |

`external_resources` retained: the six External Data Links the HIGT4C release
record itself names (NCBI BioProject / SRA, four MassIVE depositions, Figshare
CRISPRi atlas) plus the two Related Publications the record lists (CM4AI preprint
`10.1101/2024.05.21.589311`, Perturbation Cell Atlas preprint
`10.1101/2024.11.03.621734`) plus the CM4AI project portal and FAIRSCAPE
framework, which the release's own RO-Crate packaging depends on.

### 2.2 Temporal misattribution corrected

| Slot | Action | Reason |
|---|---|---|
| `existing_uses` | Removed the March 2024 CodeFest entry. | The CodeFest predates every deposited file in this release by more than two years. It cannot be a use of this release. |
| `existing_uses` | Reclassified the Perturbation Cell Atlas preprint from an existing use to a related publication reference under `external_resources`. | The Dataverse record lists it under Related Publication, not as a downstream use. It predates HIGT4C by nineteen months. |
| `collection_mechanisms` | Removed the five Year 1 mechanism entries (pipetting robot fixation protocols, 6 guide RNAs per gene, 10x Genomics 3'HT kit, 17 endogenously tagged genes, 34 in progress). | All are drawn from the May 2024 preprint's Year 1 progress narrative. The bundle does not establish that these describe the material deposited in June 2026, which includes AP-MS data absent at preprint time. |
| `preprocessing_strategies` | Removed the four MuSIC-pipeline entries (node2vec embedding, HPA DenseNet image embedding, contrastive co-embedding, HiDeF community detection). | These describe production of cell maps. Both records state, on the release record's own authority, that computed cell maps are **not** included in this release. Processing that produced absent artifacts is not preprocessing applied to the described data. |
| `raw_sources` | Removed the "deposition archives feeding the MuSIC pipeline" entry. | Internal laboratory staging locations for a pipeline whose outputs are absent from this release. |

`collection_mechanisms` and `preprocessing_strategies` are now omitted rather
than partially populated: no remaining entry in either slot survived the
temporal test against this release.

### 2.3 Field-fit corrections

| Slot | Action | Reason |
|---|---|---|
| `confidential_elements` | Removed the "commercial-use gating" entry; slot now omitted. | Commercial licensing restriction is a use-terms matter, not confidentiality of dataset content. The content is already correctly carried by `license_and_use_terms`, `prohibited_uses`, and `ip_restrictions`. |
| `collection_timeframes` | Removed both entries (release publication timeline, Year 1 milestones); slot now omitted. | Both record publication and reporting chronology, not periods during which data was collected. `distribution_dates` already carries the release chronology in the field that asks for it. |
| `sampling_strategies` | Removed the "proteome coverage attained by SEC-MS" entry. | Records achieved coverage (~7,000 proteins, 72/100 chromatin modifiers detected), which is an outcome statistic, not a selection methodology. |
| `status` | Replaced the explanatory paragraph with `Published Beta release, version 2.0`. | The slot asks for a status token. Justification prose belongs in the reconciliation record, not the slot value. |
| `created_by` | Narrowed to the project entity responsible for creation. Depositor and point of contact were already decomposed into `maintainers` and the Dataverse contact fields. | The slot asks for the primarily responsible party, singular. |

### 2.4 Overstated structure corrected

| Slot | Action | Reason |
|---|---|---|
| `subsets` | Reduced from seven `DataSubset` objects to three. Retained the untreated / paclitaxel / vorinostat MDA-MB-468 conditions, which are separately materialized as distinct deposited files. Removed the KOLF2 undifferentiated / NPC / neuron / cardiomyocyte entries. | The four iPSC-lineage groupings are not separately addressable in the release: all reside inside the single archive `cm4ai_mass-spec_KOLF2.zip`. Constructing addressable subset identifiers for non-addressable groupings overstates the release structure. |
| `relationships` | Removed the assembly-containment entry. | Explicitly describes cell-map hierarchy, which the release does not contain. |
| `compression` | Left as `zip` but see §3. | Ten of ten deposited files are ZIP archives. |

### 2.5 Anomaly added

A documented internal contradiction in the release record was not flagged. Added
to `anomalies` in both records:

> The release description asserts "Perturb-seq data for MDA-MB-468 breast cancer
> cells +/- treatment" among the included contents, but the file inventory
> contains no MDA-MB-468 Perturb-seq archive — only
> `cm4ai_perturb-seq_KOLF2_cell_atlas.zip` and
> `cm4ai_perturb-seq_KOLF2_raw_sra.zip` — and the same record's External Data
> Links mark MDA-MB-468 Perturb-seq as Embargoed. The description overstates
> deposited contents relative to the inventory in the same source.

The `description` slot itself retains the release record's wording verbatim, as
it is the record's own self-description; the contradiction is surfaced as an
anomaly rather than by silently editing the source's language.

Also refined: the IF-checksum anomaly now states that displayed sizes are
*identical to one decimal place* rather than *identical*, since 3.8 GB / 4.6 GB /
4.2 GB rounded display values do not establish byte equality. The checksum
divergence (`0d972b80…` → `6c1a8652…` etc.) remains the load-bearing evidence.

### 2.6 Full/core structural divergence resolved

The two records modelled identical content under different slots and diverged on
four scalars without stated cause. Both were brought into alignment:

| Content | Was (full) | Was (core) | Now (both) |
|---|---|---|---|
| Ten deposited files | `file_collections` | `distributions` | `file_collections` |
| Condition groupings | `subsets` | `resources` | `subsets` |
| Recommended citation | populated | omitted | populated |
| `total_file_count` | `10` | omitted | `10` |
| `third_party_sharing` | three entries | omitted | three entries |
| `relationships` | four entries | omitted | three entries (after §2.4) |

`distributions` and `resources` were not correct placements for this content.
The core schema declares `resources` for sub-resources or component datasets;
the condition groupings are partitions, which `subsets` declares. The file
inventory belongs in `file_collections` in both records, as the full record
already had it.

The four omissions in the core record had no evidentiary basis — the citation,
file count, external-repository deposition, and instance relationships are all
directly evidenced in the release record and were present in the full record.
They are now present in both.

### 2.7 Identifiers

Constructed fragment URIs (`#cm4ai_apms_MDA-MB-468_paclitaxel.zip`,
`#subset-mdamb468-untreated`, etc.) were retained. The audit correctly notes
these are not present in the bundle. They are retained because `FileCollection`
and `DataSubset` both declare `id` as required, and the bundle exposes no
per-file Dataverse identifiers. The alternative — omitting the slots entirely
rather than using locally-scoped fragments under the dataset DOI — would discard
directly-evidenced file inventory including MD5 checksums. This is documented
here as a known construction rather than treated as source-derived.

---

## 3. Left as-is, with reasoning

**`compression: zip`.** All ten deposited files are ZIP archives. The audit notes
that prior releases distributed uncompressed JSON and HTML artifacts; those are
prior releases, not the referent. For HIGT4C the value is exact.

**`total_file_count: 10` without `total_size_bytes`.** The audit flags the
asymmetry. Per-file sizes are displayed to one decimal place in gigabytes and
kilobytes (`3.8 GB`, `113.3 KB`); summing rounded display values would produce a
byte figure with false precision. The count is exact and directly enumerable;
the aggregate size is not. Asymmetric population is the correct outcome here.

**`created_on: 2025-02-27T00:00:00Z`.** The audit observes this same Data
Creation Date appears on four consecutive releases and is likely carried forward.
It is nonetheless what the release record states in that field. Recording it is
correct; the invariance across releases is noted here rather than suppressing
the value.

**Creator affinity inconsistency for Sali A.** The bundle records UCSD on the
Dataverse release and UCSF in both the preprint author list and the Nature paper.
The record preserves both without resolution, per the disagreement rule. The
audit notes this handling is not applied uniformly to other creators whose
affiliations also vary across sources. On review, the other cases (Krogan,
Lundberg) are consistent across sources; only Sali diverges. No change.

**`known_biases` — target-selection bias.** The audit flags over-generalization,
noting the genome-scale CRISPRi atlas covers 11,739 genes and contradicts the
100-modifier framing. The entry was **narrowed** rather than removed: it now
scopes the target-selection bias to the AP-MS and IF modalities, where the
curated panel is documented, and explicitly excludes the genome-scale
perturbation data. Recorded here as a change, not an as-is.

**Omitted slots verified correct.** `at_risk_populations`,
`collection_consents`, `informed_consent`, `consent_revocations`,
`collection_notifications`, `participant_compensation`, `participant_privacy`,
`data_protection_impacts` — all correctly absent given the release record's
explicit `Human Subjects: No` and `De-identified Samples: Yes` determinations
and the commercial cell-line derivation. `variables` correctly absent: the
bundle describes JSON-Schema data dictionaries as resolvable from provenance
metadata but enumerates no variable names, so no object could satisfy the
required `variable_name` key. `splits` correctly absent: no train/validation/test
partitioning appears anywhere in the bundle. `cleaning_strategies`,
`imputation_protocols`, `annotation_analyses` correctly absent: no outlier
removal, deduplication, error correction, imputation, or inter-annotator
agreement is described.

**`related_datasets` remains omitted.** The audit notes four prior release DOIs
would support `DatasetRelationship` objects. Those relationships are carried by
`version_access` and `distribution_dates`, which describe version lineage in the
fields that ask for it. Duplicating the same lineage as typed relationships adds
no information the bundle supports beyond what is already recorded.

**`download_url` remains omitted.** The bundle supplies only the Dataverse Data
Access API pattern, not a resolvable dataset-level download URL, and the record
states the dataset is too large to download whole.

**`use_repository` remains omitted.** Per-release download counts and Dataverse's
Make Data Count / Crossref integration are the only candidates; the citation
query in the bundle returned no citations. Insufficient to populate a
use-tracking resource.

**`extension_mechanism`, `modified_by`, `conforms_to_class`, `content_warnings`,
`sensitive_elements` remain omitted.** No bundle evidence describes a
contribution mechanism for the dataset itself (as distinct from the open-source
toolkit), attributes the June 2025 revisions to a named party, identifies a
specific schema class, or establishes content requiring warning. On
`sensitive_elements`: donor attributes (51-year-old Black female with metastatic
mammary adenocarcinoma; healthy male Northern European donor) are recorded under
`subpopulations` and `is_deidentified`, and the release asserts de-identification.
Omission from `sensitive_elements` is consistent with that assertion.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Slots populated | 61 | 47 |
| LinkML validation | pass | pass |
| Referent | HIGT4C v2.0 | HIGT4C v2.0 |

Both records validated against their respective schemas after reconciliation.
The paired records are now consistent: no content is modelled under divergent
slots, and no scalar is present in one and absent from the other without
evidentiary cause.

Twelve slots were modified for cross-source contamination, six for temporal
misattribution, five for field-fit, three for overstated structure, and six for
full/core alignment. One anomaly was added. No previously generated D4D record
was consulted at any phase.