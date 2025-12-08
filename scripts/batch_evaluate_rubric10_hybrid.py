#!/usr/bin/env python3
"""
Hybrid Rubric10 Batch Evaluation Script

Uses YAML parsing + quality heuristics to evaluate all D4D files against rubric10.
Faster than LLM-based evaluation, more insightful than pure presence detection.

Usage:
    python scripts/batch_evaluate_rubric10_hybrid.py

Output:
    - data/evaluation_llm/rubric10/individual/*.json
    - data/evaluation_llm/rubric10/concatenated/*.json
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Rubric10 specification
RUBRIC10_ELEMENTS = {
    1: {
        "name": "Dataset Discovery and Identification",
        "description": "Can a user or system discover and uniquely identify this dataset?",
        "sub_elements": [
            {"name": "Persistent Identifier (DOI, RRID, etc.)", "fields": ["doi", "rrid", "id"]},
            {"name": "Dataset Title and Description Completeness", "fields": ["title", "description"]},
            {"name": "Keywords or Tags for Searchability", "fields": ["keywords"]},
            {"name": "Dataset Landing Page or Platform URL", "fields": ["page", "external_resources"]},
            {"name": "Associated Project or Program", "fields": ["project", "keywords"]}
        ]
    },
    2: {
        "name": "Dataset Access and Retrieval",
        "description": "Can the dataset and its associated resources be located, accessed, and downloaded?",
        "sub_elements": [
            {"name": "Access Mechanism Defined", "fields": ["access_and_licensing.access_policy", "license_and_use_terms"]},
            {"name": "Data Use Agreement Required?", "fields": ["access_and_licensing.data_use_agreement", "license_and_use_terms"]},
            {"name": "Download URL or Platform Link Available", "fields": ["distribution_formats", "download_url", "page"]},
            {"name": "File Formats Specified", "fields": ["data_characteristics.data_formats", "files.listing.type", "distribution_formats"]},
            {"name": "External Links to Similar or Related Datasets", "fields": ["external_resources", "project_website"]}
        ]
    },
    3: {
        "name": "Data Reuse and Interoperability",
        "description": "Is sufficient information provided to reuse and integrate the dataset with others?",
        "sub_elements": [
            {"name": "License Terms Allow Reuse", "fields": ["license_and_use_terms.description", "license_and_use_terms"]},
            {"name": "Data Formats Are Standardized", "fields": ["data_characteristics.data_formats", "distribution_formats"]},
            {"name": "Schema or Ontology Conformance Stated", "fields": ["conforms_to"]},
            {"name": "Identifiers Defined for Linking", "fields": ["data_characteristics.identifiers_in_files"]},
            {"name": "Documentation of Processing Tools for Reproducibility", "fields": ["software_and_tools", "open_source_code"]}
        ]
    },
    4: {
        "name": "Ethical Use and Privacy Safeguards",
        "description": "Does the dataset provide clear information about consent, privacy, and ethical oversight?",
        "sub_elements": [
            {"name": "IRB or Ethics Review Documented", "fields": ["ethics.irb_approval", "ethical_reviews"]},
            {"name": "Deidentification Method Described", "fields": ["deidentification_and_privacy.approach", "is_deidentified"]},
            {"name": "Identifiers Removed or Masked", "fields": ["deidentification_and_privacy.examples_of_identifiers_removed", "is_deidentified"]},
            {"name": "Informed Consent Obtained from Participants", "fields": ["collection_process.consent", "informed_consent"]},
            {"name": "Ethical Sourcing Statement Included", "fields": ["ethics.ethical_position", "purposes"]}
        ]
    },
    5: {
        "name": "Data Composition and Structure",
        "description": "Can the dataset's structure, modality, and population be understood from metadata?",
        "sub_elements": [
            {"name": "Cohort or Population Characteristics Described", "fields": ["composition.population", "subpopulations", "instances"]},
            {"name": "Number of Participants or Samples Reported", "fields": ["composition.population.participants", "instances"]},
            {"name": "Modalities or Data Types Listed", "fields": ["data_characteristics.modalities", "instances"]},
            {"name": "Conditions or Phenotypes Represented", "fields": ["composition.condition_groups", "subpopulations"]},
            {"name": "File Dimensions or Sampling Rates Provided", "fields": ["data_characteristics.sampling_and_dimensions"]}
        ]
    },
    6: {
        "name": "Data Provenance and Version Tracking",
        "description": "Can a user determine dataset versions, update history, and provenance?",
        "sub_elements": [
            {"name": "Dataset Version Number Provided", "fields": ["dataset_version", "version"]},
            {"name": "Version History Documented", "fields": ["release_notes", "updates"]},
            {"name": "Change Descriptions for Each Version", "fields": ["release_notes.notes", "updates"]},
            {"name": "Update Schedule or Frequency Indicated", "fields": ["updates"]},
            {"name": "Versioned Documentation or External References", "fields": ["version_access", "external_resources"]}
        ]
    },
    7: {
        "name": "Scientific Motivation and Funding Transparency",
        "description": "Does the metadata clearly state why the dataset exists and who funded it?",
        "sub_elements": [
            {"name": "Motivation or Rationale for Dataset Creation", "fields": ["motivation", "purposes"]},
            {"name": "Primary Research Objective or Task", "fields": ["intended_uses.primary", "tasks"]},
            {"name": "Funding Source or Grant Agency Listed", "fields": ["funding_and_acknowledgements.funding.agency", "funders"]},
            {"name": "Award Number or Grant ID Present", "fields": ["funding_and_acknowledgements.funding.award_number", "funders"]},
            {"name": "Acknowledgement of Platform or Participant Support", "fields": ["funding_and_acknowledgements.acknowledgements", "funders"]}
        ]
    },
    8: {
        "name": "Technical Transparency (Data Collection and Processing)",
        "description": "Can data collection and processing steps be replicated or understood?",
        "sub_elements": [
            {"name": "Collection Setting or Sites Described", "fields": ["collection_process.setting", "data_collectors", "acquisition_methods"]},
            {"name": "Data Capture Method or Device Listed", "fields": ["collection_process.data_capture", "collection_mechanisms", "acquisition_methods"]},
            {"name": "Preprocessing or Cleaning Steps Documented", "fields": ["preprocessing_and_derived_data.raw_audio_processing", "preprocessing_strategies", "cleaning_strategies"]},
            {"name": "Open-Source Processing Code Provided", "fields": ["software_and_tools.preprocessing_code", "open_source_code"]},
            {"name": "External Standards or References Cited", "fields": ["references", "external_resources"]}
        ]
    },
    9: {
        "name": "Dataset Evaluation and Limitations Disclosure",
        "description": "Does the metadata communicate known risks, biases, or dataset limitations?",
        "sub_elements": [
            {"name": "Limitations Section Present", "fields": ["limitations"]},
            {"name": "Sampling Bias or Representativeness Noted", "fields": ["composition.population", "sampling_and_dimensions", "sampling_strategies", "anomalies"]},
            {"name": "Quality Control or Validation Steps Mentioned", "fields": ["preprocessing_and_derived_data", "data_quality", "cleaning_strategies"]},
            {"name": "Known Risks or Use Constraints Listed", "fields": ["intended_uses.usage_notes", "discouraged_uses", "future_use_impacts"]},
            {"name": "Conflicts of Interest Declared", "fields": ["ethics.conflicts_of_interest"]}
        ]
    },
    10: {
        "name": "Cross-Platform and Community Integration",
        "description": "Does the dataset connect to wider data ecosystems, repositories, or standards?",
        "sub_elements": [
            {"name": "Dataset Published on a Recognized Platform", "fields": ["publisher", "access_and_licensing.platform", "page", "maintainers"]},
            {"name": "Cross-referenced DOIs or Related Dataset Links", "fields": ["external_resources", "references", "same_as"]},
            {"name": "Community Standards or Schema Reference", "fields": ["conforms_to"]},
            {"name": "Associated Outreach Materials", "fields": ["external_resources", "distribution_formats"]},
            {"name": "Similar Dataset Links or Thematic Grouping", "fields": ["project", "related_datasets"]}
        ]
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


def check_field_presence(data: Dict, fields: List[str]) -> tuple[bool, str]:
    """
    Check if any of the specified fields are present and non-empty.
    Returns (is_present, evidence_string).
    """
    for field in fields:
        value = get_nested_value(data, field)
        if value is not None and value != "" and value != []:
            # Generate evidence string
            if isinstance(value, str):
                evidence = f"{field}: {value[:100]}..." if len(str(value)) > 100 else f"{field}: {value}"
            elif isinstance(value, list):
                evidence = f"{field}: {len(value)} items"
            elif isinstance(value, dict):
                evidence = f"{field}: present (dict with {len(value)} keys)"
            else:
                evidence = f"{field}: {value}"
            return True, evidence
    return False, f"Missing: {', '.join(fields)}"


def apply_quality_heuristics(data: Dict, element_id: int, sub_element_idx: int) -> tuple[int, str]:
    """
    Apply quality heuristics for specific sub-elements.
    Returns (score, quality_note).
    """
    sub_elem = RUBRIC10_ELEMENTS[element_id]["sub_elements"][sub_element_idx]
    fields = sub_elem["fields"]

    # Check basic presence first
    is_present, evidence = check_field_presence(data, fields)

    if not is_present:
        return 0, "Field absent or empty"

    # Apply quality heuristics
    score = 0
    quality_note = ""

    # Element 1, Sub 1: DOI/Identifier
    if element_id == 1 and sub_element_idx == 0:
        doi_value = data.get('doi') or data.get('id', '')
        if 'doi.org' in str(doi_value) or 'RRID:' in str(doi_value):
            score = 1
            quality_note = "Valid persistent identifier format"
        elif doi_value:
            score = 1
            quality_note = "Identifier present"

    # Element 1, Sub 2: Title + Description
    elif element_id == 1 and sub_element_idx == 1:
        title = data.get('title', '')
        desc = data.get('description', '')
        if title and len(title) > 10 and desc and len(str(desc)) >= 200:
            score = 1
            quality_note = f"Comprehensive title and description ({len(str(desc))} chars)"
        elif title and desc:
            score = 1
            quality_note = "Title and description present but brief"

    # Element 1, Sub 3: Keywords
    elif element_id == 1 and sub_element_idx == 2:
        keywords = data.get('keywords', [])
        if isinstance(keywords, list) and len(keywords) >= 5:
            score = 1
            quality_note = f"{len(keywords)} keywords provided"
        elif keywords:
            score = 1
            quality_note = f"Only {len(keywords) if isinstance(keywords, list) else 1} keywords"

    # Element 5, Sub 2: Participant counts
    elif element_id == 5 and sub_element_idx == 1:
        # Look for numeric values in instances or description
        instances = str(data.get('instances', ''))
        desc = str(data.get('description', ''))
        combined = instances + desc
        # Check for patterns like "306 participants" or "12,523 recordings"
        import re
        numbers = re.findall(r'\d+[,\d]*\s+(?:participants?|recordings?|samples?|subjects?)', combined)
        if numbers:
            score = 1
            quality_note = f"Participant/sample counts found: {numbers[0]}"
        elif any(word in combined.lower() for word in ['participants', 'samples', 'recordings', 'subjects']):
            score = 0
            quality_note = "Mentions participants but no specific count"

    # Element 7, Sub 3-5: Funding information
    elif element_id == 7 and sub_element_idx >= 2:
        funders = data.get('funders', [])
        if isinstance(funders, list) and funders:
            funder_str = str(funders[0]) if funders else ""
            if sub_element_idx == 2:  # Agency
                if any(agency in funder_str for agency in ['NIH', 'NSF', 'National']):
                    score = 1
                    quality_note = "Funding agency identified"
            elif sub_element_idx == 3:  # Award number
                import re
                if re.search(r'\d[A-Z0-9]{8,}', funder_str):
                    score = 1
                    quality_note = "Grant award number present"
            elif sub_element_idx == 4:  # Acknowledgements
                score = 1
                quality_note = "Funders documented"
        else:
            # Check old-style funding fields
            funding = get_nested_value(data, 'funding_and_acknowledgements.funding.agency')
            if funding:
                score = 1
                quality_note = "Funding information present"

    # Default: If present, give credit
    else:
        score = 1
        quality_note = "Field present"

    return score, quality_note


def evaluate_d4d_file(file_path: Path, project: str, method: str, eval_type: str) -> Dict:
    """Evaluate a single D4D file against rubric10."""

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
        "rubric": "rubric10",
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
        "elements": [],
        "assessment": {
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        },
        "metadata": {
            "evaluator_id": "batch-hybrid-evaluator",
            "rubric_hash": "sha256-rubric10",
            "d4d_file_hash": hashlib.sha256(open(file_path, 'rb').read()).hexdigest()
        }
    }

    total_score = 0

    # Evaluate each element
    for element_id, element_spec in RUBRIC10_ELEMENTS.items():
        element_result = {
            "id": element_id,
            "name": element_spec["name"],
            "description": element_spec["description"],
            "sub_elements": [],
            "element_score": 0,
            "element_max": 5
        }

        # Evaluate each sub-element
        for idx, sub_elem in enumerate(element_spec["sub_elements"]):
            score, quality_note = apply_quality_heuristics(data, element_id, idx)
            is_present, evidence = check_field_presence(data, sub_elem["fields"])

            element_result["sub_elements"].append({
                "name": sub_elem["name"],
                "score": score,
                "evidence": evidence if is_present else quality_note,
                "quality_note": quality_note
            })

            element_result["element_score"] += score

        total_score += element_result["element_score"]
        result["elements"].append(element_result)

    # Calculate overall score
    result["overall_score"] = {
        "total_points": total_score,
        "max_points": 50,
        "percentage": round((total_score / 50) * 100, 1)
    }

    # Generate assessment (simple heuristics)
    strengths = []
    weaknesses = []

    for elem in result["elements"]:
        if elem["element_score"] >= 4:
            strengths.append(f"Strong {elem['name']} ({elem['element_score']}/5)")
        elif elem["element_score"] <= 1:
            weaknesses.append(f"Missing {elem['name']} ({elem['element_score']}/5)")

    result["assessment"]["strengths"] = strengths
    result["assessment"]["weaknesses"] = weaknesses

    return result


def main():
    print("=" * 70)
    print("Rubric10 Hybrid Batch Evaluator")
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
    print(f"📊 Found {total_files} files to evaluate")
    print(f"   - Individual: {inventory['metadata']['total_individual_files']}")
    print(f"   - Concatenated: {inventory['metadata']['total_concatenated_files']}")
    print()

    # Create output directories
    output_dir = BASE_DIR / "data" / "evaluation_llm" / "rubric10"
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
        print(f"   ✅ Score: {score['total_points']}/50 ({score['percentage']}%)")

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
            print(f"   ✅ Score: {score['total_points']}/50 ({score['percentage']}%)")

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
    print("   python scripts/summarize_rubric10_results.py")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
