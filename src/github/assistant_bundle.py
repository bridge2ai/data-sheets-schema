#!/usr/bin/env python3
"""Prepare every document in an assistant input directory before generation.

This manifest describes ingestion, not the runner's source/chunk manifest.
No D4D application, provider, URL fetch or schema is used here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import stat
import sys


NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
COMMIT = re.compile(r"[0-9a-f]{40}")
TEXT_FORMATS = {".txt", ".md", ".json", ".html"}
PDFMINER_VERSION = "20221105"


class PreparationError(ValueError):
    """A complete bundle could not be prepared; generation must not start."""


def _stable(info):
    # Reading may update atime; it must not invalidate an unchanged source.
    return tuple(getattr(info, key) for key in (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns"))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _read(path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise PreparationError("input is not a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if _stable(os.fstat(stream.fileno())) != _stable(before):
            raise PreparationError("input changed before read")
        raw = stream.read()
        if _stable(os.fstat(stream.fileno())) != _stable(before):
            raise PreparationError("input changed during read")
    if _stable(path.lstat()) != _stable(before) or len(raw) != before.st_size:
        raise PreparationError("input changed during read")
    return raw, _stable(before)


def _members(directory):
    found = []

    def visit(parent):
        with os.scandir(parent) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(directory).as_posix()
                try:
                    relative.encode("utf-8", errors="strict")
                except UnicodeError as exc:
                    raise PreparationError("input filename is not UTF-8") from exc
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    visit(path)
                elif stat.S_ISREG(info.st_mode):
                    found.append(relative)
                else:
                    raise PreparationError("nonregular input: " + _json(relative))

    visit(directory)
    return sorted(found)


def _pdf(raw):
    import pdfminer
    from pdfminer.high_level import extract_text
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfparser import PDFParser

    version = importlib.metadata.version("pdfminer.six")
    if version != PDFMINER_VERSION or pdfminer.__version__ != version:
        raise PreparationError("unreviewed pdfminer converter version")
    document = PDFDocument(PDFParser(io.BytesIO(raw)), password="")
    if document.encryption is not None or not document.is_extractable:
        raise PreparationError("encrypted or extraction-prohibited PDF")
    text = extract_text(io.BytesIO(raw), password="", maxpages=0)
    if not text.strip():
        raise PreparationError("PDF has no extractable text (OCR is not performed)")
    return text.encode("utf-8", errors="strict"), {
        "kind": "pdf-text-only", "package": "pdfminer.six", "version": version,
        "policy": "all-pages; no OCR or layout-completeness claim",
    }


def _convert(raw, suffix):
    if suffix in TEXT_FORMATS:
        # Decode to validate, then retain the bytes, including BOM and CRLF.
        raw.decode("utf-8", errors="strict")
        return raw, {"kind": "verbatim-text", "encoding": "utf-8"}
    if suffix == ".pdf":
        return _pdf(raw)
    raise PreparationError("unsupported format; supported: .txt .md .json .html .pdf")


def prepare(inputs_root, dataset, output_dir, source_commit):
    """Return complete bundle/manifest bytes after fresh input checks.

    The caller publishes only this successful result. No cross-call cache or
    previously prepared authority is used. This is a stable-checkout check,
    not an atomic filesystem snapshot against arbitrary concurrent mutation.
    """
    if NAME.fullmatch(dataset) is None or COMMIT.fullmatch(source_commit) is None:
        raise PreparationError("invalid dataset name or source commit")
    root = Path(inputs_root)
    directory = root / dataset
    if root.is_symlink() or directory.is_symlink() or not directory.is_dir():
        raise PreparationError("dataset must be a real directory under inputs-root")
    root, directory = root.resolve(), directory.resolve()
    if directory.parent != root:
        raise PreparationError("dataset escapes inputs-root")
    out = Path(output_dir)
    if out.is_symlink() or not out.is_dir() or any(out.iterdir()):
        raise PreparationError("output directory must be fresh and empty")
    out = out.resolve()
    if out == root or root in out.parents:
        raise PreparationError("output directory must be outside the input tree")
    try:
        input_name = directory.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError as exc:
        raise PreparationError("input directory must be under the checkout cwd") from exc
    names = _members(directory)
    if not names:
        raise PreparationError("input directory contains no documents")
    bundle = bytearray(b"# D4D assistant complete input bundle v1\n")
    records, captured = [], {}
    has_text = False
    for ordinal, relative in enumerate(names, 1):
        path = directory / relative
        try:
            raw, identity = _read(path)
            suffix = path.suffix.lower()
            content, conversion = _convert(raw, suffix)
        except Exception as exc:
            reason = str(exc) if isinstance(exc, PreparationError) else type(exc).__name__
            raise PreparationError("cannot prepare " + _json(relative) + ": " + reason) from exc
        has_text = has_text or bool(content.decode("utf-8").strip())
        header = ("\n# Source " + str(ordinal) + ": " + _json(relative)
                  + "\n# Format: " + suffix + "; " + conversion["kind"] + "\n\n")
        bundle.extend(header.encode("utf-8"))
        start = len(bundle)
        bundle.extend(content)
        end = len(bundle)
        bundle.extend(b"\n# End source\n")
        records.append({"path": relative, "format": suffix,
                        "raw_bytes": len(raw), "raw_sha256": _sha(raw),
                        "conversion": conversion, "content_bytes": len(content),
                        "content_sha256": _sha(content),
                        "content_start": start, "content_end": end})
        captured[relative] = (identity, _sha(raw))
    if not has_text:
        raise PreparationError("input directory has no non-whitespace document text")
    if _members(directory) != names:
        raise PreparationError("input membership changed during preparation")
    for relative in names:
        raw, identity = _read(directory / relative)
        if (identity, _sha(raw)) != captured[relative]:
            raise PreparationError("input changed during preparation: " + _json(relative))
    raw_bundle = bytes(bundle)
    manifest = {
        "format": "d4d-assistant-input-manifest-v1", "dataset": dataset,
        "source_commit": source_commit, "input_directory": input_name,
        "members": records,
        "bundle": {"format": "d4d-assistant-input-bundle-v1",
                   "bytes": len(raw_bundle), "sha256": _sha(raw_bundle)},
    }
    return raw_bundle, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-root", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args(argv)
    try:
        out = Path(args.output_dir).absolute()
        if any(c in str(out) for c in "\r\n"):
            raise PreparationError("output path cannot contain line breaks")
        bundle, manifest = prepare(args.inputs_root, args.dataset, out, args.source_commit)
        with (out / "bundle.txt").open("xb") as stream:
            stream.write(bundle)
        with (out / "input_manifest.json").open("xb") as stream:
            stream.write((_json(manifest) + "\n").encode("utf-8"))
        outputs = (f"bundle={out / 'bundle.txt'}\n"
                   f"input-manifest={out / 'input_manifest.json'}\n"
                   f"member-count={len(manifest['members'])}\n"
                   f"bundle-sha256={manifest['bundle']['sha256']}\n")
        with Path(args.github_output).open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(outputs)
        print(f"Prepared {len(manifest['members'])} documents; {len(bundle)} bundle bytes; "
              f"sha256 {manifest['bundle']['sha256']}")
        return 0
    except Exception as exc:
        # Do not emit PDF/parser payloads. A failed resolve step never admits
        # generation, even if an output write failed after a partial write.
        reason = str(exc) if isinstance(exc, PreparationError) else type(exc).__name__
        print("Complete-input preparation failed: " + reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
