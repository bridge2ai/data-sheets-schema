"""Opt-in certification of existing attainability files (#3643)."""
from pathlib import Path

import pytest

from data_sheets_schema import attainability as at
from data_sheets_schema import provenance as pv


ROOT = Path(__file__).resolve().parents[1]


def _document(directory, text, check="consent_text", *, stem="B"):
    directory.mkdir(parents=True, exist_ok=True)
    bundle = directory / f"{stem}_preprocessed.txt"
    bundle.write_text(text, encoding="utf-8")
    doc = at.build_document(str(bundle), checks=[at.CHECKS_BY_NAME[check]])
    path = directory / at.file_name(doc)
    # Existing files need not have gone through the newer writer's gate.
    path.write_text(at.dump(doc), encoding="utf-8")
    return path, bundle, doc


def _snapshot(paths):
    return {path: path.read_bytes() for path in paths}


@pytest.mark.parametrize("text,check,item,lines", [
    ("Participants gave con\nsent to take part.\n", "consent_text", "E4.4", "1, 2"),
    ("a data\nprotection\nim\npact assessment was done\n", "ethics_review", "E4.1", "1, 2, 3, 4"),
    ("a data-\n-\n-\n-\n-\n-\nprotec-\ntion impact assessment\n", "ethics_review", "E4.1",
     "1, 2, 3, 4, 5, 6, 7, 8"),
])
def test_valid_existing_absence_is_refused_only_when_gate_selected(tmp_path, capsys, text, check, item, lines):
    path, bundle, doc = _document(tmp_path, text, check)
    before = _snapshot([path, bundle, ROOT / at.RUBRIC_PATHS["rubric10"]])
    assert doc["entries"][0]["status"] == "not_stated_in_source"
    assert at.validate_text(path.read_text(encoding="utf-8"), path.name)[0] == []
    assert at.load(path).document == doc
    assert at.main(["check", str(path)]) == 0
    assert capsys.readouterr().out == f"ok {path} (file on disk): 1 not_stated_in_source\n"

    assert at.main(["check", "--gate", str(path)]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"REFUSED {path}\n  - {item} would be certified not_stated_in_source")
    assert f"by deterministic:{check}" in out and f"on line(s) {lines};" in out
    assert "a curator must read those lines" in out and "\nok " not in out
    # Writer and checker must explain the same refusal; neither may publish a replacement.
    with pytest.raises(at.AttainabilityError) as refusal:
        at.write_document(doc, tmp_path / "unwritten")
    assert all(f"  - {problem}\n" in out for problem in refusal.value.problems)
    assert not (tmp_path / "unwritten").exists()
    assert _snapshot(before) == before
    assert at.load(path).document == doc


def test_gate_checks_only_explicitly_selected_files(tmp_path, monkeypatch, capsys):
    selected, bundle, _ = _document(tmp_path / "selected", "Nothing is stated here.\n")
    excluded, other_bundle, _ = _document(tmp_path / "default", "We got con\nsent.\n")
    monkeypatch.setattr(at, "ATTAINABILITY_DIR", excluded.parent)
    before = _snapshot([selected, bundle, excluded, other_bundle])
    assert at.main(["check", "--gate", str(selected)]) == 0
    assert capsys.readouterr().out == (
        f"ok {selected} (file on disk): 1 not_stated_in_source; "
        "line-split gate: 1 deterministic absence(s) checked\n")
    assert _snapshot(before) == before


def test_default_gate_checks_every_yaml_and_continues_after_refusal(tmp_path, monkeypatch, capsys):
    refused, bundle_a, _ = _document(tmp_path / "a", "We got con\nsent.\n", stem="A")
    accepted, bundle_b, _ = _document(tmp_path / "b", "Nothing is stated here.\n")
    roster = tmp_path / "attainability"
    roster.mkdir()
    selected = []
    for original in (refused, accepted):
        # The bundle stem controls sort order, while both files retain valid names.
        target = roster / original.name
        target.write_bytes(original.read_bytes())
        selected.append(target)
    (roster / "README.md").write_text("Not an attainability document.\n", encoding="utf-8")
    monkeypatch.setattr(at, "ATTAINABILITY_DIR", roster)
    before = _snapshot([*selected, bundle_a, bundle_b, roster / "README.md"])
    assert at.main(["check", "--gate"]) == 1
    out = capsys.readouterr().out
    assert f"REFUSED {selected[0]}\n" in out
    assert f"ok {selected[1]} (file on disk): 1 not_stated_in_source; line-split gate: 1" in out
    assert out.index(f"REFUSED {selected[0]}") < out.index(f"ok {selected[1]}")
    assert out.count("REFUSED ") == 1 and out.count("ok ") == 1
    assert "README" not in out and _snapshot(before) == before


@pytest.mark.parametrize("method", ["curator", "judge:fixture"])
def test_gate_does_not_certify_interpreted_absences(tmp_path, capsys, method):
    path, bundle, doc = _document(tmp_path, "We got con\nsent.\n")
    doc["entries"][0].update(method=method, evidence={"snippets": []},
                             note="Synthetic interpretation; this test is not a scientific annotation.")
    path.write_text(at.dump(doc), encoding="utf-8")
    before = _snapshot([path, bundle])
    assert at.main(["check", "--gate", str(path)]) == 0
    assert capsys.readouterr().out == (
        f"ok {path} (file on disk): 1 not_stated_in_source; "
        "line-split gate: 0 deterministic absence(s) checked\n")
    assert _snapshot(before) == before


def test_gate_does_not_reclassify_unknown_entries(tmp_path, capsys):
    path, bundle, doc = _document(tmp_path, "We got consent and con\nsent.\n")
    assert doc["entries"][0]["status"] == "unknown"
    before = _snapshot([path, bundle])
    assert at.main(["check", "--gate", str(path)]) == 0
    assert capsys.readouterr().out.endswith("1 unknown; line-split gate: 0 deterministic absence(s) checked\n")
    assert _snapshot(before) == before


def test_invalid_file_is_not_certified_and_later_selected_file_is_checked(tmp_path, monkeypatch, capsys):
    invalid, _, doc = _document(tmp_path / "invalid", "Nothing is stated here.\n")
    valid, _, _ = _document(tmp_path / "valid", "Nothing is stated here.\n")
    doc["entries"][0]["evidence"]["hit_count"] = False
    invalid.write_text(at.dump(doc), encoding="utf-8")
    before = _snapshot([invalid, valid])
    calls = []
    real = at._certification_problems

    def certify(document, entries):
        calls.append(document["bundle"]["path"])
        return real(document, entries)

    monkeypatch.setattr(at, "_certification_problems", certify)
    assert at.main(["check", "--gate", str(invalid), str(valid)]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"INVALID {invalid}\n") and "hit_count" in out
    assert f"ok {valid} (file on disk)" in out
    assert calls == [at.load(valid).document["bundle"]["path"]]
    assert _snapshot(before) == before


@pytest.mark.parametrize("failure", [
    at.AttainabilityError("fixture bundle", ["the pinned bytes are no longer available"]),
    OSError("fixture bundle became unreadable"),
])
def test_gate_time_resolution_error_refuses_one_file_and_continues(tmp_path, monkeypatch, capsys, failure):
    first, bundle, _ = _document(tmp_path / "first", "Nothing is stated here.\n")
    later, later_bundle, _ = _document(tmp_path / "later", "Nothing is stated here.\n")
    before = _snapshot([first, bundle, later, later_bundle])
    reads = 0
    real = at.resolve_bytes

    def resolve(path, **kwargs):
        nonlocal reads
        if path == str(bundle):
            reads += 1
            if reads == 2:  # The original validation succeeded; the gate must still resolve the pins.
                raise failure
        return real(path, **kwargs)

    monkeypatch.setattr(at, "resolve_bytes", resolve)
    assert at.main(["check", "--gate", str(first), str(later)]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"REFUSED {first}\n  - line-split gate cannot read the pinned bundle: ")
    assert str(failure) in out and f"ok {later} (file on disk)" in out
    assert reads == 2 and _snapshot(before) == before


@pytest.mark.parametrize("changed", ["bundle", "document"])
def test_gate_keeps_validated_document_and_bundle_identity_if_inputs_change(tmp_path, monkeypatch, capsys, changed):
    path, bundle, doc = _document(tmp_path, "We got con\nsent.\n")
    before = _snapshot([path, bundle])
    if changed == "bundle":
        target = bundle
        replacement = b"Nothing is stated here.\n"
    else:
        target = path
        doc["entries"][0].update(method="curator", evidence={"snippets": []},
                                 note="Synthetic later interpretation, not the document already validated.")
        replacement = at.dump(doc).encode("utf-8")
    real_load = at.load

    def load_then_replace(selected):
        loaded = real_load(selected)
        # Simulate an independent writer after validation, before certification.
        target.write_bytes(replacement)
        return loaded

    def no_committed_fixture(path, **kwargs):
        # This fresh absolute temporary source has no Git history. Keep the
        # real resolver's on-disk digest checks while isolating its fallback.
        assert path == str(bundle)
        return None

    monkeypatch.setattr(at, "load", load_then_replace)
    monkeypatch.setattr(pv, "bundle_bytes_for", no_committed_fixture)
    assert at.main(["check", "--gate", str(path)]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"REFUSED {path}\n")
    if changed == "bundle":
        assert "line-split gate cannot read the pinned bundle" in out
        assert doc["bundle"]["md5"] in out and doc["bundle"]["sha256"] in out
    else:
        assert "E4.4 would be certified not_stated_in_source" in out
    assert target.read_bytes() == replacement  # No rewrite of the independent change.
    unchanged = path if changed == "bundle" else bundle
    assert unchanged.read_bytes() == before[unchanged]


def test_default_gate_certifies_all_committed_attainability_files(monkeypatch, capsys):
    directory = ROOT / "data/attainability"
    paths = sorted(directory.glob("*.yaml"))
    assert paths, "The committed attainability roster must not silently become empty."
    before = _snapshot(paths)
    monkeypatch.setattr(at, "ATTAINABILITY_DIR", directory)
    assert at.main(["check", "--gate"]) == 0
    out = capsys.readouterr().out
    assert out.count("line-split gate:") == len(paths)
    assert all(f"ok {path} (" in out for path in paths)
    assert _snapshot(before) == before


def test_empty_default_roster_is_visible_without_certification_claim(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(at, "ATTAINABILITY_DIR", tmp_path)
    assert at.main(["check", "--gate"]) == 0
    assert capsys.readouterr().out == f"no attainability files under {tmp_path}\n"
