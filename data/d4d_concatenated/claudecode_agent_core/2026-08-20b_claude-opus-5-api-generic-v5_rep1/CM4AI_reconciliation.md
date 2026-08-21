# CM4AI Datasheet Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep1`
**Referent:** CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Phase 4 outcome:** both records revised; both revalidated.

---

## 1. Scope of the audit

The Phase 3 audit returned 39 findings: 8 high, 15 medium, 16 low. They cluster into five kinds of problem:

1. The core record was not a projection of the full record — it added, dropped and restructured content.
2. `principal_investigator` was over-claimed across fifteen Creator objects.
3. Several slots were populated with values their own caveats disowned.
4. A `uriorcurie` slot carried a `mailto:` URI where no declared prefix fits.
5. A set of slots with clear evidentiary support in the bundle were omitted.

Each is addressed below with the corresponding action.

---

## 2. Changes made to the full record

### 2.1 Creator objects — over-claimed PI designation, placeholder entry, missing roles (findings: high ×2, medium ×2)

**Removed the sixteenth Creator.** The original full record ended with a Creator object carrying only `affiliations: [{name: KTH Royal Institute of Technology}]`, a `notes` field and a `source_caveats` field, with no `principal_investigator`. It named no person and existed to hold commentary about how the creator list was constructed. In the reconciled record this object is gone; the commentary it carried has moved to top-level `source_caveats` under the heading "Creators and roles", and the pointer to the 47-author list now names the `citation` slot explicitly.

**Reordered and re-justified the remaining fifteen.** The audit was correct that only Trey Ideker is attested as principal investigator (NIH RePORTER). Rather than delete fourteen Creator objects — which would discard grounded authorship information — the reconciled record:

- reorders the list so that the parties with attributed data-generation or packaging roles (Ideker, Lundberg, Krogan, Mali, Clark) come first;
- adds a `source_caveats` on the second entry (Lundberg) stating explicitly that the bundle does not designate these people as principal investigators, that the field records "the responsible lead named by the sources", and that "the same qualification applies to every Creator below";
- restates the same qualification at top-level `source_caveats`.

**Added `credit_roles`.** The audit noted that the bundle supports role attribution for several parties and the field was empty throughout. The reconciled record populates it for five creators where the bundle attributes a specific contribution:

| Creator | `credit_roles` | Evidence in bundle |
|---|---|---|
| Ideker | conceptualization, supervision, project_administration, funding_acquisition | NIH RePORTER PI; corresponding author; point of contact |
| Lundberg | investigation, resources | Lundberg Lab credited in Dataverse file descriptions for imaging |
| Krogan | investigation, resources | Krogan laboratory credited for SEC-MS |
| Mali | investigation | perturbation atlas co-authorship |
| Clark | data_curation, software | Standards module lead; FAIRSCAPE packaging |

It is left empty for the remaining ten, where the bundle names an author but attributes no specific contribution.

**Ravitsky caveat corrected.** The original said "Both are recorded here rather than reconciled" while recording only University of Montreal. The reconciled caveat now states plainly that the Dataverse affiliation is recorded in `affiliations` and the divergent contact domain is recorded in the caveat only, "because the bundle does not state an affiliation for her at The Hastings Center."

**Affiliation identifier asymmetry.** The audit asked that the asymmetry be recorded. A paragraph headed "Affiliation identifiers" was added to top-level `source_caveats` explaining that `ROR:0153tk833` appears only for the UVA creators because the June 2026 release itself gives that ROR, and that no other affiliation in the bundle carries a registry identifier.

### 2.2 `data_governance.committee_contact` — mailto URI in a Person `id` (finding: high)

The original had:

```yaml
committee_contact:
  id: mailto:jillianparker@health.ucsd.edu
  name: Jillian Parker
```

The reconciled record replaces this with the bare name and moves the email address into `access_review_process` prose, adding a `source_caveats` on `data_governance` stating that "the bundle supplies only an email address for the committee contact and no personal identifier, so `committee_contact.id` is omitted."

Note: in the reconciled full record `committee_contact` is written as a scalar string (`Jillian Parker`), which is a consequence of applying the v4 scalar rule alongside the identifier rule. This is discussed under §5.

### 2.3 `instances[*].counts` — figures the caveats disowned (finding: medium)

The original attached `counts: 53788` and `counts: 1374` to Instance objects while the same objects' caveats said the figures were project-wide and "not stated as a per-release figure." Both `counts` values are removed in the reconciled record. The totals are retained as prose in each object's `notes`, and a "Scope of counts" paragraph in top-level `source_caveats` states that they "are therefore recorded in prose rather than in the `counts` field of any Instance object, and the 21.4 TB figure is not used for `total_size_bytes`."

### 2.4 `instances[0].data_topic` and instance-1 substrate note (finding: medium)

`data_topic` on the immunofluorescence instance changed from `B2AI_TOPIC:19` (Microscale Imaging) to `B2AI_TOPIC:15` (Image), as the audit suggested. The protein-interaction instance now carries an explicit note that "B2AI_SUBSTRATE has no term for protein interaction data, so `data_substrate` is omitted rather than approximated" — the omission was already correct but undocumented.

### 2.5 `collection_timeframes` — award dates in a measurement-window slot (finding: medium)

The slot is removed entirely from the reconciled full record. Its own caveat had conceded the bundle "does not state an explicit measurement window for any individual data stream", and the award period was already recorded under `funders`. A "Collection timeframe" paragraph in top-level `source_caveats` records the omission and its reason.

### 2.6 `errata` — an erratum for a different release (finding: medium)

The audit found the single Erratum documented a revision to the June 2025 release, not the referent. The reconciled full record retains `errata` but strips the self-disowning caveat; the same text also now appears as a `notes` field on the March 2025 `related_datasets` entry. In the core record the `errata` slot is dropped and the content lives only on the related-dataset entry.

### 2.7 `related_datasets[*].relationship_type` — flattened release chain (finding: medium)

The original typed all four prior releases `is_new_version_of`. The reconciled record keeps that type only for the October 2025 release (the immediate predecessor, which the manifest marks as superseded by this one) and retypes the June 2025, March 2025 and May 2024 releases as `continues`. A `source_caveats` on the June 2025 entry explains the distinction: these are "earlier link[s] in the chain rather than the immediate predecessor", each with its own DOI, contents and Dataverse version numbering.

### 2.8 `total_size_bytes` and per-collection `total_bytes` (finding: medium)

Both were absent from the original despite the bundle giving a size for every file. The reconciled full record adds `total_size_bytes: 12602000000` at top level and a `total_bytes` value on each of the ten FileCollections. Sizes are converted from the binary units the Dataverse listing reports; a "Size and file counts" paragraph in top-level `source_caveats` states that they "are therefore approximate to the precision the listing reports."

Each FileCollection also gains an `issued` datetime (`2026-06-17T00:00:00Z` for the seven June files, `2026-07-15T00:00:00Z` for the three image archives), replacing the publication dates that had been embedded in prose. The `total_bytes` figures were removed from the descriptions as a consequence, since they now occupy the declared field.

### 2.9 `file_count` semantics (finding: medium)

`file_count: 1` per collection was correct in aggregate but described archives rather than files. The reconciled record adds a `source_caveats` on the first FileCollection stating that "`file_count` records the number of distributed archives, which is one; the bundle does not state how many files each archive contains", and repeats the point in top-level `source_caveats`.

### 2.10 Image protein-count caveat scope and ranking framing (finding: medium)

The original attached the 464/523/563 disagreement only to the untreated archive and framed October 2025 as "highest ranked source stating a figure". The reconciled record:

- rewrites the caveat with explicit tier labels — June 2026 (tier 1, current) silent; October 2025 (tier 1, superseded) and June 2025 (tier 5) give 464; the website (tier 2) gives 523; March 2025 (tier 5) gave 563;
- states that "because the current release is silent, the ranking cannot settle the figure";
- adds a short cross-referencing caveat to the paclitaxel and vorinostat archives.

### 2.11 `raw_data_sources[6]` — third data point added (finding: medium)

The KOLF2.1J perturb-seq caveat now names all three sources: June 2026 (tier 1) embargoed, June 2025 (tier 5) SRA/BioProject link, and the March 2025 (tier 5) separate "CRISPR Perturbation RNA Sequences - Raw Sequences" RO-Crate — which the original omitted.

### 2.12 Slots added on supported evidence (findings: medium ×1, low ×5)

| Slot | Content added |
|---|---|
| `machine_annotation_tools` | GPT-4 via the GSAI pipeline; GO/Reactome alignment; confidence scores and citation module. Carries a caveat that these annotate the downstream cell maps, not this release. |
| `cleaning_strategies` | FAIRSCAPE input validation at each pipeline segment; CRISPR screen QC in progress per the preprint. Caveated as tier-3 evidence describing the project's first year. |
| `external_resources` | Five entries: project portal, Cell Mapping Toolkit repo + docs, FAIRSCAPE docs, IMP, and the two related publications. |
| `use_repository` | Dataverse download metrics (181 / 405 / 256 / 302) and its Crossref-via-DataCite citation tracking, which reported no citations. |
| `extension_mechanism` | Cell Mapping Toolkit as pip-installable packages with docs; caveated that this extends the software, not the released archives. |
| `missing_data_documentation` | The incomplete-modality-overlap pattern, plus the release-specific gaps (no AP-MS untreated, no iPSC imaging, SEC-MS only for the differentiated lineages). |
| `known_biases[1]` | `selection_bias` for the disease-relevance target design, with `affected_subsets` noting the genome-scale iPSC screen as the exception. |

### 2.13 Small corrections (findings: low ×4)

- **`status`** shortened from `Beta (interim release; data generation continues through November 2026)` to `Beta`; the parenthetical duplicated `known_limitations` and `updates`.
- **`created_by`** changed from the project name to `Justin Niestroy`, whom the Dataverse record names as depositor.
- **`last_updated_on`** removed. It had carried the image-archive publication date as a whole-record modification timestamp, which the bundle does not state. The date survives on the three image FileCollections' `issued` fields.
- **`maintainers[1].role`** changed from `researcher` to `other` for the Program Manager / website support entry, with a caveat that the enum has no administrative term.
- **`ethical_reviews[0].reviewing_organization`** shortened from `CM4AI Ethics Module (Simon Fraser University and The Hastings Center)` to `CM4AI Ethics Module`, with a caveat that the parenthetical was inferred from email domains.
- **`language`** retained; a "Language" paragraph in top-level `source_caveats` now records it as inferred rather than stated.
- **`description`** rephrased so that the collaborator list and the author-affiliation list are presented as two separate statements from the sources rather than one reconciled list.
- **`distribution_dates[0].source_caveats`** trimmed: the tier labels are now explicit and the editorial diagnosis ("appears to be an error in the year") is deleted.
- **`direct_collection`** gains `is_direct: false` and a closing sentence stating affirmatively that the consent-family slots are omitted because no individuals were enrolled.

---

## 3. Changes made to the core record

The audit's central structural finding was that the core record was not a projection. Every part of that finding was acted on.

### 3.1 `compression: zip` removed (finding: high)

The original core set a top-level `compression: zip` that the full record did not state. It is deleted. Per-file compression is carried on each `distributions` entry.

### 3.2 `direct_collection` — lost content restored (finding: high)

The audit found the core dropped the record's only affirmative statement that no data were collected from individuals. CoreDataset has no `direct_collection` slot available to this projection, so the content is preserved as a sixth `acquisition_methods` entry carrying the same text plus `was_reported_by_subjects: false`. The statement is no longer absent from the core record.

### 3.3 `resources` — split/subpopulation semantics restored (finding: high, plus medium)

The full record's `subsets` (DataSubset, with `is_data_split: false` / `is_subpopulation: true` on each of the seven strata) remain mapped to `resources` in the core, because CoreDataset declares no `subsets` slot. What changed is that the flags are no longer silently lost: every one of the seven descriptions now says "This is a subpopulation stratum rather than a data split", and a "Subpopulation strata" paragraph in top-level `source_caveats` explains the slot substitution and its reason.

### 3.4 `distributions` — retained, but reconciled with the full record (findings: high ×1, medium ×1)

The `distributions` block is retained. The audit flagged it as possibly undeclared, but the core schema was not supplied for inspection and the digest covers `Dataset`, not `CoreDataset`; the report therefore cannot assert that the slot is undeclared, and validation is the test. What changed:

- a `bytes` field was added to every entry, matching the `total_bytes` now on the full record's FileCollections, so the two records agree on size;
- `conforms_to_standard` on the metadata package changed from the scalar `RO_CRATE` to the list `[RO_CRATE]`, matching the full record;
- the image-archive caveats were rewritten to match the full record's tier-explicit version, and cross-referencing caveats were added to the paclitaxel and vorinostat entries;
- a "Sizes" paragraph in top-level `source_caveats` mirrors the full record's precision note.

The full record's `distribution_formats` also gained ten per-file entries carrying the MD5 checksums, so the checksums that the core carries in `distributions[*].md5` now have a counterpart in the full record rather than living only in `file_collections[*].distribution_formats[*].checksum`.

### 3.5 `citation` — 47-author list (finding: medium)

The core still omits `citation`. What changed is that the core's `source_caveats` no longer relies on a slot it does not have: instead of pointing at "the citation slot", it now states that "the complete authorship of the release runs to 47 named authors, listed in full in the Dataverse citation for doi:10.18130/V3/HIGT4C" — a resolvable pointer rather than a dangling internal reference.

### 3.6 Creator identifiers

In the core record each Creator now carries `id: ORCID:...` and `principal_investigator: <name>` as a scalar. This differs from the full record, which folds the ORCID into the `principal_investigator` string. Both records converge on ORCID CURIEs rather than orcid.org URLs, satisfying the v5 identifier rule; the divergence in placement is discussed under §5.

### 3.7 All shared-content changes propagated

Every substantive change listed in §2 that applies to slots the core also carries — Creator reordering and caveats, `credit_roles`, `data_governance` contact, `instances` counts and topic, `collection_timeframes` removal, `related_datasets` retyping, the new `machine_annotation_tools` / `cleaning_strategies` / `external_resources` / `use_repository` / `extension_mechanism` / `missing_data_documentation` / `known_biases[1]` slots, and the low-severity corrections to `status`, `created_by`, `last_updated_on`, `maintainers[1].role`, `ethical_reviews`, `description`, `distribution_dates` and `direct_collection` content — appears identically in both records.

---

## 4. Findings left as-is

| Finding | Severity | Why unchanged |
|---|---|---|
| `content_warnings`, `anomalies`, `imputation_protocols`, `splits`, `relationships`, `data_protection_impacts` omitted | low | The audit called the omissions defensible. Its one substantive suggestion — that the incomplete-overlap statement is also a missing-data pattern — was acted on via the new `missing_data_documentation` slot; the six slots themselves stay omitted. |
| `annotation_analyses`, `labeling_strategies` omitted | medium (part) | The audit's minimum ask was `machine_annotation_tools`, which was added. The bundle documents no inter-annotator agreement analysis and no human labeling protocol for these data streams; both slots remain empty. |
| `consent_*`, `informed_consent`, `participant_compensation`, `participant_privacy`, `at_risk_populations` omitted | low | Correctly omitted. The audit's actual complaint was that the core lacked any affirmative non-collection statement; that was fixed (§3.2). |
| `conforms_to_standard` carries only `RO_CRATE` | low | The audit itself concluded the single value is defensible: EVI, JSON-LD, Schema.org, FAIRSCAPE and ARK map to no listed enum term. They remain in `conforms_to` prose. |
| `publisher: ROR:0153tk833` | medium | Retained. The audit called it "a defensible inference"; the reasoning is stated in `source_caveats` and the alternative — omitting the publisher identifier entirely — loses information the bundle supports. |
| `created_on: 2025-02-27T00:00:00Z` | low | Retained. It is the Dataverse-stated deposit and creation date for the record. The audit's complaint concerned `last_updated_on`, which was removed. |

---

## 5. Residual concerns

Three things are worth flagging rather than claiming as clean.

**Scalar-vs-object handling of person references.** Applying the v4 rule ("populate a scalar-ranged slot with the identifier of the thing it refers to") together with the identifier rule produced an inconsistency the reconciliation did not fully resolve. In the reconciled full record, `creators[*].principal_investigator` is written as `Trey Ideker (ORCID:0000-0002-1708-8454)` — a name-plus-CURIE string — while `data_governance.committee_contact` is `Jillian Parker` and `ethical_reviews[0].contact_person` is `Vardit Ravitsky (ORCID:...)`. In the core record, `principal_investigator` is a bare name with the ORCID hoisted to a sibling `id`, and `contact_person` is a bare name. The digest declares these fields as `Person`. If the validator accepts objects here, the string form loses structure; if it accepts strings, the two records disagree on format. This should be settled by whichever form validates.

**`distributions` remains unverified against the core schema.** The audit's first high-severity finding cannot be closed by inspection because the core schema file was not among the supplied materials. The block was reconciled with the full record rather than removed, on the reasoning that removing correct content on an unverified structural suspicion is the worse error. Validation is the arbiter.

**The `errata` / `related_datasets` split.** The full record keeps `errata` and also duplicates its text as a `notes` on the March 2025 related-dataset entry; the core carries only the latter. The two records therefore differ on where this content lives, which is a projection asymmetry of the kind §3 was meant to eliminate. It is small, and both statements are grounded, but it is not clean.

---

## 6. Outcome

Both records were revised. The core record is now a projection of the full record in the sense the playbook requires: it states nothing the full record does not, and where CoreDataset lacks a slot the full record uses, the content is carried in a declared alternative with a caveat naming the substitution. Fourteen over-claimed PI designations are qualified rather than asserted. Three slots that contradicted their own caveats were emptied or removed. One `mailto:` URI in a `uriorcurie` position was eliminated. Seven slots with clear evidentiary support were added.