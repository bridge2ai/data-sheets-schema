#!/usr/bin/env python3
"""
Preprocess raw source documents into text-ready format for D4D generation.

Handles:
- .txt, .json, .md: Copy as-is (already text)
- .pdf: Extract text using pdfminer
- .html: Extract text using BeautifulSoup (if no .txt version exists)
"""
import argparse
import shutil
from pathlib import Path
from pdfminer.high_level import extract_text
from bs4 import BeautifulSoup


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using pdfminer."""
    try:
        text = extract_text(str(pdf_path))
        return text
    except Exception as e:
        print(f"    ⚠️  Error extracting PDF {pdf_path.name}: {e}")
        return ""


def extract_html_text(html_path: Path) -> str:
    """Extract text from HTML using BeautifulSoup."""
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # Remove scripts and styles
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        print(f"    ⚠️  Error extracting HTML {html_path.name}: {e}")
        return ""


def preprocess_project(src_dir: Path, dst_dir: Path) -> dict:
    """Preprocess all files in a project directory."""
    stats = {"copied": 0, "pdf_extracted": 0, "html_extracted": 0, "skipped": 0, "errors": 0}

    if not src_dir.exists():
        print(f"  ⚠️  Source directory not found: {src_dir}")
        return stats

    dst_dir.mkdir(parents=True, exist_ok=True)

    # First pass: collect which HTML files already have .txt versions
    txt_files = {f.stem for f in src_dir.glob("*.txt")}

    for src_file in src_dir.iterdir():
        if src_file.is_dir():
            continue

        suffix = src_file.suffix.lower()

        # Copy text-ready files
        if suffix in [".txt", ".json", ".md"]:
            dst_file = dst_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            print(f"    ✓ Copied: {src_file.name}")
            stats["copied"] += 1

        # Extract text from PDFs
        elif suffix == ".pdf":
            txt_name = src_file.stem + ".txt"
            dst_file = dst_dir / txt_name

            print(f"    📄 PDF: {src_file.name} → {txt_name}")
            text = extract_pdf_text(src_file)

            if text.strip():
                dst_file.write_text(text, encoding="utf-8")
                stats["pdf_extracted"] += 1
            else:
                print(f"    ⚠️  Empty extraction for {src_file.name}")
                stats["errors"] += 1

        # Extract text from HTML if no .txt version exists
        elif suffix == ".html":
            if src_file.stem in txt_files:
                stats["skipped"] += 1
                continue

            txt_name = src_file.stem + ".txt"
            dst_file = dst_dir / txt_name

            print(f"    🌐 HTML: {src_file.name} → {txt_name}")
            text = extract_html_text(src_file)

            # Only save if we got meaningful content (more than 100 chars)
            if len(text.strip()) > 100:
                dst_file.write_text(text, encoding="utf-8")
                stats["html_extracted"] += 1
            else:
                print(f"    ⚠️  Too little content ({len(text)} chars) - skipping")
                stats["skipped"] += 1
        else:
            stats["skipped"] += 1

    # Second pass: convert any PDFs in destination directory that don't have .txt versions
    # This handles PDFs that were copied in previous runs
    existing_txt = {f.stem for f in dst_dir.glob("*.txt")}
    for pdf_file in dst_dir.glob("*.pdf"):
        if pdf_file.stem in existing_txt:
            continue  # Already have text version

        txt_name = pdf_file.stem + ".txt"
        txt_file = dst_dir / txt_name

        print(f"    📄 PDF (existing): {pdf_file.name} → {txt_name}")
        text = extract_pdf_text(pdf_file)

        if text.strip():
            txt_file.write_text(text, encoding="utf-8")
            # Remove the PDF after successful extraction
            pdf_file.unlink()
            print(f"    🗑️  Removed: {pdf_file.name}")
            stats["pdf_extracted"] += 1
        else:
            print(f"    ⚠️  Empty extraction for {pdf_file.name}")
            stats["errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess raw source documents for D4D generation"
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=Path,
        default=Path("data/raw"),
        help="Input directory with raw downloads (default: data/raw)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("data/preprocessed/individual"),
        help="Output directory for preprocessed files (default: data/preprocessed/individual)"
    )
    parser.add_argument(
        "-p", "--projects",
        nargs="+",
        default=["AI_READI", "CHORUS", "CM4AI", "VOICE"],
        help="Projects to process (default: all)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Preprocessing Source Documents")
    print("=" * 60)
    print(f"Input:  {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print()

    total_stats = {"copied": 0, "pdf_extracted": 0, "html_extracted": 0, "skipped": 0, "errors": 0}

    for project in args.projects:
        print(f"\n📁 {project}")
        src_dir = args.input_dir / project
        dst_dir = args.output_dir / project

        stats = preprocess_project(src_dir, dst_dir)

        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

        print(f"    Summary: {stats['copied']} copied, {stats['pdf_extracted']} PDFs, {stats['html_extracted']} HTMLs extracted")

    print("\n" + "=" * 60)
    print("  Total Summary")
    print("=" * 60)
    print(f"  Copied:         {total_stats['copied']} files (.txt, .json, .md)")
    print(f"  PDF extracted:  {total_stats['pdf_extracted']} files")
    print(f"  HTML extracted: {total_stats['html_extracted']} files")
    print(f"  Skipped:        {total_stats['skipped']} files")
    print(f"  Errors:         {total_stats['errors']} files")
    print()
    print("✅ Preprocessing complete!")


if __name__ == "__main__":
    main()
