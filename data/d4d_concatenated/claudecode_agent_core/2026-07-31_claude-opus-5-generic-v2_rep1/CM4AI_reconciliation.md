# Reconciliation Report — CM4AI

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep1/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep1/CM4AI_d4d_core.yaml`

**Source bundle** `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (10 files). No prior D4D record was read at any phase.

---

## 1. Referent

The audit confirmed the Phase 1 choice of referent and its consistent application across both records. `Dataset` admits one referent; the declared bundle contains five CM4AI Dataverse releases (DXWOS5, B35XWX, F3TD5R, K7TGEM, HIGT4C) plus two publications, a project portal, an NIH RePORTER entry, and a licence text.

The June 2026 release, DOI `10.18130/V3/HIGT4C`, is the referent. This is supported directly: the curation note on `dataverse_10.18130_V3_HIGT4C_2026-07-24.txt` designates it the current release, and the `cm4ai_org_data-releases_row11.txt` page lists it as the latest under "Our latest data release." The earlier releases are treated as related versions, not as the subject.

One consequence is worth stating plainly. The input manifest still selected the October 2025 release (K7TGEM) as the sheet row; the bundle's own curation note supersedes that selection. Both records follow the bundle, not the sheet.

---

## 2. What the audit found

Thirty findings across both records. Three were rated high, sixteen medium, eleven low. The records were substantially well-grounded — in particular the consent, human-subjects, and preprocessing slot families showed correct restraint, and four genuine source disagreements had been surfaced rather than silently resolved. The defects clustered in three places: fabricated numeric precision, a date treated as release-specific when the bundle shows it is not, and an inclusion claim in the description that the file inventory does not bear out.

---

## 3. Changes to the full record

### 3.1 `created_on` — removed

Was `2025-02-27T00:00:00Z`, taken from the Dataverse "Data Creation Date" field. The bundle carries the identical value on all four Dataverse releases it contains (B35XWX, F3TD5R, K7TGEM, HIGT4C). It is therefore a carried-forward collection-level field, not a creation date for this release. `created_on` is a bare datetime with no room for qualification, so the choice was between asserting an unsupported per-release date and omitting. Omitted. The observation itself is retained in `collection_timeframes`, where a description field can carry it.

### 3.2 `language` — removed

Was `en`. Not stated anywhere in the bundle. The deposited files are image archives, mass-spectrometry outputs, and sequencing-derived archives; the inference ran from the language of the *metadata* to a property of the *data*. Under the rule that a plausible guess is not a correct answer, omitted.

### 3.3 `errata` → `anomalies` — reclassified

The entry recording that the reported immunofluorescence protein count changed from 563 (March 2025) to 464 (June 2025 onward) was filed under `errata`. `Erratum` is for known errors and corrections. The bundle does not characterise the change as either: the June 2025 revision note lists only "adding RGB immunofluorescent images, corrections to ro-crate metadata, and changes to naming conventions," with no mention of a count correction. Filing it as an erratum asserted an interpretation the sources do not make. Moved to `anomalies` as a `DataAnomaly`, described neutrally as a divergence between releases with the change unattributed.

### 3.4 `related_datasets` — added

Four `DatasetRelationship` objects, one per prior release, each with `relationship_type` and `target_dataset` (DOI). The bundle supplies both required keys for all four: `10.18130/V3/DXWOS5`, `10.18130/V3/B35XWX`, `10.18130/V3/F3TD5R`, `10.18130/V3/K7TGEM`. This lineage was previously carried only as prose inside `version_access` and `distribution_dates` — that is, the evidence answered a field that was left empty while sitting in a neighbouring one.

### 3.5 `was_derived_from` — added

Populated with the immediately preceding release (K7TGEM), which the bundle establishes this release extends. Supported by the file inventories: HIGT4C adds AP-MS archives absent from K7TGEM while retaining the SEC-MS, perturb-seq, and IF collections.

### 3.6 `discouraged_uses` — added

One `DiscouragedUse`. The release's own Limitations section states it "is most suitable for bioinformatics analysis of the individual datasets" and that computed cell maps are not included. That is a discouragement of integrated cross-modality analysis, distinct in force from the Prohibited Uses statement about clinical decision-making. Previously present only as a limitation; `prohibited_uses` was populated while `discouraged_uses` — the weaker and separately evidenced category — was not.

### 3.7 `description` — qualified

The release prose states the Beta release includes "Perturb-seq data for MDA-MB-468 breast cancer cells +/- treatment and undifferentiated (parental) KOLF2.1J iPSCs." The ten-file inventory lists only `cm4ai_perturb-seq_KOLF2_cell_atlas.zip` and `cm4ai_perturb-seq_KOLF2_raw_sra.zip`; the external MDA-MB-468 perturb-seq link is marked **Embargoed**. The quotation was faithful but read as an unqualified inclusion claim. The description now attributes the statement to the release page and notes that the MDA-MB-468 perturb-seq component is externally linked under embargo rather than deposited.

### 3.8 `existing_uses` — wording softened

The CodeFest entry merged demographic figures reported of the "inaugural virtual CodeFest event" with the March 2024 CodeFest described in the Results section. The bundle does not state these are the same event. The two statements are now kept distinct.

---

## 4. Changes to the core record

### 4.1 `distributions[].byte_size` — removed (high)

The most serious defect in either record. The bundle gives only rounded human-readable sizes from the Dataverse file table — `113.3 KB`, `3.8 GB`, `1.1 MB`. The core record converted these to exact integers (`113300`, `3800000000`, `1100000`) using a decimal 1000-based factor that is neither stated in the bundle nor recoverable from it. Dataverse display sizes are rounded and conventionally binary-based, so each integer asserted a byte count the source does not support, to a precision the source cannot have.

This was also internally inconsistent: the full record had correctly declined to populate `total_size_bytes` on exactly this evidence. `byte_size` removed; the displayed size string retained verbatim in each distribution's description, where it is a quotation rather than a computation.

### 4.2 `total_file_count` — added

Set to `10`, matching the full record. The bundle supports the count identically for both ("1 to 10 of 10 Files"). The prior asymmetry — populated in full, omitted in core, same evidence — was unexplained.

`total_size_bytes` remains omitted in both records, for the reason in 4.1.

### 4.3 `created_on` — removed

Same reasoning as 3.1.

### 4.4 `language` — removed

Same reasoning as 3.2.

### 4.5 `collection_timeframes` — qualified

The core entry described the 2025-02-27 Data Creation Date as belonging to this release, without the qualification the full record carried. Now states that the same date is recorded on all four Dataverse releases in the bundle and is not release-specific.

### 4.6 `errata` → `anomalies` — reclassified

Same reasoning as 3.3, applied identically.

### 4.7 `description` — qualified

Same reasoning as 3.7, applied identically.

---

## 5. Retained omissions

These slots stay empty because the bundle supplies no supporting evidence. Recording them as deliberate rather than overlooked:

| Slot | Basis for omission |
|---|---|
| `collection_consents`, `informed_consent`, `consent_revocations`, `collection_notifications` | Bundle states **Human Subjects: No**; no collection from individuals |
| `participant_compensation`, `participant_privacy`, `at_risk_populations` | As above |
| `data_protection_impacts` | No DPIA described |
| `cleaning_strategies`, `imputation_protocols` | Embedding and community detection are described; no outlier removal, deduplication, or imputation |
| `annotation_analyses` | No inter-annotator agreement analysis reported |
| `splits` | No train/validation/test partitioning at release level |
| `variables` | No per-variable schema for the deposited archives |
| `content_warnings` | No offensive or disturbing content category supported |
| `parent_datasets` | The Dataverse collection is a repository container, not a parent dataset |

Four omissions were judged borderline and are retained as omissions with reasons:

**`download_url`.** The page supplies `https://dataverse.lib.virginia.edu/api/access/datafile/` for programmatic retrieval. This is a URI stem requiring a per-file identifier, not a resolvable download URL for the dataset. Retained in `distribution_formats` prose instead.

**`extension_mechanism`.** The Cell Mapping Toolkit is described as "a flexible and generalizable framework for cell map construction," pip-installable with a step-by-step guide. This is a tooling affordance for building comparable resources, not a pathway for contributing additions or corrections to *this* dataset. Omitted.

**`conforms_to_schema` / `conforms_to_class`.** `conforms_to` carries RO-Crate, which the bundle asserts of the deposited packages. JSON-Schema and the EVI Evidence Graph Ontology are described in the preprint as FAIRSCAPE pipeline machinery; the bundle does not assert that this release's files conform to them as a schema. Omitted.

**`sensitive_elements`.** Flagged in audit as the most arguable omission. The bundle records donor attributes for both source lines — MDA-MB-468 from "a 51-year-old black female with a metastatic mammary adenocarcinoma," KOLF2.1J from "a healthy male Northern European donor." These are demographic descriptors, and the record does populate `subpopulations` with them. But the bundle's governance determination is explicit and repeated: Human Subjects **No**, De-identified Samples **Yes**, and both lines are commercially available established cell lines. Adding a `SensitiveElement` would assert a handling requirement the sources affirmatively deny. Omitted; the tension is recorded here.

The portal-level figure of "1,374 protein interactions" on `cm4ai.org` was **not** added as an anomaly. It is a project-wide portal statistic spanning all releases and cell lines; treating it as an irregularity of this release would risk exactly the cross-cell-line conflation both records otherwise avoid.

---

## 6. Retained populations, with caveats recorded

**Source disagreements, deliberately surfaced rather than resolved.** Four were found and all four are correctly represented as stated rather than merged:

- Andrej Sali's affiliation differs between the Nature paper and the CM4AI preprint. Both are recorded; neither is selected.
- Project end date differs between NIH RePORTER (2026-08-31) and the release maintenance plan (November 2026).
- The `cm4ai.org` release page labels HIGT4C the June 2026 release while displaying "Released on: June 17, 2025"; Dataverse gives publication date 2026-06-17. The curation note flags this and both records follow the Dataverse metadata while recording the page discrepancy.
- The 563→464 protein count change, now under `anomalies`.

**Constructed identifiers.** `file_collections` and `subsets` require an `id`. No source supplies identifiers for these logical groupings, so fragment identifiers were minted under the release DOI (`...HIGT4C#mda-mb-468-untreated` and similar). Minting is unavoidable under the schema. Recording it here because nothing in either record marks these identifiers as constructed rather than sourced, and a downstream consumer could reasonably mistake them for citable fragments. They are not.

**`publisher`.** Set to the Dataverse base URL. A constructed value rather than a sourced identifier; the bundle names the University of Virginia Dataverse / LibraData as host and UVa Rector and Visitors as copyright holder, but supplies no publisher URI. Retained as the nearest defensible value.

**`relationships`, second object.** "Perturbation-to-transcriptional-phenotype links" is a looser fit for the compositional sense the slot describes than the first object (PPI edges). Retained: the perturb-seq atlas does relate perturbation instances to phenotype profiles, which is a relationship between instances.

**Core `human_subject_research`.** The core record folds the full record's `direct_collection` content into this object's description, mixing the human-subjects determination with collection-route facts. Retained as the least-bad adaptation given the narrower core slot inventory, but the object is doing two jobs.

**Core absences relative to full.** `subsets` and `relationships` appear in the full record and not in core; the core class does not admit them. Lineage that the full record now carries in `related_datasets` and `was_derived_from` remains in core's `version_access` prose for the same reason.

**`keywords`.** Reproduces the Dataverse list verbatim, including `AP-MS` and `affinity purification`. Accurate here — AP-MS archives are present in the June 2026 inventory. Noted only because the identical keyword list appears on the March and October 2025 releases where AP-MS data are absent; that inconsistency was not imported.

---

## 7. Change ledger

| Record | Removed | Added | Reclassified | Reworded |
|---|---|---|---|---|
| Full | `created_on`, `language` | `related_datasets`, `was_derived_from`, `discouraged_uses` | `errata` → `anomalies` | `description`, `existing_uses` |
| Core | `created_on`, `language`, `distributions[].byte_size` | `total_file_count` | `errata` → `anomalies` | `description`, `collection_timeframes` |

---

## 8. Outcome

Both records reconciled. All three high-severity findings resolved: fabricated byte precision removed, the full/core `total_file_count` asymmetry closed, and the `sensitive_elements` omission adjudicated and documented rather than left silent.

The two records now agree on every shared slot, differ only where the core class inventory is narrower, and carry no numeric value more precise than its source. Where the bundle disagrees with itself, the disagreement is visible in the record rather than resolved behind it.

Both files validate against their respective schemas.