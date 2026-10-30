"""Read-only, per-record bundle comparisons for every selected arm (#4762).

Keep the recorded bundle, its pinned chunk manifest and today's file separate.
Unavailable evidence is unknown, never a measured match. This module does not
change historical provenance or select which experimental arms to compare.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

import yaml


class _UniqueManifestLoader(yaml.SafeLoader):
    """Ambiguous mappings must not become a last-key-wins identity claim."""


def _manifest_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("manifest requires unique string keys")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueManifestLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _manifest_mapping)


def _digest(value: Any, size: int) -> str | None:
    if isinstance(value, str) and re.fullmatch(rf"[a-fA-F0-9]{{{size}}}", value):
        return value.lower()
    return None


def _path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        raw = Path(value)
        lexical = Path(os.path.abspath(root / raw))
        try:
            lexical.relative_to(root)
        except ValueError:
            from data_sheets_schema.provenance import _repo_preprocessed_tail
            tail = _repo_preprocessed_tail(raw) if raw.is_absolute() else None
            if tail is None:
                return None
            lexical = Path(os.path.abspath(root / tail))
            lexical.relative_to(root)
        path = lexical.resolve()
        path.relative_to(root)
        return path
    except (OSError, RuntimeError, ValueError):
        return None


def _comparison(recorded: str | None, observed: str | None) -> str:
    if recorded is None or observed is None:
        return "unknown"
    return "match" if recorded == observed else "drift"


def _hashes_match(raw: bytes, md5: str | None, sha256: str | None) -> bool:
    return bool(md5 or sha256) and (
        md5 is None or hashlib.md5(raw).hexdigest() == md5
    ) and (sha256 is None or hashlib.sha256(raw).hexdigest() == sha256)


def _recover(root: Path, relative: str, **pins):
    """Use the existing historical-byte resolver only in its owning checkout."""
    from data_sheets_schema import provenance

    if Path(provenance.__file__).resolve().parents[2] != root:
        return None
    return provenance.committed_bytes_for(relative, **pins)


def bundle_drift(
    record: Mapping[str, Any],
    root: Path,
    *,
    recover: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Compare one provenance record's bundle MD5 with disk and pinned manifest.

    ``recover`` has the existing ``committed_bytes_for(path, md5=, sha256=)``
    interface. Even recovered bytes are independently checked against every
    declared manifest hash. A current, changed manifest cannot stand in for the
    historical one. Disk bytes are read afresh on each call.
    """
    root = Path(root).resolve()
    inputs = record.get("inputs")
    inputs = inputs if isinstance(inputs, Mapping) else {}
    run = record.get("run")
    run = run if isinstance(run, Mapping) else {}
    pinned = _digest(inputs.get("bundle_md5"), 32)
    bundle = _path(root, inputs.get("bundle_path"))
    result = {
        "label": run.get("label"), "project": run.get("project"),
        "bundle_path": inputs.get("bundle_path"), "recorded_md5": pinned,
        "disk_md5": None, "disk_status": "unknown", "disk_reason": None,
        "manifest_md5": None, "manifest_status": "unknown",
        "manifest_basis": None, "manifest_reason": None,
    }
    if bundle is None:
        result["disk_reason"] = "bundle path missing or outside selected checkout"
    else:
        try:
            result["disk_md5"] = hashlib.md5(bundle.read_bytes()).hexdigest()
        except OSError as exc:
            result["disk_reason"] = f"bundle unavailable: {type(exc).__name__}"
    result["disk_status"] = _comparison(pinned, result["disk_md5"])
    if pinned is None:
        result["disk_reason"] = "bundle MD5 missing or malformed in provenance"

    chunks = inputs.get("chunks")
    chunks = chunks if isinstance(chunks, Mapping) else {}
    manifest = _path(root, chunks.get("path"))
    md5, sha = _digest(chunks.get("md5"), 32), _digest(chunks.get("sha256"), 64)
    invalid_pin = any(chunks.get(key) is not None and digest is None
                      for key, digest in (("md5", md5), ("sha256", sha)))
    if manifest is None or not (md5 or sha) or invalid_pin:
        result["manifest_reason"] = "recorded chunk-manifest path/hash missing or malformed"
        return result
    raw = None
    try:
        current = manifest.read_bytes()
    except OSError:
        current = None
    if current is not None and _hashes_match(current, md5, sha):
        raw = current
        result["manifest_basis"] = "pinned manifest on disk"
    else:
        # Git names the recorded path, not the destination of today's symlink.
        # _path already bounded live IO; normalize this lexical path separately.
        cpath = Path(chunks["path"])
        if cpath.is_absolute():
            from data_sheets_schema.provenance import _repo_preprocessed_tail
            tail = _repo_preprocessed_tail(cpath)
            if tail is not None:
                cpath = tail
        relative = Path(os.path.abspath(root / cpath)).relative_to(root).as_posix()
        try:
            found = ((recover(relative, md5=md5, sha256=sha) if recover is not None
                      else _recover(root, relative, md5=md5, sha256=sha)))
        except (OSError, RuntimeError) as exc:
            result["manifest_reason"] = f"manifest recovery unavailable: {type(exc).__name__}"
            return result
        if found is not None and _hashes_match(found[0], md5, sha):
            raw = found[0]
            result["manifest_basis"] = "pinned manifest recovered from history"
    if raw is None:
        result["manifest_reason"] = "no available manifest bytes match all recorded hashes"
        return result
    try:
        doc = yaml.load(raw, Loader=_UniqueManifestLoader)
    except (yaml.YAMLError, UnicodeError, ValueError):
        doc = None
    if not isinstance(doc, Mapping):
        result["manifest_reason"] = "pinned chunk manifest is not a readable mapping"
        return result
    manifest_name = doc.get("bundle")
    if (bundle is None or not isinstance(manifest_name, str)
            or manifest_name not in (bundle.name, bundle.relative_to(root).as_posix())):
        result["manifest_reason"] = "pinned manifest does not name the recorded bundle"
        return result
    result["manifest_md5"] = _digest(doc.get("bundle_md5"), 32)
    result["manifest_status"] = _comparison(pinned, result["manifest_md5"])
    if pinned is None or result["manifest_md5"] is None:
        result["manifest_reason"] = "bundle MD5 missing or malformed in provenance or manifest"
    return result


def compare_bundle_drift(
    arms: Mapping[str, Iterable[Mapping[str, Any]]],
    root: Path,
    *,
    recover: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Preserve all selected arms and all replicate-level comparisons."""
    comparisons = {}
    for arm, records in arms.items():
        rows = [bundle_drift(record, root, recover=recover) for record in records]
        comparisons[arm] = {
            "records": rows,
            "count": len(rows),
            "disk": {s: sum(row["disk_status"] == s for row in rows)
                     for s in ("match", "drift", "unknown")},
            "manifest": {s: sum(row["manifest_status"] == s for row in rows)
                         for s in ("match", "drift", "unknown")},
            "recorded_bundle_versions": dict(Counter(
                f"{row['project']}:{row['recorded_md5']}" for row in rows
                if row["recorded_md5"] is not None)),
        }
    return comparisons


def render_bundle_drift(comparisons: Mapping[str, Any]) -> list[str]:
    """Render denominators and record-level evidence; never assert universal parity."""
    def escaped(value):
        return str(value if value is not None else "unknown").replace("|", "\\|").replace("\n", " ")

    lines = [
        "## Bundle identity by arm", "",
        "Each record is compared separately with today's bundle and the chunk manifest "
        "whose hashes it recorded. A source-ranking manifest is not a bundle-byte pin. "
        "Unknown evidence is not a match; drift describes changed inputs, not generation quality.", "",
        "| arm | records | disk: match / drift / unknown | pinned manifest: match / drift / unknown |",
        "|---|---:|---|---|",
    ]
    for arm, block in comparisons.items():
        counts = [" / ".join(str(block[basis][state]) for state in ("match", "drift", "unknown"))
                  for basis in ("disk", "manifest")]
        lines.append(f"| {escaped(arm)} | {block['count']} | {counts[0]} | {counts[1]} |")
    lines += [
        "", "Counts are per record, not unique projects. Arms with no selected records "
        "supply no comparison evidence.", "",
        "| arm | project | label | recorded bundle MD5 | disk MD5 / status | pinned manifest bundle MD5 / status | evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for arm, block in comparisons.items():
        for row in block["records"]:
            detail = "; ".join(str(row[key]) for key in (
                "disk_reason", "manifest_basis", "manifest_reason") if row[key])
            values = (arm, row["project"], row["label"], row["recorded_md5"],
                      f"{row['disk_md5'] or 'unknown'} / {row['disk_status']}",
                      f"{row['manifest_md5'] or 'unknown'} / {row['manifest_status']}", detail)
            lines.append("| " + " | ".join(escaped(v) for v in values) + " |")
    return lines + [""]


def main(argv: list[str] | None = None) -> int:
    """Read explicitly selected provenance files and print a new comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--arm", action="append", required=True, metavar="ARM=RECORD",
                        help="repeat for every selected provenance file; no inferred cohort")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    arms: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, Path]] = set()
    for selection in args.arm:
        arm, separator, name = selection.partition("=")
        path = _path(root, name)
        if not separator or not arm.strip() or path is None:
            parser.error("--arm requires ARM=RECORD inside the selected checkout")
        if (arm, path) in seen:
            parser.error(f"duplicate record for arm {arm!r}")
        seen.add((arm, path))
        try:
            record = yaml.load(path.read_bytes(), Loader=_UniqueManifestLoader)
        except (OSError, yaml.YAMLError, UnicodeError, ValueError) as exc:
            parser.error(f"unreadable provenance: {path.name}: {type(exc).__name__}")
        if not isinstance(record, dict) or not isinstance(record.get("run"), dict):
            parser.error(f"provenance lacks run identity: {path.name}")
        arms.setdefault(arm, []).append(record)
    result = compare_bundle_drift(arms, root)
    print(json.dumps(result, indent=2) if args.format == "json"
          else "\n".join(render_bundle_drift(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
