#!/usr/bin/env python3
"""
RO-Crate Merger - Merge multiple RO-Crates into single D4D datasheet.

This module intelligently merges data from multiple related RO-Crate files
(e.g., parent + children) into a comprehensive D4D dataset.
"""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from field_prioritizer import FieldPrioritizer, MergeStrategy
from d4d_builder import D4DBuilder

from data_sheets_schema.legacy_creators import (
    creator_route, author_source_presence, merge_creator_values,
    source_presence_lines, creator_assertion_lines,
)

from data_sheets_schema.legacy_creator_references import reference_evidence, reference_lines

from data_sheets_schema.legacy_root_identity import (
    root_identity_route, merge_identity_evidence, identity_report_lines,
)


class ROCrateMerger:
    """Merge multiple RO-Crate sources into single D4D dataset."""

    def __init__(self, mapping_loader):
        """
        Initialize merger with field mapping.

        Args:
            mapping_loader: MappingLoader instance with field mappings
        """
        self.mapping = mapping_loader
        self.root_identity_sources = None
        self.source_presence = None
        self.creator_assertion_sources = None
        self.creator_reference_construction = None
        self.primary_index = 0
        self.primary_name = ""
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

        marked_creators = creator_route(self.mapping)
        if marked_creators and (type(primary_index) is not int
                                or not 0 <= primary_index < len(rocrate_parsers)):
            raise ValueError('Marked Creator primary_index must be an integer in the selected source range')

        if primary_index >= len(rocrate_parsers):
            raise ValueError(f"Primary index {primary_index} out of range")

        # Refuse the entire batch before changing state or building a source.
        for parser in rocrate_parsers:
            parser.require_root_dataset()

        marked_id = root_identity_route(self.mapping)
        if source_names is None:
            source_names = [Path(parser.rocrate_path).name.replace(
                '-ro-crate-metadata.json', '') for parser in rocrate_parsers]
        if len(source_names) != len(rocrate_parsers):
            raise ValueError('source_names must match the selected RO-Crates')
        presence = author_source_presence(
            self.mapping, rocrate_parsers, source_names, primary_index)
        identity_sources = (merge_identity_evidence(
            rocrate_parsers, source_names, primary_index) if marked_id else None)
        if (marked_id or self.root_identity_sources is not None
                or marked_creators or self.creator_assertion_sources is not None):
            # Marked construction and transitions back to custom mappings must
            # not inherit earlier assertion units, identities or statistics.
            self.merged_data = {}
            self.provenance = {}
            self.merge_stats = {key: 0 for key in self.merge_stats}
        self.root_identity_sources = identity_sources
        self.source_presence = presence
        self.creator_assertion_sources = None
        self.creator_reference_construction = None

        self.merge_stats['total_sources'] = len(rocrate_parsers)

        # Get source names
        if source_names is None:
            source_names = [
                Path(parser.rocrate_path).name.replace('-ro-crate-metadata.json', '')
                for parser in rocrate_parsers
            ]

        primary_parser = rocrate_parsers[primary_index]
        primary_name = source_names[primary_index]
        self.primary_index = primary_index
        self.primary_name = primary_name

        secondary_parsers = [
            (parser, name) for i, (parser, name) in enumerate(zip(rocrate_parsers, source_names))
            if i != primary_index
        ]

        print(f"\nMerging {len(rocrate_parsers)} RO-Crate sources...")
        print(f"Primary: {primary_name}")
        for _, name in secondary_parsers:
            print(f"Secondary: {name}")

        # Get all covered D4D fields
        covered_fields = self.mapping.get_covered_fields()

        # Build D4D from each source
        print(f"\nBuilding D4D from each source...")
        primary_builder = D4DBuilder(self.mapping)
        primary_data = primary_builder.build_dataset(primary_parser)

        constructions = [primary_builder.get_creator_reference_construction()]
        secondary_data = []
        for parser, name in secondary_parsers:
            builder = D4DBuilder(self.mapping)
            data = builder.build_dataset(parser)
            secondary_data.append((data, name))
            constructions.append(builder.get_creator_reference_construction())

        if marked_creators:
            creator_merged, creator_sources, self.creator_assertion_sources = merge_creator_values(
                presence, [primary_data.get('creators')]
                + [data.get('creators') for data, _ in secondary_data])
            self.creator_reference_construction = reference_evidence(presence, constructions)

        # Merge field by field
        print(f"\nMerging fields...")
        for field_name in covered_fields:
            primary_value = primary_data.get(field_name)
            secondary_values = [
                (data.get(field_name), name)
                for data, name in secondary_data
            ]

            # Merge this field
            if marked_creators and field_name == 'creators':
                merged_value, sources = creator_merged, creator_sources
            elif marked_id and field_name == 'id':
                merged_value = primary_value
                sources = [primary_name] if primary_value is not None else []
            else:
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

    def get_creator_reference_construction(self):
        """Return the complete detached per-source reference evidence."""
        return deepcopy(self.creator_reference_construction)

    def get_source_presence(self):
        """Return detached raw source measurements, independent of provenance flags."""
        return deepcopy(self.source_presence)

    def get_creator_assertion_sources(self):
        """Return detached marked construction ranges; custom merges return None."""
        return deepcopy(self.creator_assertion_sources)

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
            report.append(f"   - Constructed Dataset fields contributed: {contributed_fields}")
            report.append("")

        report.extend(identity_report_lines(self.root_identity_sources))
        report.extend(source_presence_lines(self.source_presence))
        report.extend(creator_assertion_lines(self.creator_assertion_sources))
        report.extend(reference_lines(self.creator_reference_construction))

        # Merge statistics
        report.append("MERGE STATISTICS")
        report.append("-"*80)
        stats = self.merge_stats
        report.append(f"Total constructed Dataset fields: {stats['total_unique_fields']}")
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
        from data_sheets_schema.legacy_publication import prepare_dataset, publish
        report_path = output_path.parent / f"{output_path.stem}_merge_report.txt"
        prepare_dataset(self.merged_data, context=f"Merge report output {report_path}")
        report = self.generate_merge_report(rocrate_parsers, source_names)
        publish([(report_path, report.encode("utf-8"))],
                protected=[self.mapping.tsv_path, *(p.rocrate_path for p in rocrate_parsers)])

        print(f"\n✓ Merge report saved: {report_path}")


if __name__ == "__main__":
    # Test the RO-Crate merger
    import sys
    from pathlib import Path

    # Add parent directory to path to import other modules
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))

    from mapping_loader import MappingLoader
    from rocrate_parser import ROCrateParser

    if len(sys.argv) < 3:
        print("Usage: python rocrate_merger.py <mapping_tsv> <rocrate1.json> <rocrate2.json> [rocrate3.json ...]")
        print("\nExample:")
        print("  python rocrate_merger.py \\")
        print("    data/ro-crate_mapping/mapping.tsv \\")
        print("    data/ro-crate/CM4AI/release-ro-crate-metadata.json \\")
        print("    data/ro-crate/CM4AI/mass-spec-iPSCs-ro-crate-metadata.json \\")
        print("    data/ro-crate/CM4AI/mass-spec-cancer-cells-ro-crate-metadata.json")
        sys.exit(1)

    mapping_path = sys.argv[1]
    rocrate_paths = sys.argv[2:]

    print(f"\nLoading mapping from: {mapping_path}")
    mapping = MappingLoader(mapping_path)

    print(f"\nLoading {len(rocrate_paths)} RO-Crate files...")
    parsers = []
    for path in rocrate_paths:
        print(f"  - {Path(path).name}")
        parsers.append(ROCrateParser(path))

    print("\nMerging RO-Crates...")
    merger = ROCrateMerger(mapping)
    dataset = merger.merge_rocrates(parsers, primary_index=0)

    print("\n" + "="*80)
    print("Merge Report")
    print("="*80)
    print(merger.generate_merge_report(parsers))

    print("\n" + "="*80)
    print(f"Merged dataset has {len(dataset)} fields")
    print("="*80)
