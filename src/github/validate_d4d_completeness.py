#!/usr/bin/env python3
"""
Validate D4D completeness before GitHub Assistant creates PRs.

This script checks D4D quality gates to prevent thin/incomplete datasheets
from being submitted as pull requests. Blocks PR creation if minimum quality
thresholds are not met.

Quality Levels:
- Comprehensive: 10+ sections, 146+ slots, 200+ lines
- Acceptable: 7+ sections, 100+ slots, 150+ lines
- Minimal: 4+ sections, 50+ slots, 100+ lines
- Insufficient: Below minimal thresholds (BLOCKS PR)

Exit Codes:
- 0: Comprehensive or acceptable quality (proceed with PR)
- 1: Minimal or insufficient quality (block PR)

Usage:
    # Check completeness before creating PR
    python src/github/validate_d4d_completeness.py data/sheets_d4dassistant/mydataset_d4d.yaml

    # With custom threshold
    python src/github/validate_d4d_completeness.py \
        --file data/sheets_d4dassistant/mydataset_d4d.yaml \
        --threshold acceptable

Author: Claude Code
Version: 1.0.0
Last Updated: 2025-02-10
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


# D4D section keys (main schema modules)
D4D_SECTIONS = [
    'motivation',
    'composition',
    'collection_process',
    'preprocessing',
    'uses',
    'distribution',
    'maintenance',
    'human_subjects',
    'ethics_and_data_protection',
    'data_governance'
]

# Required fields (always must be present)
REQUIRED_FIELDS = ['id', 'name']


class D4DCompletenessValidator:
    """
    Validator for D4D datasheet completeness.

    Checks quality gates to prevent thin datasheets from PR creation.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize validator.

        Args:
            config: Configuration dictionary with thresholds
        """
        self.config = config or {}
        validation_config = self.config.get('validation', {})

        # Load thresholds from config or use defaults
        self.thresholds = {
            'comprehensive': {
                'sections': validation_config.get('min_sections_comprehensive', 10),
                'slots': validation_config.get('min_slots_comprehensive', 146),
                'lines': validation_config.get('min_lines_comprehensive', 200)
            },
            'acceptable': {
                'sections': validation_config.get('min_sections_acceptable', 7),
                'slots': validation_config.get('min_slots_acceptable', 100),
                'lines': validation_config.get('min_lines_acceptable', 150)
            },
            'minimal': {
                'sections': validation_config.get('min_sections_minimal', 4),
                'slots': validation_config.get('min_slots_minimal', 50),
                'lines': validation_config.get('min_lines_minimal', 100)
            }
        }

        self.required_fields = validation_config.get('required_fields', REQUIRED_FIELDS)
        self.block_threshold = validation_config.get('block_threshold', 'minimal')

    def load_d4d_yaml(self, file_path: Path) -> Tuple[Dict, str]:
        """
        Load D4D YAML file.

        Args:
            file_path: Path to D4D YAML file

        Returns:
            Tuple of (data dict, raw content string)

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"D4D file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        data = yaml.safe_load(content)
        return data, content

    def count_populated_sections(self, data: Dict) -> Tuple[int, List[str]]:
        """
        Count populated D4D sections.

        Args:
            data: D4D data dictionary

        Returns:
            Tuple of (count, list of populated section names)
        """
        populated = []
        for section in D4D_SECTIONS:
            if section in data and data[section] is not None:
                # Check if section has actual content (not empty dict/list)
                section_data = data[section]
                if isinstance(section_data, dict):
                    if section_data:  # Non-empty dict
                        populated.append(section)
                elif isinstance(section_data, list):
                    if section_data:  # Non-empty list
                        populated.append(section)
                else:
                    # Scalar value (string, int, etc.)
                    populated.append(section)

        return len(populated), populated

    def count_populated_slots(self, data: Dict, prefix: str = "") -> int:
        """
        Count populated slots (non-null fields) recursively.

        Args:
            data: Data dictionary or value
            prefix: Prefix for nested keys (internal)

        Returns:
            Count of populated slots
        """
        if data is None:
            return 0

        if isinstance(data, dict):
            count = 0
            for key, value in data.items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        count += self.count_populated_slots(value, f"{prefix}{key}.")
                    else:
                        count += 1
            return count

        elif isinstance(data, list):
            count = 0
            for item in data:
                count += self.count_populated_slots(item, prefix)
            return count

        else:
            # Scalar value
            return 1

    def count_lines(self, content: str) -> int:
        """
        Count non-empty, non-comment lines.

        Args:
            content: File content string

        Returns:
            Line count
        """
        lines = content.split('\n')
        return sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))

    def check_required_fields(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Check if required fields are present.

        Args:
            data: D4D data dictionary

        Returns:
            Tuple of (all present?, list of missing fields)
        """
        missing = []
        for field in self.required_fields:
            if field not in data or data[field] is None:
                missing.append(field)

        return len(missing) == 0, missing

    def determine_quality_level(
        self,
        sections_count: int,
        slots_count: int,
        lines_count: int
    ) -> str:
        """
        Determine quality level based on counts.

        Args:
            sections_count: Number of populated sections
            slots_count: Number of populated slots
            lines_count: Number of non-empty lines

        Returns:
            Quality level: comprehensive, acceptable, minimal, or insufficient
        """
        # Check comprehensive threshold
        if (sections_count >= self.thresholds['comprehensive']['sections'] and
            slots_count >= self.thresholds['comprehensive']['slots'] and
            lines_count >= self.thresholds['comprehensive']['lines']):
            return 'comprehensive'

        # Check acceptable threshold
        if (sections_count >= self.thresholds['acceptable']['sections'] and
            slots_count >= self.thresholds['acceptable']['slots'] and
            lines_count >= self.thresholds['acceptable']['lines']):
            return 'acceptable'

        # Check minimal threshold
        if (sections_count >= self.thresholds['minimal']['sections'] and
            slots_count >= self.thresholds['minimal']['slots'] and
            lines_count >= self.thresholds['minimal']['lines']):
            return 'minimal'

        return 'insufficient'

    def should_block_pr(self, quality_level: str) -> bool:
        """
        Determine if PR creation should be blocked.

        Args:
            quality_level: Quality level string

        Returns:
            True if PR should be blocked
        """
        quality_order = ['insufficient', 'minimal', 'acceptable', 'comprehensive']
        if quality_level not in quality_order or self.block_threshold not in quality_order:
            return True  # Block if unknown quality level

        return quality_order.index(quality_level) < quality_order.index(self.block_threshold)

    def validate(self, file_path: Path) -> Dict:
        """
        Validate D4D completeness.

        Args:
            file_path: Path to D4D YAML file

        Returns:
            Validation result dictionary
        """
        try:
            # Load YAML
            data, content = self.load_d4d_yaml(file_path)

            # Check required fields
            required_ok, missing_required = self.check_required_fields(data)

            # Count metrics
            sections_count, populated_sections = self.count_populated_sections(data)
            slots_count = self.count_populated_slots(data)
            lines_count = self.count_lines(content)

            # Determine quality level
            quality_level = self.determine_quality_level(sections_count, slots_count, lines_count)

            # Check if PR should be blocked
            block_pr = self.should_block_pr(quality_level) or not required_ok

            return {
                'success': True,
                'file_path': str(file_path),
                'quality_level': quality_level,
                'block_pr': block_pr,
                'required_fields_ok': required_ok,
                'missing_required_fields': missing_required,
                'metrics': {
                    'sections_count': sections_count,
                    'sections_populated': populated_sections,
                    'slots_count': slots_count,
                    'lines_count': lines_count
                },
                'thresholds': self.thresholds,
                'block_threshold': self.block_threshold
            }

        except Exception as e:
            return {
                'success': False,
                'file_path': str(file_path),
                'error': str(e),
                'block_pr': True  # Block on error
            }

    def print_report(self, result: Dict) -> None:
        """
        Print validation report.

        Args:
            result: Validation result dictionary
        """
        if not result['success']:
            print(f"❌ Validation Error: {result['error']}")
            return

        quality = result['quality_level']
        metrics = result['metrics']

        # Quality emoji
        quality_emoji = {
            'comprehensive': '🌟',
            'acceptable': '✅',
            'minimal': '⚠️',
            'insufficient': '❌'
        }

        print(f"\n{quality_emoji.get(quality, '❓')} D4D Completeness Report")
        print(f"{'='*60}\n")

        print(f"File: {result['file_path']}")
        print(f"Quality Level: {quality.upper()}\n")

        print("📊 Metrics:")
        print(f"   Sections: {metrics['sections_count']}/{len(D4D_SECTIONS)} populated")
        print(f"   Slots: {metrics['slots_count']} populated")
        print(f"   Lines: {metrics['lines_count']} non-empty\n")

        print(f"🎯 Thresholds (Block threshold: {result['block_threshold']}):")
        for level, thresholds in result['thresholds'].items():
            marker = "→" if level == quality else " "
            print(f" {marker} {level.capitalize()}: "
                  f"{thresholds['sections']} sections, "
                  f"{thresholds['slots']} slots, "
                  f"{thresholds['lines']} lines")
        print()

        print("📋 Populated Sections:")
        for section in metrics['sections_populated']:
            print(f"   ✓ {section}")
        print()

        if not result['required_fields_ok']:
            print("❌ Required Fields Missing:")
            for field in result['missing_required_fields']:
                print(f"   ✗ {field}")
            print()

        if result['block_pr']:
            print("🚫 PR CREATION BLOCKED")
            print(f"   Reason: Quality level '{quality}' is below threshold '{result['block_threshold']}'")
            if not result['required_fields_ok']:
                print(f"   Also: Missing required fields: {', '.join(result['missing_required_fields'])}")
            print("\n   Please improve the datasheet quality before creating a PR.")
        else:
            print("✅ QUALITY CHECK PASSED")
            print(f"   Quality level '{quality}' meets threshold '{result['block_threshold']}'")
            print("   PR creation is allowed.")

        print()


def load_config() -> Dict:
    """
    Load configuration from deterministic config file.

    Returns:
        Configuration dictionary
    """
    config_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "d4d_assistant_deterministic.config"

    if not config_path.exists():
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate D4D completeness before PR creation"
    )
    parser.add_argument(
        "file",
        type=Path,
        nargs='?',
        help="Path to D4D YAML file"
    )
    parser.add_argument(
        "--file",
        dest="file_alt",
        type=Path,
        help="Path to D4D YAML file (alternative flag)"
    )
    parser.add_argument(
        "--threshold",
        choices=['comprehensive', 'acceptable', 'minimal', 'none'],
        help="Override block threshold from config"
    )
    parser.add_argument(
        "--quiet",
        action='store_true',
        help="Suppress output (only exit code)"
    )

    args = parser.parse_args()

    # Get file path from positional or flag argument
    file_path = args.file or args.file_alt
    if not file_path:
        parser.error("File path is required")

    # Load config
    config = load_config()

    # Override threshold if specified
    if args.threshold:
        config.setdefault('validation', {})['block_threshold'] = args.threshold

    # Initialize validator
    validator = D4DCompletenessValidator(config)

    # Validate
    result = validator.validate(file_path)

    # Print report unless quiet mode
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(1 if result['block_pr'] else 0)


if __name__ == "__main__":
    main()
