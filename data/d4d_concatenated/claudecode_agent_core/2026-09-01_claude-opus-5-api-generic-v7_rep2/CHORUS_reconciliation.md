# CHoRUS D4D Reconciliation Report

**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep2`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Arm:** BASELINE (input documents only)
**Bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (md5 `9b2ef4b65d67957f79362266cab0bc7a`)

---

## 1. Audit summary

The Phase 3 audit returned 15 findings against the full record: 1 high, 5 moderate, 9 low. No schema-shape defects were reported — enums, CURIE forms, `uri`-ranged values, integer counts and list cardinality all conformed. The dominant defect class was **unsupported role or scope assertion**: placing people in roles the bundle does not give them, generalizing a training-program enrollment procedure into dataset-wide governance, and inferring organizational accountability and geography from adjacent facts. Two structural findings (award identifiers in free text rather than the declared `grants` field) and two supportable omissions (`machine_annotation_tools`, `external_resources`) were also raised.

Because the core record is a projection of the full record, every change made to the full record was carried through to the core record wherever the affected slot appears there.

---

## 2. Findings addressed, with the change made

### 2.1 `creators[1..5].principal_investigator` — high

**Finding:** five Leadership Team members were asserted as principal investigators, contradicting NIH RePORTER, which names Rosenthal alone.

**Change (both records):** the `principal_investigator` key was removed from creators 2–6. Each of those entries now carries only `affiliations` plus a `notes` value naming the person and their attested role — for example `notes: Azra Bihorac, member of the Bridge2AI CHoRUS Leadership Team.` Creator 1 retains `principal_investigator: Eric S. Rosenthal` and gains a `notes` value recording both the RePORTER PI designation and the Leadership Team listing.

**Also changed:** `principal_investigator` in the original held an object (`name: Eric S. Rosenthal`); in the reconciled records it holds the bare string `Eric S. Rosenthal`.

**Related — finding 2.13, creators' repeated caveats (low):** the five identical `source_caveats` sentences are gone from the creator entries. The disagreement is now stated once, at record level, in `source_caveats`: *"NIH RePORTER names Eric S. Rosenthal as the sole principal investigator of OT2OD032701; the five further individuals recorded as creators are named in the cohort 2 webinar only as members of the Bridge2AI CHoRUS Leadership Team, and no principal investigator role is asserted for them here."*

### 2.2 `data_governance.access_review_process` — moderate

**Finding:** program-specific enrollment steps presented as dataset-wide governance.

**Change (both records):** rewritten. The dataset-wide facts (controlled access for every type, cloud enclave, notes held locally) now lead. The registration form, licensing agreement, compute-provisioning email and `.edu` requirement are all explicitly scoped: *"For the AIM-AHEAD Bridge2AI for Clinical Care Training Program (cohort 2), participants fill out a registration form…"* and *"That program also requires a '.edu' email address…"* The `source_caveats` on the object now states that these requirements *"are attested only for participants in the AIM-AHEAD Bridge2AI for Clinical Care Training Program and are described as such rather than as dataset-wide policy."*

### 2.3 `license_and_use_terms.license_terms` — moderate

**Finding:** same over-generalization.

**Change (both records):** rewritten to open *"Participants in the AIM-AHEAD Bridge2AI for Clinical Care Training Program must sign a licensing agreement, included in the program registration form…"* The `source_caveats` gained a leading sentence: *"The bundle states no general license for the data themselves and no access terms outside the training program context."*

### 2.4 `data_governance.committee_members` — moderate

**Finding:** GitHub access-request contacts filed as members of a committee the bundle does not establish.

**Change (both records):** `committee_members` was removed. The named contact now sits in `committee_contact` as the string `Jared Houghtaling (jared.houghtaling@tuftsmedicine.org)`, and both addresses are recorded in the object's `notes`: *"The chorus-ai GitHub organization page gives two access request contacts: dbold@emory.edu and jared.houghtaling@tuftsmedicine.org."* The `mailto:` identifiers are gone.

### 2.5 `funders[0].notes` — moderate

**Finding:** award identifiers packed into free text while the declared `grants` field stood empty.

**Change (both records):** a `grants` list was added with one Grant entry — `id: https://reporter.nih.gov/project-details/10472824`, `name: OT2OD032701`, and a `description` carrying the project number, application ID, awardee, FY2022 amount and project period. `notes` now retains only the NIH disclaimer about views expressed on the website.

### 2.6 `data_governance.accountable_organization` — moderate

**Finding:** MGH as accountable organization was inferred from the RePORTER awardee field.

**Change (both records):** the `accountable_organization` key was removed. The `source_caveats` now opens *"The bundle names no data access committee, no committee membership, and no organization formally accountable for the data over time."*

### 2.7 `preprocessing_strategies[4]` — low

**Finding:** UF-Geocoding and the NIH abstract's "distance to the nearest hospital" were joined into a causal claim the bundle does not make.

**Change (both records):** that fifth entry was removed. `preprocessing_strategies` now has four entries. The geographic-context material survives only where the bundle supports it — in `intended_uses` (Equity and social determinants research) and in the `external_resources` repository listing, which names UF-Geocoding as one of the repositories without asserting it was applied.

### 2.8 `known_limitations[2].limitation_description` — low

**Finding:** "in the United States" was unsupported.

**Change (both records):** the phrase was removed; the text now reads *"at 14 contributing hospitals, and is available only under controlled access."* The trailing clause about registered users holding an institutional email address was also dropped, since that requirement is program-scoped (see 2.2/2.3).

### 2.9 `maintainers[0].role` — low

**Finding:** `academic_institution` approximated an entity the bundle does not characterize.

**Change (both records):** the `role` key was removed from the first maintainer. `maintainer_details` is unchanged. The second maintainer entry never carried a `role` and still does not.

### 2.10 `description` — low

**Finding:** "adult, pediatric, and neonatal intensive care units" expanded the source's "ICU, PICU, and NICU."

**Change (both records):** `description` now reads *"50,000 patient admissions from intensive care units (ICU, PICU, and NICU)."* The same expansion was corrected in `subpopulations[0].identification`, which now reads *"Admissions in the released dataset are drawn from ICU, PICU, and NICU."*

### 2.11 `machine_annotation_tools` — low

**Finding:** flagged as a possible omission for the OHNLP toolkit.

**Change (both records):** the slot was added, with `tools: [OHNLP toolkit]` and a `tool_descriptions` value stating that clinical notes are extracted and tokenized with the toolkit and follow the OHNLP open-source schema. Judged supportable: the webinar modality table names OHNLP as both the tool and the standard for the notes modality.

### 2.12 `external_resources` — low

**Finding:** flagged as a possible omission.

**Change (both records):** the slot was added with two entries — the chorus-ai GitHub organization (`id: https://github.com/chorus-ai`), with a description enumerating the repositories the bundle names, and the CHoRUS page on the Bridge2AI website (`id: https://www.bridge2ai.org/chorus`), attested in the GitHub contact block.

### 2.14 `notes` / `status` — low

**Finding:** top-level `notes` held only the site banner, which bears on availability and overlaps `status`.

**Change (both records):** top-level `notes` was removed. The banner quotation was folded into `status`, which now reads *"Partially released under controlled access; data acquisition and curation ongoing. The project website carries the banner 'This repoitory is under review for potential modification in compliance with Administration directives.'"* The banner text keeps its source's spelling, including the typo.

---

## 3. Findings left as-is

### `at_risk_populations.at_risk_groups_included` — low (finding 2.7 in the audit's numbering)

Left as-is. The slot is unchanged in both records: `at_risk_groups_included: true`, with the same `notes` and the same `source_caveats` disclosing that the boolean rests only on the ICU/PICU/NICU statement and that no assent, guardian consent or special protections are described. Neonatal and pediatric ICU admissions are minors on any reading, and `human_subject_research.special_populations` already names them from the same evidence; removing the boolean while retaining the special-populations list would have made the two objects disagree. The caveat carries the weakness.

---

## 4. Incidental change not driven by a finding

`sampling_strategies[0].strategies` was a two-item list in the original and is a single joined string in the reconciled records, carrying the same two sentences. This is a formatting difference only; no content was added or dropped.

---

## 5. Referent

`Dataset` admits one referent. Both records describe **the CHoRUS multicenter critical care dataset** — the collection of ICU/PICU/NICU admissions and their EHR, imaging, waveform, EEG and tokenized-note modalities — not the CHoRUS project, not the chorus-ai software organization, and not the AIM-AHEAD training program. The reconciliation sharpened this boundary in three places: governance and license terms are now scoped to the training program rather than stated as dataset policy; the software repositories moved from prose into `external_resources`, where they are referenced rather than described as dataset content; and the geocoding-tool inference was removed because it asserted a project capability as a dataset transformation. This referent is held consistently across both records.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots | 47 | 46 |
| Validated | yes | yes |

Slots removed relative to the originals: `notes` (folded into `status`) in both. Slots added: `machine_annotation_tools`, `external_resources` in both. Nested removals: `creators[1..5].principal_investigator`, `data_governance.committee_members`, `data_governance.accountable_organization`, `maintainers[0].role`, `preprocessing_strategies[4]`. Nested additions: `funders[0].grants`, `data_governance.committee_contact`, `data_governance.notes`, `creators[*].notes`.

Core-full divergence is confined to the projection itself: the core record omits the full record's `splits`, `direct_collection`, `third_party_sharing` and `id`/`name` duplication is as emitted, and carries `conforms_to_class: CoreDataset` with the core schema path. All reconciled values are identical in wording between the two records wherever a slot appears in both.

Reconciliation outcome: **all 15 findings resolved — 14 by change, 1 by documented retention.**