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


MOJIBAKE_SIGNATURE = "\u00e2\u0080"      # a-circumflex + C1 control: U+20xx double-decoded
#: The accent class (#875): A-tilde + a Latin-1 continuation byte, which is
#: what every U+00C0\u2013U+00FF letter becomes when UTF-8 is read as Latin-1.
ACCENT_MOJIBAKE = re.compile("\u00c3[\u0080-\u00bf]")
#: Occurrences before the accent class counts as the page's encoding rather
#: than a quoted example: a double-encoded page hits every accented letter.
ACCENT_MOJIBAKE_MIN = 2


def fix_mojibake(text: str) -> str:
    """Repair UTF-8-read-as-Latin-1 double encoding, conservatively (#872).

    A page served as UTF-8 but decoded as Latin-1 turns an em-dash into the
    three characters U+00E2 U+0080 U+0094; re-encoding as Latin-1 and
    decoding as UTF-8 restores the original. Applied only when the signature
    is present, the round trip succeeds, and it strictly removes the
    signature without introducing replacement characters - otherwise the
    text is returned unchanged. The repair happens at preprocess time so
    raw downloads stay the bytes we fetched.

    Scope, stated precisely (#874 review): the trigger is the em-dash-class
    signature only - a page whose double encoding hits only accented
    characters (e.g. \u00c3\u00a9 for e-acute, no smart punctuation) is NOT
    repaired (#875). The guard is per FILE: when the whole-text round trip
    fires, lines without the signature are rewritten too (that is the
    correct repair for a genuinely double-encoded page, and it is what
    fixed the CC language list). And the acceptance check is
    all-or-nothing: if any line is unrepairable, the whole text is returned
    unchanged rather than half-repaired.
    """
    # #875: the accent class (\u00c3 followed by a Latin-1 continuation byte \u2014
    # \u00e9 as U+00C3 U+00A9, \u00ee as U+00C3 U+00AE) has no smart-punctuation
    # signature to fire on. It counts as a signature when it recurs
    # (ACCENT_MOJIBAKE_MIN occurrences) \u2014 a page's double encoding hits
    # every accented letter, a text merely quoting one `\u00c3\u00a9` (the #874
    # guard) hits one \u2014 and the acceptance check then requires that every
    # accent-class sequence is gone too.
    accent_hits = len(ACCENT_MOJIBAKE.findall(text))
    fired = MOJIBAKE_SIGNATURE in text or accent_hits >= ACCENT_MOJIBAKE_MIN
    if not fired:
        return text

    def broken(s: str) -> bool:
        return MOJIBAKE_SIGNATURE in s or bool(ACCENT_MOJIBAKE.search(s))

    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        out = []
        for line in text.split("\n"):
            if broken(line):
                try:
                    line = line.encode("latin-1").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            out.append(line)
        repaired = "\n".join(out)
    if not broken(repaired) and "\ufffd" not in repaired:
        return repaired
    return text


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
            soup = BeautifulSoup(fix_mojibake(f.read()), 'html.parser')

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


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_paragraph_text(p) -> str:
    """Every `w:t` under a paragraph, in order — including runs wrapped in a
    `w:sdt` structured-document tag, which python-docx's `.text` skips
    (#886): a Google Docs export wrapped "The s" of "The study visit" in one,
    and the bundle read "tudy visit". Tabs and line breaks keep their place."""
    parts = []
    for node in p.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag == f"{_W}tab":
            parts.append("\t")
        elif node.tag in (f"{_W}br", f"{_W}cr"):
            parts.append("\n")
    return "".join(parts)


def _docx_children(el, *tags):
    """Direct children of `el` with one of `tags`, looking through `w:sdt`
    wrappers at that level: a structured-document tag may wrap a paragraph
    or table in the body, a row in a table, or a cell in a row (#921
    review — 195 of the AI_READI file's tags wrap cells, five of them the
    only ☒ answers on their rows). Direct children only: a nested table is
    reached through its cell's recursion, once, in place."""
    for child in el:
        if child.tag in tags:
            yield child
        elif child.tag == f"{_W}sdt":
            content = child.find(f"{_W}sdtContent")
            if content is not None:
                yield from _docx_children(content, *tags)


def _docx_block_texts(container) -> list:
    """Paragraphs and table rows under a container, in document order (the
    earlier extractor emitted every paragraph, then every table, whatever
    their order on the page), descending into `w:sdt` wrappers."""
    out = []
    for child in _docx_children(container, f"{_W}p", f"{_W}tbl"):
        if child.tag == f"{_W}p":
            text = _docx_paragraph_text(child)
            if text.strip():
                out.append(text)
        else:
            for row in _docx_children(child, f"{_W}tr"):
                cells = []
                for cell in _docx_children(row, f"{_W}tc"):
                    cell_text = "\n".join(t for t in _docx_block_texts(cell) if t.strip())
                    if cell_text.strip():
                        cells.append(cell_text.strip())
                if cells:
                    out.append("\t".join(cells))
    return out


def extract_docx_text(docx_path: Path) -> str:
    """Extract text from DOCX by walking the document XML in order."""
    try:
        doc = Document(str(docx_path))
        return "\n".join(_docx_block_texts(doc.element.body))
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


def _decode(path: Path) -> str:
    """Decode a downloaded file to text, tolerating non-UTF-8 sources.

    RFC 8259 requires UTF-8 for interchanged JSON, and publishers do not always
    comply: the AI-READI RO-Crate of 2026-08-12 is cp1252, carrying `©` as a
    single 0xA9 byte, and `read_text(encoding="utf-8")` raises on it at byte
    5096. A source that cannot be read is a source silently missing from the
    bundle, which is the failure worth avoiding.

    UTF-8 is tried first, so a well-formed file is never reinterpreted. cp1252
    is the fallback because it is what Windows-authored JSON usually is and it
    decodes every byte, so no character is lost — unlike `errors="ignore"`,
    which would delete the copyright symbol and leave no trace that it had.
    """
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Reported, not silent: the bundle is evidence, and a re-encoded source
        # should be visible to whoever reads the preprocessing log.
        print(f"    ! {path.name} is not UTF-8; decoded as cp1252")
        return raw.decode("cp1252")


def extract_source_text(source_path: Path) -> str:
    """Convert one supported raw source artifact to text."""
    suffix = source_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return fix_mojibake(source_path.read_text(encoding="utf-8", errors="ignore"))
    if suffix == ".json":
        data = json.loads(_decode(source_path))
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
            # Copied byte-for-byte when already UTF-8, so nothing that is
            # currently correct moves — re-encoding every text source would
            # rewrite mtimes across four projects and rehash bundles that have
            # no defect. Only a source that cannot be decoded as UTF-8 is
            # normalised, because the alternative is a bundle carrying bytes
            # the concatenator and every downstream reader will choke on.
            try:
                src_file.read_bytes().decode("utf-8")
                shutil.copy2(src_file, dst_file)
                print(f"    ✓ Copied: {src_file.name}")
            except UnicodeDecodeError:
                dst_file.write_text(_decode(src_file), encoding="utf-8")
                print(f"    ✓ Re-encoded to UTF-8: {src_file.name}")
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
