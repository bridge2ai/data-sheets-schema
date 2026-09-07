# Phase 4 Reconciliation Report — VOICE

## Scope

The Phase 3 audit returned 16 findings against the full record: none high, eleven medium, five low. No fabricated identifiers, no prior-D4D reuse, no enum violations, and no arithmetic defects were reported. The dominant defect class was scope leakage across the referent boundary — facts about the raw-audio distribution, the pediatric release, and unused remote-collection modalities asserted in the referent's own slots. The second was absence-as-answer, where a slot was populated with a statement that documentation does not exist. The third was a field mismatch in `prohibited_uses`.

The referent decision is unchanged: this record describes the adult Bridge2AI-Voice dataset at version 3.1.0 as published on PhysioNet (tier 1, not superseded). Reconciliation tightened the boundary around that referent rather than moving it.

## Changes made to the full record

### Scope leakage (five findings, all acted on)

**`conforms_to` and `conforms_to_standard` — removed.** Both slots asserted BIDS v1.9.0 conformance for the featurized PhysioNet release. The tier-1 v3.1.0 description gives a features/metadata/phenotype layout and never mentions BIDS; the tier-2 project documentation attributes BIDS conversion to the `b2ai-voice-audio` distribution. The record's own caveat already conceded the mismatch. Both slots are now absent from the full record; the BIDS fact was relocated to the `derives_from` entry in `related_datasets`, where it describes the raw-audio collection that actually carries that layout. The top-level `source_caveats` was rewritten to explain the relocation rather than merely flag the tension.

**`preprocessing_strategies[5]` — removed.** The sixth entry described the BIDS conversion with per-participant/per-session WAV directories and JSON sidecars. That is a processing step of the raw-audio distribution, not of this release. The list now holds five entries; the content survives inside the `derives_from` note.

**`distribution_formats[1]` — removed.** The controlled-access raw-audio distribution with the Synapse URL was listed as a format of this dataset. The referent excludes raw waveforms, which already appear under `related_datasets` with `derives_from`. `distribution_formats` now holds one entry, the PhysioNet registered-access release. The Synapse route remains recorded in `raw_data_sources[0].access_details`, in `data_governance.access_review_process`, and in the `derives_from` note — all places where it correctly describes something other than this release's own format.

**`collection_mechanisms[3]` — removed.** The Web app and iOS app remote-collection entry described an approved-but-unused modality. Tier-1 methods describe tablet collection; the project documentation states remote collection did not occur for the released data. The list now holds three entries. A new paragraph in the top-level `source_caveats` records why the modality is absent.

**`collection_consents[0]` — changed.** The entry's closing sentences on pediatric parental consent and child assent were removed, since this dataset enrolls adults only (minimum age 18). The remote-consent mechanisms (REDCap survey form, in-app) were kept, as those apply to adult enrollment. The pediatric assent detail was moved into the `is_supplemented_by` note for the pediatric release, where it belongs.

### Absence-as-answer (two findings, both acted on)

**`data_protection_impacts` — removed.** The single entry stated that no impact analysis had been conducted. That is the absence of a DPIA, not a DPIA. The slot is now absent from the full record; the fact is preserved in the top-level `source_caveats`.

**`errata[0]` — removed.** The first entry read "There is no erratum" and pointed at a changelog. The second entry, carrying the actual corrections across versions 2.0, 2.0.1 and 3.1.0, is retained and is now the sole entry, with the changelog pointer moved to its `notes`.

### Field mismatch (one finding, acted on)

**`prohibited_uses[0..2]` — changed.** Each entry placed the prohibited act in `prohibition_reason`, leaving the reason unstated. All three were restructured: the prohibited use now sits in `description`, and `prohibition_reason` carries the reason the bundle supplies — the consortium's commitment to protecting participants' rights and interests; prevention of unethical or biased outcomes based on health condition or voice characteristics; and preservation of unrestricted downstream access in alignment with Open Science principles.

### Overstated boolean (one finding, acted on)

**`at_risk_populations.at_risk_groups_included` — removed.** The value `false` was contradicted by the record's own neurological cohort (mild cognitive impairment, Alzheimer's disease, other dementias) and mood and psychiatric cohort. The bundle nowhere states that no at-risk groups are included; the IRB protocol's silence on adults is an absence of discussion, not a negative finding. The boolean is gone; `special_protections` is unchanged and the `source_caveats` on the object was rewritten to say explicitly that no determination is recorded because the bundle makes none.

### Plan-versus-actual (two findings, both acted on)

**`sampling_strategies[0].strategies` — changed.** The flyer/QR-code, waiting-room, social-media, FlowTrials and targeted-record-review items were removed from the `strategies` list, which now holds two items: non-probability sampling and purposive recruitment from high volume expert clinics. Those five approved-but-unattested methods were moved to a new `notes` field on the entry, which states plainly that they are IRB-approved across the protocol's four phases and that the bundle does not attest which supplied the 833 released participants. `source_data` was also tightened to match the tier-1 wording ("screened … by the project investigators").

**`collection_timeframes[0].timeframe_details` — changed.** The value now carries only the twelve-month collection statement. The NIH award period (a funding fact, already recorded under `funders`) and the protocol's four-phase four-year plan (an intention) were removed. The existing caveat about the twelve-month figure's provenance is retained.

### Field-answering (two findings, both acted on)

**`other_tasks` — removed.** The single entry named no additional task; it restated the absence of splits (carried in `splits`) and the labeling-documentation guidance. The slot is absent from the full record. The labeling guidance was moved to `labeling_strategies[0].notes`, where it answers a question the slot actually asks.

**`machine_annotation_tools[0].tool_accuracy` — changed to `notes`.** The statement that off-the-shelf models were not audited for correctness is a quality caveat, not an accuracy figure. It now sits in `notes` on the entry, rephrased to say explicitly that no accuracy figures are available. `tool_accuracy` is absent.

### Cross-reference (one finding, acted on)

**`known_biases[*].affected_subsets` — changed.** The `selection_bias` entry's prose value "All disease cohorts" was replaced with the four minted `DataSubset` identifiers for the disease cohorts (voice, respiratory, neurological, mood/psychiatric — the control cohort is excluded, since it is not a disease cohort). This makes the minted subset labels load-bearing rather than decorative. The `measurement_bias` entry's `affected_subsets` value "Recordings grouped by collection site" was removed entirely rather than converted: the record mints no site subsets, so there is no identifier to point at, and the site grouping is already stated in the entry's `bias_description`.

## Findings left as-is

**`creators[*]` / `distribution_formats[*]` / `external_resources[*]` / `variables[*]` carrying `name` and `description`.** The audit flagged these as keys the schema digest does not list for those classes, but explicitly conditioned the finding on schema inheritance and warned against stripping attested content to satisfy the digest's abbreviation. Both records validated with these values present, so the slots are inherited and the values were retained unchanged in both records.

**`publisher`.** The audit noted that `https://physionet.org/` is inferred rather than explicitly stated — the bundle names PhysioNet as the hosting platform and as the journal field of the citation. The inference is defensible and the value was retained in both records; a sentence was added to the top-level `source_caveats` recording that the bundle makes no explicit publisher statement.

**`use_repository` and `imputation_protocols`.** The audit checked these omissions and found them correct: the bundle answers "No" to the repository question and states that no imputation was performed. Both remain absent from both records.

## Core record

The core record was re-projected from the reconciled full record. Every change above propagates to the core where the core schema declares the slot. Two of the removed slots — `conforms_to` and `conforms_to_standard` — were present in the original core and are now absent. Three removed slots (`data_protection_impacts`, `other_tasks`, `at_risk_populations.at_risk_groups_included`) were likewise present in the original core and are now absent; `errata[0]`, `distribution_formats[1]`, `collection_mechanisms[3]` and `preprocessing_strategies[5]` were also present and are gone. `collection_consents` is not declared in the core schema and does not appear in either core record, so that change is full-only. `citation` and `consent_revocations` are likewise full-only. The core header now carries `# Phase 4 reconciliation: completed`.

## Dispositions

| slot | disposition | record | reason |
| --- | --- | --- | --- |
| `conforms_to` | removed | both | BIDS conformance is attested for the raw-audio distribution, not for the featurized PhysioNet release this record describes; relocated to `related_datasets` derives_from note. |
| `conforms_to_standard` | removed | both | Same misattribution as `conforms_to`; no standard is attested for this release's own layout. |
| `preprocessing_strategies[5]` | removed | both | BIDS conversion step describes the raw-audio distribution, not this release; content preserved in `related_datasets`. |
| `distribution_formats[1]` | removed | both | Controlled-access raw audio is another resource's access route, already recorded under `related_datasets` with `derives_from`. |
| `collection_mechanisms[3]` | removed | both | Remote Web/iOS app collection is an approved but unused modality; documentation states remote collection did not occur for released data. |
| `collection_consents[0]` | changed | full | Pediatric parental consent and child assent removed (adults-only dataset); relocated to the pediatric entry in `related_datasets`. |
| `data_protection_impacts` | removed | both | Value recorded the absence of a DPIA rather than a DPIA; fact preserved in top-level `source_caveats`. |
| `errata[0]` | removed | both | First entry stated "There is no erratum" plus a pointer; the substantive corrections entry is retained as the sole entry. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Now carries the reason (protection of participants' rights and interests) rather than restating the prohibition. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Now carries the reason (preventing unethical or biased outcomes) rather than restating the prohibition. |
| `prohibited_uses[2].prohibition_reason` | changed | both | Now carries the reason (preserving unrestricted downstream access under Open Science principles). |
| `prohibited_uses[0].description` | added | both | The prohibited use itself, moved out of `prohibition_reason` into the descriptive field. |
| `prohibited_uses[1].description` | added | both | The prohibited use itself, moved out of `prohibition_reason`. |
| `prohibited_uses[2].description` | added | both | The prohibited use itself, moved out of `prohibition_reason`. |
| `at_risk_populations.at_risk_groups_included` | removed | both | `false` contradicted by the record's own dementia and psychiatric cohorts; bundle states no determination. |
| `at_risk_populations.source_caveats` | changed | both | Rewritten to state that the bundle makes no determination about the neurological or psychiatric cohorts. |
| `sampling_strategies[0].strategies` | changed | both | Approved-but-unattested recruitment methods removed from the list of realized strategies. |
| `sampling_strategies[0].notes` | added | both | Records the IRB-approved recruitment methods as plan, and that the bundle does not attest which supplied the released participants. |
| `sampling_strategies[0].source_data` | changed | both | Tightened to the tier-1 wording naming project investigators as screeners. |
| `collection_timeframes[0].timeframe_details` | changed | both | Award period (a funding fact) and four-phase plan (an intention) removed; twelve-month collection statement retained. |
| `other_tasks` | removed | both | Named no additional task; content duplicated `splits` and labeling guidance, the latter relocated to `labeling_strategies`. |
| `labeling_strategies[0].notes` | changed | both | Extended with the new-label documentation guidance relocated from `other_tasks`. |
| `machine_annotation_tools[0].tool_accuracy` | removed | both | Held a caveat about unaudited models, not an accuracy figure. |
| `machine_annotation_tools[0].notes` | added | both | Carries the unaudited-model caveat, stating that no accuracy figures are available. |
| `known_biases[0].affected_subsets` | changed | both | Prose "All disease cohorts" replaced with the four minted disease-cohort `DataSubset` identifiers. |
| `known_biases[2].affected_subsets` | removed | both | No site subsets are minted, so no identifier exists to reference; the site grouping is already in `bias_description`. |
| `related_datasets[0].notes` | changed | both | Extended with pediatric parental consent and assent procedures relocated from `collection_consents`. |
| `related_datasets[1].notes` | changed | both | Extended with the BIDS v1.9.0 layout and controlled-access route relocated from `conforms_to` and `distribution_formats`. |
| `raw_data_sources[0].access_details` | changed | both | Opens by stating raw audio is not part of this release, before describing the controlled-access route. |
| `third_party_sharing[0].notes` | changed | both | Adjusted to say the data sits behind registered access, since controlled access governs a different resource. |
| `source_caveats` | changed | both | Rewritten to record the BIDS relocation, the excluded remote-collection modality, the raw-audio boundary, the inferred publisher, and the absent DPIA. |
| `creators[*].name` | retained | both | Audit flagged conditionally on schema inheritance; both records validate with the values present, so attested content was kept. |
| `creators[*].description` | retained | both | Same conditional finding; validated and retained. |
| `distribution_formats[0].name` | retained | both | Same conditional finding; validated and retained. |
| `external_resources[*].name` | retained | both | Same conditional finding; validated and retained. |
| `variables[*].description` | retained | full | Same conditional finding; validated and retained. `variables` is full-only. |
| `publisher` | retained | both | Inference from hosting platform and citation journal field is defensible; caveat added rather than value removed. |