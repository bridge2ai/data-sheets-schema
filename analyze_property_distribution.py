#!/usr/bin/env python3
"""
Property Distribution Analysis for FileCollection Implementation

Analyzes existing D4D YAML files to determine which properties should be
at Dataset level vs FileCollection level based on actual data patterns.
"""

import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Set
import json


class PropertyAnalyzer:
    def __init__(self):
        self.projects = ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']
        self.methods = ['curated', 'claudecode', 'claudecode_agent']
        self.property_stats = defaultdict(lambda: {
            'count': 0,
            'files': [],
            'example_values': [],
            'is_uniform': None,
            'is_list': False,
            'is_complex': False
        })

    def analyze_all_files(self):
        """Analyze all D4D YAML files."""
        print("🔍 Analyzing existing D4D YAML files...\n")

        for project in self.projects:
            for method in self.methods:
                file_path = Path(f'data/d4d_concatenated/{method}/{project}_d4d.yaml')
                if file_path.exists():
                    self.analyze_file(file_path, project, method)
                else:
                    print(f"⚠️  File not found: {file_path}")

        print(f"\n✅ Analyzed {len([f for stats in self.property_stats.values() for f in stats['files']])} files")
        print(f"✅ Found {len(self.property_stats)} unique properties\n")

    def analyze_file(self, file_path: Path, project: str, method: str):
        """Analyze a single D4D YAML file."""
        print(f"📄 Analyzing: {project} ({method})")

        with open(file_path) as f:
            data = yaml.safe_load(f)

        # Flatten and analyze all properties
        self._analyze_dict(data, '', f"{project}_{method}")

    def _analyze_dict(self, data: Any, prefix: str, file_id: str):
        """Recursively analyze dictionary structure."""
        if not isinstance(data, dict):
            return

        for key, value in data.items():
            prop_path = f"{prefix}.{key}" if prefix else key

            # Skip metadata properties
            if key in ['@context', '@type', '@id']:
                continue

            # Record property stats
            stats = self.property_stats[prop_path]
            stats['count'] += 1
            stats['files'].append(file_id)

            # Analyze value type
            if value is not None:
                if isinstance(value, list):
                    stats['is_list'] = True
                    if len(value) > 0:
                        stats['example_values'].append(f"List[{len(value)} items]")
                        if isinstance(value[0], dict):
                            stats['is_complex'] = True
                elif isinstance(value, dict):
                    stats['is_complex'] = True
                    stats['example_values'].append("Complex object")
                    # Recurse into nested objects
                    self._analyze_dict(value, prop_path, file_id)
                else:
                    # Store first 3 example values
                    if len(stats['example_values']) < 3:
                        stats['example_values'].append(str(value)[:100])

    def categorize_properties(self) -> Dict[str, List[str]]:
        """Categorize properties into Dataset vs FileCollection based on patterns."""
        categories = {
            'file_technical': [],      # bytes, format, encoding, etc.
            'file_distribution': [],   # distribution_formats, distribution_dates
            'file_collection': [],     # instances, data_collectors, collection_timeframes
            'file_preprocessing': [],  # preprocessing_strategies, cleaning_strategies
            'file_variables': [],      # variables (field-level metadata)
            'file_content': [],        # confidential_elements, content_warnings
            'dataset_motivation': [],  # purposes, tasks, creators, funders
            'dataset_ethics': [],      # ethical_reviews, license_and_use_terms
            'dataset_uses': [],        # intended_uses, prohibited_uses
            'dataset_maintenance': [], # maintainers, updates, retention_limit
            'dataset_identity': [],    # id, name, title, description, doi
            'dataset_relationships': [], # parent_datasets, related_datasets
            'uncertain': []            # Needs review
        }

        # Technical metadata patterns
        tech_keywords = ['bytes', 'format', 'encoding', 'hash', 'md5', 'sha256',
                        'media_type', 'path', 'download', 'content', 'compression', 'dialect']

        # Distribution patterns
        dist_keywords = ['distribution_format', 'distribution_date']

        # Collection patterns
        collection_keywords = ['instance', 'data_collector', 'collection_timeframe',
                              'raw_data_source', 'acquisition_method', 'collection_mechanism',
                              'sampling_strategy', 'missing_data', 'direct_collection']

        # Preprocessing patterns
        preproc_keywords = ['preprocessing', 'cleaning', 'labeling', 'raw_source',
                           'imputation', 'annotation', 'machine_annotation']

        # Variable patterns
        var_keywords = ['variable']

        # Content/sensitivity patterns
        content_keywords = ['confidential', 'content_warning', 'subpopulation',
                           'sensitive_element', 'is_deidentified', 'anomal', 'bias', 'limitation']

        # Dataset-level patterns
        motivation_keywords = ['purpose', 'task', 'addressing_gap', 'creator', 'funder', 'grant']
        ethics_keywords = ['ethical_review', 'data_protection', 'human_subject',
                          'informed_consent', 'at_risk', 'participant', 'license',
                          'regulatory', 'ip_restriction']
        uses_keywords = ['existing_use', 'use_repository', 'other_task', 'future_use',
                        'discouraged_use', 'intended_use', 'prohibited_use']
        maint_keywords = ['maintainer', 'erratum', 'update', 'retention_limit',
                         'version_access', 'extension_mechanism']
        identity_keywords = ['id', 'name', 'title', 'description', 'keyword',
                            'doi', 'citation', 'issued', 'publisher', 'version',
                            'created_on', 'last_updated', 'language', 'status']
        rel_keywords = ['parent_dataset', 'related_dataset', 'external_resource',
                       'was_derived_from', 'same_as']

        for prop, stats in self.property_stats.items():
            prop_lower = prop.lower()

            # Categorize based on keywords
            if any(kw in prop_lower for kw in tech_keywords):
                categories['file_technical'].append(prop)
            elif any(kw in prop_lower for kw in dist_keywords):
                categories['file_distribution'].append(prop)
            elif any(kw in prop_lower for kw in collection_keywords):
                categories['file_collection'].append(prop)
            elif any(kw in prop_lower for kw in preproc_keywords):
                categories['file_preprocessing'].append(prop)
            elif any(kw in prop_lower for kw in var_keywords):
                categories['file_variables'].append(prop)
            elif any(kw in prop_lower for kw in content_keywords):
                categories['file_content'].append(prop)
            elif any(kw in prop_lower for kw in motivation_keywords):
                categories['dataset_motivation'].append(prop)
            elif any(kw in prop_lower for kw in ethics_keywords):
                categories['dataset_ethics'].append(prop)
            elif any(kw in prop_lower for kw in uses_keywords):
                categories['dataset_uses'].append(prop)
            elif any(kw in prop_lower for kw in maint_keywords):
                categories['dataset_maintenance'].append(prop)
            elif any(kw in prop_lower for kw in identity_keywords):
                categories['dataset_identity'].append(prop)
            elif any(kw in prop_lower for kw in rel_keywords):
                categories['dataset_relationships'].append(prop)
            else:
                categories['uncertain'].append(prop)

        return categories

    def generate_report(self, output_path: str = '/tmp/property_distribution_analysis.md'):
        """Generate comprehensive analysis report."""
        categories = self.categorize_properties()

        # Calculate totals
        file_level_count = sum(len(props) for cat, props in categories.items()
                              if cat.startswith('file_'))
        dataset_level_count = sum(len(props) for cat, props in categories.items()
                                 if cat.startswith('dataset_'))
        uncertain_count = len(categories['uncertain'])

        report = []
        report.append("# Property Distribution Analysis for FileCollection\n")
        report.append("## Executive Summary\n")
        report.append(f"- **Total Properties Analyzed**: {len(self.property_stats)}")
        report.append(f"- **Recommended for FileCollection**: {file_level_count} properties")
        report.append(f"- **Recommended for Dataset**: {dataset_level_count} properties")
        report.append(f"- **Needs Review**: {uncertain_count} properties\n")

        report.append("## Analysis Methodology\n")
        report.append("Analyzed existing D4D YAML files across:")
        report.append(f"- Projects: {', '.join(self.projects)}")
        report.append(f"- Methods: {', '.join(self.methods)}")
        report.append("- Total files analyzed: " + str(len(set(f for stats in self.property_stats.values() for f in stats['files']))))
        report.append("")

        report.append("## Recommended Property Distribution\n")

        # FileCollection properties
        report.append("### Properties for FileCollection\n")
        report.append("These properties describe file-level characteristics and should move to FileCollection:\n")

        file_categories = {
            'file_technical': 'File Technical Metadata',
            'file_distribution': 'Distribution Properties',
            'file_collection': 'Collection-Specific Metadata',
            'file_preprocessing': 'Preprocessing Properties',
            'file_variables': 'Variable/Field Metadata',
            'file_content': 'Content Characteristics'
        }

        for cat_key, cat_name in file_categories.items():
            if categories[cat_key]:
                report.append(f"\n#### {cat_name} ({len(categories[cat_key])} properties)")
                for prop in sorted(categories[cat_key]):
                    stats = self.property_stats[prop]
                    report.append(f"- `{prop}` (in {stats['count']} files)")
                    if stats['example_values']:
                        report.append(f"  - Examples: {', '.join(stats['example_values'][:2])}")

        # Dataset properties
        report.append("\n### Properties for Dataset\n")
        report.append("These properties describe dataset-level characteristics and should remain at Dataset:\n")

        dataset_categories = {
            'dataset_motivation': 'Motivation & Purpose',
            'dataset_ethics': 'Ethics & Governance',
            'dataset_uses': 'Uses & Impact',
            'dataset_maintenance': 'Maintenance & Versioning',
            'dataset_identity': 'Identity & Metadata',
            'dataset_relationships': 'Relationships'
        }

        for cat_key, cat_name in dataset_categories.items():
            if categories[cat_key]:
                report.append(f"\n#### {cat_name} ({len(categories[cat_key])} properties)")
                for prop in sorted(categories[cat_key]):
                    stats = self.property_stats[prop]
                    report.append(f"- `{prop}` (in {stats['count']} files)")

        # Uncertain properties
        if categories['uncertain']:
            report.append("\n### Properties Needing Review\n")
            report.append("These properties don't clearly fit existing patterns:\n")
            for prop in sorted(categories['uncertain']):
                stats = self.property_stats[prop]
                report.append(f"- `{prop}` (in {stats['count']} files)")
                if stats['example_values']:
                    report.append(f"  - Examples: {', '.join(stats['example_values'][:2])}")

        # Property details table
        report.append("\n## Detailed Property Statistics\n")
        report.append("| Property | Files | Type | Examples |")
        report.append("|----------|-------|------|----------|")

        for prop in sorted(self.property_stats.keys()):
            stats = self.property_stats[prop]
            prop_type = "List" if stats['is_list'] else "Complex" if stats['is_complex'] else "Simple"
            examples = ', '.join(stats['example_values'][:2]) if stats['example_values'] else 'N/A'
            report.append(f"| `{prop}` | {stats['count']} | {prop_type} | {examples[:50]} |")

        # Write report
        report_text = '\n'.join(report)
        with open(output_path, 'w') as f:
            f.write(report_text)

        print(f"\n✅ Report generated: {output_path}")
        return report_text


def main():
    analyzer = PropertyAnalyzer()
    analyzer.analyze_all_files()
    report = analyzer.generate_report()

    # Print summary
    print("\n" + "="*80)
    print("PROPERTY DISTRIBUTION SUMMARY")
    print("="*80)
    lines = report.split('\n')
    for line in lines[:20]:  # Print first 20 lines
        print(line)
    print("\n... (see full report at /tmp/property_distribution_analysis.md)")


if __name__ == '__main__':
    main()
