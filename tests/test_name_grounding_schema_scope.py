"""Captured schema scope changes finding paths, without changing the parser (#4292)."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import name_grounding as ng, provenance as pv, run_schema


def hashes(raw):
    return {k: getattr(hashlib, k)(raw).hexdigest() for k in ("sha256", "md5")}


def schema_bytes(kind, *, selected=None, imports=None):
    chosen = selected or ("legacy_contact" if kind == "full" else "core_contact")
    doc = {"id": "https://example.test/" + kind, "name": kind,
           "default_range": "string", "classes": {
        "Person": {"attributes": {"name": {}}},
        "Creator": {"attributes": {"name": {}}},
        "Organization": {"attributes": {"name": {}}},
        "Dataset": {"attributes": {
            "creators": {"range": "Organization", "multivalued": True},
            "principal_investigator": {"range": "string"},
            chosen: {"range": "Person" if kind == "full" else "Creator"}}}}}
    if imports:
        doc["imports"] = imports
    return yaml.safe_dump(doc).encode()


def make_disk(root):
    core_dir = root / "claudecode_api_core" / "L"
    full_dir = root / "claudecode_api" / "L"
    (core_dir / "intermediate").mkdir(parents=True)
    full_dir.mkdir(parents=True)
    bundle = root / "bundle.txt"
    bundle.write_text("Evidence names only Ivo Reed.\n")
    full = {"legacy_contact": {"name": "Mira Vale"},
            "core_contact": {"name": "Sana Noor"},
            "creators": [{"name": "Nora Moss"}], "principal_investigator": "Ivo Reed"}
    record = {"run": {"project": "NEUTRAL", "label": "L"}, "inputs": {
        "bundle_path": str(bundle), **{"bundle_" + k: v for k, v in hashes(bundle.read_bytes()).items()}},
        "schema": {}}
    for kind in ("full", "core"):
        path = root / (kind + "_schema.yaml")
        raw = schema_bytes(kind)
        path.write_bytes(raw)
        record["schema"].update({kind + "_path": str(path),
                                 **{kind + "_" + k: v for k, v in hashes(raw).items()}})
    paths = {"phase1": core_dir / "intermediate/NEUTRAL_full.yaml",
             "full": full_dir / "NEUTRAL_d4d.yaml",
             "core": core_dir / "NEUTRAL_d4d_core.yaml"}
    for path in paths.values():
        path.write_text(yaml.safe_dump(full))
    prov = core_dir / "NEUTRAL_provenance.yaml"
    prov.write_text(yaml.safe_dump(record))
    return {"provenance": prov, "record": record, "paths": paths,
            "doc": full, "bundle": bundle, "root": root}


@pytest.fixture
def disk(tmp_path):
    return make_disk(tmp_path)


def findings(result):
    return {f["path"] for f in result["findings"]}


@pytest.mark.parametrize("pins", [("sha256",), ("md5",), ("sha256", "md5")])
def test_actual_run_uses_full_for_phase1_and_full_but_separate_core(disk, pins, monkeypatch):
    for kind in ("full", "core"):
        for key in {"sha256", "md5"} - set(pins):
            disk["record"]["schema"].pop(kind + "_" + key)
    disk["provenance"].write_text(yaml.safe_dump(disk["record"]))
    before = {p: p.read_bytes() for p in disk["root"].rglob("*") if p.is_file()}
    calls = []
    original = run_schema.run_schema_bytes
    def capture(record, *, kind):
        calls.append(kind)
        return original(record, kind=kind)
    monkeypatch.setattr(run_schema, "run_schema_bytes", capture)
    monkeypatch.setattr(ng, "person_name_slots", lambda: pytest.fail("ambient full/core union"))
    out = ng.check_run(disk["provenance"])
    assert calls == ["full", "core"]
    assert out["schema_policy"] == "recorded"
    for which, block in out["records"].items():
        kind = "core" if which == "core" else "full"
        field = "core_contact" if kind == "core" else "legacy_contact"
        assert findings(block) == {field + ".name"}
        assert block["counts"]["grounded"] == block["counts"]["absent"] == 2
        basis = block["schema_basis"]
        assert basis["selection"] == "recorded"
        assert basis["schema_kind"] == kind
        assert basis["slots"] == sorted([field, "principal_investigator"])
        assert basis["actual"] == {"path": disk["record"]["schema"][kind + "_path"],
                                   **hashes(schema_bytes(kind))}
        assert set(basis["requested"]) == {"path", *pins}
        assert basis["scope_rule"] == ng.NAME_SCOPE_RULE
        assert "not per-owner" in basis["scope_rule"]
        assert basis["slots_sha256"] == hashlib.sha256(json.dumps(
            basis["slots"], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    # Full and phase1 may reuse immutable slots but never a mutable output mapping.
    out["records"]["full"]["schema_basis"]["slots"].clear()
    assert out["records"]["phase1"]["schema_basis"]["slots"]
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("records,expected", [(("phase1", "full"), ["full"]),
    (("full",), ["full"]), (("core",), ["core"]), ((), [])])
def test_only_requested_schema_kinds_are_selected(disk, records, expected, monkeypatch):
    original = run_schema.run_schema_bytes
    seen = []
    def select(record, *, kind):
        assert kind in expected
        seen.append(kind)
        return original(record, kind=kind)
    monkeypatch.setattr(run_schema, "run_schema_bytes", select)
    assert ng.check_run(disk["provenance"], records)["checked"]
    assert seen == expected


@pytest.mark.parametrize("recovery", ["git", "reconstruction"])
@pytest.mark.parametrize("pins", [("sha256",), ("md5",), ("sha256", "md5")])
def test_existing_resolution_recovers_changed_disk_bytes(disk, recovery, pins, monkeypatch):
    from data_sheets_schema import reconstructed_bytes as rb
    record = copy.deepcopy(disk["record"])
    path = Path(record["schema"]["full_path"])
    raw = path.read_bytes()
    path.write_bytes(schema_bytes("full", selected="changed_contact"))
    for key in {"sha256", "md5"} - set(pins):
        record["schema"].pop("full_" + key)
    seen = []
    entry = {"commit": "c" * 40, "matched_on": list(pins), "artefact": "neutral.gz",
             "base_commit": "b" * 40, "observed_at": "2026-10-02", "issue": 4292}
    def recovered(p, **kw):
        assert p == str(path)
        assert kw == {k: hashes(raw)[k] if k in pins else None for k in ("md5", "sha256")}
        seen.append(p)
        return raw, entry
    monkeypatch.setattr(rb, "reconstructed_bytes_for", recovered if recovery == "reconstruction" else lambda *a, **k: None)
    monkeypatch.setattr(pv, "committed_bytes_for", recovered if recovery == "git" else lambda *a, **k: pytest.fail("git after reconstruction"))
    slots, basis = ng.run_name_scope(record, kind="full")
    assert seen == [str(path)]
    assert slots == {"legacy_contact", "principal_investigator"}
    assert basis["actual"]["sha256"] == hashes(raw)["sha256"]
    assert basis["selection"] == "recorded"
    assert basis["resolution"]["source"].endswith("a git blob" if recovery == "git" else "reconstructed")


def test_conflicting_pins_disclose_current_kind_and_requested_identity(disk, monkeypatch):
    from data_sheets_schema import reconstructed_bytes as rb
    record = disk["record"]
    record["schema"]["full_sha256"] = "0" * 64
    current = disk["root"] / "current.yaml"
    current.write_bytes(schema_bytes("full", selected="current_contact"))
    monkeypatch.setattr(pv, "FULL_SCHEMA", current)
    monkeypatch.setattr(pv, "CORE_SCHEMA", disk["root"] / "missing-core")
    monkeypatch.setattr(rb, "reconstructed_bytes_for", lambda *a, **k: None)
    monkeypatch.setattr(pv, "committed_bytes_for", lambda *a, **k: None)
    slots, basis = ng.run_name_scope(record, kind="full")
    assert slots == {"current_contact", "principal_investigator"}
    assert basis["selection"] == "current_fallback"
    assert basis["requested"]["sha256"] == "0" * 64
    assert basis["actual"] == {"path": str(current), **hashes(current.read_bytes())}
    assert "no committed version" in basis["reason"]


@pytest.mark.parametrize("bad", [b"[]\n", b"\xff", b"classes: [\n",
    schema_bytes("full", imports=["current_local_module"])])
def test_unusable_history_falls_back_without_importing_unpinned_modules(disk, bad, monkeypatch):
    path = Path(disk["record"]["schema"]["full_path"])
    path.write_bytes(bad)
    disk["record"]["schema"].update({"full_" + k: v for k, v in hashes(bad).items()})
    current = disk["root"] / "current.yaml"
    current.write_bytes(schema_bytes("full", selected="fallback_contact"))
    monkeypatch.setattr(pv, "FULL_SCHEMA", current)
    slots, basis = ng.run_name_scope(disk["record"], kind="full")
    assert slots == {"fallback_contact", "principal_investigator"}
    assert basis["selection"] == "current_fallback"
    assert basis["requested"]["sha256"] == hashes(bad)["sha256"]
    assert basis["actual"]["sha256"] == hashes(current.read_bytes())["sha256"]
    assert "recovered schema" in basis["reason"]


def test_current_unavailable_is_unchecked_only_for_affected_scope(disk, monkeypatch):
    for key in ("path", "sha256", "md5"):
        disk["record"]["schema"].pop("full_" + key)
    disk["provenance"].write_text(yaml.safe_dump(disk["record"]))
    current = disk["root"] / "current-bad.yaml"
    current.write_bytes(schema_bytes("full", imports=["do_not_read_me"]))
    monkeypatch.setattr(pv, "FULL_SCHEMA", current)
    out = ng.check_run(disk["provenance"])
    for kind in ("phase1", "full"):
        result = out["records"][kind]
        assert not result["checked"]
        assert "counts" not in result and "name_leaves" not in result
        assert result["schema_basis"]["selection"] == "unavailable"
        assert "import do_not_read_me" in result["reason"]
    assert out["records"]["core"]["checked"]
    assert out["records"]["core"]["schema_basis"]["selection"] == "recorded"


@pytest.mark.parametrize("historical", [True, False])
def test_capture_hashes_and_slots_cannot_race_later_path_rewrite(disk, historical, monkeypatch):
    from data_sheets_schema import schema_view
    current = disk["root"] / "current.yaml"
    original_bytes = schema_bytes("full")
    current.write_bytes(original_bytes)
    monkeypatch.setattr(pv, "FULL_SCHEMA", current)
    record = disk["record"] if historical else {}
    changing = Path(record["schema"]["full_path"]) if historical else current
    original = schema_view.version_document
    def parse(raw):
        changing.write_bytes(schema_bytes("full", selected="different_contact"))
        return original(raw)
    monkeypatch.setattr(schema_view, "version_document", parse)
    slots, basis = ng.run_name_scope(record, kind="full")
    assert slots == {"legacy_contact", "principal_investigator"}
    assert basis["actual"]["sha256"] == hashes(original_bytes)["sha256"]
    assert hashes(changing.read_bytes())["sha256"] != basis["actual"]["sha256"]


def test_repeated_current_path_is_not_a_stale_slot_cache(disk, monkeypatch):
    path = disk["root"] / "current.yaml"
    monkeypatch.setattr(pv, "FULL_SCHEMA", path)
    for field in ("first_contact", "second_contact", "first_contact"):
        path.write_bytes(schema_bytes("full", selected=field))
        slots, basis = ng.run_name_scope({}, kind="full")
        assert slots == {field, "principal_investigator"}
        assert basis["actual"]["sha256"] == hashes(path.read_bytes())["sha256"]


def invoke(disk, *args):
    from data_sheets_schema.cli.provenance import name_grounding_cmd
    return CliRunner().invoke(name_grounding_cmd, list(args))


def test_cli_json_and_human_expose_separate_scope_bases(disk, monkeypatch):
    monkeypatch.setattr(pv, "record_path_for", lambda *a: disk["provenance"])
    args = ("--label", "L", "--method", "claudecode_api", "--project", "NEUTRAL")
    text = invoke(disk, *args)
    assert text.exit_code == 0, text.output
    assert "full recorded; sha256" in text.output and "core recorded; sha256" in text.output
    assert "not per-owner semantic validation" in text.output
    result = invoke(disk, *args, "--json")
    assert result.exit_code == 0, result.output
    [body] = json.loads(result.output)
    assert findings(body["records"]["full"]) == {"legacy_contact.name"}
    assert findings(body["records"]["core"]) == {"core_contact.name"}
    legacy = invoke(disk, *args, "--schema-policy", "legacy_current")
    assert legacy.exit_code == 0, legacy.output
    assert "schema scope" not in legacy.output
    assert "creators[0].name" in legacy.output


def test_cli_standalone_remains_pure_and_refuses_run_schema_policy(disk):
    args = ("--full", str(disk["paths"]["full"]), "--bundle", str(disk["bundle"]))
    result = invoke(disk, *args, "--json")
    assert result.exit_code == 0, result.output
    [body] = json.loads(result.output)
    assert body["records"]["given"] == {"path": str(disk["paths"]["full"]),
        **ng.check_record(disk["doc"], disk["bundle"].read_text())}
    assert "schema_policy" not in body
    assert invoke(disk, *args, "--schema-policy", "recorded").exit_code == 2


@pytest.mark.parametrize("policy", ["bad", None, "", False])
def test_invalid_schema_policy_refuses(disk, policy):
    with pytest.raises(ValueError, match="schema_policy"):
        ng.check_run(disk["provenance"], schema_policy=policy)


def test_legacy_run_and_cli_and_pure_contract_match_whole_parent_outputs(disk, monkeypatch):
    # Captured from exact bfdcffd822b8dfc407241bb3be2fe2cfce76b185 modules,
    # before this change, using make_disk. Only temporary root spelling is
    # normalized; the complete JSON/text including v2 output is compared.
    expected = {
        "run": "60d398a81986ce818f8106bb4d93758e8bd8bb0d08b23902d1901d1b47ff2fc8",
        "pure": "b117436945506e74496841404ab711a0649a0e3e44eb940059b95b57ca6a5fc0",
        "cli_text": "7ab538ae85b091fda339afea55ba9309d866ac564c603cfbeb593316521eee5b",
        "cli_json": "612b5cfa1da4e511fc529c135dc2a34da0b5b44429a0afd50944c7decc828590",
        "standalone_text": "7cc4d86ab54ad40c1a65aa1b485dff708b196bfab1a72acb3e6e0e9fcb5023e7",
        "standalone_json": "72c809843ecee71413ae0dd2d6381e5db59ce01a5cfbc1b4225e892ab09ba18d",
        "malformed_record": "1a64b16eaa09d847c0ca7d52103f6af3b9c01f989f371d7e057152ebed9e094e",
        "missing_bundle": "28a3ed1f1aac88ac4dfbb5e87ce33f02d1fc0c5248c4b1b012ad241eda0cba57",
    }
    def digest(value):
        text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        return hashlib.sha256(text.replace(str(disk["root"]), "<ROOT>").encode()).hexdigest()
    def old_run():
        return ng.check_run(disk["provenance"], schema_policy="legacy_current")
    monkeypatch.setattr(ng, "run_name_scope", lambda *a, **kw: pytest.fail("legacy selected history"))
    result = {"run": digest(old_run()),
              "pure": digest(ng.check_record(disk["doc"], disk["bundle"].read_text()))}
    monkeypatch.setattr(pv, "record_path_for", lambda *a: disk["provenance"])
    args = ["--label", "L", "--method", "claudecode_api", "--project", "NEUTRAL",
            "--schema-policy", "legacy_current"]
    given = ["--full", str(disk["paths"]["full"]), "--bundle", str(disk["bundle"])]
    for key, flags in (("cli_text", args), ("cli_json", args + ["--json"]),
                       ("standalone_text", given), ("standalone_json", given + ["--json"])):
        out = invoke(disk, *flags)
        assert out.exit_code == 0, out.output
        result[key] = digest(out.output)
    disk["paths"]["full"].write_text("x: [\n")
    result["malformed_record"] = digest(old_run())
    disk["provenance"].write_text("inputs: {}\n")
    result["missing_bundle"] = digest(old_run())
    assert result == expected


@pytest.mark.parametrize("kind", ["full", "core"])
def test_real_git_history_supplies_schema_rules_and_identity(tmp_path, kind, monkeypatch):
    import subprocess
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pv, "_REPO_ROOT", tmp_path)
    path = Path("scope-" + tmp_path.name + ".yaml")
    raw = schema_bytes(kind)
    path.write_bytes(raw)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, stderr=subprocess.DEVNULL)
    git("init", "-q")
    git("add", str(path))
    git("-c", "user.name=Neutral test", "-c", "user.email=neutral@example.test",
        "commit", "-qm", "Pinned schema")
    commit = git("rev-parse", "HEAD").decode().strip()
    path.write_bytes(schema_bytes(kind, selected="drifted_contact"))
    record = {"schema": {kind + "_path": str(path),
                         **{kind + "_" + k: v for k, v in hashes(raw).items()}}}
    slots, basis = ng.run_name_scope(record, kind=kind)
    assert basis["selection"] == "recorded"
    assert basis["resolution"]["source"] == "the run's schema, a git blob"
    assert basis["resolution"]["commit"] == commit
    assert basis["actual"] == {"path": str(path), **hashes(raw)}
    assert "drifted_contact" not in slots


@pytest.mark.parametrize("kind", ["full", "core"])
def test_real_gzip_reconstruction_is_used_before_git(tmp_path, kind, monkeypatch):
    import gzip
    from data_sheets_schema import reconstructed_bytes as rb
    monkeypatch.setattr(pv, "_REPO_ROOT", tmp_path)
    path = tmp_path / "drifted.yaml"
    raw = schema_bytes(kind)
    path.write_bytes(schema_bytes(kind, selected="drifted_contact"))
    packed = gzip.compress(raw, mtime=0)
    (tmp_path / "schema.gz").write_bytes(packed)
    entry = {"path": str(path), **hashes(raw), "artefact": "schema.gz",
             "artefact_sha256": hashes(packed)["sha256"], "base_commit": "b" * 40,
             "observed_at": "invented test bytes", "issue": 4292}
    monkeypatch.setattr(rb, "RECONSTRUCTIONS", (entry,))
    monkeypatch.setattr(pv, "committed_bytes_for", lambda *a, **kw: pytest.fail("git after valid gzip"))
    record = {"schema": {kind + "_path": str(path),
                         **{kind + "_" + k: v for k, v in hashes(raw).items()}}}
    slots, basis = ng.run_name_scope(record, kind=kind)
    assert basis["selection"] == "recorded"
    assert basis["resolution"]["source"] == "the run's schema, reconstructed"
    assert basis["actual"] == {"path": str(path), **hashes(raw)}
    assert "drifted_contact" not in slots


def test_current_fallback_resolves_package_resource_from_other_cwd(tmp_path, monkeypatch):
    from data_sheets_schema.resources import resource_path
    expected = resource_path(pv.FULL_SCHEMA).resolve().read_bytes()
    monkeypatch.chdir(tmp_path)
    slots, basis = ng.run_name_scope({}, kind="full")
    assert slots and basis["selection"] == "current_fallback"
    assert basis["actual"]["sha256"] == hashes(expected)["sha256"]


def test_scope_preserves_slot_name_rule_and_releases_view(disk, monkeypatch):
    import weakref
    refs = []
    original = ng.person_name_slots_of
    def derive(view):
        refs.append(weakref.ref(view))
        return original(view)
    monkeypatch.setattr(ng, "person_name_slots_of", derive)
    slots, basis = ng.run_name_scope(disk["record"], kind="full")
    assert refs and all(ref() is None for ref in refs)
    # The established rule is key-based even below an unrelated owner.
    # This addition makes that limitation explicit rather than claiming a
    # new schema-validating owner walk.
    out = ng.check_record({"other_owner": {"legacy_contact": {"name": "Mira Vale"}}}, "", slots)
    assert findings(out) == {"other_owner.legacy_contact.name"}
    assert "not per-owner" in basis["scope_rule"]
