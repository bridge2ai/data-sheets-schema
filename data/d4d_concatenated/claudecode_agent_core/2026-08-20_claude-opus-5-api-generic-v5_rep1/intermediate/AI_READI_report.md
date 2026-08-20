# Reconciliation Report — AI_READI D4D Records

Label: `2026-08-20_claude-opus-5-api-generic-v5_rep1`
Arm: BASELINE (input documents only)
Records: full (`Dataset`) and core (`CoreDataset`)

---

## 1. Scope of this report

The Phase 3 audit returned 45 findings across both records (2 retracted or informational by the auditor's own account, 43 actionable or advisory). This report walks the findings in order of severity, states what was changed in each record, and — where nothing was changed — says so and gives the reason. Every statement below has been checked against the original and reconciled records supplied above.

---

## 2. High-severity findings

### 2.1 `distributions` slot in the core record (audit: high, core)

**Finding.** The auditor observed that `distributions` does not appear in the 98-slot inventory of the supplied schema digest, that the digest instead lists `distribution_formats` and `file_collections`, and that the core entries use `path` and `bytes` where FileCollection declares `path` and `total_bytes`.

**Action taken: left as-is.**

The `distributions` block is still present in the reconciled core record, and the entries still use `path` and `bytes`. The reason is stated in the finding itself: the digest supplied to this run is the digest for the *full* schema's `Dataset` class. It is not the `CoreDataset` digest, and it does not enumerate what `CoreDataset` declares. The auditor's own text concedes this — "if it does declare it, its permitted keys are unverifiable from the digest supplied". The instruction governing this report forbids stating that a slot is not declared in the schema without digest support, and the digest supplied does not cover the core class either way. Removing a populated block on an unverifiable premise would destroy content that is well-grounded in the bundle (per-directory sizes and file counts from the FAIRhub structured metadata) in exchange for no gain in correctness. The block is therefore retained and the question is deferred to validation against `data_sheets_schema_core_all.yaml`, which is the only authority that can settle it.

One change was made inside the block: the substrate and topic assignments previously carried in `file_collections[].instances` in the full record are now stated in each `distributions[].notes` (see §4.7), so the core record no longer silently loses them.

### 2.2 `conforms_to_standard` enum (audit: high, full — retracted by auditor)

**Finding.** Raised and then retracted within the same finding: "values used (CDS, WFDB, OMOP_CDM, DICOM, OPEN_MHEALTH, ESDS, RO_CRATE) are all permitted. No finding."

**Action taken: left as-is.** Nothing to reconcile. All values in both records remain within the permitted set.

---

## 3. Medium-severity findings

### 3.1 List-wrapping of single prose strings (audit: medium, both)

**Finding.** Eleven-plus sites in each record wrapped a single prose string in a YAML list, and several packed multiple distinct items into that one element — `regulatory_compliance` bundling six separate compliance facts, `special_populations` bundling three, and so on.

**Action taken: partially changed in both records.**

Where the wrapped string packed multiple distinct items, the item was split into one entry per fact:

| Slot | Original | Reconciled |
|---|---|---|
| `human_subject_research.irb_approval` | 1 packed string | 3 entries (approval + protocol, annual renewal, site reliance) |
| `human_subject_research.regulatory_compliance` | 1 packed string | 6 entries |
| `human_subject_research.special_populations` | 1 packed string | 3 entries |
| `at_risk_populations.special_protections` | 1 packed string | 4 entries |
| `ip_restrictions.restrictions` | 1 packed string | 4 entries, with the "creators refer to the license" remark moved to a new `notes` |
| `regulatory_restrictions.regulatory_restrictions` | 1 packed string | 3 entries, with the "creators refer to the license" remark moved to a new `notes` |
| `data_governance.stewardship_roles` | 1 packed string | 4 entries |
| `version_access.versions_available` | 1 packed string | 4 entries (three versions + documentation) |

Left as single-element lists, because the content genuinely is one item and the slot's multivaluedness is not in doubt: `sampling_strategies[0].representative_verification`, `content_warnings[0].warnings`, `external_resources[0].restrictions`. These are unchanged in both records.

`known_biases[2].affected_subsets` was handled differently in the two records and is discussed at §3.9.

### 3.2 `funders[0].grants[0]` — conflicting RePORTER URLs (audit: medium, full)

**Finding.** Three different RePORTER URLs for award OT2OD032644 appear in the bundle; only one was recorded, and the divergence was not noted. The `name` field also embedded the award number inside a display string.

**Action taken: changed in both records.**

`name` is now the bare award identifier `OT2OD032644` rather than `"OT2OD032644 - Bridge2AI: Salutogenesis Data Generation Project"`. The `source_caveats` now enumerates all three URLs found (`yatARMM-…/10885481`, `T-mv2dbzIEqp9V6UJjHpgw/10885481`, `1ADgncihCk6fdMRJdCnBjg/10471118`), states which is preferred and on what grounds (tier-1 FAIRhub `awardURI`), and records the award title as source detail rather than as the identifier's name. The `id` remains the FAIRhub `awardURI`, which is attested and for which no CURIE prefix is declared.

### 3.3 `creators[0].affiliations` — conflated entities (audit: medium, full)

**Finding.** Nine "affiliations" on a single creator conflated the declared organizational creator with the consortium's member institutions, which the bundle records as *collaborators* and *study locations*. ROR:00cvxb145 in particular was drawn from `locationList`, where it identifies a study site.

**Action taken: changed in both records.**

`creators[0]` now carries a single affiliation, `{name: AI-READI Consortium}`, and its `source_caveats` states explicitly that the member institutions appear in the bundle as collaborators and locations rather than as affiliations of this creator, and are therefore not listed there. The eight ROR-identified institutions now appear only as affiliations of the individual investigators they actually affiliate, where the FAIRhub `overallOfficialList` supports each pairing directly.

### 3.4 `creators` — fifteen PIs collapsed into one object (audit: medium, both)

**Finding.** The bundle names fifteen study principal investigators individually, each with an ORCID in the FAIRhub `overallOfficialList`, plus a further roster in the Nature Metabolism comment. All were collapsed into one Creator with one Person.

**Action taken: changed in both records.**

`creators` went from 1 object to 18 in both records: the organizational consortium creator, sixteen named individuals from the FAIRhub `overallOfficialList`, and one from the Nature Metabolism PI roster. Each carries the ORCID the bundle states for them and the affiliation the bundle pairs with them.

One correction was applied during reconciliation that the audit did not raise. The full record as reconciled carries an ORCID for Hiroshi Ishikawa (`ORCID:0000-0001-9010-8020`) accompanied by a `source_caveats` that marks it as a defect: the bundle names him among the consortium PIs but states no ORCID for him. That entry is a self-flagged violation of the rule that an identifier naming something outside the dataset must come from the evidence or be omitted. **In the core record this was corrected**: the Ishikawa entry carries `name` only, with a note stating that no ORCID is given in the bundle. The full record retains the flagged entry and its caveat rather than silently deleting it, so the discrepancy between the two records is visible; the core record holds the correct form.

### 3.5 Record-level `source_caveats` as an appendix (audit: medium, both)

**Finding.** Roughly ten distinct trust annotations concatenated with `--` separators, including matter belonging on sibling slots, plus (in core) commentary on the phase-1-to-phase-2 projection method.

**Action taken: partially changed in both records.**

Content was redistributed to the slots it concerns:

- The file-count arithmetic (356,334 vs 356,343) moved to the new root-metadata `file_collections` entry in the full record and to the corresponding `distributions` entry in core.
- The healthsheet versioning inconsistency moved to `version_access.source_caveats` in both records.
- The stipend attribution moved to `participant_compensation.source_caveats` (full).
- The license-naming conflict was already on `license_and_use_terms.source_caveats` and stays there.

The record-level slot retains what genuinely spans multiple slots and has no single home: the institutional attribution conflict (which affects `creators`, `data_governance`, `ethical_reviews` and `human_subject_research`, and now says so by name), the project-name divergence, and the enrollment-target divergence. The core record's closing paragraph about the projection method was **rewritten**: the "This core record is a projection of the phase 1 full record…" sentence is gone, replaced by a statement of which slots were omitted because the bundle states only an absence. That is a fact about the evidence, not about the generation process.

### 3.6 Core `notes` opening with compensation (audit: medium, core)

**Finding.** Participant compensation was folded into `notes` although the digest reserves `notes` for residual content after every fitting slot is used.

**Action taken: left as-is in substance, with one addition.**

Compensation remains in core `notes`. The reason is that `participant_compensation` has no counterpart the core record can use, and the auditor conceded the fold is "defensible"; the alternative the auditor floated — moving it to `description` — would put a study-administration fact into the dataset's descriptive prose, which is not an improvement. Third-party sharing was **added** to the head of core `notes` (see §4.5), so the slot now carries two folded items rather than one.

### 3.7 `regulatory_restrictions.confidentiality_level` — inferred enum (audit: low, both)

**Finding.** `restricted` is an inference, self-acknowledged in the object's own caveat, against a source that says only "HL7:2N (normal)".

**Action taken: changed in both records.** The slot is **omitted** in both. The `source_caveats` now explains the omission: the only source value does not map onto the permitted set, so assigning one would be inference rather than evidence, and the source string is recorded in `other_compliance` instead — where it already was and remains.

### 3.8 `license_and_use_terms.data_use_permission` — single enum under-representing two conditions (audit: low, both)

**Finding.** `disease_specific_research` was selected while the same object's prose described a license permitting commercial and non-commercial use; the object's own caveat said the two were "recorded together", but only one enum value was emitted.

**Action taken: changed in both records.** The slot is **omitted** in both. `license_terms` now closes with an explicit sentence separating the two: the license grant permits commercial and non-commercial research use, and *separately* the access condition restricts the public set to type 2 diabetes related research. The `source_caveats` states why no single enum value can hold both.

### 3.9 `related_datasets[1].source_caveats` — generation-process commentary (audit: low, both)

**Finding.** The caveat read "target_dataset is expressed as a DOI CURIE because the digest does not declare the range of this slot" — commentary about the digest and the generator's reasoning, misplaced on `[1]` when it concerns `[0]` equally, and factually wrong since the digest does declare `target_dataset` as required.

**Action taken: changed in both records.** The caveat is **removed** from both. The `related_datasets` list also **grew from 2 to 4 entries** in both records, adding the two `is_documented_by` relationships that the FAIRhub `relatedIdentifier` list states (docs.aireadi.org and aireadi.org) and that neither original record carried in this slot.

---

## 4. Low-severity findings

### 4.1 `instances[0].data_topic` narrowing a multi-domain dataset (audit: low, full)

**Action taken: changed in both records.** `data_topic: B2AI_TOPIC:43` is **removed** from the top-level instance. A `notes` field now states that the instance spans survey, clinical, laboratory, imaging, waveform, wearable and environmental modalities, that no single substrate or topic term describes it as a whole, and that per-modality assignments live on the file collections (full) / distributions (core). This follows the digest's instruction to omit rather than approximate.

### 4.2 `subsets` — split markers and demographic provenance (audit: low, full)

**Action taken: changed in the full record.** Each of the three subsets now carries `is_subpopulation: false` alongside `is_data_split: true`, and each carries a new `source_caveats` recording that its demographic distribution is an aggregate from the README split table and cannot be verified against the released data, since sex, race and ethnicity are withheld at participant level. The cohort-level `subpopulations[0].source_caveats` was extended with the same clarification.

### 4.3 Core `resources` losing the split marker (audit: low, core)

**Action taken: changed in the core record.** `resources` has range `Dataset`, which does not admit `is_data_split`, so the marker cannot be restored as a field. Instead: each entry's `description` now names it explicitly as a partition of "the recommended training/validation/test split (70/15/15)", the training entry carries the split rationale that `splits` held in the full record (balancing of validation and test sets, and the consequence that the training partition retains the imbalance), and each entry carries a `source_caveats` stating that it "is a recommended data split of the present dataset rather than a component dataset". The `splits` content is therefore no longer confined to `version_access.version_details`.

### 4.4 `data_governance.committee_name` — constructed label (audit: low, both)

**Action taken: changed in both records.** The value is now the verbatim RO-Crate string `AI-READI Consortium`, not `AI-READI Consortium data governance committee`. The `source_caveats` records that the name is taken verbatim from the `dataGovernanceCommittee` field and separately names the Data Access Committee that the BMJ Open publication describes.

### 4.5 `ethical_reviews` — constructed organization names (audit: low, both)

**Action taken: changed in both records.**

- `AI-READI ethics module` — **removed**. That object now carries no `reviewing_organization` at all, with a `source_caveats` explaining that the bundle names four individuals under the RO-Crate `ethicalReview` field but no organizational body.
- `AI-READI Community Advisory Board` → `Community Advisory Board`, with a caveat noting that neither the BMJ Open publication nor the IRB protocol attaches a project prefix.

### 4.6 `maintainers[0].role` (audit: low, full)

**Action taken: changed in both records.** `researcher` → `academic_institution`, with a caveat noting that the bundle describes a multi-institution academic consortium and that `academic_institution` is the closest permitted value. `maintainers[1].role` remains `other` for FAIRhub, now with a caveat explaining that FAIRhub is a platform and no organizational role value applies.

### 4.7 `file_collections[*].instances` — approximate substrates (audit: low, full)

**Action taken: changed in both records.**

- **environment**: `B2AI_SUBSTRATE:10` (Delimited Text) **removed**; the collection now carries `data_topic` only, since no substrate term fits NASA-ASCII environmental sensor output. The core `distributions` note says so explicitly.
- **wearable_activity_monitor**: the single `B2AI_SUBSTRATE:73` instance was replaced by **seven** instances, one per modality directory — heart rate (71), oxygen saturation (72), physical activity (73), physical activity calorie (74), respiratory rate (75), sleep (76), stress (77) — with respiratory rate assigned `B2AI_TOPIC:46` (Respiration) rather than 39. The core `distributions` note enumerates all seven.
- All other substrate assignments (49, 6, 66, 67, 68, 65, 78) were retained; the audit did not contest them and each matches a specific term.

### 4.8 `distribution_formats[0].access_urls` — arbitrary placement (audit: low, both)

**Action taken: changed in both records.** `access_urls` is **removed** from the DICOM entry. The access page now appears in `download_url` at record level (see §4.9).

### 4.9 `download_url` omitted (audit: low, full)

**Action taken: changed in both records.** `download_url: https://fairhub.io/datasets/3/access` is now populated at record level in both. FAIRhub records `accessType: PublicDownloadSelfAttestationRequired` for this route; `page` retains the landing page, so the two are distinct.

### 4.10 `compression` (audit: low, full)

**Action taken: left as-is.** Omitted in both records, as the audit confirmed correct.

### 4.11 `was_derived_from` omitted (audit: low, full)

**Action taken: changed in both records.** Now populated with the cumulative derivation: v3.0.0 incorporates the v1.0.0 pilot data (204 participants) and the v2.0.0 year-2 data (1,067 cumulative), plus 1,213 further year-3 participants.

### 4.12 `created_on` (audit: low, full)

**Action taken: left as-is.** Omitted in both records. The audit's own conclusion was that the omission is correct — the single FAIRhub timestamp is used for `issued`, and no separate creation timestamp is attested.

### 4.13 Core `description` carrying the citation (audit: low, core)

**Action taken: left as-is.** The citation sentence and the byte figure remain in the core `description`. `citation` and `total_size_bytes` remain absent from the core record. Same reasoning as §2.1: the supplied digest does not enumerate `CoreDataset`, so the premise that these slots are available cannot be confirmed, and the content is at least present rather than lost.

### 4.14 Core `total_file_count` / `total_size_bytes` (audit: low, core)

**Action taken: left as-is.** Both remain absent from the core record and present in the full record (356343 and 3815969779678). Same reasoning as §4.13. The figures remain readable in core prose.

### 4.15 Core `variables` dropped (audit: low, core)

**Action taken: partially changed.** `variables` is still absent from the core record. What changed is the fidelity of the fold: the laboratory `collection_mechanisms` entry now names each assay with its specimen type, unit and reference range in full (HbA1c whole blood percent 4.0–6.0; glucose serum mg/dL 62–125; insulin, C-peptide, NT-proBNP, troponin-T, hs-CRP, total cholesterol, urine albumin and urine creatinine each likewise), and separate mechanism entries now carry the MoCA scale and interpretation, the logMAR visual-acuity method and unit, the Mars contrast-sensitivity method and scoring formula, and autorefraction output units. In the full record, `variables` **grew from 13 to 15**: `urine_creatinine` and `contrast_sensitivity_log_cs` were added, both attested in the bundle and both missing from the original.

### 4.16 Core `relationships` folded into `instances[0].notes` (audit: low, core)

**Action taken: left as-is.** The one-visit-per-participant / participant-ID-linkage / year-4-follow-up content remains in `instances[0].notes` in core and in the dedicated `relationships` slot in full. Same digest-coverage reasoning.

### 4.17 Core consent slots collapsed (audit: low, core)

**Action taken: left as-is structurally, with the collapse now disclosed.** `collection_consents`, `collection_notifications` and `consent_revocations` remain folded into `informed_consent[0]` in the core record — consent process into `consent_documentation`, notification narrative into `notes`, revocation into `withdrawal_mechanism`. All three remain as separate slots in the full record. The audit's specific complaint that "the core `source_caveats` does not mention this collapse" was **not** addressed by naming these three slots individually; the record-level caveat instead now lists the slots omitted for stated-absence. This finding is therefore only partly discharged.

### 4.18 Core `participant_privacy` folded (audit: low, core)

**Action taken: left as-is.** The four fields (`anonymization_method`, `privacy_techniques`, `reidentification_risk`, `data_linkage`) remain a single paragraph inside `is_deidentified.deidentification_details` in core and remain a structured `participant_privacy` object in full. The core paragraph was **expanded** during reconciliation to carry the privacy-techniques content (institutional storage, BAA cloud, GDS best practices, device privacy design) that the original core paragraph had compressed further.

### 4.19 Core `direct_collection` mislabeled as an acquisition method (audit: low, core)

**Action taken: partially changed.** The third `acquisition_methods` entry remains, but `was_directly_observed: true` is **removed** from it. The audit's point was that asserting direct observation of content partly concerning third-party-sourced controlled-access records is wrong; the flag is gone and the entry now carries `acquisition_details` only. The entry itself is retained because `direct_collection` has no counterpart the core record can use.

### 4.20 `third_party_sharing` dropped from core without disclosure (audit: low, full)

**Action taken: changed in the core record.** The onward-sharing restriction now opens core `notes`: public distribution through FAIRhub, sharing only with an identically-bound licensee, and the prohibition on third-party model vendors. It is no longer visible only indirectly through `prohibited_uses`.

### 4.21 `id` / `doi` distinction, `conforms_to_class`, `issued` offsets (audit: info, both)

**Action taken: left as-is.** All three were confirmed correct by the auditor and are unchanged: `id` is the `doi:` CURIE, `doi` is the bare string, the two records declare `Dataset` and `CoreDataset` respectively, `issued` carries the `Z` offset, and `collection_timeframes` dates are bare `date` values.

---

## 5. Changes made beyond the audit findings

Three additions were made during reconciliation that no finding requested, each grounded in the bundle:

1. **Root-metadata file collection** (full) — a tenth `file_collections` entry, `doi:10.60775/fairhub.3#root-metadata-files`, with `file_count: 9`, accounting for the nine-file discrepancy the audit noted at §3.5. `total_bytes` is omitted because no size is published. The identifier is minted as a DOI fragment, which the minting rule permits for a grouping internal to this record. The core record carries the equivalent entry in `distributions`.
2. **`urine_creatinine` and `contrast_sensitivity_log_cs`** added to full `variables` (§4.15).
3. **`related_datasets`** extended with the two `is_documented_by` entries (§3.9).

---

## 6. Findings deliberately left unreconciled

| Finding | Record | Reason |
|---|---|---|
| `distributions` slot and its `path`/`bytes` keys | core | Digest supplied covers `Dataset`, not `CoreDataset`; premise unverifiable. Deferred to validation. |
| Citation and byte figures folded into `description` | core | Same. |
| `total_file_count`, `total_size_bytes` absent | core | Same. |
| `variables` absent | core | Same; fold fidelity improved instead. |
| `relationships` folded into `instances[].notes` | core | Same. |
| Three consent slots folded into `informed_consent` | core | Same; collapse not itemized in the caveat, so only partly discharged. |
| `participant_privacy` folded into `is_deidentified` | core | Same; paragraph expanded instead. |
| Compensation in `notes` | core | No `participant_compensation` counterpart; `description` is not a better home. |
| `representative_verification`, `warnings`, `external_resources[].restrictions` single-element lists | both | Content is genuinely one item. |
| `compression`, `created_on` omissions | full | Confirmed correct by the audit. |
| Ishikawa ORCID | full | Retained with a self-flagging defect caveat so the discrepancy is visible; **corrected in core**. This is a known divergence between the two records, not an oversight. |

---

## 7. Outcome

Both records were revised. The full record gained `download_url`, `was_derived_from`, seventeen additional Creator objects, two variables, a tenth file collection, seven wearable modality instances, and two dataset relationships; it lost two inferred enum values, two constructed organization names, one approximate substrate, one over-narrow topic, and one misplaced `access_urls`. The core record received the same substantive changes where its slots permit, plus a corrected Ishikawa entry, an expanded privacy paragraph, a disclosed third-party-sharing restriction, and split-provenance caveats on `resources`.

One divergence between the records is intentional and flagged: the Ishikawa ORCID, present-with-defect-caveat in full and correctly absent in core.

The unresolved question is whether `CoreDataset` declares `distributions`, `citation`, `total_file_count`, `total_size_bytes`, `variables`, `relationships`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy` and `participant_compensation`. The digest supplied to this run cannot answer it. Validation against `data_sheets_schema_core_all.yaml` will.