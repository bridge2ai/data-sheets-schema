#!/usr/bin/env python3
"""
RO-Crate Merger - Merge multiple RO-Crates into single D4D datasheet.

This module intelligently merges data from multiple related RO-Crate files
(e.g., parent + children) into a comprehensive D4D dataset.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..constants import MergeStrategy
from .field_prioritizer import FieldPrioritizer
from .d4d_builder import D4DBuilder


class ROCrateMerger:
    """Merge multiple RO-Crate sources into single D4D dataset."""

    def __init__(self, mapping_loader, verbose: bool = False):
        """
        Initialize merger with field mapping.

        Args:
            mapping_loader: MappingLoader instance with field mappings
            verbose: Print merge progress
        """
        self.mapping = mapping_loader
        self.prioritizer = FieldPrioritizer()
        self.merged_data: Dict[str, Any] = {}
        self.provenance: Dict[str, List[str]] = {}
        self.merge_stats: Dict[str, int] = {
            'total_sources': 0,
            'fields_from_primary': 0,
            'fields_from_secondary': 0,
            'fields_combined': 0,
            'fields_merged_as_arrays': 0,
            'total_unique_fields': 0
        }
        self.verbose = verbose
        self.primary_index: int = 0
        self.primary_name: str = ""

    def merge_rocrates(
        self,
        rocrate_parsers: List,
        primary_index: int = 0,
        source_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Merge multiple RO-Crate parsers into single D4D dataset.

        Args:
            rocrate_parsers: List of ROCrateParser instances
            primary_index: Index of primary source (default: 0)
            source_names: Optional list of source names (default: use filenames)

        Returns:
            Merged D4D dataset dict
        """
        if not rocrate_parsers:
            raise ValueError("No RO-Crate parsers provided")

        if primary_index >= len(rocrate_parsers):
            raise ValueError(f"Primary index {primary_index} out of range")

        self.merge_stats['total_sources'] = len(rocrate_parsers)

        # Get source names
        if source_names is None:
            source_names = [
                Path(parser.rocrate_path).name.replace('-ro-crate-metadata.json', '')
                for parser in rocrate_parsers
            ]

        # Validate source_names length
        if len(source_names) != len(rocrate_parsers):
            raise ValueError(
                f"source_names length ({len(source_names)}) must match "
                f"rocrate_parsers length ({len(rocrate_parsers)})"
            )

        # Store primary index and name for reporting
        self.primary_index = primary_index
        self.primary_name = source_names[primary_index]

        primary_parser = rocrate_parsers[primary_index]
        primary_name = self.primary_name

        secondary_parsers = [
            (parser, name) for i, (parser, name) in enumerate(zip(rocrate_parsers, source_names))
            if i != primary_index
        ]

        if self.verbose:
            print(f"\nMerging {len(rocrate_parsers)} RO-Crate sources...")
            print(f"Primary: {primary_name}")
            for _, name in secondary_parsers:
                print(f"Secondary: {name}")

        # Get all covered D4D fields
        covered_fields = self.mapping.get_covered_fields()

        # Build D4D from each source
        if self.verbose:
            print(f"\nBuilding D4D from each source...")

        primary_builder = D4DBuilder(self.mapping, verbose=False)
        primary_data = primary_builder.build_dataset(primary_parser)

        secondary_data = []
        for parser, name in secondary_parsers:
            builder = D4DBuilder(self.mapping, verbose=False)
            data = builder.build_dataset(parser)
            secondary_data.append((data, name))

        # Merge field by field
        if self.verbose:
            print(f"\nMerging fields...")

        for field_name in covered_fields:
            primary_value = primary_data.get(field_name)
            secondary_values = [
                (data.get(field_name), name)
                for data, name in secondary_data
            ]

            # Merge this field
            merged_value, sources = self.merge_field(
                field_name,
                primary_value,
                secondary_values,
                primary_name
            )

            if merged_value is not None:
                self.merged_data[field_name] = merged_value
                self.provenance[field_name] = sources

                # Update stats
                strategy = self.prioritizer.get_merge_strategy(field_name)
                if strategy == MergeStrategy.PRIMARY_WINS and primary_name in sources:
                    self.merge_stats['fields_from_primary'] += 1
                elif strategy == MergeStrategy.SECONDARY_WINS:
                    self.merge_stats['fields_from_secondary'] += 1
                elif strategy == MergeStrategy.COMBINE:
                    self.merge_stats['fields_combined'] += 1
                elif strategy == MergeStrategy.UNION:
                    self.merge_stats['fields_merged_as_arrays'] += 1

        self.merge_stats['total_unique_fields'] = len(self.merged_data)

        if self.verbose:
            print(f"Merged {len(self.merged_data)} unique fields")

        return self.merged_data

    def merge_field(
        self,
        field_name: str,
        primary_value: Any,
        secondary_values: List[Tuple[Any, str]],
        primary_name: str
    ) -> Tuple[Any, List[str]]:
        """
        Merge values for a single field using precedence rules.

        Args:
            field_name: D4D field name
            primary_value: Value from primary source
            secondary_values: List of (value, source_name) tuples
            primary_name: Name of primary source

        Returns:
            Tuple of (merged_value, list_of_contributing_sources)
        """
        # Use field prioritizer to resolve conflicts
        merged_value, sources = self.prioritizer.resolve_conflict(
            field_name,
            primary_value,
            secondary_values
        )

        # Replace "primary" with actual primary name
        sources = [primary_name if s == "primary" else s for s in sources]

        return merged_value, sources

    def get_merged_dataset(self) -> Dict[str, Any]:
        """
        Get the merged D4D dataset.

        Returns:
            Dict with merged D4D Dataset data
        """
        return self.merged_data.copy()

    def get_provenance(self) -> Dict[str, List[str]]:
        """
        Get provenance information (which sources contributed to each field).

        Returns:
            Dict mapping field names to list of contributing source names
        """
        return self.provenance.copy()

    def get_merge_stats(self) -> Dict[str, int]:
        """
        Get merge statistics.

        Returns:
            Dict with merge statistics
        """
        return self.merge_stats.copy()

    def generate_merge_report(
        self,
        rocrate_parsers: List,
        source_names: Optional[List[str]] = None
    ) -> str:
        """
        Generate detailed merge report.

        Args:
            rocrate_parsers: List of ROCrateParser instances
            source_names: Optional list of source names

        Returns:
            Formatted merge report string
        """
        if source_names is None:
            source_names = [
                Path(parser.rocrate_path).name
                for parser in rocrate_parsers
            ]

        report = []
        report.append("="*80)
        report.append("Multi-RO-Crate Merge Report")
        report.append("="*80)
        report.append("")

        # Sources section
        report.append("SOURCES PROCESSED")
        report.append("-"*80)
        for i, (parser, name) in enumerate(zip(rocrate_parsers, source_names)):
            file_path = Path(parser.rocrate_path)
            file_size = file_path.stat().st_size if file_path.exists() else 0
            file_size_kb = file_size / 1024

            # Count fields this source contributed
            contributed_fields = sum(
                1 for field, sources in self.provenance.items()
                if name in sources or (i == self.primary_index and self.primary_name in sources)
            )

            marker = "(PRIMARY)" if i == self.primary_index else ""
            report.append(f"{i+1}. {name} {marker}")
            report.append(f"   - Size: {file_size_kb:.1f} KB")
            report.append(f"   - D4D fields contributed: {contributed_fields}")
            report.append("")

        # Merge statistics
        report.append("MERGE STATISTICS")
        report.append("-"*80)
        stats = self.merge_stats
        report.append(f"Total unique D4D fields: {stats['total_unique_fields']}")
        report.append(f"Fields from primary only: {stats['fields_from_primary']}")
        report.append(f"Fields from secondary sources: {stats['fields_from_secondary']}")
        report.append(f"Fields combined (descriptive): {stats['fields_combined']}")
        report.append(f"Fields merged as arrays: {stats['fields_merged_as_arrays']}")
        report.append("")

        # Field contributions by category
        report.append("FIELD CONTRIBUTIONS BY CATEGORY")
        report.append("-"*80)

        # Group fields by category
        categories = {}
        for field, sources in self.provenance.items():
            category = self.prioritizer.get_field_category(field)
            if category not in categories:
                categories[category] = []
            categories[category].append((field, sources))

        for category in sorted(categories.keys()):
            fields = categories[category]
            report.append(f"\n{category} ({len(fields)} fields):")
            for field, sources in sorted(fields):
                source_str = ", ".join(sources)
                report.append(f"  • {field}: {source_str}")

        # Footer
        report.append("")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("="*80)

        return "\n".join(report)

    def save_merge_report(
        self,
        output_path: Path,
        rocrate_parsers: List,
        source_names: Optional[List[str]] = None
    ):
        """
        Save merge report to file.

        Args:
            output_path: Path for report file
            rocrate_parsers: List of ROCrateParser instances
            source_names: Optional list of source names
        """
        report = self.generate_merge_report(rocrate_parsers, source_names)

        report_path = output_path.parent / f"{output_path.stem}_merge_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        if self.verbose:
            print(f"\n✓ Merge report saved: {report_path}")
