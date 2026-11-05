# Purpose: can the round-3 recorder write `hash_basis: verified identical to the bytes
#   consumed` for bytes the run did NOT consume? Render an agentic instruction in a
#   subdirectory (absolute spellings, which round 3 accepts as evidence), then change the
#   bundle IN PLACE (same path, same inode) before recording with the exact instruction.
#   Also the control: unchanged bytes. And a relative (root) render: must be "asserted".
# Inputs: tests/test_manifest_corpus_root.project_tree (synthetic). Outputs: prints.
# Date: 2026-11-02. Claude round-3 re-check of PR #5213. Offline; run at both heads.
import hashlib

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from data_sheets_schema.resources import resource_path
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


@pytest.mark.parametrize("render_where,edit", [("nested", True), ("nested", False), ("root", False)])
def test_verified_basis_requires_consumed_bytes(project_tree, monkeypatch, render_where, edit):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    chunks = chunks.absolute()
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested if render_where == "nested" else root)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle,
                 manifest=manifest, runtime="Claude Code", provider="offline", chunk_manifest=chunks)
    instruction = spec.instruction
    consumed = hashlib.md5(bundle.read_bytes()).hexdigest()
    prompt = root / "instruction.txt"
    prompt.write_text(instruction)
    paths = {k: getattr(spec, k + "_path").absolute() for k in ("full", "core", "report", "provenance")}
    for k in ("full", "core"):
        paths[k].parent.mkdir(parents=True, exist_ok=True)
        paths[k].write_text(spec.manifest_line + "\n# Source bundle: " + str(bundle)
                            + "\n# Provider: offline\n# Agent runtime: Claude Code\n"
                            + "id: https://example.org/clinical\ntitle: Synthetic\n")
    paths["report"].write_text("# Synthetic report\n")
    if edit:
        with bundle.open("a") as stream:          # same path, same inode
            stream.write("A sentence the run never read.\n")
    monkeypatch.chdir(root)
    result = CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle), "--chunk-manifest", str(chunks),
        "--condition", spec.condition, "--runtime", spec.runtime, "--provider", "offline",
        "--prompt-text", str(prompt), "--run-date", spec.run_date,
        *[a for p in spec.prompt_files for a in ("--prompt", str(resource_path(p)))]])
    print(render_where, "edit" if edit else "same", "exit", result.exit_code,
          (result.output.strip().splitlines() or [""])[-1][:120])
    if result.exit_code == 0:
        data = yaml.safe_load(paths["provenance"].read_text())
        inputs = data["inputs"]
        print("   hash_basis:", inputs.get("hash_basis"),
              "| attested md5 == consumed:", inputs.get("bundle_md5") == consumed,
              "| unverified:", [u.get("field") for u in (data.get("unverified") or [])])
