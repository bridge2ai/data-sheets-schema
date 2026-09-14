# D4D Rubric20 API Judge — general context v2

Assess all 20 questions for documentation quality and usefulness.
Numeric questions retain this API instrument's continuous 0–5 scale:
0 absent; 1 poor; 2 minimal; 3 adequate; 4 good with minor gaps;
5 comprehensive and actionable. Fractional numeric scores are permitted
when justified. Pass/fail questions use only 0 or 1.
This is distinct from the semantic agent's discrete numeric score bands.

**Maximum Possible Score:** 88 points — 17 numeric questions at five points
and three pass/fail questions at one point. Adjust the maximum only through
the supplied applicability contract.

Examples must fit the dataset. Clinical recruitment may need eligibility,
collection settings and relevant governance; a molecular benchmark may need
sample preparation, assay and processing details. Named study membership,
institutional affiliation or a particular hosting platform earns no credit.

## Applicability and collection scope

Use the caller's supplied evaluation contract. Its context predicates describe
the dataset independently of the fields being scored. A false predicate makes
only its assigned items N/A. Unknown predicates stay applicable and scored;
record that uncertainty instead of inferring N/A from missing documentation.
Human-subject governance can use the appropriate jurisdiction's equivalent
framework; no institution, project name, hosting service or jurisdiction is
required universally.

For every item, include `applicable`, `max_score`, and `unit_scores`.
Each unit row must contain the exact required resource `path`, its `score`,
and nonempty `evidence` (including an explicit explanation when evidence is
missing). Assess precisely the dataset units named in the supplied contract.
An explicit Dataset/CoreDataset is the target even when it has resources;
its child components do not replace its documentation. For collections,
assess all member datasets, recursively reducing nested collections while
stopping at explicitly declared datasets. Component assessments require
separately selected inputs. Paths refer to the unwrapped evaluation document.
Traverse distribution/file collections for evidence about their own dataset.
Do not give one sibling credit for another sibling's documentation, and do
not implicitly inherit collection metadata. For an applicable item, its
score is the minimum of its resource scores. This conservative coverage
policy is named in the supplied contract.

For an N/A item, set `score: null`, `max_score: 0`, `applicable: false`,
and a nonempty `na_reason` tied to the declared context. Each unit score is
also null. Keep all items in the response. Applicable items have
`applicable: true` and their ordinary maximum. Never replace absent evidence
with N/A.

All group totals sum applicable item scores and maxima. Overall
`total_points` and `max_points` sum the groups. `percentage` is
100 * total_points / max_points, rounded to one decimal, or null if the
applicable maximum is zero. The runner separately records the fixed maximum,
excluded items, context and scope. Adjusted percentages with different
applicable-item sets must not be pooled or used as a common ranking.

## Rubric specification

d4d_evaluation_rubric:
  schema_version: '2.0'
  description: "A 20-question rubric for evaluating D4D YAML files for completeness,\
    \ data quality, interoperability, and FAIR compliance. Each element is linked\
    \ to specific metadata fields and tasks described in the D4D schema (data_sheets_schema_all.yaml).\n\
    Total maximum score: 88 points (17 numeric questions \xD7 5 points + 3 pass/fail\
    \ questions \xD7 1 point)\n\nApplicability uses declared predicates. Unknown context\
    \ remains scored; excluded questions are removed from the adjusted denominator.\
    \ This rubric can describe biomedical, clinical, environmental, computational\
    \ and other datasets.\n"
  scoring_scale:
    quantitative: "0\u20135"
    qualitative:
    - Pass
    - Fail
    - N/A
  rubric:
  - id: 1
    name: Field Completeness
    description: 'Proportion of mandatory schema fields populated including core identification,
      hierarchical structure, governance, and composition metadata.

      '
    field:
    - id
    - title
    - description
    - keywords
    - license_and_use_terms
    - doi
    - page
    - creators
    - purposes
    - instances
    - resources
    - parent_datasets
    - variables
    - regulatory_restrictions.confidentiality_level
    method: Count non-empty required fields; score by proportion filled.
    score_type: numeric
    scoring:
      0: "\u226440% fields populated"
      3: "\u224870% fields populated"
      5: "\u226590% fields populated"
    task_ref:
    - 1
    - 2
    - 4
    - 6
    - 13
    item_id: Q1
  - id: 2
    name: Entry Length Adequacy
    description: Checks whether narrative fields (e.g., description, purposes) have
      meaningful content length.
    field:
    - description
    - purposes
    method: Measure average string length >200 characters.
    score_type: numeric
    scoring:
      0: <50 chars
      3: "50\u2013200 chars"
      5: '>200 chars'
    task_ref:
    - 16
    - 17
    item_id: Q2
  - id: 3
    name: Keyword Diversity
    description: Number of distinct keywords describing the dataset. Domain-specific
      controlled terms or condition lists may supply additional topic evidence where
      documented; no named study or disease count is presumed.
    field:
    - keywords
    method: Count unique keywords.
    score_type: numeric
    scoring:
      0: <3 keywords
      3: "3\u20137 keywords"
      5: "\u22658 keywords"
    task_ref:
    - 1
    - 2
    - 3
    item_id: Q3
  - id: 4
    name: File Enumeration and Type Variety
    description: Number and variety of documented distribution formats and file types.
      Modalities may occur within one resource or in separate linked resources. Examine
      every distribution; modality breadth is distinct from suitability for machine
      learning.
    field:
    - distribution_formats
    - file_collections
    - total_file_count
    method: Count total formats and unique media types.
    score_type: numeric
    scoring:
      0: 1 file type only
      3: "2\u20133 file types"
      5: '>3 file types'
    task_ref:
    - 94
    - 95
    item_id: Q4
  - id: 5
    name: Data File Size Availability
    description: Presence of file size or dimensional metadata (bytes, instance counts,
      data splits).
    field:
    - total_size_bytes
    - file_collections.total_bytes
    - instances
    - subsets.is_data_split
    - splits
    - subsets.is_subpopulation
    - subpopulations
    method: Detect numeric values for file size or instance counts.
    score_type: pass_fail
    scoring:
      Pass: Numeric file size or dimension info found.
      Fail: No file size/dimension metadata.
    task_ref:
    - 69
    - 70
    item_id: Q5
  - id: 6
    name: Dataset Identification Metadata
    description: 'Presence of unique identifiers such as DOI, RRID, or persistent
      URLs, AND hosting platform identification (publisher or repository).

      Note: Dataset identification should include both persistent identifiers AND
      hosting platform information (e.g., PhysioNet, Dataverse, Zenodo, institutional
      repositories).

      '
    field:
    - doi
    - id
    - page
    - publisher
    method: Check for non-null DOI or equivalent identifier AND publisher/platform.
    score_type: pass_fail
    scoring:
      Pass: At least one persistent ID found.
      Fail: No persistent ID or link.
    task_ref:
    - 2
    - 7
    item_id: Q6
  - id: 7
    name: Funding and Acknowledgements Completeness
    description: Checks presence of funding sources, grants, institutional sponsors,
      and creator affiliations.
    field:
    - funders
    - creators
    score_type: numeric
    scoring:
      0: No funding data
      3: Funding agency or creator info but missing grants/affiliations
      5: Funders with grants + creators with affiliations
    task_ref:
    - 22
    - 23
    - 24
    - 25
    item_id: Q7
  - id: 8
    name: Ethical and Privacy Declarations
    description: Ethical oversight and privacy safeguards appropriate to the dataset,
      including consent, deidentification, privacy risks, compensation and vulnerable
      populations where applicable. Accept equivalent jurisdiction-appropriate ethics
      review and data protection frameworks.
    field:
    - ethical_reviews
    - human_subject_research
    - is_deidentified
    - participant_privacy
    - participant_compensation
    - at_risk_populations
    - informed_consent
    - data_protection_impacts
    - participant_privacy.reidentification_risk
    score_type: numeric
    scoring:
      '0': No applicable ethics or privacy documentation
      '3': Basic oversight and privacy safeguards
      '5': Comprehensive documentation of the safeguards applicable to the subjects,
        data and jurisdiction
    task_ref:
    - 59
    - 76
    - 80
    - 84
    applies_to: human_subjects
    item_id: Q8
  - id: 9
    name: Access Requirements and Governance Documentation
    description: Documentation of access and license terms, intellectual-property
      restrictions, applicable regulatory obligations, confidentiality and governance
      contacts. Distinguish unrestricted access, registration, an agreement and committee
      approval. A named license does not by itself imply unrestricted reuse.
    field:
    - license_and_use_terms
    - ip_restrictions
    - regulatory_restrictions
    - regulatory_restrictions.confidentiality_level
    - regulatory_restrictions.hipaa_compliant
    - regulatory_restrictions.other_compliance
    - regulatory_restrictions.governance_committee_contact
    score_type: numeric
    scoring:
      0: No license or access info
      3: License + basic restrictions
      5: License + multi-jurisdiction compliance + confidentiality classification
        + governance contact
    task_ref:
    - 11
    - 12
    - 87
    - 88
    item_id: Q9
  - id: 10
    name: Interoperability, Standardization, and Cross-Platform Integration
    description: Documentation of standard formats, schema or ontology conformance,
      typed dataset relationships and integration procedures. Assess suitability for
      the declared uses; machine-learning use and any study-specific readiness framework
      must not be assumed.
    field:
    - distribution_formats
    - conforms_to_schema
    - file_collections.compression
    - conforms_to
    - external_resources
    - related_datasets
    score_type: numeric
    scoring:
      0: Non-standard or unspecified format
      3: Standard format but no schema reference
      5: Standard formats + schema/ontology compliance + integration capability
    task_ref:
    - 50
    - 67
    - 96
    - 97
    applies_to: shared_dataset
    item_id: Q10
  - id: 11
    name: Tool and Software Transparency
    description: Documentation of preprocessing, cleaning, labeling, annotation and
      imputation, including relevant software names, versions and workflow inputs/outputs.
      Structured text and provenance graphs are both valid evidence. Data processing
      is relevant independently of whether software is a released dataset output.
    field:
    - preprocessing_strategies
    - cleaning_strategies
    - labeling_strategies
    - machine_annotation_tools
    - annotation_analyses
    - imputation_protocols
    score_type: numeric
    scoring:
      0: No software tools documented
      3: At least one strategy or tool listed
      5: Comprehensive strategies with software versions/URLs, annotation quality,
        and imputation protocols
    task_ref:
    - 64
    - 65
    - 66
    applies_to: data_processing
    item_id: Q11
  - id: 12
    name: Collection Protocol Clarity
    description: 'Evaluates description completeness of data collection mechanisms,
      acquisition methods, data collectors, collection timeframes, and raw data sources.

      '
    field:
    - acquisition_methods
    - collection_mechanisms
    - data_collectors
    - collection_timeframes
    - raw_data_sources
    score_type: numeric
    scoring:
      0: No collection description
      3: Partial description (e.g., mechanism only)
      5: Full collection protocol with methods, collectors, and timeframes
    task_ref:
    - 46
    - 47
    - 48
    - 49
    applies_to: data_collection
    item_id: Q12
  - id: 13
    name: Version History, Maintenance, and Sustainability
    description: Documentation of version identifiers, change history, maintenance
      and preservation plans, responsible contacts and durable access. Assess the
      preservation route appropriate to the domain and access conditions.
    field:
    - version
    - version_access
    - errata
    - updates
    - maintainers
    - doi
    - publisher
    score_type: numeric
    scoring:
      0: Single version only, no sustainability plan
      3: Version number + basic access info + persistent ID
      5: Comprehensive versioning + full sustainability documentation (governance
        + repository + commitment)
    task_ref:
    - 8
    - 95
    applies_to: shared_dataset
    item_id: Q13
  - id: 14
    name: Associated Publications
    description: Citation, identifiers and documentation links that let a reader identify
      the dataset and related publications or resources. The dataset need not belong
      to a named study or have a publication to document how it should be cited.
    field:
    - citation
    - external_resources
    - doi
    score_type: numeric
    scoring:
      0: No publication, external resource or dataset citation is documented
      3: One citation or reference with DOI
      5: Multiple references with DOI cross-links + formatted citation + citation
        instructions
    task_ref:
    - 9
    - 30
    item_id: Q14
  - id: 15
    name: Human Subject Representation
    description: Documentation of human participant or population representation,
      recruitment, sampling and relevant subgroups. Evaluate the represented population
      and stated use, not a predetermined clinical cohort.
    field:
    - subpopulations
    - instances
    - at_risk_populations
    - subsets.is_subpopulation
    - missing_data_documentation
    score_type: numeric
    scoring:
      0: No human subject information
      3: General human data without subgroup description
      5: Detailed demographics, subpopulations, and inclusion/exclusion criteria
    task_ref:
    - 31
    - 35
    - 37
    applies_to: human_subjects
    item_id: Q15
  - id: 16
    name: Findability (Persistent Links)
    description: Dataset includes persistent URLs, DOI, and identifier for access
      and documentation.
    field:
    - page
    - doi
    - id
    score_type: pass_fail
    scoring:
      Pass: At least one persistent identifier present.
      Fail: No persistent identifiers found.
    task_ref:
    - 7
    - 14
    - 91
    item_id: Q16
  - id: 17
    name: Accessibility (Access Mechanism)
    description: 'Describes how users can obtain the dataset (download URL, distribution
      formats, access policy).

      Note: "Public" does not mean "no restrictions." Even openly accessible datasets
      may require signed Data Use Agreements (DUAs). Distinguish between access tiers:
      (1) No authentication required (truly public), (2) Registration required (email/account),
      (3) DUA required (signed agreement), (4) IRB/committee approval required (restricted
      access). State the actual authorization steps, including registration or a signed
      agreement, without implying unrestricted access.

      '
    field:
    - download_url
    - distribution_formats
    - license_and_use_terms
    score_type: numeric
    scoring:
      0: Unclear access method
      3: Partially described access mechanism (access tier unclear)
      5: Fully defined access path with explicit access tier (download URL, formats,
        policy, access requirements)
    task_ref:
    - 11
    - 87
    - 90
    applies_to: shared_dataset
    item_id: Q17
  - id: 18
    name: Reusability, Use Guidance, and Social Impact
    description: 'License is clearly defined with explicit use guidance including
      intended uses, prohibited uses, discouraged uses, AND comprehensive social impact
      analysis with risk identification and mitigation strategies (CROISSANT RAI aligned).

      '
    field:
    - license_and_use_terms
    - intended_uses
    - prohibited_uses
    - discouraged_uses
    - future_use_impacts
    score_type: numeric
    scoring:
      0: No license or use guidance
      3: License + basic use guidance
      5: License + comprehensive use guidance + social impact analysis with mitigation
        strategies
    task_ref:
    - 13
    - 88
    item_id: Q18
  - id: 19
    name: Data Integrity, Provenance Graph, and Quality
    description: "Presence of version access, errata, update plans, source derivation,\
      \ parent dataset linkages, missing data documentation, data split indicators,\
      \ AND provenance graph representation.\nNote: Provenance is a transparent graph\
      \ of origins and processing of data (W3C PROV-O standard: https://www.w3.org/TR/prov-o/),\
      \ NOT just version changes. Evaluation checks for: (1) Entity-activity-agent\
      \ relationships, (2) Processing lineage, (3) Derivation paths.\nScoring distinction:\
      \ - Version history alone (version numbers, errata, updates) = 3 points - Full\
      \ provenance graph (W3C PROV-O with entity-activity-agent relationships, processing\n\
      \  lineage, derivation paths) = 5 points\n\nProvenance may be represented as\
      \ text OR as W3C PROV-O graphs. Both formats are acceptable if they provide\
      \ complete lineage information.\n"
    field:
    - version_access
    - errata
    - updates
    - was_derived_from
    - parent_datasets
    - missing_data_documentation
    - subsets.is_data_split
    - splits
    - raw_data_sources
    score_type: numeric
    scoring:
      0: No provenance metadata
      3: Version history (version numbers, errata, updates) but no full provenance
        graph
      5: Full provenance graph with entity-activity-agent relationships, processing
        lineage, and derivation paths
    task_ref:
    - 3
    - 8
    - 95
    item_id: Q19
  - id: 20
    name: Bias Documentation and Responsible AI Alignment
    description: Documentation of known biases, limitations and potential effects
      on intended or foreseeable uses. Every dataset has a scope that can be documented;
      absent bias fields do not make this question inapplicable.
    field:
    - known_biases
    - future_use_impacts
    score_type: numeric
    scoring:
      0: No bias documentation
      3: Basic bias identification without taxonomy
      5: Comprehensive bias categorization using standard taxonomy (AIO/CROISSANT
        RAI) + fairness analysis
    task_ref:
    - varies
    item_id: Q20
  instrument_version: 2.0-general-context


## Common output fields

Return only a JSON object with `rubric`, `version: "2.0-general-context"`,
`project` and `method` exactly as supplied, `d4d_file`,
`evaluation_timestamp`, `overall_score` (total_points, max_points,
percentage), `assessment` (strengths, weaknesses, recommendations), and
`metadata`. Provide actionable, evidence-based explanations. The runner
attests the actual model, rubric bytes and rendered request; do not invent
digests. Preserve arbitrary dataset/method identities literally as data.

## Rubric20 output structure

Include `categories` with four nonempty groups covering Q1–5, Q6–10,
Q11–15 and Q16–20 respectively. Each group contains `name`, `questions`,
`category_score` and `category_max`, computed from that group's questions.
Each question has integer `id`, its rubric `name`, `score_type`,
`score`, `max_score`, `applicable`, `score_label`, `evidence`,
`quality_note`, and `unit_scores` as defined above; N/A also needs
`na_reason`. Include all 20 questions exactly once.
