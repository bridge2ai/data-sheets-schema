# Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/CM4AI_crate_only.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep2/CM4AI_d4d_core.yaml`

---

## 1. Referent

Both records take as their single `Dataset` referent the **Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta)**, identified in the crate as `https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`, DOI `10.18130/V3/HIGT4C`. This is the entity the `ro-crate-metadata.json` descriptor is `about`, the entity the AI-readiness assessment scores, and the only entity in the bundle carrying release-level `rai:*`, ethics, governance and access fields.

The nine ARK-identified component crates that declare `isPartOf` the June 2026 release (two AP-MS EndoTag submissions, three IF image sets, two SEC-MS submissions, two Perturb-Seq submissions) are represented as nested `resources`, not as alternative referents. This choice is unchanged from Phase 1 and is held identically in both records.

---

## 2. What the audit found

The audit returned 53 findings: 1 substantive evidence-handling defect, 7 medium-severity consistency defects, and the remainder low/informational. No fabricated external facts were detected — every populated claim traces to either `CM4AI_crate_metadata_reduced.json` or `ai_ready_score.json`. No prior-D4D copy-through indicators were observed.

Three systematic patterns dominated:

1. **Unrepresented source disagreement on dataset size.** The bundle states the release size twice and inconsistently: `evi:totalContentSizeBytes: 21051331945400` (~21.05 TB) at the top level, versus `contentSize: "19.9 TB"` on the same entity and `"Total size: 19.9 TB"` in the AI-readiness `characterization.statistics` block. Phase 1 silently adopted the byte figure.

2. **Absence-assertion.** Eight slots were populated principally to state that the crate records nothing — `errata`, `extension_mechanism`, `regulatory_restrictions`, `sensitive_elements`, `splits`, `collection_notifications`, `consent_revocations`, `participant_privacy`. Under the uniform decision rules, omission is the correct answer when evidence is absent; asserting absence is inference.

3. **Unsignalled full/core divergence.** Six slots present in the full record were absent from the core with no difference in underlying evidence, and one statement (the EVI provenance graph) had migrated from `relationships` in the full record to `instances` in the core.

One audit finding was **rejected on re-verification** (see §5).

---

## 3. Changes made to the full record

| Slot | Change | Reason |
|---|---|---|
| `total_size_bytes` | Retained `21051331945400`; added an explicit note of the conflicting figure to `known_limitations`. | `total_size_bytes` is a single-valued integer and cannot carry two figures. The byte-precise machine-generated value is retained as the slot filler; the disagreement is now *represented* rather than resolved silently, per the rule against selecting one of two conflicting sources without disclosure. |
| `known_limitations` | Added an entry recording that the crate reports the release size as both `evi:totalContentSizeBytes` 21,051,331,945,400 bytes and `contentSize` "19.9 TB", and that these do not agree. | Carries the disagreement into the record itself. |
| `errata` | **Removed.** | Populated only to assert that no errata are recorded. The accompanying completeness and augmentation facts were already carried by `known_limitations` and `updates`; nothing was lost. |
| `sensitive_elements` | **Removed.** | Populated only to assert absence. The underlying evidence (`humanSubjectResearch: "None"`, `confidentialityLevel: "Unrestricted"`, `d4d:atRiskPopulations: "None"`) is retained in `human_subject_research`, `confidential_elements` and `at_risk_populations`, where it is directly stated rather than inferred. |
| `collection_notifications` | **Removed.** | Derived not-applicable claim; the bundle makes no notification statement. |
| `consent_revocations` | **Removed.** | Derived not-applicable claim; the bundle makes no revocation statement. |
| `participant_privacy` | **Removed.** | Derived not-applicable claim; the bundle documents no participant-privacy procedure because it documents no participants. |
| `splits` | **Removed.** | The informative half ("no train/validation/test partitions are defined") was an absence-assertion; the descriptive half (organisation by assay modality and treatment condition) duplicated `resources` and `subpopulations`. |
| `extension_mechanism` | **Retained, reworded.** Dropped the clause "No formal external contribution mechanism is recorded"; kept the quarterly-augmentation commitment through November 2026 and the contact address `tideker@health.ucsd.edu`. | The retained content is directly stated in `rai:dataReleaseMaintenancePlan` and `contactEmail`. The dropped clause asserted absence. |
| `regulatory_restrictions` | **Retained, reworded.** Dropped "No export-control or similar regulatory restriction is recorded"; kept the clinical-use condition quoted from `usageInfo` / `prohibitedUses`. | Same rationale. |
| `keywords` | Rebuilt. Now carries the complete literal `schema:keywords` array of the June 2026 release verbatim (including the case-variant duplicates the crate actually contains), plus every `about` DefinedTerm name — Breast Neoplasms, Induced Pluripotent Stem Cells, CRISPR-Cas Systems, Mass Spectrometry, Fluorescent Antibody Technique, **Paclitaxel**, Vorinostat, Proteomics, RNA-Seq, Functional genomics, Machine learning, MDA-MB-468, KOLF2.1J. | Phase 1 dropped literal keywords, added ontology terms selectively, and asymmetrically omitted Paclitaxel while including Vorinostat. The rebuild is exhaustive and symmetric across both crate fields. |
| `created_by` | Reworded to `"Trey Ideker — recorded in the crate as principalInvestigator"`. | The crate names Ideker only as `principalInvestigator`; it records no creator. The role is now stated rather than silently promoted. Affiliation removed from this slot (it is carried on the corresponding `creators` entry, sourced from the Person record for ORCID 0000-0002-1708-8454). |
| `discouraged_uses` | Reworded to attribute both entries to their sources — the domain-expertise requirement to `rai:dataLimitations`, the population-coverage caveat to `rai:dataBiases`. | The inference from limitation/bias to discouragement is defensible but was presented as if stated. Attribution makes the derivation visible. |
| `future_use_impacts` | Reworded to drop the unsourced consequence "analyses built on it may need revision"; retained the sourced facts (interim status, pre-publication embargo, quarterly augmentation to November 2026, cell maps to be added in future releases). | The consequence was synthesised. |
| `other_tasks` | Reworded from a downstream-task framing to the crate's own statement: computed cell maps are not included in this release and will be added in future releases. | The bundle does not present map construction as a third-party task. |
| `instances` | Relabelled. The counts (55,859 total entities; 53,877 datasets; 1,976 computations; 6 software; 20 schemas) are now explicitly described as RO-Crate provenance-graph entity counts, not as counts of data records. | Prevents conflation of graph entities (which include computations, software and schemas) with data instances. |
| `labeling_strategies` | **Removed.** | Described entity-ID naming conventions in the collapsed `hasPart` summaries. No annotation or labeling procedure is documented anywhere in the bundle; this was metadata structure, not methodology. |
| `sampling_strategies` | Reworded to state the coverage facts directly (464 proteins of interest per IF treatment condition; per AP-MS batch, an untagged parental control, 10 chromatin-modifier tagged lines and a positive-control tagged line, four biological replicates; DMSO vehicle controls) without framing them as a sampling methodology. | The counts are quoted from the component crate descriptions; the sampling framing was the agent's. |
| `raw_sources` | Reworded. Now states that the Perturbation Cell Atlas raw sequence component is named and identified in the crate as SRA-derived (`rocrate-sra-data-for-perturbation-cell-atlas`, sample IDs of the form `sample-sra-sample-…`) and that its `url` is recorded as `"Embargoed"`. No accession is claimed. | Removes over-specification; adds the embargo fact, which is directly stated and materially relevant to access. |
| `acquisition_methods` | Reworded to drop "rather than obtained from human participants" and to replace "mirrored from" with the crate's own linkage fields (`sameAs` to MassIVE `MSV000101915`, `MSV000101917`, `MSV000100676`; `contentUrl` `ftp://massive-ftp.ucsd.edu/v10/MSV000098237/`; `url` to FigShare). | Removes inferential gloss; keeps the verifiable identifiers. |
| `confidential_elements` | Reordered so the pre-publication embargo entry leads; the `confidentialityLevel: "Unrestricted"` statement is retained but explicitly labelled as the crate's confidentiality classification. | The slot semantics ("confidential or restricted information") were inverted by leading with an unrestricted classification. The embargo is the genuine restriction. |
| `ethical_reviews` | Reverted the surname to the crate literal `"Vardit Ravistky"` with a bracketed note that the crate's Person entity for ORCID 0000-0002-7080-8801 gives `"Ravitsky, V"`. | Phase 1 silently corrected a source typo. Both spellings are now visible and attributed. |
| `resources` | Added a scope note: the nine enumerated components are the sub-crates expanded in the reduced JSON-LD; the top-level `hasPart` is reported by the normalizer as 60 direct parts with file-level inventories collapsed. | Prevents the reader inferring that the release comprises exactly nine components. |
| `resources[3]` (Untreated IF Images) | Added `contactEmail: tideker@health.ucsd.edu`; the `funder` field is left unpopulated for this entry. | The untreated crate genuinely differs from the paclitaxel and vorinostat crates, which give `emmalu@stanford.edu` and an NIH funder string. The difference is now preserved rather than smoothed. |
| `resources[6]` (SEC-MS treated cancer cells) | `doi` now records the crate literal `https://doi.org/doi:10.25345/C5348GV4S` with the normalised form `10.25345/C5348GV4S` noted alongside. | Phase 1 silently repaired a malformed source string. |
| `issued` (top level and all `resources[*]`) | Date-only source values are now emitted as dates without fabricated time-of-day or timezone. `2026-06-30` (top level) and `2025-02-28` (three IF crates) no longer carry `T00:00:00Z`. Timestamped values (`2026-05-22T13:23:35.699025+00:00`, `2026-05-22T13:58:58.942348+00:00`, `2026-05-27T20:36:55.634084+00:00`) are retained at full source precision. | Removes unsourced precision; stops truncating precision that the source does supply. |

---

## 4. Changes made to the core record

All content changes in §3 that touch slots present in the core schema were applied identically to the core record. In addition, the following divergences were closed:

| Slot | Change | Reason |
|---|---|---|
| `total_size_bytes` | **Added** to the core record, matching the full record, with the same disagreement note carried in `known_limitations`. | The fact is directly evidenced and the slot exists in the core schema; its absence was an unexplained divergence. |
| `relationships` / `instances` | The EVI provenance-graph statement was moved back out of `instances` and into `relationships` in the core record, matching the full record's placement. | The same content was filed under two different slots across the paired records. `relationships` is the correct home: the statement describes how entities in the crate relate (inputs/outputs, `isPartOf`, evidence graph), not what an instance is. |
| `collection_consents` | **Removed** from the full record so both records now carry the `d4d:informedConsent` statement once, under `informed_consent` only. | Phase 1 duplicated a single source statement across two slots in the full record and one slot in the core. Deduplicating in the full record (rather than adding a duplicate to the core) resolves both the divergence and the redundancy. |
| `third_party_sharing` | **Added** to the core record. | Supported by `publisher` (Dataverse, MassIVE, FigShare), `sameAs`, `contentUrl` and `url` fields. Its absence from the core was an unexplained divergence. |
| `splits`, `direct_collection`, `participant_privacy` | Now absent from both records. | These were removed from the full record (§3), which incidentally closes the divergence. `direct_collection` was additionally an inferred restatement of `humanSubjectResearch`; the crate makes no direct-vs-third-party collection claim. |
| `keywords`, `created_by`, `status`, `known_limitations`, `discouraged_uses`, `future_use_impacts`, `other_tasks`, `errata`, `extension_mechanism`, `regulatory_restrictions`, `sensitive_elements`, `instances`, `creators`, `maintainers`, `ethical_reviews`, `acquisition_methods`, `raw_sources`, `labeling_strategies`, `confidential_elements` | Mirrored from the full record. | Paired-record consistency. |

---

## 5. Findings rejected on re-verification

**`creators` — Marquez, C.** The audit reported that ORCID `0000-0003-3960-420X` ("Marquez, C") appears only in the graph and in older March-2025 citation strings, not in the June 2026 release's `author` array. Re-reading the top-level `author` array confirms `0000-0003-3960-420X` **is** present, between Levinson (`0000-0003-0384-8499`) and Metallo (`0000-0003-2404-3040`). Marquez is therefore correctly listed as a creator and **no change was made**.

The related half of the finding is upheld but resolved differently than the audit implies: `Park, S` and `Zhao, X` appear in the June 2026 `citation` string but **not** in the `author` array, and have no Person entity in the graph. `creators` is derived from the structured `author` array (47 entries, matching the AI-readiness `key_actors_identified` count of 47), so they are correctly excluded from `creators`. The `citation` slot reproduces the crate's citation string verbatim, so both names remain visible in the record. A note recording the mismatch between the `author` array and the `citation` string was added to `known_limitations` in both records.

---

## 6. Left as-is, with reasons

| Slot / item | Left as-is because |
|---|---|
| `status` | The composite string ("Beta interim release; not yet in completed final form") has no single source field, but each clause is verbatim-traceable: `(Beta)` in the release `name`, `"These data are not yet in completed final form"` in `completeness`, `"This is an interim release"` in `rai:dataLimitations`. The crate has no `status` field, so a faithful composite is the only way to populate the slot; the alternative is omission, which would discard a well-evidenced and materially important fact. Retained. |
| `known_limitations` — checksum coverage | The counts are exact (`evi:entitiesWithChecksums: 8`, `evi:totalEntities: 55859`, and the AI-readiness `verifiable` detail `"0% of files have checksums (8/55859)"`). The audit noted the source frames this positively (`has_content: true`) while the record frames it as a limitation. The numeric claim is unaltered and the framing is defensible on its face — 8 of 55,859 is sparse coverage by any reading. Retained, with the source's own `verifiable` phrasing quoted so the reader can see the framing difference. |
| `maintainers` — Jilian Parker | The crate records Parker under `dataGovernanceCommittee`, not as a maintainer, and gives no contact details. The entry is retained because the core and full schemas have no governance-committee slot and `maintainers` is the nearest fit, but the entry text now names the source field explicitly ("recorded in the crate as dataGovernanceCommittee"). |
| `resources` — nine components | Retained in full. The scope note added in §3 addresses the completeness concern without discarding well-evidenced sub-crate metadata. |
| `is_tabular`, `compression`, `total_file_count`, `file_collections`, `variables`, `anomalies`, `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols`, `cleaning_strategies`, `preprocessing_strategies`, `data_protection_impacts`, `participant_compensation`, `subsets`, `use_repository`, `related_datasets`, `parent_datasets`, `was_derived_from`, `download_url`, `language`, `created_on`, `last_updated_on`, `modified_by`, `conforms_to_class` | Omitted in both records. The bundle supplies no evidence for any of them. The crate's `evi:formats` array lists file extensions but does not characterise the release as tabular; `hasPart` inventories were collapsed by the normalizer, so no defensible file count or file-collection structure can be derived. Omission is the correct answer. |
| Referent choice | Unchanged. No competing candidate in the bundle carries the release-level ethics, governance, access and `rai:*` fields. |

---

## 7. Residual disagreements carried in the records

Two source conflicts remain unresolved by design, and are now stated inside both records rather than adjudicated:

1. **Release size** — `evi:totalContentSizeBytes` 21,051,331,945,400 bytes (~21.05 TB) vs. `contentSize` "19.9 TB" (corroborated by the AI-readiness assessment). The byte value fills `total_size_bytes`; the conflict is recorded in `known_limitations`.
2. **Author list vs. citation string** — the `author` array (47 entries) includes Marquez, C; the June 2026 `citation` string omits Marquez and adds Park, S and Zhao, X. `creators` follows the structured array; `citation` reproduces the string verbatim; the mismatch is recorded in `known_limitations`.

Additionally noted but not a conflict: the top-level release, the AP-MS crates and the SEC-MS/Perturb-Seq crates carry different `license` values (`CC BY-NC-SA 4.0` at release level; `CC0 1.0` on the two MassIVE AP-MS submissions and the KOLF2 SEC-MS submission; `CC BY-NC-SA 4.0` on the IF and Perturb-Seq crates). These are distinct entities with genuinely distinct licences, not a disagreement about one entity, so each is recorded on its own `resources` entry and the release-level `license` is `https://creativecommons.org/licenses/by-nc-sa/4.0/` as stated.

---

## 8. Outcome

| | Full | Core |
|---|---|---|
| Slots populated after reconciliation | 54 | 43 |
| Slots removed in Phase 4 | 8 | 4 |
| Slots added in Phase 4 | 0 | 2 |
| Slots reworded / re-sourced | 17 | 15 |
| Schema validation | passed (`Dataset`) | passed (`CoreDataset`) |

Both records validate. The paired records are now consistent: every slot present in the core is present in the full with identical content, and every full-record slot absent from the core is absent either because the core schema does not admit it or because it was removed from both. No factual claim in either record originates outside `data/preprocessed/concatenated/CM4AI_crate_only.txt`. No previously generated D4D record was read or consulted at any phase.