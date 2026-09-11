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
