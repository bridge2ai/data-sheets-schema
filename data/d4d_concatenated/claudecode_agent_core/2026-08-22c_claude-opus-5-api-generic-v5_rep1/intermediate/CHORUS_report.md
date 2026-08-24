# CHoRUS D4D Reconciliation Report

**Project:** CHORUS
**Version label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep1
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Audit summary

The Phase 3 audit returned 24 findings: 4 high, 6 medium, 10 low, 4 informational. The high findings concerned two structural defects repeated in both records (misuse of `Creator.principal_investigator` for five leadership-team members; a `FundingMechanism` grant carrying only a resolver URL while stated grant facts sat in prose). The medium findings concerned an unsupported `was_directly_observed: true` on a retrospective chart extract and three slots present in the full record but omitted from the core record. Low and informational findings concerned enum and free-text `role` values, caveat wording, `ExternalResource` string construction, an inferred boolean, and naming variance.

---

## 2. Changes made

### 2.1 `creators` — five leadership-team members no longer asserted as principal investigators (HIGH, both records)

**Finding:** Azra Bihorac, Xiaoqian Jiang, Yulia Strekalova, Parisa Rashidi and Manlik Kwong were each placed in `principal_investigator`, a Person-ranged slot reserved for the PI. The bundle names only ROSENTHAL, ERIC S. as principal investigator of OT2OD032701; the webinar slide is titled "Bridge2AI CHoRUS Leadership Team" and says nothing about PI status.

**Change (full and core, identical):** The Rosenthal Creator object is unchanged — his PI status is directly attested by NIH RePORTER. In the other five Creator objects the `principal_investigator` key was removed. Each now carries `affiliations` (unchanged), a `notes` value naming the individual and the slide they appear on, and a `source_caveats` value recording that the person is a leadership-team member rather than a PI and that the Creator class declares no field for a named non-PI individual.

Example of the before/after shape:

```yaml
# before
- principal_investigator:
    name: "Azra Bihorac"
  affiliations:
    - name: "University of Florida"
  source_caveats: "Listed under 'Bridge2AI CHoRUS Leadership Team' …"

# after
- affiliations:
    - name: "University of Florida"
  notes: "Azra Bihorac, listed on the 'Bridge2AI CHoRUS Leadership Team' slide of the cohort-2 webinar."
  source_caveats: "Recorded as a leadership-team member rather than a principal investigator: …"
```

The names are retained — they are attested — but they are no longer carried in a slot that makes an unsupported role claim.

### 2.2 `acquisition_methods[0].was_directly_observed` — removed (MEDIUM, both records)

**Finding:** `was_directly_observed: true` was asserted for retrospective extraction of pre-existing hospital records, contradicting `direct_collection[0].is_direct: false` in the same full record and unsupported for a chart extract. Aggravated in core, which omitted `direct_collection` entirely.

**Change (full and core):** The `was_directly_observed` key was removed from the first acquisition method. `was_validated_verified: true` and the validation `notes` are retained. A `source_caveats` was added stating that the bundle describes retrospective extraction of records documented in the course of clinical care and does not state whether that counts as direct observation, so the flag is left unset. In the core record that caveat carries one additional sentence — that collection is site-mediated and retrospective rather than gathered from individuals for this project — because core does not carry `direct_collection` (see 3.2).

### 2.3 `splits` — added to the core record (MEDIUM, core)

**Finding:** The core record omitted `splits` although the full record populated it and the holdout test set is referenced in core `purposes`, `tasks` and `intended_uses`.

**Change (core only):** `splits` was added to the core record, verbatim from the full record: the holdout test set provisioned for external validation, with the caveat that the bundle does not state its size, partitioning, or access route. The full record's `splits` is unchanged.

### 2.4 `instances[2].counts` caveat — internal inconsistency resolved (LOW, both records)

**Finding:** The instance-level caveat said the two imaging figures "are not necessarily in conflict" while the top-level `source_caveats` presented them as a disagreement resolved by rank.

**Change (full and core):** Both caveats were rewritten to say the same thing. The instance-level caveat now states that the sources report imaging availability in different units, records both figures, notes that the higher-ranked figure is used as the count, and points to `known_limitations` for the webinar snapshot. The top-level `source_caveats` was changed from "disagree" to "differ" for the admissions figure, and its imaging sentence now names the two units explicitly and says the difference is recorded on the instance "rather than resolved."

### 2.5 `maintainers[*].role` — overstated enum values removed (LOW, both records)

**Finding:** All three Maintainer objects carried `role: academic_institution`, including the first (Ciera McCrary, an individual program manager) and second (two named individual access contacts).

**Change (full and core):** `role` was removed from the first two Maintainer objects, each of which gained a `source_caveats` explaining that no enum value is recorded because the bundle names individuals rather than a maintaining organization type. The third (the software-contributor collective) retains `role: academic_institution` and gained a caveat grounding that choice in the bundle's description of the CHoRUS Network as spanning 20 academic centers. The mgh.havard.edu transcription caveat on the first maintainer was preserved and folded into the expanded caveat.

### 2.6 `external_resources` — locator separated from gloss (LOW, both records)

**Finding:** Each ExternalResource packed a URL and a descriptive gloss into the single `external_resources` string using an em-dash.

**Change (full and core):** All five objects were split: `external_resources` now holds the locator alone, and the descriptive text moved to `notes`. The `www.bridge2ai.org/chorus` entry additionally notes that the address is reproduced as printed on the GitHub page (it is written there without a scheme).

### 2.7 `at_risk_populations.at_risk_groups_included` — caveat wording tightened (LOW, both records)

**Finding:** The boolean is inferred from the stated PICU and NICU admissions rather than asserted by the bundle; the original caveat said so using the word "inferred."

**Change (full and core):** The boolean is retained. The caveat was reworded from "Inclusion of at-risk groups is inferred from the stated PICU and NICU admissions" to "Inclusion of at-risk groups follows from the stated PICU and NICU admissions rather than from an explicit statement in the bundle." The remainder of the caveat (no assent, guardian consent, or minor-specific protections described) is unchanged.

### 2.8 `conforms_to_standard: OTHER` — referent made explicit (LOW, both records)

**Finding:** `OTHER` was included without the record stating which standards it stood for.

**Change (full and core):** No change to the enum list. A sentence was added to the top-level `source_caveats` stating that `OTHER` stands for the EDF+ and Persyst EEG formats and the OHNLP open-source note schema, which the enum does not name.

### 2.9 `created_by` — naming variance recorded (LOW, full)

**Finding:** "CHoRUS Consortium" is attested but the bundle also uses "CHoRUS Network," and NIH RePORTER names Massachusetts General Hospital as awardee.

**Change (full and core):** The value is unchanged. A sentence was added to the top-level `source_caveats` recording that the project is called the "CHoRUS Consortium" on chorus4ai.org and the "CHoRUS Network" on the GitHub organization page, and that `created_by` uses the former.

### 2.10 `funders[0]` — grant provenance annotated (HIGH, both records)

**Finding:** The Grant object carries only `id` (the NIH RePORTER URL) while the grant number, application ID, award amount and project period sit in `notes`.

**Change made (full and core):** A `source_caveats` was added to the FundingMechanism stating that the grant is identified by the RePORTER record URL because the bundle supplies no registered CURIE prefix for NIH awards, and that the award number, amount and period are carried in `notes` because the Grant range in this schema declares no fields for them.

**Change not made:** The `id` value and the `notes` content are unchanged. The schema digest supplied to this run lists `grants: Grant[]` as the range of `FundingMechanism.grants` but does not enumerate the fields of the `Grant` class beyond the statement that `id` is `uriorcurie` on every object listed. Without a field list I could not move the award number, amount or period into declared fields, and inventing keys is prohibited. The annotation records the limitation rather than concealing it. This finding is therefore **partially addressed**: the misplacement is documented, not repaired.

### 2.11 `direct_collection` — retained in full, compensated in core (MEDIUM, core)

**Finding:** `direct_collection` is present and evidence-supported in the full record but absent from core, removing the only explicit statement that data were not collected directly from individuals.

**Change:** The full record's `direct_collection` is unchanged. The core record still does not carry a `direct_collection` slot; instead, the substance was folded into the acquisition-method caveat described in 2.2 ("Collection is site-mediated and retrospective rather than gathered from individuals for this project"). The core schema is a reduced projection and I could not confirm from the supplied digest that `direct_collection` is available on `CoreDataset`; carrying the statement in a slot that is certainly present was the safer repair. The finding is therefore **addressed by compensation, not by adding the slot**.

---

## 3. Findings left as-is

### 3.1 `third_party_sharing` omitted from core (MEDIUM)

Comparing the two records: `third_party_sharing` remains present in the full record and remains absent from the core record. This finding was **not acted on**. Rationale: as with `direct_collection`, the supplied core-schema information does not confirm the slot's availability on `CoreDataset`, and the core record already conveys the controlled-access-plus-training-program distribution route through `license_and_use_terms`, `data_governance.access_review_process`, `intended_uses` and `existing_uses`. The full record retains the explicit statement.

### 3.2 `creators[*].affiliations[*]` carry `name` but no `id` (MEDIUM, flagged as no defect)

Unchanged. The audit itself noted this is acceptable under the evidence boundary: the bundle supplies no registry identifiers for any of the named organizations, and supplying one from outside knowledge is prohibited.

### 3.3 `data_collectors[*].role` free-text values (LOW)

Unchanged in both records. The four values ("data contributing centers", "data site manager", "clinical collaborator", "coordinating sub-teams") remain as written. The schema digest declares no enum on `DataCollector.role` — unlike `Maintainer.role`, whose permitted values are listed — so these are not validation defects, and the descriptors are grounded in the bundle's own terminology (Data Acquisition centers, data site managers, clinical collaborators, sub-teams).

### 3.4 Dataset `id` is a project website (INFO)

Unchanged in both records: `https://chorus4ai.org/`. The bundle supplies no DOI, accession, or repository identifier for the dataset itself, so no better-attested value exists. The audit raised this as informational only.

### 3.5 Core `source_caveats` abridgement (INFO)

The audit found the core abridgement permissible. In reconciliation the two top-level caveats were brought into alignment for the substantive edits (2.4, 2.8, 2.9), and the core version now also carries the full RePORTER typographical-error and truncated-sentence detail that the original core version had dropped. This is a convergence rather than a repair of a defect.

### 3.6 Core adds no content beyond full (INFO)

Verified again after reconciliation. Every core value is a verbatim or lightly extended projection of the corresponding full value; the only core-specific text is the additional sentence in the acquisition-method caveat described in 2.2, which restates full-record content from `direct_collection` rather than introducing new facts.

### 3.7 Header blocks and `conforms_to_class` (INFO)

Unchanged and correct: `Dataset` in the full record, `CoreDataset` in the core record; the core header retains `# Sources:` and `# Phase 4 reconciliation: completed`.

---

## 4. Referent

Both records describe one referent: the CHoRUS multi-center critical care dataset (the data collection), not the CHoRUS project, network, software organization, or training program. Facts about the project, GitHub organization and AIM-AHEAD training program appear only where they bear on the data — as funding, governance, access route, existing uses, maintenance, and external resources. This choice is held consistently across both records and is unchanged by reconciliation.

---

## 5. Outcome

| | |
|---|---|
| Findings acted on (changed) | 9 |
| Findings partially addressed (annotated, not repaired) | 2 (§2.10 grant fields, §2.11 core `direct_collection`) |
| Findings left as-is | 7 |
| High-severity findings fully repaired | 2 of 4 (the `creators` pair) |
| High-severity findings annotated only | 2 of 4 (the `funders` pair) |
| Records diverging in content after reconciliation | Full retains `direct_collection` and `third_party_sharing`; core does not. No other content divergence. |

Reconciliation outcome: **completed with two documented residuals** — the FundingMechanism grant identifier, which could not be restructured without a field list for the `Grant` range, and `third_party_sharing`/`direct_collection` in core, which were compensated in prose rather than added as slots.