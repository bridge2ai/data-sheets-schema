"""List-valued primitive slots must not disappear as scalar defaults (#1771)."""
import pytest

from data_sheets_schema import evidence_score, profiles, schema_digest
from data_sheets_schema.schema_view import shared_view


@pytest.mark.parametrize("target", ["Dataset", "CoreDataset"])
@pytest.mark.parametrize("profile", [profiles.NEUTRAL, profiles.BRIDGE2AI], ids=lambda p: p.name)
@pytest.mark.parametrize("slot,cls,attribute", [
    ("external_resources", "ExternalResource", "external_resources"),
    ("machine_annotation_tools", "MachineAnnotationTools", "tools"),
    ("existing_uses", "ExistingUse", "examples"),
])
def test_real_generation_and_fitness_show_schema_cardinality(target, profile, slot, cls, attribute):
    view = shared_view(schema_digest.CLASS_SCHEMA[target])
    declaration = view.induced_slot(attribute, cls)
    assert declaration.multivalued and declaration.range == "string"
    text = schema_digest.digest_text(target, profile=profile)
    block = text.split(f"- **{cls}**", 1)[1].split("\n- **", 1)[0]
    assert f"`{attribute}`: string[]" in block
    judged = evidence_score.slot_spec(slot, target, profile=profile)
    assert f"{attribute} → string[]" in judged


def test_external_schema_retains_one_element_list_obligation(tmp_path):
    schema = tmp_path / "external.yaml"
    schema.write_text("""id: https://example.org/schema
name: external
prefixes:
  linkml: https://w3id.org/linkml/
imports: [linkml:types]
default_range: string
classes:
  Catalogue:
    attributes:
      item:
        range: Item
        inlined: true
  Item:
    attributes:
      label: {}
      aliases:
        multivalued: true
""")
    digest = schema_digest.build("Catalogue", schema)
    text = schema_digest.render(digest, vocabulary={})
    assert "`aliases`: string[]" in text and "`label`: string" not in text
    spec = evidence_score.slot_spec("item", "Catalogue", schema, profile=profiles.NEUTRAL)
    assert "aliases → string[]" in spec and "label → string" not in spec
    # A scalar/list change must invalidate the instrument identity.
    schema.write_text(schema.read_text().replace("multivalued: true", "multivalued: false"))
    scalar = schema_digest.render(schema_digest.build("Catalogue", schema), vocabulary={})
    assert "`aliases`: string[]" not in scalar
    assert schema_digest.fingerprint(text) != schema_digest.fingerprint(scalar)
