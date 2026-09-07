# Phase 4 Reconciliation Report — VOICE

## What the audit found

The Phase 3 audit returned sixteen findings against the full record: one major, thirteen minor, and two informational. The summary confirmed that no unsupported hard facts were present — every quantitative claim (833 participants, five North American sites, the nine Parquet feature files and their per-feature record counts, FFT parameters, phenotype directory contents, release history and DOIs, compensation amounts, retention terms, AI-readiness scores) was verified accurate for version 3.1.0.

The findings clustered into four patterns:

1. **Subject drift.** Facts drawn from the umbrella IRB protocol's pediatric arm, the sibling pediatric dataset, and the audio dataset were asserted as facts about this adult feature-only release (`at_risk_populations`, `ethical_reviews[1]`, `preprocessing_strategies[2]`).
2. **Earlier-release state presented as current.** `content_warnings`, `collection_timeframes`, and part of `license_and_use_terms.license_terms` carried superseded conditions.
3. **Fields answered with an absence or a pointer.** `splits[0].split_details` and `external_resources[0].future_guarantees`.
4. **Shape defects.** `related_datasets[*].target_dataset` carried prose where identifiers belong.

Plus three inference/naming issues (`regulatory_restrictions` enums, `maintainers[1]`, `existing_uses[0].notes`) and two informational observations.

## What was changed, and why

### Major — subject drift into `at_risk_populations`

The audit's central finding: `at_risk_populations.guardian_consent` asserted guardian-consent provisions for a release whose eligibility is 18–120 years and whose own text conceded "Pediatric enrollment is outside this adult dataset." The provision governs the separately released pediatric dataset.

**The entire `at_risk_populations` object was removed from both records.** This resolves three findings at once — `guardian_consent` (major), `special_protections` bullet 1 (minor), and `at_risk_groups_included` (minor). Removing the whole object rather than trimming it was the right call: with `guardian_consent` gone and bullet 1 of `special_protections` gone, what remained was a statement that pediatric participants were enrolled elsewhere and that this cohort is adults — which is not a protection this dataset applies but a scope statement, already carried by `human_subject_research` and the study-metadata content in `notes`. And `at_risk_groups_included: true` had no source classifying these participants as an at-risk population; it was this record's inference from the presence of cognitive-impairment and psychiatric cohorts. The participants concerned remain documented under `human_subject_research.special_populations`, which is the field that actually asks the question the evidence answers.

### Subject drift — `ethical_reviews[1]`

The Canadian research ethics board entry described the umbrella protocol's Canadian arm and the separate genomic sub-protocol, neither of which governs this release; the entry's own text conceded the genomic work "is not part of this release." The tier-1 source states only USF IRB approval.

**Removed from both records.** The corresponding phrase "with separate research ethics board review for the Canadian sites" was also dropped from `human_subject_research.regulatory_compliance[0]`, which now reads "HIPAA; a Certificate of Confidentiality covering the data; the Single IRB process for United States sites." Leaving the Canadian clause there would have reintroduced by the back door exactly what was removed from `ethical_reviews`.

### Subject drift — `preprocessing_strategies[2]`

The BIDS v1.9.0 conversion describes the folder layout of the audio dataset (`b2ai-voice-audio`, with `sub-<participant_id>/ses-<...>/audio/*.wav`), not this feature-only release.

**Removed as a preprocessing entry in both records; the fact was relocated into `raw_sources[0].raw_data_details`** with explicit scoping: "that conversion describes the audio dataset's folder layout rather than this feature-only release." The fact is attested and worth carrying — it belongs to the raw sources this release derives from, which is where it now sits, rather than being asserted as a processing step applied to the released files. `preprocessing_strategies` went from three entries to two in both records.

### Earlier-release state — `content_warnings`

`content_warnings_present: true` rested on the healthsheet's free-speech transcription warning, but the same bundle records that transcripts of free speech audio were removed at v1.1, and that spectrograms, MFCCs, Mel spectrograms, transcriptions, EMAs and PPGs from open-response prompts are excluded from the feature-only release at v3.0.0 and v3.1.0.

**The boolean was flipped to `false` in both records, and the warning text was rewritten** to attribute the healthsheet warning to its source, state what it says, and then state why it does not describe version 3.1.0. The `source_caveats` field, which had acknowledged the conflict while the boolean still asserted the superseded state, was dropped as redundant — the warning text now carries the whole account. The slot is retained rather than removed because a reader checking "does this release carry offensive content?" deserves the reasoning, not silence.

### Earlier-release state — `collection_timeframes`

**Retained with a `source_caveats` added** to both records. The twelve-month figure is attested and is the only collection-period statement in the bundle, so removing it would lose information. The added caveat scopes it: the documentation is written against versions 2.0.0 and 3.0.0, the 3.1.0 cohort accumulated across releases from 306 participants at v1.0 to 833 at v3.0.0, and no tier-1 source states a collection period.

### Earlier-release state — `license_and_use_terms.license_terms`

**Rewritten in both records** to lead with the version 3.1.0 policy ("For version 3.1.0 the access policy is credentialed"), drop the registered-access process description from the body, and retain the controlled-access route for raw audio with an explicit note that raw audio "is not part of this release." **A `source_caveats` was added** recording that PhysioNet lists v1.1 as restricted access open to registered users and v3.0.0/v3.1.0 as credentialed, and that the documentation's registered-access description belongs to an earlier release.

### Fields answered with an absence — `splits` and `future_guarantees`

`splits[0].split_details` **was changed in both records** to keep only the actionable half: "Researchers are encouraged to create their own data splits based on their specific requirements." The negative statement was moved to `notes`, which now ends "No recommended train, validation or test splits are supplied with the release."

`external_resources[0].future_guarantees` **was changed in both records** from reporting that the healthsheet "answers 'not applicable'" to stating the substantive position: no guarantee of persistence is offered, and these are supporting materials rather than dependencies.

### Shape defect — `related_datasets[*].target_dataset`

All four values were descriptive prose. **All four were reduced to bare identifiers in both records** — `10.13026/h995-bt35`, `10.13026/k81f-qr68`, `10.13026/37yb-1t42`, `syn72370534` — with the descriptive material moved to each entry's `notes`. The third entry, which previously had no `notes`, gained one. The fourth entry's Synapse URL survives inside the note text.

### Inference and naming

`maintainers[1]` **was changed in both records**: `role` from `academic_institution` to `other` (an access-compliance office is not an academic institution), and the unsupported "Curates the dataset" dropped — the bundle names DACO as the access-review body, and the healthsheet's curator contact is redacted. The entry now reads "Reviews access requests for the raw audio and receives questions about access."

`regulatory_restrictions.confidentiality_level` and `.hipaa_compliant` **were retained in both records with a `source_caveats` added** stating that neither term is used verbatim by a source and naming the derivation for each: `restricted` from the credentialed access policy and signed DUA; `compliant` from the healthsheet's "Yes" on applying HIPAA de-identification rules plus the protocol's HIPAA-compliant collection and storage. The classifications are supportable; the derivation is now legible.

`existing_uses[0].notes` **was changed in both records** to drop the coined "Bridge2AI Voice Scholars program" and give what the bundle states: "The project documentation lists training opportunities for using the dataset at https://www.b2aivoicescholars.org/".

### Informational findings

`conforms_to` / `conforms_to_standard` **were left omitted**; the decision is now recorded in `source_caveats` in both records, which explains that the attested BIDS statement concerns the audio dataset and is carried in `raw_sources` rather than asserted as a property of this release.

`creators` granularity **was left as-is**; a `source_caveats` was added to the consortium entry in both records noting that PhysioNet enumerates roughly 120 individual authors and that authorship is represented here at institution and consortium granularity.

### Record-level `source_caveats`

**Extended in both records** with a paragraph naming the referent as the adult feature-only release and stating that facts governing only the pediatric arm, the pediatric dataset, the controlled-access raw audio, or the Canadian genomic sub-protocol are not recorded as facts about this release — with the BIDS decision spelled out as the worked example.

## What was left as-is

Nothing from the audit was left unaddressed. Three findings resolved to retention-with-caveat rather than change (`collection_timeframes`, `regulatory_restrictions` enums, `creators` granularity) and one to a documented omission (`conforms_to`). Every quantitative fact the audit verified was left untouched: participant counts, feature-file record counts, DSP parameters, phenotype directory listing, release history, DOIs, compensation, retention, and AI-readiness scores are byte-identical between the original and reconciled records.

## Core record

All changes were mirrored into the core record where the core schema declares the slot. `at_risk_populations`, `ethical_reviews`, `preprocessing_strategies`, `content_warnings`, `collection_timeframes`, `license_and_use_terms`, `regulatory_restrictions`, `maintainers`, `existing_uses`, `external_resources`, `related_datasets`, `raw_sources`, `human_subject_research`, `creators`, `notes` and `source_caveats` are all core-declared and carry the reconciled values. `splits` is not carried in the core record; the substance survives there through the `notes` sentence. The core header now reads `# Phase 4 reconciliation: completed`.

## Counts

- Full record: 78 top-level slots populated (was 80 — `at_risk_populations` and `splits` removed).
- Core record: 61 top-level slots populated (was 62 — `at_risk_populations` removed).
- Both validated against their respective schemas.

## Dispositions

| slot | disposition | record | reason |
| --- | --- | --- | --- |
| `at_risk_populations` | removed | both | Guardian-consent, assent and at-risk-group claims describe the umbrella protocol's pediatric arm, not this 18–120 adult release; `at_risk_groups_included: true` was an unsourced inference. Participants concerned remain under `human_subject_research.special_populations`. |
| `ethical_reviews[1]` | removed | both | Described the Canadian REB arm and the genomic sub-protocol, neither governing this release; tier-1 states only USF IRB approval. |
| `human_subject_research.regulatory_compliance` | changed | both | Dropped "with separate research ethics board review for the Canadian sites" to match the removal of `ethical_reviews[1]`. |
| `preprocessing_strategies[2]` | removed | both | The BIDS v1.9.0 conversion describes the audio dataset's folder layout, not a processing step of this feature-only release. |
| `raw_sources[0].raw_data_details` | changed | both | Absorbed the BIDS conversion fact with explicit scoping to the audio dataset, so an attested fact is kept without misattributing it. |
| `content_warnings[0].content_warnings_present` | changed | both | Flipped `true` → `false`: free-speech transcripts were removed at v1.1 and free-speech-derived features excluded at v3.0.0/v3.1.0, so the release does not distribute the content the warning concerns. |
| `content_warnings[0].warnings` | changed | both | Rewritten to attribute the healthsheet warning to its source and state why it describes an earlier release. |
| `collection_timeframes[0]` | retained | both | Only collection-period statement in the bundle; kept with a new `source_caveats` scoping it to the documentation's release and noting the cohort accumulated across versions. |
| `license_and_use_terms.license_terms` | changed | both | Rewritten to lead with the v3.1.0 credentialed policy and mark raw audio as outside this release; registered-access process moved to a new `source_caveats`. |
| `splits` | removed | full | The single entry only recorded the absence of recommended splits; the actionable half was rewritten first, then the slot dropped from the full record with the substance moved to `notes`. |
| `external_resources[0].future_guarantees` | changed | both | Replaced a report of the healthsheet's "not applicable" with the substantive position: no persistence guarantee offered. |
| `related_datasets[0].target_dataset` | changed | both | Prose reduced to the bare identifier `10.13026/h995-bt35`; description moved to `notes`. |
| `related_datasets[1].target_dataset` | changed | both | Prose reduced to `10.13026/k81f-qr68`; description moved to `notes`. |
| `related_datasets[2].target_dataset` | changed | both | Prose reduced to `10.13026/37yb-1t42`; description moved to a newly added `notes`. |
| `related_datasets[3].target_dataset` | changed | both | Prose reduced to `syn72370534`; access route and URL moved to `notes`. |
| `maintainers[1].role` | changed | both | `academic_institution` → `other`: an access-compliance office is not an academic institution. |
| `maintainers[1].maintainer_details` | changed | both | Dropped "Curates the dataset", which the bundle does not state; DACO is named only as the access-review body. |
| `regulatory_restrictions.confidentiality_level` | retained | both | Supportable reading of the credentialed access policy; derivation now recorded in a new `source_caveats`. |
| `regulatory_restrictions.hipaa_compliant` | retained | both | Supportable reading of the healthsheet's HIPAA answer plus the protocol's storage account; derivation now recorded in the same `source_caveats`. |
| `existing_uses[0].notes` | changed | both | Dropped the coined "Bridge2AI Voice Scholars program"; gives the URL as the documentation states it. |
| `creators[2].source_caveats` | added | both | Records that PhysioNet lists ~120 authors and that authorship is represented at institution/consortium granularity. |
| `conforms_to` | retained | both | Left omitted; the omission is now explained in the record-level `source_caveats` (the BIDS statement concerns the audio dataset). |
| `notes` | changed | both | Absorbed the statement that no recommended splits are supplied, following the removal of `splits`. |
| `source_caveats` | changed | both | Extended with a paragraph naming the referent and stating the scoping rule applied to pediatric, raw-audio and Canadian-genomic material. |