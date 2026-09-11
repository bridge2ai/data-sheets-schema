"""Review identifier flags follow the regenerated merged schema (#948)."""

import subprocess

from data_sheets_schema import review_pack
from data_sheets_schema.constants import schemas


def test_imported_identifier_change_refreshes_a_warm_review_pack(tmp_path, monkeypatch):
    source = tmp_path / "data_sheets_schema.yaml"
    root_bytes = b"id: https://example.org/root\nname: root\nimports: [module]\n"
    source.write_bytes(root_bytes)
    module = tmp_path / "module.yaml"
    module_text = (
        "id: https://example.org/module\nname: module\ndefault_range: string\n"
        "classes:\n  Dataset:\n    attributes:\n      subsets:\n"
        "        range: DataSubset\n        multivalued: true\n"
        "        inlined_as_list: true\n  DataSubset:\n    attributes:\n"
        "      id:\n        identifier: true\n"
    )
    module.write_text(module_text)
    merged = tmp_path / "data_sheets_schema_all.yaml"
    monkeypatch.setattr(schemas, "SCHEMA_PATH", source)
    monkeypatch.setattr(schemas, "SCHEMA_FULL_PATH", merged)

    def regenerate():
        subprocess.run(["poetry", "run", "gen-linkml", "-f", "yaml", "-o", str(merged),
                        str(source)], check=True, capture_output=True, text=True)

    record = {"id": "urn:dataset:test", "subsets": [{"id": "urn:dataset:test#one"}]}
    regenerate()
    first, gap = review_pack._id_slots(record)
    assert gap is None
    assert first[0]["identifier"] and first[0]["forced"]

    module.write_text(module_text.replace("identifier: true", "identifier: false"))
    regenerate()
    assert source.read_bytes() == root_bytes
    second, gap = review_pack._id_slots(record)
    assert gap is None
    assert second[0]["class"] == "DataSubset"
    assert not second[0]["identifier"] and not second[0]["forced"]
