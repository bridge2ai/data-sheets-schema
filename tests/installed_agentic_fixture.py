"""Offline acceptance of commands emitted for an installed agentic run."""
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import yaml


def check_installed_agentic():
    from data_sheets_schema import agent_pin, agentic_observed, chunking, resources
    from data_sheets_schema.api_runner import RunSpec
    from data_sheets_schema.agentic_runtime import playbook_text

    assert not resources.is_checkout()
    assert Path(agentic_observed.__file__).resolve().is_relative_to(resources.PACKAGE_ROOT.resolve())
    bundle = Path("synthetic source with spaces.txt").absolute()
    bundle.write_text("FILE: overview.txt\nA synthetic clinical dataset.\n")
    chunks, mapping = chunking.write_manifest_for(bundle)
    spec = RunSpec(project="EXTERNAL", arm="BASELINE (input documents only)", method="external_agent",
                   bundle=bundle, manifest=None, chunk_manifest=chunks, label="offline_rep1",
                   runtime="Codex CLI", provider="offline", condition="generic_v9")
    assert spec.render_version >= 5
    instruction = spec.instruction
    assert "poetry run" not in instruction
    replay = RunSpec.from_render_spec(spec.render_spec(), project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == instruction
    spec.full_path.parent.mkdir(parents=True)
    spec.full_path.write_text("id: https://example.org/clinical\ntitle: Synthetic clinical fixture\n")
    appendix = instruction.split("## Installed agentic execution", 1)[1]
    commands = re.findall(r"```bash\n(.*?)\n```", appendix, re.S)
    assert len(commands) == 5
    for command in commands:
        args = shlex.split(command)
        assert args[0] == sys.executable
        result = subprocess.run(args, capture_output=True, text=True)
        assert result.returncode == 0, (args, result.stdout, result.stderr)
    assert spec.core_path.is_file()
    view = playbook_text()
    assert "poetry run" not in view
    assert "-m data_sheets_schema.agentic_observed" in view
    # The term validator must be available in the runtime environment. Its
    # ontology lookup behavior is unchanged and is not a source-download test.
    result = subprocess.run([sys.executable, "-c", "from linkml_term_validator.cli import main; main()", "--help"],
                            capture_output=True, text=True)
    assert result.returncode == 0 and "validate-data" in result.stdout, result.stdout + result.stderr

    receipt = spec.report_path.parent / "EXTERNAL_coverage_receipt.yaml"
    receipt.write_text(yaml.safe_dump({"chunks": [{"id": c["id"]} for c in mapping["chunks"]]}))
    transcript = Path("synthetic-transcript.jsonl")
    transcript.write_text(json.dumps({"timestamp": "2026-09-13T00:00:00Z", "message": {
        "id": "offline", "role": "assistant", "usage": {"input_tokens": 7, "output_tokens": 3},
        "content": []}}) + "\n")
    command = [sys.executable, "-m", "data_sheets_schema.agentic_observed", "--bundle", str(bundle),
               "--receipt", str(receipt), "--manifest", str(chunks), str(transcript)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["total_tokens"] == 10 and observed["bundle_lines_read"] == 0
    assert observed["receipt_chunks_unopened"] == len(mapping["chunks"])

    name = "d4d-rubric10-semantic"
    digest = agent_pin.agent_digest(name)
    result = subprocess.run([sys.executable, "-m", "data_sheets_schema.cli", "agents", "digest"],
                            capture_output=True, text=True)
    assert result.returncode == 0 and digest in result.stdout, result.stdout + result.stderr
    ask = agent_pin.challenge(name)
    assert ask is not None
    preamble = agent_pin.spawn_preamble(name)
    assert digest in preamble and ask["expected"] not in preamble
    agent_pin.verify_echo(name, ask["expected"])
    try:
        agent_pin.verify_echo(name, preamble)
    except agent_pin.StaleAgentDefinition:
        pass
    else:
        raise AssertionError("copying the preamble passed check-echo")
    assert hashlib.sha256(agent_pin.agent_path(name).read_bytes()).hexdigest() == digest
