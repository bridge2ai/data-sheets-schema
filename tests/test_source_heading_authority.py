"""Captured authority uses the ordinary compiler without ambient source reads."""
from pathlib import Path
from unittest.mock import patch

import pytest

from data_sheets_schema.schema_snapshot import capture_schema
from data_sheets_schema.schema_view import captured_view
from semantic_exchange.generate_comprehensive_sssom import ComprehensiveSSSOMGenerator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml'
TTL = ROOT / 'src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl'
RECS = ROOT / 'notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv'


def test_captured_real_authority_preserves_ordinary_compiler_bytes():
    ordinary = ComprehensiveSSSOMGenerator(SCHEMA, TTL, RECS)
    expected = ordinary.render_sssom('2026-10-02')
    snapshot = capture_schema(SCHEMA, strict=True)
    ttl, recs = TTL.read_text(), RECS.read_text()
    with captured_view(snapshot) as view:
        with patch.object(Path, 'read_text', side_effect=AssertionError('ambient text read')), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('ambient byte read')):
            captured = ComprehensiveSSSOMGenerator.from_captured(view, ttl, recs)
            assert captured.render_sssom('2026-10-02') == expected
            assert list(captured.warnings()) == list(ordinary.warnings())


@pytest.mark.parametrize('which,bad', [('view', object()), ('ttl', b'text'), ('recs', b'text')])
def test_captured_compiler_requires_explicit_typed_inputs(which, bad):
    with captured_view(capture_schema(SCHEMA, strict=True)) as view:
        args = [view, '', None]
        args[{'view': 0, 'ttl': 1, 'recs': 2}[which]] = bad
        with pytest.raises(TypeError):
            ComprehensiveSSSOMGenerator.from_captured(*args)
