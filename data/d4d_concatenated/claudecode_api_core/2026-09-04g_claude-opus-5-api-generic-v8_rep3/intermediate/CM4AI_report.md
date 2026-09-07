# Phase 4 Reconciliation Report — CM4AI

## Scope

The audit returned 23 findings against the full record (4 high, 5 moderate, 14 low). The core record is a projection of the full record and was re-derived after repair; no finding was raised against the core independently. Each finding below is stated with the disposition applied and the evidence visible in the diff between the original and reconciled records.

---

## High-severity findings

### 1. `instances[0].instance_type_notes` — invented, null-valued key

**Finding.** `instance_type_notes` is not among the slots the schema digest lists for `Instance` (`counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`), and it carried `null`.

**Action: removed, both records.** The key is absent from `instances[0]` in the reconciled full record and from `instances[0]` in the reconciled core record. The `notes` value on that entry, which carries the actual channel description, was retained unchanged.

### 2. `data_governance.committee_contact.id` — second identity for one person

**Finding.** The record minted `doi:10.18130/V3/HIGT4C#person-jillian-parker-governance` while simultaneously carrying `ORCID:0000-0003-4535-3486` for the same person under `creators`. The bundle's June 2026 author list gives "Parker J … ORCID https://orcid.org/0000-0003-4535-3486", and the same person is named as Data Governance Committee contact.

**Action: changed, both records.** The `id` is now `ORCID:0000-0003-4535-3486`. The `orcid` field was additionally populated (`https://orcid.org/0000-0003-4535-3486`) and `email: jillianparker@health.ucsd.edu` retained beside it. The minted fragment no longer appears anywhere in either record. Under the v8 rule, a person the documents list with an ORCID has one, and a fragment for that person is a second identity for one referent.

### 3. `creators[*].name` — expanded given names the bundle does not state

**Finding.** Six creator names carried given names no source supplies: `Ulrika Axelsson`, `Frida Ballllosero Navarro`, `Brenton Chinn`, `Christian Metallo`, `Alina Sigaeva`, and `Tim Clark` (the preprint gives "Timothy Clark", never "Tim").

**Action: changed, both records — applied across the whole roster.** Rather than repairing only the six flagged entries and leaving a roster written two ways, every creator `name` was rendered as the tier-1 release states it: surname plus initial. `Tim Clark` → `Clark T`; `Ulrika Axelsson` → `Axelsson U`; `Frida Ballllosero Navarro` → `Ballllosero Navarro F`; `Brenton Chinn` → `Chinn B`; `Christian Metallo` → `Metallo C`; `Alina Sigaeva` → `Sigaeva A`; and correspondingly for the remaining thirty-nine entries (`Sadnan Al Manir` → `Al Manir S`, `Trey Ideker` → `Ideker T`, and so on). Where the preprint does supply a full name, that name is now recorded in the entry's `notes` field as an attributed alternate form (e.g. `Given as "Timothy Clark" in the CM4AI preprint author list.`) rather than asserted as the value. The associated `principal_investigator` object under `Ideker T` was likewise renamed and gained `orcid` and `email` fields.

The `source_caveats` slot on both records was extended with a closing sentence recording this decision: "Creator names are rendered as the bundle states them, which for several authors is surname plus initial only."

Fragment ids for creators without an ORCID were renamed to match the new name form (`#person-ulrika-axelsson` → `#person-axelsson-u`, and the six others similarly), keeping label and value consistent.

### 4. `preprocessing_strategies`, `labeling_strategies`, `machine_annotation_tools` — pipeline stated as applied to this release

**Finding.** All three slots described the MuSIC cell-map construction pipeline as preprocessing applied to this dataset, while the June 2026 release states "Computed cell maps not included in this release" and "Does not contain predicted cell maps, which will be added in future releases". These steps produce an artifact the referent does not contain.

**Action: removed from the structured slots, relocated to `notes`, both records.** `preprocessing_strategies`, `labeling_strategies` and `machine_annotation_tools` are absent from the reconciled full record and from the reconciled core record. The pipeline description was moved into `notes`, restated explicitly as a project capability with the scoping the audit asked for: "The CM4AI Tools Module maintains the Multi-Scale Integrated Cell (MuSIC) pipeline, which … produces the computed cell maps that the June 2026 release states are not included in this release." This satisfies the v8 rule that a plan or a capability is stated as such or omitted, never as the current state of the dataset.

---

## Moderate-severity findings

### 5. `use_repository[0]` — value answers a neighbouring field

**Finding.** `UseRepository` is for resources tracking how the dataset has been used. The entry described the CM4AI portal's Publications page and its release archive — a project website and a version list, the latter duplicating `version_access.versions_available`.

**Action: removed, both records.** `use_repository` is absent from both reconciled records. The version-archive content remains in `version_access.versions_available`, unchanged; the portal itself remains in `external_resources[0]`.

### 6. `parent_datasets[0]` — a web page in a dataset-ranged slot

**Finding.** The entry's `id` was `https://cm4ai.org/data-releases/`, a documentation page listing releases, not a dataset. No parent dataset is attested.

**Action: removed, full record.** `parent_datasets` is absent from the reconciled full record. It is not a declared slot on `CoreDataset`, so the core was unaffected. The release-series relationship remains represented through the four `is_new_version_of` entries in `related_datasets`.

### 7. `regulatory_restrictions.other_compliance` — prohibited use duplicated

**Finding.** The clinical-use ban was carried both in `prohibited_uses[0]` and, verbatim, in `regulatory_restrictions.other_compliance`.

**Action: removed, both records.** `other_compliance` is absent from `regulatory_restrictions` in both reconciled records. The prohibition remains in `prohibited_uses[0]`.

### 8. `instances[*].data_substrate` — imprecise vocabulary terms

**Finding.** `B2AI_SUBSTRATE:58` (Mass Spectrometry Data) was used for the SEC-MS elution profile where 59 (Size Exclusion Chromatography-Mass Spectrometry Data) exists; `B2AI_SUBSTRATE:63` (Single-cell RNA Sequence Data) was used for the CRISPRi perturbation profile where 64 (Perturb-seq Data) exists.

**Action: changed, both records.** `instances[1].data_substrate` is now `B2AI_SUBSTRATE:59`; `instances[2].data_substrate` is now `B2AI_SUBSTRATE:64`. `instances[3]` (AP-MS) remains `B2AI_SUBSTRATE:58`, which the audit confirmed correct, and `instances[0]` remains `B2AI_SUBSTRATE:19`.

### 9. `file_collections[*].total_bytes` — derived figures asserted as measurements

**Finding.** Sizes stated in the bundle as "113.3 KB", "1.1 MB" and so forth were converted at an unstated 1 KB = 1000 bytes and asserted as exact integer byte counts. The three IF image collections received no `total_bytes` at all, so the slot was populated inconsistently across siblings.

**Action: removed, both records.** `total_bytes` is absent from every entry in `file_collections` in the reconciled full record, and `bytes` is absent from every entry in `distributions` in the reconciled core record. The source-stated sizes remain in each entry's `notes` verbatim ("Size stated on the release page as 113.3 KB"), which is what the bundle actually supplies. Under the v8 derived-figure rule, a computed value must be stated as the record's own computation with its inputs named; here the cleaner repair was to keep only the attested string and drop the unstated conversion, which also resolves the sibling inconsistency.

---

## Low-severity findings

### 10. `sampling_strategies[0].strategies` — project objective as realized strategy

**Action: changed, both records.** `strategies` now reads "Targeted selection of cell lines and perturbation targets rather than random sampling." The 100-chromatin-modifiers / 100-metabolic-enzymes figure was moved into a new `notes` field on the same object and marked as a stated project objective from the May 2024 preprint, with the observation that the June 2026 release does not state this release's actual target count.

### 11. `citation` and `creators[* Bélisle-Pipon].name` — accent stripped from quoted material

**Action: changed, both records.** The `citation` string now reads `Bélisle-Pipon JC`; the creator entry `name` now reads `Bélisle-Pipon JC`. As the audit noted, the governance/ethics contact line in the bundle itself writes the name unaccented, so `ethical_reviews[1].contact_person.name` was left as `Belisle-Pipon JC`, matching its own source passage.

### 12. `related_datasets[*].target_dataset` — resolver URLs against CURIEs elsewhere

**Action: changed, both records.** All seven targets are now `doi:` CURIEs (`doi:10.18130/V3/K7TGEM`, `doi:10.1101/2024.05.21.589311`, `doi:10.1038/s41586-025-08878-3`, and the four others), matching the form used by `id`, `doi` and `version_access.latest_version_doi`.

### 13. `prohibited_uses[*].prohibition_reason` — the prohibition rather than its reason

**Action: changed, both records.** Entry 0 now gives the reason ("appropriate regulatory oversight and approval have not been obtained for such use; these are laboratory data") and carries the source's verbatim prohibition text in a new `notes` field. Entry 1 now leads with the reason ("the copyright holders have reserved commercial rights") before the licensing detail.

### 14. `external_resources[*].archival` — boolean asserted without support

**Action: removed, both records.** `archival` is absent from all seven entries in both reconciled records. The bundle nowhere states the archival status of these resources.

### 15. `conforms_to` / `conforms_to_standard` — asserted from earlier releases and the preprint

**Action: changed, both records; also reflected in `source_caveats`.** `conforms_to` was expanded from the bare string `RO-Crate` to a scoped statement naming its provenance: the preprint and the March/June 2025 releases state the RO-Crate packaging, the June 2026 release page does not restate it, and its file listing names only `cm4ai_release_metadata.zip` without stating the internal format. `conforms_to_standard: [RO_CRATE]` was retained. `source_caveats` gained a sentence: "The conforms_to value is carried from the tier-3 preprint and the tier-5 March 2025 and June 2025 releases rather than from the June 2026 release page itself."

### 16. `distribution_formats[0].notes` — access route inside a format object

**Action: changed, both records.** The object now carries `access_urls: [https://dataverse.lib.virginia.edu/api/access/datafile/]`, which is the field the class provides for access information, and the `notes` text was shortened accordingly ("Files above the 1.9 GB browser download limit are obtained through the Data Access API"), no longer describing the route in prose alone.

### 17. `regulatory_restrictions.regulatory_restrictions[0]` — a negation in a restrictions slot

**Action: changed, both records.** The entry now reads "The release records FDA Regulated: No; no export control or regulatory restriction is stated for the release." The value still records an absence, because that is what the bundle states, but it now says so explicitly rather than reading as an entry describing a restriction.

### 18. `language` — inferred from the language of the sources

**Action: removed, both records.** `language: en` is absent from both reconciled records. The bundle nowhere states the dataset's language; omission over inference applies.

### 19. `last_updated_on` — supported omission

**Action: added, both records.** `last_updated_on: '2026-07-15T00:00:00Z'` was added, supported by the three IF image collections recorded on the release page as "Published Jul 15, 2026", after the 2026-06-17 issue date. The per-collection dates in `file_collections[*].notes` were already present and remain.

### 20. `ethical_reviews[*].contact_person.orcid` — declared field left empty

**Action: added, both records.** Both `contact_person` objects now carry `orcid` (`https://orcid.org/0000-0002-7080-8801` for Ravitsky V; `https://orcid.org/0000-0002-8965-8153` for Bélisle-Pipon JC) alongside the CURIE `id` and the email.

### 21. `addressing_gaps[1].response` — wording from a passage about another dataset

**Action: changed, both records.** The entry was rewritten from the Nature paper's U2OS framing ("Much of cell structure remains uncharted…") to a statement drawn from a passage about CM4AI itself: cell maps as a foundation for downstream human-genomics applications including variant and mutation interpretation, which existing black-box models do not support.

### 22. `subsets` / `file_collections` — two parallel id spaces with no cross-reference

**Action: changed, both records.** Rather than collapse either structure, each was made to point at the other. Every `subsets[*].description` now names the file collection that carries it ("Distributed as the file collection cm4ai_ifimages_MDA-MB-468_untreated.zip (doi:10.18130/V3/HIGT4C#files-ifimages-untreated)"), and every corresponding `file_collections[*].notes` names the subset it contains ("Contains the subset doi:10.18130/V3/HIGT4C#subset-ifimages-untreated"). Under the v6 rule a minted fragment must be pointed at by some value in the record; the eight subset/collection pairs now satisfy that in both directions. `#files-release-metadata` has no subset counterpart and none was invented. `subsets` is not declared on `CoreDataset`, so the cross-references appear in the core only on the `distributions` side.

### 23. `notes` — residual content duplicating structured slots

**Action: changed, both records.** The RO-Crate/FAIRSCAPE packaging sentence that duplicated `conforms_to` was removed from `notes`; the remaining FAIRSCAPE material was narrowed to the ARK identifier scheme and EVI provenance ontology, which no structured slot carries. The AI-Ready criteria list and six-module organization were retained — these are project-level facts that `description` (scoped to this release's contents) cannot hold — and the MuSIC pipeline description relocated from finding 4 was added.

---

## Left as-is

No finding was left entirely without action. Findings 15, 17 and 22 were addressed by qualification, cross-reference or explicit scoping rather than by removal, for the reasons given above; each is visible as a change in the diff.

## Core record

The core record was re-projected from the repaired full record after all changes above. Every repair that touches a slot the core schema declares is present in the core in the same form. Slots removed from the full record (`preprocessing_strategies`, `labeling_strategies`, `machine_annotation_tools`, `use_repository`, `language`, `total_bytes`/`bytes`, `archival`, `other_compliance`) are correspondingly absent from the core. `parent_datasets` and `citation` are not declared on `CoreDataset` and never appeared there. The `# Phase 4 reconciliation: completed` header line was written only after this phase ran.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `instances[0].instance_type_notes` | removed | both | Not a declared `Instance` slot in the schema digest; carried `null`. |
| `data_governance.committee_contact.id` | changed | both | Minted fragment replaced by `ORCID:0000-0003-4535-3486`, which the bundle supplies for the same person; removes a second identity for one referent. |
| `data_governance.committee_contact.orcid` | added | both | Declared field the bundle supplies; populated beside the CURIE id. |
| `creators[*].name` | changed | both | Rendered as the bundle states them (surname plus initial); expanded given names no source supplies were removed, with preprint full names moved to attributed `notes`. |
| `creators[*].notes` | added | both | Records the preprint's full-name form as an attributed alternate rather than asserting it as the value. |
| `creators[*].id` | changed | both | Minted person fragments renamed to match the corrected name form (`#person-axelsson-u`, etc.), keeping label and value consistent. |
| `creators[* Ideker T].principal_investigator` | changed | both | Name form corrected; `orcid` and `email` added from the bundle. |
| `preprocessing_strategies` | removed | both | Describes a pipeline producing an artifact the release states it does not contain; relocated to `notes` as a scoped project capability. |
| `labeling_strategies` | removed | both | Same as above — annotation of cell maps absent from this release. |
| `machine_annotation_tools` | removed | both | Same as above — tools of the cell-map pipeline, not of this release's contents. |
| `use_repository` | removed | both | Held a project publications page and a version archive, not a use-tracking resource; version content already in `version_access`. |
| `parent_datasets` | removed | full | Pointed at a documentation web page, not a dataset; not declared on `CoreDataset`. |
| `regulatory_restrictions.other_compliance` | removed | both | Verbatim duplicate of `prohibited_uses[0]`. |
| `instances[1].data_substrate` | changed | both | `B2AI_SUBSTRATE:58` → `59`, the exact SEC-MS term. |
| `instances[2].data_substrate` | changed | both | `B2AI_SUBSTRATE:63` → `64`, the exact perturb-seq term. |
| `instances[3].data_substrate` | retained | both | `B2AI_SUBSTRATE:58` confirmed correct for AP-MS. |
| `file_collections[*].total_bytes` | removed | full | Unstated decimal conversion asserted as exact measurement; applied inconsistently across siblings. Source-stated sizes retained in `notes`. |
| `distributions[*].bytes` | removed | core | Projection of the removed `total_bytes`. |
| `sampling_strategies[0].strategies` | changed | both | Project objective replaced by the strategy actually attested; objective moved to `notes` and dated. |
| `sampling_strategies[0].notes` | added | both | Carries the 100/100 target figure as a stated May 2024 project objective, not this release's realized coverage. |
| `citation` | changed | full | Accent restored in `Bélisle-Pipon JC`; quoted material keeps its source form. Not declared on `CoreDataset`. |
| `creators[* Bélisle-Pipon].name` | changed | both | Accent restored to match the bundle's author list. |
| `ethical_reviews[1].contact_person.name` | retained | both | The bundle's governance/ethics contact line itself writes the name unaccented; the value matches its own source passage. |
| `related_datasets[*].target_dataset` | changed | both | Resolver URLs replaced by `doi:` CURIEs, matching the identifier form used elsewhere in the record. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Now states the reason (regulatory oversight absent) rather than restating the prohibition. |
| `prohibited_uses[0].notes` | added | both | Carries the release's verbatim prohibition text. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Now leads with the reason (commercial rights reserved) before the licensing detail. |
| `external_resources[*].archival` | removed | both | Boolean the bundle nowhere supports, in all seven entries. |
| `conforms_to` | changed | both | Scoped to name its source (preprint and earlier releases) rather than asserting it of the June 2026 release page. |
| `conforms_to_standard` | retained | both | `RO_CRATE` remains the registered term for the standard `conforms_to` names. |
| `distribution_formats[0].access_urls` | added | both | Access route moved from prose into the field the class provides for it. |
| `distribution_formats[0].notes` | changed | both | Shortened once the access route moved to `access_urls`. |
| `regulatory_restrictions.regulatory_restrictions[0]` | changed | both | Now states explicitly that no restriction is recorded, rather than reading as a restriction entry. |
| `language` | removed | both | `en` inferred from the language of the sources; not stated anywhere in the bundle. |
| `last_updated_on` | added | both | Supported by the three IF image collections published 2026-07-15, after the issue date. |
| `ethical_reviews[0].contact_person.orcid` | added | both | Declared field the bundle supplies for Ravitsky V. |
| `ethical_reviews[1].contact_person.orcid` | added | both | Declared field the bundle supplies for Bélisle-Pipon JC. |
| `addressing_gaps[1].response` | changed | both | Rewritten from the Nature U2OS framing to a passage about CM4AI itself. |
| `subsets[*].description` | changed | full | Each now names the file collection carrying it, so the minted subset ids are pointed at. Not declared on `CoreDataset`. |
| `file_collections[*].notes` | changed | full | Each now names the subset it contains, completing the cross-reference. |
| `distributions[*].notes` | changed | core | Projection of the `file_collections[*].notes` cross-references. |
| `notes` | changed | both | RO-Crate duplication of `conforms_to` removed; MuSIC pipeline relocated here with explicit scoping; AI-Ready criteria and module structure retained as project-level facts `description` cannot hold. |
| `source_caveats` | changed | both | Extended to record the `conforms_to` provenance and the surname-plus-initial naming decision. |