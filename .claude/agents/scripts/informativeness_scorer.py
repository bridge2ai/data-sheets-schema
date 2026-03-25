#!/usr/bin/env python3
"""
Informativeness Scorer - Rank RO-Crates by D4D value contribution.

This module scores and ranks multiple RO-Crate sources by their potential
to contribute useful information to a D4D datasheet.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class InformativenessScorer:
    """Score and rank RO-Crate sources by D4D informativeness."""

    def __init__(self):
        """Initialize informativeness scorer."""
        # Weights for different scoring dimensions
        self.weights = {
            'd4d_coverage': 0.4,      # 40% - How many D4D fields it can populate
            'unique_fields': 0.3,      # 30% - Fields not in other sources
            'metadata_richness': 0.2,  # 20% - Structured metadata quality
            'technical_completeness': 0.1  # 10% - Download URLs, checksums, etc.
        }

    def score_rocrate(
        self,
        rocrate_parser,
        mapping_loader,
        other_parsers: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Calculate informativeness score for a RO-Crate.

        Args:
            rocrate_parser: ROCrateParser instance to score
            mapping_loader: MappingLoader with field mappings
            other_parsers: List of other ROCrateParser instances for uniqueness calculation

        Returns:
            Score dict with breakdown:
            - d4d_coverage: int (# of D4D fields populatable)
            - unique_fields: int (# not in other sources)
            - metadata_richness: float (0-1)
            - technical_completeness: float (0-1)
            - total_score: float (weighted combination)
        """
        scores = {}

        # 1. D4D Coverage - how many fields can this RO-Crate populate?
        covered_fields = mapping_loader.get_covered_fields()
        populated_count = 0

        for d4d_field in covered_fields:
            rocrate_property = mapping_loader.get_rocrate_property(d4d_field)
            if not rocrate_property:
                continue

            # Try to extract value
            rocrate_props = [p.strip() for p in rocrate_property.split(',')]
            for rc_prop in rocrate_props:
                value = rocrate_parser.get_property(rc_prop)
                if value is not None:
                    populated_count += 1
                    break

        scores['d4d_coverage'] = populated_count
        coverage_normalized = populated_count / max(len(covered_fields), 1)

        # 2. Unique Fields - fields not in other sources
        unique_count = populated_count  # Default if no other parsers
        if other_parsers:
            unique_count = self._count_unique_fields(
                rocrate_parser,
                mapping_loader,
                other_parsers
            )

        scores['unique_fields'] = unique_count
        unique_normalized = unique_count / max(populated_count, 1)

        # 3. Metadata Richness - structured metadata quality
        richness = self._calculate_metadata_richness(rocrate_parser)
        scores['metadata_richness'] = richness

        # 4. Technical Completeness - download URLs, checksums, etc.
        completeness = self._calculate_technical_completeness(rocrate_parser)
        scores['technical_completeness'] = completeness

        # 5. Total Score (weighted combination)
        total_score = (
            coverage_normalized * self.weights['d4d_coverage'] +
            unique_normalized * self.weights['unique_fields'] +
            richness * self.weights['metadata_richness'] +
            completeness * self.weights['technical_completeness']
        )

        scores['total_score'] = total_score

        return scores

    def rank_rocrates(
        self,
        rocrate_parsers: List,
        mapping_loader
    ) -> List[Tuple[Any, Dict[str, Any], int]]:
        """
        Rank multiple RO-Crate parsers by informativeness.

        Args:
            rocrate_parsers: List of ROCrateParser instances
            mapping_loader: MappingLoader with field mappings

        Returns:
            List of (parser, scores, rank) tuples sorted by score descending
            rank is 1-indexed (1 = most informative)
        """
        scored = []

        for parser in rocrate_parsers:
            # Score with uniqueness calculated against other parsers
            other_parsers = [p for p in rocrate_parsers if p != parser]
            scores = self.score_rocrate(parser, mapping_loader, other_parsers)
            scored.append((parser, scores))

        # Sort by total_score descending
        scored.sort(key=lambda x: x[1]['total_score'], reverse=True)

        # Add ranks (1-indexed)
        ranked = [(parser, scores, idx + 1) for idx, (parser, scores) in enumerate(scored)]

        return ranked

    def _count_unique_fields(
        self,
        rocrate_parser,
        mapping_loader,
        other_parsers: List
    ) -> int:
        """Count fields unique to this RO-Crate vs others."""
        covered_fields = mapping_loader.get_covered_fields()
        unique_count = 0

        for d4d_field in covered_fields:
            rocrate_property = mapping_loader.get_rocrate_property(d4d_field)
            if not rocrate_property:
                continue

            # Check if this parser has the field
            rocrate_props = [p.strip() for p in rocrate_property.split(',')]
            has_field = False
            for rc_prop in rocrate_props:
                value = rocrate_parser.get_property(rc_prop)
                if value is not None:
                    has_field = True
                    break

            if not has_field:
                continue

            # Check if any other parser also has it
            is_unique = True
            for other_parser in other_parsers:
                for rc_prop in rocrate_props:
                    other_value = other_parser.get_property(rc_prop)
                    if other_value is not None:
                        is_unique = False
                        break
                if not is_unique:
                    break

            if is_unique:
                unique_count += 1

        return unique_count

    def _calculate_metadata_richness(self, rocrate_parser) -> float:
        """
        Calculate metadata richness score (0-1).

        Checks for:
        - additionalProperty array (structured metadata)
        - Person/Organization entities with detailed info
        - Provenance graphs
        - Rich descriptions
        """
        score = 0.0
        max_score = 4.0

        # Check for additionalProperty (25%)
        root = rocrate_parser.get_root_dataset()
        if root and 'additionalProperty' in root:
            additional_props = root['additionalProperty']
            if isinstance(additional_props, list) and len(additional_props) > 0:
                score += 1.0

        # Check for Person/Organization entities (25%)
        persons = rocrate_parser.get_entities_by_type('Person')
        orgs = rocrate_parser.get_entities_by_type('Organization')
        if len(persons) + len(orgs) > 0:
            score += 1.0

        # Check for provenance/workflow info (25%)
        has_provenance = False
        for prop in ['provenanceGraph', 'workflow', 'generatedBy', 'usedSoftware']:
            if rocrate_parser.get_property(prop) is not None:
                has_provenance = True
                break
        if has_provenance:
            score += 1.0

        # Check for rich description (25%)
        description = rocrate_parser.get_property('description')
        if description and len(str(description)) > 200:
            score += 1.0

        return score / max_score

    def _calculate_technical_completeness(self, rocrate_parser) -> float:
        """
        Calculate technical completeness score (0-1).

        Checks for:
        - Download URL/contentUrl
        - Checksums (md5, sha256)
        - Schema/format information
        - Size information
        """
        score = 0.0
        max_score = 4.0

        # Check for download URL (25%)
        for prop in ['contentUrl', 'downloadUrl', 'url']:
            if rocrate_parser.get_property(prop) is not None:
                score += 1.0
                break

        # Check for checksums (25%)
        has_checksum = False
        for prop in ['md5', 'sha256', 'hash']:
            if rocrate_parser.get_property(prop) is not None:
                has_checksum = True
                break
        if has_checksum:
            score += 1.0

        # Check for schema/format (25%)
        has_schema = False
        for prop in ['encodingFormat', 'format', 'schema', 'conformsTo']:
            if rocrate_parser.get_property(prop) is not None:
                has_schema = True
                break
        if has_schema:
            score += 1.0

        # Check for size information (25%)
        for prop in ['contentSize', 'size', 'bytes']:
            if rocrate_parser.get_property(prop) is not None:
                score += 1.0
                break

        return score / max_score

    def print_ranking_report(
        self,
        ranked_parsers: List[Tuple[Any, Dict[str, Any], int]]
    ):
        """Print human-readable ranking report."""
        print("="*80)
        print("RO-Crate Informativeness Ranking")
        print("="*80 + "\n")

        for parser, scores, rank in ranked_parsers:
            # Get source name from parser
            source_name = Path(parser.rocrate_path).name

            print(f"RANK {rank}: {source_name}")
            print("-"*80)
            print(f"  D4D Coverage:           {scores['d4d_coverage']:3d} fields")
            print(f"  Unique Fields:          {scores['unique_fields']:3d} fields")
            print(f"  Metadata Richness:      {scores['metadata_richness']:.2%}")
            print(f"  Technical Completeness: {scores['technical_completeness']:.2%}")
            print(f"  Total Score:            {scores['total_score']:.3f}")
            print()


if __name__ == "__main__":
    # Test the informativeness scorer
    import sys
    from pathlib import Path

    # Add parent directory to path to import other modules
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))

    from mapping_loader import MappingLoader
    from rocrate_parser import ROCrateParser

    if len(sys.argv) < 3:
        print("Usage: python informativeness_scorer.py <mapping_tsv> <rocrate1.json> [rocrate2.json] ...")
        print("\nExample:")
        print("  python informativeness_scorer.py \\")
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

    print("\nScoring RO-Crates...")
    scorer = InformativenessScorer()
    ranked = scorer.rank_rocrates(parsers, mapping)

    print()
    scorer.print_ranking_report(ranked)

    # Summary
    print("="*80)
    print("Recommendation")
    print("="*80)
    print(f"\nProcess RO-Crates in this order:")
    for parser, scores, rank in ranked:
        source_name = Path(parser.rocrate_path).name
        print(f"  {rank}. {source_name} (score: {scores['total_score']:.3f})")
