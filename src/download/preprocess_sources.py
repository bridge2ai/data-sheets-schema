#!/usr/bin/env python3
"""
Preprocess raw source documents into text-ready format for D4D generation.

Handles:
- .txt, .json, .md: Copy as-is (already text)
- .pdf: Extract text using pdfminer
- .html: Extract text using BeautifulSoup (if no .txt version exists)
- .docx: Extract text using python-docx
"""
import argparse
import json
import re
import shutil
from pathlib import Path
from pdfminer.high_level import extract_text
from bs4 import BeautifulSoup
from docx import Document
import yaml

from data_sheets_schema.constants import PROJECTS


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

        text = soup.get_text(separator="\n")
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        print(f"    ⚠️  Error extracting HTML {html_path.name}: {e}")
        return ""


def extract_docx_text(docx_path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        doc = Document(str(docx_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = '\t'.join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return '\n'.join(paragraphs)
    except Exception as e:
        print(f"    ⚠️  Error extracting DOCX {docx_path.name}: {e}")
        return ""


def load_source_manifest(manifest_path: Path) -> dict:
    """Load and minimally validate the canonical source manifest."""
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(
        manifest.get("projects"), dict
    ):
        raise ValueError(
            f"Invalid source manifest (missing projects mapping): {manifest_path}"
        )
    return manifest


def extract_source_text(source_path: Path) -> str:
    """Convert one supported raw source artifact to text."""
    suffix = source_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return source_path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".json":
        data = json.loads(source_path.read_text(encoding="utf-8"))
        return json.dumps(data, indent=2, ensure_ascii=False)
    if suffix == ".pdf":
        return extract_pdf_text(source_path)
    if suffix == ".html":
        return extract_html_text(source_path)
    if suffix == ".docx":
        return extract_docx_text(source_path)
    raise ValueError(f"Unsupported source format: {source_path}")


def normalize_extracted_text(text: str) -> str:
    """Normalize line endings and remove extractor-introduced trailing spaces."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in normalized.splitlines():
        cleaned = line.rstrip()
        cleaned = re.sub(r"^ +(?=\t)", "", cleaned)
        lines.append(cleaned)
    return "\n".join(lines).strip()


def preprocess_manifest(
    manifest_path: Path,
    input_dir: Path,
    output_dir: Path,
    projects=None,
) -> dict:
    """Build a canonical text-only processed set from a source manifest."""
    manifest = load_source_manifest(manifest_path)
    selected_projects = set(projects or manifest["projects"].keys())
    default_minimum = int(manifest.get("default_minimum_characters", 500))
    stats = {
        "processed": 0,
        "errors": 0,
        "projects": {},
    }

    unknown = selected_projects - set(manifest["projects"])
    if unknown:
        raise ValueError(
            f"Projects not present in {manifest_path}: {sorted(unknown)}"
        )

    for project, entries in manifest["projects"].items():
        if project not in selected_projects:
            continue
        if not isinstance(entries, list):
            raise ValueError(f"Manifest project {project} must contain a list")

        seen_ids = set()
        seen_outputs = set()
        project_stats = {"processed": 0, "errors": 0}
        destination_dir = output_dir / project
        destination_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📁 {project} ({len(entries)} canonical sources)")
        for entry in entries:
            source_id = entry.get("id")
            raw_name = entry.get("raw_file")
            processed_name = entry.get("processed_file")
            if not source_id or not raw_name or not processed_name:
                raise ValueError(
                    f"{project} manifest entries require id, raw_file, "
                    "and processed_file"
                )
            if source_id in seen_ids:
                raise ValueError(f"Duplicate source id for {project}: {source_id}")
            if processed_name in seen_outputs:
                raise ValueError(
                    f"Duplicate processed filename for {project}: {processed_name}"
                )
            if Path(processed_name).suffix.lower() != ".txt":
                raise ValueError(
                    f"Canonical processed output must be .txt: {processed_name}"
                )
            seen_ids.add(source_id)
            seen_outputs.add(processed_name)

            source_path = input_dir / project / raw_name
            destination_path = destination_dir / processed_name
            if not source_path.exists():
                print(f"    ❌ Missing raw source: {source_path}")
                project_stats["errors"] += 1
                stats["errors"] += 1
                continue

            try:
                text = normalize_extracted_text(
                    extract_source_text(source_path)
                )
                minimum = int(
                    entry.get("minimum_characters", default_minimum)
                )
                if len(text) < minimum:
                    raise ValueError(
                        f"extracted {len(text)} characters; minimum is {minimum}"
                    )

                metadata = [
                    "SOURCE METADATA",
                    f"Project: {project}",
                    f"Source ID: {source_id}",
                    f"Source type: {entry.get('source_type', '')}",
                    f"Source URL: {entry.get('url', '')}",
                    f"Raw file: {source_path}",
                ]
                # `curation_note` is deliberately NOT written here (#421).
                #
                # It is manifest metadata addressed to a curator, and putting it
                # in the bundle put it in front of the model instead. Two things
                # followed. It instructs — "prefer this over X where the two
                # disagree", "retain it only as evidence about the v2.0.0
                # release" — which is conflict-resolution guidance arriving
                # through the input rather than through the prompt condition.
                # And it asserts dataset facts: VOICE's note stated "published
                # 2026-05-01, 833 participants", so a record could take 833 from
                # the curator rather than from PhysioNet and still be scored
                # grounded, because the string was in the bundle.
                #
                # The volume was also unequal — six notes for AI_READI against
                # one for CHORUS — so the arm that is supposed to isolate what
                # the documents alone support gave different editorial support
                # per project.
                #
                # The notes remain in `source_manifest.yaml`, which is where the
                # reasoning belongs and where `d4d download audit-manifest`
                # reads it.
                # Neither is `verification_url` (#427). #421 stripped the notes
                # and left this behind, so curator-authored metadata was still
                # reaching the model: 7 lines across four of the five bundles,
                # unequally — three for AI_READI, none for CHORUS.
                #
                # It is the same kind of statement as the note. The URL is a
                # curator's record of where a capture was checked against
                # upstream, and it is not in the source document; a record can
                # cite it and still be scored grounded, because the string is in
                # the bundle. AI_READI's `10.60775/fairhub.4` reached four
                # values that way through the note (#424) — the mechanism is the
                # channel, not the field.
                #
                # `verification_url` stays in the manifest, which is where a
                # curator reads it and where `d4d download audit-manifest`
                # looks.
                metadata.extend(["-" * 80, ""])
                destination_path.write_text(
                    "\n".join(metadata) + text + "\n",
                    encoding="utf-8",
                )
                print(
                    f"    ✓ {raw_name} → {processed_name} "
                    f"({len(text):,} chars)"
                )
                project_stats["processed"] += 1
                stats["processed"] += 1
            except Exception as e:
                print(f"    ❌ {raw_name}: {e}")
                project_stats["errors"] += 1
                stats["errors"] += 1

        stats["projects"][project] = project_stats

    return stats


def preprocess_project(src_dir: Path, dst_dir: Path) -> dict:
    """Preprocess all files in a project directory."""
    stats = {"copied": 0, "pdf_extracted": 0, "html_extracted": 0, "docx_extracted": 0, "skipped": 0, "errors": 0}

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

        # Extract text from DOCX
        elif suffix == ".docx":
            txt_name = src_file.stem + ".txt"
            dst_file = dst_dir / txt_name

            print(f"    📝 DOCX: {src_file.name} → {txt_name}")
            text = extract_docx_text(src_file)

            if text.strip():
                dst_file.write_text(text, encoding="utf-8")
                stats["docx_extracted"] += 1
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
        default=PROJECTS,
        help="Projects to process (default: all)"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help=(
            "Canonical source manifest. When provided, only listed sources are "
            "processed and every output is normalized to .txt"
        ),
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Preprocessing Source Documents")
    print("=" * 60)
    print(f"Input:  {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print()

    total_stats = {"copied": 0, "pdf_extracted": 0, "html_extracted": 0, "docx_extracted": 0, "skipped": 0, "errors": 0}

    if args.manifest:
        manifest_stats = preprocess_manifest(
            args.manifest,
            args.input_dir,
            args.output_dir,
            args.projects,
        )
        print("\n" + "=" * 60)
        print("  Canonical Preprocessing Summary")
        print("=" * 60)
        print(f"  Processed: {manifest_stats['processed']} files")
        print(f"  Errors:    {manifest_stats['errors']} files")
        if manifest_stats["errors"]:
            raise SystemExit(1)
        print()
        print("✅ Canonical preprocessing complete!")
        return

    for project in args.projects:
        print(f"\n📁 {project}")
        src_dir = args.input_dir / project
        dst_dir = args.output_dir / project

        stats = preprocess_project(src_dir, dst_dir)

        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

        print(f"    Summary: {stats['copied']} copied, {stats['pdf_extracted']} PDFs, {stats['html_extracted']} HTMLs, {stats['docx_extracted']} DOCXs extracted")

    print("\n" + "=" * 60)
    print("  Total Summary")
    print("=" * 60)
    print(f"  Copied:         {total_stats['copied']} files (.txt, .json, .md)")
    print(f"  PDF extracted:  {total_stats['pdf_extracted']} files")
    print(f"  HTML extracted: {total_stats['html_extracted']} files")
    print(f"  DOCX extracted: {total_stats['docx_extracted']} files")
    print(f"  Skipped:        {total_stats['skipped']} files")
    print(f"  Errors:         {total_stats['errors']} files")
    print()
    print("✅ Preprocessing complete!")


if __name__ == "__main__":
    main()
