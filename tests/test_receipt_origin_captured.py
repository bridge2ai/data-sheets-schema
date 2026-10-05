"""Captured receipt-origin uses the existing history instrument, without I/O."""
import builtins
import io
import json
import os
import socket
import subprocess
from pathlib import Path

import pytest

from data_sheets_schema import receipt_origin as ro
from tests.test_receipt_origin import Run, PRE, TITLE, LICENSE, WITH_LICENSE, receipt_text


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def fixture(root, mode="phases"):
    run = Run(root)
    run.write(run.receipt, PRE)
    run.write(run.full, "id: fictional\n")
    if mode == "edit":
        run.edit(old_string=TITLE, new_string=TITLE + LICENSE, replace_all=False)
        run.last_receipt = WITH_LICENSE
    elif mode == "phases":
        run.write(run.receipt, WITH_LICENSE)
        run.derive(ok=False)
    run.derive()
    if mode == "phases":
        run.write(run.receipt, receipt_text(
            ("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701"),
                       ("license", "CC BY 4.0 license")]),
            ("c002", [("description", "a multimodal collection")]),
            ("c003", [("creators[0].name", "Fictional creator")]),
        ))
    run.receipt.write_text(run.last_receipt, encoding="utf-8")
    return run


def inputs(run, *, paths=None, extra_aliases=(), receipt_path=None, **at_run):
    paths = paths or [run.transcript()]
    receipt_path = receipt_path or run.receipt
    core = run.receipt.parent / "CHORUS_d4d_core.yaml"
    aliases = tuple((str(path), str(path)) for path in (run.receipt, run.full, core)) + extra_aliases
    return dict(transcripts=tuple((str(path), path.read_bytes()) for path in paths),
                receipt_raw=receipt_path.read_bytes(), receipt_path=str(receipt_path),
                full_path=str(run.full), aliases=aliases, **at_run)


def path_report(value):
    return ro.origin([Path(name) for name, _ in value["transcripts"]], Path(value["receipt_path"]),
                     Path(value["full_path"]),
                     **{key: Path(value[key]) for key in ("receipt_at_run", "full_at_run") if key in value})


@pytest.mark.parametrize("mode", ["phases", "edit", "simple"])
def test_complete_report_and_summary_equal_existing_path_reader(tmp_path, mode):
    run = fixture(tmp_path / mode, mode)
    value = inputs(run)
    expected = path_report(value)
    captured = ro.origin_captured(**value)
    assert expected["status"] == "checked"
    assert wire(captured) == wire(expected)
    assert ro.summary(captured) == ro.summary(expected)
    if mode == "phases":
        assert captured["origin"] == {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 1}


def test_recorded_alias_with_different_basename_and_moved_artifact(tmp_path):
    run = fixture(tmp_path / "alias")
    alias = run.root / "another-name.yaml"
    alias.symlink_to(run.receipt)
    run.write(alias, run.last_receipt)
    moved = run.root / "archived.yaml"
    moved.write_bytes(run.receipt.read_bytes())
    value = inputs(run, extra_aliases=((str(alias), str(run.receipt)),), receipt_path=moved,
                   receipt_at_run=str(run.receipt), full_at_run=str(run.full))
    expected = path_report(value)
    assert expected["status"] == "checked"
    assert wire(ro.origin_captured(**value)) == wire(expected)


def test_ordered_resumed_transcripts_keep_physical_line_and_hash_basis(tmp_path):
    run = fixture(tmp_path / "resumed", "edit")
    paths = [run.transcript("one.jsonl", run.events[:5]),
             run.transcript("two.jsonl", [run.events[0]] + run.events[5:])]
    value = inputs(run, paths=paths)
    expected = path_report(value)
    assert expected["status"] == "checked"
    assert wire(ro.origin_captured(**value)) == wire(expected)


@pytest.mark.parametrize("mutation", ["truncated", "duplicate", "receipt", "non_utf8"])
def test_captured_unknowns_retain_existing_diagnostics_and_do_not_classify(tmp_path, mutation):
    run = fixture(tmp_path / mutation)
    path = run.transcript()
    if mutation == "truncated":
        path.write_bytes(path.read_bytes() + b'{')
    elif mutation == "duplicate":
        run.events.append(run.events[1])
        path = run.transcript()
    elif mutation == "non_utf8":
        path.write_bytes(b'\xff\n')
    else:
        run.receipt.write_bytes(run.receipt.read_bytes() + b"# altered\n")
    value = inputs(run, paths=[path])
    expected = path_report(value)
    captured = ro.origin_captured(**value)
    assert expected["status"] == "unknown"
    assert wire(captured) == wire(expected)
    assert "origin" not in captured


def test_unrecorded_different_basename_alias_is_unknown_not_an_ignored_write(tmp_path):
    run = fixture(tmp_path / "unrecorded")
    alias = run.root / "unresolved-other-name.yaml"
    run.write(alias, "possibly a receipt mutation\n")
    value = inputs(run)
    captured = ro.origin_captured(**value)
    assert captured["status"] == "unknown"
    assert "origin" not in captured
    assert any("captured path identity" in reason for reason in captured["reasons"])
    assert not any("relative path with no working directory" in reason for reason in captured["reasons"])


def test_known_other_identity_is_not_target_even_with_same_basename(tmp_path):
    run = fixture(tmp_path / "known-other")
    other = run.root / "elsewhere" / run.receipt.name
    run.write(other, "an unrelated file\n")
    value = inputs(run, extra_aliases=((str(other), str(other)),))
    expected = path_report(value)
    assert expected["status"] == "checked"
    assert wire(ro.origin_captured(**value)) == wire(expected)


def test_conflicting_consulted_identity_is_unknown_but_unused_conflict_is_not_global(tmp_path):
    run = fixture(tmp_path / "conflict")
    other = str(run.root / "unrelated.yaml")
    unused = str(run.root / "unused.yaml")
    value = inputs(run, extra_aliases=((unused, other), (unused, str(run.receipt))))
    assert ro.origin_captured(**value)["status"] == "checked"
    run.write(Path(unused), run.last_receipt)
    value = inputs(run, extra_aliases=((unused, other), (unused, str(run.receipt))))
    result = ro.origin_captured(**value)
    assert result["status"] == "unknown"
    assert "origin" not in result


def test_relative_paths_without_recorded_cwd_never_use_host_cwd_or_basename(tmp_path):
    run = fixture(tmp_path / "no-cwd")
    del run.events[0]["cwd"]
    for event in run.events:
        for item in event.get("message", {}).get("content", []):
            if item.get("name") == "Write":
                item["input"]["file_path"] = Path(item["input"]["file_path"]).name
    result = ro.origin_captured(**inputs(run))
    assert result["status"] == "unknown"
    assert result["receipt"]["writes"] == 0
    assert "origin" not in result
    assert any("captured path identity" in reason for reason in result["reasons"])


def test_captured_route_is_independent_of_filesystem_cwd_process_and_network(tmp_path, monkeypatch):
    run = fixture(tmp_path / "trapped", "edit")
    value = inputs(run)
    expected = path_report(value)
    def forbidden(*args, **kwargs):
        raise AssertionError("captured route attempted ambient I/O or path resolution")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (io, "open"), (os, "open"), (os, "stat"),
                            (os, "lstat"), (os, "readlink"), (os, "getcwd"), (os, "getcwdb"),
                            (os.path, "realpath"), (os.path, "abspath"), (Path, "read_bytes"),
                            (Path, "resolve"), (Path, "cwd"), (subprocess, "Popen"),
                            (os, "system"), (socket, "socket"), (socket, "getaddrinfo")):
            patch.setattr(owner, name, forbidden)
        patch.setattr(ro, "_Target", forbidden)
        captured = ro.origin_captured(**value)
    assert wire(captured) == wire(expected)


@pytest.mark.parametrize("field,value", [
    ("transcripts", []), ("transcripts", (("relative.jsonl", b"{}\n"),)),
    ("receipt_raw", bytearray(b"receipt")), ("aliases", []),
    ("aliases", (("relative", "/physical"),)), ("full_path", "relative.yaml"),
])
def test_captured_input_contract_rejects_mutable_or_ambient_identity(tmp_path, field, value):
    captured = inputs(fixture(tmp_path / field))
    captured[field] = value
    with pytest.raises(ValueError):
        ro.origin_captured(**captured)


def test_legacy_acquisition_order_and_missing_receipt_reason_stay_exact(tmp_path, monkeypatch):
    run = fixture(tmp_path / "order", "simple")
    path = run.transcript()
    missing = run.root / "not-captured.yaml"
    order = []
    read_bytes = Path.read_bytes
    def observed_read(value):
        order.append("transcript" if value == path else "receipt")
        return read_bytes(value)
    monkeypatch.setattr(Path, "read_bytes", observed_read)
    for name in ("_pair", "_Target", "_history", "_boundaries"):
        original = getattr(ro, name)
        def observed(*args, _name=name, _original=original, **kwargs):
            order.append(_name)
            return _original(*args, **kwargs)
        monkeypatch.setattr(ro, name, observed)
    result = ro.origin([path], missing, run.full, receipt_at_run=run.receipt)
    assert order == ["transcript", "_pair", "_Target", "_Target", "_history", "_boundaries", "receipt"]
    assert result["status"] == "unknown"
    assert result["reasons"] == ["the receipt cannot be read (FileNotFoundError)"]
    assert result["receipt"]["sha256"] is None
    assert result["receipt"]["rebuilt_sha256"] is not None
