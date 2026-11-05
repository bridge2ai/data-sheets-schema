#!/usr/bin/env python3
"""#5494 offline scanner control, 2026-11-05.

Inputs: pinned local source archive, optional scanner-only working-tree overlay,
and the retained 24-finding reference. Outputs: fresh clean/planted archives and
scanner reports plus byte digests. Explicit test actions freeze a full source
snapshot and delegate bounded offline pytest to the existing validation driver.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = "d0974d4bcc0f254272ec5a95e94d83ae801bbd38"
EXEC = ROOT.parent
SCRATCH = EXEC / "scratch-codex-5494-20261105"
EVIDENCE = EXEC / "plans/reviews/codex_5448_5494_2026-11-05/5494"
REFERENCE = EXEC / "plans/reviews/pr5213_main_merge_2026-11-04/scanner/audit.json"
SCANNER = ".claude/skills/d4d-generation-specificity-audit/scan.py"
ASSET = "src/data_sheets_schema/omission_inventory_v1/policy.md"
INPUTS = (".claude", ".github", "src", "notes", "scripts", "tests", "docs", "utils",
          "CLAUDE.md", "pyproject.toml", "Makefile", "data/preprocessed/source_manifest.yaml")
OVERLAY = (SCANNER, ".claude/skills/d4d-generation-specificity-audit/SKILL.md",
           "tests/test_generation_specificity_skill.py", "scripts/adhoc/" + Path(__file__).name)
TEST_FILE = "tests/test_generation_specificity_skill.py"
TEST_DRIVER = "scripts/adhoc/bc1_g2_validate_20261103.py"
TEST_LAUNCHER = "scripts/adhoc/g2_bc1_offline_20261101.py"
SANDBOX = '(version 1) (allow default) (deny network*) (deny file-write* (subpath (param "TREE")))'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": size}


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise RuntimeError("evidence persistence failed")


def clean_env():
    """Carry only OS display/locale identity, never provider or Python settings."""
    env = {key: os.environ[key] for key in
           ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "__CF_USER_TEXT_ENCODING")
           if key in os.environ}
    env.update(PATH="/usr/bin:/bin:/usr/sbin:/sbin", GIT_NO_LAZY_FETCH="1",
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_OPTIONAL_LOCKS="0",
               GIT_ALLOW_PROTOCOL="", PYTHONDONTWRITEBYTECODE="1", PIP_NO_INDEX="1", UV_OFFLINE="1")
    return env


def label(value):
    if not value or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise ValueError("snapshot and run names must be short lowercase labels")
    return value


def census(tree):
    """Exact snapshot contents, including hidden/ignored files and symlink text."""
    files = {}
    for path in sorted(tree.rglob("*")):
        rel = path.relative_to(tree).as_posix()
        if rel == ".g2-archive.json":
            continue
        if path.is_symlink():
            files[rel] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_dir():
            files[rel] = {"kind": "directory"}
        elif path.is_file():
            files[rel] = {"kind": "file", **{k: v for k, v in pin(path).items() if k != "path"}}
        else:
            raise RuntimeError("nonregular snapshot member: " + rel)
    return files


def test_paths(snapshot):
    name = "tests-" + label(snapshot)
    return SCRATCH / name / "tree", EVIDENCE / name


def prepare_tests(snapshot):
    tree, evidence = test_paths(snapshot)
    tree.parent.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    archive = tree.parent / "source.tar"
    command = ["git", "--no-replace-objects", "-c", "protocol.allow=never", "-C", str(ROOT),
               "archive", "--format=tar", BASE]
    with archive.open("xb") as stream:
        subprocess.run(command, check=True, stdout=stream, env=clean_env(), timeout=600)
    tree.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(tree, filter="data")
    sources = {name: pin(ROOT / name) for name in OVERLAY}
    for name in OVERLAY:
        destination = tree / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
        if pin(destination)["sha256"] != sources[name]["sha256"] or pin(ROOT / name) != sources[name]:
            raise RuntimeError("source overlay changed during snapshot: " + name)
    manifest = {"base": BASE, "tree": str(tree), "archive": pin(archive), "archive_command": command,
                "copied_sources": sources, "files": census(tree)}
    save(evidence / "manifest.json", manifest)
    save(tree / ".g2-archive.json", {"commit": BASE, "snapshot_manifest": pin(evidence / "manifest.json")})
    verify_snapshot(snapshot)
    print(json.dumps(pin(evidence / "manifest.json")), flush=True)


def verify_snapshot(snapshot):
    tree, evidence = test_paths(snapshot)
    if tree.resolve() != tree or evidence.resolve() != evidence:
        raise RuntimeError("test paths must be physical task-local paths")
    identity = {"commit": BASE, "snapshot_manifest": pin(evidence / "manifest.json")}
    manifest = json.loads((evidence / "manifest.json").read_bytes())
    if json.loads((tree / ".g2-archive.json").read_bytes()) != identity:
        raise RuntimeError("snapshot identity changed")
    if manifest["base"] != BASE or manifest["tree"] != str(tree) or census(tree) != manifest["files"]:
        raise RuntimeError("snapshot contents changed")
    if any(pin(ROOT / name) != expected for name, expected in manifest["copied_sources"].items()):
        raise RuntimeError("authoring overlay changed after snapshot")
    return tree, evidence, identity


def canary_proof(evidence, name, identity):
    directory = evidence / label(name)
    request = json.loads((evidence / (name + ".request.json")).read_bytes())
    result = json.loads((directory / "result.json").read_bytes())
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    if (not request["canary"] or request["identity"] != identity or len(request["nodes"]) != 1
            or result["identity"] != identity
            or result["returncode"] != 0 or len(events) != 3
            or {row["when"] for row in events} != {"setup", "call", "teardown"}
            or any(row["outcome"] != "passed" or row["nodeid"] != request["nodes"][0] for row in events)
            or sum(int(suite["tests"]) for suite in result["suites"]) != 1):
        raise RuntimeError("one-test canary lacks successful persisted evidence")
    for name in ("pytest.log", "junit.xml", "started.json", "result.json", "events.jsonl"):
        if not (directory / name).is_file() or not (directory / name).stat().st_size:
            raise RuntimeError("missing canary artifact: " + name)


def run_tests(args):
    tree, evidence, identity = verify_snapshot(args.snapshot)
    name = label(args.name)
    nodes = args.node or []
    if (not nodes or len(set(nodes)) != len(nodes)
            or any(node != TEST_FILE and not node.startswith(TEST_FILE + "::") for node in nodes)):
        raise ValueError("only explicit scanner-test nodes or its whole file are accepted")
    if args.canary:
        if len(nodes) != 1 or "::" not in nodes[0] or args.canary_run:
            raise ValueError("the canary must be exactly one node")
    else:
        canary_proof(evidence, args.canary_run, identity)
    output = evidence / name
    if output.exists():
        raise RuntimeError("test output already exists: " + str(output))
    command = ["/usr/bin/sandbox-exec", "-p", SANDBOX, "-D", "TREE=" + str(tree),
               sys.executable, "-S", "-B", str(tree / TEST_DRIVER), "test", str(tree),
               "--output", str(output), *nodes, "-q", "-n", "2", "--dist=load", "--maxschedchunk=1"]
    env = clean_env()
    save(evidence / (name + ".request.json"), {"identity": identity, "command": command,
         "environment_keys": sorted(env), "nodes": nodes, "canary": args.canary,
         "canary_run": args.canary_run, "workers": 2, "deadline_seconds": 3600,
         "driver": pin(tree / TEST_DRIVER), "launcher": pin(tree / TEST_LAUNCHER)})
    completed = subprocess.run(command, cwd=tree, env=env)
    verify_snapshot(args.snapshot)
    result = json.loads((output / "result.json").read_bytes())
    if result["identity"] != identity or result["returncode"] != completed.returncode:
        raise RuntimeError("driver/process identity or status mismatch")
    save(evidence / (name + ".verification.json"), {"snapshot_unchanged": True, "identity": identity,
         "returncode": completed.returncode, "artifacts": {path.name: pin(path) for path in output.iterdir()
             if path.is_file()}})
    if args.canary and completed.returncode == 0:
        canary_proof(evidence, name, identity)
    return completed.returncode


def scan_controls(args):
    scratch, evidence = SCRATCH / args.phase, EVIDENCE / args.phase
    if ROOT.name != "codex-5494" or ROOT.resolve() != ROOT:
        raise RuntimeError("run only from the assigned literal worktree")
    scratch.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
               GIT_OPTIONAL_LOCKS="0", GIT_ALLOW_PROTOCOL="", PYTHONDONTWRITEBYTECODE="1")
    archive = scratch / "source.tar"
    command = ["git", "--no-replace-objects", "-c", "protocol.allow=never", "-C", str(ROOT),
               "archive", "--format=tar", BASE, *INPUTS]
    with archive.open("xb") as stream:
        subprocess.run(command, check=True, stdout=stream, env=env, timeout=600)
    expected = json.loads(REFERENCE.read_bytes())["violations"]
    if len(expected) != 24:
        raise RuntimeError("the selected reference does not contain exactly 24 findings")
    results = {}
    for variant in ("clean", "planted"):
        tree = scratch / variant
        tree.mkdir()
        with tarfile.open(archive) as bundle:
            bundle.extractall(tree, filter="data")
        if args.phase != "before":
            for name in OVERLAY:
                destination = tree / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, destination)
        original = (tree / ASSET).read_bytes()
        if variant == "planted":
            (tree / ASSET).write_bytes(original + b"\nOffline planted scanner control: CHORUS.\n")
        report_dir = evidence / variant
        report_dir.mkdir()
        cmd = [sys.executable, "-B", str(tree / SCANNER), "--root", str(tree),
               "--report", str(report_dir / "audit.md"), "--json", str(report_dir / "audit.json")]
        save(report_dir / "started.json", {"command": cmd, "base": BASE, "archive": pin(archive),
             "helper": pin(Path(__file__)), "scanner": pin(tree / SCANNER),
             "asset_before_sha256": sha(original), "asset_selected": pin(tree / ASSET)})
        with (report_dir / "stdout.txt").open("xb") as out, (report_dir / "stderr.txt").open("xb") as err:
            completed = subprocess.run(cmd, cwd=tree, env=env, stdout=out, stderr=err, timeout=3600)
        if completed.returncode not in (0, 1):
            raise RuntimeError("scanner did not complete: " + str(report_dir))
        result = json.loads((report_dir / "audit.json").read_bytes())
        if completed.returncode != 1 or result["exit"] != 1:
            raise RuntimeError("the retained/planted violations must fail the audit: " + str(report_dir))
        added = [row for row in result["violations"] if row["path"] == ASSET]
        retained = [row for row in result["violations"] if row["path"] != ASSET]
        if retained != expected or (variant == "clean" and added):
            raise RuntimeError("STOP: clean violation array changed; inspect " + str(report_dir))
        should_detect = args.phase != "before" and variant == "planted"
        if bool(added) != should_detect:
            raise RuntimeError("planted-control expectation differs: " + str(report_dir))
        results[variant] = {"exit": completed.returncode, "report": pin(report_dir / "audit.json"),
            "violations": len(result["violations"]), "planted_findings": added,
            "surfaces": len(result["surfaces"]),
            "python_sources": len(result["facts"]["python_sources"]),
            "model_facing_assets": result["facts"].get("model_facing_assets", {}),
            "asset_discovered": ASSET in result["surfaces"]}
    save(evidence / "result.json", {"base": BASE, "phase": args.phase, "reference": pin(REFERENCE),
         "helper": pin(Path(__file__)), "archive": pin(archive), "results": results})
    print(json.dumps(pin(evidence / "result.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after", "after-review", "after-final", "prepare-tests", "test"))
    parser.add_argument("--snapshot")
    parser.add_argument("--name")
    parser.add_argument("--node", action="append")
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--canary-run")
    args = parser.parse_args()
    if ROOT.name != "codex-5494" or ROOT.resolve() != ROOT:
        raise RuntimeError("run only from the assigned literal worktree")
    if args.phase == "prepare-tests":
        prepare_tests(args.snapshot)
    elif args.phase == "test":
        raise SystemExit(run_tests(args))
    else:
        scan_controls(args)
