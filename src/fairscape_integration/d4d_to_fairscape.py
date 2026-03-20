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
        
        # 2. Add root dataset
        dataset = self._build_dataset(d4d_dict)
        graph.append(dataset)
        
        # 3. Create RO-Crate
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
    
    def _build_dataset(self, d4d_dict: Dict[str, Any]) -> ROCrateMetadataElem:
        """Build Dataset from D4D metadata."""

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
            "hasPart": []  # Required field, start with empty list
        }

        # Add optional fields
        if "issued" in d4d_dict or "datePublished" in d4d_dict:
            dataset_params["datePublished"] = d4d_dict.get("issued") or d4d_dict.get("datePublished")

        if "publisher" in d4d_dict:
            dataset_params["publisher"] = d4d_dict["publisher"]

        # Create Dataset element
        dataset = ROCrateMetadataElem(**dataset_params)

        return dataset
    
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
