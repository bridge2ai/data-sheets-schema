# CHoRUS D4D Reconciliation Report

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Arm:** BASELINE (declared input bundle only)
**Referent held constant across both records:** the CHoRUS multi-center, multi-modal critical care dataset produced by the Bridge2AI CHoRUS data generation project — not the CHoRUS project, network, or software ecosystem, which appear only as context in `data_collectors`, `maintainers`, and `external_resources`.

---

## 1. Audit summary

The audit returned 24 findings: 4 high, 5 medium, 11 low, 4 informational. The high findings concerned two recurring structural defects (misuse of `Creator.principal_investigator`, and grant identity carried in prose rather than declared fields), each present in both records. Medium findings concerned an unsupported acquisition boolean and three core-only omissions. Low findings concerned internal caveat inconsistency, ad hoc and overstated role values, prose packed into a string-ranged list slot, and one acknowledged inference. Informational findings recorded that no defect existed.

---

## 2. Changes made

### 2.1 `creators` — `principal_investigator` misuse (high, both records)

**Finding:** five of six Creator objects placed leadership-team members (Bihorac, Jiang, Strekalova, Rashidi, Kwong) in `principal_investigator`, a Person-ranged slot the bundle supports only for Eric S. Rosenthal.

**Change, both records:** the five non-PI Creator objects no longer carry `principal_investigator`. Each now carries `affiliations` (unchanged), plus the individual's name in `notes` and a `source_caveats` explaining that they are recorded as leadership-team members rather than principal investigators. The Rosenthal object retains `principal_investigator`.

**Second change to the same slot:** `principal_investigator` was additionally converted from a nested object (`principal_investigator: {name: "Eric S. Rosenthal"}`) to the scalar string `"Eric S. Rosenthal"`. The audit did not raise this; it follows from the v4 rule that a scalar-ranged slot takes the identifier of its referent rather than the object. Note that the schema digest declares `Creator.principal_investigator` with range `Person`, so this change substitutes one shape for another rather than clearly correcting an error — it is flagged here as a judgment call, not a certainty.

**Note on the caveat text:** the reconciled caveats state that "the Creator class declares no field for a named non-PI individual." The schema digest lists Creator's accepted slots as `affiliations`, `credit_roles`, `notes`, `principal_investigator`, `source_caveats` (plus `id` and `used_software`). No name-bearing slot for a non-PI contributor appears in that list, so the statement is supported by the digest as given.

### 2.2 `funders[0].grants[0]` — grant identity in prose (high, both records)

**Finding:** the Grant object carried only `id` (a NIH RePORTER resolver URL) while award number, application ID, amount, and project period sat in free-text `notes`.

**Change, both records:** the substance was *not* relocated into declared fields, because the schema digest gives no expansion of the `Grant` class and therefore names no fields for grant number, amount, or period. What changed instead is that a `source_caveats` was added to the FundingMechanism object explaining (a) why the RePORTER URL is used as the identifier — no registered CURIE prefix for NIH awards is supplied by the bundle — and (b) why the award details remain in `notes`. This is a documentation change, not a structural fix. The audit's underlying complaint about prose-carried identity is therefore **partially unaddressed**, and that is stated plainly rather than papered over.

### 2.3 `acquisition_methods[0].was_directly_observed` (medium, both records)

**Finding:** `was_directly_observed: true` for a retrospective chart extract, contradicting `direct_collection[0].is_direct: false` in the full record and standing unqualified in the core record.

**Change, both records:** `was_directly_observed` was removed from the first InstanceAcquisition object. `was_validated_verified: true` was retained. A `source_caveats` was added stating that the bundle does not establish whether retrospectively extracted clinical documentation counts as directly observed for this dataset, so the flag is left unset. In the core record the same caveat additionally carries the sentence that collection is site-mediated and retrospective rather than gathered from individuals for this project — the substance the core record lacked because it omits `direct_collection`.

### 2.4 Core-only omissions (medium)

- **`direct_collection`** — the audit found it omitted from core. It remains omitted in the reconciled core record. The substance was instead folded into the `acquisition_methods[0].source_caveats` sentence described above. This is a partial rather than a full remedy: a reader of the core record now learns that collection was retrospective and site-mediated, but the `is_direct: false` boolean is still absent.
- **`splits`** — the audit found it omitted from core while the holdout test set is referenced in core `purposes`, `tasks`, and `intended_uses`. It **remains omitted** in the reconciled core record. See §3.
- **`third_party_sharing`** — the audit found it omitted from core. It **remains omitted**. See §3.

### 2.5 `instances[2]` caveat inconsistency (low, both records)

**Finding:** the instance-level caveat said the two imaging figures "are not necessarily in conflict" while the top-level `source_caveats` presented them as a disagreement resolved by rank.

**Change, both records:** the instance-level caveat was rewritten to open "The two sources report imaging availability in different units," dropping the "not necessarily in conflict" phrasing, and now records where the webinar figure went (`known_limitations`). The top-level caveat was correspondingly rewritten: "disagree" became "differ" for the admissions figure, and the imaging sentence now reads that the two sources report availability "in different units (admissions with radiology data versus images available), and that difference is recorded on the relevant instance rather than resolved." The two statements now characterize the same evidence the same way.

### 2.6 `conforms_to_standard: OTHER` left implicit (low, full record)

**Change, both records:** a sentence was added to the top-level `source_caveats` stating that `OTHER` stands for the EDF+ and Persyst EEG formats and the OHNLP open-source note schema. The enum value itself is unchanged.

### 2.7 `maintainers[*].role` overstated (low, both records)

**Finding:** all three Maintainer objects carried `role: academic_institution`, including two that describe individuals.

**Change, both records:** `role` was removed from the first two Maintainer objects (Ciera McCrary; the two access-request contacts), each gaining a `source_caveats` noting that no enum value is recorded because the bundle describes individuals rather than a maintaining organization type. The third object (the software-contributor collective) retains `role: academic_institution` and gained a caveat justifying it against the "20 academic centers" description.

### 2.8 `external_resources[*]` URL-plus-gloss strings (low, both records)

**Finding:** each ExternalResource packed a URL and a descriptive gloss into one `external_resources` string separated by an em-dash.

**Change, both records:** every ExternalResource object was restructured. `external_resources` now holds a single-element list containing the bare URL, and the gloss moved to `notes`. The `www.bridge2ai.org/chorus` entry gained an explicit note that the address is reproduced as printed in the GitHub contact section.

### 2.9 `at_risk_populations.at_risk_groups_included` inference (low, both records)

**Change, both records:** the boolean `true` was retained. The `source_caveats` wording changed from "is inferred from the stated PICU and NICU admissions" to "follows from the stated PICU and NICU admissions rather than from an explicit statement in the bundle." This sharpens the disclosure without altering the claim.

### 2.10 `created_by` variant naming (low, full record)

**Change, both records:** `created_by: "CHoRUS Consortium"` is unchanged. A sentence was added to the top-level `source_caveats` recording that chorus4ai.org uses "CHoRUS Consortium" while the GitHub organization page uses "CHoRUS Network," and that the former was chosen.

### 2.11 `existing_uses[*].examples` shape (not raised by the audit)

In both original records `examples` held a bare string; in both reconciled records it holds a single-element list. This is a shape normalization consistent with how `intended_uses[2].examples` was already written; no factual content changed.

### 2.12 Full-record `source_caveats` — RePORTER transcription detail

The full record's original caveat quoted the RePORTER typo and truncated sentence in full; the core record abridged this. In the reconciled records **both** now carry the full quotation, so the two are aligned on this point.

---

## 3. Left as-is, and why

| Finding | Record | Disposition |
|---|---|---|
| `creators[*].affiliations[*]` carry `name` but no `id` (medium) | full | Left as-is. The audit itself noted this is acceptable under the evidence boundary; the bundle supplies no registry identifiers, and supplying one from outside knowledge is prohibited. |
| `splits` omitted from core (medium) | core | **Left as-is.** The slot is still absent from the reconciled core record. This is a genuine residual gap: the holdout test set is evidenced in the bundle and referenced elsewhere in the core record. It was not reinstated. |
| `third_party_sharing` omitted from core (medium) | core | **Left as-is.** Still absent from the reconciled core record. Also a residual gap. |
| `direct_collection` omitted from core (medium) | core | Partially addressed only — see §2.4. The slot itself remains absent. |
| Grant fields in prose (high) | both | Partially addressed only — see §2.2. The `notes` block is unchanged; a caveat was added around it. |
| `data_collectors[*].role` free-text values (low) | full | Left as-is. All four values ("data contributing centers", "data site manager", "clinical collaborator", "coordinating sub-teams") are unchanged in both records. The schema digest lists no enum constraint on `DataCollector.role`, and the audit confirmed this is not a validation defect. |
| `id` is a project website rather than a dataset identifier (info) | both | Left as-is (`https://chorus4ai.org/`). The bundle supplies no DOI, accession, or repository identifier for the dataset. |
| Core `source_caveats` abridgement (info) | core | Superseded: the core caveat is no longer an abridgement of the full one — both now carry identical text including the RePORTER transcription detail. |
| `conforms_to_class` differentiation; header blocks (info) | both | Left as-is; already correct. `Dataset` / `CoreDataset` respectively, with the core header carrying `# Sources:` and `# Phase 4 reconciliation: completed`. |
| No core content absent from full (info) | core | Left as-is; the property still holds. Every reconciled core value has a full-record counterpart. |

---

## 4. Cross-record consistency after reconciliation

The two records now agree on: the top-level `source_caveats` text, the six-Creator structure and its caveats, the FundingMechanism caveat, the `acquisition_methods` shape (with the core caveat carrying one extra sentence covering the omitted `direct_collection`), the `instances[2]` caveat, all three `maintainers` objects, all five `external_resources` objects, and the `at_risk_populations` caveat. The full record continues to carry `direct_collection`, `splits`, and `third_party_sharing`, which the core record does not.

---

## 5. Outcome

Reconciliation completed. Of the 4 high findings, 2 (the `creators` pair) were structurally corrected in both records; 2 (the `funders` pair) received documentation rather than structure and remain partially open. Of the 5 medium findings, 2 (`was_directly_observed`) were corrected, 1 (`direct_collection` in core) was partially compensated, and 2 (`splits`, `third_party_sharing` in core) remain open. All 11 low findings were either corrected or explicitly justified. No new factual content was introduced in either record during reconciliation; every change was a relocation, a removal, or an added provenance caveat drawn from material already present in the declared bundle.