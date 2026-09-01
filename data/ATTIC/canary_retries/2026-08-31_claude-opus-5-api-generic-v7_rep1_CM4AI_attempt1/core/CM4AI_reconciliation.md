# Phase 4 Reconciliation Report — CM4AI

Version label: `2026-08-31_claude-opus-5-api-generic-v7_rep1`
Records reconciled: full (`CM4AI_d4d.yaml`) and core (`CM4AI_d4d_core.yaml`)
Audit findings addressed: 17 (2 high, 8 medium, 7 low)

---

## Summary of outcome

| Severity | Findings | Changed | Left as-is |
|---|---|---|---|
| high | 2 | 2 | 0 |
| medium | 8 | 7 | 1 |
| low | 7 | 7 | 0 |
| **total** | **17** | **16** | **1** |

All changes made in the full record were carried through to the core record by re-projection, so the two remain consistent. No factual claim was added that the declared bundle does not support; several were removed or moved because the bundle does not support them in the slot where they sat.

---

## High-severity findings

### 1. `creators` — Creator objects carried only an identifier

**Changed.** In the original full record every one of the 38 `creators` entries was a single-key mapping of the form `- id: ORCID:0000-...`, with no other populated field. In the reconciled record each entry carries, in addition to the ORCID where the source gives one, an `affiliations` list holding the affiliation string the June 2026 release states for that author, and a `notes` value naming the author (e.g. `notes: Clark T`, `affiliations: [{name: University of Virginia}]`). The entry for Ideker additionally carries `principal_investigator: Ideker, Trey`, since the release names him point of contact and the NIH RePORTER record names him principal investigator; a `notes` value on that entry records both roles.

Three entries carry a supplementary role note where the bundle attests one: Niestroy (depositor of the release), Thaker (program manager for project-related inquiries), and Ravitsky and Belisle-Pipon (ethical review contacts).

Rationale: `Creator` declares `affiliations`, `principal_investigator`, `credit_roles` and `notes`, and the bundle answers the first two for these authors. An identifier alone does not populate the class. `credit_roles` remains unpopulated because the bundle assigns no CRediT roles to the release authors.

### 2. `creators` — nine attested authors omitted

**Changed.** The original record listed 38 creators; the nine authors for whom the source gives no ORCID — Axelsson U, Chinn B, Fall J, Johannesson A, Khaliq H, Muralidharan M, Pan E, Polacco B, Zhang Y — were absent, though all nine appear in the `citation` value in that same record. The reconciled record carries 47 entries: the nine are now present, each with `affiliations` and a `notes` value stating the author name and that no ORCID is given in the source. `Creator` declares no required keys, so an entry without `id` validates.

The `source_caveats` sentence that previously read "Nine of the 47 listed release authors have no ORCID in the source and are not represented as creator entries" now reads that they "are represented as creator entries carrying affiliation and a note rather than an identifier." The caveat documents the identifier gap rather than an omission.

---

## Medium-severity findings

### 3. `publisher` asserted a ROR CURIE from an affiliation context

**Changed.** The original record carried `publisher: ROR:0153tk833`. The slot is absent from the reconciled record. The string `https://ror.org/0153tk833` occurs in the June 2026 Dataverse page only inside author-affiliation fields, standing for the University of Virginia as an affiliation; the bundle never states a publishing organization in a form that answers this slot. A sentence was added to `source_caveats` explaining the omission and noting that the bundle names the University of Virginia Dataverse as the hosting repository without naming a publisher.

### 4. `instances` — project-wide counts in release-scoped `counts`

**Changed.** The imaging Instance no longer carries `counts: 53788` and no longer carries the note explaining that the figure is project-wide; the AP-MS Instance no longer carries `counts: 1374` or its corresponding note. Both figures remain in `description`, where they are explicitly attributed to the CM4AI portal as project-wide totals. The `source_caveats` passage on project-level counts was extended to say they are "stated in description rather than in the release-scoped count slots."

### 5. `instances` — AP-MS scope inconsistent with `file_collections`

**Changed.** With `counts: 1374` removed, the AP-MS Instance now carries a note reading that in the June 2026 release the AP-MS archives cover treated MDA-MB-468 cells only (paclitaxel and vorinostat), which matches the scope stated in the `#apms` file collection. The two slots no longer state different scopes for the same content.

### 6. `other_tasks: []`

**Changed.** The empty list is absent from both reconciled records. Absence and an empty list convey the same thing, and the schema treats omission as the representation of absent evidence.

### 7. `data_governance` — contact in prose rather than `committee_contact`

**Changed.** The reconciled object populates `committee_contact: Parker, Jillian; jillianparker@health.ucsd.edu; University of California San Diego`, and `access_review_process` no longer opens with the sentence identifying her; it now begins with the Data Access Committee description. A `source_caveats` value was added to the object noting that the release names the committee contact but no accountable organization, and pointing to `ip_restrictions` for the copyright-holding institutions. `accountable_organization` remains unpopulated for that reason.

### 8. `ethical_reviews` — contacts in prose rather than `contact_person`

**Changed.** The original had two entries, both with `contact_person` empty and both reviewers' names and emails inside `review_details`. The reconciled record has three entries: one for Ravitsky with `contact_person: Ravitsky, Vardit; ravitskyv@thehastingscenter.org; The Hastings Center`, one for Belisle-Pipon with `contact_person: Belisle-Pipon, Jean-Christophe; jean-christophe_belisle-pipon@sfu.ca; Simon Fraser University`, and the pre-existing Ethics Module process entry unchanged. Splitting the two named reviewers into separate entries also satisfies the one-object-per-entity rule for a multivalued slot.

### 9. `external_resources` — `archival` unpopulated where the bundle states it

**Changed.** Five of the seven entries now carry `archival`: `true` for the MassIVE deposits, the SRA deposit, the Figshare deposit and the project software entry; `false` for the CM4AI portal. The software entry additionally carries `future_guarantees` recording the Zenodo long-term archive for production-ready tools, GitHub for alpha tools, and the statement that software packages are versioned with the version referenced in each dataset's metadata. The portal entry gained a `restrictions` value quoting the administrative-review notice. The NDEx entry and the related-publications entry carry no `archival` value, since the bundle states nothing about their archival status.

### 10. `conforms_to_standard` under-specification

**Left as-is.** The audit itself recorded this as "a minor under-specification rather than an error" and judged the single `RO_CRATE` value defensible. `conforms_to_standard` still reads `[RO_CRATE]` in both records, and `conforms_to` still names RO-Crate packaging with FAIRSCAPE. The enum offers no term for the EVI ontology or for JSON-LD/RDF-XML serializations, and `OTHER` would carry less information than the prose already present in `conforms_to` and in `preprocessing_strategies`.

---

## Low-severity findings

### 11. `related_datasets` — uniform `is_new_version_of`

**Changed.** All four entries now use `relationship_type: is_version_of` in place of `is_new_version_of`, and each `description` was extended to say what the target is in the series: the October 2025 entry notes it is the immediately preceding release and is superseded by June 2026; June 2025 and March 2025 are described as earlier quarterly releases of the same resource; May 2024 as the first.

### 12. `collection_timeframes` — funding-period date as collection start

**Changed.** `start_date: '2022-09-01'` was removed. The entry now opens with "The bundle does not state when data collection began or ended" and retains the RePORTER project period, the November 2026 maintenance horizon and the preprint's first-year acquisition summary as prose. A `source_caveats` value on the object explains that the available dates are funding-period and deposit boundaries. A sentence to the same effect was added to the record-level `source_caveats`.

### 13. `sampling_strategies` — two strategies in one object

**Changed.** The single object was split into two. The first covers target selection (`is_sample: true`, `is_random: false`, `strategies` describing the protein and gene panels) and no longer carries `is_representative` or `why_not_representative`. The second covers selection of the biological material (`is_sample: true`, `is_representative: false`, `strategies` naming the two cell lines and their conditions, and the `why_not_representative` text about population-level variation).

### 14. `file_collections` — `total_bytes` unpopulated

**Changed.** All six collections now carry `total_bytes`, computed by summing the per-file sizes displayed on the release page: 249100 (`#apms`), 12600000000 (`#ifimages`), 265700 (`#secms`), 30200 (`#perturbseq-atlas`), 73300 (`#perturbseq-raw`), 1100000 (`#release-metadata`). Each collection carries a `source_caveats` value stating which per-file figures were summed and that KB/MB/GB were interpreted decimally, since exact byte counts are not stated. The record-level `source_caveats` notes that `total_size_bytes` remains omitted because the project-wide 21.4 TB figure is not a figure for this release, while per-collection totals are computed from stated per-file sizes.

In the core record these appear as `bytes` on each distribution, with the same `source_caveats` values carried over.

### 15. `raw_data_sources` — two deposits collapsed into one object

**Changed.** The fifth entry was split into two. One describes the raw sequence data for the CRISPRi Perturbation Cell Atlas in undifferentiated KOLF2.1J iPSCs; the other the Perturb-seq screens in MDA-MB-468 cells with and without treatment. Each records its own embargo status. All six entries now also carry `raw_data_format` — "mass spectrometry raw data files" for the four MS deposits, "single-cell sequencing reads" for the two sequencing deposits.

### 16. `version` — 2.0 and V2 unreconciled

**Changed.** `version` still reads `'2.0'`, which is what the page header states. The `source_caveats` passage on version labelling now states explicitly that the header's "Version 2.0" and the citation's "V2" on that same page "are the same version rendered two ways, not two versions," before going on to the cross-release inconsistencies. `version_access.version_details` was likewise reworded to say the version "is shown as 2.0 in the page header and as V2 in the citation string; these are the same version rendered two ways."

### 17. `known_biases` — selection bias recorded only as a limitation

**Changed.** A second `DatasetBias` entry was added with `bias_type: selection_bias`, describing the targeted rather than random selection of the ~100 chromatin modifiers and ~100 metabolic enzymes and the uneven coverage arising from incomplete overlap between modalities. It carries `affected_subsets` naming all three modalities and any cross-modality analysis, and a `mitigation_strategy` pointing to the documented selection criteria and the release's own advice about per-dataset analysis. The corresponding `integration_limitation` entry under `known_limitations` was left in place: the incomplete overlap bears on both slots, and the limitation entry addresses fitness for use while the bias entry addresses systematic non-randomness.

---

## Cross-record consistency

The core record was re-projected from the reconciled full record. Every change above is present in both where the core schema carries the slot: `creators` (47 entries with affiliations and PI), `instances` (no `counts`), `other_tasks` (absent), `data_governance.committee_contact`, three `ethical_reviews` entries, `external_resources` with `archival`, `related_datasets` with `is_version_of`, `collection_timeframes` without dates, two `sampling_strategies` objects, six `raw_data_sources`, two `known_biases`, `labeling_strategies` with `data_annotation_protocol`, and the revised `source_caveats` and `version_access.version_details`. `publisher` is absent from both. The `file_collections` totals appear in the core record as `bytes` on the corresponding `distributions` entries.

## Referent

Unchanged: both records describe the CM4AI data resource as embodied in the June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`, with earlier quarterly releases recorded under `related_datasets`. The referent statement stands at the head of `source_caveats` in both records.