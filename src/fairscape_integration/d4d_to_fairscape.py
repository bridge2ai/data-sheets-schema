"""
D4D to FAIRSCAPE RO-Crate Converter

Converts D4D YAML/dict to FAIRSCAPE RO-Crate using Pydantic models.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import (
        ROCrateV1_2,
        ROCrateMetadataFileElem,
        ROCrateMetadataElem
    )
    from fairscape_models.dataset import Dataset
    from fairscape_models.fairscape_base import IdentifierValue
    from pydantic import ValidationError
    FAIRSCAPE_AVAILABLE = True
except ImportError as e:
    print(f"Error: Cannot import FAIRSCAPE models: {e}")
    FAIRSCAPE_AVAILABLE = False


class D4DToFairscapeConverter:
    """Convert D4D metadata to FAIRSCAPE RO-Crate."""
    
    def __init__(self):
        if not FAIRSCAPE_AVAILABLE:
            raise RuntimeError("FAIRSCAPE models not available")
    
    def convert(self, d4d_dict: Dict[str, Any]) -> ROCrateV1_2:
        """
        Convert D4D dictionary to FAIRSCAPE RO-Crate.

        Args:
            d4d_dict: D4D metadata dictionary

        Returns:
            FAIRSCAPE ROCrateV1_2 Pydantic model
        """
        # Build graph elements
        graph = []

        # 1. Add metadata descriptor
        metadata_descriptor = ROCrateMetadataFileElem(**{
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
            "about": {"@id": "./"}
        })
        graph.append(metadata_descriptor)

        # 2. Build file collections (nested Datasets)
        file_collections, hasPart_ids = self._build_file_collections(d4d_dict)
        graph.extend(file_collections)

        # 3. Add root dataset (with hasPart references to file collections)
        dataset = self._build_dataset(d4d_dict, hasPart_ids)
        graph.append(dataset)

        # 4. Create RO-Crate
        rocrate = ROCrateV1_2(**{
            "@context": {
                "@vocab": "https://schema.org/",
                "evi": "https://w3id.org/EVI#",
                "rai": "http://mlcommons.org/croissant/RAI/",
                "d4d": "https://w3id.org/bridge2ai/data-sheets-schema/"
            },
            "@graph": graph
        })

        return rocrate
    
    def _build_dataset(self, d4d_dict: Dict[str, Any], hasPart_ids: List[str] = None) -> ROCrateMetadataElem:
        """
        Build Dataset from D4D metadata.

        Args:
            d4d_dict: D4D metadata dictionary
            hasPart_ids: List of @id references to FileCollection entities

        Returns:
            ROCrateMetadataElem representing the root Dataset
        """

        # Extract author names from D4D creators (which may be complex Person objects)
        authors = d4d_dict.get("creators") or d4d_dict.get("author")
        author_str = "Unknown"
        if authors:
            if isinstance(authors, list):
                # Extract names from Person dicts or use strings directly
                names = []
                for author in authors:
                    if isinstance(author, dict):
                        names.append(author.get("name", "Unknown"))
                    else:
                        names.append(str(author))
                author_str = "; ".join(names)
            elif isinstance(authors, str):
                author_str = authors
            else:
                author_str = str(authors)

        # Build dataset params using JSON-LD field names (aliases)
        dataset_params = {
            "@id": "./",
            "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
            "name": d4d_dict.get("title") or d4d_dict.get("name") or "Untitled Dataset",
            "description": d4d_dict.get("description") or "No description provided",
            "keywords": d4d_dict.get("keywords", []),
            "version": d4d_dict.get("version", "1.0"),
            "author": author_str,
            "license": d4d_dict.get("license", "No license specified"),  # Required field
            "hasPart": [{"@id": id} for id in (hasPart_ids or [])]  # Add file collection references
        }

        # Add optional Schema.org fields
        if "issued" in d4d_dict or "datePublished" in d4d_dict:
            dataset_params["datePublished"] = d4d_dict.get("issued") or d4d_dict.get("datePublished")

        if "publisher" in d4d_dict:
            dataset_params["publisher"] = d4d_dict["publisher"]

        if "doi" in d4d_dict:
            dataset_params["identifier"] = d4d_dict["doi"]

        # File properties: only add at dataset level if no file_collections exist
        # (for backward compatibility with legacy files)
        has_file_collections = bool(d4d_dict.get("file_collections"))

        if not has_file_collections:
            if "bytes" in d4d_dict:
                dataset_params["contentSize"] = str(d4d_dict["bytes"])
        else:
            # Use aggregated total_size_bytes if available
            if "total_size_bytes" in d4d_dict:
                dataset_params["contentSize"] = str(d4d_dict["total_size_bytes"])

        # Add EVI namespace properties (computational provenance)
        evi_mapping = {
            'dataset_count': 'evi:datasetCount',
            'computation_count': 'evi:computationCount',
            'software_count': 'evi:softwareCount',
            'schema_count': 'evi:schemaCount',
            'total_entities': 'evi:totalEntities',
            'distribution_formats': 'evi:formats',
        }

        # Only add file-level properties if no file_collections
        if not has_file_collections:
            evi_mapping['md5'] = 'evi:md5'
            evi_mapping['sha256'] = 'evi:sha256'

        for d4d_field, evi_prop in evi_mapping.items():
            if d4d_field in d4d_dict:
                dataset_params[evi_prop] = d4d_dict[d4d_field]

        # Add RAI namespace properties (responsible AI)
        rai_mapping = {
            'intended_uses': 'rai:dataUseCases',
            'known_biases': 'rai:dataBiases',
            'known_limitations': 'rai:dataLimitations',
            'acquisition_methods': 'rai:dataCollection',
            'missing_data_documentation': 'rai:dataCollectionMissingData',
            'raw_data_sources': 'rai:dataCollectionRawData',
            'collection_timeframes': 'rai:dataCollectionTimeframe',
            'prohibited_uses': 'rai:prohibitedUses',
            'ethical_reviews': 'rai:ethicalReview',
            'confidential_elements': 'rai:personalSensitiveInformation',
            'data_protection_impacts': 'rai:dataSocialImpact',
            'updates': 'rai:dataReleaseMaintenancePlan',
            'preprocessing_strategies': 'rai:dataPreprocessingProtocol',
            'labeling_strategies': 'rai:dataAnnotationProtocol',
            'annotation_analyses': 'rai:dataAnnotationAnalysis',
            'machine_annotation_analyses': 'rai:machineAnnotationTools',
            'imputation_protocols': 'rai:imputationProtocol',
        }

        for d4d_field, rai_prop in rai_mapping.items():
            if d4d_field in d4d_dict:
                dataset_params[rai_prop] = d4d_dict[d4d_field]

        # Add D4D namespace properties
        d4d_mapping = {
            'addressing_gaps': 'd4d:addressingGaps',
            'anomalies': 'd4d:dataAnomalies',
            'content_warnings': 'd4d:contentWarning',
            'informed_consent': 'd4d:informedConsent',
            'human_subject_research': 'd4d:humanSubject',
            'vulnerable_populations': 'd4d:atRiskPopulations',
        }

        for d4d_field, d4d_prop in d4d_mapping.items():
            if d4d_field in d4d_dict:
                dataset_params[d4d_prop] = d4d_dict[d4d_field]

        # Create Dataset element
        dataset = ROCrateMetadataElem(**dataset_params)

        return dataset

    def _build_file_collections(self, d4d_dict: Dict[str, Any]) -> tuple[List[ROCrateMetadataElem], List[str]]:
        """
        Build nested Dataset entities for FileCollections.

        Args:
            d4d_dict: D4D metadata dictionary

        Returns:
            Tuple of (file_collection_elements, hasPart_ids)
        """
        file_collections = []
        hasPart_ids = []

        # Get file_collections from D4D
        collections_list = d4d_dict.get("file_collections", [])

        for idx, fc in enumerate(collections_list):
            if not isinstance(fc, dict):
                continue

            # Build @id for this collection
            collection_id = fc.get("id") or f"#collection-{idx + 1}"
            hasPart_ids.append(collection_id)

            # Build nested Dataset parameters
            collection_params = {
                "@id": collection_id,
                "@type": "Dataset",
                "name": fc.get("name") or fc.get("title") or f"File Collection {idx + 1}",
                "description": fc.get("description") or "File collection",
            }

            # Map FileCollection properties to RO-Crate Dataset properties
            if "format" in fc:
                collection_params["encodingFormat"] = fc["format"]

            if "bytes" in fc:
                collection_params["contentSize"] = str(fc["bytes"])
            elif "total_bytes" in fc:
                collection_params["contentSize"] = str(fc["total_bytes"])

            if "sha256" in fc:
                collection_params["sha256"] = fc["sha256"]

            if "md5" in fc:
                collection_params["md5"] = fc["md5"]

            if "path" in fc:
                collection_params["contentUrl"] = fc["path"]

            if "media_type" in fc:
                collection_params["encodingFormat"] = fc["media_type"]

            if "compression" in fc:
                collection_params["fileFormat"] = fc["compression"]

            if "encoding" in fc:
                collection_params["encoding"] = fc["encoding"]

            if "collection_type" in fc:
                collection_params["d4d:collectionType"] = fc["collection_type"]

            if "file_count" in fc:
                collection_params["d4d:fileCount"] = fc["file_count"]

            # Create nested Dataset element
            collection_elem = ROCrateMetadataElem(**collection_params)
            file_collections.append(collection_elem)

        return file_collections, hasPart_ids

    def validate(self, rocrate: ROCrateV1_2) -> tuple[bool, Optional[List[str]]]:
        """
        Validate FAIRSCAPE RO-Crate.
        
        Returns:
            (is_valid, errors)
        """
        try:
            # Pydantic validation happens on construction
            # Try to serialize to ensure all fields are valid
            rocrate.model_dump()
            return True, None
        except ValidationError as e:
            errors = [str(err) for err in e.errors()]
            return False, errors


def convert_d4d_to_fairscape(d4d_dict: Dict[str, Any]) -> tuple[ROCrateV1_2, tuple[bool, Optional[List[str]]]]:
    """
    Convert D4D dict to FAIRSCAPE RO-Crate with validation.

    Args:
        d4d_dict: D4D metadata dictionary

    Returns:
        (rocrate, (is_valid, errors))
    """
    converter = D4DToFairscapeConverter()
    rocrate = converter.convert(d4d_dict)

    # Validate
    validation_result = converter.validate(rocrate)

    return rocrate, validation_result


if __name__ == "__main__":
    # Test with minimal D4D data
    test_d4d = {
        "title": "Test Dataset",
        "description": "A test dataset for FAIRSCAPE conversion",
        "keywords": ["test", "fairscape", "d4d"],
        "license": "CC-BY-4.0",
        "creators": "John Doe; Jane Smith",
        "doi": "10.1234/test",
        "issued": "2026-03-19"
    }

    print("Converting D4D to FAIRSCAPE RO-Crate...")
    rocrate, (is_valid, errors) = convert_d4d_to_fairscape(test_d4d)

    if is_valid:
        print("✓ Validation PASSED")
    else:
        print(f"✗ Validation FAILED: {errors}")

    import json
    print(json.dumps(rocrate.model_dump(exclude_none=True), indent=2))
