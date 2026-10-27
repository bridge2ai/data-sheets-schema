#!/usr/bin/env python3
# Purpose: losslessly archive completed installed-D38 render and focused tests.
# Inputs: frozen-render evidence, its log, passing focused log/JUnit, tested head.
# Outputs: deterministic gzip/tar, exact file manifest and small evidence copies.
# Refs #4354, #5170; 2026-10-26. No tests, provider calls or production mutation.
"""Preserve immutable offline evidence without changing its original directory."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import tarfile
import xml.etree.ElementTree as ET


def read(path):
    path = Path(path)
    if path.resolve(strict=True) != path or not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
        raise ValueError("evidence must be a physical regular file: " + str(path))
    raw = path.read_bytes()
    if len(raw) > 32_000_000:
        raise ValueError("unexpectedly large evidence file")
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink in evidence: " + str(path))
        if path.is_dir():
            continue
        raw = read(path)
        files[path.relative_to(root).as_posix()] = raw
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tree", "tested-head", "render", "render-log", "test-log", "test-xml", "destination"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    tree, render, target = map(Path, (args.tree, args.render, args.destination))
    if tree.resolve(strict=True) != tree or render.resolve(strict=True) != render:
        raise ValueError("source roots must be physical and absolute")
    if target.exists() or target.is_symlink() or not target.is_relative_to(tree / "notes"):
        raise ValueError("fresh destination under owned notes required")
    paths = ("src", "tests", "scripts/adhoc/native_n2_installed_d38_20261026.py",
             "scripts/adhoc/native_n2_render_parity_20261025.py")
    changed = subprocess.check_output(
        ["git", "--no-replace-objects", "diff", "--name-only", "--no-ext-diff", "--no-textconv",
         args.tested_head, "--", *paths], cwd=tree,
    )
    if changed:
        raise ValueError("tested production/test/render helper bytes changed")
    captured = inventory(render)
    report = json.loads(captured["report.json"])
    if (report["source"]["head"] != args.tested_head
            or report["status"] != "verified_installed_assets_and_full_offline_render"
            or report["source_and_inputs_unchanged"] is not True):
        raise ValueError("render did not verify the selected source")
    copies = {"render.log": read(Path(args.render_log)), "focused.log": read(Path(args.test_log)),
              "focused.xml": read(Path(args.test_xml)), "render-report.json": captured["report.json"]}
    suites = ET.fromstring(copies["focused.xml"])
    counts = {name: sum(int(s.attrib.get(name, "0")) for s in suites.iter("testsuite"))
              for name in ("tests", "errors", "failures", "skipped")}
    if counts != {"tests": 27, "errors": 0, "failures": 0, "skipped": 0}:
        raise ValueError("focused evidence does not contain exactly the 27 passing checks")
    target.mkdir(parents=True, exist_ok=False)
    archive = target / "installed-render.tar.gz"
    with archive.open("xb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w|") as tar:
            for name, raw in captured.items():
                info = tarfile.TarInfo("installed-render/" + name)
                info.size, info.mode, info.mtime = len(raw), stat.S_IMODE((render / name).stat().st_mode), 0
                tar.addfile(info, io.BytesIO(raw))
    with tarfile.open(archive, "r:gz") as tar:
        recovered = {}
        for member in tar:
            if not member.isfile() or not member.name.startswith("installed-render/"):
                raise ValueError("unexpected archive entry")
            recovered[member.name[len("installed-render/"):]] = tar.extractfile(member).read()
    if recovered != captured or inventory(render) != captured:
        raise ValueError("archive roundtrip/source preservation failed")
    for name, raw in copies.items():
        with (target / name).open("xb") as output:
            output.write(raw)
    manifest = {"scope": "exact_evidence_preservation_not_new_test_or_runtime_acceptance",
                "tested_head": args.tested_head, "argv": vars(args),
                "helper": {"path": str(Path(__file__).resolve()), "sha256": sha(read(Path(__file__).resolve()))},
                "tested_paths_unchanged": list(paths), "focused_counts": counts,
                "source_directory": str(render), "archive_roundtrip_exact": True, "source_unchanged": True,
                "archive": {"file": archive.name, "bytes": archive.stat().st_size, "sha256": sha(read(archive))},
                "entries": [{"path": name, "bytes": len(raw), "sha256": sha(raw),
                             "mode": stat.S_IMODE((render / name).stat().st_mode)} for name, raw in captured.items()],
                "copies": [{"file": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in copies.items()]}
    with (target / "manifest.json").open("x") as output:
        json.dump(manifest, output, sort_keys=True, indent=2)
        output.write("\n")
    print(target / "manifest.json")


if __name__ == "__main__":
    main()
