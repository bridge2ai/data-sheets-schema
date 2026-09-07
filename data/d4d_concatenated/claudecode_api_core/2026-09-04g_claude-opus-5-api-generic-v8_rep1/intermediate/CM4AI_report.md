# Phase 4 Reconciliation Report — CM4AI

## Scope

Phase 3 returned six findings, all at **low** severity, against the full record.
No high or medium findings were raised. The audit summary confirms no
unsupported factual claim, no enum violation, no prose-for-list shape error, no
fabricated external identifier, and no plan or superseded-release fact presented
as the referent's current state.

Four of the six findings were acted on. Two were left as-is, for reasons given
below.

---

## Findings acted on

### 1. `human_subject_research.ethics_review_board` — value recorded an absence

**Audit:** the value read "Ethical review for the release is handled by named
CM4AI ethics contacts rather than by a named institutional review board; no IRB
or ethics committee is identified in the release record." That is a statement
that the requested information is not available, not the name of an ethics
review board.

**Action:** the key was removed. In the reconciled full record,
`human_subject_research` now carries only `involves_human_subjects: false` and
`regulatory_compliance`. The same removal was applied to the core record, which
declares `human_subject_research`.

**Why:** the uniform rules require that a slot be populated with the information
the field asks for, and that a value recording that information is pending or
absent has not answered the field. The substantive fact —
`involves_human_subjects: false` — is already carried, and the named ethics
contacts are already carried in `ethical_reviews` with their own
`contact_person` objects. Nothing was lost by the removal.

### 2. `ethical_reviews[0].contact_person.affiliation` — missing affiliation

**Audit:** the Ravitsky entry omitted `affiliation` while the structurally
parallel Bélisle-Pipon entry populated it, and the bundle attests "Ravitsky V
(University of Montreal)" in the author list of the same release record from
which the ORCID was taken.

**Action:** `affiliation: [{name: University of Montreal}]` was added to
`ethical_reviews[0].contact_person` in both records. The existing
`source_caveats` on that entry, which already discloses the mismatch between the
University of Montreal affiliation and the thehastingscenter.org email domain,
was left unchanged — it now explains the value that is present rather than
explaining a value the record withheld.

**Why:** the affiliation is attested in the bundle in the same passage that
supplies the ORCID, and the object-range rules direct that a declared field be
populated where the evidence answers it. The two entries are now consistent.

### 3. `notes` — scope inference asserted as fact

**Audit:** the clause "these are project-level totals across all CM4AI data
streams and are not counts for this release alone" is the record's own
inference; the portal presents the Data Insights figures without stating their
scope.

**Action:** the clause was deleted from `notes` in both records. The figures
themselves (1,374 protein interactions; 53,788 immunofluorescent images; 7,023
total proteins investigated; 11,739 genes targeted; 21.4 TB) remain, now
attributed simply as what the portal reports. A new sentence was appended to
the top-level `source_caveats` in both records recording that the portal
presents these figures without a stated scope, that this record reads them as
cumulative project-wide holdings rather than as counts for this release, and
that the reading is an inference the portal does not state.

**Why:** `source_caveats` is defined as commentary on the evidence behind the
sibling slots' values — source conflicts, questions the source material leaves
unanswered. A scope judgment the source does not support is exactly that. Moving
it preserves the judgment for a reader while removing it from the position of an
asserted fact.

### 4. `sampling_strategies[0]` — undisclosed conflict in the protein count

**Audit:** the 200-gene and 523-protein figures describe the project's curated
TNBC dataset generally, not necessarily this release, and the portal's 523
conflicts with the 464 the October 2025 release gives for same-named IF
archives. The conflict is disclosed for `file_collections` but not here.

**Action:** a `source_caveats` key was added to `sampling_strategies[0]` in both
records, recording that the figures are given on the portal's flagship-dataset
panel as a description of the project's curated TNBC dataset generally, that the
June 2026 file listing carries no gene or protein counts, that 523 conflicts
with the October 2025 page's 464 for same-named archives, and that neither
figure is asserted as the content of the June 2026 archives.

**Why:** the disagreeing sources — the tier-2 project portal and the tier-1
superseded October 2025 release — do not resolve against each other cleanly for
a figure neither states about this release, so the correct action is to
represent the disagreement rather than select a value. The strategy text itself
was left unchanged, since it already attributes the figures to the portal.

### 5. `sampling_strategies[1].strategies` — interpretive `is_sample: false`

**Audit:** the `is_sample: false` assertion is an interpretation of
"genome-scale" rather than a stated fact; the existing caveat partially
discloses this but the boolean itself is not directly attested.

**Action:** the existing `source_caveats` on `sampling_strategies[1]` was
rewritten in both records. It now cites the October 2025 release page's
description of the atlas as mapping phenotypes associated with 11,739 targeted
genes alongside the portal's "whole-genome" characterization, and states
explicitly that the `is_sample: false` value is this record's reading of
"expressed genome-scale" and "whole-genome" as indicating comprehensive rather
than sampled coverage, and that no source states in terms that the gene set is
not a sample.

**Why:** the boolean is a defensible reading of two attested characterizations,
and removing it would discard information a reader can use. Naming it as a
reading, at the object that carries it, is the disclosure the guard asks for.
The boolean itself was retained.

---

## Findings left as-is

### 6. `data_governance.notes` — planned Data Access Committee

**Audit:** the notes carry a forward-looking arrangement in a slot describing
operative governance; the audit itself observes that the plan is correctly
marked as a plan and attributed to the preprint, and that "the disclosure clause
is what keeps it conforming."

**Action:** none. The `data_governance.notes` value is byte-identical between
the original and reconciled records in both files.

**Why:** the tense rule requires that a plan be stated as such or omitted. This
value states it as such — "will supervise," "that is stated there as a planned
arrangement," attributed to the preprint — and the same notes field immediately
records the operative fact that all ten archives are listed with public file
access. The audit found no defect to repair, only a risk of misreading that the
existing text already forecloses. Removing the sentence would lose the reader a
documented future arrangement for no gain in accuracy.

---

## Cross-record consistency

Every change above was applied to both records where the core schema declares
the affected slot. All four changed slots — `human_subject_research`,
`ethical_reviews`, `notes`/`source_caveats`, and `sampling_strategies` — are
declared in the core schema and are present in the core record, so all four
edits are mirrored there. The core record's `# Phase 4 reconciliation:
completed` line was written only after these edits were made.

The referent is unchanged: both records describe the June 2026 Data Release
(Beta), `doi:10.18130/V3/HIGT4C`, Dataverse version 2.0, the highest-ranked
non-superseded release in the bundle.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `human_subject_research.ethics_review_board` | removed | both | Value recorded the absence of the requested information rather than naming a review board; the substantive fact is carried by `involves_human_subjects` and the named contacts by `ethical_reviews`. |
| `human_subject_research.involves_human_subjects` | retained | both | Directly attested ("Human Subjects: No"); unaffected by the removal of its sibling key. |
| `human_subject_research.regulatory_compliance` | retained | both | Directly attested; unaffected by the removal of its sibling key. |
| `ethical_reviews[0].contact_person.affiliation` | added | both | "Ravitsky V (University of Montreal)" is attested in the same release-record author list that supplies the ORCID; brings the entry into line with its structural twin. |
| `ethical_reviews[0].source_caveats` | retained | both | Already discloses the affiliation/email-domain mismatch; now explains a value that is present rather than one withheld. |
| `notes` | changed | both | Deleted the unsupported scope clause about project-level totals; the portal figures themselves remain as reported. |
| `source_caveats` | changed | both | Appended the Data Insights scope judgment moved out of `notes`, marked as this record's inference and noted as unstated by the portal. |
| `sampling_strategies[0].source_caveats` | added | both | Records that the 200-gene and 523-protein figures describe the project's curated TNBC dataset generally, and that 523 conflicts with the October 2025 page's 464 for same-named archives. |
| `sampling_strategies[0].strategies` | retained | both | Already attributes the figures to the CM4AI project portal; the new sibling caveat supplies the scope and conflict disclosure. |
| `sampling_strategies[1].source_caveats` | changed | both | Rewritten to name `is_sample: false` as this record's reading of "expressed genome-scale" and "whole-genome," and to state that no source asserts the gene set is not a sample. |
| `sampling_strategies[1].is_sample` | retained | both | A defensible reading of two attested characterizations; retained with its interpretive basis now disclosed in the sibling caveat. |
| `data_governance.notes` | retained | both | The planned Data Access Committee is already stated as a plan and attributed to the preprint, and the operative public-access fact sits beside it; the audit identified no defect to repair. |
| `file_collections[1].source_caveats` | retained | full | Already discloses the 464-protein figure as an October 2025 statement not asserted for this release; `file_collections` is not declared in the core schema. |