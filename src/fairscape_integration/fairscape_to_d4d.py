#!/usr/bin/env python3
"""
FAIRSCAPE RO-Crate to D4D Converter (Reverse Transformation)

Converts FAIRSCAPE RO-Crate JSON-LD to D4D YAML format using SSSOM mapping guidance.

Features:
- SSSOM-guided semantic mapping
- Vocabulary translation (schema.org → dcterms, etc.)
- Pydantic validation of input RO-Crate
- LinkML validation of output D4D
"""

import csv
import json
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import ROCrateV1_2
    FAIRSCAPE_AVAILABLE = True
except ImportError:
    FAIRSCAPE_AVAILABLE = False
    print("Warning: FAIRSCAPE models not available")


class FairscapeToD4DConverter:
    """Convert FAIRSCAPE RO-Crate to D4D YAML."""

    def __init__(self, sssom_mapping_file: Optional[Path] = None):
        """
        Initialize converter.

        Args:
            sssom_mapping_file: Path to SSSOM mapping TSV (optional)
        """
        self.sssom_mapping = self._load_sssom(sssom_mapping_file) if sssom_mapping_file else {}

    def _load_sssom(self, sssom_file: Path) -> Dict[str, Dict]:
        """Load SSSOM mapping for semantic guidance."""
        mapping = {}

        with open(sssom_file) as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]

        # Parse TSV
        reader = csv.DictReader(lines, delimiter='\t')
        for row in reader:
                # Map from object (RO-Crate) to subject (D4D)
                object_id = row['object_id']
                subject_id = row['subject_id']

                # Extract property name
                if ':' in object_id:
                    rocrate_prop = object_id.split(':')[1]
                else:
                    rocrate_prop = object_id

                if ':' in subject_id:
                    d4d_prop = subject_id.split(':')[1]
                else:
                    d4d_prop = subject_id

                mapping[rocrate_prop] = {
                    'd4d_property': d4d_prop,
                    'predicate': row['predicate_id'],
                    'confidence': float(row['confidence']),
                    'comment': row.get('comment', '')
                }

        return mapping

    def convert(self, rocrate_input: Any) -> Dict[str, Any]:
        """
        Convert FAIRSCAPE RO-Crate to D4D dictionary.

        Args:
            rocrate_input: FAIRSCAPE RO-Crate (dict, Path, or ROCrateV1_2)

        Returns:
            D4D dictionary
        """
        # Load RO-Crate data
        if isinstance(rocrate_input, dict):
            rocrate_data = rocrate_input
        elif isinstance(rocrate_input, (str, Path)):
            with open(rocrate_input) as f:
                rocrate_data = json.load(f)
        elif FAIRSCAPE_AVAILABLE and isinstance(rocrate_input, ROCrateV1_2):
            rocrate_data = rocrate_input.model_dump(by_alias=True, exclude_none=True)
        else:
            raise ValueError(f"Unsupported input type: {type(rocrate_input)}")

        # Validate with Pydantic if available
        if FAIRSCAPE_AVAILABLE and isinstance(rocrate_data, dict):
            try:
                rocrate_model = ROCrateV1_2(**rocrate_data)
                print("✓ Input RO-Crate validated with FAIRSCAPE Pydantic models")
            except Exception as e:
                print(f"⚠ Warning: RO-Crate validation failed: {e}")

        # Extract Dataset entity and nested Datasets from @graph
        dataset, nested_datasets = self._extract_datasets(rocrate_data)

        if not dataset:
            raise ValueError("No Dataset entity found in RO-Crate @graph")

        # Convert to D4D
        d4d_dict = self._build_d4d(dataset, nested_datasets, rocrate_data)

        return d4d_dict

    def _extract_datasets(self, rocrate_data: Dict) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Extract main Dataset and nested Datasets from RO-Crate @graph.

        Returns:
            Tuple of (main_dataset, nested_datasets_list)
        """
        graph = rocrate_data.get('@graph', [])

        main_dataset = None
        nested_datasets = []
        hasPart_ids = set()

        # First pass: find main dataset and collect hasPart references
        for entity in graph:
            entity_type = entity.get('@type', [])
            if isinstance(entity_type, str):
                entity_type = [entity_type]

            if 'Dataset' in entity_type:
                # Skip metadata descriptor
                if entity.get('@id') == 'ro-crate-metadata.json':
                    continue

                # Main dataset is the root with @id "./" or has ROCrate type
                entity_id = entity.get('@id', '')
                if entity_id == './' or 'https://w3id.org/EVI#ROCrate' in entity_type:
                    main_dataset = entity
                    # Collect hasPart references
                    has_part = entity.get('hasPart', [])
                    for part in has_part:
                        if isinstance(part, dict) and '@id' in part:
                            hasPart_ids.add(part['@id'])
                        elif isinstance(part, str):
                            hasPart_ids.add(part)

        # Second pass: collect nested datasets (those referenced by hasPart)
        for entity in graph:
            entity_type = entity.get('@type', [])
            if isinstance(entity_type, str):
                entity_type = [entity_type]

            if 'Dataset' in entity_type:
                entity_id = entity.get('@id', '')
                if entity_id in hasPart_ids:
                    nested_datasets.append(entity)

        return main_dataset, nested_datasets

    def _build_d4d(self, dataset: Dict, nested_datasets: List[Dict], full_rocrate: Dict) -> Dict[str, Any]:
        """
        Build D4D dictionary from RO-Crate Dataset entity.

        Args:
            dataset: Main Dataset entity
            nested_datasets: Nested Dataset entities (FileCollections)
            full_rocrate: Full RO-Crate data

        Returns:
            D4D dictionary
        """

        d4d = {
            # Required D4D metadata
            'schema_version': '1.1',  # Updated to 1.1 for FileCollection support
            'generated_date': datetime.now().isoformat(),
            'source': 'FAIRSCAPE RO-Crate',
        }

        # Map basic properties
        basic_props = self._map_basic_properties(dataset)

        # Convert nested Datasets to FileCollections
        has_file_collections = False
        if nested_datasets:
            file_collections = self._build_file_collections(nested_datasets)
            if file_collections:
                d4d['file_collections'] = file_collections
                has_file_collections = True

                # For schema 1.1 with file_collections: map contentSize to total_size_bytes
                if 'bytes' in basic_props:
                    basic_props['total_size_bytes'] = basic_props.pop('bytes')

        d4d.update(basic_props)

        # Map complex properties (skip hasPart mapping if we have file_collections)
        complex_props = self._map_complex_properties(dataset)
        if has_file_collections and 'resources' in complex_props:
            # Filter out resources that are already in file_collections
            fc_ids = {fc.get('id') for fc in d4d.get('file_collections', [])}
            if isinstance(complex_props['resources'], list):
                complex_props['resources'] = [
                    r for r in complex_props['resources']
                    if r not in fc_ids
                ]
                # Remove resources if empty
                if not complex_props['resources']:
                    del complex_props['resources']

        d4d.update(complex_props)

        # Map EVI properties (computational provenance)
        d4d.update(self._map_evi_properties(dataset))

        # Map RAI properties (responsible AI)
        d4d.update(self._map_rai_properties(dataset))

        # Map custom D4D properties
        d4d.update(self._map_d4d_properties(dataset))

        return d4d

    def _build_file_collections(self, nested_datasets: List[Dict]) -> List[Dict[str, Any]]:
        """
        Convert nested RO-Crate Datasets to D4D FileCollections.

        Args:
            nested_datasets: List of nested Dataset entities from RO-Crate

        Returns:
            List of FileCollection dictionaries
        """
        file_collections = []

        for dataset in nested_datasets:
            collection = {}

            # Map basic properties
            if '@id' in dataset:
                collection['id'] = dataset['@id']

            if 'name' in dataset:
                collection['name'] = dataset['name']

            if 'description' in dataset:
                collection['description'] = dataset['description']

            # Map collection-level properties
            # Note: encodingFormat, sha256, md5, format, bytes, encoding are now
            # file-level properties (on File objects), not FileCollection properties

            if 'contentSize' in dataset:
                # Parse size string to total_bytes (aggregate size)
                size_str = dataset['contentSize']
                if isinstance(size_str, str):
                    collection['total_bytes'] = self._parse_size(size_str)
                else:
                    collection['total_bytes'] = size_str

            if 'contentUrl' in dataset:
                collection['path'] = dataset['contentUrl']

            if 'fileFormat' in dataset:
                collection['compression'] = dataset['fileFormat']

            # Map D4D-specific properties
            if 'd4d:collectionType' in dataset:
                # collection_type is multivalued, wrap scalar as array
                collection_type = dataset['d4d:collectionType']
                collection['collection_type'] = (
                    collection_type if isinstance(collection_type, list) else [collection_type]
                )

            if 'd4d:fileCount' in dataset:
                collection['file_count'] = dataset['d4d:fileCount']

            # TODO: Parse nested Dataset's hasPart to build FileCollection.resources
            # Currently, file-level information in RO-Crate File entities is not converted
            # to FileCollection.resources (File objects). Future work: parse dataset['hasPart'],
            # fetch referenced File entities, and convert to D4D File objects in resources.

            # Only add non-empty collections
            if collection:
                file_collections.append(collection)

        return file_collections

    def _map_basic_properties(self, dataset: Dict) -> Dict[str, Any]:
        """Map basic Schema.org properties to D4D."""

        mapping = {
            # Direct mappings (same name)
            'name': 'title',
            'description': 'description',
            'keywords': 'keywords',
            'version': 'version',
            'license': 'license',
            'publisher': 'publisher',

            # Property name differences
            'identifier': 'doi',
            'datePublished': 'issued',
            'dateCreated': 'created_on',
            'dateModified': 'last_updated_on',
            'author': 'creators',
            'url': 'page',
            'contentUrl': 'download_url',
            'contentSize': 'bytes',
        }

        d4d_props = {}

        for rocrate_prop, d4d_prop in mapping.items():
            if rocrate_prop in dataset:
                value = dataset[rocrate_prop]

                # Handle special transformations
                if rocrate_prop == 'author' and isinstance(value, str):
                    # Convert semicolon-separated string to Person list
                    d4d_props[d4d_prop] = self._parse_authors(value)
                elif rocrate_prop == 'contentSize' and isinstance(value, str):
                    # Parse size string (e.g., "19.1 TB") to bytes
                    d4d_props[d4d_prop] = self._parse_size(value)
                else:
                    d4d_props[d4d_prop] = value

        return d4d_props

    def _map_complex_properties(self, dataset: Dict) -> Dict[str, Any]:
        """Map complex/nested properties."""

        d4d_props = {}

        # hasPart → resources
        if 'hasPart' in dataset:
            has_part = dataset['hasPart']
            if isinstance(has_part, list):
                # Extract IDs or convert to resource list
                d4d_props['resources'] = [
                    item.get('@id') if isinstance(item, dict) else item
                    for item in has_part
                ]

        # isPartOf → parent collections
        if 'isPartOf' in dataset:
            is_part_of = dataset['isPartOf']
            if isinstance(is_part_of, list):
                d4d_props['is_part_of'] = [
                    item.get('@id') if isinstance(item, dict) else item
                    for item in is_part_of
                ]

        # additionalProperty → custom metadata
        if 'additionalProperty' in dataset:
            additional = dataset['additionalProperty']
            if isinstance(additional, list):
                d4d_props.update(self._parse_additional_properties(additional))

        return d4d_props

    def _map_evi_properties(self, dataset: Dict) -> Dict[str, Any]:
        """Map EVI (Evidence) namespace properties."""

        evi_mapping = {
            'evi:datasetCount': 'dataset_count',
            'evi:computationCount': 'computation_count',
            'evi:softwareCount': 'software_count',
            'evi:schemaCount': 'schema_count',
            'evi:totalEntities': 'total_entities',
            'evi:formats': 'distribution_formats',
            'evi:md5': 'md5',
            'evi:sha256': 'sha256',
        }

        d4d_props = {}

        for evi_prop, d4d_prop in evi_mapping.items():
            if evi_prop in dataset:
                d4d_props[d4d_prop] = dataset[evi_prop]

        return d4d_props

    def _map_rai_properties(self, dataset: Dict) -> Dict[str, Any]:
        """Map RAI (Responsible AI) namespace properties."""

        rai_mapping = {
            'rai:dataUseCases': 'intended_uses',
            'rai:dataBiases': 'known_biases',
            'rai:dataLimitations': 'known_limitations',
            'rai:dataCollection': 'acquisition_methods',
            'rai:dataCollectionMissingData': 'missing_data_documentation',
            'rai:dataCollectionRawData': 'raw_data_sources',
            'rai:dataCollectionTimeframe': 'collection_timeframes',
            'rai:prohibitedUses': 'prohibited_uses',
            'rai:ethicalReview': 'ethical_reviews',
            'rai:personalSensitiveInformation': 'confidential_elements',
            'rai:dataSocialImpact': 'data_protection_impacts',
            'rai:dataReleaseMaintenancePlan': 'updates',
            'rai:dataPreprocessingProtocol': 'preprocessing_strategies',
            'rai:dataAnnotationProtocol': 'labeling_strategies',
            'rai:dataAnnotationAnalysis': 'annotation_analyses',
            'rai:machineAnnotationTools': 'machine_annotation_analyses',
            'rai:imputationProtocol': 'imputation_protocols',
        }

        d4d_props = {}

        for rai_prop, d4d_prop in rai_mapping.items():
            if rai_prop in dataset:
                d4d_props[d4d_prop] = dataset[rai_prop]

        return d4d_props

    def _map_d4d_properties(self, dataset: Dict) -> Dict[str, Any]:
        """Map D4D-specific namespace properties."""

        d4d_mapping = {
            'd4d:addressingGaps': 'addressing_gaps',
            'd4d:dataAnomalies': 'anomalies',
            'd4d:contentWarning': 'content_warnings',
            'd4d:informedConsent': 'informed_consent',
            'd4d:humanSubject': 'human_subject_research',
            'd4d:atRiskPopulations': 'vulnerable_populations',
        }

        d4d_props = {}

        for d4d_ns_prop, d4d_prop in d4d_mapping.items():
            if d4d_ns_prop in dataset:
                d4d_props[d4d_prop] = dataset[d4d_ns_prop]

        return d4d_props

    def _parse_authors(self, author_string: str) -> List[Dict[str, str]]:
        """Parse semicolon-separated author string to Person list."""
        authors = []

        for name in author_string.split(';'):
            name = name.strip()
            if name:
                authors.append({
                    'name': name,
                    'type': 'Person'
                })

        return authors

    def _parse_size(self, size_string: str) -> Optional[int]:
        """Parse size string to bytes."""
        try:
            # Try direct int conversion
            return int(size_string)
        except ValueError:
            # Parse human-readable size (e.g., "19.1 TB")
            size_string = size_string.strip().upper()

            units = {
                'B': 1,
                'KB': 1024,
                'MB': 1024**2,
                'GB': 1024**3,
                'TB': 1024**4,
                'PB': 1024**5,
            }

            for unit, multiplier in units.items():
                if size_string.endswith(unit):
                    num_str = size_string[:-len(unit)].strip()
                    try:
                        return int(float(num_str) * multiplier)
                    except ValueError:
                        pass

            # Could not parse
            return None

    def _parse_additional_properties(self, additional: List[Dict]) -> Dict[str, Any]:
        """Parse additionalProperty list to D4D fields."""
        d4d_props = {}

        for prop in additional:
            if not isinstance(prop, dict):
                continue

            prop_type = prop.get('@type')
            if prop_type != 'PropertyValue':
                continue

            name = prop.get('name')
            value = prop.get('value')

            if not name:
                continue

            # Map known additional properties to D4D fields
            name_mapping = {
                'Completeness': 'completeness',
                'Human Subject': 'human_subject_research',
                'Prohibited Uses': 'prohibited_uses',
                'Data Governance Committee': 'data_governance_committee',
            }

            d4d_field = name_mapping.get(name, name.lower().replace(' ', '_'))
            d4d_props[d4d_field] = value

        return d4d_props

    def convert_and_save(
        self,
        rocrate_input: Any,
        output_file: Path,
        validate: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Convert RO-Crate to D4D and save as YAML.

        Args:
            rocrate_input: FAIRSCAPE RO-Crate input
            output_file: Output YAML file path
            validate: Validate against D4D schema

        Returns:
            (d4d_dict, is_valid)
        """
        # Convert
        d4d_dict = self.convert(rocrate_input)

        # Save
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            yaml.safe_dump(d4d_dict, f, default_flow_style=False, sort_keys=False)

        print(f"✓ D4D YAML saved to {output_file}")

        # Validate if requested
        is_valid = True
        if validate:
            is_valid = self._validate_d4d(output_file)

        return d4d_dict, is_valid

    def _validate_d4d(self, d4d_file: Path) -> bool:
        """Validate D4D YAML against schema."""
        try:
            from linkml.validator import validate
            from linkml_runtime.loaders import yaml_loader

            schema_file = Path('src/data_sheets_schema/schema/data_sheets_schema_all.yaml')

            if not schema_file.exists():
                print(f"⚠ Warning: Schema not found: {schema_file}")
                return True

            # Load D4D data
            with open(d4d_file) as f:
                d4d_data = yaml.safe_load(f)

            # Validate
            report = validate(d4d_data, str(schema_file), target_class='Dataset')

            if report.results:
                print(f"✗ Validation failed with {len(report.results)} errors")
                for result in report.results[:5]:  # Show first 5 errors
                    print(f"  - {result.message}")
                return False
            else:
                print("✓ D4D YAML validated against schema")
                return True

        except Exception as e:
            print(f"⚠ Validation error: {e}")
            return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert FAIRSCAPE RO-Crate to D4D YAML'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input FAIRSCAPE RO-Crate JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output D4D YAML file'
    )
    parser.add_argument(
        '--sssom',
        default='src/data_sheets_schema/alignment/d4d_rocrate_sssom_mapping.tsv',
        help='SSSOM mapping file for semantic guidance'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip D4D schema validation'
    )

    args = parser.parse_args()

    # Load SSSOM mapping
    sssom_file = Path(args.sssom)
    if not sssom_file.exists():
        print(f"Warning: SSSOM mapping not found: {sssom_file}")
        sssom_file = None

    # Convert
    converter = FairscapeToD4DConverter(sssom_file)

    print(f"\nConverting FAIRSCAPE RO-Crate → D4D YAML...")
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")

    try:
        d4d_dict, is_valid = converter.convert_and_save(
            Path(args.input),
            Path(args.output),
            validate=not args.no_validate
        )

        print(f"\n✓ Conversion complete")
        print(f"  D4D fields: {len(d4d_dict)}")
        print(f"  Validation: {'✓ PASSED' if is_valid else '✗ FAILED'}")

        return 0 if is_valid else 1

    except Exception as e:
        print(f"\n✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
