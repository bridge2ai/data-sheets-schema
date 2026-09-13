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
    "version": 2,
    "unit": "source-document",
    "boundary": "FILE: line followed by PATH: or ROLE:",
    "preamble": "own-chunk",
    "split": "line-window",
    "max_lines": 400,
    "max_bytes": 48_000,
}

PREAMBLE = "<preamble>"
#: A bundle with no `FILE:` boundaries at all (the healthsheet bundles) is
#: one unsegmented document, windowed like any other (#725).
UNSEGMENTED = "<unsegmented>"
FILE_MARK = "FILE: "
#: Every bundle kind a run may declare, by name suffix. Manifests are built
#: for all of them, not only the document bundle (#725).
BUNDLE_SUFFIXES = ("_preprocessed.txt", "_preprocessed_with_crate.txt",
                   "_crate_only.txt", "_healthsheet_only.txt")


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
    # concatenator writes them, or by a `ROLE:` line, as the crate bundler
    # writes its evidence sections (#745); a document quoting "FILE: …" at
    # the start of a line is content, not a boundary (#718).
    marks = [i for i, l in enumerate(lines)
             if l.startswith(FILE_MARK) and i + 1 < len(lines)
             and lines[i + 1].startswith(("PATH: ", "ROLE: "))]
    docs: list[tuple[str, int, int]] = []
    if not marks:
        return [(UNSEGMENTED, 1, len(lines))] if lines else []
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
    return manifest_from_bytes(bundle.read_bytes(), canonical_name(bundle), rule)


def manifest_from_bytes(raw: bytes, name: str, rule: dict[str, Any] | None = None) -> dict[str, Any]:
    """`build_manifest` over bytes that are not on disk (#1140): the version
    of a bundle a record read, recovered from git after the path drifted.
    Same bytes + same rule = the same manifest the run would have chunked."""
    rule = dict(rule or DEFAULT_RULE)
    text = raw.decode("utf-8")
    chunks = chunk_text(text, rule)
    lines, _ = _split_lines(text)
    return {
        # The basename, not the path: the manifest must be the same bytes
        # wherever the bundle was read from (#713).
        "bundle": name,
        "bundle_md5": hashlib.md5(raw).hexdigest(),
        "bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "bundle_lines": len(lines),
        "bundle_bytes": len(raw),
        "rule": rule,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def manifest_path(project: str, chunks_dir: Path | None = None) -> Path:
    """The document bundle's manifest: `{PROJECT}_chunks.yaml`."""
    # Resolved at call time so a test (or a caller) can repoint the module dirs.
    return (chunks_dir if chunks_dir is not None else anchored(CHUNKS_DIR)) / f"{project}_chunks.yaml"


#: The repository this package is checked out in — the root `CONCAT_DIR`
#: is relative to. Resolved from the package, not the working directory, so
#: a study bundle named by absolute path is a study bundle from anywhere
#: (#1367 review, must-fix 7).
REPO_ROOT = Path(__file__).resolve().parents[2]


def anchored(d: Path) -> Path:
    """A repository-owned relative directory as a path that is correct from
    any working directory: as written from the repository root — so the
    paths a record carries stay relative and portable (`inputs.chunks.path`
    is `data/preprocessed/chunks/…` on every record) — and anchored to the
    checkout from anywhere else (#1367 round 2, #1388)."""
    d = Path(d)
    if d.is_absolute():
        return d
    try:
        if Path.cwd().resolve() == REPO_ROOT:
            return d
    except OSError:
        pass
    return REPO_ROOT / d


def _study_dir() -> Path:
    return anchored(CONCAT_DIR).resolve()


def canonical_name(bundle: Path) -> str:
    """The basename a manifest records for `bundle`: a study bundle's own,
    through any symlink; any other bundle's as given. The name in the
    payload and the destination of the file are decided together, so an
    alias never writes the canonical manifest under a different `bundle:`
    (#1367 round 2, #1389)."""
    bundle = Path(bundle)
    if _under_concat_dir(bundle):
        try:
            return bundle.resolve().name
        except OSError:
            return bundle.name
    return bundle.name


def _under_concat_dir(bundle: Path) -> bool:
    """Whether `bundle` is one of the study's bundles: a file under
    `CONCAT_DIR`, both resolved — so a symlink into the study directory is
    a study bundle, and a path spelled relative to another working
    directory is not mistaken for one."""
    try:
        return Path(bundle).resolve().parent == _study_dir()
    except OSError:
        return False


def manifest_for(bundle: Path, chunks_dir: Path | None = None) -> Path:
    """The manifest for any bundle kind (#725).

    A study bundle — one under `CONCAT_DIR`, or any bundle when the caller
    names a `chunks_dir` — keeps the frozen layout: the document bundle is
    `{PROJECT}_chunks.yaml` and every other kind `{bundle stem}_chunks.yaml`
    (`CHORUS_crate_only_chunks.yaml`) under the chunks directory.

    Any other bundle gets a sidecar beside itself, `{bundle stem}_chunks.yaml`
    in the bundle's own directory (#1299). Keyed by basename alone, two
    external bundles named `dataset.txt` in different directories shared one
    manifest under the study layout, so the second chunking silently replaced
    the first's — and a receipt validated against the wrong bytes. Beside the
    bundle, the manifest's identity is the bundle's, and the manifest still
    names the bundle by basename, so its bytes are the same wherever the
    bundle was read from (#713).
    """
    bundle = Path(bundle)
    if chunks_dir is None and not _under_concat_dir(bundle):
        stem = bundle.name[:-4] if bundle.name.endswith(".txt") else bundle.name
        return bundle.parent / f"{stem}_chunks.yaml"
    # A study bundle is named by what it resolves to: a symlink's alias is
    # not a second identity for the same bytes.
    name = canonical_name(bundle) if chunks_dir is None else bundle.name
    stem = name[:-4] if name.endswith(".txt") else name
    if name.endswith("_preprocessed.txt"):
        return manifest_path(name[: -len("_preprocessed.txt")], chunks_dir)
    return (chunks_dir if chunks_dir is not None else anchored(CHUNKS_DIR)) / f"{stem}_chunks.yaml"


def bundle_path(project: str, concat_dir: Path | None = None) -> Path:
    return (concat_dir if concat_dir is not None else anchored(CONCAT_DIR)) / f"{project}_preprocessed.txt"


def project_bundles(project: str, concat_dir: Path | None = None) -> list[Path]:
    """Every bundle of a known kind that exists for the project, document
    bundle first."""
    base = concat_dir if concat_dir is not None else anchored(CONCAT_DIR)
    return [p for s in BUNDLE_SUFFIXES if (p := base / f"{project}{s}").exists()]


def dump_manifest(manifest: dict[str, Any]) -> str:
    """Canonical text: same manifest → same bytes, so the file's sha256 is a
    receipt for the chunking and `--check` can compare bytes."""
    import yaml
    return yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=10_000)


def write_manifest_for(bundle: Path, rule: dict[str, Any] | None = None,
                       chunks_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    manifest = build_manifest(bundle, rule)
    out = manifest_for(bundle, chunks_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dump_manifest(manifest), encoding="utf-8")
    return out, manifest


def write_manifest(project: str, rule: dict[str, Any] | None = None,
                   concat_dir: Path | None = None, chunks_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """The document bundle's manifest (kept for callers and tests)."""
    return write_manifest_for(bundle_path(project, concat_dir), rule, chunks_dir)


def load_manifest(path: Path) -> dict[str, Any]:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_manifest_mapping(manifest: dict[str, Any], raw: bytes, name: str) -> None:
    """A receipt procedure may only send deterministic chunk IDs (#1404)."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("rule"), dict):
        raise ValueError("chunk manifest must declare a chunking rule")
    rule = manifest["rule"]
    for key, value in DEFAULT_RULE.items():
        selected = rule.get(key)
        if key in ("max_lines", "max_bytes"):
            if type(selected) is not int or selected < 1:
                raise ValueError(f"chunk rule {key} must be a positive integer")
        elif key == "version":
            if selected not in (2, "2-custom") or isinstance(selected, bool):
                raise ValueError(f"unsupported chunk rule {key}: {selected!r}")
        elif selected != value:
            raise ValueError(f"unsupported chunk rule {key}: {selected!r}")
    if set(rule) != set(DEFAULT_RULE):
        raise ValueError("unsupported chunk rule fields")
    expected = manifest_from_bytes(raw, name, rule)
    if manifest != expected:
        raise ValueError("chunk manifest does not reproduce canonical chunk identities under its recorded rule")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_status(project: str, concat_dir: Path | None = None,
                    chunks_dir: Path | None = None) -> tuple[str, str]:
    """(status, detail) for the project's *document* bundle manifest."""
    return manifest_status_for(bundle_path(project, concat_dir), chunks_dir)


def manifest_status_for(bundle: Path, chunks_dir: Path | None = None) -> tuple[str, str]:
    """(status, detail) for any bundle's manifest on disk.

    `current` — rebuilding the bundle under the manifest's own recorded rule
    reproduces the file byte for byte. `stale` — it does not (the bundle
    changed, or the rule did). `missing` — no manifest. `no_bundle` — nothing
    to chunk. The rebuild uses the *recorded* rule, not the default, so a
    manifest made under an older rule is current as long as its bytes still
    match; whether the rule is the current default is a separate question the
    caller can ask.
    """
    path = manifest_for(bundle, chunks_dir)
    # The project is the name minus its kind suffix, never a split on "_"
    # (AI_READI is not "AI", #744).
    project = next((bundle.name[: -len(s)] for s in BUNDLE_SUFFIXES if bundle.name.endswith(s)),
                   bundle.name)
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
                 chunks_dir: Path | None = None,
                 manifest: Path | None = None) -> dict[str, Any] | None:
    """What a provenance record should carry under `inputs.chunks`.

    Returned only when a manifest exists for this bundle *and* it was built
    from the same bytes the record hashed — otherwise a receipt naming its
    chunk ids would be anchored to a different file. `None` means "no
    manifest attests this input", which the record states as such. Any
    bundle kind (#725).
    """
    if bundle is None or bundle_md5 is None:
        return None
    # An explicitly selected manifest wins over discovery (#1299): the run
    # that chunked an external bundle knows where it put the manifest.
    path = Path(manifest) if manifest is not None else manifest_for(bundle, chunks_dir)
    if not path.exists():
        return None
    try:
        import yaml
        manifest_bytes = path.read_bytes()
        m = yaml.safe_load(manifest_bytes)
        if not isinstance(m, dict) or m.get("bundle_md5") != bundle_md5:
            return None
        validate_manifest_mapping(m, bundle.read_bytes(), canonical_name(bundle))
        return {"path": str(path), "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "bundle_name": m["bundle"],
                "rule": m.get("rule"), "chunk_count": m.get("chunk_count")}
    except Exception:                                               # noqa: BLE001
        # A broken manifest must not abort a live provenance record (#715);
        # "no manifest attests this input" is the true statement then.
        return None
