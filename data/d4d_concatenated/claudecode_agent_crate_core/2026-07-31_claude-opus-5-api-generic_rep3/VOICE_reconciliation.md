# Reconciliation Report — VOICE

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt`
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes at least four distinguishable resources:

1. the **Bridge2AI-Voice adult dataset**, PhysioNet feature-only release, current version **3.1.0** (DOI `10.13026/8xbn-nq66`);
2. the **Bridge2AI-Voice Pediatric Dataset**, a *separate* PhysioNet project (DOI `10.13026/h995-bt35`), distinct cohort, distinct REB approval, distinct Synapse raw-audio route;
3. the **raw-audio distribution** under controlled access via Synapse (`syn72370534`), BIDS-organised;
4. the **whole 10,000-voice consortium data-generation effort** described by the IRB protocol, NIH RePORTER entry and white paper.

**Chosen referent: (1), the adult PhysioNet feature-only release, version 3.1.0.** This is the resource that carries a DOI, a license, a data use agreement, a file inventory, a versioning history and an access policy in the bundle — i.e. the resource the bundle documents *as a dataset* rather than as a programme or a delivery channel. Both records now hold to this referent consistently, and the reconciliation below is largely an exercise in enforcing it.

The programme-level material (IRB protocol, RePORTER, white paper) is retained where it documents *how the referent came to exist* — collection methods, consent, ethics, funding — which is precisely what those Datasheets modules ask for. It is not retained where it describes enrolment ambitions or sibling resources that are not the referent.

---

## 2. What the audit found

Twenty-four findings across four severity-weighted classes. In summary:

| Class | Count | Character |
|---|---|---|
| Structural / cardinality | 4 (high) | Full record supplied lists for single-valued object slots; core record supplied single objects for the same content |
| Unsupported factual claim | 2 (medium) | An author count asserted in both records, present nowhere in the bundle and numerically wrong |
| Unrepresented source disagreement | 3 (medium/low) | Enrolment target; high-volume-clinic definition |
| Referent bleed / version mixing | 7 (medium/low) | Pediatric facts and v3.0.0 byte inventory inside a v3.1.0 adult record |
| Supported omission | 3 (medium/low) | `related_datasets`; core `citation`; aggregate size slots |
| Over-generalisation / silent normalisation | 5 (low) | Scope creep on `conforms_to`, `errata`, `funders`; a corrected BIDS path; an inferred compensation negative |

The records were otherwise well grounded. Sampling strategy, de-identification procedure, consent and revocation terms, governance and access tiers, licence and IP restrictions, feature-extraction parameters, per-feature recording counts (29,278 / 32,522 / 28,640 and the rest), and the 833-participant figure all trace cleanly and correctly to the declared bundle. The collection-timeframe entry already surfaced one disagreement correctly, which is the behaviour the remaining fixes generalise.

---

## 3. Changes applied

### 3.1 Full record

**Cardinality — four slots collapsed from list to single object (high).**
`license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions` and `at_risk_populations` each have a single-valued range in the slot inventory (no `[many]` marker). The full record supplied lists; the core record supplied single objects for the same content. Each list was merged into one object, concatenating the distinct statements into the appropriate scalar fields rather than discarding any of them. No factual content was lost. This also removes the paired-record inconsistency: full and core now express identical content with identical structure.

**`creators` — unsupported author count removed (medium).**
The sentence asserting that version 3.1.0 "lists 118 named authors" appears nowhere in the bundle and is wrong on its face: the v3.1.0 byline extends the 117-name v3.0.0 list with Ghaffar, Ghavanini, Kobayashi, Potter and Rajkumar, giving 122. Rather than substituting a recount — which would be a derived figure, not a stated one — the numeric claim was deleted. The creator descriptions now characterise authorship qualitatively (multi-institutional consortium byline, named co-PIs, named module leads), all of which is directly stated.

**`related_datasets` — populated (medium).**
This was empty despite the bundle supporting typed relationships explicitly. Added:

- the Bridge2AI-Voice Pediatric Dataset as a companion resource, with its own DOI, identified in the PhysioNet notice as a separate project rather than a version of this one;
- the Health Data Nexus v1.0 release (`10.57764/qb6h-em84`) and the PhysioNet v1.1 / 2.0.0 / 2.0.1 / 3.0.0 releases as prior versions of this same resource.

Both required keys (`relationship_type`, `target_dataset`) are present on every entry. This relocates information that had been scattered across `external_resources` and `version_access` into the slot that carries the relationship semantics.

**`conforms_to` — BIDS claim rescoped (medium).**
The bundle attributes BIDS v1.9.0 conformance to the raw-audio and questionnaire conversion — the `b2ai-voice-audio` tree in the documentation's pre-processing section — not to the PhysioNet feature-only release, whose layout is `features/`, `phenotype/` and `metadata/`. The dataset-level `conforms_to` assertion was removed. The BIDS statement is retained in `preprocessing_strategies` and `raw_sources`, where it correctly describes the upstream organisation of material that the referent is derived from.

**`file_collections` — version provenance and id namespace corrected (medium/low).**
The per-file byte sizes and SHA-256 digests in the first collection come from the v3.0.0 RO-Crate. v3.1.0 explicitly repaired the Parquet files and changed recording counts, so those figures cannot be assumed to carry forward. The collection is retained — it is genuine, cited evidence — but its description now states plainly that the inventory is the v3.0.0 crate manifest and that v3.1.0 reissued these files, so the figures are indicative of composition rather than authoritative for the declared version. The collection's `id` was re-minted under the v3.1.0 DOI base (`10.13026/8xbn-nq66`) to match the record `id` and the three sibling collections, eliminating the mixed-namespace inconsistency.

**`anomalies` — pediatric statement removed (medium).**
The observation that some recordings used the built-in tablet microphone rather than a headset is stated in the bundle about the *pediatric* cohort, where low tolerance for headphones or complex medical conditions is given as the reason. It is not stated about the adult cohort and was presented here unqualified. Removed. The adult-applicable microphone-variability anomaly — headset distance varying between participants, distinct iPad devices per site — is retained, since the bundle states it directly of the adult collection.

**`distribution_dates` — pediatric entry removed (low).**
The v1.0.0 / v1.1.0 pediatric release dates are distribution dates of a different dataset. Removed from the referent's distribution history. The pediatric resource is now represented once, correctly, in `related_datasets`.

**`errata` — CHANGES.md statement rescoped (low).**
The `CHANGES.md` file belongs to the BIDS audio distribution, not the feature-only release. The claim was narrowed to what the bundle states of the referent: PhysioNet publishes a per-version changelog with the dataset metadata, and there is no separate erratum.

**`funders` — NIH role statement rescoped (low).**
"The NIH had no role in the preparation, review or approval…" is a Role-of-the-Funder statement specific to the JAMA Otolaryngology viewpoint. It was generalised to the dataset and to consortium outputs at large. Now attributed to that publication.

**`raw_sources` — BIDS path restored verbatim (low).**
The record had silently normalised `ses-<participant_id>` to `ses-<session_id>`, which is almost certainly the correct intent but is not what the source says. The path is now reproduced as the documentation gives it, with a note that the session directory is documented using the participant identifier token. Correcting a probable upstream typo is an inference; recording it is not.

**`data_collectors` — inferred negative removed (low).**
"They were not separately compensated for data collection" is not stated. The bundle answers the compensation question for clinicians by describing IRB co-investigator listing and consortium authorship credit. The record now says that and stops there.

### 3.2 Core record

**`creators`** — same unsupported author count removed, same reasoning as §3.1.

**`citation`** — added. The recommended PhysioNet citation for v3.1.0 is supplied verbatim by the bundle and was already in the full record. Its absence from the core record was an unforced omission and a paired-record inconsistency.

**`distributions`** — the v3.0.0 byte inventory now carries the same version-provenance qualification applied to the full record's `file_collections`.

**`distribution_dates`** — pediatric release dates removed, matching the full record.

**`anomalies`** — pediatric microphone statement removed, matching the full record.

### 3.3 Both records

**Enrolment target — disagreement now represented (medium).**
The bundle carries three incompatible figures:

- **30,000** participants — IRB protocol §12.1 and the audiomics white paper ("a publicly available database of 30 000 human voices");
- **10,000** — the documentation's Study Metadata ("Enrollment Count (Anticipated by 2027): 10,000") and the project overview;
- **~3,000 by November 2026** — the crate's `rai:dataCollectionTimeframe`.

The records previously presented 10,000 in `human_subject_research`, ~3,000 in `collection_timeframes`, and dropped 30,000 entirely — a silent selection across two slots. Both records now state all three figures with their sources in `human_subject_research`, and note that they are not reconcilable from the bundle. The 833 participants actually present in the referent release remain stated separately and unambiguously in `instances` and `subsets`, where they are a fact about the dataset rather than about the programme's ambitions.

**`sampling_strategies` — high-volume-clinic disagreement represented (low).**
Two definitions appear: "more than 50 patients per month from the same disease category" (documentation, Collection Methods) and "a volume of over 1000 patients per year" (IRB protocol §6.2). Both are now given with attribution rather than only the first.

---

## 4. What was left as-is, and why

**Pediatric material in `collection_mechanisms` and `preprocessing_strategies` (low).**
The `reproschema-ui` collection route and the ReproSchema → REDCap → BIDS conversion are pediatric-specific. They were flagged as outside the chosen referent. They are **retained**, explicitly labelled as pediatric, because the documentation presents them inside the same protocol and pre-processing narrative that governs the adult collection, and because the labelling makes the scope unambiguous to a reader. Removing them would suppress a documented part of how the Bridge2AI-Voice collection apparatus works without improving the accuracy of any adult-specific claim. This is a judgement call and is recorded as such; a stricter reading would delete them.

**`is_tabular: false` (low).**
Flagged as being in tension with `distribution_formats`, since all phenotype data, `static_features.tsv` and `audio_quality_metrics.tsv` are TSV, and the dense features are column-oriented Parquet. Left as `false`. The slot asks whether the dataset *is* in tabular format — structured as a table. This dataset is a heterogeneous bundle whose substantive payload is variable-length tensor data (spectrograms, PPGs, EMA traces) keyed by participant/session/task; the tabular components are metadata and per-recording summaries. `false` is the more honest single-boolean answer, and `distribution_formats`, `file_collections` and `variables` together give the reader the precise picture that the boolean cannot.

**`total_size_bytes` and `total_file_count` omitted (low).**
Both are aggregable from `file_collections` (9 files, 13,788,089,083 bytes) and the crate reports 12.9 GB for v3.0.0. Left **omitted**. The byte inventory covers only the dense Parquet features, not the phenotype TSVs, JSON dictionaries or metadata; and it is a v3.0.0 inventory under a v3.1.0 record whose files were reissued. Publishing an aggregate here would present a partial, stale figure as a dataset-level total. The per-collection figures remain available, correctly qualified, for anyone who wants them.

**Everything not listed in §3 or §4.**
The remaining populated slots were checked against the bundle and left untouched: purposes, addressing gaps, tasks, intended and prohibited and discouraged uses, acquisition methods, direct collection, collection timeframes, consent and notification and revocation, ethical review, data protection impact, de-identification, sensitive and confidential elements, content warnings, subpopulations, known biases, known limitations, labelling and annotation strategy, machine annotation tools, missing-data documentation, imputation protocol, cleaning strategy, maintainers, update plan, retention limits, version access, extension mechanism, third-party sharing, distribution formats, external resources, funders (apart from the rescoping above), keywords, language, and the descriptive header slots. Each is directly attested.

---

## 5. Post-reconciliation state

| | Full | Core |
|---|---|---|
| Slots populated | 77 of 94 | 31 |
| Slots changed in Phase 4 | 13 | 5 |
| Slots added in Phase 4 | 1 (`related_datasets`) | 1 (`citation`) |
| Slots removed in Phase 4 | 1 (`conforms_to`) | 0 |
| Cardinality corrections | 4 | 0 |
| Unsupported claims removed | 1 | 1 |
| Referent-bleed removals | 2 | 2 |
| Schema validation | pass | pass |

Both records were re-validated after every edit:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d_core.yaml
```

Both pass. All `DatasetRelationship` entries carry `relationship_type` and `target_dataset`; all `FileCollection`, `DataSubset` and nested `Dataset` entries carry `id`; all `RawDataSource` entries carry `source_description`; all `VariableMetadata` entries carry `variable_name`.

---

## 6. Provenance

No previously generated D4D record — from any arm, label or date — was read, opened, searched or consulted at any phase. The sole factual inputs were the declared bundle and the two schema files. The Phase 3 audit was conducted against the bundle directly, not against any reference record.

Live provenance recorded:

```
poetry run d4d provenance record \
  --project VOICE \
  --method claudecode_agent_crate \
  --label 2026-07-31_claude-opus-5-api-generic_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt
```