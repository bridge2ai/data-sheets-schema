# CHORUS D4D Reconciliation Report

**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Records reconciled:**
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/CHORUS_d4d_core.yaml`

---

## 1. Dataset referent

`Dataset` admits one referent. The referent held across both records is **the CHoRUS clinical care dataset** — the multi-center, multi-modal acute/critical care data resource assembled by the CHoRUS data generation project — and *not* the CHoRUS project, the chorus-ai software organization, or the AIM-AHEAD Bridge2AI for Clinical Care training program. This choice was verified as consistent in both records during Phase 4; no drift was found.

Consequences of that choice, upheld in reconciliation:

- The MIT License attaching to the `chorus-ai` GitHub repositories is **not** carried into `license`, because it governs software, not the dataset.
- The AIM-AHEAD training program's eligibility rules, stipends and application deadlines are **not** dataset facts; only the dataset-access requirements surfaced within that webinar (registration form, licensing agreement, `.edu` email) are represented, under Distribution and Governance slots.

---

## 2. Audit findings and disposition

### 2.1 High severity

#### F1 — `data_governance.committee_members` misuse and inferred personal name (both records) — **CHANGED**

The audit found two coupled defects. First, `committee_members` (range `Person[]`) held two Person objects whose `id` values were `mailto:` URIs and whose `name` values were reconstructed from email local-parts; `D. Bold` appears nowhere in the bundle, which gives only the address `dbold@emory.edu`. Second, the bundle describes these addresses as *access-request* contacts ("Request access: dbold@emory.edu or jared.houghtaling@tuftsmedicine.org"), never as members of an access-decision committee — a mismatch the object's own `source_caveats` conceded, making the population self-contradicting.

**Change applied to both records:** `committee_members` removed. The two addresses are retained where the bundle actually places them — as the route for requesting access — under `data_governance.access_review_process`, expressed as the stated request contacts rather than as committee membership. `jared.houghtaling@tuftsmedicine.org` retains the name **Jared Houghtaling**, which *is* stated in the bundle (listed as a Tufts lecturer in the curriculum table), and is carried as `committee_contact` (range `Person`, singular) with an `id` of the form `chorus:person-houghtaling` and the email in the prose of `access_review_process`. The Emory address is carried as an address only, with no invented personal name. The now-redundant `source_caveats` disclaimer on the removed slot was deleted; a shorter caveat noting that the bundle names no formal access committee was retained on `data_governance`.

#### F2 — missing `# Sources:` line in core header — **NO CHANGE (finding retracted)**

The audit raised then retracted this. Verified independently in Phase 4: the core header block contains `# Sources: data/preprocessed/concatenated/CHORUS_preprocessed.txt + data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/CHORUS_d4d.yaml` verbatim. Both header blocks match the mandated text exactly, including the four core-only lines. No defect.

#### F3 — `is_tabular` omission — **NO CHANGE (finding downgraded by auditor)**

The auditor downgraded this to non-defect. Confirmed. The dataset spans OMOP relational tables, DICOM imaging, WFDB/EDF+ waveforms and tokenized text; `is_tabular` is a single boolean and no honest single value exists. Omission stands, per the rule preferring omission over inference.

---

### 2.2 Medium severity

#### F4 — `instances[chorus:instance-admission].counts` silently resolves a source conflict (both records) — **CHANGED**

`counts: 50000` selected one side of a conflict the sibling `source_caveats` documented as unresolved: the cohort-2 webinar states "over 45K unique admissions" as of August 2025, while chorus4ai.org states 50,000 released admissions (and 100,000 as the *anticipated final* figure). The decision rules forbid silently selecting one of two disagreeing sources.

**Change applied to both records:** the scalar `counts` was removed from this Instance. Both figures, their sources and their dates are now represented in the Instance's `notes`, and the disagreement remains flagged in `source_caveats`. The 100,000 anticipated-final figure stays where it belongs — in `updates`/`purposes` as a target, not as a count of extant instances.

#### F5 — `instances[chorus:instance-imaging].counts` unit mismatch (both records) — **CHANGED**

`counts: 7642` was attached to an Instance whose `instance_type` reads "Radiology imaging study extracted from hospital PACS", but 7,642 is the count of *admissions with radiology data* (chorus4ai.org), not of imaging studies. The bundle separately gives ~1,000 images currently available with de-identification in process. The prior `notes` acknowledged the mismatch instead of resolving it.

**Change applied to both records:** `counts` removed from this Instance. Both quantities are now stated in `notes` with their correct units and sources: 7,642 admissions carrying radiology data, and approximately 1,000 images currently released with de-identification of a larger cohort in progress.

#### F6 — `instances[chorus:instance-omop-ehr].counts` unit mismatch (both records) — **CHANGED**

`counts: 1600000000` is a count of OMOP *rows*, while `instance_type` declares a structured EHR record spanning five OMOP domains. Rows and records are different units.

**Change applied to both records:** `counts` removed; "1.6 billion rows of EHR OMOP data" retained in `notes` with its unit made explicit and attributed to chorus4ai.org.

#### F7 — `publisher` asserted without support (both records) — **CHANGED**

`publisher` (range `uriorcurie`) held `https://chorus4ai.org/`, duplicating both `id` and `page`. The bundle names no publisher for the dataset; chorus4ai.org is the project's public website, and the site itself carries a notice that the repository is under review. Asserting a publisher relationship the sources never state is inference.

**Change applied to both records:** `publisher` removed. The website remains in `page`; the awardee organization (Massachusetts General Hospital) remains in `creators` and in `data_governance.accountable_organization`, where the bundle does support it.

#### F8 — `funders[0].grants[0]` under-populated (both records) — **CHANGED**

The Grant object carried only `id: https://reporter.nih.gov/project-details/10472824` — a landing-page URL used as an identifier — while the identifiers the bundle states plainly (project number `1OT2OD032701-01`, core project number `OT2OD032701`, award amount 5,880,300 USD, period 2022-09-01 to 2026-11-30) sat in the parent `FundingMechanism.notes` as prose. This is the v3 defect: an object of the right shape holding none of the structure it exists to carry.

**Change applied to both records:** the Grant `id` is now the grant identifier itself (`chorus:grant-OT2OD032701`), with the project number, core project number, award amount and project period moved into the Grant object's own declared fields, and the RePORTER URL retained as the source reference rather than as the identity. `FundingMechanism.grantor` remains the NIH Common Fund / Bridge2AI program as stated. The parent `notes` was reduced to residual content only, per the notes-as-residual rule.

#### F9 — free-text `role` on `DataCollector` (full record) — **NO CHANGE**

The audit correctly notes that `role` is enum-constrained on `Maintainer` but not on `DataCollector`; the values "Data acquisition site", "Data site manager", "CHoRUS sub-team" are valid. The stylistic inconsistency with the constrained vocabulary used on `Maintainer` is real but not a defect, and the free-text values carry information the Maintainer enum could not express (the distinction between contributing sites, site-level managers, and the Standards / Data Acquisition / Tooling sub-teams is stated in the GitHub overview and would be lost by forcing it into enum terms). Left as-is.

---

### 2.3 Low severity

#### F10 — `known_biases[chorus:bias-selection].bias_type` (both records) — **CHANGED**

`selection_bias` was assigned to a bias the bundle never observes or characterizes. The sources state only that the project will "manage privacy and bias" and will use federated access and sampling "to ensure a balanced and diverse cohort" — an intention, not a finding. The object's own `source_caveats` conceded the point.

**Change applied to both records:** `bias_type` removed. The `DatasetBias` object is retained without a type term, since the bundle does support that bias management is an explicit project concern with stated mitigations (federated sampling for cohort balance, accounting for social determinants of health); these remain in `bias_description` and `mitigation_strategy`. The caveat that no bias has been characterized or measured in the released data is retained.

#### F11 — `regulatory_restrictions.confidentiality_level` — **NO CHANGE**

Every data type in the webinar's modality table is marked "Controlled" for access control, and access requires a signed licensing agreement, registration and a `.edu` address. Mapping this onto `restricted` rather than `confidential` is the more conservative of the two available readings and does not overstate the sources. A `source_caveats` note recording that the bundle says "controlled access" rather than using the enum's own vocabulary was added.

#### F12 — `license` omission — **NO CHANGE (verified correct)**

Confirmed. MIT applies to the software repositories (and Apache-2.0 to `Chorus_SOP`), not the dataset. The bundle describes the dataset's terms as a signed licensing agreement whose content is not reproduced. `license` stays omitted; the licensing-agreement requirement is carried in `license_and_use_terms` and in the `data_governance` access process, and `source_caveats` explains the omission.

#### F13 — uniform `maintainers[*].role: academic_institution` (both records) — **CHANGED**

Four Maintainer objects all carried `academic_institution`, flattening distinct kinds. `chorus:maintainer-access-contacts` names two individuals at Emory and Tufts Medicine; `chorus:maintainer-developers` describes open-source software contributors.

**Change applied to both records:** roles differentiated within the permitted enum — `researcher` for the named access contacts, `other` for the software-contributor group (with the specifics in `maintainer_details`), and `academic_institution` retained only for the consortium-level and site-level maintainer entries, where it fits.

#### F14 — malformed contact email propagated into `data_governance.stewardship_roles` — **CHANGED**

`cmccrary@mgh.havard.edu` is transcribed verbatim from chorus4ai.org and contains an apparent domain typo (`havard` for `harvard`). The typo was flagged only at the top-level `source_caveats`, far from the value.

**Change applied to full record:** a local `source_caveats` was added to the `data_governance` object noting that the program-manager address is transcribed as printed on the source page and that the domain appears misspelled, so the annotation travels with the value. The address itself is left unaltered — correcting it would be inference about an address we cannot verify. The top-level caveat is retained.

#### F15 — `total_file_count` / `total_size_bytes` omission — **NO CHANGE (verified correct)**

The "23 Tb" figure is waveform volume specifically, not a total across all collections, and no file counts appear anywhere in the bundle. Omission stands. The 23 TB figure is retained in the waveform `FileCollection` context where it is accurate.

#### F16 — holdout represented in both `subsets` and `splits` (full record) — **NO CHANGE**

The duplication is real but both slots are declared for different purposes: `splits` documents the partition and its rationale, `subsets` records it as a logical partition of the composition. The bundle supports both readings (the NIH abstract describes "sequestering holdout datasets for external validation"). A cross-referencing note was added to each so they cannot silently diverge; neither was deleted.

#### F17 — core drops `subsets` and `splits` (core record) — **CHANGED**

The holdout test set is the dataset's most distinctive structural feature — it is called out in the NIH abstract as a deliberate design element for external model validation — and the core projection dropped its structured representation entirely, retaining it only obliquely through `purposes`, `tasks` and `intended_uses`.

**Change applied to core record:** `splits` restored to core with the holdout entry, carrying the split rationale. `subsets` remains omitted from core, since core is a projection and one structured representation of the holdout suffices there; this resolves F16's duplication concern for the core record specifically.

#### F18 — core drops `direct_collection` (core record) — **CHANGED**

The full record carries `direct_collection` with `is_direct: false`, reflecting that data was extracted retrospectively from hospital clinical systems rather than collected directly from individuals. Core retained every neighbouring Collection-module slot (`acquisition_methods`, `collection_mechanisms`, `collection_timeframes`, `data_collectors`) but dropped this one without pattern.

**Change applied to core record:** `direct_collection` restored, matching the full record.

#### F19 — core drops `participant_privacy` (core record) — **CHANGED**

Core retained `is_deidentified`, `sensitive_elements` and `confidential_elements` but dropped `participant_privacy`, splitting a tightly coupled cluster.

**Change applied to core record:** `participant_privacy` restored, carrying the tokenization of clinical notes via the OHNLP toolkit, the de-identification in progress for imaging, and the stated project aim of transformation approaches that limit re-identification.

#### F20 — core drops `third_party_sharing` (core record) — **CHANGED**

Core retained `distribution_formats` and `distribution_dates` but dropped `third_party_sharing` (`is_shared: true` in the full record), splitting the Distribution module inconsistently.

**Change applied to core record:** `third_party_sharing` restored, matching the full record.

#### F21 — `version` omission — **NO CHANGE (verified correct)**

No version identifier appears in the bundle. Omission stands, with the reason in `source_caveats`.

#### F22 — `doi` / `citation` omission — **NO CHANGE (verified correct)**

The bundle supplies no DOI for the dataset and no recommended citation. The NIH RePORTER application ID and project numbers are grant identifiers, not dataset DOIs, and are recorded under `funders`. Omission stands.

#### F23 — `download_url` omission — **NO CHANGE (verified correct)**

The bundle describes controlled access via a registration form, a signed licensing agreement, provisioned compute, and named request contacts — an access *route*, not a download endpoint. Placing the access route in `download_url` would be the v2 wrong-neighbouring-field defect. Omission stands; the route is in `data_governance` and `license_and_use_terms`.

#### F24 — consent slots omitted — **NO CHANGE (verified correct)**

`collection_consents`, `informed_consent` and `consent_revocations` are all omitted in both records. The bundle describes retrospective extraction from clinical systems and community-facing ethics focus groups convened to determine what data is appropriate for public sharing, but says nothing about individual participant consent, its type, documentation or withdrawal. Omission stands. The ethics focus groups are represented under `ethical_reviews` and `purposes`, where the bundle does support them.

---

## 3. Verified-correct items carried forward unchanged

The audit confirmed and Phase 4 re-verified the following, none of which required edits:

- Header blocks in both records match the mandated text verbatim, including the four core-only lines (`# D4D Core Datasheet`, `# Generation Method: ... phase 2`, `# Sources:`, `# Schema: ...core_all.yaml`) and `# Phase 4 reconciliation: completed`, which is present only because Phase 4 has now run.
- `id` values are consistent between the two records and across internal references.
- `conforms_to` (prose naming OMOP CDM, DICOM, WFDB, EDF+/Persyst, OHNLP) is paired with `conforms_to_standard` terms (`OMOP_CDM`, `DICOM`, `WFDB`, `OTHER`) as the schema intends — prose in one, queryable terms in the other, both populated for the same standards.
- `conforms_to_schema` / `conforms_to_class` describe the record, not the data, and are not confused with `conforms_to`.
- All remaining enum values validate against their permitted sets.
- Multivalued slots emit one object per distinct entity: six named leadership figures as separate `Creator` entries, the nine modalities as separate `FileCollection` / `Instance` entries, distinct `purposes` and `tasks` rather than one merged blob.
- The `data_substrate` and `data_topic` CURIEs on `Instance` objects draw only from B2AI_SUBSTRATE and B2AI_TOPIC, and are omitted rather than approximated where no term fits (notably for EDF+/Persyst EEG, where no substrate term applies cleanly).

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots | 61 | 44 |
| Slots changed in Phase 4 | 8 | 12 |
| Slots removed in Phase 4 | 5 | 5 |
| Slots restored in Phase 4 | 0 | 4 |
| Validation | pass | pass |

**Validation commands run:**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/CHORUS_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/CHORUS_d4d_core.yaml
```

Both validated cleanly after reconciliation.

**Net effect.** The two high-severity defects were the same defect appearing in both records: an invented personal name and a governance relationship the bundle does not assert. Both are removed. The medium-severity cluster was concentrated in `Instance.counts`, where three of four counts carried units foreign to their declared `instance_type` or resolved a documented conflict into a scalar; all four scalar counts are now removed, with the underlying figures preserved in `notes` with explicit units and attributions. The remaining changes tightened structure (Grant identity, maintainer roles) or repaired an inconsistent core projection (four slots restored). Deliberate omissions — license, version, DOI, citation, download URL, the consent cluster, file totals — were each re-checked against the bundle and all stand.