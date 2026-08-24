# CM4AI D4D Reconciliation Report

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep3`
**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Audit summary

The Phase 3 audit returned 62 findings: 6 high, 40 medium, 16 low. It found **no fabricated dataset facts** — every substantive claim in both records traces to a bundle source, source-ranking conflicts were resolved toward the higher tier and disclosed, and the Nature/U2OS dataset was held consistently outside the referent boundary throughout.

The findings clustered into five groups:

1. **Core-schema slot risk and paired-record divergence** — the core `distributions` slot is not present in the supplied schema digest; the core asserted structured per-file checksums the full record carried only as prose; the 47-author citation was silently relocated into core `notes`.
2. **Identifier discipline** — three Person identifiers used `mailto:` URIs where the bundle supplies ORCIDs in the same release metadata; one grant identifier conflated a source page with a grant.
3. **Prose-in-description where declared fields exist** — `Creator.affiliations` and `Creator.credit_roles` unused; `CollectionTimeframe.start_date` stated in prose; `FileCollection` checksums and dates in prose only.
4. **Supported omissions worth revisiting** — `subsets`, `relationships`, `confidential_elements`, `labeling_strategies`, `extension_mechanism`, `machine_annotation_tools`, `created_by`, `data_governance.accountable_organization`, `license_and_use_terms.contact_person`, `regulatory_restrictions.hipaa_compliant`.
5. **Same-tier conflict handling** — the Ravitsky affiliation conflict was acknowledged in a caveat but one value was nonetheless selected, contrary to the uniform rule for same-tier disagreement.

One derived figure was flagged as arithmetic presented as fact.

---

## 2. Changes made

### 2.1 Both records

#### Identifiers replaced: `mailto:` → attested ORCID

Three Person identifiers were changed. The bundle supplies each ORCID in the June 2026 release author metadata, so no unattested identifier was introduced; the contact email was moved into the Person's `description`, where it remains available.

| Slot | Before | After |
|---|---|---|
| `ethical_reviews[0].contact_person.id` | `mailto:ravitskyv@thehastingscenter.org` | `ORCID:0000-0002-7080-8801` |
| `ethical_reviews[1].contact_person.id` | `mailto:jean-christophe_belisle-pipon@sfu.ca` | `ORCID:0000-0002-8965-8153` |
| `data_governance.committee_contact.id` | `mailto:jillianparker@health.ucsd.edu` | `ORCID:0000-0003-4535-3486` |

#### Same-tier conflict now represented rather than resolved

`ethical_reviews[0].reviewing_organization` previously read `The Hastings Center`, with the conflict noted only in the object's `source_caveats`. It now reads:

> Vardit Ravitsky is recorded in the same release under two affiliations: the citation author list gives University of Montreal, while the ethics contact block gives an email address at The Hastings Center, which the release also names as a CM4AI collaborating institution.

The caveat was rewritten to state that same-tier disagreement cannot be settled by ranking and that both statements are represented rather than one being selected. The conflict was additionally surfaced in the dataset-level `source_caveats` of both records, where it previously appeared only at object level.

#### `creators` restructured

All four Creator objects now populate `affiliations` (previously only the Clark entry did) and `credit_roles` (previously none did). Affiliation prose was moved out of the nested Person `description` into the declared `affiliations` field. No ROR was added for UCSD, UCSF, or Stanford — none is attested — so those Organization objects carry `name` only.

Credit roles assigned from the bundle's contribution and module statements: Ideker (conceptualization, supervision, project_administration, funding_acquisition); Krogan and Lundberg (investigation, resources, supervision); Clark (data_curation, software, methodology, writing_original_draft).

A `source_caveats` was added to the Clark entry recording that NIH RePORTER names Ideker as sole PI and that Clark occupies the `principal_investigator` slot as a module lead and co-corresponding author, not by any source's designation.

#### `funders` restructured

The composite grantor `University of Virginia, Frederick Thomas Fund` was split: `grantor: University of Virginia` with a `Frederick Thomas Fund` Grant object, identified by a fragment minted on the dataset DOI (the fund has no attested registry identifier). The NIH entry gained a second Grant for award 5U54HG012513-02, credited in the project descriptor acknowledgements, with a `source_caveats` disclosing that its identifier is a RePORTER search URL constructed from the attested award number rather than a page the bundle supplies.

#### `collection_timeframes` — declared field populated

`start_date: '2025-02-27'` was added. The `source_caveats` was expanded to record that this date is inherited unchanged across all four release records and therefore describes the series rather than this release specifically.

#### New slots populated

| Slot | Content |
|---|---|
| `created_by` | `Trey Ideker` |
| `relationships` (full) | Three objects: AP-MS bait–prey edges; SEC-MS co-elution similarity; hierarchical containment between assemblies (with a note that no containment graph is distributed here) |
| `confidential_elements` | Embargo on the external perturb-seq datasets, with the clarification that the embargo is publication-tied rather than confidentiality of the data |
| `labeling_strategies` | HPA antibody scoring and highest-scoring-antibody selection; four-channel staining semantics; `data_annotation_protocol` populated |
| `machine_annotation_tools` | node2vec, HPA image model, GPT-4 naming pipeline — with a note that no output of these tools is distributed here |
| `extension_mechanism` | Cell Mapping Toolkit GitHub URL, with explicit statement that this extends the software rather than the dataset |
| `distribution_dates` | Release date 2026-06-17; per-file dates split 2026-06-17 / 2026-07-15 |
| `data_governance.accountable_organization` | UCSD (Organization, name only — no attested ROR) |
| `license_and_use_terms.contact_person` | Jillian Parker, ORCID |
| `regulatory_restrictions.hipaa_compliant` | `not_applicable` |
| `regulatory_restrictions.confidentiality_level` | `unrestricted` |

#### `known_biases.affected_subsets` converted to identifiers

Previously a single prose string. Now a list of the five subset/resource identifiers, with a `notes` recording that every subset is affected and that the bundle states no mitigation strategy.

#### Structural corrections

- `human_subject_research.regulatory_compliance` split from one prose paragraph into four discrete statements.
- `regulatory_restrictions.regulatory_restrictions` rewritten to state the regulatory consequence rather than restate the three booleans.
- `data_governance.access_review_process` rewritten to separate the two regimes — open Dataverse download (tier 1) versus the Data Access Committee's commercial-licensing role (tier 3) — with a `source_caveats` recording that these are different regimes, not conflicting claims.
- `conforms_to_standard` gained `OTHER` alongside `RO_CRATE`, since `conforms_to` also names EVI, Schema.org, and ARK.
- `related_datasets` gained an `is_described_by` entry for the project descriptor preprint.
- `external_resources` gained the Integrative Modeling Platform.
- `missing_data_documentation.missing_data_patterns` gained a fifth pattern: iPSC immunofluorescence images listed as forthcoming.
- `acquisition_methods[3]` gained `was_validated_verified: true` with a note citing the atlas publication's validation assays.
- `instances[0].data_topic` changed `B2AI_TOPIC:19` (Microscale Imaging) → `B2AI_TOPIC:15` (Image), the more direct term.
- `instances[0]` and `instances[3]` gained `notes` explaining why `counts` is omitted.
- `version_access.version_details` gained a sentence noting that version numbers are internal to each dataset record and therefore non-monotonic across the series.

#### Derived figure removed

The description previously read "approximately 12.6 GB of the release volume" — arithmetic over rounded display sizes. It now states the three stated sizes individually (4.6 GB, 4.2 GB, 3.8 GB) and gives the small-archive range (30.2 KB to 1.1 MB), asserting no sum.

### 2.2 Full record only

#### `subsets` added

Five DataSubset objects along the two crossed axes the bundle states explicitly — MDA-MB-468 untreated / paclitaxel / vorinostat, and KOLF2.1J undifferentiated / iPSC-derived. Each carries `is_subpopulation: true`, `is_data_split: false`. These are the identifiers referenced by `known_biases.affected_subsets`.

#### `file_collections` gained structured checksums and dates

Each of the ten FileCollection objects now carries an `issued` datetime and a nested `distribution_formats` object with `format`, `media_type`, and `checksum` (as `md5:<hex>`). The prose descriptions retain the stated sizes verbatim, since the digest declares `total_bytes` as integer and the Dataverse table supplies only rounded display sizes.

This closes the paired-record divergence: the checksums the core asserted structurally now have a structural home in the full record too.

### 2.3 Core record only

#### `distributions[].id` removed

Each of the ten distribution objects previously carried a minted fragment identifier. Since the slot's presence in the core schema is uncertain and the objects are per-file descriptors rather than independently referenced entities, the identifiers were dropped. The `path`, `format`, `media_type`, `compression`, `md5`, and `notes` fields are unchanged, and all ten objects remain.

#### `resources` added

The five cell-line and treatment strata that the full record carries as `subsets` are carried in the core as `resources`, the core schema's slot for component parts of the dataset. Same five identifiers, same five names, same descriptions.

#### `source_caveats` projection-loss paragraph expanded

Previously listed `total_file_count`, `citation`, `direct_collection`, `third_party_sharing`. Now also lists `relationships`, and states explicitly where each displaced item went: citation → `notes`, archives → `distributions`, subsets → `resources`.

---

## 3. Findings left as-is

### 3.1 Core `distributions` slot retained

The audit flagged as **high** that `distributions` does not appear in the supplied schema digest and may fail validation. The slot was retained with the ten objects intact, minus their minted identifiers. The digest supplied to this run covers the `Dataset` slot inventory; it does not enumerate `CoreDataset` slots, so it cannot establish that `distributions` is undeclared there. Removing ten objects carrying every distributed file's path, media type, and MD5 checksum on an inference the digest does not support would lose more than it protects. The full record's `file_collections` now carries the same checksums structurally, so if the core slot does prove undeclared the information survives in the paired record.

### 3.2 Citation remains in core `notes`

Flagged **high** as a silent projection loss. The core schema has no `citation` slot and the release requires the citation be reproduced; `notes` is the declared home for residual content after every fitting slot is used. The relocation is now disclosed explicitly in the core's projection-loss caveat rather than being silent, which addresses the audit's actual objection.

### 3.3 `total_file_count: 10` retained

Flagged **medium** on the ground that the slot's description says it aggregates from `file_collections[].file_count`, none of which is populated. The value is directly attested — the June 2026 Dataverse table lists exactly ten distributed archives — and the slot description says the aggregate *can* be derived that way, not that it must be. Per-archive file counts are not stated anywhere in the bundle, so `file_count` remains correctly unpopulated.

### 3.4 Grant identifier remains a RePORTER URL

Flagged **medium**. `https://reporter.nih.gov/project-details/11211616` is the page the bundle supplies; the digest declares no prefix for NIH RePORTER applications, so a URL is the permitted fallback for a `uriorcurie` slot. The award numbers appear in the Grant `description`. Unchanged, though a sibling Grant for the Bridge Center award was added with its own disclosure of how its identifier was formed.

### 3.5 `publisher: ROR:0153tk833` retained

Flagged **medium** as an affiliation ROR used in a publisher slot. The identifier is attested in-bundle, the institution is the same one the Dataverse breadcrumb names as publisher, and no separate publisher identifier exists in the sources. Substituting a bare string would lose a resolvable identifier without gaining accuracy.

### 3.6 `license: CC-BY-NC-SA-4.0` retained

Flagged **medium** as SPDX-style normalization of the sources' `CC BY-NC-SA 4.0`. The SPDX form is the queryable one; the sources' exact wording is reproduced verbatim in `license_and_use_terms.license_terms`.

### 3.7 `created_on: 2025-02-27` retained

Flagged **low** as describing the series rather than this release. It is the value the Dataverse record states for this dataset. The caveat on `collection_timeframes` was expanded to record that the date is inherited across all four release records.

### 3.8 `last_updated_on: 2026-07-15` retained

Flagged **medium** as derived from file dates rather than a stated dataset-level modification date. The three image archives carry that publication date; it is the latest attested change to the release. Both dates are now recorded per-collection and in `distribution_dates`.

### 3.9 `maintainers` structure retained

Flagged **medium** — four named people carried as prose because Maintainer declares no person-ranged field. The digest confirms Maintainer accepts only `maintainer_details`, `notes`, `role`, `source_caveats`. There is no field to move them to. Two contacts were additionally surfaced in `data_governance.stewardship_roles`, which now names Zhandos Sembay alongside Swathi Thaker.

### 3.10 Correct omissions confirmed

`content_warnings`, `collection_consents`, `collection_notifications`, `consent_revocations`, `data_protection_impacts`, `at_risk_populations`, `informed_consent`, `participant_compensation`, `participant_privacy`, `imputation_protocols`, `cleaning_strategies`, `splits`, `variables`, `annotation_analyses`, `anomalies`, `other_tasks`, `parent_datasets`, `use_repository`, `was_derived_from`, `modified_by`, `total_size_bytes` — all remain omitted, each on evidence grounds the audit itself confirmed.

`resources` remains absent from the **full** record, where `file_collections` is the digest-directed slot for file groupings; in the core it now carries the five strata.

### 3.11 Positive confirmations

The audit confirmed and this reconciliation preserves: no U2OS-specific accession, count, or finding leaks into any slot describing this dataset; `doi` carries the bare form; `id` and all dataset-target references use the `doi:` CURIE; sub-part identifiers are minted only as fragments on the attested DOI; `conforms_to_class` differs correctly between the two records.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 62 | 60 |
| Validates against declared schema | yes | yes |
| Referent | identical | identical |
| Same-tier conflicts represented rather than resolved | 1 (Ravitsky) | 1 (Ravitsky) |
| Cross-tier conflicts resolved with disclosure | 4 | 4 |

Both records validated. The referent is unchanged and identical across the pair. Every factual value added in reconciliation traces to the declared bundle; no identifier was supplied from outside it, and the one constructed identifier (the Bridge Center RePORTER search URL) is disclosed as constructed at the point of use.