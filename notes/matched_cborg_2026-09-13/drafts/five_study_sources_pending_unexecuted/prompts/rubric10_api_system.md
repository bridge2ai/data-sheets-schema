# D4D Rubric10 API Judge — general context v2

Assess meaningful dataset documentation using all 50 sub-elements of the
10-element rubric. This is a semantic quality judgment, distinct from the
deterministic field-presence evaluator.

Applicable sub-element scores are strictly binary: 1 for meaningful,
actionable evidence that satisfies the item's full scope; 0 for missing,
placeholder, vague or insufficient evidence. No fractional scores.
The fixed maximum is 50. The new binary contract resolves the old template's
fractional illustrative total; it does not reinterpret historical ratings.

For example, a description of collection sites, inclusion criteria and the
relevant approvals can support a clinical collection item; a description of
sensor placement and calibration can support an environmental collection
item. "Collected at several sites" alone does not establish the required detail.

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

d4d_complex_proxy_rubric:
  schema_version: '2.0'
  description: 'Ten-element hierarchical rubric for evaluating D4D YAML completeness
    and usability. Each element represents a complex metadata-driven goal and includes
    up to five measurable sub-elements. Scores can be computed at the element or sub-element
    level.


    Applicability is declared by reusable predicates, not dataset names. Unknown context
    remains scored. Ethics and regulatory examples accept equivalent frameworks in
    the dataset''s jurisdiction.

    '
  scoring_scale:
    element: "0\u20135"
    sub_element:
    - 0
    - 1
  rubric:
  - id: 1
    name: Dataset Discovery and Identification
    description: Can a user or system discover and uniquely identify this dataset?
    sub_elements:
    - name: Persistent Identifier (DOI, RRID, or URI)
      field:
      - doi
      - rrid
      - id
      item_id: E1.1
    - name: Dataset Title and Description Completeness
      field:
      - title
      - description
      item_id: E1.2
    - name: Keywords or Tags for Searchability
      field:
      - keywords
      item_id: E1.3
    - name: Landing Page and Resources (page, hierarchical resources)
      field:
      - page
      - resources
      item_id: E1.4
    - name: Hierarchical Structure (parent datasets, relationships)
      field:
      - parent_datasets
      - related_datasets
      item_id: E1.5
    scoring_method: Sum of sub_element presence / 5
  - id: 2
    name: Dataset Access and Retrieval
    description: Can the dataset and its associated resources be located, accessed,
      and downloaded?
    sub_elements:
    - name: Access Policy and IP Restrictions Defined
      field:
      - license_and_use_terms
      - ip_restrictions
      item_id: E2.1
    - name: Regulatory Compliance and Confidentiality Classification
      field:
      - regulatory_restrictions
      - confidentiality_level
      - hipaa_compliant
      - other_compliance
      - governance_committee_contact
      item_id: E2.2
      applies_to: regulated_access
    - name: Download URL or Platform Link Available
      field:
      - download_url
      item_id: E2.3
    - name: Distribution Formats and File Types Specified
      field:
      - distribution_formats
      - format
      - media_type
      item_id: E2.4
    - name: Related Datasets and External Resources Linked
      field:
      - related_datasets
      - external_resources
      item_id: E2.5
    scoring_method: Sum of sub_element presence / 5
  - id: 3
    name: Data Reuse and Interoperability
    description: 'Is sufficient information provided to reuse and integrate the dataset
      with others?

      Note: Evaluate whether the dataset is designed for integration with similar
      datasets, including: common identifiers for cross-dataset linking, standardized
      formats for data harmonization, and documented integration procedures.

      '
    sub_elements:
    - name: License Terms Allow Reuse
      field:
      - license_and_use_terms
      item_id: E3.1
      applies_to: shared_dataset
    - name: Data Formats Are Standardized (encoding, format)
      field:
      - format
      - encoding
      item_id: E3.2
      applies_to: shared_dataset
    - name: Schema or Ontology Conformance Stated
      field:
      - conforms_to
      - conforms_to_schema
      item_id: E3.3
      applies_to: shared_dataset
    - name: Variable Metadata with Identifiers Defined
      field:
      - variables
      item_id: E3.4
      applies_to: shared_dataset
    - name: Use Guidance Provided (intended, prohibited uses)
      field:
      - intended_uses
      - prohibited_uses
      - discouraged_uses
      item_id: E3.5
    scoring_method: Sum of sub_element presence / 5
  - id: 4
    name: Ethical Use and Privacy Safeguards
    description: Does the dataset document the ethical oversight, privacy, consent
      and safeguards that apply to its subjects and governance context? Equivalent
      local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not
      a universal requirement.
    sub_elements:
    - name: IRB or Ethics Review and Data Protection Impact
      field:
      - ethical_reviews
      - human_subject_research
      - data_protection_impacts
      item_id: E4.1
      applies_to:
        any:
        - human_subjects
        - regulated_access
    - name: Deidentification Method Described
      field:
      - is_deidentified
      item_id: E4.2
      applies_to:
        any:
        - human_subjects
        - regulated_access
    - name: Privacy Protections and Re-identification Risk Assessment
      field:
      - participant_privacy
      - reidentification_risk
      item_id: E4.3
      applies_to: human_subjects
    - name: Informed Consent Obtained from Participants
      field:
      - informed_consent
      item_id: E4.4
      applies_to: human_subjects
    - name: Vulnerable Populations and Compensation Documented
      field:
      - vulnerable_populations
      - participant_compensation
      item_id: E4.5
      applies_to: human_subjects
    scoring_method: Sum of sub_element presence / 5
  - id: 5
    name: Data Composition and Structure
    description: Can the dataset's structure, modality, and population be understood
      from metadata?
    sub_elements:
    - name: Cohort or Subpopulations Characteristics Described
      field:
      - subpopulations
      item_id: E5.1
    - name: Number of Instances or Samples Reported
      field:
      - instances
      item_id: E5.2
    - name: Variable-Level Metadata, Tabular Flag, and Data Splits
      field:
      - variables
      - is_tabular
      - is_data_split
      - is_subpopulation
      item_id: E5.3
    - name: Data Topics or Conditions Represented
      field:
      - instances
      item_id: E5.4
    - name: Data Quality, Anomalies, and Missing Data Documented
      field:
      - anomalies
      - sampling_strategies
      - missing_data_documentation
      item_id: E5.5
    scoring_method: Sum of sub_element presence / 5
  - id: 6
    name: Data Provenance and Version Tracking
    description: Can a user determine dataset versions, update history, and provenance?
    sub_elements:
    - name: Dataset Version Number Provided
      field:
      - version
      item_id: E6.1
      applies_to: shared_dataset
    - name: Version Access Methods Documented
      field:
      - version_access
      item_id: E6.2
      applies_to: shared_dataset
    - name: Change Descriptions and Errata Provided
      field:
      - errata
      - updates
      item_id: E6.3
      applies_to: shared_dataset
    - name: Update Schedule or Frequency Indicated
      field:
      - updates
      item_id: E6.4
      applies_to: shared_dataset
    - name: Provenance, Source Derivation, and Raw Data Sources
      field:
      - was_derived_from
      - release_notes
      - raw_data_sources
      item_id: E6.5
      applies_to: shared_dataset
    scoring_method: Sum of sub_element presence / 5
  - id: 7
    name: Scientific Motivation and Funding Transparency
    description: Does the metadata clearly state why the dataset exists and who funded
      it?
    sub_elements:
    - name: Motivation or Purpose for Dataset Creation
      field:
      - purposes
      item_id: E7.1
    - name: Primary Research Objectives or Tasks
      field:
      - tasks
      item_id: E7.2
    - name: Funding Sources and Mechanisms Listed
      field:
      - funders
      item_id: E7.3
    - name: Grant IDs or Award Numbers Present
      field:
      - funders
      item_id: E7.4
    - name: Creators and Acknowledgements Documented
      field:
      - creators
      - funders
      item_id: E7.5
    scoring_method: Sum of sub_element presence / 5
  - id: 8
    name: Technical Transparency (Data Collection and Processing)
    description: 'Can data collection and processing steps be replicated or understood?

      Note: Preprocessing and collection metadata may be represented as structured
      text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O,
      workflow graphs). Evaluation should check for: (1) structured text descriptions
      OR (2) graph representations with entity-activity-agent relationships. Both
      formats are acceptable.

      '
    sub_elements:
    - name: Collection Mechanisms and Settings Described
      field:
      - collection_mechanisms
      item_id: E8.1
      applies_to: data_collection
    - name: Data Acquisition Methods Listed
      field:
      - acquisition_methods
      item_id: E8.2
      applies_to: data_collection
    - name: Preprocessing, Cleaning, Labeling, and Annotation Quality
      field:
      - preprocessing_strategies
      - cleaning_strategies
      - labeling_strategies
      - annotation_analyses
      - machine_annotation_tools
      item_id: E8.3
      applies_to: data_processing
    - name: Software and Tools Documented
      field:
      - software_and_tools
      item_id: E8.4
      applies_to: processing_software
    - name: External Standards, Resources, and Imputation Protocols
      field:
      - external_resources
      - conforms_to
      - imputation_protocols
      item_id: E8.5
    scoring_method: Sum of sub_element presence / 5
  - id: 9
    name: Dataset Evaluation and Limitations Disclosure
    description: Does the metadata communicate known risks, biases, or dataset limitations?
    sub_elements:
    - name: Known Limitations Documented
      field:
      - known_limitations
      item_id: E9.1
    - name: Biases Categorized Using Standard Taxonomy (RAI-aligned)
      field:
      - known_biases
      item_id: E9.2
    - name: Data Anomalies and Quality Issues Noted
      field:
      - anomalies
      item_id: E9.3
    - name: Sensitive Content and Warnings Provided
      field:
      - sensitive_elements
      - content_warnings
      item_id: E9.4
    - name: Ethical Review and Social Impact Analysis
      field:
      - ethical_reviews
      - future_use_impacts
      item_id: E9.5
    scoring_method: Sum of sub_element presence / 5
  - id: 10
    name: Cross-Platform and Community Integration
    description: Does the dataset connect to relevant repositories, communities and
      standards? A shared dataset needs citation or identifier guidance and a named
      hosting or preservation route appropriate to its domain.
    sub_elements:
    - name: Dataset Published on a Recognized Platform
      field:
      - publisher
      item_id: E10.1
      applies_to: shared_dataset
    - name: Citation and DOI for Cross-referencing
      field:
      - citation
      - doi
      item_id: E10.2
      applies_to: shared_dataset
    - name: Community Standards or Schema Conformance
      field:
      - conforms_to
      item_id: E10.3
      applies_to: shared_dataset
    - name: Outreach Materials and Documentation Links
      field:
      - external_resources
      - page
      item_id: E10.4
      applies_to: shared_dataset
    - name: Related Datasets with Typed Relationships
      field:
      - related_datasets
      item_id: E10.5
      applies_to: shared_dataset
    scoring_method: Sum of sub_element presence / 5
  instrument_version: 2.0-general-context


## Common output fields

Return only a JSON object with `rubric`, `version: "2.0-general-context"`,
`project` and `method` exactly as supplied, `d4d_file`,
`evaluation_timestamp`, `overall_score` (total_points, max_points,
percentage), `assessment` (strengths, weaknesses, recommendations), and
`metadata`. Provide actionable, evidence-based explanations. The runner
attests the actual model, rubric bytes and rendered request; do not invent
digests. Preserve arbitrary dataset/method identities literally as data.

## Rubric10 output structure

Include `elements`: every rubric element, with integer `id`, `name`,
`sub_elements`, `element_score` and `element_max`. Each sub-element
contains its exact `id` such as "E1.1", its rubric `name`, `score`,
`max_score`, `applicable`, `evidence`, `quality_note`, and
`unit_scores` as defined above; N/A also needs `na_reason`.
Include all five sub-elements of every element. Overall points are the sum
of the ten element scores. Strength in another item cannot replace missing
evidence for the item being scored.
