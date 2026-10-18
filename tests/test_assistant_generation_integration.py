"""Assistant preparation through the real registered API pipeline, without a provider.

The scripted responses test protocol plumbing, not scientific accuracy. Publication
and workflow permissions are covered separately by the workflow shell harness.
"""
import json
from pathlib import Path

from click.testing import CliRunner
import yaml

from data_sheets_schema import api_runner as api, evidence_assertions as evidence, typed_audit_runtime
from data_sheets_schema import receipt_completion
from data_sheets_schema.cli import cli
from tests import test_shared_generation_runtime as scripted
from tests.test_github_assistant_generation import (
    assistant, offline, prepared_inputs, selected,  # noqa: F401
)


def test_assistant_preparation_runs_actual_shared_cli_to_checked_outputs(prepared_inputs, monkeypatch):
    # Fixture credential activates the production CBORG identity selector; all
    # sockets are forbidden and only the transport is replaced below.
    monkeypatch.setenv("CBORG_API_KEY", "offline-fixture-not-a-credential")
    outputs = assistant.prepare(**prepared_inputs, require_credential=True)
    spec = selected(outputs)
    chunks, identities = evidence.source_chunks_from_bytes(
        spec.bundle.read_bytes(), spec.chunk_manifest.read_bytes())
    assert chunks and identities["bundle"]
    # The protocol correctly rejects a bundle preamble as source support.
    # Scripted declarations quote an actual document chunk, never its wrapper.
    source_chunks = {key: value for key, value in chunks.items()
                     if value["source"] != "<preamble>"}
    monkeypatch.setattr(scripted, "SOURCE", source_chunks)
    client = scripted.client(spec)
    client.base_url = "https://api.cborg.lbl.gov"
    monkeypatch.setattr(api, "_client", lambda: client)
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)

    result = CliRunner().invoke(cli, [
        "api", "run", "--project", prepared_inputs["dataset"],
        "--label", outputs["label"], "--out-dir", outputs["output-dir"],
        "--condition", "generic_v10", "--shared-generation-version", "1",
        "--shared-generation-registration", outputs["registration"], "--yes",
    ])
    assert result.exit_code == 0, result.output + repr(result.exception)
    assert client.messages.phases == [
        "full", receipt_completion.PHASE, typed_audit_runtime.WORKER_PHASE,
        typed_audit_runtime.OMISSION_PHASE, typed_audit_runtime.INTEGRATION_PHASE,
        "reconcile_full", "report",
    ]
    assert client.messages.count_calls
    assert Path(outputs["full-path"]).is_file()
    assert Path(outputs["core-path"]).is_file()
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    assert record["model"]["thinking_requested"] == {"type": "adaptive", "display": "summarized"}
    assert all(call.get("thinking") == {"type": "adaptive", "display": "summarized"} for call in client.messages.calls)
    assert record["shared_generation"]["scientific_support"] == "unverified evaluator declarations"
    assert record["receipt_completion"]["counts"]["unsupported"] > 0
    assert typed_audit_runtime._state(spec)["state"] == "accepted"
    # Keep the actual rendered request and declared authority alongside runtime
    # evidence; a provider mock must not bypass request/registration construction.
    prepared = json.loads((Path(outputs["attempt-dir"]) / "prepared_full_request.json").read_bytes())
    assert client.messages.calls[0]["system"] == prepared["system"]
    assert client.messages.calls[0]["messages"] == prepared["messages"]

    # A repeated CLI invocation refuses the already-used attempt before spending.
    count = len(client.messages.calls)
    repeated = CliRunner().invoke(cli, [
        "api", "run", "--project", prepared_inputs["dataset"],
        "--label", outputs["label"], "--out-dir", outputs["output-dir"],
        "--condition", "generic_v10", "--shared-generation-version", "1",
        "--shared-generation-registration", outputs["registration"], "--yes",
    ])
    assert repeated.exit_code != 0 and "never reused" in repeated.output
    assert len(client.messages.calls) == count
