#!/usr/bin/env python3
"""
SSSOM Integration - Use standard sssom-py package for SSSOM operations.

This module provides integration with the standard sssom-py package for
reading, querying, and manipulating SSSOM mapping files. Falls back to
custom SSSOMReader if sssom-py is not available.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import warnings

# Try to import standard sssom package
try:
    import sssom
    from sssom.parsers import parse_sssom_table
    from sssom.writers import write_table
    from sssom.util import filter_redundant_rows
    SSSOM_AVAILABLE = True
except ImportError:
    SSSOM_AVAILABLE = False
    warnings.warn(
        "sssom-py package not available. Install with: pip install sssom\n"
        "Falling back to custom SSSOMReader implementation.",
        ImportWarning
    )

from .sssom_reader import SSSOMReader, SSSOMMapping


class SSSOMIntegration:
    """
    Integration layer for SSSOM operations using standard sssom-py package.

    Provides a unified interface that uses sssom-py when available,
    with fallback to custom SSSOMReader implementation.
    """

    def __init__(self, sssom_path: str, verbose: bool = False):
        """
        Initialize SSSOM integration.

        Args:
            sssom_path: Path to SSSOM TSV file
            verbose: Print loading information
        """
        self.sssom_path = Path(sssom_path)
        self.verbose = verbose
        self.use_standard = SSSOM_AVAILABLE

        if not self.sssom_path.exists():
            raise FileNotFoundError(f"SSSOM file not found: {sssom_path}")

        # Load using appropriate method
        if self.use_standard:
            self._load_with_sssom_py()
        else:
            self._load_with_custom_reader()

    def _load_with_sssom_py(self):
        """Load SSSOM file using standard sssom-py package."""
        if self.verbose:
            print(f"Loading SSSOM with standard sssom-py package: {self.sssom_path}")

        # Parse SSSOM file
        self.msdf = parse_sssom_table(str(self.sssom_path))

        if self.verbose:
            print(f"Loaded {len(self.msdf.df)} mappings")
            print(f"Mapping set ID: {self.msdf.mapping_set_id}")

    def _load_with_custom_reader(self):
        """Load SSSOM file using custom SSSOMReader."""
        if self.verbose:
            print(f"Loading SSSOM with custom reader: {self.sssom_path}")

        self.reader = SSSOMReader(str(self.sssom_path), verbose=self.verbose)

    def get_mappings_count(self) -> int:
        """
        Get total number of mappings.

        Returns:
            Number of mappings in the SSSOM file
        """
        if self.use_standard:
            return len(self.msdf.df)
        else:
            return len(self.reader.mappings)

    def get_mappings_by_subject(self, subject_id: str) -> List[Dict]:
        """
        Get mappings for a given subject ID.

        Args:
            subject_id: Subject identifier to search for

        Returns:
            List of mapping dictionaries
        """
        if self.use_standard:
            df = self.msdf.df
            matches = df[df['subject_id'] == subject_id]
            return matches.to_dict('records')
        else:
            mappings = self.reader.get_by_subject(subject_id)
            return [self._mapping_to_dict(m) for m in mappings]

    def get_mappings_by_object(self, object_id: str) -> List[Dict]:
        """
        Get mappings for a given object ID.

        Args:
            object_id: Object identifier to search for

        Returns:
            List of mapping dictionaries
        """
        if self.use_standard:
            df = self.msdf.df
            matches = df[df['object_id'] == object_id]
            return matches.to_dict('records')
        else:
            mappings = self.reader.get_by_object(object_id)
            return [self._mapping_to_dict(m) for m in mappings]

    def get_mappings_by_predicate(self, predicate_id: str) -> List[Dict]:
        """
        Get mappings for a given predicate.

        Args:
            predicate_id: Predicate identifier (e.g., 'skos:exactMatch')

        Returns:
            List of mapping dictionaries
        """
        if self.use_standard:
            df = self.msdf.df
            matches = df[df['predicate_id'] == predicate_id]
            return matches.to_dict('records')
        else:
            mappings = self.reader.get_by_predicate(predicate_id)
            return [self._mapping_to_dict(m) for m in mappings]

    def get_exact_matches(self) -> List[Dict]:
        """
        Get all exact match mappings.

        Returns:
            List of exact match mapping dictionaries
        """
        return self.get_mappings_by_predicate('skos:exactMatch')

    def get_subjects(self) -> Set[str]:
        """
        Get set of all subject IDs.

        Returns:
            Set of subject identifiers
        """
        if self.use_standard:
            return set(self.msdf.df['subject_id'].dropna().unique())
        else:
            return self.reader.get_mapped_subjects()

    def get_objects(self) -> Set[str]:
        """
        Get set of all object IDs.

        Returns:
            Set of object identifiers
        """
        if self.use_standard:
            return set(self.msdf.df['object_id'].dropna().unique())
        else:
            return self.reader.get_mapped_objects()

    def get_predicates(self) -> Set[str]:
        """
        Get set of all predicates.

        Returns:
            Set of predicate identifiers
        """
        if self.use_standard:
            return set(self.msdf.df['predicate_id'].dropna().unique())
        else:
            return self.reader.get_predicates()

    def filter_by_confidence(self, min_confidence: float) -> List[Dict]:
        """
        Filter mappings by minimum confidence.

        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of filtered mapping dictionaries
        """
        if self.use_standard:
            df = self.msdf.df
            # Handle both numeric and string confidence values
            if 'confidence' in df.columns:
                filtered = df[df['confidence'].astype(float) >= min_confidence]
                return filtered.to_dict('records')
            else:
                return []
        else:
            mappings = self.reader.filter_by_confidence(min_confidence)
            return [self._mapping_to_dict(m) for m in mappings]

    def get_statistics(self) -> Dict:
        """
        Get mapping statistics.

        Returns:
            Dictionary with statistics
        """
        if self.use_standard:
            df = self.msdf.df
            stats = {
                'total_mappings': len(df),
                'unique_subjects': df['subject_id'].nunique(),
                'unique_objects': df['object_id'].nunique(),
                'predicates': df['predicate_id'].nunique(),
            }

            # Predicate counts
            predicate_counts = df['predicate_id'].value_counts().to_dict()
            stats['predicate_counts'] = predicate_counts

            # Confidence statistics
            if 'confidence' in df.columns:
                confidences = df['confidence'].dropna().astype(float)
                if len(confidences) > 0:
                    stats['avg_confidence'] = float(confidences.mean())
                    stats['mappings_with_confidence'] = len(confidences)

            # Mapping status distribution
            if 'mapping_status' in df.columns:
                status_counts = df['mapping_status'].value_counts().to_dict()
                stats['status_counts'] = status_counts

            return stats
        else:
            return self.reader.get_statistics()

    def export_to_file(self, output_path: str, format: str = 'tsv'):
        """
        Export mappings to file.

        Args:
            output_path: Output file path
            format: Output format ('tsv', 'json', 'rdf')
        """
        if not self.use_standard:
            raise NotImplementedError(
                "Export requires sssom-py package. Install with: pip install sssom"
            )

        output_path = Path(output_path)

        if format == 'tsv':
            write_table(self.msdf, output_path)
        else:
            raise ValueError(f"Format '{format}' not yet supported")

        if self.verbose:
            print(f"Exported to {output_path}")

    def _mapping_to_dict(self, mapping: SSSOMMapping) -> Dict:
        """Convert SSSOMMapping to dictionary."""
        return {
            'subject_id': mapping.subject_id,
            'subject_label': mapping.subject_label,
            'predicate_id': mapping.predicate_id,
            'object_id': mapping.object_id,
            'object_label': mapping.object_label,
            'mapping_justification': mapping.mapping_justification,
            'confidence': mapping.confidence,
            'subject_source': mapping.subject_source,
            'object_source': mapping.object_source,
            'comment': mapping.comment,
            'mapping_status': mapping.mapping_status,
            'author_id': mapping.author_id,
            'mapping_date': mapping.mapping_date,
            **mapping.extra_fields
        }

    @staticmethod
    def is_sssom_available() -> bool:
        """
        Check if standard sssom-py package is available.

        Returns:
            True if sssom-py is installed, False otherwise
        """
        return SSSOM_AVAILABLE

    @staticmethod
    def get_implementation() -> str:
        """
        Get the implementation being used.

        Returns:
            'sssom-py' if standard package is available, 'custom' otherwise
        """
        return 'sssom-py' if SSSOM_AVAILABLE else 'custom'
