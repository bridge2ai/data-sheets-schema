# Reconciliation Report — VOICE

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt`
**Records:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Referent decision

`Dataset` admits one referent. The bundle describes several distinguishable artifacts:

| Candidate | Evidence in bundle |
|---|---|
| Bridge2AI-Voice adult feature-only release, PhysioNet v3.1.0 | Full PhysioNet landing page, DOI `10.13026/8xbn-nq66`, 833 participants, credentialed access, complete feature and phenotype inventory |
| Bridge2AI-Voice adult v3.0.0 | Full PhysioNet page plus the RO-Crate (`ark:59853/rocrate-b2ai-voice-3.0.0`), DOI `10.13026/k81f-qr68` |
| Bridge2AI-Voice **Pediatric** Dataset v1.1.0 | Separate PhysioNet project, DOI `10.13026/h995-bt35`, 300 participants aged 2–18, distinct REB (SickKids), distinct Synapse endpoint |
| Raw-audio corpus | Controlled access via Synapse `syn72370534`, not published on PhysioNet |
| Health Data Nexus v1.0 | DOI `10.57764/qb6h-em84`, superseded |
| The Bridge2AI-Voice *project* / grant `OT2OD032720` | NIH RePORTER, IRB protocol, white paper |

**Chosen referent: the Bridge2AI-Voice adult, feature-only, de-identified dataset as published on PhysioNet, current version 3.1.0.**

Rationale:

- It is the artifact the bundle's curation notes explicitly designate as current and authoritative ("prefer this over `physionet_3_0_0` where the two disagree").
- It is the only candidate for which the bundle supplies a complete, citable, versioned record: DOI, license, DUA, access policy, file inventory, data dictionaries, release notes.
- The pediatric release is a **distinct project**, not a version of this one; the bundle's own curation note states this directly. It is therefore treated as a related dataset, not as a part or version.
- The RO-Crate describes v3.0.0. Its `rai:*` fields, ethics statements, provenance graph, and per-file checksums are treated as evidence about this dataset lineage and are used where the v3.1.0 page does not supersede them. Where v3.1.0 restates a fact differently (e.g. per-feature record counts), v3.1.0 governs.

Both records hold this referent consistently. `id` is the v3.1.0 DOI URL.

---

## 2. Audit outcome summary

The audit returned 22 findings: 3 high, 4 medium, 15 low. Two high findings were structural and required changes to the core record. Several medium findings resulted in additions to both records. The majority of low findings were examined and **left as-is**, with reasons given in §5.

---

## 3. Changes made

### 3.1 Core record — `distributions` slot removed (HIGH)

**Finding:** the core record carried a `distributions` block with sub-keys `media_type`, `bytes`, `sha256`, `download_url`. This slot is not declared in `CoreDataset`.

**Verification:** checked against `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`. `distributions` is not a slot on `CoreDataset`; the block would have failed validation.

**Change:** the block was removed. Its content was relocated without loss:

- Format, encoding and access-mechanism statements → `distribution_formats` (Parquet columnar binaries; TSV plain-text tables with paired JSON data dictionaries; registered/credentialed PhysioNet access; controlled raw-audio access via Synapse).
- Byte sizes and checksums → these are file-level facts. `CoreDataset` does not expose `file_collections`, so the aggregate figures were preserved instead as `total_size_bytes` and the RO-Crate's stated package size was carried in `description`. Per-file SHA-256 digests were dropped from core; they remain complete in the full record's `file_collections`.
- The Synapse raw-audio endpoint → `download_url` (see §3.4).

### 3.2 Core record — cohorts moved from `resources` to `subsets` (HIGH)

**Finding:** the six disease cohorts were slotted as `resources` (range `Dataset`) in core but `subsets` (range `DataSubset`) in full. The two records disagreed on identical content.

**Adjudication:** `DataSubset` is documented as "a logical partition such as training, validation, or test splits, **or demographic subgroups**." The cohorts (voice disorders, respiratory, neurological/neurodegenerative, mood/psychiatric, controls, pediatric) are partitions of the study population defined by inclusion criteria. They are not component datasets with independent identity, distribution, or licensing. `subsets` is correct; `resources` was wrong.

**Change:** in the core record the six entries were moved to `subsets` and re-typed as `DataSubset` objects (`id` required, present). The full record already used `subsets` and was not changed.

### 3.3 Pediatric cohort entry corrected (HIGH, consequence of 3.2)

**Finding:** the pediatric entry asserted itself as a sub-resource of this Dataset while its own description stated the pediatric data are not part of this release — a self-contradiction, and one that conflicts with the referent decision in §1.

**Change:** the pediatric entry was removed from `subsets` in **both** records. It is not a subset of the adult release; it is a separate dataset. It is now represented in `related_datasets` (see §3.5). The five remaining cohorts (voice, respiratory, neurological, mood/psychiatric, control) are genuine partitions of this dataset's 833 participants and were retained.

The protocol-level fact that the *project* defines five disease categories including pediatrics is retained in `purposes` and `description`, where it belongs as a statement about project scope rather than about this dataset's composition.

### 3.4 `download_url` — asymmetry resolved

**Finding:** core populated a download URL (via the now-removed `distributions` block); full left `download_url` unset.

**Adjudication:** the PhysioNet feature-only release has no direct-download URL — access requires credentialing and DUA signature, and the files are served behind that gate. The Synapse endpoint `https://www.synapse.org/Synapse:syn72370534/` is the raw-audio corpus, which is *not* the referent chosen in §1.

**Change:** `download_url` is now **unset in both records**. The Synapse endpoint is instead recorded in `external_resources` (full) and in `distribution_formats` prose (both), described accurately as the controlled-access route to raw audio, which is a different artifact from the one this record describes. This corrects the core record rather than propagating its value to full.

### 3.5 `related_datasets` added to both records (MEDIUM)

**Finding:** two typed relationships were present in the bundle but expressed only as prose in `external_resources`.

`DatasetRelationship` requires `relationship_type` and `target_dataset`; the bundle supplies both for each.

**Change:** added to both records:

| `relationship_type` | `target_dataset` | Basis |
|---|---|---|
| related dataset (companion cohort, separate project) | Bridge2AI-Voice Pediatric Dataset, `https://doi.org/10.13026/h995-bt35` | Separate PhysioNet project, 300 participants aged 2–18, SickKids REB, distinct Synapse endpoint `syn73617068`; bundle curation note states the two are distinct cohorts, not versions |
| is version of / supersedes | Bridge2AI-Voice v1.0 on Health Data Nexus, `https://doi.org/10.57764/qb6h-em84` | Cited in PhysioNet release notes as the first release of this same dataset lineage |

A third relationship — the RO-Crate's v3.0.0 (`10.13026/k81f-qr68`) — was **not** added as a `related_datasets` entry. It is a prior version of the same PhysioNet project and is already fully represented in `version_access`, which is the slot documented for version history.

### 3.6 `total_size_bytes` and `total_file_count` added to full record (MEDIUM)

**Finding:** the RO-Crate supplies `contentSize: "12.9 GB"` for the v3.0.0 package plus per-file byte sizes for nine Parquet feature files and two phenotype TSVs, all already transcribed into `file_collections`. Aggregation into these slots is their documented purpose.

**Change:** `total_size_bytes` populated with the sum of the byte figures the bundle actually states (13,788,088,083 bytes across the eleven files with recorded sizes), with a note in `description` that the RO-Crate's headline figure of 12.9 GB is the v3.0.0 package total and that the two figures are not expected to match exactly because the bundle does not give sizes for every file in the phenotype directory.

`total_file_count` was **not** populated. The bundle gives sizes and checksums for eleven files and lists the phenotype directory tree, but never states a total file count for the release, and the directory listing is not exhaustive across versions. Deriving a count would require assuming the listing is complete. Under the omission-over-inference rule, the slot is left unset.

### 3.7 Phenotype `total_bytes` corrected in full record (MEDIUM)

**Finding:** the phenotype `file_collections` entry reported `total_bytes: 934367` — the sum of only two files (`confounders.tsv` 721,577 + `demographics.tsv` 212,790) — while the directory demonstrably contains dozens of further TSV/JSON pairs whose sizes the bundle does not give. With no `file_count` set, the figure read as a directory total.

**Change:** `total_bytes` was removed from that entry. The two known per-file sizes are retained in the entry's description, explicitly labelled as the only two files for which the RO-Crate records a size. This avoids presenting a partial sum as a total.

### 3.8 `collection_timeframes` — conflict now flagged (MEDIUM)

**Finding:** the records reproduced the healthsheet's "data was collected over a period of 12 months" alongside a release history in which participant counts rise 306 → 442 → 833 across releases dated Nov 2024 through May 2026. A 12-month window cannot accommodate enrollment continuing across three subsequent releases. Other numeric conflicts in the record (enrollment targets, recording counts) *were* explicitly flagged; this one was not.

**Change:** an entry was added to `collection_timeframes` in both records recording that the bundle contains two irreconcilable statements about collection duration — the healthsheet's 12-month figure (written when the dataset stood at ~833 participants under the v2.0.0-era documentation) and the release chronology implying ongoing multi-year enrollment — and that the bundle does not resolve them. Both statements are retained; neither is selected over the other.

---

## 4. Changes considered and rejected

### 4.1 `license` left as free text

The audit noted that `license` carries the string `Bridge2AI Voice Registered Access License` while the slot's examples are SPDX identifiers, and that a resolvable URL exists in the bundle.

**Left as-is.** The license is a bespoke instrument with no SPDX identifier; substituting a URL would replace the license's *name* with its *location*. The slot asks for the license under which the resource is made available, and that license's name is what the bundle states. The URL remains available in `license_and_use_terms`, which is where a pointer belongs. No change.

### 4.2 `publisher` left as bare URI

`https://physionet.org/` is admissible under range `uriorcurie`. The RO-Crate's `"PhysioNet"` string is not a URI and would not satisfy the range better. No registry identifier for PhysioNet-as-organization appears in the bundle. Changing this would substitute one imperfect value for another. No change.

### 4.3 `id` left as version-specific DOI

The audit observed that a concept-level DOI (`10.13026/37yb-1t42`, "latest version") exists alongside the version DOI used as `id`.

**Left as-is**, with the choice now recorded here. The record describes v3.1.0 specifically — its participant counts, its feature inventory, its release notes. A concept DOI would identify a moving target that will not match this record's contents after the next release. The latest-version DOI is retained in `version_access`, so both are recoverable.

### 4.4 `created_by` left as the consortium

For a 118-author dataset with two co-principal investigators, the collective is the more accurate answer to "the person or organization primarily responsible for creating the resource." Yael Bensoussan is recorded as principal investigator in `creators`. Choice recorded here per the audit's request. No change.

### 4.5 Negation-as-content entries retained (five slots)

The audit flagged that `confidential_elements`, `cleaning_strategies`, `imputation_protocols`, `use_repository` and `data_protection_impacts` each open with an entry stating that the thing the slot asks about does not exist.

**Retained in all five cases.** These negations are direct, attributed answers from the project's own healthsheet — they are evidence, not padding, and recording "the healthsheet answers No to X" is a factual claim about the documentation that a reader of this datasheet needs. Dropping them would make the records appear silent on questions the source material answers explicitly. In each of the five slots the negation is followed by substantive entries, so no slot is negation-only.

One qualification was tightened: in `cleaning_strategies`, the parenthetical gloss explaining that the "No" refers to not altering participant responses was rewritten to attribute the scope-narrowing to the surrounding bundle text rather than presenting it as the record's own reading.

### 4.6 `imputation_protocols` / `missing_data_documentation` overlap retained

The overlap is real but each slot answers a different question — what was done about missing values (nothing) versus how missingness is structured and documented (row-presence rules, optional questions, feature-generation failures). Collapsing them would lose the second. No change.

### 4.7 `use_repository` weak-fit entries retained

`b2aivoicescholars.org` and the project dashboards are not citation indices. They are, however, the only resources the bundle offers that track engagement with the dataset, and the slot's negation entry makes clear that no true use-tracking registry exists. Retained with the fit made explicit in each entry's description. No change.

### 4.8 `purposes[7]` and `tasks[6]` meta-entries retained

The audit correctly observed that the enrollment-target disagreement note is not a Purpose and the no-splits note is not a Task.

**Retained.** Both facts are now also stated here in the reconciliation report, but a reader of the YAML who never sees this report still needs them. The enrollment note sits in `purposes` because every enrollment figure in the bundle appears in a statement of project aims; the splits note sits in `tasks` because a user scanning `tasks` to plan an experiment needs to know no partition is supplied. Both are additionally represented in `known_limitations` and `splits` respectively, so removal from these slots would not lose the facts — but retention costs nothing and improves the chance the caveat is seen at point of use.

### 4.9 `instances[2]` recording-count discrepancy — no change

The audit confirmed this conflict is handled correctly: the ~61,937 figure from project documentation and the per-feature counts from the PhysioNet v3.1.0 page (29,278 spectrograms, 32,522 pitch tracks, etc.) are both stated and the mismatch is marked. This is the standard the `collection_timeframes` fix in §3.8 was brought up to. No change.

---

## 5. Core-record omissions adjudicated against the core schema

The audit could not resolve several core omissions without the `CoreDataset` slot inventory. That inventory was checked. Results:

| Slot | Present on `CoreDataset`? | Disposition |
|---|---|---|
| `consent_revocations` | No | Folding into `informed_consent` was correct. Retained. |
| `collection_notifications` | No | Folding into `informed_consent` correct. Retained. |
| `collection_consents` | No | Folding correct. Retained. |
| `participant_privacy` | No | Content folded into `data_protection_impacts`; correct. |
| `participant_compensation` | No | Slot unavailable. **The compensation facts ($40 under 90 min, $80 over, max three sessions / $120) were added to `informed_consent` in core**, since compensation is disclosed during consent and the bundle presents it that way. Previously these facts were dropped entirely from core; that was the one genuine content loss the audit identified, and it is now repaired. |
| `direct_collection` | No | Content ("collected directly from individuals," no third-party intermediary) folded into `acquisition_methods` in core. |
| `relationships` | No | Content (instances are unrelated; multiple sessions per participant possible) folded into `instances` in core. |
| `splits` | No | Content already present via `tasks` and `known_limitations`. No further action. |
| `variables` | No | The 23 variable definitions are not representable in core. They remain complete in the full record. This is a schema-level difference, not an omission. |
| `file_collections` | No | Superseded by §3.1. Format facts in `distribution_formats`; aggregate size in `total_size_bytes`; per-file detail full-record-only. |

---

## 6. Consistency check between records

After the changes above:

- Both records name the same referent, the same `id`, the same `version` (3.1.0), the same `license`, the same `publisher`, the same participant count (833), the same five cohorts as `subsets`, and the same two `related_datasets`.
- `download_url` is unset in both.
- Every fact present in core is present in full. Facts present only in full are those for which `CoreDataset` declares no slot (per §5) — no fact is in full solely by oversight.
- Every numeric conflict in the bundle (enrollment target, recording count, collection duration) is flagged in both records rather than resolved.

---

## 7. Validation

Both records were validated after reconciliation:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep1/VOICE_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep1/VOICE_d4d_core.yaml
```

Both pass. The pre-reconciliation core record would not have — the `distributions` block was an undeclared slot.

---

## 8. Provenance

No previously generated D4D record was read, opened, or consulted at any phase. All factual content derives from `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` and the two schema files. RO-Crate `rai:*` fields were used as evidence about the v3.0.0 lineage and are attributed as such where they inform slots the PhysioNet v3.1.0 page does not cover.

Live provenance record written:

```
poetry run d4d provenance record --project VOICE \
  --method claudecode_agent_crate \
  --label 2026-07-31_claude-opus-5-api-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt
```