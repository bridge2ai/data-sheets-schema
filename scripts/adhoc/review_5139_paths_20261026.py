#!/usr/bin/env python3
"""Review #5139 path scope and historical compatibility, 2026-10-26.

Inputs: exact cached Git canary records, selected checkout and local source data.
Outputs: bounded JSON observations. Reads historical artifacts through git show;
creates only a new report and temporary synthetic outputs. No provider calls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--history-repo", type=Path, required=True)
    parser.add_argument("--history-ref", default="ada98b56b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    os.chdir(root)
    def offline(*_args, **_kwargs):
        raise AssertionError("network forbidden in #5139 review")
    socket.socket.connect = offline
    from data_sheets_schema import api_runner as api, provenance, replicate_structure
    from data_sheets_schema.evaluation import arm_comparison
    from scripts.build_api_registrations import build_registration
    def git(*items):
        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(args.history_repo), *items])
    history_head = git("rev-parse", args.history_ref).decode().strip()
    result = {"source_head": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "history_head": history_head, "historical": [], "network": "socket connect forbidden"}
    for date in ("2026-10-20a", "2026-10-22a"):
        name = ("data/ATTIC/d4d_concatenated_archived/claudecode_api_core/"
                f"{date}_claude-opus-5-api-generic-v10_rep1/CHORUS_provenance.yaml")
        raw = git("show", f"{history_head}:{name}")
        record = yaml.safe_load(raw)
        inputs = record["inputs"]
        texts, basis = replicate_structure.record_chunk_texts(inputs, root=root)
        result["historical"].append({"record": name, "record_sha256": hashlib.sha256(raw).hexdigest(),
            "input_paths": {"bundle": inputs.get("bundle_path"),
                "chunks": (inputs.get("chunks") or {}).get("path"),
                "source_manifest": (inputs.get("source_manifest") or {}).get("path")},
            "bundle_drift": arm_comparison.bundle_drift(record, root),
            "recovered_chunk_count": None if texts is None else len(texts),
            "recovered_chunk_basis": basis})
    bundle = root / "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
    from data_sheets_schema.chunking import manifest_for
    manifest = root / "data/preprocessed/source_manifest.yaml"
    chunks = manifest_for(bundle, source_manifest=manifest)
    selected = api.RunSpec(project="CHORUS", arm="BASELINE (input documents only)",
        method="claudecode_api", label="review-5139-synthetic", condition="generic",
        bundle=bundle, manifest=manifest, chunk_manifest=chunks,
        runtime=api.RUNTIME, provider="LBL CBORG (proxy to Anthropic)")
    identity = selected.input_identity()
    result["new_runspec"] = {"bundle": str(selected.bundle), "manifest": str(selected.manifest),
        "chunks": str(selected.chunk_manifest), "progress_input_paths": {
            name: None if identity.get(name) is None else identity[name]["path"]
            for name in ("bundle", "source_manifest", "chunks")}}
    with tempfile.TemporaryDirectory(prefix="d4d-5139-synthetic-") as scratch:
        directory = Path(scratch)
        full, core = directory / "CHORUS_d4d.yaml", directory / "CHORUS_d4d_core.yaml"
        full.write_text("id: CHORUS\n")
        core.write_text("id: CHORUS\n")
        record = provenance.build_record("CHORUS", "claudecode_api", "review-5139-synthetic",
            mode="live", input_bundle=selected.bundle, input_verified=True,
            manifest=selected.manifest, chunk_manifest=selected.chunk_manifest,
            outputs={"full": full, "core": core})
        result["new_flat_provenance_paths"] = {
            "bundle": record.data["inputs"]["bundle_path"],
            "chunks": record.data["inputs"]["chunks"]["path"],
            "source_manifest": record.data["inputs"]["source_manifest"]["path"]}
        registration = build_registration(project="CHORUS", label="review-5139-synthetic",
            partition="chorus", registration_path=directory / "registration.json", write_to_disk=False)
        result["new_registration_paths"] = {name: None if registration["inputs"].get(name) is None
            else registration["inputs"][name]["path"]
            for name in ("bundle", "chunk_manifest", "source_manifest", "context")}
        result["registration_written"] = (directory / "registration.json").exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps({"output": str(args.output), "records": len(result["historical"]),
        "source_head": result["source_head"]}))


if __name__ == "__main__":
    main()
