"""D66/F6: declared neutral substrate terms survive schema generation."""
from pathlib import Path
import yaml

from data_sheets_schema import schema_digest
from data_sheets_schema.profiles import NEUTRAL, BRIDGE2AI

ROOT = Path(__file__).resolve().parents[1]
SOURCES = 'EDAM Data, EDAM Format, IANA media types'


def test_declared_substrate_sources_survive_merge_and_neutral_rendering():
    schema = ROOT / 'src/data_sheets_schema/schema'
    for filename in ('D4D_Composition.yaml', 'data_sheets_schema_all.yaml',
                     'data_sheets_schema_core_all.yaml'):
        doc = yaml.safe_load((schema / filename).read_text())
        slot = doc['classes']['Instance']['attributes']['data_substrate']
        annotation = slot['annotations']['d4d:termSources']
        assert (annotation.get('value') if isinstance(annotation, dict) else annotation) == SOURCES
    neutral = schema_digest.digest_text('Dataset', profile=NEUTRAL)
    assert SOURCES in neutral
    assert 'B2AI_SUBSTRATE:' not in neutral
    assert SOURCES in schema_digest.digest_text('Dataset', profile=BRIDGE2AI)


def test_older_schema_has_neutral_fallback_without_profile_vocabulary():
    assert schema_digest.TERM_SOURCES[('Instance', 'data_substrate')] == SOURCES
