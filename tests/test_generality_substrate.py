"""D66/F6: declared neutral substrate terms survive schema generation."""
from pathlib import Path
import yaml

from data_sheets_schema import schema_digest
from data_sheets_schema.profiles import NEUTRAL, BRIDGE2AI

ROOT = Path(__file__).resolve().parents[1]
SOURCES = 'EDAM Data, EDAM Format, IANA media types'


def test_edam_curie_prefix_survives_full_and_core_generation():
    from linkml_runtime.utils.schemaview import SchemaView
    for name in ('data_sheets_schema_all.yaml', 'data_sheets_schema_core_all.yaml'):
        view = SchemaView(str(ROOT / 'src/data_sheets_schema/schema' / name))
        assert str(view.schema.prefixes['EDAM'].prefix_reference) == 'http://edamontology.org/'
        for curie in ('EDAM:data_0006', 'EDAM:format_3752'):
            assert str(view.namespaces().uri_for(curie)) == 'http://edamontology.org/' + curie.split(':')[1]


def test_declared_substrate_sources_survive_merge_and_neutral_rendering():
    schema = ROOT / 'src/data_sheets_schema/schema'
    for filename in ('D4D_Composition.yaml', 'data_sheets_schema_all.yaml',
                     'data_sheets_schema_core_all.yaml'):
        doc = yaml.safe_load((schema / filename).read_text())
        slot = doc['classes']['Instance']['attributes']['data_substrate']
        assert slot['description'].startswith(
            "Type or format of data (e.g., raw text, images): an EDAM Data or Format term "
            "or an IANA media type, written as a CURIE with the schema's declared `EDAM` "
            "or `mediatypes` prefix, when the documents supply one; or a term from the "
            "selected profile's pinned standards registry. A *term*, not a description:")
        annotation = slot['annotations']['d4d:termSources']
        assert (annotation.get('value') if isinstance(annotation, dict) else annotation) == SOURCES
    neutral = schema_digest.digest_text('Dataset', profile=NEUTRAL)
    assert SOURCES in neutral
    assert 'B2AI_SUBSTRATE:' not in neutral
    assert SOURCES in schema_digest.digest_text('Dataset', profile=BRIDGE2AI)


def test_unannotated_schema_renders_no_substrate_sources(tmp_path):
    # Simulate the historical schema shape without relying on an offline Git
    # merge object being available in the eventual cherry-picked checkout.
    document = yaml.safe_load((ROOT / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml').read_bytes())
    slot = document['classes']['Instance']['attributes']['data_substrate']
    del slot['annotations']['d4d:termSources']
    older = tmp_path / 'without_substrate_annotation.yaml'
    older.write_text(yaml.safe_dump(document, sort_keys=False))
    rendered = schema_digest.digest_text('Dataset', older, profile=NEUTRAL)
    assert SOURCES not in rendered
    assert 'B2AI_SUBSTRATE:' not in rendered
