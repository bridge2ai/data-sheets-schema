#!/usr/bin/env python3
"""Offline package control for root-scope composition, issue 6358, 2026-11-25.

Inputs: checkout bytes, existing backend and validation interpreters. Outputs:
fresh archive copy, wheel, source archive, synthetic fixtures and JSON receipt.
No dependency installation, network access, model or scorer process is used.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile


FROZEN = {
    "rubric10": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    "rubric20": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
}
OVERRIDES = [f"data/rubric/root_scope_v6/{name}_definition_overrides.json" for name in FROZEN]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def backend_build(args):
    backend = importlib.import_module("poetry_dynamic_versioning.backend")
    versions = {name: importlib.metadata.version(name)
                for name in ("poetry-core", "poetry-dynamic-versioning")}
    result = {"interpreter": sys.executable, "backend": backend.__file__,
              "backend_sha256": sha(Path(backend.__file__).read_bytes()),
              "versions": versions,
              "version_override": os.environ["POETRY_DYNAMIC_VERSIONING_BYPASS"],
              "wheel": backend.build_wheel(str(args.dist)),
              "sdist": backend.build_sdist(str(args.dist))}
    write_json(args.dist.parent / "backend.json", result)


def probe(args):
    assert not list(Path.cwd().iterdir()), "probe working directory must start empty"
    extracted = args.extracted.resolve()
    sys.path.insert(0, str(extracted))
    from data_sheets_schema import resources
    from data_sheets_schema.root_scope_definition import compose_definition
    from data_sheets_schema.evaluation.validate import validate_outputs
    assert not resources.is_checkout(), resources.CHECKOUT_ROOT
    assert resources.INSTALL_ROOT == extracted
    rows = []
    for rubric, digest in FROZEN.items():
        composed, provenance = compose_definition(rubric)
        assert sha(composed) == digest == provenance["composed_sha256"]
        resource_paths = {}
        for key in ("source_path", "overrides_path"):
            path = resources.resource_path(provenance[key]).resolve()
            assert path.is_relative_to(extracted)
            resource_paths[key] = str(path.relative_to(extracted))
        fixture = args.fixtures / rubric
        output = fixture / "evaluation.json"
        kwargs = {"input_path": fixture / "external.yaml",
                  "definition_path": fixture / "composed-definition.md",
                  "scope_context_path": fixture / "scope.json", "semantic_version": "6.0"}
        assert validate_outputs([output], **kwargs) == 0
        changed = fixture / "changed-definition.md"
        with changed.open("xb") as handle:
            handle.write(composed + b"\nUnregistered text.\n")
        value = json.loads(output.read_bytes())
        value["metadata"]["instrument_sha256"] = sha(changed.read_bytes())
        invalid = fixture / "changed-evaluation.json"
        write_json(invalid, value)
        kwargs["definition_path"] = changed
        assert validate_outputs([invalid], **kwargs) == 1
        rows.append({"rubric": rubric, "composed_sha256": digest,
                     "resources": resource_paths, "strict_valid_accepted": True,
                     "matching_hash_unregistered_definition_refused": True})
    module_paths = {}
    for name, module in sys.modules.copy().items():
        if name == "data_sheets_schema" or name.startswith("data_sheets_schema."):
            path = getattr(module, "__file__", None)
            if path is not None:
                selected = Path(path).resolve()
                assert selected.is_relative_to(extracted), (name, path)
                module_paths[name] = str(selected.relative_to(extracted))
    assert not list(Path.cwd().iterdir()), "probe wrote in its empty working directory"
    write_json(args.probe_result, {"status": "PASSED", "is_checkout": False,
                                  "install_root": str(extracted), "working_directory": str(Path.cwd()),
                                  "definitions": rows, "module_paths": module_paths})


def build_and_check(args):
    root = args.repo_root.resolve()
    evidence = args.evidence_root.resolve()
    evidence.mkdir(parents=False, exist_ok=False)
    script = Path(__file__).resolve()
    git = lambda *values: subprocess.run(["git", "-C", str(root), *values],
                                        check=True, capture_output=True).stdout
    head = git("rev-parse", "HEAD").decode().strip()
    pathspecs = ["src", "project", "data/rubric", ".claude/agents", ".claude/commands",
                 ".github/workflows", "pyproject.toml", "poetry.lock", "README.md"]
    changed = set(git("diff", "--name-only", "HEAD", "--", *pathspecs).decode().splitlines())
    assert changed <= {"pyproject.toml"}, changed
    source = evidence / "source"
    source.mkdir()
    archive = evidence / "source-input.tar"
    with archive.open("xb") as handle:
        subprocess.run(["git", "-C", str(root), "archive", "HEAD", *pathspecs],
                       stdout=handle, check=True)
    with tarfile.open(archive) as handle:
        handle.extractall(source, filter="data")
    original_project = (root / "pyproject.toml").read_bytes()
    (source / "pyproject.toml").write_bytes(original_project)
    dist = evidence / "dist"
    dist.mkdir()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "HOME": str(evidence / "home"), "TMPDIR": str(evidence / "tmp"),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PIP_NO_INDEX": "1",
           "POETRY_DYNAMIC_VERSIONING_BYPASS": "0.1.0"}
    Path(env["HOME"]).mkdir()
    Path(env["TMPDIR"]).mkdir()
    build_command = [str(args.build_python), "-I", "-B", str(script), "--backend-build", "--dist", str(dist)]
    with (evidence / "build.stdout").open("xb") as stdout, (evidence / "build.stderr").open("xb") as stderr:
        subprocess.run(build_command, cwd=source, env=env, stdout=stdout, stderr=stderr,
                       check=True, timeout=300)
    assert (root / "pyproject.toml").read_bytes() == original_project
    backend = json.loads((evidence / "backend.json").read_bytes())
    wheel, sdist = dist / backend["wheel"], dist / backend["sdist"]
    inventory = {}
    with zipfile.ZipFile(wheel) as handle:
        for relative in OVERRIDES:
            raw = handle.read(relative)
            assert raw == (root / relative).read_bytes()
            inventory[relative] = sha(raw)
        assert not any(name.startswith(".claude/agents/") and name.endswith("-v6.md")
                       for name in handle.namelist())
        extracted = evidence / "wheel-root"
        extracted.mkdir()
        handle.extractall(extracted)
        wheel_rubrics = sorted(name for name in handle.namelist() if name.startswith("data/rubric/"))
    with tarfile.open(sdist) as handle:
        names = handle.getnames()
        prefix = names[0].split("/", 1)[0]
        for relative in OVERRIDES:
            raw = handle.extractfile(f"{prefix}/{relative}").read()
            assert sha(raw) == inventory[relative]
    fixtures = evidence / "fixtures"
    fixtures.mkdir()
    sys.path[:0] = [str(root / "src"), str(root)]
    from tests.test_evaluation.test_root_scope_instrument import root_fixture
    for rubric in FROZEN:
        root_fixture(fixtures / rubric, rubric)
    empty = evidence / "empty-cwd"
    empty.mkdir()
    probe_command = [str(args.validation_python), "-I", "-B", str(script), "--probe",
                     "--extracted", str(extracted), "--fixtures", str(fixtures),
                     "--probe-result", str(evidence / "probe.json")]
    with (evidence / "probe.stdout").open("xb") as stdout, (evidence / "probe.stderr").open("xb") as stderr:
        subprocess.run(probe_command, cwd=empty, env=env, stdout=stdout, stderr=stderr,
                       check=True, timeout=120)
    receipt = {"status": "PASSED", "source_head": head,
               "source_archive_sha256": sha(archive.read_bytes()),
               "pyproject_sha256": sha(original_project), "source_checkout_unchanged": True,
               "helper_sha256": sha(script.read_bytes()), "build_command": build_command,
               "probe_command": probe_command, "backend": backend,
               "build_version_basis": "explicit offline 0.1.0 override; VCS version derivation not tested",
               "wheel": {"path": str(wheel), "sha256": sha(wheel.read_bytes())},
               "sdist": {"path": str(sdist), "sha256": sha(sdist.read_bytes())},
               "override_sha256": inventory, "wheel_rubric_inventory": wheel_rubrics,
               "probe": json.loads((evidence / "probe.json").read_bytes()),
               "dependency_installations": 0, "model_calls": 0}
    write_json(evidence / "result.json", receipt)
    print(json.dumps({"status": "PASSED", "receipt": str(evidence / "result.json")}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--build-python", type=Path)
    parser.add_argument("--validation-python", type=Path)
    parser.add_argument("--backend-build", action="store_true")
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--extracted", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--probe-result", type=Path)
    args = parser.parse_args()
    if args.backend_build:
        backend_build(args)
    elif args.probe:
        probe(args)
    else:
        build_and_check(args)


if __name__ == "__main__":
    main()
