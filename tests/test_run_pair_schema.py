"""Historical pair/report checks bind both recorded schemas (#4062)."""
from contextlib import contextmanager
import copy
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import backfill_checks as bc, provenance, run_pair_schema as rps, run_schema
from data_sheets_schema.d4d_pair_consistency import pair_schema_from_views
from data_sheets_schema.report_claims import declared_ranges_of, declared_slots_of


def schema(root, *, title=True, nested=True):
    attrs = {"name": {"range": "string"}}
    if title:
        attrs["title"] = {"range": "string"}
    if nested:
        attrs["distributions"] = {"range": "CoreDistribution", "multivalued": True,
                                  "inlined_as_list": True}
    return yaml.safe_dump({"id": "https://example.org/fixture", "name": "fixture",
                           "imports": ["linkml:types"],
                           "prefixes": {"linkml": "https://w3id.org/linkml/"},
                           "classes": {root: {"attributes": attrs},
                                       "CoreDistribution": {"attributes": {"url": {"range": "string"}}}}}).encode()


def pin(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    full, core, old_core = (tmp_path / n for n in ("full.yaml", "core.yaml", "old-core.yaml"))
    full.write_bytes(schema("Dataset"))
    core.write_bytes(schema("CoreDataset"))
    old_core.write_bytes(schema("CoreDataset", title=False, nested=False))
    monkeypatch.setattr(provenance, "FULL_SCHEMA", full)
    monkeypatch.setattr(provenance, "CORE_SCHEMA", core)
    def record(which=old_core):
        return {"schema": {f"{kind}_{key}": value for kind, path in (("full", full), ("core", which))
                           for key, value in pin(path).items()}}
    return full, core, old_core, record


def test_core_hash_resolution_does_not_accidentally_select_full(fixture):
    full, core, old_core, record = fixture
    data, basis = run_schema.run_schema_bytes(record(), kind="core")
    assert data == old_core.read_bytes() != full.read_bytes()
    assert basis["sha256"] == pin(old_core)["sha256"]
    assert basis["source"] == "the run's schema, on disk"
    md5_only = record()
    del md5_only["schema"]["core_sha256"]
    md5_only["schema"]["core_md5"] = hashlib.md5(old_core.read_bytes()).hexdigest()
    assert run_schema.run_schema_bytes(md5_only, kind="core")[0] == data
    with pytest.raises(ValueError, match="kind"):
        run_schema.run_schema_bytes(record(), kind="unexpected")


def test_pair_and_report_maps_use_the_same_historical_views(fixture):
    full, core, old_core, record = fixture
    with rps.run_schema_views(record()) as selected:
        pair = pair_schema_from_views(selected.full, selected.core)
        assert pair.identity_slots == ("name",)
        declarations = declared_slots_of(selected.full, selected.core)
        assert "title" in declarations["Dataset"]
        assert "title" not in declarations["CoreDataset"]
        assert "distributions" not in declared_ranges_of(selected.core)["CoreDataset"]
        assert selected.recovered_pair
        assert selected.hashes == {"full_sha256": pin(full)["sha256"],
                                   "core_sha256": pin(old_core)["sha256"]}
    with rps.run_schema_views(record(core)) as selected:
        assert "title" in pair_schema_from_views(selected.full, selected.core).identity_slots
        assert declared_ranges_of(selected.core)["CoreDataset"]["distributions"] == "CoreDistribution"


@pytest.mark.parametrize("bad", [b"not a mapping", b"name: bad\nimports: [local_other]\n",
                                    schema("WrongRoot")])
def test_unusable_recovered_core_is_an_explicit_per_file_fallback(fixture, bad):
    full, core, old_core, record = fixture
    old_core.write_bytes(bad)
    with rps.run_schema_views(record()) as selected:
        assert selected.basis["full"]["source"] == "the run's schema, on disk"
        assert selected.basis["core"]["source"] == run_schema.TODAY
        assert "could not be loaded" in selected.basis["core"]["reason"]
        assert not selected.recovered_pair
        assert selected.hashes["core_sha256"] == pin(core)["sha256"]


def test_missing_identity_is_disclosed_and_uses_actual_current_hash(fixture):
    full, core, old_core, record = fixture
    with rps.run_schema_views({}) as selected:
        assert all(b["source"] == run_schema.TODAY for b in selected.basis.values())
        assert "core" in selected.basis["core"]["reason"]
        assert selected.hashes["core_sha256"] == pin(core)["sha256"]


@pytest.mark.parametrize("kind", ["full", "core"])
def test_malformed_nested_historical_class_falls_back_before_checks(fixture, tmp_path, kind):
    full, core, old_core, record = fixture
    selected = full if kind == "full" else old_core
    data = yaml.safe_load(selected.read_bytes())
    data["classes"]["CoreDistribution"]["is_a"] = "MissingAncestor"
    historical = tmp_path / (kind + "-malformed.yaml")
    historical.write_text(yaml.safe_dump(data))
    rec = record()
    rec["schema"].update({f"{kind}_{key}": value for key, value in pin(historical).items()})
    path = layout(tmp_path, rec)
    block = bc.compute(path, only={"report_claims"})["report_claims"]
    assert block["schema_basis"][kind]["source"] == run_schema.TODAY
    assert "MissingAncestor" in block["schema_basis"][kind]["reason"]
    assert block["schema"][f"{kind}_sha256"] == pin(full if kind == "full" else core)["sha256"]


def test_both_historical_views_close_even_when_check_raises(fixture, monkeypatch):
    _full, _core, _old, record = fixture
    real_view = rps.version_view
    opened, closed = [], []
    @contextmanager
    def tracked(path, document):
        with real_view(path, document) as view:
            opened.append(path)
            try:
                yield view
            finally:
                closed.append(path)
    monkeypatch.setattr(rps, "version_view", tracked)
    with pytest.raises(RuntimeError, match="check failed"):
        with rps.run_schema_views(record()):
            raise RuntimeError("check failed")
    assert len(opened) == len(closed) == 2
    assert closed == list(reversed(opened))


def layout(tmp_path, record):
    root = tmp_path / "records"
    path = root / "api_core" / "label" / "Harbor_provenance.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(record))
    paths = bc.record_paths(path)
    paths["full"].parent.mkdir(parents=True)
    paths["full"].write_text("name: Harbor\ntitle: Source title\n")
    paths["core"].write_text("name: Harbor\n")
    paths["report"].write_text("# Reconciliation\nNo unsupported changes.\n")
    return path


def test_compute_uses_selected_rules_and_records_hashes_without_writes(fixture, tmp_path):
    _full, core, old_core, record = fixture
    path = layout(tmp_path, record())
    before = {p: p.read_bytes() for p in path.parents[2].rglob("*") if p.is_file()}
    historic = bc.compute(path, only={"pair_consistency", "report_claims"})
    assert historic["pair_consistency"]["consistent"]
    assert historic["pair_consistency"]["schema_moved"] is False
    for name in ("pair_consistency", "report_claims"):
        assert historic[name]["schema"]["core_sha256"] == pin(old_core)["sha256"]
        assert historic[name]["schema_selection_instrument"] == rps.SCHEMA_SELECTION_INSTRUMENT
    assert before == {p: p.read_bytes() for p in before}
    path.write_text(yaml.safe_dump(record(core)))
    current = bc.compute(path, only={"pair_consistency"})["pair_consistency"]
    assert not current["consistent"]
    assert any(f["path"] == "$.title" for f in current["findings"])


def test_custom_report_maps_are_disclosed_instead_of_attributed_to_schema(fixture, tmp_path):
    _full, _core, _old, record = fixture
    path = layout(tmp_path, record())
    maps = {"Dataset": {"name"}, "CoreDataset": {"name"}}
    out = bc.compute(path, maps, only={"report_claims"})["report_claims"]
    assert out["schema_overrides"]["source"] == "caller-supplied rule maps"
    assert set(out["schema_overrides"]["sha256"]) == {"declared_slots"}
    changed = copy.deepcopy(maps)
    changed["CoreDataset"].add("title")
    after = bc.compute(path, changed, only={"report_claims"})["report_claims"]
    assert out["schema_overrides"] != after["schema_overrides"]


def test_legacy_reproduction_explicitly_retains_previous_schema_and_block_shape(fixture, tmp_path):
    _full, core, _old, record = fixture
    path = layout(tmp_path, record())
    blocks = bc.compute(path, only={"pair_consistency", "report_claims"},
                        schema_policy="legacy_current")
    for block in blocks.values():
        assert block["schema"]["core_sha256"] == pin(core)["sha256"]
        assert "schema_selection_instrument" not in block
        assert "schema_basis" not in block
        assert "schema_overrides" not in block
    with pytest.raises(ValueError, match="schema_policy"):
        bc.compute(path, schema_policy="typo")
