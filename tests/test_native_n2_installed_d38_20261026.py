"""Actual installed D38 closure and causal render/refusal checks; #4354, 2026-10-26."""
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/adhoc/native_n2_installed_d38_20261026.py"
SPEC = importlib.util.spec_from_file_location("native_n2_installed_d38_test_helper", PATH)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
support = helper.load_support(ROOT)


@pytest.fixture
def rendered_sections():
    generic = (ROOT / helper.GENERIC).read_bytes()
    r9 = support.between(generic, support.R9_START, support.R9_END, "D38 R9")
    rules = support.RULE_START + b"\nBefore the rule.\n" + r9 + b"\nAfter the rule.\n"
    return generic, b"API\n" + rules + support.RULE_END, b"Native\n" + rules + support.RULE_END, r9


def test_current_installed_d38_passage_and_full_uniform_rules(rendered_sections):
    generic, api, native, r9 = rendered_sections
    result, actual, _ = helper.compare_rules(generic, api, native, support)
    assert actual == r9 and result["r9"]["sha256"] == helper.R9_SHA
    assert result["r9"]["occurrences"] == {"api25": 1, "native26": 1}
    assert result["uniform"]["identical"] is True
    assert api != native


def test_current_checker_rejects_old_asset_even_when_render_matches_it():
    old = support.git(ROOT, "show", helper.HISTORICAL + ":" + helper.GENERIC)
    with pytest.raises(ValueError, match="reviewed D38 generic"):
        helper.compare_rules(old, old, old, support)


def test_historical_support_stays_pinned_and_rejects_mutation_before_execution(tmp_path):
    assert support.ASSET_PINS[helper.GENERIC] != helper.ROTATIONS[helper.GENERIC]
    assert support.R9_SHA != helper.R9_SHA
    path = tmp_path / helper.SUPPORT
    path.parent.mkdir(parents=True)
    path.write_text("raise AssertionError('changed helper executed')\n")
    with pytest.raises(ValueError, match="before execution"):
        helper.load_support(tmp_path)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "last_byte", "uniform"])
def test_current_checker_requires_complete_single_r9_and_uniform_equality(rendered_sections, mutation):
    generic, api, native, r9 = rendered_sections
    if mutation == "missing":
        native = native.replace(r9, b"")
    elif mutation == "duplicate":
        native += r9
    elif mutation == "last_byte":
        native = native.replace(r9, r9[:-1] + bytes([r9[-1] ^ 1]))
    else:
        native = native.replace(b"After the rule.", b"Changed rule.")
    with pytest.raises(ValueError, match="verbatim exactly once|uniform sections differ"):
        helper.compare_rules(generic, api, native, support)


def test_actual_installed_13_assets_and_three_exact_stale_refusals(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    head = support.git(ROOT, "rev-parse", "HEAD").decode().strip()
    reader = support.Reader()
    assets, proof = helper.installed_assets(ROOT, head, reader, support)
    assert proof["counts"] == {"ordinary_installed": 10, "module_adjacent": 3, "total": 13}
    assert proof["positive_asset_substitution"] is False
    assert all(Path(row["path"]) == ROOT / row["logical_path"] for row in proof["assets"])
    refusals = helper.stale_refusals(ROOT, tmp_path.resolve(), assets, reader, support)
    assert [r["case"] for r in refusals] == ["both_pre_d38", "old_generic_only", "old_uniform_only"]
    assert all(r["status"] == "exact_refusal" for r in refusals)
    assert Path.cwd() == ROOT
    assert helper.installed_assets(ROOT, head, reader, support)[1] == proof
    reader.stable()


def test_positive_capture_rejects_an_alternate_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="actual selected checkout"):
        helper.installed_assets(ROOT, "unused", support.Reader(), support)


def test_descriptor_cannot_weaken_expected_asset_identity(monkeypatch):
    from data_sheets_schema import native_shared_selection as selected
    monkeypatch.chdir(ROOT)
    changed = dict(selected.ASSET_HASHES)
    changed[helper.GENERIC] = "0" * 64
    monkeypatch.setattr(selected, "ASSET_HASHES", changed)
    with pytest.raises(ValueError, match="roster/pins differ"):
        helper.installed_assets(ROOT, "unused", support.Reader(), support)
