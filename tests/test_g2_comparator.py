"""Negative controls for the D35 identity-only proof (G2 round 2, 2026-11-01)."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts.adhoc import g2_bc1_evidence_20261101 as proof
from data_sheets_schema import bc1_context as bc


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def captures(tmp_path):
    for side, digit in [("before", "a"), ("after", "b")]:
        folder = tmp_path / ".bc1-byte-evidence" / side
        folder.mkdir(parents=True)
        code = {name: digit * 64 for name in ("src/data_sheets_schema/bc1_context.py",
                                             "src/data_sheets_schema/bc1_registration.py")}
        registration = raw({"bounded_carry": {"contract": {"code": code}}})
        (folder / "registration.json").write_bytes(registration)
        packet = {"selection": {"bounded_carry": {"contract": {"code": code}}}}
        packet["sha256"] = sha(raw(packet))
        host = {"payload": {"packet_sha256": packet["sha256"], "worker_id": "worker_0001",
            "shared_context": {"schema": {"classes": {}}, "bundle": "unchanged"},
            "dictionary": {"sha256": "c" * 64}}}
        host["request_sha256"] = sha(raw(host["payload"]))
        schema = bc.SCHEMA_HEADER + raw({"catalog": {"classes": {}}}).decode()
        inner = bc.model_request(host, schema)
        binding = {"registration_sha256": sha(registration), "packet_sha256": packet["sha256"],
                   "inner_request_sha256": sha(raw(inner))}
        content = [{"text": "unchanged"} for _ in range(5)] + [
            {"text": "# Registered audit request identity\n\n" + raw(binding).decode()},
            {"text": "# Exact typed stage request\n\n" + raw(inner).decode()}]
        content[3]["text"] = schema
        payload = raw({"messages": [{"content": content}]})
        (folder / "worker.json").write_bytes(payload)
        capture = {"errors": {}, "payloads": {"typed_audit_worker:w1": {
            "path": str((folder / "worker.json").relative_to(tmp_path)), "bytes": len(payload), "sha256": sha(payload)}},
            "registration_sha256": sha(registration), "source_pins": {str(tmp_path / key): {"sha256": value}
                for key, value in code.items()}, "audit_limits": {}, "calibration": {}, "python": "fixture",
            "packages": {}, "sizing_totals": {"calls": 1}}
        for key, value in (("host_packet", packet), ("host_request", host)):
            path = folder / (key + ".json")
            path.write_bytes(raw(value))
            capture["payloads"]["typed_audit_worker:w1"][key] = {
                "path": str(path.relative_to(tmp_path)), "sha256": sha(raw(value)), "bytes": len(raw(value))}
        (folder / "capture.json").write_bytes(raw(capture))
    return tmp_path


def accepted(root):
    try:
        return proof.compare(root, identity_pin_ruling=True) == 0
    except (ValueError, AssertionError):
        return False


def test_valid_identity_only_control(captures):
    assert accepted(captures)


@pytest.mark.parametrize("damage", ["registration_binding", "registration_metadata", "inner_binding",
                                     "packet_binding", "sizing_totals", "same_length_content"])
def test_tampered_evidence_is_not_accepted(captures, damage):
    folder = captures / ".bc1-byte-evidence/after"
    metadata = json.loads((folder / "capture.json").read_bytes())
    payload = json.loads((folder / "worker.json").read_bytes())
    if damage in {"registration_binding", "inner_binding", "packet_binding"}:
        text = payload["messages"][0]["content"][5]["text"]
        offset = text.index("{")
        binding = json.loads(text[offset:])
        key = {"registration_binding": "registration_sha256", "inner_binding": "inner_request_sha256",
               "packet_binding": "packet_sha256"}[damage]
        binding[key] = "0" * 64
        payload["messages"][0]["content"][5]["text"] = text[:offset] + raw(binding).decode()
    elif damage == "registration_metadata":
        metadata["registration_sha256"] = "0" * 64
    elif damage == "sizing_totals":
        metadata["sizing_totals"]["calls"] += 1
    else:
        payload["messages"][0]["content"][0]["text"] = "Xnchanged"
    changed = raw(payload)
    assert len(changed) == (folder / "worker.json").stat().st_size
    (folder / "worker.json").write_bytes(changed)
    metadata["payloads"]["typed_audit_worker:w1"].update(bytes=len(changed), sha256=sha(changed))
    (folder / "capture.json").write_bytes(raw(metadata))
    assert not accepted(captures)


@pytest.mark.parametrize("damage", [None, "host_packet", "host_request"])
@pytest.mark.parametrize("omission", [False, True])
def test_captured_host_objects_are_rehashed(captures, damage, omission):
    for side in ("before", "after"):
        folder = captures / ".bc1-byte-evidence" / side
        metadata = json.loads((folder / "capture.json").read_bytes())
        payload = json.loads((folder / "worker.json").read_bytes())
        packet = json.loads((folder / "host_packet.json").read_bytes())
        inner = json.loads((folder / "host_request.json").read_bytes())
        if omission:
            # The omission request hashes its payload but carries no packet pin.
            inner = {"payload": {"record": "unchanged", "schema": {"classes": {}}}}
        inner["request_sha256"] = sha(raw(inner["payload"]))
        content = payload["messages"][0]["content"]
        projected = bc.model_request(inner, content[3]["text"])
        binding = {"registration_sha256": metadata["registration_sha256"], "packet_sha256": packet["sha256"],
                   "inner_request_sha256": sha(raw(projected))}
        content[5]["text"] = "# Registered audit request identity\n\n" + raw(binding).decode()
        content[6]["text"] = "# Exact typed stage request\n\n" + raw(projected).decode()
        if side == "after" and damage:
            (packet if damage == "host_packet" else inner)["tampered"] = True
            if damage == "host_request":
                inner["payload"]["tampered"] = True
        info = metadata["payloads"]["typed_audit_worker:w1"]
        for key, value in [("host_packet", packet), ("host_request", inner)]:
            path = folder / (key + ".json")
            data = raw(value)
            path.write_bytes(data)
            info[key] = {"path": str(path.relative_to(captures)), "sha256": sha(data), "bytes": len(data)}
        data = raw(payload)
        (folder / "worker.json").write_bytes(data)
        info.update(sha256=sha(data), bytes=len(data))
        (folder / "capture.json").write_bytes(raw(metadata))
    assert accepted(captures) == (damage is None)


@pytest.mark.parametrize("damage", ["different_worker", "edited_host", "edited_packet"])
def test_consistently_rehashed_host_must_match_wire_and_base(captures, damage):
    assert accepted(captures)
    folder = captures / ".bc1-byte-evidence/after"
    metadata = json.loads((folder / "capture.json").read_bytes())
    payload = json.loads((folder / "worker.json").read_bytes())
    content = payload["messages"][0]["content"]
    packet = json.loads((folder / "host_packet.json").read_bytes())
    host = json.loads((folder / "host_request.json").read_bytes())
    inner = json.loads(content[6]["text"].split("\n\n", 1)[1])
    binding = json.loads(content[5]["text"].split("\n\n", 1)[1])
    if damage == "different_worker":
        host["payload"]["worker_id"] = "worker_9999"
    elif damage == "edited_host":
        host["payload"]["untransmitted_field"] = "only in host request"
    else:
        packet["untransmitted_field"] = "only in host packet"
        packet["sha256"] = sha(raw({key: value for key, value in packet.items() if key != "sha256"}))
        host["payload"]["packet_sha256"] = inner["payload"]["packet_sha256"] = packet["sha256"]
        binding["packet_sha256"] = packet["sha256"]
    host["request_sha256"] = sha(raw(host["payload"]))
    inner["request_sha256"] = host["request_sha256"]
    binding["inner_request_sha256"] = sha(raw(inner))
    content[5]["text"] = "# Registered audit request identity\n\n" + raw(binding).decode()
    content[6]["text"] = "# Exact typed stage request\n\n" + raw(inner).decode()
    info = metadata["payloads"]["typed_audit_worker:w1"]
    for key, value in (("host_packet", packet), ("host_request", host)):
        (folder / (key + ".json")).write_bytes(raw(value))
        info[key].update(bytes=len(raw(value)), sha256=sha(raw(value)))
    assert len(raw(payload)) == (folder / "worker.json").stat().st_size
    (folder / "worker.json").write_bytes(raw(payload))
    info.update(bytes=len(raw(payload)), sha256=sha(raw(payload)))
    (folder / "capture.json").write_bytes(raw(metadata))
    assert not accepted(captures)
