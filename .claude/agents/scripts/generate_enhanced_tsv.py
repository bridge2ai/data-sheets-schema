#!/usr/bin/env python3
"""
Generate enhanced TSV v2 with semantic annotations from v1 TSV mapping.

Adds 7 semantic annotation columns:
1. Mapping_Type - exactMatch | closeMatch | broadMatch | narrowMatch | relatedMatch
2. SKOS_Relation - Full SKOS predicate URI
3. Information_Loss - none | minimal | moderate | high | bidirectional
4. Inverse_Mapping - D4D field for reverse transform (if different)
5. Validation_Rule - SHACL path or LinkML constraint reference
6. Example_D4D_Value - Sample value in D4D format
7. Example_RO_Crate_Value - Sample value in RO-Crate format
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# SKOS mapping type rules based on the alignment
MAPPING_RULES = {
    # Exact matches (direct 1:1, no transformation)
    'title': ('exactMatch', 'none', 'title', '"AI-READI Dataset"', '"AI-READI Dataset"'),
    'description': ('exactMatch', 'none', 'description', '"Diabetes dataset..."', '"Diabetes dataset..."'),
    'doi': ('exactMatch', 'none', 'doi', '"10.5281/zenodo.123456"', '"10.5281/zenodo.123456"'),
    'keywords': ('exactMatch', 'none', 'keywords', '["diabetes", "AI"]', '["diabetes", "AI"]'),
    'language': ('exactMatch', 'none', 'language', '"en"', '"en"'),
    'license': ('exactMatch', 'none', 'license', '"CC-BY-4.0"', '"CC-BY-4.0"'),
    'publisher': ('exactMatch', 'none', 'publisher', '"UCSD"', '"UCSD"'),
    'version': ('exactMatch', 'none', 'version', '"1.0"', '"1.0"'),
    'page': ('exactMatch', 'none', 'page', '"https://aireadi.org"', '"https://aireadi.org"'),
    'download_url': ('exactMatch', 'none', 'download_url', '"https://data.org/d.zip"', '"https://data.org/d.zip"'),
    'bytes': ('exactMatch', 'none', 'bytes', '1073741824', '1073741824'),
    'md5': ('exactMatch', 'none', 'md5', '"a1b2c3d4..."', '"a1b2c3d4..."'),
    'sha256': ('exactMatch', 'none', 'sha256', '"e5f6a7b8..."', '"e5f6a7b8..."'),
    'hash': ('exactMatch', 'none', 'hash', '"a1b2c3d4..."', '"a1b2c3d4..."'),
    'created_on': ('exactMatch', 'none', 'created_on', '"2024-01-15"', '"2024-01-15"'),
    'issued': ('exactMatch', 'none', 'issued', '"2024-03-01"', '"2024-03-01"'),
    'last_updated_on': ('exactMatch', 'none', 'last_updated_on', '"2024-06-01"', '"2024-06-01"'),
    'status': ('exactMatch', 'none', 'status', '"Published"', '"Published"'),
    'conforms_to': ('exactMatch', 'none', 'conforms_to', '"https://spec.org"', '"https://spec.org"'),
    'was_derived_from': ('exactMatch', 'none', 'was_derived_from', '"10.5281/zenodo.111"', '"10.5281/zenodo.111"'),

    # D4D namespace exact matches
    'addressing_gaps': ('exactMatch', 'none', 'addressing_gaps', '"Fill data gap in diabetes..."', '"Fill data gap in diabetes..."'),
    'anomalies': ('exactMatch', 'none', 'anomalies', '"5 outliers detected..."', '"5 outliers detected..."'),
    'content_warnings': ('exactMatch', 'none', 'content_warnings', '"Contains medical images"', '"Contains medical images"'),
    'informed_consent': ('exactMatch', 'none', 'informed_consent', '"Written consent obtained"', '"Written consent obtained"'),

    # RAI namespace exact matches
    'acquisition_methods': ('exactMatch', 'none', 'acquisition_methods', '"Clinical sensors, EHR export"', '"Clinical sensors, EHR export"'),
    'collection_mechanisms': ('exactMatch', 'none', 'collection_mechanisms', '"Automated API extraction"', '"Automated API extraction"'),
    'collection_timeframes': ('exactMatch', 'none', 'collection_timeframes', '"2023-01 to 2024-06"', '"2023-01 to 2024-06"'),
    'confidential_elements': ('exactMatch', 'none', 'confidential_elements', '"PHI, genetic data"', '"PHI, genetic data"'),
    'sensitive_elements': ('exactMatch', 'none', 'sensitive_elements', '"Race, ethnicity, health status"', '"Race, ethnicity, health status"'),
    'data_protection_impacts': ('exactMatch', 'none', 'data_protection_impacts', '"DPIA completed 2024-01"', '"DPIA completed 2024-01"'),
    'future_use_impacts': ('exactMatch', 'none', 'future_use_impacts', '"Risk of re-identification..."', '"Risk of re-identification..."'),
    'discouraged_uses': ('exactMatch', 'none', 'discouraged_uses', '"Insurance decisions..."', '"Insurance decisions..."'),
    'prohibited_uses': ('exactMatch', 'none', 'prohibited_uses', '"Surveillance, profiling"', '"Surveillance, profiling"'),
    'distribution_dates': ('exactMatch', 'none', 'distribution_dates', '"2024-03-01"', '"2024-03-01"'),
    'errata': ('exactMatch', 'none', 'errata', '"Bug fix in v1.1..."', '"Bug fix in v1.1..."'),
    'ethical_reviews': ('exactMatch', 'none', 'ethical_reviews', '"IRB #2023-456 approved"', '"IRB #2023-456 approved"'),
    'existing_uses': ('exactMatch', 'none', 'existing_uses', '"Diabetes prediction models"', '"Diabetes prediction models"'),
    'intended_uses': ('exactMatch', 'none', 'intended_uses', '"Research on diabetes..."', '"Research on diabetes..."'),
    'other_tasks': ('exactMatch', 'none', 'other_tasks', '"Risk stratification..."', '"Risk stratification..."'),
    'tasks': ('exactMatch', 'none', 'tasks', '"Classification, regression"', '"Classification, regression"'),
    'purposes': ('closeMatch', 'minimal', 'purposes', '"Research, education"', '"Research, education"'),
    'known_biases': ('exactMatch', 'none', 'known_biases', '"Sampling bias toward..."', '"Sampling bias toward..."'),
    'known_limitations': ('exactMatch', 'none', 'known_limitations', '"Small sample size..."', '"Small sample size..."'),
    'imputation_protocols': ('exactMatch', 'none', 'imputation_protocols', '"MICE for missing values"', '"MICE for missing values"'),
    'missing_data_documentation': ('exactMatch', 'none', 'missing_data_documentation', '"15% missing in glucose..."', '"15% missing in glucose..."'),
    'raw_data_sources': ('exactMatch', 'none', 'raw_data_sources', '"Epic EHR, lab LIMS"', '"Epic EHR, lab LIMS"'),
    'raw_sources': ('exactMatch', 'none', 'raw_sources', '"Epic EHR, lab LIMS"', '"Epic EHR, lab LIMS"'),
    'updates': ('exactMatch', 'none', 'updates', '"Quarterly updates planned"', '"Quarterly updates planned"'),
    'human_subject_research': ('exactMatch', 'none', 'human_subject_research', '"Yes, IRB approved"', '"Yes, IRB approved"'),
    'at_risk_populations': ('exactMatch', 'none', 'at_risk_populations', '"Children excluded"', '"Children excluded"'),

    # FAIRSCAPE Evidence namespace
    'distribution_formats': ('exactMatch', 'none', 'distribution_formats', '"CSV, Parquet"', '"CSV, Parquet"'),
    'encoding': ('closeMatch', 'minimal', 'encoding', '"UTF-8"', '"text/csv; charset=UTF-8"'),
    'funders': ('exactMatch', 'none', 'funders', '"NIH, NSF"', '"NIH, NSF"'),

    # Close matches (require transformation)
    'creators': ('closeMatch', 'minimal', 'creators[].name', '"John Doe, Jane Smith"', '[{"@type":"Person","name":"John Doe"},{"@type":"Person","name":"Jane Smith"}]'),
    'created_by': ('closeMatch', 'minimal', 'created_by.name', '"AI-READI Team"', '{"@type":"Organization","name":"AI-READI Team"}'),
    'modified_by': ('closeMatch', 'minimal', 'modified_by.name', '"Data Team"', '{"@type":"Organization","name":"Data Team"}'),

    'cleaning_strategies': ('closeMatch', 'minimal', 'cleaning_strategies[].description', '[{"description":"Removed duplicates","step_type":"data_cleaning"}]', '"Removed duplicate records using MD5 hash"'),
    'preprocessing_strategies': ('closeMatch', 'minimal', 'preprocessing_strategies[].description', '[{"description":"Normalized values","step_type":"normalization"}]', '"Normalized glucose values to 0-1 range"'),
    'labeling_strategies': ('closeMatch', 'minimal', 'labeling_strategies[].description', '[{"description":"Manual annotation","annotator_type":"expert"}]', '"Expert clinicians labeled diagnoses"'),
    'annotation_analyses': ('closeMatch', 'minimal', 'annotation_analyses[].description', '[{"description":"Inter-rater reliability 0.89"}]', '"Inter-rater reliability: 0.89 (Cohen\'s kappa)"'),
    'machine_annotation_analyses': ('closeMatch', 'minimal', 'machine_annotation_analyses[].tool_name', '[{"tool_name":"spaCy","version":"3.5"}]', '"spaCy v3.5 for NER"'),

    'license_and_use_terms': ('closeMatch', 'moderate', 'license + conditionsOfAccess', '"CC-BY-4.0, attribution required"', '{"license":"CC-BY-4.0","conditionsOfAccess":"Attribution required"}'),
    'ip_restrictions': ('closeMatch', 'minimal', 'ip_restrictions', '"No commercial use"', '"No commercial use"'),
    'extension_mechanism': ('closeMatch', 'moderate', 'extension_mechanism', '"GitHub PRs accepted"', '"GitHub PRs accepted"'),
    'regulatory_restrictions': ('closeMatch', 'minimal', 'regulatory_restrictions', '"HIPAA, GDPR"', '"HIPAA, GDPR"'),

    'compression': ('closeMatch', 'minimal', 'compression', '"gzip"', '"application/gzip"'),
    'dialect': ('closeMatch', 'minimal', 'dialect.delimiter', '{"delimiter":",","header":true}', '"text/csv; header=present; delimiter=,"'),
    'media_type': ('closeMatch', 'minimal', 'media_type', '"text/csv"', '"text/csv"'),

    'external_resource': ('closeMatch', 'minimal', 'external_resource', '"https://pubmed.org/123"', '{"@type":"ScholarlyArticle","url":"https://pubmed.org/123"}'),

    # Related matches (complex/partial)
    'instances': ('relatedMatch', 'high', 'instances[].data_topic', '[{"data_topic":"Patient","instance_type":"record","counts":1000}]', '"1000 patient records"'),
    'subpopulations': ('relatedMatch', 'moderate', 'subpopulations[].subpopulation_elements_present', '[{"subpopulation_elements_present":"age,gender","distribution":"50% male, 50% female"}]', '"Demographics: 50% male, 50% female, ages 18-65"'),
    'resources': ('relatedMatch', 'moderate', 'resources[]', '[{"@type":"Dataset","name":"Subset A"}]', '{"hasPart":[{"@type":"Dataset","name":"Subset A"}]}'),
    'data_collectors': ('relatedMatch', 'moderate', 'data_collectors[].name', '[{"name":"Research assistants","compensation":"$20/hr"}]', '{"contributor":[{"@type":"Person","name":"Research assistants"}]}'),
    'maintainers': ('relatedMatch', 'minimal', 'maintainers', '"Data team at UCSD"', '"Data team at UCSD"'),
    'subsets': ('relatedMatch', 'high', 'subsets[].is_data_split', '[{"is_data_split":"train","is_sub_population":"adults"}]', '{"hasPart":[{"name":"Training set"}]}'),
    'sampling_strategies': ('relatedMatch', 'moderate', 'sampling_strategies', '"Random sampling, stratified by age"', '"Random sampling, stratified by age"'),
    'version_access': ('relatedMatch', 'minimal', 'version_access', '"All versions available"', '"All versions available"'),
    'use_repository': ('relatedMatch', 'minimal', 'use_repository', '"https://github.com/org/repo"', '"https://github.com/org/repo"'),

    # Narrow/broad matches
    'path': ('narrowMatch', 'minimal', 'path', '"data/file.csv"', '"https://example.org/data/file.csv"'),
    'is_deidentified': ('narrowMatch', 'minimal', 'is_deidentified', 'true', '"de-identified"'),
    'is_tabular': ('narrowMatch', 'minimal', 'is_tabular', 'true', '"text/csv"'),
    'retention_limit': ('narrowMatch', 'minimal', 'retention_limit', '"5 years"', '"Data retained for 5 years per IRB protocol"'),
}


def determine_mapping_type(property_name: str, direct_mapping: str) -> Tuple[str, str, str, str, str]:
    """
    Determine mapping type and semantic annotations for a property.

    Returns: (mapping_type, information_loss, inverse_mapping, example_d4d, example_rocrate)
    """
    if property_name in MAPPING_RULES:
        return MAPPING_RULES[property_name]

    # Default rules based on direct_mapping flag
    if direct_mapping == '1':
        return ('exactMatch', 'none', property_name, f'"{property_name} value"', f'"{property_name} value"')
    else:
        return ('closeMatch', 'minimal', property_name, f'"{property_name} value"', f'"{property_name} value"')


def get_skos_relation_uri(mapping_type: str) -> str:
    """Get full SKOS predicate URI for mapping type."""
    base = 'http://www.w3.org/2004/02/skos/core#'
    return f'{base}{mapping_type}'


def get_validation_rule(property_name: str, property_type: str) -> str:
    """Get validation rule reference for property."""
    # Map to D4D schema constraint or SHACL shape
    if property_type == 'URI':
        return 'xsd:anyURI constraint'
    elif property_type == 'Int':
        return 'xsd:integer constraint'
    elif property_type == 'Date':
        return 'xsd:date constraint'
    elif property_type == 'str':
        return 'xsd:string constraint'
    elif property_type:
        return f'd4d:{property_name}Shape'
    else:
        return ''


def enhance_tsv(input_path: Path, output_path: Path):
    """Enhance TSV v1 with semantic annotations to create v2."""

    with open(input_path, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in, delimiter='\t')

        # Enhanced column headers
        enhanced_headers = list(reader.fieldnames) + [
            'Mapping_Type',
            'SKOS_Relation',
            'Information_Loss',
            'Inverse_Mapping',
            'Validation_Rule',
            'Example_D4D_Value',
            'Example_RO_Crate_Value'
        ]

        rows = []
        for row in reader:
            property_name = row['D4D Property'].strip()
            property_type = row['Type'].strip()
            direct_mapping = row['Direct mapping? Yes =1; No = 0'].strip()

            # Skip header rows
            if not property_name or property_name.startswith('RO-Crate:'):
                rows.append(row)
                continue

            # Determine semantic annotations
            mapping_type, info_loss, inverse, ex_d4d, ex_rocrate = determine_mapping_type(
                property_name, direct_mapping
            )

            # Add semantic annotations
            row['Mapping_Type'] = mapping_type
            row['SKOS_Relation'] = get_skos_relation_uri(mapping_type)
            row['Information_Loss'] = info_loss
            row['Inverse_Mapping'] = inverse
            row['Validation_Rule'] = get_validation_rule(property_name, property_type)
            row['Example_D4D_Value'] = ex_d4d
            row['Example_RO_Crate_Value'] = ex_rocrate

            rows.append(row)

    # Write enhanced TSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=enhanced_headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Enhanced TSV v2 created: {output_path}")
    print(f"  Rows: {len(rows)}")
    print(f"  Columns: {len(enhanced_headers)} (added 7 semantic annotation columns)")


if __name__ == '__main__':
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent.parent

    input_file = repo_root / 'data' / 'ro-crate_mapping' / 'd4d_rocrate_mapping_v1.tsv'
    output_file = repo_root / 'data' / 'ro-crate_mapping' / 'd4d_rocrate_mapping_v2_semantic.tsv'

    if not input_file.exists():
        print(f"✗ Input file not found: {input_file}")
        sys.exit(1)

    enhance_tsv(input_file, output_file)
