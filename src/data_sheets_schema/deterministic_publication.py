"""Publish a fresh deterministic label with retained evidence (#2915, #2916).

The existing emitter owns record serialization. A label is complete only when
manifest.json exists and names its exact artifacts and successful validations.
Failed labels remain incomplete for inspection; publication never rewrites one.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

from data_sheets_schema import figure_publication
from data_sheets_schema.crate_generation_comparison import parse_report, source_evidence_rows
from data_sheets_schema.rocrate_normalize import emit_deterministic_arm

METHODS = {"rocrate_static_map": "crate_mapped_d4d", "rocrate_mapped": "crate_d4d"}
SCHEMA = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
TABLE = "data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv"
STATIC_PRODUCER_FILES = frozenset(
    f"src/data_sheets_schema/{name}.py" for name in
    ("rocrate_map", "rocrate_sources", "rocrate_assertions", "scope", "schema_view")
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, limit: int = 32 * 1024 * 1024) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular input file: {path}")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"publication input exceeds its byte limit: {path}")
    return raw


def _history(concat: Path, exclude: Path | None = None) -> dict[str, str]:
    """Inventory every old label file, including ignored and hidden files."""
    found = {}
    for method in METHODS:
        base = concat / method
        if not base.exists():
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            parent = Path(directory)
            if exclude is not None and parent == exclude:
                dirs[:] = []
                continue
            for name in dirs + files:
                if (parent / name).is_symlink():
                    raise ValueError("historical label contains a symbolic link")
            for name in files:
                path = parent / name
                found[str(path.relative_to(concat))] = digest(_read(path))
    return found


def _code(repo: Path) -> tuple[str, list[str]]:
    def git(*args):
        return subprocess.check_output(["git", "-c", "gc.auto=0", *args], cwd=repo, text=True).strip()
    commit = git("rev-parse", "HEAD")
    paths = git("ls-files", "src/data_sheets_schema", "scripts/publish_deterministic_label.py").splitlines()
    paths = [path for path in paths if path.endswith(".py")]
    required = {"src/data_sheets_schema/deterministic_publication.py",
                "scripts/publish_deterministic_label.py"}
    if not required <= set(paths) or git("status", "--porcelain", "--untracked-files=all",
                                       "--", "src/data_sheets_schema", "scripts/publish_deterministic_label.py"):
        raise ValueError("commit the producer/publication code before publishing")
    return commit, paths


def prepare(repo: Path, packages: Path, concat: Path, method: str,
            label: str, projects: list[str]) -> dict:
    repo, packages, concat = repo.resolve(), packages.resolve(), concat.resolve()
    if method not in METHODS or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", label):
        raise ValueError("invalid method or single-component label")
    if not projects or len(set(projects)) != len(projects) or any(
            not re.fullmatch(r"[A-Z][A-Z0-9_]*", project) for project in projects):
        raise ValueError("projects must be explicit unique project names")
    packages.relative_to(repo)
    concat.relative_to(repo)
    destination = concat / method / label
    if os.path.lexists(destination):
        raise FileExistsError(f"label already exists: {destination}")
    captured = {}

    def capture(path):
        path = Path(path)
        relative = str(path.relative_to(repo))
        if relative not in captured:
            captured[relative] = _read(path)
        return captured[relative]

    code_commit, code_paths = _code(repo)
    for name in code_paths + [SCHEMA, TABLE]:
        capture(repo / name)
    capture(packages / "crate_manifest.yaml")
    items = []
    for project in projects:
        project_dir = packages / project
        processed = project_dir / "processed"
        record = processed / f"{project}_{METHODS[method]}.yaml"
        capture(record)
        reports = ([processed / f"{project}_crate_mapping_provenance.md",
                    processed / f"{project}_crate_mapping_sources.json"]
                   if method == "rocrate_static_map" else
                   [processed / f"{project}_crate_changes.md"])
        for report in reports:
            capture(report)
        source_names = ["ro-crate-metadata.json"]
        if method == "rocrate_mapped":
            source_names.append("ro-crate-linkml.yaml")
        sources = []
        for name in source_names:
            direct = next((project_dir / base / name for base in ("raw", "crate")
                           if (project_dir / base / name).is_file()), None)
            if project == "CM4AI":
                archive = project_dir / "raw/cm4ai_release_metadata.zip"
                archive_raw = capture(archive)
                member = f"cm4ai_release_metadata/{name}"
                with zipfile.ZipFile(io.BytesIO(archive_raw)) as handle:
                    matches = [entry for entry in handle.infolist() if entry.filename == member]
                    if len(matches) != 1 or matches[0].is_dir() or matches[0].file_size > 16 * 1024 * 1024:
                        raise ValueError(f"missing, duplicate or oversized archive member: {member}")
                    with handle.open(matches[0]) as stream:
                        raw = stream.read(16 * 1024 * 1024 + 1)
                    if len(raw) != matches[0].file_size or len(raw) > 16 * 1024 * 1024:
                        raise ValueError(f"archive member length differs: {member}")
                if direct is not None and capture(direct) != raw:
                    raise ValueError(f"extracted source differs from archive: {name}")
                sources.append({"archive": str(archive.relative_to(repo)),
                                "archive_sha256": digest(archive_raw), "member": member,
                                "sha256": digest(raw), "bytes": len(raw)})
            elif direct is not None:
                raw = capture(direct)
                sources.append({"path": str(direct.relative_to(repo)),
                                "sha256": digest(raw), "bytes": len(raw)})
            else:
                raise ValueError(f"source file missing for {project}: {name}")
        producer_binding = {
            "kind": "unrecorded", "verified": False,
            "note": "The normalizer report does not bind its producing code; code_commit identifies publication code only.",
        }
        if method == "rocrate_static_map":
            sidecar = json.loads(captured[str(reports[1].relative_to(repo))])
            report = parse_report(captured[str(reports[0].relative_to(repo))].decode("utf-8"))
            observations = source_evidence_rows(sidecar)
            if sidecar.get("project") != project:
                raise ValueError("source sidecar project differs")
            from collections import Counter
            statuses = Counter(row["mapping_status"] for row in observations)
            statuses["filled"] += report["root_identifier_rows"]
            if len(observations) != report["original_rows"] or any(
                    statuses[status] != report["outcome"].get(status, 0)
                    for status in set(statuses) | set(report["outcome"])):
                raise ValueError("source sidecar and report accounting differ")
            report_rows = Counter((row["d4d_path"], row["status"])
                                  for row in report["fields"]
                                  if row["source_path"] != "crate root identifier/@id")
            source_rows = Counter((row["d4d_path"], row["mapping_status"])
                                  for row in observations)
            if report_rows != source_rows:
                raise ValueError("source sidecar and per-field report rows differ")
            if sidecar["source"]["sha256"] != sources[0]["sha256"]:
                raise ValueError("source sidecar raw-source hash differs")
            for key, expected in (("mapping_table", TABLE), ("schema", SCHEMA)):
                if sidecar[key]["sha256"] != digest(captured[expected]):
                    raise ValueError(f"source sidecar {key} hash differs")
            if sidecar.get("record_sha256") != digest(captured[str(record.relative_to(repo))]):
                raise ValueError("source sidecar record hash differs")
            producer = sidecar.get("producer")
            producer_hashes = producer.get("files_sha256") if isinstance(producer, dict) else None
            if not isinstance(producer_hashes, dict) or not STATIC_PRODUCER_FILES <= producer_hashes.keys():
                raise ValueError("source sidecar producer code binding is missing or incomplete")
            for name, expected in producer_hashes.items():
                if name not in code_paths or expected != digest(captured[name]):
                    raise ValueError(f"source sidecar producer code hash differs: {name}")
            producer_binding = {"kind": "source_sidecar_code_hashes", "verified": True,
                                "files_sha256": dict(producer_hashes)}
        items.append({"project": project, "working_record": str(record.relative_to(repo)),
                      "reports": [str(path.relative_to(repo)) for path in reports], "sources": sources,
                      "producer_binding": producer_binding})
    return {"repo": repo, "packages": packages, "concat": concat,
            "destination": destination, "method": method, "label": label,
            "code_commit": code_commit, "code_paths": code_paths, "captured": captured,
            "items": items, "prior_labels": _history(concat)}


def validate_record(record: Path, schema: Path) -> dict:
    from data_sheets_schema.resources import linkml_validate
    argv = [*linkml_validate(), "-s", str(schema), "-C", "Dataset", str(record)]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    return {"argv": argv, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
            "valid": result.returncode == 0 and "No issues found" in result.stdout + result.stderr}


def publish(prepared: dict, *, validator=None) -> dict:
    validator = validator or validate_record
    repo, destination = prepared["repo"], prepared["destination"]
    if Path.cwd().resolve() != repo:
        raise ValueError("publish from the repository root for portable record headers")

    def verify_inputs():
        for name, raw in prepared["captured"].items():
            if _read(repo / name) != raw:
                raise ValueError(f"publication input changed: {name}")
        if _history(prepared["concat"], destination) != prepared["prior_labels"]:
            raise ValueError("historical deterministic labels changed")
        actual, _ = _code(repo)
        if actual != prepared["code_commit"]:
            raise ValueError("producer code commit changed")

    verify_inputs()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    rows = []
    emitted_hashes = {}

    def verify_records():
        for path, expected in emitted_hashes.items():
            if digest(_read(path)) != expected:
                raise ValueError(f"published record changed after emission: {path.name}")

    for item in prepared["items"]:
        record = emit_deterministic_arm(
            item["project"], prepared["label"], prepared["packages"].relative_to(repo),
            prepared["concat"].relative_to(repo), prepared["method"], METHODS[prepared["method"]])
        # The validation verdict must describe these exact emitted bytes.
        # Capturing a digest after validation could bless a replaced record.
        record_sha256 = digest(_read(record))
        emitted_hashes[record] = record_sha256
        validation = validator(record, repo / SCHEMA)
        verify_records()
        if validation.get("valid") is not True or validation.get("exit_code") != 0:
            failure = {"state": "incomplete", "project": item["project"], "validation": validation}
            (destination / "validation-failure.json").write_text(json.dumps(failure, indent=2) + "\n")
            raise ValueError(f"published record failed validation: {item['project']}")
        evidence = destination / "provenance" / item["project"]
        evidence.mkdir(parents=True)
        retained = []
        for source in item["reports"]:
            target = evidence / Path(source).name
            with target.open("xb") as stream:
                stream.write(prepared["captured"][source])
            retained.append(str(target.relative_to(destination)))
        rows.append({**item, "record": record.name, "record_sha256": record_sha256,
                     "retained_reports": retained, "validation": validation})
    verify_inputs()
    verify_records()
    artifacts = {str(path.relative_to(destination)): digest(_read(path))
                 for path in sorted(destination.rglob("*")) if path.is_file()}
    manifest = {"format_version": 1, "state": "complete", "method": prepared["method"],
                "label": prepared["label"], "code_commit": prepared["code_commit"],
                "code_commit_role": "publication_code",
                "code_sha256": {name: digest(prepared["captured"][name]) for name in prepared["code_paths"]},
                "inputs": {name: {"sha256": digest(raw), "bytes": len(raw)}
                           for name, raw in prepared["captured"].items()},
                "projects": rows, "artifacts": artifacts,
                "prior_label_sha256": prepared["prior_labels"], "prior_labels_unchanged": True,
                "scientific_scoring": False, "method_core_created": False}

    def verify():
        verify_inputs()
        verify_records()
        for name, expected in artifacts.items():
            if digest(_read(destination / name)) != expected:
                raise ValueError(f"publication artifact changed: {name}")

    raw = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    directory = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    committed = False
    try:
        figure_publication.complete(directory, "manifest.json", raw, verify)
        committed = True
    finally:
        figure_publication.close_descriptor(directory, committed=committed)
    return manifest
