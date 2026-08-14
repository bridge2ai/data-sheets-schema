# Phase 4 Reconciliation — CM4AI

**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/CM4AI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/CM4AI_d4d_core.yaml`
**Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Referent:** CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`

---

## 1. What the audit found

Twenty-four findings: three high, nine medium, ten low, and five informational confirmations.

The provenance boundary held. No finding alleged unsupported factual content, no prior D4D record was consulted, and the U2OS / *Nature* material — a distinct dataset from a different cell line and a different publication — was correctly excluded from both records rather than absorbed into the CM4AI release. Disclosed conflicts (release-date discrepancy, file-date anomaly, protein-count divergence, project-end-date conflict) were confined to `source_caveats` and did not leak into names, identifiers or values. Enum usage was clean across every enum-ranged slot checked; B2AI substrate and topic terms were apt rather than approximate.

The defects were structural and, with two exceptions, confined to the core record. They fall into four groups:

1. **An undeclared slot in the core record.** A `distributions` block carrying undeclared keys (`path`, `md5`, `bytes`) where the full record had used `file_collections` correctly. This was the only finding likely to fail validation outright.
2. **Projection drift.** Content that moved between slots on the way from full to core — `subsets` → `resources`, `collection_consents` → `informed_consent` — losing declared structure without a stated reason.
3. **Declared structure left in prose.** Creator affiliations stated in `notes` while the declared `affiliations` field stayed empty; a 47-author list represented by seven objects.
4. **Two entity merges.** A committee name and a contact drawn from two sources that the evidence keeps separate, and an instance count scoped to the project rather than to the release it was attached to.

---

## 2. Changes to the full record

No top-level slot was added or removed. All changes are within object values.

| Slot | Change | Reason |
|---|---|---|
| `creators` | Expanded from 7 objects to 47, one per named author in the June 2026 Dataverse citation | The bundle names 47 distinct authors; the slot is multivalued. Selecting seven leads was neither stated nor justified. Truncation without disclosure misrepresents the credit record. |
| `creators[*].affiliations` | Populated as `Organization` objects on every Creator; institutional statements removed from `notes` where they duplicated the new field | Affiliation is a declared field with a declared range. Carrying it as free text inside `notes` populates the object's shape without populating its structure. `Organization` requires only `id`, so name-bearing objects were available throughout. |
| `creators[*].id` | ORCID used where the citation supplies one; omitted otherwise | The bundle gives ORCIDs for most but not all authors. No identifier was synthesised for the remainder. |
| `instances[0].counts` | Removed; the figure 53,788 retained in `notes` with its scope stated | The count is the project-wide portal total across all releases and both cell lines. Attached to a release-scoped MDA-MB-468 imaging Instance it does not count the instances of the object it sits on. A caveat disclosed the mismatch but the value still asserted it. |
| `acquisition_methods` | Fifth `InstanceAcquisition` object (inferred cell maps) removed | It documented an acquisition method for content the record elsewhere states is not in this release. The fact is already carried by `known_limitations` ("does not contain predicted cell maps"), which is where it belongs. |
| `data_governance.committee_name` | Changed to `Data Governance Committee` | The Dataverse release metadata names a "Data Governance Committee" with Parker as contact; the preprint names a "Data Access Committee". The sources do not state these are the same body. Pairing the preprint's name with the metadata's contact merged two entities the evidence separates. The preprint's term now sits in `notes`, with the open question retained in `source_caveats`. |
| `data_governance.committee_contact.id` | Changed from ORCID to `mailto:jillianparker@health.ucsd.edu` | The bundle supplies an email, not an ORCID, for the governance role. The ORCID belongs to "Parker J" in the author list; equating the two was a reasonable but unstated inference. The email is the identifier the evidence actually attaches to this role. |
| `ethical_reviews` | Second `EthicalReview` object added for Bélisle-Pipon | `contact_person` is single-valued, but the slot is multivalued and the bundle names two ethical review contacts. The second reviewer was previously reachable only through `review_details` prose. |
| `data_collectors` | Single "depositing and packaging institutions" object split into four, one per production location (UCSD, UCSF, Stanford, UVA) | The slot is multivalued and the bundle names four institutions distinctly. One object describing four entities does not represent what the slot declares. |

---

## 3. Changes to the core record

| Slot | Change | Reason |
|---|---|---|
| `distributions` | **Removed** | Not declared anywhere in the schema. Its keys `path`, `md5` and `bytes` are likewise undeclared; checksums are carried by `DistributionFormat.checksum`, and per-file grouping by `FileCollection`. This block would have failed validation. |
| `file_collections` | **Added**, mirroring the full record's `FileCollection` objects | Restores the per-file content the removed block was carrying, in the slot that declares it. `collection_type`, `file_count` and `path` populated where the release listing supports them. |
| `distributions[*].conforms_to_standard` | Removed with its parent | `conforms_to_standard` is declared on `Dataset`, `DataSubset` and `FileCollection`, not on a per-file object of undeclared class. The dataset-level `RO_CRATE` assertion is unaffected. |
| `resources` | **Removed**; two cell-line arm objects restored to `subsets` as `DataSubset` | The full record modelled the arms as `DataSubset` with `is_data_split: false` and `is_subpopulation: false` populated. Projecting into `resources` (range `Dataset`) dropped both flags silently. `subsets` is the slot that carries the discrimination. |
| `informed_consent` | **Removed** | Every declared field was empty; the object's own `source_caveats` stated that no field could be populated from evidence. An object of the correct shape holding none of its structure has not answered the field. |
| `collection_consents` | **Restored**, matching the full record | The ethical-sourcing statement belongs in the slot the full record used. `informed_consent` asks a different question (procedural consent record) from `collection_consents` (consent obtained for collection); the substitution was unmarked. |
| `citation` | **Added** | Re-checked against `data_sheets_schema_core_all.yaml`: `citation` is declared on `CoreDataset`. The prior `source_caveats` claim that it is not has been removed. Its omission had lost the 47-author citation from the core record entirely. |
| `total_file_count` | **Added** (`10`) | Same evidence as the full record — ten archives on the June 2026 landing page. The asymmetry had no stated reason. |
| `distribution_formats[0].download_url` | **Added**, matching the full record | Declared on `DistributionFormat` and supported by the same landing-page URI already in `access_urls`. |
| `creators` | Expanded to 47 objects with `affiliations` populated | As for the full record. |
| `instances[0].counts` | Removed; figure retained in `notes` | As for the full record. |
| `data_governance` | `committee_name` and `committee_contact.id` corrected | As for the full record. |
| `ethical_reviews` | Second object added | As for the full record. |
| `data_collectors` | Split into four objects | As for the full record. |
| `source_caveats` | Renumbered; the schema claim in caveat 11 removed; a caveat added recording the `subsets`/`resources` and `collection_consents`/`informed_consent` corrections | A caveat should record what the evidence leaves open, not assert a schema fact that turned out to be wrong. |

---

## 4. Left as-is

| Item | Disposition |
|---|---|
| `conforms_to_standard` limited to `RO_CRATE` | Correct. The JSON-LD/RDF serialisation, EVI and Schema.org vocabularies and ARK identifier scheme described in `conforms_to` prose have no corresponding enum member. Omitting rather than approximating is the required behaviour. |
| `total_size_bytes` omitted from both records | Deliberate, and confirmed as such. The ten published file sizes are rounded display values (`4.6 GB`, `3.8 GB`); no exact byte total is derivable, and an aggregate of rounded figures would assert a precision the bundle does not supply. |
| `data_collectors[*].role` free-text values | Permissible. `DataCollector.role` is not enum-constrained, unlike `Maintainer.role`. The plural-entity problem has been fixed by splitting the objects; the remaining free-text values are accurate. |
| Dataset-level `id` = release DOI, `name` = programme name | Consistent and documented. `description` resolves the referent explicitly to the June 2026 release, and both records hold to that choice throughout. No change needed. |
| All disclosed conflicts (caveats 1–5) | Retained. The U2OS/*Nature* boundary, the release-date discrepancy, the file-date anomaly, the protein-count divergence and the project-end-date conflict are each stated rather than resolved. This is the correct handling; resolving any of them in a slot value would be the defect. |
| B2AI substrate and topic terms | Unchanged. Substrates 19, 58, 59, 64 and topics 19, 26, 28, 34 were each confirmed as fitting rather than approximating. |
| Enum values across `bias_type`, `limitation_type`, `relationship_type`, `credit_roles`, `collection_type`, `compression`, `data_use_permission`, `confidentiality_level`, `hipaa_compliant`, `Maintainer.role` | Unchanged. No undefined member found. |

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots, before | 61 | 34 |
| Populated top-level slots, after | 61 | 36 |
| Top-level slots added | 0 | 4 (`file_collections`, `collection_consents`, `citation`, `total_file_count`) |
| Top-level slots removed | 0 | 2 (`distributions`, `informed_consent`) |
| Top-level slots relocated | 0 | 1 (`resources` → `subsets`) |
| Objects added | 41 | 41 |
| Objects removed | 1 | 3 |

**Validation**

```
linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  …/CM4AI_d4d.yaml                          → PASS
linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset  …/CM4AI_d4d_core.yaml                 → PASS
```

**Reconciliation:** complete. All three high-severity findings resolved. All nine medium-severity findings resolved. Of the ten low-severity findings, seven resolved and three closed as correct-as-written with the reasoning recorded above. The five informational confirmations required no action.

The two records now agree on referent, on the seven objects that had drifted between slots, and on every value the audit identified as divergent without a stated reason. No factual claim was added, removed or altered in either record beyond the scope corrections described; every value remains traceable to the declared bundle.