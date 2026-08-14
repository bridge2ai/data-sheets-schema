# Phase 4 Reconciliation Report — VOICE

**Project:** VOICE (Bridge2AI-Voice)
**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep2`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`

**Records reconciled:**

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep2/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep2/VOICE_d4d_core.yaml`

---

## 1. Referent decision (held constant across both records)

`Dataset` admits one referent. The declared bundle describes several candidate
referents: the Bridge2AI-Voice data-generation *project*; the adult
feature-derived release on PhysioNet; the pediatric release on PhysioNet; and
the underlying audio + questionnaire corpus organised as BIDS.

**Chosen referent:** the adult Bridge2AI-Voice PhysioNet release, latest
described version **3.1.0** (published 2026-05-01). This is the referent with
the richest and most internally consistent documentation in the bundle
(abstract, methods, data description, release notes, access policy, DOI,
authorship).

The pediatric dataset is represented as a **related dataset**, not as this
record's subject. The project as a whole is represented through `purposes`,
`addressing_gaps`, `funders` and `creators`, not by shifting the referent.

This decision was already the basis of Phase 1 and Phase 2 and was **not
changed** in Phase 4. It is now stated explicitly in both records'
`source_caveats`.

---

## 2. Audit findings and dispositions

### 2.1 HIGH — `distributions` slot in the core record (**fixed**)

**Finding.** The core record carried three objects under a slot named
`distributions`, with keys `path`, `format`, `media_type`,
`conforms_to_standard`. Neither the slot nor a `Distribution` range class with
that shape appears in the schema digest for `Dataset`/`CoreDataset`. The full
record had used `file_collections` (range `FileCollection`, which does declare
`path`, `collection_type`, `file_count`, `total_bytes`) for the same content.

**Disposition — changed.** The three `distributions` objects were removed from
the core record. Their content was redistributed:

| Content | New home in core |
|---|---|
| `features/` tree — Parquet tensors + TSV static features | `file_collections[]` with `collection_type: processed_data`, `path: features/` |
| `phenotype/` tree — TSV + JSON dictionaries | `file_collections[]` with `collection_type: processed_data`, `path: phenotype/` |
| `metadata/` tree — per-recording Parquet + dictionary | `file_collections[]` with `collection_type: metadata`, `path: metadata/` |
| Access route (PhysioNet, credentialed, DUA) | already present in `distribution_formats[]` and `data_governance`; not duplicated |

**Rationale.** A slot the schema does not declare cannot validate, and the
content was already representable in a declared slot that the full record had
used correctly. Fixing this also removed the core/full asymmetry at this point.

### 2.2 HIGH — scalar in a multivalued slot (**fixed, by consequence**)

**Finding.** `distributions[].conforms_to_standard` was a bare scalar `BIDS`
where the corresponding slot on `Dataset`/`FileCollection` is
`DataStandardEnum[]`.

**Disposition — changed.** Resolved by 2.1. Where `conforms_to_standard` now
appears inside a `FileCollection`, it is a list. The top-level
`conforms_to_standard` in both records was already a list and is unchanged.

### 2.3 MEDIUM — invented enumeration in `source_caveats` (**fixed**)

**Finding.** A `source_caveats` string reasoned about "the `format` and
`media_type` enumerations", implying controlled vocabularies. The schema digest
places no enum constraint on `DistributionFormat.format` or
`DistributionFormat.media_type`.

**Disposition — changed.** The caveat was rewritten to describe only what the
bundle states — that the release ships Parquet, TSV and JSON files — without
asserting a schema constraint that does not exist. `source_caveats` is a trust
annotation about sibling slots; it must not manufacture schema facts.

### 2.4 MEDIUM — `id` set to a version DOI (**left as-is, caveat strengthened**)

**Finding.** Full `id` is `https://doi.org/10.13026/8xbn-nq66` (the v3.1.0 DOI)
while `version_access.latest_version_doi` is the concept DOI
`10.13026/37yb-1t42`.

**Disposition — unchanged, annotation improved.** This is consistent with the
referent decision in §1: the record describes a specific release, and `version`
is set to `3.1.0`. The concept DOI is retained in `version_access` because that
is the slot that exists to hold cross-version resolution. The `source_caveats`
on `id` now states the referent decision explicitly rather than merely noting
the two DOIs.

### 2.5 MEDIUM — `instances[1].counts = 32522` (**left as-is**)

**Finding.** The value is the largest per-feature file count
(`torchaudio_pitch.parquet`, n=32522); the bundle gives no total recording count
for v3.1.0. Per-feature counts range 23,533–32,522 because different extractors
succeed on different subsets and because sensitive/free-speech records are
withheld from some feature types.

**Disposition — unchanged.** The alternatives are worse: omitting the count
discards a real signal about scale, and the bundle supports no better figure.
The existing `source_caveats` already states that this is the maximum
per-feature count and not a count of distinct recordings, and that per-feature
counts vary. Retained, with the caveat kept verbatim in both records.

### 2.6 MEDIUM — `conforms_to: BIDS v1.9.0` for an audio-free release (**narrowed**)

**Finding.** The bundle attributes BIDS v1.9.0 to the `b2ai-voice-audio` tree
(per-participant `sub-*/ses-*/audio/` directories). The PhysioNet 3.1.0 release
contains no audio and uses a `features/`, `phenotype/`, `metadata/` layout.

**Disposition — changed (narrowed, not removed).** `conforms_to` now states that
the underlying audio-and-questionnaire dataset was converted to BIDS v1.9.0, and
that the derived release re-organises that content into feature, phenotype and
metadata trees while retaining the BIDS-derived `sub-`/`ses-`/`task-` entity
naming in its identifiers. `conforms_to_standard: [BIDS]` is retained, since the
bundle does register BIDS as the standard in play. A `source_caveats` records
the partial applicability.

### 2.7 LOW — core-only slots: `raw_sources`, `annotation_analyses`, `errata`, `is_tabular` (**fixed by back-propagation, except `is_tabular`**)

**Finding.** Four slots were populated in core but absent from full, though all
four are valid `Dataset` slots and the supporting evidence was available in
Phase 1. The core record was therefore not a projection of the full one.

**Disposition — changed for three, changed by removal for one.**

- `raw_sources` — **added to full.** The bundle documents raw audio (retained,
  not publicly accessible; controlled access via Synapse) and REDCap /
  ReproSchema-UI questionnaire exports as the pre-processing inputs. Now present
  in both, with the same content.
- `annotation_analyses` — **added to full.** The bundle states one labeller per
  instance, no inter-annotator agreement, and off-the-shelf transcription models
  not audited for correctness. `inter_annotator_agreement_score` is left
  unpopulated because no score exists; `agreement_metric` likewise.
- `errata` — **removed from core.** On review this value recorded the *absence*
  of an erratum ("There is no erratum"). Recording a negative does not answer
  the field. The changelog information it pointed to is already carried by
  `updates` and `version_access`. Removed rather than back-propagated.
- `is_tabular` — **removed from core.** See 2.10.

### 2.8 LOW — full-only slots: `variables`, `file_collections`, `other_tasks` (**partially fixed**)

- `other_tasks: []` — **removed from full.** An empty list occupies the slot
  without asserting anything. Core already omitted it; the two now agree by
  omission.
- `file_collections` — now present in **both** as a consequence of 2.1.
- `variables` — **left full-only.** `variables` is a full-schema slot exercised
  at a level of granularity the core record is not intended to carry; core
  omitting it is a projection decision, not an inconsistency. See 2.13 for the
  separate coverage question.

### 2.9 LOW — `data_governance.committee_contact` (**fixed**)

**Finding.** Core populated `committee_contact` (range `Person`) with a
`mailto:` IRI and the name "Bridge2AI-Voice Data Access Compliance Office". The
bundle names an office and an address, never an individual.

**Disposition — changed.** `committee_contact` removed from core. The address
`DACO@b2ai-voice.org` is retained in `data_governance.access_review_process`,
where it belongs as part of the described route, and `committee_name` carries
the office name. Full's omission was correct and is unchanged. An office is not
a `Person`.

### 2.10 LOW — `is_tabular` (**fixed by removal**)

**Finding.** Core asserted `false`; full omitted the slot. The release is
genuinely mixed: TSV phenotype tables and JSON dictionaries alongside Parquet
tensor arrays of shape 201×T, 60×T, 40×T.

**Disposition — changed.** Removed from core. A single boolean cannot represent
a mixed case without asserting something the bundle does not support, and the
mixed composition is already visible in `file_collections` and
`distribution_formats`. Both records now omit the slot.

### 2.11 LOW — elided author list in `citation` (**left as-is, caveat added**)

**Finding.** The stored citation contains `Anibal, J., ... Ghosh, S.`

**Disposition — unchanged, annotation added.** The elision is present in the
PhysioNet-supplied APA rendering that the bundle quotes; transcribing it
faithfully is correct behaviour for a baseline arm. Reconstructing the full
118-author list from the page's author block would be a synthesis the citation
field did not ask for. A `source_caveats` now records that the citation is
transcribed as given and is elided at source, and that the full authorship is
recoverable from `creators` and from the cited DOI.

### 2.12 LOW — grant identifiers (**left as-is, caveat added**)

**Finding.** `funders[0].grants[0].id` uses a RePORTER project-details URL
carrying a search-scope segment (project 10858564, taken from the documentation
site's secondary-ID link); the sibling supplement grant uses project 11376382
from the NIH RePORTER source document.

**Disposition — unchanged, annotation added.** Both URLs are literally present
in the bundle and both resolve to the correct grant records. Rewriting either
into a cleaner canonical form would be a construction not supported by the
sources. A `source_caveats` on `funders` records that the two identifiers come
from different application records of one core project (OT2OD032720) and that
the first is a search-context link.

### 2.13 LOW — `variables` covers derived features but not phenotype columns (**left as-is, caveat added**)

**Finding.** Thirteen `VariableMetadata` records describe identifiers and
feature tensors. No phenotype columns are described, although the bundle states
that every phenotype TSV ships a JSON data dictionary.

**Disposition — unchanged, annotation added.** The bundle documents that the
dictionaries *exist* and describes their structure; it does not enumerate their
columns. Emitting `VariableMetadata` for columns whose names, types and value
sets are not in the bundle would be invention. The thirteen retained records are
each grounded in explicit statements about dimensionality, frame rate and
extraction parameters. A `source_caveats` on `variables` now records that
coverage is deliberately limited to variables the bundle characterises directly,
and that phenotype-level variables are documented only by reference to
per-file JSON dictionaries.

### 2.14 LOW — unresolved recording-count conflict (**left as-is, by design**)

**Finding.** The project documentation reports ~61,937 voice-derived recordings
for v3.0 across 833 participants; PhysioNet v3.1.0 reports per-feature counts of
23,533–32,522 with no new participants.

**Disposition — unchanged.** This is a genuine disagreement between two sources
in the declared bundle, and the uniform decision rules require representing it
rather than silently selecting one. Both records surface it in `source_caveats`.
The likely reconciliation — that the documentation figure counts recordings
across feature types or across a differently-scoped release — is *not* asserted,
because the bundle does not state it.

### 2.15 LOW — AI-readiness table in `notes` (**left as-is**)

**Finding.** The Bridge2AI AI-readiness self-assessment (criterion-by-criterion
scores) is carried in `notes`, partly overlapping `known_limitations`.

**Disposition — unchanged.** It is a self-assessment artefact with no fitting
structured slot; `notes` is the correct residual home per the slot's own
definition. The one substantive overlap — the unmet "Data Quality" criterion —
is independently supported by other bundle statements (site-specific collection
configurations, protocol changes over time, unaudited transcription) and is
retained in `known_limitations` on that basis, not by importing the table's
verdict.

---

## 3. Summary of changes

| Record | Slot | Action |
|---|---|---|
| core | `distributions` | removed; content moved to `file_collections` |
| core | `file_collections` | added (3 entries: features, phenotype, metadata) |
| core | `source_caveats` (distribution) | rewritten; invented enum reference removed |
| core | `errata` | removed (recorded a negative) |
| core | `is_tabular` | removed (mixed case) |
| core | `data_governance.committee_contact` | removed (office, not a Person) |
| full | `raw_sources` | added (back-propagated from core) |
| full | `annotation_analyses` | added (back-propagated from core) |
| full | `other_tasks` | removed (was empty list) |
| full | `conforms_to` | narrowed to distinguish source dataset from release |
| both | `source_caveats` | added/strengthened on `id`, `conforms_to`, `citation`, `funders`, `variables` |

**No factual content was added from outside the declared bundle.** Every
back-propagated slot restates evidence already present in the bundle and already
used in the sibling record.

---

## 4. Post-reconciliation state

**Full record:** 71 populated slots.
**Core record:** 43 populated slots.

Core is now a proper projection of full: every slot populated in core is
populated in full with consistent content. The reverse does not hold, and is not
required — `variables`, `subpopulations`, `machine_annotation_tools`,
`imputation_protocols` and others remain full-only by design.

Both files validate:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep2/VOICE_d4d.yaml
  → PASS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep2/VOICE_d4d_core.yaml
  → PASS
```

The core header's `# Phase 4 reconciliation: completed` line is now accurate.

---

## 5. Standing caveats carried into both records

These are unresolved by design and are recorded in `source_caveats` rather than
silently decided:

1. Recording counts disagree between the project documentation (~61,937 for
   v3.0) and PhysioNet per-feature counts (23,533–32,522 for v3.1.0).
2. Participant totals disagree: documentation cites 833 adult participants for
   v3.0; PhysioNet v3.1.0 states no new participants but does not restate the
   total independently.
3. BIDS conformance is documented for the audio-bearing source dataset; its
   applicability to the audio-free derived release is partial.
4. The enrolment target (10,000 voices, anticipated by 2027) is a project goal,
   not a property of this release.
5. Collection start and end dates are not stated in the bundle; only "over a
   period of 12 months" appears, without anchoring dates.
6. Fourteen `Creator` identifiers are minted under a `b2ai-voice.org` path not
   present in the bundle, because the sources name the people but assign them no
   identifiers.