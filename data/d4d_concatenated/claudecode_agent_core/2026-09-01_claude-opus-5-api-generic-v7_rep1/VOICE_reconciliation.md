# VOICE — Phase 4 Reconciliation Report

## Scope

Phase 3 raised twelve findings against the full record: one high, three medium, eight low. This report records what was changed in the full and core records, what was left as-is, and the reasoning for each. All statements below were checked against the original and reconciled records as supplied.

---

## Findings addressed by change

### 1. `id` / `doi` / `page` — version identity (high)

**Finding.** The record was version-pinned (`version: 3.1.0`, `issued: 2026-05-01T00:00:00Z`, a 3.1.0 citation naming DOI 10.13026/8xbn-nq66) but identified by the version-agnostic latest-version DOI 10.13026/37yb-1t42 in both `id` and `doi`.

**Change (full record).**
- `id`: `doi:10.13026/37yb-1t42` → `doi:10.13026/8xbn-nq66`
- `doi`: `10.13026/37yb-1t42` → `10.13026/8xbn-nq66`
- `page`: `https://physionet.org/content/b2ai-voice/` → `https://physionet.org/content/b2ai-voice/3.1.0/`
- `version_access.latest_version_doi`: `doi:10.13026/8xbn-nq66` → `doi:10.13026/37yb-1t42`

The record now refers to one release throughout. The version-agnostic DOI is retained where it belongs — as the latest-version pointer inside `version_access`, alongside the existing `version_details` prose that already listed it.

**Change (core record).** The same four edits were applied: `id`, `doi`, `page` and `version_access.latest_version_doi`.

**Note.** `issued` and `version` were not changed; they were already consistent with 3.1.0, and the repair resolved the conflict by moving the identifiers rather than the dates. This addresses finding 3 (`issued`), which was flagged only as a symptom of the same inconsistency.

---

### 2. `was_derived_from` — distribution endpoint used as provenance antecedent (medium)

**Finding.** The slot held `https://www.synapse.org/Synapse:syn72370534/`, the Synapse controlled-access route for the raw audio, which the bundle presents as an access mechanism rather than a resource the dataset derives from. It also duplicated `raw_data_sources[0].access_details`.

**Change (full record).** The `was_derived_from` slot was removed. The Synapse URL remains in `raw_data_sources[0].access_details` and in `distribution_formats[2].access_urls`, where it correctly describes access rather than derivation. No alternative value was substituted: the bundle does not name an external antecedent resource for this dataset.

**Change (core record).** `was_derived_from` was likewise removed.

---

### 3. `instances[0].data_substrate` — unsupported substrate term (medium)

**Finding.** `B2AI_SUBSTRATE:41` (Tab-separated values) was assigned to the participant-level instance. The bundle does not state that a participant instance is a TSV; the assignment encoded a file-format split across two instance objects rather than a property of the instance. The digest instructs omission over approximation.

**Change (full record).** `data_substrate` was removed from `instances[0]`. `data_topic: B2AI_TOPIC:25` was retained. `instances[1]` was left unchanged, including its `data_substrate: B2AI_SUBSTRATE:30` — a recording *is* materially a Parquet row in this release, so that term is supported.

**Change (core record).** The same removal was applied.

---

### 4. `sampling_strategies[0].is_random` — clearly supported omission (low)

**Finding.** The bundle states explicitly "Sampling Method: Non-Probability Sample" (chunk c008), which supports `is_random: false`; the slot was unpopulated.

**Change (full and core records).** `is_random: false` was added to `sampling_strategies[0]`, between `is_sample` and `is_representative`.

---

### 5. `creators[15]` — consortium entry with no principal investigator (low)

**Finding.** The final Creator carried only an `affiliations` entry naming the consortium plus a `notes` string, with no `principal_investigator`. Affiliation was standing in for a collective author, and the entry duplicated `created_by`.

**Change (full record).** The sixteenth Creator entry was removed. The consortium remains recorded in `created_by: Bridge2AI-Voice Consortium`. The contributor-count fact it carried was preserved by folding it into `source_caveats`, which now reads "…the PhysioNet author list for version 3.1.0 names over 120 contributors" alongside the existing consortium-size discrepancies.

**Change (core record).** The same entry was removed; the core record carries no `source_caveats`-equivalent change beyond the shared caveat text, which was updated identically.

**Related change (not a Phase 3 finding).** Across all fifteen remaining Creator objects in both records, `principal_investigator` changed from a nested object (`principal_investigator: {name: …}`) to a bare string (`principal_investigator: Yael Bensoussan`). The digest declares `principal_investigator` on Creator with range `Person`; the reconciled form is a scalar. This was applied consistently in both records.

---

### 6. `existing_uses[0].examples` — inconsistent shaping (low)

**Finding.** `examples` was a bare prose string on ExistingUse, while the same-named slot on IntendedUse was a list in the same record.

**Change (full and core records).** `existing_uses[0].examples` was converted to a single-element list. The text is unchanged.

**Related normalizations applied at the same time,** for the same shape-consistency reason:
- `machine_annotation_tools[0].tools`: string → single-element list
- `distribution_dates[0].release_dates`: string → single-element list
- `external_resources[*].external_resources`: each string → single-element list (all six entries, both records)

---

### 7. `content_warnings[0]` — warning and caveat pulling in opposite directions (low)

**Finding.** The `warnings` text asserted that free-speech content is present and uncontrollable, while the `source_caveats` recorded that the preferred (PhysioNet) source says free-speech transcripts and derived features were removed from the release.

**Change (full and core records).** The warning text was rewritten to distinguish the collection protocol from the released artifact: it now states that the protocol includes free speech tasks and that participant language cannot be fully controlled, then adds that "In the released feature-only dataset this risk is reduced: transcripts of free speech audio were removed, and spectrogram-family features derived from free speech recordings were excluded." The caveat was extended with "and is the one reflected in the warning above," so the two now agree.

---

### 8. `notes` — AI-readiness rubric placement (low)

**Finding.** The full `notes` slot carried the criterion-level AI-readiness scoring. The schema directs `notes` to residual content only; the summary scores fit `description`, and the criterion failures overlap `known_limitations`.

**Change (full record).**
- The `notes` slot was removed.
- A closing sentence was added to `description` giving the seven category scores (FAIRness 100%, provenance 100%, characterization 80%, pre-model explainability 100%, ethics 100%, sustainability 50%, computability 75%).
- A sixth `known_limitations` entry was added, typed `methodological_limitation`, recording the four criteria the self-assessment marks as not met: data quality under characterization; domain-appropriate and associated under sustainability; contextualized under computability.

**Change (core record).** The same three edits: `notes` removed, `description` extended, sixth `known_limitations` entry added.

---

### 9. `related_datasets[0].target_dataset` — pediatric DOI mismatch (low)

**Finding.** The target was `doi:10.13026/mf9s-5r03`, the pediatric latest-version DOI, while the accompanying description named version 1.1.0, whose own DOI is 10.13026/h995-bt35.

**Change (full and core records).** `target_dataset` changed to `doi:10.13026/h995-bt35`. The description was extended with a closing sentence noting that 10.13026/mf9s-5r03 resolves to the latest version, so neither identifier is lost.

**Related change.** `related_datasets[1].description` was lightly amended to name the version explicitly ("The first release of the feature-only dataset, version 1.0, published on the Health Data Nexus…"), for parity with the pediatric entry.

---

### 10. `distribution_formats[*].download_url` — undeclared omission (low)

**Finding.** No `download_url` on any DistributionFormat and none at top level. The omission was correct but a reader could not distinguish it from oversight.

**Change (full and core records).** A `notes` field was added to each of the three DistributionFormat objects stating that no direct download URL is published and why — credentialing and a signed data use agreement for the two PhysioNet entries; DACO review and an institutionally signed DTUA for the Synapse entry. No `download_url` was invented.

---

### 11. `collection_timeframes[0]` — uncaveated tension (low)

**Finding.** The 12-month figure sits in tension with the IRB protocol's four-year phased study (pilot begun November 2023, ongoing November 2024) and the June–July 2023 feasibility study, with no caveat recording it.

**Change (full and core records).** A `source_caveats` field was added to `collection_timeframes[0]` naming the three sources, stating why the 12-month figure was recorded (the project documentation is the source describing the released dataset's window), and stating explicitly that the sources do not settle whether the 12 months are a subset of the wider study period.

---

### 12. `external_resources[4]` — thin FHIR entry (low)

**Finding.** The FHIR entry carried a bare description with no URL, licence or archival flag, unlike every sibling. The bundle gives no URL for it.

**Change (full and core records).** The entry text was expanded to say what it is and to state explicitly that the documentation lists the resource and links to its source code but does not give a repository URL in the captured text. No URL was supplied. This converts a bare stub into an entry whose thinness is self-explaining.

---

## Findings left as-is

None. Every one of the twelve findings resulted in a change to at least one record.

Two items within the findings were deliberately *not* changed and are recorded here for completeness:

- **`issued` and `version`** (finding 3) retain their original values. The identity conflict was repaired by moving the identifiers to the version-pinned DOI rather than by dropping the version pin, so these two slots were already correct under the resolution chosen.
- **`instances[1].data_substrate`** was retained at `B2AI_SUBSTRATE:30`. Finding 4 flagged only the participant-level term as unsupported; the recording-level Parquet term is directly attested.

---

## Changes not traceable to a Phase 3 finding

Recorded for transparency; all are shape or wording normalizations rather than factual edits.

- **`principal_investigator` scalar conversion** on fifteen Creator objects in both records, as noted under finding 5.
- **`source_caveats` referent sentence** in both records was rewritten to state the new identity resolution: it now names 10.13026/8xbn-nq66 as the record's identifier and 10.13026/37yb-1t42 as the latest-version DOI held in `version_access`.
- **YAML block-scalar reflow** throughout the core record. The original core record used flow-folded strings; the reconciled core record uses the same prose. No factual content differs.
- **Removal of `was_derived_from` from the core record's scalar block**, following the full record.

---

## Cross-record consistency

Every factual change made to the full record was applied identically to the core record. Both records now:

- identify the dataset as `doi:10.13026/8xbn-nq66`, version 3.1.0
- carry `doi: 10.13026/8xbn-nq66` and `page: https://physionet.org/content/b2ai-voice/3.1.0/`
- hold `doi:10.13026/37yb-1t42` only in `version_access.latest_version_doi`
- omit `was_derived_from`
- omit `notes`
- carry fifteen Creator entries with scalar `principal_investigator`
- carry six `known_limitations` entries
- carry `is_random: false` in `sampling_strategies[0]`
- carry the same `source_caveats` text

The core record's header retains the required `# Sources:` line pointing at the full record, and `# Phase 4 reconciliation: completed` is present, phase 4 having run.

---

## Outcome

Twelve findings, twelve addressed, none deferred. One high-severity identity inconsistency resolved by pinning the record to the version-specific DOI. Two medium-severity unsupported or misplaced values removed. One supported omission filled. Eight low-severity shape, placement and transparency issues repaired. No fabricated content was introduced; every added value is either a shape change to existing content, a caveat about sources already in the bundle, or a statement that a value is absent and why.