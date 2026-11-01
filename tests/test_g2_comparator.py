"""Negative controls for the D35 identity-only proof (G2 round 2, 2026-11-01)."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts.adhoc import g2_bc1_evidence_20261101 as proof


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
        inner = {"request_sha256": digit * 64, "payload": {"packet_sha256": digit * 64}}
        binding = {"registration_sha256": sha(registration), "packet_sha256": digit * 64,
                   "inner_request_sha256": sha(raw(inner))}
        content = [{"text": "unchanged"} for _ in range(5)] + [
            {"text": "# Registered audit request identity\n\n" + raw(binding).decode()},
            {"text": "# Exact typed stage request\n\n" + raw(inner).decode()}]
        payload = raw({"messages": [{"content": content}]})
        (folder / "worker.json").write_bytes(payload)
        capture = {"errors": {}, "payloads": {"typed_audit_worker:w1": {
            "path": str((folder / "worker.json").relative_to(tmp_path)), "bytes": len(payload), "sha256": sha(payload)}},
            "registration_sha256": sha(registration), "source_pins": {str(tmp_path / key): {"sha256": value}
                for key, value in code.items()}, "audit_limits": {}, "calibration": {}, "python": "fixture",
            "packages": {}, "sizing_totals": {"calls": 1}}
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
