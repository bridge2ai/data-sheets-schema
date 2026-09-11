"""Imported files belong to a cached schema's captured instrument (#1265)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner, schema_digest, schema_view
from data_sheets_schema.evidence_score import LLMSlotFitnessScorer
from tests.test_schema_snapshot_cache import replace_after_read


@pytest.fixture
def imported(tmp_path):
    directory = tmp_path / "nested"
    directory.mkdir()
    base = directory / "base.yaml"
    base.write_text("id: https://example.org/base\nname: base\ndefault_range: string\n"
                    "classes:\n  Base:\n    attributes:\n      subject:\n"
                    "        description: Enter a country.\n")
    middle = directory / "middle.yaml"
    middle.write_text("id: https://example.org/middle\nname: middle\nimports: [base]\n")
    root = tmp_path / "root.yaml"
    root.write_text("id: https://example.org/root\nname: root\nimports: [nested/middle]\n"
                    "classes:\n  Dataset:\n    is_a: Base\n")
    return root, base


def read(root, consumer):
    if consumer == "text":
        return schema_digest.digest_text("Dataset", root)
    if consumer == "build":
        return str(schema_digest.build("Dataset", root))
    return str(schema_view.shared_view(root).induced_slot("subject", "Dataset").description)


@pytest.mark.parametrize("consumer", ["build", "text", "view"])
def test_transitive_import_change_invalidates_warm_cache(imported, consumer):
    root, base = imported
    assert "country" in read(root, consumer)
    base.write_text(base.read_text().replace("country", "species"))
    assert "species" in read(root, consumer)


@pytest.mark.parametrize("consumer", ["build", "text", "view"])
def test_transitive_import_is_parsed_from_the_bytes_hashed(imported, monkeypatch, consumer):
    root, base = imported
    original = base.read_bytes()
    replace_after_read(monkeypatch, base, original.replace(b"country", b"species"))
    first = read(root, consumer)
    assert "country" in first
    base.write_bytes(original)
    assert read(root, consumer) == first


@pytest.mark.parametrize("consumer", ["build", "text", "view"])
def test_import_edit_when_linkml_starts_parsing_cannot_change_the_snapshot(imported, monkeypatch, consumer):
    root, base = imported
    original = base.read_bytes()
    load = schema_view.yaml_loader.loads
    changed = False

    def edit_after_capture(*args, **kwargs):
        nonlocal changed
        if not changed:
            changed = True
            base.write_bytes(original.replace(b"country", b"species"))
        return load(*args, **kwargs)

    monkeypatch.setattr(schema_view.yaml_loader, "loads", edit_after_capture)
    first = read(root, consumer)
    assert changed and "country" in first
    base.write_bytes(original)
    assert read(root, consumer) == first


def test_fitness_refreshes_when_only_an_import_changes(imported, monkeypatch):
    root, base = imported
    calls = []

    def fake(client, **kwargs):
        calls.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"fitness":1}')],
                               stop_reason="end_turn", usage=None)

    monkeypatch.setattr(api_runner, "_call_with_retry", fake)
    scorer = LLMSlotFitnessScorer(client=object(), model="offline-test", schema_path=root)
    before = scorer._context("offline-test")
    scorer(project="offline", slot="subject", value="place")
    base.write_text(base.read_text().replace("country", "species"))
    after = scorer._context("offline-test")
    scorer(project="offline", slot="subject", value="place")
    assert before != after
    assert len(calls) == 2 and "species" in calls[1]
