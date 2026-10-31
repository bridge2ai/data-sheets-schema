#!/usr/bin/env python3
"""#5212 round 3, 2026-10-31: pin offline tests to a complete git archive.

Inputs: local commit and new scratch-copy name. Output: archive checkout with
isolated index/HEAD, read-only local object alternates, pinned submodule, and
a small preparation manifest. Never fetches or alters the source checkout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("ref")
parser.add_argument("name")
args = parser.parse_args()
destination = SCRATCH / args.name
assert destination.parent == SCRATCH and not destination.exists()


def git(*command, cwd=ROOT):
    return subprocess.check_output(["git", *command], cwd=cwd, text=True).strip()


commit = git("rev-parse", args.ref + "^{commit}")
destination.mkdir()
archive = SCRATCH / (args.name + ".tar")
subprocess.run(["git", "archive", "--format=tar", "--output", str(archive), commit], cwd=ROOT, check=True)
with tarfile.open(archive) as stream:
    stream.extractall(destination, filter="data")
common = Path(git("rev-parse", "--git-common-dir"))
common = (ROOT / common).resolve()
git("init", "--quiet", cwd=destination)
(destination / ".git/objects/info/alternates").write_text(str(common / "objects") + "\n")
(destination / ".git/HEAD").write_text(commit + "\n")
git("read-tree", commit, cwd=destination)
# All local refs are read-only evidence for tests; none is fetched or moved in
# the source repository. Keep origin/main available for CI comparison tests.
main = git("rev-parse", "refs/remotes/origin/main")
git("update-ref", "refs/remotes/origin/main", main, cwd=destination)
submodule = git("ls-tree", commit, "fairscape_models").split()[2]
subarchive = SCRATCH / (args.name + "-fairscape.tar")
subgit = git("rev-parse", "--absolute-git-dir", cwd=common.parent / "fairscape_models")
subprocess.run(["git", "--git-dir=" + subgit,
                "archive", "--format=tar", "--output", str(subarchive), submodule], check=True)
with tarfile.open(subarchive) as stream:
    stream.extractall(destination / "fairscape_models", filter="data")
assert not git("diff", "--name-only", commit, cwd=destination)
metadata = {"head": commit, "main": main, "fairscape": submodule,
            "copy": destination.name, "archive": archive.name,
            "archive_bytes": archive.stat().st_size,
            "archive_sha256": hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()}
(SCRATCH / (args.name + "-preparation.json")).write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
