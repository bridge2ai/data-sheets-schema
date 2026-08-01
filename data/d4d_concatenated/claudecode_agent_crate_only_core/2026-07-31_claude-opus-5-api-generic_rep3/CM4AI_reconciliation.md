# D4D Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/CM4AI_crate_only.txt`
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep3/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep3/CM4AI_d4d_core.yaml`

---

## 1. Outcome summary

| Item | Value |
|---|---|
| Full record populated slots (Phase 1) | 53 |
| Full record populated slots (post-Phase 4) | 54 |
| Core record populated slots (Phase 2) | 31 |
| Core record populated slots (post-Phase 4) | 33 |
| Full validates against `Dataset` | yes |
| Core validates against `CoreDataset` | yes |
| High-severity findings | 0 |
| Medium-severity findings | 0 |
| Low-severity findings | 11 |
| Informational findings | 3 |
| Findings resolved by edit | 8 |
| Findings closed without edit | 6 |
| Referent drift between records | none |
| Prior-D4D copy-through indicators | none detected |

---

## 2. Referent declaration

Both records take a single referent: the top-level June 2026 release crate,
`https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`,
titled *Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta)*, version 1.0, DOI `10.18130/V3/HIGT4C`.

The nine component crates present in the bundle (two EndoTag AP-MS crates, three IF image crates, two SEC-MS crates, and the two perturb-seq crates) are carried as `resources` entries subordinate to that referent, not as alternative referents. The audit confirmed this choice is held identically in both files; no edit was required on this point.

---

## 3. What the audit found

The audit compared every populated slot in both records against the two bundle artifacts (`CM4AI_crate_metadata_reduced.json`, `ai_ready_score.json`). No assertion was found that lacks a bundle trace, and no numeric claim in the nine `resources` entries was found to be wrong. The defects that surfaced are all low-severity or informational and fall into four clusters.

**Cluster A — interpretive stretch in free-text objects.** Three objects asserted slightly more than the crate states: a "Mali laboratory, UCSD" data collector inferred from a contact email plus an author affiliation; a de-identification claim that the crate "records no personally identifiable information," which is an asserted absence rather than a source statement; and maintainer entries that recast the crate's `principalInvestigator` and `dataGovernanceCommittee` roles as maintenance responsibility, which the `rai:dataReleaseMaintenancePlan` text never assigns to anyone.

**Cluster B — internal source disagreements silently resolved.** The crate declares both `contentSize: "19.9 TB"` and `evi:totalContentSizeBytes: 21051331945400` (≈21.05 TB decimal, ≈19.15 TiB); the full record kept only the byte figure. Two distinct DOIs (`10.18130/V3/B35XWX` and `10.18130/V3/K7TGEM`) appear in the bundle under the identical title "March 2025 Data Release (Beta)", and `version_access` named only one. The Nourreddine et al. reference in the crate pairs Clark et al.'s bioRxiv accession with Nourreddine's DOI; the record had tidied this away.

**Cluster C — supported evidence not carried into typed slots, or lost from core.** The crate's `datePublished: "2026-06-30"` survived only inside a free-text `distribution_dates` entry, leaving the typed `issued` slot empty. The core record dropped the verbatim recommended citation and dropped the size statement entirely, both of which the core schema admits.

**Cluster D — category shift in `keywords`.** Eight terms appended to `keywords` are labels of MeSH/EDAM `DefinedTerm` entities attached to the crate via `schema:about`, not crate keywords. The same facts were already correctly recorded in `external_resources`, so this was duplication in the wrong category rather than fabrication.

---

## 4. Changes made to the full record

| Slot | Change | Reason |
|---|---|---|
| `issued` | Added `2026-06-30` | Directly supported by the top-level crate's `datePublished`; a typed datetime slot was left empty while the fact sat in prose. |
| `total_size_bytes` | Retained `21051331945400`; the co-declared `19.9 TB` figure added as an explicit statement in the accompanying `description` of the size evidence | The bundle disagrees with itself. Uniform rule: represent what the evidence states rather than silently selecting one side. The typed integer slot can hold only one value, so the second declared figure is surfaced in text alongside it. |
| `data_collectors` | "Mali laboratory, University of California San Diego" reworded to record what the crate states — perturb-seq crates give contact `pmali@ucsd.edu`, with Mali P affiliated to UCSD | The laboratory attribution was an inference. The Lundberg Lab (Stanford) and Nevan Krogan laboratory (UCSF) entries are explicit in the crate and were left untouched. |
| `is_deidentified` | Removed the clause asserting that no personally identifiable information is recorded; retained "commercially available de-identified human cell lines" and `confidentialityLevel: Unrestricted` | An asserted absence the bundle does not state. The retained components are verbatim source claims. |
| `maintainers` | Roles restated as the crate labels them (Trey Ideker as principal investigator and contact; Jilian Parker as data governance committee), with the maintenance-plan text kept separate and unattributed | The crate never designates a maintainer. Keeping the entries but correcting the role labels preserves the contact evidence without inventing a responsibility assignment. |
| `version_access` | Now names both `10.18130/V3/B35XWX` and `10.18130/V3/K7TGEM` as DOIs cited in the bundle under the title "March 2025 Data Release (Beta)" | The single-DOI phrasing masked a genuine source conflict across component crates. |
| `external_resources` | Nourreddine et al. entry restored to the crate's own wording, including the mismatched accession/DOI pairing, with the inconsistency noted | Silent cleanup replaced source evidence with a tidier claim. The guard prefers representing the conflict. |
| `keywords` | Eight MeSH/EDAM `DefinedTerm` labels removed | They are `schema:about` subject annotations, not crate keywords; already correctly carried in `external_resources`, so no evidence is lost. |

Net effect on the full record: one slot added (`issued`), no slot removed, six slots reworded, one slot trimmed of miscategorised values. Populated slot count 53 → 54.

---

## 5. Changes made to the core record

| Slot | Change | Reason |
|---|---|---|
| `citation` | Added, verbatim from the crate's `citation` field | Clearly supported and present in the full record; the core schema admits the slot, so the omission was unjustified. |
| `total_size_bytes` | Added `21051331945400`, with the co-declared `19.9 TB` noted in the accompanying description | Restores parity with the full record and prevents total loss of the size statement from the core file. |
| `keywords` | Same eight MeSH/EDAM labels removed | Same reason as the full record; keeps the two files aligned. |
| `creators`, `is_deidentified`, `acquisition_methods` (data-collector text) | Same wording corrections applied as in the full record | Cross-record consistency: a claim softened in one file must not survive in stronger form in the other. |

Net effect on the core record: two slots added, three slots reworded, one trimmed. Populated slot count 31 → 33.

---

## 6. What was left as-is, and why

**The 47-name creator list versus the citation string.** The crate's `author` array holds 47 entries; the release's own `citation` additionally names "Park, S" and "Zhao, X". The creator list was left at the 47 `author` entries, because `creators` is a structured authorship slot and the `author` array is the crate's structured authorship statement. The citation string is carried verbatim in `citation` in both records, so the two additional names remain visible in the record and a reader can see the discrepancy. Merging the citation names into `creators` would have silently reconciled two distinct source statements, which the decision rules forbid.

**Structural divergence between full and core in three slots.** Content the full record places in `direct_collection`, `relationships`, and `third_party_sharing` is folded into `acquisition_methods`, `instances`, and `external_resources` in the core record, reflecting the narrower core slot inventory. Field-by-field comparison confirmed the factual content is preserved verbatim and no claim diverges. This is a schema-shape difference, not a factual one, and was left unchanged.

**All nine `resources` entries.** Content sizes (441.2 GB, 532.5 GB, 2.6 GB, 3.2 GB, 2.8 GB, 1.11 TB, 910 GB, 16.7 TB, 177.35 GB), `hasPart`/input/output counts, MD5 values, versions, licenses, the MassIVE and FigShare URLs, DOI `10.25345/C5348GV4S`, and the `"Embargoed"` access URL were all verified against the crate JSON-LD and found correct. Two normalisations were reviewed and kept: `sameAs` mapped to `page` (the MassIVE query URLs are landing pages, which matches the slot definition), and the source typo "Idkeker T" rendered "Ideker T" in one author string — an orthographic correction to a name established elsewhere in the same bundle, not a factual change.

**The referent choice.** No edit; the choice is documented in §2 and held consistently.

**Empty slots.** No slot was populated during Phase 4 on the strength of inference. The many slots left absent — including `subpopulations`, `splits`, `imputation_protocols`, `annotation_analyses`, `participant_compensation`, `regulatory_restrictions`, `errata`, and `use_repository` — remain absent because the crate-only bundle carries no evidence for them. Under the uniform decision rules an absent slot is the correct answer when the evidence is absent; the crate-only arm is expected to be sparser than an arm with the document corpus, and no attempt was made to close that gap.

---

## 7. Provenance guard status

- Factual inputs limited to the declared bundle and the two schema files.
- No previously generated D4D record, from any arm, label, or date, was read or consulted. Nothing under `data/d4d_concatenated/` and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened.
- The withheld artifacts named in the bundle header (`CM4AI_crate_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`) were not present in the bundle and were not sought.
- Live provenance record written via `d4d provenance record` for project CM4AI, method `claudecode_agent_crate_only`, label `2026-07-31_claude-opus-5-api-generic_rep3`.
- Both records re-validated after Phase 4 edits; both pass.