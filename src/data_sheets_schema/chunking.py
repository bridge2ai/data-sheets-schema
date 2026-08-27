"""Deterministic chunk manifests for input bundles (#707).

A receipt that says "chunk c007 was reviewed" is anchored to bytes only if
c007 is a pure function of the bundle and a recorded rule. This module is
that function: the same bundle bytes under the same rule produce the same
manifest, byte for byte, and the concatenation of every chunk's text is the
bundle again. Nothing here reads a model's output.

Chunks follow the source-document boundaries the concatenated bundle already
carries (`FILE:` headers, `concatenate_documents.py`), and a long document is
split into windows bounded in *both* lines and bytes. Lines alone do not
bound a read: the file-reading tool caps a response at roughly 25k tokens,
and a 400-line window of AI_READI is ~63k characters with single lines of
13k. The byte bound is what keeps a chunk readable in one call — the cap that
silently truncated the v5 agents' reads (#700).

The bundle's summary and table of contents, before the first `FILE:` line,
belong to no source document; they are their own chunk (`<preamble>`) rather
than nobody's, so a coverage receipt has one entry per byte of the bundle.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

CHUNKS_DIR = Path("data/preprocessed/chunks")
CONCAT_DIR = Path("data/preprocessed/concatenated")

#: The rule is data, recorded in every manifest and in the provenance record
#: (`inputs.chunks.rule`), so two manifests are comparable only when their
#: rules are equal. Change the rule → change `version`.
DEFAULT_RULE: dict[str, Any] = {
    "version": 1,
    "unit": "source-document",
    "boundary": "FILE: header line",
    "preamble": "own-chunk",
    "split": "line-window",
    "max_lines": 400,
    "max_bytes": 48_000,
}

PREAMBLE = "<preamble>"
FILE_MARK = "FILE: "


def _split_lines(text: str) -> tuple[list[str], bool]:
    """Lines without their newline, and whether the text ends with one.

    Kept separate from `str.splitlines` on purpose: that folds `\\r` and
    Unicode separators, and a chunk must reassemble to the exact bytes.
    """
    lines = text.split("\n")
    trailing = lines[-1] == ""
    if trailing:
        lines.pop()
    return lines, trailing


def _documents(lines: list[str]) -> list[tuple[str, int, int]]:
    """(source, first_line, last_line) per document, 1-based inclusive.

    A document runs from its `FILE:` line to the line before the next one, so
    the separator that follows its content belongs to it — deterministic,
    and it keeps the union of the documents equal to the bundle.
    """
    # A boundary is a `FILE:` line *followed by* a `PATH:` line, as the
    # concatenator writes them; a document quoting "FILE: …" at the start of a
    # line is content, not a boundary (#718).
    marks = [i for i, l in enumerate(lines)
             if l.startswith(FILE_MARK) and i + 1 < len(lines) and lines[i + 1].startswith("PATH: ")]
    docs: list[tuple[str, int, int]] = []
    if not marks:
        return [(PREAMBLE, 1, len(lines))] if lines else []
    if marks[0] > 0:
        docs.append((PREAMBLE, 1, marks[0]))
    for k, start in enumerate(marks):
        end = marks[k + 1] if k + 1 < len(marks) else len(lines)
        docs.append((lines[start][len(FILE_MARK):].strip(), start + 1, end))
    return docs


def _windows(lines: list[str], first: int, last: int, rule: dict[str, Any]) -> list[tuple[int, int]]:
    """Split lines[first-1:last] into windows under both bounds.

    Greedy: a window closes when adding the next line would exceed either
    bound. A single line larger than `max_bytes` cannot be split without
    breaking the "concatenation is the bundle" property at a line boundary,
    so it becomes a window of its own and is marked `oversize` by the caller.
    """
    max_lines, max_bytes = rule["max_lines"], rule["max_bytes"]
    out: list[tuple[int, int]] = []
    start, size = first, 0
    for i in range(first, last + 1):
        n = len(lines[i - 1].encode("utf-8")) + 1
        if i > start and (i - start + 1 > max_lines or size + n > max_bytes):
            out.append((start, i - 1))
            start, size = i, 0
        size += n
    out.append((start, last))
    return out


def chunk_text(text: str, rule: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The chunks of `text` under `rule` — a pure function of both."""
    rule = rule or DEFAULT_RULE
    lines, trailing = _split_lines(text)
    if not lines:
        return []
    chunks: list[dict[str, Any]] = []
    for source, first, last in _documents(lines):
        windows = _windows(lines, first, last, rule)
        for part, (a, b) in enumerate(windows, 1):
            seg = lines[a - 1:b]
            body = "\n".join(seg) + ("\n" if (b < len(lines) or trailing) else "")
            entry: dict[str, Any] = {
                "id": "",                       # assigned below, from the position
                "source": source,
                "lines": [a, b],
                "bytes": len(body.encode("utf-8")),
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            }
            if len(windows) > 1:
                entry["part"] = [part, len(windows)]
            if entry["bytes"] > rule["max_bytes"]:
                entry["oversize"] = True        # one line larger than the bound
            chunks.append(entry)
    width = max(3, len(str(len(chunks))))
    for i, c in enumerate(chunks, 1):
        c["id"] = f"c{i:0{width}d}"
    return chunks


def chunk_texts(text: str, chunks: list[dict[str, Any]]) -> list[str]:
    """The exact text of each chunk, in order — for the validator (#708)
    and for the reassembly test."""
    lines, trailing = _split_lines(text)
    out = []
    for c in chunks:
        a, b = c["lines"]
        out.append("\n".join(lines[a - 1:b]) + ("\n" if (b < len(lines) or trailing) else ""))
    return out


def build_manifest(bundle: Path, rule: dict[str, Any] | None = None) -> dict[str, Any]:
    rule = dict(rule or DEFAULT_RULE)
    raw = bundle.read_bytes()
    text = raw.decode("utf-8")
    chunks = chunk_text(text, rule)
    lines, _ = _split_lines(text)
    return {
        # The basename, not the path: the manifest must be the same bytes
        # wherever the bundle was read from (#713).
        "bundle": bundle.name,
        "bundle_md5": hashlib.md5(raw).hexdigest(),
        "bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "bundle_lines": len(lines),
        "bundle_bytes": len(raw),
        "rule": rule,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def manifest_path(project: str, chunks_dir: Path | None = None) -> Path:
    # Resolved at call time so a test (or a caller) can repoint the module dirs.
    return (chunks_dir or CHUNKS_DIR) / f"{project}_chunks.yaml"


def bundle_path(project: str, concat_dir: Path | None = None) -> Path:
    return (concat_dir or CONCAT_DIR) / f"{project}_preprocessed.txt"


def dump_manifest(manifest: dict[str, Any]) -> str:
    """Canonical text: same manifest → same bytes, so the file's sha256 is a
    receipt for the chunking and `--check` can compare bytes."""
    import yaml
    return yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=10_000)


def write_manifest(project: str, rule: dict[str, Any] | None = None,
                   concat_dir: Path | None = None, chunks_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    bundle = bundle_path(project, concat_dir)
    manifest = build_manifest(bundle, rule)
    out = manifest_path(project, chunks_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dump_manifest(manifest), encoding="utf-8")
    return out, manifest


def load_manifest(path: Path) -> dict[str, Any]:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_status(project: str, concat_dir: Path | None = None,
                    chunks_dir: Path | None = None) -> tuple[str, str]:
    """(status, detail) for a project's manifest on disk.

    `current` — rebuilding the bundle under the manifest's own recorded rule
    reproduces the file byte for byte. `stale` — it does not (the bundle
    changed, or the rule did). `missing` — no manifest. `no_bundle` — nothing
    to chunk. The rebuild uses the *recorded* rule, not the default, so a
    manifest made under an older rule is current as long as its bytes still
    match; whether the rule is the current default is a separate question the
    caller can ask.
    """
    bundle, path = bundle_path(project, concat_dir), manifest_path(project, chunks_dir)
    if not bundle.exists():
        return "no_bundle", str(bundle)
    if not path.exists():
        return "missing", f"d4d bundle chunk --project {project}"
    try:
        recorded = load_manifest(path)
        if not isinstance(recorded, dict):
            raise ValueError("manifest is not a mapping")
        fresh = build_manifest(bundle, recorded.get("rule") or DEFAULT_RULE)
    except (ValueError, UnicodeDecodeError, OSError) as exc:      # #715
        return "unreadable", f"{type(exc).__name__}: {exc}"
    if dump_manifest(fresh) != path.read_text(encoding="utf-8"):
        why = ("bundle md5 changed" if fresh["bundle_md5"] != recorded.get("bundle_md5")
               else "chunking differs under the recorded rule")
        return "stale", f"{why}; rebuild: d4d bundle chunk --project {project}"
    if recorded.get("rule") != DEFAULT_RULE:
        # Reproducible, but not the instrument every other manifest uses; a
        # receipt over these chunks is not comparable with the others (#714).
        return "off_rule", f"rule {recorded.get('rule')} is not the default; rebuild: d4d bundle chunk --project {project}"
    return "current", path.name


def chunks_input(bundle: Path | None, bundle_md5: str | None,
                 chunks_dir: Path | None = None) -> dict[str, Any] | None:
    """What a provenance record should carry under `inputs.chunks`.

    Returned only when a manifest exists for this bundle *and* it was built
    from the same bytes the record hashed — otherwise a receipt naming its
    chunk ids would be anchored to a different file. `None` means "no
    manifest attests this input", which the record states as such.
    """
    if bundle is None or bundle_md5 is None:
        return None
    name = bundle.name
    if not name.endswith("_preprocessed.txt"):
        return None
    path = manifest_path(name[: -len("_preprocessed.txt")], chunks_dir)
    if not path.exists():
        return None
    try:
        m = load_manifest(path)
        if not isinstance(m, dict) or m.get("bundle_md5") != bundle_md5:
            return None
        return {"path": str(path), "sha256": file_sha256(path),
                "rule": m.get("rule"), "chunk_count": m.get("chunk_count")}
    except Exception:                                               # noqa: BLE001
        # A broken manifest must not abort a live provenance record (#715);
        # "no manifest attests this input" is the true statement then.
        return None
