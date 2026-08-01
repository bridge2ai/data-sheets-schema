# Reconciliation Report — VOICE

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep1/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep1/VOICE_d4d_core.yaml`

**Declared input bundle** — `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 files). No other factual source consulted.

---

## 1. Referent

`Dataset` admits one referent. The bundle describes two distinct PhysioNet projects — the adult `b2ai-voice` dataset and the pediatric `b2ai-voice-pediatric` dataset — and the bundle's own curation note states these are separate cohorts collected under a separate protocol, not versions of one another.

**Referent held across both records: the Bridge2AI-Voice adult dataset, at release v3.1.0.** All counts, feature inventories, release history and access terms in both records describe that referent. The pediatric dataset is represented as a related resource, not folded into the referent's composition. This choice was already implicit in Phase 1 and Phase 2 and has been made explicit and consistent here.

---

## 2. What the audit found

The audit reported no hallucinated dataset facts. Substantive content — 833 participants across five North American sites, per-feature row counts for v3.1.0, the five disease cohorts with their gold-standard validation methods, the two-tier registered/controlled access structure, de-identification procedure, the $40/$80/$120 compensation schedule, and the six-version release history — traces to the bundle.

Defects were structural, in three clusters plus two isolated issues:

| Cluster | Slots affected | Nature |
|---|---|---|
| Invented slots | `_readiness`, `dialect` (core) | Not in the declared inventory; would fail validation |
| Negative assertions | `use_repository`, `compression` (core); `cleaning_strategies`, `errata`, `data_protection_impacts`, `funders` (full) | Slot populated with a statement that the information is absent |
| Entity collapsing | `collection_timeframes`, `instances`, `relationships`, `creators` (full) | Multiple distinct claims fused into one object in a multivalued slot |
| Slot misuse | `subsets` (full) | A composition caveat emitted as a subset |
| Omission | `related_datasets` (both) | Pediatric dataset placed in `external_resources` instead |

---

## 3. Changes made — core record

**`_readiness` — removed.** The slot does not exist in `CoreDataset`. It carried the AI-readiness scorecard (FAIRness, Provenance, Characterization, Pre-model explainability, Ethics, Sustainability, Computability, with per-criterion scores) from the project documentation. This content is bundle-supported but has no declared home in the schema. Inventing a slot to house it populates the record at the cost of validity. Removed rather than relocated, because no existing slot asks for a readiness scorecard and forcing it into `description` or `conforms_to` would misrepresent both fields.

**`dialect` — removed.** Not in the declared inventory. The delimiter and file-format content it carried (tab-delimited `.tsv` phenotype files, Parquet columnar binaries, paired `.json` data dictionaries) is genuine and is already represented in `distribution_formats` and `conforms_to_schema`, which are the fields that ask for it. No content was lost.

**`compression` — removed.** Was emitted as an explicit `null`. `CompressionEnum` admits seven values and `null` is not among them; an explicit null is both invalid and functionally identical to omission. The Phase 2 reasoning — that the bundle never states a compression format — was correct; the correct expression of that reasoning is to leave the slot unpopulated.

**`use_repository` — removed.** The single object recorded the healthsheet's answer that no repository tracking downstream use exists ("Is there a repository that links to any or all papers or systems that use the dataset? … No"). Per the v2 rule, a value stating that the information is absent has not answered the field. The fact itself is not lost: it remains recoverable from the bundle and is not a property the schema requires to be asserted negatively.

---

## 4. Changes made — full record

**`data_protection_impacts` — restructured, one object to two.** The original led with the healthsheet's "No" to whether an impact analysis was conducted, then appended two genuinely responsive artefacts. The leading negative was dropped. The two substantive items were separated into distinct objects, as the slot is multivalued and they are distinct assessments:

1. The *Memorandum: Ethical Justification for Controlled Access to Raw Voice Data Samples*, which reasons about re-identification risk from raw audio and grounds the controlled-access tier.
2. The ethicist-led review that identified sensitive fields for removal — household income, mental health status, traumatic life experiences, cultural identity, household composition — prior to release.

**`cleaning_strategies` — first entry dropped, six retained.** The first object stated that no cleaning preprocessing was performed and functioned as a preamble to the entries that followed. It is a negative framing note, not a cleaning strategy. The six retained entries (monaural conversion, 16 kHz resampling with Butterworth anti-aliasing, transcript review for identifying information and external voices, removal of sensitive-record features, exclusion of free-speech-derived spectrograms, audio quality-control metrics) each describe an actual operation and are unchanged.

**`errata` — first entry dropped, three retained.** Same pattern: the first object asserted "There is no erratum" and framed the release-note entries that followed. The three retained errata are real corrections — the v2.0 spectrogram reprocessing that fixed issues identified in v1.x, the v2.0.1 authorship-list correction, and the v3.1.0 repair of broken Parquet files together with back-filled validated-diagnosis information and gold-standard variable renaming.

**`relationships` — split and rescoped.** The original object simultaneously asserted a participant → session → recording hierarchy (from the BIDS-compliant directory structure and the `session.tsv` / `recording.tsv` task files) *and* quoted the healthsheet's answer that instances "are unrelated," contradicting itself within a single prose block. These are not the same claim. The healthsheet question concerns whether relationships between *participants* are made explicit; the file structure concerns nesting *within* a participant. Now two objects: one recording the intra-participant hierarchy and the fact that repeated sessions mean a participant may have multiple rows per phenotype file; one recording that no inter-participant relationships are asserted, per the healthsheet.

**`funders` — second entry dropped.** The removed object recorded that "The National Institutes of Health had no role in the preparation, review, or approval of the manuscript." That is a journal-mandated funder-role disclaimer attached to a JAMA Otolaryngology opinion piece. It is not a funding mechanism supporting dataset creation and does not answer what `FundingMechanism` asks for. The retained entry — NIH Common Fund Bridge2AI, award OT2OD032720 — is correct.

**`subsets` — `#release-note-distribution` removed.** This entry recorded that the public releases do not contain an equal distribution of the five disease-cohort categories. That is a composition caveat, not a logical partition of the data. It is already correctly recorded in `known_biases` (skew by disorder category, site, and demographic factors) and `known_limitations`. Emitting it a third time as a `DataSubset` misuses the slot. The genuine cohort subsets are unaffected.

**`collection_timeframes` — one object to three.** The original fused three distinct and non-identical claims. Now separated, because the slot is multivalued and the disagreement is material:

1. The healthsheet's statement that data was collected over a period of 12 months.
2. The NIH RePORTER project period, 2022-09-01 to 2026-11-30.
3. The IRB protocol's four-phase collection plan across a four-year study period.

Separating these makes the conflict legible rather than burying it in prose. No claim was adjudicated.

**`instances` — conflicting counts separated.** The original mixed the project documentation's aggregate figure (~61,937 voice-derived recordings for 833 adult participants) with the nine per-feature row counts published in the v3.1.0 release notes (29,278 spectrograms / mel-spectrograms / MFCCs; 32,522 torchaudio pitch; 28,640 SPARC EMA; 31,855 SPARC loudness; 31,872 SPARC periodicity and pitch; 29,289 PPGs). These do not reconcile — the documentation figure appears to describe an earlier or differently-counted release. Now two objects, one per source, with the discrepancy stated rather than averaged or silently resolved.

**`creators` — final entry trimmed.** The collective-entity Creator representing the Bridge2AI-Voice Consortium was retained; it is a legitimate corporate author and appears as such in the citation. The trailing commentary summarising that 50+ investigators and 110+ named authors exist was removed — that is metadata about the author list, not a description of a creator. Named individual creators with affiliations and roles are unchanged.

**`related_datasets` — populated.** The pediatric dataset had been recorded under `external_resources`. `DatasetRelationship` is the field that answers this, and it requires `relationship_type` and `target_dataset`. Added one entry: the Bridge2AI-Voice Pediatric Dataset (PhysioNet `b2ai-voice-pediatric` v1.1.0, DOI 10.13026/h995-bt35), 300 participants aged 2–18, 23,533 derived recordings, recruited at the Hospital for Sick Children under a separate REB approval and a separate pediatric protocol. Typed as a companion/sibling dataset rather than a part or a version, following the bundle's explicit curation note that the two are distinct cohorts and not versions of one another. The `external_resources` entry was removed to avoid representing the same relationship twice under two different semantics.

---

## 5. What was left as-is

**Version-pinned `id`.** The record uses the v3.1.0 DOI (`10.13026/8xbn-nq66`) rather than the latest-version DOI (`10.13026/37yb-1t42`). Both are in the bundle. The record describes v3.1.0 specifically — its per-feature counts, its release notes, its file layout — so the version-pinned identifier is the correct referent for what is documented. The alternative would create a record whose `id` resolves to a moving target while its contents are fixed. The choice is disclosed in the record's trailing notes.

**Unresolved conflicts retained as conflicts.** Per the decision rules, disagreement in the bundle is represented rather than adjudicated. Left standing and visible:

- Target enrolment stated as 10,000 voices (project documentation, study metadata) and 30,000 voices (NIH RePORTER narrative, IRB protocol).
- Four variant award-number renderings across sources (`OT2OD032720`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3`, `3Tf-OTOD03272001S2`).
- The surname of the SickKids pediatric investigator, given as both *Sui* and *Siu* in different sources.
- The 12-month vs. multi-year collection window, now separated as described above.
- The ~61,937 vs. per-feature recording counts, now separated as described above.

**`splits` — omitted, correct.** The healthsheet states explicitly that there are no predefined recommended splits and that researchers are encouraged to construct their own. This is recorded in `known_limitations`. Omission is the right answer; populating the slot to say "none" would be the negative-assertion defect corrected elsewhere in this pass.

**`total_file_count` and `total_size_bytes` — omitted, correct.** No aggregate file count or byte total appears anywhere in the bundle. The three `file_collections` carry the partial counts the bundle does supply. Nothing was inferred by summation.

**`annotation_analyses` — omitted.** The bundle reports no inter-annotator agreement analysis. The adjacent facts it does supply — a single labeler per instance, one label per instance, and human-level performance that "varies widely" — are recorded in `labeling_strategies` and `known_limitations`, which are the fields that ask for them. Populating `annotation_analyses` would require either duplicating that content or asserting an analysis that was not performed.

**Deliberate non-population elsewhere.** Slots including `imputation_protocols`, `at_risk_populations` (adult referent; the pediatric protocol governs minors and is out of referent scope), and `regulatory_restrictions` beyond the stated "no export controls apply" were left unpopulated where the bundle supports no positive claim.

---

## 6. Outcome

| | Core | Full |
|---|---|---|
| Slots removed | 4 | 0 |
| Slots added | 0 | 1 (`related_datasets`) |
| Slots restructured in place | 0 | 8 |
| Invented slots remaining | 0 | 0 |
| Negative-assertion values remaining | 0 | 0 |

Both records now populate only declared slots, carry no explicit-null enum values, and emit one object per distinct entity in multivalued slots. Content is consistent between the two records on every fact both assert, and both describe the same referent at the same release. Bundle conflicts are surfaced in both rather than resolved in one and hidden in the other.

No factual content was added, removed, or altered in this phase except as required to relocate bundle-supported material into the field that asks for it, or to remove assertions of absence that the schema does not ask for.