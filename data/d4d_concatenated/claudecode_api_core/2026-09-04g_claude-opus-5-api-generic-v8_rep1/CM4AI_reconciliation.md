# Phase 4 Reconciliation Report — CM4AI

## Scope

The Phase 3 audit returned six findings, all severity `low`, and no high or medium findings. Phase 4 applied strict reconciliation: each finding was assessed against the declared bundle and against the schema digest, and either repaired in both records or retained with reasons stated. No new factual content was introduced in this phase; every change is either a removal, a relocation of commentary into `source_caveats`, or the addition of an affiliation already attested in the bundle and already carried elsewhere in the record.

## Findings and dispositions

### 1. `sampling_strategies[1].strategies` — interpretive `is_sample: false` (low)

**Audit position.** The genome-scale CRISPRi entry asserts `is_sample: false`, which is an interpretation of the phrases "expressed genome-scale" and "whole-genome" rather than a directly stated fact. The accompanying caveat disclosed only the gene count, not the interpretive basis of the boolean.

**Action: changed, both records.** The boolean value was retained — the reading is defensible and removing it would leave the entry less informative than the evidence supports — but `source_caveats` was rewritten to disclose it explicitly. The original caveat read:

> The project portal describes the iPSC perturb-seq component as covering more than 11,000 genes at whole-genome scale and reports 11,739 genes targeted as a project-level figure.

The reconciled caveat adds the October 2025 attestation of the 11,739 figure and then states in terms:

> The is_sample value of false is this record's reading of "expressed genome-scale" and "whole-genome" as indicating comprehensive rather than sampled coverage; no source states in terms that the gene set is not a sample.

A reader now sees the boolean and the ground for it together.

A secondary change is visible in the same entry: `strategies` was emitted in the original as a one-item YAML sequence and is emitted in the reconciled record as a scalar string. The content is identical.

### 2. `sampling_strategies[0].strategies` — undisclosed 523-vs-464 conflict (low)

**Audit position.** The 200-gene and 523-protein figures come from the project portal's flagship-dataset panel, which describes the project's curated TNBC dataset rather than this release; and 523 conflicts with the 464 figure the October 2025 release gives for same-named IF archives. The conflict was disclosed under `file_collections` but not here.

**Action: changed, both records.** A `source_caveats` key was added to this entry (the original had none). It states that the figures describe the curated TNBC dataset generally rather than this release, that the June 2026 file listing carries no gene or protein counts, and that:

> The portal's figure of 523 proteins also conflicts with the October 2025 release page, which describes same-named immunofluorescence archives as showing 464 proteins of interest; neither figure is asserted here as the content of the June 2026 archives.

As in finding 1, `strategies` changed shape from a two-item sequence to a single scalar carrying both sentences; the content is unchanged.

### 3. `ethical_reviews[0].contact_person.affiliation` — missing affiliation (low)

**Audit position.** The Ravitsky entry omitted `affiliation` while the structurally parallel Bélisle-Pipon entry carried it. The bundle attests "Ravitsky V (University of Montreal)" in the author list of the same release record from which the ORCID was taken, and the entry's own caveat already discussed the affiliation/email-domain mismatch.

**Action: added, both records.** The reconciled record adds:

```
    affiliation:
    - name: University of Montreal
```

to `ethical_reviews[0].contact_person`. The value is attested in the bundle and already appears at `creators` for the same ORCID, so this is a consistency repair rather than a new claim. The existing `source_caveats` on that entry, which already notes that the stated affiliation and the email domain differ, was left unchanged and now reads correctly against a record that carries both.

### 4. `notes` — scope inference asserted as fact (low)

**Audit position.** The clause "these are project-level totals across all CM4AI data streams and are not counts for this release alone" is the record's own inference; the portal presents the Data Insights figures without stating their scope. The judgment belongs in `source_caveats`.

**Action: changed, both records.** The clause was removed from `notes`, which now reports the portal figures without characterizing their scope:

> The CM4AI project portal reports data holdings of 1,374 protein interactions, 53,788 immunofluorescent images, 7,023 total proteins investigated, 11,739 genes targeted and 21.4 TB of data volume.

A corresponding sentence was appended to the top-level `source_caveats` in both records:

> The Data Insights figures reproduced in `notes` are presented on the CM4AI project portal and on its Data Releases page without a stated scope; this record reads them as cumulative project-wide holdings across all CM4AI data streams rather than as counts for this release alone, but that reading is an inference and the portal does not state it.

The inference is preserved and now sits where trust annotations belong.

### 5. `human_subject_research.ethics_review_board` — records an absence (low)

**Audit position.** The value stated that no IRB or ethics committee is identified in the release record. That is a statement about what the documents do not contain, not a name of an ethics review board; the conforming response is omission.

**Action: removed, both records.** The key was deleted from `human_subject_research` in the full record and in the core record. `involves_human_subjects: false` and `regulatory_compliance` remain and carry the substantive fact; the two named ethics contacts remain under `ethical_reviews`. No information is lost by the removal.

### 6. `data_governance.notes` — planned Data Access Committee (low)

**Audit position.** The notes carry a forward-looking arrangement from the preprint. The audit observed that a plan in a governance slot risks being read as the operative process, while noting that the disclosure clause is what keeps it conforming.

**Action: retained, both records.** The value is unchanged in both files. The passage already marks the arrangement as planned in the tense the source uses — "will supervise … that is stated there as a planned arrangement" — and immediately follows it with the operative fact for this release: "All ten archives in this release are listed with public file access." The audit itself identified the disclosure as sufficient. Removing the sentence would drop attested project-level governance context without correcting any misstatement.

## Consistency between the two records

Every repair was applied identically in both files, and each repaired slot is one the core schema declares:

- `sampling_strategies` — present in both; caveats and scalar form match.
- `ethical_reviews[0].contact_person.affiliation` — added in both.
- `notes` and `source_caveats` — the same text in both.
- `human_subject_research.ethics_review_board` — absent from both.
- `data_governance.notes` — unchanged in both.

The core header now carries `# Phase 4 reconciliation: completed`, which was already present in the supplied core file and remains accurate after this phase.

## What was not changed

No factual value was added, altered, or removed beyond the six findings above. Identifiers, checksums, the ten-file inventory, license terms, creator roster, funders, limitations, biases, and the release-date conflict disclosures are byte-identical between the original and reconciled records. The `is_sample: false` boolean and the 200/523 figures were retained rather than deleted, on the ground that the evidence supports stating them with a caveat and that deletion would represent the bundle less faithfully than qualified inclusion.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `sampling_strategies[1].strategies` | retained | both | Content unchanged; the interpretive basis of the sibling boolean is now disclosed in `source_caveats` rather than the strategy text being altered. |
| `sampling_strategies[1].source_caveats` | changed | both | Rewritten to add the October 2025 attestation of the 11,739 figure and to state that `is_sample: false` is this record's reading of "genome-scale"/"whole-genome", not a stated fact. |
| `sampling_strategies[1].is_sample` | retained | both | Reading is defensible and now disclosed as a reading; deleting it would understate what the evidence supports. |
| `sampling_strategies[0].strategies` | retained | both | Figures kept; their scope and the conflicting count are now handled in a new sibling caveat. |
| `sampling_strategies[0].source_caveats` | added | both | New key disclosing that the 200-gene/523-protein figures describe the project's curated TNBC dataset rather than this release, and that 523 conflicts with the October 2025 figure of 464. |
| `ethical_reviews[0].contact_person.affiliation` | added | both | "Ravitsky V (University of Montreal)" is attested in the same release record that supplied the ORCID and already appears under `creators`; adds parity with the Bélisle-Pipon entry. |
| `notes` | changed | both | The scope-inference clause about project-level totals was removed; the portal figures are now reported without characterizing their scope. |
| `source_caveats` | changed | both | A sentence was appended stating that the Data Insights figures carry no stated scope and that reading them as project-wide totals is this record's inference. |
| `human_subject_research.ethics_review_board` | removed | both | Recorded the absence of the requested information rather than naming a board; the substantive facts remain in `involves_human_subjects`, `regulatory_compliance` and `ethical_reviews`. |
| `data_governance.notes` | retained | both | The planned Data Access Committee is already marked as planned in the source's tense and is immediately followed by the operative access fact for this release; the audit judged the disclosure sufficient. |