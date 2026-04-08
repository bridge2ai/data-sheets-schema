#!/usr/bin/env python3
"""
SSSOM Reader - Read and query SSSOM mapping files.

This module provides utilities for reading SSSOM (Simple Standard for Sharing
Ontology Mappings) TSV files and querying mappings programmatically.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class SSSOMMapping:
    """Represents a single SSSOM mapping."""
    subject_id: str
    subject_label: Optional[str]
    predicate_id: str
    object_id: str
    object_label: Optional[str]
    mapping_justification: str
    confidence: Optional[float]
    subject_source: Optional[str]
    object_source: Optional[str]
    comment: Optional[str]
    mapping_status: Optional[str]
    author_id: Optional[str]
    mapping_date: Optional[str]

    # Additional fields from specific SSSOM files
    extra_fields: Dict[str, str]

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> 'SSSOMMapping':
        """Create mapping from TSV row."""
        # Core SSSOM fields
        core_fields = {
            'subject_id', 'subject_label', 'predicate_id', 'object_id',
            'object_label', 'mapping_justification', 'confidence',
            'subject_source', 'object_source', 'comment', 'mapping_status',
            'author_id', 'mapping_date'
        }

        # Get core fields
        subject_id = row.get('subject_id') or row.get('d4d_slot_name', '')
        subject_label = row.get('subject_label', '')
        predicate_id = row.get('predicate_id', '')
        object_id = row.get('object_id', '')
        object_label = row.get('object_label', '')
        mapping_justification = row.get('mapping_justification', '')

        # Parse confidence as float
        confidence_str = row.get('confidence', '')
        confidence = float(confidence_str) if confidence_str else None

        subject_source = row.get('subject_source', '')
        object_source = row.get('object_source', '')
        comment = row.get('comment', '')
        mapping_status = row.get('mapping_status', '')
        author_id = row.get('author_id', '')
        mapping_date = row.get('mapping_date', '')

        # Get extra fields not in core set
        extra_fields = {
            k: v for k, v in row.items()
            if k not in core_fields and v
        }

        return cls(
            subject_id=subject_id,
            subject_label=subject_label,
            predicate_id=predicate_id,
            object_id=object_id,
            object_label=object_label,
            mapping_justification=mapping_justification,
            confidence=confidence,
            subject_source=subject_source,
            object_source=object_source,
            comment=comment,
            mapping_status=mapping_status,
            author_id=author_id,
            mapping_date=mapping_date,
            extra_fields=extra_fields
        )


class SSSOMReader:
    """Read and query SSSOM mapping files."""

    def __init__(self, sssom_path: str, verbose: bool = False):
        """
        Initialize SSSOM reader.

        Args:
            sssom_path: Path to SSSOM TSV file
            verbose: Print loading information
        """
        self.sssom_path = Path(sssom_path)
        self.mappings: List[SSSOMMapping] = []
        self.subject_index: Dict[str, List[SSSOMMapping]] = {}
        self.object_index: Dict[str, List[SSSOMMapping]] = {}
        self.predicate_index: Dict[str, List[SSSOMMapping]] = {}
        self.verbose = verbose

        if not self.sssom_path.exists():
            raise FileNotFoundError(f"SSSOM file not found: {sssom_path}")

        self._load_sssom()

    def _load_sssom(self):
        """Load and parse SSSOM TSV file."""
        with open(self.sssom_path, 'r', encoding='utf-8') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]

            if not lines:
                if self.verbose:
                    print("Warning: SSSOM file contains only comments")
                return

            # Parse TSV
            import io
            reader = csv.DictReader(io.StringIO(''.join(lines)), delimiter='\t')

            for row in reader:
                mapping = SSSOMMapping.from_row(row)
                self.mappings.append(mapping)

                # Build indexes
                if mapping.subject_id:
                    if mapping.subject_id not in self.subject_index:
                        self.subject_index[mapping.subject_id] = []
                    self.subject_index[mapping.subject_id].append(mapping)

                if mapping.object_id:
                    if mapping.object_id not in self.object_index:
                        self.object_index[mapping.object_id] = []
                    self.object_index[mapping.object_id].append(mapping)

                if mapping.predicate_id:
                    if mapping.predicate_id not in self.predicate_index:
                        self.predicate_index[mapping.predicate_id] = []
                    self.predicate_index[mapping.predicate_id].append(mapping)

        if self.verbose:
            print(f"Loaded {len(self.mappings)} SSSOM mappings")

    def get_all_mappings(self) -> List[SSSOMMapping]:
        """
        Get all mappings.

        Returns:
            List of all SSSOMMapping objects
        """
        return self.mappings.copy()

    def get_by_subject(self, subject_id: str) -> List[SSSOMMapping]:
        """
        Get mappings by subject ID.

        Args:
            subject_id: Subject identifier to search for

        Returns:
            List of mappings with matching subject_id
        """
        return self.subject_index.get(subject_id, []).copy()

    def get_by_object(self, object_id: str) -> List[SSSOMMapping]:
        """
        Get mappings by object ID.

        Args:
            object_id: Object identifier to search for

        Returns:
            List of mappings with matching object_id
        """
        return self.object_index.get(object_id, []).copy()

    def get_by_predicate(self, predicate_id: str) -> List[SSSOMMapping]:
        """
        Get mappings by predicate.

        Args:
            predicate_id: Predicate identifier (e.g., 'skos:exactMatch')

        Returns:
            List of mappings with matching predicate_id
        """
        return self.predicate_index.get(predicate_id, []).copy()

    def get_exact_matches(self) -> List[SSSOMMapping]:
        """
        Get all exact match mappings.

        Returns:
            List of mappings with predicate skos:exactMatch
        """
        return self.get_by_predicate('skos:exactMatch')

    def get_mapped_subjects(self) -> Set[str]:
        """
        Get set of all subject IDs that have mappings.

        Returns:
            Set of subject identifiers
        """
        return set(self.subject_index.keys())

    def get_mapped_objects(self) -> Set[str]:
        """
        Get set of all object IDs that are mapped to.

        Returns:
            Set of object identifiers
        """
        return set(self.object_index.keys())

    def get_predicates(self) -> Set[str]:
        """
        Get set of all predicates used in mappings.

        Returns:
            Set of predicate identifiers
        """
        return set(self.predicate_index.keys())

    def get_statistics(self) -> Dict[str, any]:
        """
        Get mapping statistics.

        Returns:
            Dict with statistics about the SSSOM file
        """
        stats = {
            'total_mappings': len(self.mappings),
            'unique_subjects': len(self.subject_index),
            'unique_objects': len(self.object_index),
            'predicates': len(self.predicate_index),
        }

        # Count by predicate
        predicate_counts = {}
        for predicate in self.predicate_index.keys():
            predicate_counts[predicate] = len(self.predicate_index[predicate])
        stats['predicate_counts'] = predicate_counts

        # Count by mapping status if available
        status_counts = {}
        for mapping in self.mappings:
            if mapping.mapping_status:
                status_counts[mapping.mapping_status] = status_counts.get(mapping.mapping_status, 0) + 1
        if status_counts:
            stats['status_counts'] = status_counts

        # Average confidence if available
        confidences = [m.confidence for m in self.mappings if m.confidence is not None]
        if confidences:
            stats['avg_confidence'] = sum(confidences) / len(confidences)
            stats['mappings_with_confidence'] = len(confidences)

        return stats

    def filter_by_confidence(self, min_confidence: float) -> List[SSSOMMapping]:
        """
        Filter mappings by minimum confidence.

        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of mappings with confidence >= min_confidence
        """
        return [
            m for m in self.mappings
            if m.confidence is not None and m.confidence >= min_confidence
        ]

    def filter_by_status(self, status: str) -> List[SSSOMMapping]:
        """
        Filter mappings by status.

        Args:
            status: Mapping status to filter for

        Returns:
            List of mappings with matching status
        """
        return [
            m for m in self.mappings
            if m.mapping_status == status
        ]
