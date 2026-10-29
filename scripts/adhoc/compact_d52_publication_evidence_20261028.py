#!/usr/bin/env python3
# Purpose: replace D52 publication tarballs with small verified result files.
# Inputs: immutable local Git archive/manifest blobs from the reviewed D52 packet.
# Outputs: per-run compact evidence and hashes/recovery commands for inventories.
# Refs D52 review D3, #2912/#5121; 2026-10-28. Offline; originals never mutated.
"""Copy one archived run at a time; retain exact recovery through Git history."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "4cd8f2a5191d7cb58d7bf639603a820d38e825d5"
PACKET = "notes/d52_scoring_validation_2026-10-28"
OMIT = {"source-before.json", "source-after.json"}


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0")
    return subprocess.check_output(["git", "--no-replace-objects", *args], cwd=ROOT, env=env)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, choices=(1, 2), required=True)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    manifest_raw = git("show", SOURCE + ":" + PACKET + "/manifest.json")
    original = json.loads(manifest_raw)["runs"][args.run - 1]
    archive = original["archive"]
    archive_path = PACKET + "/" + archive["file"]
    raw = git("show", SOURCE + ":" + archive_path)
    if len(raw) != archive["bytes"] or digest(raw) != archive["sha256"]:
        raise ValueError("archive does not match original manifest")
    expected = {entry["path"]: entry for entry in original["entries"]}
    members = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as bundle:
        for member in bundle:
            name = member.name.removeprefix("results/")
            if (member.name != "results/" + name or name in members or name not in expected or Path(name).name != name
                    or not member.isfile() or not 0 <= member.size <= 4_000_000):
                raise ValueError("unexpected or unsafe archive member")
            content = bundle.extractfile(member).read()
            entry = expected[name]
            if (len(content) != entry["bytes"] or digest(content) != entry["sha256"]
                    or member.mode != entry["mode"]):
                raise ValueError("member bytes or mode differ from original manifest")
            members[name] = content
    if set(members) != set(expected) or not OMIT <= set(members):
        raise ValueError("incomplete archive")
    inventories = [json.loads(members[name]) for name in sorted(OMIT)]
    if inventories[0] != inventories[1] or not inventories[0]["tracked_exact"]:
        raise ValueError("original source was not frozen")
    head = inventories[0]["head"]
    if git("rev-parse", head + "^{commit}").decode().strip() != head:
        raise ValueError("source commit unavailable locally")
    result = {
        "format": "d52_compact_publication_v1", "source_commit": SOURCE,
        "original_manifest_sha256": digest(manifest_raw), "original_archive": archive,
        "original_archive_path": archive_path, "tested_head": head,
        "original_evidence_root": original["original_root"],
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "preserved_files": [expected[name] for name in sorted(members.keys() - OMIT)],
        "omitted_inventories": [dict(expected[name], exact_recovery_command=
            f"git show {SOURCE}:{archive_path} | tar -xzOf - results/{name}") for name in sorted(OMIT)],
        "tracked_tree_regeneration_command": f"git ls-tree -r -l {head}",
        "regeneration_scope": "ls-tree regenerates tracked paths/blob identities/sizes; exact archived JSON includes run metadata and is recovered by the commands above",
        "validation_outcomes": "original result files preserved verbatim; no new test or pass count inferred",
    }
    if args.plan:
        print(json.dumps({key: result[key] for key in ("tested_head", "original_archive", "preserved_files", "omitted_inventories")}, indent=2))
        return
    target = ROOT / PACKET / "compact" / f"run-{args.run:02}"
    if any(path.is_symlink() for path in (target, *target.parents)):
        raise ValueError("symlink destination refused")
    target.mkdir(parents=True, exist_ok=False)
    for name in sorted(members.keys() - OMIT):
        destination = target / name
        with destination.open("xb") as stream:
            stream.write(members[name])
        destination.chmod(expected[name]["mode"])
        if destination.read_bytes() != members[name]:
            raise ValueError("persisted result differs")
    manifest = target / "compact-manifest.json"
    with manifest.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if json.loads(manifest.read_bytes()) != result:
        raise ValueError("persisted manifest differs")
    print(json.dumps({"path": str(target), "manifest_sha256": digest(manifest.read_bytes()),
                      "retained_bytes": sum(len(members[n]) for n in members.keys() - OMIT)}, sort_keys=True))


if __name__ == "__main__":
    main()
