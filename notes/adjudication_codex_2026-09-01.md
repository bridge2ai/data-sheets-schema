## Rulings

| # | Verdict | Reason |
|---:|---|---|
| 1 | `misread` | The table marks metadata—not published schemas—as planned for notes, imaging, and EEG; telemetry metadata is “Yes,” and published schemas are present. |
| 2 | `weak` | Internal site reporting on extract curation is not a released-dataset update plan or user-facing update communication. |
| 3 | `weak` | The passages state future balancing and comprehensiveness aims, not a sampling method actually used to select instances. |
| 4 | `weak` | The passages mention the enclave, Collaborative Cloud, and Azure apps separately without establishing their asserted identity or tooling relationship. |
| 5 | `inferred` | The bundle says “Imaging (from PACS)”; classifying or expanding PACS as an “imaging archive” requires unstated domain knowledge. |
| 6 | `inferred` | `2026-11-30` is the NIH project end, not a stated data-collection end date. |
| 7 | `followed` | Repository references supplement substantive preprocessing and collection-mechanism details rather than substituting for missing answers. |
| 8 | `violated` | A website/repository review banner was placed in the dataset’s `status` field. |
| 9 | `weak` | The passage supports Rashidi’s leadership membership, name, and affiliation, but not PI status. |
| 10 | `weak` | The passage supports Kwong’s leadership membership, name, and affiliation, but not PI status. |
| 11 | `weak` | The passage supports Bihorac’s leadership membership, name, and affiliation, but not PI status. |
| 12 | `inferred` | Controlled access and broad program eligibility imply, but never state, sharing beyond contributing institutions. |
| 13 | `inferred` | The public goal, controlled access, registration, and license are stated; extension beyond contributing institutions is not. |
| 14 | `violated` | The record carries admitted or unstated inferences, including expanding PICU/NICU and inventing limitation impacts. |
| 15 | `followed` | Checking the current snapshot is itself an actionable mitigation; other references supplement substantive answers. |
| 16 | `violated` | The Cloud-enclave distribution entry carries an access route and generic project webpage rather than a distribution format. |
| 17 | `violated` | Creator `name` fields contain role phrases while the attested personal names are displaced into `principal_investigator`. |
| 18 | `violated` | Optional project-URL fragments are used to identify real people and external entities instead of attested identifiers or omission. |
| 19 | `violated` | `impact_details` and `extension_details` are populated solely with statements that the requested analysis or mechanism is absent. |
| 20 | `violated` | Payment timing does not answer compensation rationale, and storage/access controls are not an anonymization method. |
| 21 | `not_applicable` | All relevant FileCollection/DataSubset fragment IDs are schema-required once those source-described objects exist; no discretionary mint is present. |
| 22 | `supported` | The cited chunks collectively support login/self-attestation, T2D-only use, authorized-group membership and termination, and copyright. |
| 23 | `weak` | Staff responsibility for building pipelines and infrastructure does not describe preprocessing steps applied to the data. |
| 24 | `weak` | The cited passages support only OMOP, DICOM, and RO-Crate; four other standards occur only in uncited bundle passages. |
| 25 | `bundle_supports` | Line 4327 expressly names EKG and blood-pressure devices, while the Garmin passages support wearable heart-rate recording. |
| 26 | `violated` | Returning results after participation does not answer how participants were notified about data collection. |
| 27 | `not_applicable` | Every disputed FileCollection fragment is forced by the class’s required identifier; rule-14 has no optional mint to govern. |
| 28 | `supported` | Although the snippet anchor names the consortium, the immediately adjacent cited author-list passage names Yael Bensoussan. |
| 29 | `inferred` | Bahr is called a lead investigator/Lead Voice Disorders, while only Bensoussan and Elemento are identified as co-PIs. |
| 30 | `violated` | The record converts domain and cohort leads into principal investigators without source support. |
| 31 | `violated` | `split_details` is populated solely to say recommended splits are absent and users must create their own. |
| 32 | `violated` | Cohort/domain lead roles are placed in `principal_investigator`, despite the source naming only two co-PIs. |
| 33 | `weak` | Focus groups and legal/community ethics research are not an ethical-review process, board decision, or outcome. |
| 34 | `weak` | The passages establish available geocoding code and desired contextual factors, not preprocessing applied to this dataset. |
| 35 | `weak` | Registration, licensing, contacts, cloud access, and federated sampling do not describe review, reviewer, criteria, or decision. |
| 36 | `misread` | A scheduled future start is rendered as “Cohort 2 began,” and one cohort’s capacity is generalized per cohort. |
| 37 | `weak` | The receipts only name privacy/de-identification repositories; the substantive notes and imaging claims come from uncited c003. |
| 38 | `weak` | Future annotation capability does not establish labeling performed or provide procedures, guidelines, tasks, or quality control. |
| 39 | `supported` | The cited passage names Data Site Managers and their continuing curation, extraction, delivery, and status-reporting responsibilities. |
| 40 | `inferred` | Leadership-team membership supports Bihorac’s identity and affiliation, not PI status. |
| 41 | `inferred` | “Deterioration” is an isolated preferred term that the record attaches to the stated complications-prediction task. |
| 42 | `inferred` | The category combines equity, contextual-factor, and SDOH statements; the bundle never states that intended-use classification. |
| 43 | `inferred` | Varied source formats, site extracts, and OMOP transformation are stated, but “site-native EHR extracts” is not. |
| 44 | `violated` | An EEG instance is retained only to record that extraction is pending, rather than being omitted. |

## Rater counts

- Rater A right: **28**
- Rater B right: **16**
- Neither right: **0**

## Policy synthesis: weak versus supported

`Supported` means the cited receipt set, including the local passage surrounding each snippet, directly answers the exact schema slot and covers every material clause without changing entity, role, scope, or tense. The snippet itself need not contain the complete answer; adjacent context within its cited passage counts, as in items 22 and 28. `Weak` applies when genuine, relevant text answers a neighboring question, establishes only a plan or resource’s existence, or supports only part of a composite value; evidence elsewhere in an uncited chunk cannot repair the receipt. When the cited passage is affirmatively read with the wrong number, entity, scope, or temporal status, the verdict is `misread`, not `weak`.

## Policy synthesis: rules 06 and 07

Rule-06 is violated when a free-text field’s operative payload is merely “none,” “not conducted,” “pending,” or “see elsewhere” instead of the requested information; the field or object should then be omitted. A declared Boolean may legitimately be false, and a link is legitimate when the field requests an access point or when consulting it is itself a substantive mitigation. Rule-07 is violated whenever accurate evidence is placed under a neighboring semantic question, even if the same content also appears correctly elsewhere—for example, payment timing as rationale or returned results as collection notification. Contextual detail is harmless when the load-bearing content still answers the chosen field, but a generic `description` does not cure semantic misplacement.

## Material points both presented rationales missed

- **Item 4:** the source says the Azure applications are “to be deployed,” while the value says they were deployed.
- **Item 18:** the identifier problem also reaches fragments for external repositories, software, the GitHub organization, and the AIM-AHEAD program—not only people.
- **Items 19–20:** `anomalies[0]` records the absence of an external audit under a field for errors/noise, and `labeling_strategies[0]` is another absence-only object.
- **Item 31:** `participant_privacy[0].privacy_techniques` includes federated learning that is merely planned.
- **Item 36:** `distribution_dates[0]` independently repeats the scheduled program date as access already provisioned.
- **Item 44:** imaging de-identification remains recorded as in process/not complete in `is_deidentified.deidentification_details`.

No files were written or edited. Independence disclosure: a broad terminology search accidentally returned one line from the prohibited prior-rulings file concerning item 42, although I did not open that file or any review YAML. I therefore had item 42 re-adjudicated in two clean parallel contexts that had not seen that output; both independently returned `inferred`, the ruling reported above.

Codex session ID: 01a05b8a-a4fb-7813-9210-595c26278d42
Resume in Codex: codex resume 01a05b8a-a4fb-7813-9210-595c26278d42
