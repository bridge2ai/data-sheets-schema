# VOICE D4D Reconciliation Report

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep3`
**Records:** full (`Dataset`), core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Summary of the audit

The Phase 3 audit returned 36 findings: 2 high, 14 medium, 20 low. The two high-severity findings both concerned the core record's `distributions` block. Medium-severity findings clustered into three groups: (a) content present in the full record but absent from the core record with no equivalent; (b) the `at_risk_populations.at_risk_groups_included` boolean contradicting the record's own `human_subject_research.special_populations`; (c) an instance substrate term encoding packaging rather than substrate. Low-severity findings were largely positive checks (identifier form, `uri` vs `uriorcurie` handling, bare-DOI form, absence of invented registry identifiers) plus several observations about caveated-but-tense slot values.

---

## 2. Changes made

### 2.1 High severity

**`distributions` in the core record (findings 1 and 2).**

The audit asserted that `distributions` is not declared in the schema digest and that its member key `path` corresponds to no documented object range. Checking the supplied digest: the digest lists the 98 `Dataset` slots and the object ranges reachable from them, and `distributions` does not appear in that listing. However, the digest explicitly does *not* supply the `CoreDataset` slot inventory — the Phase 2 instruction names `data_sheets_schema_core_all.yaml` as the core schema, and no digest of it was provided. I therefore could not confirm from the supplied material that `distributions` is undeclared in `CoreDataset`, only that it is undeclared in `Dataset`. `path` is documented in the digest as a key on `FileCollection`.

**What changed:** the `distributions` block is still present in the reconciled core record, with three entries at the same three paths. What changed is its content:

- The two `source_caveats` asserting that `format` and `media_type` are "enumerated" ranges with no Apache Parquet term were revised. The `features/` entry now carries a caveat explaining that the collection mixes Parquet and TSV and that the single-valued `format`/`media_type` slots therefore take no value; the `metadata/` entry's caveat now says "the permitted values for those slots include no Apache Parquet term" rather than asserting an enumeration the digest does not show. The `phenotype/` entry retains `format: TSV` and `media_type: text/tab-separated-values` and needs no caveat.
- The `features/` entry no longer declares `format: TSV` / `media_type: text/tab-separated-values`. The audit was right that declaring TSV for a directory that is nine-tenths Parquet mislabels the collection; the declaration was dropped rather than corrected, because the slots are single-valued and the collection is mixed.
- Each entry now opens its `notes` with the collection's name ("Derived audio features", "Phenotype tables", "Recording metadata"), which the original core block had dropped when it replaced `file_collections`.

**What did not change:** the block was not removed, and `file_collections` was not restored to the core record. I could not verify from the supplied digest that `file_collections` is a `CoreDataset` slot or that `distributions` is not, so removing one in favour of the other on the strength of a `Dataset`-only digest would have been a guess. The full record retains `file_collections` unchanged in structure. This is the largest unresolved item in this reconciliation and is flagged as such in §4.

### 2.2 Medium severity

**`at_risk_populations.at_risk_groups_included` (finding 4, both records).**

Changed from `false` to `true` in both records. The audit's reasoning is sound and self-contained: the same record's `human_subject_research.special_populations` lists mild cognitive impairment, Alzheimer's disease, other dementias, and active psychiatric conditions in the adult cohort, and the IRB protocol records that mood-cohort questions "can lead to possible discomfort and could trigger negative emotions." A `false` boolean sitting beside that content asserts something the bundle does not support.

Alongside the boolean flip:

- `special_protections` was rewritten from one entry to three. The first now names the cognitively impaired and psychiatrically ill adult cohorts explicitly and records the consent safeguards that apply to them (English-language consent capacity requirement, thirty-minute explanation, teach-back check). The second records the mood-cohort discomfort risk. The third retains the point that minors are absent from the adult release.
- `source_caveats` was rewritten to state plainly that the bundle never uses the phrase "at-risk population", that the boolean is therefore an assessment rather than a transcribed value, and why it was assessed as `true`. The pediatric-assent material was retained but now explicitly notes that the pediatric cohort is not this record's referent.
- The `human_subject_research.special_populations` entry in both records was expanded to name the specific adult conditions (previously "cohorts of adults with cognitive impairment, dementia and active psychiatric conditions"; now naming bipolar disorder, schizophrenia and depression) and to attribute the 18–120 eligibility range to the v2.0.0-era study metadata rather than stating it flat.

**`instances[1].data_substrate` (finding 3, both records).**

Changed from `B2AI_SUBSTRATE:30` (Parquet) to `B2AI_SUBSTRATE:49` (Waveform Data). The `instance_type` string was also amended from "released as derived features" to "released as derived feature tensors", and a sentence was appended to the entry's `notes` explaining that the Parquet packaging is recorded under `distribution_formats` rather than as the instance substrate. The audit was correct that the original value encoded the container rather than the thing.

**Core-record omissions (findings 6–16).**

The audit listed eleven slots the full record populates and the core record did not. Because the `CoreDataset` inventory was not supplied, I could not distinguish "omitted although available" from "not a core slot". I resolved this by folding the substance into slots the core record demonstrably already carries, rather than by adding top-level slots whose availability I could not confirm:

| Full-record slot | Where it now appears in core |
|---|---|
| `collection_consents` | `informed_consent[0].consent_scope` — the registered/controlled dissemination tiering sentence was moved in |
| `consent_revocations` | `informed_consent[0].withdrawal_mechanism` — the "cannot be removed once collection is completed" rule, the longitudinal-retention rule, and the satisfaction survey were all folded in (previously only the first was, partially) |
| `collection_notifications` | `informed_consent[0].notes` — new; the IRB consent-process description including the teach-back check |
| `direct_collection` | `acquisition_methods[0].acquisition_details` — the direct-collection sentence and the in-clinic/remote qualifier were appended |
| `subsets` | `subpopulations` — five new entries, one per cohort, each carrying the cohort's diagnosis list in `identification` and its gold-standard validation methods in `distribution` |

Five slots (`participant_privacy`, `participant_compensation`, `relationships`, `third_party_sharing`, `citation`) were **not** carried into the core record and remain absent. Reasons in §3.

**`collection_consents` duplication (finding 5, full record).**

The second `CollectionConsent` entry — the restatement of the Consent Type answers — was removed from the full record. That material is carried by `license_and_use_terms.data_use_permission` and now also by `informed_consent[0].consent_scope`, which was extended in the full record to include the same sentence. `collection_consents` now holds one entry.

### 2.3 Low severity

**`creators[2]` collapsing twelve institutions (finding 18, both records).**

Split. The single Creator object holding twelve `affiliations` became eleven separate Creator objects, one per collaborating institution (twelve institutions, but University of South Florida and Weill Cornell Medicine already appear via the two PI entries, so the collaborator list retains its own entries for both — the reconciled records carry thirteen Creator objects in total: two PI entries plus eleven institution entries). The `source_caveats` explaining the schema's lack of a Creator name field, and the note about 50+ contributors and 120 named authors, moved to the last entry.

**`ethical_reviews[1]` naming three bodies in one scalar (finding 24, both records).**

Split into three EthicalReview objects: Mount Sinai Hospital Research Ethics Board, Hospital for Sick Children Research Ethics Board, University of Toronto Research Ethics Board. The genomic-data note was attached to the two institutions the bundle names for it (Mount Sinai and Toronto). `ethical_reviews` now holds five entries in both records.

**`subsets` / `file_collections` fragment anchoring (finding 20, both records).**

Fragments were re-anchored from `https://physionet.org/content/b2ai-voice/3.1.0/#…` to `doi:10.13026/8xbn-nq66#…`, matching the record's own `id`. This affects five `subsets` ids and three `file_collections` ids in the full record. The core record's `subsets` were folded into `subpopulations`, which takes no id, so the change does not surface there.

**`description` — "five sites in the United States and Canada" (finding 21, both records).**

Rewritten to "five sites in North America … Data was collected in the United States and Canada," which is what the two sources severally state. A sentence was added to the top-level `source_caveats` recording that the bundle does not say how the five sites distribute across the two countries.

**`description` — unqualified 18–120 eligibility (finding 22, both records).**

Rewritten to "the study metadata published against version 2.0.0 gives adult eligibility as 18 to 120 years of age…". The top-level `source_caveats` now records that these bounds come from v2.0.0-era metadata which itself flags that eligibility would be updated when a pediatric cohort was introduced.

**`id` pinned to a version DOI (finding 17, both records).**

The `id` was left as `doi:10.13026/8xbn-nq66`. A sentence was added to the top-level `source_caveats` in both records naming the concept DOI, noting where it is recorded, and stating that the record is pinned to a fixed release despite semi-annual updates. Rationale in §3.

**`maintainers[3]` — Health Data Nexus (finding 25, both records).**

The entry was left in place but reworded from "maintains the technical infrastructure for that earlier feature-only release" to "hosted version 1.0 of the dataset and … maintained the technical infrastructure for that earlier feature-only release" (past tense), and a `source_caveats` was added recording that this is the dispreferred tier-2 claim and that the entry applies to version 1.0 only.

**`errata[0].erratum_url` (finding 27, both records).**

The `erratum_url` was removed. The audit was right that the version landing page is not an erratum location. The `source_caveats` was extended to say explicitly that no `erratum_url` is given because no distinct erratum document exists, and that the release notes appear on the page recorded under `page`.

**`data_protection_impacts` (finding 28, both records).**

The slot was retained; its `source_caveats` was rewritten to state that no DPIA is reported, that the recorded work is adjacent activity, and that the slot "should be read as describing that activity rather than as asserting that a DPIA exists."

**`confidential_elements[0]` (finding 29, both records).**

`confidential_elements_present` remains `false`. The `source_caveats` was rewritten to open with "This boolean records the project documentation's own answer and should be read against evidence pointing the other way," and to close by naming the tension directly: "The false value and this caveat pull in opposite directions."

**`cleaning_strategies` (finding 30, both records).**

Both entries retained. The first entry's `source_caveats` was rewritten to say the audit protocol "is quality assessment rather than cleaning; no cleaning transformation of the data is reported." The second entry, which previously carried no caveat of its own in the full record, now carries one stating that transcript review is a privacy measure rather than a cleaning step.

**`source_caveats` truncation in core (finding 32).**

The core record's top-level `source_caveats` now quotes both corrupted award-identifier forms verbatim, matching the full record.

**`distribution_formats` media types (incidental).**

`media_type: text/tab-separated-values` and `media_type: application/json` were added to the TSV and JSON entries in both records. The Parquet and WAV entries carry no media type. This was not an audit finding; it aligns the two records' distribution descriptions with the media types the core `distributions` block already used.

---

## 3. Findings left as-is, and why

**Finding 17 — version DOI as `id`.** Left as `doi:10.13026/8xbn-nq66`. The record's stated referent is version 3.1.0 specifically; the description, `instances` counts, `variables` record counts and `file_collections` all describe that release. Switching `id` to the concept DOI would make the identifier float free of the content it names. A caveat was added instead.

**Finding 19 — Grant `id` as a RePORTER URL.** Unchanged. The audit itself recorded "no defect" — the digest declares no prefix for NIH RePORTER project records, so a URL is the correct `uriorcurie` fallback, and the bundle supplies the URL verbatim.

**Findings 23, 26, 33, 34, 35 — positive checks.** Organization objects carrying only `name` with no invented registry identifiers; `collection_timeframes` omitting dates the bundle does not supply; `conforms_to_class` correct in each record; bare `doi`; `uri`-ranged slots carrying URLs. All correct as written; nothing changed. (`collection_timeframes.source_caveats` gained the clause "so `start_date` and `end_date` are omitted" to make the omission explicit, but the values are unchanged.)

**Finding 31 — `notes` carrying the AI-readiness rubric.** Left in place in both records. The audit called it "defensible"; no better-fitting slot exists in the inventory, and the rubric is genuinely residual dataset-level assessment.

**Findings 9, 10, 11, 12, 16 — `participant_privacy`, `participant_compensation`, `relationships`, `third_party_sharing`, `citation` absent from core.** These remain absent from the core record. Unlike the five slots folded in under §2.2, these have no obvious host slot in the material the core record demonstrably carries: privacy techniques do not belong inside `is_deidentified.deidentification_details` without distorting that field, compensation has no adjacent field at all, and `citation` is a top-level scalar whose presence in `CoreDataset` I could not confirm. Adding top-level slots on an unverified inventory risks validation failure; folding them into ill-fitting hosts risks the "content in the wrong field" defect the v2 rules warn against. All five remain in the full record.

**Finding 14 — `variables` absent from core.** Unchanged, for the same reason: the audit itself scoped the finding as conditional on `variables` being a `CoreDataset` slot, which the supplied digest does not establish.

**Finding 15 — `file_collections` absent from core.** Unchanged; see §2.1.

---

## 4. Outstanding risk

The single largest uncertainty in this reconciliation is the `CoreDataset` slot inventory. The schema digest supplied to this run covers `Dataset` only. Every decision about what the core record may or may not carry — the `distributions`-versus-`file_collections` question, the five un-folded omissions, `variables`, `citation` — turns on an inventory I could not read. Where the choice was between a change that might fail validation and a caveated non-change, I took the non-change. If `distributions` is in fact undeclared in `CoreDataset`, the core record will fail validation and the correct repair is to replace that block with `file_collections` carrying `id`, `path`, `collection_type` and `description` as in the full record.

Secondary: the `at_risk_groups_included: true` flip is an inference from the cohorts the bundle describes, not a value any source states. The caveat says so. A reader who reads "at-risk population" more narrowly than I have — as covering only the regulatory categories named in the slot description (minors, pregnant women, prisoners) — would set it back to `false`, and the caveat gives them what they need to do that.