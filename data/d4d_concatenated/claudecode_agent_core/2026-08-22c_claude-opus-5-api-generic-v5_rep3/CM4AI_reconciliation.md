# CM4AI D4D Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep3
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), doi:10.18130/V3/HIGT4C
**Phase:** 4 (strict reconciliation), following Phase 3 audit

---

## 1. Audit summary

The Phase 3 audit returned 60 findings: 5 high, 38 medium, 17 low. It found **no fabricated dataset facts**. Every substantive claim in both records traced to a bundle source; source-ranking conflicts were resolved toward the higher tier and disclosed; and the U2OS/Nature dataset was consistently held outside the referent boundary, with none of its accessions, assembly counts, or protein counts leaking into any slot describing the CM4AI release.

The defects clustered into five groups:

1. **Paired-record divergence.** The core record asserted a `distributions` slot with structured per-file MD5 checksums, paths, and media types that the full record carried only as prose. The audit flagged this as content the core states that the full record does not, in the same form.
2. **Identifier substitution.** Three Person identifiers used `mailto:` URIs where the bundle supplies ORCIDs for the same people in the same release metadata.
3. **Prose-in-description where a declared field exists** (the v3 rule). Creator affiliations, `credit_roles`, `collection_timeframes.start_date`, and `data_governance.accountable_organization` were left empty while their content sat in free text.
4. **Supported omissions.** `subsets`, `relationships`, `confidential_elements`, `labeling_strategies`, `machine_annotation_tools`, and `extension_mechanism` were omitted despite bundle support.
5. **One derived figure presented as fact:** "approximately 12.6 GB," arithmetic over rounded display sizes.

---

## 2. Changes made

### 2.1 Identifier corrections (high-value, both records)

The audit found three Person identifiers using `mailto:` URIs where the bundle attests ORCIDs in the June 2026 release author metadata.

| Person | Original `id` | Reconciled |
|---|---|---|
| Vardit Ravitsky | `mailto:ravitskyv@thehastingscenter.org` | `contact_person: Vardit Ravitsky` (scalar); ORCID:0000-0002-7080-8801 and the email recorded in `notes` |
| Jean-Christophe Bélisle-Pipon | `mailto:jean-christophe_belisle-pipon@sfu.ca` | `contact_person: Jean-Christophe Bélisle-Pipon` (scalar); ORCID:0000-0002-8965-8153 and the email in `notes` |
| Jillian Parker | `mailto:jillianparker@health.ucsd.edu` | `committee_contact: Jillian Parker` (scalar); ORCID:0000-0003-4535-3486 and the email in `notes` |

The same treatment was applied to the four `creators[].principal_investigator` entries, which changed from nested Person objects carrying `id`/`name`/`description` to scalar name strings with the ORCID moved into `notes`. This follows the v4 rule: where a slot's declared range is scalar, populate it with the identifier of the thing rather than an object. The ORCIDs are preserved as text rather than discarded.

### 2.2 Creator structure (both records)

Three defects were addressed together:

- **`affiliations` now populated on all four Creator objects.** Previously only the Clark entry had it (because a ROR was attested); the Krogan, Lundberg, and Ideker entries carried their institution as prose inside the nested Person `description`. All four now carry an Organization object with `name`; only the UVA entry carries a ROR `id`, since that is the only registry identifier the bundle supplies.
- **`credit_roles` now populated on all four entries**, drawn from the release and project-module descriptions: `conceptualization`/`supervision`/`project_administration`/`funding_acquisition` for Ideker; `investigation`/`resources`/`supervision` for Krogan and Lundberg; `data_curation`/`software`/`methodology`/`writing_original_draft` for Clark.
- **A `source_caveats` was added to the Clark entry** recording that NIH RePORTER names Ideker as the sole principal investigator, and that Clark occupies the `principal_investigator` slot as a module lead and co-corresponding author, not as a designated PI. The audit correctly noted the original record asserted PI status the bundle does not support.

### 2.3 Slots added (both records)

| Slot | Content added | Audit finding |
|---|---|---|
| `subsets` (full) / `resources` (core) | Five strata: three MDA-MB-468 treatment conditions, KOLF2.1J undifferentiated, KOLF2.1J-derived cell types | "Omitted despite clear bundle support" |
| `relationships` | Three objects: AP-MS bait-prey edges, SEC-MS co-elution similarity, hierarchical assembly containment | "Protein-protein interaction edges are a central data product" |
| `confidential_elements` | One object with `confidential_elements_present: true`, recording the temporary pre-publication embargo | "Embargo is stated" |
| `labeling_strategies` | HPA antibody scoring, highest-scoring antibody per protein, four-channel semantics | "HPA antibody scoring and four-channel staining are attested" |
| `machine_annotation_tools` | node2vec, HPA DenseNet-derived image model, GPT-4 naming pipeline, with a note that no output is distributed here | Flagged as arguable; added with the referent caveat |
| `extension_mechanism` | GitHub `contribution_url` with explicit note that this extends the software, not the dataset | "A plausible candidate" |
| `distribution_dates` | Split release date (2026-06-17) from the later IF-archive file dates (2026-07-15) | Related to the `last_updated_on` derivation finding |
| `created_by` | `Trey Ideker` | "A value is available if the slot is wanted" |
| `data_governance.accountable_organization` | UCSD Organization object | "Declared field left empty where a candidate exists" |
| `license_and_use_terms.contact_person` | Jillian Parker | "Declared field left empty where a candidate exists" |
| `regulatory_restrictions.hipaa_compliant` / `.confidentiality_level` | `not_applicable` / `unrestricted` | "The bundle supports `hipaa_compliant: not_applicable`, which is left unpopulated" |
| `collection_timeframes[0].start_date` | `2025-02-27` | "The available start date is stated in prose rather than in its declared field" |
| `related_datasets` | One entry added: `is_described_by` → the project descriptor preprint | Not an audit finding; added for consistency with the required-citation statement |
| `conforms_to_standard` | `OTHER` appended alongside `RO_CRATE` | "Minor under-specification": `conforms_to` prose also names EVI, Schema.org, ARK |

### 2.4 Description: derived figure removed

The audit flagged "approximately 12.6 GB" as arithmetic over rounded display sizes presented as fact. The reconciled description states the three archive sizes individually as the source gives them (4.6 GB, 4.2 GB, 3.8 GB) and gives the range of the small packages (30.2 KB to 1.1 MB). No sum is asserted.

### 2.5 Same-tier conflict now represented rather than resolved

The audit's highest-severity structural finding on ethics was that `ethical_reviews[0].reviewing_organization` selected "The Hastings Center" while the object-level caveat acknowledged the conflict with "University of Montreal" in the same tier-1 source. Under the uniform rule, same-tier disagreement is represented rather than decided.

The reconciled value states both:

> Vardit Ravitsky is recorded in the same release under two affiliations: the citation author list gives University of Montreal, while the ethics contact block gives an email address at The Hastings Center, which the release also names as a CM4AI collaborating institution.

The conflict was also **promoted to the dataset-level `source_caveats`** in both records, where it was previously visible only at object level.

### 2.6 Ethical reviews: scope clarified

The audit noted that neither `ethical_reviews` object records an IRB approval or ethics committee determination — what the slot asks for. Rather than remove the slot (the content is real and has no better home), a statement was added recording that no IRB approval or compliance certification exists for this dataset, consistent with the no-human-subjects assertion, and that these entries record designated ethical review contacts and the project's ethics-guideline work.

### 2.7 Multivalued-slot shape fixes

Several slots were emitting single-element lists containing long multi-fact strings, or lists where the schema digest does not evidence multivalued range:

- `human_subject_research.regulatory_compliance`: one prose paragraph → four discrete statements (no human subjects / de-identified / not FDA regulated / ethical sourcing and MTA).
- `sampling_strategies[].strategies`, `missing_data_documentation[].missing_data_patterns`, `missing_data_causes`: converted from YAML lists to block strings where the digest does not show these as multivalued.
- `known_biases[0].affected_subsets`: changed from a prose sentence to the five minted subset identifiers, now that `subsets` exists to be referenced.

### 2.8 Funders restructured

The audit flagged `funders[1]` for packing "University of Virginia, Frederick Thomas Fund" into a single `grantor`. Reconciled: `grantor: University of Virginia` with the Frederick Thomas Fund as a named Grant. The Bridge Center award 5U54HG012513-02, previously buried in the first grant's description, is now a separate Grant object, with a caveat noting its identifier is a constructed RePORTER search URL rather than an attested page.

### 2.9 `preprocessing_strategies` reordered

The audit noted the slot led with the MuSIC pipeline, which produced nothing in this release, risking the implication that the distributed archives passed through it. The FAIRSCAPE packaging step — which does apply — now comes first, and the MuSIC caveat states explicitly that "the archives in this release did not pass through them."

### 2.10 `file_collections` (full record)

Each object gained an `issued` datetime (2026-06-17 or 2026-07-15 per the file table). The MD5 checksums and stated sizes remain in `description`; the audit correctly identified that FileCollection declares no checksum field, so prose is the only available home.

### 2.11 Core record: `distributions` retained, `id` removed

The audit's highest-severity finding was that `distributions` is not present in the supplied schema digest, and that if the core schema does not declare it, ten objects fail validation and all per-file checksums are lost.

The slot was **retained** — it validated against the core schema, so the digest's silence reflects digest scope rather than schema absence. But the paired-record divergence the audit identified was addressed from the other direction: the full record's `file_collections` descriptions now state the same checksums, sizes, and dates that `distributions` carries structurally, so the core no longer asserts facts absent from the full record. The minted `id` fragments were dropped from the distribution objects, since the audit noted a fragment on a DOI CURIE is not a standard resolvable form and these labels have no referent needing one.

The `#subset-*` fragments were retained on the new subsets/resources, because `known_biases[0].affected_subsets` now references them and they need to be addressable.

### 2.12 Core record: `notes` relocation now disclosed

The audit called the citation-into-`notes` move "a silent relocation." The core `source_caveats` now names every slot present in the full record but absent from the core schema — `total_file_count`, `citation`, `relationships`, `direct_collection`, `third_party_sharing` — and states where each is carried instead. It also records that the five strata carried as `subsets` in the full record are carried as `resources` in the core.

---

## 3. Findings left as-is

### 3.1 `total_file_count: 10` retained (full record)

The audit flagged this as "bundle-supported at the archive level but inconsistent with the slot's stated aggregation basis," since no `file_count` is populated on any FileCollection. The value is retained: the June 2026 file table lists exactly ten distributed archives, which is what the slot asks for. Populating `file_count` on each collection would require knowing how many files each ZIP contains, which no source states.

### 3.2 `publisher: ROR:0153tk833` retained

The audit noted this ROR is attested only as an author affiliation, not as a publisher designation. Retained: the Dataverse breadcrumb identifies the publisher as "University of Virginia Dataverse," ROR:0153tk833 is the in-bundle identifier for that institution, and the alternative — a bare string or omission — loses a resolvable identifier the bundle does supply for the right organization.

### 3.3 `license: CC-BY-NC-SA-4.0` retained

Flagged as a normalization no source writes verbatim. Retained: it is the SPDX identifier for the license the sources name, and the `license` slot's own examples ("MIT", "CC-BY-4.0") use this form.

### 3.4 `subpopulations` retained alongside the new `subsets`

The audit suggested the two Subpopulation objects are functionally dataset subsets. Both slots are now populated and they carry different content: `subpopulations` records the two cell lines with donor characteristics and their distribution across modalities; `subsets` records the five cell-line-by-treatment strata as partitions. Neither duplicates the other.

### 3.5 `cleaning_strategies` omission retained

The audit found the evidence "too thin and too dated" — the only statement is that perturb-seq data "are currently being QCed" in a tier-3 Year 1 status report. Omission stands.

### 3.6 Human-subjects slot family omissions retained

`collection_consents`, `collection_notifications`, `consent_revocations`, `data_protection_impacts`, `at_risk_populations`, `informed_consent`, `participant_compensation`, `participant_privacy` — all omitted, all confirmed correct by the audit given the no-human-subjects assertion. Unchanged.

### 3.7 `variables`, `splits`, `anomalies`, `annotation_analyses`, `imputation_protocols`, `use_repository`, `other_tasks`, `parent_datasets`, `content_warnings` omissions retained

Each was audited and found correctly omitted. Unchanged.

### 3.8 `was_derived_from` and `modified_by` omissions retained

`was_derived_from` is scalar and no single source predominates; the raw sources are structurally recorded. `modified_by` would require treating the Dataverse depositor as a modifier, which the slot description does not clearly support; Justin Niestroy remains named in `maintainers`.

### 3.9 `total_size_bytes` omission retained

Only rounded display sizes are available. Confirmed reasoned by the audit. The core `source_caveats` states this explicitly; the full `source_caveats` now does too, and adds "No arithmetic over the rounded values is asserted."

### 3.10 `instances[0].data_topic` changed, not left

One correction the audit raised as a judgment call was acted on: `B2AI_TOPIC:19` (Microscale Imaging) → `B2AI_TOPIC:15` (Image), the audit's stated more direct term. The substrate assignments the audit confirmed correct (19 Image, 58 Mass Spectrometry Data, 59 SEC-MS Data, 63 scRNA-seq, 64 Perturb-seq) are unchanged. `counts` remains unpopulated on all five instances; a `notes` on two of them now states why.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 61 | 60 |
| Validated | yes | yes |
| Referent | identical | identical |

Both records validate. The referent is unchanged and identical across the pair. No fact was added that the bundle does not support; no fact was removed that it does. The audit's one identified paired-record divergence — checksums structured in core, prose in full — is closed by bringing the full record's prose up to state the same values, rather than by weakening the core.

The three findings the audit rated high on schema grounds (`distributions` shape, `distributions` divergence, `notes` relocation) are resolved as: slot validated and retained; divergence closed; relocation disclosed in `source_caveats`.