# Purpose: can round-2's owner counterparts (cli/provenance._candidate_specs) admit a
#   DIFFERENT file whose full instruction SHA still matches? Render at corpus R1's root
#   (relative, location-independent spellings), copy R1 to R2 with a changed bundle, and
#   record R1's instruction against R2's absolute inputs from R2's root and from a
#   subdirectory of R2. Compare the attested bundle_md5 with the bytes R1's run read.
# Inputs: tests/test_manifest_corpus_root.project_tree (synthetic). Outputs: prints/asserts.
# Date: 2026-11-01; round-3 copy 2026-11-02 reads the record from R2 and prints hash_basis/unverified.
import hashlib
import shutil

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from data_sheets_schema.resources import resource_path
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


@pytest.mark.parametrize("record_where", ["R2-root", "R2-nested"])
def test_relative_instruction_from_another_corpus(project_tree, monkeypatch, record_where):
    r1, manifest1, bundle1 = project_tree
    monkeypatch.chdir(r1)
    chunks1, _ = chunking.write_manifest_for(bundle1)
    chunks1 = chunks1.absolute()
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", bundle=bundle1,
                 manifest=manifest1, runtime="Claude Code", provider="offline", chunk_manifest=chunks1)
    assert not spec.bundle.is_absolute()            # rendered at R1's root: relative spellings
    instruction = spec.instruction
    consumed_md5 = hashlib.md5(bundle1.read_bytes()).hexdigest()
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    spec.core_path.parent.mkdir(parents=True, exist_ok=True)
    header = (spec.manifest_line + "\n# Source bundle: " + str(spec.bundle)
              + "\n# Provider: offline\n# Agent runtime: Claude Code\n")
    for path in (spec.full_path, spec.core_path):
        path.write_text(header + "id: https://example.org/clinical\ntitle: Synthetic\n")
    spec.report_path.write_text("# Synthetic report\n")
    r2 = r1.parent / (r1.name + "_second_corpus")
    shutil.copytree(r1, r2, symlinks=True)
    bundle2 = r2 / bundle1.relative_to(r1)
    bundle2.write_text(bundle2.read_text() + "A different second corpus sentence.\n")
    manifest2, chunks2 = r2 / manifest1.relative_to(r1), r2 / chunks1.relative_to(r1)
    prompt = r2 / "instruction_from_r1.txt"
    prompt.write_text(instruction)
    nested = r2 / "analysis"
    nested.mkdir(exist_ok=True)
    monkeypatch.chdir(r2 if record_where == "R2-root" else nested)
    result = CliRunner().invoke(cli, ["provenance", "record", "--manifest", str(manifest2),
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--input-bundle", str(bundle2), "--chunk-manifest", str(chunks2),
        "--condition", spec.condition, "--runtime", spec.runtime, "--provider", "offline",
        "--prompt-text", str(prompt), "--run-date", spec.run_date,
        *[a for p in spec.prompt_files for a in ("--prompt", str(resource_path(p)))]])
    line = result.output.strip().splitlines()[-1:] if result.output else ""
    print(record_where, "exit", result.exit_code, line)
    if result.exit_code == 0:
        record_path = r2 / spec.provenance_path.relative_to(r1) if spec.provenance_path.is_absolute() else r2 / spec.provenance_path
        data = yaml.safe_load(record_path.read_text())
        monkeypatch.chdir(r2)
        status = runs.verify_request(spec.method, spec.label, spec.project)
        print(record_where, "verify:", status, "| attested md5 == bytes R1's run read:",
              data["inputs"].get("bundle_md5") == consumed_md5,
              "| recorded spec bundle:", (data["prompts"]["request"].get("spec") or {}).get("bundle"),
              "| inputs.bundle_path:", data["inputs"].get("bundle_path"),
              "| hash_basis:", data["inputs"].get("hash_basis"),
              "| unverified fields:", [u.get("field") for u in (data.get("unverified") or [])])
