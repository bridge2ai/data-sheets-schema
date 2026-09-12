"""Snapshots preserve LinkML loading semantics and reuse stable aliases."""

import weakref

import pytest
import yaml
from linkml_runtime import SchemaView

from data_sheets_schema import schema_digest, schema_view


def schema(description="country"):
    return {"id": "https://example.org/root", "name": "root", "default_range": "string",
            "classes": {"Dataset": {"attributes": {"subject": {"description": f"Enter a {description}."}}}}}


def test_alternating_logical_aliases_reuse_views_without_retaining_more(tmp_path):
    directory = tmp_path / "actual"
    directory.mkdir()
    path = directory / "schema.yaml"
    path.write_text(yaml.safe_dump(schema()))
    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    paths = [path, alias / path.name]
    refs = weakref.WeakSet()
    first = {}
    for p in paths * 4:
        view = schema_view.shared_view(p)
        view.all_classes()  # LinkML's method cache pins this view.
        refs.add(view)
        if p in first:
            assert id(view) == first[p]
        first[p] = id(view)
    assert len(refs) <= 2


def test_import_prefix_override_matches_the_installed_linkml_resolver(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    root = tmp_path / "root.yaml"
    root.write_text(yaml.safe_dump({"id": "https://example.org/root", "name": "root",
                                    "prefixes": {"local": str(old) + "/"},
                                    "imports": ["local:second", "local:first"]}))
    (old / "first.yaml").write_text(yaml.safe_dump({"id": "https://example.org/first", "name": "first",
                                                    "prefixes": {"local": str(new) + "/"}}))
    for directory, word in [(old, "country"), (new, "species")]:
        doc = schema(word)
        doc.update(id="https://example.org/second", name="second")
        (directory / "second.yaml").write_text(yaml.safe_dump(doc))
    direct_view = SchemaView(str(root))
    direct = direct_view.induced_slot("subject", "Dataset").description
    assert direct == "Enter a country."
    captured = schema_view.shared_view(root)
    assert captured.induced_slot("subject", "Dataset").description == direct
    assert captured.namespaces()["local"] == direct_view.namespaces()["local"]
    assert schema_digest.build("Dataset", root).slots[0].description == direct


@pytest.mark.parametrize("location", ["root", "import"])
def test_list_form_prefixes_match_direct_linkml(tmp_path, location):
    doc = schema()
    doc["prefixes"] = [{"prefix_prefix": "example", "prefix_reference": "https://example.org/"}]
    root = tmp_path / "root.yaml"
    if location == "import":
        doc.update(id="https://example.org/base", name="base")
        (tmp_path / "base.yaml").write_text(yaml.safe_dump(doc))
        root.write_text("id: https://example.org/root\nname: root\nimports: [base]\n")
    else:
        root.write_text(yaml.safe_dump(doc))
    direct = SchemaView(str(root)).induced_slot("subject", "Dataset").description
    assert schema_view.shared_view(root).induced_slot("subject", "Dataset").description == direct
    assert schema_digest.build("Dataset", root).slots[0].description == direct
    assert direct in schema_digest.digest_text("Dataset", root)


def selection_root(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    old.mkdir()
    new.mkdir()
    root = tmp_path / "root.yaml"
    root.write_text(yaml.safe_dump({"id": "https://example.org/root", "name": "root",
                                    "prefixes": {"local": str(old) + "/"},
                                    "imports": ["local:second", "first"]}))
    (tmp_path / "first.yaml").write_text(yaml.safe_dump({"id": "https://example.org/first", "name": "first",
                                                        "prefixes": {"local": str(new) + "/"}}))
    for directory, word in [(old, "country"), (new, "species")]:
        doc = schema(word)
        doc.update(id="https://example.org/second", name="second")
        (directory / "second.yaml").write_text(yaml.safe_dump(doc))
    return root


@pytest.mark.parametrize("early", [False, True])
def test_namespace_initialization_order_selects_the_same_captured_file(tmp_path, early):
    root = selection_root(tmp_path)
    direct, captured = SchemaView(str(root)), schema_view.shared_view(root)
    if early:
        direct.namespaces()
        captured.namespaces()
    expected = "Enter a country." if early else "Enter a species."
    assert direct.induced_slot("subject", "Dataset").description == expected
    assert captured.induced_slot("subject", "Dataset").description == expected
    assert schema_digest.build("Dataset", root).slots[0].description == expected


def test_inventory_cache_cannot_reuse_another_views_import_selection(tmp_path):
    root = selection_root(tmp_path)
    assert schema_digest.build("Dataset", root).slots[0].description == "Enter a species."
    original = root.read_bytes()
    root.write_bytes(original + b"description: temporary revision\n")
    schema_view.shared_view(root)
    root.write_bytes(original)
    schema_view.shared_view(root).namespaces()
    assert schema_digest.build("Dataset", root).slots[0].description == "Enter a country."


@pytest.mark.parametrize("missing", ["old", "new"])
def test_an_unavailable_alternative_does_not_block_the_selected_import(tmp_path, missing):
    root = selection_root(tmp_path)
    (tmp_path / missing / "second.yaml").unlink()
    direct, captured = SchemaView(str(root)), schema_view.shared_view(root)
    if missing == "new":
        direct.namespaces()
        captured.namespaces()
    expected = direct.induced_slot("subject", "Dataset").description
    assert captured.induced_slot("subject", "Dataset").description == expected


@pytest.mark.parametrize("spelling", ["linkml:types", "https://w3id.org/linkml/types"])
def test_official_package_imports_work_without_network(tmp_path, monkeypatch, spelling):
    import socket
    def no_network(*args, **kwargs):
        raise AssertionError("an installed package import must stay offline")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    root = tmp_path / "root.yaml"
    doc = schema()
    doc["imports"] = [spelling]
    root.write_text(yaml.safe_dump(doc))
    direct = SchemaView(str(root)).get_type("string")
    assert schema_view.shared_view(root).get_type("string").uri == direct.uri
    assert schema_digest.build("Dataset", root).slots[0].range == "string"


@pytest.mark.parametrize("location", ["root", "import"])
def test_flow_yaml_without_final_newline_is_parsed_as_captured_content(tmp_path, location):
    root = tmp_path / "root.yaml"
    if location == "import":
        (tmp_path / "base.yaml").write_text("{id: urn:example:base, name: base, classes: {Dataset: {}}}")
        root.write_text("id: urn:example:root\nname: root\nimports: [base]\n")
    else:
        root.write_text("{id: urn:example:root, name: root, classes: {Dataset: {}}}")
    expected = list(SchemaView(str(root)).all_classes())
    assert expected == ["Dataset"]
    assert list(schema_view.shared_view(root).all_classes()) == expected
    assert schema_digest.build("Dataset", root).slots == []
