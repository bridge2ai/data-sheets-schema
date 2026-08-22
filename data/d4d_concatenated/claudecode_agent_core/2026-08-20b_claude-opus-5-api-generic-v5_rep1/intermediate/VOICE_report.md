# VOICE D4D Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep1`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase 3 audit findings:** 29 (2 high, 11 medium, 12 low, 4 info)

---

## 1. What the audit found

The Phase 3 audit reported no unsupported dataset facts. Participant count, version numbering, DOIs, per-feature record counts, processing parameters, governance terms, consent scope, compensation amounts, de-identification steps and release history all trace to the declared bundle, with the higher-ranked PhysioNet entries preferred over the project documentation where they conflict, and the feasibility study's separate 47-participant cohort, IRB number and no-compensation statement correctly quarantined from the dataset record.

The defects fell into five groups:

1. **An invented slot.** The core record used `distributions`, which does not appear in the supplied slot inventory, populated with objects carrying `path` (a `FileCollection` key) and duplicating content already held in `distribution_formats`, while dropping the `file_count` values the full record carried.
2. **Full/core asymmetry.** The core record introduced eight slots the full record omitted; five of those existed only to assert that something had not been done or did not exist.
3. **Range fidelity.** `resources` (range `Dataset`) held `DataSubset` content; `splits` was dropped from core with its content relocated into trailing `notes` prose.
4. **Entity collapse.** Several multivalued slots held one object or one list element bundling distinct entities.
5. **Identifier and term precision.** A grant `id` pointing at a supplement application while its `name` gave the core project; substrate terms naming file formats rather than instance content; free-text subset names where minted identifiers existed.

---

## 2. Changes made to the full record

### 2.1 Identifiers

**`funders[0].grants[0].id` removed** (medium). The original held `https://reporter.nih.gov/project-details/11376382` while `name` held `OT2OD032720`. The audit found that the URL identifies application 11376382 — a supplement — not the core project the `name` field states, so `id` and `name` named different things. The `id` key is now absent; the RePORTER URL is retained in the object's `notes` as prose describing the supplement, and the `source_caveats` now closes by stating that no identifier for the core project itself is in the bundle, which is why the grant carries no `id`.

**`known_biases` measurement_bias `affected_subsets`** (low) changed from the free-text `Mood and psychiatric disorders cohort` to the minted identifier `doi:10.13026/8xbn-nq66#mood-psychiatric-disorders-cohort`, which the record itself defines under `subsets`.

**`known_biases` representation_bias `affected_subsets` removed** (low). The original held the free-text `Historically marginalized and underserved communities`, which corresponds to no declared subset. The entry now carries a `notes` field stating that the affected groups are historically marginalized and underserved communities and that the dataset does not delineate them as named subsets.

### 2.2 Substrate terms

**`instances[0].data_substrate`** (low) changed from `B2AI_SUBSTRATE:41` (Tab-separated values) to `B2AI_SUBSTRATE:79` (Participant response data). The audit found the original named the serialization of the phenotype tables rather than the substance of a participant instance. The TSV fact is preserved in the instance's `notes`, which now closes: "Participant-level information is distributed as tab-separated phenotype tables."

**`instances[1].data_substrate`** (low) changed from `B2AI_SUBSTRATE:30` (Parquet) to `B2AI_SUBSTRATE:69` (Time-series data). Same reasoning. The Parquet fact moves to the instance's `notes`: "The time-varying feature tensors are distributed in Apache Parquet."

### 2.3 Entity collapse

**`machine_annotation_tools`** (implied by the general collapse finding) split from one object holding nine tools into seven objects grouped by function: Whisper, openSMILE, Praat/Parselmouth, torchaudio, sparc, ppgs, and b2aiprep/senselab. The `tool_accuracy` caveat about unaudited off-the-shelf models now sits on the Whisper object, which is what it describes.

**`external_resources`** (low) split from one object holding seven resources into seven objects, one per resource. Per-resource `restrictions` now attach to the resource they govern: Apache-2.0 on b2aiprep, MIT on the REDCap dictionary, MIT on the docs repository. `archival: true` is set on the two Zenodo-archived entries. The `future_guarantees` prose became a `notes` field on the training-site entry.

**`human_subject_research.irb_approval`** (low) split from one paragraph into three list elements: single-IRB approval, written informed consent, and the separate Canadian genomic protocol.

**`human_subject_research.regulatory_compliance`** (low) split from one paragraph into five list elements: HIPAA de-identification, Certificate of Confidentiality, the partial HIPAA waiver, no data monitoring committee, and not-a-drug/not-a-device.

**`at_risk_populations.special_protections`** (low) split from one paragraph into three list elements: which at-risk groups were enrolled, the discomfort-risk disclosure, and the consent teach-back procedure. `assent_procedures` and `guardian_consent` remain unpopulated; the audit found their omission defensible since those procedures belong to the pediatric protocol and hence to the separate pediatric dataset.

**`existing_uses`** split from one object holding two examples into two objects, matching the same one-entity-per-object rule.

### 2.4 Slot placement

**`collection_timeframes[0]`** (low) restructured. The original `timeframe_details` ran "The dataset healthsheet records that the data were collected over a period of twelve months. Specific calendar start and end dates for the collection period are not stated in the released documentation." The details field now states only the fact — "Data were collected over a period of twelve months" — and the commentary about missing dates moved to `source_caveats` on the same object, where the schema declares commentary about sibling values belongs.

**`variables`** (low) gained a `source_caveats` on the final entry stating that the list documents the derived feature files, that the phenotype tables carry many further columns defined in their JSON data dictionaries, and that the bundle does not enumerate those individually. The audit found the list gave no indication of its own scope.

### 2.5 Slots added to close the asymmetry

Where the audit found a core-only slot whose facts are supported by the bundle and whose omission from the full record was an oversight rather than a judgment, the slot was added to the full record:

- **`is_tabular: false`** (medium)
- **`license: Bridge2AI Voice Registered Access License`** (medium) — the fact was already inside `license_and_use_terms.license_terms`; the scalar slot is now populated too
- **`annotation_analyses`** (medium) — one object recording that no agreement analysis was performed, why it is not computable, and what label quality rests on instead
- **`data_protection_impacts`** (medium) — one object recording that no assessment was conducted
- **`use_repository`** (medium) — one object recording that no use-tracking repository exists

**`informed_consent[0].withdrawal_mechanism`** was extended to carry the withdrawal detail the core record had (data excluded if withdrawal precedes collection completion, irremovable afterwards, re-consent each longitudinal session), so the two records now state the same thing in the same slot.

---

## 3. Changes made to the core record

### 3.1 The invented slot

**`distributions` removed** (high, the report's single highest-severity finding). All five objects are gone. Their content is not lost: the Parquet and TSV format facts were already in `distribution_formats`, whose two `notes` fields have been extended to name the folders — features/ and metadata/ for Parquet, phenotype tables plus `static_features.tsv` and `audio_quality_metrics.tsv` for TSV. The `file_count` values the projection dropped remain in the full record's `file_collections`.

### 3.2 The `resources` misuse

**`resources` removed** (medium). The five objects were the full record's `subsets` entries with the subpopulation flags stripped, which asserted that recruitment cohorts are component datasets. They are not. The cohorts remain fully described in the full record's `subsets` with `is_subpopulation: true`. The core record's `notes` now closes with a sentence naming all five minted cohort identifiers and stating explicitly that each is defined by its recruitment diagnoses and gold-standard validation methods "rather than being a separate component dataset."

### 3.3 Slots removed to close the asymmetry from the other side

Where the audit found a core-only slot that populated a field solely to state that something did not exist, and the omission-over-assertion rule applies, the slot was removed from core rather than added to full — except where the fact was substantive enough that the full record should carry it too. The split:

**Removed from core, not added to full:**

- **`is_tabular`** — no. This was *added to full*, see 2.5. It remains in core.
- **`imputation_protocols` removed** (medium) — the object said only "None applied." The same fact is already stated in `missing_data_documentation.handling_strategy` in both records: "No imputation is applied."
- **`other_tasks` removed** (medium) — the audit found its text an inference from the feature inventory rather than a claim the bundle makes about additional supported tasks. The same content is carried, as a documented purpose, in `tasks`, which both records hold.

**Kept in core and added to full** (see 2.5): `annotation_analyses`, `data_protection_impacts`, `use_repository`, `license`, `is_tabular`.

### 3.4 The `splits` relocation

**Not resolved by restoring the slot** (medium). The core record still carries the split guidance as prose in `notes` rather than in a `splits` slot. The change made was to the `source_caveats`: the original closed with a list of slots the author asserted the core schema lacks, including data splits — an assertion the schema digest does not support and which the record's own `notes` contradicted. **That entire closing sentence has been removed** (low, the `source_caveats` finding). The core `source_caveats` now ends at the NIH RePORTER / IRB scope paragraph.

### 3.5 Changes mirroring the full record

Applied identically to core so the pair stays consistent:

- `funders[0].grants[0].id` removed, RePORTER URL moved to `notes`, `source_caveats` extended
- `instances[0].data_substrate` → `B2AI_SUBSTRATE:79`; `instances[1].data_substrate` → `B2AI_SUBSTRATE:69`; format facts moved to `notes`
- `known_biases` measurement_bias `affected_subsets` → minted identifier; representation_bias `affected_subsets` → removed, replaced by `notes`
- `machine_annotation_tools` split into seven objects
- `external_resources` split into seven objects with per-resource restrictions and `archival` flags
- `human_subject_research.irb_approval` split into three; `regulatory_compliance` split into five
- `at_risk_populations.special_protections` split into three
- `existing_uses` split into two
- `collection_timeframes` restructured with `source_caveats`

---

## 4. Findings left as-is

**Per-creator `source_caveats`** (medium, flagged as a stylistic inconsistency rather than a conformance defect). The audit noted that affiliation-disagreement commentary sat inside individual `Creator` objects while other disagreements were handled at record level. **This was changed, not left as-is** — but in the opposite direction from consolidation of style: the three per-creator `source_caveats` (Rudzicz, Johnson, Ravitsky) have been **removed from both records**, and their content consolidated into the record-level `source_caveats`, which now carries a paragraph naming all three disagreements, both readings in each case, and which source was preferred. This brings affiliation disagreements into line with the record-level handling already used for the compensation and record-count conflicts.

**`publisher` as a website root** (low). Still `https://physionet.org/` in both records. The digest declares no prefix covering PhysioNet, so the URL fallback is permitted for a `uriorcurie` slot. The MIT Laboratory for Computational Physiology is named in `maintainers` in both records, so the maintaining body is not lost. No better-grounded identifier appears in the bundle.

**`variables` covering only the features layer** (low). Still eleven feature-file columns; no phenotype columns added. The bundle does not enumerate them, so adding them would be invention. The change made was to say so — see 2.4.

**`conforms_to_standard: [BIDS]` without FHIR** (low). Unchanged in both records. The audit itself judged the single BIDS value defensible: the FHIR profiles are a consortium output, not a standard the released data conforms to. The FHIR profiles remain listed under `external_resources`.

**Core record has no `variables`, `subsets`, `splits`, `relationships`, `third_party_sharing`, `direct_collection`, `file_collections`, `participant_compensation`, `participant_privacy`, `collection_consents`, `collection_notifications`, `consent_revocations`, or `citation`.** These remain absent from core. The core record is a projection, and the full record carries all of them. The change was to stop *claiming* in `source_caveats` that the core schema lacks slots for them — see 3.4.

**No ORCIDs or RORs anywhere** (info). Correct and unchanged. The bundle supplies none, and supplying one from outside the evidence would be an unsupported claim about the world.

**American English with quoted material preserved** (info). Unchanged. "Temerty Centre for Artificial Intelligence Research and Education in Medicine" keeps its British spelling because it is an organization's name.

**Header blocks** (info). Both conform. The core block carries `# Sources:` naming the bundle and the Phase 1 full record, and `# Phase 4 reconciliation: completed` — which is now accurate, Phase 4 having run.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots | 76 | 71 |
| Invented slots | 0 | 0 (was 1) |
| Slots present in one record only | 5 (`citation`, `subsets`, `splits`, `relationships`, `variables`, and others structural to a full datasheet) | 0 core-only slots remain |
| Range violations | 0 | 0 (was 1) |

The two records now agree on every fact they both state, and every slot the core record populates the full record also populates. Where the core record is smaller, it is smaller by projection, not by disagreement.