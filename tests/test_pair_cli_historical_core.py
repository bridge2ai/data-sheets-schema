"""Historical membership is recovered from recorded core bytes, not rerendered digests."""
from contextlib import redirect_stdout
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import d4d_pair_consistency as pair, schema_digest as sd


UNKNOWN = "0" * 32


def schema(class_name, slots):
    return {"id": "https://example.org/fictional-schema", "name": "fictional",
            "default_range": "string", "imports": ["linkml:types"],
            "prefixes": {"linkml": "https://w3id.org/linkml/"},
            "classes": {class_name: {"attributes": {s: {"range": "string"} for s in slots}}}}


def write_yaml(path, value):
    path.write_text(yaml.safe_dump(value), encoding="utf-8")
    return path


def case(root, *, historical=("id", "title"), digest=UNKNOWN):
    full_schema = write_yaml(root / "selected_full.yaml", schema("Dataset", ("id", "title", "future")))
    core_schema = write_yaml(root / "selected_core.yaml", schema("CoreDataset", ("id", "title", "future")))
    recorded = write_yaml(root / "recorded_core.yaml", schema("CoreDataset", historical))
    full = write_yaml(root / "EXAMPLE_d4d.yaml", {"id": "fictional", "title": "Invented title", "future": "New slot"})
    core = write_yaml(root / "EXAMPLE_d4d_core.yaml", {"id": "fictional"})
    authority = {"core_path": str(recorded), "core_sha256": hashlib.sha256(recorded.read_bytes()).hexdigest(),
                 "core_md5": hashlib.md5(recorded.read_bytes()).hexdigest(), "profile": "neutral"}
    if digest is not None:
        authority["digest_md5"] = digest
    provenance = write_yaml(root / "EXAMPLE_provenance.yaml", {"schema": authority})
    return {"full": full, "core": core, "full_schema": full_schema, "core_schema": core_schema,
            "recorded": recorded, "provenance": provenance, "record": {"schema": authority}}


def arguments(files, *, as_json=True):
    args = ["--full", str(files["full"]), "--core", str(files["core"]),
            "--full-schema", str(files["full_schema"]), "--core-schema", str(files["core_schema"])]
    return args + (["--json"] if as_json else [])


def invoke(files):
    output = io.StringIO()
    with redirect_stdout(output):
        status = pair.main(arguments(files))
    return status, json.loads(output.getvalue())


def test_actual_cli_recovers_present_slot_without_excusing_new_slot(tmp_path):
    files = case(tmp_path)
    before = {str(p): p.read_bytes() for p in files.values() if isinstance(p, Path)}
    process = subprocess.run([sys.executable, "-m", "data_sheets_schema.d4d_pair_consistency", *arguments(files)],
                             capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    (tmp_path / "stdout.json").write_text(process.stdout)
    (tmp_path / "stderr.txt").write_text(process.stderr)
    assert {p: Path(p).read_bytes() for p in before} == before
    result = json.loads(process.stdout)
    assert process.returncode == 1, result
    assert [x["path"] for x in result["errors"]] == ["$.title"]
    assert [x["path"] for x in result["warnings"]] == ["$.future"]
    context = result["presence_context"]
    assert context["ledger_inventory"] == "unknown"
    assert context["historical_core_inventory"]["status"] == "recovered"
    assert context["historical_core_inventory"]["basis"]["sha256"] == files["record"]["schema"]["core_sha256"]


@pytest.fixture
def selected(tmp_path, monkeypatch):
    """Real digest rendering and CLI comparison, over private tiny current schemas."""
    files = case(tmp_path)
    monkeypatch.setattr(sd, "CLASS_SCHEMA", {"Dataset": files["full_schema"], "CoreDataset": files["core_schema"]})
    ledger = write_yaml(tmp_path / "ledger.yaml", {"digests": {}})
    monkeypatch.setattr(sd, "INVENTORY_LEDGER", ledger)
    files["ledger"] = ledger
    return files


def replace_recorded(files, document):
    write_yaml(files["recorded"], document)
    raw = files["recorded"].read_bytes()
    files["record"]["schema"].update(core_sha256=hashlib.sha256(raw).hexdigest(), core_md5=hashlib.md5(raw).hexdigest())
    write_yaml(files["provenance"], files["record"])


def test_inherited_membership_and_no_historical_rerender_or_writes(selected, monkeypatch):
    doc = schema("CoreDataset", ("id",))
    doc["classes"]["Prior"] = {"attributes": {"title": {"range": "string"}}}
    doc["classes"]["CoreDataset"]["is_a"] = "Prior"
    replace_recorded(selected, doc)
    before = {p: p.read_bytes() for p in selected.values() if isinstance(p, Path)}
    render = sd.digest_text
    calls = []
    def current_only(class_name, schema_path=None, *, profile=None):
        assert class_name == "Dataset" and schema_path is None and profile.name == "neutral"
        calls.append(class_name)
        return render(class_name, schema_path, profile=profile)
    monkeypatch.setattr(sd, "digest_text", current_only)
    status, result = invoke(selected)
    assert status == 1 and [e["path"] for e in result["errors"]] == ["$.title"]
    assert calls == ["Dataset"]
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("slots, expected_errors", [([], []), (["id"], []), (["title"], ["$.title"])])
def test_known_ledger_including_false_and_empty_wins(selected, monkeypatch, slots, expected_errors):
    from data_sheets_schema import run_schema
    write_yaml(selected["ledger"], {"digests": {UNKNOWN: {"CoreDataset": slots}}})
    replace_recorded(selected, schema("CoreDataset", () if slots else ("title",)))
    def forbidden(*args, **kwargs):
        pytest.fail("known ledger must not recover or substitute historical membership")
    monkeypatch.setattr(run_schema, "run_schema_bytes", forbidden)
    status, result = invoke(selected)
    assert status == bool(expected_errors)
    assert [e["path"] for e in result["errors"]] == expected_errors
    assert result["presence_context"]["ledger_inventory"] == "known"
    assert result["presence_context"]["historical_core_inventory"]["status"] == "not_needed"


@pytest.mark.parametrize("existing", [True, False])
def test_empty_class_is_known_but_absent_class_is_unknown(selected, existing):
    replace_recorded(selected, schema("CoreDataset" if existing else "Other", ()))
    status, result = invoke(selected)
    assert status == 0 and len(result["warnings"]) == 2
    inventory = result["presence_context"]["historical_core_inventory"]
    assert inventory["status"] == ("recovered" if existing else "unknown")
    if existing:
        assert inventory["slots"] == [] and inventory["slot_count"] == 0
    else:
        assert "does not declare CoreDataset" in inventory["reason"]


@pytest.mark.parametrize("problem", ["no_hash", "mixed_hash", "local_import", "malformed", "git_unavailable", "full_only"])
def test_unknown_history_never_uses_current_membership(selected, monkeypatch, problem):
    from data_sheets_schema import provenance, reconstructed_bytes
    monkeypatch.setattr(reconstructed_bytes, "reconstructed_bytes_for", lambda *a, **k: None)
    calls = []
    def no_commit(*args, **kwargs):
        calls.append((args, kwargs))
        if problem == "git_unavailable":
            raise provenance.GitUnavailable("synthetic unavailable history")
        return None
    monkeypatch.setattr(provenance, "committed_bytes_for", no_commit)
    authority = selected["record"]["schema"]
    if problem == "no_hash":
        authority.pop("core_sha256"); authority.pop("core_md5")
    elif problem == "mixed_hash":
        authority["core_md5"] = "f" * 32
    elif problem == "local_import":
        doc = schema("CoreDataset", ("id", "title")); doc["imports"].append("unrecorded_current_import")
        replace_recorded(selected, doc)
    elif problem == "malformed":
        selected["recorded"].write_bytes(b"[")
        authority.update(core_sha256=hashlib.sha256(b"[").hexdigest(), core_md5=hashlib.md5(b"[").hexdigest())
    elif problem == "git_unavailable":
        authority["core_path"] = str(selected["recorded"].with_name("unavailable.yaml"))
    else:
        authority.update({key.replace("core_", "full_"): authority.pop(key)
                          for key in ("core_path", "core_sha256", "core_md5")})
    write_yaml(selected["provenance"], selected["record"])
    status, result = invoke(selected)
    assert status == 0 and result["errors"] == [] and len(result["warnings"]) == 2
    inventory = result["presence_context"]["historical_core_inventory"]
    assert inventory["status"] == "unknown" and inventory["reason"]
    if problem in {"no_hash", "mixed_hash", "git_unavailable", "full_only"}:
        assert inventory["basis"]["source"] == "today's schema"
        assert "not substituted" in inventory["reason"]
    if problem == "mixed_hash":
        assert calls[0][1]["sha256"] == authority["core_sha256"]
        assert calls[0][1]["md5"] == "f" * 32


def test_digestless_and_current_digest_stay_strict_without_recovery(selected, monkeypatch):
    from data_sheets_schema import run_schema
    from data_sheets_schema.profiles import NEUTRAL
    def forbidden(*args, **kwargs):
        pytest.fail("strict digest comparison must not use recovered membership")
    monkeypatch.setattr(run_schema, "run_schema_bytes", forbidden)
    current = sd.fingerprint(sd.digest_text("Dataset", profile=NEUTRAL))
    for digest in (None, current):
        if digest is None:
            selected["record"]["schema"].pop("digest_md5")
        else:
            selected["record"]["schema"]["digest_md5"] = digest
        write_yaml(selected["provenance"], selected["record"])
        status, result = invoke(selected)
        assert status == 1 and len(result["errors"]) == 2 and result["warnings"] == []
        assert not result["presence_context"]["schema_moved"]


def test_recovery_and_digest_use_one_captured_provenance(selected, monkeypatch):
    original = selected["provenance"].read_bytes()
    read = Path.read_bytes
    reads = []
    def replacing_read(path):
        raw = read(path)
        if path == selected["provenance"]:
            reads.append(raw)
            path.write_bytes(b"schema: {}\n")
        return raw
    monkeypatch.setattr(Path, "read_bytes", replacing_read)
    status, result = invoke(selected)
    assert status == 1 and reads == [original]
    history = result["presence_context"]
    assert history["provenance_sha256"] == hashlib.sha256(original).hexdigest()
    assert history["run_digest"] == UNKNOWN and history["historical_core_inventory"]["status"] == "recovered"


def test_content_and_custom_schema_rules_are_not_replaced(selected):
    write_yaml(selected["core"], {"id": "fictional", "title": "Different", "future": "New slot"})
    status, result = invoke(selected)
    assert status == 1 and [e["code"] for e in result["errors"]] == ["shared-slot-content"]
    # title no longer has the same signature in the selected comparison schemas.
    doc = schema("CoreDataset", ("id", "title", "future"))
    doc["classes"]["CoreDataset"]["attributes"]["title"]["range"] = "integer"
    write_yaml(selected["core_schema"], doc)
    status, result = invoke(selected)
    assert status == 0 and "title" not in result["identity_slots"]
    assert result["presence_context"]["core_schema_path"] == str(selected["core_schema"])


def test_text_output_discloses_recovered_basis(selected, capsys):
    assert pair.main(arguments(selected, as_json=False)) == 1
    text = capsys.readouterr().out
    assert "ledger inventory=unknown" in text and '"status": "recovered"' in text
    assert str(selected["recorded"]) in text


@pytest.mark.parametrize("source", ["committed", "reconstructed"])
def test_cli_uses_real_recorded_byte_recovery_routes(selected, monkeypatch, tmp_path, source):
    """Private Git/gzip fixtures exercise the unchanged actual resolvers."""
    from data_sheets_schema import provenance, reconstructed_bytes
    raw = selected["recorded"].read_bytes()
    logical = "synthetic-history/recorded_core.yaml"
    selected["record"]["schema"]["core_path"] = logical
    write_yaml(selected["provenance"], selected["record"])
    monkeypatch.setattr(provenance, "_REPO_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    if source == "committed":
        path = tmp_path / logical; path.parent.mkdir(); path.write_bytes(raw)
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=tmp_path, stderr=subprocess.STDOUT)
        git("init", "-q")
        git("add", logical)
        git("-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic historical schema")
        # The working copy now lacks title, but the committed pinned bytes contain it.
        write_yaml(path, schema("CoreDataset", ("id",)))
        expected_source = "the run's schema, a git blob"
    else:
        packed = tmp_path / "synthetic_core.yaml.gz"
        packed.write_bytes(gzip.compress(raw, mtime=0))
        entry = {"path": logical, "sha256": hashlib.sha256(raw).hexdigest(),
                 "md5": hashlib.md5(raw).hexdigest(), "artefact": packed.name,
                 "artefact_sha256": hashlib.sha256(packed.read_bytes()).hexdigest(),
                 "base_commit": "b" * 40, "observed_at": "synthetic fixture", "issue": 4061}
        monkeypatch.setattr(reconstructed_bytes, "RECONSTRUCTIONS", (entry,))
        def forbidden(*args, **kwargs):
            pytest.fail("matching reconstructed bytes precede Git")
        monkeypatch.setattr(provenance, "committed_bytes_for", forbidden)
        expected_source = "the run's schema, reconstructed"
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and ".git" not in p.parts}
    status, result = invoke(selected)
    assert status == 1 and [e["path"] for e in result["errors"]] == ["$.title"]
    assert result["presence_context"]["historical_core_inventory"]["basis"]["source"] == expected_source
    assert {p: p.read_bytes() for p in before} == before
