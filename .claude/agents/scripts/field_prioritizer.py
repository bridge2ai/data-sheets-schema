#!/usr/bin/env python3
"""
Field Prioritizer - Resolve conflicts when merging multiple RO-Crates.

This module determines merge strategies for different D4D field types when
combining data from multiple RO-Crate sources (e.g., parent + children).
"""

from enum import Enum
from typing import Any, List, Optional, Tuple


class MergeStrategy(Enum):
    """Strategies for merging field values from multiple sources."""
    PRIMARY_WINS = "primary_wins"  # Always take value from primary source
    SECONDARY_WINS = "secondary_wins"  # Prefer secondary sources over primary
    COMBINE = "combine"  # Combine values with sections/separators
    UNION = "union"  # Merge arrays/lists with deduplication
    AGGREGATE = "aggregate"  # Aggregate statistics (prefer primary for totals)


class FieldPrioritizer:
    """Determine merge strategy and resolve conflicts between RO-Crate sources."""

    # Fields where primary (release/parent) source takes precedence
    POLICY_FIELDS = {
        'prohibited_uses', 'license_and_use_terms', 'ip_restrictions',
        'ethical_reviews', 'regulatory_restrictions', 'human_subject_research',
        'is_deidentified', 'data_governance', 'known_biases', 'intended_uses',
        'discouraged_uses', 'data_protection_impacts', 'informed_consent',
        'at_risk_populations', 'confidential_elements', 'sensitive_elements',
        'updates', 'maintenance_plan', 'version_access', 'retention_limit'
    }

    # Fields where secondary (sub-crate) sources take precedence
    TECHNICAL_FIELDS = {
        'download_url', 'hash', 'md5', 'sha256', 'content_url',
        'distribution_formats', 'compression', 'encoding', 'media_type',
        'is_tabular', 'dialect', 'conforms_to'
    }

    # Fields to merge as arrays (union with deduplication)
    ARRAY_FIELDS = {
        'keywords', 'external_resource', 'creators', 'funders',
        'existing_uses', 'other_tasks', 'tasks'
    }

    # Fields to combine with sections
    DESCRIPTIVE_FIELDS = {
        'description', 'purposes', 'future_use_impacts',
        'known_limitations', 'content_warnings'
    }

    # Fields that represent aggregates (prefer primary)
    AGGREGATE_FIELDS = {
        'bytes'  # Total size from release, not sum of sub-crates
    }

    def __init__(self):
        """Initialize field prioritizer."""
        pass

    def get_merge_strategy(self, field_name: str) -> MergeStrategy:
        """
        Determine merge strategy for a D4D field.

        Args:
            field_name: D4D field name

        Returns:
            MergeStrategy enum value
        """
        if field_name in self.POLICY_FIELDS:
            return MergeStrategy.PRIMARY_WINS

        if field_name in self.TECHNICAL_FIELDS:
            return MergeStrategy.SECONDARY_WINS

        if field_name in self.ARRAY_FIELDS:
            return MergeStrategy.UNION

        if field_name in self.DESCRIPTIVE_FIELDS:
            return MergeStrategy.COMBINE

        if field_name in self.AGGREGATE_FIELDS:
            return MergeStrategy.AGGREGATE

        # Default: prefer primary source
        return MergeStrategy.PRIMARY_WINS

    def resolve_conflict(
        self,
        field_name: str,
        primary_value: Any,
        secondary_values: List[Tuple[Any, str]]
    ) -> Tuple[Any, List[str]]:
        """
        Resolve conflicting values from multiple sources.

        Args:
            field_name: D4D field name
            primary_value: Value from primary source
            secondary_values: List of (value, source_name) tuples from secondary sources

        Returns:
            Tuple of (merged_value, list_of_contributing_sources)
        """
        strategy = self.get_merge_strategy(field_name)
        sources = []

        if strategy == MergeStrategy.PRIMARY_WINS:
            if primary_value is not None:
                sources.append("primary")
                return primary_value, sources
            # Fallback to first available secondary
            for value, source in secondary_values:
                if value is not None:
                    sources.append(source)
                    return value, sources
            return None, []

        elif strategy == MergeStrategy.SECONDARY_WINS:
            # Prefer secondary sources
            for value, source in secondary_values:
                if value is not None:
                    sources.append(source)
                    return value, sources
            # Fallback to primary
            if primary_value is not None:
                sources.append("primary")
                return primary_value, sources
            return None, []

        elif strategy == MergeStrategy.UNION:
            return self._merge_arrays(field_name, primary_value, secondary_values)

        elif strategy == MergeStrategy.COMBINE:
            return self._combine_descriptive(field_name, primary_value, secondary_values)

        elif strategy == MergeStrategy.AGGREGATE:
            # For aggregates, always prefer primary
            if primary_value is not None:
                sources.append("primary")
                return primary_value, sources
            return None, []

        # Default fallback
        if primary_value is not None:
            sources.append("primary")
            return primary_value, sources
        return None, []

    def _merge_arrays(
        self,
        field_name: str,
        primary_value: Any,
        secondary_values: List[Tuple[Any, str]]
    ) -> Tuple[Any, List[str]]:
        """Merge array/list fields with deduplication."""
        all_items = []
        sources = []

        # Add primary items
        if primary_value is not None:
            if isinstance(primary_value, list):
                all_items.extend(primary_value)
            else:
                all_items.append(primary_value)
            sources.append("primary")

        # Add secondary items
        for value, source in secondary_values:
            if value is not None:
                if isinstance(value, list):
                    all_items.extend(value)
                else:
                    all_items.append(value)
                if source not in sources:
                    sources.append(source)

        if not all_items:
            return None, []

        # Deduplicate while preserving order
        # For simple types (strings, numbers)
        if all(isinstance(item, (str, int, float)) for item in all_items):
            seen = set()
            unique = []
            for item in all_items:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)
            return unique, sources

        # For complex types (dicts), deduplicate by string representation
        seen = set()
        unique = []
        for item in all_items:
            item_str = str(item)
            if item_str not in seen:
                seen.add(item_str)
                unique.append(item)

        return unique, sources

    def _combine_descriptive(
        self,
        field_name: str,
        primary_value: Any,
        secondary_values: List[Tuple[Any, str]]
    ) -> Tuple[str, List[str]]:
        """Combine descriptive text fields with sections."""
        sections = []
        sources = []

        # Add primary section
        if primary_value:
            sections.append(f"## Overview\n{primary_value}")
            sources.append("primary")

        # Add secondary sections
        for value, source in secondary_values:
            if value:
                # Create section header from source name
                source_title = source.replace('-', ' ').replace('_', ' ').title()
                sections.append(f"## {source_title}\n{value}")
                if source not in sources:
                    sources.append(source)

        if not sections:
            return None, []

        # Combine with double newlines
        combined = "\n\n".join(sections)
        return combined, sources

    def get_field_category(self, field_name: str) -> str:
        """
        Get human-readable category for a field.

        Args:
            field_name: D4D field name

        Returns:
            Category string (e.g., "Policy/Governance", "Technical/Access")
        """
        if field_name in self.POLICY_FIELDS:
            return "Policy/Governance"
        elif field_name in self.TECHNICAL_FIELDS:
            return "Technical/Access"
        elif field_name in self.ARRAY_FIELDS:
            return "Array/Collection"
        elif field_name in self.DESCRIPTIVE_FIELDS:
            return "Descriptive"
        elif field_name in self.AGGREGATE_FIELDS:
            return "Aggregate Statistics"
        else:
            return "General"


if __name__ == "__main__":
    # Test the field prioritizer
    prioritizer = FieldPrioritizer()

    test_fields = [
        'prohibited_uses',  # Policy
        'download_url',     # Technical
        'keywords',         # Array
        'description',      # Descriptive
        'bytes',           # Aggregate
        'title'            # Default
    ]

    print("=== Field Prioritizer Test ===\n")

    for field in test_fields:
        strategy = prioritizer.get_merge_strategy(field)
        category = prioritizer.get_field_category(field)
        print(f"{field:25} {category:20} {strategy.value}")

    # Test conflict resolution
    print("\n=== Conflict Resolution Test ===\n")

    # Test UNION strategy (keywords)
    primary = ['AI', 'READI', 'diabetes']
    secondary = [
        (['iPSC', 'stem cells', 'AI'], 'mass-spec-iPSCs'),
        (['cancer', 'proteomics', 'READI'], 'mass-spec-cancer')
    ]
    merged, sources = prioritizer.resolve_conflict('keywords', primary, secondary)
    print(f"Keywords merged: {merged}")
    print(f"Sources: {sources}\n")

    # Test COMBINE strategy (description)
    primary_desc = "CM4AI release dataset for mass spectrometry"
    secondary_desc = [
        ('iPSC proteomics data', 'mass-spec-iPSCs'),
        ('Cancer cell proteomics data', 'mass-spec-cancer')
    ]
    merged_desc, sources = prioritizer.resolve_conflict('description', primary_desc, secondary_desc)
    print(f"Description merged:\n{merged_desc}")
    print(f"Sources: {sources}")
