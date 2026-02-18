# AI-Readiness vs Datasheets for Datasets (D4D) Schema Comparison - Version 0

**Status:** Outdated - Historical reference only

**Citation:** AI-readiness for Biomedical Data: Bridge2AI Recommendations
https://www.biorxiv.org/content/10.1101/2024.10.23.619844v4.full.pdf

**Note:** This comparison is from an earlier version and may not reflect current schema structure or AI-Readiness criteria. Preserved for historical reference.

---

| Manuscript ID | Datasheets Schema | Comments - TWC |
|---------------|-------------------|----------------|
| **0.a Findable** | Dataset.doi, Dataset.download_url, Dataset.title, Dataset.description, Dataset.keywords, DatasetCollection | (a) 0.a says put in a FAIR repository w. PIDs. It does not say what the metadata elements need to be and no ref to DCAT so this should be in 0.b. (b) Dataverse & possibly other GREI repos do not support DCAT although there is some term mapping possible from the standards it uses: DDI 2.5 Codebook, DataCite 4.0, & Dublin Core. (c) 0.b also mentions schema.org & there ought to be a mapping available to DCAT from this standard if needed. (d) DCAT terms should be allowed but not mandated if schema.org is used. |
| **0.b Accessible** | Metadata in Dataset (esp. description, publisher, keywords), conforms_to (DCAT/schema.org), license_and_use_terms | Noting that 0.b allows schema.org (and other stds) & does not require DCAT. License and use terms belong in 4.c (duplicated). See 0.a comments for more on DCAT. Schema.org needs to be placed on at least an equal footing w/ DCAT. |
| **0.c Interoperable** | conforms_to, conforms_to_schema, format, media_type, encoding | FAIR I.1-I.3 (Wilkinson et al. 2016) says to use formal KR languages & formal vocabularies - I think that's what was meant by 0.c. rather than using defined schemas. Note the examples given: RDF & JSON-LD. We should clarify in the AI-R article. |
| **0.d Reusable** | license, license_and_use_terms, IPRestrictions, ExportControlRegulatoryRestrictions | 0.d does not mention export controls. If these apply they should be specified in the license or DUA. |
| **1.a Transparent** | was_derived_from, InstanceAcquisition, raw_sources | Where are InstanceAcquisition and raw_sources defined in a vocabulary? |
| **1.b Traceable** | was_derived_from, used_software (in DatasetProperty), PreprocessingStrategy, CleaningStrategy, LabelingStrategy | Preprocessing, labelling, and cleaning strategies would seem best represented in text if relatively simple. |
| **1.c Interpretable** | used_software, PreprocessingStrategy, CleaningStrategy, LabelingStrategy | See comments in 1.b |
| **1.d Key Actors Identified** | Creator (with principal_investigator & affiliation), data_collectors, maintainers | AI-R article 1.d does not specify distinguishing roles beyond creators although specific datasets (in Dataverse) may have additional or different creators to a release as a whole. Consider amending the article to specify the distinct roles. |
| **2.a Semantics** | Dataset.title, Dataset.description, Dataset.keywords, conforms_to, conforms_to_schema | DCAT, Schema.org, MeSH terminologies are all acceptable per AI-R article. |
| **2.b Statistics** | Instance.counts, aggregated details in Dataset.description or a custom DatasetProperty | For complex statistics and quality assessment CM4AI propose to push that onto the dataset providers requiring them to link stats software used with a human readable PDF output of the results. Maybe this is what you mean by "aggregated details" ... |
| **2.c Standards** | conforms_to, conforms_to_schema | |
| **2.d Potential Bias** | SamplingStrategy, Subpopulation, SensitiveElement, Confidentiality, FutureUseImpact | (a) IMO this requirement calls for an explicit textual description of sources of bias. (b) Sensitivity & confidentiality not part of AI-R 2.d they belong in 4.b (c) Rather than flagging sensitive elements per se, the HL7 confidentiality flag should be sufficient. In fact better as it defines how data is to be treated based on sensitivity. |
| **2.e Data Quality** | DataAnomaly, PreprocessingStrategy, CleaningStrategy | CM4AI suggests a combined statistical and data quality approach as noted in 2.b. |
| **3.a Documentation Template** | Entire schema coverage: Dataset + relevant subsets (e.g., Collection, Uses, etc.) | 3.a was meant to specify Gebru et al 2021 Datasheets (and not specifically this template). |
| **3.b Fit for Purpose** | ExistingUse, OtherTask, DiscouragedUse | Define textually. |
| **3.c Verifiable** | hash, sha256, md5 | Dataverse uses UNF (https://guides.dataverse.org/en/latest/developers/unf/index.html) |
| **4.a Ethically Acquired** | EthicalReview, DataProtectionImpact, CollectionConsent, CollectionNotification | (a) All depend on Use of Human Subjects y/n. (b) Would you not want to specify whether Exemption 4? (c) Would you not want to cite IRB & protocol # here? |
| **4.b Ethically Managed** | Deidentification, SensitiveElement, Confidentiality, license_and_use_terms | HL7 confidentiality codes fill the entire bill here. |
| **4.c Ethically Disseminated** | license_and_use_terms, IPRestrictions, ExportControlRegulatoryRestrictions, maintainers | Export controls not mentioned in 4.c and should be covered by license or DUA terms. |
| **4.d Secure** | IPRestrictions, ExportControlRegulatoryRestrictions, Confidentiality, plus distribution constraints | Ditto. |
| **5.a Persistent** | UpdatePlan, VersionAccess, RetentionLimits | (a) 5.a refers to conformance of the archive to privacy and retention guidelines. (b) Update Plan is a nice-to-have and CM4AI will include in our next release for updates thru end of project. |
| **5.b Domain-appropriate** | conforms_to (domain standards), keywords, themes | 5.b only specifies use of domain-specific repositories. |
| **5.c Well-governed** | maintainers, UpdatePlan, ExtensionMechanism | |
| **5.d Associated** | DatasetCollection, external_resources | |
| **6.a Standardized** | conforms_to, conforms_to_schema | |
| **6.b Computationally Accessible** | Dataset.download_url, DistributionFormat, path, external_resources | |
| **6.c Portable** | format, media_type, encoding, compression | |
| **6.d Contextualized** | DataSubset (is_data_split), Splits property, Subpopulation, collection_mechanisms, collection_timeframes | |

---

## Key Observations from v0

### FAIR Principles (0.a-0.d)
- Schema.org and DCAT should be on equal footing
- Export controls should be covered by license/DUA terms
- Dataverse and GREI repositories don't fully support DCAT

### Transparency and Traceability (1.a-1.d)
- Need vocabulary definitions for InstanceAcquisition and raw_sources
- Simple strategies may be best represented as text
- Role distinctions beyond "creators" should be specified

### Data Characteristics (2.a-2.e)
- Multiple terminology systems acceptable (DCAT, Schema.org, MeSH)
- Complex statistics may require external linked documentation
- Bias assessment should include explicit textual descriptions
- HL7 confidentiality codes suggested for sensitivity handling

### Documentation and Purpose (3.a-3.c)
- Original intent was Gebru et al. 2021 Datasheets template
- Fit for purpose needs textual definition
- Dataverse uses UNF for verification vs. standard hashes

### Ethics and Governance (4.a-4.d, 5.a-5.c)
- IRB protocols and exemptions should be explicitly cited
- HL7 confidentiality codes recommended
- Export controls belong in license/DUA
- Update plans are nice-to-have for ongoing projects

### Technical Accessibility (6.a-6.d)
- Coverage appears adequate for standardization, accessibility, portability, and contextualization

---

**Revision History:**
- v0: Initial comparison (date unknown) - marked as outdated
