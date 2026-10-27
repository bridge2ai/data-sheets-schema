"""Public BC1 API pipeline with scripted declarations, 2026-10-27.

The protected hook is compiled in memory by the shared test fixture. This is
real controller/receipt/evidence/assembly/report execution under that explicit
simulation, never installed-source acceptance or scientific evaluation.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket

import pytest
import yaml

from data_sheets_schema import api_runner as api, bc1_audit as audit, bc1_codec as codec
from data_sheets_schema import bc1_runtime as runtime, receipt_completion as receipts
from data_sheets_schema import shared_generation as shared, usage_ledger as ledger
from tests.test_bc1_selection import simulated_hooks, registered  # noqa: F401
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_runtime import Script, SOURCE, response, scripted_client, files
from tests.test_source_review import review_for


@pytest.fixture
def external(tmp_path):
    # Align the actual bundle with the existing scripted FULL/SOURCE fixtures.
    return specification(tmp_path)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(api, "provider_identity", lambda: {"provider": None, "base_url": None, "key_env": None})
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)


class BC1Script(Script):
    """Only BC1 responses differ; every declaration derives from the wire."""
    def create(self, **kwargs):
        blocks = [part["text"] for part in kwargs["messages"][-1]["content"]]
        exact = next((s for s in blocks if s.startswith("# Exact BC1 stage request\n\n")), None)
        if exact is None:
            return super().create(**kwargs)
        inner = json.loads(exact.split("\n\n", 1)[1])
        payload = inner["payload"]
        kind = inner.get("kind")
        phase = {"bc1_worker_request_v1": runtime.WORKER_PHASE,
                 "bc1_stage_request_v1": runtime.INTEGRATION_PHASE}.get(kind, runtime.OMISSION_PHASE)
        self.calls.append(deepcopy(kwargs))
        self.phases.append(phase)
        if phase == runtime.OMISSION_PHASE:
            return response({"format": "omission_inventory_v1", "request_sha256": inner["request_sha256"],
                "chunks": [{"chunk": row["chunk"], "status": "no_omission",
                            "reason": "No omission proposed by this scripted structural fixture.",
                            "candidates": []} for row in payload["chunks"]]})
        if phase == runtime.WORKER_PHASE:
            review = review_for(payload["shared_context"]["original_full"], chunks=SOURCE)
            review["values"] = [row for row in review["values"] if row["path"] in payload["assignment"]["paths"]]
            value = {"findings": [], "summary": "Scripted declarations; scientific support remains unverified.",
                     "source_review": review}
            maximum = codec.WORKER_BYTES
        else:
            value = {"kind": "bc1_stage_delta_v1", "stage_id": payload["stage_id"],
                "prior_state_sha256": payload["prior_state_sha256"],
                "current_row_index_sha256": payload["current_row_index_sha256"],
                "retain_other_rows_from_index_sha256": payload["current_row_index_sha256"],
                "row_replacements": [], "finding_decisions": [], "new_findings": [],
                "omission_dispositions": [], "summary": "Explicit scripted retention; no scientific certification."}
            maximum = codec.INTEGRATION_BYTES
        return response(codec.encode_candidate(value, dictionary=payload["dictionary"], max_bytes=maximum).decode())


def test_public_bc1_pipeline_multiple_groups_final_and_completed_replay(registered):
    reg = json.loads(registered.shared_generation_registration)
    reg["audit_limits"]["max_paths"] = 2
    raw = shared.canonical(reg)
    Path(reg["registration_path"]).write_bytes(raw)
    spec = replace(registered, shared_generation_registration=raw.decode())
    messages = BC1Script(spec)
    result = api.execute(spec, client=scripted_client(messages))
    assert result["validation_problems"] == []
    state = runtime._state(spec)
    assert state["state"] == "accepted"
    packet = receipts._load(state["packet"])
    assert len(packet["plan"]["workers"]) > 2
    assert len(packet["groups"]) > 1
    expected = (["full", receipts.PHASE] + [runtime.WORKER_PHASE] * len(packet["plan"]["workers"])
                + [runtime.OMISSION_PHASE] + [runtime.INTEGRATION_PHASE] * (len(packet["groups"]) + 1)
                + ["reconcile_full", "report"])
    assert messages.phases == expected
    assert [row["phase"] for row in result["usage"]] == expected
    group_calls = [row for row in state["stages"] if row["selection"]["phase"] == runtime.INTEGRATION_PHASE]
    assert [row["selection"]["stage_id"] for row in group_calls] == [g["id"] for g in packet["groups"]] + ["final"]
    assembly = receipts._load(state["assembly"])
    checked = audit.check(assembly)
    assert checked["passed"] and checked["independently_reconstructed"]
    assert checked["scientific_support"] == "unverified"
    complete = audit.audit_bytes(assembly).decode()
    projected = audit.project_bytes(assembly).decode()
    reconcile = messages.calls[expected.index("reconcile_full")]
    blocks = [part["text"] for part in reconcile["messages"][0]["content"]]
    assert api.CARRY_LABEL.format(name="Audit findings") + projected in blocks
    assert api.CARRY_LABEL.format(name="Audit findings") + complete not in blocks
    record = yaml.safe_load(spec.provenance_path.read_bytes())
    assert record["shared_generation"]["assembly_sha256"] == assembly["sha256"]
    assert record["receipt_completion"]["counts"]["unsupported"] > 0
    before = files(spec)
    before_usage = deepcopy(ledger._read(spec))
    replay_messages = BC1Script(spec)
    replay = api.execute(replace(spec), client=scripted_client(replay_messages))
    assert replay["already_complete"]
    assert replay_messages.calls == [] and replay_messages.count_calls == []
    assert ledger._read(spec) == before_usage and files(spec) == before
