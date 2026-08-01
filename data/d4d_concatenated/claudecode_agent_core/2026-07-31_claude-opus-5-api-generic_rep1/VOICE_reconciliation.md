# Reconciliation Report — VOICE

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
**Phases:** 1 (full) → 2 (core) → 3 (audit) → 4 (reconciliation)

---

## 1. Referent decision

The declared bundle describes a versioned dataset series (adult releases 1.0, 1.1, 2.0.0, 2.0.1, 3.0.0, 3.1.0) plus a separate pediatric PhysioNet project (1.0.0, 1.1.0). `Dataset` admits one referent.

**Decision:** the referent is the **Bridge2AI-Voice adult dataset series**, currently at release 3.1.0, described as a whole. The pediatric dataset is a distinct PhysioNet project on a distinct cohort under a distinct REB, and is represented as a related dataset rather than folded into the referent. This choice is held consistently across both records.

The audit flagged (high) that `id` was pinned to `https://doi.org/10.13026/8xbn-nq66`, the version-specific DOI for 3.1.0, while `version_access` records `10.13026/37yb-1t42` as the latest-version DOI and the body narrates the full series. This is a genuine referent inconsistency. **Changed in both records:** `id` is now the series-level DOI `https://doi.org/10.13026/37yb-1t42`; the 3.1.0 version DOI is retained in `doi` and `version_access` where it belongs as a version-specific fact.

---

## 2. Changes made

### 2.1 Core record — `distributions` → `file_collections` (high)

The core record populated a slot named `distributions`. This slot is not in the declared `CoreDataset` inventory, and the full record carried the same content under `file_collections`. **Changed:** the core record now uses `file_collections`, matching the full record. The content is unaltered; only the slot name changed. Both records now validate.

### 2.2 Synthetic CURIE identifiers (medium, two slots)

`subsets` and `file_collections` in the full record used coined identifiers under a `b2ai_voice:` prefix that appears nowhere in the bundle (`b2ai_voice:cohort_voice_disorders`, `b2ai_voice:raw_audio_bids`, etc.). The cohort and folder *descriptions* are supported; the identifiers were scaffolding.

**Changed:** identifiers are now derived from strings attested in the bundle. File collections use the folder names the PhysioNet 3.1.0 data description gives verbatim (`features`, `metadata`, `phenotype`); the fourth entry, previously `raw_audio_bids`, is renamed to reflect that the BIDS-structured audio tree is described in the project documentation but is **not** part of the registered-access release. Subsets use the cohort names as the bundle writes them ("Voice Disorders", "Respiratory disorders", etc.) rather than invented tokens.

### 2.3 Instance counts — pediatric figure removed, discrepancy surfaced (medium)

Two errors. First, `23,533` was included in the stated adult per-feature range; that is the pediatric recording count and does not belong there. **Changed:** removed. The adult per-feature counts from the 3.1.0 release notes range 28,640–32,522.

Second, the ~61,937 figure (project documentation, v3.0) sat adjacent to the per-feature counts with no indication that the two cannot be counting the same objects. **Changed:** `instances` now states both figures and records explicitly that the bundle does not reconcile them — 61,937 is the documentation's "voice-derived recordings" for v3.0, while the release notes enumerate 28,640–32,522 rows per feature file. The record no longer implies these are consistent.

### 2.4 Version 1.0 recording count qualified (medium)

"Version 1.0 contained 306 participants with 12,523 recordings" was presented as settled. The figure comes from the abstract of the **v1.1** PhysioNet page, which describes the initial release. **Changed:** the claim is retained but attributed to its source page, so a reader can see it is a v1.1-page statement about v1.0 rather than a v1.0 primary record.

### 2.5 Distribution platform — disagreement preserved (medium)

The record asserted that v1.0 went through Health Data Nexus and "subsequent versions are distributed through PhysioNet." The healthsheet, written against v2.0.0, still names `healthdatanexus.ai` as the distribution platform. The bundle does not say Health Data Nexus was discontinued. **Changed:** `distribution_formats` now records both — PhysioNet as the platform for 1.1 onward per the PhysioNet pages, and the healthsheet's contemporaneous statement naming Health Data Nexus — without adjudicating between them.

### 2.6 `conforms_to` scope narrowed (low)

`conforms_to: Brain Imaging Data Structure v1.9.0` was applied dataset-wide. BIDS v1.9.0 compliance is stated in the project documentation for the raw audio and phenotype folder tree, which is the **controlled-access** collection. The registered-access release is Parquet, TSV, and JSON, and is nowhere described as BIDS-compliant. **Changed:** the top-level `conforms_to` is removed; the BIDS claim is relocated to the file collection it actually describes.

### 2.7 `relationships` contradiction resolved (low)

The `Relationships` entry reproduced the healthsheet's "they are unrelated" while `instances` in the same record stated there may be multiple sessions per participant and multiple rows per participant. **Changed:** the entry now records both — the healthsheet's answer that inter-instance relationships are not made explicit, *and* the participant↔session structure carried by `participant_id` / `session_id` that the data description documents. The tension is attributed rather than silently resolved.

### 2.8 Funding identifiers — fourth variant restored (low)

Three conflicting award identifiers were reported; a fourth from the healthsheet (`3TF-OT2ActfOD032720Projectf01S1`) was dropped without comment. **Changed:** all four renderings are now listed, with a note that they appear to be variant renderings of core project `OT2OD032720`. The record does not pick a canonical form.

### 2.9 `annotation_analyses` removed (low)

The single entry existed only to assert that no inter-annotator agreement analysis is reported and that agreement "could not be computed." The supported fact is the healthsheet's "How many labelers provide a label per instance? 1", which is already carried in `labeling_strategies`. The inferential step to "could not be computed" was the record's own reasoning. **Changed:** slot omitted; the single-labeler fact remains where it is evidenced.

### 2.10 Core `other_tasks` removed (low)

The entry restated content already in `tasks` and `purposes`, and treated cohort selection — which the bundle presents as an intended function of the phenotype folder — as an unanticipated secondary use. It also created a full/core asymmetry with no evidentiary basis. **Changed:** removed from core, bringing the two records into alignment.

### 2.11 Consent slot consolidation (low)

The full record spread overlapping consent facts across `collection_consents`, `informed_consent`, `collection_notifications`, and `consent_revocations`. **Changed:** the full record now follows the core record's structure, with the consent mechanism consolidated in `informed_consent` and the remaining slots carrying only what is distinct to them (notification timing; the withdrawal-window rule that data collected before completion is excluded but data after completion cannot be removed). No facts were dropped.

### 2.12 `language` qualified (low)

**Changed:** `language: en` is retained as the correct code for the current release, with the Spanish-protocol-under-development statement moved into `known_limitations` where the scope restriction belongs.

---

## 3. Left as-is, with reasons

**`license` as a single string (low).** The audit is right that this flattens a multi-instrument regime — PhysioNet's Registered Access License for features, a separate DUA/DTUA for raw audio, MIT and Apache-2.0 for the code repositories. But `license` has range *string* and admits one value, and the PhysioNet label is the license under which the described release is actually obtained. The full picture is carried in `license_and_use_terms`, which is the slot designed for it. Splitting or hedging the bare string would make it less accurate, not more.

**`publisher: https://physionet.org/` (low).** The audit notes PhysioNet is the host and that MIT LCP maintains it, and that the Consortium or NIH are defensible alternatives. The bundle does not name a publisher in the formal sense. PhysioNet is the entity that issued the DOI and made the resource available, which is what the slot definition asks for. The alternatives are inferences; this one is on the page.

**`is_tabular: false` in core (low).** The release genuinely mixes columnar Parquet and TSV tables with dense multidimensional tensors (201×T spectrograms, T×12 EMA traces). The audit is correct that a boolean forces a single answer. But the slot is boolean-ranged, the dense feature tensors are the substance of the release, and `false` is the better of the two available answers. The full record omits the slot; the core record retains it because the core schema's narrower inventory makes the format signal more load-bearing there. The asymmetry is deliberate and noted here.

**`variables` sample of six (low).** The audit is right that six entries do not inventory a dataset with dozens of phenotype files and hundreds of static features. **Partially addressed:** the six entries are retained but each now carries a note identifying it as one of the shared keys or representative tensor columns documented in the PhysioNet data description, rather than presenting as a complete inventory. A full enumeration is not recoverable from the bundle — the data dictionaries are described but not reproduced in it.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Slots populated | 61 | 34 |
| Validated | yes | yes |

Both records validate against their respective schemas. The referent is the adult Bridge2AI-Voice dataset series, identified by its latest-version DOI, held consistently across both. Twelve issues were changed, four were left as-is with reasons recorded above. The principal substantive corrections were the removal of a pediatric recording count from the adult figures, the surfacing of the unreconciled 61,937-vs-per-feature-count discrepancy, the removal of fabricated CURIE identifiers, and the narrowing of the BIDS conformance claim from the dataset as a whole to the controlled-access collection it actually describes.