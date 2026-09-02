# Reconciliation Report — AI_READI

**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep1`
**Arm:** BASELINE (input documents only)
**Bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 `8abd7bf5389b562b95794d656af19392`)
**Records:** full (`Dataset`) and core (`CoreDataset`), the latter derived by projection from the full record.

---

## 1. Scope of the audit

Phase 3 returned fifty findings against the full record. Twelve were graded high, twenty-six medium, twelve low. A substantial fraction were confirmations rather than defects — arithmetic checks that passed, identifier forms that were already correct, omissions that the prefer-omission rule endorses. This report addresses the findings that led to changes and, separately, the findings that were considered and left alone.

The declared referent is unchanged: the record describes **version 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project** (DOI `10.60775/fairhub.3`), not the AI-READI study as a whole and not the release series. Both records hold to that choice.

---

## 2. Changes made

### 2.1 `creators` — organizational creator restored to the name-bearing position (finding: high)

**Was:** a single `Creator` whose `affiliations[0].name` read `AI-READI Consortium` with nothing else populated, and whose `principal_investigator` named Aaron Y. Lee.

**Now:** the same `Creator`, but `affiliations[0]` carries a `description` establishing that the AI-READI Consortium is the organizational creator of record, quoting FAIRhub's `nameType: Organizational` and the RO-Crate author/publisher fields. The `source_caveats` was rewritten to state explicitly that the Consortium is named here as the creating organization, and that Aaron Y. Lee is one of sixteen individuals FAIRhub lists with the role "Study Principal Investigator" — he appears in this slot as the responsible-party PI, not as a sole dataset creator.

**Reasoning:** the audit was right that the previous shape demoted the creator into its own affiliation slot. The `Creator` class as digested does not declare a `name` slot, so the organizational identity could not simply be moved up; what it does declare is `affiliations` (range `Organization[]`), and `Organization` accepts `name` and `description`. Making the affiliation entry carry an explicit statement of its role, plus the caveat, is the available repair within the declared shape. The sixteen-PI point from finding 2.1's companion (medium, `creators` collapsed) is addressed in the same caveat rather than by emitting sixteen `Creator` objects — FAIRhub records one creator, and multiplying it would misrepresent the source.

### 2.2 `data_governance.committee_name` — composed name replaced with a verbatim one (finding: high)

**Was:** `AI-READI Data Access Committee` — a name neither source uses.

**Now:** `Data Access Committee`, the tier-3 BMJ Open wording, verbatim. The `source_caveats` was rewritten to say that the bundle names two bodies and the record reproduces both rather than composing one: the tier-1 RO-Crate `dataGovernanceCommittee` value is the "AI-READI Consortium" (the consortium as a whole, not a named access committee), and the tier-3 protocol names a "Data Access Committee".

**Reasoning:** the audit's objection was exact — an entity asserted as named that no source names. The tier ranking cannot resolve this because the two sources are not describing the same body; one names the consortium, the other names a committee within the project. Reproducing both is what the disagreement rule requires.

### 2.3 `data_governance.committee_contact` — populated (finding: medium, supported omission)

**Added:** a `Person` with `id: ORCID:0000-0002-7452-1648`, `name: Aaron Lee`, `email: contact@aireadi.org`, from the FAIRhub `centralContactList` block. The prose pointer to the contact page remains in `stewardship_roles`.

### 2.4 `is_deidentified.identifiable_elements_present` — removed (finding: high, contradiction)

**Was:** `identifiable_elements_present: false`.

**Now:** the key is absent. `deidentification_details` was expanded to reproduce the FAIRhub flags individually — `deIdentDirect: true`, `deIdentHIPAA: true`, `deIdentDates: false`, `deIdentNonarr: false`, `deIdentKAnon: false` — alongside the FAIRhub explanation and the RO-Crate `deidentified: true`. The `source_caveats` now names those flags directly and states that the boolean is omitted because two equal-rank tier-1 sources cannot settle it.

**Reasoning:** the audit found the boolean asserting the opposite of two explicit tier-1 flags. Both remedies it offered were available; omission was chosen because the sources are of the same rank, which the disagreement rule says the ranking cannot decide.

### 2.5 `acquisition_methods[0].was_inferred_derived` — flipped to `true` (finding: medium, overstatement)

**Was:** `false`. **Now:** `true`, with `acquisition_details` extended to enumerate the derived values: BMI and waist-hip ratio calculated from measurements; LDL cholesterol, total globulin and A/G ratio marked "(calculated)" in the laboratory table; the Mars log CS score computed from the error count; Garmin sleep-phase and stress values as device-derived indices.

Three new `variables` entries were added to carry the same facts in structured form — `body_mass_index`, `waist_hip_ratio` and `ldl_cholesterol`, each with a `derivation` — and `derivation` was added to the existing `sleep`, `stress` and `contrast_sensitivity_log_cs` entries.

### 2.6 `sampling_strategies[0].is_sample` — set to `true` (finding: medium, non-conflict)

**Was:** unset, with a caveat asserting a conflict between "contains all possible instances" and "Non-Probability Sample". **Now:** `is_sample: true`, and the caveat rewritten to state that the two are compatible: the release is a complete census of the participants enrolled by the cut-off, and that cohort is a non-probability sample of the study base.

### 2.7 `instances[0]` — substrate and missing-information populated (findings: high and high)

- `data_substrate: B2AI_SUBSTRATE:11` (DICOM) added, with a caveat naming the other equally-attested substrates (CSV, JSON, TSV, waveform data, time-series data) and explaining that DICOM was chosen because it covers the four retinal imaging datatypes that dominate the release by files and bytes. The same caveat records that `data_topic` faced the same forced single choice.
- `missing_information` added as a one-entry `MissingInfo[]` carrying the modality-availability statement and its causes. This duplicates `missing_data_documentation` at the top level, which the audit noted; the instance-level slot is the one declared for exactly this fact.

### 2.8 `extension_mechanism` — populated (finding: high, supported omission)

**Added:** `extension_details` recording that there is currently no mechanism for others to extend or augment the dataset outside the project team, attributed to the healthsheet question it answers.

### 2.9 `discouraged_uses` and `data_protection_impacts` — populated (findings: medium each)

- `discouraged_uses[0].discouragement_details` records that the healthsheet answers the discouraged-use question by pointing at the license, and notes that the specific restrictions live in `prohibited_uses` because the bundle draws no line between the two categories.
- `data_protection_impacts[0].impact_details` records that no DPIA has been conducted — a positive statement about an absence, which the audit judged borderline and which is now carried.

### 2.10 `file_collections` — root metadata collection added, per-directory standard prose restored (findings: medium and medium)

A tenth entry, `doi:10.60775/fairhub.3#root_metadata`, was added: the nine root-level CDS metadata files, with `file_count: 9`, `collection_type: metadata`, `conforms_to_standard: [CDS]` and a `source_caveats` explaining that it accounts for the 9-file and 420,614-byte shortfall between the directory sums and the declared totals. `total_bytes` is omitted because the bundle does not state it.

Each of the nine datatype entries had its `description` extended with the per-directory `standardUse` prose from the bundle ("All the data files within this directory follow the format specified in..."), which the audit noted had been dropped for want of a `conforms_to` slot on `FileCollection`.

### 2.11 `is_tabular` — removed (finding: medium)

**Was:** `is_tabular: false`. **Now:** absent, with the reasoning added to the top-level `source_caveats`: the bundle states the release encompasses tabular, imaging and waveform data together, which one boolean cannot represent.

### 2.12 `at_risk_populations.at_risk_groups_included` — removed (finding: medium, overgeneralization)

**Was:** `false`. **Now:** absent. `special_protections` was split from one concatenated element into three, and a `source_caveats` added stating that the exclusion criteria settle minors, pregnant women, neonates and adults unable to consent, but that the bundle says nothing about prisoners — the IRB form's prisoner questions being unanswered template text.

### 2.13 `regulatory_restrictions.confidentiality_level` — removed (finding: medium, inference presented as a term)

**Was:** `restricted`. **Now:** absent, with a `source_caveats` stating that "HL7:2N (normal)" is the only classification the bundle gives, that it is reproduced verbatim in `other_compliance`, and that mapping it onto the three-term scale would be this record's inference.

### 2.14 `funders` — Microsoft AI for Good Lab removed as a funder (finding: medium)

The third `FundingMechanism` was deleted. The fact moved to `notes`, where it now sits beside the device-manufacturer in-kind paragraph and is explicitly characterized as "in-kind infrastructure support rather than a funding award".

### 2.15 Multivalued slots — concatenated elements split (finding: low/medium, recurring)

The audit identified seven slots where several distinct entities shared one list element. Six were split:

| Slot | Was | Now |
|---|---|---|
| `human_subject_research.regulatory_compliance` | 1 element | 7 elements |
| `human_subject_research.special_populations` | 1 element | 3 elements |
| `at_risk_populations.special_protections` | 1 element | 3 elements |
| `ip_restrictions.restrictions` | 1 element | 4 elements |
| `external_resources` | 1 object | 5 objects |
| `version_access.versions_available` | 1 element | 3 elements |
| `distribution_dates[0].release_dates` | 1 element (3 dates) | 3 `DistributionDate` objects |
| `data_governance.stewardship_roles` | 1 element | 3 elements |

The `external_resources` split also let `archival: false` be populated on the documentation entry (finding 2.25), with the CC-BY note moved into `restrictions` and the self-containment statement into `notes`.

### 2.16 `version_access` — v2.0.0 detail relocated

The "2.01 TB and 165,051 files, no longer accessible" fact moved from `version_details` into the v2.0.0 element of `versions_available`, where it belongs, and per-version participant deltas (863, 1213) were added from the CHANGELOG table.

### 2.17 `informed_consent[0].withdrawal_mechanism` — populated

The withdrawal statement, previously only in `consent_revocations`, was added to the declared `withdrawal_mechanism` field. `consent_revocations` retains it as the slot dedicated to the topic.

### 2.18 Smaller corrections

- `publisher`: trailing slash removed (`https://fairhub.io`), per finding 2.2. Still a URI fallback; no registry CURIE for FAIRhub is in the bundle.
- `variables[14].moca_total_score`: `minimum_value: 0.0` removed as inferred (finding 2.16); `quality_notes` added carrying the 24/26 thresholds and the training/education/socioeconomic caveats the bundle states.
- `collection_timeframes[0].source_caveats`: rewritten to name the one-day start-date offset (18 vs 19 July 2023) as the specific point of disagreement (finding 2.20).
- `subpopulations`: `source_caveats` added to all three entries reconciling them with the healthsheet's blanket "No" to the demographic-subpopulation question (finding 2.9).
- `ethical_reviews`: split from two objects into three, separating the Community Advisory Board from the ethics team.
- `license` and `license_and_use_terms.source_caveats`: the caveat now covers both the name conflict and the access-condition-versus-license-grant distinction (findings 2.19, 2.20 on license).
- Top-level `source_caveats`: extended with the `is_tabular` omission, the required-but-unpointed-at `FileCollection.id` fragments, and the file/byte arithmetic.

### 2.19 Core record

Every change above was projected. The core record additionally gained the tenth `distributions` entry (root metadata), `discouraged_uses`, `data_protection_impacts` and `extension_mechanism`; lost `is_tabular`; and carries the identical caveats. The core header block's `# Phase 4 reconciliation: completed` line is present, as is `# Sources:`.

---

## 3. Findings left as-is

### 3.1 Confirmations requiring no action

The audit checked and passed: the top-level `conforms_to_standard` enum (all seven terms valid); every `FileCollection.conforms_to_standard` list; the split-table arithmetic at all four levels (1576/352/352/2280 across race, sex and diabetes status, all summing correctly); `total_size_bytes` and `total_file_count` against the API; `doi` as a bare anchored DOI contrasted with `id` and `latest_version_doi` as CURIEs; `language: en`; `compression` correctly absent. These are unchanged.

### 3.2 `related_datasets` mixed identifier forms (finding: high, no repair)

Entries 2–3 carry bare URLs while 0–1 and 4–5 carry `doi:` CURIEs. The audit's own reasoning applies: the two documentation targets correspond to FAIRhub `relatedIdentifier` entries with `relatedIdentifierType: URL`, so URLs are what the source states. Unchanged in both records.

### 3.3 `file_collections[*].id` fragments (finding: high, unresolvable tension)

The v6 minting rule says a fragment is warranted only where another value points at the part; no value in this record points at any of the nine (now ten). But `FileCollection.id` is declared **required** in the schema digest, so the objects cannot exist without ids. The schema requirement wins. The fragments remain, and the tension is now stated in the top-level `source_caveats` rather than left silent.

### 3.4 `existing_uses` and `use_repository` (finding: medium, judgment call)

Both healthsheet questions are answered "No". Omission — nothing to list — is the prefer-omission reading. Both remain absent from both records.

### 3.5 `annotation_analyses`, `labeling_strategies`, `machine_annotation_tools`, `other_tasks`, `errata` (findings: medium/low)

All correctly absent. The no-labels fact is carried by `instances[0].label: false` and `label_description`; the erratum healthsheet response is empty in the bundle; `other_tasks` has no named task to carry.

### 3.6 `variables[*].is_sensitive` (finding: medium)

Left unpopulated. None of the twenty-two variables now listed is a controlled-access element, so a uniform `false` would add nothing. The public/controlled split is carried by `sensitive_elements` (two objects) and the `description`.

### 3.7 `creators[0].credit_roles` (finding: medium)

Left empty. Mapping the Nature Metabolism author-block structure (Writing Committee, PIs, staff, project managers, interns, program scientists) onto CRediT terms would be this record's judgment, not the bundle's statement.

### 3.8 `created_on`, `last_updated_on`, `modified_by`, `was_derived_from` (findings: low/medium)

All absent. `created_at` duplicates `issued`; the docs-site "Last updated Jun 4, 2026 by Eamon Dysinger" is the documentation's edit metadata, not the dataset's; version lineage is carried more precisely by `related_datasets` with `is_new_version_of`.

### 3.9 `data_topic` single value (finding: low)

The slot is single-valued on `Instance`. Diabetes remains the choice; the newly added caveat now records the alternatives.

### 3.10 `conforms_to` prose (finding: medium)

Confirmed as correct use — prose in `conforms_to`, terms in `conforms_to_standard`, exactly as the slot descriptions direct. Unchanged.

### 3.11 `notes` compression of competing interests (finding: medium)

The summary sentence was retained but qualified: it now adds "which list those relationships individually", so a reader knows the bundle is more granular than the record.

---

## 4. Outcome

Both records validate. The full record now carries **90 populated top-level slots**; the core record **69**. Five slots were removed as unsupported or unrepresentable (`is_tabular`, `is_deidentified.identifiable_elements_present`, `at_risk_populations.at_risk_groups_included`, `regulatory_restrictions.confidentiality_level`, the Microsoft funder entry); nine were added (`discouraged_uses`, `data_protection_impacts`, `extension_mechanism`, `instances[0].data_substrate`, `instances[0].missing_information`, `data_governance.committee_contact`, `informed_consent[0].withdrawal_mechanism`, the tenth file collection, three derived variables); one boolean was corrected (`was_inferred_derived`) and one set (`is_sample`); one composed name was replaced with a verbatim one; and eight multivalued slots were decomposed into the entities they declare.

No finding was addressed by inventing a fact. Every value added traces to a passage in the declared bundle, and every value removed was removed because the bundle would not carry it.