"""Is the schema a run is about to be generated against the real schema?

The digest sent to the model, the schema every record is validated against, and
the identity slots the pair checker uses are all read from the **merged**
schemas — `data_sheets_schema_all.yaml` and `data_sheets_schema_core_all.yaml`.
Those are generated artifacts. The source of truth is
`data_sheets_schema.yaml` and the `D4D_*.yaml` modules it imports.

Nothing checked that the two agree before a generation run. If a module is
edited without regenerating, every record in the arm attests to a digest that
describes an older schema than the repository holds — and there is no field in
the record that could reveal it, because the record correctly hashes the merged
file it actually read.

`make check-sync` exists and is not on the generation path; #521 records a
period when it reported staleness and the remedy it named was a silent no-op.

## Rebuild and compare, not mtime

The check regenerates each merged schema into a temporary directory and
compares the bytes, for the reason `audit-bundles` does the same for bundles
(#446): a timestamp says when a file was written, not what it was written
from. A merged file can be newer than its modules and still be wrong.

This costs a `gen-linkml` invocation per schema — seconds, once per run,
against an arm that takes hours.

## Fatal, unlike the other pre-run checks

Bundle drift, pair divergence, report claims and identifier grounding are all
reported and never fatal, because each describes a record that remains usable
evidence. A stale merged schema is different in kind: it corrupts the run's
central input before a token is spent, and every record produced would have to
be discarded. There is nothing to preserve by continuing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from linkml_runtime import URI_TO_LOCAL
from data_sheets_schema.schema_snapshot import capture_schema

#: (merged artifact, source it is generated from, digest class, leading `---`)
#:
#: The document marker is per-schema because the Makefile is: the full-schema
#: rule pipes `---` onto its output and the core rule does not. Assuming both
#: had it made this check report the core schema stale on its first run, for a
#: one-line difference the check itself had introduced.
MERGED_SCHEMAS = (
    (Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml"),
     Path("src/data_sheets_schema/schema/data_sheets_schema.yaml"),
     "Dataset", True),
    (Path("src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"),
     Path("src/data_sheets_schema/schema/data_sheets_schema_core.yaml"),
     "CoreDataset", False),
)

IN_SYNC = "in_sync"
STALE = "stale"
UNCHECKED = "unchecked"


_REBUILT: dict[tuple, bytes] = {}
_REBUILT_DIGESTS: dict[tuple, str] = {}


def forget_rebuilds() -> None:
    """Drop every cached rebuild. `schema_cache.clear` calls this too."""
    _REBUILT.clear()
    _REBUILT_DIGESTS.clear()


def _generator_versions() -> tuple:
    """The installed `linkml` and `linkml-runtime` — a rebuild's bytes depend
    on them, and on `linkml:types` imported from the runtime package, which
    no file under the schema directory can attest (#1204 review, S5)."""
    import importlib.metadata as _m
    out = []
    for name in ("linkml", "linkml-runtime"):
        try:
            out.append((name, _m.version(name)))
        except _m.PackageNotFoundError:
            out.append((name, None))
    return tuple(out)


def _source_snapshot(source: Path) -> tuple[tuple, dict[Path, bytes]]:
    """Capture local source/import bytes once for both the key and generator.

    Path.rglob includes ignored modules. Relative imports outside the source
    directory are captured too, and copied with their relative layout intact.
    LinkML package imports are captured too; dependency versions also remain
    part of the key because generator behavior depends on them.
    """
    source_name = str(source)
    source = Path(os.path.abspath(source))
    merged_names = {m.name for m, _s, _c, _k in MERGED_SCHEMAS}
    files = {Path(os.path.abspath(p)): p.read_bytes() for p in source.parent.rglob("*.yaml")
             if p.name not in merged_names or Path(os.path.abspath(p)) == source}
    if source not in files:
        files[source] = source.read_bytes()
    def read(path):
        if path not in files:
            files[path] = path.read_bytes()
        return files[path]
    # gen-linkml creates a fresh view and traverses imports before callers can
    # initialize namespaces. Use that same resolver and the same captured
    # bytes, including namespace aliases for local packages (#1276).
    capture_schema(source, content=files[source], read_bytes=read,
                   namespace_orders=(False,), strict=True)
    state = (str(source), _generator_versions(),
             tuple((str(p), str(p.resolve()), hashlib.sha256(data).hexdigest()) for p, data in sorted(files.items())),
             source_name)
    return state, files


def _source_state(source: Path) -> tuple:
    """Source/module content hashes and installed generator versions (#1262)."""
    return _source_snapshot(source)[0]


def _regenerate(source: Path, target: Path,
                marker: bool, *, snapshot: tuple | None = None) -> tuple[bool, str | None]:
    """Run the same generation the Makefile runs. (ok, why not)"""
    state, files = _source_snapshot(source) if snapshot is None else snapshot
    key = (state, marker)
    cached = _REBUILT.get(key)
    if cached is not None:
        target.write_bytes(cached)
        return True, None
    try:
        with tempfile.TemporaryDirectory(prefix="d4d-schema-source-") as tmp:
            base = Path(os.path.commonpath([str(p.parent) for p in files]))
            for path, content in files.items():
                copy = Path(tmp) / path.relative_to(base)
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_bytes(content)
            captured_source = Path(tmp) / Path(os.path.abspath(source)).relative_to(base)
            # Relative and namespace-resolved imports read captured files,
            # including package CURIEs and official URL aliases.
            captured_map = {}
            for path in files:
                copy = Path(tmp) / path.relative_to(base)
                captured_map[str(path)] = str(copy)
                for uri, local in URI_TO_LOCAL.items():
                    if Path(local) == path:
                        captured_map[uri] = str(copy)
            mapping = Path(tmp) / "snapshot-package-map.json"
            mapping.write_text(json.dumps(captured_map), encoding="utf-8")
            # gen-linkml discards --importmap when it creates its second view.
            # Route both views through the runtime loader's local map, only in
            # this child process. Normalize equivalent ./ and ../ spellings at
            # lookup (#1275); installed package files remain untouched.
            code = (
                "import json, os, sys\n"
                "import linkml_runtime\n"
                "from linkml_runtime.loaders import loader_root\n"
                "class CapturedPaths(dict):\n"
                "    def key(self, value):\n"
                "        return value if '://' in value else os.path.normpath(value)\n"
                "    def __contains__(self, value):\n"
                "        return super().__contains__(self.key(value))\n"
                "    def __getitem__(self, value):\n"
                "        return super().__getitem__(self.key(value))\n"
                "with open(sys.argv[1], encoding='utf-8') as stream:\n"
                "    captured = CapturedPaths(json.load(stream))\n"
                "linkml_runtime.URI_TO_LOCAL = loader_root.URI_TO_LOCAL = captured\n"
                "from linkml.generators.linkmlgen import cli\n"
                "cli(args=sys.argv[2:], prog_name='gen-linkml')\n")
            result = subprocess.run(
                [sys.executable, "-c", code, str(mapping), "-o", str(target.resolve()),
                 "-f", "yaml", str(captured_source)],
                capture_output=True, text=True, timeout=600)
    except Exception as exc:                                   # noqa: BLE001
        return False, f"gen-linkml could not run: {exc}"
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-300:]
        return False, f"gen-linkml failed: {tail}"
    if not target.exists():
        return False, "gen-linkml wrote nothing"
    # LinkML records its input filename. Preserve the logical source name the
    # Makefile supplies, rather than leaking the temporary snapshot path into
    # otherwise identical generated bytes.
    import yaml
    content = target.read_text(encoding="utf-8")
    source_line = re.search(r"(?ms)^source_file:.*?(?=^\S|\Z)", content)
    if source_line and yaml.safe_load(source_line.group()).get("source_file") == str(captured_source):
        named = yaml.safe_dump({"source_file": str(source)}, sort_keys=False, allow_unicode=True)
        content = content[:source_line.start()] + named + content[source_line.end():]
    target.write_text(("---\n" if marker else "") + content, encoding="utf-8")
    _REBUILT[key] = target.read_bytes()
    return True, None


def _rebuilt_fingerprint(class_name: str, path: Path, vocabulary: Path,
                         source_name: str, profile=None) -> str:
    """Digest frozen rebuild bytes without retaining a LinkML view (#946).

    Each check has a new temporary path. LinkML's method caches retain views
    even after callers drop them, so repeated stale checks must not build
    those views in the long-lived generation process. The child uses this
    checkout's code and a vocabulary snapshot and exits after one digest.
    Cache only the resulting strings under content hashes, including the
    displayed source name. Unchanged successful checks reuse that result.
    """
    from data_sheets_schema.profiles import active_profile
    from data_sheets_schema.schema_view import content_key
    prof = profile or active_profile()
    # The profile is part of the digest, so of the key (#1463); the child
    # is told which one rather than reading the environment.
    key = (class_name, source_name, content_key(path)[1], content_key(vocabulary)[1],
           _generator_versions(), prof.name)
    if key in _REBUILT_DIGESTS:
        return _REBUILT_DIGESTS[key]
    code = (
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from data_sheets_schema import schema_digest as d\n"
        "d.VOCABULARY_PIN = Path(sys.argv[4])\n"
        "inventory = d.build(sys.argv[2], Path(sys.argv[3]))\n"
        "inventory.schema_path = sys.argv[5]\n"
        "from data_sheets_schema.profiles import profile_named\n"
        "prof = profile_named(sys.argv[6])\n"
        "print(d.fingerprint(d.render(inventory, vocabulary=d.vocabularies(profile=prof))))\n")
    result = subprocess.run(
        [sys.executable, "-c", code, str(Path(__file__).resolve().parents[1]),
         class_name, str(path.resolve()), str(vocabulary.resolve()), source_name, prof.name],
        capture_output=True, text=True, timeout=60)
    value = result.stdout.strip()
    if result.returncode or len(value) != 32 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"rebuilt digest process failed: {(result.stderr or result.stdout).strip()[-300:]}")
    if len(_REBUILT_DIGESTS) >= 32:
        del _REBUILT_DIGESTS[next(iter(_REBUILT_DIGESTS))]
    _REBUILT_DIGESTS[key] = value
    return value


def check_one(merged: Path, source: Path, class_name: str,
              marker: bool = False, *, profile=None) -> dict[str, Any]:
    """Rebuild `merged` from `source` and compare — under `profile`, else
    the ambient one; the runner passes the run's (#1463)."""
    from data_sheets_schema import schema_digest
    from data_sheets_schema.profiles import active_profile
    profile = profile or active_profile()

    out: dict[str, Any] = {"merged": str(merged), "source": str(source),
                           "class": class_name}
    from data_sheets_schema.resources import resource_path
    merged, source = resource_path(merged), resource_path(source)   # from any directory (#1301)
    if not source.exists():
        return {**out, "status": UNCHECKED,
                "reason": f"source schema {source} is not on disk"}
    if not merged.exists():
        return {**out, "status": STALE,
                "reason": f"{merged} has never been generated"}

    with tempfile.TemporaryDirectory() as tmp:
        # Same filename, because the digest names the schema it came from and
        # a differing name would be a spurious difference.
        rebuilt = Path(tmp) / merged.name
        try:
            source_snapshot = _source_snapshot(source)
            source_state = source_snapshot[0]
            merged_bytes = merged.read_bytes()
            vocabulary_bytes = schema_digest.VOCABULARY_PIN.read_bytes()
            vocabulary = Path(tmp) / "vocabulary" / schema_digest.VOCABULARY_PIN.name
            vocabulary.parent.mkdir()
            vocabulary.write_bytes(vocabulary_bytes)
            ok, why = _regenerate(source, rebuilt, marker, snapshot=source_snapshot)
            if not ok:
                return {**out, "status": UNCHECKED, "reason": why}
            same = rebuilt.read_bytes() == merged_bytes
            live = schema_digest.fingerprint(
                schema_digest.digest_text(class_name, merged, profile=profile))
            # Compare against the preserved rebuild, not another read of the
            # live merged file: a changed-then-restored file can defeat an
            # end-of-check stability guard (#1258). No temporary views remain
            # in this process, on either successful or failed retries (#946).
            fresh = _rebuilt_fingerprint(class_name, rebuilt, vocabulary,
                                         schema_digest._schema_name(class_name, merged),
                                         profile=profile)
            source_changed = _source_state(source) != source_state
            if source_changed:
                forget_rebuilds()
            if (merged.read_bytes() != merged_bytes or source_changed
                    or schema_digest.VOCABULARY_PIN.read_bytes() != vocabulary_bytes):
                return {**out, "status": UNCHECKED,
                        "reason": "schema inputs changed during the sync check; retry with stable inputs"}
        except Exception as exc:                               # noqa: BLE001
            return {**out, "status": UNCHECKED,
                    "reason": f"digest could not be computed: {exc}"}
        out["digest"] = live
        out["digest_rebuilt"] = fresh
        if same and live == fresh:
            return {**out, "status": IN_SYNC}
        # Keep the rebuilt file so a human can diff it, rather than reporting
        # a difference and deleting the evidence of it.
        kept = Path(tempfile.mkdtemp(prefix="d4d-schema-rebuild-")) / merged.name
        shutil.copy2(rebuilt, kept)
        return {**out, "status": STALE, "rebuilt_at": str(kept),
                "reason": ("the merged schema differs from a fresh build of "
                           "its source" if not same else
                           "the merged schema matches but its digest does not")}


def check(schemas=MERGED_SCHEMAS, *, profile=None) -> list[dict[str, Any]]:
    return [check_one(m, s, c, k, profile=profile) for m, s, c, k in schemas]


def blocking(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows that must stop a generation run.

    `unchecked` blocks as well as `stale`. A gate that cannot run has not
    passed, and the whole point here is that the failure it guards against is
    invisible in the record afterwards.
    """
    return [r for r in rows if r["status"] != IN_SYNC]
