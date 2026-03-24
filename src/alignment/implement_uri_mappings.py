#!/usr/bin/env python3
"""
Phase 2: Implementation Script for URI Mappings

This script adds slot_uri definitions to D4D schema files based on the
validated mapping recommendations in data/mappings/uri_mapping_recommendations.md

Usage:
    python src/alignment/implement_uri_mappings.py [--dry-run] [--priority {high,duo,d4d,rocrate,all}]
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple


class URIMappingImplementer:
    """Implements URI mappings by adding slot_uri definitions to schema files."""

    # Enum permissible_values that should NOT get slot_uri (LinkML doesn't support this)
    ENUM_VALUES = {
        # VariableTypeEnum values
        'integer', 'float', 'double', 'string', 'boolean', 'date', 'datetime',
        'categorical', 'ordinal', 'identifier', 'json', 'array', 'object',

        # ComplianceStatusEnum values
        'compliant', 'not_compliant', 'partially_compliant', 'under_review', 'not_applicable',

        # ConfidentialityLevelEnum values
        'unrestricted', 'restricted', 'confidential',

        # DataUsePermissionEnum values (DUO terms)
        'collaboration_required', 'disease_specific_research', 'ethics_approval_required',
        'general_research_use', 'genetic_studies_only', 'geographic_restriction',
        'health_medical_biomedical_research', 'institution_specific', 'no_commercial_use',
        'no_methods_development', 'no_population_ancestry_research', 'no_restriction',
        'non_profit_use_only', 'population_origins_ancestry_research', 'project_specific',
        'publication_moratorium', 'publication_required', 'return_to_database',
        'time_limit', 'user_specific', 'clinical_care_use',
    }

    # Mapping of slot names to their modules
    SLOT_TO_MODULE = {
        # Collection Module
        'was_validated_verified': 'D4D_Collection',
        'was_inferred_derived': 'D4D_Collection',
        'was_reported_by_subjects': 'D4D_Collection',
        'was_directly_observed': 'D4D_Collection',
        'acquisition_details': 'D4D_Collection',
        'collection_details': 'D4D_Collection',
        'collector_details': 'D4D_Collection',
        'missing_data_causes': 'D4D_Collection',
        'access_details': 'D4D_Collection',
        'raw_data_format': 'D4D_Collection',
        'is_direct': 'D4D_Collection',
        'missing_data_patterns': 'D4D_Collection',
        'role': 'D4D_Collection',
        'source_description': 'D4D_Collection',
        'source_type': 'D4D_Collection',

        # Composition Module
        'is_sample': 'D4D_Composition',
        'is_random': 'D4D_Composition',
        'is_representative': 'D4D_Composition',
        'representative_verification': 'D4D_Composition',
        'label_description': 'D4D_Composition',
        'bias_description': 'D4D_Composition',
        'identifiers_removed': 'D4D_Composition',
        'recommended_mitigation': 'D4D_Composition',
        'strategies': 'D4D_Composition',
        'missing': 'D4D_Composition',
        'restrictions': 'D4D_Composition',
        'identification': 'D4D_Composition',
        'source_data': 'D4D_Composition',
        'derivation': 'D4D_Variables',
        'affected_subsets': 'D4D_Composition',
        'bias_type': 'D4D_Composition',
        'scope_impact': 'D4D_Composition',
        'why_not_representative': 'D4D_Composition',
        'identifiable_elements_present': 'D4D_Composition',
        'missing_information': 'D4D_Composition',
        'subpopulation_elements_present': 'D4D_Composition',
        'description': 'D4D_Composition',
        'relationship_type': 'D4D_Composition',
        'method': 'D4D_Composition',
        'archival': 'D4D_Composition',
        'label': 'D4D_Composition',

        # Human Subjects Module
        'consent_obtained': 'D4D_Human',
        'consent_type': 'D4D_Human',
        'consent_documentation': 'D4D_Human',
        'withdrawal_mechanism': 'D4D_Human',
        'irb_approval': 'D4D_Human',
        'ethics_review_board': 'D4D_Human',
        'guardian_consent': 'D4D_Human',
        'assent_procedures': 'D4D_Human',
        'reidentification_risk': 'D4D_Human',
        'privacy_techniques': 'D4D_Human',
        'data_linkage': 'D4D_Human',
        'regulatory_compliance': 'D4D_Human',
        'special_populations': 'D4D_Human',
        'involves_human_subjects': 'D4D_Human',
        'anonymization_method': 'D4D_Human',

        # Data Governance Module
        'restricted': 'D4D_Data_Governance',
        'unrestricted': 'D4D_Data_Governance',
        'confidential': 'D4D_Data_Governance',
        'clinical_care_use': 'D4D_Data_Governance',
        'compliant': 'D4D_Data_Governance',
        'not_compliant': 'D4D_Data_Governance',
        'partially_compliant': 'D4D_Data_Governance',
        'under_review': 'D4D_Data_Governance',
        'not_applicable': 'D4D_Data_Governance',
        'other_compliance': 'D4D_Data_Governance',
        'hipaa_compliant': 'D4D_Data_Governance',

        # DUO terms in Data Governance
        'collaboration_required': 'D4D_Data_Governance',
        'disease_specific_research': 'D4D_Data_Governance',
        'ethics_approval_required': 'D4D_Data_Governance',
        'general_research_use': 'D4D_Data_Governance',
        'genetic_studies_only': 'D4D_Data_Governance',
        'geographic_restriction': 'D4D_Data_Governance',
        'health_medical_biomedical_research': 'D4D_Data_Governance',
        'institution_specific': 'D4D_Data_Governance',
        'no_commercial_use': 'D4D_Data_Governance',
        'no_methods_development': 'D4D_Data_Governance',
        'no_population_ancestry_research': 'D4D_Data_Governance',
        'no_restriction': 'D4D_Data_Governance',
        'non_profit_use_only': 'D4D_Data_Governance',
        'population_origins_ancestry_research': 'D4D_Data_Governance',
        'project_specific': 'D4D_Data_Governance',
        'publication_moratorium': 'D4D_Data_Governance',
        'publication_required': 'D4D_Data_Governance',
        'return_to_database': 'D4D_Data_Governance',
        'time_limit': 'D4D_Data_Governance',
        'user_specific': 'D4D_Data_Governance',

        # Preprocessing Module
        'tool_accuracy': 'D4D_Preprocessing',
        'tools': 'D4D_Preprocessing',
        'tool_descriptions': 'D4D_Preprocessing',
        'inter_annotator_agreement': 'D4D_Preprocessing',
        'agreement_metric': 'D4D_Preprocessing',
        'analysis_method': 'D4D_Preprocessing',
        'annotation_quality_details': 'D4D_Preprocessing',
        'labeling_details': 'D4D_Preprocessing',
        'disagreement_patterns': 'D4D_Preprocessing',
        'inter_annotator_agreement_score': 'D4D_Preprocessing',
        'annotations_per_item': 'D4D_Preprocessing',
        'annotator_demographics': 'D4D_Preprocessing',

        # Uses Module
        'repository_details': 'D4D_Uses',
        'use_category': 'D4D_Uses',
        'examples': 'D4D_Uses',
        'usage_notes': 'D4D_Uses',

        # Maintenance Module
        'versions_available': 'D4D_Maintenance',
        'version_details': 'D4D_Maintenance',
        'contribution_url': 'D4D_Maintenance',
        'latest_version_doi': 'D4D_Maintenance',

        # Variables Module (including enums)
        'categorical': 'D4D_Variables',
        'ordinal': 'D4D_Variables',
        'quality_notes': 'D4D_Variables',
        'missing_value_code': 'D4D_Variables',
        'precision': 'D4D_Variables',

        # Base import Module
        'used_software': 'D4D_Base_import',

        # Minimal Module
        'resources': 'D4D_Minimal',

        # Distribution Module

        # Relationships (in main schema)
        'has_part': 'data_sheets_schema',
        'is_part_of': 'data_sheets_schema',
        'is_version_of': 'data_sheets_schema',
        'is_new_version_of': 'data_sheets_schema',
        'replaces': 'data_sheets_schema',
        'is_replaced_by': 'data_sheets_schema',
        'references': 'data_sheets_schema',
        'is_referenced_by': 'data_sheets_schema',
        'requires': 'data_sheets_schema',
        'is_required_by': 'data_sheets_schema',
        'supplements': 'data_sheets_schema',
        'is_supplemented_by': 'data_sheets_schema',
        'is_identical_to': 'data_sheets_schema',

        # Variables enums and attributes (not in SLOT_TO_MODULE but in Variables)
        'integer': 'D4D_Variables',
        'float': 'D4D_Variables',
        'double': 'D4D_Variables',
        'string': 'D4D_Variables',
        'boolean': 'D4D_Variables',
        'date': 'D4D_Variables',
        'datetime': 'D4D_Variables',
        'identifier': 'D4D_Variables',
        'json': 'D4D_Variables',
        'array': 'D4D_Variables',
        'object': 'D4D_Variables',

        # Common attributes that might be in multiple modules
        'description': 'MULTIPLE',  # Will need manual check
        'name': 'MULTIPLE',
        'type': 'MULTIPLE',
        'url': 'MULTIPLE',
        'version': 'MULTIPLE',
        'method': 'MULTIPLE',
        'category': 'MULTIPLE',
        'usage_notes': 'MULTIPLE',
        'extension_details': 'MULTIPLE',
        'minimum_value': 'D4D_Variables',
        'measurement_technique': 'D4D_Variables',
        'derives_from': 'data_sheets_schema',  # Relationship in main schema
    }

    # Standard vocabulary mappings (high confidence)
    HIGH_CONFIDENCE_MAPPINGS = {
        'array': 'schema:ItemList',
        'boolean': 'schema:Boolean',
        'category': 'schema:category',
        'date': 'schema:Date',
        'datetime': 'schema:DateTime',
        'derivation': 'dcterms:provenance',
        'derives_from': 'prov:wasDerivedFrom',
        'description': 'schema:description',
        'double': 'schema:Number',
        'extension_details': 'dcterms:description',
        'float': 'schema:Float',
        'identifier': 'schema:identifier',
        'integer': 'schema:Integer',
        'json': 'schema:PropertyValue',
        'labeling_details': 'dcterms:description',
        'measurement_technique': 'qudt:measurementMethod',
        'method': 'schema:method',
        'minimum_value': 'schema:minValue',
        'name': 'schema:name',
        'object': 'schema:StructuredValue',
        'quality_notes': 'dcterms:description',
        'repository_url': 'dcat:accessURL',
        'source_description': 'dcterms:description',
        'source_type': 'dcterms:type',
        'string': 'schema:Text',
        'type': 'schema:type',
        'url': 'schema:url',
        'usage_notes': 'dcterms:description',
        'version': 'schema:version',
        'version_details': 'dcterms:description',

        # New standard vocabulary mappings (remaining slots - Phase 3)
        'role': 'schema:roleName',
        'label': 'schema:name',
        'examples': 'schema:example',
        'relationship_type': 'schema:additionalType',
        'archival': 'schema:archivedAt',
        'contribution_url': 'dcat:landingPage',
        'latest_version_doi': 'schema:identifier',
        'missing_value_code': 'schema:valueRequired',
        'precision': 'schema:valuePrecision',

        # Additional remaining core slots (Phase 4)
        'resources': 'schema:hasPart',
    }

    # DUO mappings
    DUO_MAPPINGS = {
        'collaboration_required': 'DUO:0000020',
        'disease_specific_research': 'DUO:0000007',
        'ethics_approval_required': 'DUO:0000021',
        'general_research_use': 'DUO:0000042',
        'genetic_studies_only': 'DUO:0000016',
        'geographic_restriction': 'DUO:0000022',
        'health_medical_biomedical_research': 'DUO:0000006',
        'institution_specific': 'DUO:0000028',
        'no_commercial_use': 'DUO:0000046',
        'no_methods_development': 'DUO:0000015',
        'no_population_ancestry_research': 'DUO:0000044',
        'no_restriction': 'DUO:0000004',
        'non_profit_use_only': 'DUO:0000045',
        'population_origins_ancestry_research': 'DUO:0000011',
        'project_specific': 'DUO:0000027',
        'publication_moratorium': 'DUO:0000024',
        'publication_required': 'DUO:0000019',
        'return_to_database': 'DUO:0000029',
        'time_limit': 'DUO:0000025',
        'user_specific': 'DUO:0000026',
    }

    # D4D-specific mappings
    D4D_MAPPINGS = {
        # Collection
        'was_validated_verified': 'd4d:wasValidated',
        'was_inferred_derived': 'd4d:wasInferred',
        'was_reported_by_subjects': 'd4d:wasReportedBySubjects',
        'was_directly_observed': 'd4d:wasDirectlyObserved',
        'acquisition_details': 'd4d:acquisitionDetails',
        'collection_details': 'd4d:collectionDetails',
        'collector_details': 'd4d:collectorDetails',
        'missing_data_causes': 'd4d:missingDataCauses',
        'access_details': 'd4d:accessDetails',
        'raw_data_format': 'd4d:rawDataFormat',

        # Composition
        'is_sample': 'd4d:isSample',
        'is_random': 'd4d:isRandom',
        'is_representative': 'd4d:isRepresentative',
        'representative_verification': 'd4d:representativeVerification',
        'label_description': 'd4d:labelDescription',
        'bias_description': 'd4d:biasDescription',
        'identifiers_removed': 'd4d:identifiersRemoved',
        'recommended_mitigation': 'd4d:recommendedMitigation',
        'strategies': 'd4d:strategies',
        'missing': 'd4d:missing',
        'restrictions': 'd4d:restrictions',
        'identification': 'd4d:identification',
        'source_data': 'd4d:sourceData',

        # Human
        'consent_obtained': 'd4d:consentObtained',
        'consent_type': 'd4d:consentType',
        'consent_documentation': 'd4d:consentDocumentation',
        'withdrawal_mechanism': 'd4d:withdrawalMechanism',
        'irb_approval': 'd4d:irbApproval',
        'ethics_review_board': 'd4d:ethicsReviewBoard',
        'guardian_consent': 'd4d:guardianConsent',
        'assent_procedures': 'd4d:assentProcedures',
        'reidentification_risk': 'd4d:reidentificationRisk',
        'privacy_techniques': 'd4d:privacyTechniques',
        'data_linkage': 'd4d:dataLinkage',
        'regulatory_compliance': 'd4d:regulatoryCompliance',
        'special_populations': 'd4d:specialPopulations',

        # Data Governance (non-DUO)
        'restricted': 'd4d:restricted',
        'unrestricted': 'd4d:unrestricted',
        'confidential': 'd4d:confidential',
        'clinical_care_use': 'd4d:clinicalCareUse',
        'compliant': 'd4d:compliant',
        'not_compliant': 'd4d:notCompliant',
        'partially_compliant': 'd4d:partiallyCompliant',
        'under_review': 'd4d:underReview',
        'not_applicable': 'd4d:notApplicable',
        'other_compliance': 'd4d:otherCompliance',

        # Preprocessing
        'tool_accuracy': 'd4d:toolAccuracy',
        'tools': 'd4d:tools',
        'tool_descriptions': 'd4d:toolDescriptions',
        'inter_annotator_agreement': 'd4d:interAnnotatorAgreement',
        'agreement_metric': 'd4d:agreementMetric',
        'analysis_method': 'd4d:analysisMethod',
        'annotation_quality_details': 'd4d:annotationQualityDetails',

        # Uses
        'repository_details': 'd4d:repositoryDetails',
        'use_category': 'd4d:useCategory',

        # Maintenance
        'versions_available': 'd4d:versionsAvailable',

        # Variables
        'categorical': 'd4d:categoricalVariable',
        'ordinal': 'd4d:ordinalVariable',

        # New D4D-specific mappings (remaining slots - Phase 3)
        # Collection
        'is_direct': 'd4d:isDirect',
        'missing_data_patterns': 'd4d:missingDataPatterns',

        # Composition
        'affected_subsets': 'd4d:affectedSubsets',
        'bias_type': 'd4d:biasType',
        'scope_impact': 'd4d:scopeImpact',
        'why_not_representative': 'd4d:whyNotRepresentative',
        'identifiable_elements_present': 'd4d:identifiableElementsPresent',
        'missing_information': 'd4d:missingInformation',
        'subpopulation_elements_present': 'd4d:subpopulationElementsPresent',

        # Data Governance
        'hipaa_compliant': 'd4d:hipaaCompliant',

        # Human
        'involves_human_subjects': 'd4d:involvesHumanSubjects',
        'anonymization_method': 'd4d:anonymizationMethod',

        # Preprocessing
        'disagreement_patterns': 'd4d:disagreementPatterns',
        'inter_annotator_agreement_score': 'd4d:interAnnotatorAgreementScore',
        'annotations_per_item': 'd4d:annotationsPerItem',
        'annotator_demographics': 'd4d:annotatorDemographics',

        # Base import
        'used_software': 'd4d:usedSoftware',
    }

    # RO-Crate relationship mappings
    ROCRATE_MAPPINGS = {
        'has_part': 'schema:hasPart',
        'is_part_of': 'schema:isPartOf',
        'is_version_of': 'schema:isVersionOf',
        'is_new_version_of': 'schema:isNewVersionOf',
        'replaces': 'schema:replacesAction',
        'is_replaced_by': 'schema:replacesAction',
        'references': 'schema:citation',
        'is_referenced_by': 'schema:citation',
        'requires': 'schema:requirements',
        'is_required_by': 'schema:requirements',
        'supplements': 'schema:supplementTo',
        'is_supplemented_by': 'schema:supplementTo',
        'is_identical_to': 'schema:sameAs',
    }

    def __init__(self, schema_dir: Path, dry_run: bool = False):
        self.schema_dir = schema_dir
        self.dry_run = dry_run
        self.stats = {
            'files_modified': 0,
            'slots_added': 0,
            'skipped': 0,
            'errors': 0,
        }

    def get_all_mappings(self, priority: str = 'all') -> Dict[str, str]:
        """Get mappings based on priority."""
        if priority == 'high':
            return self.HIGH_CONFIDENCE_MAPPINGS
        elif priority == 'duo':
            return self.DUO_MAPPINGS
        elif priority == 'd4d':
            return self.D4D_MAPPINGS
        elif priority == 'rocrate':
            return self.ROCRATE_MAPPINGS
        else:  # all
            all_mappings = {}
            all_mappings.update(self.HIGH_CONFIDENCE_MAPPINGS)
            all_mappings.update(self.DUO_MAPPINGS)
            all_mappings.update(self.D4D_MAPPINGS)
            all_mappings.update(self.ROCRATE_MAPPINGS)
            return all_mappings

    def find_slot_in_file(self, file_path: Path, slot_name: str) -> Tuple[bool, List[str], int]:
        """
        Find a slot in a YAML file and return whether it exists,
        the file lines, and the line number where the slot is defined.

        Returns:
            (found, lines, line_number)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Look for slot definition pattern
        attr_pattern = rf'^(\s+){re.escape(slot_name)}:\s*$'

        for i, line in enumerate(lines):
            if re.match(attr_pattern, line):
                return True, lines, i

        return False, lines, -1

    def has_slot_uri(self, lines: List[str], slot_line: int) -> bool:
        """Check if a slot already has a slot_uri defined."""
        # Check the lines following the slot definition
        indent = len(lines[slot_line]) - len(lines[slot_line].lstrip())

        for i in range(slot_line + 1, min(slot_line + 20, len(lines))):
            line = lines[i]
            # Stop if we hit another attribute at the same or lower indent level
            if line.strip() and not line.strip().startswith('#'):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent:
                    break
                if 'slot_uri:' in line:
                    return True

        return False

    def add_slot_uri(self, file_path: Path, slot_name: str, slot_uri: str) -> bool:
        """Add slot_uri to a specific slot in a YAML file."""
        # Skip enum permissible_values
        if slot_name in self.ENUM_VALUES:
            print(f"  ⏭️  Skipping enum value '{slot_name}' in {file_path.name}")
            self.stats['skipped'] += 1
            return False

        found, lines, slot_line = self.find_slot_in_file(file_path, slot_name)

        if not found:
            print(f"  ⚠️  Slot '{slot_name}' not found in {file_path.name}")
            self.stats['skipped'] += 1
            return False

        if self.has_slot_uri(lines, slot_line):
            print(f"  ℹ️  Slot '{slot_name}' already has slot_uri in {file_path.name}")
            self.stats['skipped'] += 1
            return False

        # Find the right place to insert slot_uri
        # It should go after description if present, or right after the slot name
        indent = len(lines[slot_line]) - len(lines[slot_line].lstrip())
        insert_line = slot_line + 1

        # Look for description field
        for i in range(slot_line + 1, min(slot_line + 10, len(lines))):
            line = lines[i]
            if line.strip() and not line.strip().startswith('#'):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent:
                    insert_line = i
                    break
                if 'description:' in line:
                    # Find the end of description (could be multi-line)
                    if '>' in line or '|' in line:
                        # Multi-line description, find where it ends
                        for j in range(i + 1, min(i + 30, len(lines))):
                            next_line = lines[j]
                            next_indent = len(next_line) - len(next_line.lstrip())
                            if next_line.strip() and next_indent <= indent + 2:
                                insert_line = j
                                break
                    else:
                        # Single-line description
                        insert_line = i + 1
                    break
                if 'range:' in line:
                    insert_line = i
                    break

        # Create the slot_uri line with proper indentation
        slot_uri_line = ' ' * (indent + 2) + f'slot_uri: {slot_uri}\n'

        if self.dry_run:
            print(f"  [DRY RUN] Would add slot_uri to '{slot_name}' in {file_path.name}: {slot_uri}")
            return True

        # Insert the slot_uri line
        lines.insert(insert_line, slot_uri_line)

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"  ✅ Added slot_uri to '{slot_name}' in {file_path.name}: {slot_uri}")
        self.stats['slots_added'] += 1
        return True

    def process_module(self, module_name: str, mappings: Dict[str, str]) -> int:
        """Process a single module file and add slot_uri definitions."""
        file_path = self.schema_dir / f"{module_name}.yaml"

        if not file_path.exists():
            print(f"⚠️  Module file not found: {file_path}")
            return 0

        print(f"\n📝 Processing {module_name}.yaml")

        slots_added = 0
        module_slots = {
            slot: uri for slot, uri in mappings.items()
            if self.SLOT_TO_MODULE.get(slot) == module_name
        }

        for slot_name, slot_uri in module_slots.items():
            if self.add_slot_uri(file_path, slot_name, slot_uri):
                slots_added += 1

        if slots_added > 0:
            self.stats['files_modified'] += 1

        return slots_added

    def implement_mappings(self, priority: str = 'all'):
        """Implement URI mappings for all modules based on priority."""
        mappings = self.get_all_mappings(priority)

        print(f"\n{'='*60}")
        print(f"Phase 2: URI Mapping Implementation")
        print(f"Priority: {priority}")
        print(f"Total mappings to process: {len(mappings)}")
        if self.dry_run:
            print("MODE: DRY RUN (no files will be modified)")
        print(f"{'='*60}")

        # Get unique modules from mappings
        modules = set()
        for slot in mappings.keys():
            module = self.SLOT_TO_MODULE.get(slot, 'UNKNOWN')
            if module not in ['UNKNOWN', 'MULTIPLE']:
                modules.add(module)

        # Process each module
        for module in sorted(modules):
            self.process_module(module, mappings)

        # Print summary
        print(f"\n{'='*60}")
        print("Summary:")
        print(f"  Files modified: {self.stats['files_modified']}")
        print(f"  Slot URIs added: {self.stats['slots_added']}")
        print(f"  Skipped (already exists or not found): {self.stats['skipped']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Implement URI mappings by adding slot_uri definitions to schema files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--priority',
        choices=['high', 'duo', 'd4d', 'rocrate', 'all'],
        default='high',
        help='Priority level of mappings to implement (default: high)'
    )
    parser.add_argument(
        '--schema-dir',
        type=Path,
        default=Path('src/data_sheets_schema/schema'),
        help='Directory containing schema files'
    )

    args = parser.parse_args()

    implementer = URIMappingImplementer(args.schema_dir, args.dry_run)
    implementer.implement_mappings(args.priority)


if __name__ == '__main__':
    main()
