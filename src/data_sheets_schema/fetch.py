"""Manifest-driven fetch — make the local corpus match `source_manifest.yaml`.

`d4d download sources` reads URLs out of the GC Input Documents sheet. That is
the right primary path, but it cannot rebuild the whole corpus: several manifest
sources are deliberately *not* sheet-selected —

- curated historical supplements the sheet never carried (CM4AI's March and June
  2025 releases, CHORUS's GitHub organization overview),
- records captured from an API rather than a page (`fairhub_dataset_v3_api`),
- selections the sheet used to carry and no longer does, after the 2026-07-27
  upstream corrections (see notes/UPSTREAM_SOURCE_DISCREPANCIES.md).

Those are invisible to a sheet-driven download, so a fresh clone silently gets a
smaller corpus than the one every generation run consumed — and the difference
does not announce itself, it just shows up as different D4D records.

This module closes that gap by treating the manifest as what it already claims
to be: the canonical source selection. Every entry carries a `url` and a
`raw_file`, which is enough to fetch it directly.

Fetching reuses `OrganizedDatasetExtractor._process_url`, so per-type handling
(PDF, PhysioNet, Dataverse, FAIRhub, GitHub, Google Drive, generic HTML) stays
in one place rather than being reimplemented here. The one thing this module
adds is that output lands on the manifest's *declared* filename, not on the
`_row{N}` name the sheet path generates — the manifest is the authority on what
a file is called.

Safety: nothing is overwritten unless `force=True`. The default is to fetch only
what is missing, because clobbering a corpus file mid-study silently invalidates
every run that consumed it.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

MANIFEST = Path("data/preprocessed/source_manifest.yaml")
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/preprocessed/individual")
DEFAULT_MINIMUM_CHARACTERS = 500


@dataclass
class Source:
    """One manifest entry, resolved to concrete local paths."""

    project: str
    id: str
    url: str
    raw_file: str
    processed_file: str
    source_type: str | None = None
    minimum_characters: int | None = None
    curation_note: str | None = None
    fetch: str | None = None          # "manual" => no handler can reproduce it

    @property
    def is_manual(self) -> bool:
        """True when the artifact cannot be regenerated from its URL.

        Some captures are not a download of the URL — CHORUS's GitHub overview
        is a PDF rendering of a web page, so re-fetching the page yields HTML
        and never the declared artifact. Marking these keeps the fetcher honest:
        it reports them as needing a human rather than failing on every run, and
        it flags that losing the file means losing the source.
        """
        return (self.fetch or "").strip().lower() == "manual"

    @property
    def raw_path(self) -> Path:
        return RAW_DIR / self.project / self.raw_file

    @property
    def processed_path(self) -> Path:
        return PROCESSED_DIR / self.project / self.processed_file

    @property
    def has_raw(self) -> bool:
        return self.raw_path.exists()

    @property
    def has_processed(self) -> bool:
        return self.processed_path.exists()


@dataclass
class FetchResult:
    source: Source
    # fetched | skipped_present | failed | dry_run | no_url | manual
    status: str
    detail: str = ""
    bytes_written: int | None = None


@dataclass
class Plan:
    results: list[FetchResult] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def failed(self) -> list[FetchResult]:
        return [r for r in self.results if r.status == "failed"]


def load_sources(manifest_path: Path = MANIFEST,
                 projects: Iterable[str] | None = None) -> list[Source]:
    """Every manifest entry, as Source objects."""
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    out: list[Source] = []
    wanted = set(projects) if projects else None
    for project, entries in (data.get("projects") or {}).items():
        if wanted and project not in wanted:
            continue
        for e in entries or []:
            if not isinstance(e, dict):
                continue
            out.append(Source(
                project=project,
                id=str(e.get("id") or "(unnamed)"),
                url=str(e.get("url") or ""),
                raw_file=str(e.get("raw_file") or ""),
                processed_file=str(e.get("processed_file") or ""),
                source_type=e.get("source_type"),
                minimum_characters=e.get("minimum_characters"),
                curation_note=e.get("curation_note"),
                fetch=e.get("fetch"),
            ))
    return out


def missing(sources: Iterable[Source]) -> list[Source]:
    """Sources whose raw file is absent locally."""
    return [s for s in sources if not s.has_raw]


def _produced_file(staging: Path, info: dict[str, Any], want_suffix: str) -> Path | None:
    """Pick the artifact matching the manifest's declared extension.

    Some handlers emit more than one file for a single URL — the Dataverse
    handler writes both `.html` and a `.txt` text extraction. The manifest says
    which one is the raw artifact, so honour that rather than guessing.
    """
    declared = info.get("path")
    if declared:
        p = Path(declared)
        if p.exists() and p.suffix.lower() == want_suffix:
            return p
    candidates = [p for p in staging.rglob("*")
                  if p.is_file() and p.suffix.lower() == want_suffix]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_size)


def fetch_source(source: Source, *, force: bool = False, dry_run: bool = False,
                 extractor: Any | None = None) -> FetchResult:
    """Fetch one manifest source to its declared raw path."""
    if source.is_manual:
        state = "present" if source.has_raw else "ABSENT — source is unrecoverable"
        return FetchResult(source, "manual",
                           f"manual capture, cannot be re-fetched ({state})")
    if not source.url:
        return FetchResult(source, "no_url", "manifest entry has no url")
    if not source.raw_file:
        return FetchResult(source, "no_url", "manifest entry has no raw_file")
    if source.has_raw and not force:
        return FetchResult(source, "skipped_present",
                           f"{source.raw_path} already present",
                           source.raw_path.stat().st_size)
    if dry_run:
        return FetchResult(source, "dry_run", f"would fetch {source.url}")

    if extractor is None:
        from src.download.organized_dataset_extractor import OrganizedDatasetExtractor
        extractor = OrganizedDatasetExtractor(output_dir=str(RAW_DIR))

    staging = Path(tempfile.mkdtemp(prefix="d4d-supp-"))
    try:
        try:
            info = extractor._process_url(source.url, staging, 0) or {}
        except Exception as exc:                       # network, parse, anything
            return FetchResult(source, "failed", f"{type(exc).__name__}: {exc}")

        if not info.get("downloaded"):
            return FetchResult(source, "failed",
                               str(info.get("error") or "handler reported no download"))

        produced = _produced_file(staging, info, Path(source.raw_file).suffix.lower())
        if produced is None:
            return FetchResult(
                source, "failed",
                f"handler produced no {Path(source.raw_file).suffix} artifact")

        floor = int(source.minimum_characters or DEFAULT_MINIMUM_CHARACTERS)
        size = produced.stat().st_size
        if size < floor:
            return FetchResult(source, "failed",
                               f"artifact is {size}b, below the {floor}b floor "
                               "declared for this source")

        source.raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), str(source.raw_path))
        return FetchResult(source, "fetched", str(source.raw_path), size)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def fetch_missing(manifest_path: Path = MANIFEST,
                  projects: Iterable[str] | None = None, *,
                  force: bool = False, dry_run: bool = False,
                  only: Iterable[str] | None = None) -> Plan:
    """Fetch every manifest source not present locally (or all, with force)."""
    sources = load_sources(manifest_path, projects)
    if only:
        wanted = set(only)
        sources = [s for s in sources if s.id in wanted]
    targets = sources if force else missing(sources)

    plan = Plan()
    extractor = None
    if targets and not dry_run:
        from src.download.organized_dataset_extractor import OrganizedDatasetExtractor
        extractor = OrganizedDatasetExtractor(output_dir=str(RAW_DIR))
    for s in targets:
        plan.results.append(
            fetch_source(s, force=force, dry_run=dry_run, extractor=extractor))
    return plan


def audit(manifest_path: Path = MANIFEST,
          projects: Iterable[str] | None = None) -> dict[str, Any]:
    """What the manifest declares versus what is on disk.

    Reported rather than silently repaired: a missing processed file means the
    preprocessing step needs rerunning, which is a different command, and a
    missing raw file may be a deliberate pending capture.
    """
    sources = load_sources(manifest_path, projects)
    miss_raw = [s for s in sources if not s.has_raw]
    miss_proc = [s for s in sources if s.has_raw and not s.has_processed]
    manual = [s for s in sources if s.is_manual]
    return {
        "total": len(sources),
        "present": len([s for s in sources if s.has_raw and s.has_processed]),
        "missing_raw": miss_raw,
        "missing_processed": miss_proc,
        # Present but irreplaceable: if these are lost, no command brings them
        # back. They are the corpus's single points of failure.
        "manual": manual,
        "unrecoverable": [s for s in manual if not s.has_raw],
        "by_project": {
            p: len([s for s in sources if s.project == p])
            for p in sorted({s.project for s in sources})
        },
    }
