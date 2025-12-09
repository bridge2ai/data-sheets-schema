#!/usr/bin/env python3
"""
Hybrid Rubric20 Batch Evaluation Script

Uses YAML parsing + quality heuristics to evaluate all D4D files against rubric20.
Rubric20 has 20 questions in 4 categories with mixed scoring (numeric 0-5 and pass/fail).

Usage:
    python scripts/batch_evaluate_rubric20_hybrid.py

Output:
    - data/evaluation_llm/rubric20/individual/*.json
    - data/evaluation_llm/rubric20/concatenated/*.json
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import re

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Rubric20 specification (20 questions, 4 categories)
RUBRIC20_QUESTIONS = {
    # Category 1: Structural Completeness
    1: {
        "category": "Structural Completeness",
        "name": "Field Completeness",
        "description": "Proportion of mandatory schema fields populated including hierarchical structure and governance",
        "fields": ["id", "title", "description", "keywords", "license_and_use_terms", "doi", "page", "creators", "purposes", "instances", "resources", "parent_datasets", "variables", "confidentiality_level"],
        "score_type": "numeric",
        "max_score": 5
    },
    2: {
        "category": "Structural Completeness",
        "name": "Entry Length Adequacy",
        "description": "Narrative fields have meaningful content length",
        "fields": ["description", "motivation", "purposes"],
        "score_type": "numeric",
        "max_score": 5
    },
    3: {
        "category": "Structural Completeness",
        "name": "Keyword Diversity",
        "description": "Number of unique keywords provided",
        "fields": ["keywords"],
        "score_type": "numeric",
        "max_score": 5
    },
    4: {
        "category": "Structural Completeness",
        "name": "File Enumeration and Type Variety",
        "description": "Number of distribution formats and file type diversity",
        "fields": ["distribution_formats", "format", "media_type", "bytes", "files", "subsets"],
        "score_type": "numeric",
        "max_score": 5
    },
    5: {
        "category": "Structural Completeness",
        "name": "Data File Size Availability",
        "description": "Presence of file size or dimensional metadata (bytes, instance counts)",
        "fields": ["bytes", "instances", "files", "data_characteristics", "subsets"],
        "score_type": "pass_fail",
        "max_score": 1
    },

    # Category 2: Metadata Quality & Content
    6: {
        "category": "Metadata Quality & Content",
        "name": "Dataset Identification Metadata",
        "description": "Presence of unique identifiers (DOI, RRID, URLs)",
        "fields": ["doi", "rrid", "page", "id"],
        "score_type": "pass_fail",
        "max_score": 1
    },
    7: {
        "category": "Metadata Quality & Content",
        "name": "Funding and Acknowledgements Completeness",
        "description": "Funding sources, grants, sponsors, and creator affiliations",
        "fields": ["funders", "creators", "funding_and_acknowledgements"],
        "score_type": "numeric",
        "max_score": 5
    },
    8: {
        "category": "Metadata Quality & Content",
        "name": "Ethical and Privacy Declarations",
        "description": "Comprehensive ethics: IRB, deidentification, privacy, consent, compensation, vulnerable populations",
        "fields": ["ethical_reviews", "human_subject_research", "is_deidentified", "participant_privacy", "participant_compensation", "vulnerable_populations", "informed_consent", "deidentification_and_privacy", "ethics"],
        "score_type": "numeric",
        "max_score": 5
    },
    9: {
        "category": "Metadata Quality & Content",
        "name": "Access Requirements and Governance Documentation",
        "description": "Access policy, license, IP restrictions, regulatory restrictions, confidentiality level",
        "fields": ["license_and_use_terms", "ip_restrictions", "regulatory_restrictions", "confidentiality_level", "access_and_licensing"],
        "score_type": "numeric",
        "max_score": 5
    },
    10: {
        "category": "Metadata Quality & Content",
        "name": "Interoperability and Standardization",
        "description": "Standard formats, encoding, ontologies, schema conformance",
        "fields": ["format", "encoding", "conforms_to", "conforms_to_schema", "distribution_formats", "data_characteristics.data_formats"],
        "score_type": "numeric",
        "max_score": 5
    },

    # Category 3: Technical Documentation
    11: {
        "category": "Technical Documentation",
        "name": "Tool and Software Transparency",
        "description": "Preprocessing, cleaning, labeling strategies with software tools",
        "fields": ["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "software_and_tools"],
        "score_type": "numeric",
        "max_score": 5
    },
    12: {
        "category": "Technical Documentation",
        "name": "Collection Protocol Clarity",
        "description": "Collection mechanisms, acquisition methods, data collectors, timeframes",
        "fields": ["acquisition_methods", "collection_mechanisms", "data_collectors", "collection_timeframes", "collection_process", "sampling_strategies"],
        "score_type": "numeric",
        "max_score": 5
    },
    13: {
        "category": "Technical Documentation",
        "name": "Version History Documentation",
        "description": "Version info, version access, errata, update plans, release notes",
        "fields": ["version", "version_access", "errata", "updates", "release_notes", "versions_available_on_platform"],
        "score_type": "numeric",
        "max_score": 5
    },
    14: {
        "category": "Technical Documentation",
        "name": "Associated Publications",
        "description": "Citations or DOI-linked references",
        "fields": ["citation", "external_resources", "citations", "references"],
        "score_type": "numeric",
        "max_score": 5
    },
    15: {
        "category": "Technical Documentation",
        "name": "Human Subject Representation",
        "description": "Demographics, subpopulations, vulnerable population protections",
        "fields": ["subpopulations", "instances", "vulnerable_populations", "composition.population"],
        "score_type": "numeric",
        "max_score": 5
    },

    # Category 4: FAIRness & Accessibility
    16: {
        "category": "FAIRness & Accessibility",
        "name": "Findability (Persistent Links)",
        "description": "Persistent identifiers (DOI, ID) and URLs for access",
        "fields": ["page", "doi", "id", "download_url", "external_resources"],
        "score_type": "pass_fail",
        "max_score": 1
    },
    17: {
        "category": "FAIRness & Accessibility",
        "name": "Accessibility (Access Mechanism)",
        "description": "Download URL, distribution formats, access policy",
        "fields": ["download_url", "distribution_formats", "license_and_use_terms", "access_and_licensing"],
        "score_type": "numeric",
        "max_score": 5
    },
    18: {
        "category": "FAIRness & Accessibility",
        "name": "Reusability (License and Use Guidance)",
        "description": "License with explicit use guidance (intended/prohibited/discouraged)",
        "fields": ["license_and_use_terms", "intended_uses", "prohibited_uses", "discouraged_uses"],
        "score_type": "numeric",
        "max_score": 5
    },
    19: {
        "category": "FAIRness & Accessibility",
        "name": "Data Integrity and Provenance",
        "description": "Version access, errata, updates, source derivation, parent datasets",
        "fields": ["version_access", "errata", "updates", "was_derived_from", "parent_datasets", "release_notes"],
        "score_type": "numeric",
        "max_score": 5
    },
    20: {
        "category": "FAIRness & Accessibility",
        "name": "Interlinking Across Platforms and Datasets",
        "description": "External resources and dataset relationships (typed relationships, hierarchical linkages)",
        "fields": ["external_resources", "related_datasets", "parent_datasets", "resources", "project_website", "same_as"],
        "score_type": "pass_fail",
        "max_score": 1
    }
}


def get_nested_value(data: Dict, path: str) -> Optional[Any]:
    """Get value from nested dictionary using dot notation."""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value


def check_field_presence(data: Dict, fields: List[str]) -> Tuple[bool, str, Any]:
    """
    Check if any of the specified fields are present and non-empty.
    Returns (is_present, evidence_string, raw_value).
    """
    for field in fields:
        value = get_nested_value(data, field)
        if value is not None and value != "" and value != []:
            # Generate evidence string
            if isinstance(value, str):
                evidence = f"{field}: {value[:80]}..." if len(str(value)) > 80 else f"{field}: {value}"
            elif isinstance(value, list):
                evidence = f"{field}: {len(value)} items"
            elif isinstance(value, dict):
                evidence = f"{field}: present ({len(value)} keys)"
            else:
                evidence = f"{field}: {value}"
            return True, evidence, value
    return False, f"Missing: {', '.join(fields)}", None


def evaluate_question(data: Dict, question_id: int) -> Tuple[int, str, str]:
    """
    Evaluate a single rubric20 question.
    Returns (score, evidence, quality_note).
    """
    spec = RUBRIC20_QUESTIONS[question_id]
    fields = spec["fields"]
    score_type = spec["score_type"]
    max_score = spec["max_score"]

    is_present, evidence, value = check_field_presence(data, fields)

    if not is_present:
        return 0, evidence, "Field absent or empty"

    # Apply question-specific heuristics
    score = 0
    quality_note = ""

    # Q1: Field Completeness (5 mandatory fields)
    if question_id == 1:
        filled_count = sum(1 for f in fields if get_nested_value(data, f))
        percent = (filled_count / len(fields)) * 100
        if percent >= 90:
            score = 5
            quality_note = f"{filled_count}/{len(fields)} fields filled (≥90%)"
        elif percent >= 70:
            score = 3
            quality_note = f"{filled_count}/{len(fields)} fields filled (~70%)"
        else:
            score = 0
            quality_note = f"{filled_count}/{len(fields)} fields filled (≤40%)"

    # Q2: Entry Length Adequacy
    elif question_id == 2:
        lengths = []
        for field in fields:
            val = get_nested_value(data, field)
            if val:
                lengths.append(len(str(val)))

        if lengths:
            avg_length = sum(lengths) / len(lengths)
            if avg_length > 200:
                score = 5
                quality_note = f"Avg {int(avg_length)} chars (>200)"
            elif avg_length >= 50:
                score = 3
                quality_note = f"Avg {int(avg_length)} chars (50-200)"
            else:
                score = 0
                quality_note = f"Avg {int(avg_length)} chars (<50)"

    # Q3: Keyword Diversity
    elif question_id == 3:
        keywords = data.get('keywords', [])
        if isinstance(keywords, list):
            count = len(keywords)
            if count >= 8:
                score = 5
                quality_note = f"{count} keywords (≥8)"
            elif count >= 3:
                score = 3
                quality_note = f"{count} keywords (3-7)"
            else:
                score = 0
                quality_note = f"{count} keywords (<3)"
        else:
            score = 0
            quality_note = "Keywords not a list"

    # Q4: File Enumeration and Type Variety
    elif question_id == 4:
        file_types = set()

        # Check distribution_formats
        dist_formats = data.get('distribution_formats', [])
        if isinstance(dist_formats, list):
            for fmt in dist_formats:
                if isinstance(fmt, dict):
                    desc = str(fmt.get('description', ''))
                    # Extract file extensions (Parquet, TSV, JSON, etc.)
                    found = re.findall(r'\b(Parquet|TSV|CSV|JSON|XML|HDF5|DICOM|PNG|JPG)\b', desc, re.I)
                    file_types.update([f.upper() for f in found])

        # Check subsets
        subsets = data.get('subsets', [])
        if isinstance(subsets, list):
            for subset in subsets:
                if isinstance(subset, dict):
                    name = str(subset.get('name', ''))
                    # Extract extensions from filenames
                    found = re.findall(r'\.(parquet|tsv|csv|json|txt|yaml)', name, re.I)
                    file_types.update([f.upper() for f in found])

        type_count = len(file_types)
        if type_count > 3:
            score = 5
            quality_note = f"{type_count} file types (>3): {', '.join(sorted(file_types))}"
        elif type_count >= 2:
            score = 3
            quality_note = f"{type_count} file types (2-3): {', '.join(sorted(file_types))}"
        elif type_count == 1:
            score = 0
            quality_note = f"1 file type only: {', '.join(file_types)}"
        else:
            score = 0
            quality_note = "No file types detected"

    # Q5: Data File Size Availability (pass/fail)
    elif question_id == 5:
        # Look for numeric dimensions or file sizes
        combined = str(data.get('subsets', '')) + str(data.get('data_characteristics', ''))
        # Pattern: NxM dimensions, file sizes, sampling rates
        has_dimensions = bool(re.search(r'\d+\s*[x×]\s*\d+|\d+\s*[kKmMgG][bB]|\d+\s*kHz', combined))

        if has_dimensions:
            score = 1
            quality_note = "Pass: Numeric dimensions/sizes found"
        else:
            score = 0
            quality_note = "Fail: No file size/dimension metadata"

    # Q6: Dataset Identification Metadata (pass/fail)
    elif question_id == 6:
        has_doi = 'doi.org' in str(data.get('doi', '')) or 'doi.org' in str(data.get('id', ''))
        has_rrid = 'RRID:' in str(data.get('rrid', ''))
        has_page = bool(data.get('page'))

        if has_doi or has_rrid or has_page:
            score = 1
            quality_note = "Pass: Persistent identifier found"
        else:
            score = 0
            quality_note = "Fail: No persistent ID"

    # Q7: Funding and Acknowledgements Completeness
    elif question_id == 7:
        funders = data.get('funders', [])
        funding = get_nested_value(data, 'funding_and_acknowledgements.funding')

        has_agency = False
        has_award = False
        has_acknowledgements = False

        if funders and isinstance(funders, list):
            funder_str = str(funders)
            has_agency = any(keyword in funder_str for keyword in ['NIH', 'NSF', 'National', 'Fund'])
            has_award = bool(re.search(r'\d[A-Z0-9]{7,}', funder_str))
            has_acknowledgements = len(funders) > 0
        elif funding:
            has_agency = bool(get_nested_value(data, 'funding_and_acknowledgements.funding.agency'))
            has_award = bool(get_nested_value(data, 'funding_and_acknowledgements.funding.award_number'))
            has_acknowledgements = bool(get_nested_value(data, 'funding_and_acknowledgements.acknowledgements'))

        if has_agency and has_award and has_acknowledgements:
            score = 5
            quality_note = "Agency + award + acknowledgements"
        elif has_agency and not has_award:
            score = 3
            quality_note = "Agency present, missing award number"
        elif has_agency:
            score = 1
            quality_note = "Agency only"
        else:
            score = 0
            quality_note = "No funding data"

    # Q8: Ethical and Privacy Declarations
    elif question_id == 8:
        has_irb = bool(get_nested_value(data, 'ethics.irb_approval') or data.get('ethical_reviews'))
        has_deident = bool(get_nested_value(data, 'deidentification_and_privacy.approach') or data.get('is_deidentified'))
        has_consent = bool(get_nested_value(data, 'collection_process.consent') or data.get('informed_consent'))
        has_ethical = bool(get_nested_value(data, 'ethics.ethical_position') or 'ethic' in str(data.get('purposes', '')).lower())

        ethics_count = sum([has_irb, has_deident, has_consent, has_ethical])

        if ethics_count >= 3:
            score = 5
            quality_note = "IRB + deidentification + ethical sourcing"
        elif ethics_count >= 1:
            score = 3
            quality_note = "Partial ethics documentation"
        else:
            score = 0
            quality_note = "No ethics fields"

    # Q9: Access Requirements Documentation
    elif question_id == 9:
        license_terms = data.get('license_and_use_terms', {})
        has_license = bool(license_terms)
        has_dua = 'DUA' in str(license_terms) or 'Data Use Agreement' in str(license_terms)
        has_policy = bool(get_nested_value(data, 'access_and_licensing.access_policy'))

        if has_license and has_dua and has_policy:
            score = 5
            quality_note = "License + DUA + access policy"
        elif has_license:
            score = 3
            quality_note = "License type only"
        else:
            score = 0
            quality_note = "No license info"

    # Q10: Interoperability and Standardization
    elif question_id == 10:
        has_formats = bool(get_nested_value(data, 'data_characteristics.data_formats') or data.get('distribution_formats'))
        has_schema = bool(data.get('conforms_to'))

        standard_formats = ['Parquet', 'TSV', 'CSV', 'JSON', 'HDF5', 'DICOM']
        formats_str = str(has_formats)
        has_standard = any(fmt in formats_str for fmt in standard_formats)

        if has_standard and has_schema:
            score = 5
            quality_note = "Standard formats + schema conformance"
        elif has_standard:
            score = 3
            quality_note = "Standard format, no schema reference"
        else:
            score = 0
            quality_note = "Non-standard or unspecified format"

    # Q11: Tool and Software Transparency
    elif question_id == 11:
        software = data.get('software_and_tools', {})
        preprocessing = data.get('preprocessing_strategies', [])

        tool_mentions = str(software) + str(preprocessing)
        # Count tool names
        tools = re.findall(r'\b(openSMILE|Parselmouth|Whisper|Praat|UMAP|Python|R|MATLAB|TensorFlow|PyTorch)\b', tool_mentions, re.I)

        if len(tools) >= 3:
            score = 5
            quality_note = f"Comprehensive: {len(tools)} tools listed"
        elif len(tools) >= 1:
            score = 3
            quality_note = f"{len(tools)} tool(s) listed"
        else:
            score = 0
            quality_note = "No software tools documented"

    # Q12: Collection Protocol Clarity
    elif question_id == 12:
        collection = data.get('collection_process', {})
        acquisition = data.get('acquisition_methods', [])
        sampling = data.get('sampling_strategies', [])

        has_setting = bool(get_nested_value(data, 'collection_process.setting') or data.get('data_collectors'))
        has_method = bool(get_nested_value(data, 'collection_process.data_capture') or acquisition)
        has_sampling = bool(sampling)

        detail_count = sum([has_setting, has_method, has_sampling])

        if detail_count >= 3:
            score = 5
            quality_note = "Full recruitment and procedural details"
        elif detail_count >= 1:
            score = 3
            quality_note = "Partial description"
        else:
            score = 0
            quality_note = "No collection description"

    # Q13: Version History Documentation
    elif question_id == 13:
        updates = data.get('updates', {})
        version_access = data.get('version_access', {})
        release_notes = data.get('release_notes', {})

        # Count version mentions
        version_text = str(updates) + str(version_access) + str(release_notes)
        version_numbers = re.findall(r'v?\d+\.\d+(?:\.\d+)?', version_text)

        if len(set(version_numbers)) >= 2:
            score = 5
            quality_note = f"≥2 versions with details: {', '.join(list(set(version_numbers))[:3])}"
        elif len(set(version_numbers)) == 1:
            score = 0
            quality_note = "Single version only"
        else:
            score = 0
            quality_note = "No version info"

    # Q14: Associated Publications
    elif question_id == 14:
        references = data.get('references', [])
        external = data.get('external_resources', [])
        citations = data.get('citations', [])

        # Count DOIs
        ref_text = str(references) + str(external) + str(citations)
        dois = re.findall(r'10\.\d{4,}/[^\s]+', ref_text)

        if len(dois) >= 2:
            score = 5
            quality_note = f"Multiple references: {len(dois)} DOIs"
        elif len(dois) == 1:
            score = 3
            quality_note = "One DOI cited"
        else:
            score = 0
            quality_note = "No publications cited"

    # Q15: Human Subject Representation
    elif question_id == 15:
        population = get_nested_value(data, 'composition.population')
        subpops = data.get('subpopulations', [])
        instances = data.get('instances', [])

        has_demographics = bool(population) or bool(subpops)
        # Look for participant counts
        combined = str(instances) + str(population)
        has_counts = bool(re.search(r'\d+\s+(?:participants?|subjects?|samples?)', combined, re.I))
        # Look for diversity mentions
        has_diversity = bool(re.search(r'(?:demographic|diversity|inclusion|exclusion|criteria)', combined, re.I))

        detail_count = sum([has_demographics, has_counts, has_diversity])

        if detail_count >= 2:
            score = 5
            quality_note = "Detailed demographics and criteria"
        elif detail_count >= 1:
            score = 3
            quality_note = "General human data"
        else:
            score = 0
            quality_note = "No human subject information"

    # Q16: Findability (pass/fail)
    elif question_id == 16:
        has_links = bool(data.get('page') or data.get('download_url') or data.get('external_resources'))

        if has_links:
            score = 1
            quality_note = "Pass: External URLs present"
        else:
            score = 0
            quality_note = "Fail: No external links"

    # Q17: Accessibility (Access Mechanism)
    elif question_id == 17:
        dist_formats = data.get('distribution_formats', [])
        access = data.get('access_and_licensing', {})
        license_terms = data.get('license_and_use_terms', {})

        has_platform = bool(re.search(r'(?:PhysioNet|Dataverse|FAIRhub|Zenodo)', str(dist_formats) + str(access), re.I))
        has_access_desc = bool(access or license_terms)
        has_url = bool(data.get('page'))

        detail_count = sum([has_platform, has_access_desc, has_url])

        if detail_count >= 3:
            score = 5
            quality_note = "Fully defined access path"
        elif detail_count >= 1:
            score = 3
            quality_note = "Partially described"
        else:
            score = 0
            quality_note = "Unclear access method"

    # Q18: Reusability (License Clarity)
    elif question_id == 18:
        license_terms = data.get('license_and_use_terms', {})

        if license_terms:
            license_str = str(license_terms)
            # Check for specific license types
            has_specific = bool(re.search(r'(?:CC BY|MIT|Apache|GPL|BSD|Registered Access)', license_str, re.I))
            # Check for reuse terms
            has_reuse = bool(re.search(r'(?:reuse|permit|allow|commercial|non-commercial)', license_str, re.I))

            if has_specific and has_reuse:
                score = 5
                quality_note = "License explicitly defines reuse terms"
            elif has_specific:
                score = 3
                quality_note = "License present, unclear reuse"
            else:
                score = 1
                quality_note = "Generic license info"
        else:
            score = 0
            quality_note = "No license"

    # Q19: Data Integrity and Provenance
    elif question_id == 19:
        updates = data.get('updates', {})
        version_access = data.get('version_access', {})
        release_notes = data.get('release_notes', {})

        has_changes = bool(updates or release_notes)
        # Look for timestamps
        prov_text = str(updates) + str(version_access) + str(release_notes)
        has_timestamps = bool(re.search(r'\d{4}-\d{2}-\d{2}', prov_text))
        has_versions = bool(version_access)

        detail_count = sum([has_changes, has_timestamps, has_versions])

        if detail_count >= 2:
            score = 5
            quality_note = "Structured version control with timestamps"
        elif detail_count >= 1:
            score = 3
            quality_note = "Change notes only"
        else:
            score = 0
            quality_note = "No provenance metadata"

    # Q20: Interlinking Across Platforms (pass/fail)
    elif question_id == 20:
        external = data.get('external_resources', [])
        same_as = data.get('same_as', [])

        # Look for multiple platform mentions
        platform_text = str(external) + str(same_as) + str(data.get('page', ''))
        platforms = set(re.findall(r'\b(PhysioNet|Dataverse|FAIRhub|Zenodo|doi\.org|github\.com)\b', platform_text, re.I))

        if len(platforms) >= 2:
            score = 1
            quality_note = f"Pass: Cross-platform links ({', '.join(platforms)})"
        else:
            score = 0
            quality_note = "Fail: No cross-platform linkages"

    # Default: presence = full score
    else:
        score = max_score
        quality_note = "Field present"

    return score, evidence, quality_note


def evaluate_d4d_file(file_path: Path, project: str, method: str, eval_type: str) -> Dict:
    """Evaluate a single D4D file against rubric20."""

    # Load YAML
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return {
            "error": f"Failed to load YAML: {e}",
            "d4d_file": str(file_path.relative_to(BASE_DIR))
        }

    # Initialize evaluation result
    result = {
        "rubric": "rubric20",
        "version": "1.0",
        "d4d_file": str(file_path.relative_to(BASE_DIR)),
        "project": project,
        "method": method,
        "type": eval_type,
        "evaluation_timestamp": datetime.now().isoformat(),
        "model": {
            "name": "hybrid-heuristic-evaluator",
            "temperature": "N/A",
            "evaluation_type": "rule_based_with_quality_heuristics"
        },
        "overall_score": {},
        "categories": {},
        "questions": [],
        "metadata": {
            "evaluator_id": "batch-hybrid-evaluator",
            "rubric_hash": "sha256-rubric20",
            "d4d_file_hash": hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        }
    }

    total_score = 0
    max_total = 84  # 16 numeric questions × 5 + 4 pass/fail × 1

    # Group by category
    categories = {}

    # Evaluate each question
    for q_id, spec in RUBRIC20_QUESTIONS.items():
        score, evidence, quality_note = evaluate_question(data, q_id)

        category = spec["category"]
        if category not in categories:
            categories[category] = {
                "name": category,
                "questions": [],
                "category_score": 0,
                "category_max": 0
            }

        question_result = {
            "id": q_id,
            "name": spec["name"],
            "description": spec["description"],
            "score": score,
            "max_score": spec["max_score"],
            "score_type": spec["score_type"],
            "evidence": evidence,
            "quality_note": quality_note
        }

        result["questions"].append(question_result)
        categories[category]["questions"].append(question_result)
        categories[category]["category_score"] += score
        categories[category]["category_max"] += spec["max_score"]
        total_score += score

    # Add category summaries
    result["categories"] = categories

    # Calculate overall score
    result["overall_score"] = {
        "total_points": total_score,
        "max_points": max_total,
        "percentage": round((total_score / max_total) * 100, 1)
    }

    return result


def main():
    print("=" * 70)
    print("Rubric20 Hybrid Batch Evaluator")
    print("=" * 70)
    print()

    # Load file inventory
    inventory_path = BASE_DIR / "data" / "evaluation_llm" / "rubric10" / "file_inventory.json"

    if not inventory_path.exists():
        print(f"❌ File inventory not found: {inventory_path}")
        print("   Run: python scripts/evaluate_all_d4ds_rubric10.py")
        return 1

    with open(inventory_path) as f:
        inventory = json.load(f)

    total_files = inventory["metadata"]["total_files"]
    print(f"📊 Found {total_files} files to evaluate with rubric20")
    print(f"   - Individual: {inventory['metadata']['total_individual_files']}")
    print(f"   - Concatenated: {inventory['metadata']['total_concatenated_files']}")
    print()

    # Create output directories
    output_dir = BASE_DIR / "data" / "evaluation_llm" / "rubric20"
    (output_dir / "individual").mkdir(parents=True, exist_ok=True)
    (output_dir / "concatenated").mkdir(parents=True, exist_ok=True)

    # Evaluate concatenated files
    print("━" * 70)
    print("Evaluating Concatenated Files")
    print("━" * 70)

    concat_count = 0
    for key, file_path in inventory["concatenated_files"].items():
        parts = key.split('_')
        project = parts[0]
        method = '_'.join(parts[1:-1])

        file_full_path = BASE_DIR / file_path

        if not file_full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        print(f"📄 [{concat_count + 1}/16] {project} / {method}")

        result = evaluate_d4d_file(file_full_path, project, method, "concatenated")

        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            continue

        # Save result
        output_file = output_dir / "concatenated" / f"{project}_{method}_evaluation.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        score = result["overall_score"]
        print(f"   ✅ Score: {score['total_points']}/84 ({score['percentage']}%)")

        concat_count += 1

    print()

    # Evaluate individual files
    print("━" * 70)
    print("Evaluating Individual Files")
    print("━" * 70)

    individual_count = 0
    total_individual = sum(len(files) for files in inventory["individual_files"].values())

    for key, file_list in inventory["individual_files"].items():
        parts = key.split('_')
        project = parts[0]
        method = '_'.join(parts[1:-1])

        for file_path in file_list:
            file_full_path = BASE_DIR / file_path

            if not file_full_path.exists():
                print(f"⚠️  File not found: {file_path}")
                continue

            file_name = file_full_path.stem.replace('_d4d', '')

            print(f"📄 [{individual_count + 1}/{total_individual}] {project} / {method} / {file_name[:40]}")

            result = evaluate_d4d_file(file_full_path, project, method, "individual")

            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                continue

            # Save result
            output_file = output_dir / "individual" / f"{project}_{method}_{file_name}_evaluation.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)

            score = result["overall_score"]
            print(f"   ✅ Score: {score['total_points']}/84 ({score['percentage']}%)")

            individual_count += 1

    print()
    print("=" * 70)
    print(f"✅ Evaluation Complete!")
    print(f"   Total files evaluated: {concat_count + individual_count}")
    print(f"   - Concatenated: {concat_count}")
    print(f"   - Individual: {individual_count}")
    print()
    print("📊 Results saved to:")
    print(f"   {output_dir / 'concatenated'}")
    print(f"   {output_dir / 'individual'}")
    print()
    print("Next step:")
    print("   python scripts/summarize_rubric20_results.py")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
