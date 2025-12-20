#!/usr/bin/env python3
"""
Validate preprocessing quality: check for empty files, stub extractions,
and significant text volume loss.

This script compares raw source files against preprocessed outputs to detect:
- Empty or near-empty extractions
- Stub files (only headers/navigation)
- Significant text volume loss
- Missing expected outputs
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class FileQuality:
    """Quality metrics for a preprocessed file."""
    raw_file: Path
    preprocessed_file: Path
    raw_size: int
    preprocessed_size: int
    size_ratio: float
    char_count: int
    line_count: int
    is_empty: bool
    is_stub: bool
    is_problematic: bool
    issue: str = ""


def get_file_size(path: Path) -> int:
    """Get file size in bytes, return 0 if file doesn't exist."""
    return path.stat().st_size if path.exists() else 0


def count_text_content(path: Path) -> Tuple[int, int]:
    """Count characters and lines in text file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return len(content), len(content.splitlines())
    except Exception:
        return 0, 0


def is_stub_content(path: Path, min_chars: int = 500) -> bool:
    """
    Check if file appears to be a stub extraction.

    Stub indicators:
    - Less than min_chars characters
    - Only navigation/header content (Google Docs, etc.)
    - No substantial paragraphs
    """
    if not path.exists():
        return False

    char_count, line_count = count_text_content(path)

    if char_count < min_chars:
        return True

    # Check for Google Docs stub indicators
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()

        stub_indicators = [
            'google docs',
            'sign in',
            'file edit view tools help',
            'unsaved changes to drive',
            'tab  external'
        ]

        # If file is small and has stub indicators
        if char_count < 1000 and any(indicator in content for indicator in stub_indicators):
            return True
    except Exception:
        pass

    return False


def validate_file(raw_file: Path, preprocessed_file: Path,
                 min_ratio: float = 0.01, min_chars: int = 500) -> FileQuality:
    """
    Validate a single preprocessed file against its raw source.

    Args:
        raw_file: Original source file (PDF, HTML, etc.)
        preprocessed_file: Preprocessed text file
        min_ratio: Minimum acceptable ratio of preprocessed/raw size
        min_chars: Minimum character count for non-stub files
    """
    raw_size = get_file_size(raw_file)
    preprocessed_size = get_file_size(preprocessed_file)

    # Calculate size ratio (handle zero division)
    size_ratio = preprocessed_size / raw_size if raw_size > 0 else 0.0

    char_count, line_count = count_text_content(preprocessed_file)

    # Quality checks
    is_empty = char_count == 0
    is_stub = is_stub_content(preprocessed_file, min_chars)

    # Determine if problematic
    is_problematic = False
    issue = ""

    if is_empty:
        is_problematic = True
        issue = "Empty extraction"
    elif is_stub:
        is_problematic = True
        issue = f"Stub file ({char_count} chars)"
    elif raw_file.suffix.lower() in ['.pdf', '.html'] and size_ratio < min_ratio:
        is_problematic = True
        issue = f"Significant data loss ({size_ratio:.1%} retained)"

    return FileQuality(
        raw_file=raw_file,
        preprocessed_file=preprocessed_file,
        raw_size=raw_size,
        preprocessed_size=preprocessed_size,
        size_ratio=size_ratio,
        char_count=char_count,
        line_count=line_count,
        is_empty=is_empty,
        is_stub=is_stub,
        is_problematic=is_problematic,
        issue=issue
    )


def validate_project(raw_dir: Path, preprocessed_dir: Path,
                     project: str, min_ratio: float = 0.01) -> Dict:
    """Validate all preprocessed files for a project."""

    if not raw_dir.exists():
        return {"error": f"Raw directory not found: {raw_dir}"}

    if not preprocessed_dir.exists():
        return {"error": f"Preprocessed directory not found: {preprocessed_dir}"}

    results = {
        "project": project,
        "files_checked": 0,
        "problematic_files": 0,
        "empty_files": 0,
        "stub_files": 0,
        "low_extraction_rate": 0,
        "missing_outputs": 0,
        "quality_reports": []
    }

    # Find all raw source files that should have been preprocessed
    raw_files = list(raw_dir.glob("*.pdf")) + list(raw_dir.glob("*.html"))

    for raw_file in raw_files:
        # Determine expected preprocessed file
        expected_txt = preprocessed_dir / f"{raw_file.stem}.txt"

        # Check if output exists
        if not expected_txt.exists():
            results["missing_outputs"] += 1
            results["quality_reports"].append({
                "raw_file": raw_file.name,
                "issue": "Missing preprocessed output",
                "raw_size": get_file_size(raw_file),
                "status": "missing"
            })
            continue

        # Validate quality
        quality = validate_file(raw_file, expected_txt, min_ratio)
        results["files_checked"] += 1

        if quality.is_problematic:
            results["problematic_files"] += 1

            if quality.is_empty:
                results["empty_files"] += 1
            elif quality.is_stub:
                results["stub_files"] += 1
            else:
                results["low_extraction_rate"] += 1

            results["quality_reports"].append({
                "raw_file": raw_file.name,
                "preprocessed_file": expected_txt.name,
                "raw_size": quality.raw_size,
                "preprocessed_size": quality.preprocessed_size,
                "char_count": quality.char_count,
                "line_count": quality.line_count,
                "size_ratio": f"{quality.size_ratio:.1%}",
                "issue": quality.issue,
                "status": "problematic"
            })

    return results


def format_size(bytes_size: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f}TB"


def print_report(results: Dict):
    """Print formatted quality report."""
    print(f"\n📁 {results['project']}")
    print("=" * 60)

    if "error" in results:
        print(f"  ❌ {results['error']}")
        return

    total_checked = results["files_checked"] + results["missing_outputs"]
    print(f"  Total files:        {total_checked}")
    print(f"  Files checked:      {results['files_checked']}")
    print(f"  Problematic:        {results['problematic_files']}")
    print(f"    - Empty:          {results['empty_files']}")
    print(f"    - Stub:           {results['stub_files']}")
    print(f"    - Low extraction: {results['low_extraction_rate']}")
    print(f"  Missing outputs:    {results['missing_outputs']}")

    if results["problematic_files"] > 0 or results["missing_outputs"] > 0:
        print("\n  ⚠️  Issues Found:")
        for report in results["quality_reports"]:
            if report["status"] == "missing":
                print(f"    • {report['raw_file']} ({format_size(report['raw_size'])}) - {report['issue']}")
            else:
                print(f"    • {report['raw_file']} ({format_size(report['raw_size'])}) → "
                      f"{format_size(report['preprocessed_size'])} ({report['size_ratio']}) - {report['issue']}")
    else:
        print("  ✅ All files passed quality checks")


def main():
    parser = argparse.ArgumentParser(
        description="Validate preprocessing quality for D4D source documents"
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory with raw downloads (default: data/raw)"
    )
    parser.add_argument(
        "--preprocessed-dir",
        type=Path,
        default=Path("data/preprocessed/individual"),
        help="Directory with preprocessed files (default: data/preprocessed/individual)"
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        default=["AI_READI", "CHORUS", "CM4AI", "VOICE"],
        help="Projects to validate (default: all)"
    )
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=0.01,
        help="Minimum acceptable ratio of preprocessed/raw size (default: 0.01 = 1%%)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Preprocessing Quality Validation")
    print("=" * 60)
    print(f"Raw directory:         {args.raw_dir}")
    print(f"Preprocessed directory: {args.preprocessed_dir}")
    print(f"Min extraction ratio:  {args.min_ratio:.1%}")

    all_results = []
    total_issues = 0

    for project in args.projects:
        raw_dir = args.raw_dir / project
        preprocessed_dir = args.preprocessed_dir / project

        results = validate_project(raw_dir, preprocessed_dir, project, args.min_ratio)
        all_results.append(results)

        if not args.json:
            print_report(results)

        total_issues += results.get("problematic_files", 0) + results.get("missing_outputs", 0)

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)

        total_checked = sum(r.get("files_checked", 0) for r in all_results)
        total_problematic = sum(r.get("problematic_files", 0) for r in all_results)
        total_missing = sum(r.get("missing_outputs", 0) for r in all_results)

        print(f"  Total files checked: {total_checked}")
        print(f"  Problematic files:   {total_problematic}")
        print(f"  Missing outputs:     {total_missing}")

        if total_issues == 0:
            print("\n✅ All preprocessing quality checks passed!")
        else:
            print(f"\n⚠️  {total_issues} issues found - review above for details")
            print("\nRecommendations:")
            print("  1. Check Google Docs URLs - may need direct download links")
            print("  2. Verify PDFs are not scanned images (need OCR)")
            print("  3. Review HTML extraction for JavaScript-rendered content")
            print("  4. Re-run preprocessing with updated sources if needed")


if __name__ == "__main__":
    main()
