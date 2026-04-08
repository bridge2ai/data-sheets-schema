#!/usr/bin/env python3
"""
Constants for D4D ↔ RO-Crate transformations.

This module centralizes all field names, mappings, priorities, and merge strategies
used in FAIRSCAPE/RO-Crate integration to avoid scattering magic strings across
the codebase.
"""

from enum import Enum
from typing import Dict, Set


class MergeStrategy(Enum):
    """Strategies for merging field values from multiple RO-Crate sources."""
    PRIMARY_WINS = "primary_wins"  # Always take value from primary source
    SECONDARY_WINS = "secondary_wins"  # Prefer secondary sources over primary
    COMBINE = "combine"  # Combine values with sections/separators
    UNION = "union"  # Merge arrays/lists with deduplication
    AGGREGATE = "aggregate"  # Aggregate statistics (prefer primary for totals)


# =============================================================================
# D4D → RO-Crate Field Mappings (Schema.org vocabulary)
# =============================================================================

# Direct 1:1 mappings (no transformation needed)
D4D_TO_ROCRATE_DIRECT: Dict[str, str] = {
    # Core metadata
    'title': 'name',
    'description': 'description',
    'keywords': 'keywords',
    'version': 'version',
    'license': 'license',
    'publisher': 'publisher',
    'language': 'language',

    # Identifiers
    'doi': 'identifier',
    'page': 'url',
    'download_url': 'contentUrl',

    # Dates
    'issued': 'datePublished',
    'created_on': 'dateCreated',
    'last_updated_on': 'dateModified',

    # File properties
    'path': 'contentUrl',
    'compression': 'fileFormat',

    # Checksums
    'md5': 'evi:md5',
    'sha256': 'evi:sha256',
    'hash': 'evi:hash',
}

# D4D fields requiring transformation
D4D_TO_ROCRATE_TRANSFORM: Dict[str, tuple[str, str]] = {
    # (rocrate_field, transformation_note)
    'bytes': ('contentSize', 'Convert int to string'),
    'total_bytes': ('contentSize', 'Convert int to string'),
    'total_size_bytes': ('contentSize', 'Convert int to string'),
    'format': ('encodingFormat', 'Use MIME type or file extension'),
    'media_type': ('encodingFormat', 'Already MIME type format'),
    'encoding': ('encodingFormat', 'Character encoding (e.g., UTF-8)'),
}

# D4D-specific fields (use d4d: namespace in RO-Crate)
D4D_NAMESPACE_FIELDS: Set[str] = {
    # FileCollection
    'collection_type',
    'file_count',

    # Motivation
    'addressing_gaps',
    'purposes',
    'tasks',
    'other_tasks',

    # Human subjects
    'informed_consent',
    'at_risk_populations',
    'sensitive_elements',
    'confidential_elements',

    # Ethics
    'ethical_reviews',
    'data_protection_impacts',
    'known_biases',

    # Uses
    'intended_uses',
    'discouraged_uses',
    'prohibited_uses',
    'existing_uses',

    # Limitations
    'known_limitations',
    'content_warnings',
    'anomalies',

    # Distribution
    'ip_restrictions',
    'regulatory_restrictions',

    # Maintenance
    'maintenance_plan',
    'version_access',
    'retention_limit',
}


# =============================================================================
# RO-Crate → D4D Field Mappings (reverse direction)
# =============================================================================

ROCRATE_TO_D4D_DIRECT: Dict[str, str] = {
    # Reverse of D4D_TO_ROCRATE_DIRECT
    'name': 'title',
    'description': 'description',
    'keywords': 'keywords',
    'version': 'version',
    'license': 'license',
    'publisher': 'publisher',
    'language': 'language',
    'identifier': 'doi',
    'url': 'page',
    'contentUrl': 'download_url',
    'datePublished': 'issued',
    'dateCreated': 'created_on',
    'dateModified': 'last_updated_on',
    'evi:md5': 'md5',
    'evi:sha256': 'sha256',
    'evi:hash': 'hash',
}

ROCRATE_TO_D4D_TRANSFORM: Dict[str, tuple[str, str]] = {
    # (d4d_field, transformation_note)
    'contentSize': ('bytes', 'Parse string to int'),
    'encodingFormat': ('format', 'Extract format from MIME type or use as-is'),
    'fileFormat': ('compression', 'Compression format for archives'),
}


# =============================================================================
# Field Merge Strategies (for combining multiple RO-Crate sources)
# =============================================================================

# Fields where primary (release/parent) source takes precedence
POLICY_FIELDS: Set[str] = {
    'prohibited_uses',
    'license_and_use_terms',
    'ip_restrictions',
    'ethical_reviews',
    'regulatory_restrictions',
    'human_subject_research',
    'is_deidentified',
    'data_governance',
    'known_biases',
    'intended_uses',
    'discouraged_uses',
    'data_protection_impacts',
    'informed_consent',
    'at_risk_populations',
    'confidential_elements',
    'sensitive_elements',
    'updates',
    'maintenance_plan',
    'version_access',
    'retention_limit',
}

# Fields where secondary (sub-crate) sources take precedence
TECHNICAL_FIELDS: Set[str] = {
    'download_url',
    'hash',
    'md5',
    'sha256',
    'content_url',
    'distribution_formats',
    'compression',
    'encoding',
    'media_type',
    'is_tabular',
    'dialect',
    'conforms_to',
}

# Fields to merge as arrays (union with deduplication)
ARRAY_FIELDS: Set[str] = {
    'keywords',
    'external_resource',
    'creators',
    'funders',
    'existing_uses',
    'other_tasks',
    'tasks',
}

# Fields to combine with sections (concatenate with separators)
DESCRIPTIVE_FIELDS: Set[str] = {
    'description',
    'purposes',
    'future_use_impacts',
    'known_limitations',
    'content_warnings',
}

# Fields that represent aggregates (prefer primary, don't sum)
AGGREGATE_FIELDS: Set[str] = {
    'bytes',
    'total_bytes',
    'total_size_bytes',
    'file_count',
    'total_file_count',
}


# =============================================================================
# RO-Crate Schema.org Types
# =============================================================================

ROCRATE_TYPES = {
    'CRATE_ROOT': ['Dataset', 'https://w3id.org/EVI#ROCrate'],
    'METADATA_DESCRIPTOR': 'CreativeWork',
    'NESTED_DATASET': 'Dataset',  # For FileCollections
    'FILE': 'MediaObject',
}

ROCRATE_REQUIRED_FIELDS = {
    'DATASET': ['name', 'description', 'keywords', 'version', 'author', 'license'],
    'METADATA_DESCRIPTOR': ['@id', '@type', 'conformsTo', 'about'],
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_merge_strategy(field_name: str) -> MergeStrategy:
    """
    Determine merge strategy for a D4D field.

    Args:
        field_name: D4D field name

    Returns:
        MergeStrategy enum value
    """
    if field_name in POLICY_FIELDS:
        return MergeStrategy.PRIMARY_WINS

    if field_name in TECHNICAL_FIELDS:
        return MergeStrategy.SECONDARY_WINS

    if field_name in ARRAY_FIELDS:
        return MergeStrategy.UNION

    if field_name in DESCRIPTIVE_FIELDS:
        return MergeStrategy.COMBINE

    if field_name in AGGREGATE_FIELDS:
        return MergeStrategy.AGGREGATE

    # Default: prefer primary source
    return MergeStrategy.PRIMARY_WINS


def is_d4d_namespace_field(field_name: str) -> bool:
    """
    Check if a D4D field should use the d4d: namespace in RO-Crate.

    Args:
        field_name: D4D field name

    Returns:
        True if field should use d4d: namespace
    """
    return field_name in D4D_NAMESPACE_FIELDS


def get_rocrate_field_name(d4d_field: str) -> str:
    """
    Map D4D field name to RO-Crate/Schema.org field name.

    Args:
        d4d_field: D4D field name

    Returns:
        RO-Crate field name (may include namespace prefix like 'd4d:')
    """
    # Check direct mappings first
    if d4d_field in D4D_TO_ROCRATE_DIRECT:
        return D4D_TO_ROCRATE_DIRECT[d4d_field]

    # Check transformation mappings
    if d4d_field in D4D_TO_ROCRATE_TRANSFORM:
        return D4D_TO_ROCRATE_TRANSFORM[d4d_field][0]

    # Check if D4D-specific namespace
    if is_d4d_namespace_field(d4d_field):
        return f'd4d:{d4d_field}'

    # Default: use as-is
    return d4d_field


def get_d4d_field_name(rocrate_field: str) -> str:
    """
    Map RO-Crate/Schema.org field name to D4D field name.

    Args:
        rocrate_field: RO-Crate field name

    Returns:
        D4D field name
    """
    # Strip d4d: namespace if present
    if rocrate_field.startswith('d4d:'):
        return rocrate_field[4:]

    # Check direct mappings
    if rocrate_field in ROCRATE_TO_D4D_DIRECT:
        return ROCRATE_TO_D4D_DIRECT[rocrate_field]

    # Check transformation mappings
    if rocrate_field in ROCRATE_TO_D4D_TRANSFORM:
        return ROCRATE_TO_D4D_TRANSFORM[rocrate_field][0]

    # Default: use as-is
    return rocrate_field
