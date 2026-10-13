"""
D4D to FAIRSCAPE RO-Crate Converter

Converts D4D YAML/dict to FAIRSCAPE RO-Crate using Pydantic models.
"""

import json
import math
import sys
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from data_sheets_schema.rocrate_parent_admission import snapshot
from data_sheets_schema.fairscape_forward_types import (
    ForwardProjectionWarning, initialize as initialize_typed,
    projections as typed_projections, finish as finish_typed, warning_messages,
)
from data_sheets_schema.fairscape_route_assertions import (
    evidence_state, failed, forward_projections, supplied_projections, finish_forward,
)

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

if TYPE_CHECKING:
    from fairscape_models.rocrate import (
        ROCrateV1_2,
        ROCrateMetadataFileElem,
        ROCrateMetadataElem,
        GenericMetadataElem
    )

try:
    from fairscape_models.rocrate import (
        ROCrateV1_2,
        ROCrateMetadataFileElem,
        ROCrateMetadataElem,
        GenericMetadataElem
    )
    from fairscape_models.dataset import Dataset
    from fairscape_models.fairscape_base import IdentifierValue
    from pydantic import ValidationError
    FAIRSCAPE_AVAILABLE = True
except ImportError as e:
    print(f"Error: Cannot import FAIRSCAPE models: {e}")
    FAIRSCAPE_AVAILABLE = False
    # Provide stub types when not available
    ROCrateV1_2 = Any  # type: ignore
    ROCrateMetadataFileElem = Any  # type: ignore
    ROCrateMetadataElem = Any  # type: ignore
    GenericMetadataElem = Any  # type: ignore


def _require_finite_floats(value) -> None:
    """Check ordinary containers in a validated model's Python-mode dump."""
    pending = [value]
    seen = set()
    while pending:
        item = pending.pop()
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError(
                "Non-finite float in validated FAIRSCAPE model before JSON serialization")
        kind = type(item)
        if kind is dict or kind is list or kind is tuple or kind is set or kind is frozenset:
            identity = id(item)
            if identity in seen:
                continue
            seen.add(identity)
            if kind is dict:
                pending.extend(item.keys())
                pending.extend(item.values())
            else:
                pending.extend(item)


class D4DToFairscapeConverter:
    """Convert D4D metadata to FAIRSCAPE RO-Crate."""
    
    def __init__(self):
        if not FAIRSCAPE_AVAILABLE:
            raise RuntimeError("FAIRSCAPE models not available")
        self._route_evidence = evidence_state("d4d_to_fairscape", "dict")
        self._projections = {}
        initialize_typed(self._route_evidence)
    
    @property
    def route_evidence(self):
        """Detached finite source values and actual model projection outcomes."""
        return snapshot(self._route_evidence)

    def convert(self, d4d_dict: Dict[str, Any], *, source_evidence=None) -> ROCrateV1_2:
        """
        Convert D4D dictionary to FAIRSCAPE RO-Crate.

        Args:
            d4d_dict: D4D metadata dictionary
            source_evidence: Optional completed reverse evidence bound to this
                entire Dataset; permits re-emitting separate supplied assertions.

        Returns:
            FAIRSCAPE ROCrateV1_2 Pydantic model
        """
        self._route_evidence = evidence_state("d4d_to_fairscape", "dict")
        self._projections = {}
        initialize_typed(self._route_evidence)
        try:
            # The model's before-validator mutates its submitted graph. Caller
            # objects and diagnostic raw values must not share that lifecycle.
            d4d_dict = deepcopy(d4d_dict)
            self._projections = forward_projections(self._route_evidence, d4d_dict)
            supplied_projections(self._route_evidence, d4d_dict,
                                 source_evidence, self._projections)
            self._projections.update(typed_projections(self._route_evidence, d4d_dict))
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

            # Existing model objects bypass the envelope's dictionary dispatch.
            # Check the actual published JSON before claiming completed evidence.
            self._validate_wire(rocrate)
            final_graph = rocrate.model_dump(by_alias=True, exclude_none=False)["@graph"]
            final_root = next(node for node in final_graph if node.get("@id") == "./")
            finish_forward(self._route_evidence, final_root)
            finish_typed(self._route_evidence, final_root)
            return rocrate
        except BaseException as exc:
            failed(self._route_evidence, exc)
            finish_typed(self._route_evidence)
            raise

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
        # Collect all hasPart references: file collections + other resources
        all_hasPart_ids = list(hasPart_ids or [])

        # Include Dataset.resources (non-file-collection nested datasets) in hasPart
        if "resources" in d4d_dict and d4d_dict["resources"]:
            for resource in d4d_dict["resources"]:
                if isinstance(resource, dict) and "id" in resource:
                    all_hasPart_ids.append(resource["id"])

        dataset_params = {
            "@id": "./",
            "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
            "name": d4d_dict.get("title") or d4d_dict.get("name") or "Untitled Dataset",
            "description": d4d_dict.get("description") or "No description provided",
            "keywords": d4d_dict.get("keywords", []),
            "version": d4d_dict.get("version", "1.0"),
            "author": author_str,
            "license": d4d_dict.get("license", "No license specified"),  # Required field
            "hasPart": [{"@id": id} for id in all_hasPart_ids]
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
            'prohibited_uses': 'rai:prohibitedUses',
            'ethical_reviews': 'rai:ethicalReview',
            'machine_annotation_analyses': 'rai:machineAnnotationTools',
            'imputation_protocols': 'rai:imputationProtocol',
        }

        for d4d_field, rai_prop in rai_mapping.items():
            if d4d_field in d4d_dict:
                dataset_params[rai_prop] = d4d_dict[d4d_field]

        # Add D4D namespace properties
        d4d_mapping = {
            'human_subject_research': 'd4d:humanSubject',
        }

        for d4d_field, d4d_prop in d4d_mapping.items():
            if d4d_field in d4d_dict:
                dataset_params[d4d_prop] = d4d_dict[d4d_field]

        dataset_params.update(self._projections)

        # Create Dataset element
        dataset = ROCrateMetadataElem(**dataset_params)

        return dataset

    def _build_file_collections(self, d4d_dict: Dict[str, Any]) -> tuple[List[GenericMetadataElem], List[str]]:
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
                "@type": ["Dataset"],  # Must be a list
                "name": fc.get("name") or fc.get("title") or f"File Collection {idx + 1}",
                "description": fc.get("description") or "File collection",
                # Required fields for ROCrateMetadataElem
                "keywords": fc.get("keywords", []),
                "version": fc.get("version", "1.0"),
                "author": fc.get("author", "Unknown"),
                "license": fc.get("license", "Unspecified"),
                "hasPart": []
            }

            # Map FileCollection properties to RO-Crate Dataset properties
            # Note: format, bytes, encoding, media_type, sha256, md5, dialect, hash
            # are now file-level properties (on File objects), not FileCollection properties

            # Collection-level aggregate size
            if "total_bytes" in fc:
                collection_params["contentSize"] = str(fc["total_bytes"])

            # Collection location/URL
            if "path" in fc:
                collection_params["contentUrl"] = fc["path"]

            # Collection compression (if packaged as archive)
            if "compression" in fc:
                collection_params["fileFormat"] = fc["compression"]

            # D4D-specific collection properties
            if "collection_type" in fc:
                collection_params["d4d:collectionType"] = fc["collection_type"]

            if "file_count" in fc:
                collection_params["d4d:fileCount"] = fc["file_count"]

            # TODO: Convert FileCollection.resources (File objects) to RO-Crate File entities
            # Currently, file-level metadata in resources is not converted to RO-Crate.
            # Future work: iterate fc.get('resources', []), create RO-Crate File entities,
            # and add their @ids to hasPart.

            # Retain the existing field validation and defaults before using the
            # generic class. These collections assert schema.org Dataset, not
            # the EVI Dataset class (which requires a publication date/format)
            # or the ROCrate class used for the actual root.
            validated = ROCrateMetadataElem(**collection_params)
            validated_fields = validated.model_dump(
                mode="python", by_alias=True, exclude_none=False)
            validated_fields["@type"] = ["https://schema.org/Dataset"]
            collection_elem = GenericMetadataElem(**validated_fields)
            file_collections.append(collection_elem)

        return file_collections, hasPart_ids

    @staticmethod
    def _validate_wire(rocrate: ROCrateV1_2) -> None:
        """Require genuine JSON readback to retain the complete published tree."""
        # JSON-mode serializers can silently replace non-finite floats with
        # null. Inspect the validated model first, not unrelated raw input.
        _require_finite_floats(rocrate.model_dump(
            mode="python", by_alias=True, exclude_none=True))
        wire = json.dumps(
            rocrate.model_dump(mode="json", by_alias=True, exclude_none=True),
            ensure_ascii=True, allow_nan=False, sort_keys=True,
            separators=(",", ":"))
        # The before-validator mutates its submitted graph; JSON decoding gives
        # it an independent graph, without changing the returned model.
        readback = ROCrateV1_2.model_validate(json.loads(wire))
        _require_finite_floats(readback.model_dump(
            mode="python", by_alias=True, exclude_none=True))
        returned_wire = json.dumps(
            readback.model_dump(mode="json", by_alias=True, exclude_none=True),
            ensure_ascii=True, allow_nan=False, sort_keys=True,
            separators=(",", ":"))
        # Sorted JSON distinguishes false/0, integers/floats and array order;
        # ordinary Python equality would incorrectly equate some of them.
        if returned_wire != wire:
            raise ValueError("FAIRSCAPE JSON readback changed the serialized metadata")

    def validate(self, rocrate: ROCrateV1_2) -> tuple[bool, Optional[List[str]]]:
        """
        Validate FAIRSCAPE RO-Crate serialization and genuine JSON readback.
        
        Returns:
            (is_valid, errors)
        """
        try:
            self._validate_wire(rocrate)
            return True, None
        except ValidationError as e:
            errors = [str(err) for err in e.errors()]
            return False, errors
        except (TypeError, ValueError) as e:
            return False, [type(e).__name__ + ": " + str(e)]


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

    # This flag checks the model, not whether every source value was emitted.
    validation_result = converter.validate(rocrate)
    messages = warning_messages(converter.route_evidence)
    if messages:
        warnings.warn("\n".join(messages) + "\nRaw evidence was not saved; use "
                      "D4DToFairscapeConverter.route_evidence or CLI --report PATH.",
                      ForwardProjectionWarning, stacklevel=2)

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
        print("✓ Model validation PASSED (not a source-preservation claim)")
    else:
        print(f"✗ Validation FAILED: {errors}")

    import json
    print(json.dumps(rocrate.model_dump(exclude_none=True), indent=2))
